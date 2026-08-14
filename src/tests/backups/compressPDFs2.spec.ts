import { test, expect } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';
import { spawnSync } from 'child_process';
import { scanPdfsSync } from '../../utils/fileScanner';

interface CompressReportEntry {
    file: string;
    originalBytes: number;
    newBytes: number | null;
    ok: boolean;
    error?: string;
}

function findGhostscript(): { cmd: string; isWsl: boolean } | null {
    // ... (misma función de detección)
    try {
        const wslCheck = spawnSync('wsl', ['gs', '--version'], { encoding: 'utf8' });
        if (wslCheck && wslCheck.status === 0) {
            return { cmd: 'gs', isWsl: true };
        }
    } catch (e) { }
    return null;
}

function toWslPath(p: string): string {
    return p.replace(/^([a-zA-Z]):[\\\/]/, (m, drive) => '/mnt/' + drive.toLowerCase() + '/').replace(/\\/g, '/');
}

const GS_args1 = [
    '-sDEVICE=pdfwrite',
    '-dCompatibilityLevel=1.4',
    '-dNOPAUSE',
    '-dQUIET',
    '-dBATCH',
    '-dDownsampleColorImages=false',
    '-dDownsampleGrayImages=false',
    '-dDownsampleMonoImages=false',
    '-dSubsetFonts=true',
    '-dCompressFonts=true',
    '-dDetectDuplicateImages=true',
    '-dCompressPages=true'
];

const GS_args2 = [
    '-sDEVICE=pdfwrite',
    '-dCompatibilityLevel=1.4',
    '-dNOPAUSE',
    '-dQUIET',
    '-dBATCH',
    
    //# === NO usar PDFSETTINGS (sobreescribe resoluciones y destruye escaneos) ===
    //# '-dPDFSETTINGS=/ebook',  ← ELIMINAR
    
    //# === Para documentos escaneados: NO hacer downsampling ===
    //# Mantiene la resolución original del escaneo (típicamente 200-300 DPI)
    '-dDownsampleColorImages=true',
    '-dDownsampleGrayImages=true',
    '-dDownsampleMonoImages=false',
    
    //# === Compresión JPEG con calidad alta (sin perder resolución) ===
    '-dAutoFilterColorImages=true',
    '-dAutoFilterGrayImages=true',
    '-dColorImageFilter=/DCTEncode',
    '-dGrayImageFilter=/DCTEncode',
    
    //# === Imágenes monocromo (1-bit): compresión sin pérdida ===
    '-dMonoImageFilter=/CCITTFaxEncode',
    //'-dMonoImageDict=<< /K -1 /Columns 1728 >>',
    
    //# === Optimización de fuentes y estructura ===
    '-dSubsetFonts=true',
    '-dCompressFonts=true',
    '-dDetectDuplicateImages=true',
    '-dCompressPages=true'
];

test.describe('Compress PDFs in parallel with Ghostscript', () => {
    test.setTimeout(1000 * 60 * 2);

    const cwd = process.cwd();
    const pdfFiles = scanPdfsSync(cwd);

    expect(pdfFiles.length, `PDFs found under ${cwd}`).toBeGreaterThan(0);
    
    const gsInfo = findGhostscript();

    const report: CompressReportEntry[] = [];
    let fail = 0;

    // Generar un test independiente por cada PDF para que Playwright use los workers en paralelo
    for (const pdf of pdfFiles) {
        test(`Compress ${pdf.relativePath}`, async () => {
            if (!gsInfo) {
                test.skip(true, 'Ghostscript not found');
                return;
            }

            const input = pdf.absolutePath;
            const logs: string[] = [];
            logs.push(`Processing: ${input}`);

            let original = 0;
            try {
                original = fs.statSync(input).size;
            } catch (e) {
                logs.push(`  Error reading original size: ${String(e)}`);
            }

            const dirName = path.dirname(input);
            const base = path.basename(input);
            const tmp = path.join(dirName, `.tmp_compressed_${Date.now()}_${base}`);

            let res;
            try {
                if (gsInfo.isWsl) {
                    const wslInput = toWslPath(input);
                    const wslTmp = toWslPath(tmp);
                    const wslArgs = [...GS_args2, `-sOutputFile=${wslTmp}`, wslInput];
                    res = spawnSync('wsl', ['gs', ...wslArgs], { encoding: 'utf8' });
                } else {
                    const args = [...GS_args2, `-sOutputFile=${tmp}`, input];
                    res = spawnSync(gsInfo.cmd, args, { encoding: 'utf8' });
                }

                if (res.status === 0) {
                    if (fs.existsSync(tmp)) {
                        const newSize = fs.statSync(tmp).size;
                        fs.renameSync(tmp, input);
                        const reduction = original > 0 ? Math.round(((original - newSize) * 100) / original) : 0;
                        const msg = `  ✓ ${Number((original / 1024).toFixed(2))} KB -> ${Number((newSize / 1024).toFixed(2))} KB (${reduction}% less)`;
                        logs.push(msg);
                        console.log(`Processing: ${input}\n${msg}`);
                        report.push({ file: input, originalBytes: original, newBytes: newSize, ok: true });
                    } else {
                        const msg = '  ✗ Temporary file not created or empty';
                        logs.push(msg);
                        console.log(`Processing: ${input}\n${msg}`);
                        report.push({ file: input, originalBytes: original, newBytes: null, ok: false, error: 'tmp missing' });
                        fail++;
                        throw new Error(msg);
                    }
                } else {
                    const failMsg = `  ✗ Ghostscript failed (exit ${res.status})`;
                    logs.push(failMsg);
                    if (res.stdout) logs.push(res.stdout);
                    if (res.stderr) logs.push(res.stderr);
                    console.log(`Processing: ${input}\n${failMsg}\n${res.stdout || ''}\n${res.stderr || ''}`);
                    report.push({ file: input, originalBytes: original, newBytes: null, ok: false, error: `exit ${res.status}` });
                    try { if (fs.existsSync(tmp)) fs.unlinkSync(tmp); } catch (e) { }
                    fail++;
                    throw new Error(failMsg);
                }
            } catch (err) {
                logs.push(`  ✗ Exception while running Ghostscript: ${String(err)}`);
                report.push({ file: input, originalBytes: original, newBytes: null, ok: false, error: String(err) });
                try { if (fs.existsSync(tmp)) fs.unlinkSync(tmp); } catch (e) { }
                fail++;
                throw err;
            }

            await test.info().attach(`gs-compress-log-${base}.txt`, {
                body: logs.join('\n'),
                contentType: 'text/plain',
            });
        });
    }
});