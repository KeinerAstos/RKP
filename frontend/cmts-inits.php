<?php declare(strict_types=1); ?>
<!doctype html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>RKP | Monitoreo de INIT</title>
    <link rel="stylesheet" href="assets/css/style.css">
    <link rel="stylesheet" href="assets/css/sidebar.css">
    <link rel="stylesheet" href="assets/css/gkp.css?v=20261009">
    <link rel="stylesheet" href="assets/css/module-page.css?v=20261009">
    <link rel="stylesheet" href="assets/css/cmts-inits.css">
<link rel="stylesheet" href="assets/css/responsive-tables.css?v=1">
</head>
<body class="gkp-page hfc-page cmts-init-page">
<div class="app">
    <?php require __DIR__ . '/components/sidebar.php'; ?>
    <main class="main">
        <?php $headerTitle = 'Monitoreo de INIT'; $headerDescription = 'Módems en estado INIT por CMTS.'; ?>
        <?php require __DIR__ . '/components/header.php'; ?>
        <div class="module-content cmts-init-content">
            <header class="module-heading"><h2>Monitoreo de INIT</h2><p>Inventario CMTS · consultas SSH · histórico de lecturas válidas</p></header>
            <section class="init-toolbar" aria-label="Estado y controles">
                <div><strong id="init-run-state">Leyendo estado…</strong><span id="init-last-run">Sin mediciones</span></div>
                <div class="init-actions"><label class="init-search"><span class="sr-only">Buscar CMTS o IP</span><input id="init-search" type="search" placeholder="Buscar CMTS o IP"></label><label class="init-filter"><span class="sr-only">Filtrar por resultado</span><select id="init-filter"><option value="">Todos los resultados</option><option value="error">Consultas fallidas</option><option value="CRITICO">Críticos</option><option value="RIESGO">Riesgo</option><option value="ATENCION">Atención</option><option value="SIN INIT">Sin INIT</option></select></label>
                    <button id="init-export" type="button">Exportar CSV</button><button id="init-refresh" class="init-primary" type="button">Actualizar inventario</button></div>
            </section>
            <p id="init-notice" class="init-notice" role="status" aria-live="polite">Cargando última lectura…</p>
            <section class="init-metrics" aria-label="Resumen del último ciclo">
                <div><span>CMTS inventariados</span><strong id="init-total-cmts">—</strong></div>
                <div><span>Consultas exitosas</span><strong id="init-success">—</strong></div>
                <div><span>Consultas fallidas</span><strong id="init-failed">—</strong></div>
                <div><span>INIT válidos</span><strong id="init-total-init">—</strong></div>
            </section>
            <section class="init-table-panel" aria-label="Resultados por CMTS">
                <div class="init-table-scroll" tabindex="0" role="region" aria-label="Tabla de monitoreo INIT; desplazamiento interno">
                    <table class="gkp-table init-table"><thead><tr><th><button data-sort="cmts">CMTS / IP</button></th><th><button data-sort="fecha">Fecha</button></th><th><button data-sort="total_init">INIT <span aria-hidden="true">↓</span></button></th><th>Gravedad</th><th>Consulta</th><th><button data-sort="variacion">Variación</button></th><th>Detalle</th></tr></thead><tbody id="init-rows"></tbody></table>
                </div>
                <div id="init-empty" class="module-empty" hidden>Sin mediciones disponibles. Configura acceso e inicia una actualización.</div>
            </section>
            <section class="init-lower">
                <div class="init-table-panel"><div class="init-section-title"><h3>Top 10 CMTS por INIT</h3></div><ol id="init-top" class="init-top"></ol></div>
                <div class="init-table-panel"><div class="init-section-title"><h3>Tendencia del CMTS</h3><label>Equipo <select id="init-trend-cmts" aria-label="CMTS para consultar tendencia"></select></label></div><canvas id="init-trend" height="170" aria-label="Gráfica histórica de módems INIT" role="img"></canvas><p id="init-trend-empty" class="init-muted" hidden>Sin lecturas válidas para graficar.</p></div>
            </section>
            <section class="init-table-panel init-history"><div class="init-section-title"><h3>Histórico reciente</h3><div class="init-history-controls"><label>CMTS <input id="init-history-cmts" type="search" placeholder="Todos"></label><label>Desde <input id="init-history-from" type="date"></label><label>Hasta <input id="init-history-to" type="date"></label><button id="init-history-prev" type="button">Anterior</button> <button id="init-history-next" type="button">Siguiente</button></div></div><div class="init-history-meta" id="init-history-meta"></div><div class="init-table-scroll" tabindex="0" role="region" aria-label="Histórico paginado; desplazamiento interno"><table class="gkp-table"><thead><tr><th>Fecha</th><th>CMTS</th><th>IP</th><th>Total INIT</th><th>Resultado</th></tr></thead><tbody id="init-history-rows"></tbody></table></div></section>
        </div>
        <?php require __DIR__ . '/components/footer.php'; ?>
    </main>
</div>
<script src="assets/js/sidebar.js" defer></script><script src="assets/js/cmts-inits.js" defer></script>
</body>
</html>
