#!/usr/bin/env python3
"""Parche local: Estados Helix, 4 workers y lotes de 300. No modifica .env."""
import argparse
import ast
from datetime import datetime
import os
from pathlib import Path
import shutil
import sys
import tempfile

FRAGMENT = '# RKP_HELIX_WORKERS_300_V1\nclass _CursorCorte:\n    """Aplica un SCN comun y restringe las consultas principales al lote."""\n    def __init__(self, cursor, scn, perfil, ids=None):\n        self.cursor, self.scn, self.perfil, self.ids = cursor, int(scn), perfil, ids\n\n    def __getattr__(self, name):\n        return getattr(self.cursor, name)\n\n    def execute(self, sql, binds=None):\n        params = dict(binds or {})\n        if self.ids is not None and sql in (self.perfil[\'sql\'], self.perfil[\'historial\']):\n            names = []\n            for n, value in enumerate(self.ids):\n                key = \'hx_lote_\' + str(n)\n                params[key] = value\n                names.append(\':\' + key)\n            column = (\'INCIDENT_NUMBER\' if self.perfil is PERFILES[\'INC\'] else \'TASK_ID\')\n            if sql == self.perfil[\'historial\']:\n                column = \'INCIDENT_NUMBER\' if self.perfil is PERFILES[\'INC\'] else \'TASKORTASKGROUPID\'\n            # Insertar el filtro en la tabla fuente para limitar el trabajo Oracle.\n            if sql == self.perfil[\'historial\']:\n                if self.perfil is PERFILES[\'INC\']:\n                    sql = sql.replace(\'AND w.WORK_LOG_TYPE = 40000\', \'AND w.WORK_LOG_TYPE = 40000 AND w.INCIDENT_NUMBER IN (\' + (\',\'.join(names) or \'NULL\') + \')\')\n                else:\n                    sql = sql.replace(\'WHERE w.WORKINFOTYPE = 40000\', \'WHERE w.WORKINFOTYPE = 40000 AND w.TASKORTASKGROUPID IN (\' + (\',\'.join(names) or \'NULL\') + \')\')\n            elif self.perfil is PERFILES[\'INC\']:\n                sql += \' AND i.INCIDENT_NUMBER IN (\' + (\',\'.join(names) or \'NULL\') + \')\'\n            else:\n                sql += \' WHERE TASK_ID IN (\' + (\',\'.join(names) or \'NULL\') + \')\'\n        sql = re.sub(r\'\\bARADMIN\\.([A-Z_][A-Z0-9_]*)\\b\',\n                     lambda m: m.group(0) + \' AS OF SCN \' + str(self.scn), sql)\n        return self.cursor.execute(sql, params) if params else self.cursor.execute(sql)\n\n\ndef _conexion_paralela(deadline):\n    restante = deadline - time.monotonic() if deadline is not None else 8\n    if restante <= 0:\n        raise TimeoutError(\'Presupuesto de consulta agotado\')\n    return oracledb.connect(\n        user=settings.oracle_helix_user, password=settings.oracle_helix_password,\n        dsn=oracledb.makedsn(settings.oracle_helix_host, settings.oracle_helix_port,\n                             service_name=settings.oracle_helix_service_name),\n        tcp_connect_timeout=min(8, restante),\n    )\n\n\ndef consultar_incidentes(tipo=\'INC\'):\n    from concurrent.futures import ThreadPoolExecutor\n    from collections import deque\n    workers = settings.estados_helix_max_workers\n    size = settings.estados_helix_batch_size\n    if workers == 1:\n        return _consultar_lote(tipo)\n    if oracledb is None:\n        raise HTTPException(503, \'Falta instalar oracledb\')\n    if not all((settings.oracle_helix_host, settings.oracle_helix_service_name,\n                settings.oracle_helix_user, settings.oracle_helix_password)):\n        raise HTTPException(503, \'Falta configurar Oracle Helix en el .env\')\n    started = time.monotonic()\n    budget = settings.oracle_helix_query_budget_seconds\n    deadline = started + budget if budget > 0 else None\n    perfil = PERFILES[tipo]\n    with _conexion_paralela(deadline) as connection:\n        _limitar(connection, deadline)\n        with connection.cursor() as raw:\n            raw.arraysize = 300\n            raw.prefetchrows = 300\n            # No se abre una quinta conexion durante el trabajo de los workers.\n            raw.execute(\'SELECT DBMS_FLASHBACK.GET_SYSTEM_CHANGE_NUMBER, \'\n                        "ROUND((CAST(SYS_EXTRACT_UTC(SYSTIMESTAMP) AS DATE) - DATE \'1970-01-01\') * 86400) FROM dual")\n            scn, ahora = raw.fetchone()\n            ahora = Decimal(str(ahora))\n            cur = _CursorCorte(raw, scn, perfil)\n            _limitar(connection, deadline)\n            cur.execute(perfil[\'sql\'])\n            ids = []\n            seen = set()\n            for row in _filas(cur, connection, deadline):\n                key = str(row[0])\n                if key in seen:\n                    raise RuntimeError(\'Identificador duplicado en la vista Oracle\')\n                seen.add(key)\n                ids.append(key)\n    # Solo cuatro futuros en vuelo; no precargar resultados de todos los lotes.\n    chunks = iter([ids[n:n + size] for n in range(0, len(ids), size)] or [[]])\n    total_batches = max(1, (len(ids) + size - 1) // size)\n    merged = None\n    done = 0\n    print(f\'[HELIX] workers={workers}; lote={size}; registros={len(ids)}; lotes={total_batches}; SCN={int(scn)}\', flush=True)\n    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix=\'helix\') as pool:\n        pending = deque()\n        def submit():\n            chunk = next(chunks, None)\n            if chunk is not None:\n                pending.append(pool.submit(_consultar_lote, tipo, chunk, scn, ahora, deadline))\n        for _ in range(workers):\n            submit()\n        try:\n            while pending:\n                data = pending.popleft().result()\n                if merged is None:\n                    merged = data\n                else:\n                    for key in (perfil[\'contador\'], \'total\', \'menores_de_6h\', \'total_no_verificables\'):\n                        merged[key] += data[key]\n                    merged[perfil[\'coleccion\']].extend(data[perfil[\'coleccion\']])\n                    merged[\'no_verificables\'].extend(data[\'no_verificables\'])\n                    for key in (\'por_estado\', \'motivos_no_verificables\'):\n                        counter = Counter(merged[key]); counter.update(data[key]); merged[key] = dict(counter)\n                done += 1\n                print(f\'[HELIX] lotes completos={done}/{total_batches}\', flush=True)\n                submit()\n        except Exception:\n            for future in pending:\n                future.cancel()\n            raise\n    merged[perfil[\'coleccion\']].sort(key=lambda r: (-r[\'segundos_en_estado\'], r[\'numero\']))\n    merged[perfil[\'cobertura\']] = not merged[\'no_verificables\']\n    if tipo == \'INC\':\n        casos = merged[\'incidentes\']\n        tasks = {t[\'numero\']: t for caso in casos for t in caso[\'tareas\']}\n        resumen = merged[\'resumen_relaciones\']\n        resumen.update(total_tareas=len(tasks),\n                       inc_con_tareas=sum(bool(c[\'tareas\']) for c in casos),\n                       tas_tiempo_verificable=sum(t[\'tiempo_estado_verificable\'] for t in tasks.values()),\n                       tas_tiempo_no_verificable=sum(not t[\'tiempo_estado_verificable\'] for t in tasks.values()))\n    merged[\'duracion_segundos\'] = round(time.monotonic() - started, 3)\n    merged[\'ejecucion\'] = {\'workers_configurados\': workers, \'workers_efectivos\': min(workers, total_batches),\n                          \'tamano_lote\': size, \'lotes_totales\': total_batches, \'scn\': str(int(scn))}\n    return merged\n'
MARK = '# RKP_HELIX_WORKERS_300_V1'

