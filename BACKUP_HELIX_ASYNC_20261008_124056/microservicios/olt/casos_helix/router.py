"""Ruta independiente para consultar casos abiertos de una OLT."""

from fastapi import APIRouter, HTTPException, Query

from microservicios.olt.casos_helix.service import (
    HelixQueryError,
    obtener_casos_abiertos,
    normalizar_olt,
    normalizar_puertos,
)

router = APIRouter(tags=["OLT - Casos Helix"])


@router.get("/casos-abiertos")
def casos_abiertos(
    olt: str = Query(..., min_length=1, max_length=120),
    puertos: str = Query(..., min_length=1, max_length=1200),
) -> dict[str, object]:
    try:
        equipo = normalizar_olt(olt)
        ports = normalizar_puertos(puertos)
        return {"ok": True, "data": obtener_casos_abiertos(equipo, ports)}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except HelixQueryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
