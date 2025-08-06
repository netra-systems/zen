import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from legacy.content_generator import generate_and_ingest_for_type, get_all_existing_content_corpuses, populate_with_default_data
from app.db.models_clickhouse import ContentCorpus, CONTENT_CORPUS_TABLE_NAME

@pytest.fixture
def mock_clickhouse_client():
    """Fixture to create a mock ClickHouse client."""
    client = MagicMock()
    client.insert = AsyncMock()
    client.command = AsyncMock()
    client.query = AsyncMock()
    client.table_exists = AsyncMock(return_value=True)
    return client

@pytest.fixture
def mock_llm():
    """Fixture to create a mock LLM."""
    llm = MagicMock()
    # Mock the response from the LLM
    llm.generate_content.return_value = MagicMock(
        candidates=[
            MagicMock(
                content=MagicMock(
                    parts=[
                        MagicMock(
                            function_call=MagicMock(
                                args={"user_prompt": "test prompt", "assistant_response": "test response"}
                            )
                        )
                    ]
                )
            )
        ]
    )
    return llm

@patch("legacy.content_generator.get_clickhouse_client")
def test_generate_and_ingest_for_type(mock_get_client, mock_llm, mock_clickhouse_client):
    """Test that the content generation and ingestion process works as expected."""
    mock_get_client.return_value.__enter__.return_value = mock_clickhouse_client

    task_args = ("simple_chat", 1)
    generation_config = {}
    clickhouse_config = {}

    num_generated = generate_and_ingest_for_type(task_args, mock_llm, generation_config, clickhouse_config)

    assert num_generated == 1
    mock_clickhouse_client.insert.assert_called_once()
    inserted_data = mock_clickhouse_client.insert.call_args[0][1]
    assert len(inserted_data) == 1
    assert isinstance(inserted_data[0], dict)
    assert inserted_data[0]["workload_type"] == "simple_chat"
    assert inserted_data[0]["prompt"] == "test prompt"

@pytest.mark.asyncio
@patch("legacy.content_generator.get_clickhouse_client")
async def test_get_all_existing_content_corpuses_with_data(mock_get_client, mock_clickhouse_client):
    """Test that existing content is retrieved correctly."""
    mock_get_client.return_value.__aenter__.return_value = mock_clickhouse_client
    mock_clickhouse_client.query.return_value.result_rows = [("simple_chat", "p1", "r1")]

    corpuses = await get_all_existing_content_corpuses()

    assert "simple_chat" in corpuses
    assert corpuses["simple_chat"][0] == ("p1", "r1")

@pytest.mark.asyncio
@patch("legacy.content_generator.get_clickhouse_client")
async def test_get_all_existing_content_corpuses_no_data(mock_get_client, mock_clickhouse_client):
    """Test that the default corpus is returned when no data is found."""
    mock_get_client.return_value.__aenter__.return_value = mock_clickhouse_client
    mock_clickhouse_client.query.return_value.result_rows = []
    mock_clickhouse_client.table_exists.return_value = False

    with patch("legacy.content_generator.populate_with_default_data") as mock_populate:
        corpuses = await get_all_existing_content_corpuses()

    assert mock_populate.call_count == 2

@pytest.mark.asyncio
@patch("legacy.content_generator.get_clickhouse_client")
async def test_populate_with_default_data(mock_get_client, mock_clickhouse_client):
    """Test that the database is populated with the default data."""
    mock_get_client.return_value.__aenter__.return_value = mock_clickhouse_client

    await populate_with_default_data(mock_clickhouse_client)

    mock_clickhouse_client.command.assert_called_once()
    mock_clickhouse_client.insert.assert_called_once()
    inserted_data = mock_clickhouse_client.insert.call_args[0][1]
    assert len(inserted_data) > 0