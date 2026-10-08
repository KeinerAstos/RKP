"""Recolector INIT integrado; CSV como única persistencia."""

from __future__ import annotations

import argparse
import configparser
import csv
import ctypes
import ipaddress
import os
import re
import shutil
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock as ThreadLock
from typing import Iterable

from microservicios.config import settings

FIELDS = [
    "run_id",
    "alcance",
    "cmts",
    "ip",
    "fecha",
    "total_init",
    "ok",
    "estado",
    "error",
]
COMMAND = "show cable modem init"
MAX_OUTPUT_BYTES = 4 * 1024 * 1024
MAC = re.compile(
    r"(?<![\w])(?:[0-9a-f]{4}\.){2}[0-9a-f]{4}(?![\w])|(?<![\w])(?:[0-9a-f]{2}[:-]){5}[0-9a-f]{2}(?![\w])",
    re.I,
)
ERROR = re.compile(
    r"invalid (?:input|command)|unknown command|permission denied|not authorized|incomplete command|ambiguous command|--more--",
    re.I,
)
_RECONCILE_CACHE: dict[str, tuple[int, int, int, int]] = {}
_RECONCILE_CACHE_LOCK = ThreadLock()


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def data_dir() -> Path:
    project_root = Path(__file__).resolve().parents[3]
    path = Path(settings.cmts_init_data_path)
    if not path.is_absolute():
        path = project_root / path
    path = path.resolve()
    web_root = (project_root / "frontend").resolve()
    if path == web_root or web_root in path.parents:
        raise ValueError(
            "CMTS_INIT_DATA_PATH debe estar fuera del directorio servido por XAMPP"
        )
    path.mkdir(parents=True, exist_ok=True)
    return path


def inventory_path() -> Path:
    if settings.cmts_init_inventory_path:
        return Path(settings.cmts_init_inventory_path)
    return Path(__file__).with_name("inventario.ini")


def inventory(path: Path | None = None) -> list[dict[str, str]]:
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.optionxform = str
    if (
        not cfg.read(path or inventory_path(), encoding="utf-8-sig")
        or "CMTS" not in cfg
    ):
        raise ValueError("Inventario inválido: falta sección [CMTS]")
    result, seen = [], set()
    for name, address in cfg["CMTS"].items():
        address = str(ipaddress.ip_address(address.strip()))
        if address not in seen:
            result.append({"cmts": name.strip(), "ip": address})
            seen.add(address)
    if not result:
        raise ValueError("Inventario vacío")
    return result


def severity(total: int) -> str:
    if total == 0:
        return "SIN INIT"
    if total <= settings.cmts_init_threshold_attention_max:
        return "ATENCION"
    if total <= settings.cmts_init_threshold_risk_max:
        return "RIESGO"
    return "CRITICO"


def validate_output(data: bytes, errors: bytes, exit_status: int) -> int:
    if len(data) + len(errors) > MAX_OUTPUT_BYTES:
        raise ValueError("Salida supera 4 MiB; resultado incompleto")
    if exit_status != 0 or errors.strip():
        raise ValueError("Comando SSH falló; revisar compatibilidad CLI/permisos")
    return parse(data.decode(errors="replace"))


def _atomic_csv(path: Path, rows: Iterable[dict]) -> None:
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temp.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def _pid_alive(pid: int) -> bool:
    if os.name == "nt":
        kernel = ctypes.windll.kernel32
        kernel.OpenProcess.restype = ctypes.c_void_p
        handle = kernel.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE
        if not handle:
            return False
        try:
            return kernel.WaitForSingleObject(handle, 0) == 0x00000102  # WAIT_TIMEOUT
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True
    except (OSError, ValueError):
        return False


