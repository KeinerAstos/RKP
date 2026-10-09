# Graph Report - RKP  (2026-10-09)

## Corpus Check
- 161 files · ~448,796 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 22 file(s) not represented in the graph (top: .css 7, .toml 4, .csv 4)

## Summary
- 1967 nodes · 4244 edges · 143 communities (99 shown, 7 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 120 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `db3a5f97`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- renderDesignVisual
- Responsive Design
- topologias/service.py
- modern-screenshot.umd.js
- cmts/saturacion/service.py
- initPageChat
- el
- obtener_licencias_bajas
- inits_cmts.py
- showToast
- casos_helix/service.py
- initGlobalBar
- caidas/service.py
- grafana_proxy/app.py
- export_excel.py
- applyEditing
- HistorialTests
- Extract Flow
- createLiveBrowserDomHelpers
- HelixWorker
- crc/service.py
- casos_helix/router.py
- createLiveBrowserSessionState
- hfc.js
- setLiveState
- adapt.md
- intermitencias/service.py
- puertos_duplicados/service.py
- Components
- gkp.js
- temperatura.js
- olt/saturacion/service.py
- bolder.md
- MicroserviceClient
- iniciar_microserviciosypuente.py
- SKILL.md
- scheduleAcceptCleanup
- onboard.md
- consultar_influx.py
- mountSvelteComponentVariant
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
- microservicios/app.py
- live-setup.md
- WorkerTests
- Generate Report
- Cognitive Load Assessment
- Impeccable Asset Producer
- Impeccable Finish Reviewer
- Impeccable Manual Edit Applier
- Diagnostic Scan
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
- obtener_correlacion
- findVariantsWrapper
- consultar_flux_temp
- cmts_inits_visual.cjs
- responsive_wheel.cjs
- table-wheel.js
- __init__.py
- responsive_states.cjs

## God Nodes (most connected - your core abstractions)
1. `setLiveState()` - 32 edges
2. `resumeSession()` - 32 edges
3. `connectSSE()` - 31 edges
4. `showToast()` - 30 edges
5. `el()` - 29 edges
6. `initGlobalBar()` - 29 edges
7. `handleKeyDown()` - 27 edges
8. `buildInsertConfigureRow()` - 26 edges
9. `injectSvelteComponentsFromManifest()` - 26 edges
10. `cleanup()` - 26 edges

## Surprising Connections (you probably didn't know these)
- `terminado()` --calls--> `actualizar()`  [INFERRED]
  tests/test_olt_caidas_historial.py → microservicios/cmts/inits/router.py
- `EquipoScopeIssue4Tests` --uses--> `HelixWorker`  [INFERRED]
  tests/test_casos_helix_async.py → microservicios/olt/casos_helix/worker.py
- `WorkerTests` --uses--> `HelixWorker`  [INFERRED]
  tests/test_casos_helix_async.py → microservicios/olt/casos_helix/worker.py
- `test_cycle_claim_is_global_and_recovers_dead_process_lock()` --calls--> `claim_cycle()`  [EXTRACTED]
  tests/test_cmts_inits.py → microservicios/cmts/inits/inits_cmts.py
- `test_status_ignores_lock_from_dead_process_even_without_published_csv()` --calls--> `status()`  [EXTRACTED]
  tests/test_cmts_inits.py → microservicios/cmts/inits/inits_cmts.py

## Import Cycles
- None detected.

## Communities (143 total, 7 thin omitted)

### Community 0 - "renderDesignVisual"
Cohesion: 0.07
Nodes (42): buildCollapsible(), buildColorModels(), buildDesignHeader(), buildListHtml(), buildRadiiModels(), buildTypographyModels(), cssSafe(), designEmptyMessage() (+34 more)

### Community 1 - "Responsive Design"
Cohesion: 0.20
Nodes (10): Breakpoints: Content-Driven, Detect Input Method, Not Just Screen Size, Layout Adaptation Patterns, Mobile-First: Write It Right, Picture Element for Art Direction, Responsive Design, Responsive Images: Get It Right, Safe Areas: Handle the Notch (+2 more)

### Community 2 - "topologias/service.py"
Cohesion: 0.10
Nodes (55): FileResponse, archivo(), _buscar(), buscar_global(), ftto(), health(), huawei(), imagen() (+47 more)

### Community 3 - "modern-screenshot.umd.js"
Cohesion: 0.09
Nodes (55): ae(), be(), bt(), Ce(), s(), Ct(), de(), dt() (+47 more)

### Community 4 - "cmts/saturacion/service.py"
Cohesion: 0.09
Nodes (47): BackgroundTasks, _guardar_atomico(), guardar_estado(), guardar_saturacion(), _leer(), leer_estado(), leer_saturacion(), Any (+39 more)

### Community 5 - "initPageChat"
Cohesion: 0.09
Nodes (45): armPageChatForTyping(), attachSteerFocusDebug(), attachSteerFocusGuard(), buildSteerProcessingDots(), buildSteerQueueHint(), clearSteerAwaitTimer(), collapsePageChat(), expandPageChat() (+37 more)

### Community 6 - "el"
Cohesion: 0.11
Nodes (37): bindConfigureCountPillTooltip(), bindConfigureInlineControlHover(), bindConfigureModifierPillHover(), buildConfigureActionControl(), buildConfigureCountControl(), buildConfigureRow(), buildConfigureSubmitButton(), buildConfigureTrailingCluster() (+29 more)

### Community 7 - "obtener_licencias_bajas"
Cohesion: 0.10
Nodes (25): consultar_mysql(), crear_conexion(), Any, Cliente comun para consultas MySQL., Consulta SQL de las lecturas actuales de gestión., perdida_latencia_actual(), get, Rutas HTTP de pérdida y latencia OLT. (+17 more)

### Community 8 - "inits_cmts.py"
Cohesion: 0.05
Nodes (80): _acquire_lock(), actual(), _append_history(), apply_retention(), _atomic_csv(), claim_cycle(), data_dir(), export_rows() (+72 more)

### Community 9 - "showToast"
Cohesion: 0.10
Nodes (30): abandonForeignSession(), actionLabel(), applyConfigureBarChrome(), buildConfirmedRow(), buildCyclingRow(), buildDots(), buildGeneratingRow(), copyToClipboard() (+22 more)

### Community 10 - "casos_helix/service.py"
Cohesion: 0.21
Nodes (24): _consultar_equipo_asociaciones(), consultar_olt(), consultar_olt_equipo(), _consultar_puertos_asociaciones(), add(), _deadline_check(), _fetch(), _has_explicit_location() (+16 more)

### Community 11 - "initGlobalBar"
Cohesion: 0.08
Nodes (51): agentHasWorkInFlight(), agentStatusText(), applyGlobalBarLabelState(), barPaletteForTheme(), brandMarkSvg(), buildParamsPanel(), clearStoredManualApplyState(), detectPageTheme() (+43 more)

### Community 12 - "caidas/service.py"
Cohesion: 0.16
Nodes (28): _escapar_flux(), obtener_caidas_flux(), obtener_estado_actual_flux(), obtener_ultima_actividad_flux(), obtener_ultima_muestra_conocida_flux(), Consultas Flux para detectar caídas de puertos OLT por tráfico., Obtiene las últimas muestras de tráfico recientes. Se revisan 30 minutos para…, Obtiene la última muestra conocida de cada puerto. Sirve para detectar puertos… (+20 more)

### Community 13 - "grafana_proxy/app.py"
Cohesion: 0.13
Nodes (29): api_route, exception_handler, JSONResponse, error_http(), error_no_controlado(), error_validacion(), Exception, HTTPException (+21 more)

### Community 14 - "export_excel.py"
Cohesion: 0.43
Nodes (6): cell(), clean(), date_number(), Excel nativo para el ciclo actual. Solo biblioteca estándar; no modifica CSV., write_excel(), _write_excel()

### Community 15 - "applyEditing"
Cohesion: 0.08
Nodes (38): addManualContextText(), applyEditing(), buildLocatorForLeaf(), canRestoreManualEditElement(), collectEditableTextRows(), visit(), collectManualContextPieces(), walk() (+30 more)

### Community 16 - "HistorialTests"
Cohesion: 0.14
Nodes (6): CacheHistorial, Caché de historial de 7 días; las peticiones nunca esperan su consulta., CacheTests, terminado(), HistorialTests, Verificación del historial extendido sin acceso a Influx real.

### Community 17 - "Extract Flow"
Cohesion: 0.25
Nodes (7): Extract Flow, Step 1: Discover the Design System, Step 2: Identify Patterns, Step 3: Plan Extraction, Step 4: Extract & Enrich, Step 5: Migrate, Step 6: Document

### Community 18 - "createLiveBrowserDomHelpers"
Cohesion: 0.17
Nodes (10): createLiveBrowserDomHelpers(), cssId(), liveUiRoot(), makeFrozenAnchor(), own(), pickable(), rectIsUsableAnchor(), uiAppend() (+2 more)

### Community 19 - "HelixWorker"
Cohesion: 0.18
Nodes (7): get_worker(), HelixWorker, JobState, Any, Cola acotada y estado publicable para consultas Helix lentas., Un único hilo Oracle por proceso y un límite explícito de OLT en espera., start_worker()

### Community 20 - "crc/service.py"
Cohesion: 0.17
Nodes (17): _metricas_crc_flux(), obtener_crc_actual_flux(), obtener_crc_flux(), Consultas Flux para errores CRC de puertos OLT., Devuelve muestras superiores a diez errores CRC por segundo., Filtra el umbral despues de seleccionar la ultima muestra de cada puerto., crc(), crc_actual() (+9 more)

### Community 21 - "casos_helix/router.py"
Cohesion: 0.13
Nodes (18): BaseModel, BaseSettings, Settings, casos_abiertos(), casos_abiertos_lote(), _legacy_result(), Any, get (+10 more)

### Community 22 - "createLiveBrowserSessionState"
Cohesion: 0.21
Nodes (15): createLiveBrowserSessionState(), clearHandled(), clearScrollY(), clearSession(), isHandled(), loadSession(), markHandled(), nextCheckpointRevision() (+7 more)

### Community 23 - "hfc.js"
Cohesion: 0.24
Nodes (16): changeDays(), changePanel(), checkUpdateStatus(), compareCriticality(), eyeButton(), formatUpdatedAt(), grafanaUrl(), load() (+8 more)

### Community 24 - "setLiveState"
Cohesion: 0.13
Nodes (52): abortSvelteComponentInjection(), beginNewLiveConfiguration(), buildInsertPlaceholderSnapshotFromDom(), buildPickedAnchorSnapshot(), cancelEditing(), cancelEditingToPicking(), cancelInsertConfigure(), cleanup() (+44 more)

### Community 25 - "adapt.md"
Cohesion: 0.12
Nodes (15): Assess Adaptation Challenge, Content Adaptation, Desktop Adaptation (Mobile → Desktop), Email Adaptation (Web → Email), Implement Adaptations, Layout Adaptation Techniques, Mobile Adaptation (Desktop → Mobile), Navigation Adaptation (+7 more)

### Community 26 - "intermitencias/service.py"
Cohesion: 0.19
Nodes (13): obtener_intermitencias_flux(), Consultas Flux para detectar intermitencias HFC., Detecta caídas de puertos HFC usando cm_registrados. Una caída se confirma…, intermitencias_actual(), get, Rutas HTTP de intermitencias HFC., _numero_entero(), obtener_intermitencias_actuales() (+5 more)

### Community 27 - "puertos_duplicados/service.py"
Cohesion: 0.19
Nodes (13): obtener_puertos_duplicados_flux(), Consultas Flux para detectar nodos en puertos CMTS duplicados., Obtiene la ubicacion mas reciente de cada descripcion, CMTS y puerto., puertos_duplicados_actual(), get, Rutas HTTP de nodos asociados a multiples puertos CMTS., normalizar_descripcion(), obtener_puertos_duplicados_actuales() (+5 more)

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
Cohesion: 0.14
Nodes (21): Correlacion temporal de saturacion, CRC y caidas OLT., _metricas_saturacion_flux(), obtener_saturacion_actual_flux(), obtener_saturacion_flux(), Consultas Flux para saturacion de puertos OLT., Devuelve la secuencia de muestras con saturacion superior al 70 %., Filtra el umbral despues de seleccionar la ultima muestra de cada puerto., get (+13 more)

### Community 32 - "bolder.md"
Cohesion: 0.33
Nodes (5): Before you finish, Scope is sovereign, The amplification, The skeleton test, Why it reads flat

### Community 34 - "iniciar_microserviciosypuente.py"
Cohesion: 0.58
Nodes (9): esperar_puerto(), iniciar_tunel(), iniciar_tunel_oracle(), iniciar_uvicorn(), main(), matar(), nueva_consola_kwargs(), puerto_abierto() (+1 more)

### Community 35 - "SKILL.md"
Cohesion: 0.09
Nodes (17): Craft floor, Refuse, Verify, Monorepo notes, Opting out of the boot check, Step 1: Run the pass, Step 2: Act by severity, Step 3: Deprecated fields are binding (+9 more)

### Community 36 - "scheduleAcceptCleanup"
Cohesion: 0.31
Nodes (11): acceptedDomAlreadyClean(), clearHandledWrapperReloadStamp(), deferredRecoverySuperseded(), ensureAcceptedDomClean(), findAcceptedRuntimeWrappers(), handledWrapperReloadKey(), reloadAfterMissingAcceptedDom(), restoreAcceptedDomFromSnapshot() (+3 more)

### Community 37 - "onboard.md"
Cohesion: 0.09
Nodes (22): Assess Onboarding Needs, Context Over Ceremony, Contextual Help, Design Onboarding Experiences, Documentation & Help, Empty State Design, Feature Discovery & Adoption, Guided Tours & Walkthroughs (+14 more)

### Community 38 - "consultar_influx.py"
Cohesion: 0.29
Nodes (12): ejecutar_caidas(), ejecutar_intermitencias(), imprimir_resultado(), main(), mostrar_menu(), Any, Herramienta interactiva para probar manualmente los servicios OLT., seleccionar_periodo_caidas() (+4 more)

### Community 39 - "mountSvelteComponentVariant"
Cohesion: 0.13
Nodes (22): applyOriginalAttrsToSvelteAnchor(), clearMountErrorCard(), commitAcceptedSvelteComponentToDom(), componentModuleCandidates(), describeMountFailure(), detectDevServerBase(), findInsertAnchorInDom(), findLiveElementForSvelteManifest() (+14 more)

### Community 40 - "new-work.md"
Cohesion: 0.13
Nodes (14): Recommended Actions, Craft (deprecated alias), Apply, Live-mode signature params, Set the spatial thesis, Two isolated assessments, Verify, Visitor mode (+6 more)

### Community 42 - "onAnnotDown"
Cohesion: 0.18
Nodes (19): applyPlaceholderDimensions(), beginEditPin(), buildAnnotationsForCapture(), buildPinElement(), cancelEditingPin(), finalizeEditingPin(), initAnnotOverlay(), localCoords() (+11 more)

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
Cohesion: 0.11
Nodes (51): applySavedSessionMeta(), clampVariantIndex(), clearHandled(), completeParameterGenerationIfReady(), completeParameterPublication(), completeSourceInjection(), connectSSE(), disableInlineEdit() (+43 more)

### Community 84 - "New visual work"
Cohesion: 0.14
Nodes (14): 1. Decide what is already true, 2. Ask what will change the work, 3. Choose the right amount of invention, 4. Commit the world, 5. Record the decision, 6. Build with full commitment, 7. Inspect and finish, Both paths (+6 more)

### Community 85 - "optimize.md"
Cohesion: 0.14
Nodes (13): Animation Performance, Assess Performance Issues, Core Web Vitals Optimization, Cumulative Layout Shift (CLS < 0.1), Interaction to Next Paint (INP < 200ms), Largest Contentful Paint (LCP < 2.5s), Loading Performance, Network Optimization (+5 more)

### Community 86 - "live-browser.js"
Cohesion: 0.04
Nodes (103): applyParamValue(), applyPlaceholderSizingStyles(), bindEditBadgeProxy(), bufferToBase64(), buildPlaceholderResizeHandles(), buildSavingRow(), buildSvelteExpressionTextMap(), buildSveltePropValuesFromLiveElement() (+95 more)

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

### Community 108 - "microservicios/app.py"
Cohesion: 0.13
Nodes (17): FastAPI, health(), lifespan(), get, Aplicacion FastAPI principal de Backend Datos., worker_topologias(), caidas(), caidas_actuales() (+9 more)

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
Cohesion: 0.11
Nodes (23): averageRgb01(), captureAndEmit(), captureElementFromRenderedAncestor(), captureElementToBlob(), checkpointPayload(), compileShader(), cssColorToRgb01(), dominantRgb01() (+15 more)

### Community 129 - "gkp-casos-helix.js"
Cohesion: 0.25
Nodes (16): acceptResult(), actualizar(), actualizarEquipos(), celdasEquipo(), chunks(), consultarEquipo(), consultarLotes(), currentCells() (+8 more)

### Community 132 - "obtener_correlacion"
Cohesion: 0.28
Nodes (8): correlacion(), get, Rutas HTTP de correlacion OLT., eventos_se_relacionan(), obtener_correlacion(), Any, Indica si dos intervalos se cruzan dentro del margen configurado., Consulta cada fenomeno una vez y cruza sus episodios por OLT y puerto.

### Community 133 - "findVariantsWrapper"
Cohesion: 0.11
Nodes (26): applyParamDefaults(), closedClipPath(), commitAcceptedVariantToDom(), ensureInsertPlaceholder(), findVariantsWrapper(), getMountedSvelteComponentAnchor(), getVisibleVariantEl(), hideParamsPanel() (+18 more)

### Community 134 - "consultar_flux_temp"
Cohesion: 0.16
Nodes (17): InfluxDBClient, get_settings(), Configuracion comun de los microservicios., consultar_flux_temp(), crear_cliente_cmts(), crear_cliente_temp(), iterar_flux_temp(), probar_conexion_temp() (+9 more)

### Community 137 - "cmts_inits_visual.cjs"
Cohesion: 0.40
Nodes (4): assert, { chromium }, fs, rows

### Community 146 - "responsive_wheel.cjs"
Cohesion: 0.33
Nodes (5): assert, {chromium}, fs, routes, sizes

### Community 153 - "responsive_states.cjs"
Cohesion: 0.50
Nodes (3): assert, {chromium}, fs

## Knowledge Gaps
- **428 isolated node(s):** `{ chromium }`, `assert`, `fs`, `rows`, `Setup` (+423 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 678 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Reference Material` connect `Heuristics Scoring Guide` to `critique.md`, `Cognitive Load Assessment`, `Persona-Based Design Testing`?**
  _High betweenness centrality (0.009) - this node is a cross-community bridge._
- **Why does `New visual work` connect `New visual work` to `new-work.md`?**
  _High betweenness centrality (0.006) - this node is a cross-community bridge._
- **What connects `{ chromium }`, `assert`, `fs` to the rest of the system?**
  _428 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `renderDesignVisual` be split into smaller, more focused modules?**
  _Cohesion score 0.07084785133565621 - nodes in this community are weakly interconnected._
- **Should `topologias/service.py` be split into smaller, more focused modules?**
  _Cohesion score 0.10227936879018118 - nodes in this community are weakly interconnected._
- **Should `modern-screenshot.umd.js` be split into smaller, more focused modules?**
  _Cohesion score 0.09147869674185463 - nodes in this community are weakly interconnected._
- **Should `cmts/saturacion/service.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08686868686868687 - nodes in this community are weakly interconnected._