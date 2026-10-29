from pathlib import Path
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
    finally:
        root.destroy()
