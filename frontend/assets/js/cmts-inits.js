(() => {
    'use strict';
    const $ = (id) => document.getElementById(id);
    const endpoint = new URL('../backend/api/cmts_inits.php', window.location.href);
    const nodes = {
        run: $('init-run-state'), last: $('init-last-run'), notice: $('init-notice'), rows: $('init-rows'), empty: $('init-empty'),
        total: $('init-total-cmts'), success: $('init-success'), failed: $('init-failed'), sum: $('init-total-init'), search: $('init-search'),
        refresh: $('init-refresh'), export: $('init-export'), filter: $('init-filter'), top: $('init-top'), select: $('init-trend-cmts'), canvas: $('init-trend'),
        trendEmpty: $('init-trend-empty'), history: $('init-history-rows'), historyMeta: $('init-history-meta'), prev: $('init-history-prev'), next: $('init-history-next'),
        historyCmts: $('init-history-cmts'), historyFrom: $('init-history-from'), historyTo: $('init-history-to')
    };
    let current = [], historyOffset = 0, historyTotal = 0, sortKey = 'total_init', sortDirection = -1;
    let pollTimer = 0, controller = null, active = true, destroyed = false, busy = false;
    const number = new Intl.NumberFormat('es-CO');
    const date = (value) => value ? new Date(value).toLocaleString('es-CO', { timeZone: 'America/Bogota', dateStyle: 'short', timeStyle: 'short' }) : '—';
    const api = async (action, params = {}, options = {}) => {
        const url = new URL(endpoint); url.searchParams.set('accion', action);
        Object.entries(params).forEach(([key, value]) => { if (value !== '' && value != null) url.searchParams.set(key, value); });
        const response = await fetch(url, { cache: 'no-store', signal: controller?.signal, ...options });
        const payload = options.method === 'POST' ? await response.json() : (action === 'exportar' ? response : await response.json());
        if (!response.ok || (action !== 'exportar' && payload.ok !== true)) throw new Error(payload.error || 'Respuesta no disponible');
        return payload;
    };
    const notice = (text, state = '') => { nodes.notice.textContent = text; nodes.notice.dataset.state = state; };
    const badge = (text, type) => { const el = document.createElement('span'); el.className = `init-badge init-badge--${type}`; el.textContent = text; return el; };
    function render() {
        const filtered = current.filter((row) => `${row.cmts} ${row.ip}`.toLocaleLowerCase().includes(nodes.search.value.trim().toLocaleLowerCase()) && (!nodes.filter.value || (nodes.filter.value === 'error' ? !row.ok || row.total_init == null : row.estado === nodes.filter.value)));
        filtered.sort((a, b) => {
            const left = a[sortKey], right = b[sortKey];
            if (left == null) return 1; if (right == null) return -1;
            return (typeof left === 'number' ? left - right : String(left).localeCompare(String(right), 'es')) * sortDirection;
        });
        const fragment = document.createDocumentFragment();
        filtered.forEach((row) => {
            const tr = document.createElement('tr');
            const target = document.createElement('td'); const name = document.createElement('strong'); name.textContent = row.cmts; const ip = document.createElement('small'); ip.textContent = row.ip; target.append(name, ip); tr.append(target);
            const when = document.createElement('td'); when.textContent = date(row.fecha); tr.append(when);
            const total = document.createElement('td'); total.textContent = row.total_init == null ? '—' : number.format(row.total_init); tr.append(total);
            const severity = document.createElement('td'); severity.append(badge(row.estado, ({ CRITICO: 'critical', RIESGO: 'risk', ATENCION: 'attention', 'SIN INIT': 'ok', 'ERROR DE CONSULTA': 'error' })[row.estado] || 'error')); tr.append(severity);
            const result = document.createElement('td'); result.append(badge(row.ok ? 'ÉXITO' : 'FALLÓ', row.ok ? 'ok' : 'error')); tr.append(result);
            const delta = document.createElement('td'); delta.textContent = row.variacion == null ? '—' : `${row.variacion > 0 ? '+' : ''}${number.format(row.variacion)}`; delta.title = row.comparado_con ? `Contra ${date(row.comparado_con)}` : 'Sin lectura válida anterior'; tr.append(delta);
            const detail = document.createElement('td'); detail.textContent = row.error || '—'; detail.title = row.error || '';
            const probe = document.createElement('button'); probe.type = 'button'; probe.className = 'init-probe'; probe.dataset.probe = row.cmts; probe.textContent = 'Probar'; probe.setAttribute('aria-label', `Probar consulta de ${row.cmts}`); detail.append(document.createElement('br'), probe); tr.append(detail);
            fragment.append(tr);
        });
        nodes.rows.replaceChildren(fragment); nodes.empty.hidden = filtered.length > 0;
        nodes.total.textContent = number.format(current.length); nodes.success.textContent = number.format(current.filter((x) => x.ok && x.total_init != null).length);
        nodes.failed.textContent = number.format(current.filter((x) => !x.ok || x.total_init == null).length);
        nodes.sum.textContent = number.format(current.filter((x) => x.ok && x.total_init != null).reduce((sum, row) => sum + row.total_init, 0));
        nodes.last.textContent = current.length ? `Última lectura: ${date(current[0].fecha)}` : 'Sin mediciones';
        const top = [...current].filter((x) => x.ok && x.total_init != null).sort((a, b) => b.total_init - a.total_init).slice(0, 10);
        nodes.top.replaceChildren(...top.map((row) => { const li = document.createElement('li'); li.textContent = row.cmts; const value = document.createElement('span'); value.textContent = number.format(row.total_init); li.append(value); return li; }));
        const prior = nodes.select.value; nodes.select.replaceChildren(...current.map((row) => { const option = document.createElement('option'); option.value = row.cmts; option.textContent = row.cmts; return option; }));
        if (current.some((row) => row.cmts === prior)) nodes.select.value = prior;
        if (nodes.select.value) loadTrend(nodes.select.value);
    }
    async function loadActual(preserve = true) {
        try {
            const payload = await api('actual'); const data = payload.data || {};
            if (!Array.isArray(data.items)) throw new Error('Formato de lectura inválido');
            current = data.items; render();
            if (current.length) { nodes.run.textContent = 'Lectura publicada'; notice('Mostrando el último ciclo global terminado.'); }
            else { nodes.run.textContent = 'Sin mediciones'; notice('El recolector aún no ha publicado un ciclo completo.'); }
        } catch (error) {
            if (!preserve) current = [];
            notice(error.message || 'No se pudo leer la última medición.', 'error');
        }
    }
    async function loadStatus() {
        try {
            const payload = await api('estado'); const data = payload.data || {}; const progress = data.progreso || {};
            if (data.active) {
                nodes.run.textContent = progress.alcance === 'equipo' ? `Probando ${progress.cmts || data.cmts_activo}` : (progress.total ? `Actualizando ${progress.completed || 0}/${progress.total}` : 'Actualizando…');
                notice(`Consulta en curso. Último ciclo global terminado: ${date(data.last_completed_at)}.`, 'loading'); schedulePoll();
            } else if (progress.estado === 'error') { nodes.run.textContent = 'Último ciclo falló'; notice(progress.error || 'Falló la consulta; se conserva el ciclo publicado.', 'error'); }
            else if (data.enabled !== true) { nodes.run.textContent = 'Recolector deshabilitado'; }
            else { nodes.run.textContent = 'Disponible'; }
            return data;
        } catch (error) { notice(error.message || 'No se pudo leer el estado del recolector.', 'error'); return null; }
    }
    function schedulePoll() { clearTimeout(pollTimer); if (active && !document.hidden && !destroyed) pollTimer = setTimeout(poll, 5000); }
    async function poll() {
        const data = await loadStatus();
        if (data && !data.active) {
            await loadActual(); await loadHistory();
            const progress = data.progreso || {}; const probe = data.last_probe;
            if (progress.alcance === 'equipo' && progress.estado === 'completo' && probe?.run_id === progress.run_id) {
                notice(`Prueba individual completada: ${probe.cmts} · ${probe.estado}. El ciclo global se conserva.`);
            }
        } else if (data) schedulePoll();
    }
    async function start() {
        if (busy) return; busy = true; nodes.refresh.disabled = true; controller?.abort(); controller = new AbortController();
        notice('Solicitando un ciclo global…', 'loading');
        try { await api('actualizar', {}, { method: 'POST' }); nodes.run.textContent = 'Actualizando…'; schedulePoll(); }
        catch (error) { notice(error.message || 'No se pudo iniciar el ciclo.', 'error'); }
        finally { busy = false; nodes.refresh.disabled = false; }
    }
    async function startProbe(cmts) {
        if (busy) return; busy = true; nodes.refresh.disabled = true; notice(`Iniciando prueba individual de ${cmts}…`, 'loading');
        try { const payload = await api('probar', { cmts }, { method: 'POST' }); notice(`Prueba individual ${payload.estado}: ${cmts}. No reemplaza el ciclo global.`, 'loading'); schedulePoll(); }
        catch (error) { notice(error.message || `No se pudo probar ${cmts}.`, 'error'); }
        finally { busy = false; nodes.refresh.disabled = false; }
    }
    async function loadHistory() {
        try {
            const payload = await api('historico', { limit: 100, offset: historyOffset, cmts: nodes.historyCmts.value, desde: nodes.historyFrom.value, hasta: nodes.historyTo.value }); const page = payload.data;
            historyTotal = page.total; const fragment = document.createDocumentFragment();
            page.items.forEach((row) => { const tr = document.createElement('tr'); [date(row.fecha), row.cmts, row.ip, row.total_init == null ? '—' : number.format(row.total_init), row.ok ? 'ÉXITO' : 'FALLÓ'].forEach((value) => { const td = document.createElement('td'); td.textContent = value; tr.append(td); }); fragment.append(tr); });
            nodes.history.replaceChildren(fragment); nodes.historyMeta.textContent = historyTotal ? `${number.format(historyOffset + 1)}–${number.format(Math.min(historyOffset + page.items.length, historyTotal))} de ${number.format(historyTotal)} filas` : 'Sin histórico';
            nodes.prev.disabled = historyOffset === 0; nodes.next.disabled = historyOffset + 100 >= historyTotal;
        } catch (error) { nodes.historyMeta.textContent = error.message || 'Histórico no disponible'; }
    }
    async function loadTrend(cmts) {
        if (!cmts) { nodes.trendEmpty.hidden = false; return; }
        try { const payload = await api('tendencia', { cmts, limit: 200 }); drawTrend(payload.data || []); }
        catch (_) { drawTrend([]); }
    }
    function drawTrend(data) {
        const context = nodes.canvas.getContext('2d'); const width = Math.max(320, nodes.canvas.clientWidth); const height = 180; const scale = window.devicePixelRatio || 1;
        nodes.canvas.width = width * scale; nodes.canvas.height = height * scale; context.scale(scale, scale); context.clearRect(0, 0, width, height);
        nodes.trendEmpty.hidden = data.length > 0; if (!data.length) return;
        const values = data.map((x) => x.total_init); const max = Math.max(1, ...values); const pad = { left: 34, right: 10, top: 12, bottom: 24 }; const w = width - pad.left - pad.right; const h = height - pad.top - pad.bottom;
        context.strokeStyle = '#d8e1e9'; context.lineWidth = 1; context.fillStyle = '#64728a'; context.font = '10px Segoe UI, sans-serif';
        for (let i = 0; i <= 4; i += 1) { const y = pad.top + h * i / 4; context.beginPath(); context.moveTo(pad.left, y); context.lineTo(width - pad.right, y); context.stroke(); context.fillText(number.format(Math.round(max * (4 - i) / 4)), 2, y + 3); }
        context.strokeStyle = '#0876ce'; context.lineWidth = 2; context.beginPath();
        data.forEach((point, index) => { const x = pad.left + w * (data.length === 1 ? .5 : index / (data.length - 1)); const y = pad.top + h * (1 - point.total_init / max); if (index === 0) context.moveTo(x, y); else context.lineTo(x, y); }); context.stroke();
    }
    async function exportCsv() {
        try { const response = await api('exportar'); const blob = await response.blob(); const link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = 'cmts-init-historico.csv'; link.click(); URL.revokeObjectURL(link.href); }
        catch (error) { notice(error.message || 'No se pudo exportar el histórico.', 'error'); }
    }
    const handlers = [
        [nodes.search, 'input', render], [nodes.filter, 'change', render], [nodes.refresh, 'click', start], [nodes.export, 'click', exportCsv],
        [nodes.select, 'change', () => loadTrend(nodes.select.value)], [nodes.prev, 'click', () => { historyOffset = Math.max(0, historyOffset - 100); loadHistory(); }],
        [nodes.next, 'click', () => { historyOffset += 100; loadHistory(); }],
        [nodes.historyCmts, 'input', () => { historyOffset = 0; loadHistory(); }], [nodes.historyFrom, 'change', () => { historyOffset = 0; loadHistory(); }],
        [nodes.historyTo, 'change', () => { historyOffset = 0; loadHistory(); }]
    ];
    const probeClick = (event) => { const button = event.target.closest('[data-probe]'); if (button) startProbe(button.dataset.probe); };
    handlers.push([nodes.rows, 'click', probeClick]);
    document.querySelectorAll('[data-sort]').forEach((button) => handlers.push([button, 'click', () => { const next = button.dataset.sort; sortDirection = sortKey === next ? -sortDirection : (next === 'total_init' || next === 'variacion' ? -1 : 1); sortKey = next; render(); }]));
    handlers.forEach(([node, event, fn]) => node.addEventListener(event, fn));
    const visibility = () => { active = !document.hidden; if (active) { loadStatus().then((data) => { if (data?.active) schedulePoll(); }); } else clearTimeout(pollTimer); };
    const resize = () => { if (nodes.select.value) loadTrend(nodes.select.value); };
    const cleanup = () => { destroyed = true; clearTimeout(pollTimer); controller?.abort(); handlers.forEach(([node, event, fn]) => node.removeEventListener(event, fn)); document.removeEventListener('visibilitychange', visibility); window.removeEventListener('resize', resize); window.removeEventListener('pagehide', cleanup); };
    document.addEventListener('visibilitychange', visibility); window.addEventListener('resize', resize); window.addEventListener('pagehide', cleanup, { once: true });
    Promise.all([loadActual(), loadStatus(), loadHistory()]);
})();
