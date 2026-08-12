import io
import unittest

try:
    from django.test.client import RequestFactory
    from django.http import Http404
    from django.conf import settings
    settings.configure()  # Best-effort minimal config for imports if not already configured
    django_available = True
except Exception:
    RequestFactory = None  # type: ignore
    Http404 = Exception  # type: ignore
    django_available = False


class FakeFile:
    def __init__(self, data: bytes, name: str = "cotizacion-1.docx"):
        self._buf = io.BytesIO(data)
        self.name = name

    def open(self, mode="rb"):
        self._buf.seek(0)
        return self

    # Minimal file-like API used by FileResponse
    def read(self, size=-1):
        return self._buf.read(size)

    def close(self):
        try:
            self._buf.close()
        except Exception:
            pass


@unittest.skipUnless(django_available, "Django not available/configured; skipping Quotation DOCX view tests")
class TestQuotationDocxView(unittest.TestCase):
    def setUp(self):
        from core.sales_panel.views import QuotationDocxDownloadView
        self.view = QuotationDocxDownloadView.as_view()
        self.factory = RequestFactory()

    def _make_request(self, is_superuser=False):
        req = self.factory.get("/sales/quote/1/document/")
        class U:
            def __init__(self, is_superuser):
                self.is_superuser = is_superuser
                self.user = object()  # placeholder for SystemUser
        req.user = U(is_superuser)
        return req

    def test_download_success_calls_generate_and_returns_docx(self):
        # Arrange
        from core.sales_panel import views as sales_views
        fake_doc = FakeFile(b"FAKE-DOCX-CONTENT")
        class Q:
            id = 1
            docx = fake_doc
            def generateDocx(self):
                return "/media/quotes/cotizacion-1.docx"
        # Patch get_object_or_404
        orig_get = sales_views.get_object_or_404
        sales_views.get_object_or_404 = lambda model, pk=None, user=None: Q()
        try:
            # Act
            req = self._make_request(is_superuser=True)
            response = self.view(req, pk=1)
            # Assert
            self.assertEqual(response.status_code, 200)
            self.assertIn("application/vnd.openxmlformats-officedocument.wordprocessingml.document", response["Content-Type"])  # type: ignore
            cd = response["Content-Disposition"]  # type: ignore
            self.assertIn("attachment;", cd)
            self.assertIn("cotizacion-1.docx", cd)
        finally:
            sales_views.get_object_or_404 = orig_get

    def test_not_found_raises_404(self):
        from core.sales_panel import views as sales_views
        def _raise(*args, **kwargs):
            from django.http import Http404
            raise Http404("Not found")
        orig_get = sales_views.get_object_or_404
        sales_views.get_object_or_404 = _raise
        try:
            req = self._make_request(is_superuser=True)
            with self.assertRaises(Http404):
                _ = self.view(req, pk=999)
        finally:
            sales_views.get_object_or_404 = orig_get

    def test_generation_error_returns_400(self):
        from core.sales_panel import views as sales_views
        class Q:
            id = 2
            docx = FakeFile(b"")
            def generateDocx(self):
                raise RuntimeError("boom")
        orig_get = sales_views.get_object_or_404
        sales_views.get_object_or_404 = lambda *a, **kw: Q()
        try:
            req = self._make_request(is_superuser=True)
            resp = self.view(req, pk=2)
            self.assertEqual(resp.status_code, 400)
        finally:
            sales_views.get_object_or_404 = orig_get


if __name__ == "__main__":
    unittest.main(verbosity=2)
