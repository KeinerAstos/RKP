<?php declare(strict_types=1);
require_once dirname(__DIR__) . '/backend/lib/dashboard_hfc.php';
$hfcFrontendUrl = dh_url('', 'frontend');
?>
<!doctype html>
<html lang="es">

<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>RKP | Dashboard HFC</title>
    <link rel="stylesheet" href="assets/css/style.css">
    <link rel="stylesheet" href="assets/css/sidebar.css">
    <link rel="stylesheet" href="assets/css/gkp.css">
    <link rel="stylesheet" href="assets/css/module-page.css">
    <link rel="stylesheet" href="assets/css/dashboard-hfc.css">
    <link rel="stylesheet"
        href="<?= dh_html(rkp_hfc_env('HFC_FONT_AWESOME_URL', 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css')) ?>">
    <script>
        window.RKP_HFC_URLS = <?= json_encode(['frontend' => dh_url('', 'frontend'), 'dashboard' => dh_url('')], JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT) ?>;
        window.dhUrl = (path = '', scope = 'dashboard') => {
            const route = String(path).match(/(?:api\/dashboard_hfc|backend\/api\/hfc)\/([a-z_]+)\.php$/);
            if (route) return window.RKP_HFC_URLS.dashboard + '/backend/api/dashboard_hfc.php?action=' + route[1];
            return (window.RKP_HFC_URLS[scope] || window.RKP_HFC_URLS.dashboard).replace(/\/$/, '') + '/' + String(path).replace(/^\//, '');
        };
        window.RKP_HFC_POLL_MS = <?= max(15000, (int) rkp_hfc_env('HFC_POLL_SECONDS', '30') * 1000) ?>;
    </script>
</head>

<body class="gkp-page hfc-page module-flow-page dashboard-hfc-page">
    <div class="app">
        <?php require __DIR__ . '/components/sidebar.php'; ?>
        <main class="main">
            <?php $headerTitle = 'Dashboard HFC';
            $headerDescription = 'Estado de nodos y Service Groups CASA / ARRIS, incidentes y señales RF';
            require __DIR__ . '/components/header.php'; ?>
            <div class="hfc-app" id="hfcApp"
                data-api-estado="<?php echo dh_html(dh_url('api/dashboard_hfc/estado.php', 'frontend')); ?>"
                data-api-inc="<?php echo dh_html(dh_url('api/dashboard_hfc/incidentes.php', 'frontend')); ?>"
                data-api-base="<?php echo dh_html(dh_url('api/dashboard_hfc/importar_base.php', 'frontend')); ?>"
                data-api-inc-import="<?php echo dh_html(dh_url('api/dashboard_hfc/importar_incidentes.php', 'frontend')); ?>"
                data-api-analytics="<?php echo dh_html(dh_url('api/dashboard_hfc/analytics.php', 'frontend')); ?>">


                <!-- ==================================================
         HERO
         ================================================== -->

                <section class="hfc-sourcebar" aria-label="Estado de las fuentes">
                    <div id="hfcExecMeta" class="hfc-exec-meta">
                        <div id="hfcAutoCmtsCard"><span>CMTS / HFC · origen</span><strong
                                id="hfcAutoCmtsTime">Consultando…</strong></div>
                        <div id="hfcAutoNetcoolCard"><span>NETCOOL · importación</span><strong
                                id="hfcAutoNetcoolTime">Consultando…</strong></div>
                        <div><span>QoE · origen</span><strong id="hfcQoeUpdated">Sin información</strong></div>
                    </div>
                    <button class="hfc-btn primary" id="btnRefresh" type="button"><i class="fas fa-rotate"
                            aria-hidden="true"></i> Actualizar</button>
                </section>
                <div class="hfc-query-status" id="liveStatus" role="status" aria-live="polite">Consultando base local…
                </div>



                <!-- ==================================================
         KPIS
         ================================================== -->

                <section class="hfc-kpis" id="kpis"></section>



                <!-- ==================================================
         TOP 10 + DETALLE POR ZONA
         ================================================== -->




                <!-- ==================================================
         ESTADO DE RED / INCIDENTES
         ================================================== -->

                <section class="hfc-card">


                    <!-- Tabs -->

                    <div class="hfc-tabs" role="tablist" aria-label="Vistas HFC">

                        <button class="hfc-tab active" data-tab="network">
                            Operación
                        </button>


                        <button class="hfc-tab" data-tab="incidents">
                            Incidentes NETCOOL

                        </button>


                    </div>


                    <!-- ==================================================
             TAB NETWORK
             ================================================== -->

                    <div id="tabNetwork" class="hfc-tabpanel active">


                        <div class="hfc-toolbar">


                            <div class="hfc-filters">


                                <label>

                                    <span>Fabricante</span>

                                    <select id="fVendor">

                                        <option value="">
                                            Todos
                                        </option>

                                        <option>
                                            CASA
                                        </option>

                                        <option>
                                            ARRIS
                                        </option>

                                    </select>

                                </label>


                                <label>

                                    <span>Ciudad</span>

                                    <select id="fZone">

                                        <option value="">
                                            Todas
                                        </option>

                                    </select>

                                </label>


                                <label>

                                    <span>CMTS</span>

                                    <select id="fCmts">

                                        <option value="">
                                            Todos
                                        </option>

                                    </select>

                                </label>


                                <label>

                                    <span>Estado</span>

                                    <select id="fState">

                                        <option value="">
                                            Todos
                                        </option>

                                        <option value="DESENGANCHE TOTAL">
                                            DESENGANCHE TOTAL
                                        </option>

                                        <option value="POSIBLE DESENGANCHE TOTAL / HISTORICO">
                                            POSIBLE DESENGANCHE TOTAL
                                        </option>

                                        <option value="POSIBLE CAIDA PROLONGADA / HISTORICO">
                                            POSIBLE CAIDA PROLONGADA
                                        </option>

                                        <option value="DESENGANCHE PARCIAL">
                                            DESENGANCHE PARCIAL
                                        </option>

                                        <option value="ENGANCHADO">
                                            ENGANCHADO
                                        </option>

                                        <option value="CERO CON EVIDENCIA HISTORICA / VALIDAR">
                                            CERO HISTORICO / VALIDAR
                                        </option>

                                        <option value="SIN MODEMS / VALIDAR">
                                            SIN MODEMS / VALIDAR
                                        </option>

                                        <option value="SIN MODEMS / REVISAR CONFIGURACION">
                                            SIN MODEMS / REVISAR CONFIGURACION
                                        </option>

                                        <option value="SIN UPSTREAM / REVISAR CONFIGURACION">
                                            SIN UPSTREAM / REVISAR CONFIGURACION
                                        </option>

                                    </select>

                                </label>


                                <label>

                                    <span>Incidente</span>

                                    <select id="fInc">

                                        <option value="">
                                            Todos
                                        </option>

                                        <option>
                                            CON INCIDENTE
                                        </option>

                                        <option>
                                            SIN INCIDENTE
                                        </option>

                                        <option>
                                            NO APLICA
                                        </option>

                                        <option>
                                            REVISAR
                                        </option>

                                    </select>

                                </label>


                                <label class="grow">

                                    <span>
                                        Buscar
                                    </span>

                                    <input id="fSearch" type="search" placeholder="CMTS, nodo, Fiber Node, IP...">

                                </label>

                            </div>


                            <div class="hfc-toolbar-actions">

                                <button class="hfc-btn" id="btnClear">
                                    Limpiar filtros
                                </button>

                                <button class="hfc-btn" id="btnOpenBase">
                                    Cargar base plana HFC
                                </button>

                            </div>

                        </div>


                        <div class="hfc-table-section-head" id="hfcNetworkTableHead">
                            <div class="hfc-table-section-title"><strong>Elementos del alcance consultado</strong><span
                                    id="hfcFilterContext">Sin filtros</span><span>Origen HFC: <b
                                        id="estadoRedUpdatedAt">Consultando…</b></span></div>
                            <div id="hfcNetworkActions"><button class="hfc-btn" id="btnExportVista"
                                    type="button">Exportar vista CSV</button></div>
                        </div>
                        <!-- Tabla network -->

                        <div class="hfc-table-wrap" tabindex="0" role="region" aria-label="Tabla desplazable">

                            <table class="hfc-table">

                                <thead>
                                    <tr>
                                        <th scope="col">Nodo / SG</th>
                                        <th scope="col">CMTS</th>
                                        <th scope="col">Ciudad</th>
                                        <th scope="col">Estado</th>
                                        <th scope="col">Total</th>
                                        <th scope="col">Offline</th>
                                        <th scope="col">% Offline</th>
                                        <th scope="col">Incidente</th>
                                        <th scope="col">Comunidad</th>
                                        <th scope="col">Aliado</th>
                                        <th scope="col">Tipo</th>
                                        <th scope="col">Fabricante</th>
                                        <th scope="col">Descripción</th>
                                    </tr>
                                </thead>

                                <tbody id="networkBody">
                                    <tr>
                                        <td colspan="13">Cargando base local…</td>
                                    </tr>
                                </tbody>

                            </table>

                        </div>


                        <!-- Paginación -->

                        <div class="hfc-pagination">

                            <span id="networkCount"></span>

                            <div>

                                <button class="hfc-btn" id="prev">
                                    Anterior
                                </button>

                                <span id="pageInfo"></span>

                                <button class="hfc-btn" id="next">
                                    Siguiente
                                </button>

                            </div>

                        </div>

                        <details class="hfc-regional">
                            <summary>Prioridad y detalle regional <span>Dataset completo · cinco departamentos</span>
                            </summary>
                            <section class="hfc-grid-top">


                                <!-- TOP 10 -->

                                <article class="hfc-card">

                                    <div class="hfc-head">

                                        <div>



                                            <h2>
                                                Prioridad regional · 10 ciudades
                                            </h2>

                                            <p>
                                                Valle, Risaralda, Quindío, Cauca y Caldas · dataset completo.
                                            </p>

                                        </div>

                                    </div>

                                    <div id="top10" class="hfc-top10"></div>

                                </article>


                                <!-- DETALLE POR ZONA -->

                                <article class="hfc-card">

                                    <div class="hfc-head">

                                        <div>



                                            <h2>
                                                Detalle por zona
                                            </h2>

                                            <p>
                                                Selecciona cualquier ciudad,
                                                esté o no dentro del Top 10.
                                            </p>

                                        </div>


                                        <select id="zoneDetailSelect" class="hfc-select">

                                            <option value="">
                                                Seleccionar ciudad...
                                            </option>

                                        </select>

                                    </div>


                                    <div id="zoneDetail" class="hfc-zone-detail hfc-empty">
                                        Selecciona una ciudad para ver su detalle.
                                    </div>

                                </article>


                            </section>
                            <section id="hfcExecutivePanel">
                                <h3>Corte por departamento y capital</h3>
                                <p id="hfcExecutiveSubtitle"></p>
                                <div class="hfc-table-wrap" tabindex="0" role="region" aria-label="Tabla desplazable">
                                    <table class="hfc-table">
                                        <thead>
                                            <tr>
                                                <th scope="col">Tipo</th>
                                                <th scope="col">Nombre</th>
                                                <th scope="col">Total nodos</th>
                                                <th scope="col">Nodos afectados</th>
                                                <th scope="col">Porcentaje</th>
                                            </tr>
                                        </thead>
                                        <tbody id="hfcExecutiveBody"></tbody>
                                    </table>
                                </div>
                            </section>
                        </details>
                    </div>


                    <!-- ==================================================
             TAB INCIDENTS
             ================================================== -->

                    <div id="tabIncidents" class="hfc-tabpanel">

                        <div class="hfc-livebar">

                            <div>

                                <strong>
                                    Tabla independiente de incidentes NETCOOL
                                </strong>

                                <span>Dataset independiente · cruce con elementos HFC</span>

                            </div>


                            <div>

                                <button class="hfc-btn" id="btnExportInc">
                                    Descargar incidentes
                                </button>

                                <button class="hfc-btn" id="btnOpenInc">
                                    Cargar reporte NETCOOL
                                </button>

                            </div>

                        </div>


                        <div class="hfc-table-wrap" tabindex="0" role="region" aria-label="Tabla desplazable">

                            <table class="hfc-table">

                                <thead>

                                    <tr>

                                        <th scope="col">Severidad</th>
                                        <th scope="col">Primera ocurrencia</th>
                                        <th scope="col">NodeAlias</th>
                                        <th scope="col">INC / TT Helix</th>
                                        <th scope="col">Municipio</th>
                                        <th scope="col">TTNumber</th>
                                        <th scope="col">Agent</th>
                                        <th scope="col">Tipo afectación</th>
                                        <th scope="col">Cruce HFC</th>
                                        <th scope="col">CMTS</th>

                                    </tr>

                                </thead>

                                <tbody id="incBody"></tbody>

                            </table>

                        </div>

                    </div>


                    <!-- BEGIN HFC ANALYTICS NACIONAL V2 -->
                    <section class="hfc-tabpanel hfc-analytics-card" role="tabpanel" id="hfcAnalyticsPanel">

                        <!--
        Este wrapper es el que debe moverse completo
        cuando abra/cierre el sidebar lateral.
    -->
                        <div class="hfc-analytics-content" id="hfcAnalyticsContent">

                            <div class="hfc-head hfc-analytics-head">

                                <div>



                                    <h2>
                                        Vista nacional CASA + ARRIS
                                    </h2>

                                    <p>
                                        Consulta centralizada desde HFC_ANALYTICS,
                                        independiente del estado operativo e
                                        incidentes NETCOOL.
                                    </p>

                                </div>

                                <div class="hfc-analytics-status">

                                    <span id="hfcAnalyticsUpdated">
                                        Sin consultar
                                    </span>

                                </div>

                            </div>


                            <!-- AHORA LOS KPIS FORMAN PARTE DEL CONTENIDO MOVIBLE -->
                            <div class="hfc-analytics-kpis" id="hfcAnalyticsKpis"></div>


                            <!-- Toolbar Analytics -->
                            <div class="hfc-analytics-toolbar">

                                <label>

                                    <span>Tecnología</span>

                                    <select id="haTechnology">

                                        <option value="">
                                            CASA + ARRIS
                                        </option>

                                        <option value="CASA">
                                            CASA
                                        </option>

                                        <option value="ARRIS">
                                            ARRIS
                                        </option>

                                    </select>

                                </label>


                                <label>

                                    <span>CMTS</span>

                                    <select id="haCmts">

                                        <option value="">
                                            Todos
                                        </option>

                                    </select>

                                </label>


                                <label class="grow">

                                    <span>
                                        Buscar nodo
                                    </span>

                                    <input id="haSearch" type="search" placeholder="Nombre de nodo / Service Group...">

                                </label>


                                <button class="hfc-btn" type="button" id="haRefresh">

                                    <i class="fas fa-rotate"></i>
                                    Consultar

                                </button>

                                <button class="hfc-btn primary" type="button" id="haExportCsv">
                                    <i class="fas fa-download"></i>
                                    Exportar CSV
                                </button>

                            </div>


                            <!-- Tabla Analytics -->
                            <div class="hfc-analytics-table-wrap" tabindex="0" role="region"
                                aria-label="Analítica desplazable">


                                <table class="hfc-table hfc-analytics-table">

                                    <thead>

                                        <tr>

                                            <th scope="col">Tecnología</th>
                                            <th scope="col">CMTS</th>
                                            <th scope="col">Zona</th>
                                            <th scope="col">Nodo</th>
                                            <th scope="col">Hogares</th>
                                            <th scope="col">Offline</th>
                                            <th scope="col">Estado</th>
                                            <th scope="col">FEC %</th>
                                            <th scope="col">uFEC %</th>
                                            <th scope="col">SNR UP</th>
                                            <th scope="col">SQ</th>
                                            <th scope="col">QoE</th>
                                            <th scope="col">Horas estado</th>
                                            <th scope="col">HFC_AUTO</th>
                                            <th scope="col">Actualización</th>

                                        </tr>

                                    </thead>

                                    <tbody id="hfcAnalyticsBody">

                                        <tr>
                                            <td colspan="14">
                                                Pulsa Consultar para cargar la analítica.
                                            </td>
                                        </tr>

                                    </tbody>

                                </table>

                            </div>

                            <div class="hfc-pagination hfc-analytics-pagination">

                                <span id="haPageInfo">
                                    Página 1
                                </span>

                                <div>

                                    <button class="hfc-btn" type="button" id="haPrev" disabled>
                                        Anterior
                                    </button>

                                    <button class="hfc-btn" type="button" id="haNext">
                                        Siguiente
                                    </button>

                                </div>

                            </div>


                            <div class="hfc-analytics-foot">

                                <span id="hfcAnalyticsCount"></span>

                                <small>
                                    Use CMTS o búsqueda para drill-down.
                                    La vista general limita filas para
                                    mantener respuesta rápida.
                                </small>

                            </div>

                        </div>

                    </section>
                    <!-- END HFC ANALYTICS NACIONAL V2 -->
                </section>


                <!-- ==================================================
         RF / RUIDO
         ================================================== -->

                <section id="tabRf" class="hfc-card hfc-tabpanel rf-panel">


                    <section class="hfc-card">

                        <div class="hfc-head">

                            <div>



                                <h2>
                                    Salud RF por upstream
                                </h2>

                                <p id="rfGlobalStatus">
                                    Preparado.
                                </p>

                            </div>


                            <button class="hfc-btn" id="rfRefresh" type="button">
                                Actualizar RF
                            </button>

                        </div>


                        <div class="rf-kpis" id="rfKpis"></div>


                        <!-- RF Toolbar -->

                        <div class="rf-toolbar">


                            <div>



                                <div id="rfSelected">
                                    Selección nacional
                                </div>

                            </div>


                            <label>

                                <span>Nodo</span>

                                <input id="rfNode" placeholder="Ej. CX5">

                            </label>


                            <label>

                                <span>CMTS</span>

                                <input id="rfCmts" placeholder="CMTS exacto">

                            </label>


                            <label>

                                <span>Upstream</span>

                                <input id="rfUpstream" placeholder="Ej. 9/2.1">

                            </label>


                            <label>

                                <span>Búsqueda</span>

                                <input id="rfSearch" placeholder="Nodo, CMTS, upstream, diagnóstico">

                            </label>


                            <button class="hfc-btn" id="rfApply" type="button">
                                Aplicar
                            </button>


                            <button class="hfc-btn" id="rfSpectrum" type="button">
                                Spectrum
                            </button>


                            <button class="hfc-btn" id="rfClear" type="button">
                                Limpiar
                            </button>

                        </div>


                        <p class="rf-note" id="rfSearchStatus">
                            Ranking nacional cargado inicialmente.
                        </p>

                    </section>


                    <!-- ==================================================
             GRÁFICAS RF
             ================================================== -->

                    <section class="rf-grid">


                        <article class="rf-chart-card">

                            <h3>CNR</h3>

                            <p>
                                Carrier-to-noise real por upstream.
                            </p>

                            <canvas id="cnrChart"></canvas>

                        </article>


                        <article class="rf-chart-card">

                            <h3>
                                Signal Quality (SQ)
                            </h3>

                            <p>
                                Calidad de señal real por upstream.
                            </p>

                            <canvas id="sqChart"></canvas>

                        </article>


                        <article class="rf-chart-card">

                            <h3>FEC</h3>

                            <p>
                                Porcentaje de errores corregibles.
                            </p>

                            <canvas id="fecChart"></canvas>

                        </article>


                        <article class="rf-chart-card">

                            <h3>uFEC</h3>

                            <p>
                                Porcentaje de errores no corregibles.
                            </p>

                            <canvas id="ufecChart"></canvas>

                        </article>


                        <article class="rf-chart-card">

                            <h3>
                                Utilización
                            </h3>

                            <p>
                                Utilización actual del upstream.
                            </p>

                            <canvas id="utilChart"></canvas>

                        </article>


                        <article class="rf-chart-card">

                            <h3>
                                Impair
                            </h3>

                            <p>
                                Indicador de degradación RF activa.
                            </p>

                            <canvas id="impairChart"></canvas>

                        </article>


                        <article class="rf-chart-card wide">

                            <h3>
                                Spectrum · Ruido por frecuencia
                            </h3>

                            <p id="spectrumStatus">
                                Seleccione un nodo/upstream o consulte
                                la cobertura disponible.
                            </p>

                            <canvas id="spectrumChart"></canvas>

                        </article>


                    </section>


                    <!-- ==================================================
             RANKING RF
             ================================================== -->

                    <section class="hfc-card">

                        <div class="hfc-head">

                            <div>



                                <h2>
                                    Ranking de peor condición RF
                                </h2>

                                <p>
                                    Ordenado por impair, score Analytics,
                                    uFEC y CNR.
                                </p>

                            </div>

                        </div>


                        <div class="rf-table-wrap">

                            <table class="rf-table">

                                <thead>

                                    <tr>

                                        <th scope="col">#</th>
                                        <th scope="col">Nodo</th>
                                        <th scope="col">CMTS</th>
                                        <th scope="col">Upstream</th>
                                        <th scope="col">CNR</th>
                                        <th scope="col">SQ</th>
                                        <th scope="col">FEC %</th>
                                        <th scope="col">uFEC %</th>
                                        <th scope="col">Util %</th>
                                        <th scope="col">Impair</th>
                                        <th scope="col">Score</th>
                                        <th scope="col">Estado</th>

                                    </tr>

                                </thead>

                                <tbody id="rfRankingBody"></tbody>

                            </table>

                        </div>

                    </section>


                </section>


                <!-- ==================================================
         DIALOG CARGAR BASE HFC
         ================================================== -->

                <dialog id="dlgBase" class="hfc-dialog">

                    <form method="dialog" class="hfc-dialog-card" id="formBase">

                        <div class="hfc-head">

                            <div>



                                <h2>
                                    Cargar base plana HFC
                                </h2>

                            </div>


                            <button class="hfc-x" value="cancel">
                                ×
                            </button>

                        </div>


                        <p>
                            CSV separado por punto y coma o coma.
                            Si el archivo trae un solo fabricante,
                            se reemplaza únicamente ese fabricante;
                            si trae CASA + ARRIS, se reemplaza
                            la base completa.
                        </p>


                        <input type="file" id="baseFile" accept=".csv,.txt" required>


                        <div id="baseResult" class="hfc-result"></div>


                        <div class="hfc-dialog-actions">

                            <button class="hfc-btn" value="cancel">
                                Cancelar
                            </button>


                            <button type="button" class="hfc-btn primary" id="btnImportBase">
                                Importar
                            </button>

                        </div>

                    </form>

                </dialog>


                <!-- ==================================================
         DIALOG NETCOOL
         ================================================== -->

                <dialog id="dlgInc" class="hfc-dialog">

                    <form method="dialog" class="hfc-dialog-card" id="formInc">

                        <div class="hfc-head">

                            <div>



                                <h2>
                                    Cargar reporte de incidentes NETCOOL
                                </h2>

                            </div>


                            <button class="hfc-x" value="cancel">
                                ×
                            </button>

                        </div>


                        <p>
                            Esta carga es independiente de CASA + ARRIS.
                            Se reconocen campos NETCOOL como Severity,
                            FirstOccurrence, NodeAlias, TTNumber_Helix,
                            MUNICIPIO, TTNumber, Agent, Summary y
                            TipoAfectacion. La carga reemplaza únicamente
                            la tabla NETCOOL actual.
                        </p>


                        <input type="file" id="incFile" accept=".csv,.txt,.tsv,.xlsx" required>


                        <div id="incResult" class="hfc-result"></div>


                        <div class="hfc-dialog-actions">

                            <button class="hfc-btn" value="cancel">
                                Cancelar
                            </button>


                            <button type="button" class="hfc-btn primary" id="btnImportInc">
                                Importar
                            </button>

                        </div>

                    </form>

                </dialog>


            </div>


            <!-- ======================================================
     JAVASCRIPT PRINCIPAL HFC
     ====================================================== -->






            <!-- ======================================================
     HFC NODE CARD
     ====================================================== -->

            <script>
                window.HFC_NODE_CARD_CONFIG = {
                    analyticsNodesUrl: window.dhUrl("api/dashboard_hfc/analytics.php", "frontend")
                };
            </script>


            <?php require __DIR__ . '/components/footer.php'; ?>
        </main>
    </div>
    <script src="assets/js/sidebar.js" defer></script>
    <script src="assets/js/dashboard-hfc.js" defer></script>
</body>

</html>