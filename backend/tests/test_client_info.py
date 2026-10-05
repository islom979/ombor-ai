from app.core.audit_middleware import parse_body, redact
from app.core.client_info import extract_client_info

VERCEL_HEADERS = {
    "x-real-ip": "213.230.100.7",
    "x-forwarded-for": "213.230.100.7, 76.76.21.21",
    "x-vercel-ip-country": "UZ",
    "x-vercel-ip-country-region": "TK",
    "x-vercel-ip-city": "Tashkent",
    "x-vercel-ip-latitude": "41.2995",
    "x-vercel-ip-longitude": "69.2401",
    "x-vercel-id": "bom1::abc",
    "user-agent": "Mozilla/5.0",
}


def test_trusted_proxy_headers_give_ip_and_location() -> None:
    info = extract_client_info(VERCEL_HEADERS, "10.0.0.1", trust_proxy=True)
    assert info.ip == "213.230.100.7"
    assert (info.country, info.region, info.city) == ("UZ", "TK", "Tashkent")
    assert (info.latitude, info.longitude) == (41.2995, 69.2401)
    assert info.request_id == "bom1::abc" and info.user_agent == "Mozilla/5.0"


def test_untrusted_proxy_headers_are_ignored() -> None:
    # Ishonilmagan muhitda mijoz o'z IP/shahrini soxtalashtira olmasligi kerak.
    info = extract_client_info(VERCEL_HEADERS, "10.0.0.1", trust_proxy=False)
    assert info.ip == "10.0.0.1"
    assert info.country is None and info.city is None and info.latitude is None


def test_falls_back_to_forwarded_for_then_peer() -> None:
    assert extract_client_info({"x-forwarded-for": "1.2.3.4, 5.6.7.8"}, None, trust_proxy=True).ip == "1.2.3.4"
    assert extract_client_info({}, "9.9.9.9", trust_proxy=True).ip == "9.9.9.9"


def test_garbage_values_do_not_break_parsing() -> None:
    info = extract_client_info(
        {"x-real-ip": "not-an-ip", "x-vercel-ip-latitude": "north", "x-vercel-ip-city": "S%C3%A3o%20Paulo"},
        "bad",
        trust_proxy=True,
    )
    assert info.ip is None and info.latitude is None
    assert info.city == "São Paulo"  # Vercel shahar nomini URL-kodlangan holda yuboradi


def test_ipv6_is_normalised() -> None:
    assert extract_client_info({"x-real-ip": "2001:DB8::0001"}, None, trust_proxy=True).ip == "2001:db8::1"


def test_redact_hides_secrets_recursively() -> None:
    body = {"name": "x", "password": "p", "nested": [{"api_key": "k", "ok": 1}], "Token": "t"}
    assert redact(body) == {"name": "x", "password": "***", "nested": [{"api_key": "***", "ok": 1}], "Token": "***"}


def test_parse_body_limits() -> None:
    assert parse_body(b"") is None
    assert parse_body(b'{"a": 1}') == {"a": 1}
    assert parse_body(b"not json") == {"raw": "not json"}
    assert parse_body(b"x" * 9000) == {"truncated": True, "size": 9000}


def test_path_template_replaces_param_values() -> None:
    from app.core.audit_middleware import path_template

    assert path_template("/api/v1/products/abc-1", {"product_id": "abc-1"}) == "/api/v1/products/{product_id}"
    assert path_template("/api/v1/stock", {}) == "/api/v1/stock"
