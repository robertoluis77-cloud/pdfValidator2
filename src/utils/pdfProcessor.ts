import * as fs from 'fs';

export interface PdfPageImage {
  pageNumber: number;
  buffer: Buffer;
}

/**
 * Convierte cada página de un PDF a una imagen PNG (Buffer).
 * `scale` controla la resolución (mayor = mejor detección de QR).
 */
export async function convertPdfToImages(
  pdfPath: string,
  options: { scale?: number } = {}
): Promise<PdfPageImage[]> {
  if (!fs.existsSync(pdfPath)) {
    throw new Error(`PDF no encontrado: ${pdfPath}`);
  }

  // Use a runtime dynamic import via eval to ensure Node's native ESM loader
  // is used even when TypeScript compiles modules to CommonJS. This avoids
  // errors like "require() cannot be used on an ESM graph with top-level await".
  // Provide explicit, actionable error messages if the dynamic import fails.
  let pdfModule: any;
  try {
    // eslint-disable-next-line no-eval
    pdfModule = await 'import("pdf-to-img")';
  } catch (err: any) {
    const errMsg = (err && (err.message || String(err))) || 'unknown error';
    const message = [
      'Failed to load ESM module "pdf-to-img" required to convert PDF to images.',
      `Error: ${errMsg}`,
      '',
      'Likely causes and remedies:',
      '- The project is compiled/loaded as CommonJS while "pdf-to-img" is ESM-only.',
      '- Migrate the project to ESM: add "type": "module" to package.json and set',
      '  "module": "nodenext" or "esnext" in tsconfig.json; update imports accordingly.',
      '- Alternatively, run this functionality in a separate ESM process or use a different PDF-to-image tool that supports CommonJS.',
      '',
      'If you want, I can prepare an ESM migration patch or add a fallback wrapper.'];

    console.error(message.join('\n'));
    throw new Error(message.join('\n'));
  }
  const { pdf } = pdfModule;
  const scale = options.scale ?? 2.5;
  const document = await pdf(pdfPath, { scale });

  const pages: PdfPageImage[] = [];
  let pageNumber = 1;

  for await (const image of document) {
    // Para obtener dimensiones necesitamos leer la imagen con Jimp
    // Pero lo hacemos lazy en qrValidator para no duplicar trabajo
    pages.push({
      pageNumber,
      buffer: image
    });
    pageNumber++;
  }

  return pages;
}
