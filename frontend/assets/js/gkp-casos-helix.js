(() => {
    'use strict';

    const endpoint = new URL('../backend/api/olt_casos_helix.php', window.location.href);
    const known = new Map();
    let visible = new Map();
    let inFlight = false;

    function normalizarPuerto(value) {
        const text = String(value ?? '').trim();
        const slash = text.match(/^\s*(\d{1,3})\s*\/\s*(\d{1,3})\s*\/\s*(\d{1,3})\s*$/);
        let parts = slash ? slash.slice(1, 4) : null;
        if (!parts) {
            const frame = text.match(/\bFRAME\s*=\s*(\d+)\b/i);
            const slot = text.match(/(?<![A-Z0-9_])SLOT\s*=\s*(\d+)\b/i);
            const port = text.match(/\bPORT\s*=\s*(\d+)\b/i);
            if (frame && slot && port) parts = [frame[1], slot[1], port[1]];
        }
        if (!parts) return '';
        const numbers = parts.map((part) => Number(part));
        return numbers.every((number) => Number.isSafeInteger(number) && number >= 0)
            ? numbers.join('/') : '';
    }

    function oltKey(value) {
        const olt = String(value ?? '').trim().toUpperCase();
        return /^[A-Z0-9._-]{1,120}$/.test(olt) ? olt : '';
    }

    function currentCells(olt, port) {
        return Array.from(document.querySelectorAll('#gkp-rows .gkp-helix-cases'))
            .filter((cell) => cell.dataset.olt === olt && cell.dataset.puerto === port);
    }

    function paintCell(cell, state, port) {
        const prior = state?.ports.get(port);
        cell.replaceChildren();
        cell.classList.remove('gkp-helix-cases--error', 'gkp-helix-cases--empty');

        if (!state || state.estado === 'sin_solicitud' || state.estado === 'expirado') {
            cell.textContent = 'Actualizando…';
            cell.title = '';
            return;
        }
        if (state.estado === 'actualizando') {
            cell.textContent = 'Actualizando…';
            cell.title = state.consultado_en
                ? `Actualizando. Última consulta completa: ${new Date(state.consultado_en).toLocaleString()}`
                : 'Consulta aceptada; Oracle aún no ha completado el resultado';
            return;
        }
        if (state.estado === 'error') {
            cell.textContent = 'No se pudo consultar';
            cell.title = state.error?.mensaje || 'La consulta de casos Helix falló';
            cell.classList.add('gkp-helix-cases--error');
            return;
        }
        if (state.estado !== 'listo' || !prior || !Array.isArray(prior.casos)) {
            cell.textContent = 'No se pudo consultar';
            cell.title = 'La respuesta Helix no cubre este puerto';
            cell.classList.add('gkp-helix-cases--error');
            return;
        }

        if (prior.casos.length === 0) {
            cell.textContent = 'Sin INC, WO o TAS abiertos asociados';
            cell.title = 'Consulta completada: no se identificaron casos abiertos asociados a este puerto';
            cell.classList.add('gkp-helix-cases--empty');
            return;
        }

        cell.title = prior.consultado_en
            ? `Consulta completa: ${new Date(prior.consultado_en).toLocaleString()}` : '';
        const order = { INC: 0, WO: 1, TAS: 2 };
        const unique = new Map();
        for (const item of prior.casos) {
            const type = String(item?.tipo ?? '').toUpperCase();
            const number = String(item?.numero ?? '').trim();
            const status = String(item?.estado ?? '').trim();
            if (!Object.hasOwn(order, type) || !number || !status) {
                cell.textContent = 'No se pudo consultar';
                cell.title = 'La respuesta Helix contiene un caso inválido';
                cell.classList.add('gkp-helix-cases--error');
                return;
            }
            unique.set(number, { type, number, status });
        }
        const cases = Array.from(unique.values()).sort((a, b) =>
            order[a.type] - order[b.type] || a.number.localeCompare(b.number, 'en', { numeric: true })
        );
        if (!cases.length) {
            cell.textContent = 'No se encontró información';
            cell.classList.add('gkp-helix-cases--empty');
            return;
        }
        for (const item of cases) {
            const line = document.createElement('span');
            line.className = 'gkp-helix-case';
            line.textContent = `${item.number} - ${item.status}`;
            cell.append(line);
        }
    }

    function paintCurrent(olt) {
        const state = known.get(olt);
        for (const port of visible.get(olt) || []) {
            for (const cell of currentCells(olt, port)) paintCell(cell, state, port);
        }
    }

    function chunks(groups) {
        const units = [];
        for (const [olt, ports] of groups) {
            for (let offset = 0; offset < ports.length; offset += 100) {
                units.push({ olt, puertos: ports.slice(offset, offset + 100) });
            }
        }
        const output = [];
        let current = [];
        let olts = new Set();
        for (const unit of units) {
            if (current.length >= 32 || olts.has(unit.olt)) {
                output.push(current);
                current = [];
                olts = new Set();
            }
            current.push(unit);
            olts.add(unit.olt);
        }
        if (current.length) output.push(current);
        return output;
    }

    function isNewer(previous, incoming) {
        if (!previous) return true;
        const oldGeneration = Number(previous.generacion || 0);
        const newGeneration = Number(incoming.generacion || 0);
        if (newGeneration && oldGeneration && newGeneration !== oldGeneration) {
            return newGeneration > oldGeneration;
        }
        const oldRevision = Number(previous.revision || 0);
        const newRevision = Number(incoming.revision || 0);
        if (newRevision && oldRevision && newRevision !== oldRevision) return newRevision > oldRevision;
        const oldDate = Date.parse(previous.finalizado_en || previous.consultado_en || '') || 0;
        const newDate = Date.parse(incoming.finalizado_en || incoming.consultado_en || '') || 0;
        return newDate >= oldDate;
    }

    function acceptResult(incoming) {
        const olt = oltKey(incoming?.olt);
        if (!olt || !visible.has(olt)) return;
        const previous = known.get(olt);
        if (!isNewer(previous, incoming)) return;
        const next = {
            estado: incoming.estado,
            revision: incoming.revision,
            generacion: incoming.generacion,
            consultado_en: incoming.consultado_en,
            finalizado_en: incoming.finalizado_en,
            error: incoming.error,
            ports: new Map(previous?.ports || [])
        };
        if (incoming.estado === 'listo') {
            for (const [port, result] of Object.entries(incoming.puertos || {})) {
                if (result?.estado === 'listo' && Array.isArray(result.casos)) {
                    next.ports.set(port, {
                        casos: result.casos,
                        consultado_en: incoming.consultado_en || result.consultado_en || null
                    });
                }
            }
        }
        known.set(olt, next);
        paintCurrent(olt);
    }

    async function consultarLotes(groups) {
        for (const solicitudes of chunks(groups)) {
            const controller = new AbortController();
            const timer = window.setTimeout(() => controller.abort(), 20000);
            try {
                const response = await fetch(endpoint.href, {
                    method: 'POST',
                    cache: 'no-store',
                    signal: controller.signal,
                    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
                    body: JSON.stringify({ solicitudes })
                });
                const payload = await response.json();
                if (!response.ok || payload?.ok !== true || !Array.isArray(payload.data?.resultados)) {
                    throw new Error('No se pudo consultar el estado de casos Helix');
                }
                const results = new Map(payload.data.resultados.map((item) => [oltKey(item?.olt), item]));
                for (const solicitud of solicitudes) {
                    const olt = solicitud.olt;
                    const result = results.get(olt);
                    if (result) acceptResult(result);
                    else acceptResult({
                        olt,
                        estado: 'error',
                        revision: Number(known.get(olt)?.revision || 0) + 1,
                        error: { codigo: 'INVALID_RESPONSE', mensaje: 'La respuesta no incluyó esta OLT' }
                    });
                }
            } catch (_error) {
                for (const solicitud of solicitudes) {
                    const previous = known.get(solicitud.olt);
                    acceptResult({
                        olt: solicitud.olt,
                        estado: 'error',
                        revision: Number(previous?.revision || 0) + 1,
                        error: { codigo: 'HTTP_ERROR', mensaje: 'No se pudo consultar el estado; se reintentará en la próxima actualización' }
                    });
                }
            } finally {
                window.clearTimeout(timer);
            }
        }
    }

    function actualizar(rows) {
        const grouped = new Map();
        for (const row of Array.isArray(rows) ? rows : []) {
            const olt = oltKey(row?.equipo);
            const port = normalizarPuerto(row?.puerto);
            if (!olt || !port) continue;
            if (!grouped.has(olt)) grouped.set(olt, new Set());
            grouped.get(olt).add(port);
        }
        visible = new Map(Array.from(grouped, ([olt, ports]) => [olt, Array.from(ports)]));
        for (const olt of Array.from(known.keys())) if (!visible.has(olt)) known.delete(olt);
        for (const olt of visible.keys()) paintCurrent(olt);
        if (inFlight || visible.size === 0) return;

        inFlight = true;
        void consultarLotes(visible).finally(() => { inFlight = false; });
    }

    // Consultas por OLT completa; se mantienen separadas del contrato por puerto.
    const equipos = new Map();
    let equipoTimer = null;
    let equipoBusy = false;
    const EQUIPO_TTL = 120000;
    const ERROR_RETRY = 30000;
    const PENDING_RETRY = 25000;

    function celdasEquipo(olt) {
        return Array.from(document.querySelectorAll(
            '#perdida-latencia-rows .gkp-helix-cases--equipo, #temperatura-rows .gkp-helix-cases--equipo'
        )).filter((cell) => cell.dataset.olt === olt);
    }

    function pintarEquipo(olt) {
        const state = equipos.get(olt);
        for (const cell of celdasEquipo(olt)) {
            cell.replaceChildren();
            cell.classList.remove('gkp-helix-cases--error', 'gkp-helix-cases--empty');
            cell.title = 'Casos abiertos asociados a la OLT; no necesariamente causados por esta condición';
            if (!state || state.estado === 'actualizando') {
                cell.textContent = 'Consultando…';
            } else if (state.estado === 'error') {
                cell.textContent = 'No se pudo consultar';
                cell.classList.add('gkp-helix-cases--error');
            } else if (!state.casos.length) {
                cell.textContent = 'Sin INC, WO o TAS abiertos asociados';
                cell.title = 'Consulta completada: no se identificaron casos abiertos asociados a esta OLT';
                cell.classList.add('gkp-helix-cases--empty');
            } else {
                for (const item of state.casos) {
                    const line = document.createElement('span');
                    line.className = 'gkp-helix-case';
                    line.textContent = `${item.numero} - ${item.estado}`;
                    cell.appendChild(line);
                }
            }
        }
    }

    function validarCasos(casos) {
        if (!Array.isArray(casos)) throw new Error('Lista de casos inválida');
        const unique = new Map();
        const order = { INC: 0, WO: 1, TAS: 2 };
        for (const item of casos) {
            const tipo = String(item?.tipo || '').toUpperCase();
            const numero = String(item?.numero || '').trim();
            const estado = String(item?.estado || '').trim();
            if (!Object.hasOwn(order, tipo) || !numero || !estado) {
                throw new Error('Caso Helix inválido');
            }
            unique.set(`${tipo}:${numero}`, { tipo, numero, estado });
        }
        return Array.from(unique.values()).sort((a, b) =>
            order[a.tipo] - order[b.tipo] || a.numero.localeCompare(b.numero, 'en', { numeric: true })
        );
    }

    async function consultarEquipo(olt) {
        const controller = new AbortController();
        const timer = window.setTimeout(() => controller.abort(), 20000);
        try {
            const url = new URL(endpoint);
            url.searchParams.set('olt', olt);
            url.searchParams.set('alcance', 'equipo');
            const response = await fetch(url.href, { cache: 'no-store', signal: controller.signal });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const payload = await response.json();
            if (payload?.ok !== true || payload.data?.alcance !== 'equipo') {
                throw new Error('Respuesta de alcance inválido');
            }
            const data = payload.data;
            if (data.estado !== 'listo' && data.estado !== 'actualizando') {
                throw new Error('Estado de consulta inválido');
            }
            if (data.estado === 'listo') {
                equipos.set(olt, { estado: 'listo', casos: validarCasos(data.casos), at: Date.now() });
            } else {
                equipos.set(olt, { estado: 'actualizando', casos: [], at: Date.now() });
            }
        } catch (_error) {
            equipos.set(olt, { estado: 'error', casos: [], at: Date.now() });
        } finally {
            window.clearTimeout(timer);
            pintarEquipo(olt);
        }
    }

    async function procesarEquipos() {
        if (equipoBusy) return;
        equipoBusy = true;
        try {
            const olts = new Set(Array.from(document.querySelectorAll(
                '#perdida-latencia-rows .gkp-helix-cases--equipo[data-olt], #temperatura-rows .gkp-helix-cases--equipo[data-olt]'
            )).map((cell) => cell.dataset.olt));
            for (const olt of olts) {
                const state = equipos.get(olt);
                const ttl = state?.estado === 'listo' ? EQUIPO_TTL
                    : state?.estado === 'error' ? ERROR_RETRY : PENDING_RETRY;
                if (state && Date.now() - state.at < ttl) continue;
                await consultarEquipo(olt);
            }
        } finally {
            equipoBusy = false;
        }
    }

    function actualizarEquipos() {
        for (const cell of document.querySelectorAll(
            '#perdida-latencia-rows .gkp-helix-cases--equipo[data-olt], #temperatura-rows .gkp-helix-cases--equipo[data-olt]'
        )) pintarEquipo(cell.dataset.olt);
        if (equipoTimer !== null) window.clearTimeout(equipoTimer);
        equipoTimer = window.setTimeout(() => {
            equipoTimer = null;
            void procesarEquipos();
        }, 0);
    }

    window.GKPCasosHelix = { actualizar, normalizarPuerto, actualizarEquipos };
})();
