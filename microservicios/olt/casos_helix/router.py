"""Rutas de estado y lote para las consultas OLT de Helix."""

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from microservicios.olt.casos_helix import worker as worker_module
from microservicios.olt.casos_helix.service import normalizar_olt, normalizar_puertos

router = APIRouter(tags=["OLT - Casos Helix"])


class SolicitudOLT(BaseModel):
    model_config = ConfigDict(extra="forbid")

    olt: str = Field(min_length=1, max_length=120)
    puertos: list[str] = Field(min_length=1, max_length=100)


class SolicitudLote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    solicitudes: list[SolicitudOLT] = Field(min_length=1, max_length=32)


def _worker():
    worker = worker_module.get_worker()
    if worker is None:
        raise HTTPException(status_code=503, detail="El trabajador Helix no está disponible")
    return worker


def _legacy_result(result: dict[str, Any]) -> dict[str, Any]:
    state = result["estado"]
    data = {
        "olt": result["olt"],
        "cache": state == "listo",
        "estado": state,
        "job_id": result.get("job_id"),
        "generacion": result.get("generacion"),
        "revision": result.get("revision"),
        "iniciado_en": result.get("iniciado_en"),
        "finalizado_en": result.get("finalizado_en"),
        "consultado_en": result.get("consultado_en"),
        "puertos": {
            port: {
                "ok": item["estado"] == "listo",
                "estado": item["estado"],
                "casos": item["casos"],
            }
            for port, item in result["puertos"].items()
        },
    }
    if result.get("error"):
        data["error"] = result["error"]
    return data


@router.get("/casos-abiertos")
def casos_abiertos(
    olt: str = Query(..., min_length=1, max_length=120),
    puertos: str | None = Query(None, max_length=1200),
    alcance: str = "puertos",
) -> dict[str, Any]:
    try:
        equipo = normalizar_olt(olt)
        if alcance not in {"puertos", "equipo"}:
            raise ValueError("Alcance inválido")
        if alcance == "equipo":
            if puertos:
                raise ValueError("No envíe puertos cuando alcance=equipo")
            ports = []
        else:
            ports = normalizar_puertos(puertos or "")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    result = (_worker().submit(equipo, ports) if alcance == "puertos"
              else _worker().submit(equipo, [], alcance="equipo"))
    if result["estado"] == "error":
        raise HTTPException(status_code=503, detail=result.get("error", {}).get("mensaje", "No se pudo consultar Helix"))
    return {"ok": True, "data": (_legacy_result(result) if alcance == "puertos" else result)}


@router.post("/casos-abiertos/lote")
def casos_abiertos_lote(request: SolicitudLote) -> dict[str, Any]:
    combined: dict[str, list[str]] = {}
    try:
        for item in request.solicitudes:
            olt = normalizar_olt(item.olt)
            ports = normalizar_puertos(item.puertos)
            group = combined.setdefault(olt, [])
            for port in ports:
                if port not in group:
                    group.append(port)
            if len(group) > 100:
                raise ValueError("Se permiten hasta 100 puertos únicos por OLT en cada lote")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    worker = _worker()
    results = [worker.submit(olt, ports) for olt, ports in combined.items()]
    return {"ok": True, "data": {"resultados": results}}
