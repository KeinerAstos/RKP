"""Colectores CASA / ARRIS y unificación, portados de HFC_AUTO (noc_cable).

Origen de cada parte:
  CASA     app/collectors/casa/reporte_nodos_casa_masivo_v3_hilos.py
  ARRIS    app/collectors/arris/reporte_arris_38_cmts_v5_auto.py
  Unificar app/processors/unificar_hfc_actual.py  (incluye traducción ARRIS por SNMP)
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import timedelta

from microservicios.cmts.dashboard_hfc.conexion import SesionCLI, ahora, config, snmp_get

# ===================================================================== CASA
CASA_PAGINACION = "page off"  # como HFC_ANALYTICS/collect_cmts_fast.py
CASA_CMD_SG = "show service group | exclude qam | exclude downstream"
CASA_CMD_SUMMARY = "show cable modem summary"

SG_LINE_RE = re.compile(r"(?i)^\s*service\s+group\s+(\S+)\s*$")
UP_LINE_RE = re.compile(r"(?i)^\s*upstream\s+((?:\d+:)?\d+/\d+\.\d+)\s*$")  # VCCAP conserva "N:"
SUMMARY_ROW_RE = re.compile(
    r"^\s*(?P<iface>(?:\d+:)?\d+/\d+\.\d+/\d+)\s+(?P<total>\d+)\s+(?P<active>\d+)\s+"
    r"(?P<registered>\d+)\s+(?P<secondary>\d+)\s+(?P<offline>\d+)\s+(?P<bonding>\d+)\s+"
    r"(?P<nonbonding>\d+)(?:\s+(?P<description>.*))?$")


def casa_parse_service_groups(texto: str) -> dict[str, list[str]]:
    grupos: dict[str, list[str]] = {}
    actual = None
    for raw in texto.splitlines():
        linea = raw.strip()
        m = SG_LINE_RE.match(linea)
        if m:
            actual = m.group(1)
            grupos.setdefault(actual, [])
            continue
        if actual:
            m = UP_LINE_RE.match(linea)
            if m and m.group(1) not in grupos[actual]:
                grupos[actual].append(m.group(1))
    return grupos


def casa_parse_summary(texto: str) -> dict[str, dict]:
    filas = {}
    for raw in texto.splitlines():
        m = SUMMARY_ROW_RE.match(raw.rstrip())
        if not m:
            continue
        iface = re.sub(r"/\d+$", "", m.group("iface").strip())  # 0/0.0/0 -> 0/0.0
        filas[iface] = {k: int(m.group(k)) for k in ("total", "active", "registered", "secondary", "offline")}
        filas[iface]["description"] = (m.group("description") or "").strip()
    return filas


def casa_filas(nombre: str, ip: str, grupos: dict, resumen: dict) -> list[dict]:
    filas = []
    for sg, upstreams in grupos.items():
        total = active = registered = offline = 0
        descripciones: list[str] = []
        for us in upstreams:
            item = resumen.get(us)
            if not item:
                continue
            total += item["total"]
            active += item["active"]
            registered += item["registered"]
            offline += item["offline"]
            if item["description"] and item["description"] not in descripciones:
                descripciones.append(item["description"])
        fuente = "SIN_UPSTREAM" if not upstreams else ("SIN_MODEMS" if total <= 0 else "")
        filas.append({"FABRICANTE": "CASA", "CMTS": nombre, "IP": ip, "ELEMENTO": sg, "ID_FABRICANTE": sg,
                      "TOTAL": total, "ACTIVE": active, "REGISTERED": registered, "OFFLINE": offline,
                      "INIT": 0, "DISABLE": None, "PORC_OPER_ARRIS": "", "PRIORIDAD": "",
                      "DESCRIPCION": " | ".join(descripciones), "FUENTE": fuente})
    return filas


def consultar_casa(nombre: str, ip: str) -> tuple[list[dict], str]:
    with SesionCLI(ip, "CASA") as s:
        try:
            s.ejecutar(CASA_PAGINACION, timeout=15)
        except RuntimeError:
            pass  # sin "page off" se sigue respondiendo --More-- con espacio
        sg_raw = s.ejecutar(CASA_CMD_SG)
        grupos = casa_parse_service_groups(sg_raw)
        if not grupos:
            raise RuntimeError("[PARSER] No se pudieron extraer service groups.")
        summary_raw = s.ejecutar(CASA_CMD_SUMMARY)
        resumen = casa_parse_summary(summary_raw)
        if not resumen:
            raise RuntimeError("[PARSER] No se pudieron extraer filas de cable modem summary.")
    crudo = f"### {CASA_CMD_SG}\n{sg_raw}\n\n### {CASA_CMD_SUMMARY}\n{summary_raw}\n"
    return casa_filas(nombre, ip, grupos, resumen), crudo


# ==================================================================== ARRIS
ARRIS_CMD = "show cable modem summary fiber-node"
ARRIS_ROW_RE = re.compile(
    r"^\s*(?P<node>\S+)\s+(?P<total>\d+)\s+(?P<oper>\d+)\s+(?P<disable>\d+)\s+"
    r"(?P<init>\d+)\s+(?P<offline>\d+)\s+(?P<poper>\d+)%\s*$")
ARRIS_TOTAL_RE = re.compile(r"(?m)^\s*Total\s+\d+\s+\d+\s+\d+\s+\d+\s+\d+\s+\d+%\s*$")


def arris_clasificar(total: int, offline: int) -> tuple[str, str]:
    """(detalle, prioridad) como classify() del colector ARRIS."""
    if total <= 0:
        return "SIN MODEMS - TOTAL_MODEMS = 0; validar si el Fiber Node esta en servicio", "VALIDAR"
    if offline <= 0:
        obs, pri = "ENGANCHADO", "NORMAL"
    elif offline >= total:
        obs, pri = "DESENGANCHE TOTAL", "ALTA"
    else:
        obs, pri = "DESENGANCHE PARCIAL", "MEDIA"
    return f"{obs} - {offline} de {total} modems offline ({offline / total * 100:.1f}%)", pri


def arris_parse(nombre: str, ip: str, texto: str) -> list[dict]:
    filas = []
    for linea in texto.splitlines():
        m = ARRIS_ROW_RE.match(linea)
        if not m or m.group("node").lower() == "total":
            continue
        total, offline = int(m.group("total")), int(m.group("offline"))
        detalle, prioridad = arris_clasificar(total, offline)
        filas.append({"FABRICANTE": "ARRIS", "CMTS": nombre, "IP": ip, "ELEMENTO": m.group("node"),
                      "ID_FABRICANTE": m.group("node"), "TOTAL": total, "ACTIVE": int(m.group("oper")),
                      "REGISTERED": total,  # el unificador original publica REGISTERED = TOTAL
                      "OFFLINE": offline, "INIT": int(m.group("init")), "DISABLE": int(m.group("disable")),
                      "PORC_OPER_ARRIS": f"{int(m.group('poper'))}%", "PRIORIDAD": prioridad,
                      "DESCRIPCION": detalle, "FUENTE": ""})
    return filas


def consultar_arris(nombre: str, ip: str) -> tuple[list[dict], str]:
    with SesionCLI(ip, "ARRIS") as s:
        crudo = s.ejecutar(ARRIS_CMD, fin_alterno=ARRIS_TOTAL_RE)
    filas = arris_parse(nombre, ip, crudo)
    if not filas:
        raise RuntimeError("[PARSER] Sin filas Fiber Node parseables")
    return filas, f"### {ARRIS_CMD}\n{crudo}\n"


def consultar(equipo: dict) -> tuple[list[dict], str]:
    if equipo["fabricante"] == "ARRIS":
        return consultar_arris(equipo["cmts"], equipo["ip"])
    return consultar_casa(equipo["cmts"], equipo["ip"])


# ======================================================= ARRIS: alias SNMP
OID_IFALIAS = "1.3.6.1.2.1.31.1.1.1.18"


class TraductorArris:
    """ID numérico de fiber node -> código de nodo (ifAlias "NODO XXX").

    Misma lógica que _arris_resolve_numeric_node() del unificador; el resultado
    queda en hfc_arris_alias y se reutiliza HFC_ARRIS_ALIAS_TTL_HORAS.
    """

    def __init__(self, cnx):
        c = config()
        self.cnx = cnx
        self.indice = self._json(c.arris_index)
        self.snmp = self._json(c.arris_snmp)
        self.avisos: list[str] = []
        if not self.indice or not self.snmp:
            self.avisos.append("Catálogos ARRIS no encontrados: los fiber nodes quedan con su ID numérico "
                               f"({c.arris_index.name}, {c.arris_snmp.name})")
        cur = cnx.cursor(dictionary=True)
        cur.execute("SELECT cmts, fiber_node, elemento, alias, estado, actualizado FROM hfc_arris_alias")
        self.cache = {(r["cmts"], r["fiber_node"]): r for r in cur.fetchall()}
        cur.close()
        self.nuevos: list[tuple] = []

    @staticmethod
    def _json(ruta):
        try:
            return json.loads(ruta.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def traducir(self, cmts: str, fiber_node: str) -> tuple[str, str, str]:
        if not str(fiber_node).isdigit():
            return str(fiber_node), "", "YA_OPERATIVO"
        clave = (cmts.upper(), str(fiber_node))
        previo = self.cache.get(clave)
        vigencia = ahora() - timedelta(hours=config().alias_ttl_horas)
        if previo and previo["actualizado"] >= vigencia and previo["estado"] != "ERROR":
            return previo["elemento"], previo["alias"], previo["estado"]
        elemento, alias, estado = self._resolver(cmts, str(fiber_node))
        if estado == "ERROR" and previo and previo["estado"] == "OK":
            return previo["elemento"], previo["alias"], previo["estado"]  # SNMP caído: se usa lo último bueno
        self.cache[clave] = {"elemento": elemento, "alias": alias, "estado": estado, "actualizado": ahora()}
        self.nuevos.append((clave[0], clave[1], elemento[:80], alias[:1000], estado, ahora()))
        return elemento, alias, estado

    def _resolver(self, cmts: str, fiber_node: str) -> tuple[str, str, str]:
        obj, datos = self.indice.get(cmts, {}), self.snmp.get(cmts)
        if not obj or not datos:
            return fiber_node, "", "SIN_CATALOGO"
        cmac = [str(x) for x in obj.get("cmac", {}).get(fiber_node, [])]
        if not cmac:
            return fiber_node, "", "SIN_CMAC"
        por_cmac = defaultdict(list)
        for r in obj.get("relacion", []):
            if "." in str(r):
                a, b = str(r).split(".", 1)
                por_cmac[a].append(b)
        upstreams = sorted({u for ci in cmac for u in por_cmac.get(ci, [])})
        if not upstreams:
            return fiber_node, "", "SIN_UPSTREAM"
        try:
            aliases = set()
            for i in range(0, len(upstreams), 10):
                lote = [f"{OID_IFALIAS}.{u}" for u in upstreams[i:i + 10]]
                for valor in snmp_get(datos[0], datos[1], lote, timeout=config().snmp_timeout).values():
                    if valor and valor.strip():
                        aliases.add(valor.strip())
        except Exception:
            return fiber_node, "", "ERROR"
        aliases = sorted(aliases)
        utiles = [a for a in aliases if a.upper() != "PUERTO LIBRE"]
        codigos = []
        for a in utiles:
            m = re.search(r"\bNODO\s+([A-Z0-9_-]+)\b", a, re.I)
            if m and m.group(1).upper() not in codigos:
                codigos.append(m.group(1).upper())
        texto = " | ".join(aliases)
        if len(codigos) == 1:
            return codigos[0], texto, "OK"
        if len(codigos) > 1:
            return fiber_node, texto, "CONFLICTO"
        if aliases and not utiles:
            return fiber_node, texto, "PUERTO_LIBRE"
        if utiles:
            return fiber_node, texto, "ALIAS_SIN_CODIGO"
        return fiber_node, "", "SIN_ALIAS"

    def guardar(self) -> None:
        if not self.nuevos:
            return
        cur = self.cnx.cursor()
        cur.executemany(
            "INSERT INTO hfc_arris_alias (cmts, fiber_node, elemento, alias, estado, actualizado) "
            "VALUES (%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE elemento=VALUES(elemento), "
            "alias=VALUES(alias), estado=VALUES(estado), actualizado=VALUES(actualizado)", self.nuevos)
        self.cnx.commit()
        cur.close()
        self.nuevos.clear()


# =============================================================== UNIFICAR
ZONAS = {"ARME": "ARMENIA", "BARR": "BARRANQUILLA", "BOGO": "BOGOTA", "BUCA": "BUCARAMANGA", "CALI": "CALI",
         "CHIA": "CHIA", "CUCU": "CUCUTA", "JAMU": "JAMUNDI", "MADRI": "MADRID", "MANI": "MANIZALES",
         "MEDE": "MEDELLIN", "PALM": "PALMIRA", "PERE": "PEREIRA", "POPA": "POPAYAN", "SANT": "SANTA MARTA",
         "SINC": "SINCELEJO", "SOACH": "SOACHA", "SOGA": "SOGAMOSO", "SOLE": "SOLEDAD", "TULU": "TULUA",
         "VILL": "VILLAVICENCIO", "YOPA": "YOPAL"}


def zona(cmts: str) -> str:
    c = (cmts or "").upper()
    if c.startswith("PERE-DOSQ-") or c.startswith("DRDA-"):
        return "DOSQUEBRADAS"  # igual que el unificador; dashboard_hfc.php corrige DRDA a DORADAL
    p = c.split("-", 1)[0]
    return ZONAS.get(p, p)


def estado_canonico(total: int, offline: int, fuente: str = "") -> str:
    if total <= 0:
        if "SIN UPSTREAM" in (fuente or "").upper().replace("_", " "):
            return "SIN UPSTREAM / REVISAR CONFIGURACION"
        return "SIN MODEMS / REVISAR CONFIGURACION"
    if offline <= 0:
        return "ENGANCHADO"
    if offline >= total:
        return "DESENGANCHE TOTAL"
    return "DESENGANCHE PARCIAL"


def _puntaje_casa(f: dict) -> tuple:
    return (1 if f["TOTAL"] > 0 else 0, 1 if f["FUENTE"] != "SIN_UPSTREAM" else 0, f["TOTAL"], f["OFFLINE"])


def unificar(casa: list[dict], arris: list[dict], traductor: TraductorArris | None) -> tuple[list[dict], dict]:
    """Devuelve filas finales con las columnas de hfc_unificado_actual.csv."""
    mejor: dict[tuple, dict] = {}
    duplicados = 0
    for f in casa:
        clave = (f["CMTS"].strip().upper(), f["ELEMENTO"].strip().upper())
        if not clave[0] or not clave[1]:
            continue
        if clave in mejor:
            duplicados += 1
            if _puntaje_casa(f) > _puntaje_casa(mejor[clave]):
                mejor[clave] = f
        else:
            mejor[clave] = f
    casa_final = list(mejor.values())

    arris_final: dict[tuple, dict] = {}
    for f in arris:
        original = f["ELEMENTO"]
        elemento, alias, estado = traductor.traducir(f["CMTS"], original) if traductor else (original, "", "SIN_CATALOGO")
        if estado == "PUERTO_LIBRE" and f["TOTAL"] <= 0 and f["OFFLINE"] <= 0:
            continue  # el original deja ELEMENTO vacío y la fila se descarta
        descripcion = f["DESCRIPCION"]
        if alias and estado == "OK":
            descripcion = f"{descripcion} | ARRIS ID {original} | {alias}".strip(" |")
        elif estado in ("CONFLICTO", "ALIAS_SIN_CODIGO"):
            descripcion = f"{descripcion} | ARRIS ID {original} | MAPEO {estado} | {alias}".strip(" |")
        fila = {**f, "ELEMENTO": elemento, "DESCRIPCION": descripcion}
        clave = (f["CMTS"].upper(), elemento.upper())
        if clave in arris_final:
            # Dos IDs que traducen al mismo nodo: se suman (la tabla exige una fila por elemento).
            previo = arris_final[clave]
            for k in ("TOTAL", "ACTIVE", "REGISTERED", "OFFLINE", "INIT", "DISABLE"):
                previo[k] += fila[k]
            previo["ID_FABRICANTE"] += f",{original}"
            previo["DESCRIPCION"] = f"{previo['DESCRIPCION']} | {descripcion}"
        else:
            arris_final[clave] = fila

    filas = []
    for f in casa_final + list(arris_final.values()):
        if not f["CMTS"] or not f["ELEMENTO"]:
            continue
        total, offline = f["TOTAL"], f["OFFLINE"]
        if f["FABRICANTE"] == "ARRIS":
            f["PRIORIDAD"] = arris_clasificar(total, offline)[1]
        filas.append({
            "FABRICANTE": f["FABRICANTE"], "ZONA": zona(f["CMTS"]), "CMTS": f["CMTS"], "IP": f["IP"],
            "ELEMENTO": f["ELEMENTO"], "ID_FABRICANTE": f["ID_FABRICANTE"],
            "TIPO_ELEMENTO": "FIBER NODE" if f["FABRICANTE"] == "ARRIS" else "SERVICE GROUP",
            "TOTAL_MODEMS": total, "ACTIVE_OPER": f["ACTIVE"], "REGISTERED": f["REGISTERED"],
            "DISABLE": f["DISABLE"], "INIT": f["INIT"], "OFFLINE": offline,
            "PORC_OFFLINE": round(offline / total * 100, 1) if total > 0 else 0.0,
            "PORC_OPER_ARRIS": f["PORC_OPER_ARRIS"],
            "OBSERVACION": estado_canonico(total, offline, f["FUENTE"]),
            "PRIORIDAD": f["PRIORIDAD"], "DESCRIPCION": f["DESCRIPCION"], "NIVEL_HISTORICO": "",
        })
    resumen = {"casa_fuente": len(casa), "casa_duplicados": duplicados, "arris_elementos": len(arris_final)}
    return filas, resumen
