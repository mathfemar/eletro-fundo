from dash import html, dcc
import dash_bootstrap_components as dbc

CUSTOM_STYLE = {
    "background": "linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 100%)",
    "color": "#e0e0e0",
    "fontFamily": "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
}

NAVBAR_STYLE = {
    "background": "linear-gradient(90deg, #1a1a1a 0%, #2d2d2d 100%)",
    "borderBottom": "3px solid #ffc107",
    "boxShadow": "0 4px 6px rgba(0, 0, 0, 0.3)",
    "backdropFilter": "blur(10px)",
}


def create_navbar() -> dbc.Navbar:
    return dbc.Navbar(
        dbc.Container(
            [
                # Logo
                html.Span("⚡", 
                    id="navbar-logo",
                    style={
                        "font-size": "28px",
                        "filter": "drop-shadow(0 0 8px #ffc107)",
                        "animation": "pulse 2s infinite"
                    }
                ),
                # Desktop title (hidden on mobile)
                html.Span("Eletro Fundo", 
                    id="navbar-title",
                    style={
                        "font-size": "22px", 
                        "font-weight": "700", 
                        "color": "#ffc107",
                        "letterSpacing": "1px",
                        "textShadow": "0 0 10px rgba(255, 193, 7, 0.3)",
                        "marginRight": "20px"
                    },
                    className="d-none d-md-inline"
                ),
                # Navigation links
                dbc.Nav(
                    [
                        dbc.NavLink("Home", href="/", active="exact", 
                            style={"color": "#e0e0e0", "fontWeight": "500", "transition": "all 0.3s"},
                            className="nav-link-custom"),
                        dbc.NavLink("Posições", href="/posicoes", active="exact", 
                            style={"color": "#e0e0e0", "fontWeight": "500", "transition": "all 0.3s"},
                            className="nav-link-custom"),
                        dbc.NavLink("Operações", href="/operacoes", active="exact", 
                            style={"color": "#e0e0e0", "fontWeight": "500", "transition": "all 0.3s"},
                            className="nav-link-custom"),
                        dbc.NavLink("Preços", href="/precos", active="exact", 
                            style={"color": "#e0e0e0", "fontWeight": "500", "transition": "all 0.3s"},
                            className="nav-link-custom"),
                    ],
                    pills=True,
                    className="ms-auto flex-row",
                ),
            ],
            fluid=True,
            className="d-flex align-items-center",
        ),
        color="dark",
        dark=True,
        sticky="top",
        style=NAVBAR_STYLE,
    )


def create_hero_card(title: str, value: str, subtitle: str, icon: str, color: str = "warning") -> dbc.Card:
    color_hex = _get_color_hex(color)
    return dbc.Card(
        dbc.CardBody(
            [
                html.Div(
                    [
                        html.Div(
                            html.Span(icon, style={
                                "font-size": "48px",
                                "filter": f"drop-shadow(0 0 12px {color_hex})"
                            }),
                            style={
                                "marginRight": "20px",
                                "display": "flex",
                                "alignItems": "center",
                                "justifyContent": "center",
                                "width": "80px",
                                "height": "80px",
                                "borderRadius": "50%",
                                "background": f"radial-gradient(circle, {color_hex}22 0%, transparent 70%)"
                            }
                        ),
                        html.Div(
                            [
                                html.P(title, className="text-muted mb-2", 
                                    style={"font-size": "13px", "textTransform": "uppercase", "letterSpacing": "1px", "fontWeight": "600"}),
                                html.H2(value, className=f"text-{color} mb-1", 
                                    style={"font-weight": "700", "fontSize": "32px", "textShadow": f"0 0 20px {color_hex}44"}),
                                html.P(subtitle, className="text-muted mb-0", 
                                    style={"font-size": "13px", "fontStyle": "italic"}),
                            ],
                            style={"flex": "1"}
                        ),
                    ],
                    style={"display": "flex", "align-items": "center"},
                ),
            ],
            style={"padding": "24px"}
        ),
        style={
            "background": "linear-gradient(135deg, #1a1a1a 0%, #252525 100%)",
            "border": "1px solid #333",
            "borderRadius": "12px",
            "boxShadow": "0 8px 16px rgba(0, 0, 0, 0.4)",
            "transition": "all 0.3s ease",
        },
        className="h-100 hero-card",
    )


def _get_color_hex(color: str) -> str:
    """Convert bootstrap color names to hex."""
    colors = {
        "warning": "#ffc107",
        "info": "#17a2b8",
        "success": "#28a745",
        "danger": "#dc3545",
        "primary": "#007bff",
    }
    return colors.get(color, "#ffc107")


