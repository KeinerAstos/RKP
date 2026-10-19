<?php
declare(strict_types=1);
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
    http_response_code(405);
    echo json_encode(['ok' => false, 'error' => 'Metodo no permitido']);
    exit;
}
$ruta = dirname(__DIR__, 2) . '/data/dashboard_hfc/helix_global_snapshot.json';
if (!is_readable($ruta)) {
    http_response_code(503);
    echo json_encode(['ok' => false, 'error' => 'Snapshot global no disponible']);
    exit;
}
$contenido = file_get_contents($ruta);
$data = is_string($contenido) ? json_decode($contenido, true) : null;
if (!is_array($data) || ($data['estado'] ?? '') !== 'completo_nodos_validos'
    || !is_array($data['nodos'] ?? null)
    || count($data['nodos']) !== (int)($data['nodos_consultados'] ?? -1)) {
    http_response_code(503);
    echo json_encode(['ok' => false, 'error' => 'Snapshot global incompleto']);
    exit;
}
echo json_encode(['ok' => true, 'data' => $data], JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE);
