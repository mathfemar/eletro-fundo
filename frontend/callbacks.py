from dash import Input, Output


def register_page_callbacks(app):
    from .layout import home_page, posicoes_page, operacoes_page, precos_page

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
        return home_page()