def replace_once(s, old, new):
    if s.count(old) != 1:
        raise ValueError('Version no compatible; falta bloque unico: ' + old[:90])
    return s.replace(old, new, 1)

def patch_router(s):
    if MARK in s:
        return s
    s = replace_once(s, 'def consultar_incidentes(tipo="INC"):',
        'def _consultar_lote(tipo="INC", _ids=None, _scn=None, _ahora=None, _deadline=None):')
    s = replace_once(s, 'deadline = started + budget if budget > 0 else None',
        'deadline = _deadline if _deadline is not None else (started + budget if budget > 0 else None)')
    s = replace_once(s, '            cursor.prefetchrows = 500',
        '            cursor.prefetchrows = 300\n            cursor.arraysize = 300\n            if _scn is not None:\n                cursor = _CursorCorte(cursor, _scn, perfil, _ids)')
    s = replace_once(s, '            ahora = Decimal(str(cursor.fetchone()[0]))',
        '            ahora_leido = Decimal(str(cursor.fetchone()[0]))\n            ahora = _ahora if _ahora is not None else ahora_leido')
    s = s.replace('cursor.fetchmany(500)', 'cursor.fetchmany(300)')
    s = replace_once(s, 'range(0, len(valores), 200)', 'range(0, len(valores), settings.estados_helix_batch_size)')
    s = replace_once(s, 'valores[inicio:inicio + 200]', 'valores[inicio:inicio + settings.estados_helix_batch_size]')
    s = s.replace('hasta 200 IDs', 'hasta estados_helix_batch_size IDs')
    s = replace_once(s, 'def _obtener(tipo):', FRAGMENT + '\n\ndef _obtener(tipo):')
    s = s.replace('Las lecturas comparten una transacción Oracle READ ONLY y un instante de corte.',
        'En paralelo, las lecturas comparten un SCN Oracle y un instante de corte.')
    ast.parse(s)
    return s

