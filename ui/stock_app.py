import os
import tempfile
from dataclasses import dataclass, field

from nicegui import ui, events

from models.stock_item import StockItem
from services.excel_importer import load_stock_items_from_excel
from services.label_pdf import generate_labels_pdf
from services.file_opener import open_with_default_app
from services.raw_printer import send_raw_to_printer
from services.label_zpl import build_zpl_label
from utils.text_utils import contains


# ---------------------------------------------------------------------------
# Estado da aplicação
# ---------------------------------------------------------------------------

@dataclass
class AppState:
    all_items:       list[StockItem] = field(default_factory=list)
    filtered_items:  list[StockItem] = field(default_factory=list)
    selected_item:   StockItem | None = None
    filter_position: str = ""
    filter_code:     str = ""
    filter_pn:       str = ""
    filter_desc:     str = ""
    label_size:      str = "100x50"
    quantity:        int = 1
    printer_name:    str = "VZPL_port_Douglas"


state = AppState()

# Referências de widgets para atualização cross-function
_status_label:   ui.label  | None = None
_grid:           ui.aggrid | None = None
_input_position: ui.input  | None = None
_input_code:     ui.input  | None = None
_input_pn:       ui.input  | None = None
_input_desc:     ui.input  | None = None


# ---------------------------------------------------------------------------
# Lógica de filtro e grid
# ---------------------------------------------------------------------------

def _apply_filters() -> None:
    state.filtered_items = [
        it for it in state.all_items
        if contains(it.position,     state.filter_position)
        and contains(it.code,        state.filter_code)
        and contains(it.pn,          state.filter_pn)
        and contains(it.description, state.filter_desc)
    ]
    state.selected_item = None
    _refresh_grid()
    if _status_label:
        _status_label.set_text(
            f"Mostrando: {len(state.filtered_items)} / {len(state.all_items)} itens."
        )


def _clear_filters() -> None:
    state.filter_position = ""
    state.filter_code     = ""
    state.filter_pn       = ""
    state.filter_desc     = ""
    for inp in (_input_position, _input_code, _input_pn, _input_desc):
        if inp:
            inp.value = ""


def _refresh_grid() -> None:
    if not _grid:
        return
    _grid.options["rowData"] = [
        {
            "position":    it.position,
            "code":        it.code,
            "pn":          it.pn,
            "description": it.description,
        }
        for it in state.filtered_items
    ]
    _grid.update()


# ---------------------------------------------------------------------------
# Handlers de eventos
# ---------------------------------------------------------------------------

def _handle_row_click(e) -> None:
    row = e.args.get("data", {}) if isinstance(e.args, dict) else {}
    state.selected_item = next(
        (
            it for it in state.filtered_items
            if it.position == row.get("position")
            and it.code == row.get("code")
            and it.pn == row.get("pn")
        ),
        None,
    )


def _handle_file_upload(e: events.UploadEventArguments) -> None:
    suffix = ".xlsm" if (e.name or "").endswith(".xlsm") else ".xlsx"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(e.content.read())
        tmp_path = tmp.name

    try:
        state.all_items = load_stock_items_from_excel(tmp_path)
    except Exception as exc:
        ui.notify(str(exc), type="negative", timeout=0)
        return
    finally:
        os.unlink(tmp_path)

    _apply_filters()
    if _status_label:
        _status_label.set_text(f"Importado: {len(state.all_items)} itens.")
    ui.notify(f"Importado: {len(state.all_items)} itens.", type="positive")


def _on_print_pdf() -> None:
    item = state.selected_item
    if not item:
        ui.notify("Selecione um item no grid primeiro.", type="warning")
        return

    qty = state.quantity
    if qty < 1:
        ui.notify("Quantidade deve ser >= 1.", type="negative")
        return

    label_size = (100, 50) if state.label_size == "100x50" else (50, 30)

    try:
        tmp_dir   = tempfile.gettempdir()
        safe_code = "".join(ch for ch in item.code if ch.isalnum() or ch in ("-", "_"))[:20] or "item"
        pdf_path  = os.path.join(tmp_dir, f"etiquetas_{safe_code}_{label_size[0]}x{label_size[1]}.pdf")

        generate_labels_pdf(pdf_path, label_size_mm=label_size, item=item, quantity=qty)
        open_with_default_app(pdf_path)

        ui.notify(
            "PDF gerado. Imprima em escala 100% (não ajustar à página).",
            type="positive",
            timeout=8000,
        )
    except Exception as exc:
        ui.notify(f"Erro: {exc}", type="negative", timeout=0)


