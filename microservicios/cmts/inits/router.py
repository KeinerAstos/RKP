"""API del monitoreo INIT; GET sólo consulta CSV ya publicados."""
import asyncio
import csv
import io
from contextlib import suppress

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import StreamingResponse

from microservicios.config import settings
from microservicios.cmts.inits import inits_cmts as service

router = APIRouter(tags=["CMTS - Monitoreo INIT"])
_cycle_task: asyncio.Task | None = None
_scheduler_task: asyncio.Task | None = None


def _summary(rows: list[dict]) -> dict:
    valid = [row for row in rows if row["ok"] and row["total_init"] is not None]
    return {"total_cmts": len(rows), "exitosas": len(valid), "fallidas": len(rows) - len(valid),
            "total_init": sum(row["total_init"] for row in valid), "cobertura": len(valid) / len(rows) if rows else 0}


def _with_delta(rows: list[dict]) -> list[dict]:
    previous = {}
    try:
        with (service.data_dir() / "historico.csv").open(newline="", encoding="utf-8-sig") as f:
            for old in csv.DictReader(f):
                if old.get("ok", "").lower() == "true" and old.get("total_init") not in (None, "") and (not rows or old.get("run_id") != rows[0].get("run_id")):
                    previous[old["cmts"]] = old
    except OSError:
        pass
    output = []
    for row in rows:
        old = previous.get(row["cmts"])
        delta = row["total_init"] - int(old["total_init"]) if row["ok"] and row["total_init"] is not None and old else None
        output.append({**row, "variacion": delta, "comparado_con": old.get("fecha") if delta is not None else None})
    return output


async def _run_cycle(run_id: str | None = None, claimed: bool = False) -> None:
    global _cycle_task
    try:
        await asyncio.to_thread(service.run_cycle, run_id, claimed=claimed)
    except Exception as exc:
        print(f"[CMTS INIT] Ciclo {run_id or 'manual'} terminó con error: {type(exc).__name__}")
    finally:
        _cycle_task = None


async def _run_probe(run_id: str, cmts: str) -> None:
    global _cycle_task
    try:
        await asyncio.to_thread(service.run_probe, cmts, run_id, claimed=True)
    except Exception as exc:
        print(f"[CMTS INIT] Prueba {cmts} terminó con error: {type(exc).__name__}")
    finally:
        _cycle_task = None


async def start_scheduler() -> None:
    global _scheduler_task
    if settings.cmts_init_enabled and _scheduler_task is None:
        _scheduler_task = asyncio.create_task(_scheduled_cycles())


async def _scheduled_cycles() -> None:
    while True:
        global _cycle_task
        if _cycle_task is None or _cycle_task.done():
            try:
                claim = service.claim_cycle()
            except (RuntimeError, OSError) as exc:
                print(f"[CMTS INIT] No se pudo reservar ciclo: {type(exc).__name__}")
                await asyncio.sleep(5)
                continue
            if not claim["created"]:
                await asyncio.sleep(5)
                continue
            _cycle_task = asyncio.create_task(_run_cycle(claim["run_id"], True))
        await asyncio.shield(_cycle_task)
        await asyncio.sleep(max(60, settings.cmts_init_interval_seconds))


async def stop_scheduler() -> None:
    global _scheduler_task, _cycle_task
    if _scheduler_task:
        _scheduler_task.cancel()
        with suppress(asyncio.CancelledError): await _scheduler_task
        _scheduler_task = None
    if _cycle_task and not _cycle_task.done():
        # Do not cancel an in-flight SSH thread; individual connections are bounded at 90 s.
        with suppress(Exception, asyncio.TimeoutError):
            await asyncio.wait_for(asyncio.shield(_cycle_task), timeout=95)
    _cycle_task = None


@router.get("/inits/actual")
def actual() -> dict:
    try:
        rows = service.actual()
        return {"ok": True, "data": {"items": _with_delta(rows), "resumen": _summary(rows),
                "run_id": rows[0]["run_id"] if rows else None, "fecha": max((r["fecha"] for r in rows), default=None)}}
    except (OSError, ValueError) as exc:
        raise HTTPException(503, str(exc)) from exc


@router.get("/inits/estado")
def estado() -> dict:
    data = service.status(); data["progreso"] = service.get_progress()
    return {"ok": True, "data": data}


