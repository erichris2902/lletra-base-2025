import io
import os
import zipfile
import unittest
import tempfile

from core.system_panel.services.pdf_reducer import (
    process_zip_pdf_reduction,
    reduce_pdf,
)
from core.system_panel.services.expediente_processor import ProcessorError

try:
    import fitz  # PyMuPDF
except Exception:  # pragma: no cover - environment without PyMuPDF
    fitz = None


def _make_sample_pdf(path: str, pages: int = 3, text_prefix: str = "Page"):
    if fitz is None:
        raise unittest.SkipTest("PyMuPDF no disponible en el entorno de pruebas")
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"{text_prefix} {i+1}")
    doc.save(path)
    doc.close()


class TestPdfReducer(unittest.TestCase):
    def setUp(self):
        if fitz is None:
            self.skipTest("PyMuPDF no disponible en el entorno de pruebas")

    def test_reduce_single_pdf_keep_first_true(self):
        with tempfile.TemporaryDirectory() as td:
            src = os.path.join(td, 'A.pdf')
            dst = os.path.join(td, 'A_out.pdf')
            _make_sample_pdf(src, pages=4)
            reduce_pdf(src, dst, quality=65, scale=0.8, keep_first=True)
            self.assertTrue(os.path.exists(dst))
            # Quick sanity: page count preserved
            in_doc = fitz.open(src)
            out_doc = fitz.open(dst)
            self.assertEqual(in_doc.page_count, out_doc.page_count)
            in_doc.close(); out_doc.close()

    def test_process_zip_with_multiple_pdfs(self):
        with tempfile.TemporaryDirectory() as td:
            # Create PDFs
            p1 = os.path.join(td, 'EXP_001.pdf')
            p2 = os.path.join(td, 'EXP_002.pdf')
            _make_sample_pdf(p1, pages=2)
            _make_sample_pdf(p2, pages=3)
            # Make zip (inside a root folder to test tolerance)
            root = os.path.join(td, 'root')
            os.makedirs(root, exist_ok=True)
            rp1 = os.path.join(root, 'EXP_001.pdf')
            rp2 = os.path.join(root, 'EXP_002.pdf')
            os.replace(p1, rp1)
            os.replace(p2, rp2)
            inzip_path = os.path.join(td, 'in.zip')
            with zipfile.ZipFile(inzip_path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
                z.write(rp1, arcname='root/EXP_001.pdf')
                z.write(rp2, arcname='root/EXP_002.pdf')
            # Feed as file-like
            with open(inzip_path, 'rb') as f:
                out_fp, out_name = process_zip_pdf_reduction(f, quality=65, scale=0.8, keep_first=True)
            self.assertEqual(out_name, 'expedientes_reducidos.zip')
            # Inspect output zip contents
            data = out_fp.read()
            out_fp.close()
            with zipfile.ZipFile(io.BytesIO(data), 'r') as z:
                names = sorted(z.namelist())
                self.assertEqual(names, ['EXP_001.pdf', 'EXP_002.pdf'])

    def test_invalid_zip_raises(self):
        with self.assertRaises(ProcessorError):
            process_zip_pdf_reduction(io.BytesIO(b'not a zip'), quality=65, scale=0.8, keep_first=False)

    def test_duplicate_names_detected(self):
        with tempfile.TemporaryDirectory() as td:
            p1 = os.path.join(td, 'EXP.pdf')
            p2 = os.path.join(td, 'EXP.pdf')  # same name in another folder later
            _make_sample_pdf(p1, pages=1)
            # create other folder with same name
            other = os.path.join(td, 'sub')
            os.makedirs(other, exist_ok=True)
            p2_path = os.path.join(other, 'EXP.pdf')
            _make_sample_pdf(p2_path, pages=1)
            inzip_path = os.path.join(td, 'in.zip')
            with zipfile.ZipFile(inzip_path, 'w') as z:
                z.write(p1, arcname='a/EXP.pdf')
                z.write(p2_path, arcname='b/EXP.pdf')
            with open(inzip_path, 'rb') as f:
                with self.assertRaises(ProcessorError):
                    process_zip_pdf_reduction(f, quality=65, scale=0.8, keep_first=False)

    def test_zip_slip_blocked(self):
        # Build a malicious zip with traversal
        mem = io.BytesIO()
        with zipfile.ZipFile(mem, 'w') as z:
            z.writestr('../evil.pdf', b'%PDF-1.4\n%...')
        mem.seek(0)
        with self.assertRaises(ProcessorError):
            process_zip_pdf_reduction(mem, quality=65, scale=0.8, keep_first=False)

    def test_stream_pointer_not_at_start_is_handled(self):
        # Ensure that if the uploaded file-like has an advanced pointer, the reducer still works
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, 'A.pdf')
            _make_sample_pdf(p, pages=2)
            inzip_path = os.path.join(td, 'in.zip')
            with zipfile.ZipFile(inzip_path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
                z.write(p, arcname='A.pdf')
            f = open(inzip_path, 'rb')
            try:
                # advance pointer arbitrarily
                _ = f.read(7)
                out_fp, out_name = process_zip_pdf_reduction(f, quality=65, scale=0.8, keep_first=True)
                self.assertEqual(out_name, 'expedientes_reducidos.zip')
                # consume result and assert it is a valid zip with A.pdf inside
                data = out_fp.read()
                out_fp.close()
                with zipfile.ZipFile(io.BytesIO(data), 'r') as z:
                    self.assertIn('A.pdf', z.namelist())
            finally:
                f.close()


if __name__ == '__main__':
    unittest.main()
