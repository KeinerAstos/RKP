
document.addEventListener('DOMContentLoaded', () => {
    'use strict';

    // =====================================================
    // CONFIGURACIÓN DE LAS TRES TABLAS
    // =====================================================

    const tablas = [
        {
            id: 'gkp-rows',
            buscador: 'rkps-search-red',
            selector: 'rkps-filter-red',
            columnaEstado: 3,
            tipo: 'red'
        },
        {
            id: 'perdida-latencia-rows',
            buscador: 'rkps-search-perdida',
            selector: 'rkps-filter-perdida',
            columnaEstado: 2,
            tipo: 'perdida'
        },
        {
            id: 'temperatura-rows',
            buscador: 'rkps-search-temperatura',
            selector: 'rkps-filter-temperatura',
            columnaEstado: 1,
            tipo: 'temperatura'
        }
    ];

    // =====================================================
    // FILTROS DE BÚSQUEDA Y ESTADO
    // =====================================================

    function obtenerEstado(fila, config) {
        if (config.tipo === 'temperatura') {
            const elemento = fila.cells[1];
            if (!elemento) return '';

            const clases = elemento.innerHTML.toLowerCase();

            if (
                clases.includes('rojo') ||
                clases.includes('red')
            ) return 'rojo';

            if (
                clases.includes('naranja') ||
                clases.includes('orange')
            ) return 'naranja';

            if (
                clases.includes('amarillo') ||
                clases.includes('yellow')
            ) return 'amarillo';

            const valor = parseFloat(
                elemento.textContent.replace(',', '.')
            );

            if (!Number.isFinite(valor)) return '';
            if (valor >= 90) return 'rojo';
            if (valor >= 80) return 'naranja';
            if (valor >= 70) return 'amarillo';

            return '';
        }

        return (
            fila.cells[config.columnaEstado]?.textContent || ''
        ).trim();
    }

    function iniciarFiltros(config) {
        const tbody = document.getElementById(config.id);
        const buscador = document.getElementById(config.buscador);
        const selector = document.getElementById(config.selector);

        if (!tbody || !buscador || !selector) return;

        function actualizarOpciones() {
            const seleccionado = selector.value;
            const estados = new Set();

            tbody.querySelectorAll('tr').forEach(fila => {
                if (!fila.cells.length) return;

                const estado = obtenerEstado(fila, config);

                if (estado) {
                    estados.add(estado);
                }
            });

            if (config.tipo === 'temperatura') {
                const niveles = {
                    amarillo: 'Elevada',
                    naranja: 'Alta',
                    rojo: 'Crítica'
                };

                selector.replaceChildren(
                    new Option('Todos los niveles', '')
                );

                Object.entries(niveles).forEach(([valor, etiqueta]) => {
                    if (estados.has(valor)) {
                        selector.add(new Option(etiqueta, valor));
                    }
                });
            } else {
                selector.replaceChildren(
                    new Option('Todos los estados', '')
                );

                [...estados].sort().forEach(estado => {
                    selector.add(new Option(estado, estado));
                });
            }

            selector.value = estados.has(seleccionado)
                ? seleccionado
                : '';
        }

        function aplicarFiltros() {
            const texto = buscador.value.trim().toLowerCase();
            const estadoSeleccionado = selector.value.toLowerCase();

            tbody.querySelectorAll('tr').forEach(fila => {
                if (!fila.cells.length) return;

                const equipo =
                    fila.cells[0]?.textContent.toLowerCase() || '';

                const puerto = config.tipo === 'red'
                    ? fila.cells[1]?.textContent.toLowerCase() || ''
                    : '';

                const estado = obtenerEstado(
                    fila,
                    config
                ).toLowerCase();

                const coincideBusqueda = !texto ||
                    equipo.includes(texto) ||
                    puerto.includes(texto);

                const coincideEstado = !estadoSeleccionado ||
                    estado === estadoSeleccionado;

                fila.hidden = !(
                    coincideBusqueda && coincideEstado
                );
            });
        }

        buscador.addEventListener('input', aplicarFiltros);
        selector.addEventListener('change', aplicarFiltros);

        const botonesLimpiar = {
            red: 'rkps-clear-red',
            perdida: 'rkps-clear-perdida',
            temperatura: 'rkps-clear-temperatura'
        };

        document.getElementById(botonesLimpiar[config.tipo])
            ?.addEventListener('click', () => {
                buscador.value = '';
                selector.value = '';
                aplicarFiltros();
            });

        const observador = new MutationObserver(() => {
            actualizarOpciones();
            aplicarFiltros();
        });

        observador.observe(tbody, {
            childList: true
        });

        actualizarOpciones();
        aplicarFiltros();
    }

    tablas.forEach(iniciarFiltros);

    // =====================================================
    // FICHAS COMPACTAS DE CASOS HELIX
    // =====================================================

    function compactarCasos() {
        tablas.forEach(config => {
            const tbody = document.getElementById(config.id);
            if (!tbody) return;

            tbody.querySelectorAll('.gkp-helix-cases').forEach(celda => {
                const casos = celda.querySelectorAll('.gkp-helix-case');

                const grupos = {
                    INC: new Set(),
                    WO: new Set(),
                    TAS: new Set()
                };

                casos.forEach(caso => {
                    const texto = caso.textContent.trim();

                    const identificador = texto
                        .split(/\s+-\s+/)[0]
                        .trim();

                    const coincidencia = identificador.match(
                        /^(INC|WO|TAS)(?=\d)/i
                    );

                    if (!coincidencia) return;

                    const tipo = coincidencia[1].toUpperCase();

                    grupos[tipo].add(
                        identificador.toUpperCase()
                    );

                    caso.classList.add('rkps-case-original');
                });

                const total = Object.values(grupos)
                    .reduce((suma, grupo) => suma + grupo.size, 0);

                let resumen = celda.querySelector(
                    '.rkps-case-summary'
                );

                if (total === 0) {
                    resumen?.remove();

                    const fichaAnterior = celda.querySelector(
                        '.rkps-case-empty'
                    );

                    const texto = [...celda.childNodes]
                        .filter(nodo =>
                            nodo !== fichaAnterior &&
                            !(
                                nodo.nodeType === Node.ELEMENT_NODE &&
                                nodo.classList?.contains('rkps-case-summary')
                            )
                        )
                        .map(nodo => nodo.textContent || '')
                        .join(' ')
                        .trim();

                    let mensaje = '';
                    let estado = '';

                    if (
                        /actualizando|consultando|cargando|pendiente/i
                            .test(texto)
                    ) {
                        mensaje = 'Actualizando...';
                        estado = 'loading';
                    } else if (
                        /sin\s+inc,\s*wo\s+o\s+tas\s+abiertos|sin casos/i
                            .test(texto)
                    ) {
                        mensaje = 'Sin casos';
                        estado = 'empty';
                    } else if (
                        /error|fall[oó]|no disponible/i.test(texto)
                    ) {
                        mensaje = 'Consulta no disponible';
                        estado = 'error';
                    }

                    if (!mensaje) {
                        fichaAnterior?.remove();
                        return;
                    }

                    const ficha = fichaAnterior ||
                        document.createElement('span');

                    ficha.className =
                        `rkps-case-empty rkps-case-empty--${estado}`;

                    ficha.textContent = mensaje;

                    if (!fichaAnterior) {
                        celda.prepend(ficha);
                    }

                    return;
                }

                celda.querySelector('.rkps-case-empty')?.remove();

                if (!resumen) {
                    resumen = document.createElement('div');
                    resumen.className = 'rkps-case-summary';
                    celda.prepend(resumen);
                }

                resumen.replaceChildren();

                ['INC', 'WO', 'TAS'].forEach(tipo => {
                    const cantidad = grupos[tipo].size;
                    if (!cantidad) return;

                    const ficha = document.createElement('span');

                    ficha.className =
                        `rkps-case-count rkps-case-count--${tipo.toLowerCase()}`;

                    ficha.textContent = `${tipo} ${cantidad}`;

                    resumen.appendChild(ficha);
                });
            });
        });
    }

    const observadorHelix = new MutationObserver(() => {
        observadorHelix.disconnect();
        compactarCasos();
        observarHelix();
    });

    function observarHelix() {
        tablas.forEach(config => {
            const tbody = document.getElementById(config.id);
            if (!tbody) return;

            observadorHelix.observe(tbody, {
                childList: true,
                characterData: true,
                subtree: true
            });
        });
    }

    compactarCasos();
    observarHelix();

    // =====================================================
    // PANEL LATERAL - RESUMEN, CASOS HELIX Y GRÁFICAS
    // =====================================================

    const overlay = document.createElement('div');
    overlay.className = 'rkps-detail-overlay';
    overlay.hidden = true;

    const panel = document.createElement('aside');
    panel.className = 'rkps-detail-panel';
    panel.hidden = true;

    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-modal', 'true');
    panel.setAttribute('aria-label', 'Detalle del equipo');

    panel.innerHTML = `
        <header class="rkps-detail-header">
            <h2>Detalle del equipo</h2>
            <button
                type="button"
                class="rkps-detail-close"
                aria-label="Cerrar detalle"
            >×</button>
        </header>

        <div class="rkps-detail-identity">
            <h3 id="rkps-detail-equipo"></h3>
            <p id="rkps-detail-subtitle"></p>
        </div>

        <nav class="rkps-detail-tabs"
             aria-label="Secciones del detalle">
            <button
                type="button"
                class="is-active"
                data-rkps-detail-tab="resumen"
            >Resumen</button>

            <button
                type="button"
                data-rkps-detail-tab="casos"
            >Casos Helix</button>

            <button
                type="button"
                data-rkps-detail-tab="graficas"
            >Gráficas</button>
        </nav>

        <div class="rkps-detail-body">
            <section data-rkps-detail-section="resumen">
                <div class="rkps-detail-grid">
                    <div class="rkps-detail-field">
                        <span>Estado actual</span>
                        <strong id="rkps-detail-estado"></strong>
                    </div>

                    <div class="rkps-detail-field">
                        <span>Valor</span>
                        <strong id="rkps-detail-valor"></strong>
                    </div>

                    <div class="rkps-detail-field">
                        <span>Puerto / Interfaz</span>
                        <strong id="rkps-detail-puerto"></strong>
                    </div>

                    <div class="rkps-detail-field">
                        <span>Origen</span>
                        <strong id="rkps-detail-origen"></strong>
                    </div>
                </div>

                <h4>Casos abiertos</h4>

                <div class="rkps-detail-counts">
                    <div class="rkps-detail-count rkps-detail-count--inc">
                        <span>INC</span>
                        <strong id="rkps-detail-inc">0</strong>
                    </div>

                    <div class="rkps-detail-count rkps-detail-count--wo">
                        <span>WO</span>
                        <strong id="rkps-detail-wo">0</strong>
                    </div>

                    <div class="rkps-detail-count rkps-detail-count--tas">
                        <span>TAS</span>
                        <strong id="rkps-detail-tas">0</strong>
                    </div>
                </div>

                <div id="rkps-detail-extra" hidden>
                    <h4>Detalles adicionales</h4>
                    <div id="rkps-detail-extra-rows"></div>
                </div>
            </section>

            <section data-rkps-detail-section="casos" hidden>
                <h4>Casos Helix asociados</h4>
                <div
                    id="rkps-detail-casos"
                    class="rkps-detail-casos"
                ></div>
            </section>

            <section data-rkps-detail-section="graficas" hidden>
                <h4>Gráficas del equipo</h4>

                <p id="rkps-detail-grafana-msg"></p>

                <button
                    type="button"
                    class="rkps-detail-grafana"
                    id="rkps-detail-grafana"
                >Ver en Grafana</button>
            </section>
        </div>
    `;

    document.body.append(overlay, panel);

    // =====================================================
    // REFERENCIAS DEL PANEL
    // =====================================================

    const campos = {
        equipo: panel.querySelector('#rkps-detail-equipo'),
        subtitulo: panel.querySelector('#rkps-detail-subtitle'),
        estado: panel.querySelector('#rkps-detail-estado'),
        valor: panel.querySelector('#rkps-detail-valor'),
        puerto: panel.querySelector('#rkps-detail-puerto'),
        origen: panel.querySelector('#rkps-detail-origen'),
        inc: panel.querySelector('#rkps-detail-inc'),
        wo: panel.querySelector('#rkps-detail-wo'),
        tas: panel.querySelector('#rkps-detail-tas'),
        casos: panel.querySelector('#rkps-detail-casos'),
        extra: panel.querySelector('#rkps-detail-extra'),
        extraRows: panel.querySelector('#rkps-detail-extra-rows'),
        grafana: panel.querySelector('#rkps-detail-grafana'),
        grafanaMsg: panel.querySelector('#rkps-detail-grafana-msg')
    };

    let elementoAnterior = null;
    let botonGrafanaOriginal = null;

    // =====================================================
    // NAVEGACIÓN DEL PANEL
    // =====================================================

    function cambiarTabDetalle(nombre) {
        panel.querySelectorAll('[data-rkps-detail-tab]')
            .forEach(boton => {
                const activo =
                    boton.dataset.rkpsDetailTab === nombre;

                boton.classList.toggle('is-active', activo);

                boton.setAttribute(
                    'aria-current',
                    activo ? 'true' : 'false'
                );
            });

        panel.querySelectorAll('[data-rkps-detail-section]')
            .forEach(seccion => {
                seccion.hidden =
                    seccion.dataset.rkpsDetailSection !== nombre;
            });
    }

    function cerrarDetalle() {
        panel.hidden = true;
        overlay.hidden = true;
        botonGrafanaOriginal = null;

        if (elementoAnterior?.isConnected) {
            elementoAnterior.focus();
        }

        elementoAnterior = null;
    }

    // =====================================================
    // DETALLE DE CASOS HELIX
    // =====================================================

    function mostrarCasos(fila) {
        campos.casos.replaceChildren();

        const grupos = {
            INC: new Set(),
            WO: new Set(),
            TAS: new Set()
        };

        const casos = fila.querySelectorAll(
            '.gkp-helix-cases .gkp-helix-case'
        );

        casos.forEach(caso => {
            const texto = caso.textContent.trim();

            const coincidencia = texto.match(
                /^(INC|WO|TAS)[0-9_-]+/i
            );

            if (!coincidencia) return;

            const tipo = coincidencia[1].toUpperCase();
            const numero = coincidencia[0].toUpperCase();

            if (grupos[tipo].has(numero)) return;

            grupos[tipo].add(numero);

            const item = document.createElement('div');
            item.className = 'rkps-detail-case';

            const ficha = document.createElement('span');

            ficha.className =
                `rkps-case-count rkps-case-count--${tipo.toLowerCase()}`;

            ficha.textContent = tipo;

            const descripcion = document.createElement('span');
            descripcion.textContent = texto;

            item.append(ficha, descripcion);
            campos.casos.append(item);
        });

        campos.inc.textContent = String(grupos.INC.size);
        campos.wo.textContent = String(grupos.WO.size);
        campos.tas.textContent = String(grupos.TAS.size);

        const total =
            grupos.INC.size +
            grupos.WO.size +
            grupos.TAS.size;

        if (total === 0) {
            const aviso = document.createElement('p');
            const ficha = fila.querySelector('.rkps-case-empty');

            aviso.textContent =
                ficha?.classList.contains('rkps-case-empty--empty')
                    ? 'Sin casos abiertos asociados.'
                    : 'No hay casos identificados. La consulta de Helix puede estar pendiente.';

            campos.casos.append(aviso);
        }
    }

    // =====================================================
    // DATOS ADICIONALES
    // =====================================================

    function mostrarDatosAdicionales(fila) {
        campos.extraRows.replaceChildren();

        const datos = [
            ['ID beneficiario', fila.dataset.idBeneficiario],
            ['Regional', fila.dataset.regional],
            ['Aliado', fila.dataset.aliado],
            ['Departamento', fila.dataset.departamento],
            ['Ciudad', fila.dataset.ciudad]
        ].filter(([, valor]) =>
            typeof valor === 'string' && valor.trim()
        );

        campos.extra.hidden = datos.length === 0;

        datos.forEach(([nombre, valor]) => {
            const linea = document.createElement('div');
            linea.className = 'rkps-detail-extra-row';

            const etiqueta = document.createElement('span');
            etiqueta.textContent = nombre;

            const dato = document.createElement('strong');
            dato.textContent = valor;

            linea.append(etiqueta, dato);
            campos.extraRows.append(linea);
        });
    }

    // =====================================================
    // ABRIR DETALLE DEL EQUIPO
    // =====================================================

    function abrirDetalle(fila, config) {
        const celdas = fila.cells;
        if (!celdas.length) return;

        const nombres = {
            red: 'Estado actual de red',
            perdida: 'Pérdida y latencia',
            temperatura: 'Temperatura OLT'
        };

        campos.equipo.textContent =
            celdas[0]?.textContent.trim() || 'Equipo desconocido';

        campos.subtitulo.textContent = nombres[config.tipo];
        campos.origen.textContent = nombres[config.tipo];

        campos.puerto.textContent = config.tipo === 'red'
            ? celdas[1]?.textContent.trim() || '—'
            : 'No aplica';

        const indiceValor = config.tipo === 'red' ? 2 : 1;

        campos.valor.textContent =
            celdas[indiceValor]?.textContent.trim() || '—';

        campos.estado.textContent =
            obtenerEstado(fila, config) || 'No disponible';

        mostrarCasos(fila);
        mostrarDatosAdicionales(fila);

        botonGrafanaOriginal = fila.querySelector(
            '.ftth-eye-button, .temperature-detail-button'
        );

        campos.grafana.hidden = !botonGrafanaOriginal;

        campos.grafanaMsg.textContent = botonGrafanaOriginal
            ? 'Abre la gráfica original de este equipo.'
            : 'No hay una acción de Grafana disponible en esta tabla.';

        cambiarTabDetalle('resumen');

        elementoAnterior = document.activeElement;

        overlay.hidden = false;
        panel.hidden = false;

        panel.querySelector('.rkps-detail-close').focus();
    }

    // =====================================================
    // EVENTOS DE LAS TRES TABLAS
    // =====================================================

    tablas.forEach(config => {
        const tbody = document.getElementById(config.id);
        if (!tbody) return;

        tbody.addEventListener('click', evento => {
            if (evento.target.closest(
                'button, a, input, select, textarea'
            )) return;

            const fila = evento.target.closest('tr');

            if (!fila || !tbody.contains(fila)) return;

            abrirDetalle(fila, config);
        });
    });

    panel.querySelectorAll('[data-rkps-detail-tab]')
        .forEach(boton => {
            boton.addEventListener('click', () => {
                cambiarTabDetalle(
                    boton.dataset.rkpsDetailTab
                );
            });
        });

    campos.grafana.addEventListener('click', () => {
        const original = botonGrafanaOriginal;

        if (!original?.isConnected) return;

        cerrarDetalle();
        original.click();
    });

    overlay.addEventListener('click', cerrarDetalle);

    panel.querySelector('.rkps-detail-close')
        .addEventListener('click', cerrarDetalle);

    document.addEventListener('keydown', evento => {
        if (panel.hidden) return;

        if (evento.key === 'Escape') {
            cerrarDetalle();
            return;
        }

        if (evento.key !== 'Tab') return;

        const botones = [
            ...panel.querySelectorAll('button')
        ].filter(boton =>
            !boton.hidden &&
            boton.getClientRects().length > 0
        );

        if (!botones.length) return;

        const primero = botones[0];
        const ultimo = botones[botones.length - 1];

        if (
            evento.shiftKey &&
            document.activeElement === primero
        ) {
            evento.preventDefault();
            ultimo.focus();
        } else if (
            !evento.shiftKey &&
            document.activeElement === ultimo
        ) {
            evento.preventDefault();
            primero.focus();
        }
    });
});
