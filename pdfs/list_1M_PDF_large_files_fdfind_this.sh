#!/bin/bash

# ============================================================
# list_1M_PDF_large_files_fdfind.sh — Lista PDFs > 1MB con fdfind
# ============================================================
# Busca recursivamente en el directorio donde se ejecuta el script
# y lista todos los archivos PDF que miden más de 1MB, usando 'fdfind'.
# ============================================================

# Directorio donde se ejecuta el script
DIR="$(cd "$(dirname "$0")" && pwd)"

# Archivo de salida para guardar el listado de PDFs mayores a 1MB
OUTPUT_FILE="$DIR/listado_PDFs_1M_fdfind_$(date '+%Y-%m-%d_%H-%M-%S').txt"

# Redirigir toda la salida a un archivo de log y a la consola
exec > >(tee "$OUTPUT_FILE") 2>&1

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


echo ""
echo "========================================"
echo "🔍 Buscando PDFs mayores a 1MB en: $DIR (usando $FD_CMD)"
echo "   (búsqueda recursiva, incluyendo subcarpetas)"
echo "========================================"
echo ""

# Buscar archivos PDF recursivamente, filtrar los mayores a 1MB
# -e pdf: filtra por extensión 'pdf'
# --size +1M: filtra archivos con tamaño mayor a 1MB
# . "$DIR": busca en el directorio especificado
PDF_LIST=$($FD_CMD -e pdf --size +1M . "$DIR")
COUNT=$(echo "$PDF_LIST" | wc -l)

if [ "$COUNT" -gt 0 ]; then
    echo "📄 PDFs encontrados:"
    # Usamos xargs para pasar la lista de archivos a 'ls' para un formato amigable
    # El uso de 'ls -lhS' ordena por tamaño (más grande primero)
    echo "$PDF_LIST" | xargs -d '\n' ls -lhS --color=never | sed '/^total/d; s/^/   📁 /'
    echo ""
else
    echo "📄 No se encontraron PDFs mayores a 1MB."
    echo ""
fi

echo "========================================"
echo "📊 Total de PDFs mayores a 1MB: $COUNT"
echo "📝 Registro guardado en: $OUTPUT_FILE"
echo "========================================"
echo ""