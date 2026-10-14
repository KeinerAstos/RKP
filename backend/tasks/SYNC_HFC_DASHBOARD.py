#!/usr/bin/env python3
"""Sincroniza un CSV HFC y lo importa por PHP. Solo librerías estándar."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def settings():
    sys.path.insert(0,str(ROOT))
    from microservicios.entorno import read_env
    values=dict(read_env());values.update(os.environ)
    return values


def run(cmd, timeout=180):
    p = subprocess.run(cmd, capture_output=True, text=True, errors='replace',
                       timeout=timeout, stdin=subprocess.DEVNULL,
                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    if p.returncode:
        raise RuntimeError((p.stderr or p.stdout or f'Código {p.returncode}').strip()[-2000:])
    return p.stdout.strip()


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def php_binary(env):
    candidates = [env.get('HFC_PHP_EXE', ''), shutil.which('php') or '',
                  str(ROOT.parent.parent / 'php/php.exe')]
    for item in candidates:
        if item and Path(item).is_file():
            return item
    raise RuntimeError('Configura HFC_PHP_EXE en .env (ruta a php.exe)')


def publish_json(path, data):
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False,
                                     dir=path.parent, prefix='.meta_') as f:
        json.dump(data, f, ensure_ascii=False)
        temp = Path(f.name)
    try:
        if path.exists():
            shutil.copy2(path, path.with_name(path.name + '.last_good'))
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', type=Path, help='Importa un CSV local sin conexión SSH')
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--install-task', action='store_true', help='Crea tarea del usuario actual cada 5 minutos')
    args = parser.parse_args()
    env = settings()
    if args.install_task:
        if os.name != 'nt':
            raise RuntimeError('El registro de tarea solo aplica a Windows')
        name = 'RKP - Dashboard HFC Sync'
        exists = subprocess.run(['schtasks.exe', '/Query', '/TN', name], capture_output=True)
        if exists.returncode == 0:
            raise RuntimeError('La tarea ya existe; se conserva. Revísala en el Programador de tareas')
        task = subprocess.list2cmdline([sys.executable, str(Path(__file__).resolve())])
        run(['schtasks.exe', '/Create', '/TN', name, '/SC', 'MINUTE', '/MO', '5',
             '/TR', task, '/RL', 'LIMITED'])
        print('Tarea creada:', name)
        return 0
    if not args.csv and env.get('HFC_SYNC_ENABLED', 'false').lower() not in ('true','1','yes'):
        print('SKIP: HFC_SYNC_ENABLED=false. Para CSV local usa --csv RUTA')
        return 0
    php = php_binary(env)
    api = ROOT / 'backend/api/dashboard_hfc.php'
    config = json.loads(run([php, str(api), '--export-config']))
    data = Path(config['data']); data.mkdir(parents=True, exist_ok=True)
    # OS lock releases even if the process crashes; no stale lock directory.
    lock = (data / '.sync.lock').open('a+b')
    try:
        if os.name == 'nt':
            import msvcrt
            if lock.seek(0, 2) == 0: lock.write(b'0'); lock.flush()
            lock.seek(0)
            try: msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                print('SKIP: otra sincronización está activa'); return 0
        else:
            import fcntl
            try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                print('SKIP: otra sincronización está activa'); return 0
        meta_path = data / 'ultima_carga_hfc_auto.json'
        previous = json.loads(meta_path.read_text()) if meta_path.is_file() else {}
        with tempfile.TemporaryDirectory(prefix='hfc_sync_', dir=data) as td:
            csv = Path(td) / 'hfc_unificado_actual.csv'
            source_ts = None
            if args.csv:
                source = args.csv.expanduser().resolve()
                shutil.copy2(source, csv); source_ts = int(source.stat().st_mtime)
                source_name, source_host = str(source), 'LOCAL'
            else:
                host = env.get('HFC_SYNC_HOST', '').strip()
                user = env.get('HFC_SYNC_USER', '').strip()
                remote = env.get('HFC_SYNC_REMOTE_CSV', '').strip()
                if not host or not user or not remote or host.startswith('-') or user.startswith('-'):
                    raise RuntimeError('Configura HFC_SYNC_HOST, HFC_SYNC_USER y HFC_SYNC_REMOTE_CSV en .env')
                port = int(env.get('HFC_SYNC_PORT', '22'))
                if not 1 <= port <= 65535: raise RuntimeError('Puerto SSH inválido')
                options = ['-o','BatchMode=yes','-o','ConnectTimeout=15']
                key = env.get('HFC_SYNC_KEY_PATH','').strip()
                if key:
                    if not Path(key).is_file(): raise RuntimeError('No existe la llave HFC_SYNC_KEY_PATH')
                    options += ['-i', key]
                ssh = shutil.which('ssh'); scp = shutil.which('scp')
                if not ssh or not scp: raise RuntimeError('Se requieren ssh.exe y scp.exe')
                stat = run([ssh, *options, '-p', str(port), user+'@'+host,
                            'stat -c '+shlex.quote('%s|%Y')+' -- '+shlex.quote(remote)], 35)
                size, source_ts = map(int, stat.split('|'))
                if size <= 0: raise RuntimeError('CSV remoto vacío')
                if not args.force and previous.get('source_timestamp') == source_ts and previous.get('source_size') == size:
                    print('SIN_CAMBIOS: conserva base actual'); return 0
                extra = ['-O'] if env.get('HFC_SCP_LEGACY','false').lower() in ('true','1') else []
                run([scp, *extra, *options, '-P', str(port), user+'@'+host+':'+remote, str(csv)], 180)
                if csv.stat().st_size != size: raise RuntimeError('Descarga incompleta; no se importa')
                source_name, source_host = remote, host
            with csv.open('r', encoding='utf-8-sig', errors='replace') as f:
                header = f.readline().upper()
            if 'FABRICANTE' not in header or 'CMTS' not in header or not any(x in header for x in ['ELEMENTO','SERVICE_GROUP','FIBER_NODE','NODO']):
                raise RuntimeError('Encabezado CSV HFC inválido; se conserva base actual')
            digest = sha(csv)
            if not args.force and previous.get('sha256','').lower() == digest.lower():
                print('SIN_CAMBIOS_HASH: no se repite importación'); return 0
            result = json.loads(run([php, str(api), '--import', str(csv)], 120))
            if not result.get('ok'):
                raise RuntimeError('Importador: '+json.dumps(result,ensure_ascii=False))
            destination = data / 'hfc_unificado_actual.csv'
            if destination.exists(): shutil.copy2(destination, data / 'hfc_unificado_actual.csv.last_good')
            os.replace(csv, destination)
            publish_json(meta_path, {'ok':True,'mode':'HFC_AUTO_REMOTE_SYNC' if not args.csv else 'HFC_LOCAL_IMPORT',
                'source':source_name,'source_host':source_host,'source_timestamp':source_ts,
                'source_iso':datetime.fromtimestamp(source_ts,timezone.utc).isoformat(),
                'source_size':destination.stat().st_size,'sha256':digest,
                'rows':result.get('total_final'), 'imported_iso':datetime.now(timezone.utc).isoformat()})
            print('OK:', json.dumps(result,ensure_ascii=False))
            return 0
    finally:
        lock.close()


if __name__ == '__main__':
    try: raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as e:
        print('ERROR:', e, file=sys.stderr);raise SystemExit(1)
