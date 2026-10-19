<?php declare(strict_types=1); ?>
<!doctype html>
<html lang="es">

<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>RKP | Estados Helix</title>
    <link rel="stylesheet" href="assets/css/style.css">
    <link rel="stylesheet" href="assets/css/sidebar.css">
    <link rel="stylesheet" href="assets/css/gkp.css?v=20261009">
    <link rel="stylesheet" href="assets/css/module-page.css?v=20261009">
    <style>
        .helix-estados-page .app {
            height: auto;
            min-height: 100dvh;
            overflow: visible
        }

        .helix-estados-page .main {
            min-width: 0;
            height: auto;
            overflow: visible
        }

        .helix-estados {
            color: var(--gkp-ink);
            gap: 12px;
            min-width: 0
        }

        .helix-estados .hx-summary {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 12px
        }

        .helix-estados .hx-panel {
            min-width: 0;
            max-width: 100%;
            background: var(--gkp-surface);
            border: 1px solid var(--gkp-line);
            border-radius: 12px;
            padding: 14px
        }

        .helix-estados h2,
        .helix-estados h3,
        .helix-estados p {
            margin: 0
        }

        .helix-estados h2 {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            letter-spacing: .04em
        }

        .helix-estados svg {
            width: 18px;
            height: 18px;
            fill: none;
            stroke: currentColor;
            stroke-width: 1.7;
            flex-shrink: 0
        }

        .helix-estados .hx-numbers {
            display: grid;
            grid-template-columns: .8fr 1fr 1fr;
            gap: 10px;
            margin: 12px 0
        }

        .helix-estados .hx-numbers>div+div {
            border-left: 1px solid var(--gkp-line);
            padding-left: 12px
        }

        .helix-estados .hx-numbers strong {
            display: block;
            font-size: 22px;
            line-height: 1.2;
            font-variant-numeric: tabular-nums
        }

        .helix-estados .hx-numbers span,
        .helix-estados .hx-muted {
            font-size: 12px;
            color: var(--gkp-muted)
        }

        .helix-estados .hx-good {
            color: var(--gkp-green-strong)
        }

        .helix-estados .hx-warn {
            color: #885b12
        }

        .helix-estados .hx-toolbar,
        .helix-estados .hx-tabs,
        .helix-estados .hx-pagination {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 10px
        }

        .helix-estados .hx-toolbar {
            align-items: end
        }

        .helix-estados label {
            display: grid;
            gap: 4px;
            font-size: 12px;
            min-width: 0
        }

        .helix-estados .hx-search {
            flex: 1 1 220px
        }

        .helix-estados input,
        .helix-estados select,
        .helix-estados button {
            font: inherit;
            font-size: 12px;
            min-height: 36px;
            padding: 7px 10px;
            color: var(--gkp-ink);
            background: var(--gkp-surface);
            border: 1px solid var(--gkp-line);
            border-radius: 7px;
            max-width: 100%
        }

        .helix-estados button {
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 6px
        }

        .helix-estados button:hover {
            border-color: var(--gkp-green)
        }

        .helix-estados .hx-primary,
        .helix-estados [role=tab][aria-selected=true] {
            background: var(--gkp-green-strong);
            color: white;
            border-color: var(--gkp-green-strong)
        }

        .helix-estados button:disabled {
            opacity: .55;
            cursor: default
        }

        .helix-estados :focus-visible {
            outline: 2px solid var(--gkp-green);
            outline-offset: 3px
        }

        .helix-estados .hx-status {
            font-size: 13px;
            line-height: 1.5;
            padding: 10px 12px;
            border-left: 1px solid var(--gkp-line)
        }

        .helix-estados .hx-status[data-state=error] {
            color: #9a2534;
            border-color: #9a2534;
            background: #fff1f2
        }

        .helix-estados .hx-status[data-state=loading] {
            color: #805a0b;
            border-color: #b38020
        }

        .helix-estados .hx-results {
            padding: 0;
            overflow: hidden
        }

        .helix-estados .hx-scroll {
            max-width: 100%;
            max-height: 60vh;
            overflow: auto
        }

        .helix-estados table {
            width: 100%;
            min-width: 780px;
            border-collapse: collapse;
            font-size: 12px;
            text-align: left
        }

        .helix-estados th {
            position: sticky;
            top: 0;
            z-index: 1;
            background: var(--gkp-paper);
            font-size: 11px;
            color: var(--gkp-ink-2)
        }

        .helix-estados th,
        .helix-estados td {
            padding: 10px 12px;
            border-bottom: 1px solid var(--gkp-line-soft);
            vertical-align: top
        }

        .helix-estados td {
            font-size: 12px;
            color: var(--gkp-ink);
            line-height: 1.5
        }

        .helix-estados td:first-child {
            max-width: 320px;
            min-width: 220px;
            overflow-wrap: anywhere
        }

        .helix-estados td strong,
        .helix-estados td small {
            display: block
        }

        .helix-estados td small {
            font-size: 12px;
            color: var(--gkp-ink-2);
            margin-top: 4px;
            line-height: 1.4;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden
        }

        .helix-estados .hx-time {
            white-space: nowrap;
            font-variant-numeric: tabular-nums;
            font-weight: 600
        }

        .helix-estados .hx-eye {
            color: var(--gkp-green-strong);
            padding: 7px
        }

        .helix-estados .hx-expanded>td {
            background: var(--gkp-paper);
            padding: 16px
        }

        .helix-estados .hx-detail-heading {
            display: flex;
            justify-content: space-between;
            gap: 12px;
            align-items: center;
            margin-bottom: 12px
        }

        .helix-estados h3 {
            font-size: 15px
        }

        .helix-estados dl {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 12px;
            margin: 12px 0
        }

        .helix-estados dt {
            font-size: 11px;
            color: var(--gkp-muted)
        }

        .helix-estados dd {
            margin: 3px 0 0;
            white-space: pre-wrap;
            overflow-wrap: anywhere;
            font-size: 13px
        }

        .helix-estados .hx-pagination {
            padding: 10px 12px;
            justify-content: flex-end
        }

        .helix-estados .hx-empty {
            padding: 26px 14px;
            color: var(--gkp-muted);
            font-size: 13px
        }

        .helix-estados dialog {
            width: min(720px, calc(100% - 24px));
            max-height: 85dvh;
            overflow: auto;
            padding: 20px;
            color: var(--gkp-ink);
            background: var(--gkp-surface);
            border: 1px solid var(--gkp-line);
            border-radius: 12px
        }

        .helix-estados dialog::backdrop {
            background: rgba(3, 5, 8, .6)
        }

        .helix-estados dialog p {
            white-space: pre-wrap;
            overflow-wrap: anywhere;
            font-size: 13px;
            line-height: 1.5
        }

        .helix-estados [hidden] {
            display: none !important
        }

        /* Mantener el fondo y resaltar únicamente el texto. */
        .helix-estados tbody tr:hover {
            background: transparent;
        }

        .helix-estados tbody tr:hover td,
        .helix-estados tbody tr:hover td small {
            font-weight: 700;
        }

        .helix-estados tbody tr:hover td strong {
            font-weight: 900;
        }

        /* Detalle lateral derecho. */
        .helix-estados #hx-detail {
            position: fixed;
            inset: 0 0 0 auto;
            margin: 0;
            box-sizing: border-box;
            width: min(880px, 94vw);
            max-width: 100vw;
            height: 100dvh;
            max-height: 100dvh;
            padding: 20px;
            overflow: auto;
            color: var(--gkp-ink);
            background: var(--gkp-surface);
            border: 0;
            border-left: 1px solid var(--gkp-line);
            border-radius: 14px 0 0 14px;
            box-shadow: -12px 0 36px rgba(0, 0, 0, .12);
        }

        .helix-estados #hx-detail::backdrop {
            background: rgba(20, 40, 30, .15);
        }

        .helix-estados #hx-detail .hx-detail-heading {
            position: sticky;
            top: -20px;
            z-index: 2;
            padding: 14px 0;
            background: var(--gkp-surface);
        }

        .helix-estados #hx-detail .hx-scroll {
            margin-top: 12px;
        }

        @media (max-width: 760px) {
            .helix-estados #hx-detail {
                width: 100vw;
                border-radius: 0;
            }
        }

        @media(max-width:760px) {
            .helix-estados .hx-summary {
                grid-template-columns: 1fr
            }

            .helix-estados .hx-toolbar>label {
                flex: 1 1 160px
            }

            .helix-estados dl {
                grid-template-columns: 1fr
            }

            .helix-estados .hx-numbers strong {
                font-size: 20px
            }
        }

        /* RKP_HELIX_DOS_TABLAS_V1 */
        .helix-estados #hx-cutoff,
        .helix-estados #hx-cutoff+p.hx-muted,
        .helix-estados #hx-status[data-state=success] {
            display: none !important
        }

        .helix-estados tbody tr:hover {
            background: transparent !important
        }

        .helix-estados tbody tr:hover td,
        .helix-estados tbody tr:hover td small {
            font-weight: 700
        }

        .helix-estados tbody tr:hover td strong {
            font-weight: 900
        }

        .helix-estados .hx-workspace {
            display: grid;
            grid-template-columns: minmax(0, 1fr);
            gap: 12px;
            min-width: 0;
            align-items: start
        }

        .helix-estados .hx-workspace.has-detail {
            grid-template-columns: repeat(2, minmax(0, 1fr))
        }

        .helix-estados #hx-view {
            min-width: 0
        }

        .helix-estados #hx-detail {
            position: static !important;
            inset: auto !important;
            margin: 0 !important;
            width: auto !important;
            height: auto !important;
            min-width: 0;
            max-width: 100% !important;
            max-height: 75dvh !important;
            overflow: auto;
            padding: 14px;
            border: 1px solid var(--gkp-line) !important;
            border-radius: 12px !important;
            box-shadow: none !important;
            background: var(--gkp-surface);
            color: var(--gkp-ink)
        }

        .helix-estados #hx-detail[hidden] {
            display: none !important
        }

        .helix-estados #hx-detail .hx-detail-heading {
            position: static !important;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            margin-bottom: 12px
        }

        .helix-estados #hx-detail-body>h3 {
            margin: 16px 0 10px
        }

        .helix-estados #hx-detail .hx-scroll {
            max-height: 48dvh
        }

        @media(max-width:1000px) {
            .helix-estados .hx-workspace.has-detail {
                grid-template-columns: repeat(2, minmax(360px, 1fr));
                overflow-x: auto
            }
        }
    </style>
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
    <script>
        (() => {
            'use strict';
            const root = document.getElementById('helix-estados');
            const $ = id => root.querySelector('#hx-' + id);
            const eye = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>';
            const node = (tag, text, cls) => { const n = document.createElement(tag); if (text != null) n.textContent = String(text); if (cls) n.className = cls; return n; };
            const verified = r => r && r.tiempo_estado_verificable === true && typeof r.segundos_en_estado === 'number' && Number.isFinite(r.segundos_en_estado) && r.segundos_en_estado >= 0;
            const unique = rows => [...new Map(rows.filter(r => r && typeof r.numero === 'string' && r.numero).map(r => [r.numero, r])).values()];
            const tasks = inc => unique(Array.isArray(inc.tareas) ? inc.tareas.filter(verified) : []);
            const normalize = v => String(v ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('es');
            const matches = (r, q) => [r.numero, r.titulo, r.grupo_soporte].some(v => normalize(v).includes(q));
            const duration = seconds => { const n = Math.floor(seconds); return `${Math.floor(n / 86400)}d ${Math.floor(n % 86400 / 3600)}h ${Math.floor(n % 3600 / 60)}min`; };
            const date = value => { if (value == null || value === '') return 'No disponible'; const d = new Date(typeof value === 'number' ? value * 1000 : value); return Number.isFinite(d.getTime()) ? new Intl.DateTimeFormat('es-CO', { timeZone: 'America/Bogota', dateStyle: 'medium', timeStyle: 'medium' }).format(d) : 'No disponible'; };
            let payload = null, incidents = [], tab = 'inc', page = 0, busy = false, expanded = null, visible = [], trigger = null;
            const pageSize = 30;
            function button(label, action, isEye = false) {
                const b = node('button', isEye ? null : label, isEye ? 'hx-eye' : ''); b.type = 'button';
                if (isEye) { b.innerHTML = eye; b.setAttribute('aria-label', label); }
                b.addEventListener('click', action); return b;
            }
            function evidence(record, target) {
                target.replaceChildren(node('p', `${record.numero} · ${record.titulo || 'Sin título'}`));
                const dl = node('dl');
                const fields = [['Estado actual', record.estado], ['Entrada al estado (Bogotá)', date(record.fecha_entrada_estado_epoch ?? record.fecha_entrada_estado)], ['Tiempo al corte', duration(record.segundos_en_estado)], ['Grupo de soporte', record.grupo_soporte], ['Fuente de verificación', record.fuente_tiempo_estado], ['Worklog de entrada', record.worklog_entrada_estado], ['Tipo de relación', record.relacion]];
                for (const [label, value] of fields) { if (value == null || value === '') continue; dl.append(node('div')); const item = dl.lastChild; item.append(node('dt', label), node('dd', value)); }
                target.append(dl, node('p', 'Evidencia de entrada al estado actual; la API no entrega una secuencia completa de transiciones.', 'hx-muted'));
            }
            function openEvidence(record, b) { trigger = b; evidence(record, $('evidence')); $('dialog').showModal(); }
            $('dialog-close').addEventListener('click', () => $('dialog').close());
            $('dialog').addEventListener('close', () => { if (trigger?.isConnected) trigger.focus(); });
            let detailTrigger = null;
            function closeDetail(restoreFocus = true) {
                $('detail').hidden = true;
                $('workspace').classList.remove('has-detail');
                if (restoreFocus && detailTrigger?.isConnected) detailTrigger.focus();
            }
            function openDetail(result, b) {
                detailTrigger = b;
                const i = result.inc, body = $('detail-body');
                $('detail-title').textContent = `Detalle de ${i.numero}`;
                body.replaceChildren();
                const info = node('div');
                evidence(i, info);
                info.prepend(node('h3', 'Evidencia del estado actual'));
                body.append(info, node('h3', `Tareas de ${i.numero}`));
                if (result.tasks.length) body.append(taskTable(result.tasks));
                else body.append(node('p', 'Este INC no tiene TAS verificables relacionadas.', 'hx-muted'));
                if (tab === 'tas' && ($('search').value.trim() || $('state').value)) body.append(node('p', 'Filtro activo: se muestran únicamente las TAS coincidentes.', 'hx-muted'));
                root.querySelectorAll('#hx-rows .hx-eye').forEach(eyeButton => eyeButton.setAttribute('aria-expanded', String(eyeButton === b)));
                $('detail').hidden = false;
                $('workspace').classList.add('has-detail');
                $('detail').scrollTop = 0;
            }
            $('detail-close').addEventListener('click', () => {
                closeDetail();
                root.querySelectorAll('#hx-rows .hx-eye').forEach(b => b.setAttribute('aria-expanded', 'false'));
            });
            root.addEventListener('keydown', event => {
                if (event.key === 'Escape' && !$('detail').hidden && !$('dialog').open) {
                    $('detail-close').click();
                }
            });
            function titleCell(record) { const td = node('td'); td.append(node('strong', record.numero), node('small', record.titulo || 'Sin título')); return td; }
            function taskTable(rows) {
                const wrap = node('div', null, 'hx-scroll'); wrap.tabIndex = 0; wrap.setAttribute('role', 'region'); wrap.setAttribute('aria-label', 'Tareas verificables relacionadas');
                const table = node('table'), head = node('thead'), tr = node('tr'), body = node('tbody');
                ['TAS / título', 'Estado actual', 'Tiempo en estado', 'Grupo de soporte', 'Relación', 'Evidencia'].forEach(t => { const th = node('th', t); th.scope = 'col'; tr.append(th); }); head.append(tr);
                for (const t of rows) { const row = node('tr'); row.append(titleCell(t), node('td', t.estado), node('td', duration(t.segundos_en_estado), 'hx-time'), node('td', t.grupo_soporte || '—'), node('td', t.relacion || '—')); const td = node('td'); const b = button(`Ver evidencia de ${t.numero}`, () => openEvidence(t, b), true); b.setAttribute('aria-haspopup', 'dialog'); td.append(b); row.append(td); body.append(row); }
                table.append(head, body); wrap.append(table); return wrap;
            }
            function categoryValues(record) {
                return [
                    record.categoria_operacional_nivel_1,
                    record.categoria_operacional_nivel_2,
                    record.categoria_operacional_nivel_3,
                ]
                    .map(value => String(value ?? '').trim())
                    .filter(Boolean);
            }

            function categories() {
                const previous = $('category').value;
                const values = new Map();

                for (const incident of incidents) {
                    for (const value of categoryValues(incident)) {
                        const key = normalize(value);
                        if (!values.has(key)) values.set(key, value);
                    }
                }

                const options = [...values.entries()].sort(
                    (a, b) => a[1].localeCompare(b[1], 'es')
                );

                $('category').replaceChildren(
                    new Option('Todas las categorías', ''),
                    ...options.map(([key, label]) => new Option(label, key))
                );

                $('category').value = values.has(previous) ? previous : '';
            }
            function selectRows() {
                const q = normalize($('search').value.trim());
                const state = $('state').value;
                const category = $('category').value;

                const filtered = incidents.filter(incident =>
                    !category || categoryValues(incident).some(
                        value => normalize(value) === category
                    )
                );

                let rows;

                if (tab === 'inc') {
                    rows = filtered
                        .filter(i => matches(i, q) && (!state || i.estado === state))
                        .map(i => ({
                            inc: i,
                            tasks: tasks(i),
                            seconds: i.segundos_en_estado,
                        }));
                } else {
                    rows = filtered.map(i => {
                        const parentMatches = matches(i, q);
                        const children = tasks(i).filter(t =>
                            (!state || t.estado === state) &&
                            (parentMatches || matches(t, q))
                        );

                        return {
                            inc: i,
                            tasks: children,
                            seconds: children.reduce(
                                (max, t) => Math.max(max, t.segundos_en_estado),
                                0
                            ),
                        };
                    }).filter(r => r.tasks.length);
                }

                const order = $('sort').value;
                rows.sort((a, b) =>
                    (order === 'id'
                        ? 0
                        : (a.seconds - b.seconds) * (order === 'asc' ? 1 : -1)
                    ) || a.inc.numero.localeCompare(b.inc.numero)
                );

                return rows;
            }
            function render() {
                closeDetail(false);
                visible = selectRows(); page = Math.min(page, Math.max(0, Math.ceil(visible.length / pageSize) - 1));
                const head = node('tr');
                (tab === 'inc' ? ['INC / título', 'Estado actual', 'Tiempo en estado', 'Grupo de soporte', 'TAS verificables', 'Detalle'] : ['INC / título', 'TAS verificables visibles', 'Estados de TAS visibles', 'Mayor tiempo de TAS', 'Detalle']).forEach(t => { const th = node('th', t); th.scope = 'col'; head.append(th); });
                const categoryHead = node('th', 'Categoría operacional');
                categoryHead.scope = 'col';
                head.insertBefore(categoryHead, head.lastChild);
                $('head').replaceChildren(head); $('rows').replaceChildren();
                visible.slice(page * pageSize, (page + 1) * pageSize).forEach((r, index) => {
                    const row = node('tr'), i = r.inc; row.append(titleCell(i));
                    if (tab === 'inc') row.append(node('td', i.estado), node('td', duration(r.seconds), 'hx-time'), node('td', i.grupo_soporte || '—'), node('td', r.tasks.length));
                    else { const counts = new Map(); r.tasks.forEach(t => counts.set(t.estado, (counts.get(t.estado) || 0) + 1)); row.append(node('td', r.tasks.length), node('td', [...counts].map(([s, n]) => `${s}: ${n}`).join(' · ')), node('td', duration(r.seconds), 'hx-time')); }
                    const category = [
                        i.categoria_operacional_nivel_1,
                        i.categoria_operacional_nivel_2,
                        i.categoria_operacional_nivel_3,
                    ].map(value => String(value ?? '').trim())
                        .filter(Boolean)
                        .join(' > ');

                    row.append(node('td', category || '—'));

                    const control = node('td');
                    const b = button(`Ver detalle de ${i.numero}`, () => openDetail(r, b), true);
                    b.setAttribute('aria-controls', 'hx-detail');
                    b.setAttribute('aria-expanded', 'false');
                    control.append(b); row.append(control); $('rows').append(row);
                });
                $('empty').hidden = visible.length > 0 || !payload;
                $('empty').textContent = incidents.length === 0 ? 'La consulta no devolvió INC verificables que cumplan el umbral.' : (tab === 'tas' && !incidents.some(i => tasks(i).length) ? 'No hay TAS verificables relacionadas con estos INC.' : 'No hay coincidencias con los filtros actuales.');
                $('page').textContent = payload ? `${visible.length} ${tab === 'inc' ? 'INC' : 'grupos INC'}${$('search').value.trim() || $('state').value ? ' · Filtro activo' : ''} · Página ${page + 1} de ${Math.max(1, Math.ceil(visible.length / pageSize))}` : 'Sin resultado disponible';
                $('prev').disabled = page === 0; $('next').disabled = (page + 1) * pageSize >= visible.length; $('export').disabled = !visible.length;
            }
            function states() {
                const values = [...new Set(tab === 'inc' ? incidents.map(i => i.estado) : incidents.flatMap(i => tasks(i).map(t => t.estado)))].sort();
                $('state').replaceChildren(new Option('Todos los estados', ''), ...values.map(s => new Option(s, s)));
            }
            function changeTab(next) { tab = next; page = 0; expanded = null; for (const name of ['inc', 'tas']) { const b = $(name + '-tab'); b.setAttribute('aria-selected', String(name === tab)); b.tabIndex = name === tab ? 0 : -1; } $('view').setAttribute('aria-labelledby', `hx-${tab}-tab`); states(); render(); }
            for (const name of ['inc', 'tas']) { $(name + '-tab').addEventListener('click', () => changeTab(name)); $(name + '-tab').addEventListener('keydown', e => { if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(e.key)) { e.preventDefault(); changeTab(e.key === 'Home' ? 'inc' : e.key === 'End' ? 'tas' : tab === 'inc' ? 'tas' : 'inc'); $(tab + '-tab').focus(); } }); }
            for (const id of ['search', 'state', 'category', 'sort']) {
                $(id).addEventListener(
                    id === 'search' ? 'input' : 'change',
                    () => {
                        page = 0;
                        expanded = null;
                        render();
                    }
                );
            }
            $('prev').addEventListener('click', () => { page--; expanded = null; render(); }); $('next').addEventListener('click', () => { page++; expanded = null; render(); });
            const csvCell = value => { let s = String(value ?? ''); if (/^[\s\uFEFF]*[=+@-]/.test(s) || /^[\t\r\n]/.test(s)) s = "'" + s; return '"' + s.replace(/"/g, '""') + '"'; };
            $('export').addEventListener('click', () => {
                let rows;

                if (tab === 'inc') {
                    rows = [
                        [
                            'INC',
                            'Título',
                            'Estado',

                            'Tiempo en estado',
                            'Grupo de soporte',
                            'TAS verificables',
                            'Categoría operacional 1',
                            'Categoría operacional 2',
                            'Categoría operacional 3'
                        ],
                        ...visible.map(r => [
                            r.inc.numero,
                            r.inc.titulo,
                            r.inc.estado,

                            duration(r.seconds),
                            r.inc.grupo_soporte,
                            r.tasks.length,

                            // Categorías operacionales separadas
                            r.inc.categoria_operacional_nivel_1 || '',
                            r.inc.categoria_operacional_nivel_2 || '',
                            r.inc.categoria_operacional_nivel_3 || ''
                        ])
                    ];
                } else {
                    rows = [
                        [
                            'INC padre',
                            'TAS',
                            'Título',
                            'Estado',

                            'Tiempo en estado',
                            'Grupo de soporte',
                            'Relación',
                            'Categoría operacional 1',
                            'Categoría operacional 2',
                            'Categoría operacional 3'
                        ],
                        ...visible.flatMap(r =>
                            r.tasks.map(t => [
                                r.inc.numero,
                                t.numero,
                                t.titulo,
                                t.estado,

                                duration(t.segundos_en_estado),
                                t.grupo_soporte,
                                t.relacion,

                                // La categoría corresponde al INC padre
                                r.inc.categoria_operacional_nivel_1 || '',
                                r.inc.categoria_operacional_nivel_2 || '',
                                r.inc.categoria_operacional_nivel_3 || ''
                            ])
                        )
                    ];
                }

                const url = URL.createObjectURL(
                    new Blob(
                        [
                            '\uFEFF' +
                            rows
                                .map(r => r.map(csvCell).join(';'))
                                .join('\r\n')
                        ],
                        { type: 'text/csv;charset=utf-8' }
                    )
                );

                const a = node('a');
                a.href = url;
                a.download = `estados-helix-${tab}.csv`;
                a.click();

                setTimeout(() => URL.revokeObjectURL(url), 1000);
            });
            function summary(data) {
                const r = data.resumen_relaciones, count = v => Number.isInteger(v) && v >= 0 ? v : null, show = v => v == null ? 'No disponible' : String(v);
                const total = count(data.total), low = count(data.menores_de_6h);
                const partition = total !== null && low !== null && count(data.total_no_verificables) !== null && total + low + data.total_no_verificables === data.total_inc_revisados;
                $('inc-total').textContent = show(count(data.total_inc_revisados)); $('inc-yes').textContent = partition ? String(total + low) : 'No disponible'; $('inc-no').textContent = show(count(data.total_no_verificables));
                $('inc-scope').textContent = `${total ?? '—'} cumplen el umbral de ${data.umbral_horas ?? '—'} h · ${low ?? '—'} verificables por debajo del umbral. Categorías: ${(data.categorias_incluidas || []).join(', ')}.${partition ? '' : ' La respuesta no permite confirmar la partición del universo revisado.'}`;
                $('tas-total').textContent = show(count(r.total_tareas)); $('tas-yes').textContent = show(count(r.tas_tiempo_verificable)); $('tas-no').textContent = show(count(r.tas_tiempo_no_verificable));
                $('tas-scope').textContent = `TAS relacionadas con los INC del resultado. ${r.alcance || ''}`;
                $('cutoff').textContent = `Corte: ${date(data.fecha_corte)} (America/Bogota). Duraciones y estados corresponden a esta consulta.`;
            }
            async function load() {
                if (busy) return; busy = true; $('refresh').disabled = true; $('view').setAttribute('aria-busy', 'true'); $('status').dataset.state = 'loading'; $('status').textContent = 'Consultando Estados Helix… La consulta puede tardar.';
                try {
                    const response = await fetch('../backend/api/estados_helix.php', { headers: { Accept: 'application/json' }, cache: 'no-store' });
                    let data; try { data = await response.json(); } catch (_) { throw new Error('El adaptador no devolvió una respuesta JSON válida.'); }
                    if (!response.ok || data.ok !== true) throw new Error(data.error || `No se pudo completar la consulta (HTTP ${response.status}).`);
                    if (!Array.isArray(data.incidentes) || !data.resumen_relaciones || typeof data.resumen_relaciones !== 'object') throw new Error('La respuesta no contiene el contrato esperado de Estados Helix.');
                    incidents = unique(data.incidentes.filter(verified));
                    delete data.no_verificables;
                    payload = data;
                    page = 0;
                    expanded = null;
                    summary(data);
                    states();
                    categories();
                    render();
                    $('status').dataset.state = 'success'; $('status').textContent = 'Consulta completada. Filtros, detalles y exportación utilizan este resultado en memoria.';
                } catch (error) {
                    $('status').dataset.state = 'error'; $('status').textContent = `${error.message} ${payload ? 'Se conserva el resultado anterior. Corte: ' + date(payload.fecha_corte) + '.' : 'No hay un resultado válido disponible; los contadores permanecen pendientes.'}`;
                } finally { busy = false; $('refresh').disabled = false; $('view').setAttribute('aria-busy', 'false'); }
            }
            $('refresh').addEventListener('click', load); render(); load();
        })();
    </script>
</body>

</html>