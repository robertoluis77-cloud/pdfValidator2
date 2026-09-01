# 📄 PDF QR Validator

Herramienta de **validación automatizada y recursiva** de archivos PDF y los códigos QR contenidos en ellos, construida con **Playwright + TypeScript**. Incluye escaneo optimizado por zonas, compresión de PDFs con Ghostscript y un conjunto de scripts Bash para mantenimiento de archivos.

---

## Tabla de contenidos

1. [Descripción general del proyecto](#1-descripción-general-del-proyecto)
2. [Instalación de dependencias del sistema](#2-instalación-de-dependencias-del-sistema)
3. [Instalación de dependencias del proyecto](#3-instalación-de-dependencias-del-proyecto)
4. [Carga de archivos PDF en `./pdfs`](#4-carga-de-archivos-pdf-en-pdfs)
5. [Instalación y configuración del proyecto](#5-instalación-y-configuración-del-proyecto)
6. [Ejecución del proyecto](#6-ejecución-del-proyecto)
7. [Descripción de los archivos spec](#7-descripción-de-los-archivos-spec)
8. [Scripts `.sh` en `./pdfs`](#8-scripts-sh-en-pdfs)
9. [Solución de problemas comunes](#9-solución-de-problemas-comunes)
10. [Estructura del proyecto](#10-estructura-del-proyecto)

---

## 1. Descripción general del proyecto

**PDF QR Validator** es una suite de pruebas automatizadas que resuelve dos necesidades frecuentes en flujos de trabajo con documentos PDF:

- **Validación de códigos QR**: Escanea recursivamente todos los PDFs de una carpeta, convierte cada página a imagen, recorta regiones de interés (zonas definidas como porcentajes de la página) y decodifica cualquier código QR presente. El contenido del QR se valida contra un esquema [Zod](https://zod.dev/) configurable (p. ej., que sea una URL HTTPS, un UUID, etc.).

- **Compresión de PDFs**: Comprime recursivamente archivos PDF utilizando Ghostscript con perfiles de calidad/tamaño configurables. Reporta el ahorro en bytes por archivo y genera artefactos JSON y de texto adjuntos al reporte de Playwright.

### Casos de uso

| Caso de uso | Herramienta |
|-------------|------------|
| Verificar que facturas o tickets tienen QR válidos | `pdfQrValidationThis.spec.ts` |
| Reducir el tamaño de lotes de PDFs escaneados | `compressPdfsThis.spec.ts` |
| Detectar si un PDF es vectorial o de imagen | `check_if_pdf_has_images_this.sh` |
| Convertir imágenes JPG/PNG a PDF en lote | `convert_images_to_pdfs_recursive_this.sh` |
| Auditar archivos pesados en el directorio de PDFs | `list_1M_PDF_large_files_this.sh` |

---

## 2. Instalación de dependencias del sistema

### 2.1 Ghostscript (`gs`)

Ghostscript es necesario para comprimir PDFs. El proyecto lo detecta automáticamente bajo los nombres `gs`, `gswin64c` y `gswin32c`.

#### 🐧 Linux (Debian / Ubuntu)

```bash
sudo apt-get update
sudo apt-get install -y ghostscript
```

#### 🐧 Linux (RHEL / CentOS / Fedora)

```bash
# Fedora / RHEL 8+
sudo dnf install -y ghostscript

# CentOS 7 / RHEL 7
sudo yum install -y ghostscript
```

#### 🍎 macOS (Homebrew)

```bash
brew install ghostscript
```

> Si no tienes Homebrew instalado: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`

#### 🪟 Windows (Chocolatey)

```powershell
choco install ghostscript
```

#### 🪟 Windows (instalador manual)

Descarga el instalador oficial desde:
`https://ghostscript.readthedocs.io/en/latest/Install.html`

Durante la instalación, asegúrate de marcar la opción **"Add to PATH"** para que `gswin64c` esté disponible en la terminal.

#### ✅ Verificar instalación

```bash
# Linux / macOS
gs --version

# Windows (CMD o PowerShell)
gswin64c --version
```

La salida debe mostrar la versión instalada, p. ej.: `10.03.1`

---

### 2.2 Poppler (`pdftotext`) — opcional

Requerido únicamente por el script `check_if_pdf_has_images_this.sh` para detectar si un PDF es escaneado o vectorial.

```bash
# Ubuntu / Debian
sudo apt-get install -y poppler-utils

# macOS
brew install poppler

# Windows: descarga desde https://github.com/oschwartz10612/poppler-windows/releases
```

---

### 2.3 ImageMagick — opcional

Requerido únicamente por el script `convert_images_to_pdfs_recursive_this.sh`.

```bash
# Ubuntu / Debian
sudo apt-get install -y imagemagick

# macOS
brew install imagemagick

# Windows (Chocolatey)
choco install imagemagick
```

---

## 3. Instalación de dependencias del proyecto

### Requisitos previos

| Herramienta | Versión mínima recomendada |
|-------------|--------------------------|
| Node.js     | 18 LTS o superior        |
| npm         | 9 o superior             |

Verifica tu versión de Node.js:

```bash
node --version
npm --version
```

### Instalar dependencias de Node.js

```bash
npm install
```

Este comando instala todas las dependencias declaradas en [`package.json`](package.json), incluyendo:

| Paquete | Propósito |
|---------|-----------|
| `@playwright/test` | Framework de pruebas y runner |
| `pdf-to-img` | Conversión de páginas PDF a imágenes PNG |
| `jsqr` | Decodificación de códigos QR |
| `jimp` | Manipulación de imágenes (recorte de zonas) |
| `zod` | Validación del contenido del QR mediante esquemas |
| `glob` | Búsqueda recursiva de archivos PDF |
| `pdf-parse` | Extracción de texto de PDFs vectoriales |
| `typescript` / `ts-node` | Compilación y ejecución de TypeScript |

### Instalar navegadores de Playwright

```bash
npx playwright install
```

> ⚠️ Este paso es obligatorio. Playwright necesita descargar los binarios del navegador (Chromium, Firefox, WebKit) para ejecutar los tests.

---

## 4. Carga de archivos PDF en `./pdfs`

### 📁 Estructura esperada del directorio

El directorio `./pdfs` es la fuente de datos del proyecto. Coloca aquí todos los archivos PDF que deseas procesar. El escaneo es **recursivo**: se procesan PDFs en subcarpetas de cualquier profundidad.

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

### Copiar archivos al directorio

```bash
# Copiar un archivo individual
cp /ruta/a/mi/documento.pdf ./pdfs/

# Copiar todos los PDFs de un directorio
cp /ruta/origen/*.pdf ./pdfs/

# Copiar recursivamente una carpeta completa
cp -r /ruta/origen/carpeta/ ./pdfs/carpeta/
```

### Variable de entorno `PDFS_DIR`

Puedes cambiar la carpeta de PDFs sin modificar el código usando la variable de entorno `PDFS_DIR`:

```bash
# Linux / macOS
PDFS_DIR=/ruta/absoluta/a/mis/pdfs npm test

# Windows (PowerShell)
$env:PDFS_DIR = "C:\ruta\a\mis\pdfs"; npm test
```

### Permisos necesarios

Los archivos deben ser **legibles** por el proceso de Node.js. En Linux/macOS:

```bash
# Dar permisos de lectura a todos los PDFs del directorio
chmod -R 644 ./pdfs/*.pdf
```

En Windows, si los archivos descargados de internet aparecen bloqueados, usa el script [`unlock_files_recursive_this.sh`](#unlock_files_recursive_thissh--desbloquear-archivos-windows) incluido en el proyecto.

---

## 5. Instalación y configuración del proyecto

### Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/pdf-qr-validator.git
cd pdf-qr-validator
```

### Instalación completa paso a paso

```bash
# 1. Instalar dependencias de Node.js
npm install

# 2. Instalar navegadores de Playwright
npx playwright install

# 3. Verificar Ghostscript (necesario para compresión)
gs --version        # Linux / macOS
gswin64c --version  # Windows

# 4. Colocar tus PDFs en la carpeta ./pdfs
cp /ruta/a/tus/pdfs/*.pdf ./pdfs/
```

### Configuración de los tests

Los parámetros de comportamiento se configuran directamente en el archivo de test correspondiente. No se requiere archivo `.env` para el funcionamiento básico.

#### Parámetros en [`src/tests/pdfQrValidationThis.spec.ts`](src/tests/pdfQrValidationThis.spec.ts)

```typescript
// ¿Cada página DEBE tener un QR? (falla el test si no lo encuentra)
const EXPECTED_QR_PER_PAGE = false;

// ¿Intentar página completa si no se encuentra en zonas?
const USE_FULL_PAGE_FALLBACK = true;

// Esquema Zod para validar el contenido del QR
const QR_VALIDATION_SCHEMA = QrUrlSchema;

// Zonas donde se busca el QR (en orden de prioridad)
const SCAN_REGIONS = [
  QR_REGIONS.bottomRight,   // Esquina inferior derecha (más común)
  QR_REGIONS.topRight,      // Esquina superior derecha
  QR_REGIONS.bottomLeft,    // Esquina inferior izquierda
];
```

#### Variable de entorno para compresión

```bash
# Perfil de compresión (1 = calidad alta, 2 = máxima compresión legible [default], 3 = escaneados, 4 = texto vectorial)
GS_PROFILE=2
```

---

## 6. Ejecución del proyecto

### Comandos disponibles

```bash
# Ejecutar todos los tests en modo headless (recomendado para CI/CD)
npm test

# Modo UI interactivo con visor de Playwright
npm run test:ui

# Modo debug con inspector paso a paso
npm run test:debug

# Debugger de zonas QR (verifica que las regiones recortan correctamente)
npm run debug:zones
```

### Ejecutar un test específico

```bash
# Solo validación de QR
npx playwright test src/tests/pdfQrValidationThis.spec.ts

# Solo compresión de PDFs (perfil por defecto)
npx playwright test src/tests/compressPdfsThis.spec.ts

# Compresión con perfil para PDFs escaneados (200 DPI)
GS_PROFILE=3 npx playwright test src/tests/compressPdfsThis.spec.ts

# Compresión para texto vectorial (sin tocar imágenes)
GS_PROFILE=4 npx playwright test src/tests/compressPdfsThis.spec.ts
```

### Ver el reporte HTML

```bash
npx playwright show-report
```

### Salida esperada (validación de QR)

```
Running 1 test using 1 worker

  ✓  pdfQrValidationThis › validates QR codes in all PDFs (12.3s)

  1 passed (13s)
```

En el reporte HTML encontrarás, por cada PDF procesado:
- Número de páginas analizadas
- QRs encontrados por página y zona
- Contenido decodificado de cada QR
- Capturas de pantalla en caso de error

### Salida esperada (compresión)

```
→ Procesando: facturas/factura_001.pdf
  ✓ 1 245.30 KB → 387.12 KB (68% menos)
→ Procesando: tickets/ticket_compra.pdf
  ✓ 540.00 KB → 201.44 KB (62% menos)
```

---

## 7. Descripción de los archivos spec

Los tests de Playwright viven en [`src/tests/`](src/tests/) y se ejecutan con el comando `npm test`. Cada archivo `.spec.ts` es un test independiente que puede ejecutarse por separado.

---

### `pdfQrValidationThis.spec.ts` — Validación de QR en PDFs

**Qué hace:** Escanea recursivamente todos los PDFs en `./pdfs`, convierte cada página a imagen PNG, recorta las zonas de interés definidas en `SCAN_REGIONS` y decodifica cualquier QR presente usando `jsqr`. El contenido decodificado se valida contra el esquema Zod configurado.

**Variables de entorno:**

| Variable   | Valor por defecto | Descripción |
|------------|-------------------|-------------|
| `PDFS_DIR` | `./pdfs`          | Carpeta donde buscar PDFs (relativa al directorio de trabajo) |

**Parámetros clave:**

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `EXPECTED_QR_PER_PAGE` | `boolean` | Si es `true`, el test falla cuando una página no tiene QR |
| `USE_FULL_PAGE_FALLBACK` | `boolean` | Si es `true`, intenta la página completa si no encuentra QR en las zonas |
| `QR_VALIDATION_SCHEMA` | `ZodSchema` | Esquema Zod para validar el contenido del QR (URL, UUID, regex, etc.) |
| `SCAN_REGIONS` | `Region[]` | Lista ordenada de zonas donde se busca el QR |

**Zonas de escaneo predefinidas (`QR_REGIONS`):**

Las regiones se definen como **porcentajes del tamaño de la página**, por lo que funcionan con cualquier resolución:

```
┌─────────────────────────────────────┐
│  topLeft      │      topRight       │
│   (2%, 2%)    │     (70%, 2%)       │
│   28%×23%     │      28%×23%        │
├───────────────┼─────────────────────┤
│               │      center         │
│               │    (30%, 30%)       │
│               │     40%×40%         │
├───────────────┼─────────────────────┤
│  bottomLeft   │    bottomRight      │
│   (2%, 75%)   │     (70%, 75%)      │
│   28%×23%     │   28%×23%  ← común  │
└───────────────┴─────────────────────┘
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

**Personalizar el esquema de validación del QR:**

```typescript
// QR debe ser una URL HTTPS (esquema por defecto)
const QrUrlSchema = z.string().url().startsWith('https://');

// QR debe ser un UUID v4
const QrUuidSchema = z.string().uuid();

// QR debe coincidir con patrón de factura
const QrInvoiceSchema = z.string().regex(/^INV-\d{6}$/);

// QR debe ser URL de un dominio específico
const QrMyDomainSchema = z.string().url().startsWith('https://midominio.com/');
```

**Comparativa de rendimiento:**

| Modo | Velocidad | Precisión | Cuándo usar |
|------|-----------|-----------|-------------|
| Solo zonas (`USE_FULL_PAGE_FALLBACK = false`) | 🚀 ~5–10× más rápido | ⚠️ Puede perder QRs atípicos | Cuando conoces la ubicación exacta del QR |
| Zonas + fallback (`USE_FULL_PAGE_FALLBACK = true`) | 🐢 Más lento | ✅ 100% | Cuando no estás seguro de la ubicación |

---

### `compressPdfsThis.spec.ts` — Compresión de PDFs con Ghostscript

**Qué hace:** Busca todos los PDFs en `./pdfs` de forma recursiva, los comprime con Ghostscript usando el perfil seleccionado y reemplaza los originales solo si la compresión es exitosa. Genera artefactos adjuntos al reporte de Playwright.

> ✅ **Método recomendado** para comprimir PDFs. Prefiere este test sobre el script `compress_pdfs_this.sh` del directorio `./pdfs`.

**Variable de entorno:**

| Variable     | Valor por defecto | Descripción |
|--------------|-------------------|-------------|
| `GS_PROFILE` | `'2'`             | Perfil de compresión de Ghostscript |

**Perfiles disponibles:**

| Perfil | Descripción | Uso recomendado |
|--------|-------------|-----------------|
| `GS_PROFILE=2` *(default)* | JPEG controlado (QFactor 0.5), 150 DPI. Mantiene legibilidad | Documentos mixtos: facturas, tickets, cartas porte |
| `GS_PROFILE=3` | 200 DPI en color/gris/mono, Bicubic. Alta legibilidad | PDFs completamente escaneados |
| `GS_PROFILE=4` | Sin tocar imágenes; comprime fuentes y elimina recursos no usados | PDFs con texto vectorial puro |

**Detección automática de Ghostscript:** El test busca `gs`, `gswin64c` y `gswin32c` en el PATH. En Windows también soporta WSL (`wsl gs`).

**Artefactos generados:**

| Artefacto | Descripción |
|-----------|-------------|
| `gs-compress-report.json` | Resumen por archivo: bytes originales, nuevos, reducción %, errores |
| `gs-compress-log.txt` | Log detallado de cada archivo procesado |

**Notas importantes:**
- El original se reemplaza solo si la compresión es exitosa.
- Usa un archivo temporal `.tmp_compressed_<timestamp>_<nombre>.pdf` y un `renameSync` atómico al final.
- Timeout configurado en 2 minutos por archivo (`test.setTimeout(120000)`).
- Si Ghostscript no se encuentra, el test se omite y adjunta `gs-diagnostics.txt` con detalles del PATH.

---

### `testHelpers.ts` — Utilidades compartidas

Contiene funciones auxiliares para capturar logs de consola durante los tests y adjuntarlos al reporte de Playwright. Es importado automáticamente por los tests principales; no requiere configuración adicional.

---

## 8. Scripts `.sh` en `./pdfs`

Dentro de `./pdfs/` hay scripts Bash para operaciones de mantenimiento de archivos PDF. **Se ejecutan desde Git Bash (Windows) o cualquier terminal Bash (Linux/macOS).**

> ⚠️ **Importante:** Todos los scripts deben ejecutarse desde dentro del directorio `./pdfs/` o desde la raíz del proyecto con la ruta relativa. Por defecto operan sobre el directorio donde residen.

---

### `check_if_pdf_has_images_this.sh` — Detectar PDFs escaneados

**Qué hace:** Determina si cada PDF es **parseable** (tiene texto vectorial real) o **escaneado** (solo contiene imágenes). Útil para decidir qué perfil de compresión usar.

**Requisito:** `pdftotext` (paquete `poppler-utils`).

**Cómo ejecutarlo:**

```bash
cd pdfs
bash check_if_pdf_has_images_this.sh
```

**Salida:** Imprime por consola el tipo de cada PDF y genera el archivo:
```
listado_PDFs_imagenes_YYYY-MM-DD HH:MM:SS.txt
```

---

### `compress_pdfs_this.sh` — Comprimir PDFs con Ghostscript

**Qué hace:** Comprime recursivamente todos los PDFs usando Ghostscript con las opciones de compresión optimizadas (sin preset `/ebook` para mayor control). Reemplaza los archivos originales si la compresión es exitosa.

> ⚠️ Para la mayoría de los casos, se recomienda usar `npx playwright test src/tests/compressPdfsThis.spec.ts` en lugar de este script, ya que ofrece múltiples perfiles y mejor reporte de resultados.

**Requisito:** Ghostscript instalado (`gs`, `gswin64c` o `gswin32c` en el PATH).

**Cómo ejecutarlo:**

```bash
cd pdfs
bash compress_pdfs_this.sh
```

**Parámetros aceptados:** Ninguno (la configuración se edita directamente en el script).

**Salida:** Genera un log con tamaños antes/después de cada archivo:
```
gs_exex_log_YYYY-MM-DD HH:MM:SS.txt
```

**Ejemplo de salida en consola:**
```
→ Procesando: factura_001.pdf
  ✓ 1 245.30 KB → 387.12 KB (68% menos)
```

---

### `convert_images_to_pdfs_recursive_this.sh` — Imágenes → PDF

**Qué hace:** Convierte recursivamente todos los archivos `.jpg`, `.jpeg` y `.png` encontrados en el directorio a PDF usando ImageMagick a 150 DPI. **Elimina la imagen original** tras una conversión exitosa.

**Requisito:** ImageMagick (`magick` o `convert` en el PATH).

**Cómo ejecutarlo:**

```bash
cd pdfs
bash convert_images_to_pdfs_recursive_this.sh
```

**Salida:** Genera un log de conversiones:
```
images_to_pdf_log_YYYY-MM-DD HH:MM:SS.txt
```

> ⚠️ El script elimina las imágenes originales. Asegúrate de tener una copia de respaldo antes de ejecutarlo.

---

### `list_1M_PDF_large_files_this.sh` — Listar PDFs mayores a 1 MB

**Qué hace:** Lista todos los archivos PDF mayores a 1 MB en el directorio y sus subdirectorios. Útil para identificar qué archivos comprimir con prioridad.

**Cómo ejecutarlo:**

```bash
cd pdfs
bash list_1M_PDF_large_files_this.sh
```

**Salida:** Genera el archivo:
```
listado_PDFs_1M_YYYY-MM-DD HH:MM.txt
```

---

### `list_4MB_large_files_this.sh` — Listar archivos mayores a 4 MB

**Qué hace:** Lista **todos** los archivos (no solo PDFs) mayores o iguales a 4 MB. Ideal para una auditoría rápida del espacio en disco.

**Cómo ejecutarlo:**

```bash
cd pdfs
bash list_4MB_large_files_this.sh
```

**Salida:** Genera el archivo:
```
archivos_4M_YYYY-MM-DD HH:MM.txt
```

---

### `unlock_files_recursive_this.sh` — Desbloquear archivos (Windows)

**Qué hace:** Utiliza PowerShell (`Unblock-File`) para desbloquear recursivamente todos los PDFs del directorio. Necesario cuando Windows marca como bloqueados los archivos descargados de Internet.

**Requisito:** Windows con PowerShell disponible en el PATH.

**Cómo ejecutarlo:**

```bash
cd pdfs
bash unlock_files_recursive_this.sh
```

**Salida:** Genera el archivo:
```
unlockedFiles_logYYYY-MM-DD HH:MM.txt
```

---

### `list_1M_PDF_large_files_fdfind_this.sh` — Listar PDFs > 1 MB con `fdfind`

**Qué hace:** Variante del script de listado que usa `fdfind` (fd) en lugar de `find`. Más rápido en directorios con muchos archivos.

**Requisito:** `fdfind` o `fd` instalado.

```bash
# Ubuntu / Debian
sudo apt-get install -y fd-find
```

**Cómo ejecutarlo:**

```bash
cd pdfs
bash list_1M_PDF_large_files_fdfind_this.sh
```

---

## 9. Solución de problemas comunes

### ⚠️ Ghostscript no encontrado al ejecutar el test de compresión

**Síntoma:**
```
Test skipped: Ghostscript not found. See gs-diagnostics.txt for details.
```

**Causa:** El ejecutable `gs` (Linux/macOS) o `gswin64c` (Windows) no está en el PATH del sistema.

**Solución:**

```bash
# Linux: instalar
sudo apt-get install -y ghostscript

# macOS: instalar con Homebrew
brew install ghostscript

# Windows: verificar que el directorio de instalación está en el PATH
# Normalmente: C:\Program Files\gs\gs10.xx.x\bin
# Agregar manualmente en: Panel de control → Variables de entorno → PATH

# Verificar que funciona
gs --version       # Linux/macOS
gswin64c --version # Windows
```

---

### ⚠️ QR no detectado en ninguna zona del PDF

**Síntoma:** El test reporta que no encontró QR en ninguna zona ni en la página completa.

**Causas posibles y soluciones:**

1. **Resolución de imagen demasiado baja:** Aumenta el parámetro `scale` en [`pdfProcessor.ts`](src/utils/pdfProcessor.ts):
   ```typescript
   // Cambiar de scale: 2 a scale: 4 o incluso 5
   const pages = await convertPdfToImages(pdfPath, { scale: 4 });
   ```

2. **Zona mal configurada:** El QR está en una posición no cubierta por `SCAN_REGIONS`. Activa el debug de zonas:
   ```bash
   npm run debug:zones
   ```
   Esto guarda las imágenes recortadas en `./debug/` para inspeccionarlas visualmente.

3. **QR demasiado pequeño o con baja calidad:** Usa `USE_FULL_PAGE_FALLBACK = true` como medida temporal mientras ajustas las zonas.

---

### ⚠️ PDFs mal formados o corruptos al comprimir

**Síntoma:** El test de compresión reporta error en algunos archivos y los deja sin procesar.

**Causa:** El PDF de origen tiene errores estructurales que Ghostscript no puede reparar automáticamente.

**Solución:**

```bash
# Verificar si el PDF está dañado con pdfinfo (requiere poppler-utils)
pdfinfo archivo.pdf

# Intentar reparar con Ghostscript directamente
gs -sDEVICE=pdfwrite -dNOPAUSE -dBATCH -dQUIET \
   -sOutputFile=archivo_reparado.pdf archivo.pdf

# En Windows
gswin64c -sDEVICE=pdfwrite -dNOPAUSE -dBATCH -dQUIET ^
   -sOutputFile=archivo_reparado.pdf archivo.pdf
```

---

### ⚠️ Error al instalar el paquete `canvas` (dependencia de `jimp`)

**Síntoma:**
```
npm ERR! gyp ERR! build error
```

**Causa:** `jimp` requiere compilar módulos nativos de Node.js y faltan herramientas de compilación.

**Solución:**

```bash
# Linux (Ubuntu/Debian)
sudo apt-get install -y build-essential libcairo2-dev libpango1.0-dev

# macOS
xcode-select --install

# Windows (PowerShell como administrador)
npm install -g windows-build-tools
```

---

### ⚠️ Archivos PDF bloqueados en Windows (acceso denegado)

**Síntoma:** Node.js o los scripts Bash lanzan `EACCES` o `Permission denied` al leer PDFs.

**Causa:** Windows marca como bloqueados los archivos descargados de Internet.

**Solución:** Usa el script incluido en el proyecto:

```bash
cd pdfs
bash unlock_files_recursive_this.sh
```

O desbloquea manualmente desde PowerShell:

```powershell
Get-ChildItem -Path ".\pdfs" -Recurse -Filter "*.pdf" | Unblock-File
```

---

### ⚠️ PDFs comprimidos salen borrosos

**Síntoma:** Después de comprimir, el texto o las imágenes del PDF se ven borrosas o pixeladas.

**Causa:** El perfil de compresión usa una resolución demasiado baja para el tipo de contenido.

**Solución:** Cambia el perfil de compresión al ejecutar el test:

```bash
# Para PDFs escaneados (todo imagen): usar perfil 3 con 200 DPI
GS_PROFILE=3 npx playwright test src/tests/compressPdfsThis.spec.ts

# Para PDFs con texto vectorial: usar perfil 4 (no toca imágenes)
GS_PROFILE=4 npx playwright test src/tests/compressPdfsThis.spec.ts
```

---

## 10. Estructura del proyecto

```
pdf-qr-validator/
│
├── 📁 src/
│   ├── 📁 utils/
│   │   ├── fileScanner.ts          # Escaneo recursivo de PDFs en ./pdfs
│   │   ├── pdfProcessor.ts         # Conversión de páginas PDF a imágenes PNG
│   │   ├── qrValidator.ts          # Recorte por zonas y decodificación de QR
│   │   ├── ghostscript.ts          # Wrapper para invocar Ghostscript
│   │   └── zoneDebugger.ts         # Utilidad para guardar imágenes de zonas recortadas
│   │
│   ├── 📁 tests/
│   │   ├── pdfQrValidationThis.spec.ts   # ✅ Test principal: validación de QR
│   │   ├── compressPdfsThis.spec.ts      # ✅ Test principal: compresión con GS
│   │   ├── testHelpers.ts                # Funciones auxiliares (captura de logs)
│   │   └── 📁 backups/                   # Versiones anteriores de los tests (referencia)
│   │
│   └── 📁 bashScripts/
│       ├── compress_pdfs_this.sh         # Copia del script de compresión (referencia)
│       └── gsParametersPerfiles.md       # Documentación de perfiles de Ghostscript
│
├── 📁 pdfs/                         # ← Coloca aquí tus PDFs
│   ├── check_if_pdf_has_images_this.sh           # Detectar PDFs escaneados
│   ├── compress_pdfs_this.sh                     # Comprimir PDFs (script Bash)
│   ├── convert_images_to_pdfs_recursive_this.sh  # Imágenes → PDF
│   ├── list_1M_PDF_large_files_this.sh           # Listar PDFs > 1 MB
│   ├── list_1M_PDF_large_files_fdfind_this.sh    # Listar PDFs > 1 MB (con fdfind)
│   ├── list_4MB_large_files_this.sh              # Listar archivos > 4 MB
│   └── unlock_files_recursive_this.sh            # Desbloquear archivos (Windows)
│
├── 📁 specs/                        # Planes de prueba y especificaciones
├── 📁 tests/                        # Tests adicionales (exploración)
├── 📁 playwright-report/            # Reportes HTML generados por Playwright
├── 📁 test-results/                 # Screenshots y trazas de ejecuciones anteriores
│
├── playwright.config.ts             # Configuración de Playwright (testDir, reporter, trace)
├── tsconfig.json                    # Configuración de TypeScript
├── package.json                     # Dependencias y scripts npm
├── AGENTS.md                        # Instrucciones para agentes de IA
└── README.md                        # Este archivo
```

---

> 📌 **Referencia rápida de comandos:**
>
> ```bash
> npm install                          # Instalar dependencias
> npx playwright install               # Instalar navegadores
> npm test                             # Ejecutar todos los tests
> npm run test:ui                      # Modo UI interactivo
> npx playwright show-report           # Ver reporte HTML
> GS_PROFILE=3 npm test               # Comprimir con perfil para escaneados
> PDFS_DIR=/ruta/pdfs npm test        # Usar carpeta de PDFs personalizada
> ```
