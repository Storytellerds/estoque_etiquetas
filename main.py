from ui.stock_app import build_ui
from nicegui import ui

build_ui()

ui.run(
    title="Estoque + Etiquetas",
    native=True,
    window_size=(1100, 700),
    reload=False,
)
