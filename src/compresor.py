#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
compresor.py — Empacado por lotes de archivos en ZIP mediante WinRAR.

Unifica comprime4mb.py y comprime19mb.py: el perfil (4 MB o 19 MB) se
selecciona por línea de comandos en lugar de mantener dos scripts duplicados.

Uso:
    python src/compresor.py --limite 4mb
    python src/compresor.py --limite 19mb
"""

from __future__ import annotations

import argparse
import datetime
import logging
import os
import subprocess
import sys
from dataclasses import dataclass, replace
from pathlib import Path

# Umbral aproximado para WinError 206 (nombre de archivo o extensión demasiado largo)
UMBRAL_RUTA_LARGA = 240  # caracteres
PREFIJO_RUTA_LARGA = "\\\\?\\"


@dataclass(frozen=True)
class Config:
    """Configuración inmutable del empacador."""
    limite_grupo: int              # bytes por grupo ZIP (límite superior)
    limite_reempacado: int         # no reempacar ZIPs cuyo tamaño >= este valor
    limite_arch_origen: int        # tamaño máximo permitido para un archivo individual
    limite50kb: int = 50_000
    limite_dispara_empacado: int = 10
    max_files_per_iteration: int = 200
    nivel_compresion: int = 3
    num_hilos: int = 4
    timeout_segundos: int = 600
    winrar_ruta: Path = Path(r"C:\Program Files\WinRAR\WinRAR.exe")
    log_dir: Path = Path(r"C:\Compression_WinRAR_logs")
    wrkdir: Path = Path(".")


PERFILES = {
    "4mb": Config(
        limite_grupo=3_990_000,
        limite_reempacado=3_900_000,
        limite_arch_origen=4_200_000,
    ),
    "19mb": Config(
        limite_grupo=19_922_944,
        limite_reempacado=19_451_084,
        limite_arch_origen=19_922_944,
    ),
}


def ruta_segura(ruta: Path | str) -> str:
    """
    Devuelve la ruta con prefijo \\\\?\\ si supera el umbral de WinError 206.
    Evita errores al manejar rutas muy largas en Windows.
    """
    texto = str(ruta)
    if len(texto) < UMBRAL_RUTA_LARGA:
        return texto
    absoluta = str(Path(texto).resolve())
    if not absoluta.startswith(PREFIJO_RUTA_LARGA):
        absoluta = PREFIJO_RUTA_LARGA + absoluta
    return absoluta


def tamano_archivo(ruta: Path) -> int:
    """Obtiene el tamaño de un archivo, aplicando corrección para rutas largas."""
    return os.path.getsize(ruta_segura(ruta))


def descubrir_archivos(carpeta: Path) -> dict[Path, int]:
    """
    Descubre archivos para empacar.
    Incluye archivos sin extensión.
    Excluye: .zip, archivos que empiecen con ~$ (bloqueo de Office), y archivos de tamaño 0.
    """
    archivos: dict[Path, int] = {}
    for entrada in carpeta.rglob("*"):
        if not entrada.is_file():
            continue
        if entrada.name.endswith(".zip") or entrada.name.startswith("~$"):
            continue
        tamano = tamano_archivo(entrada)
        if tamano == 0:
            continue
        archivos[entrada] = tamano
    return archivos


def eliminar_auxiliares(carpeta: Path, log: logging.Logger, dry_run: bool = False) -> None:
    """
    Elimina archivos auxiliares .db y .ini de forma recursiva.
    En modo dry-run solo registra la intención sin eliminar.
    """
    if dry_run:
        log.info("DRY-RUN: se omitiría la eliminación de archivos .db y .ini en %s", carpeta)
        return
    for patron in ("*.db", "*.ini"):
        for ruta in carpeta.rglob(patron):
            try:
                os.unlink(ruta_segura(ruta))
                log.info("Carpeta %s: eliminado %s", carpeta, ruta.name)
            except OSError as error:
                log.error(
                    "Carpeta %s: no fue posible eliminar %s: %s",
                    carpeta,
                    ruta,
                    error,
                )


def validar_tamanos(archivos: dict[Path, int], cfg: Config) -> None:
    """
    Verifica que ningún archivo supere el límite individual.
    Lanza SystemExit si se encuentra alguno.
    """
    excedido = max(archivos.items(), key=lambda par: par[1], default=None)
    if excedido and excedido[1] > cfg.limite_arch_origen:
        raise SystemExit(
            f"El archivo {excedido[0]} supera el límite: {excedido[1]} > {cfg.limite_arch_origen}"
        )


@dataclass
class Agrupacion:
    """Resultado del proceso de agrupamiento."""
    grupos: list[list[Path]]
    tamanos: list[int]          # tamaño actual (bytes) de cada grupo
    empaquetados: set[int]      # índices de grupos ya empacados y sin cambios


def agrupar_por_tamano(
    archivos: dict[Path, int],
    carpeta: Path,
    cfg: Config,
    log: logging.Logger,
    dry_run: bool = False,
) -> Agrupacion:
    """
    Agrupa los archivos usando el algoritmo first-fit decreciente en dos recorridos:
    1. Archivos con tamaño >= limite50kb
    2. Archivos con tamaño < limite50kb
    Durante el proceso se empacan grupos intermedios cada limite_dispara_empacado + 1 grupos nuevos.
    """
    grupos: list[list[Path]] = []
    tamanos: list[int] = []
    empaquetados: set[int] = set()

    # Ordenamiento único por tamaño descendente (evita doble ordenamiento)
    ordenados = sorted(archivos, key=archivos.get, reverse=True)

    log.info(
        "Carpeta %s: primer recorrido, archivos >= %d bytes",
        carpeta.name,
        cfg.limite50kb,
    )

    nuevos_grupos = 0
    for archivo in ordenados:
        tamano = archivos[archivo]
        if tamano < cfg.limite50kb:
            continue

        # Ciclo de empacado intermedio: cada (limite_dispara_empacado + 1) grupos nuevos
        if nuevos_grupos > cfg.limite_dispara_empacado:
            log.info("Carpeta %s: ciclo 1, comprimiendo", carpeta.name)
            nuevos_grupos = 0
            empacar_grupos(
                grupos, tamanos, empaquetados, carpeta, cfg, log,
                final=False, dry_run=dry_run,
            )

        agregado = False
        for i in range(len(grupos)):
            if tamanos[i] + tamano <= cfg.limite_grupo:
                grupos[i].append(archivo)
                tamanos[i] += tamano
                agregado = True
                break

        if not agregado:
            grupos.append([archivo])
            tamanos.append(tamano)
            nuevos_grupos += 1
            log.info(
                "Carpeta %s: ciclo 1, nuevo grupo %d (tamaño %d)",
                carpeta.name,
                len(grupos) - 1,
                tamano,
            )

    log.info("Carpeta %s: empacado general 1", carpeta.name)
    empacar_grupos(
        grupos, tamanos, empaquetados, carpeta, cfg, log,
        final=False, dry_run=dry_run,
    )

    log.info(
        "Carpeta %s: segundo recorrido, archivos 0 a %d bytes",
        carpeta.name,
        cfg.limite50kb,
    )
    for archivo in ordenados:
        tamano = archivos[archivo]
        if tamano >= cfg.limite50kb:
            continue

        agregado = False
        for i in range(len(grupos)):
            if tamanos[i] + tamano <= cfg.limite_grupo:
                grupos[i].append(archivo)
                tamanos[i] += tamano
                empaquetados.discard(i)  # El grupo cambió, debe reempacarse
                agregado = True
                break

        if not agregado:
            grupos.append([archivo])
            tamanos.append(tamano)
            log.info(
                "Carpeta %s: ciclo 2, nuevo grupo %d (tamaño %d)",
                carpeta.name,
                len(grupos) - 1,
                tamano,
            )

    return Agrupacion(grupos=grupos, tamanos=tamanos, empaquetados=empaquetados)


def empacar_grupos(
    grupos: list[list[Path]],
    tamanos: list[int],
    empaquetados: set[int],
    carpeta: Path,
    cfg: Config,
    log: logging.Logger,
    final: bool = False,
    dry_run: bool = False,
) -> None:
    """
    Empaca los grupos pendientes (o todos si final=True) en archivos ZIP.
    En modo dry-run solo registra la intención sin ejecutar WinRAR ni eliminar archivos.
    """
    if dry_run:
        log.info("DRY-RUN: se omitiría la compresión con WinRAR")
        empaquetados.update(range(len(grupos)))
        return

    for idx, grupo in enumerate(grupos):
        if not final and idx in empaquetados:
            continue

        ruta_salida = cfg.wrkdir / f"{carpeta.name}-{idx:04}.zip"

        # Eliminar ZIP existente para evitar entradas duplicadas (WinRAR 'a' anexa)
        if ruta_salida.exists():
            try:
                os.remove(ruta_segura(ruta_salida))
            except OSError as error:
                log.error(
                    "Carpeta %s: no fue posible eliminar ZIP existente %s: %s",
                    carpeta,
                    ruta_salida,
                    error,
                )
                continue

        # Empacar en lotes para evitar WinError 206 (nombre demasiado largo al concatenar)
        for inicio in range(0, len(grupo), cfg.max_files_per_iteration):
            fin = inicio + cfg.max_files_per_iteration
            lote = grupo[inicio:fin]
            log.info(
                "Carpeta %s: empacando grupo %04d lote %d-%d",
                carpeta.name,
                idx,
                inicio,
                min(fin, len(grupo)),
            )
            zip_files_with_winrar(lote, ruta_salida, cfg, log)

        # Actualizar tamaño del grupo con el tamaño real del ZIP creado
        try:
            tamanos[idx] = tamano_archivo(ruta_salida)
        except OSError as error:
            raise SystemExit(
                f"El ZIP {ruta_salida} no fue creado o no es accesible tras el empacado: {error}"
            ) from error
        empaquetados.add(idx)


def zip_files_with_winrar(
    archivos: list[Path],
    ruta_salida: Path,
    cfg: Config,
    log: logging.Logger,
) -> None:
    """
    Invoca WinRAR para empacar un lote de archivos en un ZIP.
    Lanza SystemExit si el comando falla o agota el timeout.
    """
    comando = [
        str(cfg.winrar_ruta),
        "a",           # agregar archivos
        "-afzip",      # formato ZIP
        "-y",          # asumir 'Sí' a todas las preguntas
        "-ibck",       # ejecutar en segundo plano (sin ventana)
        f"-m{cfg.nivel_compresion}",
        f"-mt{cfg.num_hilos}",
        ruta_segura(ruta_salida),
    ] + [ruta_segura(a) for a in archivos]

    try:
        resultado = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            timeout=cfg.timeout_segundos,
        )
    except subprocess.TimeoutExpired as error:
        raise SystemExit(
            f"WinRAR excedió el timeout ({cfg.timeout_segundos}s) al empacar {ruta_salida}: {error}"
        ) from error
    except OSError as error:
        raise SystemExit(
            f"No se pudo ejecutar WinRAR ({cfg.winrar_ruta}) para empacar {ruta_salida}: {error}"
        ) from error

    if resultado.returncode != 0:
        error_msg = (
            f"WinRAR devolvió código {resultado.returncode} al empacar {ruta_salida}. "
            f"Salida de error: {resultado.stderr.strip()}"
        )
        log.error(error_msg)
        raise SystemExit(error_msg)


def destino_listado(
    preferida: Path,
    cfg: Config,
    log: logging.Logger,
    etiqueta: str,
) -> Path | None:
    """
    Resuelve dónde escribir un listado (Total Origen u output.txt).
    Si la carpeta de datos no permite escritura, usa la carpeta de logs;
    si tampoco, omite el listado sin abortar el empacado.
    """
    try:
        with open(preferida, "w", encoding="utf-8"):
            pass
        return preferida
    except OSError as error:
        log.warning(
            "%s: no se pudo escribir en %s (%s); se intentará en la carpeta de logs",
            etiqueta,
            preferida,
            error,
        )
    alternativa = cfg.log_dir / preferida.name
    try:
        os.makedirs(cfg.log_dir, exist_ok=True)
        with open(alternativa, "w", encoding="utf-8"):
            pass
        log.info("%s: listado redirigido a %s", etiqueta, alternativa)
        return alternativa
    except OSError as error:
        log.warning(
            "%s: tampoco se pudo escribir en %s (%s); el listado se omite",
            etiqueta,
            alternativa,
            error,
        )
        return None


def escribir_output(
    carpetas_procesadas: list[tuple[Path, Agrupacion, dict[Path, int]]],
    cfg: Config,
    log: logging.Logger,
) -> None:
    """
    Escribe el archivo output.txt con formato: ruta|grupo|tamaño, agregando los
    archivos de TODAS las carpetas procesadas en un solo archivo (modo 'w').
    Los índices de grupo son por carpeta, consistentes con los nombres de ZIP
    (<carpeta>-NNNN.zip). Cae a la carpeta de logs si la carpeta de datos está
    protegida contra escritura.
    """
    destino = destino_listado(cfg.wrkdir / "output.txt", cfg, log, "output.txt")
    if destino is None:
        return
    with open(destino, "w", encoding="utf-8") as salida:
        for carpeta, agrupacion, archivos in carpetas_procesadas:
            for idx, grupo in enumerate(agrupacion.grupos):
                for archivo in grupo:
                    salida.write(f"{archivo}|{idx}|{archivos[archivo]}\n")


def configurar_logging(cfg: Config) -> logging.Logger:
    """
    Configura el sistema de logging con handlers para consola y archivo.
    El archivo de log se crea en cfg.log_dir con nombre Log-<fecha>.txt.
    """
    os.makedirs(cfg.log_dir, exist_ok=True)
    fecha = datetime.date.today().isoformat()
    log = logging.Logger("compresor", level=logging.INFO)

    # Handler para consola
    consola = logging.StreamHandler()
    consola.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(consola)

    # Handler para archivo
    fichero = logging.FileHandler(
        cfg.log_dir / f"Log-{fecha}.txt", encoding="utf-8"
    )
    fichero.setFormatter(
        logging.Formatter("%(asctime)s | %(message)s")
    )
    log.addHandler(fichero)

    return log


def main(argv: list[str] | None = None) -> int:
    """
    Punto de entrada principal.
    Parsea argumentos, configura el entorno y procesa cada subcarpeta.
    """
    parser = argparse.ArgumentParser(
        description="Empaca subcarpetas en ZIP por lotes mediante WinRAR"
    )
    parser.add_argument(
        "--limite",
        choices=sorted(PERFILES),
        default="4mb",
        help="perfil de tamaño de grupo (4mb o 19mb)",
    )
    parser.add_argument(
        "--winrar",
        type=Path,
        default=None,
        help="ruta a WinRAR.exe (sobrescribe el valor por defecto)",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=None,
        help="carpeta de bitácora (sobrescribe el valor por defecto)",
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=None,
        help="carpeta de trabajo con las subcarpetas a empacar (sobrescribe .)",
    )
    parser.add_argument(
        "--nivel_compresion",
        type=int,
        default=None,
        help="nivel de compresión de WinRAR 0-5 (sobrescribe el valor por defecto: 3)",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="número máximo de archivos por lote de WinRAR (sobrescribe el valor por defecto)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="ejecuta en modo simulación: no elimina archivos ni ejecuta WinRAR",
    )
    args = parser.parse_args(argv)

    # Construir configuración a partir del perfil y los overrides
    cfg = PERFILES[args.limite]
    if args.winrar is not None:
        cfg = replace(cfg, winrar_ruta=args.winrar)
    if args.log_dir is not None:
        cfg = replace(cfg, log_dir=args.log_dir)
    if args.dir is not None:
        cfg = replace(cfg, wrkdir=args.dir)
    if args.max_files is not None:
        cfg = replace(cfg, max_files_per_iteration=args.max_files)
    if args.nivel_compresion is not None:
        cfg = replace(cfg, nivel_compresion=args.nivel_compresion)

    # Configurar logging
    log = configurar_logging(cfg)

    # Validaciones tempranas
    if not cfg.winrar_ruta.exists():
        log.error("No se encontró WinRAR en %s", cfg.winrar_ruta)
        return 1

    if not cfg.wrkdir.is_dir():
        log.error("El directorio de trabajo %s no existe o no es accesible", cfg.wrkdir)
        return 1

    # Determinar subcarpetas a procesar (excluir aquellas cuyo nombre empieza con 'tempo')
    carpetas = [
        c
        for c in cfg.wrkdir.iterdir()
        if c.is_dir() and not c.name.startswith("tempo")
    ]

    if not carpetas:
        log.error(
            "No hay subcarpetas para procesar en %s (se excluyen las que empiezan con 'tempo')",
            cfg.wrkdir,
        )
        return 1

    hoy = datetime.date.today().isoformat()
    log.info("_" * 92)
    log.info(
        "COMIENZA PROCESO DE EMPACADO (perfil %s): %s",
        args.limite,
        datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
    )
    log.info("_" * 92)

    # Abrir Total Origen-<fecha>.txt una sola vez para escritura (modo 'w');
    # si la carpeta de datos está protegida, el listado cae a la carpeta de logs
    total_origen = destino_listado(
        cfg.wrkdir / f"Total Origen-{hoy}.txt", cfg, log, "Total Origen"
    )
    origen = open(total_origen, "w", encoding="utf-8") if total_origen else None

    resumen = []
    carpetas_procesadas = []
    try:
        for carpeta in carpetas:
            try:
                cifras, agrupacion, archivos = procesar_carpeta(
                    carpeta,
                    cfg,
                    log,
                    origen,
                    dry_run=args.dry_run,
                )
                resumen.append((carpeta.name, cifras))
                carpetas_procesadas.append((carpeta, agrupacion, archivos))
            except SystemExit as e:
                # Error fatal de la carpeta (límite excedido, WinRAR, etc.)
                log.error("Error procesando carpeta %s: %s", carpeta.name, e)
                return 1
    finally:
        # Escribir output.txt agregando TODAS las carpetas procesadas, una sola
        # vez (queda el listado incluso si el proceso abortó a mitad de camino)
        try:
            escribir_output(carpetas_procesadas, cfg, log)
        except OSError as error:
            log.error("No se pudo escribir output.txt: %s", error)
        if origen is not None:
            origen.close()

    # Reporte final resumido
    for nombre, cifras in resumen:
        log.info(
            "CARPETA %s | archivos leídos: %d | grupos creados: %d | suma de archivos en grupos: %d",
            nombre,
            cifras["total_archivos"],
            cifras["total_grupos"],
            cifras["suma_en_grupos"],
        )

    log.info("_" * 92)
    log.info(
        "TERMINA PROCESO DE EMPACADO (perfil %s): %s",
        args.limite,
        datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
    )
    log.info("_" * 92)
    return 0


def procesar_carpeta(
    carpeta: Path,
    cfg: Config,
    log: logging.Logger,
    origen,
    dry_run: bool = False,
) -> tuple[dict[str, int], Agrupacion, dict[Path, int]]:
    """
    Procesa una única carpeta: elimina archivos auxiliares, valida tamaños,
    agrupa y empaca. No escribe output.txt: ese listado se agrega al final
    de la ejecución con los resultados de todas las carpetas.
    Devuelve las cifras de control, la agrupación y el inventario de archivos.
    """
    log.info("Carpeta %s: iniciando procesamiento", carpeta.name)

    # Eliminar archivos auxiliares (.db, .ini)
    eliminar_auxiliares(carpeta, log, dry_run)

    # Descubrir archivos candidatos
    archivos = descubrir_archivos(carpeta)
    log.info(
        "Carpeta %s: %d archivos descubiertos (excluyendo .zip, ~$ y tamaño 0)",
        carpeta.name,
        len(archivos),
    )

    # Validar que ningún archivo supere el límite individual
    validar_tamanos(archivos, cfg)

    # Escribir Total Origen-<fecha>.txt (orden ascendente por tamaño)
    if origen is not None:
        for archivo in sorted(archivos, key=archivos.get):
            origen.write(f"{archivo}\n")

    # Agrupar y empacar
    agrupacion = agrupar_por_tamano(
        archivos, carpeta, cfg, log, dry_run=dry_run
    )

    # Empaquetado final: eliminar y regenerar todos los ZIP
    log.info(
        "Carpeta %s: compresión final de %d grupos",
        carpeta.name,
        len(agrupacion.grupos),
    )
    empacar_grupos(
        agrupacion.grupos,
        agrupacion.tamanos,
        agrupacion.empaquetados,
        carpeta,
        cfg,
        log,
        final=True,
        dry_run=dry_run,
    )

    # Cifras de control
    cifras = {
        "total_archivos": len(archivos),
        "total_grupos": len(agrupacion.grupos),
        "suma_en_grupos": sum(len(g) for g in agrupacion.grupos),
    }
    log.info(
        "CIFRAS DE CONTROL carpeta %s: %s",
        carpeta.name,
        cifras,
    )
    return cifras, agrupacion, archivos


if __name__ == "__main__":
    sys.exit(main())