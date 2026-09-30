"""
program name:comprime4mb.py
creado por:jprieto/jmanzo
modificaciones:
jlm01 06Jun23 se eliminaron ciclos de compresion para dejar unicamente rango
              de 50kb a 4mb en un ciclo y 0 a 50kb en otro ciclo
              
jlm02 09Jun23 agregar encode utf8 para rutina with open 

"""

"""
pendientes:
archivos sin extension
comparar desde excel leidos por python versus extraidos con comandos de OS
que hacer con todos  los pequeños
enviar a empacar por lotes cuando sean muchos archivos pequeños para evitar error:FileNotFoundError: [WinError 206] El nombre del archivo o la extensión es demasiado largo
aprox con 300 ha funcionado

CAUSAS DE DIFERENCIAS ENTRE python y OS:
1 algunos files con ñ difieren al comparar
info_usuarios\gabriel\solicitudes Octubre 2022\dolares\REPORTE PARA JM 206199 v02 from gabriel±.xlsx
info_usuarios\gabriel\solicitudes Octubre 2022\dolares\REPORTE PARA JM 206199 v02 from gabrielñ.xlsx

2 por alguna razon hay archivos que tiene espacio entre ciertas palabras pero en python tienen 1 espacio mientras que en OS tienen 2
3 el comando de python no obtiene archivos sin extension
4 python si lee archivos ocultos como estos:
info_usuarios\jcrr\~$consumos enero-oct 2022.xlsx
info_usuarios\jcrr\~$ejemplo flujo de efectivo.xlsx
info_usuarios\fhorta\saldo proveedores cuentas 202000 y 203000 sep2022 reproceso\~$saldo proveedores sep2022 cuentas 202 y 2023 (detalle).xlsx
info_usuarios\fv\~$requisicion p08024.xlsx
info_usuarios\fv\~$resumen 3 facturas.xlsx
5.- Python no muestra archivos con tamaño ZERO, que hacer?

6.- El limite de tamaño de archivo individual txt, pdf, jpg, cuanto debe ser?


cmd = 'WinRAR.exe a -r -m5 -ep1 -y "{}" "{}\\*"'.format(
        os.path.join(folder_path, "compressed_files.rar"), folder_path
        
        
"""


#FUNCIONES CON POSIBLE USO
#pause_execution()
#sorted_files = [e for e in path.rglob('*.*') if e.is_file() and os.path.getsize(e)]

# Remove a specific entry from the sorted_files list
#entry_to_remove = sorted_files[0]  # Replace with the entry you want to remove
#sorted_files.remove(entry_to_remove)


#time.sleep(3)  # Pause for 3 seconds


#sorted_files = [...]  # Sorted list of file objects
#size_limit = 1000000  # Maximum total size for each group (e.g., 1 MB)
#groups = separate_files_by_size_optimized(sorted_files, size_limit)


"""
FUNCIONES CON POSIBLE USO
    for i in range(len(groups)):
        print("grupo",i, "tamaño ",group_sizes[i])


"""

"""
DESCRIPCION GENERAL DEL ALGORITMO:
Se crean N grupos para poder generar N archivos ZIP de 4 MB 
Para crearlos se crean subdivisiones:
50kb a 4mb
0 a 50kb

"""


import shutil
import filecmp

import os 
import shutil
import sys
import datetime
import time
import zipfile    #To use python zip libraries
import msvcrt     #To create a pause space bar
import subprocess #To run winrar
from pathlib import Path
from PyPDF2 import PdfFileReader, PdfFileWriter
from pdfminer.high_level import extract_text


# Global variable

arch_leidos          = 0 #archivos leidos
arch_procesados      = 0
wrk_procesados       = 0
cuenta_nuevos_grupos = 0 #Cuenta nuevos grupos, por cada 10 envia proceso de empacado
suma_arch_en_grupos  = 0



max_files_per_iteration = 200  # Se usa especialmente para empacar xml por ser demasiados, al concatenar nombres se satura y envia mensaje de error
size_limit              = 3990000  # limite 4 Mb
size_limit2             = 3900000  # si es mayor a este tamaño, ya no se elimina para reempacar
limite_arch_origen      = 4200000  # Cualquier archivo en arbol origen debe ser <= a este tamaño
limite_dispara_empacado = 10       # por cada 10 grupos generados envia a empacar
acumula_grupos          = 0

