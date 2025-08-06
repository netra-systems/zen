import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app

client = TestClient(app)

@pytest.mark.asyncio
@patch('app.routes.generation.get_clickhouse_client')
async def test_list_clickhouse_tables_success(mock_get_clickhouse_client):
    """Test that the /clickhouse_tables endpoint returns a list of tables."""
    mock_client = MagicMock()
    mock_client.execute_query.return_value = [{'name': 'table1'}, {'name': 'table2'}]

    mock_async_context_manager = MagicMock()
    mock_async_context_manager.__aenter__.return_value = mock_client
    mock_get_clickhouse_client.return_value = mock_async_context_manager

    response = client.get("/api/v3/generation/clickhouse_tables")
    assert response.status_code == 200
    assert response.json() == ['table1', 'table2']

@pytest.mark.asyncio
@patch('app.routes.generation.get_clickhouse_client')
async def test_list_clickhouse_tables_failure(mock_get_clickhouse_client):
    """Test that the /clickhouse_tables endpoint returns a 500 error when the ClickHouse client fails to connect."""
    mock_get_clickhouse_client.side_effect = Exception("Failed to connect")

    response = client.get("/api/v3/generation/clickhouse_tables")
    assert response.status_code == 500
    assert response.json() == {'detail': 'Failed to fetch tables from ClickHouse: Failed to connect'}