"""Configuración, MySQL (XAMPP), SSH a CMTS y SNMP v2c para el Dashboard HFC.

Todo se lee del .env raíz de RKP mediante microservicios.entorno; no depende
de microservicios/config.py ni modifica otros módulos.
"""

from __future__ import annotations

import configparser
import ipaddress
import random
import re
import socket
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from microservicios.entorno import ROOT, env

CARPETA = Path(__file__).resolve().parent
BOGOTA = timezone(timedelta(hours=-5))  # Colombia no usa horario de verano.


# ============================================================ configuración
def _texto(nombre: str, defecto: str = "") -> str:
    return env(nombre, defecto).strip()


def _entero(nombre: str, defecto: int, minimo: int = 0, maximo: int = 10**9) -> int:
    valor = _texto(nombre, str(defecto))
    try:
        numero = int(valor)
    except ValueError:
        raise RuntimeError(f"{nombre} debe ser numérico") from None
    if not minimo <= numero <= maximo:
        raise RuntimeError(f"{nombre} debe estar entre {minimo} y {maximo}")
    return numero


def _booleano(nombre: str, defecto: bool) -> bool:
    valor = _texto(nombre, "true" if defecto else "false").lower()
    if valor in ("1", "true", "yes", "on", "si", "sí"):
        return True
    if valor in ("0", "false", "no", "off", ""):
        return False
    raise RuntimeError(f"{nombre} debe ser true o false")


def _ruta(nombre: str, defecto: str) -> Path:
    p = Path(_texto(nombre, defecto) or defecto).expanduser()
    return p if p.is_absolute() else ROOT / p


class Config:
    """Variables del .env (todas opcionales salvo credenciales y BD)."""

    def __init__(self) -> None:
        # Credenciales CMTS: las mismas de HFC_AUTO (hfc.env) e INIT.
        self.cmts_user = _texto("CMTS_USER")
        self.cmts_password = env("CMTS_PASSWORD", "")
        self.arris_user = _texto("HFC_ARRIS_USER") or self.cmts_user
        self.arris_password = env("HFC_ARRIS_PASSWORD", "") or self.cmts_password
        # MySQL XAMPP local (independiente de MYSQL_*, que es la base OLT remota).
        self.db_host = _texto("HFC_DB_HOST", "127.0.0.1")
        self.db_port = _entero("HFC_DB_PORT", 3306, 1, 65535)
        self.db_user = _texto("HFC_DB_USER")
        self.db_password = env("HFC_DB_PASSWORD", "")
        self.db_database = _texto("HFC_DB_DATABASE", "rkp_hfc")
        # Recolección (valores por defecto = HFC_AUTO de noc_cable).
        self.workers = _entero("HFC_WORKERS", 10, 1, 40)
        self.connect_timeout = _entero("HFC_CONNECT_TIMEOUT", 18, 3, 120)
        self.command_timeout = _entero("HFC_COMMAND_TIMEOUT", 90, 10, 600)
        self.intervalo = _entero("HFC_INTERVALO_SEGUNDOS", 1800, 300, 86400)
        self.aceptar_hostkeys = _booleano("HFC_ACEPTAR_HOSTKEYS_NUEVAS", True)
        self.known_hosts = _ruta("HFC_KNOWN_HOSTS", "data/dashboard_hfc/known_hosts_hfc")
        self.cmts_known_hosts = _texto("CMTS_KNOWN_HOSTS")
        # Salto SSH opcional (por ejemplo vía noc_cable) si el servidor no llega directo.
        self.salto = _booleano("HFC_SALTO_HABILITADO", False)
        self.salto_host = _texto("HFC_SALTO_HOST")
        self.salto_port = _entero("HFC_SALTO_PORT", 22, 1, 65535)
        self.salto_user = _texto("HFC_SALTO_USER")
        self.salto_password = env("HFC_SALTO_PASSWORD", "")
        # ARRIS: traducción de fiber node numérico por SNMP (catálogos de noc_cable).
        self.arris_index = _ruta("HFC_ARRIS_INDEX_JSON", "data/dashboard_hfc/index_puertos_arris.json")
        self.arris_snmp = _ruta("HFC_ARRIS_SNMP_JSON", "data/dashboard_hfc/CMTS_ARRIS.json")
        self.snmp_timeout = _entero("HFC_SNMP_TIMEOUT", 3, 1, 30)
        self.alias_ttl_horas = _entero("HFC_ARRIS_ALIAS_TTL_HORAS", 24, 1, 720)
        # Histórico y retención.
        self.hist_dias = _entero("HFC_HIST_DIAS", 7, 1, 31)
        self.retencion_meses = _entero("HFC_RETENCION_MESES", 1, 0, 24)
        self.retencion_dias = _entero("HFC_RETENCION_DIAS", 1, 0, 366)
        # Salidas.
        self.publicar_json = _booleano("HFC_PUBLICAR_JSON", False)
        self.dashboard_dir = _ruta("HFC_DATA_PATH", "backend/storage/dashboard_hfc")
        self.salida_dir = _ruta("HFC_SALIDA_PATH", "data/dashboard_hfc")
        self.inventario = _ruta("HFC_INVENTARIO", str(CARPETA / "inventario.ini"))
        if not re.fullmatch(r"[A-Za-z0-9_]{1,64}", self.db_database):
            raise RuntimeError("HFC_DB_DATABASE solo admite letras, números y _")

    def secretos(self) -> list[str]:
        return [s for s in (self.cmts_password, self.arris_password, self.salto_password, self.db_password) if s]

    def ocultar(self, texto: str) -> str:
        for s in self.secretos():
            texto = texto.replace(s, "<oculto>")
        return texto


