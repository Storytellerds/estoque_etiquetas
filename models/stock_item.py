from dataclasses import dataclass

@dataclass
class StockItem:
    position: str
    code: str
    pn: str
    description: str