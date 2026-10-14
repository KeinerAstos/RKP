from microservicios.influx_resultados import leer_resultado
"""Rutas HTTP de errores CRC OLT."""

from fastapi import APIRouter


router = APIRouter(tags=["OLT - CRC"])


@router.get("/crc")
def crc() -> dict:
    return {"ok": True, "data": leer_resultado('olt_crc')}


@router.get("/crc/actual")
def crc_actual() -> dict:
    return {"ok": True, "data": leer_resultado('olt_crc_actual')}

