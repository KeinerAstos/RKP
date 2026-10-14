"""Resultados compartidos: las lecturas HTTP nunca consultan Influx."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile

ROOT = Path(__file__).resolve().parents[1]

def directorio():
    from microservicios.entorno import path_value
    return path_value('INFLUX_RESULTADOS_DIR', 'backend/storage/influx')

def guardar(nombre, contenido):
    carpeta = directorio()
    carpeta.mkdir(parents=True, exist_ok=True)
    temporal = None
    try:
        with NamedTemporaryFile('w', encoding='utf-8', dir=carpeta, delete=False) as f:
            temporal = Path(f.name)
            json.dump(contenido, f, ensure_ascii=False, default=_fecha, allow_nan=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporal, carpeta / (nombre + '.json'))
    finally:
        if temporal is not None:
            temporal.unlink(missing_ok=True)

def _fecha(valor):
    from datetime import date
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()
    raise TypeError(type(valor).__name__)

def leer(nombre):
    try:
        return json.loads((directorio() / (nombre + '.json')).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None

def leer_resultado(nombre):
    from fastapi import HTTPException
    guardado = leer(nombre)
    if not guardado or 'data' not in guardado:
        raise HTTPException(503, 'Resultado pendiente: ejecutar iniciar_rutinas.py --ahora influx')
    return guardado['data']

def ahora():
    return datetime.now(timezone.utc).isoformat()

class Candado:
    def __enter__(self):
        carpeta = directorio()
        carpeta.mkdir(parents=True, exist_ok=True)
        self.f = (carpeta / 'rutina.lock').open('a+b')
        self.f.seek(0)
        if not self.f.read(1):
            self.f.write(b'0')
            self.f.flush()
        self.f.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.f.close()
            raise RuntimeError('Ya hay una rutina Influx ejecutándose') from None
        return self

    def __exit__(self, *args):
        self.f.close()
