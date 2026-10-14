
document.addEventListener('DOMContentLoaded', () => {
    'use strict';

    const tablas = [
        { id: 'gkp-rows', buscador: 'rkps-search-red',
          selector: 'rkps-filter-red', limpiar: 'rkps-clear-red',
          estado: 3, tipo: 'red' },
        { id: 'perdida-latencia-rows', buscador: 'rkps-search-perdida',
          selector: 'rkps-filter-perdida', limpiar: 'rkps-clear-perdida',
          estado: 2, tipo: 'perdida' },
        { id: 'temperatura-rows', buscador: 'rkps-search-temperatura',
          selector: 'rkps-filter-temperatura', limpiar: 'rkps-clear-temperatura',
          estado: 1, tipo: 'temperatura' }
    ];

    const nombres = {
        red: 'Estado actual de red',
        perdida: 'Pérdida y latencia',
        temperatura: 'Temperatura OLT'
    };

    const niveles = {
        amarillo: 'Elevada',
        naranja: 'Alta',
        rojo: 'Crítica'
    };

    // =====================================================
    // ESTADOS Y FILTROS
    // =====================================================

    function obtenerEstado(fila, config) {
        if (config.tipo !== 'temperatura') {
            return fila.cells[config.estado]?.textContent.trim() || '';
        }

        const celda = fila.cells[1];
        if (!celda) return '';

        const html = celda.innerHTML.toLowerCase();

        for (const [nivel, palabras] of Object.entries({
            rojo: ['rojo', 'red'],
            naranja: ['naranja', 'orange'],
            amarillo: ['amarillo', 'yellow']
        })) {
            if (palabras.some(palabra => html.includes(palabra))) {
                return nivel;
            }
        }

        const valor = parseFloat(celda.textContent.replace(',', '.'));
        if (!Number.isFinite(valor)) return '';
        if (valor >= 90) return 'rojo';
        if (valor >= 80) return 'naranja';
        if (valor >= 70) return 'amarillo';
        return '';
    }

    function iniciarFiltros(config) {
        const tbody = document.getElementById(config.id);
        const buscador = document.getElementById(config.buscador);
        const selector = document.getElementById(config.selector);

        if (!tbody || !buscador || !selector) return;

        const filas = () => [...tbody.querySelectorAll('tr')]
            .filter(fila => fila.cells.length > 0);

        function actualizarOpciones() {
            const anterior = selector.value;
            const estados = [...new Set(
                filas().map(fila => obtenerEstado(fila, config)).filter(Boolean)
            )];

            selector.replaceChildren(new Option(
                config.tipo === 'temperatura'
                    ? 'Todos los niveles'
                    : 'Todos los estados',
                ''
            ));

            if (config.tipo === 'temperatura') {
                Object.entries(niveles).forEach(([valor, etiqueta]) => {
                    if (estados.includes(valor)) {
                        selector.add(new Option(etiqueta, valor));
                    }
                });
            } else {
                estados.sort().forEach(estado => {
                    selector.add(new Option(estado, estado));
                });
            }

            selector.value = estados.includes(anterior) ? anterior : '';
        }

        function aplicarFiltros() {
            const texto = buscador.value.trim().toLowerCase();
            const seleccionado = selector.value.toLowerCase();

            filas().forEach(fila => {
                const equipo = fila.cells[0]?.textContent.toLowerCase() || '';
                const puerto = config.tipo === 'red'
                    ? fila.cells[1]?.textContent.toLowerCase() || ''
                    : '';
                const estado = obtenerEstado(fila, config).toLowerCase();

                fila.hidden = !(
                    (!texto || equipo.includes(texto) || puerto.includes(texto)) &&
                    (!seleccionado || estado === seleccionado)
                );
            });
        }

        buscador.addEventListener('input', aplicarFiltros);
        selector.addEventListener('change', aplicarFiltros);

        document.getElementById(config.limpiar)?.addEventListener('click', () => {
            buscador.value = '';
            selector.value = '';
            aplicarFiltros();
        });

        new MutationObserver(() => {
            actualizarOpciones();
            aplicarFiltros();
        }).observe(tbody, { childList: true });

        actualizarOpciones();
        aplicarFiltros();
    }

    tablas.forEach(iniciarFiltros);

    // =====================================================
    // CASOS HELIX
    // =====================================================

    function obtenerCasos(fila) {
        const grupos = { INC: new Map(), WO: new Map(), TAS: new Map() };

        fila.querySelectorAll('.gkp-helix-cases .gkp-helix-case')
            .forEach(elemento => {
                const texto = elemento.textContent.trim();
                const coincidencia = texto.match(/^(INC|WO|TAS)[0-9_-]+/i);

                if (!coincidencia) return;

                const tipo = coincidencia[1].toUpperCase();
                const numero = coincidencia[0].toUpperCase();

        grupos[tipo].set(numero, {
            texto,
            grupoSoporte: tipo === 'TAS'
                ? elemento.dataset.grupoSoporte || ''
                : ''
        });
                elemento.classList.add('rkps-case-original');
            });

        return grupos;
    }

   function compactarCasos() {
    tablas.forEach(config => {
        const tbody = document.getElementById(config.id);
        if (!tbody) return;

        tbody.querySelectorAll('.gkp-helix-cases').forEach(celda => {
            const grupos = obtenerCasos(celda);
            const total = Object.values(grupos)
                .reduce((suma, grupo) => suma + grupo.size, 0);

            let resumen = celda.querySelector('.rkps-case-summary');
            let ficha = celda.querySelector('.rkps-case-empty');

            // Los elementos originales permanecen en el DOM
            // para conservar casos, grupos de soporte y ubicación.
            celda.querySelectorAll('.gkp-helix-case').forEach(elemento => {
                elemento.classList.add('rkps-case-original');
            });

            if (total > 0) {
                ficha?.remove();

                if (!resumen) {
                    resumen = document.createElement('div');
                    resumen.className = 'rkps-case-summary';
                    celda.prepend(resumen);
                }

                const cantidades = ['INC', 'WO', 'TAS']
                    .filter(tipo => grupos[tipo].size > 0)
                    .map(tipo => {
                        const elemento = document.createElement('span');
                        elemento.className =
                            `rkps-case-count rkps-case-count--${tipo.toLowerCase()}`;
                        elemento.textContent = `${tipo} ${grupos[tipo].size}`;
                        return elemento;
                    });

                resumen.replaceChildren(...cantidades);
                return;
            }

            resumen?.remove();

            // Leer únicamente los mensajes originales de Helix.
            const texto = [...celda.childNodes]
                .filter(nodo =>
                    nodo !== ficha &&
                    nodo.nodeType === Node.TEXT_NODE
                )
                .map(nodo => nodo.textContent || '')
                .join(' ')
                .concat(' ', [...celda.querySelectorAll('.gkp-helix-case')]
                    .map(elemento => elemento.textContent || '')
                    .join(' '))
                .trim();

            let mensaje = 'Consultando...';
            let estado = 'loading';

            if (/datos anteriores/i.test(texto)) {
                mensaje = /no se pudo actualizar/i.test(texto)
                    ? 'No se pudo actualizar · datos anteriores'
                    : 'Actualizando datos anteriores...';

                estado = /no se pudo actualizar/i.test(texto)
                    ? 'error'
                    : 'loading';

            } else if (
                /sin\s+inc,\s*wo\s+o\s+tas\s+abiertos|sin casos/i.test(texto)
            ) {
                mensaje = 'Sin casos';
                estado = 'empty';

            } else if (
                /no se pudo consultar|consulta.*fall|error/i.test(texto) ||
                celda.classList.contains('gkp-helix-cases--error')
            ) {
                mensaje = 'Consulta no disponible';
                estado = 'error';
            }

            if (!ficha) {
                ficha = document.createElement('span');
                ficha.className = 'rkps-case-empty';
                celda.prepend(ficha);
            }

            ficha.className = `rkps-case-empty rkps-case-empty--${estado}`;
            ficha.textContent = mensaje;
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
            if (tbody) {
                observadorHelix.observe(tbody, {
                    childList: true,
                    characterData: true,
                    subtree: true
                });
            }
        });
    }

    compactarCasos();
    observarHelix();

    // =====================================================
    // CREACIÓN DEL PANEL LATERAL
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
            <button type="button" class="rkps-detail-close"
                    aria-label="Cerrar detalle">×</button>
        </header>

        <div class="rkps-detail-identity">
            <h3 id="rkps-detail-equipo"></h3>
            <p id="rkps-detail-subtitle"></p>
        </div>

        <nav class="rkps-detail-tabs" aria-label="Secciones del detalle">
            <button type="button" class="is-active"
                    data-rkps-detail-tab="resumen">Resumen</button>
            <button type="button"
                    data-rkps-detail-tab="casos">Casos Helix</button>
            <button type="button"
                    data-rkps-detail-tab="graficas">Gráficas</button>
        </nav>

        <div class="rkps-detail-body">
            <section data-rkps-detail-section="resumen">
                <div class="rkps-detail-grid">
                    <div class="rkps-detail-field">
                        <span>Estado actual</span>
                        <strong id="rkps-detail-estado"></strong>
                    </div>
                    <div class="rkps-detail-field">
                        <span id="rkps-detail-valor-label">Valor</span>
                        <strong id="rkps-detail-valor"></strong>
                    </div>
                    <div class="rkps-detail-field">
                        <span>Puerto / Interfaz</span>
                        <strong id="rkps-detail-puerto"></strong>
                    </div>
                    <div class="rkps-detail-field">
                        <span>Última actualización</span>
                        <strong id="rkps-detail-actualizacion">No disponible</strong>
                    </div>
                </div>

                <h4>Casos abiertos</h4>
                <div class="rkps-detail-counts">
                    <div class="rkps-detail-count rkps-detail-count--inc">
                        <span>INC</span><strong id="rkps-detail-inc">0</strong>
                    </div>
                    <div class="rkps-detail-count rkps-detail-count--wo">
                        <span>WO</span><strong id="rkps-detail-wo">0</strong>
                    </div>
                    <div class="rkps-detail-count rkps-detail-count--tas">
                        <span>TAS</span><strong id="rkps-detail-tas">0</strong>
                    </div>
                </div>

                <div id="rkps-detail-extra">
                    <h4>Detalles adicionales</h4>
                    <div id="rkps-detail-extra-rows"></div>
                </div>
            </section>

            <section data-rkps-detail-section="casos" hidden>
                <h4>Casos Helix asociados</h4>
                <div id="rkps-detail-casos" class="rkps-detail-casos"></div>
            </section>

            <section data-rkps-detail-section="graficas" hidden>
                <h4>Gráficas del equipo</h4>
                <p id="rkps-detail-grafana-msg"></p>
            </section>
        </div>

        <button type="button" class="rkps-detail-grafana"
                id="rkps-detail-grafana" hidden>Ver en Grafana</button>
    `;

    document.body.append(overlay, panel);

    const obtener = id => panel.querySelector(`#rkps-detail-${id}`);

    const campos = {
        equipo: obtener('equipo'),
        subtitulo: obtener('subtitle'),
        estado: obtener('estado'),
        valor: obtener('valor'),
        valorLabel: obtener('valor-label'),
        puerto: obtener('puerto'),
        actualizacion: obtener('actualizacion'),
        inc: obtener('inc'),
        wo: obtener('wo'),
        tas: obtener('tas'),
        casos: obtener('casos'),
        extraRows: obtener('extra-rows'),
        grafana: obtener('grafana'),
        grafanaMsg: obtener('grafana-msg')
    };

    // El subtítulo usa un identificador distinto al prefijo común.
    campos.subtitulo = panel.querySelector('#rkps-detail-subtitle');

    let elementoAnterior = null;
    let botonGrafanaOriginal = null;

    // =====================================================
    // NAVEGACIÓN Y DATOS DEL PANEL
    // =====================================================

    function cambiarTab(nombre) {
        panel.querySelectorAll('[data-rkps-detail-tab]').forEach(boton => {
            const activo = boton.dataset.rkpsDetailTab === nombre;
            boton.classList.toggle('is-active', activo);
            boton.setAttribute('aria-current', String(activo));
        });

        panel.querySelectorAll('[data-rkps-detail-section]').forEach(seccion => {
            seccion.hidden = seccion.dataset.rkpsDetailSection !== nombre;
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

function mostrarCasos(fila) {
    campos.casos.replaceChildren();

    const grupos = obtenerCasos(fila);
    const total = ['INC', 'WO', 'TAS'].reduce(
        (suma, tipo) => suma + grupos[tipo].size, 0
    );

    ['INC', 'WO', 'TAS'].forEach(tipo => {
        campos[tipo.toLowerCase()].textContent = String(grupos[tipo].size);

        grupos[tipo].forEach(caso => {
            const item = document.createElement('article');
            item.className = `rkps-detail-case rkps-detail-case--${tipo.toLowerCase()}`;

            const cabecera = document.createElement('div');
            cabecera.className = 'rkps-detail-case__head';

            const badge = document.createElement('span');
            badge.className = `rkps-detail-case__badge rkps-detail-case__badge--${tipo.toLowerCase()}`;
            badge.textContent = tipo;

            const identidad = document.createElement('div');
            identidad.className = 'rkps-detail-case__identity';

            const numero = document.createElement('strong');
            numero.className = 'rkps-detail-case__number';

            const separador = caso.texto.indexOf(' - ');
            numero.textContent = separador >= 0
                ? caso.texto.slice(0, separador)
                : caso.texto;

            const descripcion = document.createElement('span');
            descripcion.className = 'rkps-detail-case__type';
            descripcion.textContent = {
                INC: 'Tipo de caso: Incidente',
                WO: 'Tipo de caso: Work Order',
                TAS: 'Tipo de caso: Task'
            }[tipo];

            identidad.append(numero, descripcion);

            const estado = document.createElement('span');
            estado.className = 'rkps-detail-case__status';
            estado.textContent = separador >= 0
                ? caso.texto.slice(separador + 3)
                : 'Sin estado';

            cabecera.append(badge, identidad, estado);
            item.appendChild(cabecera);

            if (tipo === 'TAS' && caso.grupoSoporte) {
                const grupo = document.createElement('div');
                grupo.className = 'rkps-detail-case__group';

                const etiqueta = document.createElement('strong');
                etiqueta.textContent = 'Grupo de soporte:';

                const valor = document.createElement('span');
                valor.textContent = caso.grupoSoporte;

                grupo.append(etiqueta, valor);
                item.appendChild(grupo);
            }

            campos.casos.appendChild(item);
        });
    });

    if (!total) {
        const aviso = document.createElement('p');
        const estado = fila.querySelector('.rkps-case-empty');

        aviso.textContent = estado?.classList.contains('rkps-case-empty--empty')
            ? 'Sin casos abiertos asociados.'
            : 'No hay casos identificados. La consulta de Helix puede estar pendiente.';

        campos.casos.appendChild(aviso);
    }
}
    function mostrarDatosAdicionales(fila) {
        campos.extraRows.replaceChildren();

        const incidentes = [...fila.querySelectorAll(
            '.gkp-helix-cases .gkp-helix-case[data-regional], ' +
            '.gkp-helix-cases .gkp-helix-case[data-aliado], ' +
            '.gkp-helix-cases .gkp-helix-case[data-departamento], ' +
            '.gkp-helix-cases .gkp-helix-case[data-ciudad]'
        )].filter(elemento =>
            /^INC\d+/i.test(elemento.textContent.trim())
        );

        const camposUbicacion = [
            ['Regional', 'regional'],
            ['Aliado', 'aliado'],
            ['Departamento', 'departamento'],
            ['Ciudad', 'ciudad']
        ];

        camposUbicacion.forEach(([nombre, clave]) => {
            const valores = [...new Set(
                incidentes
                    .map(inc => (inc.dataset[clave] || '').trim())
                    .filter(Boolean)
            )];

            let valor = 'No disponible';

            if (valores.length === 1) {
                valor = valores[0];
            } else if (valores.length > 1) {
                valor = 'Por verificar';
            }

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
    function formatearActualizacion(valor) {
        if (!valor) return 'No disponible';

        const fecha = new Date(valor);
        if (Number.isNaN(fecha.getTime())) return 'No disponible';

        return fecha.toLocaleString('es-CO', {
            timeZone: 'America/Bogota',
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        });
    }

    function abrirDetalle(fila, config) {
        if (!fila.cells.length) return;

        const celdas = fila.cells;
        const estado = obtenerEstado(fila, config) || 'No disponible';
        const normalizado = estado.toLowerCase();

        campos.equipo.textContent =
            celdas[0]?.textContent.trim() || 'Equipo desconocido';
        campos.subtitulo.textContent = nombres[config.tipo];

        campos.puerto.textContent = config.tipo === 'red'
            ? celdas[1]?.textContent.trim() || '—'
            : 'No aplica';

        if (config.tipo === 'perdida') {
            const valores = celdas[1]?.querySelectorAll(
                '.gestion-value-stack > span'
            );

            const textos = valores
                ? [...valores]
                    .map(elemento => elemento.textContent.trim())
                    .filter(Boolean)
                : [];

            campos.valor.textContent = textos.length
                ? textos.join(' · ')
                : celdas[1]?.textContent.trim() || '—';
        } else {
            campos.valor.textContent =
                celdas[config.tipo === 'red' ? 2 : 1]?.textContent.trim() || '—';
        }

        campos.valorLabel.textContent =
            config.tipo === 'red' && fila.dataset.unidad === 'min'
                ? 'Tiempo'
                : 'Valor';

        campos.actualizacion.textContent =
            formatearActualizacion(fila.dataset.ultimaActualizacion);

        campos.estado.textContent = config.tipo === 'temperatura'
            ? niveles[estado] || estado
            : estado;

        let tono = 'danger';

        if (/normal|operativo|activo|estable|recuperado/.test(normalizado)) {
            tono = 'success';
        } else if (
            /latencia|amarillo|naranja|elevada|alta/.test(normalizado) &&
            !/pérdida|perdida|caída|caida|crítica|critica|rojo/.test(normalizado)
        ) {
            tono = 'warning';
        }

        panel.dataset.rkpsTone = tono;

        mostrarCasos(fila);
        mostrarDatosAdicionales(fila);

        botonGrafanaOriginal = fila.querySelector(
            '.ftth-eye-button, .temperature-detail-button'
        );

        campos.grafana.hidden = !botonGrafanaOriginal;
        campos.grafanaMsg.textContent = botonGrafanaOriginal
            ? 'Utiliza el botón inferior para abrir la gráfica original.'
            : 'No hay una acción de Grafana disponible en esta tabla.';

        cambiarTab('resumen');

        elementoAnterior = document.activeElement;
        overlay.hidden = false;
        panel.hidden = false;
        panel.querySelector('.rkps-detail-close').focus();
    }

    // =====================================================
    // EVENTOS
    // =====================================================

    tablas.forEach(config => {
        document.getElementById(config.id)?.addEventListener('click', evento => {
            if (evento.target.closest(
                'button, a, input, select, textarea'
            )) return;

            const fila = evento.target.closest('tr');
            if (!fila || !fila.cells.length || fila.hidden) return;

            abrirDetalle(fila, config);
        });
    });

    panel.querySelectorAll('[data-rkps-detail-tab]').forEach(boton => {
        boton.addEventListener('click', () => {
            cambiarTab(boton.dataset.rkpsDetailTab);
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

        const botones = [...panel.querySelectorAll('button')]
            .filter(boton =>
                !boton.hidden &&
                boton.getClientRects().length > 0
            );

        if (!botones.length) return;

        const primero = botones[0];
        const ultimo = botones[botones.length - 1];

        if (evento.shiftKey && document.activeElement === primero) {
            evento.preventDefault();
            ultimo.focus();
        } else if (!evento.shiftKey && document.activeElement === ultimo) {
            evento.preventDefault();
            primero.focus();
        }
    });
});