def _acquire_lock(
    path: Path, run_id: str, alcance: str = "global", cmts: str = ""
) -> None:
    lock = path / "consulta.lock"
    for _ in range(2):
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(
                    f"pid={os.getpid()}\nrun_id={run_id}\nstarted={now()}\nalcance={alcance}\ncmts={cmts}\n"
                )
            return
        except FileExistsError:
            try:
                content = lock.read_text(encoding="utf-8")
                pid = int(re.search(r"pid=(\d+)", content).group(1))
            except (OSError, ValueError, AttributeError):
                pid = -1
            if pid > 0 and _pid_alive(pid):
                raise RuntimeError("Ya hay un ciclo INIT activo")
            if pid < 0:
                try:
                    if time.time() - lock.stat().st_mtime < 30:
                        raise RuntimeError(
                            "Se está inicializando el lock de otro ciclo INIT"
                        )
                except FileNotFoundError:
                    continue
            try:
                lock.unlink()
            except FileNotFoundError:
                pass
    raise RuntimeError("No fue posible adquirir el lock del ciclo INIT")


def claim_cycle(alcance: str = "global", cmts: str = "") -> dict:
    """Reserva un ciclo global o una prueba aislada entre procesos."""
    path = data_dir()
    try:
        _acquire_lock(path, uuid.uuid4().hex, alcance, cmts)
        values = dict(
            line.split("=", 1)
            for line in (path / "consulta.lock")
            .read_text(encoding="utf-8")
            .splitlines()
            if "=" in line
        )
        return {
            "run_id": values["run_id"],
            "started": values["started"],
            "alcance": alcance,
            "cmts": cmts,
            "created": True,
        }
    except RuntimeError:
        try:
            values = dict(
                line.split("=", 1)
                for line in (path / "consulta.lock")
                .read_text(encoding="utf-8")
                .splitlines()
                if "=" in line
            )
            if values.get("pid") and _pid_alive(int(values["pid"])):
                return {
                    "run_id": values.get("run_id"),
                    "started": values.get("started"),
                    "alcance": values.get("alcance", "global"),
                    "cmts": values.get("cmts", ""),
                    "created": False,
                }
        except (OSError, ValueError):
            pass
        raise


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != FIELDS:
            raise ValueError(f"Esquema inválido en {path.name}")
        return [normalize(row) for row in reader]


def normalize(row: dict) -> dict:
    total = row.get("total_init")
    try:
        total = int(total) if total not in (None, "") else None
    except (ValueError, TypeError):
        total = None
    return {**row, "total_init": total, "ok": str(row.get("ok", "")).lower() == "true"}


def _append_history(path: Path, rows: list[dict]) -> None:
    history = path / "historico.csv"
    temp = path / ("historico." + rows[0]["run_id"] + ".tmp")
    try:
        with temp.open("w", newline="", encoding="utf-8") as dest:
            if history.exists():
                with history.open("r", newline="", encoding="utf-8-sig") as src:
                    if next(csv.reader(src), []) != FIELDS:
                        raise ValueError("Esquema del histórico incompatible")
                    src.seek(0)
                    shutil.copyfileobj(src, dest, length=65536)
            else:
                csv.DictWriter(dest, fieldnames=FIELDS).writeheader()
            csv.DictWriter(dest, fieldnames=FIELDS).writerows(rows)
        os.replace(temp, history)
    finally:
        temp.unlink(missing_ok=True)


def reconcile_published_cycle(path: Path | None = None) -> None:
    """Completa el histórico si un apagado ocurrió después de publicar actual.csv."""
    path = path or data_dir()
    actual_path, history_path = path / "actual.csv", path / "historico.csv"

    def stamp(file: Path) -> tuple[int, int]:
        try:
            stat_result = file.stat()
            return stat_result.st_mtime_ns, stat_result.st_size
        except OSError:
            return 0, 0

    before = (*stamp(actual_path), *stamp(history_path))
    key = str(path.resolve())
    with _RECONCILE_CACHE_LOCK:
        if _RECONCILE_CACHE.get(key) == before:
            return
    run_id = uuid.uuid4().hex
    try:
        _acquire_lock(path, run_id)
    except RuntimeError:
        return
    lock = path / "consulta.lock"
    try:
        _reconcile_published_cycle_locked(path)
        after = (*stamp(actual_path), *stamp(history_path))
        with _RECONCILE_CACHE_LOCK:
            _RECONCILE_CACHE[key] = after
    finally:
        try:
            values = dict(
                line.split("=", 1)
                for line in lock.read_text(encoding="utf-8").splitlines()
                if "=" in line
            )
            if values.get("run_id") == run_id:
                lock.unlink(missing_ok=True)
        except OSError:
            pass


