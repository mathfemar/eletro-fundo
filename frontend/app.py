from dash import Dash
import dash_bootstrap_components as dbc  # noqa: F401

from config import DASH_HOST, DASH_PORT, DASH_DEBUG
from .layout import build_main_layout
from .callbacks import register_page_callbacks


def create_app() -> Dash:
    app = Dash(
        __name__,
        external_stylesheets=[dbc.themes.DARKLY],
        meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
        suppress_callback_exceptions=True,
    )
    app.title = "Eletro Fundo"
    app.layout = build_main_layout()
    register_page_callbacks(app)
    return app
