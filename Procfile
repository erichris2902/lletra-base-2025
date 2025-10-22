web: gunicorn ikigai2025.wsgi
worker: celery -A ikigai2025 worker --loglevel=info --concurrency=1
beat: celery -A ikigai2025 beat --loglevel=info