#!/bin/bash

# ============================================================
# list_4MB_large_files.sh — Lista archivos mayores a 4MB
# ============================================================
# Busca recursivamente en el directorio donde se ejecuta el script
# y cuenta cuántos archivos miden más de 4MB.
# ============================================================

# Directorio donde se ejecuta el script
DIR="$(pwd)"

# Archivo de salida para guardar el listado de archivos mayores a 4MB
OUTPUT_FILE="$DIR/archivos_4M_$(date '+%Y-%m-%d %H:%M').txt"

# Crear el archivo de salida y redirigir toda la salida del script
# hacia él, manteniendo además la impresión en consola.
exec > >(tee "$OUTPUT_FILE") 2>&1

# Tamaño límite: 4MB en bytes (4 * 1024 * 1024 = 4194304)
# LIMIT=4194304
echo ""
echo "========================================"
echo "🔍 Buscando archivos mayores a 4MB en: $DIR"
echo "   (búsqueda recursiva, incluyendo subcarpetas)"
echo "========================================"
echo ""

# Buscar archivos recursivamente, filtrar los de 4MB o más y contar
COUNT=$(find "$DIR" \( -type f -size +4M -o -size 4M \) 2>/dev/null | wc -l)

# Mostrar los archivos encontrados (opcional, para ver cuáles son)
# find . -type f \(-size +4M -o -size 4M \) -print0 | xargs -0 ls -alhS | tee Archivos4MBs.txt

if [ "$COUNT" -gt 0 ]; then
    echo "📄 Archivos encontrados:"
    find "$DIR" \( -type f -size +4M -o -size 4M \) -print0 2>/dev/null | \
        xargs -0 ls -alhS --color=never 2>/dev/null | \
        sed '/^total/d; s/^/   📁 /'
    echo ""
fi

echo ""
echo "========================================"
echo "📊 Total de archivos mayores a 4MB: $COUNT"

# Finalmente indicar el archivo generado
echo "📝 Registro guardado en: $OUTPUT_FILE"
echo "========================================"
echo ""
