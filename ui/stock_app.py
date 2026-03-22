import os
import tempfile
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from models.stock_item import StockItem
from services.excel_importer import load_stock_items_from_excel
from services.label_pdf import generate_labels_pdf
from services.file_opener import open_with_default_app
from utils.text_utils import contains, ellipsize
from services.raw_printer import send_raw_to_printer
from services.label_zpl import build_zpl_label

class StockApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Estoque + Etiquetas (MVP)")
        self.geometry("1000x650")

        self.all_items: list[StockItem] = []
        self.filtered_items: list[StockItem] = []

        self._build_ui()

    def _build_ui(self) -> None:
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        ttk.Label(
            top,
            text="Estoque (Importar Excel → Filtrar → Imprimir)",
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor="w")

        filters = ttk.LabelFrame(self, text="Filtros", padding=10)
        filters.pack(fill="x", padx=10, pady=(0, 10))

        self.var_position = tk.StringVar()
        self.var_code = tk.StringVar()
        self.var_pn = tk.StringVar()
        self.var_desc = tk.StringVar()

        row = ttk.Frame(filters)
        row.pack(fill="x")

        ttk.Label(row, text="Posição").grid(row=0, column=0, sticky="w")
        entry_position = ttk.Entry(row, textvariable=self.var_position, width=25)
        entry_position.grid(row=1, column=0, padx=(0, 10), sticky="w")

        ttk.Label(row, text="Código").grid(row=0, column=1, sticky="w")
        entry_code = ttk.Entry(row, textvariable=self.var_code, width=25)
        entry_code.grid(row=1, column=1, padx=(0, 10), sticky="w")
        
        ttk.Label(row, text="PN").grid(row=0, column=2, sticky="w")
        entry_pn = ttk.Entry(row, textvariable=self.var_pn, width=25)
        entry_pn.grid(row=1, column=2, padx=(0, 10), sticky="w")

        ttk.Label(row, text="Descrição").grid(row=0, column=3, sticky="w")
        entry_desc = ttk.Entry(row, textvariable=self.var_desc, width=35)
        entry_desc.grid(row=1, column=3, sticky="we")

        self._bind_enter_to_search(entry_position)
        self._bind_enter_to_search(entry_code)
        self._bind_enter_to_search(entry_pn)
        self._bind_enter_to_search(entry_desc)

        row.grid_columnconfigure(3, weight=1)

        actions = ttk.Frame(filters)
        actions.pack(fill="x", pady=(10, 0))

        ttk.Button(actions, text="Importar Excel", command=self.on_import_excel).pack(side="left")
        ttk.Button(actions, text="Pesquisar", command=self.apply_filters).pack(side="left", padx=8)
        ttk.Button(actions, text="Limpar filtros", command=self.clear_filters).pack(side="left")

        self.lbl_status = ttk.Label(actions, text="Nenhum arquivo importado.")
        self.lbl_status.pack(side="right")

        grid_frame = ttk.Frame(self, padding=(10, 0, 10, 10))
        grid_frame.pack(fill="both", expand=True)

        columns = ("position", "code", "pn", "description")
        self.tree = ttk.Treeview(grid_frame, columns=columns, show="headings")
        self.tree.heading("position", text="Posição")
        self.tree.heading("code", text="Código")
        self.tree.heading("pn", text="PN")
        self.tree.heading("description", text="Descrição")

        self.tree.column("position", width=120, anchor="w")
        self.tree.column("code", width=140, anchor="w")
        self.tree.column("pn", width=160, anchor="w")
        self.tree.column("description", width=500, anchor="w")

        vsb = ttk.Scrollbar(grid_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=vsb.set)

        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        bottom = ttk.LabelFrame(self, text="Impressão (fallback PDF)", padding=10)
        bottom.pack(fill="x", padx=10, pady=(0, 10))

        ttk.Label(bottom, text="Tamanho").pack(side="left")
        self.var_size = tk.StringVar(value="100x50")
        ttk.Combobox(bottom, textvariable=self.var_size, values=["100x50", "50x30"], width=8, state="readonly").pack(side="left", padx=6)

        ttk.Label(bottom, text="Quantidade").pack(side="left", padx=(10, 0))
        self.var_qty = tk.StringVar(value="1")
        ttk.Entry(bottom, textvariable=self.var_qty, width=6).pack(side="left", padx=6)

        ttk.Button(bottom, text="Gerar PDF", command=self.on_print_pdf).pack(side="left", padx=10)

        ttk.Label(bottom, text="Impressora (Windows)").pack(side="left", padx=(20, 0))
        self.var_printer = tk.StringVar(value="VZPL_port_Douglas")  # ajuste depois
        ttk.Entry(bottom, textvariable=self.var_printer, width=30).pack(side="left", padx=6)

        ttk.Button(bottom, text="Imprimir (ZPL)", command=self.on_print_zpl).pack(side="left", padx=10)

        ttk.Label(bottom, text="Selecione um item no grid.").pack(side="left", padx=10)

    def on_import_excel(self) -> None:
        path = filedialog.askopenfilename(
            title="Selecionar planilha Excel",
            filetypes=[("Excel", "*.xlsx *.xlsm"), ("Todos", "*.*")]
        )
        if not path:
            return

        try:
            self.all_items = load_stock_items_from_excel(path)
        except Exception as e:
            messagebox.showerror("Erro ao importar", str(e))
            return

        self.apply_filters()
        self.lbl_status.config(text=f"Importado: {len(self.all_items)} itens.")

    def clear_filters(self) -> None:
        self.var_position.set("")
        self.var_code.set("")
        self.var_pn.set("")
        self.var_desc.set("")
        self.apply_filters()

    def _bind_enter_to_search(self, widget: tk.Widget) -> None:
        widget.bind("<Return>", lambda event: self.apply_filters())

    def apply_filters(self) -> None:
        pos_q = self.var_position.get()
        code_q = self.var_code.get()
        pn_q = self.var_pn.get()
        desc_q = self.var_desc.get()

        self.filtered_items = [
            it for it in self.all_items
            if contains(it.position, pos_q)
            and contains(it.code, code_q)
            and contains(it.pn, pn_q)
            and contains(it.description, desc_q)
        ]

        self._refresh_grid()
        self.lbl_status.config(text=f"Mostrando: {len(self.filtered_items)} / {len(self.all_items)} itens.")

    def _refresh_grid(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for it in self.filtered_items:
            self.tree.insert("", "end", values=(it.position, it.code, it.pn, ellipsize(it.description, 80)))

    def _get_selected_item(self) -> StockItem | None:
        sel = self.tree.selection()
        if not sel:
            return None

        pos, code, pn, _ = self.tree.item(sel[0], "values")
        for it in self.filtered_items:
            if it.position == pos and it.code == code and it.pn == pn:
                return it
        return None

    def on_print_pdf(self) -> None:
        item = self._get_selected_item()
        if not item:
            messagebox.showwarning("Atenção", "Selecione um item no grid primeiro.")
            return

        try:
            quantity = int(self.var_qty.get().strip())
            if quantity < 1:
                raise ValueError()
        except Exception:
            messagebox.showerror("Quantidade inválida", "Quantidade deve ser um número inteiro >= 1.")
            return

        label_size = (100, 50) if self.var_size.get() == "100x50" else (50, 30)

        try:
            tmp_dir = tempfile.gettempdir()
            safe_code = "".join(ch for ch in item.code if ch.isalnum() or ch in ("-", "_"))[:20] or "item"
            pdf_path = os.path.join(tmp_dir, f"etiquetas_{safe_code}_{label_size[0]}x{label_size[1]}.pdf")

            generate_labels_pdf(pdf_path, label_size_mm=label_size, item=item, quantity=quantity)
            open_with_default_app(pdf_path)

            messagebox.showinfo(
                "PDF gerado",
                f"Arquivo:\n{pdf_path}\n\n"
                "Abra o PDF e imprima.\n"
                "IMPORTANTE: escala 100% (não ajustar à página)."
            )
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def on_print_zpl(self) -> None:
        item = self._get_selected_item()
        if not item:
            messagebox.showwarning("Atenção", "Selecione um item no grid primeiro.")
            return

        try:
            quantity = int(self.var_qty.get().strip())
            if quantity < 1:
                raise ValueError()
        except Exception:
            messagebox.showerror("Quantidade inválida", "Quantidade deve ser um número inteiro >= 1.")
            return

        label_size = (100, 50) if self.var_size.get() == "100x50" else (50, 30)
        printer_name = self.var_printer.get().strip()
        if not printer_name:
            messagebox.showerror("Impressora", "Informe o nome da impressora do Windows.")
            return

        try:
            zpl = build_zpl_label(item, label_size)
            payload = (zpl + "\n").encode("utf-8")

            for i in range(quantity):
                send_raw_to_printer(printer_name, payload, job_name=f"Etiqueta {item.code} ({i+1}/{quantity})")

            messagebox.showinfo("OK", f"Enviei {quantity} etiqueta(s) via ZPL para:\n{printer_name}")
        except Exception as e:
            messagebox.showerror("Erro ao imprimir (ZPL)", str(e))