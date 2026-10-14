<?php
$resolvedHeaderTitle = $headerTitle ?? 'Estado operacional de red';
$resolvedHeaderDescription = $headerDescription ?? 'Excepciones activas y temperatura OLT';
?>
<?php require_once dirname(__DIR__,2).'/backend/lib/entorno.php'; ?>
<script>
window.RKP_CONNECTIONS=<?= json_encode(rkp_public_connections(),JSON_HEX_TAG|JSON_HEX_AMP|JSON_HEX_APOS|JSON_HEX_QUOT|JSON_THROW_ON_ERROR) ?>;
window.rkpGrafanaUrl=function(type){
    const c=window.RKP_CONNECTIONS;
    const base=c.grafanaPublicUrl || `${window.location.protocol}//${window.location.hostname}:${c.grafanaProxyPort}`;
    const dashboard=type==='cmts'?c.grafanaCmtsPath:c.grafanaOltPath;
    if(!dashboard || (!c.grafanaPublicUrl && !c.grafanaProxyPort))throw new Error('Falta configuración pública de Grafana en .env');
    return new URL(dashboard,base.replace(/\/$/,'')+'/').toString();
};
</script>

<header class="topbar">
    <div class="topbar__main">
        <div class="topbar__left">
            <button id="sidebar-toggle" class="sidebar-toggle" type="button" aria-expanded="true"
                aria-controls="main-sidebar" aria-label="Ocultar barra lateral" title="Ocultar barra lateral">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M15 18 9 12l6-6" />
                </svg>
            </button>
            <span class="topbar__collapsed-brand">RKP</span>
            <div class="topbar__title-group">
                <h1><?= htmlspecialchars($resolvedHeaderTitle, ENT_QUOTES, 'UTF-8') ?></h1>
                <p><?= htmlspecialchars($resolvedHeaderDescription, ENT_QUOTES, 'UTF-8') ?></p>
            </div>
        </div>

        <div class="topbar__status" aria-label="Estado del sistema">
            <div class="topbar-card topbar-card--monitoring">
                <span class="monitor-dot" aria-hidden="true"></span>
                <div>
                    <span class="topbar-card__label">Monitoreo general</span>
                    <strong id="header-monitoring">Consultando</strong>
                    <small id="header-monitoring-detail">Esperando datos</small>
                </div>
            </div>
            <div class="topbar-card topbar-card--connection">
                <span class="connection-dot offline" aria-hidden="true"></span>
                <div>
                    <span class="topbar-card__label">Conexión frontend</span>
                    <strong id="header-connection">Pendiente</strong>
                    <small id="header-connection-detail">Esperando primera consulta</small>
                </div>
            </div>
            <div class="topbar-card topbar-card--sources">
                <svg class="topbar-card__icon" viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M4 6h16M4 12h16M4 18h16" />
                </svg>
                <div>
                    <span class="topbar-card__label">Fuentes de datos</span>
                    <strong id="header-sources">Pendiente</strong>
                    <small id="header-sources-detail">Esperando consulta</small>
                </div>
            </div>
            <div class="topbar-card topbar-card--time">
                <svg class="topbar-card__icon" viewBox="0 0 24 24" aria-hidden="true">
                    <circle cx="12" cy="12" r="9" />
                    <path d="M12 7v5l3 2" />
                </svg>
                <div>
                    <span class="topbar-card__label">Última actualización</span>
                    <strong id="header-datetime">Pendiente</strong>
                </div>
            </div>
        </div>
    </div>
</header>
