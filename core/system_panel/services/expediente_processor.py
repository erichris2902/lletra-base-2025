import io
import os
import zipfile
import logging
from dataclasses import dataclass
from typing import List, Tuple, Dict, Iterable
from tempfile import TemporaryDirectory

from pypdf import PdfReader, PdfWriter

logger = logging.getLogger(__name__)


@dataclass
class ProcessorConfig:
    max_upload_size_mb: int = 200  # hard limit for uploaded zip (form should also enforce)
    max_uncompressed_size_mb: int = 500  # basic protection against zip bombs
    ignore_dirs: Tuple[str, ...] = ("__MACOSX",)


class ProcessorError(Exception):
    pass


def _is_pdf(filename: str) -> bool:
    return filename.lower().endswith(".pdf")


def _safe_extractall(zf: zipfile.ZipFile, dest_dir: str, *, config: ProcessorConfig) -> int:
    """Safely extract zip into dest_dir and return total uncompressed size in bytes.

    - Protects against Zip Slip by validating final path under dest_dir.
    - Enforces a basic total uncompressed size limit.
    - Skips directory members implicitly by zipfile extraction.
    """
    total_uncompressed = 0

    for member in zf.infolist():
        # Normalize member filename
        name = member.filename
        # Skip absolute or drive-rooted paths
        if os.path.isabs(name):
            logger.warning("Skipping absolute path inside ZIP: %s", name)
            continue
        # Normalize traversal sequences
        normalized = os.path.normpath(name).lstrip("/\\")
        # Skip ignored dirs early
        parts = normalized.split(os.sep)
        if any(part in config.ignore_dirs for part in parts if part):
            continue
        # Compute destination path
        dest_path = os.path.normpath(os.path.join(dest_dir, normalized))
        if not dest_path.startswith(os.path.abspath(dest_dir) + os.sep) and os.path.abspath(dest_path) != os.path.abspath(dest_dir):
            # Outside of dest_dir
            logger.error("Blocked path traversal attempt: %s -> %s", name, dest_path)
            raise ProcessorError("El archivo ZIP contiene rutas inválidas (posible Zip Slip).")

        # Track total uncompressed size
        total_uncompressed += member.file_size or 0
        if total_uncompressed > config.max_uncompressed_size_mb * 1024 * 1024:
            raise ProcessorError(
                f"El contenido descomprimido excede el límite permitido de {config.max_uncompressed_size_mb} MB."
            )

        # Extract
        if name.endswith("/"):
            # directory entry
            os.makedirs(dest_path, exist_ok=True)
            continue
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with zf.open(member, 'r') as source, open(dest_path, 'wb') as target:
            # Stream copy to avoid excess memory
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                target.write(chunk)

    return total_uncompressed


def _iter_folders_with_pdfs(root: str, *, config: ProcessorConfig) -> Iterable[Tuple[str, List[str]]]:
    """Yield tuples (folder_abs_path, list_of_pdf_file_abs_paths) for folders that contain PDFs directly.
    Ignores non-PDF files and ignored directories. Does not descend into subfolders when collecting PDFs.
    """
    for current_dir, dirs, files in os.walk(root):
        # Filter ignored dirs in-place to avoid descending
        dirs[:] = [d for d in dirs if d not in config.ignore_dirs and not d.startswith('.')]
        # Collect PDFs directly under current_dir
        pdfs = [os.path.join(current_dir, f) for f in files if _is_pdf(f)]
        if pdfs:
            yield current_dir, sorted(pdfs)  # initial alpha sorting for deterministic behavior


def _order_pdfs(pdfs: List[str]) -> List[str]:
    """Order PDFs respecting: A*.pdf first, then others alphabetically, ending with *EVI*.pdf.
    Case-insensitive checks for 'A' prefix and 'EVI' containment. If multiple A* or multiple *EVI* exist, raise error.
    """
    pdf_a = None
    pdf_evi = None
    others: List[str] = []

    for pdf in pdfs:
        name = os.path.basename(pdf).upper()
        if name.startswith('A'):
            if pdf_a is not None:
                raise ProcessorError("Se encontró más de un PDF que inicia con 'A' en una carpeta.")
            pdf_a = pdf
        elif 'EVI' in name:
            if pdf_evi is not None:
                raise ProcessorError("Se encontró más de un PDF que contiene 'EVI' en una carpeta.")
            pdf_evi = pdf
        else:
            others.append(pdf)

    ordered: List[str] = []
    if pdf_a:
        ordered.append(pdf_a)
    ordered.extend(sorted(others, key=lambda p: os.path.basename(p).lower()))
    if pdf_evi:
        ordered.append(pdf_evi)
    return ordered


