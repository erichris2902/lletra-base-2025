from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

admin.autodiscover()

urlpatterns = [
    path('admin/', admin.site.urls),
    path('openai/', include("apps.openai_assistant.urls")),
    path('telegram/', include("apps.telegram_bots.urls")),
    path('google-drive/', include("apps.google_drive.urls")),
    path('commercial/', include("core.commercial_panel.urls")),  # Commercial panel URLs
    path('sales/', include("core.sales_panel.urls")),  # Sales panel URLs
    path('rh/', include("core.rh_panel.urls")),  # RH panel URLs
    path('operations/', include("core.operations_panel.urls")),  # Operations panel URLs
    path('system/', include("core.system_panel.urls")),  # System panel URLs
    path('', include("core.admin_panel.urls")),  # Admin panel URLs at root
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
