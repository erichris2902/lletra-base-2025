from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse, HttpResponseBadRequest
from django.utils.html import escape

from core.operations_panel.views.route import RouteAsturianoListView

admin.autodiscover()


def qr_landing(request):
    """
    Interstitial QR landing page.
    Usage: /qr/?to=https://destino.final/&s=3&title=Titulo&msg=Mensaje
    - to: URL final a donde redirigir (http/https obligatorio)
    - s: segundos de espera antes de redirigir (0-15, por defecto 3)
    - title/msg: textos opcionales para personalizar la página
    """
    to = 'https://www.facebook.com/LLETRAMX'
    if not to:
        return HttpResponseBadRequest("Falta el parámetro 'to'.")
    if not (to.startswith('http://') or to.startswith('https://')):
        return HttpResponseBadRequest("El parámetro 'to' debe iniciar con http:// o https://")

    try:
        seconds = int(request.GET.get('s', 3))
    except (TypeError, ValueError):
        seconds = 3
    # Limitar a 0-15 segundos para evitar abusos
    seconds = max(0, min(seconds, 15))

    title = request.GET.get('title', 'Te estamos redirigiendo…')
    msg = request.GET.get('msg', f'Serás redirigido automáticamente en {seconds} segundos.')

    # Escapar textos para evitar inyecciones
    safe_title = escape(title)
    safe_msg = escape(msg)
    safe_to = escape(to)

    html = f"""
<!DOCTYPE html>
<html lang=\"es\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>{safe_title}</title>
  <meta http-equiv=\"refresh\" content=\"{seconds};url={safe_to}\">
  <style>
    body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 0; background: #0b1220; color: #f3f4f6; }}
    .wrap {{ max-width: 720px; margin: 0 auto; padding: 24px; }}
    .card {{ background: #111827; border: 1px solid #1f2937; border-radius: 12px; padding: 24px; box-shadow: 0 10px 25px rgba(0,0,0,.35); }}
    .ad {{ background: linear-gradient(135deg,#0ea5e9,#6366f1); border-radius: 10px; padding: 18px; margin-top: 12px; color: white; text-align: center; }}
    .btn {{ display: inline-block; padding: 10px 16px; background: #22c55e; color: #06240f; border-radius: 8px; text-decoration: none; font-weight: 700; }}
    .btn:hover {{ filter: brightness(1.05); }}
    .muted {{ color: #9ca3af; }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <div class=\"card\">
      <h1 style=\"margin-top:0\">{safe_title}</h1>
      <p class=\"muted\">{safe_msg} <span id=\"count\">{seconds}</span>s</p>
      <div class=\"ad\">
        <strong>Publicidad</strong>
        <div style=\"margin-top:8px\">Aquí puedes colocar tu anuncio, imagen o mensaje promocional.</div>
      </div>
      <p style=\"margin-top:16px\"><a class=\"btn\" href=\"{safe_to}\">Continuar ahora</a></p>
      <p class=\"muted\">Destino: <span style=\"word-break:break-all\">{safe_to}</span></p>
    </div>
  </div>
  <script>
    (function() {{
      var to = {safe_to!r};
      var remaining = {seconds};
      var el = document.getElementById('count');
      function tick() {{
        if (remaining <= 0) return;
        remaining -= 1;
        if (el) el.textContent = remaining;
        if (remaining <= 0) window.location.href = to;
      }}
      setInterval(tick, 1000);
    }})();
  </script>
</body>
</html>
"""
    return HttpResponse(html, content_type='text/html; charset=utf-8')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('openai/', include("apps.openai_assistant.urls")),
    path('telegram/', include("apps.telegram_bots.urls")),
    path('google-drive/', include("apps.google_drive.urls")),
    path('commercial/', include("core.commercial_panel.urls")),  # Commercial panel URLs
    path('sales/', include("core.sales_panel.urls")),  # Sales panel URLs
    path('rh/', include("core.rh_panel.urls")),  # RH panel URLs
    path('operations/', include("core.operations_panel.urls")),  # Operations panel URLs
    path('system/operations-master/', include("core.operation_control.urls")),  # Operations master control module
    path('system/', include("core.system_panel.urls")),  # System panel URLs
    path('supplier/', include("core.supplier_panel.urls")),  # System panel URLs
    path('', include("core.admin_panel.urls")),  # Admin panel URLs at root
    path('asturiano/', RouteAsturianoListView.as_view(), name='routes_asturiano'),
    path('qr/', qr_landing, name='qr'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
