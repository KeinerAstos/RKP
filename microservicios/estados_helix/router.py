"""INC y TAS con al menos seis horas en su estado actual, según HPD_WORKLOG.

No usa creación, última modificación ni cambios de responsable como sustitutos.
Las lecturas comparten una transacción Oracle READ ONLY y un instante de corte.
"""
from __future__ import annotations

import logging
import re
import threading
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from itertools import groupby

from fastapi import APIRouter, HTTPException

from microservicios.config import settings

try:
    import oracledb
except ImportError:
    oracledb = None

router = APIRouter(prefix="/api/estados_helix", tags=["Estados Helix"])
logger = logging.getLogger(__name__)
_consulta_lock = threading.Lock()
ESTADOS = {1: "Asignado", 2: "En progreso", 3: "Pendiente"}
CODIGOS = {
    "new": 0, "assigned": 1, "in progress": 2, "pending": 3,
    "resolved": 4, "closed": 5, "cancelled": 6, "canceled": 6,
}
PATRON = re.compile(
    r"^\s*Status Marked:\s*(New|Assigned|In Progress|Work In Progress|Pending|Resolved|Closed|Cancelled|Canceled|Staged|Waiting|Bypassed)\s+by\s+",
    re.IGNORECASE,
)
UMBRAL_SEGUNDOS = 6 * 60 * 60
BOGOTA = timezone(timedelta(hours=-5))

CATEGORIAS = ("SERVICIOS FIJOS", "REDES NEUTRAS")
# Coincidencia exacta: no incluye variantes EYN, RC u otras categorías.
FILTRO_CATEGORIA = "i.CATEGORIZATION_TIER_1 IN ('SERVICIOS FIJOS', 'REDES NEUTRAS')"
SQL_INCIDENTES = f"""
    SELECT i.INCIDENT_NUMBER, i.STATUS, i.SHORT_DESCRIPTION, i.ASSIGNED_GROUP,
           i.ASSIGNEE, i.REGIONAL, i.ALIADO, i.DEPARTAMENTO__ESTADO_PROVINCIA,
           i.CIUDAD, i.CATEGORIZATION_TIER_1
    FROM ARADMIN.HPD_HELP_DESK i
    WHERE i.STATUS IN (1, 2, 3) AND {FILTRO_CATEGORIA}
"""
SQL_HISTORIAL = f"""
    SELECT w.INCIDENT_NUMBER, w.WORK_LOG_SUBMIT_DATE,
           DBMS_LOB.SUBSTR(w.DETAILED_DESCRIPTION, 1000, 1), w.WORK_LOG_ID
    FROM ARADMIN.HPD_WORKLOG w
    JOIN ARADMIN.HPD_HELP_DESK i ON i.INCIDENT_NUMBER = w.INCIDENT_NUMBER
    WHERE i.STATUS IN (1, 2, 3) AND {FILTRO_CATEGORIA}
      AND w.WORK_LOG_TYPE = 40000
    ORDER BY w.INCIDENT_NUMBER, w.WORK_LOG_SUBMIT_DATE DESC NULLS LAST,
             w.WORK_LOG_ID DESC
"""