def _reconcile_published_cycle_locked(path: Path) -> None:
    published = read_csv(path / "actual.csv")
    if not published:
        return
    published_id = published[0]["run_id"]
    history = path / "historico.csv"
    if history.exists():
        with history.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames != FIELDS:
                raise ValueError("Esquema del histórico incompatible")
            if any(row.get("run_id") == published_id for row in reader):
                return
    _append_history(path, published)


def apply_retention(path: Path | None = None) -> None:
    path = path or data_dir()
    history = path / "historico.csv"
    if not history.exists() or settings.cmts_init_retention_days <= 0:
        return
    cutoff = datetime.now(timezone.utc) - timedelta(
        days=settings.cmts_init_retention_days
    )
    temp = path / ("historico.retent." + uuid.uuid4().hex + ".tmp")
    try:
        with history.open("r", newline="", encoding="utf-8-sig") as src, temp.open(
            "w", newline="", encoding="utf-8"
        ) as dst:
            reader = csv.DictReader(src)
            if reader.fieldnames != FIELDS:
                raise ValueError("Esquema del histórico incompatible")
            writer = csv.DictWriter(dst, fieldnames=FIELDS)
            writer.writeheader()
            for row in reader:
                try:
                    keep = (
                        datetime.fromisoformat(row["fecha"].replace("Z", "+00:00"))
                        >= cutoff
                    )
                except (ValueError, TypeError):
                    keep = True
                if keep:
                    writer.writerow(row)
        if temp.stat().st_size < history.stat().st_size:
            backup = path / (
                "historico.pre-retencion."
                + datetime.now().strftime("%Y%m%d%H%M%S")
                + ".csv"
            )
            shutil.copyfile(history, backup)
            os.replace(temp, history)
    finally:
        temp.unlink(missing_ok=True)


def status() -> dict:
    path = data_dir()
    reconcile_published_cycle(path)
    active = None
    try:
        values = dict(
            line.split("=", 1)
            for line in (path / "consulta.lock")
            .read_text(encoding="utf-8")
            .splitlines()
            if "=" in line
        )
        active = values
    except OSError:
        pass
    current = read_csv(path / "actual.csv")
    probe = read_csv(path / "prueba_equipo.csv")
    return {
        "enabled": settings.cmts_init_enabled,
        "configured": bool(settings.cmts_user and settings.cmts_password),
        "active": active is not None,
        "run_id": active.get("run_id") if active else None,
        "started_at": active.get("started") if active else None,
        "alcance_activo": active.get("alcance") if active else None,
        "cmts_activo": active.get("cmts") if active else None,
        "last_completed_at": max((r["fecha"] for r in current), default=None),
        "total": len(current),
        "last_probe": probe[0] if probe else None,
        "state": (
            "procesando" if active else ("disponible" if current else "sin_mediciones")
        ),
    }


