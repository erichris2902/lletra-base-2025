import io
import os
import zipfile
import unittest

from core.system_panel.services.expediente_processor import (
    process_expedientes_zip,
    ProcessorError,
    ProcessorConfig,
    _order_pdfs,
)

from pypdf import PdfWriter


def make_pdf_bytes():
    w = PdfWriter()
    w.add_blank_page(width=72, height=72)
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


def make_zip_bytes(structure):
    """
    structure: dict of arcname -> bytes (file contents). Directories can be implied by file paths.
    Returns BytesIO ready at pos 0.
    """
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for arcname, data in structure.items():
            z.writestr(arcname, data)
    bio.seek(0)
    return bio


class UploadLike(io.BytesIO):
    """A BytesIO that mimics Django UploadedFile with name and size."""
    def __init__(self, data: bytes, name: str = 'upload.zip'):
        super().__init__(data)
        self.name = name
        self._size = len(data)

    @property
    def size(self):
        return self._size


class TestOrdering(unittest.TestCase):
    def test_ordering_a_then_alpha_then_evi(self):
        folder = 'X'
        pdfs = [
            os.path.join(folder, 'doc3.pdf'),
            os.path.join(folder, 'A001.pdf'),
            os.path.join(folder, 'EVI_foo.pdf'),
            os.path.join(folder, 'b.pdf'),
        ]
        ordered = _order_pdfs(pdfs)
        self.assertEqual([os.path.join(folder, 'A001.pdf'), os.path.join(folder, 'b.pdf'), os.path.join(folder, 'doc3.pdf'), os.path.join(folder, 'EVI_foo.pdf')], ordered)

    def test_ordering_no_a(self):
        folder = 'Y'
        pdfs = [
            os.path.join(folder, 'doc3.pdf'),
            os.path.join(folder, 'EVIDENCIA.pdf'),
            os.path.join(folder, 'b.pdf'),
        ]
        ordered = _order_pdfs(pdfs)
        self.assertEqual([os.path.join(folder, 'b.pdf'), os.path.join(folder, 'doc3.pdf'), os.path.join(folder, 'EVIDENCIA.pdf')], ordered)

    def test_ordering_no_evi(self):
        folder = 'Z'
        pdfs = [
            os.path.join(folder, 'A123.pdf'),
            os.path.join(folder, 'b.pdf'),
        ]
        ordered = _order_pdfs(pdfs)
        self.assertEqual([os.path.join(folder, 'A123.pdf'), os.path.join(folder, 'b.pdf')], ordered)

    def test_multiple_a_raises(self):
        folder = 'W'
        pdfs = [os.path.join(folder, 'A1.pdf'), os.path.join(folder, 'A2.pdf')]
        with self.assertRaises(ProcessorError):
            _order_pdfs(pdfs)

    def test_multiple_evi_raises(self):
        folder = 'W2'
        pdfs = [os.path.join(folder, 'EVI1.pdf'), os.path.join(folder, 'file_EVI.pdf')]
        with self.assertRaises(ProcessorError):
            _order_pdfs(pdfs)


class TestProcessor(unittest.TestCase):
    def test_valid_zip_single_folder(self):
        pdf = make_pdf_bytes()
        z = make_zip_bytes({
            'EXP_1/A1.pdf': pdf,
            'EXP_1/doc.pdf': pdf,
        })
        out_io, name = process_expedientes_zip(z)
        self.assertEqual(name, 'expedientes_procesados.zip')
        with zipfile.ZipFile(out_io, 'r') as outz:
            names = sorted(outz.namelist())
            self.assertEqual(names, ['EXP_1.pdf'])
            data = outz.read('EXP_1.pdf')
            self.assertGreater(len(data), 0)

    def test_valid_zip_multiple_folders_and_ignore_non_pdfs(self):
        pdf = make_pdf_bytes()
        z = make_zip_bytes({
            'EXP_1/A1.pdf': pdf,
            'EXP_1/readme.txt': b'not a pdf',
            'EXP_2/b.pdf': pdf,
            'EXP_2/EVI.pdf': pdf,
            '__MACOSX/junk': b'x',
        })
        out_io, _ = process_expedientes_zip(z)
        with zipfile.ZipFile(out_io, 'r') as outz:
            names = sorted(outz.namelist())
            self.assertEqual(names, ['EXP_1.pdf', 'EXP_2.pdf'])

    def test_zip_with_root_folder(self):
        pdf = make_pdf_bytes()
        z = make_zip_bytes({
            'carpeta_raiz/EXP_1/A1.pdf': pdf,
            'carpeta_raiz/EXP_2/b.pdf': pdf,
        })
        out_io, _ = process_expedientes_zip(z)
        with zipfile.ZipFile(out_io, 'r') as outz:
            self.assertCountEqual(outz.namelist(), ['EXP_1.pdf', 'EXP_2.pdf'])

    def test_folder_without_pdfs_is_ignored_but_error_if_none_have_pdfs(self):
        pdf = make_pdf_bytes()
        # Some folder without pdf, one with
        z = make_zip_bytes({
            'A/readme.txt': b'x',
            'B/file.pdf': pdf,
        })
        out_io, _ = process_expedientes_zip(z)
        with zipfile.ZipFile(out_io, 'r') as outz:
            self.assertEqual(outz.namelist(), ['B.pdf'])
        # Now none with pdfs
        z2 = make_zip_bytes({'A/readme.txt': b'x'})
        with self.assertRaises(ProcessorError):
            process_expedientes_zip(z2)

    def test_invalid_zip(self):
        bad = UploadLike(b'not a zip', name='exp.zip')
        with self.assertRaises(ProcessorError):
            process_expedientes_zip(bad)

    def test_zip_slip_is_blocked(self):
        pdf = make_pdf_bytes()
        z = make_zip_bytes({
            '../evil.pdf': pdf,
            'EXP/A.pdf': pdf,
        })
        with self.assertRaises(ProcessorError):
            process_expedientes_zip(z)

    def test_duplicate_folder_names(self):
        pdf = make_pdf_bytes()
        z = make_zip_bytes({
            'root/EXP/A.pdf': pdf,
            'other/EXP/b.pdf': pdf,
        })
        with self.assertRaises(ProcessorError):
            process_expedientes_zip(z)

    def test_corrupt_pdf_raises(self):
        z = make_zip_bytes({
            'EXP/A.pdf': b'not a real pdf',
        })
        with self.assertRaises(ProcessorError):
            process_expedientes_zip(z)

    def test_upload_size_limit(self):
        pdf = make_pdf_bytes()
        # Build a zip a few KB
        zbio = make_zip_bytes({'EXP/A.pdf': pdf})
        upl = UploadLike(zbio.getvalue(), name='small.zip')
        # Set absurdly small max to trigger
        with self.assertRaises(ProcessorError):
            process_expedientes_zip(upl, config=ProcessorConfig(max_upload_size_mb=0))

    def test_uncompressed_size_limit(self):
        # Create a zip with many files to exceed small limit
        data = b'x' * 1024  # 1 KB each
        files = {f'EXP/file_{i}.pdf': data for i in range(1100)}  # ~1.1 MB uncompressed
        z = make_zip_bytes(files)
        with self.assertRaises(ProcessorError):
            process_expedientes_zip(z, config=ProcessorConfig(max_uncompressed_size_mb=1))


if __name__ == '__main__':
    unittest.main(verbosity=2)
