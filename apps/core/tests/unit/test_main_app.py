import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest_asyncio.fixture()
async def main_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


class TestMainApp:
    async def test_root_route_returns_200(self, main_client):
        # Arrange / Act
        response = await main_client.get("/")

        # Assert
        assert response.status_code == 200

    async def test_login_page_route_returns_200(self, main_client):
        # Arrange / Act
        response = await main_client.get("/login")

        # Assert
        assert response.status_code == 200
