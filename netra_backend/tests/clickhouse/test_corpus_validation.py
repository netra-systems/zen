"""
Corpus validation and cloning tests
Tests validation and safety measures, plus corpus cloning functionality
COMPLIANCE: 450-line max file, 25-line max functions
"""

# Add project root to path
import sys
from pathlib import Path

from tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add project root to path
from app.services.corpus_service import CorpusService

# Add project root to path


class TestValidationAndSafety:
    """Test validation and safety measures"""
    
    def test_prompt_response_length_validation(self):
        """Test 13: Verify prompt/response length limits"""
        service = CorpusService()
        
        # Test max length validation
        long_prompt = "x" * 100001
        long_response = "y" * 100001
        
        records = [
            {"workload_type": "simple_chat", "prompt": long_prompt, "response": "r"},
            {"workload_type": "simple_chat", "prompt": "p", "response": long_response}
        ]
        
        result = service._validate_records(records)
        
        assert not result["valid"]
        assert "exceeds maximum length" in str(result["errors"])
    
    def test_required_fields_validation(self):
        """Test 14: Verify all required fields are validated"""
        service = CorpusService()
        
        test_cases = _get_validation_test_cases()
        
        for record, expected_errors in test_cases:
            result = service._validate_records([record])
            assert not result["valid"]
            for expected in expected_errors:
                assert any(expected in error for error in result["errors"])

    async def test_corpus_access_control(self):
        """Test 15: Verify corpus access control"""
        service = CorpusService()
        
        db = MagicMock()
        
        # Test filtering by user_id
        await service.get_corpora(db, user_id="specific_user")
        
        # Verify filter was applied
        db.query().filter.assert_called()
        filter_call = db.query().filter.call_args
        assert filter_call != None


class TestCorpusCloning:
    """Test corpus cloning functionality"""
    
    async def test_corpus_clone_workflow(self):
        """Test 11: Verify corpus cloning creates new corpus with data"""
        service = CorpusService()
        
        with patch('app.services.corpus_service.get_clickhouse_client') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            db = MagicMock()
            
            # Mock source corpus
            source = _create_source_corpus()
            
            db.query().filter().first.return_value = source
            
            # Clone corpus
            result = await service.clone_corpus(
                db, "source_id", "Cloned Corpus", "new_user"
            )
            
            assert result != None
            assert result.name == "Cloned Corpus"
            assert result.description == "Clone of Original Corpus"

    async def test_corpus_content_copy(self):
        """Test 12: Verify corpus content is copied correctly"""
        service = CorpusService()
        
        with patch('app.services.corpus_service.get_clickhouse_client') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            db = MagicMock()
            
            await service._copy_corpus_content(
                "source_table", "dest_table", "corpus_id", db
            )
            
            # Should wait for table to be ready
            await asyncio.sleep(2.1)
            
            # Verify copy query
            mock_instance.execute.assert_called()
            query = mock_instance.execute.call_args[0][0]
            assert "INSERT INTO dest_table" in query
            assert "SELECT * FROM source_table" in query


def _get_validation_test_cases():
    """Get test cases for field validation."""
    return [
        ({}, ["missing 'prompt'", "missing 'response'", "missing 'workload_type'"]),
        ({"prompt": "p"}, ["missing 'response'", "missing 'workload_type'"]),
        ({"response": "r"}, ["missing 'prompt'", "missing 'workload_type'"]),
        ({"workload_type": "test"}, ["missing 'prompt'", "missing 'response'"])
    ]


def _create_source_corpus():
    """Create source corpus for cloning."""
    source = MagicMock()
    source.id = "source_id"
    source.name = "Original Corpus"
    source.status = "available"
    source.table_name = "source_table"
    source.domain = "testing"
    return source