def home_page() -> dbc.Container:
    return dbc.Container(
        [
            # Header Section
            dbc.Row(
                [
                    dbc.Col(
                        html.Div(
                            [
                                html.H1("Dashboard de Investimentos", 
                                    style={
                                        "color": "#ffc107", 
                                        "fontWeight": "700",
                                        "marginBottom": "8px",
                                        "fontSize": "36px",
                                        "textShadow": "0 0 20px rgba(255, 193, 7, 0.3)"
                                    }),
                                html.P("Acompanhe seu patrimônio em tempo real",
                                    style={"color": "#999", "fontSize": "16px", "marginBottom": "0"}),
                            ],
                            style={"padding": "20px 0"}
                        ),
                        width=12,
                    ),
                ],
                className="mb-4",
            ),
            # Hero Cards
            dbc.Row(
                [
                    dbc.Col(create_hero_card("Patrimônio Líquido", "R$ 0,00", "Aguardando dados do servidor", "💰"), xs=12, sm=12, md=4),
                    dbc.Col(create_hero_card("Valor da Cota", "R$ 0,00", "Última atualização: --", "💵", "info"), xs=12, sm=12, md=4),
                    dbc.Col(create_hero_card("Rentabilidade", "+0,00%", "Último Mês", "💸", "success"), xs=12, sm=12, md=4),
                ],
                className="g-4 mb-5",
            ),
            # Chart Section
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.Div(
                                        [
                                            html.H4("Evolução do Patrimônio", 
                                                style={"color": "#ffc107", "fontWeight": "600", "marginBottom": "4px"}),
                                            html.P("Últimos 90 dias", 
                                                style={"color": "#999", "fontSize": "14px", "marginBottom": "0"}),
                                        ],
                                        style={"marginBottom": "20px"}
                                    ),
                                    html.Div(
                                        [
                                            html.Div("📈", style={"fontSize": "64px", "marginBottom": "16px", "opacity": "0.3"}),
                                            html.P("Gráfico interativo será carregado aqui",
                                                style={"color": "#666", "fontSize": "16px"}),
                                            html.P("Conecte ao banco de dados para visualizar os dados reais",
                                                style={"color": "#555", "fontSize": "14px", "fontStyle": "italic"}),
                                        ],
                                        style={
                                            "height": "350px", 
                                            "display": "flex", 
                                            "flexDirection": "column",
                                            "align-items": "center", 
                                            "justifyContent": "center",
                                            "border": "2px dashed #333",
                                            "borderRadius": "8px",
                                            "background": "rgba(255, 193, 7, 0.02)"
                                        },
                                    ),
                                ],
                                style={"padding": "24px"}
                            ),
                            style={
                                "background": "linear-gradient(135deg, #1a1a1a 0%, #252525 100%)",
                                "border": "1px solid #333",
                                "borderRadius": "12px",
                                "boxShadow": "0 8px 16px rgba(0, 0, 0, 0.4)",
                            },
                        ),
                        width=12,
                    ),
                ],
                className="mb-5",
            ),
            # Positions Table Section
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.Div(
                                        [
                                            html.H4("Posições em Carteira", 
                                                style={"color": "#ffc107", "fontWeight": "600", "marginBottom": "4px"}),
                                            html.P("Visão consolidada dos seus ativos", 
                                                style={"color": "#999", "fontSize": "14px", "marginBottom": "0"}),
                                        ],
                                        style={"marginBottom": "20px"}
                                    ),
                                    html.Div(
                                        [
                                            html.Div("💼", style={"fontSize": "64px", "marginBottom": "16px", "opacity": "0.3"}),
                                            html.P("Tabela de posições será exibida aqui",
                                                style={"color": "#666", "fontSize": "16px"}),
                                            html.P("Você verá: Ativo | Quantidade | Preço Médio | Valor Atual | Rentabilidade",
                                                style={"color": "#555", "fontSize": "13px", "fontStyle": "italic"}),
                                        ],
                                        style={
                                            "height": "250px", 
                                            "display": "flex", 
                                            "flexDirection": "column",
                                            "align-items": "center", 
                                            "justifyContent": "center",
                                            "border": "2px dashed #333",
                                            "borderRadius": "8px",
                                            "background": "rgba(255, 193, 7, 0.02)"
                                        },
                                    ),
                                ],
                                style={"padding": "24px"}
                            ),
                            style={
                                "background": "linear-gradient(135deg, #1a1a1a 0%, #252525 100%)",
                                "border": "1px solid #333",
                                "borderRadius": "12px",
                                "boxShadow": "0 8px 16px rgba(0, 0, 0, 0.4)",
                            },
                        ),
                        width=12,
                    ),
                ],
            ),
        ],
        fluid=True,
        className="py-4",
    )


