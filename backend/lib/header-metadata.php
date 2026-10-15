<?php
declare(strict_types=1);
require_once __DIR__ . '/entorno.php';

// Sólo metadatos de resultados publicados. Nunca ejecuta una rutina.
function rkp_header_generated_at(string $job): ?string
{
    $dir = trim(rkp_env('INFLUX_RESULTADOS_DIR', 'backend/storage/influx'));
    $absolute = str_starts_with($dir, '/') || str_starts_with($dir, chr(92))
        || (strlen($dir) > 2 && $dir[1] === ':' && in_array($dir[2], ['/', chr(92)], true));
    if (!$absolute) {
        $dir = rkp_root() . '/' . $dir;
    }
    $handle = @fopen(rtrim($dir, '/\\') . '/' . $job . '.json', 'rb');
    if ($handle === false) return null;
    // El productor escribe generado_en primero. No carga los resultados masivos.
    try { $prefix = fread($handle, 4096); } finally { fclose($handle); }
    if (!is_string($prefix) || !preg_match('/^\s*\{\s*"generado_en"\s*:\s*"([^"]+)"/', $prefix, $m)) return null;
    $date = $m[1];
    return is_string($date) && strtotime($date) !== false ? $date : null;
}

function rkp_response_header_metadata(array $payload): array
{
    $name = basename((string) ($_SERVER['SCRIPT_FILENAME'] ?? ''));
    $jobs = [
        'gkp.php' => ['caidas' => 'olt_caidas_actuales', 'saturacion' => 'olt_saturacion_actual', 'crc' => 'olt_crc_actual'],
        'temperatura.php' => ['temperatura' => 'olt_temperatura'],
        'perdida_latencia.php' => ['perdida_latencia' => 'olt_perdida_latencia'],
        'recursos_zte.php' => ['recursos_zte' => 'zte_licencias'],
        'intermitencias.php' => ['intermitencias' => 'cmts_intermitencias'],
        'puertos_duplicados.php' => ['puertos_duplicados' => 'cmts_duplicados'],
        'intermitencias_ftth.php' => ['intermitencias_ftth' => 'olt_intermitencias_2'],
        'hfc.php' => ['hfc' => 'cmts_saturacion'],
    ];
    $sources = [];
    foreach ($jobs[$name] ?? [] as $key => $job) {
        $ok = ($payload['sources'][$key]['ok'] ?? $payload['ok'] ?? false) === true;
        $sources[$key] = ['ok' => $ok, 'updated_at' => $ok ? rkp_header_generated_at($job) : null];
    }
    if ($sources !== []) $payload['_rkp_header'] = ['sources' => $sources];
    return $payload;
}
