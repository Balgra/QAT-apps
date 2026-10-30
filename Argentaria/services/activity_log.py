"""Small, per-run activity recorder used by the desktop and service boundaries."""
from copy import deepcopy
from datetime import datetime, timezone
from functools import wraps
from inspect import signature
import json
from math import isfinite
import os
from pathlib import Path
import tempfile
from threading import Lock
from time import perf_counter
from typing import Any, Callable, TypeVar, cast
from uuid import uuid4


REDACTED = "[REDACTED]"
SENSITIVE_FIELDS = frozenset({"pin", "oldpin", "newpin", "cardnumber", "password", "token"})
F = TypeVar("F", bound=Callable[..., Any])


def snapshot(value: Any) -> Any:
    """Create detached, serializable values without traversing private domain state."""
    if isinstance(value, dict):
        return _snapshot_mapping(value)
    if isinstance(value, (list, tuple)):
        return [snapshot(item) for item in value]
    if isinstance(value, float) and not isfinite(value):
        return str(value)
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    return {"type": type(value).__name__}


def _snapshot_mapping(values: dict[str, Any]) -> dict[str, Any]:
    result = {}
    for key, item in values.items():
        name = str(key).lower().replace("_", "").replace("-", "")
        result[str(key)] = REDACTED if name in SENSITIVE_FIELDS else snapshot(item)
    return result


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ActivityLog:
    def __init__(self) -> None:
        self.session_id = uuid4().hex
        self.started_at = utc_now()
        self._events: list[dict[str, Any]] = []
        self._lock = Lock()

    def record(self, action: str, request: Any = None, response: Any = None,
               error: dict[str, str] | None = None, duration_ms: float = 0) -> None:
        event = {"timestamp": utc_now(), "action": action, "request": snapshot(request),
                 "response": snapshot(response), "error": snapshot(error), "duration_ms": duration_ms}
        with self._lock:
            self._events.append({"sequence": len(self._events) + 1, **event})

    def to_json(self) -> str:
        with self._lock:
            events = deepcopy(self._events)
        return json.dumps({
            "schema_version": 1, "application": "Argentaria", "session_id": self.session_id,
            "started_at": self.started_at, "exported_at": utc_now(), "events": events,
        }, ensure_ascii=False, indent=2, allow_nan=False)

    def export(self, path: Path) -> None:
        document = self.to_json()
        descriptor, temporary = tempfile.mkstemp(prefix=".activity-log-", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as output:
                output.write(document)
            os.replace(temporary, path)
        finally:
            Path(temporary).unlink(missing_ok=True)


def record_activity(action: str) -> Callable[[F], F]:
    """Observe public service calls while preserving their signature and exceptions."""
    def decorate(method: F) -> F:
        parameters = signature(method)

        @wraps(method)
        def wrapped(self: Any, *args: Any, **kwargs: Any) -> Any:
            activity_log = self.activity_log
            if activity_log is None:
                return method(self, *args, **kwargs)
            bound = parameters.bind(self, *args, **kwargs)
            bound.apply_defaults()
            request = snapshot({key: value for key, value in bound.arguments.items() if key != "self"})
            started = perf_counter()
            try:
                result = method(self, *args, **kwargs)
            except Exception as error:
                activity_log.record(action, request, error={"type": type(error).__name__, "message": str(error)},
                                    duration_ms=round((perf_counter() - started) * 1000, 3))
                raise
            activity_log.record(action, request, response=result,
                                duration_ms=round((perf_counter() - started) * 1000, 3))
            return result

        return cast(F, wrapped)

    return decorate
