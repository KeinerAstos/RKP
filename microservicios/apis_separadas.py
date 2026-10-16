"""APIs por carpeta y gateway compatible con las rutas públicas existentes."""
from __future__ import annotations

import ast
import asyncio
import importlib
import logging
import os
import zlib
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from fastapi import Request

from microservicios.entorno import ROOT, env

BASE = ROOT / 'microservicios'
KNOWN = {
    name: 18100 + index for index, name in enumerate((
        'cmts/inits', 'cmts/intermitencias', 'cmts/puertos_docsis',
        'cmts/puertos_duplicados', 'cmts/saturacion', 'estados_helix',
        'olt/caidas', 'olt/casos_helix', 'olt/correlacion', 'olt/crc',
        'olt/perdida_latencia', 'olt/recursos_zte', 'olt/saturacion',
        'olt/temperatura', 'olt/topologias',
    ))
}
KNOWN['cmts/hfc_casos_helix'] = 31404
METHODS = {'get', 'post', 'put', 'patch', 'delete', 'head', 'options'}

@dataclass(frozen=True)
class Service:
    name: str
    module: str
    port: int
    mount: str
    routes: tuple

    @property
    def key(self):
        return 'SVC_' + self.name.replace('/', '_').upper()

    @property
    def health_name(self):
        return 'RKP API: ' + self.name


def read_routes(path, mount):
    """Descubre rutas sin importar todos los módulos en cada proceso."""
    tree = ast.parse(path.read_text(encoding='utf-8-sig'))
    prefix = ''
    found = False
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'router' for t in node.targets):
            if isinstance(node.value, ast.Call):
                found = True
                for kw in node.value.keywords:
                    if kw.arg == 'prefix':
                        prefix = ast.literal_eval(kw.value)
    if not found:
        return ()
    routes = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            if not (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute)
                    and isinstance(dec.func.value, ast.Name) and dec.func.value.id == 'router'):
                continue
            if dec.func.attr not in METHODS:
                raise RuntimeError(f'{path}: decorador {dec.func.attr} requiere configurar su publicación')
            value = dec.args[0] if dec.args else next(k.value for k in dec.keywords if k.arg == 'path')
            route = mount + prefix + ast.literal_eval(value)
            routes.append((route, dec.func.attr.upper()))
    return tuple(routes)


@lru_cache(maxsize=1)
def catalog():
    services = []
    ports, routes = {}, {}
    for path in sorted(BASE.rglob('router.py')):
        relative = path.parent.relative_to(BASE)
        if any(part.startswith('.') or part in {'__pycache__', 'venv', '.venv'} for part in relative.parts):
            continue
        name = relative.as_posix()

        if name == 'cmts/hfc_casos_helix':
            mount = ''
        else:
            mount = (
                '/api/' + relative.parts[0]
                if relative.parts[0] in {'olt', 'cmts'}
                else ''
            )
        declared = read_routes(path, mount)
        if not declared:
            continue
        slug = name.replace('/', '_').upper()
        default = KNOWN.get(name, 20000 + zlib.crc32(name.encode()) % 20000)
        number = int(env('RKP_API_' + slug + '_PORT', str(default)))
        if not 1 <= number <= 65535 or number in ports:
            raise RuntimeError(f'Puerto independiente inválido/duplicado: {name}={number}')
        for item in declared:
            if item in routes:
                raise RuntimeError(f'Ruta duplicada: {item} en {name} y {routes[item]}')
            routes[item] = name
        ports[number] = name
        services.append(Service(name, 'microservicios.' + '.'.join(relative.parts) + '.router', number, mount, declared))
    if not services:
        raise RuntimeError('No se encontraron carpetas API con router.py')
    return tuple(services)


