from microservicios.influx_resultados import leer_resultado
"""Rutas HTTP de nodos asociados a multiples puertos CMTS."""

from fastapi import APIRouter


router = APIRouter(tags=["CMTS - Puertos duplicados"])


@router.get("/puertos-duplicados/actual")
def puertos_duplicados_actual() -> dict:
    return {"ok": True, "data": leer_resultado('cmts_duplicados')}

