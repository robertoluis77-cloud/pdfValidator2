#!/bin/bash

# ============================================================
# list_1M_PDF_large_files.sh — Lista PDFs mayores a 1MB
# ============================================================
# Busca recursivamente en el directorio donde se ejecuta el script
# y lista todos los archivos PDF que miden más de 1MB.
# ============================================================

# Directorio donde se ejecuta el script
DIR="$(cd "$(dirname "$0")" && pwd)"

# Archivo de salida para guardar el listado de PDFs mayores a 1MB
OUTPUT_FILE="$DIR/listado_PDFs_1M_$(date '+%Y-%m-%d %H:%M').txt"

# Umbral de tamaño: 1MB en bytes (1 * 1024 * 1024 = 1048576)
# En find se usa el criterio +1M para mayor a 1MB

echo ""
echo "========================================"
echo "🔍 Buscando PDFs mayores a 1MB en: $DIR"
echo "   (búsqueda recursiva, incluyendo subcarpetas)"
echo "========================================"
echo ""

# Buscar archivos PDF recursivamente, filtrar los mayores a 1MB y contar
COUNT=$(find "$DIR" -type f -iname "*.pdf" -size +1M 2>/dev/null | wc -l)

# Crear el archivo de salida con el listado
{
    echo "Listado de PDFs mayores a 1MB"
    echo "Directorio de búsqueda: $DIR"
    echo "Generado el: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""

    if [ "$COUNT" -gt 0 ]; then
        find "$DIR" -type f -iname "*.pdf" -size +1M -printf "   %p  (%s bytes)\n" 2>/dev/null
    else
        echo "No se encontraron PDFs mayores a 1MB."
    fi
} > "$OUTPUT_FILE"

# Mostrar los archivos encontrados
if [ "$COUNT" -gt 0 ]; then
    echo "📄 PDFs encontrados:"
    find "$DIR" -type f -iname "*.pdf" -size +1M -printf "   📁 %p  (%s bytes)\n" 2>/dev/null
    echo ""
else
    echo "📄 No se encontraron PDFs mayores a 1MB."
    echo ""
fi

echo ""
echo "========================================"
echo "📄 Listado guardado en: $OUTPUT_FILE"
echo "📊 Total de PDFs mayores a 1MB: $COUNT"
echo "========================================"
echo ""
