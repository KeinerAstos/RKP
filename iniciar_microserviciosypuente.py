# PARCHE_ORACLE_DESTINO_DIRECTO_V2
from __future__ import annotations

import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent

SSH_HOST = "100.66.80.175"
SSH_USER = "AdminBOA"

MYSQL_LOCAL_HOST = "127.0.0.1"
MYSQL_LOCAL_PORT = 3307
MYSQL_REMOTO_HOST = "127.0.0.1"
MYSQL_REMOTO_PORT = 3306

# PARCHE_ORACLE_PUENTE_V1
ORACLE_SSH_HOST = "172.31.33.23"
ORACLE_SSH_USER = "noc_cable"
ORACLE_LOCAL_HOST = "127.0.0.1"
ORACLE_LOCAL_PORT = 12110
ORACLE_PUENTE_HOST = "127.0.0.1"
ORACLE_PUENTE_PORT = 12110

API_HOST = "127.0.0.1"
API_PORT = 8000

GRAFANA_HOST = "0.0.0.0"
GRAFANA_PORT = 8002


def puerto_abierto(host: str, port: int, timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def esperar_puerto(host: str, port: int, segundos: int = 30) -> bool:
    limite = time.time() + segundos
    while time.time() < limite:
        if puerto_abierto(host, port):
            return True
        time.sleep(0.5)
    return False


def matar(proceso: subprocess.Popen | None) -> None:
    if proceso is None or proceso.poll() is not None:
        return

    try:
        proceso.terminate()
        proceso.wait(timeout=5)
    except Exception:
        try:
            proceso.kill()
        except Exception:
            pass


def nueva_consola_kwargs() -> dict:
    if sys.platform == "win32":
        return {"creationflags": subprocess.CREATE_NEW_CONSOLE}
    return {}


def iniciar_tunel() -> subprocess.Popen:
    if shutil.which("ssh") is None:
        raise RuntimeError("No se encontró 'ssh' en PATH.")

    if puerto_abierto(MYSQL_LOCAL_HOST, MYSQL_LOCAL_PORT):
        print(
            f"[MYSQL] El puerto {MYSQL_LOCAL_PORT} ya está abierto. "
            "Asumo que el túnel ya está activo."
        )
        return None

    comando = [
        "ssh",
        "-N",
        "-o",
        "ExitOnForwardFailure=yes",
        "-L",
        f"{MYSQL_LOCAL_PORT}:{MYSQL_REMOTO_HOST}:{MYSQL_REMOTO_PORT}",
        f"{SSH_USER}@{SSH_HOST}",
    ]

    print("[MYSQL] Abriendo túnel SSH...")
    print(
        f"[MYSQL] {MYSQL_LOCAL_HOST}:{MYSQL_LOCAL_PORT} "
        f"-> {SSH_HOST}:{MYSQL_REMOTO_PORT}"
    )
    print("[MYSQL] Se abrirá una consola para ingresar la contraseña SSH.")

    proceso = subprocess.Popen(
        comando,
        cwd=RAIZ,
        **nueva_consola_kwargs(),
    )

    if esperar_puerto(MYSQL_LOCAL_HOST, MYSQL_LOCAL_PORT, 45):
        print("[MYSQL] Túnel listo.")
    else:
        print(
            "[MYSQL] AVISO: el puerto 3307 todavía no responde. "
            "Revisa la ventana SSH y confirma que el login haya sido exitoso."
        )

    return proceso


def iniciar_tunel_oracle() -> subprocess.Popen | None:
    if puerto_abierto(ORACLE_LOCAL_HOST, ORACLE_LOCAL_PORT):
        print(
            f"[ORACLE] Puerto {ORACLE_LOCAL_PORT} ya abierto; se reutiliza. "
            "Esto no confirma una conexión a la DB."
        )
        return None

    if shutil.which("ssh") is None:
        raise RuntimeError("No se encontró 'ssh' en PATH.")

    comando = [
        "ssh", "-N",
        "-o", "ExitOnForwardFailure=yes",
        "-o", "ServerAliveInterval=30",
        "-o", "ServerAliveCountMax=3",
        "-L",
        (
            f"{ORACLE_LOCAL_HOST}:{ORACLE_LOCAL_PORT}:"
            f"{ORACLE_PUENTE_HOST}:{ORACLE_PUENTE_PORT}"
        ),
        f"{ORACLE_SSH_USER}@{ORACLE_SSH_HOST}",
    ]

    print("[ORACLE] Abriendo túnel hacia Linux...")
    print("[ORACLE] Ingresa la contraseña de noc_cable en la consola SSH.")
    print("[ORACLE] El túnel inverso del Windows remoto debe estar activo.")
    proceso = subprocess.Popen(comando, cwd=RAIZ, **nueva_consola_kwargs())
    limite = time.monotonic() + 45

    try:
        while time.monotonic() < limite:
            if proceso.poll() is not None:
                raise RuntimeError(
                    f"El túnel Oracle terminó con código {proceso.returncode}. "
                    "Revisa la consola SSH."
                )
            if puerto_abierto(ORACLE_LOCAL_HOST, ORACLE_LOCAL_PORT):
                print(
                    f"[ORACLE] Puerto local listo: "
                    f"{ORACLE_LOCAL_HOST}:{ORACLE_LOCAL_PORT}"
                )
                print("[ORACLE] Falta validar la conexión con Oracle.")
                return proceso
            time.sleep(0.5)

        raise RuntimeError(
            "El túnel Oracle no abrió el puerto 12110 en 45 segundos. "
            "Revisa el acceso SSH."
        )
    except BaseException:
        matar(proceso)
        raise




def iniciar_uvicorn(
    modulo: str,
    nombre: str,
    host: str,
    port: int,
) -> subprocess.Popen | None:
    if puerto_abierto(host, port):
        print(
            f"[{nombre}] El puerto {port} ya está ocupado. "
            f"No inicio otra instancia."
        )
        return None

    comando = [
        sys.executable,
        "-m",
        "uvicorn",
        modulo,
        "--host",
        host,
        "--port",
        str(port),
    ]

    print(f"[{nombre}] Iniciando en http://{host}:{port}")

    return subprocess.Popen(
        comando,
        cwd=RAIZ,
        **nueva_consola_kwargs(),
    )


def main() -> int:
    print("=" * 64)
    print(" BACKEND-DATOS - INICIO DE SERVICIOS")
    print("=" * 64)
    print(f"Proyecto: {RAIZ}")
    print()

    procesos: list[tuple[str, subprocess.Popen | None]] = []

    try:
        tunel_oracle = iniciar_tunel_oracle()
        procesos.append(("Túnel Oracle", tunel_oracle))

        tunel = iniciar_tunel()
        procesos.append(("Túnel MySQL", tunel))

        api = iniciar_uvicorn(
            "microservicios.app:app",
            "API",
            API_HOST,
            API_PORT,
        )
        procesos.append(("API", api))

        grafana = iniciar_uvicorn(
            "microservicios.grafana_proxy.app:app",
            "GRAFANA",
            GRAFANA_HOST,
            GRAFANA_PORT,
        )
        procesos.append(("Grafana proxy", grafana))

        print()
        print("=" * 64)
        print(" SERVICIOS")
        print("=" * 64)
        print(f"API principal:  http://{API_HOST}:{API_PORT}")
        print(f"API health:     http://{API_HOST}:{API_PORT}/health")
        print(f"Grafana proxy:  http://{GRAFANA_HOST}:{GRAFANA_PORT}")
        print(f"Grafana health: http://{GRAFANA_HOST}:{GRAFANA_PORT}/__proxy_health")
        print(f"MySQL túnel:    {MYSQL_LOCAL_HOST}:{MYSQL_LOCAL_PORT}")
        print(f"Oracle túnel:   {ORACLE_LOCAL_HOST}:{ORACLE_LOCAL_PORT}")
        print()
        print("XAMPP/frontend NO se inicia desde este script.")
        print("Presiona Ctrl+C aquí para cerrar los procesos iniciados.")
        print("=" * 64)

        # ORACLE_REINTENTO_LOCAL_V2
        avisados = set()
        siguiente_oracle = 0.0
        while True:
            for indice, (nombre, proceso) in enumerate(procesos):
                caido = proceso is not None and proceso.poll() is not None
                if nombre == "Túnel Oracle" and proceso is None:
                    caido = not puerto_abierto(ORACLE_LOCAL_HOST, ORACLE_LOCAL_PORT)
                if caido:
                    if nombre not in avisados:
                        codigo = proceso.returncode if proceso is not None else "puerto cerrado"
                        print(f"[AVISO] {nombre} no está activo ({codigo}).")
                        avisados.add(nombre)
                    if nombre == "Túnel Oracle" and time.monotonic() >= siguiente_oracle:
                        siguiente_oracle = time.monotonic() + 10
                        try:
                            print("[ORACLE] Intentando reabrir el túnel local...")
                            nuevo_oracle = iniciar_tunel_oracle()
                            procesos[indice] = (nombre, nuevo_oracle)
                            avisados.discard(nombre)
                        except Exception as exc:
                            print(f"[ORACLE] Reintento pendiente: {exc}")
            time.sleep(2)

    except KeyboardInterrupt:
        print("\nCerrando servicios...")

    except Exception as exc:
        print(f"\nERROR: {exc}")
        return 1

    finally:
        for nombre, proceso in reversed(procesos):
            if proceso is not None and proceso.poll() is None:
                print(f"Cerrando {nombre}...")
                matar(proceso)

    print("Servicios cerrados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
