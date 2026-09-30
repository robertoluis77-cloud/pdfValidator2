# sugerencias.md — Análisis técnico y recomendaciones de mejora

> **Estado:** las sugerencias críticas (§1, §5) y las refactorizaciones (§6) se implementaron en el script unificado `src/compresor.py`, que reemplaza a `comprime4mb.py` y `comprime19mb.py` (respaldo en `backup_original/`). Queda pendiente solo la alternativa de *best-fit* con `bisect` (3.4), descartada para preservar la composición de grupos del algoritmo original.

Análisis del código fuente de `src/comprime4mb.py` y `src/comprime19mb.py`. Ambos archivos son ~90 % idénticos: solo cambian las constantes de tamaño de cabecera. Las recomendaciones aplican a ambos salvo indicación de línea específica.

## 1. Hallazgos críticos (riesgos de ejecución)

### 1.1 Ruta de bitácora con escape mixto
`comprime4mb.py:456` usa `"c:\\SAT_logs\Log-"`: mezcla `\\` con `\L`. Como `\L` no es una secuencia de escape reconocida, Python la conserva literal y el código "funciona de suerte", pero lanza `SyntaxWarning` en Python 3.12+ y es frágil (un `\t` o `\n` accidental rompería la ruta). Usar cadena cruda:

```python
log_ruta = r"c:\SAT_logs\Log-"
```

### 1.2 Carpeta de bitácora no se crea
El script abre `c:\SAT_logs\Log-<fecha>.txt` sin verificar que `c:\SAT_logs` exista; si falta, falla con `FileNotFoundError` a mitad del proceso, después de haber borrado archivos. Crearla al inicio:

```python
os.makedirs(r"c:\SAT_logs", exist_ok=True)
```

### 1.3 Uso de `quit()` en código de producción
`comprime4mb.py:232, 430` y `comprime19mb.py:107, 238` usan `quit()`, función pensada para el intérprete interactivo, no para scripts. Usar `sys.exit(1)` o, mejor, lanzar excepciones con mensaje:

```python
raise SystemExit(f"El archivo {archivo} supera el límite {limite_arch_origen}")
```

### 1.4 Sombreado de variables en bucles anidados
`comprime4mb.py:397/425/433` y `comprime19mb.py:216/233/240`: el bucle exterior itera `for file in basefolder:` (nombres de carpeta) y los bucles interiores reutilizan `for file in objeto_arch:` (rutas de archivo). Tras el bucle interior, `file` queda con la última ruta de archivo, corruptiendo el estado del bucle exterior y produciendo mensajes erróneos (el mensaje de abortado imprime la ruta dos veces donde la primera debería ser la carpeta). Renombrar a `carpeta` y `archivo` respectivamente.

### 1.5 `mainfoldername` puede quedar indefinido
`comprime4mb.py:474-476` y `comprime19mb.py:266-268`: si todas las carpetas empiezan con `tempo`, `mainfoldername` queda indefinido (`NameError` latente). Además, la variable nunca se usa: código muerto. Eliminarla o validar el caso.

### 1.6 Acoplamiento oculto con globales
`empacar_archivos()` usa `ruta_arch` (definida como global dentro del bucle principal, `comprime4mb.py:409` / `comprime19mb.py:226`) sin recibirla como parámetro. Funciona por accidente porque el bucle la asigna antes de llamarla. Pasarla como argumento explícito.

### 1.7 Invocación de WinRAR sin verificación
`comprime4mb.py:222` y `comprime19mb.py:99`: `subprocess.run(cmd)` sin `check=True`, sin capturar `stderr` y sin timeout. Riesgos:
- Si WinRAR falla (archivo bloqueado, antivirus), el script continúa silenciosamente y `os.path.getsize(ruta_salida)` posterior puede lanzar `FileNotFoundError`.
- El comando actual no incluye `-y` (asumir "sí" a todo): si WinRAR muestra un diálogo interactivo, el script queda colgado. Añadir `-y` y `-ibck` (ejecutar en segundo plano).

```python
resultado = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
if resultado.returncode != 0:
    # registrar resultado.stderr en la bitácora y decidir: abortar o continuar
```

### 1.8 Dependencia PyPDF2 legacy
`from PyPDF2 import PdfFileReader, PdfFileWriter` (línea 92 en `comprime4mb.py`, 19 en `comprime19mb.py`): la API legacy `PdfFileReader`/`PdfFileWriter` fue eliminada en PyPDF2 3.0. El `pyproject.toml` ya fija `PyPDF2<3.0`; a mediano plazo migrar a `pypdf` (`from pypdf import PdfReader, PdfWriter`).

