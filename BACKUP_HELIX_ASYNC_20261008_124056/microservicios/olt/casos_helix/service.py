"""Cruce exacto de casos Helix abiertos por OLT y puerto."""

from __future__ import annotations

import re
import logging
import threading
import time
from collections import OrderedDict, defaultdict
from datetime import datetime, timezone
from typing import Any, Iterable

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

_cache: OrderedDict[str, tuple[float, str, dict[str, list[dict[str, Any]]]]] = OrderedDict()
_cache_lock = threading.Lock()
_query_lock = threading.Lock()


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


def _deadline_check(deadline: float, connection: Any | None = None) -> None:
    remaining = deadline - time.monotonic()
    if connection is not None:
        call_timeout = max(1, min(settings.oracle_helix_call_timeout_ms, int(max(0, remaining) * 1000)))
        connection.call_timeout = call_timeout
    if time.monotonic() >= deadline:
        raise HelixQueryError("La consulta Helix superó el tiempo disponible")


def _fetch(cursor: Any, sql: str, binds: dict[str, Any], deadline: float, connection: Any) -> list[tuple[Any, ...]]:
    _deadline_check(deadline, connection)
    cursor.execute(sql, binds)
    rows: list[tuple[Any, ...]] = []
    while True:
        _deadline_check(deadline, connection)
        batch = cursor.fetchmany(50)
        if not batch:
            break
        rows.extend(tuple(_read(value) if hasattr(value, "read") else value for value in row) for row in batch)
        if len(rows) > MAX_RELATIONS:
            raise HelixQueryError("La consulta excedió el límite de relaciones; resultado incompleto")
    return rows


def _in_query(cursor: Any, sql_prefix: str, ids: Iterable[str], deadline: float, connection: Any) -> list[tuple[Any, ...]]:
    values = sorted({str(value).strip() for value in ids if str(value or "").strip()})
    rows: list[tuple[Any, ...]] = []
    for start in range(0, len(values), 200):
        group = values[start:start + 200]
        if not group:
            continue
        names = [f"id{i}" for i in range(len(group))]
        binds = dict(zip(names, group))
        sql = sql_prefix.format(bind_list=", ".join(f":{name}" for name in names))
        rows.extend(_fetch(cursor, sql, binds, deadline, connection))
    return rows


