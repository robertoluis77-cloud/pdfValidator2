#!/bin/bash

# =============================================================================
# convert_images_to_pdfs_recursive.sh
# Convierte recursivamente todos los archivos JPG/JPEG/PNG en el directorio
# actual y sus subdirectorios a PDF usando ImageMagick con DPI = 150.
# =============================================================================

set -euo pipefail

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Directorio donde se ejecuta el script
DIR="$(cd "$(dirname "$0")" && pwd)"

# Archivo de salida para registro
OUTPUT_FILE="$DIR/images_to_pdf_log_$(date '+%Y-%m-%d %H:%M:%S').txt"

# Función para imprimir en consola (con color) y en log (sin color ANSI)
log() {
    local msg="$1"
    # Consola: con colores
    echo -e "$msg"
    # Log: strip códigos de escape ANSI antes de escribir al archivo
    echo -e "$msg" | sed 's/\x1B\[[0-9;]*[mK]//g' >> "$OUTPUT_FILE"
}

# Detectar el comando de ImageMagick
# En Windows con Git Bash, 'convert' puede apuntar a C:\Windows\System32\convert.exe
# (herramienta de conversión de sistemas de archivos), NO a ImageMagick.
# Por eso verificamos que la versión reportada mencione "ImageMagick".
IMG_CMD=""

_is_imagemagick() {
    "$1" --version 2>&1 | grep -qi "imagemagick"
}

# 1. Buscar 'magick' (ImageMagick 7+)
if command -v magick &> /dev/null && _is_imagemagick magick; then
    IMG_CMD="magick"
# 2. Buscar 'convert' solo si realmente es ImageMagick (no el del sistema Windows)
elif command -v convert &> /dev/null && _is_imagemagick convert; then
    IMG_CMD="convert"
# 3. Rutas de instalación estándar de ImageMagick en Windows
else
    for _dir in \
        "/c/Program Files/ImageMagick-7.1.1-Q16-HDRI" \
        "/c/Program Files/ImageMagick-7.1.0-Q16-HDRI" \
        "/c/Program Files/ImageMagick-7.0.11-Q16-HDRI" \
        "/c/Program Files (x86)/ImageMagick-7.1.1-Q16-HDRI" \
        "/c/Program Files (x86)/ImageMagick-7.0.11-Q16-HDRI"; do
        if [[ -x "$_dir/magick.exe" ]] && _is_imagemagick "$_dir/magick.exe"; then
            IMG_CMD="$_dir/magick.exe"
            break
        fi
        if [[ -x "$_dir/convert.exe" ]] && _is_imagemagick "$_dir/convert.exe"; then
            IMG_CMD="$_dir/convert.exe"
            break
        fi
    done
fi

if [[ -z "$IMG_CMD" ]]; then
    log "${RED}Error: ImageMagick no está instalado o no está en el PATH.${NC}"
    log ""
    log "  NOTA: En Windows, 'convert.exe' del sistema NO es ImageMagick."
    log "  Asegúrate de que el directorio de ImageMagick aparezca ANTES"
    log "  que C:\\Windows\\System32 en la variable de entorno PATH."
    log ""
    log "Instálalo con:"
    log "  Ubuntu/Debian: sudo apt-get install imagemagick"
    log "  macOS:         brew install imagemagick"
    log "  Windows:       descarga ImageMagick desde https://imagemagick.org/"
    exit 1
fi

log "${BLUE}Usando ImageMagick: $IMG_CMD${NC}"

log "${BLUE}Configuración: DPI 150${NC}"

TOTAL=0
OK=0
FAIL=0

convert_image_to_pdf() {
    local input_file="$1"
    local dir
    local basename
    local stem
    local output_file

    dir=$(dirname "$input_file")
    basename=$(basename "$input_file")
    stem="${basename%.*}"
    output_file="${dir}/${stem}.pdf"

    log "${YELLOW}→${NC} Procesando: $input_file"

    if [[ -e "$output_file" ]]; then
        rm -f "$output_file"
    fi

    # En Windows con Git Bash, ImageMagick nativo necesita rutas estilo Windows.
    # cygpath -w convierte /c/ruta/... a C:\ruta\...
    # Si cygpath no existe (Linux/macOS), se usan las rutas tal cual.
    local win_input win_output
    if command -v cygpath &> /dev/null; then
        win_input="$(cygpath -w "$input_file")"
        win_output="$(cygpath -w "$output_file")"
    else
        win_input="$input_file"
        win_output="$output_file"
    fi

    # Convertir JPG/JPEG/PNG a PDF con DPI 150 y compresión moderada.
    # Se usa un redimensionamiento controlado para reducir el tamaño del PDF
    # sin perder legibilidad de texto y QR.
    if "$IMG_CMD" \
      "$win_input" \
      -units PixelsPerInch \
      -density 150 \
      -resize '1800x1800>' \
      -strip \
      -background white \
      -alpha remove \
      -compress jpeg \
      -quality 80 \
      -define pdf:use-cropbox=true \
      "$win_output"; then
        if [[ -s "$output_file" ]]; then
            rm -f "$input_file"
            log "  ${GREEN}✓${NC} ${output_file} (imagen original eliminada)"
            OK=$((OK + 1))
        else
            log "  ${RED}✗${NC} Error: PDF generado vacío"
            rm -f "$output_file"
            FAIL=$((FAIL + 1))
        fi
    else
        log "  ${RED}✗${NC} Error: ImageMagick falló al convertir este archivo"
        rm -f "$output_file"
        FAIL=$((FAIL + 1))
    fi
}

# =============================================================================
# MAIN
# =============================================================================

log "========================================"
log "  Conversor de imágenes a PDF"
log "  Programa: ImageMagick"
log "  DPI: 150"
log "  Directorio: $(pwd)"
log "========================================"
log ""

# Buscar recursivamente JPG, JPEG y PNG
while IFS= read -r -d '' image_file; do
    TOTAL=$((TOTAL + 1))
    convert_image_to_pdf "$image_file"
done < <(find "$DIR" -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" \) -print0)

# Resumen
log ""
log "========================================"
log "  RESUMEN"
log "========================================"
log "  Total encontrados: ${TOTAL}"
log "  ${GREEN}Convertidos OK:${NC}    ${OK}"
log "  ${RED}Fallidos:${NC}          ${FAIL}"
log "========================================"

log ""
log "========================================"
log "📝 Registro guardado en: $OUTPUT_FILE"
log "========================================"

log ""
