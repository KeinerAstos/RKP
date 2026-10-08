"""Verificación del historial extendido sin acceso a Influx real."""

import unittest
from datetime import datetime, timedelta, timezone
from threading import Event
from unittest.mock import patch

from microservicios.olt.caidas import service
from microservicios.olt.caidas.cache import CacheHistorial


class HistorialTests(unittest.TestCase):
    def setUp(self):
        self.ahora = datetime.now(timezone.utc)
        self.clave = ("OLT-1", "1/1/1")
        service._cache_ultima_actividad.clear()

    def fila(self, dias=0, trafico=0):
        return {"OLT": self.clave[0], "PUERTO": self.clave[1],
                "_time": self.ahora - timedelta(days=dias), "TRAFICO": trafico}

    def historial(self, actividad=True, dias=5):
        return {
            "ultimas": {self.clave: {"fecha": self.ahora - timedelta(days=dias),
                                    "trafico": 0}},
            "actividades": {self.clave: {
                "fecha": self.ahora - timedelta(days=dias), "trafico": 50,
            }} if actividad else {},
            "verificados": frozenset([self.clave]),
        }

    def consultar(self, historial, recientes, conocidas=None):
        with patch.object(service._cache_historial_7d, "leer",
                          return_value=(historial, {"estado": "LISTA"})), \
             patch.object(service._cache_historial_7d, "solicitar"), \
             patch.object(service, "consultar_flux_temp",
                          side_effect=[recientes, conocidas or []]), \
             patch.object(service, "_buscar_ultima_actividad", return_value={}):
            return service.obtener_caidas_actuales()

    def puerto(self, resultado):
        return resultado["datos"][0]["puertos"][0]

    def test_trafico_hace_cinco_dias_confirma_caida_actual(self):
        puerto = self.puerto(self.consultar(self.historial(), [self.fila()]))
        self.assertEqual(puerto["estado"], "CAIDO_ACTUAL")
        self.assertEqual(puerto["clasificacion"], "DOWN_CON_HISTORIAL")
        self.assertEqual(puerto["origen_historial"], "cache_7_dias")
        self.assertGreaterEqual(puerto["tiempo_sin_trafico_dias"], 5)

    def test_sin_reportes_por_seis_dias_no_desaparece(self):
        puerto = self.puerto(self.consultar(self.historial(dias=6), []))
        self.assertEqual(puerto["estado"], "SIN_MUESTRAS_RECIENTES")
        self.assertEqual(puerto["clasificacion"], "SIN_MUESTRAS_RECIENTES")

    def test_recuperacion_prevalece_sobre_cache(self):
        resultado = self.consultar(self.historial(), [self.fila(trafico=100)],
                                   [self.fila(dias=1)])
        self.assertEqual(resultado["cantidad_puertos"], 0)

    def test_sin_actividad_no_se_declara_down_confirmado(self):
        puerto = self.puerto(self.consultar(self.historial(False), [self.fila()]))
        self.assertEqual(puerto["estado"], "CAIDO_SIN_FECHA")
        self.assertEqual(puerto["clasificacion"], "SIN_ACTIVIDAD_7_DIAS")

    def test_cache_fria_no_equivale_a_sin_actividad(self):
        puerto = self.puerto(self.consultar(None, [self.fila()]))
        self.assertEqual(puerto["clasificacion"], "PENDIENTE_VERIFICACION")

    def test_historial_fuera_de_siete_dias_se_excluye(self):
        resultado = self.consultar(self.historial(dias=8), [])
        self.assertEqual(resultado["cantidad_puertos"], 0)
        puerto = self.puerto(self.consultar(self.historial(dias=8), [self.fila()]))
        self.assertFalse(puerto["historial_encontrado"])

    def test_consultas_principales_siguen_en_cuatro_dias(self):
        with patch.object(service._cache_historial_7d, "solicitar"), \
             patch.object(service._cache_historial_7d, "leer", return_value=(None, {})), \
             patch.object(service, "consultar_flux_temp",
                          side_effect=[[self.fila()], [], []]) as consultar:
            service.obtener_caidas_actuales()
        consultas = [call.args[0] for call in consultar.call_args_list]
        self.assertIn("range(start: -30m)", consultas[0])
        self.assertTrue(all("range(start: -4d)" in q for q in consultas[1:]))

    def test_carga_background_busca_siete_dias(self):
        with patch.object(service, "consultar_flux_temp",
                          side_effect=[[self.fila(dias=6)], [self.fila(dias=6, trafico=50)]]) as consultar:
            historial = service._cargar_historial_7d()
        self.assertIn(self.clave, historial["actividades"])
        self.assertTrue(all("range(start: -7d)" in call.args[0]
                            for call in consultar.call_args_list))


class CacheTests(unittest.TestCase):
    def test_no_bloquea_y_no_duplica_trabajo(self):
        cache = CacheHistorial()
        entro, liberar, termino = Event(), Event(), Event()
        llamadas = []

        def cargar():
            llamadas.append(1)
            entro.set()
            liberar.wait(2)
            return {"ok": True}

        actualizar = cache._actualizar

        def terminado(cargar):
            try:
                actualizar(cargar)
            finally:
                termino.set()

        with patch.object(cache, "_actualizar", terminado):
            try:
                cache.solicitar(cargar)
                self.assertTrue(entro.wait(1))
                for _ in range(10):
                    cache.solicitar(cargar)
                self.assertIsNone(cache.leer()[0])
                self.assertTrue(cache.leer()[1]["en_curso"])
            finally:
                liberar.set()
                self.assertTrue(termino.wait(1))
        self.assertEqual(llamadas, [1])
        self.assertEqual(cache.leer()[0], {"ok": True})
        cache.solicitar(cargar)
        self.assertEqual(llamadas, [1])

    def test_fallo_conserva_snapshot_y_reintenta(self):
        cache = CacheHistorial()
        with patch("microservicios.olt.caidas.cache.monotonic", return_value=100):
            cache._actualizar(lambda: {"ok": True})
        with patch("microservicios.olt.caidas.cache.monotonic", return_value=110), \
             self.assertLogs("microservicios.olt.caidas.cache", level="ERROR"):
            cache._actualizar(lambda: (_ for _ in ()).throw(RuntimeError("Influx")))
            self.assertEqual(cache.leer()[0], {"ok": True})
            self.assertEqual(cache.leer()[1]["estado"], "ERROR")
            self.assertEqual(cache._proximo, 140)
        with patch("microservicios.olt.caidas.cache.monotonic", return_value=1001):
            self.assertIsNone(cache.leer()[0])


if __name__ == "__main__":
    unittest.main()
