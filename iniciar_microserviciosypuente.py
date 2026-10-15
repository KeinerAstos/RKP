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
from microservicios.apis_separadas import catalog

RAIZ = ROOT
SUPERVISOR_VERSION = "RKP_APIS_INDEPENDIENTES_V3"
INDEPENDENT = {}


def service_port(name):
    return INDEPENDENT[name].port if name in INDEPENDENT else port(name + '_PORT')


def service_host(name):
    return '127.0.0.1' if name in INDEPENDENT else required(name + '_HOST')


def service_expected(name):
    if name in INDEPENDENT:
        return INDEPENDENT[name].health_name
    return 'Backend Datos API' if name == 'API' else 'grafana-proxy'


def service_module(name):
    if name in INDEPENDENT:
        return 'microservicios.apis_separadas:create_service'
    return 'microservicios.apis_separadas:create_gateway' if name == 'API' else 'microservicios.grafana_proxy.app:app'


def url(host: str, number: int, path: str) -> str:
    if ':' in host and not host.startswith('['): host = '[' + host + ']'
    return f'http://{host}:{number}{path}'


def client_host(prefix: str) -> str:
    if prefix in INDEPENDENT: return '127.0.0.1'
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


def positive_setting(name: str, default: int) -> int:
    try:
        value = int(env(name, str(default)))
    except ValueError:
        raise RuntimeError(name + ' debe ser un entero positivo') from None
    if value <= 0:
        raise RuntimeError(name + ' debe ser un entero positivo')
    return value


def health_status(target: str, expected: str) -> tuple[bool, str]:
    """Salud informativa. Un fallo HTTP no demuestra que el proceso terminó."""
    timeout = positive_setting('SERVICE_HEALTH_TIMEOUT_SECONDS', 5)
    try:
        request = Request(target, headers={'Accept': 'application/json'})
        with urlopen(request, timeout=timeout) as response:
            data = json.load(response)
        if not isinstance(data, dict):
            return False, 'JSON de salud no es un objeto'
        if data.get('ok') is not True or data.get('service') != expected:
            return False, 'respuesta de salud no coincide con el servicio esperado'
        return True, 'OK'
    except (OSError, ValueError) as exc:
        return False, f'{type(exc).__name__}: {exc}'


def healthy(target: str, expected: str) -> bool:
    return health_status(target, expected)[0]


def service_health_path(name: str) -> str:
    # /health/recovery describe al trabajador OLT. No es una condición
    # válida para matar el servidor completo y sus consultas independientes.
    return '/__proxy_health' if name == 'GRAFANA' else '/health'


