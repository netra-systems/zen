"""
Unit tests for corpus schema models
Coverage Target: 70%
Business Value: Long-term maintainability
"""

import pytest
from datetime import datetime
from netra_backend.app.schemas.corpus import Corpus, CorpusCreate, CorpusUpdate
from shared.isolated_environment import IsolatedEnvironment

class CorpusTests:
    """Test suite for Corpus Pydantic model"""
    
    @pytest.fixture
    def corpus_data(self):
        """Create test corpus data"""
        return {
            "id": "test-corpus-123",
            "name": "Test Corpus",
            "description": "A test corpus for unit testing",
            "domain": "testing",
            "status": "active",
            "created_by_id": "user-123",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
    
    @pytest.fixture
    def instance(self, corpus_data):
        """Create test instance"""
        return Corpus(**corpus_data)
    
    def test_initialization(self, instance):
        """Test proper initialization"""
        assert instance is not None
        assert instance.name == "Test Corpus"
        assert instance.description == "A test corpus for unit testing"
        assert instance.domain == "testing"
        assert instance.status == "active"
    
    def test_corpus_create_model(self):
        """Test CorpusCreate model"""
        create_data = {
            "name": "New Corpus",
            "description": "A new corpus",
            "domain": "general"
        }
        corpus_create = CorpusCreate(**create_data)
        assert corpus_create.name == "New Corpus"
        assert corpus_create.description == "A new corpus"
        assert corpus_create.domain == "general"
    
    def test_corpus_update_model(self):
        """Test CorpusUpdate model"""
        update_data = {
            "name": "Updated Corpus",
            "description": "Updated description"
        }
        corpus_update = CorpusUpdate(**update_data)
        assert corpus_update.name == "Updated Corpus"
        assert corpus_update.description == "Updated description"
    
    def test_model_validation(self):
        """Test model validation"""
        # Test required fields
        with pytest.raises(ValueError):
            Corpus()  # Missing required fields
        
        # Test with minimal required data
        minimal_data = {
            "id": "test-id",
            "name": "Test Name",
            "status": "pending",
            "created_by_id": "user-123",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        corpus = Corpus(**minimal_data)
        assert corpus.name == "Test Name"
        assert corpus.domain == "general"  # Default value
    
    def test_serialization(self, instance):
        """Test model serialization"""
        corpus_dict = instance.model_dump()
        assert "name" in corpus_dict
        assert "id" in corpus_dict
        assert corpus_dict["name"] == "Test Corpus"