ESTADOS_TAS = {2000: "Asignado", 3000: "Pendiente", 4000: "En progreso"}
CODIGOS_TAS = {
    "staged": 1000, "assigned": 2000, "pending": 3000,
    "work in progress": 4000, "waiting": 5000, "closed": 6000,
    "bypassed": 7000, "cancelled": 8000, "canceled": 8000,
}
# Las dos ramas son disjuntas por ROOTREQUESTFORMNAME. No se filtra el
# estado del INC padre: una TAS abierta puede pertenecer a un INC cerrado.
CTE_TAREAS = f"""
    WITH tareas_filtradas AS (
        SELECT t.TASK_ID, t.STATUS, t.SUMMARY, t.ASSIGNEE_GROUP,
               t.ROOTREQUESTNAME, t.ROOTREQUESTFORMNAME,
               i.CATEGORIZATION_TIER_1 AS CATEGORIA, i.INCIDENT_NUMBER AS INC_CATEGORIA
        FROM ARADMIN.TMS_TASK t
        JOIN ARADMIN.HPD_HELP_DESK i ON i.INCIDENT_NUMBER = t.ROOTREQUESTNAME
        WHERE t.STATUS IN (2000, 3000, 4000)
          AND t.ROOTREQUESTFORMNAME = 'HPD:Help Desk'
          AND {FILTRO_CATEGORIA}
        UNION ALL
        SELECT t.TASK_ID, t.STATUS, t.SUMMARY, t.ASSIGNEE_GROUP,
               t.ROOTREQUESTNAME, t.ROOTREQUESTFORMNAME,
               i.CATEGORIZATION_TIER_1 AS CATEGORIA, i.INCIDENT_NUMBER AS INC_CATEGORIA
        FROM ARADMIN.TMS_TASK t
        JOIN ARADMIN.WOI_WORKORDER o ON o.WORK_ORDER_ID = t.ROOTREQUESTNAME
        JOIN ARADMIN.HPD_HELP_DESK i ON i.INCIDENT_NUMBER = o.ROOT_INCIDENT
        WHERE t.STATUS IN (2000, 3000, 4000)
          AND t.ROOTREQUESTFORMNAME = 'WOI:WorkOrder'
          AND {FILTRO_CATEGORIA}
    )
"""
SQL_TAREAS = CTE_TAREAS + """
    SELECT TASK_ID, STATUS, SUMMARY, ASSIGNEE_GROUP,
           ROOTREQUESTNAME, ROOTREQUESTFORMNAME, CATEGORIA, INC_CATEGORIA
    FROM tareas_filtradas
"""
SQL_HISTORIAL_TAS = CTE_TAREAS + """
    SELECT w.TASKORTASKGROUPID, w.WORKINFOSUBMITDATE,
           DBMS_LOB.SUBSTR(w.NOTES, 1000, 1), w.WORK_INFO_ID
    FROM ARADMIN.TMS_WORKINFO w
    JOIN tareas_filtradas t ON t.TASK_ID = w.TASKORTASKGROUPID
    WHERE w.WORKINFOTYPE = 40000
    ORDER BY w.TASKORTASKGROUPID, w.WORKINFOSUBMITDATE DESC NULLS LAST,
             w.WORK_INFO_ID DESC
"""

PERFILES = {
    "INC": {
        "estados": ESTADOS, "codigos": CODIGOS,
        "sql": SQL_INCIDENTES, "historial": SQL_HISTORIAL,
        "campos": ("titulo", "grupo_soporte", "responsable", "regional",
                   "aliado", "departamento", "ciudad", "categoria_operacional_nivel_1"),
        "fuente": "ARADMIN.HPD_WORKLOG / WORK_LOG_TYPE=40000",
        "contador": "total_inc_revisados", "coleccion": "incidentes",
        "cobertura": "todos_los_inc_con_fecha_verificable",
    },
    "TAS": {
        "estados": ESTADOS_TAS, "codigos": CODIGOS_TAS,
        "sql": SQL_TAREAS, "historial": SQL_HISTORIAL_TAS,
        "campos": ("titulo", "grupo_soporte", "solicitud_raiz", "formulario_raiz",
                   "categoria_operacional_nivel_1", "inc_fuente_categoria"),
        "fuente": "ARADMIN.TMS_WORKINFO / WORKINFOTYPE=40000",
        "contador": "total_tas_revisadas", "coleccion": "tareas",
        "cobertura": "todas_las_tas_con_fecha_verificable",
    },
}


def fecha_iso(epoch):
    return datetime.fromtimestamp(float(epoch), timezone.utc).astimezone(BOGOTA).isoformat()


def evaluar_historial(estado_actual, filas, ahora, mapa_codigos=None):
    """Filas (INC, epoch, texto, WLG) ordenadas de más nuevas a más antiguas.

    Colapsa marcas consecutivas del mismo estado: una repetición o cambio de
    motivo no reinicia el contador. Nunca busca una marca antigua ignorando
    una transición posterior diferente o no interpretable.
    """
    mapa_codigos = CODIGOS if mapa_codigos is None else mapa_codigos
    inicio = None
    evidencia = None
    for fecha, grupo in groupby(filas, key=lambda row: row[1]):
        if fecha is None:
            return None, None, "fecha_historial_ausente"
        fecha = Decimal(str(fecha))
        if not fecha.is_finite() or fecha <= 0 or fecha > ahora:
            return None, None, "fecha_historial_invalida"
        codigos = set()
        ids = []
        for _, _, texto, worklog_id in grupo:
            match = PATRON.match(str(texto or ""))
            codigos.add(mapa_codigos.get(match.group(1).lower(), -1) if match else -1)
            ids.append(str(worklog_id))
        if len(codigos) != 1:
            return None, None, "estados_ambiguos_en_mismo_segundo"
        codigo = codigos.pop()
        if codigo == -1:
            return None, None, "marca_estado_no_reconocida"
        if codigo != estado_actual:
            if inicio is None:
                return None, None, "historial_no_coincide_con_estado_actual"
            break
        inicio, evidencia = fecha, min(ids)
    if inicio is None:
        return None, None, "sin_historial_de_estado"
    return inicio, evidencia, None


