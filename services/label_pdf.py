from turtle import left
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

from models.stock_item import StockItem
from utils.text_utils import ellipsize


def _draw_border(pdf: canvas.Canvas, width_mm: int, height_mm: int) -> None:
    # borda leve para ajudar no recorte/alinhamento
    pdf.setLineWidth(0.3)
    pdf.rect(1 * mm, 1 * mm, (width_mm - 2) * mm, (height_mm - 2) * mm)

def _draw_centered_in_area(pdf: canvas.Canvas, x_left: float, x_right: float, y: float, text: str) -> None:
    text_width = pdf.stringWidth(text, pdf._fontname, pdf._fontsize)
    area_center = (x_left + x_right) / 2
    x = area_center - (text_width / 2)
    pdf.drawString(x, y, text)

def _wrap_text_by_width(pdf: canvas.Canvas, text: str, max_width: float) -> list[str]:
    """
    Quebra o texto em múltiplas linhas respeitando a largura máxima (em pontos).
    """
    words = text.split()
    lines: list[str] = []
    current = ""

    for word in words:
        test = f"{current} {word}".strip()
        w = pdf.stringWidth(test, pdf._fontname, pdf._fontsize)
        if w <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines

def generate_labels_pdf(
    output_path: str,
    label_size_mm: tuple[int, int],
    item: StockItem,
    quantity: int,
) -> None:
    """
    Gera um PDF com 'quantity' páginas. Cada página = 1 etiqueta no tamanho exato.
    Layout pensado para etiqueta de posição/estoque.
    """
    if quantity < 1:
        raise ValueError("Quantidade deve ser >= 1.")

    width_mm, height_mm = label_size_mm
    pdf = canvas.Canvas(output_path, pagesize=(width_mm * mm, height_mm * mm))

    is_large = label_size_mm == (100, 50)

    # Margens
    left = 8 * mm
    top = (height_mm - 10) * mm  # coordenada Y do topo "útil"
    right = (width_mm * mm) - (4 * mm)     # margem direita
    value_area_left = left + (0 * mm)     # começa depois do "COD:"/"PN:"

    # Fontes (bem legíveis e consistentes)
    if is_large:
        pos_font = 18
        label_font = 9
        value_font = 10
        desc_font = 12
        # cortes
        pos_max = 18
        code_max = 28
        pn_max = 28
        desc_max = 62
        # espaçamentos
        line_gap_mm = 6.0
    else:
        pos_font = 12
        label_font = 7
        value_font = 8
        desc_font = 7
        pos_max = 14
        code_max = 20
        pn_max = 20
        desc_max = 28
        line_gap_mm = 4.2

    for _ in range(quantity):
        _draw_border(pdf, width_mm, height_mm)

        pdf.setFont("Helvetica-Bold", pos_font)
        _draw_centered_in_area(pdf, left, right, top - 0 * mm, ellipsize(item.position, pos_max))


        # Linha 2: Código
        y2 = top - (line_gap_mm * 1) * mm
        pdf.setFont("Helvetica", label_font)
        pdf.drawString(left, y2, "COD:")
        pdf.setFont("Helvetica-Bold", value_font)
        _draw_centered_in_area(pdf, value_area_left, right, y2, ellipsize(item.code, code_max))

        # Linha 3: PN
        y3 = top - (line_gap_mm * 2) * mm
        pdf.setFont("Helvetica", label_font)
        pdf.drawString(left, y3, "PN:")
        pdf.setFont("Helvetica-Bold", value_font)
        _draw_centered_in_area(pdf, value_area_left, right, y3, ellipsize(item.pn, pn_max))

        # Linha 4: Descrição (menor) -> centralizada no "miolo" todo
        y4 = top - (line_gap_mm * 3) * mm
        pdf.setFont("Helvetica", desc_font)

        # largura útil da descrição (entre as margens)
        desc_area_left = left
        desc_area_right = right
        max_width = desc_area_right - desc_area_left

        # quebra em linhas pela largura real
        lines = _wrap_text_by_width(pdf, item.description, max_width)

        # limitar quantidade de linhas (pra não invadir a etiqueta)
        max_lines = 2 if is_large else 2  # pode testar 3 na 100x50 depois

        text_obj = pdf.beginText(desc_area_left, y4)
        for i, line in enumerate(lines[:max_lines]):
            text_obj.textLine(line)

        pdf.drawText(text_obj)

        pdf.showPage()

    pdf.save()
