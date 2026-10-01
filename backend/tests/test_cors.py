import pytest


@pytest.mark.asyncio
async def test_preflight_allows_all_origins_with_credentials(client):
    resp = await client.options(
        "/health",
        headers={
            "Origin": "http://app.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert 200 <= resp.status_code < 300
    assert resp.headers["access-control-allow-credentials"] == "true"
    assert resp.headers["access-control-allow-origin"] == "http://app.example.com"
