<?php
declare(strict_types=1);

require_once __DIR__ . '/../lib/bootstrap.php';

$actions = [
    'actual' => ['/api/cmts/inits/actual', 'GET'],
    'estado' => ['/api/cmts/inits/estado', 'GET'],
    'actualizar' => ['/api/cmts/inits/actualizar', 'POST'],
    'probar' => ['/api/cmts/inits/probar', 'POST'],
    'historico' => ['/api/cmts/inits/historico', 'GET'],
    'tendencia' => ['/api/cmts/inits/tendencia', 'GET'],
    'exportar' => ['/api/cmts/inits/exportar', 'GET'],
    'exportar_excel' => ['/api/cmts/inits/exportar-excel', 'GET'],
];
$action = (string) ($_GET['accion'] ?? '');
if (!isset($actions[$action])) {
    jsonResponse(['ok' => false, 'error' => 'Accion invalida'], 400);
}
[$path, $method] = $actions[$action];
requireMethod($method);
$query = [];
foreach (['cmts', 'desde', 'hasta', 'limit', 'offset', 'busqueda', 'estado', 'ordenar', 'direccion', 'alcance'] as $key) {
    if (isset($_GET[$key]) && is_scalar($_GET[$key])) {
        $query[$key] = (string) $_GET[$key];
    }
}

try {
    $client = datosClient();
    if ($action === 'exportar') {
        header('Content-Type: text/csv; charset=utf-8');
        header('Content-Disposition: attachment; filename=cmts-init-historico.csv');
        header('Cache-Control: no-store');
        $status = $client->streamCsv($path, $query);
        if ($status < 200 || $status >= 300) { error_log('Exportación INIT FastAPI respondió ' . $status); }
        exit;
    }
    if ($action === 'exportar_excel') {
        $response = $client->download($path, $query);
        if ($response['status'] < 200 || $response['status'] >= 300) {
            jsonResponse(['ok' => false, 'error' => 'No se pudo generar la exportación INIT'], $response['status']);
        }
        $excel = $action === 'exportar_excel';
        header('Content-Type: ' . ($excel ? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' : 'text/csv; charset=utf-8'));
        header('Content-Disposition: attachment; filename=' . (($query['alcance'] ?? 'actual') === 'historico5d' ? 'cmts-init-historico-5-dias.xlsx' : 'cmts-init-actual.xlsx'));
        header('Cache-Control: no-store');
        echo $response['body'];
        exit;
    }
    $response = $method === 'POST' ? $client->post($path . ($query ? '?' . http_build_query($query, '', '&', PHP_QUERY_RFC3986) : '')) : $client->get($path, $query);
    jsonResponse($response['body'], $response['status']);
} catch (Throwable $error) {
    error_log('CMTS INIT: ' . $error->getMessage());
    jsonResponse(['ok' => false, 'error' => 'Servicio de monitoreo INIT no disponible'], 503);
}