_config: Config | None = None


def config() -> Config:
    global _config
    if _config is None:
        _config = Config()
    return _config


def ahora() -> datetime:
    """Hora Colombia sin zona, como FECHA_REPORTE de HFC_AUTO."""
    return datetime.now(BOGOTA).replace(tzinfo=None, microsecond=0)


def inventario() -> list[dict[str, str]]:
    """[CASA] y [ARRIS] de inventario.ini -> lista de {fabricante, cmts, ip}."""
    cfg = configparser.ConfigParser(interpolation=None, inline_comment_prefixes=(";", "#"))
    cfg.optionxform = str
    ruta = config().inventario
    if not cfg.read(ruta, encoding="utf-8-sig"):
        raise RuntimeError(f"No se pudo leer {ruta}")
    equipos, vistos = [], set()
    for seccion in ("CASA", "ARRIS"):
        if seccion not in cfg:
            continue
        for nombre, ip in cfg[seccion].items():
            ip = str(ipaddress.ip_address(ip.strip()))
            if ip in vistos:
                raise RuntimeError(f"IP repetida en inventario.ini: {ip}")
            vistos.add(ip)
            equipos.append({"fabricante": seccion, "cmts": nombre.strip().upper(), "ip": ip})
    if not equipos:
        raise RuntimeError("inventario.ini sin equipos en [CASA] ni [ARRIS]")
    return equipos


# ==================================================================== MySQL
def conectar_bd():
    import mysql.connector

    c = config()
    if not c.db_user:
        raise RuntimeError("Configura HFC_DB_USER y HFC_DB_PASSWORD en .env")
    return mysql.connector.connect(
        host=c.db_host, port=c.db_port, user=c.db_user, password=c.db_password,
        database=c.db_database, connection_timeout=15, autocommit=False, charset="utf8mb4")


@contextmanager
def bd():
    cnx = conectar_bd()
    try:
        yield cnx
    finally:
        try:
            cnx.close()
        except Exception:
            pass


# ====================================================================== SSH
ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
PAGER_RE = re.compile(r"(?i)(--\s*more\s*--|more:|press any key|press <space>)")
PROMPT_RE = re.compile(r"^[A-Za-z0-9_.:/()@-]+[>#]\s*$")
_lock_hosts = threading.Lock()


def limpiar(texto: str) -> str:
    return ANSI_RE.sub("", texto.replace("\r", "")).replace("\x08", "")