#LIMITES PARA LOS BLOQUES DE EMPACADO
limite1mb   = 1000000
limite2mb   = 2000000
limite500kb = 500000
limite50kb  = 50000

#winrar_ruta = "C:\\Program Files\\WinRAR\\WinRAR.exe"
#winrar_ruta = "C:\\test_zip01\\WinRAR.exe"

winrar_ruta = "C:\\winrar_ejecutable\\WinRAR.exe"


# Set the desired compression level (0-5)
compression_level = 3  # Example: Use 3 for normal compression
# Set the number of threads to use for compression
num_threads = 4  # Example: Use 4 threads
# Set the dictionary size (KB)

#Este parametro no aplica para winrar cuando se crean archivos zip (chatGPT)
#dictionary_size = 2048  # Example: Use 2048 KB (2MB)


def pause_execution():
    print("Press the space bar to continue...")
    while True:
        if msvcrt.kbhit() and msvcrt.getch() == b' ':
            break

    
""" NO USADA pendiente porque no toma archivos en root del folder origen
# Function to compare file sizes recursively
def compare_file_sizes(dir1, dir2):
    print("COMPARANDO tamaño")
    dir_comparison = filecmp.dircmp(dir1, dir2)

    for file in dir_comparison.common_files:
        file1_ruta = os.path.join(dir1, file)
        file2_ruta = os.path.join(dir2, file)

        file1_size = os.path.getsize(file1_ruta)
        file2_size = os.path.getsize(file2_ruta)

        if file1_size != file2_size:
            print(f"File '{file}' has a different size.")

    for subdir in dir_comparison.common_dirs:
        subdir1 = os.path.join(dir1, subdir)
        subdir2 = os.path.join(dir2, subdir)
        compare_file_sizes(subdir1, subdir2)

"""


#Empaca archivos
def empacar_archivos(groups, group_sizes):
    for iCnt, group in enumerate(groups):
        ruta_salida = f"{ruta_arch}-{iCnt:04}.zip"
        
        # Si existe, borra el .zip y lo vuelve a crear
        if os.path.exists(ruta_salida):
            zip_size = os.path.getsize(ruta_salida)
            if zip_size < size_limit2:
                
                os.remove(ruta_salida)                           #Eliminar archivo comprimido actual
                           
                # Envia solicitudes de empacado por cada "max_files_per_iteration"
                num_files = len(groups[iCnt])
                for idx in range(0, num_files, max_files_per_iteration):
                    
                    files_to_archive = groups[iCnt][idx:idx+max_files_per_iteration] #si max = 100, de 0 a 99 y despues de 100 a 199
                    # Prepare the command to call WinRAR
                    zip_files_with_winrar(files_to_archive, ruta_salida) #Enviar nuevamente a comprimir
                               
                zip_size = os.path.getsize(ruta_salida)          #Obtiene tamaño del archivo comprimido
                           
                group_sizes[iCnt] = zip_size                     #Reasigna nuevo tamaño
                                
        else:
            #Si no existe .zip genera comando de empacado
            num_files = len(groups[iCnt])
            for idx in range(0, num_files, max_files_per_iteration):
                
                files_to_archive = groups[iCnt][idx:idx+max_files_per_iteration] #si max = 100, de 0 a 99 y despues de 100 a 199
                # Prepare the command to call WinRAR
                zip_files_with_winrar(files_to_archive, ruta_salida) #Enviar nuevamente a comprimir
                               
            zip_size = os.path.getsize(ruta_salida)          #Obtiene tamaño del archivo comprimido
                         
            group_sizes[iCnt] = zip_size                     #Reasigna nuevo tamaño
        
    
    
#zip files recomendado chatgpt
def zip_files_with_winrar(group, ruta_salida):

    # OLD COMMAND cmd = ['WinRAR.exe', 'a', ruta_salida] + group
    
    #no aplica dictionary size cuando se crean zip files
    #cmd = [winrar_ruta, 'a', '-afzip', '-m' + str(compression_level), '-mt' + str(num_threads),'-md' + str(dictionary_size), ruta_salida] + group
    
    # a append 
    # -afzip empacar en formato zip
    #ep1 Exclude path nivel1(no funciona, elimina 1er nivel)
    
    cmd = [winrar_ruta, 'a', '-afzip', '-m' + str(compression_level), '-mt' + str(num_threads), ruta_salida] + group
    


    #print("empacando",cmd)
    subprocess.run(cmd)
    #print("termina empacando",cmd)
    

