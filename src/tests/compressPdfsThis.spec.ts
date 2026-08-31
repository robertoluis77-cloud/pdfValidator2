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

test.describe('Compress PDFs with Ghostscript', () => {

    // No timeout for long-running compression
    test.setTimeout(1000 * 60 * 2); // 2'

    const PDFS_DIR = process.env.PDFS_DIR
        ? path.resolve(process.cwd(), process.env.PDFS_DIR)
        : path.resolve(process.cwd(), './pdfs');

    const pdfFiles = scanPdfsSync(PDFS_DIR);

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

            const report: CompressReportEntry[] = [];
            let failed = false;

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
});
