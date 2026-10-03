#!/usr/bin/env python3
"""Split large PDF files into smaller parts, each under a size limit.

Recursively scans a target directory, finds PDFs larger than the limit
(default 4 MB) and splits them page by page, accumulating pages into each
part until the size threshold is reached.

Naming: myPDF.pdf -> myPDF_1.pdf, myPDF_2.pdf, ... (same folder as the source).

On full success the original file is deleted; on any failure it is kept.
A PDF containing a single page that alone exceeds the limit is not split
(abort, no parts created, original kept).

Usage:
    python split_4M_PDF_python.py [--dir <ruta>] [--max-mb <mb>]

Requires pypdf (preferred) or PyPDF2. Works on Windows paths and
MSYS/Git-Bash style paths (/c/...).
"""

import argparse
import logging
import re
import sys
import tempfile
import time
from pathlib import Path

try:
    from pypdf import PdfReader, PdfWriter

    PDF_LIB = "pypdf"
except ImportError:
    from PyPDF2 import PdfReader, PdfWriter

    PDF_LIB = "PyPDF2"

BYTES_PER_MB = 1024 * 1024
DEFAULT_DIR = "/c/githubProjects/playwrightProjects/pdfValidator/pdfs"
DEFAULT_MAX_MB = 4
MAX_BISECT_DEPTH = 10


def normalize_path(raw: str) -> Path:
    """Accept Windows paths and MSYS/Git-Bash paths like /c/foo."""
    text = raw.strip()
    match = re.match(r"^/([A-Za-z])/(.*)$", text)
    if match:
        return Path(f"{match.group(1).upper()}:\\{match.group(2).replace('/', chr(92))}")
    return Path(text)


def setup_logging(log_dir: Path) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"split_PDFs_4M_python_{time.strftime('%Y-%m-%d_%H-%M-%S')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )
    return log_file


def open_reader(pdf_path: Path):
    """Open a PdfReader, trying an empty owner password for encrypted files.

    Returns (reader, None) on success or (None, reason) on failure.
    """
    try:
        reader = PdfReader(str(pdf_path))
    except Exception as exc:
        return None, (
            f"no se pudo abrir el PDF ({type(exc).__name__}: {exc}); "
            "el archivo esta corrupto o no es un PDF valido"
        )
    if reader.is_encrypted:
        try:
            result = reader.decrypt("")
        except Exception as exc:
            return None, (
                "el PDF esta protegido con contrasena y fallo el intento de "
                f"descifrado con contrasena vacia ({type(exc).__name__}: {exc})"
            )
        name = getattr(result, "name", str(result))
        if name == "NOT_DECRYPTED" or int(result) == 0:
            return None, (
                "el PDF esta protegido con contrasena y no acepta la "
                "contrasena vacia; hace falta la contrasena para dividirlo"
            )
    return reader, None


def write_pages(reader, page_indices, out_path: Path) -> int:
    """Write the given pages (by index) into out_path; return its size in bytes."""
    writer = PdfWriter()
    for index in page_indices:
        writer.add_page(reader.pages[index])
    with open(out_path, "wb") as handle:
        writer.write(handle)
    return out_path.stat().st_size


def bisect_group(reader, page_indices, tmp_dir: Path, limit_bytes: int, log, depth=0):
    """Split a page-index group in halves until each half fits the limit.

    Returns the list of page-index groups, or None when a part cannot be
    divided further and still exceeds the limit (the caller must abort).
    """
    if depth >= MAX_BISECT_DEPTH or len(page_indices) == 1:
        log.error(
            "        FALLO: la pagina %d sola mide mas que el limite; no se puede dividir mas",
            page_indices[0] + 1,
        )
        return None
    mid = len(page_indices) // 2
    result = []
    for part in (page_indices[:mid], page_indices[mid:]):
        probe = tmp_dir / "bisect_probe.pdf"
        size = write_pages(reader, part, probe)
        if size > limit_bytes:
            log.warning(
                "        La mitad (paginas %d-%d) midio %.2f MB (> limite); subdividiendo de nuevo",
                part[0] + 1,
                part[-1] + 1,
                size / BYTES_PER_MB,
            )
            sub = bisect_group(reader, part, tmp_dir, limit_bytes, log, depth + 1)
            if sub is None:
                return None
            result.extend(sub)
        else:
            result.append(part)
    return result


