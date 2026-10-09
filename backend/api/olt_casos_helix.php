<?php
declare(strict_types=1);

require_once __DIR__ . '/../lib/bootstrap.php';

$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
if (!in_array($method, ['GET', 'POST'], true)) {
    header('Allow: GET, POST');
    jsonResponse(['ok' => false, 'error' => 'Método no permitido'], 405);
}

if ($method === 'GET') {
    $body = null;
    $path = '/api/olt/casos-abiertos';
    $query = [
        'olt' => trim((string) ($_GET['olt'] ?? '')),
    ];

    $alcance = trim((string) ($_GET['alcance'] ?? ''));

    if ($alcance !== '') {
        if (!in_array($alcance, ['equipo', 'puertos'], true)) {
            jsonResponse([
                'ok' => false,
                'error' => 'Alcance no válido',
            ], 422);
        }

        $query['alcance'] = $alcance;
    }

    if ($alcance !== 'equipo') {
        $query['puertos'] = trim((string) ($_GET['puertos'] ?? ''));
    }
} else {
    try {
        $body = json_decode((string) file_get_contents('php://input'), true, 512, JSON_THROW_ON_ERROR);
    } catch (JsonException $exception) {
        jsonResponse(['ok' => false, 'error' => 'El cuerpo JSON no es válido'], 400);
    }
    if (!is_array($body)) {
        jsonResponse(['ok' => false, 'error' => 'El cuerpo JSON debe ser un objeto'], 400);
    }
    $path = '/api/olt/casos-abiertos/lote';
    $query = [];
}

try {
    $services = require __DIR__ . '/../config/microservices.php';
    $config = $services['datos'];
    $client = new MicroserviceClient($config['base_url'], 15, (int) $config['connect_timeout']);
    $result = $method === 'GET'
        ? $client->get($path, $query)
        : $client->post($path, $body);
    jsonResponse($result['body'], (int) $result['status']);
} catch (Throwable $exception) {
    error_log('[OLT CASOS HELIX] ' . $exception->getMessage());
    jsonResponse(['ok' => false, 'error' => 'No fue posible consultar el estado de casos Helix'], 503);
}
