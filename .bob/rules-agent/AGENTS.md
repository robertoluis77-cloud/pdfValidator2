# AGENTS.md — Agent (coding) mode

This file provides guidance to agents when writing or modifying code in this repository.

## Non-obvious coding rules

### ESM import workaround — do not break it
`pdf-to-img` is ESM-only in a CommonJS project. The only working pattern is:
```ts
const pdfModule = await eval('import("pdf-to-img")');
const { pdf } = pdfModule;
```
Never replace this with `import` at the top of the file or `require()`.

### Dynamic test registration must stay at module scope
`scanPdfsSync()` and the `for (const pdf of pdfFiles)` loop that calls `test(...)` must remain at the top level of each spec file — not inside `beforeAll` or any async context. Playwright discovers tests synchronously at import time.

### QR Region coordinates are percentages (0.0–1.0), never pixels
Any new region added to `QR_REGIONS` in [`src/utils/qrValidator.ts`](src/utils/qrValidator.ts) must use fractional values. Ensure `x + width ≤ 1.0` and `y + height ≤ 1.0`.

### Use `decodeQrFromImage` for fallback, `decodeQrFromRegionsOnly` for speed
Both functions are in `qrValidator.ts`. Only `decodeQrFromImage` scans the full page as fallback. Pick based on `USE_FULL_PAGE_FALLBACK`.

### Console capture must be started/restored in beforeEach/afterEach pair
Import `startConsoleCapture` and `restoreConsoleCapture` from `./testHelpers`. Patch in `beforeEach`, restore in `afterEach` — not in the test body itself.

### Ghostscript is async — use `runGhostscript()`, never `spawnSync`
`runGhostscript(cmd, args)` in `ghostscript.ts` returns a `Promise<GsResult>`. Use it to avoid blocking the event loop during compression (important with `fullyParallel: true`).

### `humanKb()` returns a `number`, not a string
Don't interpolate it as `${humanKb(n)} KB` expecting rounding via `.toString()` — it already returns a float with 2 decimal places.

### `toWslPath()` is only needed when `gsInfo.isWsl === true`
Don't apply WSL path conversion to native Windows or Linux paths — it will break Ghostscript invocation.
