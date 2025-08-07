import pytest
import time
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.generation_service import update_job_status, get_corpus_from_clickhouse, save_corpus_to_clickhouse
from app.services.job_store import job_store

@pytest.mark.asyncio
async def test_update_job_status():
    # Arrange
    job_id = "test_job"
    status = "running"
    kwargs = {"progress": 50}

    # Act
    await update_job_status(job_id, status, **kwargs)

    # Assert
    assert job_id in job_store._jobs
    assert job_store._jobs[job_id]['status'] == status
    assert job_store._jobs[job_id]['progress'] == 50
    assert 'last_updated' in job_store._jobs[job_id]

@pytest.mark.asyncio
async def test_get_corpus_from_clickhouse():
    # Arrange
    table_name = "test_corpus"
    mock_db_instance = MagicMock()
    mock_db_instance.connect = AsyncMock()
    mock_db_instance.execute_query = AsyncMock(return_value=[
        {'workload_type': 'test_type', 'prompt': 'p1', 'response': 'r1'},
        {'workload_type': 'test_type', 'prompt': 'p2', 'response': 'r2'}
    ])
    mock_db_instance.is_connected = AsyncMock(return_value=True)
    mock_db_instance.disconnect = AsyncMock()

    with patch('app.services.generation_service.ClickHouseDatabase') as mock_db_class:
        mock_db_class.return_value = mock_db_instance

        # Act
        corpus = await get_corpus_from_clickhouse(table_name)

        # Assert
        assert "test_type" in corpus
        assert len(corpus["test_type"]) == 2
        assert corpus["test_type"][0] == ('p1', 'r1')
        mock_db_instance.execute_query.assert_called_once_with(f"SELECT workload_type, prompt, response FROM {table_name}")
        mock_db_instance.disconnect.assert_called_once()

@pytest.mark.asyncio
async def test_save_corpus_to_clickhouse():
    # Arrange
    table_name = "test_corpus"
    corpus = {"test_type": [("p1", "r1"), ("p2", "r2")]}
    mock_db_instance = MagicMock()
    mock_db_instance.connect = AsyncMock()
    mock_db_instance.command = AsyncMock()
    mock_db_instance.insert_data = AsyncMock()
    mock_db_instance.is_connected = AsyncMock(return_value=True)
    mock_db_instance.disconnect = AsyncMock()

    with patch('app.services.generation_service.ClickHouseDatabase') as mock_db_class:
        mock_db_class.return_value = mock_db_instance

        # Act
        await save_corpus_to_clickhouse(corpus, table_name)

        # Assert
        mock_db_instance.command.assert_called_once()
        mock_db_instance.insert_data.assert_called_once()
        mock_db_instance.disconnect.assert_called_once()