def _limitar(connection, deadline):
    limites = []
    if settings.oracle_helix_call_timeout_ms > 0:
        limites.append(settings.oracle_helix_call_timeout_ms)
    if deadline is not None:
        restante = deadline - time.monotonic()
        if restante <= 0:
            raise TimeoutError("Presupuesto de consulta agotado")
        limites.append(max(1, int(restante * 1000)))
    connection.call_timeout = min(limites) if limites else 0


def _filas(cursor, connection, deadline):
    while True:
        _limitar(connection, deadline)
        lote = cursor.fetchmany(500)
        if not lote:
            return
        yield from lote



ESTADOS_WO_INCLUIDOS = frozenset({0, 1, 4, 7})
ESTADOS_TAS_INCLUIDOS = frozenset({2000, 3000, 4000, 8000})

ESTADOS_WO = {
    0: "Asignado", 1: "Pendiente", 2: "Esperando aprobacion", 3: "Planificacion",
    4: "En progreso", 5: "Completado", 6: "Rechazado", 7: "Cancelado", 8: "Cerrado",
}
ESTADOS_TAS_TODOS = {
    1000: "Preparado", 2000: "Asignado", 3000: "Pendiente", 4000: "En progreso",
    5000: "En espera", 6000: "Cerrado", 7000: "Omitido", 8000: "Cancelado",
}


def _por_ids(cursor, connection, deadline, sql, ids):
    """Consultas por lotes de hasta 200 IDs, nunca una por INC/WO."""
    valores = sorted(set(ids))
    for inicio in range(0, len(valores), 200):
        lote = valores[inicio:inicio + 200]
        binds = {f"id{n}": valor for n, valor in enumerate(lote)}
        nombres = ", ".join(":" + nombre for nombre in binds)
        _limitar(connection, deadline)
        cursor.execute(sql.format(ids=nombres), binds)
        yield from _filas(cursor, connection, deadline)


