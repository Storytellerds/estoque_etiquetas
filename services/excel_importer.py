from typing import List
import unicodedata
import openpyxl

from models.stock_item import StockItem


COLUMN_ALIASES = {
    "position": ["Armaz_Sumare", "posicao", "posição", "pos", "endereco", "endereço", "local", "loc"],
    "code": ["CODIGO", "código", "code", "item", "cod"],
    "pn": ["Part Number", "part number", "partnumber", "p/n"],
    "description": ["DESCRICAO", "descrição", "description", "desc"],
}

REQUIRED_FIELDS = ["position", "code", "pn", "description"]


def norm(text: str) -> str:
    text = str(text or "")
    text = text.replace("\n", " ").replace("\r", " ")
    text = " ".join(text.split())
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")
    return text.strip().lower()


def _find_header_map(headers: List[str]) -> dict[str, int]:
    headers_norm = [norm(h) for h in headers]
    mapping: dict[str, int] = {}

    for field, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            alias_norm = norm(alias)
            if alias_norm in headers_norm:
                mapping[field] = headers_norm.index(alias_norm)
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

    header_norm = [norm(h) for h in headers]

    items: List[StockItem] = []
    for row in rows[1:]:
        row_values = [str(cell or "").strip() for cell in row]

        if [norm(v) for v in row_values[:len(headers)]] == header_norm:
            continue

        position = str(row[col_map["position"]] or "").strip()
        code = str(row[col_map["code"]] or "").strip()
        pn = str(row[col_map["pn"]] or "").strip()
        description = str(row[col_map["description"]] or "").strip()

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