"""Configuración: lee las credenciales desde variables de entorno / archivo .env.
Las credenciales NUNCA se escriben en el código ni se publican en GitHub."""
import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[2]
load_dotenv(RAIZ / ".env")

DB = {
    "host": os.getenv("PGHOST", "localhost"),
    "port": os.getenv("PGPORT", "5432"),
    "dbname": os.getenv("PGDATABASE", "sig_cauca"),
    "user": os.getenv("PGUSER", "postgres"),
    "password": os.getenv("PGPASSWORD", ""),
}
FRONTEND_DIR = RAIZ / "frontend"
