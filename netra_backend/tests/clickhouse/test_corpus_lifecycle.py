"""
Corpus lifecycle and workload types tests
Tests complete corpus lifecycle from creation to deletion and workload type coverage
COMPLIANCE: 450-line max file, 25-line max functions
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from netra_backend.app.schemas import CorpusCreate

# Add project root to path
from netra_backend.app.services.corpus_service import (
    ContentSource,
    CorpusService,
    CorpusStatus,
)

# Add project root to path


class TestCorpusLifecycle:
    """Test complete corpus lifecycle from creation to deletion"""
    
    async def test_corpus_creation_workflow(self):
        """Test 1: Verify complete corpus creation workflow"""
        service = CorpusService()
        
        with patch('app.services.corpus_service.get_clickhouse_client') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            db = MagicMock()
            corpus_data = _create_test_corpus_data()
            
            # Create corpus
            corpus = await service.create_corpus(
                db, corpus_data, "test_user", ContentSource.GENERATE
            )
            
            # Verify corpus attributes
            _assert_corpus_created_correctly(corpus)

    async def test_corpus_status_transitions(self):
        """Test 2: Verify corpus status transitions"""
        service = CorpusService()
        
        with patch('app.services.corpus_service.get_clickhouse_client') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            db = MagicMock()
            
            # Test status flow: CREATING -> AVAILABLE
            await service._create_clickhouse_table("corpus_id", "table_name", db)
            
            # Verify status update to AVAILABLE
            db.query().filter().update.assert_called_with(
                {"status": CorpusStatus.AVAILABLE.value}
            )
            
            # Test error flow: CREATING -> FAILED
            mock_instance.execute.side_effect = Exception("Table creation failed")
            await service._create_clickhouse_table("corpus_id2", "table_name2", db)
            
            # Verify status update to FAILED
            calls = db.query().filter().update.call_args_list
            assert {"status": CorpusStatus.FAILED.value} in [call[0][0] for call in calls]

    async def test_corpus_deletion_workflow(self):
        """Test 3: Verify complete corpus deletion workflow"""
        service = CorpusService()
        
        with patch('app.services.corpus_service.get_clickhouse_client') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            db = MagicMock()
            corpus = _create_mock_corpus()
            
            db.query().filter().first.return_value = corpus
            
            result = await service.delete_corpus(db, "test_id")
            
            # Verify deletion steps
            assert result == True
            mock_instance.execute.assert_called_with("DROP TABLE IF EXISTS test_table")
            db.delete.assert_called_with(corpus)
            db.commit.assert_called()


class TestWorkloadTypesCoverage:
    """Test coverage of all workload types"""
    
    async def test_all_workload_types_supported(self):
        """Test 4: Verify all workload types are supported"""
        service = CorpusService()
        
        valid_workload_types = _get_valid_workload_types()
        
        for workload_type in valid_workload_types:
            records = [{
                "workload_type": workload_type,
                "prompt": "test prompt",
                "response": "test response"
            }]
            
            result = service._validate_records(records)
            assert result["valid"], f"Workload type {workload_type} should be valid"

    async def test_workload_distribution_tracking(self):
        """Test 5: Verify workload distribution is tracked correctly"""
        service = CorpusService()
        
        with patch('app.services.corpus_service.get_clickhouse_client') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            # Mock distribution query result
            _setup_distribution_mock(mock_instance)
            
            db = MagicMock()
            corpus = _create_available_corpus()
            db.query().filter().first.return_value = corpus
            
            stats = await service.get_corpus_statistics(db, "test_id")
            
            # Verify all workload types are tracked
            assert len(stats["workload_distribution"]) == 6
            assert sum(stats["workload_distribution"].values()) == 1000


def _create_test_corpus_data():
    """Create test corpus data."""
    return CorpusCreate(
        name="test_corpus",
        description="Test corpus for coverage",
        domain="testing"
    )


def _assert_corpus_created_correctly(corpus):
    """Assert corpus was created with correct attributes."""
    assert corpus.name == "test_corpus"
    assert corpus.status == CorpusStatus.CREATING.value
    assert corpus.created_by_id == "test_user"
    assert "netra_content_corpus_" in corpus.table_name
    
    # Verify metadata
    metadata = json.loads(corpus.metadata_)
    assert metadata["content_source"] == ContentSource.GENERATE.value
    assert metadata["version"] == 1


def _create_mock_corpus():
    """Create mock corpus for testing."""
    corpus = MagicMock()
    corpus.id = "test_id"
    corpus.table_name = "test_table"
    corpus.status = CorpusStatus.AVAILABLE.value
    return corpus


def _get_valid_workload_types():
    """Get list of valid workload types."""
    return [
        "simple_chat",
        "rag_pipeline", 
        "tool_use",
        "multi_turn_tool_use",
        "failed_request",
        "custom_domain"
    ]


def _setup_distribution_mock(mock_instance):
    """Setup distribution query mock."""
    mock_instance.execute.side_effect = [
        [(1000, 6, 100, 200, datetime.now(), datetime.now())],  # stats
        [
            ("simple_chat", 400),
            ("rag_pipeline", 300),
            ("tool_use", 200),
            ("multi_turn_tool_use", 50),
            ("failed_request", 30),
            ("custom_domain", 20)
        ]  # distribution
    ]


def _create_available_corpus():
    """Create available corpus for testing."""
    corpus = MagicMock()
    corpus.status = "available"
    corpus.table_name = "test_table"
    return corpus