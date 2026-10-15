<?php
declare(strict_types=1);

require_once __DIR__ . '/../lib/bootstrap.php';
requireMethod('GET');
if ($_GET !== []) {
    jsonResponse(['ok' => false, 'error' => 'Esta consulta no admite parámetros.'], 422);
}
if (session_status() === PHP_SESSION_ACTIVE) {
    session_write_close();
}
try {
    $result = datosClient()->get('/api/estados_helix/relaciones');
    $status = (int) $result['status'];
    if ($status < 200 || $status >= 300) {
        // Only known public errors may cross the adapter; never forward traces or DSNs.
        $detail = $result['body']['detail'] ?? '';
        $message = match (true) {
            $status === 503 && $detail === 'Ya hay una consulta de estados Helix en curso' => 'Ya hay una consulta de estados Helix en curso. Intenta actualizar cuando termine.',
            $status === 504 => 'La consulta superó el tiempo disponible. Intenta actualizar de nuevo.',
            default => 'El servicio no pudo completar la consulta de Estados Helix.',
        };
        jsonResponse(['ok' => false, 'error' => $message], $status >= 400 && $status <= 599 ? $status : 502);
    }
    $body = $result['body'];
    if (($body['ok'] ?? false) !== true || !is_array($body['incidentes'] ?? null)
        || !is_array($body['resumen_relaciones'] ?? null)) {
        jsonResponse(['ok' => false, 'error' => 'El servicio devolvió una respuesta inesperada.'], 502);
    }
    // Unverifiable identifiers are deliberately not delivered to the view.
    unset($body['no_verificables']);
    jsonResponse($body, $status);
} catch (Throwable $exception) {
    $message = $exception->getMessage();
    $invalid = $exception->getPrevious() instanceof JsonException || str_contains($message, 'respuesta inesperada');
    $timeout = preg_match('/timed? out|timeout/i', $message) === 1;
    jsonResponse(['ok' => false, 'error' => $invalid
        ? 'El servicio devolvió una respuesta JSON inválida.'
        : ($timeout ? 'Se agotó el tiempo de consulta del servicio.' : 'No fue posible conectar con el servicio de Estados Helix.')], $invalid ? 502 : ($timeout ? 504 : 503));
}
