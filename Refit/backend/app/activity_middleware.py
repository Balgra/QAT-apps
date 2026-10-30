"""Observe ASGI messages without consuming, replacing, or replaying their bodies."""
import json
from time import perf_counter
from typing import Any
from urllib.parse import parse_qs

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .activity_log import ActivityLog, utc_now


MAX_BODY_BYTES = 1024 * 1024
DOWNLOAD_PATH = "/api/activity-log"


class BodyCapture:
    def __init__(self, content_type: str = "", complete: bool = False) -> None:
        self.content_type = content_type
        self.complete = complete
        self.size = 0
        self._data = bytearray()

    def append(self, message: Message) -> None:
        chunk = message.get("body", b"")
        self.size += len(chunk)
        if self.size <= MAX_BODY_BYTES:
            self._data.extend(chunk)
        else:
            self._data.clear()
        self.complete = not message.get("more_body", False)

    def snapshot(self) -> dict[str, Any]:
        result = {"content_type": self.content_type, "size_bytes": self.size,
                  "complete": self.complete, "value": None}
        if not self.complete:
            return {**result, "omitted_reason": "Body was not completely observed"}
        if self.size > MAX_BODY_BYTES:
            return {**result, "omitted_reason": "Body exceeds the 1 MiB capture limit"}
        if not self.size:
            return result
        if "json" not in self.content_type.lower():
            return {**result, "omitted_reason": "Non-JSON body omitted for safe redaction"}
        try:
            return {**result, "value": json.loads(self._data)}
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {**result, "omitted_reason": "Non-JSON body omitted for safe redaction"}


class ActivityLogMiddleware:
    def __init__(self, app: ASGIApp, activity_log: ActivityLog) -> None:
        self.app = app
        self.activity_log = activity_log

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not scope["path"].startswith("/api/"):
            await self.app(scope, receive, send)
            return
        if scope["path"].rstrip("/") == DOWNLOAD_PATH:
            await self.app(scope, receive, send)
            return
        await self._observe(scope, receive, send)

    async def _observe(self, scope: Scope, receive: Receive, send: Send) -> None:
        headers = Headers(scope=scope)
        request_body = BodyCapture(headers.get("content-type", ""), headers.get("content-length", "0") == "0")
        response_body = BodyCapture()
        started_at = utc_now()
        started = perf_counter()
        status_code = 500
        error_type = None

        async def observe_receive() -> Message:
            message = await receive()
            if message["type"] == "http.request":
                request_body.append(message)
            return message

        async def observe_send(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                response_body.content_type = Headers(raw=message["headers"]).get("content-type", "")
            if message["type"] == "http.response.body":
                response_body.append(message)
            await send(message)

        try:
            await self.app(scope, observe_receive, observe_send)
        except Exception as error:
            error_type = type(error).__name__
            raise
        finally:
            self.activity_log.record({
                "timestamp": started_at, "duration_ms": round((perf_counter() - started) * 1000, 3),
                "method": scope["method"], "path": scope["path"],
                "request": {"query": parse_qs(scope.get("query_string", b"").decode("latin-1"), keep_blank_values=True),
                            "payload": request_body.snapshot()},
                "response": {"status_code": status_code, "payload": response_body.snapshot()},
                "error_type": error_type,
            })
