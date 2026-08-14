# PDF QR Validator (con Crop por Zonas)

Validación automatizada y recursiva de archivos PDF y los códigos QR contenidos en ellos, usando **Playwright + TypeScript** con escaneo optimizado por zonas.

## 🚀 Instalación

```bash
# 1. Clonar o crear la carpeta del proyecto
mkdir pdf-qr-validator && cd pdf-qr-validator

# 2. Copiar todos los archivos del proyecto

# 3. Instalar dependencias
npm install

# 4. Instalar navegadores de Playwright
npx playwright install
```

## 📂 Uso Rápido

1. **Coloca tus PDFs** en la carpeta `/pdfs` (se escanean recursivamente).
2. **Ajusta la configuración** en `src/tests/pdfQrValidationThis.spec.ts`:
   - `PDFS_DIR`: ruta a tus PDFs
   - `SCAN_REGIONS`: zonas donde suele estar el QR
   - `USE_FULL_PAGE_FALLBACK`: `true` para escanear toda la página si no encuentra en zonas
   - `EXPECTED_QR_PER_PAGE`: `true` si cada página DEBE tener QR
   - `QR_VALIDATION_SCHEMA`: esquema Zod para validar el contenido del QR

3. **Ejecuta los tests:**
```bash
# Modo headless (rápido)
npm test

# Modo UI interactivo
npm run test:ui

# Con debugger
npm run test:debug

# Debug de zonas (verifica que tus regiones recortan bien)
npm run debug:zones
```

## 🧪 Tests en `src/tests/`

La suite de pruebas vive en `src/tests/` y se ejecuta con Playwright. Cada archivo `.spec.ts` es un test independiente.

### `pdfQrValidationThis.spec.ts` — Validación de QR en PDFs

**Qué hace:** Escanea recursivamente todos los PDFs en `./pdfs`, convierte cada página a imagen, busca códigos QR en las zonas definidas y valida su contenido contra un esquema Zod.

**Variables de entorno:**

| Variable | Valor por defecto | Descripción |
|----------|-------------------|-------------|
| `PDFS_DIR` | `./pdfs` | Carpeta donde buscar PDFs (relativa al cwd) |

**Configuración clave dentro del archivo:**

```typescript
const EXPECTED_QR_PER_PAGE = false;   // true = falla si una página no tiene QR
const USE_FULL_PAGE_FALLBACK = true;  // true = busca en zonas, luego en página completa
const QR_VALIDATION_SCHEMA = QrUrlSchema;  // Esquema Zod para validar el QR
const SCAN_REGIONS = [
  QR_REGIONS.bottomRight,  // Primero intenta aquí
  QR_REGIONS.topRight,     // Luego aquí
  QR_REGIONS.bottomLeft,
];
```

**Ejecutar solo este test:**
```bash
npx playwright test src/tests/pdfQrValidationThis.spec.ts
```

### `compressPdfsThis.spec.ts` — Compresión de PDFs con Ghostscript

**Qué hace:** Busca todos los PDFs en el directorio actual, los comprime con Ghostscript usando un perfil configurable y reemplaza los originales.

**Variables de entorno:**

| Variable | Valor por defecto | Descripción |
|----------|-------------------|-------------|
| `GS_PROFILE` | `'2'` | Perfil de compresión: `'2'` (máxima compresión + legible), `'3'` (200 DPI, bueno para escaneados), `'4'` (solo texto vectorial) |

**Ejecutar solo este test:**
```bash
npx playwright test src/tests/compressPdfsThis.spec.ts
```

### `testHelpers.ts` — Helpers compartidos

Contiene funciones para capturar logs de consola durante los tests y adjuntarlos al reporte de Playwright. Se usa automáticamente desde los tests principales.

---

## 🔧 Scripts de Bash en `pdfs/`

Dentro de la carpeta `./pdfs/` hay varios scripts `.sh` para operaciones comunes de mantenimiento de archivos PDF. **Todos se ejecutan desde Git Bash (Windows) o cualquier terminal Bash (Linux/macOS).**

> **Nota:** Los scripts deben ejecutarse desde dentro de la carpeta `./pdfs/` o apuntar a ella. Por defecto operan sobre el directorio donde residen.

