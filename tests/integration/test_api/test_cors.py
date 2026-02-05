"""Integration tests for CORS middleware configuration."""


def test_allowed_origin_gets_cors_headers(api_client):
    """Requests from an allowed origin should include CORS headers."""
    response = api_client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_unknown_origin_no_cors_headers(api_client):
    """Requests from an unknown origin should not include CORS allow-origin."""
    response = api_client.options(
        "/health",
        headers={
            "Origin": "http://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers.get("access-control-allow-origin") != "http://evil.example.com"