def install_errors(app):
    from fastapi import HTTPException
    from fastapi.exceptions import RequestValidationError
    from fastapi.responses import JSONResponse

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return JSONResponse(status_code=exc.status_code, content={'ok': False, 'error': str(exc.detail)}, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        return JSONResponse(status_code=422, content={'ok': False, 'error': 'Parametros invalidos'})

    @app.exception_handler(Exception)
    async def unexpected_error(request, exc):
        logging.getLogger(__name__).error('Error en %s', request.url.path, exc_info=exc)
        return JSONResponse(status_code=500, content={'ok': False, 'error': 'Error interno del servicio'})


def create_service():
    from fastapi import FastAPI
    name = os.environ['RKP_SERVICE_ID']
    spec = next((s for s in catalog() if s.name == name), None)
    if spec is None:
        raise RuntimeError('API independiente no registrada: ' + name)
    module = importlib.import_module(spec.module)

    @asynccontextmanager
    async def lifespan(app):
        topologies_task = None
        helix = None
        scheduler_started = False
        try:
            if name == 'olt/casos_helix':
                from microservicios.config import settings
                from microservicios.olt.casos_helix import service, worker
                helix = (service, worker)
                worker.start_worker(service.consultar_olt, ttl_seconds=settings.oracle_helix_cache_seconds)
            if name == 'cmts/inits':
                await module.start_scheduler()
                scheduler_started = True
            if name == 'olt/topologias' and os.environ.get('TOPOLOGIAS_AUTO') == '1':
                from microservicios.olt.topologias import service
                async def refresh():
                    while True:
                        try:
                            await asyncio.to_thread(service.materializar_aleatoria)
                        except Exception:
                            logging.exception('Falló rutina de topologías')
                        await asyncio.sleep(120)
                topologies_task = asyncio.create_task(refresh())
            yield
        finally:
            if scheduler_started:
                await module.stop_scheduler()
            if helix:
                helix[1].stop_worker()
                helix[0].close_oracle_pool()
            if topologies_task:
                topologies_task.cancel()
                with suppress(asyncio.CancelledError):
                    await topologies_task

    app = FastAPI(title=spec.health_name, lifespan=lifespan)
    install_errors(app)

    @app.get('/health')
    async def health():
        return {'ok': True, 'service': spec.health_name, 'mode': 'independent', 'pid': os.getpid()}

    app.include_router(module.router, prefix=spec.mount)
    return app


# Encabezados de transporte no deben atravesar el proxy.
HOP_HEADERS = {'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
               'te', 'trailer', 'transfer-encoding', 'upgrade'}


def open_upstream(service, request, body):
    import requests
    session = requests.Session()
    session.trust_env = False
    forbidden = HOP_HEADERS | {v.strip().lower() for v in request.headers.get('connection', '').split(',')}
    headers = {k: v for k, v in request.headers.items() if k.lower() not in forbidden}
    timeout = float(env('RKP_GATEWAY_READ_TIMEOUT_SECONDS', '0'))
    if timeout < 0:
        raise ValueError('RKP_GATEWAY_READ_TIMEOUT_SECONDS no puede ser negativo')
    target = f'http://127.0.0.1:{service.port}' + request.scope.get('raw_path', request.url.path.encode()).decode('ascii')
    if request.url.query:
        target += '?' + request.url.query
    try:
        response = session.request(request.method, target, headers=headers, data=body,
                                   timeout=(5, timeout or None), stream=True, allow_redirects=False)
        return session, response
    except BaseException:
        session.close()
        raise


def create_gateway():
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse, StreamingResponse
    from starlette.background import BackgroundTask
    specs = catalog()
    app = FastAPI(title='Backend Datos API', version='2.0.0')
    install_errors(app)

    @app.get('/health')
    @app.get('/health/recovery')
    async def health():
        return {'ok': True, 'service': 'Backend Datos API', 'mode': 'gateway', 'pid': os.getpid()}

    @app.get('/servicios')
    async def services():
        return {'ok': True, 'services': [
            {'name': s.name, 'port': s.port, 'health': f'http://127.0.0.1:{s.port}/health',
             'routes': [p for p, _ in s.routes]} for s in specs
        ]}

    async def proxy(request: Request):
        import requests
        service = request.scope['route'].rkp_service
        body = await request.body()
        try:
            session, response = await asyncio.to_thread(open_upstream, service, request, body)
        except requests.Timeout:
            return JSONResponse(status_code=504, content={'ok': False, 'error': 'Tiempo de espera del servicio agotado', 'service': service.name})
        except requests.RequestException:
            return JSONResponse(status_code=502, content={'ok': False, 'error': 'API independiente no disponible', 'service': service.name})

        def close():
            response.close()
            session.close()

        async def chunks():
            try:
                while True:
                    block = await asyncio.to_thread(response.raw.read, 65536, decode_content=False)
                    if not block:
                        break
                    yield block
            finally:
                close()
        forbidden = HOP_HEADERS | {v.strip().lower() for v in response.headers.get('Connection', '').split(',')}
        result = StreamingResponse(chunks(), status_code=response.status_code, background=BackgroundTask(close))
        # Conserva Content-Type, descargas, compresión y encabezados repetidos.
        result.raw_headers = [
            (key.lower().encode('latin-1'), value.encode('latin-1'))
            for key in response.raw.headers.keys() if key.lower() not in forbidden
            for value in response.raw.headers.getlist(key)
        ]
        return result

    # El orden específico antes de los parámetros mantiene el enrutamiento.
    entries = sorted(((s, path, method) for s in specs for path, method in s.routes),
                     key=lambda row: (row[1].count('{'), -len(row[1]), row[1]))
    for service, path, method in entries:
        app.add_api_route(path, proxy, methods=[method], name=service.name + ':' + method + ':' + path)
        app.routes[-1].rkp_service = service
    return app
