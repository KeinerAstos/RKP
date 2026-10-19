<?php declare(strict_types=1); ?>
<!doctype html>
<html lang="es">

<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>RKP | Estados Helix</title>
    <link rel="stylesheet" href="assets/css/style.css">
    <link rel="stylesheet" href="assets/css/sidebar.css">
    <link rel="stylesheet" href="assets/css/gkp.css">
    <link rel="stylesheet" href="assets/css/module-page.css">
    <link rel="stylesheet" href="assets/css/estados-helix.css">
</head>

<body class="gkp-page helix-estados-page">
    <div class="app">
        <?php require __DIR__ . '/components/sidebar.php'; ?>
        <main class="main">
            <?php $headerTitle = 'Estados Helix';
            $headerDescription = 'Tiempo en estado de incidentes y tareas';
            require __DIR__ . '/components/header.php'; ?>
            <div class="module-content helix-estados" id="helix-estados">
                <div class="hx-summary">
                    <?php foreach (['inc' => ['INCIDENTES', 'INC'], 'tas' => ['TAREAS', 'TAS']] as $key => [$title, $type]): ?>
                        <section class="hx-panel" aria-label="Resumen de <?= $title ?>">
                            <h2><svg viewBox="0 0 24 24" aria-hidden="true">
                                    <path d="M5 4h14v16H5zM8 8h8M8 12h8M8 16h5" />
                                </svg><?= $title ?></h2>
                            <div class="hx-numbers">
                                <div><strong id="hx-<?= $key ?>-total">—</strong><span>Total <?= $type ?></span></div>
                                <div><strong class="hx-good" id="hx-<?= $key ?>-yes">—</strong><span>Con historial
                                        verificable</span></div>
                                <div><strong class="hx-warn" id="hx-<?= $key ?>-no">—</strong><span>Sin historial
                                        verificable</span></div>
                            </div>
                            <p class="hx-muted" id="hx-<?= $key ?>-scope">Pendiente de consulta</p>
                        </section>
                    <?php endforeach; ?>
                </div>
                <p class="hx-muted" id="hx-cutoff">Fecha de corte pendiente</p>
                <p class="hx-muted">Los registros sin historial verificable solo se incluyen en los contadores.</p>
                <div id="hx-status" class="hx-status" role="status" aria-live="polite">Preparando consulta…</div>
                <div class="hx-tabs" role="tablist" aria-label="Vista de Estados Helix"><button type="button"
                        id="hx-inc-tab" role="tab" aria-selected="true"
                        aria-controls="hx-view">Incidentes</button><button type="button" id="hx-tas-tab" role="tab"
                        aria-selected="false" aria-controls="hx-view" tabindex="-1">Tareas por INC</button></div>
                <div class="hx-toolbar">
                    <label class="hx-search">Buscar INC, TAS, título o grupo<input id="hx-search" type="search"
                            placeholder="Identificador, título o grupo" autocomplete="off"></label>
                    <label>Estado<select id="hx-state">
                            <option value="">Todos los estados</option>
                        </select></label>
                    <label>Categoría<select id="hx-category">
                            <option value="">Todas las categorías</option>
                        </select></label>
                    <label>Orden<select id="hx-sort">
                            <option value="desc">Mayor tiempo primero</option>
                            <option value="asc">Menor tiempo primero</option>
                            <option value="id">Identificador</option>
                        </select></label>
                    <button type="button" id="hx-export" disabled>Exportar CSV</button><button type="button"
                        id="hx-refresh" class="hx-primary">Actualizar</button>
                </div>
                <div class="hx-workspace" id="hx-workspace">
                    <section id="hx-view" role="tabpanel" aria-labelledby="hx-inc-tab" class="hx-panel hx-results"
                        tabindex="0">
                        <div class="hx-scroll" tabindex="0" role="region"
                            aria-label="Resultados; desplazamiento de tabla">
                            <table>
                                <thead id="hx-head"></thead>
                                <tbody id="hx-rows"></tbody>
                            </table>
                        </div>
                        <p id="hx-empty" class="hx-empty" hidden></p>
                        <div class="hx-pagination"><span id="hx-page" class="hx-muted"></span><button type="button"
                                id="hx-prev" disabled>Anterior</button><button type="button" id="hx-next"
                                disabled>Siguiente</button></div>
                    </section>
                    <aside id="hx-detail" class="hx-panel" aria-labelledby="hx-detail-title" hidden>
                        <div class="hx-detail-heading">
                            <h3 id="hx-detail-title">Detalle del incidente</h3><button type="button"
                                id="hx-detail-close">Cerrar</button>
                        </div>
                        <div id="hx-detail-body"></div>
                    </aside>
                </div>

                <dialog id="hx-dialog" aria-labelledby="hx-dialog-title">
                    <div class="hx-detail-heading">
                        <h3 id="hx-dialog-title">Evidencia del estado actual</h3><button type="button"
                            id="hx-dialog-close" autofocus>Cerrar</button>
                    </div>
                    <div id="hx-evidence"></div>
                </dialog>
            </div>
            <?php require __DIR__ . '/components/footer.php'; ?>
        </main>
    </div>
    <script src="assets/js/sidebar.js" defer></script>
    <script src="assets/js/estados-helix.js?v=20261019" defer></script>
</body>

</html>