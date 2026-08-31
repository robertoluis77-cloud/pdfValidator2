import { spawnSync, spawn } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';

// ─────────────────────────────────────────────────────────────────────────────
// Ghostscript discovery
// ─────────────────────────────────────────────────────────────────────────────

export interface GsInfo {
    cmd: string;
    isWsl: boolean;
}

/**
 * Resolve candidate Ghostscript full paths from well-known Windows install
 * directories (the Ghostscript Windows installer puts binaries under
 * C:\Program Files\gs\gs<version>\bin\ but does NOT always add them to PATH).
 */
function windowsGsCandidates(): string[] {
    if (process.platform !== 'win32') return [];
    const candidates: string[] = [];
    const roots = [
        path.join('C:\\', 'Program Files', 'gs'),
        path.join('C:\\', 'Program Files (x86)', 'gs'),
    ];
    for (const root of roots) {
        if (!fs.existsSync(root)) continue;
        for (const entry of fs.readdirSync(root)) {
            const bin = path.join(root, entry, 'bin');
            if (!fs.existsSync(bin)) continue;
            for (const exe of ['gswin64c.exe', 'gswin32c.exe', 'gs.exe']) {
                const full = path.join(bin, exe);
                if (fs.existsSync(full)) candidates.push(full);
            }
        }
    }
    return candidates;
}

/**
 * Probe the host for a working Ghostscript binary.
 * Returns null when Ghostscript cannot be located.
 */
export function findGhostscript(): GsInfo | null {
    const candidates = ['gs', 'gswin64c', 'gswin32c'];
    for (const cmd of candidates) {
        try {
            const res = spawnSync(cmd, ['--version'], { encoding: 'utf8' });
            if (res && res.status === 0) return { cmd, isWsl: false };
        } catch {
            // ignore
        }
    }

    // On Windows, also probe well-known install paths that may not be on PATH
    for (const fullPath of windowsGsCandidates()) {
        try {
            const res = spawnSync(fullPath, ['--version'], { encoding: 'utf8' });
            if (res && res.status === 0) return { cmd: fullPath, isWsl: false };
        } catch {
            // ignore
        }
    }

    // Fallback: check if 'wsl gs' works (Windows environments where gs is in WSL/Ubuntu)
    try {
        const wslCheck = spawnSync('wsl', ['gs', '--version'], { encoding: 'utf8' });
        if (wslCheck && wslCheck.status === 0) {
            return { cmd: 'gs', isWsl: true };
        }
    } catch {
        // ignore
    }

    return null;
}

/**
 * Collect diagnostic strings explaining why Ghostscript was not found.
 * Safe to call at any time — does not throw.
 */
export function collectGsDiagnostics(): string {
    const diag: string[] = [];
    diag.push('Ghostscript not found via findGhostscript()');
    diag.push(`process.platform=${process.platform}`);
    diag.push(`process.env.PATH=${process.env.PATH}`);
    try {
        const whereCmd = process.platform === 'win32' ? 'where' : 'which';
        for (const cmd of ['gs', 'gswin64c', 'gswin32c']) {
            const r = spawnSync(whereCmd, [cmd], { encoding: 'utf8' });
            diag.push(`--- ${whereCmd} ${cmd} ---`);
            diag.push(`status=${r && typeof r.status !== 'undefined' ? r.status : 'N/A'}`);
            if (r && r.stdout) diag.push(`stdout:\n${r.stdout}`);
            if (r && r.stderr) diag.push(`stderr:\n${r.stderr}`);
        }
    } catch (e) {
        diag.push(`where/which spawn exception: ${String(e)}`);
    }
    // Report which well-known Windows paths were scanned
    if (process.platform === 'win32') {
        const winCandidates = windowsGsCandidates();
        diag.push('--- Windows install path candidates ---');
        if (winCandidates.length > 0) {
            diag.push(winCandidates.join('\n'));
        } else {
            diag.push('None found under C:\\Program Files\\gs or C:\\Program Files (x86)\\gs');
        }
        diag.push('--- install Ghostscript ---');
        diag.push('Download from https://www.ghostscript.com/releases/gsdnld.html');
        diag.push('Or via Chocolatey: choco install ghostscript');
        diag.push('Or via Scoop:      scoop install ghostscript');
    }
    return diag.join('\n');
}

