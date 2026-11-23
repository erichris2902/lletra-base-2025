import os
import smtplib
import ssl

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ikigai2025.settings")
django.setup()

from django.conf import settings

HOST = settings.EMAIL_HOST
PORT = settings.EMAIL_PORT
USER = settings.EMAIL_HOST_USER
PASSWORD = settings.EMAIL_HOST_PASSWORD

try:
    context = ssl.create_default_context()

    with smtplib.SMTP(HOST, PORT, timeout=20) as smtp:
        smtp.ehlo()

        smtp.starttls(context=context)
        smtp.ehlo()

        print("TLS correcto")

        smtp.login(USER, PASSWORD)
        print("Autenticacion SMTP correcta")

except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")