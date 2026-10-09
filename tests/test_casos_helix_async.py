"""Tests focalizados del worker Helix; no requieren Oracle ni el puente."""

import time
import unittest
from threading import Event, get_ident
from unittest.mock import patch

from microservicios.config import Settings, settings
from microservicios.olt.casos_helix import service
from microservicios.olt.casos_helix import worker as worker_module
from microservicios.olt.casos_helix.router import SolicitudLote, casos_abiertos, casos_abiertos_lote
from microservicios.olt.casos_helix.worker import HelixWorker


OLT = "HAC-BAR.ALKARAWI-M1-MA5800"


def esperar(predicate, timeout=2.0):
    limit = time.monotonic() + timeout
    while time.monotonic() < limit:
        if predicate():
            return True
        time.sleep(0.005)
    return predicate()


class WorkerTests(unittest.TestCase):
    def test_pending_deduplicates_and_publishes_complete_result(self):
        entered, release = Event(), Event()
        calls = []
        thread_ids = []
        now = [100.0]

        def query(olt, _register_cancel):
            calls.append(olt)
            thread_ids.append(get_ident())
            entered.set()
            release.wait(2)
            return {"0/9/3": [{"tipo": "INC", "numero": "INC1", "estado": "In Progress"}]}, "2026-10-08T16:20:00+00:00"

        worker = HelixWorker(query, clock=lambda: now[0])
        worker.start()
        try:
            first = worker.submit(OLT, ["0/9/3"])
            self.assertEqual(first["estado"], "actualizando")
            self.assertIsNone(first["puertos"]["0/9/3"]["casos"])
            self.assertTrue(entered.wait(1))
            self.assertNotEqual(thread_ids[0], get_ident())
            now[0] = 146.0  # Simula 46 segundos sin dormir el test.
            second = worker.submit(OLT, ["0/9/3", "0/9/4"])
            self.assertEqual(second["estado"], "actualizando")
            self.assertEqual(calls, [OLT])
            result = worker.read(OLT, ["0/9/3"])
            self.assertEqual(result["puertos"]["0/9/3"]["casos"], None)
            release.set()
            self.assertTrue(esperar(lambda: worker.read(OLT, ["0/9/3"])["estado"] == "listo"))
            ready = worker.read(OLT, ["0/9/3", "0/9/4"])
            self.assertEqual(ready["puertos"]["0/9/3"]["casos"][0]["numero"], "INC1")
            self.assertEqual(ready["puertos"]["0/9/4"]["casos"], [])
        finally:
            release.set()
            worker.stop()

    def test_ttl_starts_at_completion_and_status_reads_do_not_extend_it(self):
        now = [100.0]
        count = [0]

        def query(_olt, _register_cancel):
            count[0] += 1
            return {}, "2026-10-08T16:20:00+00:00"

        worker = HelixWorker(query, ttl_seconds=60, clock=lambda: now[0])
        worker.start()
        try:
            worker.submit(OLT, ["0/9/3"])
            self.assertTrue(esperar(lambda: worker.read(OLT, ["0/9/3"])["estado"] == "listo"))
            now[0] = 145
            worker.read(OLT, ["0/9/3"])
            now[0] = 161
            next_state = worker.submit(OLT, ["0/9/3"])
            self.assertEqual(next_state["estado"], "actualizando")
            self.assertTrue(esperar(lambda: count[0] == 2 and worker.read(OLT, ["0/9/3"])["estado"] == "listo"))
            self.assertEqual(worker.read(OLT, ["0/9/3"])["puertos"]["0/9/3"]["casos"], [])
        finally:
            worker.stop()

    def test_terminal_cache_is_bounded(self):
        worker = HelixWorker(lambda _olt, _cancel: ({}, "2026-10-08T16:20:00+00:00"), max_cache=2)
        worker.start()
        try:
            for index in range(5):
                worker.submit(f"OLT-{index}", ["0/0/1"])
                self.assertTrue(esperar(lambda i=index: worker.read(f"OLT-{i}", ["0/0/1"])["estado"] == "listo"))
            terminal = [state for state in worker._states.values() if state.estado in {"listo", "error"}]
            self.assertLessEqual(len(terminal), 2)
        finally:
            worker.stop()

    def test_queue_is_bounded_and_failure_has_cooldown(self):
        entered, release = Event(), Event()
        calls = []

        def query(olt, _register_cancel):
            calls.append(olt)
            entered.set()
            release.wait(2)
            raise RuntimeError("private SQL details")

        now = [50.0]
        worker = HelixWorker(query, max_pending=1, retry_seconds=30, clock=lambda: now[0])
        worker.start()
        try:
            worker.submit("OLT-A", ["0/0/1"])
            self.assertTrue(entered.wait(1))
            self.assertEqual(worker.submit("OLT-B", ["0/0/1"])["estado"], "actualizando")
            full = worker.submit("OLT-C", ["0/0/1"])
            self.assertEqual(full["error"]["codigo"], "QUEUE_FULL")
            release.set()
            self.assertTrue(esperar(lambda: worker.read("OLT-A", ["0/0/1"])["estado"] == "error"))
            failed = worker.submit("OLT-A", ["0/0/1"])
            self.assertEqual(failed["estado"], "error")
            self.assertNotIn("private SQL", str(failed))
            self.assertEqual(calls.count("OLT-A"), 1)
            now[0] += 31
            worker.submit("OLT-A", ["0/0/1"])
            self.assertTrue(esperar(lambda: calls.count("OLT-A") == 2))
        finally:
            release.set()
            worker.stop()

    def test_stop_cancels_active_sentence_without_long_join(self):
        started, cancelled = Event(), Event()

        def query(_olt, register_cancel):
            register_cancel(cancelled.set)
            started.set()
            cancelled.wait(3)
            return {}, "2026-10-08T16:20:00+00:00"

        worker = HelixWorker(query)
        worker.start()
        worker.submit(OLT, ["0/9/3"])
        self.assertTrue(started.wait(1))
        before = time.monotonic()
        worker.stop(join_seconds=0.1)
        self.assertLess(time.monotonic() - before, 0.5)
        self.assertTrue(cancelled.is_set())


