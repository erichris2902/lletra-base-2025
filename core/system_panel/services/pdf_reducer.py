import io
import os
import zipfile
import logging
from dataclasses import dataclass
from typing import Iterable, List, Tuple
from tempfile import TemporaryDirectory, SpooledTemporaryFile

import pymupdf  # PyMuPDF
from PIL import Image

from .expediente_processor import ProcessorConfig as BaseProcessorConfig, ProcessorError, _safe_extractall

logger = logging.getLogger(__name__)


@dataclass
class PdfReduceConfig(BaseProcessorConfig):
    # Inherit limits from the existing processor config
    max_files: int = 2000  # hard cap to avoid absurd amount of files


def _is_pdf(path: str) -> bool:
    return path.lower().endswith('.pdf')


def _iter_pdfs_one_or_two_levels(root: str, *, config: PdfReduceConfig) -> List[str]:
    """
    Find PDFs either directly under root or under exactly one common subfolder.
    Ignore __MACOSX, hidden files and non-PDFs. Returns absolute paths.
    """
    pdfs: List[str] = []
    for current_dir, dirs, files in os.walk(root):
        # Prune ignored/hidden dirs to reduce traversal
        dirs[:] = [d for d in dirs if d not in config.ignore_dirs and not d.startswith('.')]
        for f in files:
            if f in ('.DS_Store',):
                continue
            if _is_pdf(f):
                pdfs.append(os.path.join(current_dir, f))
    # Sort deterministically by base name (case-insensitive) then by path to stabilize
    pdfs.sort(key=lambda p: (os.path.basename(p).lower(), p))
    if len(pdfs) > config.max_files:
        raise ProcessorError("El ZIP contiene demasiados archivos a procesar.")
    return pdfs


def _pil_image_from_pixmap(pix: pymupdf.Pixmap) -> Image.Image:
    """Create a PIL Image from a PyMuPDF Pixmap, handling alpha and colorspaces safely."""
    # If pix has alpha, remove to fit JPEG (no alpha channel)
    if pix.alpha:  # type: ignore[attr-defined]
        pix = pymupdf.Pixmap(pix, 0)  # remove alpha by creating a new pixmap without alpha
    # Determine mode
    mode = None
    try:
        if pix.n >= 4:  # CMYK or RGB with alpha already handled
            mode = "RGB"
        elif pix.n == 1:
            mode = "L"  # grayscale
        else:
            mode = "RGB"
    except Exception:
        mode = "RGB"
    img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img


def reduce_pdf(input_path: str, output_path: str, *, quality: int, scale: float, keep_first: bool) -> None:
    """
    Reduce a single PDF:
    - Optionally keep the first page intact (copied as vector content).
    - Other pages are rasterized using PyMuPDF to a JPEG at the given quality and inserted back into a new PDF.
    """
    if not os.path.exists(input_path):
        raise ProcessorError(f"No se encontró el PDF: {os.path.basename(input_path)}")

    try:
        src = pymupdf.open(input_path)
    except Exception as e:
        logger.exception("No se pudo abrir el PDF: %s", input_path)
        raise ProcessorError(f"No se pudo abrir el PDF: {os.path.basename(input_path)}") from e

    try:
        dst = pymupdf.open()
        page_count = src.page_count
        for i in range(page_count):
            # Keep first page intact if requested
            if keep_first and i == 0:
                temp = pymupdf.open()
                try:
                    temp.insert_pdf(src, from_page=0, to_page=0)
                    dst.insert_pdf(temp)
                finally:
                    temp.close()
                continue

            page = src.load_page(i)
            # Render page to pixmap with the chosen scale
            try:
                matrix = pymupdf.Matrix(scale, scale)
                pix = page.get_pixmap(matrix=matrix, alpha=False)
            except Exception as e:
                logger.exception("Error al rasterizar la página %s de %s", i + 1, input_path)
                raise ProcessorError(
                    f"Error al rasterizar la página {i + 1} de {os.path.basename(input_path)}"
                ) from e

            # Convert to JPEG in memory
            try:
                pil_img = _pil_image_from_pixmap(pix)
                buf = io.BytesIO()
                pil_img.save(buf, format="JPEG", quality=quality, optimize=True)
                img_bytes = buf.getvalue()
                buf.close()
            except Exception as e:
                logger.exception("Error al convertir la página %s a JPEG (%s)", i + 1, input_path)
                raise ProcessorError(
                    f"Error al convertir la página {i + 1} de {os.path.basename(input_path)} a imagen"
                ) from e

            # Create a single-page PDF from the JPEG and insert
            try:
                img_pdf = pymupdf.open("jpeg", img_bytes).convert_to_pdf()
                img_doc = pymupdf.open("pdf", img_pdf)
                try:
                    dst.insert_pdf(img_doc)
                finally:
                    img_doc.close()
            except Exception as e:
                logger.exception("Error al reinsertar la página como PDF (%s)", input_path)
                raise ProcessorError(
                    f"Error al insertar la página convertida en {os.path.basename(input_path)}"
                ) from e

        # Save optimized
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        dst.save(output_path, garbage=4, deflate=True)
    finally:
        try:
            dst.close()
        except Exception:
            pass
        try:
            src.close()
        except Exception:
            pass


