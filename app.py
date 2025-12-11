"""
Aplicação Dash Plotly - Eletro Fundo
Sistema de acompanhamento de investimentos / fundo
Tema: Escuro (preto/cinza/amarelo)
"""
import logging
from dash import Dash, html, dcc, Input, Output
import dash_bootstrap_components as dbc
from config import DASH_HOST, DASH_PORT, DASH_DEBUG, LOG_LEVEL

# Configurar logging
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Inicializar Dash com tema DARKLY (escuro)
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    suppress_callback_exceptions=True
)
app.title = "Eletro Fundo"

# Estilos customizados (preto/cinza/amarelo)
CUSTOM_STYLE = {
    "background": "#0a0a0a",
    "color": "#e0e0e0",
}

NAVBAR_STYLE = {
    "background-color": "#1a1a1a",
    "border-bottom": "2px solid #ffc107",
}

# Componentes
def create_navbar():
    return dbc.Navbar(
        dbc.Container(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            html.Div(
                                [
                                    html.Span("⚡", style={"font-size": "24px", "margin-right": "8px"}),
                                    html.Span("Eletro Fundo", style={"font-size": "20px", "font-weight": "bold", "color": "#ffc107"}),
                                ]
                            ),
                            width="auto",
                        ),
                    ],
                    align="center",
                    className="g-0 w-100",
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            dbc.Nav(
                                [
                                    dbc.NavLink("Home", href="/", active="exact", style={"color": "#e0e0e0"}),
                                    dbc.NavLink("Posições", href="/posicoes", active="exact", style={"color": "#e0e0e0"}),
                                    dbc.NavLink("Operações", href="/operacoes", active="exact", style={"color": "#e0e0e0"}),
                                    dbc.NavLink("Preços", href="/precos", active="exact", style={"color": "#e0e0e0"}),
                                ],
                                pills=True,
                                className="ms-auto",
                            ),
                            width="auto",
                        ),
                    ],
                    align="center",
                    className="g-0 w-100 justify-content-end",
                ),
            ],
            fluid=True,
        ),
        color="dark",
        dark=True,
        sticky="top",
        style=NAVBAR_STYLE,
    )

def create_hero_card(title, value, subtitle, icon, color="warning"):
    return dbc.Card(
        dbc.CardBody(
            [
                html.Div(
                    [
                        html.Span(icon, style={"font-size": "32px", "margin-right": "12px"}),
                        html.Div(
                            [
                                html.P(title, className="text-muted mb-1", style={"font-size": "14px"}),
                                html.H3(value, className=f"text-{color} mb-0", style={"font-weight": "bold"}),
                                html.P(subtitle, className="text-muted mb-0", style={"font-size": "12px"}),
                            ],
                        ),
                    ],
                    style={"display": "flex", "align-items": "center"},
                ),
            ]
        ),
        style={"background-color": "#1a1a1a", "border": "1px solid #333"},
        className="h-100",
    )

# Layout principal
app.layout = html.Div(
    [
        dcc.Location(id="url", refresh=False),
        create_navbar(),
        html.Div(id="page-content", style={"min-height": "calc(100vh - 80px)", "background-color": "#0a0a0a"}),
    ],
    style=CUSTOM_STYLE,
)

# Páginas
def home_page():
    return dbc.Container(
        [
            # Hero Section
            dbc.Row(
                [
                    dbc.Col(create_hero_card("PL Atual", "R$ 0,00", "Aguardando dados", "💰"), md=4),
                    dbc.Col(create_hero_card("Cota Hoje", "R$ 0,00", "--", "📊", "info"), md=4),
                    dbc.Col(create_hero_card("Variação", "0%", "Últimas 24h", "📈", "success"), md=4),
                ],
                className="g-3 mb-4",
            ),
            # Placeholder para gráfico
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.H5("Curva de Cotas (Últimos 90 dias)", className="text-warning mb-3"),
                                    html.Div(
                                        "Gráfico será implementado aqui",
                                        style={"height": "300px", "display": "flex", "align-items": "center", "justify-content": "center", "color": "#666"},
                                    ),
                                ]
                            ),
                            style={"background-color": "#1a1a1a", "border": "1px solid #333"},
                        ),
                        width=12,
                    ),
                ],
                className="mb-4",
            ),
            # Placeholder para tabela de posições
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.H5("Posições Atuais", className="text-warning mb-3"),
                                    html.Div(
                                        "Tabela de posições será implementada aqui",
                                        style={"height": "200px", "display": "flex", "align-items": "center", "justify-content": "center", "color": "#666"},
                                    ),
                                ]
                            ),
                            style={"background-color": "#1a1a1a", "border": "1px solid #333"},
                        ),
                        width=12,
                    ),
                ],
            ),
        ],
        fluid=True,
        className="py-4",
    )

def posicoes_page():
    return dbc.Container(
        [
            html.H2("Posições", className="text-warning mb-4"),
            html.P("Página de posições em desenvolvimento...", className="text-muted"),
        ],
        fluid=True,
        className="py-4",
    )

def operacoes_page():
    return dbc.Container(
        [
            html.H2("Operações", className="text-warning mb-4"),
            html.P("Página de operações em desenvolvimento...", className="text-muted"),
        ],
        fluid=True,
        className="py-4",
    )

def precos_page():
    return dbc.Container(
        [
            html.H2("Preços", className="text-warning mb-4"),
            html.P("Página de preços em desenvolvimento...", className="text-muted"),
        ],
        fluid=True,
        className="py-4",
    )

# Callback para navegação
@app.callback(
    Output("page-content", "children"),
    [Input("url", "pathname")]
)
def display_page(pathname):
    if pathname == "/posicoes":
        return posicoes_page()
    elif pathname == "/operacoes":
        return operacoes_page()
    elif pathname == "/precos":
        return precos_page()
    else:
        return home_page()

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
        debug=DASH_DEBUG
    )
