<?php
declare(strict_types=1);
// RKP_ESTADOS_HELIX_RUTINA_V1: lectura compartida, sin Oracle por usuario.
require_once __DIR__ . '/../lib/bootstrap.php';
requireMethod('GET');
if ($_GET !== []) {
    jsonResponse(['ok' => false, 'error' => 'Esta consulta no admite parámetros.'], 422);
}
if (session_status() === PHP_SESSION_ACTIVE) { session_write_close(); }
header('Cache-Control: no-store');
$ruta = __DIR__ . '/../storage/estados_helix/actual.json';
if (!is_file($ruta)) {
    jsonResponse(['ok' => false, 'error' => 'Estados Helix aún no tiene una lectura publicada. Ejecuta la rutina estados_helix y vuelve a actualizar.'], 503);
}
try {
    $raw = file_get_contents($ruta);
    if ($raw === false) { throw new RuntimeException('Lectura no disponible'); }
    $body = json_decode($raw, true, 512, JSON_THROW_ON_ERROR);
    if (!is_array($body) || ($body['ok'] ?? false) !== true
        || !is_array($body['incidentes'] ?? null)
        || !is_array($body['resumen_relaciones'] ?? null)) {
        throw new RuntimeException('Contrato inválido');
    }
    unset($body['no_verificables']);
    // fecha_corte conserva la fecha REAL de Oracle: actualizar la página solo relee.
    header('X-RKP-Data-Source: rutina-estados-helix');
    jsonResponse($body, 200);
} catch (Throwable $exception) {
    jsonResponse(['ok' => false, 'error' => 'No fue posible leer el último resultado de Estados Helix. Revisa la rutina.'], 503);
}
