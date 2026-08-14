# Agent Instructions for pdf-qr-validator

## Project overview
- This repository is a Node.js + TypeScript project that uses `@playwright/test` to validate PDF files and QR codes.
- The main test suite lives in `src/tests`, and utilities for PDF scanning and QR decoding live in `src/utils`.
- The repository is configured to run Playwright tests with an HTML reporter and trace collection on first retry.

## Key files
- `package.json` - contains install and test scripts.
- `playwright.config.ts` - sets `testDir: './src/tests'`, `fullyParallel: true`, `reporter: 'html'`, and `trace: 'on-first-retry'`.
- `src/tests/pdfQrValidation.spec.ts` - main QR validation test implementation.
- `src/tests/pdfParser.spec.ts` - PDF text extraction and parseability checks.
- `src/utils/fileScanner.ts`, `src/utils/pdfProcessor.ts`, `src/utils/qrValidator.ts` - core PDF file scanning and processing utilities.
- `README.md` - user-facing usage and troubleshooting guidance.
- `specs/README.md` - directory description for test plans.

## Recommended workflow
- Install dependencies: `npm install`
- Install Playwright browsers: `npx playwright install`
- Run tests: `npm test`
- Run interactive test UI: `npm run test:ui`
- Run debug mode: `npm run test:debug`
- Run zone debugger if needed: `npm run debug:zones`

## Test conventions
- Keep Playwright tests in `src/tests`.
- Use the `test` and `expect` APIs from `@playwright/test`.
- Attach diagnostic output to the Playwright report via `test.info().attach(...)` when the information should appear in test artifacts.
- Use `PDFS_DIR` environment variable to override the default PDF source directory (`./pdfs`).
- Tests may rely on recursive PDF discovery and should handle the case where `PDFS_DIR` does not exist.

## Notes for AI agents
- Prefer updating existing test files rather than creating new top-level scripts unless the feature is test-related.
- Do not change the Playwright configuration unless the change is needed for a valid test or reporter enhancement.
- Keep changes compatible with the current `@playwright/test` version and TypeScript setup.
- Link to `README.md` for usage and debugging details rather than duplicating large sections.
