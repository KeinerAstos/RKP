"""INC con al menos seis horas en su estado actual, según HPD_WORKLOG.

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
    r"^\s*Status Marked:\s*(New|Assigned|In Progress|Pending|Resolved|Closed|Cancelled|Canceled)\s+by\s+",
    re.IGNORECASE,
)
UMBRAL_SEGUNDOS = 6 * 60 * 60
BOGOTA = timezone(timedelta(hours=-5))

SQL_INCIDENTES = """
    SELECT INCIDENT_NUMBER, STATUS, SHORT_DESCRIPTION, ASSIGNED_GROUP,
           ASSIGNEE, REGIONAL, ALIADO, DEPARTAMENTO__ESTADO_PROVINCIA, CIUDAD
    FROM ARADMIN.HPD_HELP_DESK
    WHERE STATUS IN (1, 2, 3)
"""
SQL_HISTORIAL = """
    SELECT w.INCIDENT_NUMBER, w.WORK_LOG_SUBMIT_DATE,
           DBMS_LOB.SUBSTR(w.DETAILED_DESCRIPTION, 1000, 1), w.WORK_LOG_ID
    FROM ARADMIN.HPD_WORKLOG w
    JOIN ARADMIN.HPD_HELP_DESK i ON i.INCIDENT_NUMBER = w.INCIDENT_NUMBER
    WHERE i.STATUS IN (1, 2, 3)
      AND w.WORK_LOG_TYPE = 40000
    ORDER BY w.INCIDENT_NUMBER, w.WORK_LOG_SUBMIT_DATE DESC NULLS LAST,
             w.WORK_LOG_ID DESC
"""


def fecha_iso(epoch):
    return datetime.fromtimestamp(float(epoch), timezone.utc).astimezone(BOGOTA).isoformat()


def evaluar_historial(estado_actual, filas, ahora):
    """Filas (INC, epoch, texto, WLG) ordenadas de más nuevas a más antiguas.

    Colapsa marcas consecutivas del mismo estado: una repetición o cambio de
    motivo no reinicia el contador. Nunca busca una marca antigua ignorando
    una transición posterior diferente o no interpretable.
    """
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
            codigos.add(CODIGOS[match.group(1).lower()] if match else -1)
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


def consultar_incidentes():
    """Una conexión nueva por consulta; no comparte el pool de OLT."""
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
            cursor.execute(SQL_INCIDENTES)
            incidentes = {}
            for row in _filas(cursor, connection, deadline):
                numero = str(row[0])
                if numero in incidentes:
                    raise RuntimeError("INC duplicado en la vista Oracle")
                incidentes[numero] = {
                    "numero": numero, "estado_codigo": int(row[1]),
                    "estado": ESTADOS[int(row[1])],
                    **dict(zip(
                        ("titulo", "grupo_soporte", "responsable", "regional",
                         "aliado", "departamento", "ciudad"),
                        (str(value or "") for value in row[2:]),
                    )),
                }
            _limitar(connection, deadline)
            cursor.execute(SQL_HISTORIAL)
            resultados, no_verificables, vistos = [], [], set()
            menores = 0
            for numero, filas in groupby(
                _filas(cursor, connection, deadline), key=lambda row: str(row[0])
            ):
                caso = incidentes[numero]
                vistos.add(numero)
                inicio, evidencia, motivo = evaluar_historial(
                    caso["estado_codigo"], filas, ahora
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
    resultados.sort(key=lambda row: (-row["segundos_en_estado"], row["numero"]))
    conteo = Counter(row["estado"] for row in resultados)
    return {
        "ok": True, "fecha_corte": fecha_iso(ahora),
        "zona_horaria": "America/Bogota", "umbral_horas": 6,
        "fuente": "ARADMIN.HPD_WORKLOG / WORK_LOG_TYPE=40000",
        "total_inc_revisados": len(incidentes),
        "total": len(resultados),
        "por_estado": {estado: conteo[estado] for estado in ESTADOS.values()},
        "menores_de_6h": menores,
        "todos_los_inc_con_fecha_verificable": not no_verificables,
        "total_no_verificables": len(no_verificables),
        "motivos_no_verificables": dict(Counter(x["motivo"] for x in no_verificables)),
        "no_verificables": no_verificables,
        "incidentes": resultados,
        "duracion_segundos": round(time.monotonic() - started, 3),
    }


@router.get("/incidentes")
def obtener_incidentes():
    # Endpoint síncrono: FastAPI ejecuta Oracle fuera del event loop.
    # Evita dos barridos simultáneos dentro del mismo proceso.
    if not _consulta_lock.acquire(blocking=False):
        raise HTTPException(503, "Ya hay una consulta de estados Helix en curso")
    try:
        return consultar_incidentes()
    except HTTPException:
        raise
    except TimeoutError:
        raise HTTPException(504, "Oracle superó el presupuesto de consulta configurado") from None
    except Exception:
        logger.exception("Falló la consulta de estados Helix")
        raise HTTPException(503, "No se pudo completar la consulta de estados Helix; revise el log") from None
    finally:
        _consulta_lock.release()
