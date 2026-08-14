#!/bin/bash

# ============================================================
# check_pdf_text.sh — Detecta si PDFs son escaneados o parseables
# ============================================================
# Busca recursivamente todos los PDFs en el directorio donde se
# ejecuta el script y determina si son imágenes escaneadas.
# ============================================================

# Directorio donde se ejecuta el script
DIR="$(cd "$(dirname "$0")" && pwd)"

# Umbral mínimo de caracteres para considerar "parseable"
# Un PDF escaneado suele generar 0-5 caracteros de basura
MIN_CHARS=15

# Archivo de salida para guardar el listado de PDFs con imágenes escaneadas
OUTPUT_FILE="$DIR/listado_PDFs_imagenes_$(date '+%Y-%m-%d %H:%M:%S').txt"

# Crear el archivo de salida y redirigir toda la salida del script
# hacia él, manteniendo además la impresión en consola.
exec > >(tee "$OUTPUT_FILE") 2>&1

echo "🔍 Analizando PDFs en: $DIR con imagenes"
echo "   (búsqueda recursiva)"
echo ""

# Verificar que pdftotext esté instalado
if ! command -v pdftotext &> /dev/null; then
    echo "❌ Error: 'pdftotext' no está instalado."
    echo ""
    echo "   Instálalo con:"
    echo "   • Debian/Ubuntu:  sudo apt-get install poppler-utils"
    echo "   • Fedora/RHEL:    sudo dnf install poppler-utils"
    echo "   • macOS:          brew install poppler"
    echo "   • Arch:           sudo pacman -S poppler"
    exit 1
fi

# Contadores
TOTAL=0
PARSEABLE=0
SCANNED=0

# Archivo temporal para extraer texto
TMPFILE=$(mktemp /tmp/pdf_text.XXXXXX)

# Encontrar todos los PDFs recursivamente
while IFS= read -r -d '' pdf; do
    TOTAL=$((TOTAL + 1))

    # Extraer texto del PDF a archivo temporal
    pdftotext -layout "$pdf" "$TMPFILE" 2>/dev/null

    # Contar caracteres de texto extraído (sin espacios en blanco)
    CHAR_COUNT=$(tr -d '[:space:]' < "$TMPFILE" | wc -m)

    if [ "$CHAR_COUNT" -ge "$MIN_CHARS" ]; then
       # echo "✅ PARSEABLE  ($CHAR_COUNT chars) → $pdf"
        PARSEABLE=$((PARSEABLE + 1))
    else
        echo "📄 ESCANEADO → $pdf"
        SCANNED=$((SCANNED + 1))
    fi

done < <(find "$DIR" -type f -iname "*.pdf" -print0)

# Limpiar temporal
rm -f "$TMPFILE"

echo ""
echo "═══════════════════════════════════════"
echo "📊 RESUMEN"
echo "═══════════════════════════════════════"
echo "   📁 Total de PDFs analizados: $TOTAL"
echo "   ✅ Parseables (con texto):   $PARSEABLE"
echo "   📄 Escaneados (imagen):      $SCANNED"
echo "═══════════════════════════════════════"

echo ""
echo "═══════════════════════════════════════"
# Finalmente indicar el archivo generado
echo "📝 Registro guardado en: $OUTPUT_FILE"
echo "═══════════════════════════════════════"
echo ""