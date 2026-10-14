"""RKP_ENV_UNIFICADO_V1: arranque común, conexiones exclusivas del .env raíz."""
from __future__ import annotations
import argparse
import ipaddress
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from microservicios.entorno import ROOT, boolean, env, load_env, port, required

RAIZ = ROOT


def url(host: str, number: int, path: str) -> str:
    if ':' in host and not host.startswith('['): host = '[' + host + ']'
    return f'http://{host}:{number}{path}'


def client_host(prefix: str) -> str:
    host = env(prefix + '_CLIENT_HOST').strip()
    if host: return host
    bind = required(prefix + '_HOST')
    try:
        if ipaddress.ip_address(bind).is_unspecified:
            raise RuntimeError('Configura ' + prefix + '_CLIENT_HOST para comprobar el listener')
    except ValueError:
        pass
    return bind


def tcp_open(host: str, number: int) -> bool:
    try:
        with socket.create_connection((host, number), timeout=.5): return True
    except OSError: return False


def healthy(target: str, expected: str) -> bool:
    try:
        with urlopen(Request(target,headers={'Accept':'application/json'}), timeout=2) as response:
            data=json.load(response)
        return data.get('ok') is True and data.get('service') == expected
    except (OSError, ValueError): return False


def stop(process):
    if process is None or process.poll() is not None: return
    process.terminate()
    try: process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill();process.wait(timeout=5)


def process_options(show: bool) -> dict:
    if os.name != 'nt': return {}
    return {'creationflags':subprocess.CREATE_NEW_CONSOLE if show else subprocess.CREATE_NO_WINDOW}


def start_tunnel(prefix: str):
    if not boolean(prefix + '_TUNNEL_ENABLED'): return None
    bind = required(prefix + '_TUNNEL_BIND_HOST');number = port(prefix + '_TUNNEL_LOCAL_PORT')
    if tcp_open(bind, number):
        print(f'[{prefix}] Puerto local {number} disponible; se conserva el proceso existente (no valida la DB)')
        return None
    ssh = shutil.which(env('SSH_EXECUTABLE', 'ssh'))
    if not ssh: raise RuntimeError('No se encontró el cliente SSH configurado')
    ssh_host = required(prefix + '_SSH_HOST');user = required(prefix + '_SSH_USER')
    if ssh_host.startswith('-') or user.startswith('-'): raise RuntimeError('Host/usuario SSH inválido')
    remote = required(prefix + '_TUNNEL_REMOTE_HOST');remote_port = port(prefix + '_TUNNEL_REMOTE_PORT')
    command=[ssh,'-N','-p',str(port(prefix + '_SSH_PORT')),
             '-o','ExitOnForwardFailure=yes','-o','ServerAliveInterval=30','-o','ServerAliveCountMax=3',
             '-o','ConnectTimeout='+env('SSH_CONNECT_TIMEOUT_SECONDS','15')]
    batch=boolean(prefix + '_SSH_BATCH_MODE')
    command+=['-o','BatchMode='+('yes' if batch else 'no')]
    key=env(prefix + '_SSH_KEY_PATH').strip()
    if key:
        key_path=Path(key).expanduser();key_path=key_path if key_path.is_absolute() else ROOT/key_path
        if not key_path.is_file(): raise RuntimeError('No existe '+prefix+'_SSH_KEY_PATH')
        command+=['-i',str(key_path)]
    forward_bind='['+bind+']' if ':' in bind else bind
    forward_remote='['+remote+']' if ':' in remote else remote
    command+=['-L',f'{forward_bind}:{number}:{forward_remote}:{remote_port}',user+'@'+ssh_host]
    print(f'[{prefix}] Abriendo túnel configurado en .env, puerto local {number}')
    show=boolean('SSH_SHOW_CONSOLE',True)
    if os.name=='nt' and not batch and not show:
        raise RuntimeError('SSH interactivo requiere SSH_SHOW_CONSOLE=true; para ocultarlo configura llave/agente y BatchMode')
    process=subprocess.Popen(command,cwd=ROOT,**process_options(show))
    try:
        deadline=time.monotonic()+int(env('SSH_READY_TIMEOUT_SECONDS','45'))
        while time.monotonic()<deadline:
            if process.poll() is not None: raise RuntimeError(f'{prefix} SSH terminó con código {process.returncode}')
            if tcp_open(bind,number):
                print(f'[{prefix}] Túnel disponible');return process
            time.sleep(.5)
        raise RuntimeError(prefix+' no abrió el puerto local a tiempo')
    except BaseException:
        stop(process);raise


def start_service(prefix: str, module: str, expected: str, health_path: str):
    bind=required(prefix+'_HOST');number=port(prefix+'_PORT');check_host=client_host(prefix)
    health_url=url(check_host,number,health_path)
    if tcp_open(check_host,number):
        if not healthy(health_url,expected):
            raise RuntimeError(f'{prefix}: puerto {number} ocupado por un servicio que no responde con el health esperado')
        print(f'[{prefix}] Servicio existente validado; no se reinicia');return None
    command=[sys.executable,'-m','uvicorn',module,'--host',bind,'--port',str(number)]
    print(f'[{prefix}] Iniciando listener {bind}:{number}')
    process=subprocess.Popen(command,cwd=ROOT,**process_options(boolean('UVICORN_SHOW_CONSOLE')))
    try:
        deadline=time.monotonic()+int(env('SERVICE_READY_TIMEOUT_SECONDS','45'))
        while time.monotonic()<deadline:
            if process.poll() is not None: raise RuntimeError(f'{prefix} terminó con código {process.returncode}')
            if healthy(health_url,expected):
                print(f'[{prefix}] Health OK');return process
            time.sleep(.5)
        raise RuntimeError(prefix+' no respondió al health dentro del tiempo configurado')
    except BaseException:
        stop(process);raise


