from concurrent.futures import ThreadPoolExecutor
import json

from fastapi import Request
from fastapi.testclient import TestClient
import pytest
from starlette.responses import PlainTextResponse, StreamingResponse

from app.activity_log import ActivityLog, REDACTED
from app.activity_middleware import BodyCapture, MAX_BODY_BYTES
from test_commerce import payload, shop


def events(client):
    response = client.get("/api/activity-log")
    assert response.status_code == 200
    assert response.headers["content-disposition"] == 'attachment; filename="refit-activity-log.json"'
    assert response.headers["cache-control"] == "no-store"
    return response.json()["events"]


def test_download_is_a_snapshot_and_does_not_log_itself_or_change_state(shop):
    client, _, _, path = shop
    original = path.read_bytes()
    assert events(client) == events(client) == []
    response = client.get("/api/products", params={"category": "tops", "q": "sweater"})
    record = events(client)[0]
    assert record["method"] == "GET" and record["path"] == "/api/products"
    assert record["request"]["query"] == {"category": ["tops"], "q": ["sweater"]}
    assert record["response"]["payload"]["value"] == response.json()
    assert record["response"]["status_code"] == 200
    assert record["duration_ms"] >= 0
    assert len(events(client)) == 1
    assert path.read_bytes() == original


def test_checkout_records_wire_values_and_redacts_credentials_and_validation_inputs(shop):
    client = shop[0]
    body = payload(customer_name="Åsa", coupon_code="WELCOME10")
    purchase = client.post("/api/checkout", json=body, headers={"Authorization": "Bearer private-token"})
    assert purchase.status_code == 200
    bad = client.post("/api/checkout", json=payload(card_number="411111111111"))
    assert bad.status_code == 422
    records = events(client)
    incoming = records[0]["request"]["payload"]["value"]
    assert incoming["customer_name"] == "Åsa"
    assert incoming["items"] == body["items"]
    assert incoming["card_number"] == incoming["cvv"] == incoming["expiry"] == REDACTED
    assert records[0]["response"]["payload"]["value"] == purchase.json()
    assert records[1]["response"]["status_code"] == 422
    assert records[1]["response"]["payload"]["value"]["detail"][0]["input"] == REDACTED
    exported = client.get("/api/activity-log").text
    for secret in ["4242424242424242", "411111111111", "private-token", '"cvv": "123"', "12/35"]:
        assert secret not in exported


def test_malformed_json_and_non_json_bodies_are_not_exposed(shop):
    client, app, _, _ = shop

    @app.get("/api/plain")
    def plain():
        return PlainTextResponse("private-token")

    response = client.post("/api/checkout", content='{"card_number":"4242424242424242",broken',
                           headers={"Content-Type": "application/json"})
    assert response.status_code == 422
    assert client.get("/api/plain").text == "private-token"
    records = events(client)
    assert records[0]["request"]["payload"]["value"] is None
    assert "omitted_reason" in records[0]["request"]["payload"]
    assert records[1]["response"]["payload"]["value"] is None
    exported = client.get("/api/activity-log").text
    assert "4242424242424242" not in exported and "private-token" not in exported


def test_error_and_empty_responses_are_logged_without_changing_http_behavior(shop):
    client, app, _, _ = shop

    @app.get("/api/broken")
    def broken():
        raise RuntimeError("private exception context")

    assert client.get("/api/products/99999").status_code == 404
    assert client.delete("/api/products/20").status_code == 204
    with TestClient(app, raise_server_exceptions=False) as tolerant:
        assert tolerant.get("/api/broken").status_code == 500
    records = events(client)
    assert [record["response"]["status_code"] for record in records] == [404, 204, 500]
    assert records[1]["response"]["payload"]["value"] is None
    assert records[2]["error_type"] == "RuntimeError"
    assert "private exception context" not in client.get("/api/activity-log").text


def test_streamed_json_and_query_secrets_are_captured_without_altering_response(shop):
    client, app, _, _ = shop

    @app.get("/api/stream")
    def stream():
        return StreamingResponse(iter([b'{"items":', b'[1,2]}']), status_code=202, media_type="application/json")

    response = client.get("/api/stream?token=secret-token&tag=a&tag=b")
    assert response.status_code == 202 and response.json() == {"items": [1, 2]}
    record = events(client)[0]
    assert record["request"]["query"] == {"token": REDACTED, "tag": ["a", "b"]}
    assert record["response"]["payload"]["value"] == response.json()
    assert record["response"]["payload"]["complete"] is True


def test_concurrent_calls_are_recorded_once_and_each_app_has_its_own_log(shop, tmp_path):
    client = shop[0]
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(lambda _: client.get("/api/products/2"), range(12)))
    assert all(response.status_code == 200 for response in responses)
    records = events(client)
    assert [record["sequence"] for record in records] == list(range(1, 13))
    from app.main import create_app
    from test_api import make_client
    assert events(make_client(tmp_path)) == []
    with TestClient(create_app()) as fresh:
        assert events(fresh) == []


@pytest.mark.parametrize("size", [MAX_BODY_BYTES - 1, MAX_BODY_BYTES, MAX_BODY_BYTES + 1])
def test_body_capture_limit_is_explicit(size):
    capture = BodyCapture("application/json")
    body = json.dumps("a" * (size - 2)).encode()
    capture.append({"body": body[:size // 2], "more_body": True})
    capture.append({"body": body[size // 2:], "more_body": False})
    result = capture.snapshot()
    assert result["size_bytes"] == size and result["complete"] is True
    if size <= MAX_BODY_BYTES:
        assert result["value"] == "a" * (size - 2)
    else:
        assert result["value"] is None and "limit" in result["omitted_reason"]


def test_large_api_bodies_are_forwarded_completely_but_not_stored_in_log(shop):
    client, app, _, _ = shop

    @app.post("/api/echo")
    async def echo(request: Request):
        return await request.json()

    body = {"description": "a" * MAX_BODY_BYTES}
    response = client.post("/api/echo", json=body)
    assert response.status_code == 200 and response.json() == body
    record = events(client)[0]
    for direction in ["request", "response"]:
        captured = record[direction]["payload"]
        assert captured["value"] is None and captured["size_bytes"] > MAX_BODY_BYTES


def test_partial_body_snapshot_is_explicit():
    capture = BodyCapture("application/json")
    capture.append({"body": b'{"pin":"1234"', "more_body": True})
    assert capture.snapshot()["complete"] is False
    assert capture.snapshot()["value"] is None


def test_export_is_valid_json_for_nonfinite_inputs_and_redacts_nested_fields():
    activity = ActivityLog()
    request = {"amount": float("nan"), "values": [float("inf")],
               "payment": {"cardNumber": "4242424242424242"}, "nested": [{"pin": "1234"}]}
    activity.record({"request": request})
    request["payment"]["cardNumber"] = "changed after recording"
    exported = activity.to_json()
    row = json.loads(exported)["events"][0]["request"]
    assert row["amount"] == "nan" and row["values"] == ["inf"]
    assert row["payment"]["cardNumber"] == row["nested"][0]["pin"] == REDACTED
    assert "4242424242424242" not in exported and "changed after recording" not in exported
