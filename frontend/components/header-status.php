<?php /* RKP_HEADER_ROUTINES_V1: shared browser controller, included by header.php. */ ?>
<script>
(() => {
    'use strict';
    if (window.RKPHeaderStatus) return;
    const definitions = {
        'index.php': ['caidas', 'saturacion', 'crc', 'temperatura', 'perdida_latencia'],
        'hfc.php': ['hfc'],
        'intermitencias.php': ['intermitencias', 'puertos_duplicados'],
        // The current DOCSIS service is an explicit placeholder without a real source.
        'puertos-docsis.php': [],
        'recursos-zte.php': ['recursos_zte'],
        'agotamiento-ip.php': ['intermitencias_ftth'],
        'cmts-inits.php': ['cmts_inits'],
        'estados-helix.php': ['estados_helix'],
        'dashboard-hfc.php': ['hfc_cmts', 'netcool', 'qoe'],
    };
    let page = location.pathname.split('/').pop() || 'index.php';
    // configuracion.php currently includes the operational index.
    if (page === 'configuracion.php') page = 'index.php';
    const state = new Map((definitions[page] || []).map(key => [key, {ok: null, date: null}]));
    const endpointKeys = {
        'gkp.php': ['caidas', 'saturacion', 'crc'],
        'temperatura.php': ['temperatura'], 'perdida_latencia.php': ['perdida_latencia'],
        'hfc.php': ['hfc'], 'intermitencias.php': ['intermitencias'],
        'puertos_duplicados.php': ['puertos_duplicados'], 'puertos_docsis.php': ['puertos_docsis'],
        'recursos_zte.php': ['recursos_zte'], 'intermitencias_ftth.php': ['intermitencias_ftth'],
        'estados_helix.php': ['estados_helix'],
    };
    function stamp(value) {
        if (typeof value !== 'string' || !/^\d{4}-\d\d-\d\d[T ]\d\d:\d\d/.test(value)) return null;
        // Naive API datetimes use UTC (same convention as the INIT exporter).
        const normalized = /(?:Z|[+-]\d\d:\d\d)$/.test(value) ? value : value.replace(' ', 'T') + 'Z';
        const ts = Date.parse(normalized);
        return Number.isFinite(ts) ? ts : null;
    }
    function dateOf(payload) {
        for (const container of [payload, payload?.data, payload?.meta]) {
            for (const key of ['fecha_corte', 'generado_en', 'actualizado_en', 'updated_at_iso', 'updated_at', 'last_completed_at', 'fecha']) {
                const ts = stamp(container?.[key]);
                if (ts !== null) return ts;
            }
        }
        return null;
    }
    function set(key, ok, date = null) {
        if (!state.has(key)) return;
        const old = state.get(key);
        // Preserve last published timestamp when the next read fails.
        state.set(key, {ok, date: date ?? old.date});
    }
    function render() {
        const sources = document.getElementById('rkp-header-sources');
        const time = document.getElementById('rkp-header-datetime');
        if (!sources || !time) return;
        const entries = [...state.entries()];
        const good = entries.filter(([, v]) => v.ok === true).length;
        const pending = entries.filter(([, v]) => v.ok === null).length;
        const text = entries.length ? `${good} / ${entries.length} disponibles` : 'Sin fuentes configuradas';
        if (sources.textContent !== text) sources.textContent = text;
        sources.title = entries.map(([key, value]) => `${key}: ${value.ok === null ? 'pendiente' : value.ok ? 'disponible' : 'no disponible'}`).join('\n');
        const dates = entries.map(([, v]) => v.date).filter(v => v !== null);
        // Conservative cutoff: the oldest published source in this combined view.
        let label = !entries.length ? 'No aplica' : pending ? 'Pendiente' : 'Fecha no informada';
        if (entries.length && dates.length === entries.length) label = new Date(Math.min(...dates)).toLocaleString('es-CO', {timeZone:'America/Bogota'});
        if (time.textContent !== label) time.textContent = label;
        time.title = entries.map(([key, v]) => `${key}: ${v.date === null ? 'sin fecha publicada' : new Date(v.date).toLocaleString('es-CO', {timeZone:'America/Bogota'})}`).join('\n');
    }
    function route(input, options) {
        try {
            const url = new URL(input instanceof Request ? input.url : String(input), location.href);
            if (url.origin !== location.origin || !url.pathname.includes('/backend/api/')) return null;
            const method = String(options?.method || (input instanceof Request ? input.method : 'GET')).toUpperCase();
            if (method !== 'GET') return null;
            const name = url.pathname.split('/').pop();
            if (name === 'cmts_inits.php') return url.searchParams.get('accion') === 'actual' ? {keys:['cmts_inits']} : null;
            if (name === 'dashboard_hfc.php') {
                const action = url.searchParams.get('action') || 'estado';
                if (action === 'actualizaciones') return {keys:['hfc_cmts','netcool'], action};
                if (action === 'qoe_actualizacion') return {keys:['qoe'], action};
                if (['analytics','analytics_proxy','rf_proxy'].includes(action) && (url.searchParams.get('resource') || url.searchParams.get('op') || 'resumen') === 'resumen') {
                    const key = action === 'rf_proxy' ? 'rf' : 'analytics';
                    if (page !== 'dashboard-hfc.php') return null;
                    if (!state.has(key)) state.set(key, {ok:null, date:null});
                    return {keys:[key], action};
                }
                return null;
            }
            const keys = endpointKeys[name];
            return keys?.some(key => state.has(key)) ? {keys} : null;
        } catch { return null; }
    }
    function accept(info, payload, httpOk) {
        if (info.action === 'actualizaciones') {
            for (const [key, source] of [['hfc_cmts',payload.cmts || payload.estado_red],['netcool',payload.netcool]]) {
                set(key, httpOk && payload.ok === true && source?.existe === true, stamp(source?.iso));
            }
        } else if (info.action === 'qoe_actualizacion') {
            const data = payload.data || payload;
            set('qoe', httpOk && payload.ok !== false && data.available === true, stamp(data.updated_at_iso));
        } else {
            for (const key of info.keys) {
                const meta = payload._rkp_header?.sources?.[key];
                const available = meta?.ok ?? payload.sources?.[key]?.ok ?? (info.action ? payload.ok !== false : payload.ok);
                set(key, httpOk && available === true, meta ? stamp(meta.updated_at) : dateOf(payload));
            }
        }
        render();
    }
    const originalFetch = window.fetch.bind(window);
    window.fetch = function(input, options) {
        const info = route(input, options);
        const result = originalFetch(input, options);
        if (info) {
            // Observe a clone; never consume or delay the module's own response.
            result.then(response => response.clone().json().then(payload => accept(info, payload, response.ok)))
                .catch(() => { for (const key of info.keys) set(key, false); render(); });
        }
        return result;
    };
    window.RKPHeaderStatus = {render};
    document.addEventListener('DOMContentLoaded', render, {once:true});
    render();
})();
</script>
