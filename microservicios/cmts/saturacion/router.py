"""Lectura compartida HFC. La página no inicia consultas a Influx."""
from fastapi import APIRouter
from microservicios.cmts.saturacion.cache import leer_estado, leer_saturacion
router = APIRouter(tags=["CMTS - Saturación"])
@router.get("/saturacion/actual")
def saturacion_actual():
    return {"ok": True, "data": leer_saturacion()}
@router.get("/saturacion/estado")
def saturacion_estado():
    return {"ok": True, "data": leer_estado()}
@router.post("/saturacion/actualizar")
def saturacion_actualizar():
    return {"ok": True, "estado": "programado", "mensaje": "Actualización a cargo de la rutina central"}
