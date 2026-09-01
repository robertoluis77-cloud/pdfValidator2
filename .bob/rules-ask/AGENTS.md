# AGENTS.md — Ask mode

This file provides guidance to agents answering questions about this repository.

## Non-obvious documentation context

### The two "compress" entry points are intentionally different tools
- `src/tests/compressPdfsThis.spec.ts` — the recommended path; supports 4 profiles via `GS_PROFILE`, produces JSON/log artifacts, skips gracefully when GS is absent.
- `pdfs/compress_pdfs_this.sh` — a legacy Bash script with hardcoded settings and no profile selection. The README recommends the spec over the script.

### `src/tests/backups/` contains old spec versions — they do NOT run
`playwright.config.ts` sets `testIgnore: ['**/backups/**']`. These files are reference copies only.

### `src/bashScripts/` mirrors `pdfs/` scripts — it is a reference copy, not the canonical location
Canonical scripts are in `./pdfs/`. `src/bashScripts/compress_pdfs_this.sh` and `gsParametersPerfiles.md` are for developer reference.

### Ghostscript GS_PROFILE '12' is undocumented in README but exists in code
`ghostscript.ts` `GS_PROFILES` defines keys `'2'`, `'12'`, `'3'`, `'4'`. The README only mentions 2, 3, and 4. Profile `'12'` is a balanced `/ebook` + 250 DPI bicubic profile.

### `fileScanner` uses glob with `nocase: true` — picks up `.PDF` on case-sensitive systems
Both `scanPdfs` (async) and `scanPdfsSync` share this behaviour. Relevant when the source directory has mixed-case extensions.

### `zoneDebugger.ts` is executed with ts-node via `npm run debug:zones`, not as a test
It's a standalone CLI utility in `src/utils/`, not a Playwright spec. It won't show up in test reports.