def process_pdf(pdf_path: Path, limit_bytes: int, tmp_dir: Path, log):
    """Split one PDF into parts under the limit.

    Returns the list of created part paths on success, or None on failure
    (on failure the original file must be preserved).
    """
    reader, reason = open_reader(pdf_path)
    if reader is None:
        log.error("FALLO '%s': %s", pdf_path.name, reason)
        return None

    try:
        total = len(reader.pages)
    except Exception as exc:
        log.error(
            "FALLO '%s': no se pudo determinar el numero de paginas (%s: %s)",
            pdf_path.name,
            type(exc).__name__,
            exc,
        )
        return None

    base = pdf_path.stem
    out_dir = pdf_path.parent
    log.info(
        "Procesando '%s' (%d paginas, limite %.2f MB, libreria %s)",
        pdf_path.name,
        total,
        limit_bytes / BYTES_PER_MB,
        PDF_LIB,
    )

    # Medir el tamano aproximado de cada pagina por separado (una escritura por pagina)
    page_sizes = []
    for index in range(total):
        probe = tmp_dir / "page_probe.pdf"
        try:
            page_sizes.append(write_pages(reader, [index], probe))
        except Exception as exc:
            log.error(
                "FALLO '%s': no se pudo extraer la pagina %d (%s: %s); "
                "la pagina esta danada o usa objetos no soportados",
                pdf_path.name,
                index + 1,
                type(exc).__name__,
                exc,
            )
            return None

    # Acumular paginas hasta alcanzar el limite (con un margen de seguridad del 2%)
    margin = int(limit_bytes * 0.02) + 1024
    groups = []
    current, current_size = [], 0
    for index, size in enumerate(page_sizes):
        if current and current_size + size + margin > limit_bytes:
            groups.append(current)
            current, current_size = [index], size
        else:
            current.append(index)
            current_size += size
    if current:
        groups.append(current)

    # Verificar cada grupo en un temporal; subdividir los que excedan el limite real
    leaf_groups = []
    for number, group in enumerate(groups, start=1):
        probe = tmp_dir / f"group_probe_{number}.pdf"
        try:
            size = write_pages(reader, group, probe)
        except Exception as exc:
            log.error(
                "FALLO '%s': no se pudo escribir el grupo %d (paginas %d-%d): %s: %s",
                pdf_path.name,
                number,
                group[0] + 1,
                group[-1] + 1,
                type(exc).__name__,
                exc,
            )
            return None
        if size > limit_bytes and len(group) > 1:
            log.warning(
                "    El grupo %d (paginas %d-%d) midio %.2f MB (> limite); subdividiendo",
                number,
                group[0] + 1,
                group[-1] + 1,
                size / BYTES_PER_MB,
            )
            sub = bisect_group(reader, group, tmp_dir, limit_bytes, log)
            if sub is None:
                return None
            leaf_groups.extend(sub)
        elif size > limit_bytes:
            log.error(
                "FALLO '%s': la pagina %d mide %.2f MB y excede el limite por si sola; "
                "no se puede dividir mas, abortando sin crear partes",
                pdf_path.name,
                group[0] + 1,
                size / BYTES_PER_MB,
            )
            return None
        else:
            leaf_groups.append(group)

    # Escribir las partes finales con numeracion secuencial
    created = []
    for number, group in enumerate(leaf_groups, start=1):
        out_path = out_dir / f"{base}_{number}.pdf"
        try:
            size = write_pages(reader, group, out_path)
        except Exception as exc:
            if out_path.exists():
                try:
                    out_path.unlink()
                except OSError:
                    pass
            log.error(
                "FALLO '%s': no se pudo crear la parte %d (paginas %d-%d): %s: %s",
                pdf_path.name,
                number,
                group[0] + 1,
                group[-1] + 1,
                type(exc).__name__,
                exc,
            )
            # Division incompleta: eliminar las partes ya creadas para no dejar duplicados
            for part in created:
                try:
                    part.unlink()
                except OSError:
                    pass
            return None
        log.info(
            "    CREADA: %s (paginas %d-%d, %.2f MB)",
            out_path.name,
            group[0] + 1,
            group[-1] + 1,
            size / BYTES_PER_MB,
        )
        created.append(out_path)
    return created


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Divide PDFs mayores a un limite de tamano en partes menores."
    )
    parser.add_argument(
        "--dir",
        default=DEFAULT_DIR,
        help="Directorio objetivo (por defecto: %(default)s)",
    )
    parser.add_argument(
        "--max-mb",
        type=float,
        default=DEFAULT_MAX_MB,
        help="Limite en MB por parte (por defecto: %(default)s)",
    )
    args = parser.parse_args()

    target = normalize_path(args.dir)
    if not target.is_dir():
        print(f"ERROR: el directorio objetivo no existe: {target}", file=sys.stderr)
        return 1

    limit_bytes = int(args.max_mb * BYTES_PER_MB)
    log_dir = Path(__file__).resolve().parent.parent / "shellScriptResults"
    log_file = setup_logging(log_dir)
    log = logging.getLogger("split_pdfs")
    log.info("Directorio objetivo: %s", target)
    log.info("Limite por parte: %.2f MB (%d bytes)", limit_bytes / BYTES_PER_MB, limit_bytes)
    log.info("Registro guardado en: %s", log_file)

    try:
        candidates = [
            path
            for path in target.rglob("*")
            if path.is_file() and path.suffix.lower() == ".pdf"
        ]
    except OSError as exc:
        log.error("FALLO: no se pudo listar el directorio objetivo (%s: %s)", type(exc).__name__, exc)
        return 1

    big = []
    for path in candidates:
        try:
            if path.stat().st_size > limit_bytes:
                big.append(path)
        except OSError as exc:
            log.error("FALLO '%s': no se pudo leer el tamano del archivo (%s: %s)", path, type(exc).__name__, exc)
    big.sort(key=lambda p: str(p).lower())

    log.info("PDFs encontrados en el directorio: %d; mayores al limite: %d", len(candidates), len(big))
    if not big:
        log.info("No hay PDFs mayores al limite. Nada que hacer.")
        return 0

    failures = 0
    deleted = 0
    with tempfile.TemporaryDirectory(prefix="split_pdf_") as tmp:
        tmp_dir = Path(tmp)
        for pdf_path in big:
            try:
                parts = process_pdf(pdf_path, limit_bytes, tmp_dir, log)
            except Exception as exc:
                log.error(
                    "FALLO inesperado en '%s': %s: %s; se conserva el original",
                    pdf_path.name,
                    type(exc).__name__,
                    exc,
                )
                failures += 1
                continue
            if parts is None:
                log.info(
                    "CONSERVADO: '%s' (la division fallo; el original no se elimina)",
                    pdf_path.name,
                )
                failures += 1
                continue
            if not parts:
                log.error(
                    "FALLO '%s': la division no genero ninguna parte; se conserva el original",
                    pdf_path.name,
                )
                failures += 1
                continue
            try:
                valid = all(part.exists() and part.stat().st_size > 0 for part in parts)
                if not valid:
                    raise OSError("una de las partes generadas falta o esta vacia")
                pdf_path.unlink()
            except OSError as exc:
                log.error(
                    "FALLO '%s': no se pudo eliminar el original de forma segura (%s); se conserva",
                    pdf_path.name,
                    exc,
                )
                failures += 1
                continue
            deleted += 1
            log.info(
                "ELIMINADO: '%s' (reemplazado por %d parte(s))",
                pdf_path.name,
                len(parts),
            )

    log.info("Resumen: %d PDF(s) procesados, %d eliminados, %d con fallo", len(big), deleted, failures)
    log.info("Proceso finalizado.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