### `check_if_pdf_has_images_this.sh` — Detectar PDFs escaneados

Determina si cada PDF es **parseable** (tiene texto vectorial) o **escaneado** (solo imágenes). Requiere `pdftotext` (paquete `poppler-utils`).

```bash
cd pdfs
bash check_if_pdf_has_images_this.sh
```

**Salida:** Muestra en consola y genera un archivo `listado_PDFs_imagenes_YYYY-MM-DD HH:MM:SS.txt` con el resumen.

---

### `compress_pdfs_this.sh` — Comprimir PDFs con Ghostscript

Comprime recursivamente todos los PDFs usando Ghostscript con preset `/ebook` (150 DPI). Reemplaza los archivos originales.

```bash
cd pdfs
bash compress_pdfs_this.sh
```

**Requisito:** Ghostscript instalado (`gs` en Linux/Mac, `gswin64c`/`gswin32c` en Windows).

**Salida:** Genera un log `gs_exex_log_YYYY-MM-DD HH:MM:SS.txt` con los tamaños antes/después.

---

### `convert_images_to_pdfs_recursive_this.sh` — Imágenes → PDF

Convierte recursivamente todos los archivos `.jpg`, `.jpeg` y `.png` a PDF usando ImageMagick (DPI 150). **Elimina la imagen original** tras la conversión exitosa.

```bash
cd pdfs
bash convert_images_to_pdfs_recursive_this.sh
```

**Requisito:** ImageMagick (`magick` o `convert`).

**Salida:** Genera un log `images_to_pdf_log_YYYY-MM-DD HH:MM:SS.txt`.

---

### `list_1M_PDF_large_files_this.sh` — Listar PDFs > 1 MB

Lista todos los PDFs mayores a 1 MB en el directorio y subdirectorios.

```bash
cd pdfs
bash list_1M_PDF_large_files_this.sh
```

**Salida:** Genera `listado_PDFs_1M_YYYY-MM-DD HH:MM.txt`.

---

### `list_4MB_large_files_this.sh` — Listar archivos > 4 MB

Lista **todos** los archivos (no solo PDFs) mayores o iguales a 4 MB.

```bash
cd pdfs
bash list_4MB_large_files_this.sh
```

**Salida:** Genera `archivos_4M_YYYY-MM-DD HH:MM.txt`.

---

### `unlock_files_recursive_this.sh` — Desbloquear archivos (Windows)

Usa PowerShell (`Unblock-File`) para desbloquear recursivamente todos los PDFs. Útil cuando Windows marca archivos descargados de Internet como bloqueados.

```bash
cd pdfs
bash unlock_files_recursive_this.sh
```

**Requisito:** Windows + PowerShell disponible en PATH.

**Salida:** Genera `unlockedFiles_logYYYY-MM-DD HH:MM.txt`.

---

## 🎯 Zonas de QR Predefinidas

Las regiones se definen como **porcentajes** del tamaño de la página, así funcionan con cualquier resolución:

```
┌─────────────────────────────────────┐
│  topLeft      │      topRight       │
│   (2%,2%)     │      (70%,2%)       │
│   28%x23%     │       28%x23%       │
├───────────────┼─────────────────────┤
│               │                     │
│               │      center         │
│               │    (30%,30%)        │
│               │     40%x40%         │
│               │                     │
├───────────────┼─────────────────────┤
│  bottomLeft   │    bottomRight      │
│   (2%,75%)    │     (70%,75%)       │
│   28%x23%     │      28%x23%        │
│               │  ← MÁS COMÚN        │
└───────────────┴─────────────────────┘
```

### Configurar zonas en el test

```typescript
const SCAN_REGIONS: Region[] = [
  QR_REGIONS.bottomRight,   // Primero intenta aquí (más rápido)
  QR_REGIONS.topRight,      // Luego aquí
  QR_REGIONS.bottomLeft,    // Etc.
];
```

### Crear tu propia zona

```typescript
const MI_ZONA: Region = {
  name: 'miZonaPersonalizada',
  x: 0.60,      // 60% desde la izquierda
  y: 0.80,      // 80% desde arriba
  width: 0.20,  // 20% del ancho total
  height: 0.15, // 15% del alto total
};
```

