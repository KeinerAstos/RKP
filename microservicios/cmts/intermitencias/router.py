from microservicios.influx_resultados import leer_resultado
"""Rutas HTTP de intermitencias HFC."""

from fastapi import APIRouter


router = APIRouter(tags=["CMTS - Intermitencias"])


@router.get("/intermitencias/actual")
def intermitencias_actual() -> dict:
    return {"ok": True, "data": leer_resultado('cmts_intermitencias')}

