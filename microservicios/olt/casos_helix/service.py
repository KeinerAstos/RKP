"""Cruce exacto de casos Helix abiertos por OLT y puerto."""

from __future__ import annotations

import re
import logging
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Iterator

from microservicios.config import settings

logger = logging.getLogger(__name__)

try:
    import oracledb  # type: ignore[import-not-found]
except ImportError:  # La ausencia del driver no debe impedir iniciar la API.
    oracledb = None  # type: ignore[assignment]

INCIDENT_STATES = {
    0: "New", 1: "Assigned", 2: "In Progress", 3: "Pending",
    4: "Resolved", 5: "Closed", 6: "Cancelled",
}
WO_STATES = {
    0: "Assigned", 1: "Pending", 2: "Waiting Approval", 3: "Planning",
    4: "In Progress", 5: "Completed", 6: "Rejected", 7: "Cancelled", 8: "Closed",
}
TASK_STATES = {
    1000: "Staged", 2000: "Assigned", 3000: "Pending", 4000: "Work In Progress",
    5000: "Waiting", 6000: "Closed", 7000: "Bypassed", 8000: "Cancelled",
}
OPEN_INC = frozenset({0, 1, 2, 3})
OPEN_WO = frozenset({0, 1, 2, 3, 4})
OPEN_TASK = frozenset({1000, 2000, 3000, 4000, 5000})
MAX_RELATIONS = 5000
MAX_CASES = 3000

class HelixQueryError(RuntimeError):
    """Fallo en una rama necesaria de la consulta Helix."""


def normalizar_olt(value: str) -> str:
    olt = value.strip().upper()
    if len(olt) > 120 or not re.fullmatch(r"[A-Z0-9._-]+", olt):
        raise ValueError("El nombre de OLT no es válido")
    return olt


def normalizar_puerto(value: str) -> str:
    text = value.strip()
    slash_match = re.fullmatch(r"\s*(\d{1,3})\s*/\s*(\d{1,3})\s*/\s*(\d{1,3})\s*", text)
    parts: tuple[str, str, str] | None = slash_match.groups() if slash_match else None
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
    ports: list[str] = []
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


def _has_explicit_location(fields: Iterable[Any]) -> bool:
    for field in fields:
        text = _read(field)
        if re.search(r"\bFRAME\s*=\s*\d+\b.*?(?<![A-Z0-9_])SLOT\s*=\s*\d+\b.*?\bPORT\s*=\s*\d+\b", text, re.I):
            return True
        if re.search(r"(?<!\d)\d{1,3}\s*/\s*\d{1,3}\s*/\s*\d{1,3}(?!\d)", text):
            return True
        if re.search(r"(?<![A-Z0-9_.-])[A-Z0-9][A-Z0-9_.-]{4,}(?=\s*,?\s*FRAME\s*=)", text, re.I):
            return True
    return False


def _ports_for_olt(text: str, olt: str) -> set[str]:
    """Extract exact port tuples only from segments bearing this exact OLT."""
    upper = text.upper()
    pattern = re.compile(r"(?<![A-Z0-9_.-])" + re.escape(olt) + r"(?![A-Z0-9_.-])", re.I)
    matches = list(pattern.finditer(upper))
    equipment_markers = list(re.finditer(
        r"(?<![A-Z0-9_.-])[A-Z0-9][A-Z0-9_.-]{2,}(?=\s*,\s*FRAME\s*=)",
        upper,
    ))
    found: set[str] = set()
    for index, match in enumerate(matches):
        next_target = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        next_equipment = next((marker.start() for marker in equipment_markers if marker.start() > match.start()), len(text))
        end = min(next_target, next_equipment)
        segment = text[match.end():end]
        structured = re.compile(
            r"\bFRAME\s*=\s*(\d+)\b\s+SLOT\s*=\s*(\d+)\b"
            r"(?:\s+SUBSLOT\s*=\s*\d+\b)?\s+PORT\s*=\s*(\d+)\b",
            re.I,
        )
        for structured_match in structured.finditer(segment):
            found.add("/".join(str(int(value)) for value in structured_match.groups()))
        slash = re.compile(r"(?<!\d)(\d{1,3})\s*/\s*(\d{1,3})\s*/\s*(\d{1,3})(?!\d)")
        for slash_match in slash.finditer(segment):
            found.add("/".join(str(int(value)) for value in slash_match.groups()))
    return found


