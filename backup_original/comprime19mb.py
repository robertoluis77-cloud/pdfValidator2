"""
program name:comprime19mb.py
modificaciones:
FFM01 08Sep26 Modificado para limite de tamaño de archivo individual y grupos a 19 MB.
"""

import shutil
import filecmp

import os 
import shutil
import sys
import datetime
import time
import zipfile    # To use python zip libraries
import msvcrt     # To create a pause space bar
import subprocess # To run winrar
from pathlib import Path
from PyPDF2 import PdfFileReader, PdfFileWriter
from pdfminer.high_level import extract_text


# Global variables

arch_leidos          = 0 # archivos leidos
arch_procesados      = 0
wrk_procesados       = 0
cuenta_nuevos_grupos = 0 # Cuenta nuevos grupos, por cada 10 envia proceso de empacado
suma_arch_en_grupos  = 0


max_files_per_iteration = 200  # Se usa especialmente para empacar xml por ser demasiados, al concatenar nombres se satura y envia mensaje de error

# --- AJUSTE A 19 MB ---
size_limit              = 19922944  # Limite grupo ZIP (~19 MB: 19 * 1024 * 1024)
size_limit2             = 19451084  # Limite de reempacado (~18.55 MB)
limite_arch_origen      = 19922944  # Cualquier archivo en arbol origen debe ser <= 19 MB

limite_dispara_empacado = 10       # por cada 10 grupos generados envia a empacar[cite: 1]
acumula_grupos          = 0

# LIMITES PARA LOS BLOQUES DE EMPACADO
limite1mb   = 1000000
limite2mb   = 2000000
limite500kb = 500000
limite50kb  = 50000

winrar_ruta = "C:\\winrar_ejecutable\\WinRAR.exe"

# Set the desired compression level (0-5)
compression_level = 3  # Example: Use 3 for normal compression[cite: 1]
# Set the number of threads to use for compression
num_threads = 4  # Example: Use 4 threads[cite: 1]


def pause_execution():
    print("Press the space bar to continue...")
    while True:
        if msvcrt.kbhit() and msvcrt.getch() == b' ':
            break


# Empaca archivos
def empacar_archivos(groups, group_sizes):
    for iCnt, group in enumerate(groups):
        ruta_salida = f"{ruta_arch}-{iCnt:04}.zip"
        
        # Si existe, borra el .zip y lo vuelve a crear[cite: 1]
        if os.path.exists(ruta_salida):
            zip_size = os.path.getsize(ruta_salida)
            if zip_size < size_limit2:
                
                os.remove(ruta_salida)                           # Eliminar archivo comprimido actual[cite: 1]
                           
                # Envia solicitudes de empacado por cada "max_files_per_iteration"[cite: 1]
                num_files = len(groups[iCnt])
                for idx in range(0, num_files, max_files_per_iteration):
                    
                    files_to_archive = groups[iCnt][idx:idx+max_files_per_iteration]
                    zip_files_with_winrar(files_to_archive, ruta_salida)
                               
                zip_size = os.path.getsize(ruta_salida)          # Obtiene tamaño del archivo comprimido[cite: 1]
                group_sizes[iCnt] = zip_size                     # Reasigna nuevo tamaño[cite: 1]
                                
        else:
            # Si no existe .zip genera comando de empacado[cite: 1]
            num_files = len(groups[iCnt])
            for idx in range(0, num_files, max_files_per_iteration):
                
                files_to_archive = groups[iCnt][idx:idx+max_files_per_iteration]
                zip_files_with_winrar(files_to_archive, ruta_salida)
                               
            zip_size = os.path.getsize(ruta_salida)          # Obtiene tamaño del archivo comprimido[cite: 1]
            group_sizes[iCnt] = zip_size                     # Reasigna nuevo tamaño[cite: 1]
        
    
def zip_files_with_winrar(group, ruta_salida):
    cmd = [winrar_ruta, 'a', '-afzip', '-m' + str(compression_level), '-mt' + str(num_threads), ruta_salida] + group
    subprocess.run(cmd)


def validapdf():
    try:
        text = extract_text(file)
    except:
        print("No fue posible leer el PDF", file)
        quit()