class ServiceHealthMonitor:
    """Observa HTTP y avisa; nunca autoriza reiniciar un proceso vivo."""
    def __init__(self, interval=30, warning_interval=60, clock=time.monotonic,
                 probe=health_status, emit=print):
        self.interval = interval
        self.warning_interval = warning_interval
        self.clock = clock
        self.probe = probe
        self.emit = emit
        self.next_check = {}
        self.failures = {}
        self.next_warning = {}

    def observe(self, name, process, target, expected):
        if process is None:
            return None
        exit_code = process.poll()
        if exit_code is not None:
            return exit_code
        now = self.clock()
        if now < self.next_check.get(name, 0):
            return None
        good, detail = self.probe(target, expected)
        now = self.clock()
        self.next_check[name] = now + self.interval
        previous = self.failures.get(name, 0)
        self.failures[name] = 0 if good else previous + 1
        if good:
            if previous:
                self.emit(f'[SALUD] {name} PID={process.pid} vuelve a responder')
            self.next_warning.pop(name, None)
        elif now >= self.next_warning.get(name, 0):
            self.next_warning[name] = now + self.warning_interval
            self.emit(
                f'[AVISO SALUD] {name} PID={process.pid} '
                f'fallos={self.failures[name]}: {detail}. '
                'El proceso sigue activo; se conserva sin interrumpir consultas.'
            )
        # Puede haber terminado mientras se comprobaba HTTP.
        return process.poll()

    def reset(self, name):
        self.next_check.pop(name, None)
        self.failures.pop(name, None)
        self.next_warning.pop(name, None)


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
    bind=service_host(prefix);number=service_port(prefix);check_host=client_host(prefix)
    health_url=url(check_host,number,health_path)
    if tcp_open(check_host,number):
        if not healthy(health_url,expected):
            raise RuntimeError(f'{prefix}: puerto {number} ocupado por un servicio que no responde con el health esperado')
        if prefix == 'API' and module.endswith(':create_gateway'):
            with urlopen(health_url, timeout=5) as response:
                mode = json.load(response).get('mode')
            if mode != 'gateway':
                raise RuntimeError('El puerto API aún pertenece al backend anterior. Detén su iniciador antes de arrancar el modo separado.')
        print(f'[{prefix}] Servicio existente validado; no se reinicia');return None
    command=[sys.executable,'-m','uvicorn',module,'--host',bind,'--port',str(number)]
    if module.endswith((':create_service', ':create_gateway')):
        command.append('--factory')
    print(f'[{prefix}] Iniciando listener {bind}:{number}')
    show = boolean('UVICORN_SHOW_CONSOLE')
    child_env = os.environ.copy()
    child_env['PYTHONUNBUFFERED'] = '1'
    if prefix in INDEPENDENT:
        child_env['RKP_SERVICE_ID'] = INDEPENDENT[prefix].name
    options = process_options(show)
    if show:
        process = subprocess.Popen(command, cwd=ROOT, env=child_env, **options)
    else:
        log_dir = Path(env('SERVICE_LOG_DIR', 'backend/storage/logs')).expanduser()
        if not log_dir.is_absolute():
            log_dir = ROOT / log_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / (prefix.lower() + '.log')
        with log_path.open('ab', buffering=0) as output:
            marker = f"\n--- {time.strftime('%Y-%m-%d %H:%M:%S')} inicio {prefix} ---\n"
            output.write(marker.encode('utf-8'))
            process = subprocess.Popen(
                command, cwd=ROOT, env=child_env, stdout=output,
                stderr=subprocess.STDOUT, **options,
            )
        print(f'[{prefix}] Log: {log_path}')

    try:
        deadline=time.monotonic()+positive_setting('SERVICE_READY_TIMEOUT_SECONDS',120)
        while time.monotonic()<deadline:
            if process.poll() is not None: raise RuntimeError(f'{prefix} terminó con código {process.returncode}')
            if healthy(health_url,expected):
                print(f'[{prefix}] Health OK');return process
            time.sleep(.5)
        raise RuntimeError(prefix+' no respondió al health dentro del tiempo configurado')
    except BaseException:
        stop(process);raise