def patch_config(s):
    if 'estados_helix_max_workers:' in s:
        if 'estados_helix_batch_size:' not in s:
            raise ValueError('Configuracion parcial; no se escribio nada')
        return s
    s = replace_once(s, '    # Oracle Helix, conectado mediante el puente local existente.',
        '    # Estados Helix: limites exclusivos para esta consulta.\n'
        '    estados_helix_max_workers: int = Field(default=4, ge=1, le=4)\n'
        '    estados_helix_batch_size: int = Field(default=300, ge=1, le=300)\n\n'
        '    # Oracle Helix, conectado mediante el puente local existente.')
    ast.parse(s)
    return s

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    root = args.root.resolve()
    changes=[]
    for relative, transform in [('microservicios/estados_helix/router.py', patch_router),
                                ('microservicios/config.py', patch_config)]:
        p=root/relative
        raw=p.read_bytes()
        text=raw.decode('utf-8-sig').replace('\r\n','\n')
        result=transform(text)
        if result != text:
            newline='\r\n' if b'\r\n' in raw else '\n'
            data=(b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+result.replace('\n',newline).encode('utf-8')
            changes.append((p,raw,data))
    if not changes:
        print('El parche ya esta aplicado. Sin cambios.')
        return
    if args.check:
        print('VALIDACION OK. Archivos previstos:')
        for p,_,_ in changes: print(p)
        return
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backups={}
    # Respaldar TODOS antes de escribir el primero.
    for p,raw,_ in changes:
        backup=p.with_name(p.name+'.'+stamp+'.bak')
        shutil.copy2(p,backup)
        if backup.read_bytes()!=raw: raise ValueError('Respaldo no verificable: '+str(p))
        backups[p]=backup
        print('RESPALDADO:',backup)
    written=[]
    try:
        for p,raw,data in changes:
            if p.read_bytes()!=raw: raise ValueError('Archivo cambiado durante el parche: '+str(p))
            fd,name=tempfile.mkstemp(dir=p.parent,prefix=p.name+'.',suffix='.tmp')
            temp=Path(name)
            try:
                with os.fdopen(fd,'wb') as f:
                    f.write(data);f.flush();os.fsync(f.fileno())
                shutil.copymode(p,temp)
                os.replace(temp,p)
            finally:
                temp.unlink(missing_ok=True)
            written.append(p)
            print('MODIFICADO:',p)
    except Exception:
        for p in reversed(written):
            shutil.copy2(backups[p],p)
            print('RESTAURADO:',p)
        raise
    print('OK: defaults 4 workers / 300 IDs. No se modifico el .env.')
    print('Reinicia el proceso API que carga Estados Helix antes de probar la rutina.')
    print('El modo paralelo requiere lectura AS OF SCN y DBMS_FLASHBACK.GET_SYSTEM_CHANGE_NUMBER en Oracle.')
    print('Si Oracle lo rechaza, se conserva el JSON publicado anterior; usa ESTADOS_HELIX_MAX_WORKERS=1 para el modo secuencial.')

if __name__=='__main__':
    try: main()
    except (OSError,ValueError,SyntaxError,UnicodeError) as exc:
        print('ERROR:',exc,file=sys.stderr)
        sys.exit(1)