def separate_files_by_size_optimized(wrk_punto, sorted_files, size_limit):
    
    global arch_leidos
    global arch_procesados
    global wrk_procesados
    global cuenta_nuevos_grupos
    global limite_dispara_empacado
    global acumula_grupos
    global suma_arch_en_grupos
    
    groups = []
    group_sizes = []
    
    sorted_files = sorted(sorted_files, key=lambda x: os.path.getsize(x), reverse=True)
    
    # PRIMER RECORRIDO CON ARCHIVOS >= limite50kb[cite: 1]
    print("CARPETA:", wrk_punto, " ", "PRIMER RECORRIDO ARCH >= limite50kb (Límite max 19MB)")
    
    cuenta_nuevos_grupos = 0
    arch_leidos = 0
    arch_procesados = 0
    for archSAT in sorted_files:
        
        file_size = os.path.getsize(archSAT)
        added = False
        
        if file_size < limite50kb:
            continue
        
        arch_leidos += 1
        
        if cuenta_nuevos_grupos > limite_dispara_empacado:
            print("CARPETA:", wrk_punto, " ", "CICLO 1: comprimiendo ")
            cuenta_nuevos_grupos = 0
            empacar_archivos(groups, group_sizes)
        
        for i in range(len(groups)):
            acumula_grupos = i

            if group_sizes[i] + file_size <= size_limit:
                groups[i].append(archSAT)
                arch_procesados += 1
                group_sizes[i] += file_size
                added = True
                break
        
        if not added:
            print("CARPETA:", wrk_punto, " ", "ciclo 1 CREANDO NUEVO GRUPO", acumula_grupos)
            groups.append([archSAT])
            cuenta_nuevos_grupos += 1
            arch_procesados += 1
            group_sizes.append(file_size)
    
    print("CARPETA:", wrk_punto, " ", "comienza EMPACADO GENERAL 1")                
    empacar_archivos(groups, group_sizes)
    
    # SEGUNDO RECORRIDO CON ARCHIVOS de 0 a 50kb -1[cite: 1]
    print("CARPETA:", wrk_punto, " ", "Segundo RECORRIDO ARCH 0 a 50kb")
    
    for archSAT in sorted_files:
        
        file_size = os.path.getsize(archSAT)
        added = False
        
        if file_size >= limite50kb:
            continue
        
        arch_leidos += 1
                
        for i in range(len(groups)):
            acumula_grupos = i

            if group_sizes[i] + file_size <= size_limit:
                groups[i].append(archSAT)
                arch_procesados += 1
                group_sizes[i] += file_size
                added = True
                break
        
        if not added:
            print("CARPETA:", wrk_punto, " ", "ciclo 2 CREANDO NUEVO GRUPO", acumula_grupos)
            groups.append([archSAT])
            arch_procesados += 1
            group_sizes.append(file_size)

    # Imprime salida[cite: 1]
    with open("output.txt", "w", encoding='utf-8') as file:
        for yx in range(len(groups)):
            print("imprimegrupos antes de empacar final ", yx, "num-entries:", len(groups[yx]))

            for nombrearch_en_grupo in groups[yx]:
                file_size = os.path.getsize(nombrearch_en_grupo)
                file.write(str(nombrearch_en_grupo) + "|" + str(yx) + "|" + f"{file_size}" + "\n")
    
    return groups


##################################################################################################
# Inicio validaciones previas al empacado
##################################################################################################

today = datetime.date.today()
wrkdir = '.'

basefolder = [name for name in os.listdir(wrkdir) if os.path.isdir(os.path.join(wrkdir, name))]

for file in basefolder:
    
    print("CARPETA:", file, " ", "ELIMINANDO .db, .ini")
    for ruta_y_nombre in Path(file).rglob('*.db'):
        print("CARPETA:", file, " ", "Archivo .db encontrado, eliminando ", ruta_y_nombre.name)
        os.unlink(ruta_y_nombre)
    for ruta_y_nombre in Path(file).rglob('*.ini'):
        print("CARPETA:", file, " ", "Archivo .ini encontrado, eliminando ", ruta_y_nombre.name)
        os.unlink(ruta_y_nombre)

    ruta_arch = Path(file) 
    objeto_arch = [e for e in ruta_arch.rglob('*.*') if e.is_file() and os.path.getsize(e)]
    objeto_arch = sorted(objeto_arch, key=os.path.getsize)

    # Verifica si un archivo tiene tamaño mayor al limite de 19 MB[cite: 1]
    print("CARPETA:", file, " ", "Verificando si un archivo tiene tamaño mayor al limite", limite_arch_origen)
    verif = 0
    for file in objeto_arch:
        verif = os.path.getsize(file)
        
        if verif > limite_arch_origen:
            print("Carpeta:", file, " ", "El archivo", file, "es superior en tamaño, abortando. Tamaño arch:", verif, "limite:", limite_arch_origen)
            quit()
        
    for file in objeto_arch:
        archivo = Path(file)
        doc = open("Total Origen-" + str(today) + ".txt", "a", encoding='utf-8')
        doc.write(str(archivo) + "\n")
        doc.close()

