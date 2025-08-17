"""
Test 24: Corpus Route Operations
Tests for corpus CRUD operations - app/routes/corpus.py
"""

import pytest
from unittest.mock import patch, MagicMock
from .test_utilities import secured_client


class TestCorpusRoute:
    """Test corpus CRUD operations."""
    
    def test_corpus_create(self, secured_client):
        """Test creating corpus documents."""
        document = {
            "title": "Test Document",
            "content": "This is test content",
            "metadata": {"category": "test", "tags": ["sample"]}
        }
        
        with patch('app.services.corpus_service.create_document') as mock_create:
            mock_create.return_value = {"id": "doc123", **document}
            
            response = secured_client.post("/api/corpus", json=document)
            
            if response.status_code == 201:
                data = response.json()
                assert "id" in data
    
    async def test_corpus_search(self):
        """Test corpus search functionality."""
        from app.routes.corpus import search_corpus
        from app.db.models_postgres import User
        
        # Mock search method
        with patch('app.services.corpus_service.corpus_service_instance.search_with_fallback') as mock_search:
            mock_search.return_value = [
                {"id": "1", "title": "Result 1", "score": 0.95},
                {"id": "2", "title": "Result 2", "score": 0.87}
            ]
            
            # Mock user
            mock_user = User()
            mock_user.id = 1
            
            # Test search function
            result = await search_corpus(
                q="test query",
                corpus_id="default",
                current_user=mock_user
            )
            
            # Verify results
            mock_search.assert_called_once_with("default", "test query")
            assert isinstance(result, list)
            assert len(result) == 2
            assert result[0]["id"] == "1"
            assert result[0]["score"] == 0.95

    async def test_corpus_bulk_operations(self):
        """Test bulk corpus operations."""
        from app.routes.corpus import bulk_index_documents, BulkIndexRequest
        
        documents = [
            {"title": f"Doc {i}", "content": f"Content {i}"}
            for i in range(5)
        ]
        
        # Create proper request object
        request = BulkIndexRequest(documents=documents)
        result = await bulk_index_documents(request)
        assert result["indexed"] == 5