def run_cycle(run_id: str | None = None, *, claimed: bool = False) -> dict:
    path = data_dir()
    run_id = run_id or uuid.uuid4().hex
    if not claimed:
        _acquire_lock(path, run_id)
    try:
        _reconcile_published_cycle_locked(path)
        if not settings.cmts_user or not settings.cmts_password:
            raise RuntimeError("Configura CMTS_USER y CMTS_PASSWORD")
        items = inventory()
        _write_progress(
            path,
            {
                "run_id": run_id,
                "started": now(),
                "completed": 0,
                "total": len(items),
                "estado": "procesando",
                "error": "",
            },
        )
        rows = []
        with ThreadPoolExecutor(
            max_workers=max(1, min(settings.cmts_init_max_workers, 20))
        ) as pool:
            for item, row in zip(items, pool.map(query, items)):
                row.update(run_id=run_id, alcance="global")
                rows.append(row)
                progress = {
                    "run_id": run_id,
                    "started": rows[0]["fecha"],
                    "completed": len(rows),
                    "total": len(items),
                    "estado": "procesando",
                    "error": "",
                }
                _write_progress(path, progress)
        rows.sort(key=lambda r: (not r["ok"], -(r["total_init"] or 0), r["cmts"]))
        _atomic_csv(path / "actual.csv", rows)
        _append_history(path, rows)
        apply_retention(path)
        _write_progress(
            path,
            {
                "run_id": run_id,
                "started": rows[0]["fecha"],
                "completed": len(rows),
                "total": len(items),
                "estado": "completo",
                "error": "",
            },
        )
        return {"run_id": run_id, "rows": rows, "completed_at": now()}
    except Exception as exc:
        try:
            progress = get_progress()
            _write_progress(
                path,
                {
                    "run_id": run_id,
                    "started": progress.get("started") or now(),
                    "completed": progress.get("completed", 0),
                    "total": progress.get("total", 0),
                    "estado": "error",
                    "error": str(exc)[:300],
                },
            )
        except Exception:
            pass
        raise
    finally:
        (path / "consulta.lock").unlink(missing_ok=True)


def run_probe(target: str, run_id: str | None = None, *, claimed: bool = False) -> dict:
    path = data_dir()
    run_id = run_id or uuid.uuid4().hex
    if not claimed:
        _acquire_lock(path, run_id, "equipo", target)
    try:
        if not settings.cmts_user or not settings.cmts_password:
            raise RuntimeError("Configura CMTS_USER y CMTS_PASSWORD")
        item = next(
            (
                x
                for x in inventory()
                if x["cmts"].casefold() == target.casefold() or x["ip"] == target
            ),
            None,
        )
        if item is None:
            raise ValueError("CMTS no encontrado en el inventario")
        _write_progress(
            path,
            {
                "run_id": run_id,
                "started": now(),
                "completed": 0,
                "total": 1,
                "estado": "procesando",
                "error": "",
                "alcance": "equipo",
                "cmts": item["cmts"],
            },
        )
        row = query(item)
        row.update(run_id=run_id, alcance="equipo")
        _atomic_csv(path / "prueba_equipo.csv", [row])
        _write_progress(
            path,
            {
                "run_id": run_id,
                "started": row["fecha"],
                "completed": 1,
                "total": 1,
                "estado": "completo",
                "error": row["error"],
                "alcance": "equipo",
                "cmts": item["cmts"],
            },
        )
        return row
    except Exception as exc:
        progress = get_progress()
        _write_progress(
            path,
            {
                "run_id": run_id,
                "started": progress.get("started") or now(),
                "completed": progress.get("completed", 0),
                "total": progress.get("total", 1),
                "estado": "error",
                "error": str(exc)[:300],
                "alcance": "equipo",
                "cmts": target,
            },
        )
        raise
    finally:
        (path / "consulta.lock").unlink(missing_ok=True)


def _write_progress(path: Path, values: dict) -> None:
    """El progreso es auxiliar; un bloqueo no aborta las consultas SSH."""
    progress = path / "progreso.csv"
    temp = path / ("progreso." + uuid.uuid4().hex + ".tmp")
    try:
        with temp.open("w", newline="", encoding="utf-8") as f:
            fields = [
                "run_id",
                "started",
                "completed",
                "total",
                "estado",
                "error",
                "alcance",
                "cmts",
            ]
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerow(values)
        for attempt in range(31):
            try:
                os.replace(temp, progress)
                return
            except PermissionError:
                if attempt == 30:
                    print(
                        "[CMTS INIT] AVISO: progreso.csv bloqueado; se conserva el progreso previo y continúa la consulta.",
                        flush=True,
                    )
                    return
                time.sleep(0.1)
    except PermissionError:
        print(
            "[CMTS INIT] AVISO: no se pudo escribir el progreso auxiliar; continúa la consulta.",
            flush=True,
        )
    finally:
        try:
            temp.unlink(missing_ok=True)
        except PermissionError:
            print(
                "[CMTS INIT] AVISO: temporal de progreso bloqueado; limpieza pendiente.",
                flush=True,
            )


