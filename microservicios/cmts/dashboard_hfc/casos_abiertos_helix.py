
"""Consulta de INC, WO y TAS abiertos asociados a nodos HFC."""

from __future__ import annotations

import logging
import re
import time
import threading
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any

from microservicios.config import settings
from microservicios.olt.casos_helix import service as helix

logger = logging.getLogger(__name__)

HFC_CACHE_TTL = 120
HFC_CACHE_MAX_NODOS = 100

_hfc_cache = OrderedDict()
_hfc_cache_lock = threading.Lock()
_hfc_query_lock = threading.Lock()

def normalizar_nodo(nodo: str) -> str:
    """Normaliza y valida el nombre exacto del nodo HFC."""
    valor = nodo.strip().upper()
    if not re.fullmatch(r"[A-Z0-9._-]{1,120}", valor):
        raise ValueError("Nombre de nodo HFC no valido")
    return valor


def consultar_ci_nodo(
    cursor: Any,
    nodo: str,
    deadline: float | None,
    connection: Any,
    meter: list[int],
) -> set[str]:
    """Obtiene los CI unicos del nodo HFC."""

    sql = """
        SELECT RECONCILIATION_IDENTITY
        FROM ARADMIN.AST_BASEELEMENT
        WHERE NAME = :nodo
          AND SHORT_DESCRIPTION = 'RT.TR.HFC.NODO'
          AND CLASS_ID = 'BMC_COMPUTERSYSTEM'
    """

    return {
        helix._read(fila[0]).strip()
        for fila in helix._fetch(
            cursor, sql, {"nodo": normalizar_nodo(nodo)},
            deadline, connection, meter,
        )
        if helix._read(fila[0]).strip()
    }


def _consultar_casos(
    cursor: Any,
    nodo: str,
    deadline: float | None,
    connection: Any,
    meter: list[int],
) -> dict[str, Any]:
    """Recupera los casos relacionados con el nodo."""

    leer = helix._read
    estado_num = helix._status
    casos = {}

    ci_ids = consultar_ci_nodo(
        cursor, nodo, deadline, connection, meter
    )

    resultado = {
        "nodo": nodo,
        "ci_encontrados": len(ci_ids),
        "inc": 0,
        "wo": 0,
        "tas": 0,
        "casos": [],
    }

    if not ci_ids:
        return resultado

    # 1. Buscar INC asociados a los CI del nodo.
    inc_ids = set()

    sql_asociaciones = """
        SELECT REQUEST_ID01, REQUEST_ID02
        FROM ARADMIN.HPD_ASSOCIATIONS
        WHERE REQUEST_ID01 IN ({bind_list})
          AND FORM_NAME01 = 'AST:ComputerSystem'
          AND FORM_NAME02 = 'HPD:Help Desk'
    """

    for _, inc in helix._in_query(
        cursor, sql_asociaciones, ci_ids,
        deadline, connection, meter,
    ):
        numero = leer(inc).strip().upper()
        if re.fullmatch(r"INC\d+", numero):
            inc_ids.add(numero)

    if not inc_ids:
        return resultado

    # 2. Consultar estados de los INC.
    # Se conservan todos los INC asociados para buscar
    # sus WO y TAS, incluso si el INC esta cerrado.
    sql_inc = """
        SELECT INCIDENT_NUMBER, STATUS,
               SHORT_DESCRIPTION, DESCRIPTION,
               REGIONAL, ALIADO,
               DEPARTAMENTO__ESTADO_PROVINCIA, CIUDAD
        FROM ARADMIN.HPD_HELP_DESK
        WHERE INCIDENT_NUMBER IN ({bind_list})
    """

    for fila in helix._in_query(
        cursor, sql_inc, inc_ids,
        deadline, connection, meter,
    ):
        numero = leer(fila[0]).strip().upper()
        estado = estado_num(fila[1])

        if numero and estado in helix.OPEN_INC:
            casos[("INC", numero)] = {
                "tipo": "INC",
                "numero": numero,
                "estado_codigo": estado,
                "estado": helix.INCIDENT_STATES[estado],
                "resumen": leer(fila[2]).strip(),
                "descripcion": leer(fila[3]).strip(),
                "regional": leer(fila[4]).strip(),
                "aliado": leer(fila[5]).strip(),
                "departamento": leer(fila[6]).strip(),
                "ciudad": leer(fila[7]).strip(),
            }

    # 3. Buscar WO asociadas a los INC.
    wo_ids = set()

    sql_wo = """
        SELECT WORK_ORDER_ID, ROOT_INCIDENT, STATUS
        FROM ARADMIN.WOI_WORKORDER
        WHERE ROOT_INCIDENT IN ({bind_list})
    """

    for numero, inc_padre, estado_raw in helix._in_query(
        cursor, sql_wo, inc_ids,
        deadline, connection, meter,
    ):
        numero = leer(numero).strip().upper()
        inc_padre = leer(inc_padre).strip().upper()
        estado = estado_num(estado_raw)

        if not numero:
            continue

        wo_ids.add(numero)

        if estado in helix.OPEN_WO:
            casos[("WO", numero)] = {
                "tipo": "WO",
                "numero": numero,
                "estado_codigo": estado,
                "estado": helix.WO_STATES[estado],
                "inc_padre": inc_padre,
            }

    # 4. Buscar TAS relacionadas directamente con INC.
    sql_tas_inc = """
        SELECT TASK_ID, ROOTREQUESTNAME,
               STATUS, ASSIGNEE_GROUP
        FROM ARADMIN.TMS_TASK
        WHERE ROOTREQUESTFORMNAME = 'HPD:Help Desk'
          AND ROOTREQUESTNAME IN ({bind_list})
    """

    for numero, padre, estado_raw, grupo in helix._in_query(
        cursor, sql_tas_inc, inc_ids,
        deadline, connection, meter,
    ):
        numero = leer(numero).strip().upper()
        estado = estado_num(estado_raw)

        if numero and estado in helix.OPEN_TASK:
            casos[("TAS", numero)] = {
                "tipo": "TAS",
                "numero": numero,
                "estado_codigo": estado,
                "estado": helix.TASK_STATES[estado],
                "caso_padre": leer(padre).strip().upper(),
                "grupo_soporte": leer(grupo).strip(),
            }

    # 5. Buscar TAS relacionadas con WO.
    sql_tas_wo = """
        SELECT TASK_ID, ROOTREQUESTNAME,
               STATUS, ASSIGNEE_GROUP
        FROM ARADMIN.TMS_TASK
        WHERE ROOTREQUESTFORMNAME = 'WOI:WorkOrder'
          AND ROOTREQUESTNAME IN ({bind_list})
    """

    for numero, padre, estado_raw, grupo in helix._in_query(
        cursor, sql_tas_wo, wo_ids,
        deadline, connection, meter,
    ):
        numero = leer(numero).strip().upper()
        estado = estado_num(estado_raw)

        if numero and estado in helix.OPEN_TASK:
            casos[("TAS", numero)] = {
                "tipo": "TAS",
                "numero": numero,
                "estado_codigo": estado,
                "estado": helix.TASK_STATES[estado],
                "caso_padre": leer(padre).strip().upper(),
                "grupo_soporte": leer(grupo).strip(),
            }

    if len(casos) > helix.MAX_CASES:
        raise helix.HelixQueryError(
            "Se excedio el limite permitido de casos"
        )

    orden = {"INC": 0, "WO": 1, "TAS": 2}
    resultado["casos"] = sorted(
        casos.values(),
        key=lambda c: (orden[c["tipo"]], c["numero"]),
    )

    for caso in resultado["casos"]:
        resultado[caso["tipo"].lower()] += 1

    return resultado