def _result(olt: str, deadline: float) -> tuple[dict[str, list[dict[str, Any]]], str]:
    required = (
        settings.oracle_helix_host,
        settings.oracle_helix_service_name,
        settings.oracle_helix_user,
        settings.oracle_helix_password,
    )
    if not all(required):
        raise HelixQueryError("Oracle Helix no está configurado completamente")
    if oracledb is None:
        raise HelixQueryError("Falta la dependencia python-oracledb")

    dsn = oracledb.makedsn(
        settings.oracle_helix_host,
        settings.oracle_helix_port,
        service_name=settings.oracle_helix_service_name,
    )
    results: dict[str, list[dict[str, Any]]] = defaultdict(list)
    parent_ports: dict[str, set[str]] = defaultdict(set)
    inc_records: dict[str, tuple[int, set[str]]] = {}
    wo_records: dict[str, tuple[str, int, set[str]]] = {}
    alarms: dict[str, set[str]] = defaultdict(set)
    relation_count = 0

    try:
        _deadline_check(deadline)
        connection = oracledb.connect(
            user=settings.oracle_helix_user,
            password=settings.oracle_helix_password,
            dsn=dsn,
            tcp_connect_timeout=8,
        )
        try:
            _deadline_check(deadline, connection)
            with connection.cursor() as cursor:
                cursor.arraysize = 50
                cursor.prefetchrows = 50

                alarm_rows = _fetch(cursor, """
                    SELECT INCIDENT_NUMBER, R_TICKETNRO, NODE, EB, PADRE_EB, SECTOR_EB, INFO_SUPLEM
                    FROM ARADMIN.INT_NETCOOL_ALARMAS
                    WHERE INSTR(UPPER(NODE), :olt) > 0 OR INSTR(UPPER(EB), :olt) > 0
                       OR INSTR(UPPER(PADRE_EB), :olt) > 0 OR INSTR(UPPER(SECTOR_EB), :olt) > 0
                       OR INSTR(UPPER(INFO_SUPLEM), :olt) > 0
                """, {"olt": olt}, deadline, connection)
                for incident, ticket, *fields in alarm_rows:
                    scope = _scope(olt, fields)
                    if not scope:
                        continue
                    for value in (incident, ticket):
                        match = re.search(r"INC\d+", _read(value), re.I)
                        if match:
                            alarms[match.group(0).upper()].update(scope)
                    relation_count += 1

                inc_rows = _fetch(cursor, """
                    SELECT INCIDENT_NUMBER, STATUS, SHORT_DESCRIPTION, DESCRIPTION
                    FROM ARADMIN.HPD_HELP_DESK
                    WHERE INSTR(UPPER(SHORT_DESCRIPTION), :olt) > 0 OR INSTR(UPPER(DESCRIPTION), :olt) > 0
                """, {"olt": olt}, deadline, connection)
                for number, status, short, description in inc_rows:
                    scope = _scope(olt, (short, description))
                    number = _read(number).strip().upper()
                    if number and scope:
                        inc_records[number] = (_status(status), scope)
                        relation_count += 1

                wo_rows = _fetch(cursor, """
                    SELECT WORK_ORDER_ID, ROOT_INCIDENT, STATUS, SUMMARY, NODE, DETAILED_DESCRIPTION
                    FROM ARADMIN.WOI_WORKORDER
                    WHERE INSTR(UPPER(SUMMARY), :olt) > 0 OR INSTR(UPPER(NODE), :olt) > 0
                       OR INSTR(UPPER(DETAILED_DESCRIPTION), :olt) > 0
                """, {"olt": olt}, deadline, connection)
                for number, root, status, summary, node, description in wo_rows:
                    scope = _scope(olt, (summary, node, description))
                    number = _read(number).strip().upper()
                    if number and scope:
                        wo_records[number] = (_read(root).strip().upper(), _status(status), scope)
                        relation_count += 1

                tas_rows = _fetch(cursor, """
                    SELECT TASK_ID, ROOTREQUESTNAME, ROOTREQUESTFORMNAME, STATUS, SUMMARY
                    FROM ARADMIN.TMS_TASK
                    WHERE INSTR(UPPER(SUMMARY), :olt) > 0
                """, {"olt": olt}, deadline, connection)
                tas_candidates: dict[str, tuple[str, str, int, set[str]]] = {}
                for number, root, form, status, summary in tas_rows:
                    scope = _scope(olt, (summary,))
                    number = _read(number).strip().upper()
                    if number and scope:
                        tas_candidates[number] = (_read(root).strip().upper(), _read(form).strip(), _status(status), scope)
                        relation_count += 1

                inc_ids = set(alarms) | set(inc_records)
                for number, status in _in_query(cursor, """
                    SELECT INCIDENT_NUMBER, STATUS FROM ARADMIN.HPD_HELP_DESK
                    WHERE INCIDENT_NUMBER IN ({bind_list})
                """, inc_ids, deadline, connection):
                    key = _read(number).strip().upper()
                    if key:
                        old_scope = inc_records.get(key, (_status(status), set()))[1]
                        inc_records[key] = (_status(status), old_scope | alarms.get(key, set()))

                wo_parent_ids = set(inc_records)
                for number, root, status, summary, node, description in _in_query(cursor, """
                    SELECT WORK_ORDER_ID, ROOT_INCIDENT, STATUS, SUMMARY, NODE, DETAILED_DESCRIPTION
                    FROM ARADMIN.WOI_WORKORDER WHERE ROOT_INCIDENT IN ({bind_list})
                """, wo_parent_ids, deadline, connection):
                    key = _read(number).strip().upper()
                    parent = _read(root).strip().upper()
                    explicit = _scope(olt, (summary, node, description))
                    inherited = inc_records.get(parent, (0, set()))[1]
                    has_location = _has_explicit_location((summary, node, description))
                    scope = explicit if explicit else (set() if has_location else inherited)
                    if key and scope:
                        wo_records[key] = (parent, _status(status), scope)
                        relation_count += 1

                tas_parent_ids = set(inc_records)
                for number, root, form, status, summary in _in_query(cursor, """
                    SELECT TASK_ID, ROOTREQUESTNAME, ROOTREQUESTFORMNAME, STATUS, SUMMARY
                    FROM ARADMIN.TMS_TASK WHERE ROOTREQUESTFORMNAME = 'HPD:Help Desk'
                      AND ROOTREQUESTNAME IN ({bind_list})
                """, tas_parent_ids, deadline, connection):
                    key, parent = _read(number).strip().upper(), _read(root).strip().upper()
                    explicit = _scope(olt, (summary,))
                    has_location = _has_explicit_location((summary,))
                    scope = explicit if explicit else (set() if has_location else inc_records.get(parent, (0, set()))[1])
                    if key and scope:
                        tas_candidates[key] = (parent, _read(form).strip(), _status(status), scope)
                        relation_count += 1

                wo_ids = set(wo_records)
                for number, root, form, status, summary in _in_query(cursor, """
                    SELECT TASK_ID, ROOTREQUESTNAME, ROOTREQUESTFORMNAME, STATUS, SUMMARY
                    FROM ARADMIN.TMS_TASK WHERE ROOTREQUESTFORMNAME = 'WOI:WorkOrder'
                      AND ROOTREQUESTNAME IN ({bind_list})
                """, wo_ids, deadline, connection):
                    key, parent = _read(number).strip().upper(), _read(root).strip().upper()
                    explicit = _scope(olt, (summary,))
                    has_location = _has_explicit_location((summary,))
                    scope = explicit if explicit else (set() if has_location else wo_records.get(parent, ("", 0, set()))[2])
                    if key and scope:
                        tas_candidates[key] = (parent, _read(form).strip(), _status(status), scope)
                        relation_count += 1

                if relation_count > MAX_RELATIONS:
                    raise HelixQueryError("La consulta excedió el límite de relaciones; resultado incompleto")

                def add(kind: str, number: str, status: int, scope: set[str], states: dict[int, str], allowed: frozenset[int]) -> None:
                    if status not in allowed:
                        return
                    state = states.get(status)
                    if not state:
                        return
                    for port in scope:
                        results[port].append({"tipo": kind, "numero": number, "estado_codigo": status, "estado": state})

                for number, (status, scope) in inc_records.items():
                    add("INC", number, status, scope, INCIDENT_STATES, OPEN_INC)
                for number, (_parent, status, scope) in wo_records.items():
                    add("WO", number, status, scope, WO_STATES, OPEN_WO)
                for number, (_parent, _form, status, scope) in tas_candidates.items():
                    add("TAS", number, status, scope, TASK_STATES, OPEN_TASK)

                total_cases = sum(len(cases) for cases in results.values())
                if total_cases > MAX_CASES:
                    raise HelixQueryError("La consulta excedió el límite de casos; resultado incompleto")
        finally:
            connection.close()
    except HelixQueryError:
        raise
    except Exception as exc:
        logger.exception("Falló la consulta completa de casos Helix para la OLT solicitada")
        raise HelixQueryError("Oracle Helix no está disponible o la consulta falló") from exc

    type_order = {"INC": 0, "WO": 1, "TAS": 2}
    normalized = {
        port: sorted(items, key=lambda item: (type_order[item["tipo"]], item["numero"]))
        for port, items in results.items()
    }
    consulted_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return normalized, consulted_at