def _scope(olt: str, fields: Iterable[Any]) -> set[str]:
    result: set[str] = set()
    for field in fields:
        result.update(_ports_for_olt(_read(field), olt))
    return result



def _scope_equipo(olt: str, fields: Iterable[Any]) -> set[str]:
    """Solo asociaciones con el identificador OLT completo, no coincidencias parciales."""
    exact = re.compile(r"(?<![A-Z0-9_.-])" + re.escape(olt) + r"(?![A-Z0-9_.-])", re.I)
    return {"__equipo__"} if any(exact.search(_read(field)) for field in fields) else set()


def _deadline_check(deadline: float | None, connection: Any | None = None) -> None:
    remaining = deadline - time.monotonic() if deadline is not None else None
    if connection is not None:
        limits: list[int] = []
        if settings.oracle_helix_call_timeout_ms > 0:
            limits.append(settings.oracle_helix_call_timeout_ms)
        if remaining is not None:
            if remaining <= 0:
                raise HelixQueryError("La consulta Helix superó el tiempo disponible")
            limits.append(max(1, int(remaining * 1000)))
        call_timeout = min(limits) if limits else 0
        connection.call_timeout = call_timeout
    if deadline is not None and time.monotonic() >= deadline:
        raise HelixQueryError("La consulta Helix superó el tiempo disponible")


def _fetch(
    cursor: Any,
    sql: str,
    binds: dict[str, Any],
    deadline: float | None,
    connection: Any,
    relation_meter: list[int],
) -> Iterator[tuple[Any, ...]]:
    _deadline_check(deadline, connection)
    cursor.execute(sql, binds)
    while True:
        _deadline_check(deadline, connection)
        batch = cursor.fetchmany(50)
        if not batch:
            break
        for row in batch:
            relation_meter[0] += 1
            if relation_meter[0] > MAX_RELATIONS:
                raise HelixQueryError("La consulta excedió el límite de relaciones; resultado incompleto")
            yield tuple(_read(value) if hasattr(value, "read") else value for value in row)


def _in_query(
    cursor: Any,
    sql_prefix: str,
    ids: Iterable[str],
    deadline: float | None,
    connection: Any,
    relation_meter: list[int],
) -> Iterator[tuple[Any, ...]]:
    values = sorted({str(value).strip() for value in ids if str(value or "").strip()})
    rows: list[tuple[Any, ...]] = []
    for start in range(0, len(values), 200):
        group = values[start:start + 200]
        if not group:
            continue
        names = [f"id{i}" for i in range(len(group))]
        binds = dict(zip(names, group))
        sql = sql_prefix.format(bind_list=", ".join(f":{name}" for name in names))
        yield from _fetch(cursor, sql, binds, deadline, connection, relation_meter)