def validate(expected_profile: str | None = None):
    load_env()
    profile=required('RKP_PROFILE').lower()
    if profile not in ('local','servidor'): raise RuntimeError('RKP_PROFILE debe ser local o servidor')
    if expected_profile and profile != expected_profile:
        raise RuntimeError('Este iniciador requiere RKP_PROFILE='+expected_profile+'; el .env activo es '+profile)
    for prefix in ['API','GRAFANA']:
        if prefix=='GRAFANA' and not boolean('GRAFANA_START_ENABLED',True): continue
        required(prefix+'_HOST');port(prefix+'_PORT');client_host(prefix)
    data_url=urlsplit(required('DATOS_SERVICE_URL'))
    if data_url.scheme not in ('http','https') or not data_url.hostname or data_url.username:
        raise RuntimeError('DATOS_SERVICE_URL debe ser una URL HTTP(S) sin credenciales')
    for prefix in ['MYSQL','ORACLE']:
        if not boolean(prefix+'_TUNNEL_ENABLED'): continue
        for key in ['TUNNEL_BIND_HOST','TUNNEL_REMOTE_HOST','SSH_HOST','SSH_USER']:required(prefix+'_'+key)
        for key in ['TUNNEL_LOCAL_PORT','TUNNEL_REMOTE_PORT','SSH_PORT']:port(prefix+'_'+key)
        # Avoid starting a tunnel unused by the configured DB connection.
        database_prefix='MYSQL' if prefix=='MYSQL' else 'ORACLE_HELIX'
        if env(database_prefix+'_HOST').strip()!=env(prefix+'_TUNNEL_BIND_HOST').strip() or port(database_prefix+'_PORT')!=port(prefix+'_TUNNEL_LOCAL_PORT'):
            raise RuntimeError(database_prefix+' debe apuntar al bind/puerto local de su túnel en .env')
    for name,flag in [('INFLUX_SOURCE_IP','INFLUX_SOURCE_REQUIRED'),('MYSQL_SOURCE_ADDRESS','MYSQL_SOURCE_REQUIRED')]:
        value=env(name).strip()
        if boolean(flag) and not value:raise RuntimeError('Falta '+name+' requerido por el perfil')
        if value:ipaddress.ip_address(value)
    print('Perfil:',profile,'| .env:',ROOT/'.env')
    print('MySQL:', 'túnel SSH' if boolean('MYSQL_TUNNEL_ENABLED') else 'conexión directa')
    print('Oracle:', 'túnel SSH' if boolean('ORACLE_TUNNEL_ENABLED') else 'destino configurado directamente')
    print('Origen Influx:', 'fijado por .env' if env('INFLUX_SOURCE_IP') else 'selección del sistema')
    print('Origen MySQL:', 'fijado por .env' if env('MYSQL_SOURCE_ADDRESS') else 'selección del sistema')
    return profile


def main(expected_profile: str | None = None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true',help='Valida configuración sin conectar ni iniciar servicios')
    args=parser.parse_args()
    processes=[]
    try:
        os.chdir(ROOT);profile=validate(expected_profile)
        if args.check:
            print('CHECK OK: validación de configuración; no prueba credenciales ni conectividad');return 0
        for prefix in ['ORACLE','MYSQL']:
            if boolean(prefix+'_TUNNEL_ENABLED'):processes.append((prefix,start_tunnel(prefix)))
        processes.append(('API',start_service('API','microservicios.app:app','Backend Datos API','/health')))
        if boolean('GRAFANA_START_ENABLED',True):
            processes.append(('GRAFANA',start_service('GRAFANA','microservicios.grafana_proxy.app:app','grafana-proxy','/__proxy_health')))
        print('\nServicios disponibles. Ctrl+C cierra solamente los procesos creados por este arranque.')
        print('XAMPP se administra por separado.')
        warned=set();retry_at={}
        while True:
            for index,(name,process) in enumerate(processes):
                tunnel=name in ('MYSQL','ORACLE')
                down=process is not None and process.poll() is not None
                if tunnel and process is None:
                    down=not tcp_open(required(name+'_TUNNEL_BIND_HOST'),port(name+'_TUNNEL_LOCAL_PORT'))
                if not down:continue
                if name not in warned:print('[AVISO]',name,'no está disponible');warned.add(name)
                retry=int(env(name+'_TUNNEL_RETRY_SECONDS','0')) if tunnel else 0
                if retry>0 and time.monotonic()>=retry_at.get(name,0):
                    retry_at[name]=time.monotonic()+retry
                    try:processes[index]=(name,start_tunnel(name));warned.discard(name)
                    except Exception as exc:print('[REINTENTO]',name,str(exc))
            time.sleep(2)
    except KeyboardInterrupt:print('\nCerrando procesos propios...')
    except Exception as exc:print('ERROR:',exc);return 1
    finally:
        for name,process in reversed(processes):
            if process is not None:
                try:stop(process)
                except OSError as exc:print('[AVISO]',name,str(exc))
    return 0


if __name__=='__main__':raise SystemExit(main())
