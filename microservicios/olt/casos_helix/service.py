
"""Consulta de casos Helix abiertos asociados a OLT y puertos."""

from __future__ import annotations

import logging
import os
import re
import threading
import time
from collections import defaultdict
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Iterator

from microservicios.config import settings

try:
    import oracledb
except ImportError:
    oracledb = None

logger = logging.getLogger(__name__)

INCIDENT_STATES = {
    0: "New", 1: "Assigned", 2: "In Progress", 3: "Pending",
    4: "Resolved", 5: "Closed", 6: "Cancelled",
}
WO_STATES = {
    0: "Assigned", 1: "Pending", 2: "Waiting Approval", 3: "Planning",
    4: "In Progress", 5: "Completed", 6: "Rejected", 7: "Cancelled",
    8: "Closed",
}
TASK_STATES = {
    1000: "Staged", 2000: "Assigned", 3000: "Pending",
    4000: "Work In Progress", 5000: "Waiting",
    6000: "Closed", 7000: "Bypassed", 8000: "Cancelled",
}

OPEN_INC = frozenset({0, 1, 2, 3})
OPEN_WO = frozenset({0, 1, 2, 3, 4})
OPEN_TASK = frozenset({1000, 2000, 3000, 4000, 5000})
MAX_RELATIONS = 5000
MAX_CASES = 3000

_pool = None
_pool_lock = threading.Lock()
_query_metrics = ContextVar("helix_query_metrics", default=None)


# ============================================================
# CONEXIÓN Y NORMALIZACIÓN
# ============================================================

def _get_pool(dsn):
    global _pool
    with _pool_lock:
        if _pool is None:
            _pool = oracledb.create_pool(
                user=settings.oracle_helix_user,
                password=settings.oracle_helix_password,
                dsn=dsn, min=0, max=1, increment=1,
                getmode=oracledb.POOL_GETMODE_TIMEDWAIT,
                wait_timeout=8000, tcp_connect_timeout=8,
                ping_interval=0, stmtcachesize=20,
            )
        return _pool


def close_oracle_pool():
    global _pool
    with _pool_lock:
        pool, _pool = _pool, None
    if pool is not None:
        try:
            pool.close(force=True)
        except Exception:
            logger.warning("[HELIX] No se pudo cerrar el pool")


class HelixQueryError(RuntimeError):
    """Error al consultar Oracle Helix."""


def normalizar_olt(value: str) -> str:
    olt = value.strip().upper()
    if len(olt) > 120 or not re.fullmatch(r"[A-Z0-9._-]+", olt):
        raise ValueError("El nombre de OLT no es válido")
    return olt


def normalizar_puerto(value: str) -> str:
    text = value.strip()
    match = re.fullmatch(
        r"\s*(\d{1,3})\s*/\s*(\d{1,3})\s*/\s*(\d{1,3})\s*", text
    )
    parts = match.groups() if match else None

    if parts is None:
        frame = re.search(r"\bFRAME\s*=\s*(\d+)\b", text, re.I)
        slot = re.search(r"(?<![A-Z0-9_])SLOT\s*=\s*(\d+)\b", text, re.I)
        port = re.search(r"\bPORT\s*=\s*(\d+)\b", text, re.I)
        if frame and slot and port:
            parts = (frame.group(1), slot.group(1), port.group(1))

    if parts is None:
        raise ValueError("Puerto inválido; se esperaba frame/slot/puerto")
    return "/".join(str(int(part)) for part in parts)


def normalizar_puertos(value: str | Iterable[str]) -> list[str]:
    raw = value.split(",") if isinstance(value, str) else list(value)
    ports = []
    for item in raw:
        port = normalizar_puerto(str(item))
        if port not in ports:
            ports.append(port)
    if not ports:
        raise ValueError("Indique al menos un puerto válido")
    if len(ports) > 100:
        raise ValueError("Se permiten hasta 100 puertos únicos por petición")
    return ports


def _read(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "read"):
        value = value.read()
    return str(value or "")