print("Verificación terminada")

##################################################################################################
# PROCESO PRINCIPAL DE EMPACADO
##################################################################################################

today = datetime.date.today()
wrkdir = '.'

wrk_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
doc = open("c:\\SAT_logs\\Log-" + str(today) + ".txt", "a", encoding='utf-8')

doc.write("____________________________________________________________________________________________\n")
doc.write("COMIENZA PROCESO DE EMPACADO (19 MB): " + str(wrk_time) + "\n")
doc.write("____________________________________________________________________________________________\n")
doc.close()

basefolder = [name for name in os.listdir(wrkdir) if os.path.isdir(os.path.join(wrkdir, name))]
root_folders = [name for name in os.listdir(wrkdir) if os.path.isdir(os.path.join(name))]

for file in root_folders:
    if not file.startswith("tempo"):
        mainfoldername = file

for file in basefolder:
  
    ruta_arch = Path(file) 
    count_same_size = 0
    
    sorted_files = [e for e in ruta_arch.rglob('*.*') if e.is_file() and not e.name.endswith('.zip') and os.path.getsize(e)]
 
    groups = separate_files_by_size_optimized(file, sorted_files, size_limit)
    
    print("CARPETA:", file, " ", "total de grupos a procesar ", len(groups))

    for i, group in enumerate(groups):
        ruta_salida = f"{ruta_arch}-{i:04}.zip"
        
        if os.path.exists(ruta_salida):
            os.remove(ruta_salida)
        
        print("CARPETA:", file, " ", "Generando zip FINAL", i, " ruta ", ruta_salida, "num-entries:", len(groups[i]))
        
        num_files = len(groups[i])
        for idx in range(0, num_files, max_files_per_iteration):
            print("CARPETA:", file, " ", "iteraciones ", idx, "inter:", idx + max_files_per_iteration)
            files_to_archive = groups[i][idx:idx + max_files_per_iteration]
            zip_files_with_winrar(files_to_archive, ruta_salida)
            
    suma_arch_en_grupos = 0
    print("=========================================================")
    print("CARPETA:", file, " ", "CIFRAS DE CONTROL (Límite 19 MB)")
    print("=========================================================")
    
    for y in range(len(groups)):
        print("Carpeta:", file, " ", "Grupos creados ", y, "num-entries:", len(groups[y]))
        suma_arch_en_grupos += len(groups[y])
    
    print("CARPETA:", file, " ", "archivos leidos total", arch_leidos)
    print("CARPETA:", file, " ", "archivos Procesados total", arch_procesados)
    print("CARPETA:", file, " ", "SUMA DE archivos en grupos:", suma_arch_en_grupos)
    
    wrk_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    doc = open("c:\\SAT_logs\\Log-" + str(today) + ".txt", "a", encoding='utf-8')
    doc.write("CARPETA:" + str(file) + " CIFRAS DE CONTROL:" + str(wrk_time) + "\n")
    doc.write("Total archivos leidos:" + str(arch_leidos) + "\n")
    doc.write("Total archivos procesados:" + str(arch_procesados) + "\n")
    doc.write("SUMA de archivos en grupos:" + str(suma_arch_en_grupos) + "\n")
    doc.write("\n")
    for y in range(len(groups)):
        doc.write("Carpeta:" + str(file) + " grupos CREADOS " + str(y) + " num-entries:" + str(len(groups[y])) + "\n")
    doc.write("____________________________________________________________________________________________\n")
    doc.close()

wrk_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
doc = open("c:\\SAT_logs\\Log-" + str(today) + ".txt", "a", encoding='utf-8')
doc.write("TERMINA PROCESO DE EMPACADO: " + str(wrk_time) + "\n")
doc.write("____________________________________________________________________________________________\n")
doc.close()