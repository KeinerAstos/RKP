<?php declare(strict_types=1);
// Scoped compatibility helpers for the imported module; RKP config is untouched.
function rkp_hfc_root(): string { return dirname(__DIR__, 2); }
function rkp_hfc_env(string $name, string $default=''): string {
    static $values=null;
    if ($values===null) {
        $values=[];
        foreach ([rkp_hfc_root().'/microservicios/.env', rkp_hfc_root().'/.env'] as $file) {
            if (!is_file($file)) continue;
            foreach (file($file, FILE_IGNORE_NEW_LINES) ?: [] as $line) {
                if (!preg_match('/^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$/', $line, $m)) continue;
                $v=$m[2];
                if (strlen($v)>=2 && (($v[0]==='"' && substr($v,-1)==='"') || ($v[0]==="'" && substr($v,-1)==="'"))) $v=substr($v,1,-1);
                $values[$m[1]]=$v;
            }
        }
    }
    $v=getenv($name); return $v!==false ? $v : ($values[$name] ?? $default);
}
function dh_path(string $key): string {
    $root=rkp_hfc_root();
    $paths=['hfc_data'=>(rkp_hfc_env('HFC_DATA_PATH') ?: $root.'/backend/storage/dashboard_hfc'),
            'xpertrak'=>(rkp_hfc_env('HFC_XPERTRAK_PATH') ?: $root.'/backend/storage/xpertrak_dashboard')];
    return $paths[$key] ?? $root;
}
function dh_html(string $text): string { return htmlspecialchars($text,ENT_QUOTES,'UTF-8'); }
function dh_url(string $path='', string $scope='dashboard'): string {
    $script=str_replace('\\','/',$_SERVER['SCRIPT_NAME'] ?? '');
    $base=rkp_hfc_env('HFC_WEB_BASE_PATH');
    if ($base==='') {
        if (preg_match('~^(.*?)/(frontend|backend)/~',$script,$m)) $base=$m[1];
    }
    $base=rtrim($base,'/');
    if ($scope==='frontend') $base.='/frontend';
    $action=null;
    if (preg_match('~(?:api/dashboard_hfc|backend/api/hfc)/([a-z_]+)\.php$~',$path,$m)) $action=$m[1];
    if ($action!==null) return rtrim(dh_url(),'/').'/backend/api/dashboard_hfc.php?action='.$action;
    return $base . ($path!=='' ? '/'.ltrim($path,'/') : '');
}
function rkp_hfc_config(): array {
    return ['services'=>['hfc'=>['base_url'=>rtrim(rkp_hfc_env('HFC_API_BASE_URL'),'/')]]];
}
date_default_timezone_set('America/Bogota');