def _merge_pdfs(pdf_paths: List[str]) -> bytes:
    writer = PdfWriter()
    for path in pdf_paths:
        try:
            with open(path, 'rb') as f:
                reader = PdfReader(f)
                # Handle encrypted PDFs by attempting to decrypt with empty password
                if reader.is_encrypted:
                    try:
                        reader.decrypt("")
                    except Exception:
                        raise ProcessorError(f"El PDF '{os.path.basename(path)}' está encriptado o no se puede leer.")
                for page in reader.pages:
                    writer.add_page(page)
        except ProcessorError:
            raise
        except Exception as exc:
            logger.exception("Error leyendo PDF: %s", path)
            raise ProcessorError(f"No se pudo leer el PDF '{os.path.basename(path)}': {exc}")

    output = io.BytesIO()
    try:
        writer.write(output)
    except Exception as exc:
        logger.exception("Error uniendo PDFs: %s", pdf_paths)
        raise ProcessorError(f"Ocurrió un error al unir los PDFs: {exc}")
    return output.getvalue()


def process_expedientes_zip(
    upload_file,
    *,
    config: ProcessorConfig | None = None,
) -> Tuple[io.BytesIO, str]:
    """Process an uploaded ZIP file-like object and return a BytesIO of the resulting ZIP and a filename.

    Steps:
      - Validate ZIP
      - Securely extract to temp dir
      - Discover folders that contain PDFs
      - For each folder, order and merge PDFs and write to an output ZIP with the folder name as filename
      - Return output ZIP as BytesIO positioned at start
    """
    config = config or ProcessorConfig()

    # Enforce upload size if possible (UploadedFile has size attr)
    size = getattr(upload_file, 'size', None)
    if size is not None and size > config.max_upload_size_mb * 1024 * 1024:
        raise ProcessorError(
            f"El archivo subido excede el tamaño máximo permitido de {config.max_upload_size_mb} MB."
        )

    # Read minimally to validate without loading fully in memory
    # We can pass file-like directly to zipfile if it supports seek
    fileobj = upload_file
    # Some storages provide InMemoryUploadedFile or TempFile. Ensure we can seek.
    try:
        pos = fileobj.tell()
    except Exception:
        pos = None
    try:
        if pos is not None:
            fileobj.seek(0)
        is_zip = zipfile.is_zipfile(fileobj)
    finally:
        try:
            if pos is not None:
                fileobj.seek(pos)
        except Exception:
            pass

    if not is_zip:
        raise ProcessorError("El archivo proporcionado no es un ZIP válido.")

    # Processing
    with TemporaryDirectory() as tmpdir:
        # Extract safely
        try:
            with zipfile.ZipFile(upload_file, 'r') as zf:
                _safe_extractall(zf, tmpdir, config=config)
        except ProcessorError:
            raise
        except Exception as exc:
            logger.exception("Error al leer o extraer el ZIP")
            raise ProcessorError(f"No fue posible leer o extraer el ZIP: {exc}")

        # Discover folders with PDFs
        folders_with_pdfs = list(_iter_folders_with_pdfs(tmpdir, config=config))
        if not folders_with_pdfs:
            raise ProcessorError("No se encontraron carpetas que contengan PDFs dentro del ZIP.")

        # Detect duplicate folder basenames
        name_counts: Dict[str, int] = {}
        for folder, _ in folders_with_pdfs:
            base = os.path.basename(folder)
            name_counts[base] = name_counts.get(base, 0) + 1
        duplicates = [n for n, c in name_counts.items() if c > 1]
        if duplicates:
            dup_list = ", ".join(sorted(duplicates))
            raise ProcessorError(
                f"Se detectaron múltiples carpetas con el mismo nombre: {dup_list}. No es posible generar PDFs sin conflicto."
            )

        # Prepare output zip in memory (streamed writes)
        output_io = io.BytesIO()
        with zipfile.ZipFile(output_io, mode='w', compression=zipfile.ZIP_DEFLATED) as outzip:
            for folder, pdfs in folders_with_pdfs:
                try:
                    ordered = _order_pdfs(pdfs)
                except ProcessorError as e:
                    folder_name = os.path.basename(folder)
                    raise ProcessorError(f"Error en carpeta '{folder_name}': {e}") from e

                if not ordered:
                    # Should not happen because we filtered on folders with PDFs already
                    continue

                merged_bytes = _merge_pdfs(ordered)
                folder_name = os.path.basename(folder)
                arcname = f"{folder_name}.pdf"
                outzip.writestr(arcname, merged_bytes)

        output_io.seek(0)
        return output_io, "expedientes_procesados.zip"