def agregar_relaciones(cursor, connection, deadline, incidentes):
    """Relaciones por ROOT_INCIDENT y ROOTREQUESTNAME/FORMNAME.

    La selección por categoría y >=6h corresponde al INC. Sus hijos se
    incluyen en Asignado/Pendiente/En progreso/Cancelado, sin exigirles antigüedad propia.
    """
    por_inc = {caso["numero"]: caso for caso in incidentes}
    wos, tareas_por_inc = {}, {numero: {} for numero in por_inc}
    for caso in incidentes:
        caso["wos"] = []
        caso["tareas"] = []
    sql_wo = """
        SELECT WORK_ORDER_ID, ROOT_INCIDENT, STATUS, SUMMARY
        FROM ARADMIN.WOI_WORKORDER
        WHERE ROOT_INCIDENT IN ({ids})
    """
    for numero, padre, estado, titulo in _por_ids(
        cursor, connection, deadline, sql_wo, por_inc
    ):
        numero, padre = str(numero), str(padre)
        if padre not in por_inc:
            raise RuntimeError("WO fuera de los INC seleccionados")
        if numero in wos:
            if wos[numero]["inc_padre"] != padre:
                raise RuntimeError("WO con varios INC padre en la vista")
            continue
        codigo = int(estado) if estado is not None else -1
        wo = {
            "numero": numero, "inc_padre": padre, "estado_codigo": codigo,
            "estado": ESTADOS_WO.get(codigo, "Desconocido"),
            "titulo": str(titulo or ""), "tas_relacionadas": [],
        }
        wos[numero] = wo
        por_inc[padre]["wos"].append(wo)
    sql_tas_inc = """
        SELECT TASK_ID, ROOTREQUESTNAME, STATUS, SUMMARY, ASSIGNEE_GROUP
        FROM ARADMIN.TMS_TASK
        WHERE ROOTREQUESTFORMNAME = 'HPD:Help Desk'
          AND ROOTREQUESTNAME IN ({ids})
          AND STATUS IN (2000, 3000, 4000, 8000)
    """
    sql_tas_wo = """
        SELECT TASK_ID, ROOTREQUESTNAME, STATUS, SUMMARY, ASSIGNEE_GROUP
        FROM ARADMIN.TMS_TASK
        WHERE ROOTREQUESTFORMNAME = 'WOI:WorkOrder'
          AND ROOTREQUESTNAME IN ({ids})
          AND STATUS IN (2000, 3000, 4000, 8000)
    """
    for relacion, sql, ids in (
        ("directa", sql_tas_inc, por_inc), ("mediante_wo", sql_tas_wo, wos)
    ):
        for numero, padre, estado, titulo, grupo in _por_ids(
            cursor, connection, deadline, sql, ids
        ):
            numero, padre = str(numero), str(padre)
            inc = padre if relacion == "directa" else wos[padre]["inc_padre"]
            if inc not in por_inc:
                raise RuntimeError("TAS fuera de los INC seleccionados")
            codigo = int(estado) if estado is not None else -1
            tarea = {
                "numero": numero, "estado_codigo": codigo,
                "estado": ESTADOS_TAS_TODOS.get(codigo, "Desconocido"),
                "titulo": str(titulo or ""), "grupo_soporte": str(grupo or ""),
                "relacion": relacion, "wo_padre": padre if relacion == "mediante_wo" else None,
            }
            anterior = tareas_por_inc[inc].get(numero)
            if anterior is not None and anterior != tarea:
                raise RuntimeError("TAS con relaciones contradictorias en la vista")
            tareas_por_inc[inc][numero] = tarea
            if relacion == "mediante_wo":
                wos[padre]["tas_relacionadas"].append(numero)
    tareas_unicas, wos_visibles = set(), set()
    for caso in incidentes:
        # Se recorren todas las WO para encontrar TAS válidas incluso si la
        # WO padre está cerrada; cada hijo se filtra por su estado propio.
        caso["wos"] = [wo for wo in caso["wos"] if wo["estado_codigo"] in ESTADOS_WO_INCLUIDOS]
        wos_visibles.update(wo["numero"] for wo in caso["wos"])
        caso["wos"].sort(key=lambda row: row["numero"])
        caso["tareas"] = sorted(tareas_por_inc[caso["numero"]].values(), key=lambda row: row["numero"])
        for wo in caso["wos"]:
            wo["tas_relacionadas"] = sorted(set(wo["tas_relacionadas"]))
            wo["cantidad_tareas"] = len(wo["tas_relacionadas"])
        caso["cantidad_wos"] = len(caso["wos"])
        caso["cantidad_tareas"] = len(caso["tareas"])
        caso["cantidad_tareas_directas"] = sum(t["relacion"] == "directa" for t in caso["tareas"])
        caso["cantidad_tareas_via_wo"] = caso["cantidad_tareas"] - caso["cantidad_tareas_directas"]
        caso["wos_por_estado"] = dict(Counter(w["estado"] for w in caso["wos"]))
        caso["tareas_por_estado"] = dict(Counter(t["estado"] for t in caso["tareas"]))
        tareas_unicas.update(t["numero"] for t in caso["tareas"])
    return {
        "total_wos": len(wos_visibles), "total_tareas": len(tareas_unicas),
        "inc_con_wos": sum(bool(caso["wos"]) for caso in incidentes),
        "inc_con_tareas": sum(bool(caso["tareas"]) for caso in incidentes),
        "alcance": "WO/TAS en Asignado, Pendiente, En progreso o Cancelado; >=6h y categoria se aplican al INC",
        "estados_hijos_incluidos": ["Asignado", "Pendiente", "En progreso", "Cancelado"],
        "fuente": "WOI_WORKORDER.ROOT_INCIDENT y TMS_TASK.ROOTREQUESTNAME/ROOTREQUESTFORMNAME",
    }

