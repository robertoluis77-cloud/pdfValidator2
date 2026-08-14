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

# Redirigir salida a consola y archivo de log
exec > >(tee "$OUTPUT_FILE") 2>&1

# Detectar el comando de ImageMagick
IMG_CMD=""
if command -v magick &> /dev/null; then
    IMG_CMD="magick"
elif command -v convert &> /dev/null; then
    IMG_CMD="convert"
else
    echo -e "${RED}Error: ImageMagick no está instalado o no está en el PATH.${NC}"
    echo "Instálalo con:"
    echo "  Ubuntu/Debian: sudo apt-get install imagemagick"
    echo "  macOS:         brew install imagemagick"
    echo "  Windows:       descarga ImageMagick desde https://imagemagick.org/"
    exit 1
fi

echo -e "${BLUE}Usando ImageMagick: $IMG_CMD${NC}"

echo -e "${BLUE}Configuración: DPI 150${NC}"

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

    echo -e "${YELLOW}→${NC} Procesando: $input_file"

    if [[ -e "$output_file" ]]; then
        rm -f "$output_file"
    fi

    # Convertir JPG/JPEG/PNG a PDF con DPI 150 y compresión moderada.
    # Se usa un redimensionamiento controlado para reducir el tamaño del PDF
    # sin perder legibilidad de texto y QR.
    if "$IMG_CMD" \
      "$input_file" \
      -units PixelsPerInch \
      -density 150 \
      -resize '1800x1800>' \
      -strip \
      -background white \
      -alpha remove \
      -compress jpeg \
      -quality 80 \
      -define pdf:use-cropbox=true \
      "$output_file"; then
        if [[ -s "$output_file" ]]; then
            rm -f "$input_file"
            echo -e "  ${GREEN}✓${NC} ${output_file} (imagen original eliminada)"
            OK=$((OK + 1))
        else
            echo -e "  ${RED}✗${NC} Error: PDF generado vacío"
            rm -f "$output_file"
            FAIL=$((FAIL + 1))
        fi
    else
        echo -e "  ${RED}✗${NC} Error: ImageMagick falló al convertir este archivo"
        rm -f "$output_file"
        FAIL=$((FAIL + 1))
    fi
}

# =============================================================================
# MAIN
# =============================================================================

echo "========================================"
echo "  Conversor de imágenes a PDF"
echo "  Programa: ImageMagick"
echo "  DPI: 150"
echo "  Directorio: $(pwd)"
echo "========================================"
echo ""

# Buscar recursivamente JPG, JPEG y PNG
while IFS= read -r -d '' image_file; do
    TOTAL=$((TOTAL + 1))
    convert_image_to_pdf "$image_file"
done < <(find "$DIR" -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" \) -print0)

# Resumen
echo ""
echo "========================================"
echo "  RESUMEN"
echo "========================================"
echo -e "  Total encontrados: ${TOTAL}"
echo -e "  ${GREEN}Convertidos OK:${NC}    ${OK}"
echo -e "  ${RED}Fallidos:${NC}          ${FAIL}"
echo "========================================"

echo ""
echo "========================================"
echo "📝 Registro guardado en: $OUTPUT_FILE"
echo "========================================"

echo ""
