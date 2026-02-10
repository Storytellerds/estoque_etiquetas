import os

def open_with_default_app(path: str) -> None:
    # Windows
    os.startfile(path)