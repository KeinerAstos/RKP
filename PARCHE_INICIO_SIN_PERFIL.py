"""Quita perfiles del iniciador portable V1. No modifica .env."""
from pathlib import Path
from datetime import datetime
import argparse
import shutil
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()
    path = root / 'iniciar_microserviciosypuente.py'
    wrapper = root / 'iniciar_microserviciosypuente_servidor.py'
    text = path.read_text(encoding='utf-8-sig')
    old = """    profile=required('RKP_PROFILE').lower()
    if profile not in ('local','servidor'): raise RuntimeError('RKP_PROFILE debe ser local o servidor')
    if expected_profile and profile != expected_profile:
        raise RuntimeError('Este iniciador requiere RKP_PROFILE='+expected_profile+'; el .env activo es '+profile)
"""
    if old in text:
        text = text.replace(old, '', 1)
        text = text.replace("    print('Perfil:',profile,'| .env:',ROOT/'.env')", "    print('Configuración:', ROOT/'.env')")
        text = text.replace('    return profile\n', '    return None\n')
        text = text.replace('def validate(expected_profile: str | None = None):', 'def validate():')
        text = text.replace('def main(expected_profile: str | None = None) -> int:', 'def main() -> int:')
        text = text.replace('os.chdir(ROOT);profile=validate(expected_profile)', 'os.chdir(ROOT);validate()')
    elif "print('Configuración:', ROOT/'.env')" not in text:
        raise RuntimeError('Versión no reconocida. No se modificó ningún archivo.')
    if 'RKP_PROFILE' in text or 'expected_profile' in text:
        raise RuntimeError('Quedan referencias de perfil no reconocidas. No se modificó ningún archivo.')
    updates = {path: text}
    if wrapper.exists():
        updates[wrapper] = '''"""Alias del iniciador común: usa únicamente el .env raíz."""
from iniciar_microserviciosypuente import main
if __name__ == '__main__':
    raise SystemExit(main())
'''
    changes = {p: content for p, content in updates.items()
               if p.read_text(encoding='utf-8-sig') != content}
    if not changes:
        print('OK: parche ya aplicado.'); return
    for p, content in changes.items():
        compile(content, str(p), 'exec')
    backup = root / 'backend' / 'storage' / '_backups' / ('inicio_sin_perfil_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir(parents=True, exist_ok=False)
    for p in changes:
        shutil.copy2(p, backup / p.name)
        print('BACKUP:', backup / p.name)
    try:
        for p, content in changes.items():
            p.write_text(content, encoding='utf-8')
            print('MODIFICADO:', p)
    except BaseException:
        for p in changes:
            shutil.copy2(backup / p.name, p)
        print('ERROR: restaurados los archivos originales.')
        raise
    print('OK: se usa el .env raíz sin exigir RKP_PROFILE. El .env no se modificó.')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('ERROR:', exc, file=sys.stderr)
        sys.exit(1)