def _consultar_equipo_asociaciones(
    cursor: Any,
    olt: str,
    deadline: float | None,
    connection: Any,
    relation_meter: list[int],
) -> dict[str, list[dict[str, Any]]]:
    """Consulta casos asociados al CI y confirmados para la OLT."""
    results: list[dict[str, Any]] = []

    ci_ids = {
        _read(row[0]).strip()
        for row in _fetch(
            cursor,
            """
            SELECT RECONCILIATION_IDENTITY
            FROM ARADMIN.AST_BASEELEMENT
            WHERE NAME = :olt
            """,
            {"olt": olt},
            deadline,
            connection,
            relation_meter,
        )
        if _read(row[0]).strip()
    }
    if not ci_ids:
        return {"__equipo__": []}

    inc_ids: set[str] = set()
    for _ci, inc in _in_query(
        cursor,
        """
        SELECT REQUEST_ID01, REQUEST_ID02
        FROM ARADMIN.HPD_ASSOCIATIONS
        WHERE REQUEST_ID01 IN ({bind_list})
          AND FORM_NAME01 = 'AST:ComputerSystem'
          AND FORM_NAME02 = 'HPD:Help Desk'
        """,
        ci_ids,
        deadline,
        connection,
        relation_meter,
    ):
        number = _read(inc).strip().upper()
        if re.fullmatch(r"INC\d+", number):
            inc_ids.add(number)

    if not inc_ids:
        return {"__equipo__": []}

    patron_olt = re.compile(
        r"(?<![A-Z0-9_.-])" + re.escape(olt) + r"(?![A-Z0-9_.-])",
        re.IGNORECASE,
    )
    inc_confirmados: set[str] = set()
    for number, status, short, description, impacto in _in_query(
        cursor,
        """
        SELECT INCIDENT_NUMBER, STATUS, SHORT_DESCRIPTION,
               DESCRIPTION, DESCRIPCION_DE_IMPACTO
        FROM ARADMIN.HPD_HELP_DESK
        WHERE INCIDENT_NUMBER IN ({bind_list})
        """,
        inc_ids,
        deadline,
        connection,
        relation_meter,
    ):
        number = _read(number).strip().upper()
        status = _status(status)
        fields = (_read(short), _read(description), _read(impacto))
        if not any(patron_olt.search(value) for value in fields):
            logger.info(
                "INC %s excluido de OLT %s: sin relacion explicita",
                number, olt,
            )
            continue
        inc_confirmados.add(number)
        if status in OPEN_INC:
            results.append({
                "tipo": "INC", "numero": number,
                "estado_codigo": status, "estado": INCIDENT_STATES[status],
            })

    # Conservar INC padres resueltos/cerrados para localizar hijos abiertos.
    wo_ids: set[str] = set()
    for number, _parent, status in _in_query(
        cursor,
        """
        SELECT WORK_ORDER_ID, ROOT_INCIDENT, STATUS
        FROM ARADMIN.WOI_WORKORDER
        WHERE ROOT_INCIDENT IN ({bind_list})
        """,
        inc_confirmados,
        deadline,
        connection,
        relation_meter,
    ):
        number = _read(number).strip().upper()
        status = _status(status)
        if number:
            wo_ids.add(number)
        if number and status in OPEN_WO:
            results.append({
                "tipo": "WO", "numero": number,
                "estado_codigo": status, "estado": WO_STATES[status],
            })

    # Individual por INC: evita timeout observado usando IN en TMS_TASK.
    for inc in sorted(inc_confirmados):
        for number, _parent, status in _fetch(
            cursor,
            """
            SELECT TASK_ID, ROOTREQUESTNAME, STATUS
            FROM ARADMIN.TMS_TASK
            WHERE ROOTREQUESTFORMNAME = 'HPD:Help Desk'
              AND ROOTREQUESTNAME = :inc
            """,
            {"inc": inc},
            deadline,
            connection,
            relation_meter,
        ):
            number = _read(number).strip().upper()
            status = _status(status)
            if number and status in OPEN_TASK:
                results.append({
                    "tipo": "TAS", "numero": number,
                    "estado_codigo": status, "estado": TASK_STATES[status],
                })

    for number, _parent, status in _in_query(
        cursor,
        """
        SELECT TASK_ID, ROOTREQUESTNAME, STATUS
        FROM ARADMIN.TMS_TASK
        WHERE ROOTREQUESTFORMNAME = 'WOI:WorkOrder'
          AND ROOTREQUESTNAME IN ({bind_list})
        """,
        wo_ids,
        deadline,
        connection,
        relation_meter,
    ):
        number = _read(number).strip().upper()
        status = _status(status)
        if number and status in OPEN_TASK:
            results.append({
                "tipo": "TAS", "numero": number,
                "estado_codigo": status, "estado": TASK_STATES[status],
            })

    unique = {(case["tipo"], case["numero"]): case for case in results}
    if len(unique) > MAX_CASES:
        raise HelixQueryError("La consulta excedio el limite de casos; resultado incompleto")
    type_order = {"INC": 0, "WO": 1, "TAS": 2}
    return {
        "__equipo__": sorted(
            unique.values(),
            key=lambda case: (type_order[case["tipo"]], case["numero"]),
        )
    }


