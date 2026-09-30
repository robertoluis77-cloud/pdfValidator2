# compressionWinRAR

Herramienta de escritorio para **Windows** que empaca por lotes el contenido de carpetas en archivos **ZIP** generados con **WinRAR**, dividiendo los archivos en grupos que respetan un límite de tamaño configurable (4 MB o 19 MB según el perfil seleccionado).

## Propósito

El proyecto automatiza el empacado de árboles de carpetas (documentos, PDF, XML, imágenes, etc.) en archivos ZIP de tamaño acotado. Es útil cuando un sistema destino impone un tamaño máximo por archivo o por lote (por ejemplo, cargas masivas de documentación).

Por cada carpeta de trabajo, el proceso:

1. Elimina los archivos auxiliares `*.db` y `*.ini` del árbol.
2. Valida que ningún archivo individual supere `limite_arch_origen` (aborta si existe alguno).
3. Genera un listado de origen (`Total Origen-<fecha>.txt`).
4. Agrupa los archivos con el algoritmo *first-fit decreciente* en dos recorridos:
   - **Primer recorrido:** archivos con tamaño ≥ 50 KB.
   - **Segundo recorrido:** archivos de 0 a 50 KB, insertados en los grupos ya creados.
5. Empaca cada grupo en un ZIP (`<carpeta>-NNNN.zip`) invocando `WinRAR.exe`, en ciclos de empacado intermedios cada 11 grupos nuevos y una compresión final.
6. Registra cifras de control (archivos leídos, procesados y suma por grupo) en `c:\SAT_logs\Log-<fecha>.txt`.

## Cambios de comportamiento respecto a los scripts originales

- **Exclusión de carpetas `tempo*`:** ahora se ignoran explícitamente (en los scripts originales el código estaba presente pero no tenía efecto).
- **Exclusión de archivos `~$*.*`:** se omiten los archivos de bloqueo de Office (antes se leían, causando posibles conflictos).
- **Inclusión de archivos sin extensión:** antes se perdían al usar el patrón `*.*`; ahora se encuentran con `*.*`.
- **Validación temprana de WinRAR:** se verifica la existencia de `WinRAR.exe` al inicio y se aborta con mensaje claro si falta.
- **Creación automática de la carpeta de logs:** si `c:\SAT_logs` no existe, se crea antes de escribir el archivo de log.
- **Manejo de rutas largas:** se usa el prefijo `\\\\?\\` para evitar `WinError 206` (nombre de archivo o extensión demasiado largo).
- **Salida determinista y segura:** el empacado intermedio ya no vuelve a comprimir innecesariamente grupos ya empacados y sin cambios.
- **Dependencias actualizadas:** ya no se requieren `PyPDF2` ni `pdfminer.six` (el código de validación de PDF estaba muerto y fue eliminado).

## Estructura del proyecto

```
├── .venv/                  # Entorno virtual (no modificar)
├── src/                    # Código fuente de la aplicación
│   └── compresor.py        # Script unificado (perfil 4 MB o 19 MB según argumento --limite)
├── .gitignore              # Excluye .venv/ y artefactos generados
├── pyproject.toml          # Configuración y dependencias del proyecto
├── README.md               # Documentación del proyecto
└── sugerencias.md          # Análisis técnico y recomendaciones de mejora (se implementaron en compresor.py)
```

## Requisitos previos

- **Windows** (el script usa `msvcrt` indiretamente vía la consola, pero el núcleo es portable; sin embargo, WinRAR es obligatorio).
- **Python 3.8 o superior.**
- **WinRAR** instalado en `C:\winrar_ejecutable\WinRAR.exe` (valor por defecto de `winrar_ruta`; ajústelo con `--winrar` si su ruta difiere).
- No se requiere crear previamente la carpeta `c:\SAT_logs`: el script la crea automáticamente si falta.

## Guía de instalación (paso a paso)

1. **Abrir una terminal en la raíz del proyecto** (`C:\githubProjects\python\compressionWinRAR`).

2. **Crear el entorno virtual.** Recomendado con el módulo estándar `venv`:

   ```powershell
   py -m venv .venv
   ```

   Si `py` no está disponible, use directamente su intérprete de Python:

   ```powershell
   python -m venv .venv
   ```

3. **Activar el entorno virtual:**

   - **PowerShell:**

     ```powershell
     .venv\Scripts\Activate.ps1
     ```

     Si PowerShell bloquea la ejecución de scripts, habilítela solo para su usuario:

     ```powershell
     Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
     ```

   - **Símbolo del sistema (CMD):**

     ```cmd
     .venv\Scripts\activate.bat
     ```

   - **Git Bash:**

     ```bash
     source .venv\Scripts\activate
     ```

   Al activarse, el prompt mostrará el prefijo `(.venv)`.

