import { test, expect } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';
import { scanPdfs, scanPdfsSync } from '../utils/fileScanner';
import { startConsoleCapture, restoreConsoleCapture } from './testHelpers';
import { convertPdfToImages } from '../utils/pdfProcessor';
import {
  decodeQrFromImage,
  decodeQrFromRegionsOnly,
  validateQrContent,
  QrUrlSchema,
  QR_REGIONS,
  Region,
} from '../utils/qrValidator';

// Helper: wrap a promise with a timeout guard
function withTimeout<T>(p: Promise<T>, ms: number, message = 'Operation timed out'): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(message)), ms);
    p.then((v) => {
      clearTimeout(timer);
      resolve(v);
    }).catch((err) => {
      clearTimeout(timer);
      reject(err);
    });
  });
}

// ═══════════════════════════════════════════════
// CONFIGURACIÓN: Ajusta estas variables
// ═══════════════════════════════════════════════
// Escanea recursivamente todos los PDFs dentro de la carpeta desde donde se ejecuta la prueba.
// Puedes cambiarla con la variable de entorno PDFS_DIR, o dejarla en ./pdfs relativo al cwd.
const PDFS_DIR = process.env.PDFS_DIR
  ? path.resolve(process.cwd(), process.env.PDFS_DIR)
  : path.resolve(process.cwd(), './pdfs');

// ¿Cada página DEBE tener QR? (true = falla si alguna página no tiene)
const EXPECTED_QR_PER_PAGE = false;

// ¿Usar fallback a página completa si no encuentra en zonas?
// true = primero zonas, luego página completa (más lento pero seguro)
// false = solo zonas (mucho más rápido, pero puede perder QRs raros)
const USE_FULL_PAGE_FALLBACK = true;

// Esquema Zod para validar contenido del QR
const QR_VALIDATION_SCHEMA = QrUrlSchema;

// Zonas a escanear (en orden de prioridad).
// Puedes definir tus propias regiones o usar las predefinidas.
const SCAN_REGIONS: Region[] = [
  QR_REGIONS.bottomRight,   // ← Más común: esquina inferior derecha
  QR_REGIONS.topRight,      // ← Segundo más común
  QR_REGIONS.bottomLeft,
  // Descomenta si tu formato lo necesita:
  QR_REGIONS.topLeft,
  // QR_REGIONS.bottomCenter,
  // QR_REGIONS.center,
];

// ═══════════════════════════════════════════════

interface QrReport {
  pdf: string;
  totalPages: number;
  qrDetected: number;
  qrMissed: number;
  results: Array<{
    pageNumber: number;
    found: boolean;
    data: string | null;
    region?: string;
    fullPageFallback?: boolean;
  }>;
}

test.describe('Validación recursiva de PDFs y códigos QR (por zonas) ', () => {
  // Aumentar el timeout por defecto para pruebas en este archivo (ms)
  test.setTimeout(120_000 * 2);
  // Ensure folder exists and discover PDFs synchronously at module load so
  // the `for (const pdfFile of pdfFiles)` loop below registers tests per PDF.
  if (!fs.existsSync(PDFS_DIR)) {
    fs.mkdirSync(PDFS_DIR, { recursive: true });
  }

  const pdfFiles = scanPdfsSync(PDFS_DIR);

  test.beforeEach(() => {
    // start capturing console logs for each test
    startConsoleCapture(test.info(), `logs-${Date.now()}`);
  });

  test.afterEach(async () => {
    await restoreConsoleCapture(test.info());
  });

  test(`[${PDFS_DIR}] se debe encontrar al menos un PDF para validar`, () => {
    expect(
      pdfFiles.length,
      `Si hay PDFs en ${PDFS_DIR}. Agrega archivos PDF para probar.`
    ).toBeGreaterThan(0);
  });

  for (const pdfFile of pdfFiles) {
    test(` [${pdfFile.absolutePath}] PDF debe contener QR válidos`, async () => {
      // Log the full absolute path so it's visible in console and attached logs
      console.log(`\n📄 Procesando: ${pdfFile.absolutePath}`);
      console.log(`   Zonas a escanear: ${SCAN_REGIONS.map((r) => r.name).join(', ')}`);

      // 1. Convertir PDF a imágenes (con guardia de timeout)
      const pages = await withTimeout(
        convertPdfToImages(pdfFile.absolutePath, { scale: 3 }),
        60_000 * 4,
        `convertPdfToImages timed out for ${pdfFile.relativePath}`
      );

      expect(
        pages.length,
        `El PDF ${pdfFile.fileName} si tiene páginas visibles`
      ).toBeGreaterThan(0);

      console.log(`   ↳ ${pages.length} página(s) encontrada(s)`);

      let qrFoundInPdf = false;

      const report: QrReport = {
        pdf: pdfFile.relativePath,
        totalPages: pages.length,
        qrDetected: 0,
        qrMissed: 0,
        results: [],
      };

      // 2. Procesar cada página buscando QR en zonas definidas
      for (const page of pages) {
        const qr = USE_FULL_PAGE_FALLBACK
          ? await decodeQrFromImage(page.buffer, page.pageNumber, SCAN_REGIONS)
          : await decodeQrFromRegionsOnly(page.buffer, page.pageNumber, SCAN_REGIONS);

        report.results.push({
          pageNumber: page.pageNumber,
          found: qr.found,
          data: qr.data,
          region: qr.region,
          fullPageFallback: qr.fullPageFallback,
        });

        if (qr.found && qr.data) {
          qrFoundInPdf = true;
          report.qrDetected++;

          const fallbackTag = qr.fullPageFallback ? ' [fallback]' : '';
          console.log(`   ✅ Página ${page.pageNumber}: QR en zona "${qr.region}"${fallbackTag}`);
          console.log(`      Datos: ${qr.data.substring(0, 100)}${qr.data.length > 100 ? '...' : ''}`);

          // 3. Validar contenido del QR con Zod
          const validation = validateQrContent(qr.data, QR_VALIDATION_SCHEMA);

          // Replace the entire if/else block (L159-170) with:
          if (!validation.valid) {
            console.error(`      ❌ Contenido inválido: ${validation.errors?.join(', ')}`);
          }
          expect(
            validation.valid,
            `QR en página ${page.pageNumber} tiene contenido ${validation.valid ? 'válido' : 'inválido'}: ${validation.valid ? qr.data : validation.errors?.join(', ')}`
          ).toBe(true);

        } else {
          report.qrMissed++;
          console.log(`   ❌ Página ${page.pageNumber}: Sin QR detectado`);

          if (EXPECTED_QR_PER_PAGE) {
            expect(
              qr.found,
              `Se esperaba un QR en la página ${page.pageNumber} de ${pdfFile.fileName}`
            ).toBe(true);
          }
        }
      }

      // 5. Adjuntar reporte JSON al test de Playwright
      await test.info().attach('qr-report', {
        body: JSON.stringify(report, null, 2),
        contentType: 'application/json',
      });

      console.log(`   📊 Resumen: ${report.qrDetected}/${report.totalPages} páginas con QR`);

      // logs will be attached by the afterEach hook
    });
  }
});
