import Jimp from 'jimp';
import jsQR from 'jsqr';
import { z } from 'zod';

// ─────────────────────────────────────────────
// TIPOS Y CONFIGURACIÓN DE REGIONES
// ─────────────────────────────────────────────

/**
 * Define una región rectangular dentro de una imagen.
 * Todas las coordenadas son PORCENTAJES (0.0 - 1.0) para ser independientes del tamaño.
 */
export interface Region {
  name: string;
  x: number;      // % desde la izquierda
  y: number;      // % desde arriba
  width: number;  // % del ancho total
  height: number; // % del alto total
}

/**
 * Zonas predefinidas donde suele estar el QR en documentos.
 * Ajusta según tu formato de PDF.
 */
export const QR_REGIONS: Record<string, Region> = {
  // Esquina inferior derecha (más común en facturas, tickets, documentos oficiales)
  bottomRight: {
    name: 'bottomRight',
    x: 0.70,      // 70% desde la izquierda
    y: 0.75,      // 75% desde arriba
    width: 0.28,  // 28% del ancho
    height: 0.23, // 23% del alto
  },
  // Esquina superior derecha
  topRight: {
    name: 'topRight',
    x: 0.70,
    y: 0.02,
    width: 0.28,
    height: 0.23,
  },
  // Esquina inferior izquierda
  bottomLeft: {
    name: 'bottomLeft',
    x: 0.02,
    y: 0.75,
    width: 0.28,
    height: 0.23,
  },
  // Esquina superior izquierda
  topLeft: {
    name: 'topLeft',
    x: 0.02,
    y: 0.02,
    width: 0.28,
    height: 0.23,
  },
  // Centro inferior (algunos formatos de ticket)
  bottomCenter: {
    name: 'bottomCenter',
    x: 0.35,
    y: 0.80,
    width: 0.30,
    height: 0.18,
  },
  // Centro de la página
  center: {
    name: 'center',
    x: 0.30,
    y: 0.30,
    width: 0.40,
    height: 0.40,
  },
};

export interface QrResult {
  found: boolean;
  data: string | null;
  pageNumber: number;
  region?: string;      // qué región lo encontró
  fullPageFallback: boolean; // true = se encontró escaneando toda la página
}

// ─────────────────────────────────────────────
// ESQUEMAS ZOD PARA VALIDACIÓN
// ─────────────────────────────────────────────

export const QrContentSchema = z.string().min(1);
export const QrUrlSchema = z.string().url().startsWith('https://');
export const QrUuidSchema = z.string().uuid();

// ─────────────────────────────────────────────
// FUNCIONES DE CROP Y DECODIFICACIÓN
// ─────────────────────────────────────────────

/**
 * Recorta (crop) una región específica de una imagen Jimp.
 */
export async function cropRegion(
  image: Jimp,
  region: Region
): Promise<Jimp> {
  const imgWidth = image.bitmap.width;
  const imgHeight = image.bitmap.height;

  const cropX = Math.round(region.x * imgWidth);
  const cropY = Math.round(region.y * imgHeight);
  const cropW = Math.round(region.width * imgWidth);
  const cropH = Math.round(region.height * imgHeight);

  // Asegurar que no nos salgamos de los límites
  const safeX = Math.min(cropX, imgWidth - 1);
  const safeY = Math.min(cropY, imgHeight - 1);
  const safeW = Math.min(cropW, imgWidth - safeX);
  const safeH = Math.min(cropH, imgHeight - safeY);

  return image.clone().crop(safeX, safeY, safeW, safeH);
}

/**
 * Intenta decodificar un QR desde un buffer de imagen.
 * Primero escanea las regiones definidas (rápido), luego hace fallback a página completa.
 */
export async function decodeQrFromImage(
  imageBuffer: Buffer,
  pageNumber: number,
  regions: Region[] = Object.values(QR_REGIONS)
): Promise<QrResult> {
  try {
    const image = await Jimp.read(imageBuffer);

    // ── PASO 1: Intentar en cada región definida (rápido) ──
    for (const region of regions) {
      const cropped = await cropRegion(image, region);
      const qrData = jsQR(
        new Uint8ClampedArray(cropped.bitmap.data),
        cropped.bitmap.width,
        cropped.bitmap.height,
        { inversionAttempts: 'attemptBoth' }
      );

      if (qrData && qrData.data) {
        return {
          found: true,
          data: qrData.data,
          pageNumber,
          region: region.name,
          fullPageFallback: false,
        };
      }
    }

    // ── PASO 2: Fallback - escanear página completa ──
    const qrData = jsQR(
      new Uint8ClampedArray(image.bitmap.data),
      image.bitmap.width,
      image.bitmap.height,
      { inversionAttempts: 'attemptBoth' }
    );

    if (qrData && qrData.data) {
      return {
        found: true,
        data: qrData.data,
        pageNumber,
        region: 'fullPage',
        fullPageFallback: true,
      };
    }

    return {
      found: false,
      data: null,
      pageNumber,
      fullPageFallback: false,
    };
  } catch (error) {
    return {
      found: false,
      data: null,
      pageNumber,
      fullPageFallback: false,
    };
  }
}

/**
 * Versión optimizada: solo escanea las regiones, SIN fallback a página completa.
 * Útil cuando sabes EXACTAMENTE dónde está el QR y quieres máxima velocidad.
 */
export async function decodeQrFromRegionsOnly(
  imageBuffer: Buffer,
  pageNumber: number,
  regions: Region[] = Object.values(QR_REGIONS)
): Promise<QrResult> {
  try {
    const image = await Jimp.read(imageBuffer);

    for (const region of regions) {
      const cropped = await cropRegion(image, region);
      const qrData = jsQR(
        new Uint8ClampedArray(cropped.bitmap.data),
        cropped.bitmap.width,
        cropped.bitmap.height,
        { inversionAttempts: 'attemptBoth' }
      );

      if (qrData && qrData.data) {
        return {
          found: true,
          data: qrData.data,
          pageNumber,
          region: region.name,
          fullPageFallback: false,
        };
      }
    }

    return {
      found: false,
      data: null,
      pageNumber,
      fullPageFallback: false,
    };
  } catch (error) {
    return {
      found: false,
      data: null,
      pageNumber,
      fullPageFallback: false,
    };
  }
}

/**
 * Guarda una imagen recortada para debugging (útil para verificar zonas).
 */
export async function saveCroppedRegion(
  imageBuffer: Buffer,
  region: Region,
  outputPath: string
): Promise<void> {
  const image = await Jimp.read(imageBuffer);
  const cropped = await cropRegion(image, region);
  await cropped.writeAsync(outputPath);
}

/**
 * Valida que el contenido del QR cumpla un esquema Zod.
 */
export function validateQrContent(
  content: string,
  schema: z.ZodSchema = QrContentSchema
): { valid: boolean; errors?: string[] } {
  const result = schema.safeParse(content);
  if (result.success) {
    return { valid: true };
  }
  return { valid: false, errors: result.error.issues.map((i) => i.message) };
}