4. **Actualizar pip (recomendado):**

   ```powershell
   python -m pip install --upgrade pip
   ```

5. **Instalar dependencias del proyecto** declaradas en `pyproject.toml` (en este caso, ninguna dependencia de ejecución; solo opcionales para desarrollo):

   ```powershell
   pip install -e .   # instala el proyecto en modo editable (útil para desarrollo)
   ```

   O bien, si solo desea asegurar que el entorno tenga las herramientas de desarrollo sugeridas:

   ```powershell
   pip install -e .[dev]   # instala pytest, ruff y black además del proyecto
   ```

   Dado que el script unificado no tiene dependencias de ejecución, `pip install -e .` simplemente registra el proyecto localmente; no instala paquetes externos. Las herramientas de desarrollo (pytest, ruff, black) están disponibles en el extra `[dev]`.

6. **Verificar la instalación del script:**

   ```powershell
   python -c "import compresor; print('Import OK')"
   ```

   Debe imprimir `Import OK` sin errores.

## Ejecución del script unificado

> **Importante:** el script opera sobre las **subcarpetas del directorio de trabajo actual** (`wrkdir = '.'` por defecto). Ejécútelo desde una carpeta que contenga únicamente las carpetas de datos a empacar, **no** desde la raíz del proyecto (de lo contrario procesaría `src/`, `venv/` u otras carpetas, y eliminaría los `.db`/`.ini` que contengan). Las carpetas cuyo nombre empieza con `tempo` se ignoran.

```powershell
# Perfil de 4 MB por grupo ZIP (grupo ≤ 3.990.000 bytes)
python src\compresor.py --limite 4mb

# Perfil de 19 MB por grupo ZIP (grupo ≤ 19.922.944 bytes)
python src\compresor.py --limite 19mb
```

### Opciones de línea de comandos

| Opción | Descripción | Valor por defecto |
|---|---|---|
| `--limite` | Perfil de tamaño de grupo: `4mb` o `19mb` | `4mb` |
| `--winrar` | Ruta completa a `WinRAR.exe` | `C:\winrar_ejecutable\WinRAR.exe` |
| `--log-dir` | Carpeta donde se escribirá el archivo de log `Log-<fecha>.txt` | `c:\SAT_logs` |
| `--dir` | Directorio de trabajo que contiene las subcarpetas a empacar | `.` (directorio actual) |
| `--max-files` | Número máximo de archivos por lote de WinRAR (para evitar WinError 206) | `200` |
| `--dry-run` | Ejecuta en modo simulación: muestra lo que haría sin eliminar archivos ni ejecutar WinRAR | desactivado |

Ejemplo avanzado (sobrescribiendo múltiples opciones):

```powershell
python src\compresor.py --limite 19mb --winrar "D:\Programas\WinRAR\WinRAR.exe" --log-dir "D:\Logs" --dir "D:\Datos" --max-files 100
```

## Archivos generados

| Archivo | Descripción |
|---|---|
| `<carpeta>-NNNN.zip` | ZIP final de cada grupo (WinRAR, nivel de compresión 3, 4 hilos). |
| `output.txt` | Listado `ruta\|grupo\|tamaño` de todos los archivos agrupados (sobrescrito por carpeta procesada). |
| `Total Origen-<fecha>.txt` | Listado de archivos origen validados (ordenados por tamaño ascendente). |
| `c:\SAT_logs\Log-<fecha>.txt` | Bitácora con cifras de control de la ejecución (marcas de tiempo, progreso y resúmenes). |

## Advertencias

- El proceso es **destructivo**: borra `*.db` y `*.ini` de forma recursiva y sobrescribe los ZIP previos de las carpetas procesadas.
- Use `--dry-run` para una prueba segura antes de la ejecución real.
- Con árboles de rutas muy largas puede aparecer `FileNotFoundError: [WinError 206]` (nombre de archivo o extensión demasiado largo); el empacado por lotes de 200 archivos mitiga este error, y el script usa internamente el prefijo `\\\\?\\` cuando es necesario.

## Documentación adicional

- [`sugerencias.md`](sugerencias.md): análisis técnico del código original con recomendaciones de rendimiento, buenas prácticas PEP 8, manejo de errores y refactorizaciones. La mayoría de estas sugerencias han sido implementadas en el script unificado `src/compresor.py`.