def _status(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return -1


# ============================================================
# ASOCIACIÓN EXACTA OLT / PUERTO
# ============================================================

def _has_explicit_location(fields: Iterable[Any]) -> bool:
    patterns = (
        r"\bFRAME\s*=\s*\d+\b.*?"
        r"(?<![A-Z0-9_])SLOT\s*=\s*\d+\b.*?\bPORT\s*=\s*\d+\b",
        r"(?<!\d)\d{1,3}\s*/\s*\d{1,3}\s*/\s*\d{1,3}(?!\d)",
        r"(?<![A-Z0-9_.-])[A-Z0-9][A-Z0-9_.-]{4,}"
        r"(?=\s*,?\s*FRAME\s*=)",
    )
    return any(
        re.search(pattern, _read(field), re.I)
        for field in fields for pattern in patterns
    )


def _ports_for_olt(text: str, olt: str) -> set[str]:
    upper = text.upper()
    pattern = re.compile(
        r"(?<![A-Z0-9_.-])" + re.escape(olt) + r"(?![A-Z0-9_.-])",
        re.I,
    )
    matches = list(pattern.finditer(upper))
    markers = list(re.finditer(
        r"(?<![A-Z0-9_.-])[A-Z0-9][A-Z0-9_.-]{2,}"
        r"(?=\s*,\s*FRAME\s*=)", upper
    ))

    structured = re.compile(
        r"\bFRAME\s*=\s*(\d+)\b\s+SLOT\s*=\s*(\d+)\b"
        r"(?:\s+SUBSLOT\s*=\s*\d+\b)?\s+PORT\s*=\s*(\d+)\b",
        re.I,
    )
    slash = re.compile(
        r"(?<!\d)(\d{1,3})\s*/\s*(\d{1,3})\s*/\s*(\d{1,3})(?!\d)"
    )
    found = set()

    for index, match in enumerate(matches):
        next_target = (
            matches[index + 1].start()
            if index + 1 < len(matches) else len(text)
        )
        next_equipment = next(
            (marker.start() for marker in markers
             if marker.start() > match.start()), len(text)
        )
        segment = text[match.end():min(next_target, next_equipment)]

        for expression in (structured, slash):
            for item in expression.finditer(segment):
                found.add("/".join(str(int(n)) for n in item.groups()))
    return found


def _scope(olt: str, fields: Iterable[Any]) -> set[str]:
    result = set()
    for field in fields:
        result.update(_ports_for_olt(_read(field), olt))
    return result


def _scope_equipo(olt: str, fields: Iterable[Any]) -> set[str]:
    exact = re.compile(
        r"(?<![A-Z0-9_.-])" + re.escape(olt) + r"(?![A-Z0-9_.-])",
        re.I,
    )
    return {"__equipo__"} if any(
        exact.search(_read(field)) for field in fields
    ) else set()


# ============================================================
# CONSULTAS ORACLE Y CONTROL DE TIEMPOS
# ============================================================

def _deadline_check(
    deadline: float | None, connection: Any | None = None
) -> None:
    remaining = deadline - time.monotonic() if deadline is not None else None

    if connection is not None:
        limits = []
        if settings.oracle_helix_call_timeout_ms > 0:
            limits.append(settings.oracle_helix_call_timeout_ms)
        if remaining is not None:
            if remaining <= 0:
                raise HelixQueryError("La consulta Helix superó el tiempo disponible")
            limits.append(max(1, int(remaining * 1000)))
        connection.call_timeout = min(limits) if limits else 0

    if deadline is not None and time.monotonic() >= deadline:
        raise HelixQueryError("La consulta Helix superó el tiempo disponible")


def _fetch(
    cursor: Any, sql: str, binds: dict[str, Any],
    deadline: float | None, connection: Any,
    relation_meter: list[int],
) -> Iterator[tuple[Any, ...]]:
    started, rows = time.monotonic(), 0
    match = re.search(r"\bFROM\s+ARADMIN\.([A-Z0-9_]+)", sql, re.I)
    stage = match.group(1).upper() if match else "OTRA"

    try:
        _deadline_check(deadline, connection)
        cursor.execute(sql, binds)

        while True:
            _deadline_check(deadline, connection)
            batch = cursor.fetchmany(50)
            if not batch:
                break
            for row in batch:
                relation_meter[0] += 1
                rows += 1
                if relation_meter[0] > MAX_RELATIONS:
                    raise HelixQueryError(
                        "La consulta excedió el límite de relaciones; resultado incompleto"
                    )
                yield tuple(
                    _read(value) if hasattr(value, "read") else value
                    for value in row
                )
    finally:
        metrics = _query_metrics.get()
        if metrics is not None:
            bucket = metrics.setdefault(stage, [0.0, 0, 0])
            bucket[0] += time.monotonic() - started
            bucket[1] += 1
            bucket[2] += rows


def _in_query(
    cursor: Any, sql: str, ids: Iterable[str],
    deadline: float | None, connection: Any,
    relation_meter: list[int],
) -> Iterator[tuple[Any, ...]]:
    values = sorted({
        str(value).strip() for value in ids
        if str(value or "").strip()
    })
    for start in range(0, len(values), 200):
        group = values[start:start + 200]
        names = [f"id{i}" for i in range(len(group))]
        binds = dict(zip(names, group))
        query = sql.format(
            bind_list=", ".join(f":{name}" for name in names)
        )
        yield from _fetch(
            cursor, query, binds, deadline, connection, relation_meter
        )


# ============================================================
# CASOS POR OLT COMPLETA
# ============================================================

def _consultar_equipo_asociaciones(
    cursor: Any, olt: str, deadline: float | None,
    connection: Any, meter: list[int],
) -> dict[str, list[dict[str, Any]]]:
    results = []

    ci_ids = {
        _read(row[0]).strip()
        for row in _fetch(
            cursor,
            "SELECT RECONCILIATION_IDENTITY FROM ARADMIN.AST_BASEELEMENT "
            "WHERE NAME = :olt",
            {"olt": olt}, deadline, connection, meter,
        ) if _read(row[0]).strip()
    }
    if not ci_ids:
        return {"__equipo__": []}

    inc_ids = set()
    for _, inc in _in_query(
        cursor,
        """SELECT REQUEST_ID01, REQUEST_ID02
           FROM ARADMIN.HPD_ASSOCIATIONS
           WHERE REQUEST_ID01 IN ({bind_list})
             AND FORM_NAME01 = 'AST:ComputerSystem'
             AND FORM_NAME02 = 'HPD:Help Desk'""",
        ci_ids, deadline, connection, meter,
    ):
        number = _read(inc).strip().upper()
        if re.fullmatch(r"INC\d+", number):
            inc_ids.add(number)

    if not inc_ids:
        return {"__equipo__": []}

    patron = re.compile(
        r"(?<![A-Z0-9_.-])" + re.escape(olt) + r"(?![A-Z0-9_.-])", re.I
    )
    inc_confirmados = set()

    for number, status, short, description, impacto, regional, aliado, departamento, ciudad in _in_query(
        cursor,
        """SELECT INCIDENT_NUMBER, STATUS, SHORT_DESCRIPTION,
                DESCRIPTION, DESCRIPCION_DE_IMPACTO,
                REGIONAL, ALIADO,
                DEPARTAMENTO__ESTADO_PROVINCIA, CIUDAD
        FROM ARADMIN.HPD_HELP_DESK
        WHERE INCIDENT_NUMBER IN ({bind_list})""",
        inc_ids, deadline, connection, meter,
    ):
        number, status = _read(number).strip().upper(), _status(status)
        if not any(patron.search(_read(v)) for v in (short, description, impacto)):
            logger.info("INC %s excluido de OLT %s: sin relacion explicita", number, olt)
            continue

        inc_confirmados.add(number)

        if status in OPEN_INC:
            results.append({
                "tipo": "INC",
                "numero": number,
                "estado_codigo": status,
                "estado": INCIDENT_STATES[status],
                "regional": _read(regional).strip(),
                "aliado": _read(aliado).strip(),
                "departamento": _read(departamento).strip(),
                "ciudad": _read(ciudad).strip(),
            })

    wo_ids = set()
    for number, _, status in _in_query(
        cursor,
        """SELECT WORK_ORDER_ID, ROOT_INCIDENT, STATUS
           FROM ARADMIN.WOI_WORKORDER
           WHERE ROOT_INCIDENT IN ({bind_list})""",
        inc_confirmados, deadline, connection, meter,
    ):
        number, status = _read(number).strip().upper(), _status(status)
        if number:
            wo_ids.add(number)
        if number and status in OPEN_WO:
            results.append({
                "tipo": "WO", "numero": number,
                "estado_codigo": status, "estado": WO_STATES[status],
            })

    # TAS asociadas con INC.
    for inc in sorted(inc_confirmados):
        for number, _, status, grupo in _fetch(
            cursor,
            """SELECT TASK_ID, ROOTREQUESTNAME, STATUS, ASSIGNEE_GROUP
               FROM ARADMIN.TMS_TASK
               WHERE ROOTREQUESTFORMNAME = 'HPD:Help Desk'
                 AND ROOTREQUESTNAME = :inc""",
            {"inc": inc}, deadline, connection, meter,
        ):
            number, status = _read(number).strip().upper(), _status(status)
            if number and status in OPEN_TASK:
                results.append({
                    "tipo": "TAS", "numero": number,
                    "estado_codigo": status, "estado": TASK_STATES[status],
                    "grupo_soporte": _read(grupo).strip(),
                })

    # TAS asociadas con WO.
    for number, _, status, grupo in _in_query(
        cursor,
        """SELECT TASK_ID, ROOTREQUESTNAME, STATUS, ASSIGNEE_GROUP
           FROM ARADMIN.TMS_TASK
           WHERE ROOTREQUESTFORMNAME = 'WOI:WorkOrder'
             AND ROOTREQUESTNAME IN ({bind_list})""",
        wo_ids, deadline, connection, meter,
    ):
        number, status = _read(number).strip().upper(), _status(status)
        if number and status in OPEN_TASK:
            results.append({
                "tipo": "TAS", "numero": number,
                "estado_codigo": status, "estado": TASK_STATES[status],
                "grupo_soporte": _read(grupo).strip(),
            })

    unique = {(c["tipo"], c["numero"]): c for c in results}
    if len(unique) > MAX_CASES:
        raise HelixQueryError("La consulta excedió el límite de casos; resultado incompleto")

    order = {"INC": 0, "WO": 1, "TAS": 2}
    return {
        "__equipo__": sorted(
            unique.values(), key=lambda c: (order[c["tipo"]], c["numero"])
        )
    }


# ============================================================
# CASOS POR PUERTO
# ============================================================

def _consultar_puertos_asociaciones(
    cursor: Any, olt: str, deadline: float | None,
    connection: Any, meter: list[int],
) -> dict[str, list[dict[str, Any]]]:
    results = defaultdict(list)

    ci_ids = {
        _read(row[0]).strip()
        for row in _fetch(
            cursor,
            "SELECT RECONCILIATION_IDENTITY FROM ARADMIN.AST_BASEELEMENT "
            "WHERE NAME = :olt",
            {"olt": olt}, deadline, connection, meter,
        ) if _read(row[0]).strip()
    }
    if not ci_ids:
        return {}

    inc_ids = set()
    for _, inc in _in_query(
        cursor,
        """SELECT REQUEST_ID01, REQUEST_ID02
           FROM ARADMIN.HPD_ASSOCIATIONS
           WHERE REQUEST_ID01 IN ({bind_list})
             AND FORM_NAME01 = 'AST:ComputerSystem'
             AND FORM_NAME02 = 'HPD:Help Desk'""",
        ci_ids, deadline, connection, meter,
    ):
        inc = _read(inc).strip().upper()
        if re.fullmatch(r"INC\d+", inc):
            inc_ids.add(inc)

    if not inc_ids:
        return {}

    inc_records = {}
    inc_ubicaciones = {}
    for number, status, short, description, impacto, regional, aliado, departamento, ciudad in _in_query(
        cursor,
        """SELECT INCIDENT_NUMBER, STATUS, SHORT_DESCRIPTION,
                DESCRIPTION, DESCRIPCION_DE_IMPACTO,
                REGIONAL, ALIADO,
                DEPARTAMENTO__ESTADO_PROVINCIA, CIUDAD
        FROM ARADMIN.HPD_HELP_DESK
        WHERE INCIDENT_NUMBER IN ({bind_list})""",
        inc_ids, deadline, connection, meter,
    ):
        number = _read(number).strip().upper()
        scope = _scope(olt, (short, description, impacto))
        if number and scope:
            inc_records[number] = (_status(status), scope)

            inc_ubicaciones[number] = {
                "regional": _read(regional).strip(),
                "aliado": _read(aliado).strip(),
                "departamento": _read(departamento).strip(),
                "ciudad": _read(ciudad).strip(),
            }

    if not inc_records:
        return {}

    wo_records = {}
    for number, parent, status, summary, node, description in _in_query(
        cursor,
        """SELECT WORK_ORDER_ID, ROOT_INCIDENT, STATUS,
                  SUMMARY, NODE, DETAILED_DESCRIPTION
           FROM ARADMIN.WOI_WORKORDER
           WHERE ROOT_INCIDENT IN ({bind_list})""",
        inc_records.keys(), deadline, connection, meter,
    ):
        number, parent = _read(number).strip().upper(), _read(parent).strip().upper()
        fields = (summary, node, description)
        explicit = _scope(olt, fields)
        inherited = inc_records.get(parent, (0, set()))[1]
        scope = explicit if explicit else (
            set() if _has_explicit_location(fields) else inherited
        )
        if number and scope:
            wo_records[number] = (parent, _status(status), scope)

    tas_records = {}

    # TAS asociadas con INC.
    for inc in sorted(inc_records):
        started = time.monotonic()
        logger.warning("[HELIX TAS] Consultando OLT=%s INC=%s", olt, inc)

        for number, parent, form, status, summary, grupo in _fetch(
            cursor,
            """SELECT TASK_ID, ROOTREQUESTNAME, ROOTREQUESTFORMNAME,
                      STATUS, SUMMARY, ASSIGNEE_GROUP
               FROM ARADMIN.TMS_TASK
               WHERE ROOTREQUESTNAME = :inc""",
            {"inc": inc}, deadline, connection, meter,
        ):
            if _read(form).strip() != "HPD:Help Desk":
                continue

            number, parent = _read(number).strip().upper(), _read(parent).strip().upper()
            fields = (summary,)
            explicit = _scope(olt, fields)
            inherited = inc_records.get(parent, (0, set()))[1]
            scope = explicit if explicit else (
                set() if _has_explicit_location(fields) else inherited
            )

            if number and scope:
                tas_records[number] = (_status(status), scope, _read(grupo).strip())
                logger.warning(
                    "[HELIX TAS] Finalizado OLT=%s INC=%s Tiempo=%.2fs",
                    olt, inc, time.monotonic() - started,
                )

    logger.warning(
        "[HELIX WO] OLT=%s Total WO relacionadas=%s IDs=%s",
        olt, len(wo_records), sorted(wo_records),
    )

    # TAS asociadas con WO: consulta dentro del ciclo.
    for wo in sorted(wo_records):
        logger.warning("[HELIX TAS-WO] Consultando OLT=%s WO=%s", olt, wo)

        for number, parent, form, status, summary, grupo in _fetch(
            cursor,
            """SELECT TASK_ID, ROOTREQUESTNAME, ROOTREQUESTFORMNAME,
                      STATUS, SUMMARY, ASSIGNEE_GROUP
               FROM ARADMIN.TMS_TASK
               WHERE ROOTREQUESTNAME = :wo""",
            {"wo": wo}, deadline, connection, meter,
        ):
            if _read(form).strip() != "WOI:WorkOrder":
                continue

            number, parent = _read(number).strip().upper(), _read(parent).strip().upper()
            fields = (summary,)
            explicit = _scope(olt, fields)
            inherited = wo_records.get(parent, ("", 0, set()))[2]
            scope = explicit if explicit else (
                set() if _has_explicit_location(fields) else inherited
            )

            if number and scope:
                tas_records[number] = (_status(status), scope, _read(grupo).strip())

    case_count = 0

    def add(kind, number, status, scope, states, allowed, grupo=""):
        nonlocal case_count
        if status not in allowed:
            return

        for port in scope:
            case_count += 1
            if case_count > MAX_CASES:
                raise HelixQueryError(
                    "La consulta excedió el límite de casos; resultado incompleto"
                )
            caso = {
                "tipo": kind, "numero": number,
                "estado_codigo": status, "estado": states[status],
            }
            if kind == "TAS":
                caso["grupo_soporte"] = grupo
            results[port].append(caso)

    for number, (status, scope) in inc_records.items():
        add("INC", number, status, scope, INCIDENT_STATES, OPEN_INC)

        if status in OPEN_INC:
            for port in scope:
                for caso in results[port]:
                    if caso["tipo"] == "INC" and caso["numero"] == number:
                        caso.update(inc_ubicaciones[number])

    for number, (_, status, scope) in wo_records.items():
        add("WO", number, status, scope, WO_STATES, OPEN_WO)

    for number, (status, scope, grupo) in tas_records.items():
        add("TAS", number, status, scope, TASK_STATES, OPEN_TASK, grupo)

    order = {"INC": 0, "WO": 1, "TAS": 2}
    return {
        port: sorted(
            {(c["tipo"], c["numero"]): c for c in cases}.values(),
            key=lambda c: (order[c["tipo"]], c["numero"]),
        )
        for port, cases in results.items()
    }


# ============================================================
# EJECUCIÓN Y FUNCIONES PÚBLICAS
# ============================================================

def _result_once(
    olt: str,
    deadline: float | None,
    register_cancel: Callable[[Callable[[], None] | None], None] | None = None,
    alcance: str = "puertos",
) -> tuple[dict[str, list[dict[str, Any]]], str]:
    if alcance not in {"puertos", "equipo"}:
        raise ValueError("Alcance de consulta no válido")

    required = (
        settings.oracle_helix_host, settings.oracle_helix_service_name,
        settings.oracle_helix_user, settings.oracle_helix_password,
    )
    if not all(required):
        raise HelixQueryError("Oracle Helix no está configurado completamente")
    if oracledb is None:
        raise HelixQueryError("Falta la dependencia python-oracledb")

    dsn = oracledb.makedsn(
        settings.oracle_helix_host, settings.oracle_helix_port,
        service_name=settings.oracle_helix_service_name,
    )

    connection, pool, failed = None, None, True
    started = time.monotonic()
    metrics = {}
    token = _query_metrics.set(metrics)
    connection_seconds = 0.0

    try:
        _deadline_check(deadline)
        pool = _get_pool(dsn)
        connection = pool.acquire()
        connection_seconds = time.monotonic() - started

        if register_cancel:
            register_cancel(connection.cancel)

        _deadline_check(deadline, connection)

        with connection.cursor() as cursor:
            cursor.arraysize = 50
            cursor.prefetchrows = 50
            meter = [0]

            if alcance == "equipo":
                result = _consultar_equipo_asociaciones(
                    cursor, olt, deadline, connection, meter
                )
            else:
                result = _consultar_puertos_asociaciones(
                    cursor, olt, deadline, connection, meter
                )

        failed = False
        return result, datetime.now(timezone.utc).isoformat(timespec="seconds")

    except HelixQueryError:
        raise
    except Exception as exc:
        logger.exception("Falló la consulta completa de casos Helix")
        raise HelixQueryError(
            "Oracle Helix no está disponible o la consulta falló"
        ) from exc
    finally:
        if register_cancel:
            register_cancel(None)

        if connection is not None:
            try:
                if failed:
                    pool.drop(connection)
                else:
                    connection.call_timeout = 0
                    pool.release(connection)
            except Exception:
                try:
                    pool.drop(connection)
                except Exception:
                    pass

        _query_metrics.reset(token)
        if os.environ.get("HELIX_METRICAS", "1") != "0":
            detail = "; ".join(
                f"{name}={v[0]:.2f}s/{v[1]} consultas/{v[2]} filas"
                for name, v in sorted(metrics.items())
            )
            logger.warning(
                "[HELIX TIEMPOS] OLT=%s alcance=%s total=%.2fs "
                "conexion=%.2fs ok=%s %s",
                olt, alcance, time.monotonic() - started,
                connection_seconds, not failed, detail,
            )


# RKP_RECUPERACION_V1: reintento solo para desconexiones de lecturas.
def _desconexion(exc):
    cause = exc.__cause__ or exc
    detail = cause.args[0] if cause.args else cause
    code = getattr(detail, "full_code", "")
    return bool(getattr(detail, "isrecoverable", False)) or code in {
        "DPY-1001", "DPY-4011", "ORA-03113", "ORA-03114",
        "ORA-03135", "ORA-01012", "ORA-12537", "ORA-12547",
        "ORA-12570", "ORA-12571",
    }


def _result(olt, deadline, register_cancel=None, alcance="puertos"):
    for attempt in range(2):
        try:
            return _result_once(olt, deadline, register_cancel, alcance)
        except HelixQueryError as exc:
            if not _desconexion(exc):
                raise
            # El intento anterior ya devolvió/descartó su conexión en finally.
            close_oracle_pool()
            if attempt or (deadline is not None and time.monotonic() >= deadline):
                raise
            logger.warning("[HELIX RECUPERACION] Desconexión; nuevo pool y un reintento")
    raise HelixQueryError("Oracle Helix no disponible")


def consultar_olt(
    olt: str,
    register_cancel: Callable[[Callable[[], None] | None], None] | None = None,
) -> tuple[dict[str, list[dict[str, Any]]], str]:
    budget = settings.oracle_helix_query_budget_seconds
    deadline = time.monotonic() + budget if budget > 0 else None
    return _result(olt, deadline, register_cancel)


def consultar_olt_equipo(
    olt: str,
    register_cancel: Callable[[Callable[[], None] | None], None] | None = None,
) -> tuple[dict[str, list[dict[str, Any]]], str]:
    budget = settings.oracle_helix_query_budget_seconds
    deadline = time.monotonic() + budget if budget > 0 else None
    return _result(olt, deadline, register_cancel, alcance="equipo")
