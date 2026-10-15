
"""API HTTP para consultar casos abiertos Helix por nodo HFC."""

from fastapi import APIRouter, HTTPException, Query

from microservicios.cmts.dashboard_hfc.casos_abiertos_helix import (
    consultar_nodo,
)
from microservicios.olt.casos_helix.service import HelixQueryError

router = APIRouter(tags=["HFC - Casos Helix"])


@router.get("/casos-abiertos-helix")
def casos_abiertos_helix(
    nodo: str = Query(..., min_length=1, max_length=120),
):
    try:
        resultado = consultar_nodo(nodo)
        return {"ok": True, "data": resultado}

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except HelixQueryError as exc:
        raise HTTPException(
            status_code=503,
            detail="No fue posible consultar Oracle Helix",
        ) from exc
