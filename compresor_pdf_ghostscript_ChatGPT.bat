@echo off
setlocal EnableExtensions DisableDelayedExpansion
title Compresor de PDF con Ghostscript

echo ==========================================
echo       COMPRESOR DE PDF - GHOSTSCRIPT
echo ==========================================
echo.
echo 1^) Alta        - /prepress
echo 2^) Media-Alta  - /printer
echo 3^) Media       - /ebook
echo 4^) Media-Baja  - /screen
echo 5^) Baja        - Maxima compresion (72 dpi, sin metadatos)
echo.

:MENU
set "OPCION="
set /p "OPCION=Seleccione un nivel [1-5]: "
if "%OPCION%"=="1" goto OPCION1
if "%OPCION%"=="2" goto OPCION2
if "%OPCION%"=="3" goto OPCION3
if "%OPCION%"=="4" goto OPCION4
if "%OPCION%"=="5" goto OPCION5
echo.
echo [ERROR] Opcion no valida. Seleccione un numero del 1 al 5.
echo.
goto MENU

:OPCION1
set "PRESET=/prepress"
set "NOMBRE_NIVEL=Alta"
goto ARCHIVOS

:OPCION2
set "PRESET=/printer"
set "NOMBRE_NIVEL=Media-Alta"
goto ARCHIVOS

:OPCION3
set "PRESET=/ebook"
set "NOMBRE_NIVEL=Media"
goto ARCHIVOS

:OPCION4
set "PRESET=/screen"
set "NOMBRE_NIVEL=Media-Baja"
goto ARCHIVOS

:OPCION5
set "PRESET="
set "NOMBRE_NIVEL=Baja - 72 dpi, sin metadatos"
goto ARCHIVOS

:ARCHIVOS
echo.
echo Nivel seleccionado: %NOMBRE_NIVEL%
echo.

set "GS="
where gswin64c.exe >nul 2>&1
if not errorlevel 1 set "GS=gswin64c.exe"
if not defined GS (
    where gs.exe >nul 2>&1
    if not errorlevel 1 set "GS=gs.exe"
)

if not defined GS (
    echo [ERROR] Ghostscript no esta instalado o no se encuentra en PATH.
    goto FIN
)

echo Ghostscript detectado: %GS%
echo.

set "INPUT="
set /p "INPUT=Introduzca la ruta del PDF de entrada: "
if not defined INPUT (
    echo [ERROR] No se especifico un archivo de entrada.
    goto FIN
)
if /I not "%INPUT:~-4%"==".pdf" set "INPUT=%INPUT%.pdf"

if not exist "%INPUT%" (
    echo.
    echo [ERROR] El archivo de entrada no existe:
    echo "%INPUT%"
    goto FIN
)

set "OUTPUT="
set /p "OUTPUT=Introduzca la ruta del PDF de salida: "
if not defined OUTPUT (
    echo [ERROR] No se especifico un archivo de salida.
    goto FIN
)
if /I not "%OUTPUT:~-4%"==".pdf" set "OUTPUT=%OUTPUT%.pdf"

if /I "%INPUT%"=="%OUTPUT%" (
    echo.
    echo [ERROR] El archivo de entrada y el de salida no pueden ser el mismo.
    goto FIN
)

echo.
echo Archivo de entrada:
echo "%INPUT%"
echo Archivo de salida:
echo "%OUTPUT%"
echo Nivel: %NOMBRE_NIVEL%
echo.
echo Iniciando compresion...
echo.

if "%OPCION%"=="5" goto COMPRESION_MAXIMA

"%GS%" -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dNOPAUSE -dBATCH -dSAFER -dQUIET -dPDFSETTINGS=%PRESET% -sOutputFile="%OUTPUT%" "%INPUT%"
if errorlevel 1 (
    echo.
    echo [ERROR] Ghostscript no pudo completar la compresion.
    if exist "%OUTPUT%" del /q "%OUTPUT%" >nul 2>&1
    goto FIN
)
goto EXITO

:COMPRESION_MAXIMA
"%GS%" -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dNOPAUSE -dBATCH -dSAFER -dQUIET ^
-dDetectDuplicateImages=true ^
-dDownsampleColorImages=true -dColorImageResolution=72 -dColorImageDownsampleType=/Average ^
-dDownsampleGrayImages=true -dGrayImageResolution=72 -dGrayImageDownsampleType=/Average ^
-dDownsampleMonoImages=true -dMonoImageResolution=72 -dMonoImageDownsampleType=/Subsample ^
-dAutoFilterColorImages=false -dColorImageFilter=/DCTEncode ^
-dAutoFilterGrayImages=false -dGrayImageFilter=/DCTEncode ^
-dJPEGQ=25 ^
-dOmitInfo=true ^
-dMetadata=none ^
-sOutputFile="%OUTPUT%" "%INPUT%"

if errorlevel 1 (
    echo.
    echo [ERROR] Ghostscript no pudo completar la compresion.
    if exist "%OUTPUT%" del /q "%OUTPUT%" >nul 2>&1
    goto FIN
)

:EXITO
echo.
echo ==========================================
echo COMPRESION COMPLETADA CORRECTAMENTE
echo ==========================================
echo Archivo generado:
echo "%OUTPUT%"
echo.

:FIN
pause
endlocal
