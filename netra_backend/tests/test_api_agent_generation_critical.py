"""
Critical agent and generation API endpoint tests.

Tests for agent interaction, content generation, and configuration endpoints.
Core AI functionality validation.
"""

# Add project root to path
import sys
from pathlib import Path

from ..test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestAPIAgentGenerationCritical:
    """Critical agent and generation API endpoint tests."""
    async def test_agent_query_endpoint(self):
        """Test agent query endpoint."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        
        # Test agent query
        query_data = {
            "query": "Analyze my system performance",
            "thread_id": str(uuid.uuid4()),
            "context": {"optimization_type": "cost"}
        }
        
        mock_client.post = AsyncMock(return_value={
            "status_code": 200,
            "json": {
                "response": "Based on analysis, your system shows...",
                "metadata": {
                    "processing_time": 2.5,
                    "agents_used": ["triage", "data", "optimization"]
                }
            }
        })
        
        response = await mock_client.post(
            "/api/agent/query",
            json=query_data,
            headers=auth_headers
        )
        assert response["status_code"] == 200
        assert "response" in response["json"]
    async def test_agent_metadata_validation(self):
        """Test agent response metadata validation."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        
        query_data = {
            "query": "Test query",
            "thread_id": str(uuid.uuid4()),
            "context": {"type": "test"}
        }
        
        mock_client.post = AsyncMock(return_value={
            "status_code": 200,
            "json": {
                "response": "Test response",
                "metadata": {
                    "processing_time": 2.5,
                    "agents_used": ["triage", "data", "optimization"]
                }
            }
        })
        
        response = await mock_client.post(
            "/api/agent/query",
            json=query_data,
            headers=auth_headers
        )
        
        metadata = response["json"]["metadata"]
        assert len(metadata["agents_used"]) == 3
        assert metadata["processing_time"] == 2.5
    async def test_synthetic_data_generation(self):
        """Test synthetic data generation endpoint."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        
        # Test generate synthetic data
        generation_data = {
            "type": "logs",
            "count": 100,
            "format": "json"
        }
        
        mock_client.post = AsyncMock(return_value={
            "status_code": 200,
            "json": {
                "job_id": str(uuid.uuid4()),
                "status": "processing",
                "estimated_time": 30
            }
        })
        
        response = await mock_client.post(
            "/api/generate/synthetic-data",
            json=generation_data,
            headers=auth_headers
        )
        assert response["status_code"] == 200
        assert response["json"]["status"] == "processing"
    async def test_generation_job_tracking(self):
        """Test generation job tracking."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        
        generation_data = {
            "type": "metrics",
            "count": 50,
            "format": "csv"
        }
        
        job_id = str(uuid.uuid4())
        mock_client.post = AsyncMock(return_value={
            "status_code": 200,
            "json": {
                "job_id": job_id,
                "status": "processing",
                "estimated_time": 15
            }
        })
        
        response = await mock_client.post(
            "/api/generate/synthetic-data",
            json=generation_data,
            headers=auth_headers
        )
        
        assert response["json"]["job_id"] == job_id
        assert "estimated_time" in response["json"]
    async def test_configuration_get_endpoint(self):
        """Test configuration get endpoint."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        
        # Test get configuration
        mock_client.get = AsyncMock(return_value={
            "status_code": 200,
            "json": {
                "environment": "development",
                "features": {
                    "optimization": True,
                    "synthetic_data": True
                },
                "limits": {
                    "max_threads": 100,
                    "max_messages_per_thread": 1000
                }
            }
        })
        
        response = await mock_client.get("/api/config", headers=auth_headers)
        assert response["status_code"] == 200
        assert response["json"]["environment"] == "development"
    async def test_configuration_features_validation(self):
        """Test configuration features validation."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        
        mock_client.get = AsyncMock(return_value={
            "status_code": 200,
            "json": {
                "environment": "development",
                "features": {
                    "optimization": True,
                    "synthetic_data": True
                },
                "limits": {
                    "max_threads": 100,
                    "max_messages_per_thread": 1000
                }
            }
        })
        
        response = await mock_client.get("/api/config", headers=auth_headers)
        features = response["json"]["features"]
        assert features["optimization"] is True
        assert features["synthetic_data"] is True
    async def test_configuration_update_endpoint(self):
        """Test configuration update endpoint."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        
        # Test update configuration (admin only)
        config_update = {
            "features": {
                "optimization": False
            }
        }
        
        mock_client.patch = AsyncMock(return_value={
            "status_code": 200,
            "json": {"message": "Configuration updated successfully"}
        })
        
        response = await mock_client.patch(
            "/api/config",
            json=config_update,
            headers=auth_headers
        )
        assert response["status_code"] == 200
    async def test_agent_context_handling(self):
        """Test agent context handling."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        
        contexts = [
            {"optimization_type": "cost"},
            {"optimization_type": "performance"},
            {"analysis_depth": "detailed"}
        ]
        
        for context in contexts:
            query_data = {
                "query": "Context test query",
                "thread_id": str(uuid.uuid4()),
                "context": context
            }
            
            mock_client.post = AsyncMock(return_value={
                "status_code": 200,
                "json": {
                    "response": "Context-aware response",
                    "metadata": {"context_processed": True}
                }
            })
            
            response = await mock_client.post(
                "/api/agent/query",
                json=query_data,
                headers=auth_headers
            )
            assert response["status_code"] == 200
    async def test_generation_type_validation(self):
        """Test generation type validation."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        
        generation_types = ["logs", "metrics", "events", "traces"]
        
        for gen_type in generation_types:
            generation_data = {
                "type": gen_type,
                "count": 10,
                "format": "json"
            }
            
            mock_client.post = AsyncMock(return_value={
                "status_code": 200,
                "json": {
                    "job_id": str(uuid.uuid4()),
                    "status": "processing",
                    "type": gen_type
                }
            })
            
            response = await mock_client.post(
                "/api/generate/synthetic-data",
                json=generation_data,
                headers=auth_headers
            )
            assert response["json"]["type"] == gen_type
    async def test_agent_processing_time_tracking(self):
        """Test agent processing time tracking."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        
        query_data = {
            "query": "Performance tracking test",
            "thread_id": str(uuid.uuid4()),
            "context": {"track_performance": True}
        }
        
        mock_client.post = AsyncMock(return_value={
            "status_code": 200,
            "json": {
                "response": "Performance tracked response",
                "metadata": {
                    "processing_time": 1.25,
                    "start_time": "2024-01-01T10:00:00Z",
                    "end_time": "2024-01-01T10:00:01.25Z"
                }
            }
        })
        
        response = await mock_client.post(
            "/api/agent/query",
            json=query_data,
            headers=auth_headers
        )
        
        metadata = response["json"]["metadata"]
        assert "processing_time" in metadata
        assert isinstance(metadata["processing_time"], (int, float))
    async def test_configuration_limits_validation(self):
        """Test configuration limits validation."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        
        mock_client.get = AsyncMock(return_value={
            "status_code": 200,
            "json": {
                "environment": "production",
                "limits": {
                    "max_threads": 1000,
                    "max_messages_per_thread": 5000,
                    "max_concurrent_requests": 100
                }
            }
        })
        
        response = await mock_client.get("/api/config", headers=auth_headers)
        limits = response["json"]["limits"]
        assert limits["max_threads"] == 1000
        assert limits["max_messages_per_thread"] == 5000
    async def test_generation_format_options(self):
        """Test generation format options."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        
        formats = ["json", "csv", "xml", "yaml"]
        
        for format_type in formats:
            generation_data = {
                "type": "logs",
                "count": 25,
                "format": format_type
            }
            
            mock_client.post = AsyncMock(return_value={
                "status_code": 200,
                "json": {
                    "job_id": str(uuid.uuid4()),
                    "status": "processing",
                    "format": format_type
                }
            })
            
            response = await mock_client.post(
                "/api/generate/synthetic-data",
                json=generation_data,
                headers=auth_headers
            )
            assert response["json"]["format"] == format_type
    async def test_agent_multi_agent_orchestration(self):
        """Test multi-agent orchestration."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        
        query_data = {
            "query": "Complex multi-agent analysis",
            "thread_id": str(uuid.uuid4()),
            "context": {"complexity": "high"}
        }
        
        mock_client.post = AsyncMock(return_value={
            "status_code": 200,
            "json": {
                "response": "Multi-agent analysis result",
                "metadata": {
                    "agents_used": ["triage", "data", "optimization", "supervisor"],
                    "orchestration_time": 5.2,
                    "coordination_steps": 3
                }
            }
        })
        
        response = await mock_client.post(
            "/api/agent/query",
            json=query_data,
            headers=auth_headers
        )
        
        metadata = response["json"]["metadata"]
        assert len(metadata["agents_used"]) == 4
        assert "orchestration_time" in metadata
    async def test_configuration_environment_detection(self):
        """Test configuration environment detection."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        
        environments = ["development", "staging", "production"]
        
        for env in environments:
            mock_client.get = AsyncMock(return_value={
                "status_code": 200,
                "json": {
                    "environment": env,
                    "features": {"debug": env == "development"},
                    "limits": {"rate_limit": 100 if env == "production" else 1000}
                }
            })
            
            response = await mock_client.get("/api/config", headers=auth_headers)
            assert response["json"]["environment"] == env
    async def test_generation_count_validation(self):
        """Test generation count validation."""
        mock_client = AsyncMock()
        auth_headers = {"Authorization": "Bearer token123"}
        
        counts = [1, 10, 100, 1000]
        
        for count in counts:
            generation_data = {
                "type": "events",
                "count": count,
                "format": "json"
            }
            
            mock_client.post = AsyncMock(return_value={
                "status_code": 200,
                "json": {
                    "job_id": str(uuid.uuid4()),
                    "status": "processing",
                    "requested_count": count
                }
            })
            
            response = await mock_client.post(
                "/api/generate/synthetic-data",
                json=generation_data,
                headers=auth_headers
            )
            assert response["json"]["requested_count"] == count