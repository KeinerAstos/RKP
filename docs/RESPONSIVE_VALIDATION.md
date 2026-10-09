# Corrección responsive y rueda — 9 de octubre de 2026

Rama: `codex/responsive-table-wheel`. Base: `cc3a880`, idéntica a `origin/main` tras `git fetch origin`. Ambos historiales indicados en el documento están integrados. Los cambios locales previos de INIT, backend, microservicios, CSV, backups y graphify se conservaron; el commit de esta corrección excluye ese trabajo. En `cmts-inits.php` se preparó exclusivamente el cambio de assets en el índice de Git, manteniendo las modificaciones locales de exportación en el archivo de trabajo.

Se eliminó el bloqueo de altura del dashboard y HFC, y la columna fantasma entre 641 y 860 px. La vista general distribuye paneles según un contenedor de contenido de 1200 px, contando el espacio usado por la navegación. El footer participa en el flujo. Las regiones de tablas desplazan localmente y conservan encabezados sticky; temperatura y pérdida conservan el máximo de tres filas. El cuerpo del modal HFC puede desplazarse completo en ventanas bajas. Los assets modificados tienen versión en sus referencias.

`table-wheel.js` conserva la rueda vertical nativa cuando hay filas desbordadas y los gestos con deltaX. Traduce Shift + rueda y la rueda vertical cuando solo hay desbordamiento horizontal. Cancela el evento únicamente si el navegador efectivamente mueve scrollLeft, incluyendo el caso de gutters que sobreestiman el rango. Al borde deja continuar el evento. Excluye Ctrl/Meta, controles editables y selects enfocados. No activa ni cambia el autoscroll de Monitoreo general.

## Evidencia y alcance

Fixtures identificadas como FIXTURE, aisladas de todas las API de backend y de recursos externos en las pruebas nuevas. No se ejecutaron consultas operativas ni se escribieron CSV. No había captura original adjunta disponible; la reproducción se hizo sobre el código actual.

| Prueba | Cobertura | Evidencia |
| --- | --- | --- |
| Geometría Chrome y Edge | 11 rutas; 31 tamaños; sidebar visible/colapsado desde 1024 px | `artifacts/responsive/results.json`, `artifacts/responsive-edge/results.json` |
| Tamaños | Todos los 25 del documento, más 1023/1025, 860/861 y 640/641 px | Lista exacta en `tests/responsive_wheel.cjs` y resultados JSON |
| Rueda real | Vertical interna, Shift horizontal, deltaX, horizontal-only, ambos bordes, tabla sin overflow | `page.mouse.wheel()` en Chrome y Edge |
| Zoom | Ctrl + rueda sintético sin cancelación por el controlador | Zoom real 125/150/200 % pendiente; viewport reducido no se presenta como zoom |
| Estados de filas | 0/1/3/20/160 filas, 11 rutas, tres viewports | 165 casos en `artifacts/responsive/states.json` |
| Teclado | Flecha desplaza región enfocada; encabezado sigue sticky; drawer cierra con Escape y restaura foco | Pruebas nuevas |
| INIT funcional | 20 casos de geometría, 30 de tablas de otros módulos; filtros, orden, error expandible, actualizar, probar y descarga CSV | `tests/cmts_inits_visual.cjs`, `artifacts/init-validation/geometry.json` |
| Revisión visual | Vista general 1920×1080, 1366×680, 1280×600, 390×844; INIT escritorio/móvil; modal OLT 1280×600 | PNG en directorios de artifacts |

Rutas: index, hfc, intermitencias, agotamiento-ip, puertos-docsis, recursos-zte, cmts-inits, autofind-hw, onts, troncales-pon y configuracion. Las rutas aún sin tablas mantienen sus estados actuales; las pruebas no añaden funcionalidades.

Limitaciones: quedan pendientes zoom real y dispositivos físicos, pruebas funcionales exhaustivas de cada módulo, foco/cierre de todos los modales y gráficos alimentados por datos reales. El modal OLT se inspeccionó estructuralmente con lista larga y dependencias externas bloqueadas; no se afirma haber validado sus gráficos. Carga, error y sin coincidencias tienen evidencia en las fixtures/prueba INIT; no se validaron todas sus combinaciones en cada ruta. No se publicó ni mezcló en main.

## Repetir

Desde la raíz, con PHP y Playwright instalados:

```powershell
C:\xampp\php\php.exe -S 127.0.0.1:8765 -t .
# En otra terminal:
$env:PLAYWRIGHT_MODULE='C:\Users\UITMICRO\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules\playwright'
$env:CHROMIUM_PATH='C:\Program Files\Google\Chrome\Application\chrome.exe'
node tests/responsive_wheel.cjs
node tests/responsive_states.cjs
$env:RKP_VISUAL_OUTPUT='artifacts/init-validation'
New-Item -ItemType Directory -Force $env:RKP_VISUAL_OUTPUT
node tests/cmts_inits_visual.cjs
$env:CHROMIUM_PATH='C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
$env:RKP_VISUAL_OUTPUT='artifacts/responsive-edge'
node tests/responsive_wheel.cjs
git diff --check
```

Las nuevas pruebas bloquean las API. La prueba existente de INIT responde con fixtures y sus botones solo generan solicitudes interceptadas.

## Revisar y aplicar conservando trabajo local

Revisar el commit de la rama con `git show codex/responsive-table-wheel`. Antes de integrarlo en otra copia, guardar su trabajo local en un commit propio o stash identificado, actualizar las referencias y usar merge/PR. Si existe conflicto en INIT, combinar las referencias de assets con los botones/exportaciones actuales. No sustituir archivos completos ni aplicar versiones históricas. Los archivos locales ajenos a esta corrección permanecen sin commit en esta copia.

Las capturas y resultados son artefactos locales; no forman parte del commit. Para comprobación de parche, generar `git diff --binary --output=responsive.patch origin/main...codex/responsive-table-wheel` y ejecutar `git apply --check responsive.patch` en la copia de destino antes de aplicarlo.
