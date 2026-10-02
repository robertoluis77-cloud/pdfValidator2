#!/bin/bash

# ============================================================
# split_4M_PDF_ghostscript_this.sh — Divide PDFs > 4MB en partes < 4MB
# ============================================================
# Busca recursivamente (como list_4M_PDF_And_Pages_fdfind_this.sh)
# todos los PDFs mayores a 4MB y los divide en partes usando
# Ghostscript, acumulando páginas hasta alcanzar el límite de
# tamaño. Cada parte se nombra como <nombre>_1.pdf, <nombre>_2.pdf...
# Uso: ./split_4M_PDF_ghostscript_this.sh [max_mb]
# ============================================================

MAX_MB="${1:-4}"
MAX_BYTES=$(( MAX_MB * 1024 * 1024 ))

# Directorio donde se ejecuta el script
DIR="$(cd "$(dirname "$0")" && pwd)"

# Archivo de salida para guardar el registro del proceso (anclado al directorio del script)
OUTPUT_FILE="$DIR/../shellScriptResults/split_PDFs_4M_ghostscript_$(date '+%Y-%m-%d_%H-%M-%S').txt"

# Redirigir toda la salida a un archivo de log y a la consola
mkdir -p "$(dirname "$OUTPUT_FILE")"
exec > >(tee "$OUTPUT_FILE") 2>&1

# Verificar que Ghostscript esté disponible (gs / gswin64c / gswin32c)
GS_CMD="gs"
if ! command -v "$GS_CMD" &> /dev/null; then
    if command -v gswin64c &> /dev/null; then
        GS_CMD="gswin64c"
    elif command -v gswin32c &> /dev/null; then
        GS_CMD="gswin32c"
    else
        echo "❌ Error: Ghostscript no está instalado (gs / gswin64c / gswin32c)."
        echo "   Descárgalo desde: https://www.ghostscript.com/download.html"
        exit 1
    fi
fi

# Verificar que fd/fdfind esté instalado
if ! command -v fdfind &> /dev/null && ! command -v fd &> /dev/null; then
    echo "❌ Error: 'fdfind' (o 'fd') no está instalado."
    echo "   Instálalo con:"
    echo "   • Debian/Ubuntu:  sudo apt-get install fd-find (y alias fd=fdfind)"
    echo "   • Fedora/RHEL:    sudo dnf install fd-find"
    echo "   • macOS:          brew install fd"
    echo "   • Arch:           sudo pacman -S fd"
    exit 1
fi

FD_CMD="fdfind"
command -v "$FD_CMD" &> /dev/null || FD_CMD="fd"

# Parámetros de Ghostscript (idénticos en todas las invocaciones)
GS_PARAMS=(
    -sDEVICE=pdfwrite
    -dCompatibilityLevel=1.4
    -dDownsampleColorImages=true
    -dDownsampleGrayImages=true
    -dDownsampleMonoImages=true
    -dColorImageResolution=130
    -dGrayImageResolution=300
    -dMonoImageResolution=300
    -dColorImageDownsampleType=/Bicubic
    -dGrayImageDownsampleType=/Bicubic
    -dMonoImageDownsampleType=/Bicubic
    -dAutoFilterColorImages=false
    -dAutoFilterGrayImages=false
    -dAutoFilterMonoImages=false
    -dColorImageFilter=/DCTEncode
    -dGrayImageFilter=/DCTEncode
    -dMonoImageFilter=/CCITTFaxEncode
    -dOmitInfo=true
    -dOmitdata=true
    -dJPEGQ=75
    -dUCRandBGInfo=/Remove
    -dSubsetFonts=true
    -dCompressFonts=true
    -dDetectDuplicateImages=true
    -dRemoveUnusedResources=true
    -dEmbedAllFonts=true
    -dCompressPages=true
    -dNOPAUSE
    -dBATCH
)

# Obtener el total de páginas de un PDF (pdfinfo o Ghostscript)
get_page_count() {
    local pdf="$1"
    local total
    total=$(pdfinfo "$pdf" 2>/dev/null | awk '/Pages:/ {print $2}')
    if [ -z "$total" ]; then
        # --permit-file-read: necesario porque GS >= 9.50 activa -dSAFER por defecto
        # y bloquea la lectura del PDF via el operador 'file' de PostScript
        total=$("$GS_CMD" -q -dNODISPLAY --permit-file-read="$pdf" \
            -c "($(echo "$pdf" | sed 's/\\/\\\\/g;s/(/\\(/g;s/)/\\)/g')) (r) file runpdfbegin pdfpagecount = quit" 2>/dev/null)
    fi
    echo "$total"
}

# Invocar Ghostscript desactivando la conversión de rutas de MSYS2/Git Bash.
# Sin esto, Git Bash corrompe los parámetros estilo '/Nombre' (p.ej.
# -dColorImageDownsampleType=/Bicubic se convierte en
# -dColorImageDownsampleType=C:/Program Files/Git/Bicubic) y gs falla.
run_gs_capture_err() {
    local err_file="$1"; shift
    MSYS2_ARG_CONV_EXCL="*" MSYS_NO_PATHCONV=1 "$GS_CMD" "$@" 2>"$err_file" >/dev/null
}

# Extraer un rango de páginas a un archivo de salida usando Ghostscript
extract_pages() {
    local input_pdf="$1"
    local first="$2"
    local last="$3"
    local output_pdf="$4"
    local err_file="$5"
    run_gs_capture_err "$err_file" \
        "${GS_PARAMS[@]}" \
        -dFirstPage="$first" \
        -dLastPage="$last" \
        -sOutputFile="$output_pdf" \
        "$input_pdf"
}

