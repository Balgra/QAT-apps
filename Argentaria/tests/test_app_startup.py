import json
from pathlib import Path
from types import SimpleNamespace
import sys

import app


def test_each_launch_restores_accounts_without_changing_supplied_data(tmp_path, monkeypatch):
    template = tmp_path / "accounts.json"
    source = Path(__file__).parents[1] / "data" / "accounts.json"
    template.write_bytes(source.read_bytes())
    original = template.read_bytes()
    monkeypatch.setattr(app, "DEFAULT_DATA_FILE", template)
    paths = []

    class DemoWindow:
        def __init__(self, data_file):
            self.data_file = data_file
            paths.append(data_file)

        def run(self):
            rows = json.loads(self.data_file.read_text(encoding="utf-8"))
            assert rows == json.loads(original)
            rows[0]["balance"] = 0
            rows[0]["card"]["pin"] = "0000"
            rows[0]["card"]["status"] = "blocked"
            self.data_file.write_text(json.dumps(rows), encoding="utf-8")

    monkeypatch.setitem(sys.modules, "ui.tk_app", SimpleNamespace(ArgentariaApp=DemoWindow))
    app.main()
    app.main()
    assert len(paths) == 2 and paths[0] != paths[1]
    assert all(not path.exists() for path in paths)
    assert template.read_bytes() == original
