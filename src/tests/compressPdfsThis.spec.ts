import { test, expect } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';
import { spawnSync } from 'child_process';
import { scanPdfsSync } from '../utils/fileScanner';

interface CompressReportEntry {
    file: string;
    originalBytes: number;
    newBytes: number | null;
    ok: boolean;
    error?: string;
}



test.describe('Compress PDFs with Ghostscript', () => {

    // No timeout for long-running compression
    test.setTimeout(1000 * 60 * 2); // 2'

    function findGhostscript(): { cmd: string; isWsl: boolean } | null {
        const candidates = ['gs', 'gswin64c', 'gswin32c'];
        for (const cmd of candidates) {
            try {
                let res = spawnSync(cmd, ['--version'], { encoding: 'utf8' });
                if (res && res.status === 0) return { cmd, isWsl: false };

                res = spawnSync(`${cmd} -v`, { encoding: 'utf8', shell: true });
                if (res && res.status === 0) return { cmd, isWsl: false };

                const whereCmd = process.platform === 'win32' ? 'where' : 'which';
                const which = spawnSync(whereCmd, [cmd], { encoding: 'utf8' });
                if (which && which.status === 0 && which.stdout && which.stdout.trim()) {
                    const first = which.stdout.split(/\r?\n/)[0].trim();
                    if (first) return { cmd: first, isWsl: false };
                }
            } catch (e) {
                // ignore
            }
        }

        // Fallback: check if 'wsl gs' works (for Windows environments where gs is in WSL/Ubuntu)
        try {
            const wslCheck = spawnSync('wsl', ['gs', '--version'], { encoding: 'utf8' });
            if (wslCheck && wslCheck.status === 0) {
                return { cmd: 'gs', isWsl: true };
            }
        } catch (e) {
            // ignore
        }

        return null;
    }

    function humanKb(bytes: number) {
        return Number((bytes / 1024).toFixed(2));
    }

    // Ghostscript parameter profiles (pick via env GS_PROFILE = '2'|'3'|'4')

    /* Profile 1, original, resultado: text borroso en carta porte pdfs:
    
    Ghostscript paramenters: tengo estos paramentros para comprimir un pdf pero me los esta comprimiendo borrosos: '-dCompatibilityLevel=1.4',
            '-dPDFSETTINGS=/ebook',
            '-dColorImageDownsampleType=/Bicubic',
            '-dColorImageResolution=120',
            '-dGrayImageDownsampleType=/Bicubic',
            '-dGrayImageResolution=120',
            '-dMonoImageDownsampleType=/Bicubic',
            '-dMonoImageResolution=120', como se puede arreglar esto para q no me mande los pfd comprimidos borrosos, los quiero legibles y comprimidos lo mas q se pueda
    
    
    Opción 2: Máxima compresión + legible (recomendada)
    
    Sube a 150 DPI (el estándar de /ebook) y añade compresión JPEG controlada en lugar de depender solo del downsampling:
    Qué cambia:
    150 DPI en color y escala de grises (nítido para pantalla y lectura)
    300 DPI en monocromo (texto escaneado en blanco y negro se mantiene filoso)
    JPEG con QFactor 0.5 (calidad media-alta, buena compresión sin artefactos feos)
    Subsample en monocromo (más agresivo pero el texto B/N aguanta mejor Subsample que Bicubic) 
    
    Consejo práctico
    Si no sabes si tu PDF es escaneado o tiene texto vectorial, prueba este perfile. 
    Si el archivo resultante sigue siendo muy grande, sube el QFactor a 0.7 (menos compresión JPEG) 
    o baja las resoluciones a 150. Si sigue borroso, sube a 200 DPI.
    */

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

    const GS_args12 = [
        '-sDEVICE=pdfwrite',
        '-dCompatibilityLevel=1.4',
        '-dPDFSETTINGS=/ebook',
        '-dNOPAUSE',
        '-dQUIET',
        '-dBATCH',
        // Resoluciones (ajustadas para legibilidad)
        '-dColorImageResolution=250',
        '-dGrayImageResolution=250',
        '-dMonoImageResolution=200',
        //Downsampling
        '-dColorImageDownsampleType=/Bicubic',
        '-dGrayImageDownsampleType=/Bicubic',
        '-dMonoImageDownsampleType=/Subsample',
        '-dDownsampleColorImages=true',
        '-dDownsampleGrayImages=true',
        '-dDownsampleMonoImages=true',
        // Optimización de fuentes y duplicados
        '-dSubsetFonts=true',
        '-dCompressFonts=true',
        '-dDetectDuplicateImages=true'
    ];


    /* Si el texto sigue borroso (PDFs escaneados)
    Si tu PDF es un escaneo (todo es imagen), sube todo a 200 DPI y usa calidad JPEG más alta: */

    const GS_args3 = [
        '-sDEVICE=pdfwrite',
        '-dCompatibilityLevel=1.4',
        '-dNOPAUSE',
        '-dQUIET',
        '-dBATCH',
        '-dColorImageResolution=200',
        '-dGrayImageResolution=200',
        '-dMonoImageResolution=200',
        '-dColorImageDownsampleType=/Bicubic',
        '-dGrayImageDownsampleType=/Bicubic',
        '-dMonoImageDownsampleType=/Bicubic',
        '-dDownsampleColorImages=true',
        '-dDownsampleGrayImages=true',
        '-dDownsampleMonoImages=true',
        '-dAutoFilterColorImages=false',
        '-dAutoFilterGrayImages=false',
        '-dColorImageFilter=/DCTEncode',
        '-dGrayImageFilter=/DCTEncode',
        '-dSubsetFonts=true',
        '-dCompressFonts=true',
        '-dDetectDuplicateImages=true'
    ];


    /*  Si necesitas el archivo muy pequeño y el contenido es mayormente texto vectorial
     Si el PDF tiene texto real (no escaneado), no necesitas tocar las imágenes tanto. Enfócate en fuentes y estructura:
   */

    const GS_args4 = [
        '-sDEVICE=pdfwrite',
        '-dCompatibilityLevel=1.4',
        '-dPDFSETTINGS=/ebook',
        '-dNOPAUSE',
        '-dQUIET',
        '-dBATCH',
        '-dSubsetFonts=true',
        '-dCompressFonts=true',
        '-dDetectDuplicateImages=true',
        '-dRemoveUnusedResources=true',
        '-dPreserveHalftoneInfo=false',
        '-dPreserveOverprintSettings=false',
        '-dUCRandBGInfo=/Remove'
    ];

    function toWslPath(p: string): string {
        return p.replace(/^([a-zA-Z]):[\\\/]/, (m, drive) => '/mnt/' + drive.toLowerCase() + '/').replace(/\\/g, '/');
    }

    const cwd = process.cwd();
    const gsInfo = findGhostscript();

    if (!gsInfo) {
        const diag: string[] = [];
        diag.push('Ghostscript not found via findGhostscript()');
        diag.push(`process.platform=${process.platform}`);
        diag.push(`process.env.PATH=${process.env.PATH}`);
        try {
            const r1 = spawnSync('gs -v', { encoding: 'utf8', shell: true });
            diag.push('--- gs -v (shell) ---');
            diag.push(`status=${r1 && typeof r1.status !== 'undefined' ? r1.status : 'N/A'}`);
            if (r1 && r1.stdout) diag.push(`stdout:\n${r1.stdout}`);
            if (r1 && r1.stderr) diag.push(`stderr:\n${r1.stderr}`);
        } catch (e) {
            diag.push(`gs -v spawn exception: ${String(e)}`);
        }
        try {
            const whereCmd = process.platform === 'win32' ? 'where' : 'which';
            const r2 = spawnSync(whereCmd, ['gs'], { encoding: 'utf8' });
            diag.push(`--- ${whereCmd} gs ---`);
            diag.push(`status=${r2 && typeof r2.status !== 'undefined' ? r2.status : 'N/A'}`);
            if (r2 && r2.stdout) diag.push(`stdout:\n${r2.stdout}`);
            if (r2 && r2.stderr) diag.push(`stderr:\n${r2.stderr}`);
        } catch (e) {
            diag.push(`which/where spawn exception: ${String(e)}`);
        }

        // Attach diagnostics to Playwright report to help debugging PATH differences
        test.info().attach('gs-diagnostics.txt', {
            body: diag.join('\n'),
            contentType: 'text/plain',
        });

        test.skip(true, 'Ghostscript not found on PATH (diagnostics attached)');
        return;
    }

    const pdfFiles = scanPdfsSync(cwd);

    //expect(pdfFiles.length, `PDFs found under ${cwd}`).toBeGreaterThan(0);

    const results: {
        total: number;
        ok: number;
        fail: number;
        report: CompressReportEntry[];
        logs: string[]
    }[] = [];

    test('Verify PDFs exist on ./pdfs folder', () => {
        expect(pdfFiles.length, `PDFs found under ${cwd}`).toBeGreaterThan(0);
    });

    for (const pdf of pdfFiles) {
        test(`Compress ${pdf.relativePath}`, async ({ }) => {

            const report: CompressReportEntry[] = [];
            let ok = 0, fail = 0;

            const input = pdf.absolutePath;
            let logs: string[] = [`Processing: ${input}`];
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

            // Select Ghostscript profile via env GS_PROFILE ('2'|'3'|'4')
            const profile = process.env.GS_PROFILE || '2';
            let profileArgs: string[];
            if (profile === '2') profileArgs = GS_args2;
            else if (profile === '3') profileArgs = GS_args3;
            else if (profile === '4') profileArgs = GS_args4;
            else profileArgs = GS_args2;

            let res;
            try {
                if (gsInfo.isWsl) {
                    const wslInput = toWslPath(input);
                    const wslTmp = toWslPath(tmp);
                    const wslArgs = [...profileArgs, `-sOutputFile=${wslTmp}`, wslInput];
                    res = spawnSync('wsl', ['gs', ...wslArgs], { encoding: 'utf8' });
                } else {
                    const args = [...profileArgs, `-sOutputFile=${tmp}`, input];
                    res = spawnSync(gsInfo.cmd, args, { encoding: 'utf8' });
                }

                if (res.status === 0) {
                    // verify tmp exists
                    if (fs.existsSync(tmp)) {
                        const newSize = fs.statSync(tmp).size;
                        if (newSize < original) {
                            fs.renameSync(tmp, input);
                            const reduction = original > 0 ? Math.round(((original - newSize) * 100) / original) : 0;
                            const msg = `  ✓ ${humanKb(original)} KB -> ${humanKb(newSize)} KB (${reduction}% less)`;
                            logs.push(msg);
                            console.log(`Processing: ${input}\n${msg}`);
                            report.push({ file: input, originalBytes: original, newBytes: newSize, ok: true });
                            ok++;
                        } else {
                            fs.unlinkSync(tmp); // discard compressed, keep original
                            const msg = `  ⚠ ${humanKb(original)} KB -> ${humanKb(newSize)} KB (NO reduction, original kept)`;
                            logs.push(msg);
                            console.log(`Processing: ${input}\n${msg}`);
                            report.push({ file: input, originalBytes: original, newBytes: newSize, ok: true });
                        }
                    } else {
                        const msg = '  ✗ Temporary file not created or empty';
                        logs.push(msg);
                        console.log(`Processing: ${input}\n${msg}`);
                        report.push({ file: input, originalBytes: original, newBytes: null, ok: false, error: 'tmp missing' });
                        fail++;
                    }
                } else {
                    const failMsg = `  ✗ Ghostscript failed (exit ${res.status})`;
                    logs.push(failMsg);
                    if (res.stdout) logs.push(res.stdout);
                    if (res.stderr) logs.push(res.stderr);
                    console.log(`Processing: ${input}\n${failMsg}\n${res.stdout || ''}\n${res.stderr || ''}`);
                    report.push({ file: input, originalBytes: original, newBytes: null, ok: false, error: `exit ${res.status}` });
                    // cleanup
                    try { if (fs.existsSync(tmp)) fs.unlinkSync(tmp); } catch (e) { }
                    fail++;
                }
            } catch (err) {
                logs.push(`  ✗ Exception while running Ghostscript: ${String(err)}`);
                report.push({ file: input, originalBytes: original, newBytes: null, ok: false, error: String(err) });
                try { if (fs.existsSync(tmp)) fs.unlinkSync(tmp); } catch (e) { }
                fail++;
            }

            //const summary = { total, ok, fail, details: report };

            results.push({ total: 1, ok: ok, fail: fail, report: report, logs: logs });

            // Attach report and logs to Playwright report
            await test.info().attach('gs-compress-report.json', {
                body: JSON.stringify(results, null, 2),
                contentType: 'application/json',
            });

            await test.info().attach('gs-compress-log.txt', {
                body: logs.join('\n'),
                contentType: 'text/plain',
            });

            // Assert that there were no failures
            expect(fail, `Checking if some PDFs failed to compress. See attached 'gs-compress-log.txt'`).toBe(0);
        });
    }




});
