<?php

declare(strict_types=1);

require_once __DIR__ . '/../lib/bootstrap.php';

requireMethod('GET');

try {
    $response = datosClient()->get('/api/olt/recursos-huawei');
    $body = $response['body'];

    if (
        $response['status'] < 200
        || $response['status'] >= 300
        || ($body['ok'] ?? false) !== true
        || !is_array($body['data']['columnas'] ?? null)
        || !is_array($body['data']['filas'] ?? null)
    ) {
        throw new RuntimeException(
            'Respuesta inválida de recursos Huawei'
        );
    }

    jsonResponse([
        'ok' => true,
        'data' => [
            'columnas' => $body['data']['columnas'],
            'filas' => $body['data']['filas'],
        ],
    ]);
} catch (Throwable $error) {
    error_log('Recursos Huawei: ' . $error->getMessage());

    jsonResponse([
        'ok' => false,
        'error' => 'Servicio de recursos Huawei no disponible',
    ], 503);
}