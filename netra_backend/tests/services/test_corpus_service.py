"""Test corpus service for managing document and content collections."""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from netra_backend.app.schemas import Corpus, CorpusCreate

# Add project root to path
from netra_backend.app.services.corpus_service import CorpusStatus


# Add project root to path
class TestCorpusService:
    """Test corpus service basic functionality."""

    async def test_corpus_status_enum(self):
        """Test corpus status enumeration."""
        assert CorpusStatus.CREATING.value == "creating"
        assert CorpusStatus.AVAILABLE.value == "available"
        assert CorpusStatus.FAILED.value == "failed"
        assert CorpusStatus.UPDATING.value == "updating"
        assert CorpusStatus.DELETING.value == "deleting"

    async def test_corpus_schema(self):
        """Test corpus Pydantic schema."""
        corpus_data = {
            "id": "test-corpus-123",
            "name": "Test Corpus",
            "description": "A test corpus for validation",
            "status": "available",
            "created_by_id": "user123",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        corpus = Corpus(**corpus_data)
        assert corpus.id == "test-corpus-123"
        assert corpus.name == "Test Corpus"
        assert corpus.description == "A test corpus for validation"
        assert corpus.status == "available"
        assert corpus.created_by_id == "user123"

    async def test_corpus_create_schema(self):
        """Test corpus creation schema."""
        create_data = {
            "name": "New Corpus", 
            "description": "Creating a new corpus"
        }
        
        corpus_create = CorpusCreate(**create_data)
        assert corpus_create.name == "New Corpus"
        assert corpus_create.description == "Creating a new corpus"

    async def test_corpus_service_import(self):
        """Test that corpus service can be imported."""
        from netra_backend.app.services.corpus_service import CorpusStatus
        assert CorpusStatus != None