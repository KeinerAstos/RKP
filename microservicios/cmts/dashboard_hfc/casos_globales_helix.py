"""Barrido HFC Helix por lotes con reanudacion. No modifica Oracle ni APIs.

Prueba: python -m microservicios.cmts.dashboard_hfc.casos_globales_helix_v4 --limit 100
Produccion (solo tras validar): ...casos_globales_helix_v4 --full
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from microservicios.cmts.dashboard_hfc.conexion import config
from microservicios.config import settings
from microservicios.olt.casos_helix import service as helix

ESTADOS_AFECTADOS = {
    "DESENGANCHE PARCIAL", "DESENGANCHE TOTAL",
    "POSIBLE DESENGANCHE TOTAL / HISTORICO",
    "POSIBLE CAIDA PROLONGADA / HISTORICO",
}
PATRON_NODO = re.compile(r"[A-Z0-9._-]{1,120}\Z")


def utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def escribir_atomico(ruta: Path, contenido: dict) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_name(ruta.name + ".tmp")
    with temporal.open("w", encoding="utf-8") as archivo:
        json.dump(contenido, archivo, ensure_ascii=False, indent=2)
        archivo.flush()
        os.fsync(archivo.fileno())
    os.replace(temporal, ruta)


def cargar_inventario():
    ruta = Path(config().dashboard_dir) / "estado_red.json"
    bruto = ruta.read_bytes()
    filas = json.loads(bruto.decode("utf-8-sig"))
    if not isinstance(filas, list):
        raise ValueError("estado_red.json debe contener un arreglo")
    afectados = [f for f in filas if isinstance(f, dict) and
                 f.get("observacion") in ESTADOS_AFECTADOS]
    nodos, invalidos = set(), set()
    for fila in afectados:
        for parte in str(fila.get("service_group") or "").upper().split(","):
            nodo = parte.strip()
            if PATRON_NODO.fullmatch(nodo):
                nodos.add(nodo)
            else:
                invalidos.add(nodo or "<VACIO>")
    return sorted(nodos), len(afectados), sorted(invalidos), hashlib.sha256(bruto).hexdigest()


def consulta(cursor, sql, ids, deadline, conexion, meter, etiqueta):
    """Mantiene los mismos binds que _in_query, pero reduce solo TMS_TASK a 50 IDs."""
    valores = sorted({str(v).strip() for v in ids if str(v or "").strip()})
    tam = 50 if etiqueta.startswith("TMS_TASK") else 200
    filas = []
    for posicion in range(0, len(valores), tam):
        grupo = valores[posicion:posicion + tam]
        inicio = time.perf_counter()
        try:
            filas.extend(helix._in_query(cursor, sql, grupo, deadline, conexion, meter))
        finally:
            print(f"  {etiqueta} grupo {posicion//tam+1}: {len(grupo)} IDs, "
                  f"{time.perf_counter()-inicio:.2f}s", flush=True)
    return filas

def contar_lote(nodos: list[str], presupuesto_segundos: int):
    resultado = {n: {"inc": set(), "wo": set(), "tas": set()} for n in nodos}
    ci_nodos, inc_nodos, wo_nodos = defaultdict(set), defaultdict(set), defaultdict(set)
    deadline = time.monotonic() + presupuesto_segundos
    meter = [0]
    dsn = helix.oracledb.makedsn(
        settings.oracle_helix_host, settings.oracle_helix_port,
        service_name=settings.oracle_helix_service_name)
    with helix.oracle_query_lock:
        pool = helix._get_pool(dsn)
        conexion = pool.acquire()
        fallida = True
        try:
            with conexion.cursor() as cursor:
                cursor.arraysize = 100
                cursor.prefetchrows = 100
                for nombre, ci in consulta(cursor, """
                    SELECT NAME, RECONCILIATION_IDENTITY
                    FROM ARADMIN.AST_BASEELEMENT
                    WHERE NAME IN ({bind_list})
                      AND SHORT_DESCRIPTION = 'RT.TR.HFC.NODO'
                      AND CLASS_ID = 'BMC_COMPUTERSYSTEM'
                """, nodos, deadline, conexion, meter, "AST_BASEELEMENT"):
                    n, c = helix._read(nombre).strip().upper(), helix._read(ci).strip()
                    if n in resultado and c:
                        ci_nodos[c].add(n)

                for ci, inc in consulta(cursor, """
                    SELECT REQUEST_ID01, REQUEST_ID02
                    FROM ARADMIN.HPD_ASSOCIATIONS
                    WHERE REQUEST_ID01 IN ({bind_list})
                      AND FORM_NAME01 = 'AST:ComputerSystem'
                      AND FORM_NAME02 = 'HPD:Help Desk'
                """, ci_nodos, deadline, conexion, meter, "HPD_ASSOCIATIONS"):
                    c, i = helix._read(ci).strip(), helix._read(inc).strip().upper()
                    if re.fullmatch(r"INC\d+", i):
                        inc_nodos[i].update(ci_nodos[c])

                for inc, estado in consulta(cursor, """
                    SELECT INCIDENT_NUMBER, STATUS FROM ARADMIN.HPD_HELP_DESK
                    WHERE INCIDENT_NUMBER IN ({bind_list})
                """, inc_nodos, deadline, conexion, meter, "HPD_HELP_DESK"):
                    i = helix._read(inc).strip().upper()
                    if helix._status(estado) in helix.OPEN_INC:
                        for n in inc_nodos[i]:
                            resultado[n]["inc"].add(i)

                # WO y TAS pueden permanecer abiertas aun si su INC padre esta cerrado.
                for wo, padre, estado in consulta(cursor, """
                    SELECT WORK_ORDER_ID, ROOT_INCIDENT, STATUS
                    FROM ARADMIN.WOI_WORKORDER
                    WHERE ROOT_INCIDENT IN ({bind_list})
                """, inc_nodos, deadline, conexion, meter, "WOI_WORKORDER"):
                    w, i = helix._read(wo).strip().upper(), helix._read(padre).strip().upper()
                    if not w:
                        continue
                    wo_nodos[w].update(inc_nodos[i])
                    if helix._status(estado) in helix.OPEN_WO:
                        for n in inc_nodos[i]:
                            resultado[n]["wo"].add(w)

                for padres, form, relacionados, etiqueta in (
                    (inc_nodos, "HPD:Help Desk", inc_nodos, "TMS_TASK_INC"),
                    (wo_nodos, "WOI:WorkOrder", wo_nodos, "TMS_TASK_WO"),
                ):
                    for tas, padre, estado in consulta(cursor, f"""
                        SELECT TASK_ID, ROOTREQUESTNAME, STATUS
                        FROM ARADMIN.TMS_TASK
                        WHERE ROOTREQUESTFORMNAME = '{form}'
                          AND STATUS IN (1000, 2000, 3000, 4000, 5000)
                          AND ROOTREQUESTNAME IN ({{bind_list}})
                    """, padres, deadline, conexion, meter, etiqueta):
                        t, p = helix._read(tas).strip().upper(), helix._read(padre).strip().upper()
                        if t and helix._status(estado) in helix.OPEN_TASK:
                            for n in relacionados[p]:
                                resultado[n]["tas"].add(t)
            fallida = False
        finally:
            if fallida:
                pool.drop(conexion)
            else:
                conexion.call_timeout = 0
                pool.release(conexion)
    return {n: {tipo: len(valores) for tipo, valores in casos.items()}
            for n, casos in resultado.items()}


def contar_lote_300(nodos: list[str], presupuesto_segundos: int):
    """
    Procesa un lote principal de hasta 300 nodos mediante
    sublotes independientes de 50.

    Conserva las validaciones y los limites del servicio Helix.
    """
    resultados = {}

    for posicion in range(0, len(nodos), 50):
        sublote = nodos[posicion:posicion + 50]

        print(
            f"  SUBLOTE {posicion // 50 + 1}: "
            f"{len(sublote)} nodos",
            flush=True
        )

        parcial = contar_lote(sublote, presupuesto_segundos)
        resultados.update(parcial)

    if len(resultados) != len(nodos):
        raise RuntimeError(
            "Resultado incompleto al consolidar los sublotes"
        )

    return resultados


def ejecutar(args):
    if helix.oracledb is None:
        raise RuntimeError("Falta dependencia oracledb")
    nodos, afectados, invalidos, inventario_hash = cargar_inventario()
    seleccion = nodos if args.full else nodos[:args.limit]
    if not seleccion:
        raise ValueError("No hay nodos para consultar")
    identidad = hashlib.sha256(json.dumps({
        "inventario": inventario_hash, "nodos": seleccion,
        "batch_size": args.batch_size, "version": 5},
        sort_keys=True).encode()).hexdigest()
    carpeta = Path(args.output_dir).resolve()
    carpeta.mkdir(parents=True, exist_ok=True)
    progreso = carpeta / "progreso_global.json"
    publicado = carpeta / "resumen_global.json"
    candado = carpeta / "proceso_global.lock"
    # Impide dos ejecuciones que escriban el mismo progreso.
    fd = os.open(str(candado), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(f"PID={os.getpid()} inicio={utc()}\n")
        if progreso.exists():
            estado = json.loads(progreso.read_text(encoding="utf-8"))
            if estado.get("identidad") != identidad:
                raise RuntimeError("Inventario, seleccion o tamano de lote cambiaron. "
                                   "Use otro --output-dir para comenzar un barrido nuevo.")
        else:
            estado = {"identidad": identidad, "inicio": utc(), "modo": "full" if args.full else "prueba",
                      "inventario_sha256": inventario_hash, "registros_afectados": afectados,
                      "total_nodos_validos": len(nodos), "nodos_objetivo": len(seleccion),
                      "invalidos": invalidos, "lotes": {}, "estado": "en_progreso"}
            escribir_atomico(progreso, estado)
        total_lotes = (len(seleccion) + args.batch_size - 1) // args.batch_size
        print(f"Inventario: {afectados} filas afectadas; {len(nodos)} nodos validos; "
              f"{len(invalidos)} componente(s) invalido(s): {invalidos[:10]}")
        print(f"Objetivo: {len(seleccion)} nodos en {total_lotes} lotes de {args.batch_size}.")
        for pos in range(0, len(seleccion), args.batch_size):
            numero = pos // args.batch_size + 1
            llave = str(numero)
            lote = seleccion[pos:pos + args.batch_size]
            existente = estado["lotes"].get(llave)
            if existente and existente.get("estado") == "ok":
                print(f"LOTE {numero}/{total_lotes}: recuperado de progreso, omitido")
                continue
            for intento in range(1, args.retries + 2):
                try:
                    print(f"LOTE {numero}/{total_lotes}: {len(lote)} nodos, intento {intento}", flush=True)
                    comienzo = time.perf_counter()
                    resultado = contar_lote_300(lote, args.budget)
                    estado["lotes"][llave] = {"estado": "ok", "nodos": resultado,
                        "segundos": round(time.perf_counter()-comienzo, 2), "terminado_en": utc()}
                    escribir_atomico(progreso, estado)
                    break
                except Exception as exc:
                    print(f"ERROR LOTE {numero}, intento {intento}: {type(exc).__name__}: {exc}",
                          file=sys.stderr, flush=True)
                    estado["lotes"][llave] = {"estado": "error", "tipo": type(exc).__name__,
                                             "mensaje": str(exc)[:400], "fecha": utc()}
                    escribir_atomico(progreso, estado)
                    if intento <= args.retries:
                        time.sleep(3)
                    else:
                        print("Barrido interrumpido; reejecute el mismo comando para reanudar.",
                              file=sys.stderr)
                        return 2
        # Solo publicar una fotografia completa en modo --full.
        resultados = {}
        for i in range(1, total_lotes+1):
            lote = estado["lotes"].get(str(i))
            if not lote or lote.get("estado") != "ok":
                return 2
            resultados.update(lote["nodos"])
        if set(resultados) != set(seleccion):
            raise RuntimeError("Resultado incompleto o identificadores inconsistentes")
        con = sum(any(d[t] > 0 for t in ("inc", "wo", "tas")) for d in resultados.values())
        resumen = {"estado": "completo_nodos_validos" if args.full else "prueba_completa",
                   "calculado_en": utc(), "inventario_sha256": inventario_hash,
                   "registros_afectados": afectados, "nodos_unicos_validos": len(nodos),
                   "nodos_consultados": len(resultados), "con_casos": con,
                   "sin_casos": len(resultados)-con, "exclusiones": invalidos,
                   "nota": "Totales por nodo individual, NO por fila HFC; casos consultados durante el barrido"}
        if args.full:
            escribir_atomico(publicado, resumen)
            print(f"Resumen completo publicado: {publicado}")
        else:
            print("PRUEBA: no se publico resumen global")
        estado["estado"] = "completado"
        estado["fin"] = utc()
        escribir_atomico(progreso, estado)
        print(json.dumps(resumen, indent=2, ensure_ascii=False))
        return 0
    finally:
        candado.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description="HFC Helix v4: barrido por lotes reanudable")
    parser.add_argument("--limit", type=int, default=100, help="Nodos de prueba (maximo 100)")
    parser.add_argument("--batch-size", type=int, default=300, help="1 a 300 nodos por lote")
    parser.add_argument("--budget", type=int, default=180, help="Segundos por intento de lote")
    parser.add_argument("--retries", type=int, default=1, help="Reintentos adicionales por lote (0 a 2)")
    parser.add_argument("--full", action="store_true", help="Barrido completo; publicar solo al terminar")
    parser.add_argument("--output-dir", default="data/dashboard_hfc/helix_global",
                        help="Carpeta nueva y separada para progreso y resumen")
    args = parser.parse_args()
    if not 1 <= args.limit <= 150: parser.error("--limit debe estar entre 1 y 150")
    if not 1 <= args.batch_size <= 300: parser.error("--batch-size debe estar entre 1 y 300")
    if not 30 <= args.budget <= 600: parser.error("--budget debe estar entre 30 y 600")
    if not 0 <= args.retries <= 2: parser.error("--retries debe estar entre 0 y 2")
    try:
        return ejecutar(args)
    except FileExistsError:
        print("ERROR: existe el candado de ejecucion. Confirme que no hay otro proceso activo; "
              "si fue una interrupcion, borre manualmente proceso_global.lock.", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
