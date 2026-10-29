from __future__ import annotations

import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from threading import RLock


class StateStore:
    """One process, one state file, one atomic replacement per business operation."""

    def __init__(self, path: Path):
        self.path = path
        self.lock = RLock()

    def read(self) -> dict:
        with self.lock:
            state = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(state, list):
                state = {"products": state}
            for key, default in {"orders": {}, "reservations": {}, "moderation": {}, "profiles": {
                "ada@example.com": {"points": 600, "first_order": True},
                "member@refit.example": {"points": 1200, "first_order": False},
            }, "sellers": {}}.items():
                state.setdefault(key, default)
            return state

    def commit(self, state: dict) -> None:
        descriptor, name = tempfile.mkstemp(prefix="refit-", suffix=".tmp", dir=self.path.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as output:
                json.dump(state, output, ensure_ascii=False, indent=2, allow_nan=False)
                output.flush()
                os.fsync(output.fileno())
            os.replace(name, self.path)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    @contextmanager
    def transaction(self):
        with self.lock:
            state = self.read()
            yield state
            self.commit(state)