### 1.9 Fase de validación inconsistente con la de empacado
`comprime4mb.py:410` y `comprime19mb.py:227`: la validación previa no excluye `*.zip` (la fase de empacado sí, línea 485 / 275). Un ZIP residual de una ejecución anterior se lista en `Total Origen-<fecha>.txt` y, si superara el límite, abortaría el proceso. Unificar el filtro en ambas fases.

### 1.10 `Total Origen-<fecha>.txt` en modo append
Se abre con `"a"` por archivo (línea 436-438 / 242-244): acumula duplicados entre ejecuciones y abre/cierra el fichero en cada iteración. Abrir una vez con `with` en modo `"w"` al inicio de la validación.

## 2. Código muerto e imports

Detectable con `ruff check --select F401,F811,F841`:

- **Imports duplicados:** `shutil` dos veces en ambos (`comprime4mb.py:80, 84`; `comprime19mb.py:7, 11`).
- **Imports sin uso:** `filecmp` (solo en código comentado), `sys`, `time` (`time.sleep` comentado), `zipfile` (el empaquetado lo hace WinRAR), `PdfFileReader`/`PdfFileWriter`, y `msvcrt` (solo en `pause_execution()`, que tampoco recibe llamadas).
- **Variables sin uso:** `wrk_procesados`, `count_same_size` (`comprime4mb.py:483`), `limite1mb`, `limite2mb`, `limite500kb` (solo se usa `limite50kb`), `verif` inicializada sin necesidad, `text` en `validapdf()`.
- **Funciones muertas:** `pause_execution()` (llamadas comentadas), `validapdf()` (rota: depende de la global `file` y su bloque de llamada está comentado), `compare_file_sizes` (comentada).
- **Bloques comentados** (`FUNCIONES CON POSIBLE USO`, comandos viejos): documentan decisiones del algoritmo; trasladarlos a este documento o a docstrings y eliminarlos del código.

## 3. Rendimiento

### 3.1 `os.path.getsize` repetido
Se invoca decenas de veces por el mismo archivo: ordenamientos (línea 411 / 228), primer y segundo recorrido (272, 325 / 133, 169), escritura de `output.txt` (372 / 201). Medir cada tamaño una sola vez y guardar en un diccionario; idealmente usar `os.scandir()`, que entrega `stat()` sin syscalls extra:

```python
archivos = {}
with os.scandir(carpeta) as it:
    for entrada in it:
        if entrada.is_file():
            archivos[entrada.path] = entrada.stat().st_size
```

### 3.2 `rglob('*.*')` pierde archivos sin extensión
Pendiente ya documentado en el docstring de `comprime4mb.py`. `rglob('*.*')` no captura archivos sin punto en el nombre. Usar `rglob('*')` + `is_file()`.

### 3.3 Doble ordenamiento
Los archivos se ordenan ascendente a nivel de módulo (411 / 228) y de nuevo descendente dentro de `separate_files_by_size_optimized` (258 / 123). Eliminar uno de los dos.

### 3.4 First-fit decreciente es O(n·g)
Con muchos grupos, el bucle interior de búsqueda (288 / 146, 335 / 179) se vuelve costoso. Alternativa: *best-fit* con búsqueda binaria sobre las capacidades restantes (`bisect` sobre una lista ordenada), complejidad O(n log g).

### 3.5 Reempacado repetido
`empacar_archivos()` se dispara cada 11 grupos nuevos y re-comprime **todos** los grupos cuyo ZIP pese menos que `size_limit2`, incluidos los ya empacados en ciclos anteriores. Llevar un registro (set) de grupos ya empacados y saltarlos.

### 3.6 Proceso WinRAR por lote
Se lanza un proceso WinRAR por cada lote de 200 archivos: la sobrecarga de arranque domina con muchos lotes pequeños. Evaluar: lotes mayores (el docstring reporta ~300 estables), `-ibck`, y `-m0` (store, sin compresión) para archivos ya comprimidos (jpg, pdf, zip), que es donde más tiempo se pierde.

## 4. PEP 8 y estilo

- **Falta el guard principal:** todo el código a nivel de módulo se ejecuta al importar. Envolverlo en `def main():` + `if __name__ == "__main__": main()`.
- **Imports no agrupados** (estándar/terceros mezclados) y duplicados: orden PEP 8.
- **Líneas > 79 caracteres** (E501) y alineación con espacios arbitrarios (`arch_leidos          = 0`).
- **Mezcla de estilos de formateo:** concatenación con `+`, `.format()` y f-strings conviven (376 / 202). Unificar en f-strings.
- **Mensajes mezclando español e inglés** en `print`. Unificar idioma.
- **Comentarios desactualizados:** `comprime4mb.py:265` imprime `"PRIMER RECORRIDO ARCH >= limite2mb"` cuando el código compara con `limite50kb`.
- **`for i in range(len(groups)):` + indexado** → `for i, group in enumerate(groups)`, y usar `len(group)` en vez de `len(groups[iCnt])` cuando `group` ya está disponible (179 / 76).
- **`print` + escritura manual de bitácora** → usar el módulo `logging` con dos handlers (consola + archivo rotativo).
- **Ficheros sin context manager:** `doc = open(...); doc.write(...); doc.close()` en varios puntos; usar `with open(...) as doc:`.
- **Configuración editable en código:** `winrar_ruta`, límites y rutas de log como constantes modificables a mano → externalizar con `argparse` o variables de entorno.
- **Type hints ausentes** en firmas y variables clave.