## ⚡ Rendimiento: Zonas vs Página Completa

| Modo | Velocidad | Precisión | Cuándo usar |
|------|-----------|-----------|-------------|
| **Solo zonas** (`USE_FULL_PAGE_FALLBACK = false`) | 🚀 ~5-10x más rápido | ⚠️ Puede perder QRs raros | Cuando sabes exactamente dónde está el QR |
| **Zonas + Fallback** (`USE_FULL_PAGE_FALLBACK = true`) | 🐢 Más lento | ✅ 100% | Cuando no estás seguro de la ubicación |
| **Página completa** (versión anterior) | 🐌🐌 Muy lento | ✅ 100% | Nunca recomendado con muchos PDFs |

## 🛠️ Debugging de Zonas

Para verificar que tus zonas están bien definidas, puedes guardar las imágenes recortadas:

```typescript
import { saveCroppedRegion, QR_REGIONS } from '../utils/qrValidator';

// En tu test, después de convertir el PDF:
for (const page of pages) {
  for (const region of SCAN_REGIONS) {
    await saveCroppedRegion(
      page.buffer,
      region,
      `./debug/${pdfFile.fileName}_p${page.pageNumber}_${region.name}.png`
    );
  }
}
```

Esto genera imágenes como:
```
debug/
├── factura.pdf_p1_bottomRight.png   ← ¿Aquí está tu QR?
├── factura.pdf_p1_topRight.png
├── ticket.pdf_p1_bottomRight.png
└── ...
```

## 📊 Reportes

Playwright genera automáticamente:
- **Reporte HTML**: `npx playwright show-report`
- **Adjuntos JSON** en cada test con el resultado de cada página
- **Screenshots y traces** en `test-results/`

## ⚙️ Personalización del esquema QR

Por defecto se valida que el QR contenga una URL `https://`. Para personalizar:

```typescript
// QR debe ser un UUID
const QrUuidSchema = z.string().uuid();

// QR debe coincidir con patrón de factura
const QrInvoiceSchema = z.string().regex(/^INV-\d{6}$/);

// QR debe ser URL de dominio específico
const QrMyDomainSchema = z.string().url().startsWith('https://midominio.com/');
```

## 🔧 Solución de Problemas

| Problema | Solución |
|----------|----------|
| QR no detectado en ninguna zona | Aumenta `scale` en `convertPdfToImages()` (ej: `scale: 4` o `5`) |
| QR detectado solo en fallback | Ajusta las coordenadas de `SCAN_REGIONS` usando el debug de zonas |
| Zona recorta fuera de la imagen | Las coordenadas se clamp automáticamente, revisa que `x + width <= 1.0` |
| `canvas` no instala | Instala build tools: `npm install -g windows-build-tools` (Win) o `apt-get install build-essential` (Linux) |
| Muchos falsos negativos | Aumenta `scale` a 4+ o usa `USE_FULL_PAGE_FALLBACK = true` |

## 📁 Estructura del proyecto

```
pdf-qr-validator/
├── src/
│   ├── utils/
│   │   ├── fileScanner.ts       # Escaneo recursivo de PDFs
│   │   ├── pdfProcessor.ts      # PDF → imágenes PNG
│   │   ├── qrValidator.ts       # Crop por zonas + decodificación QR
│   │   └── zoneDebugger.ts      # Utilidad para depurar regiones
│   └── tests/
│       ├── pdfQrValidationThis.spec.ts   # Tests de validación QR
│       ├── compressPdfsThis.spec.ts      # Tests de compresión Ghostscript
│       └── testHelpers.ts                # Helpers compartidos
├── pdfs/                        # ← Pon aquí tus PDFs + scripts Bash
│   ├── check_if_pdf_has_images_this.sh
│   ├── compress_pdfs_this.sh
│   ├── convert_images_to_pdfs_recursive_this.sh
│   ├── list_1M_PDF_large_files_this.sh
│   ├── list_4MB_large_files_this.sh
│   └── unlock_files_recursive_this.sh
├── playwright.config.ts
├── tsconfig.json
├── package.json
└── README.md
```