@router.post("/inits/actualizar", status_code=202)
async def actualizar(response: Response) -> dict:
    global _cycle_task
    if not settings.cmts_init_enabled:
        raise HTTPException(503, "Monitoreo INIT deshabilitado")
    if not settings.cmts_user or not settings.cmts_password:
        raise HTTPException(503, "Configura CMTS_USER y CMTS_PASSWORD")
    run_id = None
    reused = False
    if _cycle_task is None or _cycle_task.done():
        try:
            claim = service.claim_cycle()
        except RuntimeError as exc:
            raise HTTPException(409, str(exc)) from exc
        if not claim["created"] and claim.get("alcance") != "global":
            raise HTTPException(409, "Hay una prueba individual en curso")
        if claim["created"]:
            _cycle_task = asyncio.create_task(_run_cycle(claim["run_id"], True))
        else:
            run_id = claim["run_id"]
            reused = True
            response.headers["Retry-After"] = "5"
            return {"ok": True, "estado": "procesando", "run_id": run_id, "reutilizado": True}
        run_id = claim["run_id"]
    else:
        active = service.status()
        if active.get("alcance_activo") != "global":
            raise HTTPException(409, "Hay una prueba individual en curso")
        run_id = active.get("run_id")
        reused = True
    response.headers["Retry-After"] = "5"
    return {"ok": True, "estado": "procesando", "run_id": run_id, "reutilizado": reused}


@router.post("/inits/probar", status_code=202)
async def probar(response: Response, cmts: str = Query(..., min_length=1, max_length=160)) -> dict:
    global _cycle_task
    if not settings.cmts_init_enabled:
        raise HTTPException(503, "Monitoreo INIT deshabilitado")
    if not settings.cmts_user or not settings.cmts_password:
        raise HTTPException(503, "Configura CMTS_USER y CMTS_PASSWORD")
    try:
        items = service.inventory()
    except (OSError, ValueError) as exc:
        raise HTTPException(503, str(exc)) from exc
    if not any(item["cmts"].casefold() == cmts.casefold() or item["ip"] == cmts for item in items):
        raise HTTPException(404, "CMTS no encontrado en el inventario")
    run_id = None
    reused = False
    if _cycle_task is None or _cycle_task.done():
        try:
            claim = service.claim_cycle("equipo", cmts)
        except RuntimeError as exc:
            raise HTTPException(409, str(exc)) from exc
        if not claim["created"]:
            if claim.get("alcance") != "equipo" or claim.get("cmts", "").casefold() != cmts.casefold():
                raise HTTPException(409, "Hay otro ciclo CMTS en curso")
            run_id, reused = claim["run_id"], True
        else:
            run_id = claim["run_id"]
            _cycle_task = asyncio.create_task(_run_probe(run_id, cmts))
    else:
        active = service.status()
        if active.get("alcance_activo") != "equipo" or active.get("cmts_activo", "").casefold() != cmts.casefold():
            raise HTTPException(409, "Hay otro ciclo CMTS en curso")
        run_id, reused = active.get("run_id"), True
    response.headers["Retry-After"] = "5"
    return {"ok": True, "estado": "procesando", "run_id": run_id, "reutilizado": reused, "alcance": "equipo"}


@router.get("/inits/historico")
def historico(cmts: str = "", desde: str = "", hasta: str = "", limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0)) -> dict:
    try: return {"ok": True, "data": service.history(cmts=cmts, desde=desde, hasta=hasta, limit=limit, offset=offset)}
    except FileNotFoundError: return {"ok": True, "data": {"items": [], "total": 0, "limit": limit, "offset": offset}}
    except (OSError, ValueError) as exc: raise HTTPException(503, str(exc)) from exc


@router.get("/inits/tendencia")
def tendencia(cmts: str, limit: int = Query(200, ge=2, le=1000)) -> dict:
    try: return {"ok": True, "data": service.trend(cmts, limit)}
    except FileNotFoundError: return {"ok": True, "data": []}
    except (OSError, ValueError) as exc: raise HTTPException(503, str(exc)) from exc


def _safe_cell(value: str, numeric: bool) -> str:
    if not numeric and value.startswith(("=", "+", "-", "@", "\t", "\r")): return "'" + value
    return value


@router.get("/inits/exportar")
def exportar(cmts: str = "", desde: str = "", hasta: str = ""):
    def stream():
        buffer = io.StringIO(newline=""); writer = csv.DictWriter(buffer, fieldnames=service.FIELDS); writer.writeheader()
        yield "\ufeff" + buffer.getvalue(); buffer.seek(0); buffer.truncate(0)
        for row in service.export_rows(cmts, desde, hasta):
            for key in ("run_id", "alcance", "cmts", "ip", "fecha", "estado", "error"):
                row[key] = _safe_cell(str(row.get(key) or ""), False)
            writer.writerow(row); yield buffer.getvalue(); buffer.seek(0); buffer.truncate(0)
    return StreamingResponse(stream(), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": "attachment; filename=cmts-init-historico.csv"})
