<?php
declare(strict_types=1);

require_once __DIR__ . '/../lib/bootstrap.php';

requireMethod('GET');
$olt = trim((string) ($_GET['olt'] ?? ''));
$ports = trim((string) ($_GET['puertos'] ?? ''));
if ($olt === '' || $ports === '') {
    jsonResponse(['ok' => false, 'error' => 'Faltan los parámetros OLT o puertos'], 422);
}

try {
    $services = require __DIR__ . '/../config/microservices.php';
    $config = $services['datos'];
    $client = new MicroserviceClient($config['base_url'], 65, (int) $config['connect_timeout']);
    $result = $client->get('/api/olt/casos-abiertos', [
        'olt' => $olt,
        'puertos' => $ports,
    ]);
    jsonResponse($result['body'], (int) $result['status']);
} catch (Throwable $exception) {
    error_log('[OLT CASOS HELIX] ' . $exception->getMessage());
    jsonResponse(['ok' => false, 'error' => 'No fue posible consultar los casos Helix'], 503);
}
