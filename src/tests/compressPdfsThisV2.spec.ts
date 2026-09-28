import { test, expect } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';
import { scanPdfsSync } from '../utils/fileScanner';
import {
    findGhostscript,
    collectGsDiagnostics,
    GS_PROFILES,
    GsInfo,
    humanKb,
    toWslPath,
    runGhostscript,
} from '../utils/ghostscript';

// pdf-parse v2 exporta la clase PDFParse (no una función directa como en v1)
const { PDFParse } = require('pdf-parse');

// ──────────────────────────────────────────────────────────────────────────────
// Directorio y timestamp para los archivos de resultados
// ──────────────────────────────────────────────────────────────────────────────
const RESULTS_DIR = path.resolve(process.cwd(), './shellScriptResults/compressPdfsResults');

/**
 * Escribe un archivo de resultados.
 * Crea el directorio de destino si no existe.
 * Los errores de escritura se loguean pero NO rompen la ejecución.
 */
function escribirArchivoResultados(rutaArchivo: string, lineas: string[]) {
    try {
        fs.mkdirSync(path.dirname(rutaArchivo), { recursive: true });
        fs.writeFileSync(rutaArchivo, lineas.join('\n') + '\n', 'utf-8');
        console.log(`[Resultados] Archivo generado: ${rutaArchivo}`);
    } catch (err) {
        console.error(`[Resultados] Error al escribir ${rutaArchivo}:`, err);
    }
}

