#!/usr/bin/env bash
# Desbloquea recursivamente todos los archivos dentro del directorio actual.
# Requiere Windows + PowerShell (porque el comando Unblock-File es de PowerShell).

set -euo pipefail

# Usa el directorio donde se está ejecutando el script como raíz.
# En Git Bash en Windows, pwd devuelve rutas POSIX tipo /c/Users/... ; eso
# es correcto para find, pero para PowerShell hay que convertir el archivo
# a una ruta Win32 antes del comando Unblock-File.
root_dir="$(pwd)"

normalize_for_powershell() {
  local path="$1"

  # Git Bash emite rutas POSIX para cada PDF encontrado: /c/Users/... o /mnt/c/...
  # PowerShell requiere C:\Users\... para que Unblock-File encuentre el archivo.
  if [[ "$path" =~ ^/(mnt/)?([a-zA-Z])/(.*)$ ]]; then
    local drive="${BASH_REMATCH[2]^^}"
    local rest="${BASH_REMATCH[3]}"
    path="${drive}:/${rest}"
  fi

  # Reemplaza la barra posix de cualquier otra ruta de entrada.
  path=${path//\//\\}
  printf '%s' "$path"
}

# Archivo de salida para guardar el registro del desbloqueo.
OUTPUT_FILE="$root_dir/unlockedFiles_log$(date '+%Y-%m-%d %H:%M').txt"

# Crear el archivo de salida y redirigir toda la salida del script
# hacia él, manteniendo además la impresión en consola.
exec > >(tee "$OUTPUT_FILE") 2>&1

if [ ! -d "$root_dir" ]; then
  echo "Error: no existe el directorio: $root_dir"
  exit 1
fi

if ! command -v powershell.exe >/dev/null 2>&1; then
  echo "Error: powershell.exe no está disponible en PATH."
  exit 1
fi

count=0

: > "$OUTPUT_FILE"

pdf_list_file="$(mktemp)"
find "$root_dir" -type f -iname "*.pdf" -print0 > "$pdf_list_file"

mapfile -d '' -t pdf_files < "$pdf_list_file"
rm -f "$pdf_list_file"

for file in "${pdf_files[@]}"; do
  win_file="$(normalize_for_powershell "$file")"

  # Escapa comillas simples para PowerShell.
  safe_file=${win_file//\'/\'\'}

  echo "Procesando: $file" >> "$OUTPUT_FILE"
  powershell.exe -NoProfile -Command "Unblock-File -LiteralPath '$safe_file'" >> "$OUTPUT_FILE" 2>&1 || true

  count=$((count + 1))
done

echo ""
echo "========================================"
printf 'Se procesaron %d archivos dentro de: %s\n' "$count" "$root_dir"
echo ""
echo "📝 Registro guardado en: $OUTPUT_FILE"
echo "========================================"
echo ""