def obtener_casos_abiertos(olt: str, puertos: list[str]) -> dict[str, Any]:
    ttl = max(0, settings.oracle_helix_cache_seconds)
    now = time.monotonic()
    with _cache_lock:
        for expired_olt, cached_entry in list(_cache.items()):
            if now - cached_entry[0] > ttl:
                del _cache[expired_olt]
        cached = _cache.get(olt)
        if cached and now - cached[0] <= ttl:
            _cache.move_to_end(olt)
            stamp, consulted_at, index = cached
            return {
                "olt": olt, "cache": True, "consultado_en": consulted_at,
                "puertos": {port: {"ok": True, "casos": list(index.get(port, []))} for port in puertos},
            }
        if cached:
            del _cache[olt]

    if not _query_lock.acquire(timeout=0.15):
        raise HelixQueryError("La consulta de otra OLT está ocupada; reintente en el próximo ciclo")
    try:
        # Recheck after the lock: another request may have populated the cache.
        with _cache_lock:
            cached = _cache.get(olt)
            if cached and time.monotonic() - cached[0] <= ttl:
                _cache.move_to_end(olt)
                _stamp, consulted_at, index = cached
                return {
                    "olt": olt, "cache": True, "consultado_en": consulted_at,
                    "puertos": {port: {"ok": True, "casos": list(index.get(port, []))} for port in puertos},
                }

        deadline = time.monotonic() + max(1, settings.oracle_helix_budget_seconds)
        index, consulted_at = _result(olt, deadline)
        with _cache_lock:
            _cache[olt] = (time.monotonic(), consulted_at, index)
            _cache.move_to_end(olt)
            while len(_cache) > 32:
                _cache.popitem(last=False)
        return {
            "olt": olt, "cache": False, "consultado_en": consulted_at,
            "puertos": {port: {"ok": True, "casos": list(index.get(port, []))} for port in puertos},
        }
    finally:
        _query_lock.release()
