"""
Unit tests for document schema models
Coverage Target: 70%
Business Value: Long-term maintainability
"""

import pytest
from datetime import datetime
from netra_backend.app.schemas.corpus import Document, DocumentCreate, DocumentUpdate
from shared.isolated_environment import IsolatedEnvironment

class DocumentTests:
    """Test suite for Document Pydantic model"""
    
    @pytest.fixture
    def document_data(self):
        """Create test document data"""
        return {
            "id": "test-doc-123",
            "corpus_id": "test-corpus-123", 
            "title": "Test Document",
            "content": "This is test document content for unit testing.",
            "metadata": {"type": "test", "tags": ["unit", "test"]},
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
    
    @pytest.fixture
    def instance(self, document_data):
        """Create test instance"""
        return Document(**document_data)
    
    def test_initialization(self, instance):
        """Test proper initialization"""
        assert instance is not None
        assert instance.title == "Test Document"
        assert instance.content == "This is test document content for unit testing."
        assert instance.metadata["type"] == "test"
        assert "unit" in instance.metadata["tags"]
    
    def test_document_create_model(self):
        """Test DocumentCreate model"""
        create_data = {
            "title": "New Document",
            "content": "New document content",
            "metadata": {"category": "new"}
        }
        doc_create = DocumentCreate(**create_data)
        assert doc_create.title == "New Document"
        assert doc_create.content == "New document content"
        assert doc_create.metadata["category"] == "new"
    
    def test_document_update_model(self):
        """Test DocumentUpdate model"""
        update_data = {
            "title": "Updated Document",
            "content": "Updated content"
        }
        doc_update = DocumentUpdate(**update_data)
        assert doc_update.title == "Updated Document"
        assert doc_update.content == "Updated content"
    
    def test_model_validation(self):
        """Test model validation"""
        # Test required fields
        with pytest.raises(ValueError):
            Document()  # Missing required fields
        
        # Test with minimal required data
        minimal_data = {
            "id": "test-id",
            "corpus_id": "test-corpus-id",
            "title": "Test Title",
            "content": "Test content",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        document = Document(**minimal_data)
        assert document.title == "Test Title"
        assert document.content == "Test content"
        assert document.metadata is None  # Optional field
    
    def test_serialization(self, instance):
        """Test model serialization"""
        doc_dict = instance.model_dump()
        assert "title" in doc_dict
        assert "content" in doc_dict
        assert "id" in doc_dict
        assert "corpus_id" in doc_dict
        assert doc_dict["title"] == "Test Document"
