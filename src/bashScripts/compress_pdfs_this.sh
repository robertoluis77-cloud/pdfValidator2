#!/bin/bash

# =============================================================================
# compress_pdfs.sh
# Comprime recursivamente todos los archivos PDF en el directorio actual
# y sus subdirectorios usando Ghostscript con preset /ebook.
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

# Archivo de salida para guardar el listado de archivos mayores a 4MB
OUTPUT_FILE="$DIR/gs_exex_log_$(date '+%Y-%m-%d %H:%M:%S').txt"

# Crear el archivo de salida y redirigir toda la salida del script
# hacia él, manteniendo además la impresión en consola.
exec > >(tee "$OUTPUT_FILE") 2>&1

# Detectar el comando de Ghostscript (gs en Linux/Mac, gswin64c/gswin32c en Windows)
GS_CMD="gs"
if ! command -v "$GS_CMD" &> /dev/null; then
    if command -v gswin64c &> /dev/null; then
        GS_CMD="gswin64c"
    elif command -v gswin32c &> /dev/null; then
        GS_CMD="gswin32c"
    else
        echo -e "${RED}Error: Ghostscript no está instalado o no está en el PATH.${NC}"
        echo "Instálalo con:"
        echo "  Ubuntu/Debian: sudo apt-get install ghostscript"
        echo "  macOS:         brew install ghostscript"
        echo "  Windows:       descarga desde https://www.ghostscript.com/"
        exit 1
    fi
fi

echo -e "${BLUE}Usando Ghostscript: $GS_CMD${NC}"

# Contadores
TOTAL=0
OK=0
FAIL=0

# Función para comprimir un solo PDF
compress_pdf() {
    local input_file="$1"
    local dir
    local basename
    local tmp_file
    local original_size
    local new_size
    local reduction
    local original_kb
    local new_kb

    dir=$(dirname "$input_file")
    basename=$(basename "$input_file")
    tmp_file="${dir}/.tmp_compressed_${RANDOM}_${basename}"

    echo -e "${YELLOW}→${NC} Procesando: $input_file"

    # Obtener tamaño original
    original_size=$(stat -f%z "$input_file" 2>/dev/null || stat -c%s "$input_file" 2>/dev/null || echo "0")

    # Ejecutar Ghostscript con estas optiones:
    #   -sDEVICE=pdfwrite            -> Indica al driver de salida que genere un nuevo PDF (pdfwrite)
    #   -dCompatibilityLevel=1.4    -> Define el nivel de compatibilidad del PDF generado
    #   -dPDFSETTINGS=/ebook         -> Preset de calidad/compression para ebooks
    #   -dNOPAUSE                    -> Hace que Ghostscript no se detenga para pedir confirmación entre páginas
    #   -dQUIET                      -> Suprime o reduce mensajes de salida por consola
    #   -dBATCH                      -> Pone Ghostscript en modo batch o no interactivo
    #   -sOutputFile="$tmp_file"      -> Especifica la ruta del archivo PDF de salida recién generado
    #   "$input_file"                -> El PDF de entrada que Ghostscript va a leer y procesar
    #
    
    # Ejecutar Ghostscript (TODO EN UNA SOLA LÍNEA para evitar problemas con el if)
    
    if "$GS_CMD" \
      -sDEVICE=pdfwrite \
      -dCompatibilityLevel=1.4 \
      -dPDFSETTINGS=/ebook \
      -dColorImageDownsampleType=/Bicubic \
      -dColorImageResolution=120 \
      -dGrayImageDownsampleType=/Bicubic \
      -dGrayImageResolution=120 \
      -dMonoImageDownsampleType=/Bicubic \
      -dMonoImageResolution=120 \
      -dNOPAUSE \
      -dQUIET \
      -dBATCH \
      -sOutputFile="$tmp_file" \
      "$input_file"; then

        # Verificar que el archivo temporal se creó y no está vacío
        if [[ -s "$tmp_file" ]]; then
            new_size=$(stat -f%z "$tmp_file" 2>/dev/null || stat -c%s "$tmp_file" 2>/dev/null || echo "0")

            # Reemplazar el original
            mv "$tmp_file" "$input_file"

            # Calcular reducción
            if [[ "$original_size" -gt 0 && "$new_size" -gt 0 ]]; then
                reduction=$(( (original_size - new_size) * 100 / original_size ))
                original_kb=$(awk -v bytes="$original_size" 'BEGIN { printf "%.2f", bytes / 1024 }')
                new_kb=$(awk -v bytes="$new_size" 'BEGIN { printf "%.2f", bytes / 1024 }')
                echo -e "  ${GREEN}✓${NC} ${original_kb} KB → ${new_kb} KB (${reduction}% menos)"
            else
                echo -e "  ${GREEN}✓${NC} Comprimido correctamente"
            fi
            OK=$((OK + 1))
        else
            echo -e "  ${RED}✗${NC} Error: archivo temporal vacío o corrupto"
            rm -f "$tmp_file"
            FAIL=$((FAIL + 1))
        fi
    else
        echo -e "  ${RED}✗${NC} Error: Ghostscript falló al procesar este archivo"
        rm -f "$tmp_file"
        FAIL=$((FAIL + 1))
    fi
}

# =============================================================================
# MAIN
# =============================================================================

echo "========================================"
echo "  Compresor de PDFs con Ghostscript"
echo "  Preset: /ebook (150 dpi)"
echo "  Directorio: $(pwd)"
echo "========================================"
echo ""

# Buscar todos los PDFs recursivamente
while IFS= read -r -d '' pdf_file; do
    TOTAL=$((TOTAL + 1))
    compress_pdf "$pdf_file"
done < <(find "$DIR" -type f -iname "*.pdf" -print0)

# Resumen
echo ""
echo "========================================"
echo "  RESUMEN"
echo "========================================"
echo -e "  Total encontrados: ${TOTAL}"
echo -e "  ${GREEN}Comprimidos OK:${NC}    ${OK}"
echo -e "  ${RED}Fallidos:${NC}          ${FAIL}"
echo "========================================"

echo ""

echo "========================================"
# Finalmente indicar el archivo generado
echo "📝 Registro guardado en: $OUTPUT_FILE"
echo "========================================"

echo ""
