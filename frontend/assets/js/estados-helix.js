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

        const i = result.inc;
        const body = $('detail-body');
        const relatedTasks = result.tasks;

        $('detail-title').textContent = 'Detalle del incidente';
        body.replaceChildren();

        // ENCABEZADO DEL INCIDENTE
        const hero = node('section', null, 'hx-detail-hero');

        const numberRow = node('div', null, 'hx-detail-number-row');
        const number = node('h2', i.numero, 'hx-detail-number');
        const status = node('span', i.estado || 'Sin estado', 'hx-detail-status');

        const statusNormalized = normalize(i.estado);
        status.dataset.tone = statusNormalized.includes('progreso')
            ? 'progress'
            : statusNormalized.includes('pendiente')
                ? 'pending'
                : 'neutral';

        numberRow.append(number, status);

        const description = node(
            'p',
            i.titulo || 'Sin título disponible',
            'hx-detail-description'
        );

        hero.append(numberRow, description);

        // CATEGORÍA OPERACIONAL
        const category = categoryValues(i);

        if (category.length) {
            const categoryBox = node('div', null, 'hx-detail-category');

            categoryBox.append(
                node('span', 'Categoría operacional'),
                node('strong', category.join(' > '))
            );

            hero.append(categoryBox);
        }

        body.append(hero);

        // EVIDENCIA ORIGINAL DE HELIX
        const info = node('section', null, 'hx-detail-evidence');
        evidence(i, info);

        // La descripción ya se muestra en el encabezado.
        // Evitamos repetirla dentro de la evidencia.
        const originalDescription = info.querySelector('p');

        if (originalDescription) {
            originalDescription.remove();
        }

        info.prepend(node('h3', 'Evidencia del estado actual'));

        body.append(info);

        // TAREAS RELACIONADAS
        const taskSection = node('section', null, 'hx-detail-tasks');
        const taskHeader = node('div', null, 'hx-detail-tasks-header');

        taskHeader.append(
            node('h3', 'Tareas relacionadas'),
            node('span', `${relatedTasks.length} TAS`, 'hx-detail-tasks-count')
        );

        taskSection.append(taskHeader);

        if (relatedTasks.length) {
            taskSection.append(taskTable(relatedTasks));
        } else {
            taskSection.append(
                node(
                    'p',
                    'Este INC no tiene TAS verificables relacionadas.',
                    'hx-detail-tasks-empty'
                )
            );
        }

        if (
            tab === 'tas' &&
            ($('search').value.trim() || $('state').value)
        ) {
            taskSection.append(
                node(
                    'p',
                    'Filtro activo: se muestran únicamente las TAS coincidentes.',
                    'hx-muted'
                )
            );
        }

        body.append(taskSection);

        // CONSERVAR COMPORTAMIENTO EXISTENTE
        root.querySelectorAll('#hx-rows .hx-eye').forEach(
            eyeButton => eyeButton.setAttribute(
                'aria-expanded',
                String(eyeButton === b)
            )
        );

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
