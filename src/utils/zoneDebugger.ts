/**
 * Script auxiliar para visualizar las zonas de QR.
 * Ejecuta: npx ts-node src/utils/zoneDebugger.ts <ruta-a-pdf>
 *
 * Genera imágenes recortadas de cada zona para que puedas verificar
 * que tus regiones están bien definidas.
 */

import * as path from 'path';
import * as fs from 'fs';
import { convertPdfToImages } from './pdfProcessor';
import { saveCroppedRegion, QR_REGIONS, Region } from './qrValidator';

const REGIONS_TO_DEBUG = Object.values(QR_REGIONS);

async function debugZones(pdfPath: string, outputDir: string = './debug-zones') {
  if (!fs.existsSync(pdfPath)) {
    console.error(`❌ PDF no encontrado: ${pdfPath}`);
    process.exit(1);
  }

  fs.mkdirSync(outputDir, { recursive: true });

  const fileName = path.basename(pdfPath, '.pdf');
  const pages = await convertPdfToImages(pdfPath, { scale: 3 });

  console.log(`🔍 Procesando ${pages.length} página(s) de "${fileName}"...`);

  for (const page of pages) {
    console.log(`\n  📄 Página ${page.pageNumber}:`);

    for (const region of REGIONS_TO_DEBUG) {
      const outFile = path.join(
        outputDir,
        `${fileName}_p${page.pageNumber}_${region.name}.png`
      );

      await saveCroppedRegion(page.buffer, region, outFile);
      console.log(`    ✅ ${region.name} → ${outFile}`);
    }
  }

  console.log(`\n🎉 Listo. Revisa las imágenes en: ${path.resolve(outputDir)}`);
  console.log('   Si tu QR no aparece en ninguna zona, ajusta las coordenadas en qrValidator.ts');
}

// CLI
const pdfPath = process.argv[2];
if (!pdfPath) {
  console.log('Uso: npx ts-node src/utils/zoneDebugger.ts <ruta-al-pdf>');
  process.exit(1);
}

debugZones(pdfPath);
