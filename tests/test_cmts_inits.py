import csv
import threading
import time
from pathlib import Path

import pytest

from microservicios.cmts.inits import inits_cmts as service
from microservicios.cmts.inits.router import _with_delta


def test_parser_counts_unique_init_rows_and_zero():
    assert service.parse("0000.0000.0001 init(d)\n0000.0000.0001 init(d)\n0000.0000.0002 init(d)") == 2
    assert service.parse("Total cable modems: 0") == 0


@pytest.mark.parametrize("output", ["", "0000.0000.0001 online", "--More--"])
def test_parser_rejects_unknown_or_incomplete_output(output):
    with pytest.raises(ValueError):
        service.parse(output)


def test_output_rejects_truncated_ssh_result():
    with pytest.raises(ValueError, match="incompleto"):
        service.validate_output(b"x" * (service.MAX_OUTPUT_BYTES + 1), b"", 0)


def test_output_rejects_ssh_error_instead_of_publishing_zero():
    with pytest.raises(ValueError, match="SSH falló"):
        service.validate_output(b"Total cable modems: 0", b"permission denied", 0)


def test_csv_normalizes_boolean_and_blank_total(tmp_path):
    path = tmp_path / "actual.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=service.FIELDS)
        writer.writeheader()
        writer.writerow(dict(run_id="a", alcance="global", cmts="CMTS-A", ip="192.0.2.1", fecha=service.now(), total_init="", ok="False", estado="ERROR DE CONSULTA", error="SSH"))
    row = service.read_csv(path)[0]
    assert row["total_init"] is None
    assert row["ok"] is False


