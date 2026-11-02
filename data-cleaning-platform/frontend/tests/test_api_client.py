"""api_client: chuyển lỗi HTTP/kết nối thành APIError với thông điệp thân thiện."""

import httpx
import pytest

import api_client


def _error(response: httpx.Response) -> api_client.APIError:
    with pytest.raises(api_client.APIError) as info:
        api_client._raise_for_response(response)
    return info.value


def test_backend_detail_is_kept_for_4xx():
    exc = _error(httpx.Response(401, json={"detail": "Thiếu token xác thực."}))
    assert exc.status_code == 401 and exc.detail == "Thiếu token xác thực."


def test_pydantic_422_is_flattened():
    body = {"detail": [{"loc": ["body", "password"], "msg": "quá ngắn"}]}
    assert _error(httpx.Response(422, json=body)).detail == "password: quá ngắn"


def test_5xx_hides_raw_body_but_keeps_technical_detail():
    exc = _error(httpx.Response(500, text="Internal Server Error"))
    assert "chưa sẵn sàng" in exc.detail
    assert exc.technical == "Internal Server Error"


def test_connection_refused_is_friendly(monkeypatch):
    monkeypatch.setattr(api_client, "MOCK", False)
    monkeypatch.setattr(api_client, "BACKEND_URL", "http://127.0.0.1:9")
    with pytest.raises(api_client.APIConnectionError) as info:
        api_client.login("a@b.co", "x")
    assert info.value.status_code == 0
    assert "Không kết nối được" in info.value.detail


def test_timeout_is_friendly(monkeypatch):
    class _Client:
        def __init__(self, *args, **kwargs): ...
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def request(self, *args, **kwargs):
            raise httpx.ReadTimeout("chậm")

    monkeypatch.setattr(api_client, "MOCK", False)
    monkeypatch.setattr(api_client.httpx, "Client", _Client)
    with pytest.raises(api_client.APIConnectionError) as info:
        api_client.get_me("t")
    assert "quá lâu" in info.value.detail
