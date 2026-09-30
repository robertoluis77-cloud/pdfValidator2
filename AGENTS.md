# AGENTS.md

## Contexto del proyecto

- Script de Windows que empaca subcarpetas en archivos ZIP invocando `WinRAR.exe`. `src/compresor.py` es un programa ejecutable unificado: el perfil (4 MB o 19 MB) se selecciona con `--limite 4mb` o `--limite 19mb`. Reemplaza a `comprime4mb.py` y `comprime19mb.py` (respaldo en `backup_original/`).
- No hay lint, typecheck ni CI. La verificación se hace con pytest (`tests/`) y con ejecuciones reales contra un árbol de datos de prueba revisando las cifras de control.

## Peligros de ejecución (crítico)

- Es destructivo: borra `*.db` y `*.ini` de forma recursiva en cada carpeta procesada, y elimina y recrea los `*.zip` previos. Usar `--dry-run` para previsualizar.
- Opera sobre las subcarpetas del directorio de trabajo actual (`--dir`, por defecto `.`). Ejecutarlo desde la raíz del proyecto procesaría `src/` y `venv/`.
- `src/compresor.py` SÍ tiene guard `if __name__ == "__main__"` y es importable con seguridad (los tests lo importan); los scripts de `backup_original/` NO lo tienen: nunca importarlos, un import lanza el proceso completo.
- Solo Windows: usa `msvcrt` (pausa con teclado) y `WinRAR.exe`.

## Comandos de verificación

- Tests: `venv\Scripts\python.exe -m pytest tests -v` (nunca invocan WinRAR real: `subprocess.run` se simula).
- Humo real: `venv\Scripts\python.exe src\compresor.py --limite 4mb --dir <carpeta-de-datos> --log-dir <logs> --dry-run`.

## Rutas fijas (hardcodeadas, sobrescribibles)

- `winrar_ruta`: por defecto `C:\winrar_ejecutable\WinRAR.exe`; ajustar con `--winrar`; el script verifica su existencia al inicio.
- La bitácora se escribe en `<log-dir>\Log-<fecha>.txt` (por defecto `c:\SAT_logs`): la carpeta se crea automáticamente si falta.
- Los límites están en los perfiles de `PERFILES` en `src/compresor.py` (`limite_grupo`, `limite_reempacado`, `limite_arch_origen`, `limite50kb`, `max_files_per_iteration`); en bytes, no en MB.

## Dependencias

- En tiempo de ejecución el script no requiere paquetes externos: solo biblioteca estándar.
- `pip install -e .[dev]` instala `pytest`, `ruff` y `black` (extras de desarrollo en `pyproject.toml`).
- El código original usó `PyPDF2` y `pdfminer.six` para validación de PDF, pero ese código estaba muerto y fue eliminado; por tanto ya no son dependencias.