def _consultar_puertos_asociaciones(
    cursor: Any,
    olt: str,
    deadline: float | None,
    connection: Any,
    relation_meter: list[int],
) -> dict[str, list[dict[str, Any]]]:
    """Casos abiertos cuya relación con OLT y puerto se puede verificar."""
    results: dict[str, list[dict[str, Any]]] = defaultdict(list)

    ci_ids = {
        _read(row[0]).strip()
        for row in _fetch(
            cursor,
            "SELECT RECONCILIATION_IDENTITY FROM ARADMIN.AST_BASEELEMENT WHERE NAME = :olt",
            {"olt": olt}, deadline, connection, relation_meter,
        )
        if _read(row[0]).strip()
    }
    if not ci_ids:
        return {}

    inc_ids: set[str] = set()
    for _ci, inc in _in_query(
        cursor,
        """
        SELECT REQUEST_ID01, REQUEST_ID02 FROM ARADMIN.HPD_ASSOCIATIONS
        WHERE REQUEST_ID01 IN ({bind_list})
          AND FORM_NAME01 = 'AST:ComputerSystem'
          AND FORM_NAME02 = 'HPD:Help Desk'
        """,
        ci_ids, deadline, connection, relation_meter,
    ):
        inc = _read(inc).strip().upper()
        if re.fullmatch(r"INC\d+", inc):
            inc_ids.add(inc)
    if not inc_ids:
        return {}

    # Los incidentes sin ubicación verificable no se asignan a un puerto.
    inc_records: dict[str, tuple[int, set[str]]] = {}
    for number, status, short, description, impacto in _in_query(
        cursor,
        """
        SELECT INCIDENT_NUMBER, STATUS, SHORT_DESCRIPTION, DESCRIPTION,
               DESCRIPCION_DE_IMPACTO
        FROM ARADMIN.HPD_HELP_DESK
        WHERE INCIDENT_NUMBER IN ({bind_list})
        """,
        inc_ids, deadline, connection, relation_meter,
    ):
        number = _read(number).strip().upper()
        scope = _scope(olt, (short, description, impacto))
        if number and scope:
            inc_records[number] = (_status(status), scope)
    if not inc_records:
        return {}

    wo_records: dict[str, tuple[str, int, set[str]]] = {}
    for number, parent, status, summary, node, description in _in_query(
        cursor,
        """
        SELECT WORK_ORDER_ID, ROOT_INCIDENT, STATUS, SUMMARY, NODE,
               DETAILED_DESCRIPTION
        FROM ARADMIN.WOI_WORKORDER
        WHERE ROOT_INCIDENT IN ({bind_list})
        """,
        inc_records.keys(), deadline, connection, relation_meter,
    ):
        number = _read(number).strip().upper()
        parent = _read(parent).strip().upper()
        fields = (summary, node, description)
        explicit = _scope(olt, fields)
        inherited = inc_records.get(parent, (0, set()))[1]
        scope = explicit if explicit else (set() if _has_explicit_location(fields) else inherited)
        if number and scope:
            wo_records[number] = (parent, _status(status), scope)

    tas_records: dict[str, tuple[int, set[str]]] = {}

    for inc in sorted(inc_records):
        inicio_consulta = time.monotonic()

        logger.warning(
            "[HELIX TAS] Consultando OLT=%s INC=%s",
            olt,
            inc,
        )

        for number, parent, form, status, summary in _fetch(
            cursor,
            """
            SELECT TASK_ID,
                ROOTREQUESTNAME,
                ROOTREQUESTFORMNAME,
                STATUS,
                SUMMARY
            FROM ARADMIN.TMS_TASK
            WHERE ROOTREQUESTNAME = :inc
            """,
            {"inc": inc}, deadline, connection, relation_meter,
        ):
            if _read(form).strip() != "HPD:Help Desk":
                continue
        
            number = _read(number).strip().upper()
            parent = _read(parent).strip().upper()
            fields = (summary,)
            explicit = _scope(olt, fields)
            inherited = inc_records.get(parent, (0, set()))[1]
            scope = explicit if explicit else (set() if _has_explicit_location(fields) else inherited)
            if number and scope:
                tas_records[number] = (_status(status), scope)
                logger.warning(
                "[HELIX TAS] Finalizado OLT=%s INC=%s Tiempo=%.2fs",
                olt,
                inc,
                time.monotonic() - inicio_consulta,
            )
    logger.warning(
        "[HELIX WO] OLT=%s Total WO relacionadas=%s IDs=%s",
        olt,
        len(wo_records),
        sorted(wo_records),
    )

    for wo in sorted(wo_records):
        logger.warning(
            "[HELIX TAS-WO] Consultando OLT=%s WO=%s",
            olt,
            wo,
        )

        for number, parent, form, status, summary in _fetch(
            cursor,
            """
            SELECT TASK_ID,
                   ROOTREQUESTNAME,
                   ROOTREQUESTFORMNAME,
                   STATUS,
                   SUMMARY
            FROM ARADMIN.TMS_TASK
            WHERE ROOTREQUESTNAME = :wo
            """,
            {"wo": wo},
            deadline,
            connection,
            relation_meter,
        ):
            
            if _read(form).strip() != "WOI:WorkOrder":
                continue

            number = _read(number).strip().upper()
            parent = _read(parent).strip().upper()
            fields = (summary,)
            explicit = _scope(olt, fields)
            inherited = wo_records.get(parent, ("", 0, set()))[2]
            scope = explicit if explicit else (set() if _has_explicit_location(fields) else inherited)
            if number and scope:
                tas_records[number] = (_status(status), scope)

    case_count = 0

    def add(kind: str, number: str, status: int, scope: set[str],
            states: dict[int, str], allowed: frozenset[int]) -> None:
        nonlocal case_count
        if status not in allowed:
            return
        for port in scope:
            case_count += 1
            if case_count > MAX_CASES:
                raise HelixQueryError("La consulta excedió el límite de casos; resultado incompleto")
            results[port].append({
                "tipo": kind, "numero": number,
                "estado_codigo": status, "estado": states[status],
            })

    for number, (status, scope) in inc_records.items():
        add("INC", number, status, scope, INCIDENT_STATES, OPEN_INC)
    for number, (_parent, status, scope) in wo_records.items():
        add("WO", number, status, scope, WO_STATES, OPEN_WO)
    for number, (status, scope) in tas_records.items():
        add("TAS", number, status, scope, TASK_STATES, OPEN_TASK)

    type_order = {"INC": 0, "WO": 1, "TAS": 2}
    return {
        port: sorted(
            {(item["tipo"], item["numero"]): item for item in cases}.values(),
            key=lambda item: (type_order[item["tipo"]], item["numero"]),
        )
        for port, cases in results.items()
    }


def _result(
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
    connection = None
    try:
        _deadline_check(deadline)
        connection = oracledb.connect(
            user=settings.oracle_helix_user,
            password=settings.oracle_helix_password,
            dsn=dsn, tcp_connect_timeout=8,
        )
        if register_cancel:
            register_cancel(connection.cancel)
        _deadline_check(deadline, connection)
        with connection.cursor() as cursor:
            cursor.arraysize = 50
            cursor.prefetchrows = 50
            relation_meter = [0]
            if alcance == "equipo":
                result = _consultar_equipo_asociaciones(
                    cursor, olt, deadline, connection, relation_meter,
                )
            else:
                result = _consultar_puertos_asociaciones(
                    cursor, olt, deadline, connection, relation_meter,
                )
        return result, datetime.now(timezone.utc).isoformat(timespec="seconds")
    except HelixQueryError:
        raise
    except Exception as exc:
        logger.exception("Falló la consulta completa de casos Helix para la OLT solicitada")
        raise HelixQueryError("Oracle Helix no está disponible o la consulta falló") from exc
    finally:
        if connection is not None:
            try:
                connection.close()
            finally:
                if register_cancel:
                    register_cancel(None)


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