def test_history_paginates_without_loading_entire_file(monkeypatch, tmp_path):
    monkeypatch.setattr(service, "data_dir", lambda: tmp_path)
    with (tmp_path / "historico.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=service.FIELDS); writer.writeheader()
        for index in range(2500):
            writer.writerow(dict(run_id=str(index), alcance="global", cmts="CMTS-A", ip="192.0.2.1", fecha=f"2026-01-{(index % 28)+1:02d}T00:00:00+00:00", total_init=index, ok="True", estado="RIESGO", error=""))
    result = service.history(limit=50, offset=1000)
    assert result["total"] == 2500
    assert len(result["items"]) == 50
    assert result["items"][0]["run_id"] == "1499"


def test_delta_ignores_errors_and_never_compares_current_run(monkeypatch, tmp_path):
    monkeypatch.setattr(service, "data_dir", lambda: tmp_path)
    with (tmp_path / "historico.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=service.FIELDS); writer.writeheader()
        writer.writerow(dict(run_id="previous", alcance="global", cmts="CMTS-A", ip="192.0.2.1", fecha=service.now(), total_init=4, ok="True", estado="ATENCION", error=""))
        writer.writerow(dict(run_id="current", alcance="global", cmts="CMTS-A", ip="192.0.2.1", fecha=service.now(), total_init=0, ok="False", estado="ERROR DE CONSULTA", error="SSH"))
    rows = [dict(run_id="current", cmts="CMTS-A", total_init=None, ok=False, estado="ERROR DE CONSULTA")]
    assert _with_delta(rows)[0]["variacion"] is None
    rows = [dict(run_id="new", cmts="CMTS-A", total_init=7, ok=True, estado="ATENCION")]
    assert _with_delta(rows)[0]["variacion"] == 3


def test_delta_compares_against_valid_zero(monkeypatch, tmp_path):
    monkeypatch.setattr(service, "data_dir", lambda: tmp_path)
    with (tmp_path / "historico.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=service.FIELDS); writer.writeheader()
        writer.writerow(dict(run_id="previous", alcance="global", cmts="CMTS-Z", ip="192.0.2.9", fecha=service.now(), total_init=0, ok="True", estado="SIN INIT", error=""))
    rows = [dict(run_id="current", cmts="CMTS-Z", total_init=2, ok=True, estado="ATENCION")]
    assert _with_delta(rows)[0]["variacion"] == 2


def test_published_cycle_is_reconciled_after_interrupted_history_write(tmp_path):
    row = dict(run_id="published", alcance="global", cmts="CMTS-A", ip="192.0.2.1", fecha="2026-10-08T17:00:00+00:00", total_init=3, ok=True, estado="ATENCION", error="")
    service._atomic_csv(tmp_path / "actual.csv", [row])
    service.reconcile_published_cycle(tmp_path)
    service.reconcile_published_cycle(tmp_path)
    history = service.read_csv(tmp_path / "historico.csv")
    assert len(history) == 1
    assert history[0]["run_id"] == "published"


def test_cycle_claim_is_global_and_recovers_dead_process_lock(monkeypatch, tmp_path):
    monkeypatch.setattr(service, "data_dir", lambda: tmp_path)
    first = service.claim_cycle()
    second = service.claim_cycle()
    assert first["created"] is True
    assert second["created"] is False
    (tmp_path / "consulta.lock").write_text("pid=2147483647\nrun_id=dead\nstarted=2020-01-01T00:00:00+00:00\n", encoding="utf-8")
    recovered = service.claim_cycle()
    assert recovered["created"] is True
    assert recovered["run_id"] != "dead"
    (tmp_path / "consulta.lock").unlink(missing_ok=True)


def test_retention_streams_csv_and_saves_backup(monkeypatch, tmp_path):
    monkeypatch.setattr(service.settings, "cmts_init_retention_days", 90)
    old = dict(run_id="old", alcance="global", cmts="CMTS-A", ip="192.0.2.1", fecha="2020-01-01T00:00:00+00:00", total_init=1, ok="True", estado="ATENCION", error="")
    fresh = dict(run_id="fresh", alcance="global", cmts="CMTS-A", ip="192.0.2.1", fecha=service.now(), total_init=2, ok="True", estado="ATENCION", error="")
    service._atomic_csv(tmp_path / "historico.csv", [old, fresh])
    service.apply_retention(tmp_path)
    rows = service.read_csv(tmp_path / "historico.csv")
    assert [row["run_id"] for row in rows] == ["fresh"]
    assert list(tmp_path.glob("historico.pre-retencion.*.csv"))


def test_probe_writes_only_probe_csv_and_preserves_published_cycle(monkeypatch, tmp_path):
    monkeypatch.setattr(service, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(service, "inventory", lambda: [{"cmts": "CMTS-A", "ip": "192.0.2.1"}])
    monkeypatch.setattr(service, "query", lambda item: dict(item, fecha=service.now(), total_init=2, ok=True, estado="ATENCION", error=""))
    monkeypatch.setattr(service.settings, "cmts_user", "test-user")
    monkeypatch.setattr(service.settings, "cmts_password", "test-password")
    published = dict(run_id="global-old", alcance="global", cmts="CMTS-A", ip="192.0.2.1", fecha=service.now(), total_init=8, ok=True, estado="ATENCION", error="")
    service._atomic_csv(tmp_path / "actual.csv", [published])
    before = (tmp_path / "actual.csv").read_bytes()
    row = service.run_probe("CMTS-A")
    assert row["run_id"]
    assert (tmp_path / "actual.csv").read_bytes() == before
    assert service.read_csv(tmp_path / "prueba_equipo.csv")[0]["alcance"] == "equipo"
    assert not (tmp_path / "historico.csv").exists()


def test_date_range_end_day_is_inclusive():
    assert service._in_range("2026-10-08T22:00:00+00:00", "2026-10-08", "2026-10-08")
    assert not service._in_range("2026-10-09T00:00:00+00:00", "2026-10-08", "2026-10-08")


def test_excel_csv_text_prefixes_are_neutralized_only_on_text_columns():
    from microservicios.cmts.inits.router import _safe_cell
    assert _safe_cell("=HYPERLINK('x')", False).startswith("'=")
    assert _safe_cell("192.0.2.1", False) == "192.0.2.1"
    assert _safe_cell("-2", True) == "-2"


def test_get_actual_reads_csv_without_ssh(monkeypatch, tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from microservicios.cmts.inits.router import router
    monkeypatch.setattr(service, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(service, "query", lambda _item: (_ for _ in ()).throw(AssertionError("GET no debe consultar SSH")))
    app = FastAPI(); app.include_router(router, prefix="/api/cmts")
    response = TestClient(app).get("/api/cmts/inits/actual")
    assert response.status_code == 200
    assert response.json()["data"]["items"] == []


def test_post_returns_while_cycle_runs_in_background(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from microservicios.cmts.inits import router as routes
    started, release, finished = threading.Event(), threading.Event(), threading.Event()
    monkeypatch.setattr(routes.settings, "cmts_init_enabled", True)
    monkeypatch.setattr(routes.settings, "cmts_user", "test-user")
    monkeypatch.setattr(routes.settings, "cmts_password", "test-password")
    monkeypatch.setattr(service, "claim_cycle", lambda: {"run_id": "mock-run", "created": True})
    def slow_cycle(*_args, **_kwargs):
        started.set(); release.wait(10); finished.set()
    monkeypatch.setattr(service, "run_cycle", slow_cycle)
    routes._cycle_task = None
    app = FastAPI(); app.include_router(routes.router, prefix="/api/cmts")
    try:
        with TestClient(app) as client:
            response = client.post("/api/cmts/inits/actualizar")
            assert response.status_code == 202
            assert response.json()["run_id"] == "mock-run"
            assert started.wait(1)
            assert not finished.is_set()
            release.set()
    finally:
        release.set()
        deadline = time.monotonic() + 2
        while routes._cycle_task is not None and time.monotonic() < deadline:
            time.sleep(.01)
