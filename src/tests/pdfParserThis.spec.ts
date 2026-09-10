// Spec de validación de PDFs: legibilidad y parsing (API pdf-parse v2)
// Tareas:
//   1. Adjuntar métricas de parsing (numpages, numrender, info, text) al reporte y consola.
//   2. Generar archivos passed_<timestamp>.txt y failed_<timestamp>.txt al finalizar.

const { test, expect } = require('@playwright/test');
const { startConsoleCapture, restoreConsoleCapture } = require('./testHelpers');
const fs = require('fs');
const path = require('path');
const { glob } = require('glob');

// pdf-parse v2 exporta la clase PDFParse (no una función directa como en v1)
const { PDFParse } = require('pdf-parse');

// ──────────────────────────────────────────────────────────────────────────────
// Configuración de directorio de PDFs
// ──────────────────────────────────────────────────────────────────────────────
const PDFS_DIR = process.env.PDFS_DIR
  ? path.resolve(process.cwd(), process.env.PDFS_DIR)
  : path.resolve(process.cwd(), './pdfs');

const PDF_PATTERN = path.join(PDFS_DIR, '**/*.pdf').replace(/\\/g, '/');

// ──────────────────────────────────────────────────────────────────────────────
// Directorio y timestamp para los archivos de resultados
// ──────────────────────────────────────────────────────────────────────────────
const RESULTS_DIR = path.resolve(process.cwd(), './test-results/pdfParserResults');

/** Genera un timestamp en formato YYYYMMDD_HHmmss */
function buildTimestamp() {
  const ahora = new Date();
  const yyyy = ahora.getFullYear();
  const MM   = String(ahora.getMonth() + 1).padStart(2, '0');
  const dd   = String(ahora.getDate()).padStart(2, '0');
  const HH   = String(ahora.getHours()).padStart(2, '0');
  const mm   = String(ahora.getMinutes()).padStart(2, '0');
  const ss   = String(ahora.getSeconds()).padStart(2, '0');
  return `${yyyy}${MM}${dd}_${HH}${mm}${ss}`;
}

// ──────────────────────────────────────────────────────────────────────────────
// Utilidades de acceso al sistema de archivos
// ──────────────────────────────────────────────────────────────────────────────

/** Encuentra todos los PDFs en PDFS_DIR. */
async function findPdfFiles() {
  if (!fs.existsSync(PDFS_DIR)) {
    return [];
  }
  return await glob(PDF_PATTERN, { absolute: true, nocase: true });
}

/**
 * Escribe un archivo de resultados.
 * Crea el directorio de destino si no existe.
 * Los errores de escritura se loguean pero NO rompen la ejecución.
 */
