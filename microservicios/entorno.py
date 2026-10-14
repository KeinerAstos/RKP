"""Carga única del .env raíz, independiente del directorio de ejecución."""
from __future__ import annotations
from functools import lru_cache
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / '.env'


def parse_env(text: str) -> dict[str, str]:
    result = {}
    for line in text.lstrip('\ufeff').splitlines():
        match = re.match(r'^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$', line)
        if not match:
            continue
        key, value = match.groups()
        if value[:1] in ('"', "'"):
            quote = value[0]
            # Preserve secret values as written, without variable expansion.
            end = next((i for i in range(len(value)-1, 0, -1) if value[i] == quote), -1)
            if end > 0:
                value = value[1:end]
        else:
            value = re.split(r'\s+#', value, maxsplit=1)[0].rstrip()
        result[key] = value
    return result


@lru_cache(maxsize=1)
def read_env() -> dict[str, str]:
    if not ENV_FILE.is_file():
        raise RuntimeError(f'No existe {ENV_FILE}; aplica el perfil .env del equipo')
    return parse_env(ENV_FILE.read_text(encoding='utf-8-sig'))


def load_env() -> dict[str, str]:
    values = read_env()
    for key, value in values.items():
        os.environ.setdefault(key, value)
    # Legacy aliases only when the canonical variable is absent.
    for key in ['URL', 'VERIFY_SSL', 'ORG', 'TOKEN', 'BUCKET', 'TIMEOUT_MS']:
        alias = 'CMTS_INFLUX_' + key
        canonical = 'INFLUX_CMTS_' + key
        if canonical not in os.environ and alias in os.environ:
            os.environ[canonical] = os.environ[alias]
    return values


def env(name: str, default: str = '') -> str:
    load_env()
    return os.environ.get(name, default)


def required(name: str) -> str:
    value = env(name).strip()
    if not value:
        raise RuntimeError(f'Falta {name} en .env')
    return value


def boolean(name: str, default: bool = False) -> bool:
    value = env(name, 'true' if default else 'false').strip().lower()
    if value in ('1', 'true', 'yes', 'on'): return True
    if value in ('0', 'false', 'no', 'off', ''): return False
    raise RuntimeError(f'{name} debe ser true o false')


def port(name: str) -> int:
    try: value = int(required(name))
    except ValueError: raise RuntimeError(f'{name} debe ser un puerto numérico') from None
    if not 1 <= value <= 65535: raise RuntimeError(f'{name} debe estar entre 1 y 65535')
    return value


def path_value(name: str, default: str = '') -> Path:
    value = required(name) if not default else env(name, default)
    path = Path(value).expanduser()
    return path if path.is_absolute() else ROOT / path
