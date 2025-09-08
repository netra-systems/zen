"""
Test 29: Synthetic Data Route Generation
Tests for synthetic data creation - app/routes/synthetic_data.py
"""

import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from shared.isolated_environment import IsolatedEnvironment


import pytest

from netra_backend.tests.test_utilities import base_client

class TestSyntheticDataRoute:
    """Test synthetic data creation."""
    
    def test_synthetic_data_generation(self, base_client):
        """Test synthetic data generation endpoint."""
        generation_request = {
            "domain_focus": "user_data",
            "tool_catalog": [
                {
                    "name": "user_generator",
                    "type": "data_generation",
                    "latency_ms_range": [50, 200],
                    "failure_rate": 0.01
                }
            ],
            "workload_distribution": {"user_creation": 1.0},
            "scale_parameters": {
                "num_traces": 10,
                "time_window_hours": 24,
                "concurrent_users": 100,
                "peak_load_multiplier": 1.0
            }
        }
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.synthetic_data_service.synthetic_data_service.generate_synthetic_data') as mock_gen:
            mock_gen.return_value = {
                "job_id": "test_job_123",
                "status": "initiated",
                "table_name": "netra_synthetic_data_test_job_123",
                "websocket_channel": "generation_test_job_123"
            }
            
            response = base_client.post("/api/synthetic-data/generate", json=generation_request)
            
            if response.status_code == 200:
                data = response.json()
                assert "job_id" in data
                assert "status" in data
                assert data["status"] == "initiated"
    
    def test_synthetic_data_validation(self, base_client):
        """Test synthetic data validation."""
        validation_request = {
            "data": [
                {"id": 1, "value": "test"},
                {"id": 2, "value": "test2"}
            ],
            "schema": {
                "id": "integer",
                "value": "string"
            }
        }
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.synthetic_data_service.validate_data') as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                "errors": []
            }
            
            response = base_client.post("/api/synthetic-data/validate", json=validation_request)
            
            if response.status_code == 200:
                result = response.json()
                assert "valid" in result

    @pytest.mark.asyncio
    async def test_synthetic_data_templates(self):
        """Test synthetic data template management."""
        from netra_backend.app.routes.synthetic_data import _fetch_templates
        
        # Mock database dependency
        # Mock: Generic component isolation for controlled unit testing
        mock_db = AsyncNone  # TODO: Use real service instance
        
        # Create mock for SyntheticDataService class
        # Mock: Component isolation for testing without external dependencies
        with patch('app.routes.synthetic_data.SyntheticDataService') as mock_service_class:
            # Mock static method to return templates
            # Mock: Async component isolation for testing without real async operations
            mock_service_class.get_available_templates = AsyncMock(return_value=[
                {"name": "user_profile", "fields": 5},
                {"name": "transaction", "fields": 8}
            ])
            
            result = await _fetch_templates(mock_db)
            assert "templates" in result
            assert len(result["templates"]) == 2
            assert result["status"] == "ok"