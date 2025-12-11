"""Entry point do frontend do Eletro Fundo."""
import logging

from config import DASH_HOST, DASH_PORT, DASH_DEBUG, DASH_DEV_TOOLS_HOT_RELOAD, LOG_LEVEL
from frontend import create_app

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = create_app()

if __name__ == "__main__":
    logger.info(f"Iniciando Dash em {DASH_HOST}:{DASH_PORT}")
    print(f"\n{'='*60}")
    print(f"🚀 Eletro Fundo - Webapp de Investimentos")
    print(f"{'='*60}")
    print(f"🌐 URL: http://{DASH_HOST}:{DASH_PORT}")
    print(f"🎨 Tema: Escuro (Preto/Cinza/Amarelo)")
    print(f"{'='*60}\n")

    app.run_server(
        host=DASH_HOST,
        port=DASH_PORT,
        debug=DASH_DEBUG,
        dev_tools_hot_reload=DASH_DEV_TOOLS_HOT_RELOAD
    )
