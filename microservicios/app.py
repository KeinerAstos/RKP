"""Aplicacion FastAPI principal de Backend Datos."""

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from microservicios.config import settings
from microservicios.olt.casos_helix import service as casos_helix_service
from microservicios.olt.casos_helix.worker import start_worker as start_helix_worker
from microservicios.olt.casos_helix.worker import stop_worker as stop_helix_worker
from microservicios.olt.topologias.router import router as topologias_router
from microservicios.olt.topologias import service as topologias_service
from microservicios.cmts.saturacion.router import router as cmts_saturacion_router
from microservicios.cmts.intermitencias.router import (
    router as cmts_intermitencias_router,
)
from microservicios.cmts.puertos_docsis.router import (
    router as cmts_puertos_docsis_router,
)
from microservicios.cmts.puertos_duplicados.router import (
    router as cmts_puertos_duplicados_router,
)
from microservicios.cmts.inits.router import (
    router as cmts_inits_router,
    start_scheduler as start_cmts_inits_scheduler,
    stop_scheduler as stop_cmts_inits_scheduler,
)
from microservicios.olt.caidas.router import router as caidas_router
from microservicios.olt.casos_helix.router import router as casos_helix_router
from microservicios.olt.correlacion.router import router as correlacion_router
from microservicios.olt.crc.router import router as crc_router
from microservicios.olt.perdida_latencia.router import (
    router as perdida_latencia_router,
)
from microservicios.olt.recursos_zte.router import router as recursos_zte_router
from microservicios.olt.saturacion.router import router as saturacion_router
from microservicios.olt.temperatura.router import router as temperatura_router
from microservicios.olt.topologias.router import router as topologias_router

async def worker_topologias() -> None:
    while True:
        try:
            resultado = await asyncio.to_thread(
                topologias_service.materializar_aleatoria
            )

        except Exception as exc:
            print(f"[TOPOLOGIAS AUTO] ERROR: {exc}")

        await asyncio.sleep(120)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    tarea = None
    start_helix_worker(
        casos_helix_service.consultar_olt,
        ttl_seconds=settings.oracle_helix_cache_seconds,
    )
    await start_cmts_inits_scheduler()

    if os.environ.get("TOPOLOGIAS_AUTO") == "1":
        print("[TOPOLOGIAS AUTO] Worker habilitado")
        tarea = asyncio.create_task(worker_topologias())
    else:
        print("[TOPOLOGIAS AUTO] Worker deshabilitado")

    try:
        yield
    finally:
        await stop_cmts_inits_scheduler()
        stop_helix_worker()
        if tarea:
            tarea.cancel()

            try:
                await tarea
            except asyncio.CancelledError:
                pass

app = FastAPI(title="Backend Datos API", version="1.0.0", lifespan=lifespan,)

@app.exception_handler(Exception)
async def error_no_controlado(_request: Request, _exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"ok": False, "error": "Error interno del servicio"},
    )


@app.exception_handler(HTTPException)
async def error_http(_request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"ok": False, "error": str(exc.detail)},
    )


@app.exception_handler(RequestValidationError)
async def error_validacion(
    _request: Request, _exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"ok": False, "error": "Parametros invalidos"},
    )


@app.get("/health")
def health() -> dict[str, object]:
    return {"ok": True, "service": "Backend Datos API"}


app.include_router(saturacion_router, prefix="/api/olt")
app.include_router(caidas_router, prefix="/api/olt")
app.include_router(casos_helix_router, prefix="/api/olt")
app.include_router(crc_router, prefix="/api/olt")
app.include_router(correlacion_router, prefix="/api/olt")
app.include_router(temperatura_router, prefix="/api/olt")
app.include_router(topologias_router, prefix="/api/olt")
app.include_router(perdida_latencia_router, prefix="/api/olt")
app.include_router(recursos_zte_router, prefix="/api/olt")
app.include_router(cmts_saturacion_router, prefix="/api/cmts")
app.include_router(cmts_puertos_docsis_router, prefix="/api/cmts")
app.include_router(cmts_intermitencias_router, prefix="/api/cmts")
app.include_router(cmts_puertos_duplicados_router, prefix="/api/cmts")
app.include_router(cmts_inits_router, prefix="/api/cmts")
