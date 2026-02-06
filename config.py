"""Configuración centralizada de la aplicación."""
import os
from pathlib import Path

# Rutas
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
DB_PATH = DATA_DIR / "app.db"
LOG_FILE = LOGS_DIR / "app.log"

# Crear directorios si no existen
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Base de datos
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Streamlit config
STREAMLIT_CONFIG = {
    "page_layout": "wide",
    "max_upload_size": 200,
}
