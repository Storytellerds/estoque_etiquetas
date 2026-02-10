import win32print


def send_raw_to_printer(printer_name: str, raw_data: bytes, job_name: str = "ZPL Job") -> None:
    """
    Envia bytes como RAW para a fila da impressora no Windows.
    Funciona para impressora local USB e também compartilhada (\\PC\\Impressora).
    """
    handle = win32print.OpenPrinter(printer_name)
    try:
        # ("JobName", outputFile, "RAW")
        job = win32print.StartDocPrinter(handle, 1, (job_name, None, "RAW"))
        try:
            win32print.StartPagePrinter(handle)
            win32print.WritePrinter(handle, raw_data)
            win32print.EndPagePrinter(handle)
        finally:
            win32print.EndDocPrinter(handle)
    finally:
        win32print.ClosePrinter(handle)
