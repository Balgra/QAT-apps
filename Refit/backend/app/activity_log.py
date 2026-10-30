"""Per-run API activity snapshots, independent of the commerce implementation."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from math import isfinite
from threading import Lock
from typing import Any
from uuid import uuid4


REDACTED = "[REDACTED]"
SENSITIVE_FIELDS = frozenset({
    "card", "cardnumber", "cvv", "cvc", "expiry", "pin", "oldpin", "newpin",
    "password", "authorization", "cookie", "setcookie", "token", "accesstoken",
    "refreshtoken", "input",
})


def redact(value: Any) -> Any:
    """Copy JSON data while removing credentials, including validation-error inputs."""
    if isinstance(value, dict):
        return _redact_mapping(value)
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    if isinstance(value, float) and not isfinite(value):
        return str(value)
    return value


def _redact_mapping(values: dict[str, Any]) -> dict[str, Any]:
    result = {}
    for key, item in values.items():
        name = str(key).lower().replace("_", "").replace("-", "")
        result[key] = REDACTED if name in SENSITIVE_FIELDS else redact(item)
    return result


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ActivityLog:
    def __init__(self) -> None:
        self.session_id = uuid4().hex
        self.started_at = utc_now()
        self._events: list[dict[str, Any]] = []
        self._lock = Lock()

    def record(self, event: dict[str, Any]) -> None:
        safe_event = redact(event)
        with self._lock:
            self._events.append({"sequence": len(self._events) + 1, **safe_event})

    def to_json(self) -> str:
        with self._lock:
            events = deepcopy(self._events)
        return json.dumps({
            "schema_version": 1, "application": "Refit", "session_id": self.session_id,
            "started_at": self.started_at, "exported_at": utc_now(), "events": events,
        }, ensure_ascii=False, indent=2, allow_nan=False)