class SesionCLI:
    """with SesionCLI(ip, "CASA") as s: salida = s.ejecutar("show ...")"""

    def __init__(self, ip: str, fabricante: str):
        self.ip, self.fabricante = ip, fabricante
        self.client = self.salto = self.tunel = self.canal = None
        self.prompt = ""
        self.etapa = "CONEXION_SSH"

    # ---- claves de host: accept-new como en noc_cable, nunca acepta una clave cambiada.
    def _preparar(self, client, paramiko) -> None:
        c = config()
        client.load_system_host_keys()
        with _lock_hosts:
            for archivo in (c.cmts_known_hosts, str(c.known_hosts)):
                if archivo and Path(archivo).is_file():
                    client.load_host_keys(archivo)
        if not c.aceptar_hostkeys:
            client.set_missing_host_key_policy(paramiko.RejectPolicy())
            return

        class AceptarNueva(paramiko.MissingHostKeyPolicy):
            def missing_host_key(self, cli, hostname, key):
                with _lock_hosts:
                    c.known_hosts.parent.mkdir(parents=True, exist_ok=True)
                    with c.known_hosts.open("a", encoding="utf-8") as f:
                        f.write(f"{hostname} {key.get_name()} {key.get_base64()}\n")
                cli.get_host_keys().add(hostname, key.get_name(), key)

        client.set_missing_host_key_policy(AceptarNueva())

    def __enter__(self) -> "SesionCLI":
        import paramiko

        c = config()
        if self.fabricante == "ARRIS" and not hasattr(paramiko, "DSSKey"):
            raise RuntimeError(
                f"[DEPENDENCIA] ARRIS E6000 solo ofrece ssh-dss y paramiko {paramiko.__version__} ya no lo "
                'soporta. Instale: pip install "paramiko>=3.4,<4"')
        usuario, clave = (c.arris_user, c.arris_password) if self.fabricante == "ARRIS" else (c.cmts_user, c.cmts_password)
        if not usuario or not clave:
            raise RuntimeError("[CONFIG] Falta CMTS_USER / CMTS_PASSWORD en .env")
        t = c.connect_timeout
        try:
            extra = {}
            if c.salto:
                self.etapa = "CONEXION_SALTO"
                self.salto = paramiko.SSHClient()
                self._preparar(self.salto, paramiko)
                self.salto.connect(c.salto_host, port=c.salto_port, username=c.salto_user,
                                   password=c.salto_password, timeout=t, banner_timeout=t, auth_timeout=t,
                                   look_for_keys=False, allow_agent=False)
                self.tunel = self.salto.get_transport().open_channel(
                    "direct-tcpip", (self.ip, 22), ("127.0.0.1", 0), timeout=t)
                extra["sock"] = self.tunel
            self.etapa = "CONEXION_CMTS"
            self.client = paramiko.SSHClient()
            self._preparar(self.client, paramiko)
            self.client.connect(self.ip, port=22, username=usuario, password=clave, timeout=t,
                                banner_timeout=t, auth_timeout=t, look_for_keys=False, allow_agent=False, **extra)
            self.etapa = "APERTURA_CLI"
            self.canal = self.client.invoke_shell(width=240, height=1000)
            self.etapa = "PROMPT_INICIAL"
            texto = self._leer(c.connect_timeout + 10)
            lineas = [l.strip() for l in texto.splitlines() if l.strip()]
            if not lineas or not PROMPT_RE.match(lineas[-1]):
                raise TimeoutError("No apareció el prompt del CMTS")
            self.prompt = lineas[-1].rstrip()
            return self
        except Exception as exc:
            self.__exit__()
            if str(exc).startswith("["):
                raise
            raise RuntimeError(f"[{self.etapa}] {type(exc).__name__}: {c.ocultar(str(exc))}"[:400]) from None

    def _leer(self, timeout: float, fin_alterno: re.Pattern | None = None) -> str:
        """Lee hasta ver el prompt; responde paginación con espacio.
        fin_alterno: si aparece y el equipo queda en silencio 2 s, también termina
        (la fila Total de ARRIS en el colector original)."""
        fin = time.monotonic() + timeout
        bruto = ""
        visto_alterno = None
        while time.monotonic() < fin:
            if self.canal.recv_ready():
                bruto += self.canal.recv(65536).decode("utf-8", errors="replace")
                if len(bruto) > 8 * 1024 * 1024:
                    raise ValueError("Salida supera 8 MiB")
                texto = limpiar(bruto)
                if PAGER_RE.search(texto[-200:]):
                    bruto = PAGER_RE.sub("", texto)
                    self.canal.send(" ")
                    continue
                if fin_alterno is not None and visto_alterno is None and fin_alterno.search(texto):
                    visto_alterno = time.monotonic()
                ultima = next((l.strip() for l in reversed(texto.splitlines()) if l.strip()), "")
                if (self.prompt and ultima == self.prompt) or (not self.prompt and PROMPT_RE.match(ultima)):
                    time.sleep(0.2)
                    if not self.canal.recv_ready():
                        return texto
                continue
            if self.canal.closed:
                raise ConnectionError("El CMTS cerró la sesión")
            if visto_alterno is not None and time.monotonic() - visto_alterno > 2:
                return limpiar(bruto)
            time.sleep(0.03)
        raise TimeoutError(f"Sin prompt en {timeout}s")

    def ejecutar(self, comando: str, timeout: int | None = None, fin_alterno: re.Pattern | None = None) -> str:
        c = config()
        self.etapa = f"COMANDO:{comando[:40]}"
        try:
            while self.canal.recv_ready():
                self.canal.recv(65536)
            self.canal.send(comando + "\n")
            texto = self._leer(timeout or c.command_timeout, fin_alterno)
        except Exception as exc:
            raise RuntimeError(f"[{self.etapa}] {type(exc).__name__}: {c.ocultar(str(exc))}"[:400]) from None
        lineas = texto.splitlines()
        # Quita el eco del comando (algunas terminales lo repiten) y el prompt final.
        while lineas and (not lineas[0].strip() or lineas[0].strip().endswith(comando.strip())):
            lineas.pop(0)
        salida = [linea.rstrip() for linea in lineas]
        while salida and (not salida[-1].strip() or salida[-1].strip() == self.prompt):
            salida.pop()
        return "\n".join(salida)

    def __exit__(self, *_):
        for recurso in (self.client, self.tunel, self.salto):
            if recurso is not None:
                try:
                    recurso.close()
                except Exception:
                    pass
        return False