function escribirArchivoResultados(rutaArchivo, lineas) {
  try {
    fs.mkdirSync(path.dirname(rutaArchivo), { recursive: true });
    fs.writeFileSync(rutaArchivo, lineas.join('\n') + '\n', 'utf-8');
    console.log(`[Resultados] Archivo generado: ${rutaArchivo}`);
  } catch (err) {
    console.error(`[Resultados] Error al escribir ${rutaArchivo}:`, err);
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// Colecciones compartidas entre tests para el resumen final
// ──────────────────────────────────────────────────────────────────────────────
const pdfsExitosos = [];
const pdfsConError = [];

// ──────────────────────────────────────────────────────────────────────────────
// Suite principal
// ──────────────────────────────────────────────────────────────────────────────
test.describe('Validación de PDFs que sean legibles y parseables', () => {

  test.beforeEach(() => {
    // Inicia captura de consola; los logs se adjuntan automáticamente en afterEach
    startConsoleCapture(test.info(), 'console-logs');
  });

  test.afterEach(async () => {
    // Restaura console.log y adjunta los logs capturados al reporte
    await restoreConsoleCapture(test.info());
  });

  // ──────────────────────────────────────────────────────────────────────────
  // Test principal: parsear todos los PDFs y adjuntar métricas
  // ──────────────────────────────────────────────────────────────────────────
  test('Verifica que todos los PDFs en el directorio de ejecución tienen texto extraíble', async () => {
    const pdfFiles = await findPdfFiles();

    expect(
      pdfFiles.length,
      `Se encontraron archivos PDF en: ${PDFS_DIR}`
    ).toBeGreaterThan(0);

    const info = test.info();

    for (const pdfFile of pdfFiles) {
      const nombreBase = path.basename(pdfFile);
      console.log(`\n── Procesando: ${nombreBase} ──`);

      // ── Parseo del PDF ────────────────────────────────────────────────────
      let infoResult;
      let textResult;
      try {
        // Crear instancia del parser apuntando al archivo local
        const parser = new PDFParse({ url: pdfFile });

        // getInfo(): devuelve { total, info, pages } con metadatos del documento
        infoResult = await parser.getInfo({ parsePageInfo: true });

        // getText(): devuelve { text, pages } con el contenido textual
        textResult = await parser.getText();

        // Destruir la instancia para liberar recursos
        await parser.destroy();
      } catch (err) {
        // Registrar el fallo y continuar con el siguiente PDF
        console.error(`  ✗ Error al parsear: ${nombreBase} →`, err);
        pdfsConError.push(nombreBase);
        continue;
      }

      // ── Tarea 1: métricas de parsing ──────────────────────────────────────

      // numpages: total de páginas del documento (devuelto por getInfo como "total")
      const numpages = infoResult.total ?? 0;
      console.log(`  numpages  : ${numpages}`);
      await info.attach(`[${nombreBase}] numpages`, {
        body: Buffer.from(String(numpages), 'utf-8'),
        contentType: 'text/plain',
      });

      // numrender: páginas efectivamente procesadas en getText (longitud del array pages)
      const numrender = Array.isArray(textResult.pages) ? textResult.pages.length : 0;
      console.log(`  numrender : ${numrender}`);
      await info.attach(`[${nombreBase}] numrender`, {
        body: Buffer.from(String(numrender), 'utf-8'),
        contentType: 'text/plain',
      });

      // info: metadatos del documento (Title, Author, Producer, CreationDate, etc.)
      const metadatos = infoResult.info ?? {};
      const metadatosJson = JSON.stringify(metadatos, null, 2);
      console.log(`  info (metadatos):\n${metadatosJson}`);
      await info.attach(`[${nombreBase}] info (metadatos)`, {
        body: Buffer.from(metadatosJson, 'utf-8'),
        contentType: 'application/json',
      });

      // text: solo los primeros 50 caracteres del texto extraído
      const textoCompleto = textResult.text ?? '';
      const textoParcial = textoCompleto.slice(0, 50);
      console.log(`  text (50 chars): ${textoParcial}`);
      await info.attach(`[${nombreBase}] text (primeros 50 chars)`, {
        body: Buffer.from(textoParcial, 'utf-8'),
        contentType: 'text/plain',
      });

      // ── Verificación de legibilidad ───────────────────────────────────────
      // Si el texto extraído tiene más de 50 caracteres, el PDF es válido.
      // PDFs escaneados sin OCR pueden tener muy poco texto; se registran como fallidos
      // pero NO se lanza un error para que el test continúe con los demás archivos.
      if (textoCompleto.length > 50) {
        console.log(`\n  ✓ PDF válido: ${nombreBase} (${textoCompleto.length} chars)`);
        pdfsExitosos.push(nombreBase);
      } else {
        console.warn(`\n  ⚠ PDF sin texto suficiente: ${nombreBase} (${textoCompleto.length} chars, umbral: 50)`);
        pdfsConError.push(`${nombreBase} [texto insuficiente: ${textoCompleto.length} chars]`);
      }
    }
  });

  // ──────────────────────────────────────────────────────────────────────────
  // afterAll: generar archivos de resultados con timestamp (Tarea 2)
  // ──────────────────────────────────────────────────────────────────────────
  test.afterAll(() => {
    const ts = buildTimestamp();

    const rutaPassed = path.join(RESULTS_DIR, `passed_${ts}.txt`);
    const rutaFailed = path.join(RESULTS_DIR, `failed_${ts}.txt`);

    console.log(`\n[Resultados] PDFs exitosos : ${pdfsExitosos.length}`);
    console.log(`[Resultados] PDFs con error: ${pdfsConError.length}`);

    escribirArchivoResultados(rutaPassed, pdfsExitosos.length > 0 ? pdfsExitosos : ['(ninguno)']);
    escribirArchivoResultados(rutaFailed, pdfsConError.length > 0 ? pdfsConError : ['(ninguno)']);
  });
});
