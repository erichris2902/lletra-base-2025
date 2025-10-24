import datetime, re

def clean_text(text: str) -> str:
    """Elimina espacios extra y normaliza texto."""
    return re.sub(r'\s+', ' ', text.strip()) if text else ''

def timestamp() -> str:
    """Devuelve timestamp en formato legible."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def safe_get(d, path, default=None):
    """Acceso seguro a dicts anidados."""
    try:
        for p in path.split('.'):
            d = d[p]
        return d
    except Exception:
        return default