## 5. Manejo de errores

- **`except:` desnudo** en `validapdf()` (229-232 / 104-107): captura todo, incluido `KeyboardInterrupt`. Capturar excepciones específicas (`pdfminer.pdfdocument.PDFSyntaxError`, `Exception` como mínimo) y registrar sin `quit()`.
- **Validar WinRAR al inicio:** `os.path.exists(winrar_ruta)` o `shutil.which("WinRAR.exe")` antes de empezar; abortar temprano con mensaje claro.
- **`os.unlink` sin try/except** (401-406 / 219-224): un archivo en uso (Excel/antivirus) lanza `PermissionError` y aborta todo. Capturar y registrar.
- **WinError 206 (ruta demasiado larga):** pendiente documentado. Mitigaciones: prefijo `\\?\` en rutas largas, nombres de ZIP más cortos, y mantener el empacado por lotes.
- **Archivos de bloqueo de Office:** los `~$*.xlsx` se leen (documentado en el docstring); excluir el patrón `~$*` si no deben procesarse.
- **Verificar `returncode` y `stderr` de WinRAR** y registrarlos en la bitácora (ver 1.7).

## 6. Refactorizaciones arquitectónicas

### 6.1 Unificar los dos scripts
`comprime4mb.py` y `comprime19mb.py` solo difieren en las constantes de tamaño. Extraer un módulo común con configuración por CLI y mantener entradas delgadas:

```python
# src/compresor.py — núcleo reutilizable
@dataclass
class Config:
    limite_grupo: int          # bytes
    limite_reempacado: int     # bytes
    limite_arch_origen: int    # bytes
    winrar_ruta: Path = Path(r"C:\winrar_ejecutable\WinRAR.exe")
    ...

def main(argv: list[str] | None = None) -> int:
    # argparse: --limite 4MB|19MB o valores en bytes
    ...
```

```python
# src/comprime4mb.py — entrada delgada
from compresor import Config, main
main(Config(limite_grupo=3_990_000, limite_reempacado=3_900_000, limite_arch_origen=4_200_000))
```

Esto elimina el riesgo clásico de que una corrección lógica se aplique a un script y no al otro.

### 6.2 Eliminar globals
Los contadores (`arch_leidos`, `arch_procesados`, `cuenta_nuevos_grupos`, `acumula_grupos`) mutados vía `global` se convierten en valores de retorno o en una clase de contexto (`GroupingState`). `ruta_arch` y `size_limit` se pasan como parámetros explícitos.

### 6.3 Separar responsabilidades
Funciones puras e independientes: descubrimiento de archivos, agrupamiento, empacado, registro de cifras. Facilita pruebas unitarias.

### 6.4 Tests
Con pytest: fixtures con `tmp_path` para árboles de datos pequeños, mock de `subprocess.run` (nunca invocar WinRAR real en CI) y aserciones sobre los grupos generados y los comandos construidos.

## 7. Prioridades sugeridas

| Prioridad | Hallazgo | Impacto | Esfuerzo |
|---|---|---|---|
| Alta | Guard `if __name__ == "__main__"` y prohibir import (1.1-1.7, §4) | Evita ejecuciones destructivas accidentales | Bajo |
| Alta | Crear `c:\SAT_logs` y validar WinRAR (1.2, §5) | Fallas a mitad de proceso | Bajo |
| Alta | `subprocess.run` con `check`/`-y`/timeout (1.7) | Colgadas y errores silenciosos | Bajo |
| Media | Unificar los dos scripts (6.1) | Doble mantenimiento | Medio |
| Media | Cachear tamaños y eliminar doble ordenamiento (3.1, 3.3) | Rendimiento | Bajo |
| Media | Sombreado de `file` y `quit()` (1.3, 1.4) | Estado corrupto, mensajes erróneos | Bajo |
| Baja | Limpieza de código muerto (§2) | Legibilidad | Bajo |
| Baja | Migrar PyPDF2 → pypdf (1.8) | Deuda técnica | Medio |
| Baja | Best-fit con `bisect` (3.4) | Rendimiento con muchos grupos | Medio |
