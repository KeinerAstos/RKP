<?php declare(strict_types=1);
require_once dirname(__DIR__).'/lib/entorno.php';
$base=rkp_http_url('DATOS_SERVICE_URL');
$hfc=trim(rkp_env('HFC_DATOS_SERVICE_URL'))!=='' ? rkp_http_url('HFC_DATOS_SERVICE_URL') : $base;
return [
    'datos'=>[
        'base_url'=>$base,
        'timeout'=>rkp_env_int('DATOS_SERVICE_TIMEOUT_SECONDS',180),
        'connect_timeout'=>rkp_env_int('DATOS_SERVICE_CONNECT_TIMEOUT_SECONDS',3),
    ],
    'hfc'=>[
        'base_url'=>$hfc,
        'timeout'=>rkp_env_int('HFC_DATOS_TIMEOUT_SECONDS',0),
        'connect_timeout'=>rkp_env_int('DATOS_SERVICE_CONNECT_TIMEOUT_SECONDS',3),
    ],
];
