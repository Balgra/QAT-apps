from pathlib import Path
import json
import tkinter as tk

import pytest

from ui.tk_app import ArgentariaApp


def test_all_desktop_views_construct_on_isolated_data(tmp_path, monkeypatch):
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tk display is unavailable")
    root.withdraw()
    monkeypatch.setattr(tk, "Tk", lambda: root)
    source = Path(__file__).parents[1] / "data/accounts.json"
    target = tmp_path / "accounts.json"
    target.write_bytes(source.read_bytes())
    try:
        app = ArgentariaApp(target)
        root.withdraw()
        app.session = app.gateway.insert("4556123412341234", "1234")
        for view in [app.show_dashboard, app.show_deposit, app.show_withdraw, app.show_transfer,
                     app.show_scheduled, app.show_history, app.show_details, app.show_card_settings]:
            view()
            root.update_idletasks()
            assert app.content.winfo_children(), view.__name__
        app.eject()
        assert app.session is None
        assert any(row["action"] == "card.eject" for row in json.loads(app.activity_log.to_json())["events"])
    finally:
        root.destroy()


def test_activity_download_button_exports_after_eject_and_handles_cancel_and_errors(tmp_path, monkeypatch):
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tk display is unavailable")
    root.withdraw()
    monkeypatch.setattr(tk, "Tk", lambda: root)
    target = tmp_path / "accounts.json"
    target.write_bytes((Path(__file__).parents[1] / "data/accounts.json").read_bytes())
    messages = []
    monkeypatch.setattr("ui.tk_app.messagebox.showinfo", lambda *a, **kw: messages.append("saved"))
    monkeypatch.setattr("ui.tk_app.messagebox.showerror", lambda *a, **kw: messages.append("error"))

    def descendants(widget):
        for child in widget.winfo_children():
            yield child
            yield from descendants(child)

    def button(text):
        return next(widget for widget in descendants(root)
                    if "text" in widget.keys() and widget.cget("text") == text)

    try:
        app = ArgentariaApp(target)
        app.session = app.gateway.insert("4556123412341234", "1234")
        app.show_dashboard()
        root.geometry("900x620+10000+10000")
        root.deiconify()
        root.update()
        download = button("Download activity log")
        eject = button("Eject card")
        assert download.winfo_parent() == eject.winfo_parent()
        assert download.winfo_y() > eject.winfo_y()
        assert download.winfo_y() + download.winfo_height() <= download.master.winfo_height()
        destination = tmp_path / "activity.json"
        monkeypatch.setattr("ui.tk_app.filedialog.asksaveasfilename", lambda **kw: str(destination))
        download.invoke()
        document = json.loads(destination.read_text(encoding="utf-8"))
        assert any(row["action"] == "banking.get_balance" for row in document["events"])
        original = destination.read_bytes()
        monkeypatch.setattr("ui.tk_app.filedialog.asksaveasfilename", lambda **kw: "")
        app.download_activity_log()
        assert destination.read_bytes() == original and messages == ["saved"]
        app.eject()
        root.update()
        assert button("Download activity log").winfo_ismapped()
        monkeypatch.setattr("ui.tk_app.filedialog.asksaveasfilename", lambda **kw: str(destination))
        button("Download activity log").invoke()
        document = json.loads(destination.read_text(encoding="utf-8"))
        assert any(row["action"] == "card.eject" for row in document["events"])
        monkeypatch.setattr("ui.tk_app.filedialog.asksaveasfilename", lambda **kw: str(tmp_path))
        app.download_activity_log()
        assert messages == ["saved", "saved", "error"]
    finally:
        root.destroy()
