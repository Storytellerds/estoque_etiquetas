from models.stock_item import StockItem
from utils.text_utils import ellipsize


def _zpl_escape(text: str) -> str:
    # ZPL costuma aceitar texto simples; aqui só limpamos quebras de linha.
    return (text or "").replace("\r", " ").replace("\n", " ").strip()


def build_zpl_label(item: StockItem, size_mm: tuple[int, int]) -> str:
    """
    Gera ZPL para 100x50 ou 50x30 (203dpi).
    Campos: posição, código, PN, descrição.
    """
    pos = _zpl_escape(ellipsize(item.position, 18))
    code = _zpl_escape(ellipsize(item.code, 28))
    pn = _zpl_escape(ellipsize(item.pn, 28))
    desc = _zpl_escape(ellipsize(item.description, 60 if size_mm == (100, 50) else 30))

    if size_mm == (100, 50):
        # 100mm ~ 800 dots, 50mm ~ 400 dots @203dpi
        pw = 800
        ll = 400
        # layout: posição grande, depois cod/pn, depois desc
        return f"""^XA
^PW{pw}
^LL{ll}
^CI28
^FO20,20^A0N,60,50^FB760,1,0,C,0^FD{pos}^FS

^FO20,110^A0N,32,28^FDCOD:^FS
^FO105,110^A0N,32,28^FB655,1,0,C,0^FD{code}^FS

^FO20,155^A0N,32,28^FDPN:^FS
^FO105,155^A0N,32,28^FB655,1,0,C,0^FD{pn}^FS

^FO20,210^A0N,26,22^FB760,2,0,C,0^FD{desc}^FS

^XZ"""
    else:
        # 50mm ~ 400 dots, 30mm ~ 240 dots @203dpi
        pw = 400
        ll = 240
        return f"""^XA
^PW{pw}
^LL{ll}
^CI28
^FO10,10^A0N,36,30^FB380,1,0,C,0^FD{pos}^FS

^FO10,65^A0N,22,20^FDCOD:^FS
^FO85,65^A0N,22,20^FB300,1,0,C,0^FD{ellipsize(code, 20)}^FS

^FO10,95^A0N,22,20^FDPN:^FS
^FO85,95^A0N,22,20^FB300,1,0,C,0^FD{ellipsize(pn, 20)}^FS

^FO10,130^A0N,18,16^FB380,2,0,C,0^FD{ellipsize(desc, 40)}^FS

^XZ"""