#valida pdf jprieto
def validapdf():
    try:
        text = extract_text(file)
    except:
        print("No fue posible leer el PDF",file)
        quit()





# logica sugerida chatgpt
# 1er recorrido     (Intenta llenar N grupos con archivo >= 50kb           (Con ciclos de empacado cada 10 grupos)
# Ultimo recorrido  (Inserta todos los arch pequeños en cualquiera de los grupos (sin ciclo de empacado cada 10 grupos)

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
    
    # Sort the files in decreasing order of size
    #sorted_files = sorted(sorted_files, key = os.path.getsize)
    sorted_files = sorted(sorted_files, key=lambda x: os.path.getsize(x), reverse=True)
    
    # ====================================================================
    # ====================================================================
    #PRIMER RECORRIDO CON ARCHIVOS >= limite50kb
    # ====================================================================
    # ====================================================================
    print("CARPETA:",wrk_punto," ","PRIMER RECORRIDO ARCH >= limite2mb")
    
    cuenta_nuevos_grupos = 0
    arch_leidos = 0
    arch_procesados = 0
    for archSAT in sorted_files:
        
        file_size = os.path.getsize(archSAT)
        added = False
        
        if file_size < limite50kb: #2MB , 1 megabyte (MB) = 1,048,576 bytes
            continue
        
        arch_leidos += 1
        
        if cuenta_nuevos_grupos > limite_dispara_empacado:

            print("CARPETA:",wrk_punto," ","CICLO 1: comprimiendo ")
            
            cuenta_nuevos_grupos = 0
            empacar_archivos(groups,group_sizes) #Empacar archivos
        
        # Try to fit the archSAT into existing groups in decreasing order of available space
        for i in range(len(groups)):
            acumula_grupos = i
            # Call the function to create a pause
            #pause_execution()

            if group_sizes[i] + file_size <= size_limit:
                #if len(groups[i]) <= 300:
                groups[i].append(archSAT)
                arch_procesados += 1
                group_sizes[i] += file_size
                added = True
                #print("inside loop group ", i,"num-entries:", len(groups[i])," group size ",group_sizes[i], " File size:",file_size, "file-name ",archSAT)
                break
        
        # If the archSAT couldn't fit into any existing group, create a new group
        
        if not added:
            
            print("CARPETA:",wrk_punto," ","ciclo 1 CREANDO NUEVO GRUPO",acumula_grupos)
            groups.append([archSAT])
            cuenta_nuevos_grupos += 1
            arch_procesados += 1
            group_sizes.append(file_size)
    
    print("CARPETA:",wrk_punto," ","comienza EMPACADO GENERAL 1")                
    empacar_archivos(groups,group_sizes) #Empacar archivos
    
    
    # ====================================================================
    # ====================================================================
    #Segundo RECORRIDO CON ARCHIVOS de 0 a 50kb -1
    # ====================================================================
    # ====================================================================
    print("CARPETA:",wrk_punto," ","Segundo RECORRIDO ARCH 0 a 50kb")
    
    for archSAT in sorted_files:
        
        file_size = os.path.getsize(archSAT)
        added = False
        
        #Procesa unicamente archivos de tamaño 0 a 50kb -1
        if file_size >= limite50kb: #1 megabyte (MB) = 1,048,576 bytes
            continue
        
        arch_leidos += 1
                
        # Try to fit the archSAT into existing groups in decreasing order of available space
        for i in range(len(groups)):
            acumula_grupos = i
            # Call the function to create a pause
            #pause_execution()

            if group_sizes[i] + file_size <= size_limit:
                #if len(groups[i]) <= 300:
                groups[i].append(archSAT)
                arch_procesados += 1
                group_sizes[i] += file_size
                added = True
                #print("inside loop group ", i,"num-entries:", len(groups[i])," group size ",group_sizes[i], " File size:",file_size, "file-name ",archSAT)
                break
        
        # If the archSAT couldn't fit into any existing group, create a new group
        
        if not added:
            
            print("CARPETA:",wrk_punto," ","ciclo 2 CREANDO NUEVO GRUPO",acumula_grupos)
            groups.append([archSAT])
            arch_procesados += 1
            group_sizes.append(file_size)
            
           
                                                    
    
    #imprime grupos, tamaño y cantidad de archivos por grupo 

    # Create a text file
    with open("output.txt", "w", encoding='utf-8') as file:
        for yx in range(len(groups)):
            print("imprimegrupos antes de empacar >2mb xxx ", yx, "num-entries:", len(groups[yx]))
            #pause_execution()
            

            # Iterate over each file in the current group
            for nombrearch_en_grupo in groups[yx]:
                file_size = os.path.getsize(nombrearch_en_grupo)
                # Write the file path to the text file
                
                #file.write(str(nombrearch_en_grupo) + "archivo " + str(yx) + "\n")
                file.write(str(nombrearch_en_grupo) + "|" + str(yx) + "|" + f"{file_size}" + "\n")
                #file.write(f"{nombrearch_en_grupo} (Size: {file_size} bytes)\n")
            
    
    
    return groups


