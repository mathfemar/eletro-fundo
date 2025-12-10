"""
Aplicação Dash Plotly - Eletro Fundo
Sistema de acompanhamento de investimentos / fundo
"""
import logging
from dash import Dash
import dash_bootstrap_components as dbc
from config import DASH_HOST, DASH_PORT, DASH_DEBUG, LOG_LEVEL

# Configurar logging
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Inicializar Dash com tema Bootstrap
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}]
)

# Layout inicial
app.layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        dbc.CardTitle("Eletro Fundo", className="h1"),
                                        dbc.CardText(
                                            "Sistema de Acompanhamento de Investimentos",
                                            className="text-muted"
                                        ),
                                    ]
                                )
                            ],
                            className="mb-4"
                        )
                    ]
                )
            ]
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Alert(
                            "✓ Aplicação inicializada com sucesso!",
                            color="success",
                            className="mb-4"
                        )
                    ]
                )
            ]
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        dbc.CardTitle("Status do Projeto"),
                                        dbc.CardText(
                                            "Fase 1: Setup base\n"
                                            "✓ Estrutura de pastas criada\n"
                                            "✓ Configurações inicializadas\n"
                                            "✓ Modelos ORM definidos\n"
                                            "➜ Próximo: Testes de conexão"
                                        ),
                                        dbc.Button(
                                            "Testar Conexão",
                                            id="btn-test-connection",
                                            color="primary",
                                            className="me-2"
                                        ),
                                    ]
                                )
                            ]
                        )
                    ]
                )
            ]
        ),
    ],
    fluid=True,
    className="py-4"
)

if __name__ == "__main__":
    logger.info(f"Iniciando Dash em {DASH_HOST}:{DASH_PORT}")
    print(f"\n{'='*60}")
    print(f"🚀 Eletro Fundo - Webapp de Investimentos")
    print(f"{'='*60}")
    print(f"📍 Acesse: http://127.0.0.1:{DASH_PORT}")
    print(f"{'='*60}\n")
    
    app.run_server(
        host=DASH_HOST,
        port=DASH_PORT,
        debug=DASH_DEBUG,
        use_reloader=True
    )
