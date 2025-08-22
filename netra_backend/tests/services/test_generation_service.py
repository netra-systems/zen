import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from netra_backend.app.services.generation_service import (
    get_corpus_from_clickhouse,
    save_corpus_to_clickhouse,
    update_job_status,
)
from netra_backend.app.services.job_store import job_store

async def test_update_job_status():
    # Arrange
    job_id = "test_job"
    status = "running"
    kwargs = {"progress": 50}
    await job_store.set(job_id, {"status": "pending"})

    # Act
    await update_job_status(job_id, status, **kwargs)

    # Assert
    job = await job_store.get(job_id)
    assert job['status'] == status
    assert job['progress'] == 50
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

    with patch('app.services.generation_job_manager.ClickHouseDatabase') as mock_db_class:
        mock_db_class.return_value = mock_db_instance

        # Act
        corpus = await get_corpus_from_clickhouse(table_name)

        # Assert
        assert "test_type" in corpus
        assert len(corpus["test_type"]) == 2
        assert corpus["test_type"][0] == ('p1', 'r1')
        mock_db_instance.execute_query.assert_called_once_with(f"SELECT workload_type, prompt, response FROM {table_name}")
        mock_db_instance.disconnect.assert_called_once()
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

    with patch('app.services.generation_job_manager.ClickHouseDatabase') as mock_db_class:
        mock_db_class.return_value = mock_db_instance

        # Act
        await save_corpus_to_clickhouse(corpus, table_name)

        # Assert
        mock_db_instance.command.assert_called_once()
        mock_db_instance.insert_data.assert_called_once()
        mock_db_instance.disconnect.assert_called_once()
