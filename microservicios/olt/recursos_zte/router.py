"""Rutas HTTP de recursos ZTE."""

from fastapi import APIRouter

from microservicios.influx_resultados import leer_resultado

router = APIRouter(tags=["OLT - Recursos ZTE"])


@router.get("/recursos-zte/licencias-bajas")
def licencias_bajas() -> dict:
    return {"ok": True, "data": leer_resultado('zte_licencias')}