// ─────────────────────────────────────────────────────────────────────────────
// Ghostscript compression profiles
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Named compression profiles for Ghostscript.
 * Select via the GS_PROFILE env var: '2' | '12' | '3' | '4' (default: '2').
 *
 * Profile 2  – scanned docs: no downsampling, high-quality JPEG, lossless mono
 * Profile 12 – balanced: /ebook preset + 250 DPI bicubic downsampling
 * Profile 3  – scanned docs with blurring issues: 200 DPI bicubic all channels
 * Profile 4  – vector/text PDFs: /ebook + font optimisation only
 */
export const GS_PROFILES: Record<string, string[]> = {
    '2': [
        '-sDEVICE=pdfwrite',
        '-dCompatibilityLevel=1.4',
        '-dNOPAUSE',
        '-dQUIET',
        '-dBATCH',
        '-dDownsampleColorImages=true',
        '-dDownsampleGrayImages=true',
        '-dDownsampleMonoImages=false',
        '-dAutoFilterColorImages=true',
        '-dAutoFilterGrayImages=true',
        '-dColorImageFilter=/DCTEncode',
        '-dGrayImageFilter=/DCTEncode',
        '-dMonoImageFilter=/CCITTFaxEncode',
        '-dSubsetFonts=true',
        '-dCompressFonts=true',
        '-dDetectDuplicateImages=true',
        '-dCompressPages=true',
    ],
    '12': [
        '-sDEVICE=pdfwrite',
        '-dCompatibilityLevel=1.4',
        '-dPDFSETTINGS=/ebook',
        '-dNOPAUSE',
        '-dQUIET',
        '-dBATCH',
        '-dColorImageResolution=250',
        '-dGrayImageResolution=250',
        '-dMonoImageResolution=200',
        '-dColorImageDownsampleType=/Bicubic',
        '-dGrayImageDownsampleType=/Bicubic',
        '-dMonoImageDownsampleType=/Subsample',
        '-dDownsampleColorImages=true',
        '-dDownsampleGrayImages=true',
        '-dDownsampleMonoImages=true',
        '-dSubsetFonts=true',
        '-dCompressFonts=true',
        '-dDetectDuplicateImages=true',
    ],
    '3': [
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
        '-dDetectDuplicateImages=true',
    ],
    '4': [
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
        '-dUCRandBGInfo=/Remove',
    ],
};

// ─────────────────────────────────────────────────────────────────────────────
// Async Ghostscript runner
// ─────────────────────────────────────────────────────────────────────────────

export interface GsResult {
    status: number;
    stdout: string;
    stderr: string;
}

/**
 * Run Ghostscript asynchronously, freeing the Node.js event loop during
 * compression (important when Playwright runs tests with fullyParallel=true).
 */
export function runGhostscript(cmd: string, args: string[]): Promise<GsResult> {
    return new Promise((resolve, reject) => {
        const proc = spawn(cmd, args);
        let stdout = '';
        let stderr = '';
        proc.stdout.on('data', (chunk: Buffer) => { stdout += chunk.toString(); });
        proc.stderr.on('data', (chunk: Buffer) => { stderr += chunk.toString(); });
        proc.on('close', (code: number | null) => resolve({ status: code ?? 1, stdout, stderr }));
        proc.on('error', reject);
    });
}

// ─────────────────────────────────────────────────────────────────────────────
// Misc helpers
// ─────────────────────────────────────────────────────────────────────────────

/** Format bytes as kilobytes rounded to 2 decimal places. */
export function humanKb(bytes: number): number {
    return Number((bytes / 1024).toFixed(2));
}

/** Convert a Windows absolute path to a WSL mount path (e.g. C:\foo → /mnt/c/foo). */
export function toWslPath(p: string): string {
    return p
        .replace(/^([a-zA-Z]):[\\\/]/, (_m, drive: string) => `/mnt/${drive.toLowerCase()}/`)
        .replace(/\\/g, '/');
}
