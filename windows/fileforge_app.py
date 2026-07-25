"""FileForge for Windows 11 — desktop GUI (packaged as FileForge.exe).

A dependency-free Tkinter shell over :class:`fileforge_core.Controller`, which
in turn builds on the FileForge 2.0 discovery/suggestion layer. Features:

- Directory browser
- File-type summary for the chosen folder
- Conversion-suggestion panel (ranked, engine-aware)
- Conversion execution with a progress bar (off the UI thread)
- History / logging view

Run from source:   python windows/fileforge_app.py
Build the .exe:     windows/build_windows.ps1
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path

# When run from source (not the frozen exe), make ``src/`` importable.
if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from fileforge_core import ConversionResult, Controller


APP_TITLE = "FileForge 2.0"


class FileForgeApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.ctl = Controller()
        self._pending_route: tuple[str, str] | None = None

        root.title(APP_TITLE)
        root.geometry("760x560")
        root.minsize(680, 500)

        self._build_toolbar()
        self._build_body()
        self._build_statusbar()

    # -- layout ------------------------------------------------------------- #

    def _build_toolbar(self) -> None:
        bar = ttk.Frame(self.root, padding=(12, 10))
        bar.pack(fill="x")
        ttk.Label(bar, text=APP_TITLE, font=("Segoe UI", 14, "bold")).pack(side="left")
        ttk.Button(bar, text="Choose folder…", command=self.pick_folder).pack(side="right")
        self.recursive_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            bar, text="Recursive", variable=self.recursive_var, command=self._rescan
        ).pack(side="right", padx=8)

    def _build_body(self) -> None:
        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=12, pady=6)

        # --- Convert tab (summary + suggestions + run) --------------------- #
        convert = ttk.Frame(nb, padding=8)
        nb.add(convert, text="Convert")

        panes = ttk.Panedwindow(convert, orient="horizontal")
        panes.pack(fill="both", expand=True)

        # Left: file-type summary.
        left = ttk.Labelframe(panes, text="File types", padding=6)
        self.summary_tree = ttk.Treeview(
            left, columns=("count",), show="tree headings", height=12
        )
        self.summary_tree.heading("#0", text="Extension")
        self.summary_tree.heading("count", text="Count")
        self.summary_tree.column("#0", width=120)
        self.summary_tree.column("count", width=60, anchor="e")
        self.summary_tree.pack(fill="both", expand=True)
        panes.add(left, weight=1)

        # Right: suggestions.
        right = ttk.Labelframe(panes, text="Suggested conversions", padding=6)
        self.sugg_tree = ttk.Treeview(
            right, columns=("count", "tier"), show="tree headings", height=12
        )
        self.sugg_tree.heading("#0", text="Route")
        self.sugg_tree.heading("count", text="Files")
        self.sugg_tree.heading("tier", text="Tier")
        self.sugg_tree.column("#0", width=160)
        self.sugg_tree.column("count", width=50, anchor="e")
        self.sugg_tree.column("tier", width=80, anchor="center")
        self.sugg_tree.pack(fill="both", expand=True)
        self.sugg_tree.bind("<<TreeviewSelect>>", self._on_pick_suggestion)
        panes.add(right, weight=1)

        # Run row.
        run_row = ttk.Frame(convert, padding=(0, 8))
        run_row.pack(fill="x")
        self.route_label = ttk.Label(run_row, text="Select a suggestion to convert")
        self.route_label.pack(side="left")
        self.run_btn = ttk.Button(run_row, text="Convert", command=self.run_selected, state="disabled")
        self.run_btn.pack(side="right")
        self.progress = ttk.Progressbar(convert, mode="determinate")
        self.progress.pack(fill="x", pady=(4, 0))

        # --- History tab --------------------------------------------------- #
        history = ttk.Frame(nb, padding=8)
        nb.add(history, text="History")
        self.history_tree = ttk.Treeview(
            history, columns=("ts", "result"), show="tree headings"
        )
        self.history_tree.heading("#0", text="Conversion")
        self.history_tree.heading("ts", text="When")
        self.history_tree.heading("result", text="Result")
        self.history_tree.column("#0", width=380)
        self.history_tree.column("ts", width=150)
        self.history_tree.column("result", width=90, anchor="center")
        self.history_tree.pack(fill="both", expand=True)
        hrow = ttk.Frame(history, padding=(0, 6))
        hrow.pack(fill="x")
        ttk.Button(hrow, text="Refresh", command=self._refresh_history).pack(side="left")
        ttk.Button(hrow, text="Clear", command=self._clear_history).pack(side="left", padx=6)

    def _build_statusbar(self) -> None:
        self.status = ttk.Label(self.root, text="Choose a folder to begin.", relief="sunken", anchor="w")
        self.status.pack(fill="x", side="bottom")

    # -- actions ------------------------------------------------------------ #

    def pick_folder(self) -> None:
        path = filedialog.askdirectory()
        if not path:
            return
        self.ctl.set_directory(path, recursive=self.recursive_var.get())
        self._refresh_summary()
        self._refresh_suggestions()
        self.status.config(text=f"{path} — {self.ctl.scan.total_files} files")

    def _rescan(self) -> None:
        if self.ctl.directory:
            self.ctl.set_directory(self.ctl.directory, recursive=self.recursive_var.get())
            self._refresh_summary()
            self._refresh_suggestions()

    def _refresh_summary(self) -> None:
        self.summary_tree.delete(*self.summary_tree.get_children())
        for row in self.ctl.file_type_summary():
            self.summary_tree.insert("", "end", text=f".{row.ext}", values=(row.count,))

    def _refresh_suggestions(self) -> None:
        self.sugg_tree.delete(*self.sugg_tree.get_children())
        for s in self.ctl.suggestions():
            route = f"{s.source_ext} → {s.target_ext}"
            tier = s.tier if s.supported else "generic"
            iid = f"{s.source_ext}>{s.target_ext}"
            tag = "supported" if s.supported else "generic"
            self.sugg_tree.insert(
                "", "end", iid=iid, text=route, values=(s.count, tier), tags=(tag,)
            )
        self.sugg_tree.tag_configure("generic", foreground="#888")

    def _on_pick_suggestion(self, _event=None) -> None:
        sel = self.sugg_tree.selection()
        if not sel:
            return
        src, tgt = sel[0].split(">")
        supported = "generic" not in self.sugg_tree.item(sel[0], "tags")
        self._pending_route = (src, tgt)
        n = len(self.ctl.plan(src, tgt, recursive=self.recursive_var.get()))
        if supported:
            self.route_label.config(text=f"{src} → {tgt}  ({n} file(s))")
            self.run_btn.config(state="normal" if n else "disabled")
        else:
            self.route_label.config(text=f"{src} → {tgt} is a generic suggestion (no engine route)")
            self.run_btn.config(state="disabled")

    def run_selected(self) -> None:
        if not self._pending_route:
            return
        src, tgt = self._pending_route
        recursive = self.recursive_var.get()
        plan = self.ctl.plan(src, tgt, recursive=recursive)
        if not plan:
            messagebox.showinfo(APP_TITLE, "Nothing to convert.")
            return
        self.run_btn.config(state="disabled")
        self.progress.config(maximum=len(plan), value=0)

        def worker() -> None:
            def progress(done: int, total: int, res: ConversionResult) -> None:
                self.root.after(0, self._on_progress, done, total, res)

            results = self.ctl.run_plan(src, tgt, recursive=recursive, on_progress=progress)
            self.root.after(0, self._on_done, results)

        threading.Thread(target=worker, daemon=True).start()

    def _on_progress(self, done: int, total: int, res: ConversionResult) -> None:
        self.progress.config(value=done)
        mark = "ok" if res.ok else "ERR"
        self.status.config(text=f"[{done}/{total}] {mark}: {Path(res.source).name}")

    def _on_done(self, results) -> None:
        ok = sum(1 for r in results if r.ok)
        fail = len(results) - ok
        self.status.config(text=f"Done — {ok} ok, {fail} failed.")
        self.run_btn.config(state="normal")
        self._refresh_history()
        if fail:
            messagebox.showwarning(APP_TITLE, f"{fail} file(s) failed. See History for details.")

    def _refresh_history(self) -> None:
        self.history_tree.delete(*self.history_tree.get_children())
        for entry in reversed(self.ctl.history(limit=200)):
            label = f"{Path(entry['source']).name} → {Path(entry['target']).name}"
            result = "ok" if entry.get("ok") else "ERR"
            self.history_tree.insert("", "end", text=label, values=(entry.get("ts", ""), result))

    def _clear_history(self) -> None:
        if messagebox.askyesno(APP_TITLE, "Clear conversion history?"):
            self.ctl.clear_history()
            self._refresh_history()


def main() -> int:
    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista")  # native look on Windows; ignored elsewhere
    except tk.TclError:
        pass
    FileForgeApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