def process_zip_pdf_reduction(upload_file, *, quality: int, scale: float, keep_first: bool,
                              config: PdfReduceConfig | None = None) -> Tuple[io.BufferedIOBase, str]:
    """
    Process an uploaded ZIP containing PDFs. Returns (file_like, output_name) where file_like is positioned at 0.
    - Validates zip, extracts safely, finds PDFs at any depth but flattens to top-level in output zip.
    - Keeps same filenames; aborts if duplicates across subfolders.
    """
    config = config or PdfReduceConfig()

    with TemporaryDirectory() as tmpdir:
        in_zip_path = os.path.join(tmpdir, 'input.zip')

        # Ensure we start reading the uploaded stream from the beginning
        try:
            upload_file.seek(0)
        except Exception:
            pass

        # Copy to disk in chunks and enforce upload size defensively
        max_upload_bytes = config.max_upload_size_mb * 1024 * 1024
        total_copied = 0
        with open(in_zip_path, 'wb') as f:
            while True:
                chunk = upload_file.read(1024 * 1024)
                if not chunk:
                    break
                total_copied += len(chunk)
                if max_upload_bytes and total_copied > max_upload_bytes:
                    raise ProcessorError(
                        f"El archivo subido excede el tamaño máximo permitido de {config.max_upload_size_mb} MB."
                    )
                f.write(chunk)
        # Best effort: reset original stream pointer for caller reuse
        try:
            upload_file.seek(0)
        except Exception:
            pass

        # Validate the saved file as a ZIP now (avoids file-pointer issues)
        try:
            if not zipfile.is_zipfile(in_zip_path):
                raise ProcessorError("El archivo subido no es un ZIP válido.")
        except zipfile.BadZipFile:
            raise ProcessorError("El archivo subido está corrupto o no es un ZIP válido.")

        # Extract safely with our hardened extractor
        try:
            with zipfile.ZipFile(in_zip_path, 'r') as zf:
                _safe_extractall(zf, tmpdir, config=config)
        except zipfile.BadZipFile:
            raise ProcessorError("El archivo ZIP está corrupto y no se puede leer.")
        except ProcessorError:
            raise
        except Exception as exc:
            logger.exception("Error al leer o extraer el ZIP")
            raise ProcessorError(f"No fue posible leer o extraer el ZIP: {exc}")

        extracted_root = tmpdir
        # Collect PDFs (possibly inside a single root folder); we'll just walk all and flatten
        pdf_paths = _iter_pdfs_one_or_two_levels(extracted_root, config=config)
        if not pdf_paths:
            raise ProcessorError("El ZIP no contiene archivos PDF para procesar.")

        # Detect duplicates by basename
        basenames = {}
        for p in pdf_paths:
            b = os.path.basename(p)
            if b in basenames:
                raise ProcessorError(
                    f"Se encontraron archivos PDF con el mismo nombre en distintas carpetas: {b}"
                )
            basenames[b] = p

        out_dir = os.path.join(tmpdir, 'out')
        os.makedirs(out_dir, exist_ok=True)

        # Choose safe, bounded parameters
        quality = int(quality)
        quality = max(30, min(95, quality))
        scale = float(scale)
        scale = max(0.5, min(1.5, scale))

        # Reduce each PDF
        for p in pdf_paths:
            out_path = os.path.join(out_dir, os.path.basename(p))
            reduce_pdf(p, out_path, quality=quality, scale=scale, keep_first=keep_first)

        # Build output zip in memory (spooled to disk if large)
        spooled = SpooledTemporaryFile(max_size=10 * 1024 * 1024)  # 10MB in-memory then disk
        with zipfile.ZipFile(spooled, 'w', compression=zipfile.ZIP_DEFLATED) as outzip:
            for name in sorted(os.listdir(out_dir), key=str.lower):
                full = os.path.join(out_dir, name)
                if os.path.isfile(full) and _is_pdf(full):
                    outzip.write(full, arcname=name)
        spooled.seek(0)
        return spooled, 'expedientes_reducidos.zip'
