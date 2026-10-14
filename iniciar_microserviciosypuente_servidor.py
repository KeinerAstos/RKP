"""Arranque servidor: reutiliza el motor común y exige su perfil en .env."""
from iniciar_microserviciosypuente import main
if __name__ == '__main__':
    raise SystemExit(main(expected_profile='servidor'))
