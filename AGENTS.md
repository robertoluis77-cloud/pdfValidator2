# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Project overview
- Node.js + TypeScript project using `@playwright/test` to validate PDF QR codes, compress PDFs via Ghostscript, and classify PDFs (text vs. scanned image).
- Test suite in `src/tests/`; utilities in `src/utils/`.
- **Windows-only.** Only verified on Windows; relies on `gswin64c`/`gswin32c`, native ImageMagick detection, and `Unblock-File`.

## Commands
- `npm test` — run all tests (headless, HTML reporter → `test-results/`)
- `npm run test:ui` — interactive Playwright UI
- `npm run test:debug` — debug mode
- `npm run debug:zones -- <path-to-pdf>` — run `src/utils/zoneDebugger.ts` via ts-node (requires a PDF path arg)
- Run a single spec: `npx playwright test src/tests/compressPdfsThis.spec.ts`
- Run with a custom PDF folder: `PDFS_DIR=/path/to/pdfs npm test` (PowerShell: `$env:PDFS_DIR="..."; npm test`)
- Run compression with a profile: `GS_PROFILE=3 npx playwright test src/tests/compressPdfsThis.spec.ts`

There is no lint/typecheck/build script in `package.json`. Tests run directly from TypeScript via Playwright's transpiler; no `tsc` build step is required.

## Critical non-obvious patterns

### `pdf-to-img` is ESM-only — must be loaded with `eval('import(...)')`
The project compiles to CommonJS (`"module": "commonjs"` in tsconfig). `pdf-to-img` is an ESM-only package.
Importing it normally will crash. The workaround already in [`src/utils/pdfProcessor.ts`](src/utils/pdfProcessor.ts) is:
```ts
const pdfModule = await eval('import("pdf-to-img")');
const { pdf } = pdfModule;
```
Do **not** change this to a regular `import` or `require` — it will break.

### Tests register one `test()` per PDF at module load time
`pdfQrValidationThis.spec.ts` and `compressPdfsThis.spec.ts` call `scanPdfsSync(PDFS_DIR)` **synchronously at the top level** (outside any `test()` or hook) and loop over the results to dynamically register one test per file. This means:
- `pdfQrValidationThis.spec.ts` creates `PDFS_DIR` with `fs.mkdirSync(..., { recursive: true })` if it doesn't exist; `compressPdfsThis.spec.ts` does not.
- If the folder is empty, a dedicated "at least one PDF" test will fail.
- Do **not** move the scan call inside `test.beforeAll` — dynamic test registration must happen at module scope for Playwright to discover the tests.
- `pdfParserThis.spec.ts` is different: it discovers PDFs **inside** the test via async `findPdfFiles()` (glob), not at module scope.

### `src/tests/backups/` is excluded from test discovery
`playwright.config.ts` sets `testIgnore: ['**/backups/**']`. Old spec versions in that folder will never run.

### QR regions use percentage coordinates (0.0–1.0), not pixels
[`src/utils/qrValidator.ts`](src/utils/qrValidator.ts) — `Region` fields (`x`, `y`, `width`, `height`) are fractions of the image dimensions. Coordinates are clamped automatically, but `x + width` and `y + height` should each stay ≤ 1.0.

### Ghostscript is discovered at `test.beforeAll`, not at module load
[`src/utils/ghostscript.ts`](src/utils/ghostscript.ts) probes `gs`, `gswin64c`, `gswin32c`, Windows install paths under `C:\Program Files\gs\`, and finally `wsl gs`. If none found, the compression test **skips** (not fails) and attaches `gs-diagnostics.txt`.

### `GS_PROFILE` env var selects compression profile
Valid values: `'2'` (default), `'12'`, `'3'`, `'4'`. Defined in `GS_PROFILES` record in `ghostscript.ts`. Unknown values silently fall back to profile `'2'`.

### Console logs are captured per-test and attached as artifacts
[`src/tests/testHelpers.ts`](src/tests/testHelpers.ts) patches `console.log` via `startConsoleCapture()` and restores+attaches in `afterEach`. Call `startConsoleCapture(test.info(), name)` in `beforeEach` and `await restoreConsoleCapture(test.info())` in `afterEach` — exactly as the existing specs do.

### `pdfParserThis.spec.ts` classifies PDFs and writes timestamped result files
Uses `pdf-parse` v2 (the `PDFParse` class, not the v1 function export: `const { PDFParse } = require('pdf-parse')`). Classifies each PDF as text (>50 extracted chars) vs. image/scanned, and at `afterAll` writes `textPDFs_<ts>.txt`, `imagePDFs_<ts>.txt`, `errorPDFs_<ts>.txt` to `./shellScriptResults/pdfParserResults/` (created on demand). Parse errors are logged and skipped, never thrown.

### The bash scripts (in `./pdfs/`) write results to a shared dir
The `.sh` scripts run under Git Bash and write output to `../shellScriptResults/` (or `../test-results/shellScriptResults/` for the image→PDF script). `listandoTipos.sh` and `list_1M_PDF_large_files_fdfind_this.sh` require `fdfind`/`fd`; `check_if_pdf_has_images_this.sh` requires `pdftotext`; `convert_images_to_pdfs_recursive_this.sh` requires ImageMagick and deletes the source images. See the README's script section for details.

### `convertPdfToImages` default scale is `2.5`; QR validation spec uses `scale: 3`
Low scale values (≤ 2) frequently miss QR codes. Use `scale: 3` or higher when adding new QR-reading code.

### Compression only replaces the original if the compressed file is **smaller**
If Ghostscript produces a larger file, the original is kept and the temp file is deleted — the test still passes. A compression failure (non-zero exit or missing tmp file) causes the test to fail.

## Test conventions
- Attach diagnostic output with `test.info().attach(name, { body, contentType })`.
- Use `PDFS_DIR` env var to point at a custom PDF folder.
- Keep tests in `src/tests/`; do not change `playwright.config.ts` unless strictly necessary.
- Prefer updating existing spec files over creating new ones.