def get_progress() -> dict:
    try:
        with (data_dir() / "progreso.csv").open(newline="", encoding="utf-8") as f:
            row = next(csv.DictReader(f))
        return {**row, "completed": int(row["completed"]), "total": int(row["total"])}
    except (OSError, StopIteration, ValueError, KeyError):
        return {}


def actual() -> list[dict]:
    return read_csv(data_dir() / "actual.csv")


def history(
    *,
    cmts: str = "",
    desde: str = "",
    hasta: str = "",
    limit: int = 100,
    offset: int = 0,
) -> dict:
    reconcile_published_cycle()
    from collections import deque

    rows = deque(maxlen=offset + limit)
    total = 0
    with (data_dir() / "historico.csv").open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != FIELDS:
            raise ValueError("Esquema del histórico incompatible")
        for raw in reader:
            if cmts and cmts.casefold() not in raw["cmts"].casefold():
                continue
            if not _in_range(raw["fecha"], desde, hasta):
                continue
            rows.append(raw)
            total += 1
    newest_first = list(reversed(rows))
    return {
        "items": [normalize(r) for r in newest_first[offset : offset + limit]],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def trend(cmts: str, limit: int = 200) -> list[dict]:
    # Streaming aggregation keeps memory bounded by output cap.
    reconcile_published_cycle()
    result = []
    with (data_dir() / "historico.csv").open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if (
                row.get("cmts", "").casefold() == cmts.casefold()
                and row.get("ok", "").lower() == "true"
                and row.get("total_init") not in (None, "")
            ):
                result.append(
                    {"fecha": row["fecha"], "total_init": int(row["total_init"])}
                )
                if len(result) > limit:
                    result.pop(0)
    return result


def export_rows(cmts: str = "", desde: str = "", hasta: str = ""):
    reconcile_published_cycle()
    history = data_dir() / "historico.csv"
    if not history.exists():
        return
    with history.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if cmts and cmts.casefold() not in row["cmts"].casefold():
                continue
            if not _in_range(row["fecha"], desde, hasta):
                continue
            yield row


def _in_range(value: str, start: str, end: str) -> bool:
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        timestamp = timestamp.astimezone(timezone.utc)
        if start:
            lower = datetime.fromisoformat(
                start + "T00:00:00+00:00"
                if len(start) == 10
                else start.replace("Z", "+00:00")
            )
            if lower.tzinfo is None:
                lower = lower.replace(tzinfo=timezone.utc)
            if timestamp < lower.astimezone(timezone.utc):
                return False
        if end:
            upper = datetime.fromisoformat(
                end + "T23:59:59.999999+00:00"
                if len(end) == 10
                else end.replace("Z", "+00:00")
            )
            if upper.tzinfo is None:
                upper = upper.replace(tzinfo=timezone.utc)
            if timestamp > upper.astimezone(timezone.utc):
                return False
        return True
    except (ValueError, TypeError):
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--equipo",
        help="Prueba aislada por nombre exacto o IP; no reemplaza actual.csv",
    )
    args = parser.parse_args()
    try:
        if args.equipo:
            row = run_probe(args.equipo)
            print(
                f"Prueba {row['cmts']}: {row['estado']} ({row['total_init']}) · {row['fecha']}"
            )
            return 0 if row["ok"] else 2
        result = run_cycle()
        failures = sum(not row["ok"] for row in result["rows"])
        print(
            f"Ciclo {result['run_id']} terminado: {len(result['rows'])} CMTS, {failures} consultas fallidas"
        )
        return 0 if failures == 0 else 2
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}")
        return 1


