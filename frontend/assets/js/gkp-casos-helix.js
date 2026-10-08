(() => {
    'use strict';

    const endpoint = new URL('../backend/api/olt_casos_helix.php', window.location.href);
    const cache = new Map();
    const failures = new Map();
    let visible = new Map();
    let running = false;

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

    function renderCell(cell, result, date) {
        cell.replaceChildren();
        cell.title = date ? `Consultado: ${new Date(date).toLocaleString()}` : '';
        cell.classList.remove('gkp-helix-cases--error', 'gkp-helix-cases--empty');
        if (!result || result.ok !== true || !Array.isArray(result.casos)) {
            cell.textContent = 'No se pudo consultar';
            cell.title = 'La consulta de casos Helix no se completó';
            cell.classList.add('gkp-helix-cases--error');
            return;
        }
        const order = { INC: 0, WO: 1, TAS: 2 };
        const unique = new Map();
        for (const item of result.casos) {
            const type = String(item?.tipo ?? '').toUpperCase();
            const number = String(item?.numero ?? '').trim();
            const state = String(item?.estado ?? '').trim();
            if (!Object.hasOwn(order, type) || !number || !state) {
                cell.textContent = 'No se pudo consultar';
                cell.title = 'La respuesta Helix contiene un caso inválido';
                cell.classList.add('gkp-helix-cases--error');
                return;
            }
            unique.set(number, { type, number, state });
        }
        const cases = Array.from(unique.values()).sort((a, b) =>
            order[a.type] - order[b.type] || a.number.localeCompare(b.number, 'en', { numeric: true })
        );
        if (!cases.length) {
            cell.textContent = 'Sin casos abiertos';
            cell.classList.add('gkp-helix-cases--empty');
            return;
        }
        for (const item of cases) {
            const line = document.createElement('span');
            line.className = 'gkp-helix-case';
            line.textContent = `${item.number} - ${item.state}`;
            cell.append(line);
        }
    }

    function paint(olt, port) {
        const item = cache.get(olt);
        const entry = item?.ports.get(port);
        const cells = currentCells(olt, port);
        for (const cell of cells) {
            if (failures.has(`${olt}|${port}`)) renderCell(cell, null, null);
            else if (entry) renderCell(cell, entry.result, entry.date);
            else {
                cell.textContent = 'Consultando…';
                cell.title = '';
                cell.classList.remove('gkp-helix-cases--error', 'gkp-helix-cases--empty');
            }
        }
    }

    function chunk(values, size) {
        const groups = [];
        for (let index = 0; index < values.length; index += size) groups.push(values.slice(index, index + size));
        return groups;
    }

    async function drain() {
        if (running) return;
        running = true;
        const attempted = new Set();
        try {
            while (true) {
                let next = null;
                for (const [olt, ports] of visible) {
                    const item = cache.get(olt);
                    const missing = Array.from(ports).filter((port) =>
                        (!item?.ports.has(port) || Date.now() - item.ports.get(port).receivedAt >= 120000)
                        && !attempted.has(`${olt}|${port}`)
                    );
                    if (missing.length) { next = { olt, ports: missing }; break; }
                }
                if (!next) break;
                for (const ports of chunk(next.ports, 100)) {
                    for (const port of ports) attempted.add(`${next.olt}|${port}`);
                    await consult(next.olt, ports);
                }
            }
        } finally {
            running = false;
        }
    }

    async function consult(olt, ports) {
        const controller = new AbortController();
        const timer = window.setTimeout(() => controller.abort(), 70000);
        try {
            const query = new URLSearchParams({ olt, puertos: ports.join(',') });
            const response = await fetch(`${endpoint.href}?${query.toString()}`, {
                method: 'GET', cache: 'no-store', signal: controller.signal,
                headers: { Accept: 'application/json' }
            });
            const payload = await response.json();
            const data = payload?.data;
            if (!response.ok || payload?.ok !== true || data?.olt !== olt || !data?.puertos || typeof data.puertos !== 'object') {
                throw new Error('Respuesta Helix inválida');
            }
            if (!visible.has(olt)) return;
            const date = data.consultado_en;
            const validated = [];
            for (const port of ports) {
                const result = data.puertos[port];
                if (!result || typeof result.ok !== 'boolean' || (result.ok && !Array.isArray(result.casos))) {
                    throw new Error('Cobertura Helix incompleta');
                }
                for (const item of result.casos || []) {
                    if (!['INC', 'WO', 'TAS'].includes(String(item?.tipo ?? '').toUpperCase())
                        || !String(item?.numero ?? '').trim() || !String(item?.estado ?? '').trim()) {
                        throw new Error('Caso Helix inválido');
                    }
                }
                validated.push([port, result]);
            }
            const current = cache.get(olt) || { ports: new Map() };
            for (const [port, result] of validated) {
                if (result.ok) {
                    current.ports.set(port, { result, date, receivedAt: Date.now() });
                    failures.delete(`${olt}|${port}`);
                } else failures.set(`${olt}|${port}`, true);
            }
            cache.set(olt, current);
            for (const port of ports) paint(olt, port);
        } catch (_error) {
            for (const port of ports) {
                failures.set(`${olt}|${port}`, true);
                paint(olt, port);
            }
        } finally {
            window.clearTimeout(timer);
        }
    }

    function actualizar(rows) {
        const nextVisible = new Map();
        for (const row of Array.isArray(rows) ? rows : []) {
            const olt = oltKey(row?.equipo);
            const port = normalizarPuerto(row?.puerto);
            if (!olt || !port) continue;
            if (!nextVisible.has(olt)) nextVisible.set(olt, new Set());
            nextVisible.get(olt).add(port);
        }
        visible = nextVisible;
        for (const olt of Array.from(cache.keys())) if (!visible.has(olt)) cache.delete(olt);
        for (const key of Array.from(failures.keys())) if (!visible.has(key.split('|', 1)[0])) failures.delete(key);
        for (const [olt, ports] of visible) for (const port of ports) paint(olt, port);
        void drain();
    }

    window.GKPCasosHelix = { actualizar, normalizarPuerto };
})();
