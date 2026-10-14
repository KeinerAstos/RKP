from microservicios.influx_resultados import leer_resultado
"""Rutas HTTP de correlacion OLT."""

from fastapi import APIRouter


router = APIRouter(tags=["OLT - Correlación"])


@router.get("/correlacion")
def correlacion() -> dict:
    return {"ok": True, "data": leer_resultado('olt_correlacion')}

