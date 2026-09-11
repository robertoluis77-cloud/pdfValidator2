#!/bin/bash

# ============================================================
# listandoTipos.sh — Lista todos los archivos NO-PDF con fdfind
# ============================================================
# Busca recursivamente en el directorio donde se ejecuta el script
# y lista todos los archivos que NO tienen extensión .pdf, usando
# 'fdfind' (o 'fd'). La salida se muestra por consola y se guarda
# en ../shellScriptResults/tiposArchivos_YYYYMMDD_HHMMSS.txt
# ============================================================

set -u

# Directorio donde se ejecuta el script (./pdfs)
DIR="$(cd "$(dirname "$0")" && pwd)"

# Directorio de salida (./shellScriptResults, hermano de pdfs)
OUTPUT_DIR="$DIR/../shellScriptResults"

# Verificar que el directorio de salida existe antes de escribir
if [ ! -d "$OUTPUT_DIR" ]; then
    echo "⚠️  El directorio de salida '$OUTPUT_DIR' no existe. Creándolo..."
    if ! mkdir -p "$OUTPUT_DIR"; then
        echo "❌ Error: no se pudo crear el directorio de salida: $OUTPUT_DIR"
        exit 1
    fi
fi

# Archivo de salida con marca de tiempo
OUTPUT_FILE="$OUTPUT_DIR/tiposArchivos_$(date '+%Y%m%d_%H%M%S').txt"

# Verificar que el archivo de salida se puede escribir antes de continuar
if ! touch "$OUTPUT_FILE" 2>/dev/null; then
    echo "❌ Error: no se puede escribir en el archivo: $OUTPUT_FILE"
    exit 1
fi

# Verificar que fdfind (o fd) esté instalado
if ! command -v fdfind &> /dev/null && ! command -v fd &> /dev/null; then
    echo "❌ Error: 'fdfind' (o 'fd') no está instalado."
    echo ""
    echo "   Instálalo con:"
    echo "   • Debian/Ubuntu:  sudo apt-get install fd-find (y alias fd=fdfind)"
    echo "   • Fedora/RHEL:    sudo dnf install fd-find"
    echo "   • macOS:          brew install fd"
    echo "   • Arch:           sudo pacman -S fd"
    exit 1
fi

# Usar 'fd' si 'fdfind' no existe
FD_CMD="fdfind"
command -v "$FD_CMD" &> /dev/null || FD_CMD="fd"

# Redirigir toda la salida a la consola y al archivo de resultados
exec > >(tee "$OUTPUT_FILE") 2>&1

echo ""
echo "========================================"
echo "🔍 Buscando archivos que NO son PDF en: $DIR (usando $FD_CMD)"
echo "   (búsqueda recursiva, incluyendo subcarpetas)"
echo "========================================"
echo ""

# Buscar recursivamente todos los archivos excluyendo los .pdf y .sh:
#   --type f    : solo archivos regulares
#   -H -I       : incluye archivos ocultos y NO respeta .gitignore/.fdignore
#                 (necesario para entrar en subcarpetas ignoradas como
#                 pdfsComprimidos)
#   . "$DIR"    : búsqueda recursiva a partir del directorio del script
# Los filtros de exclusión son insensibles a mayúsculas/minúsculas
# (.PDF, .Pdf, .SH, etc.) mediante grep -iv sobre la lista devuelta por fd.
# El último sed reescribe cada ruta absoluta como relativa al proyecto,
# empezando desde ./pdfs (sin depender del formato de ruta del sistema).
FILE_LIST=$($FD_CMD --type f -H -I . "$DIR" | grep -ivE '\.(pdf|sh)$' | sed 's|^.*/pdfs/|./pdfs/|; s|^./pdfs$|./pdfs|' || true)
COUNT=0
[ -n "$FILE_LIST" ] && COUNT=$(printf '%s\n' "$FILE_LIST" | wc -l)

if [ "$COUNT" -gt 0 ]; then
    echo "📄 Archivos no-PDF encontrados (rutas desde ./pdfs):"
    # Imprimir cada ruta completa, una por línea
    printf '%s\n' "$FILE_LIST" | sed 's/^/   📁 /'
    echo ""
    echo "📊 Resumen por tipo de archivo (extensión):"
    # Extraer la extensión (en minúsculas), contar por tipo y ordenar
    # de mayor a menor por número de archivos
    printf '%s\n' "$FILE_LIST" | awk -F. '{
        if (NF > 1) { print tolower($NF) } else { print "(sin extension)" }
    }' | sort | uniq -c | sort -k1,1nr | while read -r n ext; do
        printf "   %-20s %d\n" "$ext" "$n"
    done
    printf "   %-20s %d\n" "(total)" "$COUNT"
    echo ""
else
    echo "📄 No se encontraron archivos que no sean PDF."
    echo ""
fi

echo "========================================"
echo "📊 Total de archivos no-PDF: $COUNT"
echo "📝 Registro guardado en: $OUTPUT_FILE"
echo "========================================"
echo ""

exit 0