##################################################################################################
#Inicio validaciones previas al empacado
##################################################################################################


today=datetime.date.today()


wrkdir = '.'

basefolder = [name for name in os.listdir(wrkdir) if os.path.isdir(os.path.join(wrkdir, name))]

#Loop principal
for file in basefolder:
    
    #Eliminando .db y .ini
    print("CARPETA:",file," ","ELIMINANDO .db, .ini")
    for ruta_y_nombre in Path(file).rglob('*.db'):
        print("CARPETA:",file," ","Archivo .db encontrado, eliminando ",ruta_y_nombre.name)
        os.unlink(ruta_y_nombre)
    for ruta_y_nombre in Path(file).rglob('*.ini'):
        print("CARPETA:",file," ","Archivo .ini encontrado, eliminando ",ruta_y_nombre.name)
        os.unlink(ruta_y_nombre)

    #ruta y tamaño a cadena objeto, tuple por tamaño
    ruta_arch = Path(file) 
    objeto_arch = [e for e in ruta_arch.rglob('*.*') if e.is_file() and os.path.getsize(e)]
    objeto_arch = sorted(objeto_arch, key = os.path.getsize)

    """
    #Valida pdf 
    print("Verificando todos los PDF.")    
    for file in objeto_arch:
        path = Path(file)
        if path.name.endswith('.pdf'):
            validapdf()
    """        
      
    #Verifica si un archivo tiene tamaño mayor al limite
    print("CARPETA:",file," ","Verificando si un archivo tiene tamaño mayor al limite",limite_arch_origen)
    verif=0
    for file in objeto_arch:
        verif = os.path.getsize(file)
        
        if verif > limite_arch_origen:
            print("Carpeta:",file," ","El archivo",file,"es superior en tamaño, abortando. Tamaño arch:",verif, "limite:",limite_arch_origen)
            quit()
        
    #Genera Archivo con listado de archivos origen
    for file in objeto_arch:
        archivo = Path(file)
        
        doc = open("Total Origen-" + str(today) + ".txt","a", encoding='utf-8')
        doc.write(str(archivo) + "\n")
        doc.close()

    
    
print("Verificación terminada")
##################################################################################################
#TERMINA validaciones previas al empacado
##################################################################################################



#Área de trabajo (redef)
today=datetime.date.today()
wrkdir = '.'



wrk_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
doc = open("c:\\SAT_logs\Log-"+str(today) + ".txt","a", encoding='utf-8')

doc.write("____________________________________________________________________________________________" + "\n")
doc.write("____________________________________________________________________________________________" + "\n")
doc.write("____________________________________________________________________________________________" + "\n")
doc.write("COMIENZA PROCESO DE EMPACADO:" + str(wrk_time) + "\n")
doc.write("____________________________________________________________________________________________" + "\n")
doc.write("____________________________________________________________________________________________" + "\n")
doc.write("____________________________________________________________________________________________" + "\n")
doc.close()



basefolder = [name for name in os.listdir(wrkdir) if os.path.isdir(os.path.join(wrkdir, name))]

