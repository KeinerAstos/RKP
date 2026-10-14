"""Rutina del Dashboard HFC: reemplaza run_hfc_30min.sh de noc_cable.

Ciclo: CASA + ARRIS por SSH -> unificar -> MySQL (rkp_hfc) -> validación
histórica V2 -> estado actual -> retención 1 mes + 1 día -> publicación.

Uso (desde la raíz de RKP):
  python -m microservicios.dashboard_hfc.rutina --ciclo
  python -m microservicios.dashboard_hfc.rutina --equipo BOGO-CENT-C-01-CS100G --crudo
  python -m microservicios.dashboard_hfc.rutina --comparar ruta\\hfc_unificado_actual.csv
  python -m microservicios.dashboard_hfc.rutina --purgar
  python -m microservicios.dashboard_hfc.rutina --loop        (ciclo cada HFC_INTERVALO_SEGUNDOS)
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from microservicios.dashboard_hfc import colectores, historico
from microservicios.dashboard_hfc.conexion import BOGOTA, ahora, bd, config, conectar_bd, inventario

LOCK_BD = "rkp_dashboard_hfc_ciclo"
CAMPOS_CSV = ["FECHA_REPORTE", "FABRICANTE", "ZONA", "CMTS", "IP", "ELEMENTO", "TIPO_ELEMENTO", "TOTAL_MODEMS",
              "ACTIVE_OPER", "REGISTERED", "DISABLE", "INIT", "OFFLINE", "PORC_OFFLINE", "PORC_OPER_ARRIS",
              "OBSERVACION", "PRIORIDAD", "DESCRIPCION"]


# ===================================================================== ciclo
def _consultar(equipo: dict) -> dict:
    inicio = time.monotonic()
    r = {"equipo": equipo, "ok": False, "filas": [], "error": "", "etapa": ""}
    try:
        r["filas"], _ = colectores.consultar(equipo)
        r["ok"] = True
    except Exception as exc:
        mensaje = config().ocultar(str(exc) or type(exc).__name__).replace("\n", " ")
        m = re.match(r"^\[([^\]]+)\]", mensaje)
        r["etapa"] = (m.group(1) if m else "")[:40]
        r["error"] = mensaje[:400]
    r["duracion_ms"] = int((time.monotonic() - inicio) * 1000)
    return r


def ciclo() -> dict:
    c = config()
    equipos = inventario()
    candado = conectar_bd()
    cur = candado.cursor()
    cur.execute("SELECT GET_LOCK(%s, 0)", (LOCK_BD,))
    if (cur.fetchone() or [0])[0] != 1:
        candado.close()
        raise RuntimeError("Ya hay otro ciclo HFC en ejecución")
    cur.close()
    run_id = uuid.uuid4().hex
    inicio = ahora()
    try:
        with bd() as cnx:
            k = cnx.cursor()
            k.execute("INSERT INTO hfc_ciclos (run_id, inicio, cmts_total) VALUES (%s,%s,%s)",
                      (run_id, inicio, len(equipos)))
            cnx.commit()
            k.close()
        try:
            return _ciclo(run_id, inicio, equipos, c)
        except Exception as exc:
            with bd() as cnx:
                k = cnx.cursor()
                k.execute("UPDATE hfc_ciclos SET fin=%s, estado='error', error=%s WHERE run_id=%s",
                          (ahora(), c.ocultar(str(exc))[:500], run_id))
                cnx.commit()
                k.close()
            raise
    finally:
        try:
            k = candado.cursor()
            k.execute("SELECT RELEASE_LOCK(%s)", (LOCK_BD,))
            k.fetchall()
            k.close()
        finally:
            candado.close()


def _ciclo(run_id: str, inicio: datetime, equipos: list[dict], c) -> dict:
    print(f"[HFC] Ciclo {run_id} · {len(equipos)} CMTS · {c.workers} hilos", flush=True)
    resultados = []
    with ThreadPoolExecutor(max_workers=c.workers) as pool:
        for n, fut in enumerate(as_completed([pool.submit(_consultar, e) for e in equipos]), 1):
            r = fut.result()
            resultados.append(r)
            estado = f"OK {len(r['filas'])}" if r["ok"] else f"ERROR {r['error'][:120]}"
            print(f"[{n}/{len(equipos)}] {r['equipo']['cmts']} · {estado} · {r['duracion_ms']} ms", flush=True)
    ok = sum(r["ok"] for r in resultados)
    casa = [f for r in resultados if r["ok"] and r["equipo"]["fabricante"] == "CASA" for f in r["filas"]]
    arris = [f for r in resultados if r["ok"] and r["equipo"]["fabricante"] == "ARRIS" for f in r["filas"]]

    with bd() as cnx:
        traductor = colectores.TraductorArris(cnx) if arris else None
        filas, resumen = colectores.unificar(casa, arris, traductor)
        if traductor:
            traductor.guardar()
            for aviso in traductor.avisos:
                print(f"[HFC] AVISO: {aviso}", flush=True)
        fecha = ahora()
        k = cnx.cursor()
        k.executemany(
            "INSERT INTO hfc_consultas_cmts (run_id, fecha, fabricante, cmts, ip, ok, elementos, duracion_ms, "
            "etapa_error, error) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            [(run_id, fecha, r["equipo"]["fabricante"], r["equipo"]["cmts"][:60], r["equipo"]["ip"], int(r["ok"]),
              len(r["filas"]), r["duracion_ms"], r["etapa"], r["error"]) for r in resultados])
        muestras = [(run_id, fecha, f["FABRICANTE"], f["CMTS"][:60], f["ELEMENTO"][:80], f["TOTAL_MODEMS"],
                     f["ACTIVE_OPER"], f["REGISTERED"], f["OFFLINE"], f["INIT"], f["DISABLE"] or 0) for f in filas]
        for i in range(0, len(muestras), 2000):
            k.executemany(
                "INSERT INTO hfc_muestras (run_id, fecha, fabricante, cmts, elemento, total_modems, active_oper, "
                "registered, offline, init_cm, disable_cm) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                muestras[i:i + 2000])
        cnx.commit()

        # La V2 va después de guardar las muestras: el ciclo actual cuenta como cero.
        auditoria = historico.aplicar_v2(cnx, filas, fecha, run_id) if filas else []
        if auditoria:
            k.executemany(
                "INSERT INTO hfc_validacion_historica (run_id, fecha, fabricante, cmts, elemento, "
                "observacion_anterior, observacion_nueva, prioridad_nueva, nivel_historico, muestras_positivas, "
                "ultimo_total_positivo, ultima_fecha_positiva, mediana_total_hist, max_total_hist, "
                "ceros_consecutivos, inicio_cero_estimado, horas_en_cero, razon) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", auditoria)
        if filas:
            k.execute("UPDATE hfc_estado_actual SET vigente = 0")
            columnas = ["fabricante", "cmts", "elemento", "zona", "ip", "tipo_elemento", "id_fabricante",
                        "total_modems", "active_oper", "registered", "disable_cm", "init_cm", "offline",
                        "porc_offline", "porc_oper_arris", "observacion", "prioridad", "descripcion",
                        "nivel_historico", "fecha_reporte", "run_id", "vigente"]
            datos = [(f["FABRICANTE"], f["CMTS"][:60], f["ELEMENTO"][:80], f["ZONA"][:40], f["IP"],
                      f["TIPO_ELEMENTO"], str(f["ID_FABRICANTE"])[:40], f["TOTAL_MODEMS"], f["ACTIVE_OPER"],
                      f["REGISTERED"], f["DISABLE"], f["INIT"], f["OFFLINE"], f["PORC_OFFLINE"],
                      f["PORC_OPER_ARRIS"], f["OBSERVACION"][:60], f["PRIORIDAD"][:10], f["DESCRIPCION"],
                      f["NIVEL_HISTORICO"], fecha, run_id, 1) for f in filas]
            sql = (f"INSERT INTO hfc_estado_actual ({', '.join(columnas)}) VALUES ({', '.join(['%s'] * len(columnas))}) "
                   "ON DUPLICATE KEY UPDATE " + ", ".join(f"{x}=VALUES({x})" for x in columnas[3:]))
            for i in range(0, len(datos), 2000):
                k.executemany(sql, datos[i:i + 2000])
        cnx.commit()
        k.close()
        borrados = historico.purgar(cnx)

    publicado = False
    if filas:
        exportar_csv(filas, fecha)
        if c.publicar_json:
            publicar_dashboard(filas, fecha, run_id)
            publicado = True
    estado = "sin_datos" if not filas else ("completo" if ok == len(resultados) else "parcial")
    with bd() as cnx:
        k = cnx.cursor()
        k.execute(
            "UPDATE hfc_ciclos SET fin=%s, estado=%s, cmts_ok=%s, cmts_error=%s, elementos=%s, casa_fuente=%s, "
            "casa_duplicados=%s, arris_elementos=%s, reclasificados_v2=%s, publicado=%s WHERE run_id=%s",
            (ahora(), estado, ok, len(resultados) - ok, len(filas), resumen["casa_fuente"],
             resumen["casa_duplicados"], resumen["arris_elementos"], len(auditoria), int(publicado), run_id))
        cnx.commit()
        k.close()
    return {"run_id": run_id, "estado": estado, "cmts_ok": ok, "cmts_error": len(resultados) - ok,
            "elementos": len(filas), "reclasificados_v2": len(auditoria), "publicado": publicado,
            "purgados": borrados, **resumen}


# ================================================================ salidas
def _atomico(ruta, contenido: str, encoding: str = "utf-8") -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_name(f".{ruta.name}.{uuid.uuid4().hex}.tmp")
    try:
        with tmp.open("w", encoding=encoding, newline="") as f:
            f.write(contenido)
        if ruta.exists():
            shutil.copy2(ruta, ruta.with_name(ruta.name + ".last_good"))
        os.replace(tmp, ruta)
    finally:
        tmp.unlink(missing_ok=True)


def exportar_csv(filas: list[dict], fecha: datetime) -> None:
    """Mismo formato que hfc_unificado_actual.csv de noc_cable (para comparar)."""
    import io

    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=CAMPOS_CSV, delimiter=";", extrasaction="ignore")
    w.writeheader()
    for f in filas:
        w.writerow({**f, "FECHA_REPORTE": fecha.strftime("%Y-%m-%d %H:%M:%S"),
                    "DISABLE": "" if f["DISABLE"] is None else f["DISABLE"]})
    _atomico(config().salida_dir / "hfc_unificado_actual.csv", buf.getvalue(), "utf-8-sig")


def fila_dashboard(f: dict) -> dict:
    """Misma transformación que importar_base de backend/api/dashboard_hfc.php."""
    total, offline = f["TOTAL_MODEMS"], f["OFFLINE"]
    if f["OBSERVACION"] in historico.ESTADOS_V2:
        obs = f["OBSERVACION"]
    elif total <= 0:
        obs = "SIN MODEMS / VALIDAR"
    elif offline <= 0:
        obs = "ENGANCHADO"
    elif offline >= total:
        obs = "DESENGANCHE TOTAL"
    else:
        obs = "DESENGANCHE PARCIAL"
    return {"fabricante": f["FABRICANTE"], "zona": f["ZONA"].upper(), "cmts": f["CMTS"], "ip": f["IP"],
            "service_group": f["ELEMENTO"], "tipo_elemento": f["TIPO_ELEMENTO"], "total_modems": total,
            "active": f["ACTIVE_OPER"], "registered": f["REGISTERED"], "offline": offline,
            "porc_offline": offline / total if total > 0 else 0, "observacion": obs, "detalle_observacion": "",
            "prioridad": f["PRIORIDAD"], "descripcion": f["DESCRIPCION"], "fecha_incidente": "",
            "hora_incidente": "", "inc_status": ""}


def publicar_dashboard(filas: list[dict], fecha: datetime, run_id: str) -> None:
    """Escribe estado_red.json y ultima_carga_hfc_auto.json, que ya lee dashboard_hfc.php."""
    c = config()
    contenido = json.dumps([fila_dashboard(f) for f in filas], ensure_ascii=False, separators=(",", ":"))
    _atomico(c.dashboard_dir / "estado_red.json", contenido)
    marca = fecha.replace(tzinfo=BOGOTA)
    meta = {"ok": True, "mode": "HFC_LOCAL_SSH_MYSQL", "source": f"mysql:{c.db_database}", "source_host": "LOCAL",
            "source_timestamp": int(marca.timestamp()), "source_iso": marca.isoformat(),
            "source_size": len(contenido.encode()), "sha256": hashlib.sha256(contenido.encode()).hexdigest(),
            "rows": len(filas), "imported_iso": datetime.now(BOGOTA).isoformat(), "run_id": run_id}
    _atomico(c.dashboard_dir / "ultima_carga_hfc_auto.json", json.dumps(meta, ensure_ascii=False))


# =========================================================== herramientas
def probar_equipo(nombre: str, crudo: bool) -> int:
    """Consulta un CMTS y muestra lo interpretado. No escribe en la BD."""
    equipo = next((e for e in inventario() if e["cmts"].casefold() == nombre.casefold() or e["ip"] == nombre), None)
    if equipo is None:
        print("ERROR: el CMTS no está en inventario.ini")
        return 1
    print(f"{equipo['fabricante']} {equipo['cmts']} ({equipo['ip']})")
    t0 = time.monotonic()
    try:
        filas, salida = colectores.consultar(equipo)
    except Exception as exc:
        print(f"ERROR ({time.monotonic() - t0:.1f}s): {config().ocultar(str(exc))}")
        return 2
    print(f"OK en {time.monotonic() - t0:.1f}s · {len(filas)} elementos")
    if crudo:
        ruta = config().salida_dir / "crudo" / f"{equipo['cmts']}_{datetime.now():%Y%m%d_%H%M%S}.txt"
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(salida, encoding="utf-8")
        print(f"Salida cruda: {ruta}")
    traductor = None
    if equipo["fabricante"] == "ARRIS":
        try:
            cnx = conectar_bd()
            traductor = colectores.TraductorArris(cnx)
        except Exception as exc:
            print(f"(sin traducción SNMP: {exc})")
    unificadas, _ = colectores.unificar(filas if equipo["fabricante"] == "CASA" else [],
                                       filas if equipo["fabricante"] == "ARRIS" else [], traductor)
    print(f"{'ELEMENTO':<24}{'ID':>8}{'TOTAL':>7}{'ACTIVE':>7}{'OFFL':>6}  OBSERVACION")
    for f in sorted(unificadas, key=lambda x: x["ELEMENTO"]):
        print(f"{f['ELEMENTO'][:23]:<24}{str(f['ID_FABRICANTE'])[:7]:>8}{f['TOTAL_MODEMS']:>7}"
              f"{f['ACTIVE_OPER']:>7}{f['OFFLINE']:>6}  {f['OBSERVACION']}")
    return 0


def comparar(ruta_noc: str) -> int:
    """Compara el estado actual de MySQL con un hfc_unificado_actual.csv de noc_cable."""
    with open(ruta_noc, encoding="utf-8-sig", newline="") as f:
        primera = f.readline()
        f.seek(0)
        noc = {(r["FABRICANTE"].upper(), r["CMTS"].upper(), r["ELEMENTO"].upper()): r
               for r in csv.DictReader(f, delimiter=";" if primera.count(";") >= primera.count(",") else ",")}
    with bd() as cnx:
        cur = cnx.cursor(dictionary=True)
        cur.execute("SELECT * FROM hfc_estado_actual WHERE vigente = 1")
        local = {(r["fabricante"], r["cmts"].upper(), r["elemento"].upper()): r for r in cur.fetchall()}
    for fab in ("CASA", "ARRIS"):
        n = sum(k[0] == fab for k in noc)
        l = sum(k[0] == fab for k in local)
        print(f"{fab:<6} noc_cable={n:>6}  local={l:>6}")
    solo_noc, solo_local = sorted(set(noc) - set(local)), sorted(set(local) - set(noc))
    print(f"Solo en noc_cable: {len(solo_noc)}   Solo en local: {len(solo_local)}")
    for k in solo_noc[:15]:
        print("  noc  :", " | ".join(k))
    for k in solo_local[:15]:
        print("  local:", " | ".join(k))
    comunes = set(noc) & set(local)
    dif_total = [k for k in comunes if abs(int(noc[k]["TOTAL_MODEMS"] or 0) - local[k]["total_modems"]) > max(
        5, 0.1 * int(noc[k]["TOTAL_MODEMS"] or 0))]
    dif_obs = [k for k in comunes if noc[k]["OBSERVACION"] != local[k]["observacion"]]
    print(f"Comunes: {len(comunes)} · TOTAL_MODEMS distinto (>10% y >5): {len(dif_total)} · "
          f"OBSERVACION distinta: {len(dif_obs)}")
    print("(diferencias pequeñas son normales: las dos rutinas no consultan en el mismo minuto)")
    for k in sorted(dif_obs)[:15]:
        print(f"  {' | '.join(k)}: noc={noc[k]['OBSERVACION']}  local={local[k]['observacion']}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Rutina Dashboard HFC (SSH -> MySQL rkp_hfc)")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--ciclo", action="store_true", help="Ejecuta un ciclo completo")
    g.add_argument("--loop", action="store_true", help="Ciclo cada HFC_INTERVALO_SEGUNDOS (por defecto 1800)")
    g.add_argument("--equipo", help="Prueba un CMTS por nombre o IP, sin escribir en la BD")
    g.add_argument("--comparar", metavar="CSV", help="Compara con hfc_unificado_actual.csv de noc_cable")
    g.add_argument("--purgar", action="store_true", help="Solo aplica la retención")
    p.add_argument("--crudo", action="store_true", help="Con --equipo, guarda la salida CLI")
    a = p.parse_args()
    try:
        if a.equipo:
            return probar_equipo(a.equipo, a.crudo)
        if a.comparar:
            return comparar(a.comparar)
        if a.purgar:
            with bd() as cnx:
                print("Purgados:", historico.purgar(cnx))
            return 0
        while True:
            t0 = time.monotonic()
            try:
                r = ciclo()
                print(f"[HFC] {r['estado'].upper()} · CMTS ok={r['cmts_ok']} error={r['cmts_error']} · "
                      f"elementos={r['elementos']} · V2={r['reclasificados_v2']} · publicado={r['publicado']} · "
                      f"purgados={sum(r['purgados'].values())}", flush=True)
                codigo = 0 if r["estado"] == "completo" else 2
            except Exception as exc:
                print(f"[HFC] ERROR: {type(exc).__name__}: {config().ocultar(str(exc))}", flush=True)
                codigo = 1
            if not a.loop:
                return codigo
            time.sleep(max(60, config().intervalo - (time.monotonic() - t0)))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
