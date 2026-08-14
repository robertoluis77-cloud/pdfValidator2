import { glob } from 'glob';
import * as path from 'path';

export interface PdfFile {
  absolutePath: string;
  relativePath: string;
  fileName: string;
}

/**
 * Escanea recursivamente una carpeta buscando archivos PDF.
 */
export async function scanPdfs(directory: string): Promise<PdfFile[]> {
  const pattern = path.join(directory, '**/*.pdf').replace(/\\/g, '/');
  // Use case-insensitive matching so files like *.PDF are included on case-sensitive filesystems
  const files = await glob(pattern, { absolute: true, nocase: true });

  return files.map((file) => ({
    absolutePath: file,
    relativePath: path.relative(directory, file),
    fileName: path.basename(file),
  }));
}

export function scanPdfsSync(directory: string): PdfFile[] {
  const pattern = path.join(directory, '**/*.pdf').replace(/\\/g, '/');
  const files = glob.sync(pattern, { absolute: true, nocase: true });

  return files.map((file) => ({
    absolutePath: file,
    relativePath: path.relative(directory, file),
    fileName: path.basename(file),
  }));
}
