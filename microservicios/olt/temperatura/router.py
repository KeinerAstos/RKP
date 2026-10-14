from microservicios.influx_resultados import leer_resultado
"""Rutas HTTP de temperatura OLT."""

from fastapi import APIRouter


router = APIRouter(tags=["OLT - Temperatura"])


@router.get("/temperatura/actual")
def temperatura_actual() -> dict:
    return {"ok": True, "data": leer_resultado('olt_temperatura')}

