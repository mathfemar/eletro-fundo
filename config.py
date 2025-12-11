import os
from dotenv import load_dotenv

load_dotenv()

# Ambiente
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Database
DB_HOST = os.getenv("DB_HOST", "100.116.199.25")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "eletrofundo")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_SCHEMA = os.getenv("DB_SCHEMA", "public")  # Não usado mais, mas manter para compatibilidade

# Construir URL de conexão
if DB_PASSWORD:
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:
    DATABASE_URL = f"postgresql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Dash
DASH_HOST = os.getenv("DASH_HOST", "0.0.0.0")
DASH_PORT = int(os.getenv("DASH_PORT", 8526))
DASH_DEBUG = os.getenv("DASH_DEBUG", "True").lower() == "true"
DASH_DEV_TOOLS_HOT_RELOAD = os.getenv("DASH_DEV_TOOLS_HOT_RELOAD", "False").lower() == "true"

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.path.join(os.path.dirname(__file__), "logs", "app.log")

# Yahoo Finance
YF_START_DATE = "2020-01-01"
YF_MAX_RETRIES = 4
YF_CHUNK_SIZE = 10  # Download tickers em chunks para evitar erros

print(f"[CONFIG] Ambiente: {ENVIRONMENT}")
print(f"[CONFIG] Database: {DB_HOST}:{DB_PORT}/{DB_NAME}")
print(f"[CONFIG] Dash: {DASH_HOST}:{DASH_PORT}")
print(f"[CONFIG] Hot reload: {'enabled' if DASH_DEV_TOOLS_HOT_RELOAD else 'disabled'}")
