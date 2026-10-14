<?php declare(strict_types=1);
/* RKP_ENV_UNIFICADO_V1: no destinos de conexión fijos en código. */
function rkp_root(): string { return dirname(__DIR__, 2); }
function rkp_env(string $name, string $default=''): string {
    static $values=null;
    if ($values===null) {
        $file=rkp_root().'/.env';
        if (!is_file($file)) throw new RuntimeException('No existe .env en la raíz de RKP');
        $values=[];
        foreach (file($file, FILE_IGNORE_NEW_LINES) ?: [] as $index=>$line) {
            if ($index===0) $line=preg_replace('/^\xEF\xBB\xBF/', '', $line);
            if (!preg_match('/^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$/', $line, $m)) continue;
            $v=$m[2];
            if (strlen($v)>1 && ($v[0]==='"' || $v[0]==="'")) {
                $end=strrpos($v,$v[0]); if ($end>0) $v=substr($v,1,$end-1);
            } else $v=preg_split('/\s+#/',$v,2)[0];
            $values[$m[1]]=$v;
        }
    }
    $value=getenv($name); return $value!==false ? $value : ($values[$name] ?? $default);
}
function rkp_required(string $name): string {
    $value=trim(rkp_env($name));
    if ($value==='') throw new RuntimeException('Falta '.$name.' en .env');
    return $value;
}
function rkp_env_int(string $name, int $default): int {
    $value=rkp_env($name,(string)$default);
    if (!preg_match('/^-?\d+$/',$value)) throw new RuntimeException($name.' debe ser numérico');
    return (int)$value;
}
function rkp_http_url(string $name): string {
    $value=rkp_required($name);$parts=parse_url($value);
    if (!$parts || !in_array($parts['scheme'] ?? '',['http','https'],true) || empty($parts['host']) || isset($parts['user']) || isset($parts['pass'])) {
        throw new RuntimeException($name.' debe ser una URL HTTP(S) sin credenciales');
    }
    return rtrim($value,'/');
}
function rkp_public_connections(): array {
    // Whitelist: no tokens, passwords, DB hosts or upstream Grafana credentials.
    return [
        'grafanaPublicUrl'=>rkp_env('GRAFANA_PUBLIC_URL'),
        'grafanaProxyPort'=>rkp_env_int('GRAFANA_PORT',0),
        'grafanaOltPath'=>rkp_env('GRAFANA_OLT_DASHBOARD_PATH'),
        'grafanaCmtsPath'=>rkp_env('GRAFANA_CMTS_DASHBOARD_PATH'),
        'grafanaOrgId'=>rkp_env('GRAFANA_ORG_ID','1'),
    ];
}
