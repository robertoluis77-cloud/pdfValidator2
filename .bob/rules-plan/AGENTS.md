# AGENTS.md — Plan mode

This file provides guidance to agents planning changes in this repository.

## Non-obvious architectural constraints

### CommonJS + ESM hybrid is a hard constraint
`tsconfig.json` targets CommonJS. `pdf-to-img` is ESM-only. The `eval('import(...)')` hack in `pdfProcessor.ts` is the load-bearing bridge. Any migration to native ESM (`"type": "module"`) would require updating all `require`-style imports and is a breaking change across the whole project.

### Tests are data-driven: adding PDFs changes the test count
Both spec files register one Playwright test per PDF file found in `PDFS_DIR` at module load. An empty `./pdfs` folder means exactly one test runs (the "at least one PDF" guard test) and it fails. Planning for CI requires pre-seeding the folder or setting `PDFS_DIR` to a fixture directory.

### `fullyParallel: true` with workers=4 — compression tests can run concurrently
Each PDF is a separate test; all can run in parallel. `compressPdfsThis.spec.ts` uses a tmp file named `.tmp_compressed_<timestamp>_<basename>` to avoid collisions. Do not change the naming scheme without ensuring uniqueness per concurrent run.

### Ghostscript discovery is done once in `beforeAll`, shared across all per-PDF tests
`gsInfo` is module-level in `compressPdfsThis.spec.ts`. If GS discovery is made async or moved inside individual tests, all per-PDF tests will attempt discovery independently — change with care.

### `QR_VALIDATION_SCHEMA` is a compile-time constant, not a runtime config
The Zod schema used to validate QR content is hardcoded inside each spec file. To support multiple document types in one run you must either split into multiple spec files or refactor the constant into a per-file/per-PDF lookup.

### The compression test does NOT fail when the output is larger than the input
It silently discards the compressed file and keeps the original. This is intentional (safe-by-default) but means a test pass does not guarantee compression occurred.