class ConfigurationAndOracleMockTests(unittest.TestCase):
    def test_legacy_get_keeps_shape_and_marks_pending_without_empty_list(self):
        class FakeWorker:
            def submit(self, olt, ports):
                return {
                    "olt": olt, "estado": "actualizando", "job_id": "job-1",
                    "generacion": 1, "revision": 1, "consultado_en": None,
                    "puertos": {port: {"estado": "actualizando", "casos": None} for port in ports},
                }

        with patch.object(worker_module, "get_worker", return_value=FakeWorker()):
            response = casos_abiertos(OLT, "00/09/03")
        self.assertTrue(response["ok"])
        self.assertEqual(response["data"]["estado"], "actualizando")
        self.assertFalse(response["data"]["puertos"]["0/9/3"]["ok"])
        self.assertIsNone(response["data"]["puertos"]["0/9/3"]["casos"])

    def test_batch_route_groups_duplicate_olt_and_keeps_pending_null(self):
        class FakeWorker:
            def __init__(self):
                self.calls = []

            def submit(self, olt, ports):
                self.calls.append((olt, ports))
                return {
                    "olt": olt,
                    "estado": "actualizando",
                    "job_id": "job-1",
                    "generacion": 1,
                    "revision": 1,
                    "consultado_en": None,
                    "puertos": {port: {"estado": "actualizando", "casos": None} for port in ports},
                }

        fake = FakeWorker()
        payload = SolicitudLote(solicitudes=[
            {"olt": OLT.lower(), "puertos": ["00/09/03"]},
            {"olt": OLT, "puertos": ["0/9/3", "0/9/4"]},
        ])
        with patch.object(worker_module, "get_worker", return_value=fake):
            response = casos_abiertos_lote(payload)
        self.assertEqual(fake.calls, [(OLT, ["0/9/3", "0/9/4"])])
        self.assertIsNone(response["data"]["resultados"][0]["puertos"]["0/9/3"]["casos"])

    def test_zero_timeout_aliases_are_preserved(self):
        import os

        with patch.dict(os.environ, {
            "ORACLE_HELIX_QUERY_BUDGET_SECONDS": "0",
            "ORACLE_HELIX_CALL_TIMEOUT_MS": "0",
        }):
            config = Settings(_env_file=None)
        self.assertEqual(config.oracle_helix_query_budget_seconds, 0)
        self.assertEqual(config.oracle_helix_call_timeout_ms, 0)
        legacy = Settings(_env_file=None, ORACLE_HELIX_BUDGET_SECONDS=0)
        self.assertEqual(legacy.oracle_helix_query_budget_seconds, 0)

    def test_disabled_deadline_sets_oracle_timeout_to_zero(self):
        class Connection:
            call_timeout = 123

        captured = []
        with (
            patch.object(settings, "oracle_helix_call_timeout_ms", 0),
            patch.object(settings, "oracle_helix_query_budget_seconds", 0),
            patch.object(service, "_result", side_effect=lambda _olt, deadline, _register: (captured.append(deadline) or {}, "2026-10-08T16:20:00+00:00")),
        ):
            service.consultar_olt(OLT, lambda _cancel: None)
            service._deadline_check(None, Connection)
        self.assertEqual(captured, [None])
        self.assertEqual(Connection.call_timeout, 0)

    def test_query_streams_and_keeps_open_children_of_closed_parent(self):
        class Cursor:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

            def execute(self, sql, _binds):
                query = " ".join(sql.upper().split())

                if "AST_BASEELEMENT" in query:
                    self.rows = [("CI_TEST_OLT",)]

                elif "HPD_ASSOCIATIONS" in query:
                    self.rows = [
                        ("CI_TEST_OLT", "INC1"),
                        ("CI_TEST_OLT", "INC2"),
                    ]

                elif "HPD_HELP_DESK" in query:
                    self.rows = [
                        (
                            "INC1",
                            5,
                            f"{OLT},FRAME=0 SLOT=9 PORT=3",
                            "",
                            "",
                        ),
                        (
                            "INC2",
                            2,
                            f"{OLT},FRAME=0 SLOT=9 PORT=3",
                            "",
                            "",
                        ),
                    ]

                elif "WOI_WORKORDER" in query:
                    self.rows = [
                        ("WO1", "INC1", 4, "Generic", "", ""),
                        ("WO2", "INC1", 8, "Generic", "", ""),
                    ]

                elif "TMS_TASK" in query and "ROOTREQUESTNAME = :INC" in query:
                    inc = _binds["inc"]

                    self.rows = [
                        ("TAS1", "INC1", "HPD:Help Desk", 2000, "Generic"),
                        ("TAS2", "INC1", "HPD:Help Desk", 6000, "Generic"),
                        (
                            "TAS4",
                            "INC1",
                            "HPD:Help Desk",
                            2000,
                            f"{OLT},FRAME=0 SLOT=9 PORT=4",
                        ),
                    ] if inc == "INC1" else []

                elif "TMS_TASK" in query and "ROOTREQUESTNAME = :WO" in query:
                    wo = _binds["wo"]

                    self.rows = [
                        ("TAS3", "WO2", "WOI:WorkOrder", 4000, "Generic"),
                        ("TAS5", "WO2", "WOI:WorkOrder", 6000, "Generic"),
                    ] if wo == "WO2" else []

                else:
                    raise AssertionError(query)

            def fetchmany(self, size):
                rows, self.rows = self.rows[:size], self.rows[size:]
                return rows

        class Connection:
            call_timeout = None
            closed = False

            def cursor(self):
                return Cursor()

            def close(self):
                self.closed = True

            def cancel(self):
                return None

        connection = Connection()

        class Oracle:
            @staticmethod
            def makedsn(*_args, **_kwargs):
                return "mock-dsn"

            @staticmethod
            def connect(**_kwargs):
                return connection

        cancel_registration = []
        with (
            patch.object(service, "oracledb", Oracle),
            patch.object(settings, "oracle_helix_host", "mock"),
            patch.object(settings, "oracle_helix_service_name", "mock-service"),
            patch.object(settings, "oracle_helix_user", "mock-user"),
            patch.object(settings, "oracle_helix_password", "mock-secret"),
            patch.object(settings, "oracle_helix_query_budget_seconds", 0),
            patch.object(settings, "oracle_helix_call_timeout_ms", 0),
        ):
            result, _consulted_at = service._result(OLT, None, lambda cancel: cancel_registration.append(cancel))
        numbers = [
            (item["tipo"], item["numero"])
            for item in result["0/9/3"]
        ]

        self.assertEqual(
            numbers,
            [
                ("INC", "INC2"),
                ("WO", "WO1"),
                ("TAS", "TAS1"),
                ("TAS", "TAS3"),
            ],
        )

        self.assertNotIn(
            "TAS4",
            [item["numero"] for item in result["0/9/3"]],
        )

        self.assertEqual(
            [
                (item["tipo"], item["numero"])
                for item in result["0/9/4"]
            ],
            [("TAS", "TAS4")],
        )
        self.assertTrue(connection.closed)
        self.assertEqual(connection.call_timeout, 0)
        self.assertIsNone(cancel_registration[-1])

    def test_all_required_candidate_searches_complete_before_empty_result(self):
        class Cursor:
            def __enter__(self): return self
            def __exit__(self, *_args): return None
            def execute(self, _sql, _binds): self.rows = []
            def fetchmany(self, _size): return []

        class Connection:
            call_timeout = None
            def cursor(self): return Cursor()
            def close(self): self.closed = True
            def cancel(self): return None

        connection = Connection()

        class Oracle:
            @staticmethod
            def makedsn(*_args, **_kwargs): return "mock-dsn"
            @staticmethod
            def connect(**_kwargs): return connection

        with (
            patch.object(service, "oracledb", Oracle),
            patch.object(settings, "oracle_helix_host", "mock"),
            patch.object(settings, "oracle_helix_service_name", "mock-service"),
            patch.object(settings, "oracle_helix_user", "mock-user"),
            patch.object(settings, "oracle_helix_password", "mock-secret"),
        ):
            result, consulted_at = service._result(OLT, None)
        self.assertEqual(result, {})
        self.assertTrue(consulted_at)
        self.assertTrue(connection.closed)