stat_size() {
    stat -c%s "$1" 2>/dev/null || stat -f%z "$1" 2>/dev/null || echo 0
}

echo ""
echo "========================================"
echo "🔍 Buscando PDFs mayores a 4MB en: $DIR (usando $FD_CMD)"
echo "   Límite por parte: ${MAX_MB} MB"
echo "========================================"
echo ""

# Buscar archivos PDF recursivamente, filtrar los mayores a 4MB
# -I (--no-ignore): NO respetar .gitignore. Este repo ignora '*.pdf', así que sin -I
# fd solo encontraba los archivos con extensión en mayúsculas (.PDF) y omitía el resto.
PDF_LIST=$($FD_CMD -e pdf --size +4M -I . "$DIR")
COUNT=$(echo "$PDF_LIST" | grep -c . || true)

if [ "$COUNT" -eq 0 ]; then
    echo "📄 No se encontraron PDFs mayores a 4MB. Nada que hacer."
    echo ""
    exit 0
fi

TMP_OUT="tmp_split_eval.pdf"
TMP_ERR="tmp_split_err.txt"
trap 'rm -f "$TMP_OUT" "$TMP_ERR"' EXIT

# Procesar cada PDF mayor a 4MB
while IFS= read -r PDF_INPUT; do
    [ -z "$PDF_INPUT" ] && continue

    # Nombre base sin extensión: myPDF.pdf -> myPDF
    BASE_NAME="$(basename "$PDF_INPUT")"
    BASE_NAME="${BASE_NAME%.[Pp][Dd][Ff]}"
    OUT_DIR="$(dirname "$PDF_INPUT")"

    TOTAL_PAGS=$(get_page_count "$PDF_INPUT")
    if [ -z "$TOTAL_PAGS" ] || [ "$TOTAL_PAGS" -lt 1 ]; then
        echo "⚠️  No se pudo determinar el número de páginas de '$PDF_INPUT'. Omitido."
        echo ""
        continue
    fi

    echo "----------------------------------------"
    echo "📄 Procesando '$PDF_INPUT' ($TOTAL_PAGS páginas, límite ${MAX_MB} MB)..."
    echo "----------------------------------------"

    PARTE=1
    PAG_INICIO=1
    OK=1

    for (( pag=1; pag<=TOTAL_PAGS; pag++ )); do
        # Extraer desde PAG_INICIO hasta la página actual (acumulado tentativo)
        # rm previo: evita que un fallo de gs deje un acumulado obsoleto
        rm -f "$TMP_OUT"
        extract_pages "$PDF_INPUT" "$PAG_INICIO" "$pag" "$TMP_OUT" "$TMP_ERR"
        if [ ! -f "$TMP_OUT" ]; then
            echo "   ❌ Error: Ghostscript no pudo extraer las páginas $PAG_INICIO-$pag (se aborta este archivo)"
            if [ -s "$TMP_ERR" ]; then
                echo "   ❌ Ghostscript devolvió:"
                sed 's/^/   >  /' "$TMP_ERR" | head -n 5
            fi
            OK=0
            break
        fi
        TAMANO_ACTUAL=$(stat_size "$TMP_OUT")

        # Si excede el límite y hay más de 1 página en el acumulado,
        # guardar el bloque válido (hasta la página anterior) y empezar uno nuevo
        if [ "$TAMANO_ACTUAL" -gt "$MAX_BYTES" ] && [ "$pag" -gt "$PAG_INICIO" ]; then
            PAG_FIN=$(( pag - 1 ))
            ARCH_SALIDA="$OUT_DIR/${BASE_NAME}_${PARTE}.pdf"

            rm -f "$ARCH_SALIDA"
            extract_pages "$PDF_INPUT" "$PAG_INICIO" "$PAG_FIN" "$ARCH_SALIDA" "$TMP_ERR"

            if [ -f "$ARCH_SALIDA" ]; then
                echo "   ✅ Creado: $ARCH_SALIDA (Páginas $PAG_INICIO a $PAG_FIN, $(stat_size "$ARCH_SALIDA") bytes)"
            else
                echo "   ❌ Error: no se pudo crear $ARCH_SALIDA"
                if [ -s "$TMP_ERR" ]; then
                    echo "   ❌ Ghostscript devolvió:"
                    sed 's/^/   >  /' "$TMP_ERR" | head -n 5
                fi
            fi

            PARTE=$(( PARTE + 1 ))
            PAG_INICIO=$pag
        fi
    done

    # Guardar el último bloque restante
    if [ "$OK" -eq 1 ] && [ "$PAG_INICIO" -le "$TOTAL_PAGS" ]; then
        ARCH_SALIDA="$OUT_DIR/${BASE_NAME}_${PARTE}.pdf"

        rm -f "$ARCH_SALIDA"
        extract_pages "$PDF_INPUT" "$PAG_INICIO" "$TOTAL_PAGS" "$ARCH_SALIDA" "$TMP_ERR"

        if [ -f "$ARCH_SALIDA" ]; then
            echo "   ✅ Creado: $ARCH_SALIDA (Páginas $PAG_INICIO a $TOTAL_PAGS, $(stat_size "$ARCH_SALIDA") bytes)"
        else
            echo "   ❌ Error: no se pudo crear $ARCH_SALIDA"
            if [ -s "$TMP_ERR" ]; then
                echo "   ❌ Ghostscript devolvió:"
                sed 's/^/   >  /' "$TMP_ERR" | head -n 5
            fi
        fi
    fi

    echo ""
done <<< "$PDF_LIST"

rm -f "$TMP_OUT"

echo "========================================"
echo "📊 Total de PDFs mayores a 4MB procesados: $COUNT"
echo "📝 Registro guardado en: $OUTPUT_FILE"
echo "========================================"
echo ""
