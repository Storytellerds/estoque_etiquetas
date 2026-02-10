from typing import List

import openpyxl

from models.stock_item import StockItem
from utils.text_utils import norm


COLUMN_ALIASES = {
    "position": ["armazem_sumare", "posicao", "posição", "pos", "endereco", "endereço", "local", "loc"],
    "code": ["codigo", "código", "code", "item", "cod"],
    "pn": ["pn", "part number", "partnumber", "p/n"],
    "description": ["descricao", "descrição", "description", "desc"],
}

REQUIRED_FIELDS = ["position", "code", "pn", "description"]


def _find_header_map(headers: List[str]) -> dict[str, int]:
    headers_norm = [norm(h) for h in headers]
    mapping: dict[str, int] = {}

    for field, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in headers_norm:
                mapping[field] = headers_norm.index(alias)
                break

    return mapping


def load_stock_items_from_excel(path: str) -> List[StockItem]:
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        raise ValueError("Planilha vazia.")

    headers = [str(cell or "") for cell in rows[0]]
    col_map = _find_header_map(headers)

    missing = [f for f in REQUIRED_FIELDS if f not in col_map]
    if missing:
        raise ValueError(
            "Não encontrei as colunas obrigatórias no Excel: "
            + ", ".join(missing)
            + "\n\nCabeçalhos encontrados:\n- "
            + "\n- ".join(headers)
        )

    items: List[StockItem] = []
    for row in rows[1:]:
        position = str(row[col_map["position"]] or "").strip()
        code = str(row[col_map["code"]] or "").strip()
        pn = str(row[col_map["pn"]] or "").strip()
        description = str(row[col_map["description"]] or "").strip()

        # ignora linha totalmente vazia
        if not (position or code or pn or description):
            continue

        items.append(
            StockItem(
                position=position,
                code=code,
                pn=pn,
                description=description,
            )
        )

    return items
