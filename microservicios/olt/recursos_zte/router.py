import logging

from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder

from microservicios.influx_resultados import leer_resultado
from microservicios.mysql import consultar_mysql

logger = logging.getLogger(__name__)

router = APIRouter(tags=["OLT - Recursos ZTE"])


@router.get("/recursos-zte/licencias-bajas")
def licencias_bajas() -> dict:
    return {"ok": True, "data": leer_resultado("zte_licencias")}


@router.get("/recursos-huawei")
def recursos_huawei() -> dict:
    try:
        filas = consultar_mysql("SELECT * FROM OLT.recursos_huawei")

        # También permite mostrar encabezados si la tabla está vacía.
        estructura = consultar_mysql("SHOW COLUMNS FROM OLT.recursos_huawei")
        columnas = [str(campo["Field"]) for campo in estructura]

        return {
            "ok": True,
            "data": {
                "columnas": columnas,
                "filas": jsonable_encoder(filas),
            },
        }
    except Exception as exc:
        logger.exception("Error consultando recursos Huawei")
        raise HTTPException(
            status_code=503,
            detail="No se pudieron consultar los recursos Huawei",
        ) from exc
