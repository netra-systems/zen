import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from app.main import app
from app.db.session import get_db_session
from datetime import datetime

class TestReferenceManagement:
    
    def test_create_reference(self):
        """Test creating a new reference"""
        client = TestClient(app)
        
        reference_data = {
            "name": "performance_optimization_guide",
            "friendly_name": "Performance Optimization Guide",
            "type": "document",
            "value": "Optimization strategies for AI workloads",
            "description": "Guide for AI performance optimization",
            "version": "1.0"
        }
        
        with patch('app.db.session.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.return_value.__aexit__ = AsyncMock()
            mock_session.add = MagicMock()
            mock_session.commit = AsyncMock()
            mock_session.refresh = AsyncMock()
            
            response = client.post("/api/references", json=reference_data)
            
            assert response.status_code == 201
            assert response.json()["friendly_name"] == reference_data["friendly_name"]
    
    def test_get_reference_by_id(self):
        """Test retrieving a reference by ID"""
        # Setup mock reference with proper structure
        mock_reference = MagicMock()
        mock_reference.id = "ref-123"
        mock_reference.name = "test_reference"
        mock_reference.friendly_name = "Test Reference"
        mock_reference.type = "document"
        mock_reference.value = "Test content"
        mock_reference.description = "Test description"
        mock_reference.version = "1.0"
        mock_reference.created_at = datetime.now()
        mock_reference.updated_at = datetime.now()
        
        # Setup mock session
        mock_session = AsyncMock()
        
        # Setup proper mock chain for result.scalars().first()
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = mock_reference
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        
        # Mock execute as an async method that returns the result
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Setup mock context manager - session should be a context manager itself
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        async def mock_get_db_session():
            yield mock_session
        
        # Override dependency
        app.dependency_overrides[get_db_session] = mock_get_db_session
        
        try:
            client = TestClient(app)
            response = client.get("/api/references/ref-123")
            
            assert response.status_code == 200
            assert response.json()["id"] == "ref-123"
        finally:
            # Clean up dependency override
            app.dependency_overrides = {}
    
    def test_search_references(self):
        """Test searching references with filters"""
        client = TestClient(app)
        
        mock_references = [
            {
                "id": "ref-1", 
                "name": "ai_guide", 
                "friendly_name": "AI Guide",
                "type": "document",
                "value": "AI content",
                "description": "AI guide description",
                "version": "1.0"
            },
            {
                "id": "ref-2", 
                "name": "ml_optimization", 
                "friendly_name": "ML Optimization",
                "type": "document",
                "value": "ML content",
                "description": "ML optimization description",
                "version": "1.0"
            }
        ]
        
        with patch('app.db.session.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.return_value.__aexit__ = AsyncMock()
            
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = mock_references
            mock_session.execute = AsyncMock(return_value=mock_result)
            
            response = client.get("/api/references/search?query=optimization")
            
            assert response.status_code == 200
            assert len(response.json()) == 2
    
    def test_update_reference(self):
        """Test updating an existing reference"""
        client = TestClient(app)
        
        update_data = {
            "friendly_name": "Updated Reference Name",
            "value": "Updated content"
        }
        
        with patch('app.db.session.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.return_value.__aexit__ = AsyncMock()
            
            mock_reference = MagicMock()
            mock_reference.id = "ref-123"
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_reference
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_session.commit = AsyncMock()
            
            response = client.patch("/api/references/ref-123", json=update_data)
            
            assert response.status_code == 200
            assert mock_reference.friendly_name == update_data["friendly_name"]
    
    def test_delete_reference(self):
        """Test deleting a reference"""
        # Setup mock session
        mock_session = AsyncMock()
        mock_reference = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_reference
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.delete = AsyncMock()
        mock_session.commit = AsyncMock()
        
        # Setup mock context manager - session should be a context manager itself
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        async def mock_get_db_session():
            yield mock_session
        
        # Override dependency
        app.dependency_overrides[get_db_session] = mock_get_db_session
        
        try:
            client = TestClient(app)
            response = client.delete("/api/references/ref-123")
            
            assert response.status_code == 204
            mock_session.delete.assert_called_once_with(mock_reference)
        finally:
            # Clean up dependency override
            app.dependency_overrides = {}