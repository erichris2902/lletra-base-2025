# lletra2025/env.py
import os

def load_environment():
    """Carga .env solo si no estamos en producción (Heroku)."""
    if not os.getenv("DYNO"):  # Heroku siempre define esta variable
        from dotenv import load_dotenv
        from pathlib import Path

        env_path = Path(__file__).resolve().parent.parent / '.env'
        load_dotenv(dotenv_path=env_path)