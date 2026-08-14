// tests/pdf-legible.spec.js
const { test, expect } = require('@playwright/test');
const { startConsoleCapture, restoreConsoleCapture } = require('./testHelpers');
const fs = require('fs');
const path = require('path');
const { glob } = require('glob');
const pdfParse = require('pdf-parse');

const PDFS_DIR = process.env.PDFS_DIR
  ? path.resolve(process.cwd(), process.env.PDFS_DIR)
  : path.resolve(process.cwd(), './pdfs');

const PDF_PATTERN = path.join(PDFS_DIR, '**/*.pdf').replace(/\\/g, '/');

async function findPdfFiles() {
  if (!fs.existsSync(PDFS_DIR)) {
    return [];
  }
  return await glob(PDF_PATTERN, { absolute: true, nocase: true });
}

test.describe('Validación de PDFs que sean legibles y parseables', () => {
  test('Todos los PDFs en el directorio de ejecución tienen texto extraíble', async () => {
    const pdfFiles = await findPdfFiles();

    expect(
      pdfFiles.length,
      `No se encontraron archivos PDF en: ${PDFS_DIR}`
    ).toBeGreaterThan(0);

    const info = test.info();

    // startConsoleCapture is started in beforeEach; logs will be attached in afterEach

    for (const pdfFile of pdfFiles) {
      const pdfBuffer = fs.readFileSync(pdfFile);
      const data = await pdfParse(pdfBuffer);

      const message = `Verificando texto extraíble en: ${pdfFile}`;
      console.log(message);
      await info.attach(`Verificación de PDF: ${path.basename(pdfFile)}`, {
        body: Buffer.from(message, 'utf-8'),
        contentType: 'text/plain',
      });

      expect(data.text.length).toBeGreaterThan(50);
      //expect(data.text).toContain('RFC');
    }

    // logs will be attached by afterEach hook
  });

  test.beforeEach(() => {
    startConsoleCapture(test.info(), 'console-logs');
  });

  test.afterEach(async () => {
    await restoreConsoleCapture(test.info());
  });
});