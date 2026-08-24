import html

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse, HttpResponseBadRequest
from django.utils.html import escape

from core.operations_panel.views.route import RouteAsturianoListView

admin.autodiscover()


def qr_landing(request):
    # Parámetro opcional:
    # /redirect/?to=https://google.com
    to = request.GET.get("to", "").strip()

    # Escapamos por seguridad para insertarlo en HTML
    safe_to = html.escape(to, quote=True)

    # URL del minivideo
    # Puedes cambiarla por un archivo dentro de static.
    video_url = "/static/video_lletra_qr.mp4"

    # Redes sociales
    facebook_url = "https://www.facebook.com/lletra"
    instagram_url = "https://www.instagram.com/lletralogistica.mx/"
    linkedin_url = "https://www.linkedin.com/company/lletra-mx/?originalSubdomain=mx"
    tiktok_url = ""

    html_content = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <meta
        name="viewport"
        content="width=device-width, initial-scale=1, viewport-fit=cover"
    >

    <title>Lletra</title>

    <style>
        * {{
            box-sizing: border-box;
        }}

        html,
        body {{
            margin: 0;
            padding: 0;
            width: 100%;
            min-height: 100%;
            background: #000;
            font-family:
                system-ui,
                -apple-system,
                BlinkMacSystemFont,
                "Segoe UI",
                Roboto,
                Arial,
                sans-serif;
        }}

        body {{
            min-height: 100dvh;
            overflow: hidden;
        }}

        .page {{
            position: relative;
            width: 100%;
            min-height: 100dvh;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #000;
        }}

        /*
         * VIDEO
         */

        #video-container {{
            position: absolute;
            inset: 0;
            width: 100%;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 1;
            transition: opacity .5s ease;
        }}

        #intro-video {{
            width: 100%;
            height: 100%;
            object-fit: cover;
        }}

        #video-container.hide {{
            opacity: 0;
            pointer-events: none;
        }}

        /*
         * REDES SOCIALES
         */

        #social-container {{
            position: absolute;
            inset: 0;
            width: 100%;
            min-height: 100dvh;

            display: flex;
            align-items: center;
            justify-content: center;

            padding:
                max(24px, env(safe-area-inset-top))
                24px
                max(24px, env(safe-area-inset-bottom));

            background:
                radial-gradient(
                    circle at top,
                    #1f2937 0%,
                    #0b1220 45%,
                    #05070b 100%
                );

            opacity: 0;
            visibility: hidden;

            transition:
                opacity .6s ease,
                visibility .6s ease;
        }}

        #social-container.show {{
            opacity: 1;
            visibility: visible;
        }}

        .social-content {{
            width: 100%;
            max-width: 480px;
            text-align: center;
            color: #fff;
        }}

        .logo {{
            width: 110px;
            max-width: 35vw;
            margin-bottom: 20px;
        }}

        h1 {{
            font-size: clamp(26px, 7vw, 38px);
            margin: 0 0 10px;
            line-height: 1.15;
        }}

        .subtitle {{
            color: #9ca3af;
            font-size: 16px;
            margin: 0 0 32px;
        }}

        .social-buttons {{
            display: flex;
            flex-direction: column;
            gap: 14px;
            width: 100%;
        }}

        .social-btn {{
            position: relative;

            display: flex;
            align-items: center;
            justify-content: center;

            width: 100%;
            min-height: 58px;

            padding: 15px 20px;

            border-radius: 16px;

            text-decoration: none;
            color: #fff;

            font-size: 17px;
            font-weight: 700;

            border: 1px solid rgba(255,255,255,.12);

            background: rgba(255,255,255,.08);

            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);

            transition:
                transform .2s ease,
                background .2s ease,
                border-color .2s ease;
        }}

        .social-btn:hover {{
            transform: translateY(-2px);
            background: rgba(255,255,255,.14);
            border-color: rgba(255,255,255,.25);
        }}

        .social-btn:active {{
            transform: scale(.98);
        }}

        .social-icon {{
            position: absolute;
            left: 20px;

            width: 30px;
            height: 30px;

            display: flex;
            align-items: center;
            justify-content: center;

            font-size: 22px;
        }}

        /*
         * REDIRECCIÓN
         */

        #redirect-message {{
            position: absolute;
            bottom: max(24px, env(safe-area-inset-bottom));

            left: 50%;
            transform: translateX(-50%);

            color: rgba(255,255,255,.65);

            font-size: 13px;
            text-align: center;

            z-index: 10;

            display: none;
        }}

        #redirect-message.show {{
            display: block;
        }}

        @media (min-width: 768px) {{
            #intro-video {{
                object-fit: contain;
            }}
        }}
    </style>
</head>

<body>

<div class="page">

    <!-- VIDEO -->
    <div id="video-container">
        <video
            id="intro-video"
            autoplay
            muted
            playsinline
            preload="auto"
        >
            <source src="{video_url}" type="video/mp4">
        </video>
    </div>


    <!-- REDES SOCIALES -->
    <div id="social-container">

        <div class="social-content">

            <h1>Síguenos</h1>

            <p class="subtitle">
                Conoce más sobre nosotros y mantente conectado.
            </p>

            <div class="social-buttons">

                <a
                    href="{instagram_url}"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="social-btn"
                >
                    <span class="social-icon">◎</span>
                    Instagram
                </a>

                <a
                    href="{facebook_url}"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="social-btn"
                >
                    <span class="social-icon">f</span>
                    Facebook
                </a>

                <a
                    href="{tiktok_url}"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="social-btn"
                >
                    <span class="social-icon">♪</span>
                    TikTok
                </a>

                <a
                    href="{linkedin_url}"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="social-btn"
                >
                    <span class="social-icon">in</span>
                    LinkedIn
                </a>

            </div>

        </div>

    </div>


    <div id="redirect-message">
        Redirigiendo...
    </div>

</div>


<script>

(function () {{

    const redirectTo = {to!r};

    const video = document.getElementById("intro-video");
    const videoContainer = document.getElementById("video-container");
    const socialContainer = document.getElementById("social-container");
    const redirectMessage = document.getElementById("redirect-message");

    let finished = false;


    function finishIntro() {{

        // Evitar que se ejecute dos veces
        if (finished) {{
            return;
        }}

        finished = true;


        /*
         * SI EXISTE "to":
         *
         * /pagina/?to=https://ejemplo.com
         *
         * redirigimos.
         */

        if (redirectTo) {{

            redirectMessage.classList.add("show");

            window.location.href = redirectTo;

            return;
        }}


        /*
         * SI NO EXISTE "to":
         * mostramos las redes sociales.
         */

        videoContainer.classList.add("hide");

        setTimeout(function () {{

            videoContainer.style.display = "none";
            socialContainer.classList.add("show");

        }}, 400);

    }}


    /*
     * Lo ideal:
     * esperar a que termine realmente el video.
     */

    video.addEventListener("ended", finishIntro);


    /*
     * Intentar reproducir automáticamente.
     */

    const playPromise = video.play();

    if (playPromise !== undefined) {{

        playPromise.catch(function () {{

            console.log(
                "El navegador bloqueó el autoplay."
            );

        }});

    }}


    /*
     * FALLBACK:
     *
     * Si por algún problema el video no termina,
     * después de 5 segundos continuamos.
     */

    setTimeout(function () {{

        finishIntro();

    }}, 5000);

}})();

</script>

</body>
</html>
"""

    return HttpResponse(html_content)


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
