(() => {
    'use strict';

    const panel = document.getElementById('recursos-huawei-panel');
    const head = document.getElementById('recursos-huawei-head');
    const rows = document.getElementById('recursos-huawei-rows');
    const table = document.getElementById('recursos-huawei-table');
    const status = document.getElementById('recursos-huawei-status');
    const summary = document.getElementById('recursos-huawei-summary');
    const refresh = document.getElementById('recursos-huawei-refresh');

    if (
        !panel ||
        !head ||
        !rows ||
        !table ||
        !status ||
        !summary ||
        !refresh
    ) {
        return;
    }

    let busy = false;

    const mostrarValor = (value) => {
        if (value === null || value === undefined) {
            return '—';
        }

        if (typeof value === 'object') {
            return JSON.stringify(value);
        }

        return String(value);
    };

    const render = (columnas, filas) => {
        const encabezado = document.createElement('tr');

        columnas.forEach((columna) => {
            const th = document.createElement('th');

            th.scope = 'col';
            th.textContent = columna.replace(/_/g, ' ');

            encabezado.append(th);
        });

        head.replaceChildren(encabezado);

        const fragment = document.createDocumentFragment();

        filas.forEach((fila) => {
            const tr = document.createElement('tr');

            columnas.forEach((columna) => {
                const td = document.createElement('td');

                const valor = fila[columna];
                const sinGemPorts =
                    columna.toLowerCase() === 'total' &&
                    (
                        valor === 0 ||
                        (
                            typeof valor === 'string' &&
                            valor.trim() === '0'
                        )
                    );

                td.textContent = sinGemPorts
                    ? 'Sin GEM ports en el sistema'
                    : mostrarValor(valor);

                tr.append(td);
            });

            fragment.append(tr);
        });

        rows.replaceChildren(fragment);

        const hayRegistros = filas.length > 0;

        table.hidden = !hayRegistros;
        status.hidden = hayRegistros;
        status.style.display = hayRegistros ? 'none' : '';
        status.dataset.state = hayRegistros ? '' : 'empty';

        status.textContent = hayRegistros
            ? ''
            : 'No hay registros en OLT.recursos_huawei.';

        const cantidad = new Intl.NumberFormat('es-CO').format(
            filas.length
        );

        const fechaConsulta = new Date().toLocaleString('es-CO');

        summary.textContent =
            `${cantidad} registro${filas.length === 1 ? '' : 's'} · ` +
            `Consultado: ${fechaConsulta}`;
    };

    const load = async () => {
        if (busy) {
            return;
        }

        busy = true;
        refresh.disabled = true;

        panel.setAttribute('aria-busy', 'true');

        table.hidden = true;
        status.hidden = false;
        status.style.display = '';
        status.dataset.state = 'loading';
        status.textContent = 'Cargando…';

        summary.textContent = 'Consultando MySQL…';

        const controller = new AbortController();

        const timeout = window.setTimeout(() => {
            controller.abort();
        }, 60000);

        try {
            const response = await fetch(
                '../backend/api/recursos_huawei.php',
                {
                    cache: 'no-store',
                    signal: controller.signal,
                    headers: {
                        Accept: 'application/json'
                    }
                }
            );

            const payload = await response.json();

            if (
                !response.ok ||
                payload?.ok !== true ||
                !Array.isArray(payload.data?.columnas) ||
                !Array.isArray(payload.data?.filas) ||
                !payload.data.columnas.every(
                    (columna) => typeof columna === 'string'
                ) ||
                !payload.data.filas.every(
                    (fila) =>
                        fila !== null &&
                        typeof fila === 'object' &&
                        !Array.isArray(fila)
                )
            ) {
                throw new Error('Respuesta inválida de recursos Huawei');
            }

            render(
                payload.data.columnas,
                payload.data.filas
            );
        } catch (error) {
            head.replaceChildren();
            rows.replaceChildren();

            table.hidden = true;
            status.hidden = false;
            status.style.display = '';
            status.dataset.state = 'error';

            status.textContent = error.name === 'AbortError'
                ? 'La consulta Huawei superó el tiempo de espera.'
                : 'No se pudieron consultar los recursos Huawei.';

            summary.textContent = 'Error de consulta';
        } finally {
            window.clearTimeout(timeout);

            busy = false;
            refresh.disabled = false;

            panel.setAttribute('aria-busy', 'false');
        }
    };

    refresh.addEventListener('click', load);

    load();
})();