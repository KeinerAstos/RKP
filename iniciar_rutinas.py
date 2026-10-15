#!/usr/bin/env python3
"""Lanzador de rutinas de RKP: ejecuta periódicamente todas las rutinas registradas.

Cada rutina corre como un proceso aparte (python -m <modulo> <args>), con:
  - intervalo alineado al reloj, como cron (cada 30 min -> :00 y :30),
  - un solo proceso a la vez por rutina (si sigue corriendo, se salta el turno),
  - tiempo máximo (si lo supera, se detiene),
  - log propio en data/rutinas/<nombre>.log (rotado al pasar de 10 MB).

Agregar una rutina: añadir una entrada a RUTINAS (abajo).
Ajustar sin tocar código, en el .env de RKP:
  RUTINA_<NOMBRE>_HABILITADA=true|false
  RUTINA_<NOMBRE>_CADA_MINUTOS=30
  RUTINA_<NOMBRE>_TIMEOUT_MINUTOS=25
  RUTINAS_PYTHON=C:\\ruta\\python.exe   (opcional; por defecto el Python que ejecuta este archivo)

Uso (desde la raíz de RKP):
  python iniciar_rutinas.py                 inicia el lanzador (queda corriendo)
  python iniciar_rutinas.py --listar        muestra rutinas, intervalos y próxima ejecución
  python iniciar_rutinas.py --ahora NOMBRE  ejecuta una rutina una vez y muestra su salida
"""
from __future__ import annotations

import argparse
import os
import re
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent

# =====================================================================
# RUTINAS REGISTRADAS
#   nombre           identificador corto (letras, números y _); se usa en el .env y en el log
#   modulo           módulo Python que se ejecuta con "python -m"
#   argumentos       argumentos del módulo
#   cada_minutos     intervalo; alineado al reloj (30 -> :00 y :30, 15 -> :00 :15 :30 :45)
#   desfase_minutos  corre N minutos después de cada marca (para no arrancar todas juntas)
#   timeout_minutos  si la ejecución supera este tiempo, se detiene
#   habilitada       valor por defecto (el .env lo puede cambiar)
# =====================================================================
RUTINAS = [
    {
        "nombre": "influx",
        "descripcion": "Consultas Influx centralizadas -> resultados compartidos",
        "modulo": "microservicios.rutina_influx",
        "argumentos": ["--ciclo"],
        "cada_minutos": 1,
        "cada_segundos": 30,
        "desfase_minutos": 0,
        "timeout_minutos": 120,
        "habilitada": True,
    },
    {
        "nombre": "dashboard_hfc",
        "descripcion": "Dashboard HFC: CASA + ARRIS por SSH -> MySQL rkp_hfc",
        "modulo": "microservicios.cmts.dashboard_hfc.rutina",
        "argumentos": ["--ciclo"],
        "cada_minutos": 10,
        "desfase_minutos": 0,
        "timeout_minutos": 25,
        "habilitada": True,
    },
    {
        "nombre": "estados_helix",
        "descripcion": "Estados Helix: API existente -> ultima lectura compartida",
        "modulo": "iniciar_rutinas",
        "argumentos": ["--ciclo-estados-helix"],
        "cada_minutos": 5,
        "desfase_minutos": 1,
        "timeout_minutos": 25,
        "habilitada": True,
    },
    # Ejemplo de la próxima rutina:
    # {
    #     "nombre": "otra_rutina",
    #     "descripcion": "Qué hace",
    #     "modulo": "microservicios.carpeta.rutina",
    #     "argumentos": ["--ciclo"],
    #     "cada_minutos": 15,
    #     "desfase_minutos": 5,
    #     "timeout_minutos": 12,
    #     "habilitada": True,
    # },
]

CARPETA_LOGS = RAIZ / "data" / "rutinas"
LOG_MAX_BYTES = 10 * 1024 * 1024
CANDADO = CARPETA_LOGS / "iniciar_rutinas.lock"


