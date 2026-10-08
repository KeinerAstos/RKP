"""Caché de historial de 7 días; las peticiones nunca esperan su consulta."""

import logging
from threading import Lock, Thread
from time import monotonic

logger = logging.getLogger(__name__)


class CacheHistorial:
    def __init__(self, ttl=300, reintento=30, max_antiguedad=900):
        self.ttl = ttl
        self.reintento = reintento
        self.max_antiguedad = max_antiguedad
        self._lock = Lock()
        self._datos = None
        self._actualizado = None
        self._proximo = 0
        self._en_curso = False
        self._error = False

    def leer(self):
        with self._lock:
            edad = (monotonic() - self._actualizado
                    if self._actualizado is not None else None)
            utilizable = edad is not None and edad <= self.max_antiguedad
            estado = (
                "ERROR" if self._error else
                "PENDIENTE" if edad is None else
                "VENCIDA" if edad > self.max_antiguedad else
                "ACTUALIZANDO" if self._en_curso else
                "LISTA"
            )
            return (self._datos if utilizable else None), {
                "estado": estado,
                "en_curso": self._en_curso,
                "utilizable": utilizable,
                "antiguedad_segundos": round(edad, 1) if edad is not None else None,
            }

    def solicitar(self, cargar):
        with self._lock:
            if self._en_curso or monotonic() < self._proximo:
                return
            self._en_curso = True
        try:
            Thread(target=self._actualizar, args=(cargar,),
                   name="olt-historial-7d", daemon=True).start()
        except Exception:
            with self._lock:
                self._en_curso = False
                self._proximo = monotonic() + self.reintento
                self._error = True
            logger.exception("No se pudo iniciar la verificación OLT de 7 días")

    def _actualizar(self, cargar):
        try:
            # Publicar todo junto: un fallo parcial no equivale a historial vacío.
            datos = cargar()
            with self._lock:
                self._datos = datos
                self._actualizado = monotonic()
                self._proximo = self._actualizado + self.ttl
                self._error = False
        except Exception:
            with self._lock:
                self._proximo = monotonic() + self.reintento
                self._error = True
            logger.exception("Falló la verificación OLT de 7 días")
        finally:
            with self._lock:
                self._en_curso = False
