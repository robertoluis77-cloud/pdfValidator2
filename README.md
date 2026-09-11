# 📄 PDF QR Validator

Herramienta de **validación automatizada y recursiva** de archivos PDF y de los códigos QR contenidos en ellos, construida con **Playwright + TypeScript**. Incluye escaneo optimizado por zonas, compresión de PDFs con Ghostscript, análisis de legibilidad/parseo de PDFs (texto vs. imagen escaneada) y un conjunto de scripts Bash para mantenimiento de archivos.

---

## Tabla de contenidos

1. [Compatibilidad](#1-compatibilidad)
2. [Prerrequisitos](#2-prerrequisitos)
3. [Novedades y cambios recientes](#3-novedades-y-cambios-recientes)
4. [Instalación paso a paso](#4-instalación-paso-a-paso)
5. [Carga de archivos PDF en `./pdfs`](#5-carga-de-archivos-pdf-en-pdfs)
6. [Ejecución del proyecto](#6-ejecución-del-proyecto)
7. [Descripción de los archivos spec](#7-descripción-de-los-archivos-spec)
8. [Scripts `.sh` en `./pdfs`](#8-scripts-sh-en-pdfs)
9. [Solución de problemas comunes](#9-solución-de-problemas-comunes)
10. [Estructura del proyecto](#10-estructura-del-proyecto)

---

## 1. Compatibilidad

> ⚠️ **Nota de compatibilidad importante**
>
> Este proyecto **solo ha sido probado en un entorno Windows**. Aunque el código TypeScript y los scripts Bash son, en su mayor parte, portables, el flujo completo de trabajo (instalación de dependencias nativas como `pdf-to-img`/`jimp`, detección de Ghostscript `gswin64c`/`gswin32c`, uso de ImageMagick nativo de Windows, conversión de rutas Windows↔WSL, y desbloqueo de archivos con `Unblock-File`) está verificado únicamente sobre Windows.
>
> **Se recomienda encarecidamente ejecutar el proyecto en Windows** para garantizar estabilidad y evitar errores relacionados con la resolución de rutas y la detección de binarios externos. En Linux/macOS el proyecto puede funcionar, pero **no está garantizado** y no se ofrece soporte para esos sistemas operativos.

### 1.1 Detalles específicos de Windows

| Aspecto | Comportamiento en Windows |
|---------|---------------------------|
| Ghostscript | Se detecta como `gswin64c` / `gswin32c`, o escaneando `C:\Program Files\gs\...` y `C:\Program Files (x86)\gs\...`. Como último recurso usa `wsl gs`. |
| ImageMagick | Los scripts bash detectan `magick`/`convert` **verificando que realmente sea ImageMagick** (en Windows `convert.exe` suele ser la herramienta del sistema, no ImageMagick). |
| Scripts Bash | Deben ejecutarse desde **Git Bash** (o cualquier shell Bash compatible con Windows). |
| Archivos bloqueados | Los PDFs descargados de Internet pueden estar bloqueados por Windows; se resuelve con `unlock_files_recursive_this.sh`. |
| Rutas | Se usa `cygpath -w` para convertir rutas POSIX de Git Bash a rutas Win32 cuando un binario nativo de Windows lo requiere. |

---

## 2. Prerrequisitos

Antes de instalar o ejecutar **cualquier cosa**, asegúrate de tener instaladas todas las herramientas listadas a continuación. Saltarte una de estas dependencias puede provocar errores de ejecución, tests omitidos o scripts que fallan sin explicación aparente.

### 2.1 Herramientas de núcleo (obligatorias)

| Herramienta | Versión mínima | Propósito | ¿Obligatoria? |
|-------------|----------------|-----------|:---:|
| **Node.js** | 18 LTS o superior | Ejecutar el runtime y los tests | ✅ Sí |
| **npm** | 9 o superior | Instalar dependencias | ✅ Sí |
| **Ghostscript** | 10.x recomendada | Comprimir PDFs (`gswin64c` / `gswin32c` / `gs`) | ✅ Sí (para compresión) |
| **Git Bash** (o Bash) | — | Ejecutar los scripts `.sh` en `./pdfs` | ✅ Sí (para scripts) |

### 2.2 Herramientas externas auxiliares (según el script/test)

| Herramienta | Requerido por | Propósito | ¿Obligatoria? |
|-------------|---------------|-----------|:---:|
| **pdftotext** (paquete `poppler-utils`) | `check_if_pdf_has_images_this.sh` | Detectar si un PDF es escaneado (imagen) o vectorial (texto) | ⚠️ Solo para ese script |
| **ImageMagick** (`magick`/`convert`) | `convert_images_to_pdfs_recursive_this.sh` | Convertir imágenes JPG/PNG a PDF | ⚠️ Solo para ese script |
| **fdfind** / **fd** | `list_1M_PDF_large_files_fdfind_this.sh`, `listandoTipos.sh` | Búsqueda rápida de archivos | ⚠️ Solo para esos scripts |

### 2.3 Verificar instalación

```bash
# Node.js y npm
node --version
npm --version

# Ghostscript
gswin64c --version      # Windows
# gs --version          # Linux / macOS

# pdftotext (opcional)
pdftotext -v

# ImageMagick (opcional)
magick -version

# fdfind / fd (opcional)
fdfind --version        # o: fd --version
```

> ✅ **Ghostscript es la dependencia externa más importante.** El test de compresión (`compressPdfsThis.spec.ts`) y el script `compress_pdfs_this.sh` **dependen por completo de Ghostscript**. Si no está instalado, el test se **omite** (adjuntando `gs-diagnostics.txt`) y el script **aborta** con un error claro.

#### Instalar Ghostscript en Windows

```powershell
# Opción A — Chocolatey
choco install ghostscript

# Opción B — Scoop
scoop install ghostscript

# Opción C — Instalador manual
# Descarga desde: https://www.ghostscript.com/releases/gsdnld.html
```

> Durante la instalación manual, marca **"Add to PATH"**. Si Ghostscript no queda en el PATH, el proyecto igualmente lo detecta escaneando `C:\Program Files\gs\` y `C:\Program Files (x86)\gs\`.

#### Instalar Poppler / ImageMagick / fd (opcionales)

```powershell
# Poppler (pdftotext) — descarga para Windows desde:
# https://github.com/oschwartz10612/poppler-windows/releases

# ImageMagick — descarga desde:
# https://imagemagick.org/script/download.php#windows

# fd (fdfind) — Chocolatey o Scoop
choco install fd
# o
scoop install fd
```

---

## 3. Novedades y cambios recientes

Relación completa de funcionalidades y modificaciones incorporadas en los últimos días:

### 3.1 Nuevas funcionalidades

| # | Novedad | Detalle |
|---|---------|---------|
| 1 | **Nuevo spec de parseo/legibilidad** | `src/tests/pdfParserThis.spec.ts` valida que los PDFs sean legibles y parseables. Clasifica cada PDF como **"con texto"** (más de 50 caracteres extraídos) o **"con imagen"** (escaneado sin OCR), y adjunta métricas (`numpages`, `numrender`, metadatos e `info`, fragmento de `text`) al reporte. |
| 2 | **Archivos de resultados con timestamp** | El spec de parseo genera `textPDFs_<ts>.txt`, `imagePDFs_<ts>.txt` y `errorPDFs_<ts>.txt` en `./shellScriptResults/pdfParserResults/`. |
| 3 | **Detección automática de Ghostscript en Windows** | `findGhostscript()` ahora escanea también rutas de instalación conocidas de Windows (`C:\Program Files\gs\...`, `C:\Program Files (x86)\gs\...`), además de `gs`/`gswin64c`/`gswin32c` en el PATH y el fallback `wsl gs`. |
| 4 | **Nuevo perfil de compresión `12`** | `GS_PROFILE=12` usa el preset `/ebook` + downsampling bicúbico a 250 DPI (color/gris) y 200 DPI (mono). Los perfiles disponibles ahora son `2`, `12`, `3` y `4`. |
| 5 | **Nuevo script de listado de archivos no-PDF** | `pdfs/listandoTipos.sh` lista recursivamente todos los archivos que **no** son PDF, agrupados por extensión, usando `fdfind`/`fd`. |
| 6 | **Detección robusta de ImageMagick en Windows** | `convert_images_to_pdfs_recursive_this.sh` verifica que `magick`/`convert` invocados sean realmente ImageMagick (y no `convert.exe` del sistema Windows), e incluye rutas de instalación estándar de ImageMagick 7.x. |

### 3.2 Modificaciones y correcciones

| # | Cambio | Detalle |
|---|--------|---------|
| 1 | **Rutas de salida consolidadas** | Los scripts Bash ahora escriben sus resultados en un directorio compartido `./shellScriptResults/` (en lugar de dispersarlos). El spec de parseo usa `./shellScriptResults/pdfParserResults/`. |
| 2 | **Conversión imagen→PDF mejorada** | Se añadió redimensionamiento controlado (`-resize 1800x1800>`, `-strip`, JPEG calidad 80) para reducir tamaño sin perder legibilidad de texto ni QR. |
| 3 | **Compresión con reducción condicional** | El test `compressPdfsThis.spec.ts` **solo reemplaza el original si el archivo comprimido es más pequeño**; en caso contrario conserva el original y borra el temporal. |
| 4 | **Validación de QR estricta** | El contenido QR que no cumple el esquema Zod ahora **hace fallar el test** correspondiente (ya no se limita a un log de advertencia). |
| 5 | **Timeout guard en conversión PDF→imagen** | Se añadió una guarda de timeout (`withTimeout`) alrededor de `convertPdfToImages` para evitar tests colgados. |
| 6 | **Flujos de CI deshabilitados** | Los workflows de GitHub Actions (`.github/workflows/playwright.yml` y `copilot-setup-steps.yml`) están renombrados con extensión `.disabled` para evitar ejecuciones automáticas. |
| 7 | **Corrección de rutas relativas** | Los scripts y la salida por consola reportan las rutas de los PDFs empezando desde `./pdfs` (re-escritura de rutas absolutas a relativas). |
| 8 | **Carpeta de backups excluida** | `playwright.config.ts` ignora `src/tests/backups/` (versiones antiguas de specs). |

### 3.3 Cambios de configuración del reporter

El reporter HTML de Playwright ahora escribe en `test-results/` (`outputFolder: 'test-results'` en `playwright.config.ts`), y el proyecto de navegador activo es únicamente **Chromium** (`Desktop Chrome`).

---

## 4. Instalación paso a paso

### Requisitos previos

Verifica que tienes **Node.js 18+ (LTS)** y **npm 9+**:

```bash
node --version
npm --version
```

### Paso 1 — Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/pdf-qr-validator.git
cd pdf-qr-validator
```

### Paso 2 — Instalar dependencias de Node.js

```bash
npm install
```

Esto instala las dependencias declaradas en [`package.json`](package.json):

| Paquete | Propósito |
|---------|-----------|
| `@playwright/test` | Framework de pruebas y runner |
| `pdf-to-img` | Conversión de páginas PDF a imágenes PNG |
| `jsqr` | Decodificación de códigos QR |
| `jimp` | Manipulación de imágenes (recorte de zonas) |
| `zod` | Validación del contenido del QR mediante esquemas |
| `glob` | Búsqueda recursiva de archivos PDF |
| `pdf-parse` | Extracción de texto de PDFs (clase `PDFParse`, API v2) |
| `typescript` / `ts-node` | Compilación y ejecución de TypeScript |

> ⚠️ **Nota técnica:** `pdf-to-img` es un paquete **solo-ESM**. El proyecto se compila a *CommonJS* (`"module": "commonjs"` en `tsconfig.json`), por lo que el código lo carga mediante un *dynamic import* con `eval('import("pdf-to-img")')` en [`src/utils/pdfProcessor.ts`](src/utils/pdfProcessor.ts). **No** cambies este patrón por un `import` o `require` convencional.

> ⚠️ Si la instalación falla compilando módulos nativos (por `jimp`), consulta la sección [Error al instalar el paquete `canvas`](#-error-al-instalar-el-paquete-canvas-dependencia-de-jimp).

### Paso 3 — Instalar navegadores de Playwright

```bash
npx playwright install
```

> ⚠️ **Este paso es obligatorio.** Playwright necesita descargar el binario de Chromium para ejecutar los tests (el proyecto usa únicamente el proyecto `chromium`).

### Paso 4 — Verificar Ghostscript

```powershell
# Windows
gswin64c --version
```

Si no está instalado, consulta [Instalar Ghostscript en Windows](#instalar-ghostscript-en-windows). Sin Ghostscript, el test de compresión se **omitirá** y el script de compresión **abortará**.

### Paso 5 — Colocar tus PDFs en `./pdfs`

```bash
# Copiar un archivo individual
cp /ruta/a/mi/documento.pdf ./pdfs/

# Copiar todos los PDFs de un directorio
cp /ruta/origen/*.pdf ./pdfs/

# Copiar recursivamente una carpeta completa
cp -r /ruta/origen/carpeta/ ./pdfs/carpeta/
```

> Si los archivos descargados de Internet están bloqueados por Windows, ejecuta el script [`unlock_files_recursive_this.sh`](#unlock_files_recursive_thissh--desbloquear-archivos-windows).

---

## 5. Carga de archivos PDF en `./pdfs`

### 5.1 Estructura esperada del directorio

El directorio `./pdfs` es la fuente de datos del proyecto. Coloca aquí todos los PDFs que deseas procesar. El escaneo es **recursivo** y **no distingue mayúsculas/minúsculas** en la extensión (se incluyen `*.pdf`, `*.PDF`, `*.Pdf`, etc.):

```
pdfs/
├── facturas/
│   ├── enero/
│   │   ├── factura_001.pdf
│   │   └── factura_002.pdf
│   └── febrero/
│       └── factura_003.pdf
├── tickets/
│   └── ticket_compra.pdf
└── documento_suelto.pdf
```

### 5.2 Variable de entorno `PDFS_DIR`

Puedes cambiar la carpeta de PDFs sin modificar el código usando la variable de entorno `PDFS_DIR`:

```powershell
# Windows (PowerShell)
$env:PDFS_DIR = "C:\ruta\a\mis\pdfs"; npm test
```

```bash
# Linux / macOS
PDFS_DIR=/ruta/absoluta/a/mis/pdfs npm test
```

### 5.3 Permisos necesarios

Los archivos deben ser **legibles** por el proceso de Node.js. En Windows, desbloquear si provienen de Internet (ver [`unlock_files_recursive_this.sh`](#unlock_files_recursive_thissh--desbloquear-archivos-windows)).

---

## 6. Ejecución del proyecto

### 6.1 Comandos disponibles

```bash
# Ejecutar todos los tests en modo headless
npm test

# Modo UI interactivo con visor de Playwright
npm run test:ui

# Modo debug con inspector paso a paso
npm run test:debug

# Debugger de zonas QR (verifica que las regiones recortan correctamente)
# Uso: npx ts-node src/utils/zoneDebugger.ts <ruta-al-pdf>
npm run debug:zones -- <ruta-al-pdf>
```

### 6.2 Ejecutar un test específico

```bash
# Solo validación de QR
npx playwright test src/tests/pdfQrValidationThis.spec.ts

# Solo compresión de PDFs (perfil por defecto)
npx playwright test src/tests/compressPdfsThis.spec.ts

# Solo análisis de legibilidad/parseo
npx playwright test src/tests/pdfParserThis.spec.ts

# Compresión con perfil específico
GS_PROFILE=2  npx playwright test src/tests/compressPdfsThis.spec.ts
GS_PROFILE=12 npx playwright test src/tests/compressPdfsThis.spec.ts
GS_PROFILE=3  npx playwright test src/tests/compressPdfsThis.spec.ts
GS_PROFILE=4  npx playwright test src/tests/compressPdfsThis.spec.ts
```

> En PowerShell (Windows), para definir la variable de entorno en una sola línea usa `$env:GS_PROFILE = "3"; npx playwright test src/tests/compressPdfsThis.spec.ts`.

### 6.3 Ver el reporte HTML

```bash
npx playwright show-report
```

El reporte se genera en `test-results/` (configurado en `playwright.config.ts`).

### 6.4 Salida esperada

**Validación de QR:** en el reporte HTML encontrarás, por cada PDF procesado: número de páginas, QRs encontrados por página y zona, contenido decodificado y capturas en caso de error.

**Compresión:** por cada PDF se muestra la reducción de tamaño:

```
Processing: C:\...\factura_001.pdf
  ✓ SUCCESS 1245.30 KB -> 387.12 KB (68% less)
```

---

## 7. Descripción de los archivos spec

Los tests de Playwright viven en [`src/tests/`](src/tests/) y se ejecutan con `npm test`. Cada `.spec.ts` registra **un test por PDF** en tiempo de carga del módulo.

### 7.1 `pdfQrValidationThis.spec.ts` — Validación de QR en PDFs

**Qué hace:** escanea recursivamente todos los PDFs en `./pdfs`, convierte cada página a imagen PNG (`scale: 3`), recorta las zonas definidas en `SCAN_REGIONS` y decodifica cualquier QR con `jsqr`. El contenido se valida contra el esquema Zod configurado; **un QR con contenido inválido hace fallar el test**.

| Variable de entorno | Valor por defecto | Descripción |
|---------------------|-------------------|-------------|
| `PDFS_DIR` | `./pdfs` | Carpeta donde buscar PDFs (relativa al cwd) |

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `EXPECTED_QR_PER_PAGE` | `boolean` (`false`) | Si `true`, falla cuando una página no tiene QR |
| `USE_FULL_PAGE_FALLBACK` | `boolean` (`true`) | Si `true`, escanea la página completa si no encuentra QR en las zonas |
| `QR_VALIDATION_SCHEMA` | `ZodSchema` (`QrUrlSchema`) | Esquema Zod que debe cumplir el contenido del QR |
| `SCAN_REGIONS` | `Region[]` | Lista ordenada de zonas donde se busca el QR |

**Zonas predefinidas (`QR_REGIONS`)** — se definen como **porcentajes del tamaño de la página** (0.0–1.0), por lo que funcionan a cualquier resolución:

```
┌─────────────────────────────────────┐
│  topLeft (2%,2%)   │  topRight (70%,2%) │
│    28% × 23%       │    28% × 23%       │
├────────────────────┼────────────────────┤
│                    │ center (30%,30%)   │
│                    │   40% × 40%        │
├────────────────────┼────────────────────┤
│ bottomLeft (2%,75%)│ bottomRight (70%,75%) │
│    28% × 23%       │    28% × 23%  ← común │
└────────────────────┴────────────────────┘
   (adicionalmente: bottomCenter)
```

**Crear una zona personalizada:**

```typescript
const MI_ZONA: Region = {
  name: 'miZonaPersonalizada',
  x: 0.60,      // 60% desde la izquierda
  y: 0.80,      // 80% desde arriba
  width: 0.20,  // 20% del ancho total
  height: 0.15, // 15% del alto total
};
```

**Personalizar el esquema de validación:**

```typescript
// URL HTTPS (esquema por defecto)
const QrUrlSchema = z.string().url().startsWith('https://');

// UUID v4
const QrUuidSchema = z.string().uuid();

// Patrón de factura
const QrInvoiceSchema = z.string().regex(/^INV-\d{6}$/);
```

### 7.2 `compressPdfsThis.spec.ts` — Compresión de PDFs con Ghostscript

**Qué hace:** busca todos los PDFs recursivamente, los comprime con Ghostscript usando el perfil seleccionado y **solo reemplaza el original si la compresión es exitosa y más pequeña**. Genera artefactos `gs-compress-report.json` y `gs-compress-log.txt`.

| Variable de entorno | Valor por defecto | Descripción |
|---------------------|-------------------|-------------|
| `PDFS_DIR` | `./pdfs` | Carpeta donde buscar PDFs |
| `GS_PROFILE` | `'2'` | Perfil de compresión (`2`, `12`, `3`, `4`) |

**Perfiles de compresión disponibles** (definidos en `GS_PROFILES` en [`ghostscript.ts`](src/utils/ghostscript.ts)):

| Perfil | Descripción | Uso recomendado |
|--------|-------------|-----------------|
| `GS_PROFILE=2` *(default)* | Sin downsampling de monocromo; JPEG de alta calidad en color/gris; compresión de fuentes y páginas | Documentos mixtos: facturas, tickets, cartas porte |
| `GS_PROFILE=12` | Preset `/ebook` + downsampling bicúbico a 250 DPI (color/gris) y 200 DPI (mono) | Balance calidad/tamaño |
| `GS_PROFILE=3` | 200 DPI bicúbico en color/gris/mono | PDFs completamente escaneados (evita texto borroso) |
| `GS_PROFILE=4` | Sin tocar imágenes; comprime fuentes y elimina recursos no usados | PDFs con texto vectorial puro |

> Valores desconocidos de `GS_PROFILE` caen silenciosamente al perfil `'2'`.

**Notas importantes:**
- El original se reemplaza solo si el resultado es **más pequeño** que el original.
- Usa un temporal `.tmp_compressed_<timestamp>_<nombre>.pdf` y un `renameSync` atómico.
- Timeout de 2 minutos por archivo (`test.setTimeout(120000)`).
- Si Ghostscript no se encuentra, el test **se omite** y adjunta `gs-diagnostics.txt`.

### 7.3 `pdfParserThis.spec.ts` — Análisis de legibilidad y parseo

**Qué hace:** recorre todos los PDFs y, con la API v2 de `pdf-parse` (clase `PDFParse`), extrae métricas y clasifica cada documento:

- **`numpages`**: total de páginas (devuelto por `getInfo()` como `total`).
- **`numrender`**: páginas efectivamente procesadas por `getText()`.
- **`info`**: metadatos del documento (Título, Autor, Productor, Fecha de creación, etc.).
- **`text`**: primeros 50 caracteres del texto extraído.

Si un PDF tiene **más de 50 caracteres** de texto extraíble se clasifica como **"PDF con texto"**; en caso contrario como **"PDF con imagen"** (escaneado sin OCR). Los errores de parseo se registran **sin** interrumpir el resto de archivos.

**Archivos de resultados** (generados en `./shellScriptResults/pdfParserResults/` con timestamp `YYYYMMDD_HHmmss`):

| Archivo | Contenido |
|---------|-----------|
| `textPDFs_<ts>.txt` | PDFs con texto extraíble |
| `imagePDFs_<ts>.txt` | PDFs de solo imagen (escaneados) |
| `errorPDFs_<ts>.txt` | PDFs que fallaron al parsear |

### 7.4 `testHelpers.ts` — Utilidades compartidas

Captura `console.log` durante cada test y lo adjunta al reporte de Playwright vía `startConsoleCapture()` / `restoreConsoleCapture()`. Se usa en los `beforeEach`/`afterEach` de cada spec.

---

## 8. Scripts `.sh` en `./pdfs`

Dentro de `./pdfs/` hay scripts Bash para mantenimiento de archivos. **Se ejecutan desde Git Bash (Windows) o cualquier terminal Bash (Linux/macOS).**

> ⚠️ **Importante:** los scripts deben ejecutarse desde dentro del directorio `./pdfs/` (o con la ruta relativa correspondiente). Por defecto operan sobre el directorio donde residen, y escriben sus resultados en `./shellScriptResults/` (o en el mismo directorio según el script).

### 8.1 `check_if_pdf_has_images_this.sh` — Detectar PDFs escaneados

Determina si cada PDF es **parseable** (texto vectorial) o **escaneado** (solo imágenes), usando `pdftotext`.

**Requisito:** `pdftotext` (paquete `poppler-utils`).

```bash
cd pdfs
bash check_if_pdf_has_images_this.sh
```

**Salida:** imprime el tipo de cada PDF y genera `listado_PDFs_imagenes_<YYYY-MM-DD HH:MM:SS>.txt`.

### 8.2 `compress_pdfs_this.sh` — Comprimir PDFs con Ghostscript

Comprime recursivamente todos los PDFs usando Ghostscript (perfil de calidad similar al `GS_PROFILE=2`) y reemplaza el original solo si la compresión es exitosa.

> ⚠️ Para la mayoría de los casos se recomienda usar `npx playwright test src/tests/compressPdfsThis.spec.ts`, que ofrece múltiples perfiles y mejor reporte.

**Requisito:** Ghostscript (`gs`, `gswin64c` o `gswin32c` en el PATH).

```bash
cd pdfs
bash compress_pdfs_this.sh
```

**Salida:** genera `gs_exex_log_<YYYY-MM-DD HH:MM:SS>.txt` con tamaños antes/después.

### 8.3 `convert_images_to_pdfs_recursive_this.sh` — Imágenes → PDF

Convierte recursivamente todos los `.jpg`/`.jpeg`/`.png` a PDF usando ImageMagick a 150 DPI. **Elimina la imagen original** tras una conversión exitosa.

**Requisito:** ImageMagick (`magick` o `convert` real).

```bash
cd pdfs
bash convert_images_to_pdfs_recursive_this.sh
```

**Salida:** genera `images_to_pdf_log_<timestamp>.txt` en `../test-results/shellScriptResults/`.

> ⚠️ El script elimina las imágenes originales. Haz una copia de respaldo antes de ejecutarlo.

### 8.4 `list_1M_PDF_large_files_this.sh` — Listar PDFs mayores a 1 MB

Lista los PDFs mayores a 1 MB y sus tamaños.

```bash
cd pdfs
bash list_1M_PDF_large_files_this.sh
```

**Salida:** genera `../shellScriptResults/listado_PDFs_1M_<timestamp>.txt`.

### 8.5 `list_1M_PDF_large_files_fdfind_this.sh` — Listar PDFs > 1 MB con `fdfind`

Variante del anterior usando `fdfind`/`fd` (más rápida en directorios grandes), ordenada por tamaño.

**Requisito:** `fdfind` o `fd` instalado.

```bash
cd pdfs
bash list_1M_PDF_large_files_fdfind_this.sh
```

### 8.6 `list_4MB_large_files_this.sh` — Listar archivos mayores a 4 MB

Lista **todos** los archivos (no solo PDFs) de 4 MB o más.

```bash
cd pdfs
bash list_4MB_large_files_this.sh
```

**Salida:** genera `../shellScriptResults/archivos_4M_<timestamp>.txt`.

### 8.7 `unlock_files_recursive_this.sh` — Desbloquear archivos (Windows)

Usa `Unblock-File` (PowerShell) para desbloquear recursivamente todos los PDFs bloqueados por Windows.

**Requisito:** Windows con `powershell.exe` en el PATH.

```bash
cd pdfs
bash unlock_files_recursive_this.sh
```

**Salida:** genera `unlockedFiles_log<YYYY-MM-DD HH:MM>.txt`.

### 8.8 `listandoTipos.sh` — Listar archivos que NO son PDF

Lista recursivamente todos los archivos que **no** tienen extensión `.pdf` (ni `.sh`), agrupados por extensión, usando `fdfind`/`fd`.

**Requisito:** `fdfind` o `fd` instalado.

```bash
cd pdfs
bash listandoTipos.sh
```

**Salida:** imprime el listado y resumen por extensión, y guarda `../shellScriptResults/tiposArchivos_<YYYYMMDD_HHMMSS>.txt`.

---

## 9. Solución de problemas comunes

### ⚠️ Ghostscript no encontrado al ejecutar el test de compresión

**Síntoma:**
```
Test skipped: Ghostscript not found on PATH (diagnostics attached to beforeAll)
```

**Causa:** `gs` / `gswin64c` / `gswin32c` no está en el PATH, ni en las rutas de instalación de Windows escaneadas.

**Solución:** instala Ghostscript (ver [Instalar Ghostscript en Windows](#instalar-ghostscript-en-windows)) y verifica:

```powershell
gswin64c --version
```

### ⚠️ QR no detectado en ninguna zona del PDF

1. **Resolución demasiado baja:** aumenta el `scale` en [`pdfProcessor.ts`](src/utils/pdfProcessor.ts) (actualmente `scale: 3` en el spec de QR; el valor por defecto de la utilidad es `2.5`):
   ```typescript
   const pages = await convertPdfToImages(pdfPath, { scale: 4 });
   ```
2. **Zona mal configurada:** corre el debug de zonas para inspeccionar las regiones:
   ```bash
   npm run debug:zones -- /ruta/al/pdf.pdf
   ```
   Esto guarda imágenes recortadas en `./debug-zones/`.
3. **QR muy pequeño o de baja calidad:** usa `USE_FULL_PAGE_FALLBACK = true` mientras ajustas las zonas.

### ⚠️ PDFs mal formados o corruptos al comprimir

```bash
# Verificar con pdfinfo (requiere poppler-utils)
pdfinfo archivo.pdf

# Reparar con Ghostscript directamente
gswin64c -sDEVICE=pdfwrite -dNOPAUSE -dBATCH -dQUIET ^
   -sOutputFile=archivo_reparado.pdf archivo.pdf
```

### ⚠️ Error al instalar el paquete `canvas` (dependencia de `jimp`)

**Síntoma:** `npm ERR! gyp ERR! build error`.

**Solución (Windows, como administrador):**

```powershell
npm install -g windows-build-tools
```

En Linux/macOS: instalar `build-essential libcairo2-dev libpango1.0-dev` (Linux) o `xcode-select --install` (macOS).

### ⚠️ Archivos PDF bloqueados en Windows (acceso denegado)

```bash
cd pdfs
bash unlock_files_recursive_this.sh
```

O manualmente:

```powershell
Get-ChildItem -Path ".\pdfs" -Recurse -Filter "*.pdf" | Unblock-File
```

### ⚠️ PDFs comprimidos salen borrosos

Cambia al perfil de compresión adecuado:

```powershell
# Escaneados (todo imagen): 200 DPI
$env:GS_PROFILE = "3"; npx playwright test src/tests/compressPdfsThis.spec.ts

# Texto vectorial: sin tocar imágenes
$env:GS_PROFILE = "4"; npx playwright test src/tests/compressPdfsThis.spec.ts
```

### ⚠️ Error `require() cannot be used on an ESM graph with top-level await`

**Causa:** `pdf-to-img` es ESM-only y el proyecto compila a CommonJS. El código ya usa el workaround `eval('import("pdf-to-img")')`. **No lo cambies.** Si aparece este error, revisa que [`pdfProcessor.ts`](src/utils/pdfProcessor.ts) mantenga ese patrón.

---

## 10. Estructura del proyecto

```
pdf-qr-validator/
│
├── src/
│   ├── utils/
│   │   ├── fileScanner.ts          # Escaneo recursivo de PDFs en ./pdfs
│   │   ├── pdfProcessor.ts         # Conversión de páginas PDF a imágenes PNG
│   │   ├── qrValidator.ts          # Recorte por zonas y decodificación de QR
│   │   ├── ghostscript.ts          # Wrapper para invocar Ghostscript + perfiles
│   │   └── zoneDebugger.ts         # Guarda imágenes de zonas recortadas
│   │
│   ├── tests/
│   │   ├── pdfQrValidationThis.spec.ts   # Validación de QR
│   │   ├── compressPdfsThis.spec.ts      # Compresión con Ghostscript
│   │   ├── pdfParserThis.spec.ts         # Legibilidad/parseo (texto vs. imagen)
│   │   ├── testHelpers.ts                # Captura de logs de consola
│   │   └── backups/                      # Versiones anteriores (ignoradas por Playwright)
│   │
│   └── bashScripts/
│       ├── compress_pdfs_this.sh         # Copia de referencia del script de compresión
│       └── gsParametersPerfiles.md       # Documentación de perfiles Ghostscript
│
├── pdfs/                             # ← Coloca aquí tus PDFs
│   ├── check_if_pdf_has_images_this.sh
│   ├── compress_pdfs_this.sh
│   ├── convert_images_to_pdfs_recursive_this.sh
│   ├── list_1M_PDF_large_files_this.sh
│   ├── list_1M_PDF_large_files_fdfind_this.sh
│   ├── list_4MB_large_files_this.sh
│   ├── listandoTipos.sh
│   └── unlock_files_recursive_this.sh
│
├── specs/                            # Planes de prueba y especificaciones
├── tests/                            # Tests adicionales (exploración)
├── shellScriptResults/               # Resultados generados por los scripts Bash
├── test-results/                     # Reporte HTML de Playwright (reporter)
│
├── playwright.config.ts              # Configuración de Playwright
├── tsconfig.json                     # Configuración de TypeScript (CommonJS)
├── package.json                      # Dependencias y scripts npm
├── AGENTS.md                         # Instrucciones para agentes de IA
└── README.md                         # Este archivo
```

---

> 📌 **Referencia rápida de comandos:**
>
> ```bash
> npm install                          # Instalar dependencias
> npx playwright install               # Instalar navegador Chromium
> npm test                             # Ejecutar todos los tests
> npm run test:ui                      # Modo UI interactivo
> npx playwright show-report           # Ver reporte HTML
> GS_PROFILE=3 npm test               # Perfil de compresión para escaneados
> PDFS_DIR=/ruta/pdfs npm test        # Carpeta de PDFs personalizada
> npm run debug:zones -- ./pdfs/archivo.pdf   # Debug de zonas QR
> ```