def _on_print_zpl() -> None:
    item = state.selected_item
    if not item:
        ui.notify("Selecione um item no grid primeiro.", type="warning")
        return

    qty = state.quantity
    if qty < 1:
        ui.notify("Quantidade deve ser >= 1.", type="negative")
        return

    printer_name = state.printer_name.strip()
    if not printer_name:
        ui.notify("Informe o nome da impressora do Windows.", type="negative")
        return

    label_size = (100, 50) if state.label_size == "100x50" else (50, 30)

    try:
        zpl     = build_zpl_label(item, label_size)
        payload = (zpl + "\n").encode("utf-8")

        for i in range(qty):
            send_raw_to_printer(
                printer_name,
                payload,
                job_name=f"Etiqueta {item.code} ({i + 1}/{qty})",
            )

        ui.notify(f"Enviado {qty} etiqueta(s) via ZPL para: {printer_name}", type="positive")
    except Exception as exc:
        ui.notify(f"Erro ao imprimir (ZPL): {exc}", type="negative", timeout=0)


# ---------------------------------------------------------------------------
# Construtores de UI
# ---------------------------------------------------------------------------

def _build_filter_panel() -> None:
    global _status_label, _input_position, _input_code, _input_pn, _input_desc

    with ui.card().classes("w-full"):
        with ui.row().classes("w-full flex-wrap gap-4 items-end"):
            _input_position = ui.input(
                label="Posição",
                on_change=lambda e: setattr(state, "filter_position", e.value),
            ).classes("w-36")
            _input_position.on("keydown.enter", _apply_filters)

            _input_code = ui.input(
                label="Código",
                on_change=lambda e: setattr(state, "filter_code", e.value),
            ).classes("w-36")
            _input_code.on("keydown.enter", _apply_filters)

            _input_pn = ui.input(
                label="PN",
                on_change=lambda e: setattr(state, "filter_pn", e.value),
            ).classes("w-36")
            _input_pn.on("keydown.enter", _apply_filters)

            _input_desc = ui.input(
                label="Descrição",
                on_change=lambda e: setattr(state, "filter_desc", e.value),
            ).classes("flex-1 min-w-40")
            _input_desc.on("keydown.enter", _apply_filters)

        with ui.row().classes("w-full gap-2 items-center flex-wrap"):
            ui.upload(
                label="Importar Excel",
                on_upload=_handle_file_upload,
                auto_upload=True,
                max_files=1,
            ).props('accept=".xlsx,.xlsm" flat dense color=primary').classes("shrink-0")

            ui.button("Pesquisar", on_click=_apply_filters, icon="search")
            ui.button("Limpar filtros", on_click=_clear_filters, icon="clear").props("flat")

            _status_label = ui.label("Nenhum arquivo importado.").classes(
                "ml-auto text-sm text-gray-500"
            )


def _build_grid() -> None:
    global _grid

    _grid = ui.aggrid(
        {
            "defaultColDef": {"sortable": True, "resizable": True, "filter": True},
            "columnDefs": [
                {"headerName": "Posição",   "field": "position",    "width": 130},
                {"headerName": "Código",    "field": "code",        "width": 150},
                {"headerName": "PN",        "field": "pn",          "width": 170},
                {"headerName": "Descrição", "field": "description", "flex": 1},
            ],
            "rowData": [],
            "rowSelection": "single",
            ":getRowId": "(params) => params.data.position + '_' + params.data.code + '_' + params.data.pn",
        }
    ).classes("w-full").style("height: 400px;")

    _grid.on("rowClicked", _handle_row_click)


def _build_print_panel() -> None:
    with ui.card().classes("w-full"):
        ui.label("Impressão").classes("text-base font-semibold")
        with ui.row().classes("w-full flex-wrap gap-4 items-end"):
            ui.select(
                label="Tamanho",
                options=["100x50", "50x30"],
                value=state.label_size,
                on_change=lambda e: setattr(state, "label_size", e.value),
            ).classes("w-28")

            ui.number(
                label="Quantidade",
                value=state.quantity,
                min=1,
                step=1,
                precision=0,
                on_change=lambda e: setattr(state, "quantity", int(e.value or 1)),
            ).classes("w-28")

            ui.button("Gerar PDF", on_click=_on_print_pdf, icon="picture_as_pdf")

            ui.input(
                label="Impressora (Windows)",
                value=state.printer_name,
                on_change=lambda e: setattr(state, "printer_name", e.value),
            ).classes("w-64")

            ui.button("Imprimir (ZPL)", on_click=_on_print_zpl, icon="print")


# ---------------------------------------------------------------------------
# Ponto de entrada público
# ---------------------------------------------------------------------------

def build_ui() -> None:
    with ui.column().classes("w-full max-w-screen-xl mx-auto p-4 gap-4"):
        ui.label("Estoque + Etiquetas").classes("text-2xl font-bold")
        _build_filter_panel()
        _build_grid()
        _build_print_panel()
