"""FileForge Desktop GUI (monetization strategy #6).

A dependency-free reference GUI built on Tkinter (ships with Python) so it
runs on Windows, macOS, and Linux without a toolkit install. The commercial
Pro build swaps this for a PyQt/Electron shell with real drag-and-drop, but
the conversion path is identical — it calls the same shared registry.

Run:  python desktop/fileforge_gui.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from fileforge.core.registry import ConversionError, load_builtin_converters, registry
from fileforge.licensing import current_license


class ConverterApp:
    def __init__(self, root: tk.Tk) -> None:
        load_builtin_converters()
        self.root = root
        self.source: Path | None = None
        root.title("FileForge Converter")
        root.geometry("520x300")

        lic = current_license()
        ttk.Label(root, text=f"Tier: {lic.name}", foreground="#0a7").pack(anchor="e", padx=10, pady=4)

        ttk.Button(root, text="Choose file…", command=self.pick).pack(pady=8)
        self.file_label = ttk.Label(root, text="No file selected")
        self.file_label.pack()

        row = ttk.Frame(root)
        row.pack(pady=12)
        ttk.Label(row, text="Convert to:").pack(side="left", padx=6)
        self.target_var = tk.StringVar()
        self.target_menu = ttk.Combobox(row, textvariable=self.target_var, state="readonly", width=12)
        self.target_menu.pack(side="left")

        ttk.Button(root, text="Convert", command=self.convert).pack(pady=10)
        self.status = ttk.Label(root, text="", wraplength=480)
        self.status.pack(pady=6)

    def pick(self) -> None:
        path = filedialog.askopenfilename()
        if not path:
            return
        self.source = Path(path)
        self.file_label.config(text=self.source.name)
        src_ext = self.source.suffix.lstrip(".").lower()
        targets = registry.targets_for(src_ext)
        self.target_menu["values"] = targets
        if targets:
            self.target_var.set(targets[0])
            self.status.config(text=f"{len(targets)} output format(s) available")
        else:
            self.status.config(text=f"No conversions available for .{src_ext}")

    def convert(self) -> None:
        if not self.source or not self.target_var.get():
            messagebox.showwarning("FileForge", "Pick a file and a target format first.")
            return
        tgt_ext = self.target_var.get()
        conv = registry.get(self.source.suffix.lstrip(".").lower(), tgt_ext)
        out = self.source.with_suffix(f".{tgt_ext}")
        try:
            conv.fn(self.source, out)
        except ConversionError as exc:
            messagebox.showerror("FileForge", str(exc))
            return
        self.status.config(text=f"Saved: {out}")
        messagebox.showinfo("FileForge", f"Converted to:\n{out}")


def main() -> None:
    root = tk.Tk()
    ConverterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