def consultar_incidentes(tipo="INC"):
    """Una conexión nueva por consulta; no comparte el pool de OLT."""
    perfil = PERFILES[tipo]
    estados = perfil["estados"]
    if oracledb is None:
        raise HTTPException(503, "Falta instalar oracledb")
    if not all((settings.oracle_helix_host, settings.oracle_helix_service_name,
                settings.oracle_helix_user, settings.oracle_helix_password)):
        raise HTTPException(503, "Falta configurar Oracle Helix en el .env")
    started = time.monotonic()
    budget = settings.oracle_helix_query_budget_seconds
    deadline = started + budget if budget > 0 else None
    dsn = oracledb.makedsn(
        settings.oracle_helix_host, settings.oracle_helix_port,
        service_name=settings.oracle_helix_service_name,
    )
    with oracledb.connect(
        user=settings.oracle_helix_user, password=settings.oracle_helix_password,
        dsn=dsn, tcp_connect_timeout=min(8, budget) if budget > 0 else 8,
    ) as connection:
        _limitar(connection, deadline)
        with connection.cursor() as cursor:
            cursor.arraysize = 500
            cursor.prefetchrows = 500
            cursor.execute("SET TRANSACTION READ ONLY")
            _limitar(connection, deadline)
            cursor.execute("""
                SELECT ROUND((CAST(SYS_EXTRACT_UTC(SYSTIMESTAMP) AS DATE)
                        - DATE '1970-01-01') * 86400) FROM dual
            """)
            ahora = Decimal(str(cursor.fetchone()[0]))
            _limitar(connection, deadline)
            cursor.execute(perfil["sql"])
            incidentes = {}
            for row in _filas(cursor, connection, deadline):
                numero = str(row[0])
                if numero in incidentes:
                    raise RuntimeError("Identificador duplicado en la vista Oracle")
                incidentes[numero] = {
                    "numero": numero, "estado_codigo": int(row[1]),
                    "estado": estados[int(row[1])],
                    **dict(zip(
                        perfil["campos"],
                        (str(value or "") for value in row[2:]),
                    )),
                }
            _limitar(connection, deadline)
            cursor.execute(perfil["historial"])
            resultados, no_verificables, vistos = [], [], set()
            menores = 0
            for numero, filas in groupby(
                _filas(cursor, connection, deadline), key=lambda row: str(row[0])
            ):
                caso = incidentes[numero]
                vistos.add(numero)
                inicio, evidencia, motivo = evaluar_historial(
                    caso["estado_codigo"], filas, ahora, perfil["codigos"]
                )
                if motivo:
                    no_verificables.append({
                        "numero": numero, "estado": caso["estado"], "motivo": motivo,
                    })
                    continue
                segundos = ahora - inicio
                if segundos < UMBRAL_SEGUNDOS:
                    menores += 1
                    continue
                resultados.append({
                    **caso, "fecha_entrada_estado": fecha_iso(inicio),
                    "fecha_entrada_estado_epoch": int(inicio),
                    "segundos_en_estado": float(segundos),
                    "horas_en_estado": round(float(segundos / 3600), 4),
                    "worklog_entrada_estado": evidencia,
                })
            for numero in sorted(incidentes.keys() - vistos):
                no_verificables.append({
                    "numero": numero, "estado": incidentes[numero]["estado"],
                    "motivo": "sin_historial_de_estado",
                })
            resumen_relaciones = (
                agregar_relaciones(cursor, connection, deadline, resultados)
                if tipo == "INC" else None
            )
    resultados.sort(key=lambda row: (-row["segundos_en_estado"], row["numero"]))
    conteo = Counter(row["estado"] for row in resultados)
    return {
        "ok": True, "fecha_corte": fecha_iso(ahora),
        "zona_horaria": "America/Bogota", "umbral_horas": 6,
        "tipo": tipo, "fuente": perfil["fuente"],
        **({"resumen_relaciones": resumen_relaciones} if tipo == "INC" else {}),
        "categorias_incluidas": list(CATEGORIAS),
        "categoria_fuente": "INC actual" if tipo == "INC" else "INC raiz directo o mediante WO",
        perfil["contador"]: len(incidentes),
        "total": len(resultados),
        "por_estado": {estado: conteo[estado] for estado in estados.values()},
        "menores_de_6h": menores,
        perfil["cobertura"]: not no_verificables,
        "total_no_verificables": len(no_verificables),
        "motivos_no_verificables": dict(Counter(x["motivo"] for x in no_verificables)),
        "no_verificables": no_verificables,
        perfil["coleccion"]: resultados,
        "duracion_segundos": round(time.monotonic() - started, 3),
    }


def _obtener(tipo):
    # Endpoint síncrono: FastAPI ejecuta Oracle fuera del event loop.
    # Evita dos barridos simultáneos dentro del mismo proceso.
    if not _consulta_lock.acquire(blocking=False):
        raise HTTPException(503, "Ya hay una consulta de estados Helix en curso")
    try:
        return consultar_incidentes() if tipo == "INC" else consultar_incidentes(tipo)
    except HTTPException:
        raise
    except TimeoutError:
        raise HTTPException(504, "Oracle superó el presupuesto de consulta configurado") from None
    except Exception:
        logger.exception("Falló la consulta de estados Helix")
        raise HTTPException(503, "No se pudo completar la consulta de estados Helix; revise el log") from None
    finally:
        _consulta_lock.release()


@router.get("/relaciones")
@router.get("/incidentes")
def obtener_incidentes():
    return _obtener("INC")


@router.get("/tareas")
def obtener_tareas():
    return _obtener("TAS")