def validate():
    load_env()
    for key, default in (
        ('SERVICE_HEALTH_TIMEOUT_SECONDS', 5),
        ('SERVICE_HEALTH_INTERVAL_SECONDS', 30),
        ('SERVICE_HEALTH_WARNING_SECONDS', 60),
        ('SERVICE_READY_TIMEOUT_SECONDS', 120),
    ):
        positive_setting(key, default)
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
    print('Configuración:', ROOT/'.env')
    print('MySQL:', 'túnel SSH' if boolean('MYSQL_TUNNEL_ENABLED') else 'conexión directa')
    print('Oracle:', 'túnel SSH' if boolean('ORACLE_TUNNEL_ENABLED') else 'destino configurado directamente')
    print('Origen Influx:', 'fijado por .env' if env('INFLUX_SOURCE_IP') else 'selección del sistema')
    print('Origen MySQL:', 'fijado por .env' if env('MYSQL_SOURCE_ADDRESS') else 'selección del sistema')
    return None


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true',help='Valida configuración sin conectar ni iniciar servicios')
    args=parser.parse_args()
    processes=[]
    try:
        os.chdir(ROOT);validate()
        INDEPENDENT.clear()
        for spec in catalog():
            INDEPENDENT[spec.key] = spec
        reserved = {port('API_PORT')}
        if boolean('GRAFANA_START_ENABLED', True):
            reserved.add(port('GRAFANA_PORT'))
        for spec in INDEPENDENT.values():
            if spec.port in reserved:
                raise RuntimeError(f'{spec.name}: puerto {spec.port} coincide con API/Grafana')
            print(f'[API INDEPENDIENTE] {spec.name}: 127.0.0.1:{spec.port}')
        if args.check:
            print('CHECK OK: validación de configuración; no prueba credenciales ni conectividad');return 0
        # Rechazar el monolito antes de iniciar rutinas en otros procesos.
        if tcp_open(client_host('API'), port('API_PORT')):
            target = url(client_host('API'), port('API_PORT'), '/health')
            with urlopen(target, timeout=5) as response:
                existing = json.load(response)
            if not isinstance(existing, dict) or existing.get('mode') != 'gateway' or existing.get('service') != 'Backend Datos API':
                raise RuntimeError('Detén el iniciador anterior: el puerto principal todavía no pertenece al gateway.')
        for prefix in ['ORACLE','MYSQL']:
            if boolean(prefix+'_TUNNEL_ENABLED'):processes.append((prefix,start_tunnel(prefix)))
        for name in INDEPENDENT:
            processes.append((name, start_service(name, service_module(name), service_expected(name), '/health')))
        processes.append(('API', start_service('API', service_module('API'), service_expected('API'), '/health')))
        if boolean('GRAFANA_START_ENABLED',True):
            processes.append(('GRAFANA',start_service('GRAFANA','microservicios.grafana_proxy.app:app','grafana-proxy','/__proxy_health')))
        print('\nServicios disponibles. Ctrl+C cierra solamente los procesos creados por este arranque.')
        print('XAMPP se administra por separado.')
        print(SUPERVISOR_VERSION)
        print('HTTP lento o trabajador Helix degradado: aviso. Reinicio automático: solo si el proceso termina.')
        monitor = ServiceHealthMonitor(
            interval=positive_setting('SERVICE_HEALTH_INTERVAL_SECONDS', 30),
            warning_interval=positive_setting('SERVICE_HEALTH_WARNING_SECONDS', 60),
        )
        warned = set()
        retry_at, restart_count, stable_since = {}, {}, {}

        while True:
            for index,(name,process) in enumerate(processes):
                tunnel=name in ('MYSQL','ORACLE')
                down=process is not None and process.poll() is not None
                if tunnel and process is None:
                    down=not tcp_open(required(name+'_TUNNEL_BIND_HOST'),port(name+'_TUNNEL_LOCAL_PORT'))
                now=time.monotonic()
                if not tunnel:
                    # Solo supervisar/reiniciar procesos propios. None es un servicio externo.
                    if process is None:continue
                    expected = service_expected(name)
                    exit_code = monitor.observe(
                        name, process,
                        url(client_host(name), service_port(name), service_health_path(name)),
                        expected,
                    )
                    now = time.monotonic()
                    if exit_code is None:
                        stable_since.setdefault(name, now)
                        if now - stable_since[name] >= 300:
                            restart_count[name] = 0
                        continue
                    stable_since.pop(name, None)
                    if now<retry_at.get(name,0):continue
                    if restart_count.get(name,0)>=5:
                        if name not in warned:
                            print('[AVISO]',name,'agotó 5 reinicios; revisar y reiniciar el iniciador')
                            warned.add(name)
                        continue
                    restart_count[name]=restart_count.get(name,0)+1
                    retry_at[name]=now+min(120,10*restart_count[name])
                    print('[RECUPERACION]',name,'PID='+str(process.pid),'terminó con código',exit_code,'; reinicio',restart_count[name])
                    # No se inicia un reemplazo hasta confirmar que terminó el anterior.
                    stop(process)
                    monitor.reset(name)
                    try:
                        module=service_module(name)
                        replacement=start_service(name,module,expected,service_health_path(name))
                        processes[index]=(name,replacement)
                        monitor.reset(name)
                        warned.discard(name)
                    except Exception as exc:print('[REINTENTO]',name,str(exc))
                    continue
                if not down:continue
                if name not in warned:print('[AVISO]',name,'no está disponible');warned.add(name)
                retry=int(env(name+'_TUNNEL_RETRY_SECONDS','0'))
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
