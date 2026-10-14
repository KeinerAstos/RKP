from microservicios.influx_resultados import leer_resultado
"""Rutas HTTP de saturacion OLT."""

from fastapi import APIRouter


router = APIRouter(tags=["OLT - Saturación"])


@router.get("/saturacion")
def saturacion() -> dict:
    return {"ok": True, "data": leer_resultado('olt_saturacion')}


@router.get("/saturacion/actual")
def saturacion_actual() -> dict:
    return {"ok": True, "data": leer_resultado('olt_saturacion_actual')}

