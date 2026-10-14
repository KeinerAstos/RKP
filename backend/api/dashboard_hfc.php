<?php declare(strict_types=1);
require_once dirname(__DIR__).'/lib/dashboard_hfc.php';
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-cache');
if (PHP_SAPI!=='cli' && !ini_get('zlib.output_compression') && function_exists('ob_gzhandler')) ob_start('ob_gzhandler');
$action=(string)($_GET['action'] ?? 'estado');
if (PHP_SAPI==='cli') {
    if (($argv[1] ?? '')==='--export-config') {
        echo json_encode(['root'=>rkp_hfc_root(),'data'=>dh_path('hfc_data')]);exit;
    }
    if (($argv[1] ?? '')!=='--import' || !is_file($argv[2] ?? '')) {fwrite(STDERR,"Uso: php dashboard_hfc.php --import CSV\n");exit(2);}
    $action='importar_base';$_SERVER['REQUEST_METHOD']='POST';
    $_FILES['archivo']=['tmp_name'=>$argv[2],'name'=>basename($argv[2]),'error'=>UPLOAD_ERR_OK,'size'=>filesize($argv[2])];
}
$write=in_array($action,['importar_base','importar_incidentes'],true);
if (PHP_SAPI!=='cli' && ($_SERVER['REQUEST_METHOD'] ?? 'GET')!==($write?'POST':'GET')) {
    header('Allow: '.($write?'POST':'GET'));http_response_code(405);echo json_encode(['ok'=>false,'error'=>'Método no permitido']);exit;
}
if ($write && (($_FILES['archivo']['error'] ?? UPLOAD_ERR_NO_FILE)!==UPLOAD_ERR_OK)) {
    http_response_code(400);echo json_encode(['ok'=>false,'error'=>'Carga de archivo incompleta']);exit;
}
function rkp_hfc_version(): string {
    $parts=['code:'.filemtime(__FILE__).':'.filesize(__FILE__)];
    foreach (['estado_red.json','incidentes.json','catalogo_nodos_comunidad_aliado.json','ultima_carga_hfc_auto.json','ultima_carga_netcool.json'] as $f) {
        $p=dh_path('hfc_data').'/'.$f;clearstatcache(true,$p);
        $parts[]=$f.':'.(is_file($p)?filemtime($p).':'.filesize($p):'missing');
    }
    return hash('sha256',implode('|',$parts));
}
try {


header('Content-Type: application/json; charset=utf-8');
$dashboardDir = dirname(__DIR__, 2) . '/frontend';

$dataDir = dh_path('hfc_data');
$historyDir = $dataDir . DIRECTORY_SEPARATOR . 'historico';
if (!is_dir($dataDir)) @mkdir($dataDir, 0775, true);


function hfc_read_json(string $path, array $default=[]): array {
    if (!is_file($path)) return $default;
    $raw = file_get_contents($path);
    if ($raw === false || trim($raw)==='') return $default;
    $v = json_decode($raw, true, 512, JSON_THROW_ON_ERROR);
    if (!is_array($v)) throw new RuntimeException('JSON inválido: ' . basename($path));
    return $v;
}
function hfc_write_json(string $path, array $data): void {
    $tmp = tempnam(dirname($path), '.hfc_');
    if ($tmp === false) throw new RuntimeException('No se pudo crear archivo temporal');
    try {
        $json = json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR);
        if (file_put_contents($tmp, $json, LOCK_EX) === false) throw new RuntimeException('Error escribiendo datos');
        if (!rename($tmp, $path)) throw new RuntimeException('No se pudo publicar ' . basename($path));
    } finally {
        if (is_file($tmp)) unlink($tmp);
    }
}
function hfc_key(array $r): string {
    return strtoupper(trim((string)($r['fabricante'] ?? ''))).'|'.strtoupper(trim((string)($r['cmts'] ?? ''))).'|'.strtoupper(trim((string)($r['elemento'] ?? $r['service_group'] ?? '')));
}
function hfc_backup(string $path, string $historyDir, string $prefix): void {
    if (is_file($path) && !copy($path, $path . '.last_good')) {
        throw new RuntimeException('No se pudo respaldar ' . basename($path));
    }
}
function hfc_detect_delimiter(string $line): string {
    $semi = substr_count($line, ';'); $comma = substr_count($line, ',');
    return $semi >= $comma ? ';' : ',';
}
function hfc_csv_assoc(string $tmp): iterable {
    $fh=fopen($tmp,'rb');if(!$fh)throw new RuntimeException('No se pudo abrir CSV');
    try {
        $line=fgets($fh);if($line===false)return;
        $delim=hfc_detect_delimiter($line);rewind($fh);
        $header=fgetcsv($fh,0,$delim,'"','');if(!$header)return;
        $header=array_map(fn($x)=>strtoupper(trim((string)$x)),$header);
        $header[0]=preg_replace('/^\xEF\xBB\xBF/','',$header[0]);
        while(($row=fgetcsv($fh,0,$delim,'"',''))!==false){
            if(!array_filter($row,fn($v)=>trim((string)$v)!==''))continue;
            $record=[];foreach($header as $i=>$name)$record[$name]=$row[$i] ?? '';
            yield $record;
        }
    } finally {fclose($fh);}
}
if (($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'POST') {
    $hfcImportLock = fopen($dataDir . '/.import.lock', 'c');
    if (!$hfcImportLock || !flock($hfcImportLock, LOCK_EX | LOCK_NB)) {
        http_response_code(409); echo json_encode(['ok'=>false,'error'=>'Otra importación está activa']); exit;
    }
    register_shutdown_function(static function() use ($hfcImportLock): void {
        flock($hfcImportLock, LOCK_UN); fclose($hfcImportLock);
    });
}

 switch($action) {
case 'estado':
$version=rkp_hfc_version();
$cachePath=$dataDir.'/.estado_cache.json';$tagPath=$dataDir.'/.estado_cache.version';
$etag='"'.$version.'"';header('ETag: '.$etag);
if (($_SERVER['HTTP_IF_NONE_MATCH'] ?? '')===$etag) {http_response_code(304);exit;}
$cacheLock=fopen($dataDir.'/.estado_cache.lock','c');
if (!$cacheLock || !flock($cacheLock,LOCK_EX)) throw new RuntimeException('No se pudo bloquear cache');
if (is_file($cachePath) && is_file($tagPath) && trim((string)file_get_contents($tagPath))===$version) {
    readfile($cachePath);flock($cacheLock,LOCK_UN);fclose($cacheLock);exit;
}
$statePath=$dataDir.DIRECTORY_SEPARATOR.'estado_red.json';
$incPath=$dataDir.DIRECTORY_SEPARATOR.'incidentes.json';
$rows=hfc_read_json($statePath,[]);

/* CATALOGO NODOS COMUNIDAD ALIADO V2 - SOPORTE MULTINODO
 * Llave simple:
 *   dashboard.service_group / elemento -> catalogo.NODES
 *
 * Llave compuesta:
 *   "4VD,3VD" -> ["4VD","3VD"]
 *
 * Para cada nodo se busca COMUNIDAD y ALIADO.
 * Si todos coinciden, se muestra un solo valor.
 * Si existen valores diferentes, se muestran valores unicos separados por " / ".
 */
$catalogPath=$dataDir.DIRECTORY_SEPARATOR.'catalogo_nodos_comunidad_aliado.json';
$catalogRows=hfc_read_json($catalogPath,[]);
$catalogMap=[];

foreach($catalogRows as $__cat){
    $__node=strtoupper(trim((string)($__cat['nodes']??'')));
    if($__node!=='') $catalogMap[$__node]=$__cat;
}

foreach($rows as &$__rowCat){
    $__rawNode=strtoupper(trim((string)($__rowCat['service_group']??$__rowCat['elemento']??'')));

    // CASA puede entregar Service Groups con varios nodos, por ejemplo "4VD,3VD".
    $__nodes=array_values(array_filter(
        array_map('trim', preg_split('/[,;|]+/', $__rawNode) ?: []),
        static fn($__v)=>$__v!==''
    ));

    if(!$__nodes && $__rawNode!=='') $__nodes=[$__rawNode];

    $__comunidades=[];
    $__aliados=[];
    $__matched=[];
    $__unmatched=[];

    foreach($__nodes as $__node){
        if(isset($catalogMap[$__node])){
            $__cat=$catalogMap[$__node];

            $__comunidad=trim((string)($__cat['comunidad']??''));
            $__aliado=trim((string)($__cat['aliado']??''));

            if($__comunidad!=='' && !in_array($__comunidad,$__comunidades,true)){
                $__comunidades[]=$__comunidad;
            }
            if($__aliado!=='' && !in_array($__aliado,$__aliados,true)){
                $__aliados[]=$__aliado;
            }
            $__matched[]=$__node;
        } else {
            $__unmatched[]=$__node;
        }
    }

    $__rowCat['comunidad']=implode(' / ',$__comunidades);
    $__rowCat['aliado']=implode(' / ',$__aliados);
    $__rowCat['catalogo_nodo_match']=count($__matched)>0;
    $__rowCat['catalogo_nodos_match']=$__matched;
    $__rowCat['catalogo_nodos_sin_match']=$__unmatched;
}
unset($__rowCat);

/*
 * REGLA OPERATIVA HFC OFICIAL
 * TOTAL <= 0              => SIN MODEMS
 * OFFLINE <= 0            => ENGANCHADO
 * 0 < OFFLINE < TOTAL     => DESENGANCHE PARCIAL
 * OFFLINE >= TOTAL        => DESENGANCHE TOTAL
 *
 * Se recalcula en lectura para NO depender de clasificaciones históricas
 * guardadas dentro de estado_red.json.
 */
/* MAPEO DRDA DORADAL V1
 * Correccion inmediata de ciudad en ATLAS.
 * DRDA-*       => DORADAL
 * PERE-DOSQ-* => DOSQUEBRADAS
 */
foreach($rows as &$__zonaRow){
    $__cmtsZona=strtoupper(trim((string)($__zonaRow['cmts']??'')));
    if(str_starts_with($__cmtsZona,'DRDA-')){
        $__zonaRow['zona']='DORADAL';
    } elseif(str_starts_with($__cmtsZona,'PERE-DOSQ-')){
        $__zonaRow['zona']='DOSQUEBRADAS';
    }
}
unset($__zonaRow);

foreach($rows as &$__hfcRow){
    $__total=(int)($__hfcRow['total_modems']??0);
    $__offline=(int)($__hfcRow['offline']??0);

    $__estadoFuente=strtoupper(trim((string)($__hfcRow['observacion']??'')));

    $__estadosHistoricos=[
        'POSIBLE DESENGANCHE TOTAL / HISTORICO',
        'POSIBLE CAIDA PROLONGADA / HISTORICO',
        'CERO CON EVIDENCIA HISTORICA / VALIDAR'
    ];

    if(in_array($__estadoFuente,$__estadosHistoricos,true)){
        // Respetar clasificacion historica V2.
        $__hfcRow['observacion']=$__estadoFuente;
    } elseif($__total<=0){
        $__hfcRow['observacion']='SIN MODEMS / VALIDAR';
    } elseif($__offline<=0){
        $__hfcRow['observacion']='ENGANCHADO';
    } elseif($__offline>=$__total){
        $__hfcRow['observacion']='DESENGANCHE TOTAL';
    } else {
        $__hfcRow['observacion']='DESENGANCHE PARCIAL';
    }

    $__hfcRow['porc_offline']=$__total>0 ? ($__offline/$__total) : 0;
}
unset($__hfcRow);
$incs=hfc_read_json($incPath,[]);

$exact=[];$aliasInc=[];
foreach($incs as $inc){
    $fab=strtoupper(trim((string)($inc['fabricante']??'')));
    $cmts=strtoupper(trim((string)($inc['cmts']??'')));
    $el=strtoupper(trim((string)($inc['elemento']??$inc['node_alias']??'')));
    if($el==='') continue;
    if($fab!=='' && $cmts!=='') $exact[$fab.'|'.$cmts.'|'.$el]=$inc;
    if(!isset($aliasInc[$el])) $aliasInc[$el]=[];
    $aliasInc[$el][]=$inc;
}
$networkAliasCount=[];
foreach($rows as $r){
    $el=strtoupper(trim((string)($r['service_group']??$r['elemento']??'')));
    if($el!=='') $networkAliasCount[$el]=($networkAliasCount[$el]??0)+1;
}

foreach($rows as &$r){
    $fab=strtoupper(trim((string)($r['fabricante']??'')));
    $cmts=strtoupper(trim((string)($r['cmts']??'')));
    $el=strtoupper(trim((string)($r['service_group']??$r['elemento']??'')));
    $k=$fab.'|'.$cmts.'|'.$el;
    $aff=in_array(($r['observacion']??''),['DESENGANCHE PARCIAL','DESENGANCHE TOTAL','POSIBLE DESENGANCHE TOTAL / HISTORICO','POSIBLE CAIDA PROLONGADA / HISTORICO'],true);
    $hit=$exact[$k]??null;

    // Solo cruce por alias cuando el alias existe una sola vez en la red.
    if($hit===null && $el!=='' && ($networkAliasCount[$el]??0)===1 && isset($aliasInc[$el]) && count($aliasInc[$el])>=1){
        $hit=$aliasInc[$el][0];
    }

    if($hit!==null){
        $r['incidente']=$hit['incidente']??$hit['ttnumber_helix']??'';
        $r['inc_status']='CON INCIDENTE';
        $r['incidente_data']=$hit;
    } elseif($aff){
        $r['inc_status']='SIN INCIDENTE';
        $r['incidente']='';
    } elseif(in_array(($r['observacion']??''),['ENGANCHADO','OPERATIVO'],true)){
        $r['inc_status']='NO APLICA'; $r['incidente']='';
    } else {
        $r['inc_status']='REVISAR'; $r['incidente']='';
    }
}
unset($r);
$response=['ok'=>true,'actualizado'=>is_file($statePath)?date('c',filemtime($statePath)):null,'total'=>count($rows),'rows'=>$rows];
hfc_write_json($cachePath,$response);
file_put_contents($tagPath,$version,LOCK_EX);
readfile($cachePath);flock($cacheLock,LOCK_UN);fclose($cacheLock);


break;
case 'incidentes':
$path=$dataDir.DIRECTORY_SEPARATOR.'incidentes.json';
if($_SERVER['REQUEST_METHOD']!=='GET'){
    http_response_code(405); echo json_encode(['ok'=>false,'error'=>'Método no permitido']); exit;
}
$rows=hfc_read_json($path,[]);
usort($rows,function($a,$b){
    return strcmp((string)($b['first_occurrence']??''),(string)($a['first_occurrence']??''));
});
echo json_encode([
  'ok'=>true,
  'fuente'=>'NETCOOL',
  'actualizado'=>date('c'),
  'total'=>count($rows),
  'rows'=>$rows
],JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES);

break;
case 'importar_base':
$path=$dataDir.DIRECTORY_SEPARATOR.'estado_red.json';
if($_SERVER['REQUEST_METHOD']!=='POST' || !isset($_FILES['archivo'])){http_response_code(400);echo json_encode(['ok'=>false,'error'=>'Archivo requerido']);exit;}
$records=hfc_csv_assoc($_FILES['archivo']['tmp_name']);

function pick(array $r,array $names,string $d=''): string {foreach($names as $n)if(array_key_exists($n,$r))return trim((string)$r[$n]);return $d;}
function city_from_cmts(string $cmts): string {
  $c=strtoupper($cmts);
  if(str_starts_with($c,'DRDA-'))return 'DORADAL';
  if(str_starts_with($c,'PERE-DOSQ-'))return 'DOSQUEBRADAS';
  $p=explode('-',$c)[0]??'';
  $m=['ARME'=>'ARMENIA','BARR'=>'BARRANQUILLA','BOGO'=>'BOGOTA','BUCA'=>'BUCARAMANGA','CALI'=>'CALI','CHIA'=>'CHIA','CUCU'=>'CUCUTA','JAMU'=>'JAMUNDI','MADRI'=>'MADRID','MANI'=>'MANIZALES','MEDE'=>'MEDELLIN','PALM'=>'PALMIRA','PERE'=>'PEREIRA','POPA'=>'POPAYAN','SANT'=>'SANTA MARTA','SINC'=>'SINCELEJO','SOACH'=>'SOACHA','SOGA'=>'SOGAMOSO','SOLE'=>'SOLEDAD','TULU'=>'TULUA','VILL'=>'VILLAVICENCIO','YOPA'=>'YOPAL'];
  return $m[$p]??$p;
}
$out=[];$vendors=[];
foreach($records as $r){
    $vendor=strtoupper(pick($r,['FABRICANTE','VENDOR']));
    $cmts=pick($r,['CMTS']); $ip=pick($r,['IP']);
    $element=pick($r,['SERVICE_GROUP','FIBER_NODE','ELEMENTO','NODO']);
    if($vendor===''||$cmts===''||$element==='') continue;
    $total=(int)pick($r,['TOTAL_MODEMS','TOTAL'],'0');
    $offline=(int)pick($r,['OFFLINE'],'0');
    $porc=$total>0?$offline/$total:0;

    // HFC HISTORICO V2:
    // Los estados historicos calculados en LNXAUTOBOAPR02 tienen prioridad.
    // Si el CSV no trae uno de esos estados, se aplica la regla instantanea normal.
    $obsFuente=strtoupper(trim((string)pick($r,['OBSERVACION','ESTADO'],'')));

    $estadosHistoricos=[
      'POSIBLE DESENGANCHE TOTAL / HISTORICO',
      'POSIBLE CAIDA PROLONGADA / HISTORICO',
      'CERO CON EVIDENCIA HISTORICA / VALIDAR'
    ];

    if(in_array($obsFuente,$estadosHistoricos,true)){
        $obs=$obsFuente;
    } elseif($total<=0){
        $obs='SIN MODEMS / VALIDAR';
    } elseif($offline<=0){
        $obs='ENGANCHADO';
    } elseif($offline>=$total){
        $obs='DESENGANCHE TOTAL';
    } else {
        $obs='DESENGANCHE PARCIAL';
    }
    $zona=pick($r,['ZONA','CIUDAD','REGIONAL'],city_from_cmts($cmts));
    $out[]=[
      'fabricante'=>$vendor,'zona'=>strtoupper($zona),'cmts'=>$cmts,'ip'=>$ip,'service_group'=>$element,
      'tipo_elemento'=>$vendor==='ARRIS'?'FIBER NODE':'SERVICE GROUP',
      'total_modems'=>$total,'active'=>(int)pick($r,['ACTIVE','OPER'],'0'),'registered'=>(int)pick($r,['REGISTERED'],'0'),
      'offline'=>$offline,'porc_offline'=>$porc,'observacion'=>$obs,
      'detalle_observacion'=>pick($r,['DETALLE_OBSERVACION']),
      'prioridad'=>pick($r,['PRIORIDAD']),
      'descripcion'=>pick($r,['DESCRIPCION','DESCRIPCIÓN']),
      'fecha_incidente'=>pick($r,['FECHA_INCIDENTE','FECHA Y','FECHA']),
      'hora_incidente'=>pick($r,['HORA_INCIDENTE','HORA']),
      'inc_status'=>''
    ];
    $vendors[$vendor]=true;
}
if(!$out){http_response_code(422);echo json_encode(['ok'=>false,'error'=>'No se encontraron filas con FABRICANTE, CMTS y ELEMENTO/SG/FIBER_NODE']);exit;}
if(count($vendors)===1){
    $current=hfc_read_json($path,[]);
    $only=array_key_first($vendors);
    $current=array_values(array_filter($current,fn($x)=>strtoupper((string)($x['fabricante']??''))!==$only));
    $final=array_merge($current,$out); $mode='REEMPLAZO FABRICANTE '.$only;
}else{
    $final=$out; $mode='REEMPLAZO BASE COMPLETA';
}
hfc_backup($path,$historyDir,'estado_red');
hfc_write_json($path,$final);
echo json_encode(['ok'=>true,'modo'=>$mode,'importados'=>count($out),'total_final'=>count($final),'fabricantes'=>array_keys($vendors)],JSON_UNESCAPED_UNICODE);

break;
case 'importar_incidentes':

$path=$dataDir.DIRECTORY_SEPARATOR.'incidentes.json';
$statePath=$dataDir.DIRECTORY_SEPARATOR.'estado_red.json';

if($_SERVER['REQUEST_METHOD']!=='POST' || !isset($_FILES['archivo'])){
    http_response_code(400);
    echo json_encode(['ok'=>false,'error'=>'Archivo requerido']);
    exit;
}

function nc_norm_header(string $s): string {
    $s=preg_replace('/^\xEF\xBB\xBF/','',$s);
    $s=strtoupper(trim($s));
    $s=str_replace([' ','-','.','/'],['_','_','','_'],$s);
    return $s;
}
function nc_is_time(string $s): bool { return preg_match('/^\d{1,2}:\d{2}(?::\d{2})?$/',trim($s))===1; }
function nc_is_date(string $s): bool { return preg_match('/^\d{1,2}\/\d{1,2}\/\d{4}$/',trim($s))===1; }
function nc_is_inc(string $s): bool { return preg_match('/\bINC\d{6,}\b/i',$s)===1; }
function nc_find_inc(array $row): string {
    foreach($row as $v) if(preg_match('/\b(INC\d{6,})\b/i',(string)$v,$m)) return strtoupper($m[1]);
    return '';
}
function nc_delimiter(string $line): string {
    $scores=["\t"=>substr_count($line,"\t"),";"=>substr_count($line,';'),","=>substr_count($line,','),"|"=>substr_count($line,'|')];
    arsort($scores);
    return (string)array_key_first($scores);
}
function nc_read_delimited(string $tmp): array {
    $fh=fopen($tmp,'rb'); if(!$fh) throw new RuntimeException('No se pudo abrir el archivo.');
    $first='';
    while(($first=fgets($fh))!==false && trim($first)===''){}
    if($first===false){fclose($fh);return [[],[]];}
    $first=preg_replace('/^\xEF\xBB\xBF/','',$first);
    $delim=nc_delimiter($first);
    rewind($fh);
    $rows=[];
    while(($r=fgetcsv($fh,0,$delim))!==false){
        if($delim==='|' && count($r)>=2){
            if(trim((string)$r[0])==='') array_shift($r);
            if(count($r) && trim((string)$r[count($r)-1])==='') array_pop($r);
        }
        if(count(array_filter($r,fn($x)=>trim((string)$x)!==''))===0) continue;
        $rows[]=$r;
    }
    fclose($fh);
    if(!$rows) return [[],[]];
    $header=array_map(fn($x)=>nc_norm_header((string)$x),array_shift($rows));
    // Markdown separator row
    if($rows && count(array_filter($rows[0],fn($x)=>preg_match('/^-{2,}$/',trim((string)$x))))>=2) array_shift($rows);
    return [$header,$rows];
}
function nc_xlsx_rows(string $tmp): array {
    if(!class_exists('ZipArchive')) throw new RuntimeException('Este PHP no tiene ZipArchive. Guarda el reporte como CSV y vuelve a cargarlo.');
    $zip=new ZipArchive();
    if($zip->open($tmp)!==true) throw new RuntimeException('No fue posible abrir XLSX.');
    $shared=[];
    $ss=$zip->getFromName('xl/sharedStrings.xml');
    if($ss!==false){
        $xml=simplexml_load_string($ss);
        if($xml!==false) foreach($xml->si as $si){
            $parts=[];
            if(isset($si->t)) $parts[]=(string)$si->t;
            foreach($si->r as $r) $parts[]=(string)$r->t;
            $shared[]=implode('',$parts);
        }
    }
    $sheet=$zip->getFromName('xl/worksheets/sheet1.xml');
    $zip->close();
    if($sheet===false) throw new RuntimeException('No se encontró la primera hoja del XLSX.');
    $xml=simplexml_load_string($sheet);
    if($xml===false) throw new RuntimeException('XLSX inválido.');
    $all=[];
    foreach($xml->sheetData->row as $row){
        $out=[]; $pos=0;
        foreach($row->c as $c){
            $ref=(string)$c['r'];
            if(preg_match('/^([A-Z]+)/',$ref,$m)){
                $letters=$m[1]; $idx=0;
                for($i=0;$i<strlen($letters);$i++) $idx=$idx*26+(ord($letters[$i])-64);
                $idx--;
            } else $idx=$pos;
            while(count($out)<$idx) $out[]='';
            $v=(string)$c->v;
            if((string)$c['t']==='s') $v=$shared[(int)$v]??'';
            elseif((string)$c['t']==='inlineStr') $v=(string)$c->is->t;
            $out[$idx]=$v; $pos=$idx+1;
        }
        if(count(array_filter($out,fn($x)=>trim((string)$x)!==''))) $all[]=$out;
    }
    if(!$all) return [[],[]];
    $header=array_map(fn($x)=>nc_norm_header((string)$x),array_shift($all));
    return [$header,$all];
}
function nc_assoc(array $header,array $row): array {
    $a=[]; foreach($header as $i=>$h) if($h!=='') $a[$h]=(string)($row[$i]??''); return $a;
}
function nc_pick(array $a,array $keys): string {
    foreach($keys as $k){$k=nc_norm_header($k); if(isset($a[$k]) && trim((string)$a[$k])!=='') return trim((string)$a[$k]);}
    return '';
}
function nc_guess_occurrence(array $row,array $a): array {
    $raw=nc_pick($a,['FIRSTOCCURRENCE','FIRST_OCCURRENCE','FECHA_CREACION']);
    $date='';$time='';
    if($raw!==''){
        if(preg_match('/(\d{1,2}\/\d{1,2}\/\d{4})/',$raw,$m))$date=$m[1];
        if(preg_match('/(\d{1,2}:\d{2}(?::\d{2})?)/',$raw,$m))$time=$m[1];
    }
    if($date==='' || $time===''){
        foreach($row as $i=>$v){
            $v=trim((string)$v);
            if($date==='' && nc_is_date($v)){
                $date=$v;
                if(isset($row[$i+1]) && nc_is_time((string)$row[$i+1])) $time=trim((string)$row[$i+1]);
                break;
            }
        }
    }
    return [$date,$time,trim($date.' '.$time)];
}
function nc_guess_alias(array $header,array $row,array $a): string {
    $alias=nc_pick($a,['NODEALIAS','NODE_ALIAS','ELEMENTO','NODO']);
    if($alias!=='' && !nc_is_time($alias) && !nc_is_date($alias) && !nc_is_inc($alias)) return $alias;
    foreach($row as $i=>$v){
        if(nc_is_time((string)$v) && isset($row[$i+1])){
            $cand=trim((string)$row[$i+1]);
            if($cand!=='' && !nc_is_date($cand) && !nc_is_inc($cand)) return $cand;
        }
    }
    return '';
}

$name=$_FILES['archivo']['name']??'';
$ext=strtolower(pathinfo($name,PATHINFO_EXTENSION));
try{
    [$header,$records]=($ext==='xlsx') ? nc_xlsx_rows($_FILES['archivo']['tmp_name']) : nc_read_delimited($_FILES['archivo']['tmp_name']);
}catch(Throwable $e){
    http_response_code(422); echo json_encode(['ok'=>false,'error'=>$e->getMessage()],JSON_UNESCAPED_UNICODE); exit;
}
if(!$header || !$records){
    http_response_code(422); echo json_encode(['ok'=>false,'error'=>'El archivo no contiene filas utilizables.']); exit;
}

$network=hfc_read_json($statePath,[]);
$aliasIndex=[];
foreach($network as $n){
    $alias=strtoupper(trim((string)($n['service_group']??$n['elemento']??'')));
    if($alias==='') continue;
    if(!isset($aliasIndex[$alias])) $aliasIndex[$alias]=[];
    $aliasIndex[$alias][]=$n;
}

$out=[];$discard=0;$withInc=0;$matched=0;$amb=0;
foreach($records as $row){
    $a=nc_assoc($header,$row);
    $severity=nc_pick($a,['SEVERITY']);
    if($severity==='' && isset($row[0])) $severity=trim((string)$row[0]);
    [$fecha,$hora,$occ]=nc_guess_occurrence($row,$a);
    $alias=nc_guess_alias($header,$row,$a);
    $inc=nc_find_inc($row);
    $ttHelix=nc_pick($a,['TTNUMBER_HELIX','TTNUMBERHELIX']);
    if($inc!=='' && ($ttHelix==='' || !nc_is_inc($ttHelix))) $ttHelix=$inc;
    $municipio=nc_pick($a,['MUNICIPIO','CIUDAD','ZONA']);
    $tt=nc_pick($a,['TTNUMBER','TT_NUMBER']);
    $agent=nc_pick($a,['AGENT']);
    $summary=nc_pick($a,['SUMMARY']);
    $tipo=nc_pick($a,['TIPOAFECTACION','TIPO_AFECTACION']);
    $cod=nc_pick($a,['CODALARM','COD_ALARM']);
    $location=nc_pick($a,['LOCATION']);
    $alertKey=nc_pick($a,['ALERTKEY','ALERT_KEY']);
    $alertGroup=nc_pick($a,['ALERTGROUP','ALERT_GROUP']);
    $cinum=nc_pick($a,['CINUM']);
    $cinumHelix=nc_pick($a,['CINUM_HELIX']);
    $ubicacion=nc_pick($a,['UBICACION']);

    if($alias===''){ $discard++; continue; }

    $fab='';$cmts='';$zona='';$cruce='SIN_CRUCE';
    $ak=strtoupper($alias);
    $matches=$aliasIndex[$ak]??[];
    if(count($matches)===1){
        $m=$matches[0];
        $fab=strtoupper(trim((string)($m['fabricante']??'')));
        $cmts=trim((string)($m['cmts']??''));
        $zona=trim((string)($m['zona']??''));
        if($municipio==='')$municipio=$zona;
        $cruce='ALIAS_UNICO'; $matched++;
    } elseif(count($matches)>1){
        $cruce='ALIAS_AMBIGUO'; $amb++;
    }

    if($inc!=='')$withInc++;
    $x=[
      'id'=>sha1(strtoupper($alias).'|'.$occ.'|'.$inc.'|'.$tt.'|'.$severity),
      'severity'=>$severity,
      'first_occurrence'=>$occ,
      'fecha_creacion'=>$fecha,
      'hora_creacion'=>$hora,
      'node_alias'=>$alias,
      'elemento'=>$alias,
      'incidente'=>$inc,
      'ttnumber_helix'=>$ttHelix,
      'municipio'=>$municipio,
      'zona'=>$municipio!==''?$municipio:$zona,
      'ttnumber'=>$tt,
      'codalarm'=>$cod,
      'agent'=>$agent,
      'summary'=>$summary,
      'tipo_afectacion'=>$tipo,
      'location'=>$location,
      'alert_key'=>$alertKey,
      'alert_group'=>$alertGroup,
      'cinum'=>$cinum,
      'cinum_helix'=>$cinumHelix,
      'ubicacion'=>$ubicacion,
      'fabricante'=>$fab,
      'cmts'=>$cmts,
      'estado_incidente'=>$severity!==''?$severity:'NETCOOL',
      'origen'=>'NETCOOL',
      'cruce_hfc'=>$cruce,
      'ultima_actualizacion'=>date('Y-m-d H:i:s')
    ];
    $out[]=$x;
}
if(count($out)===0){
    http_response_code(422);
    echo json_encode(['ok'=>false,'error'=>'No fue posible identificar NodeAlias en ninguna fila.']);
    exit;
}

// La carga NETCOOL reemplaza SOLO el dataset de incidentes, nunca estado_red.json.
hfc_backup($path,$historyDir,'incidentes_netcool');
hfc_write_json($path,$out);
$ncMetaPath=$dataDir.DIRECTORY_SEPARATOR.'ultima_carga_netcool.json';
hfc_backup($ncMetaPath,$historyDir,'ultima_carga_netcool');
hfc_write_json($ncMetaPath,[
  'fecha'=>date('c'),'archivo'=>$name,'filas_leidas'=>count($records),'importados'=>count($out),
  'descartados'=>$discard,'con_inc'=>$withInc,'cruce_unico'=>$matched,'cruce_ambiguo'=>$amb
]);

echo json_encode([
  'ok'=>true,
  'fuente'=>'NETCOOL',
  'archivo'=>$name,
  'modo'=>'REEMPLAZO SOLO INCIDENTES NETCOOL',
  'filas_leidas'=>count($records),
  'importados'=>count($out),
  'descartados'=>$discard,
  'con_inc'=>$withInc,
  'cruce_hfc_unico'=>$matched,
  'cruce_hfc_ambiguo'=>$amb
],JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES);

break;
case 'actualizaciones':


header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');

$dashboardDir = dirname(__DIR__, 2);
$dataDir = dh_path('hfc_data');

function hfc_file_meta(string $path, string $label = ''): array {
    if (!is_file($path)) {
        return [
            'existe' => false,
            'timestamp' => null,
            'iso' => null,
            'texto' => 'Sin información',
            'label' => $label
        ];
    }

    clearstatcache(true, $path);
    $ts = @filemtime($path);

    return [
        'existe' => true,
        'timestamp' => $ts ?: null,
        'iso' => $ts ? date('c', $ts) : null,
        'texto' => $ts ? date('d/m/Y H:i:s', $ts) : 'Fecha no disponible',
        'label' => $label
    ];
}

function hfc_auto_meta(string $metaPath, string $fallbackPath): array {
    if (is_file($metaPath)) {
        $raw = @file_get_contents($metaPath);
        $j = is_string($raw) ? json_decode($raw, true) : null;

        if (is_array($j)) {
            $ts = isset($j['source_timestamp']) ? (int)$j['source_timestamp'] : 0;
            $iso = (string)($j['source_iso'] ?? '');

            if ($ts > 0 || $iso !== '') {
                return [
                    'existe' => true,
                    'timestamp' => $ts > 0 ? $ts : null,
                    'iso' => $iso !== '' ? $iso : ($ts > 0 ? date('c', $ts) : null),
                    'texto' => $ts > 0 ? date('d/m/Y H:i:s', $ts) : $iso,
                    'importado_iso' => $j['imported_iso'] ?? null,
                    'sha256' => $j['sha256'] ?? null,
                    'filas' => $j['rows'] ?? null,
                    'modo' => 'HFC_AUTO_REMOTE'
                ];
            }
        }
    }

    $meta = hfc_file_meta($fallbackPath, 'fallback_estado_red');
    $meta['modo'] = 'FALLBACK_FILETIME';
    return $meta;
}

$estadoPath = $dataDir . DIRECTORY_SEPARATOR . 'estado_red.json';
$incPath = $dataDir . DIRECTORY_SEPARATOR . 'incidentes.json';
$hfcMetaPath = $dataDir . DIRECTORY_SEPARATOR . 'ultima_carga_hfc_auto.json';
$netcoolMetaPath = $dataDir . DIRECTORY_SEPARATOR . 'ultima_carga_netcool.json';

$cmts = hfc_auto_meta($hfcMetaPath, $estadoPath);
$netcool=hfc_file_meta($incPath,'incidentes_fallback');
if (is_file($netcoolMetaPath)) {
    $netMeta=hfc_read_json($netcoolMetaPath,[]);
    $netTs=isset($netMeta['fecha'])?strtotime((string)$netMeta['fecha']):false;
    if ($netTs!==false) $netcool=['existe'=>true,'timestamp'=>$netTs,'iso'=>date('c',$netTs),'texto'=>date('d/m/Y H:i:s',$netTs),'label'=>'ultima_carga_netcool'];
}

echo json_encode([
    'ok' => true,
    'version' => rkp_hfc_version(),
    'cmts' => $cmts,
    'estado_red' => $cmts,
    'netcool' => $netcool,
    'servidor' => date('c')
], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
break;
case 'qoe_actualizacion':


header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');

$dir = dh_path('xpertrak');
$maxDeltaSeconds = 20 * 60;

function atlas_file_stamp(string $path): int {
    $name = basename($path);
    if (preg_match('/_(\d{8})_(\d{6})\.csv$/i', $name, $m)) {
        $dt = DateTime::createFromFormat('Ymd_His', $m[1] . '_' . $m[2]);
        if ($dt instanceof DateTime) {
            return $dt->getTimestamp();
        }
    }

    $mtime = @filemtime($path);
    return $mtime === false ? 0 : (int)$mtime;
}

try {
    $centros = glob($dir . '/salud_diaria_centro_*.csv') ?: [];
    $regionales = glob($dir . '/salud_diaria_regionales_*.csv') ?: [];

    usort($centros, fn($a, $b) => atlas_file_stamp($b) <=> atlas_file_stamp($a));
    usort($regionales, fn($a, $b) => atlas_file_stamp($b) <=> atlas_file_stamp($a));

    $best = null;
    $bestScore = -1;

    foreach (array_slice($centros, 0, 30) as $centro) {
        $tc = atlas_file_stamp($centro);

        foreach (array_slice($regionales, 0, 30) as $regional) {
            $tr = atlas_file_stamp($regional);
            $delta = abs($tc - $tr);

            if ($delta > $maxDeltaSeconds) {
                continue;
            }

            $score = max($tc, $tr);
            if ($score > $bestScore) {
                $bestScore = $score;
                $best = [
                    'centro' => $centro,
                    'regionales' => $regional,
                    'delta_seconds' => $delta,
                ];
            }
        }
    }

    if ($best === null) {
        echo json_encode([
            'ok' => true,
            'available' => false,
            'updated_at_iso' => null,
            'message' => 'No existe un par CENTRO + REGIONALES valido.',
        ], JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
        exit;
    }

    $centroMtime = @filemtime($best['centro']);
    $regionalMtime = @filemtime($best['regionales']);

    $updatedTs = max(
        $centroMtime === false ? atlas_file_stamp($best['centro']) : (int)$centroMtime,
        $regionalMtime === false ? atlas_file_stamp($best['regionales']) : (int)$regionalMtime
    );

    echo json_encode([
        'ok' => true,
        'available' => true,
        'updated_at_iso' => date('c', $updatedTs),
        'pair_delta_seconds' => $best['delta_seconds'],
        'source_files' => [
            'centro' => basename($best['centro']),
            'regionales' => basename($best['regionales']),
        ],
    ], JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
} catch (Throwable $e) {
    http_response_code(500);
    echo json_encode([
        'ok' => false,
        'available' => false,
        'error' => $e->getMessage(),
    ], JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
}

break;
case 'analytics': case 'analytics_proxy': case 'rf_proxy':
    $base=rkp_hfc_env('HFC_API_BASE_URL');
    if ($base==='') {http_response_code(503);echo json_encode(['ok'=>false,'error'=>'API HFC externa sin configurar: completa HFC_API_BASE_URL en .env']);break;}
    $rf=$action==='rf_proxy';
    $resource=(string)($_GET['resource'] ?? $_GET['op'] ?? 'resumen');
    // Preserve action query used by RF by mapping it in the combined JS.
    $allowed=$rf?['schema','resumen','upstreams','ranking','spectrum']:['resumen','cmts','nodos','nodo'];
    if (!in_array($resource,$allowed,true)) {http_response_code(400);echo json_encode(['ok'=>false,'error'=>'Recurso no permitido']);break;}
    $query=[];
    foreach (['technology','node','cmts','upstream','search','limit','offset'] as $key) if(isset($_GET[$key])) $query[$key]=(string)$_GET[$key];
    if(isset($query['limit']))$query['limit']=(string)max(1,min(5000,(int)$query['limit']));
    if(isset($query['offset']))$query['offset']=(string)max(0,(int)$query['offset']);
    $suffix=$resource==='nodo'?'/nodo/'.rawurlencode((string)($_GET['name'] ?? '')):'/'.$resource;
    $url=rtrim($base,'/').'/api/deco/hfc/'.($rf?'rf':'analytics').$suffix.($query?'?'.http_build_query($query):'');
    if(!function_exists('curl_init'))throw new RuntimeException('Activa la extensión PHP curl para RF y analítica');
    $ch=curl_init($url);
    curl_setopt_array($ch,[CURLOPT_RETURNTRANSFER=>true,CURLOPT_CONNECTTIMEOUT=>5,CURLOPT_TIMEOUT=>max(5,min(90,(int)rkp_hfc_env('HFC_API_TIMEOUT_SECONDS','30'))),CURLOPT_HTTPHEADER=>['Accept: application/json']]);
    $body=curl_exec($ch);$status=(int)curl_getinfo($ch,CURLINFO_HTTP_CODE);$error=curl_error($ch);curl_close($ch);
    if($body===false)throw new RuntimeException('API HFC: '.$error);
    json_decode($body,true,512,JSON_THROW_ON_ERROR);
    http_response_code($status ?: 502);echo $body;
    break;
default: http_response_code(404);echo json_encode(['ok'=>false,'error'=>'Acción no disponible']);
 }
} catch(Throwable $e) {
    http_response_code(500);echo json_encode(['ok'=>false,'error'=>$e->getMessage()],JSON_UNESCAPED_UNICODE);
    if(PHP_SAPI==='cli')exit(1);
}
