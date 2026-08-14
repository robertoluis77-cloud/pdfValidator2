Profile 1, original, resultado: text borroso en carta porte pdfs:

Ghostscript paramenters: tengo estos paramentros para comprimir un pdf pero me los esta comprimiendo borrosos: '-dCompatibilityLevel=1.4',
        '-dPDFSETTINGS=/ebook',
        '-dColorImageDownsampleType=/Bicubic',
        '-dColorImageResolution=120',
        '-dGrayImageDownsampleType=/Bicubic',
        '-dGrayImageResolution=120',
        '-dMonoImageDownsampleType=/Bicubic',
        '-dMonoImageResolution=120', como se puede arreglar esto para q no me mande los pfd comprimidos borrosos, los quiero legibles y comprimidos lo mas q se pueda


Opción 1: Máxima compresión + legible (recomendada)

Sube a 150 DPI (el estándar de /ebook) y añade compresión JPEG controlada en lugar de depender solo del downsampling:
Qué cambia:
150 DPI en color y escala de grises (nítido para pantalla y lectura)
300 DPI en monocromo (texto escaneado en blanco y negro se mantiene filoso)
JPEG con QFactor 0.5 (calidad media-alta, buena compresión sin artefactos feos)
Subsample en monocromo (más agresivo pero el texto B/N aguanta mejor Subsample que Bicubic)

   -sDEVICE=pdfwrite \
   -dCompatibilityLevel=1.4 \
   -dPDFSETTINGS=/ebook \
   -dNOPAUSE -dQUIET -dBATCH \
   -dColorImageResolution=150 \
   -dGrayImageResolution=150 \
   -dMonoImageResolution=300 \
   -dColorImageDownsampleType=/Bicubic \
   -dGrayImageDownsampleType=/Bicubic \
   -dMonoImageDownsampleType=/Subsample \
   -dDownsampleColorImages=true \
   -dDownsampleGrayImages=true \
   -dDownsampleMonoImages=true \
   -dAutoFilterColorImages=false \
   -dAutoFilterGrayImages=false \
   -dColorImageFilter=/DCTEncode \
   -dGrayImageFilter=/DCTEncode \
   -dColorImageDict="<< /QFactor 0.5 /Blend 1 /HSamples [2 1 1 2] /VSamples [2 1 1 2] >>" \
   -dGrayImageDict="<< /QFactor 0.5 /Blend 1 /HSamples [2 1 1 2] /VSamples [2 1 1 2] >>" \
   -dSubsetFonts=true \
   -dCompressFonts=true \
   -dDetectDuplicateImages=true \
   -sOutputFile=salida.pdf \
  




Opción 2: Si el texto sigue borroso (PDFs escaneados)
Si tu PDF es un escaneo (todo es imagen), sube todo a 200 DPI y usa calidad JPEG más alta:
   
   -sDEVICE=pdfwrite \
   -dCompatibilityLevel=1.4 \
   -dNOPAUSE -dQUIET -dBATCH \
   -dColorImageResolution=200 \
   -dGrayImageResolution=200 \
   -dMonoImageResolution=200 \
   -dColorImageDownsampleType=/Bicubic \
   -dGrayImageDownsampleType=/Bicubic \
   -dMonoImageDownsampleType=/Bicubic \
   -dDownsampleColorImages=true \
   -dDownsampleGrayImages=true \
   -dDownsampleMonoImages=true \
   -dAutoFilterColorImages=false \
   -dAutoFilterGrayImages=false \
   -dColorImageFilter=/DCTEncode \
   -dGrayImageFilter=/DCTEncode \
   -dColorImageDict="<< /QFactor 0.4 /Blend 1 /HSamples [2 1 1 2] /VSamples [2 1 1 2] >>" \
   -dGrayImageDict="<< /QFactor 0.4 /Blend 1 /HSamples [2 1 1 2] /VSamples [2 1 1 2] >>" \
   -dSubsetFonts=true \
   -dCompressFonts=true \
   -dDetectDuplicateImages=true \
   -sOutputFile=salida.pdf \
   

Opción 3: Si necesitas el archivo muy pequeño y el contenido es mayormente texto vectorial
Si el PDF tiene texto real (no escaneado), no necesitas tocar las imágenes tanto. Enfócate en fuentes y estructura:
   
   -sDEVICE=pdfwrite \
   -dCompatibilityLevel=1.4 \
   -dPDFSETTINGS=/ebook \
   -dNOPAUSE -dQUIET -dBATCH \
   -dSubsetFonts=true \
   -dCompressFonts=true \
   -dDetectDuplicateImages=true \
   -dRemoveUnusedResources=true \
   -dPreserveHalftoneInfo=false \
   -dPreserveOverprintSettings=false \
   -dUCRandBGInfo=/Remove \
   -sOutputFile=salida.pdf \


   From kimi:


const GS_args2 = [

   '-sDEVICE=pdfwrite',
    '-dCompatibilityLevel=1.4',
    '-dNOPAUSE',
    '-dQUIET',
    '-dBATCH',
    
    # === NO usar PDFSETTINGS (sobreescribe resoluciones y destruye escaneos) ===
    # '-dPDFSETTINGS=/ebook',  ← ELIMINAR
    
    # === Para documentos escaneados: NO hacer downsampling ===
    # Mantiene la resolución original del escaneo (típicamente 200-300 DPI)
    '-dDownsampleColorImages=false',
    '-dDownsampleGrayImages=false',
    '-dDownsampleMonoImages=false',
    
    # === Compresión JPEG con calidad alta (sin perder resolución) ===
    '-dAutoFilterColorImages=false',
    '-dAutoFilterGrayImages=false',
    '-dColorImageFilter=/DCTEncode',
    '-dGrayImageFilter=/DCTEncode',
    
    # QFactor 0.15 = calidad ~85% (nítido pero comprimido)
    # QFactor 0.25 = calidad ~75% (más pequeño, aún legible)
    '-dColorImageDict=<< /QFactor 0.15 /Blend 1 /HSamples [2 1 1 2] /VSamples [2 1 1 2] >>',
    '-dGrayImageDict=<< /QFactor 0.15 /Blend 1 /HSamples [2 1 1 2] /VSamples [2 1 1 2] >>',
    
    # === Imágenes monocromo (1-bit): compresión sin pérdida ===
    '-dMonoImageFilter=/CCITTFaxEncode',
    '-dMonoImageDict=<< /K -1 /Columns 1728 >>',
    
    # === Optimización de fuentes y estructura ===
    '-dSubsetFonts=true',
    '-dCompressFonts=true',
    '-dDetectDuplicateImages=true',
    '-dCompressPages=true'
   
     ];