# ============================================================ SNMP v2c (GET)
# Cliente mínimo con librería estándar: reemplaza easysnmp (que no existe en
# Windows) para leer ifAlias (1.3.6.1.2.1.31.1.1.1.18.<ifIndex>) de ARRIS.
def _ber_len(n: int) -> bytes:
    if n < 0x80:
        return bytes([n])
    b = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(b)]) + b


def _tlv(tag: int, valor: bytes) -> bytes:
    return bytes([tag]) + _ber_len(len(valor)) + valor


def _ber_int(v: int) -> bytes:
    return _tlv(0x02, v.to_bytes(max(1, (v.bit_length() + 8) // 8), "big", signed=True))


def _ber_oid(oid: str) -> bytes:
    partes = [int(x) for x in oid.strip(".").split(".")]
    cuerpo = bytearray([40 * partes[0] + partes[1]])
    for p in partes[2:]:
        grupo = [p & 0x7F]
        p >>= 7
        while p:
            grupo.append(0x80 | (p & 0x7F))
            p >>= 7
        cuerpo.extend(reversed(grupo))
    return _tlv(0x06, bytes(cuerpo))


def _leer_tlv(datos: bytes, i: int) -> tuple[int, bytes, int]:
    tag = datos[i]
    largo = datos[i + 1]
    i += 2
    if largo & 0x80:
        n = largo & 0x7F
        largo = int.from_bytes(datos[i:i + n], "big")
        i += n
    return tag, datos[i:i + largo], i + largo


def _hijos(datos: bytes) -> list[tuple[int, bytes]]:
    i, salida = 0, []
    while i < len(datos):
        tag, valor, i = _leer_tlv(datos, i)
        salida.append((tag, valor))
    return salida


def _oid_texto(valor: bytes) -> str:
    partes = [str(valor[0] // 40), str(valor[0] % 40)]
    n = 0
    for b in valor[1:]:
        n = (n << 7) | (b & 0x7F)
        if not b & 0x80:
            partes.append(str(n))
            n = 0
    return ".".join(partes)


def snmp_get(ip: str, comunidad: str, oids: list[str], timeout: int = 3, reintentos: int = 1) -> dict[str, str | None]:
    """GET SNMP v2c. Devuelve {oid: texto o None si noSuchObject/Instance}."""
    req_id = random.randint(1, 2**31 - 1)
    varbinds = b"".join(_tlv(0x30, _ber_oid(o) + b"\x05\x00") for o in oids)
    pdu = _tlv(0xA0, _ber_int(req_id) + _ber_int(0) + _ber_int(0) + _tlv(0x30, varbinds))
    mensaje = _tlv(0x30, _ber_int(1) + _tlv(0x04, comunidad.encode()) + pdu)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(timeout)
        for intento in range(reintentos + 1):
            try:
                s.sendto(mensaje, (ip, 161))
                while True:
                    datos, _ = s.recvfrom(65535)
                    _, cuerpo, _ = _leer_tlv(datos, 0)
                    partes = _hijos(cuerpo)
                    tag_pdu, valor_pdu = partes[2]
                    campos = _hijos(valor_pdu)
                    if int.from_bytes(campos[0][1], "big", signed=True) != req_id:
                        continue
                    error = int.from_bytes(campos[1][1], "big", signed=True)
                    if error:
                        raise RuntimeError(f"SNMP error-status {error}")
                    salida = {}
                    for _, vb in _hijos(campos[3][1]):
                        (_, oid_b), (tag_v, val) = _hijos(vb)
                        salida[_oid_texto(oid_b)] = None if tag_v in (0x80, 0x81, 0x82) else val.decode("utf-8", "replace")
                    return salida
            except socket.timeout:
                if intento == reintentos:
                    raise TimeoutError(f"SNMP sin respuesta de {ip}") from None
    return {}