def posicoes_page() -> dbc.Container:
    return dbc.Container(
        [
            html.Div(
                [
                    html.H1("Posições", style={
                        "color": "#ffc107", 
                        "fontWeight": "700",
                        "marginBottom": "8px",
                        "fontSize": "36px",
                        "textShadow": "0 0 20px rgba(255, 193, 7, 0.3)"
                    }),
                    html.P("Gerencie e acompanhe suas posições ativas",
                        style={"color": "#999", "fontSize": "16px"}),
                ],
                style={"padding": "20px 0", "marginBottom": "30px"}
            ),
            dbc.Card(
                dbc.CardBody(
                    [
                        html.Div("📊", style={"fontSize": "80px", "marginBottom": "20px", "opacity": "0.3"}),
                        html.H4("Página em desenvolvimento", style={"color": "#999", "marginBottom": "12px"}),
                        html.P("Em breve você poderá visualizar e gerenciar todas as suas posições aqui.",
                            style={"color": "#666", "fontSize": "16px"}),
                    ],
                    style={
                        "padding": "60px",
                        "textAlign": "center",
                        "minHeight": "400px",
                        "display": "flex",
                        "flexDirection": "column",
                        "justifyContent": "center",
                        "alignItems": "center"
                    }
                ),
                style={
                    "background": "linear-gradient(135deg, #1a1a1a 0%, #252525 100%)",
                    "border": "1px solid #333",
                    "borderRadius": "12px",
                    "boxShadow": "0 8px 16px rgba(0, 0, 0, 0.4)",
                }
            ),
        ],
        fluid=True,
        className="py-4",
    )


def operacoes_page() -> dbc.Container:
    return dbc.Container(
        [
            html.Div(
                [
                    html.H1("Operações", style={
                        "color": "#ffc107", 
                        "fontWeight": "700",
                        "marginBottom": "8px",
                        "fontSize": "36px",
                        "textShadow": "0 0 20px rgba(255, 193, 7, 0.3)"
                    }),
                    html.P("Registre e consulte todas as operações do fundo",
                        style={"color": "#999", "fontSize": "16px"}),
                ],
                style={"padding": "20px 0", "marginBottom": "30px"}
            ),
            dbc.Card(
                dbc.CardBody(
                    [
                        html.Div("💼", style={"fontSize": "80px", "marginBottom": "20px", "opacity": "0.3"}),
                        html.H4("Página em desenvolvimento", style={"color": "#999", "marginBottom": "12px"}),
                        html.P("Em breve você poderá registrar compras, vendas, aportes e resgates.",
                            style={"color": "#666", "fontSize": "16px"}),
                    ],
                    style={
                        "padding": "60px",
                        "textAlign": "center",
                        "minHeight": "400px",
                        "display": "flex",
                        "flexDirection": "column",
                        "justifyContent": "center",
                        "alignItems": "center"
                    }
                ),
                style={
                    "background": "linear-gradient(135deg, #1a1a1a 0%, #252525 100%)",
                    "border": "1px solid #333",
                    "borderRadius": "12px",
                    "boxShadow": "0 8px 16px rgba(0, 0, 0, 0.4)",
                }
            ),
        ],
        fluid=True,
        className="py-4",
    )


def precos_page() -> dbc.Container:
    return dbc.Container(
        [
            html.Div(
                [
                    html.H1("Preços de Mercado", style={
                        "color": "#ffc107", 
                        "fontWeight": "700",
                        "marginBottom": "8px",
                        "fontSize": "36px",
                        "textShadow": "0 0 20px rgba(255, 193, 7, 0.3)"
                    }),
                    html.P("Acompanhe cotações em tempo real dos seus ativos",
                        style={"color": "#999", "fontSize": "16px"}),
                ],
                style={"padding": "20px 0", "marginBottom": "30px"}
            ),
            dbc.Card(
                dbc.CardBody(
                    [
                        html.Div("💰", style={"fontSize": "80px", "marginBottom": "20px", "opacity": "0.3"}),
                        html.H4("Página em desenvolvimento", style={"color": "#999", "marginBottom": "12px"}),
                        html.P("Em breve você terá acesso aos preços atualizados via Yahoo Finance.",
                            style={"color": "#666", "fontSize": "16px"}),
                    ],
                    style={
                        "padding": "60px",
                        "textAlign": "center",
                        "minHeight": "400px",
                        "display": "flex",
                        "flexDirection": "column",
                        "justifyContent": "center",
                        "alignItems": "center"
                    }
                ),
                style={
                    "background": "linear-gradient(135deg, #1a1a1a 0%, #252525 100%)",
                    "border": "1px solid #333",
                    "borderRadius": "12px",
                    "boxShadow": "0 8px 16px rgba(0, 0, 0, 0.4)",
                }
            ),
        ],
        fluid=True,
        className="py-4",
    )


def build_main_layout() -> html.Div:
    return html.Div(
        [
            dcc.Location(id="url", refresh=False),
            create_navbar(),
            html.Div(id="page-content", style={"min-height": "calc(100vh - 80px)", "background-color": "#0a0a0a"}),
        ],
        style=CUSTOM_STYLE,
    )
