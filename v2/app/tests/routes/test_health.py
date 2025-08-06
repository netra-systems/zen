import pytest
from httpx import AsyncClient

# Mark the test as asynchronous
@pytest.mark.asyncio
async def test_health_live(client: AsyncClient):
    """
    Tests the /health/live endpoint to ensure it returns a 200 OK response.
    """
    response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_health_ready(client: AsyncClient):
    """
    Tests the /health/ready endpoint to ensure it returns a 200 OK response.
    """
    response = await client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}