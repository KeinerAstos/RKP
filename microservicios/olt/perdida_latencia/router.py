from microservicios.influx_resultados import leer_resultado
"""Rutas HTTP de pérdida y latencia OLT."""

from fastapi import APIRouter


router = APIRouter(tags=["OLT - Pérdida y latencia"])


@router.get("/perdida-latencia/actual")
def perdida_latencia_actual() -> dict:
    return {"ok": True, "data": leer_resultado('olt_perdida_latencia')}