if __name__ == "__main__":
    unittest.main()

class EquipoScopeIssue4Tests(unittest.TestCase):
    def test_exact_olt_match_not_prefix(self):
        self.assertEqual(service._scope_equipo(OLT, [f"Equipo: {OLT}"]), {"__equipo__"})
        self.assertEqual(service._scope_equipo(OLT, [f"Equipo: {OLT}-OTRO"]), set())
        self.assertEqual(service._scope_equipo(OLT, ["Ningún equipo relacionado"]), set())

    def test_worker_separates_scope_and_reuses_same_equipment_cache(self):
        calls = []
        def ports(olt, cancel):
            calls.append(("puertos", olt))
            return {"0/9/3": [{"tipo": "INC", "numero": "INC1"}]}, "today"
        def equipment(olt, cancel):
            calls.append(("equipo", olt))
            return {"__equipo__": [{"tipo": "TAS", "numero": "TAS1"}]}, "today"
        worker = HelixWorker(ports, query_equipo=equipment)
        worker.start()
        try:
            worker.submit(OLT, ["0/9/3"])
            worker.submit(OLT, [], alcance="equipo")
            self.assertTrue(esperar(lambda: worker.read(OLT, [], alcance="equipo")["estado"] == "listo"))
            self.assertTrue(esperar(lambda: worker.read(OLT, ["0/9/3"])["estado"] == "listo"))
            self.assertEqual(worker.read(OLT, [], alcance="equipo")["casos"][0]["numero"], "TAS1")
            self.assertEqual(worker.read(OLT, ["0/9/3"])["puertos"]["0/9/3"]["casos"][0]["numero"], "INC1")
            worker.submit(OLT, [], alcance="equipo")
            self.assertEqual(calls.count(("equipo", OLT)), 1)
        finally:
            worker.stop()

    def test_route_equipment_and_invalid_scope(self):
        from fastapi import HTTPException
        class FakeWorker:
            def submit(self, olt, ports, alcance="puertos"):
                return {"olt": olt, "alcance": alcance, "estado": "listo", "casos": [], "consultado_en": "today"}
        with patch.object(worker_module, "get_worker", return_value=FakeWorker()):
            result = casos_abiertos(OLT, None, "equipo")
            self.assertEqual(result["data"]["alcance"], "equipo")
            self.assertEqual(result["data"]["casos"], [])
            with self.assertRaises(HTTPException) as ex:
                casos_abiertos(OLT, None, "cualquier_cosa")
            self.assertEqual(ex.exception.status_code, 422)
            with self.assertRaises(HTTPException):
                casos_abiertos(OLT, "0/9/3", "equipo")

    def test_equipment_query_retains_open_task_with_closed_parent(self):
        ci = "REGIUDJBJH36RAT0TEST"

        class Cursor:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

            def execute(self, sql, binds):
                q = " ".join(sql.upper().split())

                if "AST_BASEELEMENT" in q:
                    self.rows = [(ci,)]

                elif "HPD_ASSOCIATIONS" in q:
                    self.rows = [
                        (ci, "INC0001"),
                        (ci, "INC0002"),
                    ]

                elif "HPD_HELP_DESK" in q:
                    self.rows = [
                        ("INC0001", 5, ".", "", OLT),
                        ("INC0002", 2, ".", f"Troncal afectada {OLT}", ""),
    ]

                elif "WOI_WORKORDER" in q:
                    self.rows = [
                        ("WO0001", "INC0001", 8),  # Closed
                        ("WO0002", "INC0002", 0),  # Assigned
                    ]

                elif "TMS_TASK" in q and "'HPD:HELP DESK'" in q:
                    self.rows = [
                        ("TAS0001", "INC0001", 2000),  # Assigned
                    ]

                elif "TMS_TASK" in q and "'WOI:WORKORDER'" in q:
                    self.rows = [
                        ("TAS0002", "WO0002", 4000),  # Work In Progress
                    ]

                else:
                    raise AssertionError(q)

            def fetchmany(self, n):
                batch, self.rows = self.rows[:n], self.rows[n:]
                return batch

        class Conn:
            call_timeout = 0

            def cursor(self):
                return Cursor()

            def close(self):
                pass

            def cancel(self):
                pass

        class Oracle:
            @staticmethod
            def makedsn(*args, **kwargs):
                return "fake"

            @staticmethod
            def connect(**kwargs):
                return Conn()

        with (
            patch.object(service, "oracledb", Oracle),
            patch.object(settings, "oracle_helix_host", "fake"),
            patch.object(settings, "oracle_helix_service_name", "fake"),
            patch.object(settings, "oracle_helix_user", "fake"),
            patch.object(settings, "oracle_helix_password", "fake"),
        ):
            result, _ = service._result(
                OLT,
                None,
                alcance="equipo",
            )

        encontrados = [
            (item["tipo"], item["numero"])
            for item in result["__equipo__"]
        ]

        self.assertEqual(
            encontrados,
            [
                ("INC", "INC0002"),
                ("WO", "WO0002"),
                ("TAS", "TAS0001"),
                ("TAS", "TAS0002"),
            ],
        )