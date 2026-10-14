"""Validación histórica V2 y retención de 1 mes + 1 día.

La regla es la de HFC_AUTO/app/processors/validar_hfc_historico.py (noc_cable);
en lugar de leer los hfc_unificado_*.csv de 7 días, lee hfc_muestras.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from statistics import median

from microservicios.cmts.dashboard_hfc.conexion import ahora, config

MIN_POSITIVE_SAMPLES = 2
MIN_CEROS_CONSECUTIVOS = 2
MEDIANA_ALTA = ULTIMO_ALTA = 20
MEDIANA_MEDIA = ULTIMO_MEDIA = 5
ESTADO_ALTA = "POSIBLE DESENGANCHE TOTAL / HISTORICO"
ESTADO_MEDIA = "POSIBLE CAIDA PROLONGADA / HISTORICO"
ESTADO_VALIDAR = "CERO CON EVIDENCIA HISTORICA / VALIDAR"
ESTADOS_V2 = (ESTADO_ALTA, ESTADO_MEDIA, ESTADO_VALIDAR)
PALABRAS_PUERTO_LIBRE = ("PUERTO LIBRE", "PUERTO_LIBRE", "PORT FREE", "SIN ASIGNAR")


def clasificar(ultimo_total: int, mediana_total: int, muestras: int, ceros: int) -> tuple:
    """(estado, prioridad, nivel, razón); idéntico al original."""
    if muestras < MIN_POSITIVE_SAMPLES:
        return None, None, "SIN_EVIDENCIA", "No hay suficientes observaciones positivas."
    alta = mediana_total >= MEDIANA_ALTA or ultimo_total >= ULTIMO_ALTA
    media = mediana_total >= MEDIANA_MEDIA or ultimo_total >= ULTIMO_MEDIA
    sostenida = ceros >= MIN_CEROS_CONSECUTIVOS
    if alta and sostenida:
        return ESTADO_ALTA, "ALTA", "ALTA", "Historico fuerte y cero sostenido."
    if alta:
        return ESTADO_MEDIA, "MEDIA", "MEDIA", "Historico fuerte, pero aun no hay suficientes ceros consecutivos."
    if media and sostenida:
        return ESTADO_MEDIA, "MEDIA", "MEDIA", "Historico moderado y cero sostenido."
    return ESTADO_VALIDAR, "VALIDAR", "VALIDAR", "Existe evidencia historica positiva, pero el impacto habitual es bajo."


def _fmt(dt: datetime | None) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else "NO DISPONIBLE"


def aplicar_v2(cnx, filas: list[dict], fecha_reporte: datetime, run_id: str) -> list[tuple]:
    """Reclasifica en sitio las filas con TOTAL_MODEMS = 0.

    Debe llamarse DESPUÉS de insertar las muestras del ciclo, porque el
    original cuenta el ciclo actual dentro de los ceros consecutivos.
    Devuelve las filas para hfc_validacion_historica.
    """
    desde = fecha_reporte - timedelta(days=config().hist_dias)
    auditoria = []
    cur = cnx.cursor()
    try:
        for fila in filas:
            if fila["TOTAL_MODEMS"] > 0:
                continue
            texto = " ".join(str(fila.get(k) or "") for k in ("OBSERVACION", "DESCRIPCION", "ELEMENTO")).upper()
            if any(p in texto for p in PALABRAS_PUERTO_LIBRE):
                continue
            cur.execute(
                "SELECT fecha, total_modems FROM hfc_muestras WHERE fabricante=%s AND cmts=%s AND elemento=%s "
                "AND fecha >= %s AND fecha <= %s ORDER BY fecha, id",
                (fila["FABRICANTE"], fila["CMTS"], fila["ELEMENTO"], desde, fecha_reporte))
            observaciones = cur.fetchall()
            positivas = [(f, t) for f, t in observaciones if t > 0]
            if len(positivas) < MIN_POSITIVE_SAMPLES:
                continue
            ultima_fecha, ultimo_total = positivas[-1]
            valores = [t for _, t in positivas]
            mediana_total = int(round(median(valores)))
            max_total = max(valores)
            ceros, inicio_cero = 0, None
            for f, t in reversed(observaciones):
                if t != 0:
                    break
                ceros += 1
                inicio_cero = f
            if ceros == 0:  # el ciclo actual siempre cuenta como cero
                ceros, inicio_cero = 1, fecha_reporte
            horas = max(0.0, (fecha_reporte - inicio_cero).total_seconds() / 3600) if inicio_cero else None
            estado, prioridad, nivel, razon = clasificar(ultimo_total, mediana_total, len(positivas), ceros)
            if not estado:
                continue
            detalle = (
                "VALIDACION HISTORICA V2: actualmente TOTAL_MODEMS=0. "
                f"Este elemento tuvo modems en {len(positivas)} observaciones positivas. "
                f"Ultimo total positivo={ultimo_total} ({_fmt(ultima_fecha)}); "
                f"mediana historica={mediana_total}; maximo historico={max_total}; "
                f"ceros consecutivos={ceros}; inicio estimado del cero={_fmt(inicio_cero)}; "
                f"horas en cero={'tiempo no calculable' if horas is None else f'{horas:.1f} h'}. "
                f"Clasificacion={nivel}. Razon={razon} "
                "El valor cero no se interpreta automaticamente como nodo sin modems.")
            anterior = fila["OBSERVACION"]
            base = re.split(r"\s+\|\s+VALIDACION HISTORICA(?: V2)?:", fila.get("DESCRIPCION") or "",
                            maxsplit=1, flags=re.I)[0].strip()
            fila["OBSERVACION"], fila["PRIORIDAD"], fila["NIVEL_HISTORICO"] = estado, prioridad, nivel
            fila["DESCRIPCION"] = f"{base} | {detalle}" if base else detalle
            auditoria.append((run_id, fecha_reporte, fila["FABRICANTE"], fila["CMTS"][:60], fila["ELEMENTO"][:80],
                              anterior[:60], estado, prioridad, nivel, len(positivas), ultimo_total, ultima_fecha,
                              mediana_total, max_total, ceros, inicio_cero,
                              None if horas is None else round(horas, 2), razon[:120]))
    finally:
        cur.close()
    return auditoria


def purgar(cnx, lote: int = 20000) -> dict[str, int]:
    """Borra por lotes todo lo anterior a ahora - HFC_RETENCION_MESES - HFC_RETENCION_DIAS."""
    c = config()
    if c.retencion_meses == 0 and c.retencion_dias == 0:
        return {}
    corte = "%s - INTERVAL %s MONTH - INTERVAL %s DAY"
    parametros = (ahora(), c.retencion_meses, c.retencion_dias)
    tablas = [
        ("hfc_muestras", "fecha", ""),
        ("hfc_consultas_cmts", "fecha", ""),
        ("hfc_validacion_historica", "fecha", ""),
        ("hfc_ciclos", "inicio", ""),
        ("hfc_arris_alias", "actualizado", ""),
        ("hfc_estado_actual", "fecha_reporte", "vigente = 0 AND "),
    ]
    borrados = {}
    cur = cnx.cursor()
    try:
        for tabla, columna, filtro in tablas:
            total = 0
            while True:
                cur.execute(f"DELETE FROM {tabla} WHERE {filtro}{columna} < {corte} LIMIT {int(lote)}", parametros)
                n = cur.rowcount or 0
                cnx.commit()
                total += n
                if n < lote:
                    break
            borrados[tabla] = total
    finally:
        cur.close()
    return borrados