def parse(output: str) -> int:
    """Valida filas INIT y total explícito del CMTS; nunca cuenta cabeceras."""
    if ERROR.search(output):
        raise ValueError("Respuesta CLI de error o paginada")
    macs = set()
    for line in output.splitlines():
        match = MAC.match(line.strip())
        if match:
            if not re.search(r"\b(?:init|bpi)\([^\s)]+\)", line, re.I):
                raise ValueError(f"Fila MAC sin estado INIT reconocido: {line[:250]!r}")
            macs.add(re.sub(r"[.:-]", "", match.group()).lower())
    totals = re.findall(r"(?im)^\s*total\s+cm\s+(\d+)\s*$", output)
    if totals:
        total = int(totals[-1])
        if total != len(macs):
            raise ValueError(
                f"Salida incompleta/inconsistente: total cm {total}, filas únicas {len(macs)}"
            )
        return total
    if macs:
        return len(macs)
    if re.search(
        r"\b(?:total(?:\s+(?:cable\s+)?modems?)?\s*[:=]\s*0\b|no\s+(?:cable\s+)?modems?\s+(?:found|in\s+init)\b)",
        output,
        re.I,
    ):
        return 0
    raise ValueError("Salida no reconocida: no se publica cero")


def _read_cli_prompt(
    channel, deadline: float, prompt: str | None = None
) -> tuple[str, str]:
    data = bytearray()
    pages = 0
    while time.monotonic() < deadline:
        if channel.recv_ready():
            chunk = channel.recv(65536)
            if not chunk:
                raise ConnectionError("CLI cerró la sesión antes del prompt final")
            data.extend(chunk)
            if len(data) > MAX_OUTPUT_BYTES:
                raise ValueError("Salida supera 4 MiB; resultado incompleto")
            text = data.decode(errors="replace").replace("\r", "")
            text = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text)
            if re.search(r"--\s*more\s*--", text, re.I):
                pages += 1
                if pages > 1000:
                    raise ValueError("Límite de paginación excedido")
                text = re.sub(r"--\s*more\s*--", "", text, flags=re.I).replace("\b", "")
                data = bytearray(text.encode())
                channel.sendall(" ")
                continue
            if prompt:
                found = re.search(r"(?:^|\n)" + re.escape(prompt) + r"\s*\Z", text)
            else:
                found = re.search(r"(?:^|\n)([A-Za-z0-9_.:/()-]+[>#])\s*\Z", text)
            if found:
                return text, prompt or found.group(1)
        elif channel.closed:
            raise ConnectionError("CLI cerró la sesión antes del prompt final")
        time.sleep(0.02)
    raise TimeoutError("Timeout esperando prompt completo del CMTS")


def query(item: dict[str, str]) -> dict:
    import paramiko

    result = dict(
        item,
        fecha=now(),
        total_init=None,
        ok=False,
        estado="ERROR DE CONSULTA",
        error="",
    )
    client = paramiko.SSHClient()
    try:
        client.load_system_host_keys()
        if settings.cmts_known_hosts:
            client.load_host_keys(settings.cmts_known_hosts)
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
        client.connect(
            item["ip"],
            username=settings.cmts_user,
            password=settings.cmts_password,
            timeout=30,
            banner_timeout=30,
            auth_timeout=30,
            look_for_keys=False,
            allow_agent=False,
        )
        channel = client.invoke_shell(width=240, height=1000)
        channel.settimeout(90)
        deadline = time.monotonic() + 90
        _, prompt = _read_cli_prompt(channel, deadline)
        if not prompt.endswith("#"):
            raise ValueError(
                "Sesión sin prompt privilegiado #; revisar permisos del usuario"
            )
        channel.sendall(COMMAND + "\n")
        output, _ = _read_cli_prompt(channel, deadline, prompt)
        total = parse(output)
        result.update(total_init=total, ok=True, estado=severity(total))
    except Exception as exc:
        message = (
            str(exc).replace(settings.cmts_password, "<oculto>")
            if settings.cmts_password
            else str(exc)
        )
        result["error"] = f"{type(exc).__name__}: {message}"[:400]
    finally:
        client.close()
    return result


if __name__ == "__main__":
    raise SystemExit(main())
