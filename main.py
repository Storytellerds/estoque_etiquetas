from ui.stock_app import build_ui
from nicegui import ui

build_ui()

ui.run(
    title="Estoque + Etiquetas",
    host="127.0.0.1",
    port=8080,
    show=True,
    reload=False,
)
