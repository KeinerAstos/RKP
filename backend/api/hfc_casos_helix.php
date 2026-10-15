<?php
declare(strict_types=1);

/**
 * Consulta los casos INC, WO y TAS de un nodo HFC
 * mediante la API FastAPI local de RKP.
 */

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

function responder(int $http, array $datos): void
{
    http_response_code($http);
    echo json_encode($datos, JSON_UNESCAPED_UNICODE);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
    header('Allow: GET');
    responder(405, [
        'ok' => false,
        'error' => 'Metodo no permitido'
    ]);
}

$nodo = strtoupper(trim((string) ($_GET['nodo'] ?? '')));

if (!preg_match('/^[A-Z0-9._-]{1,120}$/', $nodo)) {
    responder(422, [
        'ok' => false,
        'error' => 'Identificador de nodo invalido'
    ]);
}

if (!function_exists('curl_init')) {
    responder(503, [
        'ok' => false,
        'error' => 'La extension cURL de PHP no esta disponible'
    ]);
}

// FastAPI se consulta desde el servidor, no desde el navegador.
$url = 'http://127.0.0.1:8000/api/hfc/casos-abiertos-helix'
     . '?nodo=' . rawurlencode($nodo);

$ch = curl_init($url);

curl_setopt_array($ch, [
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_CONNECTTIMEOUT => 3,
    CURLOPT_TIMEOUT => 30,
    CURLOPT_FOLLOWLOCATION => false,
    CURLOPT_HTTPHEADER => [
        'Accept: application/json'
    ],
]);

$respuesta = curl_exec($ch);
$codigo = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
$error = curl_error($ch);

curl_close($ch);

if ($respuesta === false) {
    error_log('[HFC HELIX] FastAPI no disponible: ' . $error);
    responder(503, [
        'ok' => false,
        'error' => 'Servicio Helix no disponible'
    ]);
}

$datos = json_decode($respuesta, true);

if (!is_array($datos)) {
    responder(502, [
        'ok' => false,
        'error' => 'Respuesta invalida de FastAPI'
    ]);
}

if ($codigo !== 200 || ($datos['ok'] ?? false) !== true) {
    responder(503, [
        'ok' => false,
        'error' => 'No fue posible consultar Oracle Helix'
    ]);
}

responder(200, $datos);
