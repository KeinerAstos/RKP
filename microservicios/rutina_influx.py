"""Un productor, resultados persistentes, consultas secuenciales por ciclo."""
import argparse
import importlib
import time
from datetime import datetime
from microservicios.influx_resultados import Candado, ahora, guardar, leer
from microservicios.entorno import env

# nombre, modulo, funcion, argumentos, intervalo por defecto en minutos
JOBS = [
    ('zte_licencias', 'olt.recursos_zte', 'obtener_licencias_bajas', (), 1440),
    ('olt_temperatura', 'olt.temperatura', 'obtener_temperatura_actual', (), 0.5),
    ('olt_perdida_latencia', 'olt.perdida_latencia', 'obtener_perdida_latencia_actual', (), 0.5),
    ('olt_saturacion_actual', 'olt.saturacion', 'obtener_saturacion_actual', (), 0.5),
    ('olt_crc_actual', 'olt.crc', 'obtener_crc_actual', (), 0.5),
    ('olt_caidas_actuales', 'olt.caidas', 'obtener_caidas_actuales', (), 0.5),
    ('cmts_intermitencias', 'cmts.intermitencias', 'obtener_intermitencias_actuales', (), 420),
    ('cmts_duplicados', 'cmts.puertos_duplicados', 'obtener_puertos_duplicados_actuales', (), 420),
    ('olt_saturacion', 'olt.saturacion', 'obtener_saturacion', (), 30),
    ('olt_crc', 'olt.crc', 'obtener_crc', (), 30),
    ('olt_correlacion', 'olt.correlacion', 'obtener_correlacion', (), 30),
    *[(f'olt_{tipo}_{d}', 'olt.caidas', 'obtener_' + tipo, (f'-{d}d',), 420 if tipo == 'intermitencias' else 30)
      for d in (2, 4, 7) for tipo in ('caidas', 'intermitencias')],
    ('cmts_saturacion', 'cmts.saturacion', 'actualizar_saturacion', (), 1440),
]

def ejecutar(forzar=False):
    errores = 0
    with Candado():
        for nombre, modulo, funcion, argumentos, minutos in JOBS:
            previo = leer(nombre)
            intervalo = float(env('INFLUX_' + nombre.upper() + '_CADA_MINUTOS', str(minutos)))
            if intervalo < 0.5:
                raise ValueError('Intervalo debe ser >= 0.5: ' + nombre)
            if previo and not forzar:
                edad = time.time() - datetime.fromisoformat(previo['generado_en']).timestamp()
                if edad < intervalo * 60:
                    continue
            inicio = time.monotonic()
            guardar(nombre + '_estado', {'estado': 'procesando', 'iniciado_en': ahora()})
            try:
                service = importlib.import_module('microservicios.' + modulo + '.service')
                if nombre == 'olt_caidas_actuales':
                    # Completar verificación de 7d antes del cálculo: este proceso
                    # termina al finalizar el ciclo y no debe dejar un hilo pendiente.
                    service._cache_historial_7d._actualizar(service._cargar_historial_7d)
                resultado = getattr(service, funcion)(*argumentos)
                guardar(nombre, {'generado_en': ahora(), 'data': resultado})
                guardar(nombre + '_estado', {'estado': 'listo', 'finalizado_en': ahora()})
                print(nombre, 'OK', round(time.monotonic() - inicio, 1), 's', flush=True)
            except Exception as exc:
                errores += 1
                guardar(nombre + '_estado', {'estado': 'error', 'finalizado_en': ahora(), 'error': str(exc)})
                if nombre == 'cmts_saturacion':
                    from microservicios.cmts.saturacion.cache import leer_estado, guardar_estado
                    guardar_estado({**leer_estado(), 'estado': 'error', 'error': str(exc), 'finalizado_en': ahora()})
                print(nombre, 'ERROR', str(exc), flush=True)
    return 2 if errores else 0

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--ciclo', action='store_true')
    p.add_argument('--forzar', action='store_true')
    a = p.parse_args()
    try:
        return ejecutar(a.forzar)
    except RuntimeError as exc:
        print(exc, flush=True)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