def _consultar_nodo_once(nodo: str) -> dict[str, Any]:
    """Ejecuta la consulta usando el pool Oracle existente."""

    if helix.oracledb is None:
        raise helix.HelixQueryError(
            "La dependencia oracledb no esta instalada"
        )

    required = (
        settings.oracle_helix_host,
        settings.oracle_helix_service_name,
        settings.oracle_helix_user,
        settings.oracle_helix_password,
    )

    if not all(required):
        raise helix.HelixQueryError(
            "Configuracion Oracle Helix incompleta"
        )

    dsn = helix.oracledb.makedsn(
        settings.oracle_helix_host,
        settings.oracle_helix_port,
        service_name=settings.oracle_helix_service_name,
    )

    presupuesto = settings.oracle_helix_query_budget_seconds
    deadline = (
        time.monotonic() + presupuesto
        if presupuesto > 0 else None
    )

    pool = None
    connection = None
    failed = True

    try:
        helix._deadline_check(deadline)

        pool = helix._get_pool(dsn)
        connection = pool.acquire()

        helix._deadline_check(deadline, connection)

        with connection.cursor() as cursor:
            cursor.arraysize = 50
            cursor.prefetchrows = 50

            resultado = _consultar_casos(
                cursor,
                nodo,
                deadline,
                connection,
                [0],
            )

        resultado["consultado_en"] = datetime.now(
            timezone.utc
        ).isoformat(timespec="seconds")

        failed = False
        return resultado

    except helix.HelixQueryError:
        raise
    except Exception as exc:
        logger.exception(
            "[HFC HELIX] Error consultando nodo %s", nodo
        )
        raise helix.HelixQueryError(
            "No se pudo consultar Oracle Helix"
        ) from exc

    finally:
        if connection is not None and pool is not None:
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



def consultar_nodo(nodo: str) -> dict[str, Any]:
    """Consulta casos HFC con cache, concurrencia y recuperacion Oracle."""

    nodo = normalizar_nodo(nodo)

    # 1. Comprobar si hay resultado vigente en cache.
    with _hfc_cache_lock:
        entrada = _hfc_cache.get(nodo)

        if entrada and time.monotonic() - entrada["timestamp"] < HFC_CACHE_TTL:
            _hfc_cache.move_to_end(nodo)
            return {**entrada["resultado"], "cache": True}

    # 2. Evitar consultas HFC simultaneas.
    with helix.oracle_query_lock:

        # Segunda comprobacion de cache.
        with _hfc_cache_lock:
            entrada = _hfc_cache.get(nodo)

            if entrada and time.monotonic() - entrada["timestamp"] < HFC_CACHE_TTL:
                _hfc_cache.move_to_end(nodo)
                return {**entrada["resultado"], "cache": True}

        # 3. Consultar Oracle y reintentar ante desconexiones recuperables.
        for intento in range(2):
            try:
                resultado = _consultar_nodo_once(nodo)
                break

            except helix.HelixQueryError as exc:
                if not helix._desconexion(exc) or intento == 1:
                    raise

                helix.close_oracle_pool()
                logger.warning(
                    "[HFC HELIX] Conexion perdida. "
                    "Recreando pool y reintentando nodo=%s",
                    nodo,
                )

        # 4. Guardar resultado en cache.
        with _hfc_cache_lock:
            _hfc_cache[nodo] = {
                "timestamp": time.monotonic(),
                "resultado": resultado,
            }
            _hfc_cache.move_to_end(nodo)

            while len(_hfc_cache) > HFC_CACHE_MAX_NODOS:
                _hfc_cache.popitem(last=False)

        # 5. Devolver resultado.
        return {**resultado, "cache": False}