# ============================================================== utilidades
def _leer_env() -> dict[str, str]:
    """Lee el .env raíz con el mismo formato que microservicios/entorno.py."""
    ruta = RAIZ / ".env"
    valores: dict[str, str] = {}
    if not ruta.is_file():
        return valores
    for linea in ruta.read_text(encoding="utf-8-sig").splitlines():
        m = re.match(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$", linea)
        if not m:
            continue
        clave, valor = m.groups()
        if valor[:1] in ('"', "'") and len(valor) > 1 and valor.rfind(valor[0]) > 0:
            valor = valor[1:valor.rfind(valor[0])]
        else:
            valor = re.split(r"\s+#", valor, maxsplit=1)[0].rstrip()
        valores[clave] = valor
    return valores


def _ahora() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _msg(texto: str) -> None:
    print(f"{_ahora()} [RUTINAS] {texto}", flush=True)


@dataclass
class Rutina:
    nombre: str
    descripcion: str
    modulo: str
    argumentos: list[str]
    cada_minutos: int
    desfase_minutos: int
    timeout_minutos: int
    habilitada: bool
    cada_segundos: int = 0
    proceso: subprocess.Popen | None = None
    inicio: float = 0.0
    proxima: datetime | None = None
    ultima: str = "nunca"
    log: object = field(default=None, repr=False)

    @property
    def ruta_log(self) -> Path:
        return CARPETA_LOGS / f"{self.nombre}.log"

    def calcular_proxima(self, desde: datetime) -> datetime:
        """Siguiente marca alineada al reloj, estrictamente posterior a 'desde'."""
        if self.cada_segundos:
            siguiente = (int(desde.timestamp()) // self.cada_segundos + 1) * self.cada_segundos
            return datetime.fromtimestamp(siguiente)
        base = desde.replace(second=0, microsecond=0)
        minutos_dia = base.hour * 60 + base.minute
        paso = self.cada_minutos
        siguiente = ((minutos_dia - self.desfase_minutos) // paso + 1) * paso + self.desfase_minutos
        return base.replace(hour=0, minute=0) + timedelta(minutes=siguiente)

    def comando(self, python: str) -> list[str]:
        return [python, "-m", self.modulo, *self.argumentos]


def cargar_rutinas(env: dict[str, str]) -> list[Rutina]:
    rutinas, vistos = [], set()
    for d in RUTINAS:
        nombre = d["nombre"]
        if not re.fullmatch(r"[A-Za-z0-9_]+", nombre) or nombre.upper() in vistos:
            raise SystemExit(f"Nombre de rutina inválido o repetido: {nombre!r}")
        vistos.add(nombre.upper())
        prefijo = f"RUTINA_{nombre.upper()}_"

        def entero(clave: str, defecto: int, minimo: int) -> int:
            valor = env.get(prefijo + clave, str(defecto)).strip()
            try:
                numero = int(valor)
            except ValueError:
                raise SystemExit(f"{prefijo}{clave} debe ser numérico") from None
            if numero < minimo:
                raise SystemExit(f"{prefijo}{clave} debe ser >= {minimo}")
            return numero

        habilitada = env.get(prefijo + "HABILITADA", "true" if d.get("habilitada", True) else "false")
        r = Rutina(
            nombre=nombre,
            descripcion=d.get("descripcion", ""),
            modulo=d["modulo"],
            argumentos=list(d.get("argumentos", [])),
            cada_minutos=entero("CADA_MINUTOS", int(d["cada_minutos"]), 1),
            desfase_minutos=entero("DESFASE_MINUTOS", int(d.get("desfase_minutos", 0)), 0),
            timeout_minutos=entero("TIMEOUT_MINUTOS", int(d.get("timeout_minutos", d["cada_minutos"])), 1),
            cada_segundos=entero("CADA_SEGUNDOS", int(d.get("cada_segundos", 0)), 0),
            habilitada=habilitada.strip().lower() in ("1", "true", "yes", "on", "si", "sí"),
        )
        if r.desfase_minutos >= r.cada_minutos:
            raise SystemExit(f"{nombre}: el desfase debe ser menor que el intervalo")
        rutinas.append(r)
    return rutinas


def _abrir_log(r: Rutina):
    CARPETA_LOGS.mkdir(parents=True, exist_ok=True)
    if r.ruta_log.is_file() and r.ruta_log.stat().st_size > LOG_MAX_BYTES:
        anterior = r.ruta_log.with_suffix(".log.1")
        anterior.unlink(missing_ok=True)
        r.ruta_log.rename(anterior)
    return r.ruta_log.open("a", encoding="utf-8", errors="replace")


# =========================================================== una instancia
class Candado:
    """Impide dos lanzadores a la vez; el sistema lo libera aunque el proceso muera."""

    def __init__(self, ruta: Path):
        ruta.parent.mkdir(parents=True, exist_ok=True)
        self.archivo = ruta.open("a+b")
        try:
            if os.name == "nt":
                import msvcrt

                self.archivo.seek(0)
                msvcrt.locking(self.archivo.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.archivo, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.archivo.close()
            raise SystemExit("Ya hay un iniciar_rutinas.py corriendo en este equipo.") from None
        self.archivo.seek(0)
        self.archivo.truncate()
        self.archivo.write(f"pid={os.getpid()} inicio={_ahora()}\n".encode())
        self.archivo.flush()


# ================================================================ ejecución
def lanzar(r: Rutina, python: str) -> None:
    r.log = _abrir_log(r)
    r.log.write(f"\n===== {_ahora()} INICIO {r.nombre} ({' '.join(r.comando('python')[1:])}) =====\n")
    r.log.flush()
    opciones = {}
    if os.name == "nt":
        opciones["creationflags"] = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        opciones["start_new_session"] = True
    entorno = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")
    r.proceso = subprocess.Popen(r.comando(python), cwd=RAIZ, stdout=r.log, stderr=subprocess.STDOUT,
                                 stdin=subprocess.DEVNULL, env=entorno, **opciones)
    r.inicio = time.monotonic()
    _msg(f"{r.nombre}: iniciada (pid {r.proceso.pid})")


def _terminar(r: Rutina, motivo: str) -> None:
    p = r.proceso
    if p is None or p.poll() is not None:
        return
    _msg(f"{r.nombre}: deteniendo ({motivo})")
    try:
        if os.name == "nt":
            p.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            os.killpg(p.pid, signal.SIGTERM)
        p.wait(timeout=15)
    except Exception:
        pass
    if p.poll() is None:
        p.kill()
        try:
            p.wait(timeout=10)
        except Exception:
            pass


def revisar(r: Rutina) -> None:
    """Cierra la ejecución terminada o la detiene si superó su tiempo máximo."""
    if r.proceso is None:
        return
    if r.proceso.poll() is None:
        if time.monotonic() - r.inicio > r.timeout_minutos * 60:
            _terminar(r, f"superó {r.timeout_minutos} min")
        else:
            return
    codigo = r.proceso.returncode
    duracion = time.monotonic() - r.inicio
    estado = {0: "OK", 2: "PARCIAL"}.get(codigo, f"ERROR código {codigo}")
    r.ultima = f"{_ahora()} {estado} ({duracion / 60:.1f} min)"
    r.log.write(f"===== {_ahora()} FIN {r.nombre}: {estado} en {duracion:.0f}s =====\n")
    r.log.close()
    r.proceso, r.log = None, None
    _msg(f"{r.nombre}: terminó {estado} en {duracion / 60:.1f} min")


def bucle(rutinas: list[Rutina], python: str) -> int:
    candado = Candado(CANDADO)  # se mantiene tomado mientras viva esta variable
    activas = [r for r in rutinas if r.habilitada]
    if not activas:
        _msg("No hay rutinas habilitadas. Nada que hacer.")
        return 0
    detener = threading.Event()

    def senal(*_):
        detener.set()

    signal.signal(signal.SIGINT, senal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, senal)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, senal)

    _msg(f"Lanzador iniciado en {RAIZ} con {python}")
    for r in activas:
        r.proxima = r.calcular_proxima(datetime.now())
        _msg(f"{r.nombre}: cada {r.cada_minutos} min (desfase {r.desfase_minutos}) · próxima {r.proxima:%H:%M}")
    for r in rutinas:
        if not r.habilitada:
            _msg(f"{r.nombre}: deshabilitada (RUTINA_{r.nombre.upper()}_HABILITADA)")

    while not detener.is_set():
        ahora = datetime.now()
        for r in activas:
            revisar(r)
            if ahora >= r.proxima:
                if r.proceso is not None:
                    _msg(f"{r.nombre}: sigue corriendo; se salta el turno de las {r.proxima:%H:%M}")
                else:
                    try:
                        lanzar(r, python)
                    except Exception as exc:
                        _msg(f"{r.nombre}: no se pudo iniciar: {exc}")
                r.proxima = r.calcular_proxima(ahora)
        detener.wait(5)

    _msg("Deteniendo lanzador...")
    for r in activas:
        _terminar(r, "lanzador detenido")
        revisar(r)
    _msg("Lanzador detenido.")
    candado.archivo.close()
    return 0


def listar(rutinas: list[Rutina], python: str) -> int:
    print(f"Raíz: {RAIZ}\nPython: {python}\nLogs: {CARPETA_LOGS}\n")
    for r in rutinas:
        estado = "HABILITADA" if r.habilitada else "deshabilitada"
        print(f"- {r.nombre} [{estado}] {r.descripcion}")
        print(f"    python -m {r.modulo} {' '.join(r.argumentos)}")
        print(f"    cada {r.cada_minutos} min, desfase {r.desfase_minutos}, máximo {r.timeout_minutos} min, "
              f"próxima {r.calcular_proxima(datetime.now()):%Y-%m-%d %H:%M}")
        print(f"    log: {r.ruta_log}")
    return 0


def ahora_una(rutinas: list[Rutina], nombre: str, python: str) -> int:
    r = next((x for x in rutinas if x.nombre.lower() == nombre.lower()), None)
    if r is None:
        print(f"No existe la rutina {nombre!r}. Use --listar.")
        return 1
    print(f"Ejecutando {r.nombre}: python -m {r.modulo} {' '.join(r.argumentos)}\n", flush=True)
    try:
        return subprocess.run(r.comando(python), cwd=RAIZ, timeout=r.timeout_minutos * 60).returncode
    except subprocess.TimeoutExpired:
        print(f"\nSuperó {r.timeout_minutos} min; detenida.")
        return 1


def ciclo_estados_helix() -> int:
    """Publica una única lectura completa; nunca levanta otra API."""
    import json
    import tempfile
    from urllib.parse import urlsplit
    from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler
    from urllib.error import HTTPError, URLError

    class SinRedireccion(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    configuracion = _leer_env()
    def valor(nombre, defecto=""):
        return os.environ.get(nombre, configuracion.get(nombre, defecto)).strip()

    carpeta = RAIZ / "backend" / "storage" / "estados_helix"
    carpeta.mkdir(parents=True, exist_ok=True)
    # Lock del SO compartido por --ahora y el scheduler; queda libre al morir.
    try:
        candado = Candado(carpeta / "consulta.lock")
    except SystemExit:
        _msg("estados_helix: otra ejecución sigue activa; turno omitido")
        return 0
    temporal = None
    try:
        base = valor("DATOS_SERVICE_URL")
        partes = urlsplit(base)
        if (partes.scheme not in ("http", "https") or not partes.hostname
                or partes.username is not None or partes.password is not None
                or partes.query or partes.fragment):
            raise ValueError("DATOS_SERVICE_URL debe ser HTTP(S) sin credenciales, query ni fragmento")
        timeout = int(valor("DATOS_SERVICE_TIMEOUT_SECONDS", "180"))
        if timeout < 0:
            raise ValueError("DATOS_SERVICE_TIMEOUT_SECONDS debe ser >= 0")
        opener = build_opener(ProxyHandler({}), SinRedireccion())
        peticion = Request(base.rstrip("/") + "/api/estados_helix/relaciones",
                           headers={"Accept": "application/json"})
        with opener.open(peticion, timeout=timeout or None) as respuesta:
            datos = json.load(respuesta)
        if (not isinstance(datos, dict) or datos.get("ok") is not True
                or not isinstance(datos.get("incidentes"), list)
                or not isinstance(datos.get("resumen_relaciones"), dict)
                or not isinstance(datos.get("fecha_corte"), str)):
            raise ValueError("La API devolvió un contrato inesperado")
        datos.pop("no_verificables", None)
        # Un único archivo vigente. Nunca borrar el anterior si falla Oracle/HTTP.
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=carpeta,
                                         prefix="actual-", suffix=".tmp", delete=False) as salida:
            temporal = Path(salida.name)
            json.dump(datos, salida, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
            salida.flush()
            os.fsync(salida.fileno())
        os.replace(temporal, carpeta / "actual.json")
        temporal = None
        _msg("estados_helix: lectura publicada; INC=" + str(datos.get("total", "?"))
             + "; TAS=" + str(datos["resumen_relaciones"].get("total_tareas", "?"))
             + "; corte=" + datos["fecha_corte"])
        return 0
    except HTTPError as exc:
        _msg("estados_helix: HTTP " + str(exc.code) + "; se conserva la lectura anterior")
        return 1
    except (URLError, TimeoutError, OSError):
        _msg("estados_helix: fallo de conexión/escritura; se conserva la lectura anterior")
        return 1
    except (ValueError, TypeError):
        _msg("estados_helix: configuración o respuesta inválida; se conserva la lectura anterior")
        return 1
    finally:
        if temporal is not None:
            temporal.unlink(missing_ok=True)
        candado.archivo.close()


def main() -> int:
    p = argparse.ArgumentParser(description="Lanzador de rutinas de RKP")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--listar", action="store_true", help="Muestra las rutinas registradas")
    g.add_argument("--ahora", metavar="NOMBRE", help="Ejecuta una rutina una vez, en primer plano")
    g.add_argument("--ciclo-estados-helix", action="store_true", help=argparse.SUPPRESS)
    a = p.parse_args()
    if a.ciclo_estados_helix:
        return ciclo_estados_helix()
    env = _leer_env()
    python = env.get("RUTINAS_PYTHON", "").strip() or sys.executable
    rutinas = cargar_rutinas(env)
    if a.listar:
        return listar(rutinas, python)
    if a.ahora:
        return ahora_una(rutinas, a.ahora, python)
    return bucle(rutinas, python)


if __name__ == "__main__":
    sys.exit(main())