test.describe('Compress PDFs with Ghostscript', () => {

    // No timeout for long-running compression
    test.setTimeout(1000 * 60 * 2); // 2'

    const PDFS_DIR = process.env.PDFS_DIR
        ? path.resolve(process.cwd(), process.env.PDFS_DIR)
        : path.resolve(process.cwd(), './pdfs');

    const pdfFiles = scanPdfsSync(PDFS_DIR);

    // Frase a buscar (case-insensitive): los PDFs que la contienen NO se comprimen
    const FRASE_BUSCADA = 'estado de cuenta';

    // Colección compartida: rutas (desde ./pdfs) de los PDFs omitidos por la comprobación previa
    const skippedEstadosDeCuenta: string[] = [];

    // Ghostscript info resolved once before any test runs
    let gsInfo: GsInfo | null = null;

    test.beforeAll(async ({}, testInfo) => {
        gsInfo = findGhostscript();
        if (!gsInfo) {
            await testInfo.attach('gs-diagnostics.txt', {
                body: collectGsDiagnostics(),
                contentType: 'text/plain',
            });
        }
    });

    interface CompressReportEntry {
        file: string;
        originalBytes: number;
        newBytes: number | null;
        ok: boolean;
        error?: string;
    }

    test('Verify PDFs exist on ./pdfs folder', () => {
        expect(pdfFiles.length, `PDFs found under ${PDFS_DIR}`).toBeGreaterThan(0);
    });

    for (const pdf of pdfFiles) {
        test(`Compress ${pdf.relativePath}`, async ({}, testInfo) => {

            if (!gsInfo) {
                test.skip(true, 'Ghostscript not found on PATH (diagnostics attached to beforeAll)');
                return;
            }

            const input = pdf.absolutePath;
            const logs: string[] = [];
            logs.push(`Processing: ${input}`);
            logs.push(`Using Ghostscript: ${gsInfo.cmd} (isWsl: ${gsInfo.isWsl})`);

            let original = 0;
            try {
                original = fs.statSync(input).size;
            } catch (e) {
                logs.push(`  Error reading original size: ${String(e)}`);
            }

            const dirName = path.dirname(input);
            const base = path.basename(input);
            const tmp = path.join(dirName, `.tmp_compressed_${Date.now()}_${base}`);

            // Select Ghostscript profile via env GS_PROFILE ('2'|'12'|'3'|'4', default '2')
            const profileKey = process.env.GS_PROFILE ?? '2';
            const profileArgs = GS_PROFILES[profileKey] ?? GS_PROFILES['2'];
            console.log('GS Profile used: ',profileKey);

            const report: CompressReportEntry[] = [];
            let failed = false;

            // ── Comprobación previa a la compresión ───────────────────────────
            // Si el PDF contiene la frase "estado de cuenta" (case-insensitive),
            // se omite la compresión y el archivo NO se modifica en absoluto.
            let shouldSkip = false;
            try {
                const parser = new PDFParse({ url: input });
                const textResult = await parser.getText();
                await parser.destroy();
                shouldSkip = (textResult.text ?? '').toLowerCase().includes(FRASE_BUSCADA);
            } catch (err) {
                // Si falla la lectura del texto, NO se omite: se continúa con la compresión
                console.warn(`  ⚠ No se pudo leer el texto para la comprobación previa: ${pdf.relativePath} → ${String(err)}`);
            }

            if (shouldSkip) {
                console.log(`  🔍 Frase "${FRASE_BUSCADA}" encontrada (case-insensitive): ${pdf.relativePath} → compresión omitida`);
                const rutaDesdePdfs = './pdfs/' + path.relative(path.resolve(process.cwd(), './pdfs'), input).replace(/\\/g, '/');
                skippedEstadosDeCuenta.push(rutaDesdePdfs);
                test.skip(true, `Contiene la frase "${FRASE_BUSCADA}" (case-insensitive); compresión omitida, archivo sin modificar`);
                return;
            }

            try {
                let res;
                if (gsInfo.isWsl) {
                    const wslInput = toWslPath(input);
                    const wslTmp = toWslPath(tmp);
                    res = await runGhostscript('wsl', ['gs', ...profileArgs, `-sOutputFile=${wslTmp}`, wslInput]);
                } else {
                    res = await runGhostscript(gsInfo.cmd, [...profileArgs, `-sOutputFile=${tmp}`, input]);
                }

                if (res.status === 0) {
                    if (fs.existsSync(tmp)) {
                        const newSize = fs.statSync(tmp).size;
                        if (newSize < original) {
                            fs.renameSync(tmp, input);
                            const reduction = original > 0 ? Math.round(((original - newSize) * 100) / original) : 0;
                            const msg = `  ✓ SUCCESS ${humanKb(original)} KB -> ${humanKb(newSize)} KB (${reduction}% less)`;
                            logs.push(msg);
                            console.log(`Processing: ${input}\n${msg}`);
                            report.push({ file: input, originalBytes: original, newBytes: newSize, ok: true });
                        } else {
                            fs.unlinkSync(tmp); // discard compressed, keep original
                            const msg = `  ⚠ SKIPPED ${humanKb(original)} KB -> ${humanKb(newSize)} KB (NO reduction, original kept)`;
                            logs.push(msg);
                            console.log(`Processing: ${input}\n${msg}`);
                            report.push({ file: input, originalBytes: original, newBytes: newSize, ok: true });
                        }
                    } else {
                        const msg = '  ✗ Temporary file not created or empty';
                        logs.push(msg);
                        console.log(`Processing: ${input}\n${msg}`);
                        report.push({ file: input, originalBytes: original, newBytes: null, ok: false, error: 'tmp missing' });
                        failed = true;
                    }
                } else {
                    const failMsg = `  ✗ Ghostscript failed (exit ${res.status})`;
                    logs.push(failMsg);
                    if (res.stdout) logs.push(res.stdout);
                    if (res.stderr) logs.push(res.stderr);
                    console.log(`Processing: ${input}\n${failMsg}\n${res.stdout || ''}\n${res.stderr || ''}`);
                    report.push({ file: input, originalBytes: original, newBytes: null, ok: false, error: `exit ${res.status}` });
                    try { if (fs.existsSync(tmp)) fs.unlinkSync(tmp); } catch { }
                    failed = true;
                }
            } catch (err) {
                logs.push(`  ✗ Exception while running Ghostscript: ${String(err)}`);
                report.push({ file: input, originalBytes: original, newBytes: null, ok: false, error: String(err) });
                try { if (fs.existsSync(tmp)) fs.unlinkSync(tmp); } catch { }
                failed = true;
            }

            // Attach per-test report and logs
            await testInfo.attach('gs-compress-report.json', {
                body: JSON.stringify(report, null, 2),
                contentType: 'application/json',
            });

            await testInfo.attach('gs-compress-log.txt', {
                body: logs.join('\n'),
                contentType: 'text/plain',
            });

            // Assert no failure for this file
            expect(failed, `PDF compression successfull. See attached 'gs-compress-log.txt'`).toBe(false);
        });
    }

    // ──────────────────────────────────────────────────────────────────────────
    // afterAll: generar/mantener el archivo de PDFs omitidos por la comprobación previa
    // ──────────────────────────────────────────────────────────────────────────
    test.afterAll(() => {
        const rutaSkipped = path.join(RESULTS_DIR, 'skippedEstadosDeCuentaPDFs.txt');

        // Con múltiples workers, afterAll se ejecuta una vez por worker; cada worker
        // combina las rutas ya presentes en el archivo con las detectadas en su grupo,
        // de modo que el archivo final contiene TODOS los PDFs omitidos.
        const rutas = new Set<string>();
        try {
            if (fs.existsSync(rutaSkipped)) {
                for (const linea of fs.readFileSync(rutaSkipped, 'utf-8').split('\n')) {
                    if (linea.startsWith('   📁 ')) rutas.add(linea);
                }
            }
        } catch { /* si no se puede leer, se parte de la lista vacía */ }
        for (const ruta of skippedEstadosDeCuenta) rutas.add(`   📁 ${ruta}`);
        const rutasFinales = Array.from(rutas).sort();

        const lineasSkipped: string[] = [
            '========================================',
            '🔍 Buscando archivos PDF que sean Estados de Cuentas de bancos',
            '========================================',
            '',
            '📄 Archivos PDF omitidos en la compresión por contener estados de cuentas (rutas desde ./pdfs):',
            ...(rutasFinales.length > 0 ? rutasFinales : ['   (ninguno)']),
        ];

        console.log(`\n[Resultados] PDFs omitidos (estados de cuenta) : ${skippedEstadosDeCuenta.length} (total acumulado: ${rutasFinales.length})`);

        // Escritura atómica: archivo temporal + rename para evitar corrupción entre workers
        try {
            fs.mkdirSync(path.dirname(rutaSkipped), { recursive: true });
            const tmp = path.join(path.dirname(rutaSkipped), `.tmp_skipped_${Date.now()}_${path.basename(rutaSkipped)}`);
            fs.writeFileSync(tmp, lineasSkipped.join('\n') + '\n', 'utf-8');
            fs.renameSync(tmp, rutaSkipped);
            console.log(`[Resultados] Archivo generado: ${rutaSkipped}`);
        } catch (err) {
            console.error(`[Resultados] Error al escribir ${rutaSkipped}:`, err);
        }
    });
});
