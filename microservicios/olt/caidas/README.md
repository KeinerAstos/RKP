# Puertos down: consulta de 4 días y verificación de 7 días

`GET /api/olt/caidas/actuales` conserva las consultas principales de
30 minutos (estado reciente) y 4 días (última muestra y tráfico positivo).
Una caché Python por proceso amplía la comprobación a 7 días.

La primera petición inicia un hilo de fondo y responde sin esperar esa
comprobación. Las siguientes peticiones usan su resultado. Al transcurrir
5 minutos, la siguiente petición inicia una actualización; sólo puede haber
una actualización en curso por proceso. El historial queda en memoria y se
reconstruye al reiniciar la API; no requiere nuevas dependencias ni tareas
programadas. Si no hay peticiones, no se realizan consultas adicionales.

La consulta de fondo descubre últimas muestras de todos los puertos en 7 días
y busca el último tráfico positivo sólo para los puertos con cero o sin
muestras recientes, en lotes secuenciales de hasta 100 puertos.

## Resultado

- Cero reciente y tráfico positivo en 4 días o en la caché de 7 días:
  `CAIDO_ACTUAL`, con duración desde el último tráfico positivo. Esto permite
  que GKP muestre también caídas de 5 o 6 días; mantiene su filtro actual.
- Última muestra con antigüedad mayor a 15 minutos, hasta 7 días:
  `SIN_MUESTRAS_RECIENTES`. No se presenta como caída actual en GKP.
- Cero reciente sin tráfico positivo en la verificación de 7 días:
  `CAIDO_SIN_FECHA`, clasificación `SIN_ACTIVIDAD_7_DIAS`.
- Sin verificación disponible para el puerto:
  clasificación `PENDIENTE_VERIFICACION`.

Sin actividad no demuestra que el puerto esté apagado administrativamente:
para confirmar eso se necesita su estado administrativo/operativo (SNMP/CLI).
El tráfico positivo reciente siempre prevalece sobre los datos de la caché.
Las muestras y actividades que salen de la ventana de 7 días se descartan.

Los campos existentes se conservan. Se agregan `clasificacion`,
`origen_historial` (`4_dias` o `cache_7_dias`), `verificado_7_dias` y el resumen
`verificacion_7_dias` de la caché. La primera respuesta puede estar pendiente;
la comprobación aparece en las peticiones posteriores, tras completar Influx.

Si la consulta de fondo falla, se conserva el último resultado completo y se
permite reintentar en la siguiente petición después de 30 segundos. Una caché
de más de 15 minutos no se usa. Un fallo nunca se interpreta como historial
vacío. Las consultas principales conservan su manejo de errores habitual.
Con varios procesos Uvicorn, cada proceso mantiene su propia caché/hilo.

## Validación

Desde la raíz de RKP:

```powershell
py -m unittest discover -s tests -v
```

Las pruebas simulan Influx: caída con actividad hace 5 días, ausencia de
reportes hace 6 días, recuperación, historial fuera de 7 días, caché fría,
fallos, caducidad y exclusión de consultas de fondo duplicadas. Tras aplicar
los cambios, reiniciar el proceso de la API que sirve `microservicios.app:app`.