root_folders = [name for name in os.listdir(wrkdir) if os.path.isdir(os.path.join(name))]

#Ignora carpetas con nombre tempo para tomar solo 1 directorio
for file in root_folders:
    if not file.startswith("tempo"):
        mainfoldername = file



for file in basefolder:
  
    ruta_arch = Path(file) 
    count_same_size = 0
    
    sorted_files = [e for e in ruta_arch.rglob('*.*') if e.is_file() and not e.name.endswith('.zip') and os.path.getsize(e)]
 
    
    #Crea grupos de archivos, cada grupo con limite de tamaño   
    groups = separate_files_by_size_optimized(file, sorted_files, size_limit)
    
    
    print("CARPETA:",file," ","total de grupos a procesar ",len(groups))
    
    
    ##################################################################################################
    #ENVIA LA ULTIMA COMPRESION
    ##################################################################################################
    # Assuming 'groups' contains the resulting groups from the algorithm

    for i, group in enumerate(groups):

        ruta_salida = f"{ruta_arch}-{i:04}.zip"
        
        
        if os.path.exists(ruta_salida):
            os.remove(ruta_salida)
        
        print("CARPETA:",file," ","GEnerando zip FINAL",i," ruta ",ruta_salida,"num-entries:", len(groups[i]))
        
        num_files = len(groups[i])
        for idx in range(0, num_files, max_files_per_iteration):
            print("CARPETA:",file," ","iteraciones  ",idx,"inter:",idx+max_files_per_iteration)
            files_to_archive = groups[i][idx:idx+max_files_per_iteration] #si max = 100, de 0 a 99 y despues de 100 a 199
            # Prepare the command to call WinRAR
            zip_files_with_winrar(files_to_archive, ruta_salida) #Enviar nuevamente a comprimir
            
            
    
    #imprime grupos, y cantidad de archivos por grupo 
    suma_arch_en_grupos = 0
    print("CARPETA:",file," ","despues de ultimo empacado")
    
    print("=========================================================")
    print("=========================================================")
    print("CARPETA:",file," ","CIFRAS DE CONTROL")
    print("=========================================================")
    print("=========================================================")
    
    for y in range(len(groups)):
        print("Carpeta:",file," ","Grupos creados xxx ", y,"num-entries:", len(groups[y]))
        suma_arch_en_grupos = suma_arch_en_grupos + len(groups[y])
    
    print("CARPETA:",file," ","archivos leidos total",arch_leidos)
    print("CARPETA:",file," ","archivos Procesados total",arch_procesados)

    print("CARPETA:",file," ","SUMA DE archivos en grupos:",suma_arch_en_grupos)
    
    wrk_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    doc = open("c:\\SAT_logs\Log-"+str(today) + ".txt","a", encoding='utf-8')
    doc.write("CARPETA:" + str(file) + " CIFRAS DE CONTROL:" + str(wrk_time) + "\n")
    doc.write("Total archivos leidos:" + str(arch_leidos) + "\n")
    doc.write("Total archivos procesados:" + str(arch_procesados) + "\n")
    doc.write("SUMA de archivos en grupos:" + str(suma_arch_en_grupos) + "\n")
    doc.write("\n")
    doc.write("\n")
    for y in range(len(groups)):
        doc.write("Carpeta:" + str(file) + " grupos CREADOS xxx " + str(y) + " num-entries:" + str(len(groups[y])) + "\n")
    
    doc.write("____________________________________________________________________________________________" + "\n")
    doc.write("____________________________________________________________________________________________" + "\n")
    doc.write("____________________________________________________________________________________________" + "\n")
    
    doc.write("\n")
    
    doc.close()
            


wrk_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
doc = open("c:\\SAT_logs\Log-"+str(today) + ".txt","a", encoding='utf-8')

doc.write("____________________________________________________________________________________________" + "\n")
doc.write("____________________________________________________________________________________________" + "\n")
doc.write("____________________________________________________________________________________________" + "\n")
doc.write("TERMINA PROCESO DE EMPACADO:" + str(wrk_time) + "\n")
doc.write("____________________________________________________________________________________________" + "\n")
doc.write("____________________________________________________________________________________________" + "\n")
doc.write("____________________________________________________________________________________________" + "\n")
doc.close()
            
    
    
    
    
    