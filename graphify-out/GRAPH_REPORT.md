# Graph Report - RKP  (2026-10-09)

## Corpus Check
- 174 files · ~457,745 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 23 file(s) not represented in the graph (top: .css 8, .toml 4, .csv 4)

## Summary
- 2044 nodes · 4389 edges · 155 communities (109 shown, 8 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 124 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `4bfffcd6`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- renderDesignVisual
- BACKUP_CMTS_MENU_5DIAS_20261009_101544_189823/microservicios/cmts/inits/router.py
- topologias/service.py
- modern-screenshot.umd.js
- cmts/saturacion/service.py
- initPageChat
- el
- perdida_latencia/service.py
- inits_cmts.py
- showToast
- casos_helix/service.py
- handleManualEditActivity
- caidas/service.py
- grafana_proxy/app.py
- microservicios/app.py
- resolveLiveInjectionAnchor
- HistorialTests
- Extract Flow
- createLiveBrowserDomHelpers
- HelixWorker
- crc/service.py
- casos_helix/router.py
- createLiveBrowserSessionState
- hfc.js
- setLiveState
- Responsive Design
- intermitencias/service.py
- consultar_flux_temp
- Components
- gkp.js
- temperatura.js
- olt/saturacion/service.py
- obtener_licencias_bajas
- MicroserviceClient
- iniciar_microserviciosypuente.py
- SKILL.md
- mountSvelteComponentVariant
- onboard.md
- consultar_influx.py
- initGlobalBar
- new-work.md
- MicroserviceClient
- onAnnotDown
- live-browser-ignores.js
- impeccable
- scrollToTop
- The Toolkit
- perdida_latencia.js
- puertos_docsis/queries.py
- animate.md
- live.md
- Handle `generate`
- Generate Report
- resumeSession
- New visual work
- optimize.md
- live-browser.js
- Scan mode (approach C: auto-extract, then confirm descriptive language)
- critique.md
- Simplify the Design
- Hardening Dimensions
- Product
- clarify.md
- Nielsen's 10 Heuristics
- Generate Combined Critique Report
- document.md
- polish.md
- quieter.md
- Init flow
- Common Cognitive Load Violations
- iOS platform
- Operate mode depth (and Read notes)
- Shape
- puertos_docsis/router.py
- adapt.native.md
- Android platform
- colorize.md
- Persona-Based Design Testing
- test_cmts_inits.py
- live-setup.md
- WorkerTests
- Generate Report
- Cognitive Load Assessment
- Impeccable Asset Producer
- Impeccable Finish Reviewer
- Impeccable Manual Edit Applier
- Diagnostic Scan
- microservicios/cmts/inits/router.py
- $impeccable hooks
- Visualize: Direction Comps & Asset Production
- Impeccable Documenter
- bootstrap.php
- Heuristics Scoring Guide
- README.md
- Puertos down: consulta de 4 días y verificación de 7 días
- frontend/assets/js/cmts-inits.js
- captureElementToBlob
- gkp-casos-helix.js
- .test_equipment_query_retains_open_task_with_closed_parent
- claim_cycle
- correlacion/service.py
- BACKUP_CMTS_MENU_5DIAS_20261009_101544_189823/frontend/assets/js/cmts-inits.js
- temperatura/service.py
- config.py
- cmts_inits_visual.cjs
- doctor.md
- BACKUP_CMTS_MENU_5DIAS_20261009_101544_189823/microservicios/cmts/inits/export_excel.py
- probar_topologias.py
- probar_vsd_jpg.py
- consultar_mysql
- scopeCssBlock
- responsive_wheel.cjs
- table-wheel.js
- __init__.py
- test_query_connection_error_has_stage_and_redacts_password
- responsive_states.cjs
- Corrección responsive y rueda — 9 de octubre de 2026

## God Nodes (most connected - your core abstractions)
1. `setLiveState()` - 32 edges
2. `resumeSession()` - 32 edges
3. `connectSSE()` - 31 edges
4. `showToast()` - 30 edges
5. `initGlobalBar()` - 29 edges
6. `el()` - 29 edges
7. `handleKeyDown()` - 27 edges
8. `cleanup()` - 26 edges
9. `buildInsertConfigureRow()` - 26 edges
10. `injectSvelteComponentsFromManifest()` - 26 edges

## Surprising Connections (you probably didn't know these)
- `EquipoScopeIssue4Tests` --uses--> `HelixWorker`  [INFERRED]
  tests/test_casos_helix_async.py → microservicios/olt/casos_helix/worker.py
- `ConfigurationAndOracleMockTests` --uses--> `SolicitudLote`  [INFERRED]
  tests/test_casos_helix_async.py → microservicios/olt/casos_helix/router.py
- `WorkerTests` --uses--> `HelixWorker`  [INFERRED]
  tests/test_casos_helix_async.py → microservicios/olt/casos_helix/worker.py
- `ConfigurationAndOracleMockTests` --uses--> `Settings`  [INFERRED]
  tests/test_casos_helix_async.py → microservicios/config.py
- `CacheTests` --uses--> `CacheHistorial`  [INFERRED]
  tests/test_olt_caidas_historial.py → microservicios/olt/caidas/cache.py

## Import Cycles
- None detected.

## Communities (155 total, 8 thin omitted)

### Community 0 - "renderDesignVisual"
Cohesion: 0.08
Nodes (39): buildCollapsible(), buildColorModels(), buildDesignHeader(), buildListHtml(), buildRadiiModels(), buildTypographyModels(), cssSafe(), designEmptyMessage() (+31 more)

### Community 1 - "BACKUP_CMTS_MENU_5DIAS_20261009_101544_189823/microservicios/cmts/inits/router.py"
Cohesion: 0.13
Nodes (25): actual(), estado(), exportar(), exportar_excel(), stream(), historico(), get, API del monitoreo INIT; GET sólo consulta CSV ya publicados. (+17 more)

### Community 2 - "topologias/service.py"
Cohesion: 0.09
Nodes (62): FileResponse, archivo(), _buscar(), buscar_global(), ftto(), health(), huawei(), imagen() (+54 more)

### Community 3 - "modern-screenshot.umd.js"
Cohesion: 0.09
Nodes (55): ae(), be(), bt(), Ce(), s(), Ct(), de(), dt() (+47 more)

### Community 4 - "cmts/saturacion/service.py"
Cohesion: 0.09
Nodes (47): BackgroundTasks, _guardar_atomico(), guardar_estado(), guardar_saturacion(), _leer(), leer_estado(), leer_saturacion(), Any (+39 more)

### Community 5 - "initPageChat"
Cohesion: 0.08
Nodes (51): agentHasWorkInFlight(), armPageChatForTyping(), attachSteerFocusDebug(), attachSteerFocusGuard(), buildSteerProcessingDots(), buildSteerQueueHint(), clearSteerAwaitTimer(), clearSteerFocusRecoverTimer() (+43 more)

### Community 6 - "el"
Cohesion: 0.07
Nodes (55): actionLabel(), applyConfigureBarChrome(), bindConfigureCountPillTooltip(), bindConfigureInlineControlHover(), bindConfigureModifierPillHover(), buildConfigureActionControl(), buildConfigureCountControl(), buildConfigureRow() (+47 more)

### Community 7 - "perdida_latencia/service.py"
Cohesion: 0.25
Nodes (8): Consulta SQL de las lecturas actuales de gestión., perdida_latencia_actual(), get, Rutas HTTP de pérdida y latencia OLT., _numero_finito(), obtener_perdida_latencia_actual(), Any, Normalización de lecturas actuales de pérdida y latencia OLT.

### Community 8 - "inits_cmts.py"
Cohesion: 0.19
Nodes (24): _append_history(), apply_retention(), data_dir(), export_rows(), get_progress(), history(), _in_range(), inventory() (+16 more)

### Community 9 - "showToast"
Cohesion: 0.10
Nodes (26): abandonForeignSession(), captureAndEmit(), checkpointPayload(), compileShader(), copyToClipboard(), discardOrphanedSession(), enterRecoveryWaitingForAnchor(), injectVariantsFromSource() (+18 more)

### Community 10 - "casos_helix/service.py"
Cohesion: 0.21
Nodes (24): _consultar_equipo_asociaciones(), consultar_olt(), consultar_olt_equipo(), _consultar_puertos_asociaciones(), add(), _deadline_check(), _fetch(), _has_explicit_location() (+16 more)

### Community 11 - "handleManualEditActivity"
Cohesion: 0.18
Nodes (25): clearStoredManualApplyState(), fetchPendingCount(), handleManualEditActivity(), hidePendingApplyDock(), manualApplyLoadingText(), manualApplyStateKey(), manualEditEventForCurrentPage(), numberOrNull() (+17 more)

### Community 12 - "caidas/service.py"
Cohesion: 0.12
Nodes (35): _escapar_flux(), obtener_caidas_flux(), obtener_estado_actual_flux(), obtener_ultima_actividad_flux(), obtener_ultima_muestra_conocida_flux(), Consultas Flux para detectar caídas de puertos OLT por tráfico., Obtiene las últimas muestras de tráfico recientes. Se revisan 30 minutos para…, Obtiene la última muestra conocida de cada puerto. Sirve para detectar puertos… (+27 more)

### Community 13 - "grafana_proxy/app.py"
Cohesion: 0.21
Nodes (20): api_route, _configuration_ready(), _ensure_authenticated_locked(), _is_login_redirect(), _login_locked(), proxy(), proxy_health(), _proxy_locked() (+12 more)

### Community 14 - "microservicios/app.py"
Cohesion: 0.18
Nodes (15): exception_handler, JSONResponse, error_http(), error_no_controlado(), error_validacion(), health(), lifespan(), Exception (+7 more)

### Community 15 - "resolveLiveInjectionAnchor"
Cohesion: 0.16
Nodes (19): buildSvelteExpressionTextMap(), buildSveltePropValuesFromLiveElement(), buildSveltePropValuesV2(), cloneWithoutElements(), collectTextNodes(), collectVisibleTexts(), cssEscapeIdent(), elementMatchesOriginalMarkup() (+11 more)

### Community 16 - "HistorialTests"
Cohesion: 0.14
Nodes (5): CacheHistorial, Caché de historial de 7 días; las peticiones nunca esperan su consulta., CacheTests, HistorialTests, Verificación del historial extendido sin acceso a Influx real.

### Community 17 - "Extract Flow"
Cohesion: 0.25
Nodes (7): Extract Flow, Step 1: Discover the Design System, Step 2: Identify Patterns, Step 3: Plan Extraction, Step 4: Extract & Enrich, Step 5: Migrate, Step 6: Document

### Community 18 - "createLiveBrowserDomHelpers"
Cohesion: 0.16
Nodes (11): createLiveBrowserDomHelpers(), cssId(), liveUiRoot(), makeFrozenAnchor(), own(), pickable(), rectIsUsableAnchor(), uiAppend() (+3 more)

### Community 19 - "HelixWorker"
Cohesion: 0.16
Nodes (8): get_worker(), HelixWorker, JobState, Any, Cola acotada y estado publicable para consultas Helix lentas., Un único hilo Oracle por proceso y un límite explícito de OLT en espera., start_worker(), stop_worker()

### Community 20 - "crc/service.py"
Cohesion: 0.17
Nodes (17): _metricas_crc_flux(), obtener_crc_actual_flux(), obtener_crc_flux(), Consultas Flux para errores CRC de puertos OLT., Devuelve muestras superiores a diez errores CRC por segundo., Filtra el umbral despues de seleccionar la ultima muestra de cada puerto., crc(), crc_actual() (+9 more)

### Community 21 - "casos_helix/router.py"
Cohesion: 0.18
Nodes (15): BaseModel, casos_abiertos(), casos_abiertos_lote(), _legacy_result(), Any, get, post, Rutas de estado y lote para las consultas OLT de Helix. (+7 more)

### Community 22 - "createLiveBrowserSessionState"
Cohesion: 0.21
Nodes (15): createLiveBrowserSessionState(), clearHandled(), clearScrollY(), clearSession(), isHandled(), loadSession(), markHandled(), nextCheckpointRevision() (+7 more)

### Community 23 - "hfc.js"
Cohesion: 0.24
Nodes (16): changeDays(), changePanel(), checkUpdateStatus(), compareCriticality(), eyeButton(), formatUpdatedAt(), grafanaUrl(), load() (+8 more)

### Community 24 - "setLiveState"
Cohesion: 0.11
Nodes (57): applyEditing(), beginNewLiveConfiguration(), cancelEditing(), cancelEditingToPicking(), cancelInsertConfigure(), cleanup(), cleanupAcceptedSession(), clearAnnotations() (+49 more)

### Community 25 - "Responsive Design"
Cohesion: 0.08
Nodes (25): Assess Adaptation Challenge, Breakpoints: Content-Driven, Content Adaptation, Desktop Adaptation (Mobile → Desktop), Detect Input Method, Not Just Screen Size, Email Adaptation (Web → Email), Implement Adaptations, Layout Adaptation Patterns (+17 more)

### Community 26 - "intermitencias/service.py"
Cohesion: 0.19
Nodes (13): obtener_intermitencias_flux(), Consultas Flux para detectar intermitencias HFC., Detecta caídas de puertos HFC usando cm_registrados. Una caída se confirma…, intermitencias_actual(), get, Rutas HTTP de intermitencias HFC., _numero_entero(), obtener_intermitencias_actuales() (+5 more)

### Community 27 - "consultar_flux_temp"
Cohesion: 0.13
Nodes (22): InfluxDBClient, obtener_puertos_duplicados_flux(), Consultas Flux para detectar nodos en puertos CMTS duplicados., Obtiene la ubicacion mas reciente de cada descripcion, CMTS y puerto., puertos_duplicados_actual(), get, Rutas HTTP de nodos asociados a multiples puertos CMTS., normalizar_descripcion() (+14 more)

### Community 28 - "Components"
Cohesion: 0.07
Nodes (27): Buttons, Cards / Containers, Chips, Colors, Components, Design System: NOC BOA, Do:, Do's and Don'ts (+19 more)

### Community 29 - "gkp.js"
Cohesion: 0.26
Nodes (14): alertIdentity(), closeFtthModal(), connection(), formatValue(), ftthGrafanaUrl(), load(), loadFtthFrame(), monitoring() (+6 more)

### Community 30 - "temperatura.js"
Cohesion: 0.33
Nodes (11): badgeClass(), closeTemperatureModal(), formatTemperature(), loadTemperature(), loadTemperatureChart(), openTemperatureModal(), renderTemperature(), setTemperatureRange() (+3 more)

### Community 31 - "olt/saturacion/service.py"
Cohesion: 0.15
Nodes (20): _metricas_saturacion_flux(), obtener_saturacion_actual_flux(), obtener_saturacion_flux(), Consultas Flux para saturacion de puertos OLT., Devuelve la secuencia de muestras con saturacion superior al 70 %., Filtra el umbral despues de seleccionar la ultima muestra de cada puerto., get, Rutas HTTP de saturacion OLT. (+12 more)

### Community 32 - "obtener_licencias_bajas"
Cohesion: 0.29
Nodes (9): licencias_bajas(), get, Rutas HTTP de recursos ZTE., _fecha_serializable(), _numero_finito(), obtener_licencias_bajas(), Any, Normalización de recursos ZTE con baja disponibilidad. (+1 more)

### Community 34 - "iniciar_microserviciosypuente.py"
Cohesion: 0.58
Nodes (9): esperar_puerto(), iniciar_tunel(), iniciar_tunel_oracle(), iniciar_uvicorn(), main(), matar(), nueva_consola_kwargs(), puerto_abierto() (+1 more)

### Community 35 - "SKILL.md"
Cohesion: 0.10
Nodes (15): Before you finish, Scope is sovereign, The amplification, The skeleton test, Why it reads flat, Craft floor, Refuse, Verify (+7 more)

### Community 36 - "mountSvelteComponentVariant"
Cohesion: 0.15
Nodes (21): acceptedDomAlreadyClean(), applyOriginalAttrsToSvelteAnchor(), clearHandledWrapperReloadStamp(), commitAcceptedSvelteComponentToDom(), componentModuleCandidates(), deferredRecoverySuperseded(), describeMountFailure(), detectDevServerBase() (+13 more)

### Community 37 - "onboard.md"
Cohesion: 0.09
Nodes (22): Assess Onboarding Needs, Context Over Ceremony, Contextual Help, Design Onboarding Experiences, Documentation & Help, Empty State Design, Feature Discovery & Adoption, Guided Tours & Walkthroughs (+14 more)

### Community 38 - "consultar_influx.py"
Cohesion: 0.36
Nodes (10): ejecutar_caidas(), ejecutar_intermitencias(), imprimir_resultado(), main(), mostrar_menu(), Any, Herramienta interactiva para probar manualmente los servicios OLT., seleccionar_periodo_caidas() (+2 more)

### Community 39 - "initGlobalBar"
Cohesion: 0.08
Nodes (41): agentStatusText(), barPaletteForTheme(), brandMarkSvg(), buildParamsPanel(), cursorForInsertAxis(), designPanelCss(), detectPageTheme(), ensureAgentPollTooltip() (+33 more)

### Community 40 - "new-work.md"
Cohesion: 0.13
Nodes (14): Recommended Actions, Craft (deprecated alias), Apply, Live-mode signature params, Set the spatial thesis, Two isolated assessments, Verify, Visitor mode (+6 more)

### Community 42 - "onAnnotDown"
Cohesion: 0.20
Nodes (17): beginEditPin(), buildAnnotationsForCapture(), buildPinElement(), cancelEditingPin(), clampPlaceholderSize(), finalizeEditingPin(), initAnnotOverlay(), localCoords() (+9 more)

### Community 43 - "live-browser-ignores.js"
Cohesion: 0.52
Nodes (6): globToRegex(), matchesScope(), normalizeIgnoreRule(), normalizeIgnoreValue(), pageCandidates(), resolveDetectIgnores()

### Community 44 - "impeccable"
Cohesion: 0.60
Nodes (5): impeccable script, check_download(), fetch_url(), probe_ok(), setup_help()

### Community 45 - "scrollToTop"
Cohesion: 0.60
Nodes (4): frame(), hold(), resetAll(), scrollToTop()

### Community 46 - "The Toolkit"
Cohesion: 0.10
Nodes (20): Animate complex properties, Assess What "Extraordinary" Means Here, For data-heavy interfaces, For functional UI, For performance-critical UI, For visual/marketing surfaces, Implement with Discipline, Interact with the device (+12 more)

### Community 47 - "perdida_latencia.js"
Cohesion: 0.83
Nodes (3): formatNumber(), load(), render()

### Community 79 - "animate.md"
Cohesion: 0.12
Nodes (14): Accessibility and control, Choose material by meaning, Find the job, Implement to the runtime, Set the motion thesis, Timing and easing, Verify, Visitor mode (+6 more)

### Community 80 - "live.md"
Cohesion: 0.12
Nodes (15): Cleanup, Exit, First-time setup, Handle `accept`, Handle `discard`, Handle fallback, Handle `manual_edit_apply`, Handle `prefetch` (+7 more)

### Community 81 - "Handle `generate`"
Cohesion: 0.12
Nodes (16): 1. Read the screenshot (if present), 2. Wrap the element, 3. Load the action's reference, 4. Plan three variants: identity first, then mode, then axes, 5. Apply the freeform prompt (if present), 6. Deliver variants, 7. Parameters (composition-sized, 0-4 per variant), 8. Signal done (+8 more)

### Community 82 - "Generate Report"
Cohesion: 0.13
Nodes (14): 1. Accessibility (A11y), 2. Performance, 3. Theming, 4. Responsive Design, 5. Implementation Integrity (CRITICAL), Audit Health Score, Detailed Findings by Severity, Diagnostic Scan (+6 more)

### Community 83 - "resumeSession"
Cohesion: 0.06
Nodes (83): abortSvelteComponentInjection(), applyParamDefaults(), applyParamValue(), applyPlaceholderDimensions(), applySavedSessionMeta(), clampVariantIndex(), clearHandled(), clearSession() (+75 more)

### Community 84 - "New visual work"
Cohesion: 0.14
Nodes (14): 1. Decide what is already true, 2. Ask what will change the work, 3. Choose the right amount of invention, 4. Commit the world, 5. Record the decision, 6. Build with full commitment, 7. Inspect and finish, Both paths (+6 more)

### Community 85 - "optimize.md"
Cohesion: 0.14
Nodes (13): Animation Performance, Assess Performance Issues, Core Web Vitals Optimization, Cumulative Layout Shift (CLS < 0.1), Interaction to Next Paint (INP < 200ms), Largest Contentful Paint (LCP < 2.5s), Loading Performance, Network Optimization (+5 more)

### Community 86 - "live-browser.js"
Cohesion: 0.04
Nodes (90): addManualContextText(), applyGlobalBarLabelState(), applyPlaceholderSizingStyles(), bindEditBadgeProxy(), buildInsertPlaceholderSnapshotFromDom(), buildLocatorForLeaf(), buildPickedAnchorSnapshot(), buildPlaceholderResizeHandles() (+82 more)

### Community 87 - "Scan mode (approach C: auto-extract, then confirm descriptive language)"
Cohesion: 0.15
Nodes (13): Component translation rules, Narrative mapping, Scan mode (approach C: auto-extract, then confirm descriptive language), Schema, Step 1: Find the design assets, Step 2: Auto-extract what can be auto-extracted, Step 2b: Stage the frontmatter, Step 3: Ask the user for qualitative language (+5 more)

### Community 88 - "critique.md"
Cohesion: 0.17
Nodes (11): Action Summary, Ask the User, Assessment A: Design Review, Assessment B: Detector + Browser Evidence, Assessment Orchestration, Deliver the Report, Hard Invariants, Persist the Snapshot (+3 more)

### Community 89 - "Simplify the Design"
Cohesion: 0.17
Nodes (11): Assess Current State, Code Simplification, Content Simplification, Document Removed Complexity, Information Architecture, Interaction Simplification, Layout Simplification, Plan Simplification (+3 more)

### Community 90 - "Hardening Dimensions"
Cohesion: 0.17
Nodes (11): Accessibility Resilience, Assess Hardening Needs, Edge Cases & Boundary Conditions, Error Handling, Hardening Dimensions, Input Validation & Sanitization, Internationalization (i18n), Performance Resilience (+3 more)

### Community 91 - "Product"
Cohesion: 0.17
Nodes (11): Accessibility & Inclusion, Brand Commitments, Capabilities and Constraints, Evidence on Hand, Operating Context, Platform, Positioning, Product (+3 more)

### Community 92 - "clarify.md"
Cohesion: 0.18
Nodes (10): Actions and navigation, Audit the language, Errors and permissions, Forms, Help and instructional text, Loading, empty, and success states, Rewrite by function, Set the message hierarchy (+2 more)

### Community 93 - "Nielsen's 10 Heuristics"
Cohesion: 0.18
Nodes (11): 10. Help and Documentation, 1. Visibility of System Status, 2. Match Between System and Real World, 3. User Control and Freedom, 4. Consistency and Standards, 5. Error Prevention, 6. Recognition Rather Than Recall, 7. Flexibility and Efficiency of Use (+3 more)

### Community 94 - "Generate Combined Critique Report"
Cohesion: 0.18
Nodes (11): Design Health Score, Design Specificity Verdict, Generate Combined Critique Report, Minor Observations, Overall Impression, Persona Red Flags, Priority Issues, Questions to Consider (+3 more)

### Community 95 - "document.md"
Cohesion: 0.18
Nodes (10): Pitfalls, Seed mode, Step 1: Route through new-work's workshop, Step 2: Write seed DESIGN.md, Step 3: Confirm, Style guidelines, The frontmatter: token schema, The markdown body: eight sections (canonical order) (+2 more)

### Community 96 - "polish.md"
Cohesion: 0.18
Nodes (10): 1. Establish the system, 2. Gather the evidence, 3. Triage, 4. Polish the whole path, 5. Verify and finish, Color, imagery, and icons, Content and code, Flow and hierarchy (+2 more)

### Community 97 - "quieter.md"
Cohesion: 0.18
Nodes (10): Assess Current State, Color Refinement, Composition Refinement, Motion Reduction, Plan Refinement, Refine the Design, Simplification, Verify Quality (+2 more)

### Community 98 - "Init flow"
Cohesion: 0.20
Nodes (10): Completion gate, Init flow, Step 1: Load current state, Step 2: Explore the project, Step 3: Interview for product truth, Step 4: Write PRODUCT.md, Step 5: Record workflow defaults, Step 6: Wrap up or resume (+2 more)

### Community 99 - "Common Cognitive Load Violations"
Cohesion: 0.22
Nodes (9): 1. The Wall of Options, 2. The Memory Bridge, 3. The Hidden Navigation, 4. The Jargon Barrier, 5. The Visual Noise Floor, 6. The Inconsistent Pattern, 7. The Multi-Task Demand, 8. The Context Switch (+1 more)

### Community 100 - "iOS platform"
Cohesion: 0.22
Nodes (9): Color & materials, Components & controls, iOS platform, Layout & structure, Motion, The iOS slop test, Touch targets, Typography (+1 more)

### Community 101 - "Operate mode depth (and Read notes)"
Cohesion: 0.22
Nodes (9): Color, Components, Layout, Motion, Operate mode depth (and Read notes), Product constraints, Product permissions, The product slop test (+1 more)

### Community 102 - "Shape"
Cohesion: 0.22
Nodes (8): Cadence, Confirm and stop, Phase 1: Discovery interview, Phase 2: Resolve the design direction, Phase 3: Write the brief, Round 1: purpose, people, and outcome, Round 2: material, behavior, and boundaries, Shape

### Community 103 - "puertos_docsis/router.py"
Cohesion: 0.28
Nodes (7): puertos_docsis_actual(), get, Rutas HTTP de puertos DOCSIS., obtener_puertos_docsis_actuales(), Any, Logica de negocio para la consulta de puertos DOCSIS., Devuelve un resultado vacio hasta disponer de la fuente real.

### Community 104 - "adapt.native.md"
Cohesion: 0.25
Nodes (7): Adaptation Strategies, Assess Adaptation Challenge, Implement & Verify, Orientation & foldables, Phone → Tablet (iPad / large screens), Platform → platform (iOS ↔ Android), Web → native (porting a website or web app)

### Community 105 - "Android platform"
Cohesion: 0.25
Nodes (8): Android platform, Color & theming, Components & motion, Layout & structure, The Android slop test, Touch targets, Typography, Verifying the build

### Community 106 - "colorize.md"
Cohesion: 0.25
Nodes (7): Apply at system scale, Audit before choosing, Choose a strategy, Contrast and perception, Live-mode signature params, Verify, Visitor mode

### Community 107 - "Persona-Based Design Testing"
Cohesion: 0.25
Nodes (8): 1. Impatient Power User: "Alex", 2. Confused First-Timer: "Jordan", 3. Accessibility-Dependent User: "Sam", 4. Deliberate Stress Tester: "Riley", 5. Distracted Mobile User: "Casey", Persona-Based Design Testing, Project-Specific Personas, Selecting Personas

### Community 108 - "test_cmts_inits.py"
Cohesion: 0.11
Nodes (24): FastAPI, _atomic_csv(), now(), parse(), Valida filas INIT y total explícito del CMTS; nunca cuenta cabeceras., read_csv(), validate_output(), _with_delta() (+16 more)

### Community 109 - "live-setup.md"
Cohesion: 0.25
Nodes (7): append-arrays, append-string, Config drift, Consent prompt (use this phrasing), CSP detection (first-time only), Troubleshooting, Write the config

### Community 111 - "WorkerTests"
Cohesion: 0.29
Nodes (3): esperar(), WorkerTests, query()

### Community 112 - "Generate Report"
Cohesion: 0.29
Nodes (7): Audit Health Score, Detailed Findings by Severity, Executive Summary, Generate Report, Patterns & Systemic Issues, Platform Conformance Verdict, Positive Findings

### Community 113 - "Cognitive Load Assessment"
Cohesion: 0.29
Nodes (7): Cognitive Load Assessment, Cognitive Load Checklist, Extraneous Load: Bad Design, Germane Load: Learning Effort, Intrinsic Load: The Task Itself, The Working Memory Rule, Three Types of Cognitive Load

### Community 114 - "Impeccable Asset Producer"
Cohesion: 0.29
Nodes (6): Core Rule, Decision Comps, Impeccable Asset Producer, Input Contract, Output Contract, The job

### Community 115 - "Impeccable Finish Reviewer"
Cohesion: 0.29
Nodes (6): Checks, in order, Disposition, Impeccable Finish Reviewer, Input Contract, Output Contract, Verdict Pass

### Community 116 - "Impeccable Manual Edit Applier"
Cohesion: 0.29
Nodes (6): Checks, Entry Atomicity, Impeccable Manual Edit Applier, Input Contract, Output Contract, Workflow

### Community 117 - "Diagnostic Scan"
Cohesion: 0.33
Nodes (6): 1. Accessibility (VoiceOver / TalkBack), 2. Performance, 3. Appearance & Theming, 4. Platform Conformance (CRITICAL), 5. Adaptivity, Diagnostic Scan

### Community 118 - "microservicios/cmts/inits/router.py"
Cohesion: 0.14
Nodes (20): tendencia(), trend(), actual(), estado(), exportar(), stream(), historico(), _history_excel_rows() (+12 more)

### Community 119 - "$impeccable hooks"
Cohesion: 0.33
Nodes (6): Constraints, Failure modes, Flow, $impeccable hooks, Routing, Triage findings

### Community 120 - "Visualize: Direction Comps & Asset Production"
Cohesion: 0.33
Nodes (5): After approval: the comp becomes a spec, Generate three compositional options, One approval point, Plates and provenance, Visualize: Direction Comps & Asset Production

### Community 121 - "Impeccable Documenter"
Cohesion: 0.40
Nodes (4): Impeccable Documenter, Input Contract, Output Contract, Workflow

### Community 123 - "bootstrap.php"
Cohesion: 0.50
Nodes (4): datosClient(), jsonResponse(), requireMethod(), MicroserviceClient

### Community 124 - "Heuristics Scoring Guide"
Cohesion: 0.50
Nodes (4): Heuristics Scoring Guide, Issue Severity (P0–P3), Reference Material, Score Summary

### Community 126 - "Puertos down: consulta de 4 días y verificación de 7 días"
Cohesion: 0.50
Nodes (3): Puertos down: consulta de 4 días y verificación de 7 días, Resultado, Validación

### Community 127 - "frontend/assets/js/cmts-inits.js"
Cohesion: 0.27
Nodes (13): downloadExport(), drawTrend(), exportCsv(), exportMenuWorkbook(), loadActual(), loadHistory(), loadStatus(), loadTrend() (+5 more)

### Community 128 - "captureElementToBlob"
Cohesion: 0.14
Nodes (19): averageRgb01(), bufferToBase64(), captureChromeNodes(), captureElementFromRenderedAncestor(), captureElementToBlob(), collectFontCssText(), cssColorToRgb01(), dominantRgb01() (+11 more)

### Community 129 - "gkp-casos-helix.js"
Cohesion: 0.25
Nodes (16): acceptResult(), actualizar(), actualizarEquipos(), celdasEquipo(), chunks(), consultarEquipo(), consultarLotes(), currentCells() (+8 more)

### Community 131 - "claim_cycle"
Cohesion: 0.18
Nodes (17): actualizar(), probar(), post, Response, _run_probe(), _acquire_lock(), claim_cycle(), _pid_alive() (+9 more)

### Community 132 - "correlacion/service.py"
Cohesion: 0.25
Nodes (9): correlacion(), get, Rutas HTTP de correlacion OLT., eventos_se_relacionan(), obtener_correlacion(), Any, Correlacion temporal de saturacion, CRC y caidas OLT., Indica si dos intervalos se cruzan dentro del margen configurado. (+1 more)

### Community 133 - "BACKUP_CMTS_MENU_5DIAS_20261009_101544_189823/frontend/assets/js/cmts-inits.js"
Cohesion: 0.27
Nodes (13): downloadExport(), drawTrend(), exportCsv(), exportExcel(), loadActual(), loadHistory(), loadStatus(), loadTrend() (+5 more)

### Community 134 - "temperatura/service.py"
Cohesion: 0.24
Nodes (9): obtener_temperatura_actual_flux(), Consulta de temperatura actual por tarjeta OLT., get, Rutas HTTP de temperatura OLT., temperatura_actual(), clasificar_temperatura(), obtener_temperatura_actual(), Any (+1 more)

### Community 135 - "config.py"
Cohesion: 0.11
Nodes (5): BaseSettings, get_settings(), Configuracion comun de los microservicios., Settings, ConfigurationAndOracleMockTests

### Community 137 - "cmts_inits_visual.cjs"
Cohesion: 0.40
Nodes (4): assert, { chromium }, fs, rows

### Community 139 - "doctor.md"
Cohesion: 0.25
Nodes (7): Monorepo notes, Opting out of the boot check, Step 1: Run the pass, Step 2: Act by severity, Step 3: Deprecated fields are binding, Step 4: Do not overclaim on truth drift, What this owns, and what it does not

### Community 141 - "BACKUP_CMTS_MENU_5DIAS_20261009_101544_189823/microservicios/cmts/inits/export_excel.py"
Cohesion: 0.39
Nodes (6): cell(), clean(), date_number(), Path, Excel nativo para el ciclo actual. Solo biblioteca estándar; no modifica CSV., write_excel()

### Community 142 - "probar_topologias.py"
Cohesion: 0.43
Nodes (7): consultar(), convertir_visio_a_jpg(), main(), obtener_ruta_local(), procesar_mensajes(), Prueba manual de la API de topologías OLT con conversión VSD/VSDX -> JPG., recortar_imagen()

### Community 143 - "probar_vsd_jpg.py"
Cohesion: 0.50
Nodes (7): convertir_individual(), convertir_masivo(), convertir_visio_a_jpg(), main(), obtener_archivos_visio(), procesar_mensajes(), recortar_imagen()

### Community 144 - "consultar_mysql"
Cohesion: 0.27
Nodes (8): consultar_mysql(), crear_conexion(), Any, Cliente comun para consultas MySQL., obtener_licencias_bajas_mysql(), Any, Consultas de recursos ZTE con baja disponibilidad., Obtiene únicamente los recursos ZTE bajo el umbral indicado.

### Community 145 - "scopeCssBlock"
Cohesion: 0.40
Nodes (6): findMatchingCssBrace(), prefixCssSelectors(), scopeCssBlock(), shouldScopeNestedCssAtRule(), splitCssSelectorList(), unwrapSvelteGlobalSelector()

### Community 146 - "responsive_wheel.cjs"
Cohesion: 0.33
Nodes (5): assert, {chromium}, fs, routes, sizes

### Community 153 - "responsive_states.cjs"
Cohesion: 0.50
Nodes (3): assert, {chromium}, fs

### Community 154 - "Corrección responsive y rueda — 9 de octubre de 2026"
Cohesion: 0.40
Nodes (4): Corrección responsive y rueda — 9 de octubre de 2026, Evidencia y alcance, Repetir, Revisar y aplicar conservando trabajo local

## Knowledge Gaps
- **431 isolated node(s):** `Evidencia y alcance`, `Repetir`, `Revisar y aplicar conservando trabajo local`, `{ chromium }`, `assert` (+426 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 693 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `HelixWorker` connect `HelixWorker` to `.test_equipment_query_retains_open_task_with_closed_parent`, `casos_helix/router.py`, `WorkerTests`?**
  _High betweenness centrality (0.011) - this node is a cross-community bridge._
- **Why does `ConfigurationAndOracleMockTests` connect `config.py` to `.test_query_streams_and_keeps_open_children_of_closed_parent`, `casos_helix/router.py`?**
  _High betweenness centrality (0.010) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `initGlobalBar()` (e.g. with `hideAgentPollTooltip()` and `onDetectMessage()`) actually correct?**
  _`initGlobalBar()` has 7 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Evidencia y alcance`, `Repetir`, `Revisar y aplicar conservando trabajo local` to the rest of the system?**
  _431 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `renderDesignVisual` be split into smaller, more focused modules?**
  _Cohesion score 0.07692307692307693 - nodes in this community are weakly interconnected._
- **Should `BACKUP_CMTS_MENU_5DIAS_20261009_101544_189823/microservicios/cmts/inits/router.py` be split into smaller, more focused modules?**
  _Cohesion score 0.12962962962962962 - nodes in this community are weakly interconnected._
- **Should `topologias/service.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08502939846223428 - nodes in this community are weakly interconnected._