import pytest
import json
import uuid
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

@pytest.mark.asyncio
async def test_health_check(client):
    """Test health check endpoint"""
    
    response = client.get("/api/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data

@pytest.mark.asyncio
async def test_create_thread_endpoint(client, auth_headers):
    """Test thread creation via API"""
    
    thread_data = {
        "metadata": {
            "source": "api_test",
            "user_agent": "pytest"
        }
    }
    
    with patch("app.services.agent_service.AgentService.create_thread") as mock_create:
        mock_create.return_value = MagicMock(
            id=str(uuid.uuid4()),
            object="thread",
            created_at=int(datetime.now().timestamp()),
            metadata_=thread_data["metadata"]
        )
        
        response = client.post(
            "/api/threads",
            json=thread_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["object"] == "thread"
        assert data["metadata"]["source"] == "api_test"

@pytest.mark.asyncio
async def test_get_thread_endpoint(client, auth_headers):
    """Test retrieving thread via API"""
    
    thread_id = str(uuid.uuid4())
    
    with patch("app.services.agent_service.AgentService.get_thread") as mock_get:
        mock_get.return_value = MagicMock(
            id=thread_id,
            object="thread",
            created_at=int(datetime.now().timestamp()),
            metadata_={}
        )
        
        response = client.get(
            f"/api/threads/{thread_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == thread_id

@pytest.mark.asyncio
async def test_list_threads_endpoint(client, auth_headers):
    """Test listing threads via API"""
    
    with patch("app.services.agent_service.AgentService.list_threads") as mock_list:
        mock_list.return_value = [
            MagicMock(id=str(uuid.uuid4()), object="thread"),
            MagicMock(id=str(uuid.uuid4()), object="thread")
        ]
        
        response = client.get(
            "/api/threads?limit=10&order=desc",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) == 2

@pytest.mark.asyncio
async def test_create_message_endpoint(client, auth_headers):
    """Test message creation via API"""
    
    thread_id = str(uuid.uuid4())
    message_data = {
        "role": "user",
        "content": "Test message from API"
    }
    
    with patch("app.services.agent_service.AgentService.create_message") as mock_create:
        mock_create.return_value = MagicMock(
            id=str(uuid.uuid4()),
            thread_id=thread_id,
            role=message_data["role"],
            content=message_data["content"]
        )
        
        response = client.post(
            f"/api/threads/{thread_id}/messages",
            json=message_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["content"] == "Test message from API"

@pytest.mark.asyncio
async def test_list_messages_endpoint(client, auth_headers):
    """Test listing messages in a thread"""
    
    thread_id = str(uuid.uuid4())
    
    with patch("app.services.agent_service.AgentService.list_messages") as mock_list:
        mock_list.return_value = [
            MagicMock(content="Message 1", role="user"),
            MagicMock(content="Message 2", role="assistant")
        ]
        
        response = client.get(
            f"/api/threads/{thread_id}/messages",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2

@pytest.mark.asyncio
async def test_create_run_endpoint(client, auth_headers):
    """Test run creation via API"""
    
    thread_id = str(uuid.uuid4())
    run_data = {
        "assistant_id": "netra-assistant",
        "instructions": "Analyze the conversation"
    }
    
    with patch("app.services.agent_service.AgentService.create_run") as mock_create:
        mock_create.return_value = MagicMock(
            id=str(uuid.uuid4()),
            thread_id=thread_id,
            assistant_id=run_data["assistant_id"],
            status="queued"
        )
        
        response = client.post(
            f"/api/threads/{thread_id}/runs",
            json=run_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "queued"

@pytest.mark.asyncio
async def test_get_run_endpoint(client, auth_headers):
    """Test retrieving run status"""
    
    thread_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    
    with patch("app.services.agent_service.AgentService.get_run") as mock_get:
        mock_get.return_value = MagicMock(
            id=run_id,
            thread_id=thread_id,
            status="completed",
            completed_at=int(datetime.now().timestamp())
        )
        
        response = client.get(
            f"/api/threads/{thread_id}/runs/{run_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

@pytest.mark.asyncio
async def test_cancel_run_endpoint(client, auth_headers):
    """Test canceling a run"""
    
    thread_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    
    with patch("app.services.agent_service.AgentService.cancel_run") as mock_cancel:
        mock_cancel.return_value = MagicMock(
            id=run_id,
            status="cancelled",
            cancelled_at=int(datetime.now().timestamp())
        )
        
        response = client.post(
            f"/api/threads/{thread_id}/runs/{run_id}/cancel",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

@pytest.mark.asyncio
async def test_generation_endpoint(client, auth_headers):
    """Test generation API endpoint"""
    
    generation_request = {
        "prompt": "Generate a test response",
        "model": "gpt-4",
        "max_tokens": 100,
        "temperature": 0.7
    }
    
    with patch("app.services.generation_service.GenerationService.generate") as mock_gen:
        mock_gen.return_value = {
            "response": "Generated test response",
            "tokens_used": 50,
            "model": "gpt-4"
        }
        
        response = client.post(
            "/api/generate",
            json=generation_request,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert data["tokens_used"] == 50

@pytest.mark.asyncio
async def test_workload_analysis_endpoint(client, auth_headers):
    """Test workload analysis endpoint"""
    
    analysis_request = {
        "workload_id": str(uuid.uuid4()),
        "time_range": {
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-01-31T23:59:59Z"
        },
        "metrics": ["latency", "tokens", "cost"]
    }
    
    with patch("app.services.analysis_service.AnalysisService.analyze_workload") as mock_analyze:
        mock_analyze.return_value = {
            "workload_id": analysis_request["workload_id"],
            "metrics": {
                "avg_latency": 250,
                "total_tokens": 1000000,
                "total_cost": 150.50
            }
        }
        
        response = client.post(
            "/api/workloads/analyze",
            json=analysis_request,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["metrics"]["total_cost"] == 150.50

@pytest.mark.asyncio
async def test_supply_catalog_endpoint(client, auth_headers):
    """Test supply catalog listing"""
    
    with patch("app.services.catalog_service.CatalogService.list_models") as mock_list:
        mock_list.return_value = [
            {
                "provider": "openai",
                "model": "gpt-4",
                "price_per_1k_tokens": 0.03
            },
            {
                "provider": "anthropic",
                "model": "claude-3",
                "price_per_1k_tokens": 0.02
            }
        ]
        
        response = client.get(
            "/api/supply-catalog",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["provider"] == "openai"

@pytest.mark.asyncio
async def test_optimization_recommendation_endpoint(client, auth_headers):
    """Test optimization recommendation endpoint"""
    
    optimization_request = {
        "workload_id": str(uuid.uuid4()),
        "optimization_goals": ["cost", "latency"],
        "constraints": {
            "max_latency_ms": 500,
            "min_quality_score": 0.85
        }
    }
    
    with patch("app.services.optimization_service.OptimizationService.get_recommendations") as mock_opt:
        mock_opt.return_value = {
            "recommendations": [
                {
                    "action": "switch_model",
                    "from": "gpt-4",
                    "to": "gpt-3.5-turbo",
                    "estimated_savings": 45.2
                }
            ]
        }
        
        response = client.post(
            "/api/optimize",
            json=optimization_request,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["recommendations"]) == 1
        assert data["recommendations"][0]["estimated_savings"] == 45.2

@pytest.mark.asyncio
async def test_error_handling_404(client, auth_headers):
    """Test 404 error handling"""
    
    response = client.get(
        "/api/threads/non-existent-id",
        headers=auth_headers
    )
    
    assert response.status_code in [404, 500]

@pytest.mark.asyncio
async def test_error_handling_validation(client, auth_headers):
    """Test request validation error handling"""
    
    invalid_data = {
        "role": "invalid_role",
    }
    
    response = client.post(
        f"/api/threads/{uuid.uuid4()}/messages",
        json=invalid_data,
        headers=auth_headers
    )
    
    assert response.status_code in [400, 422]

@pytest.mark.asyncio
async def test_pagination(client, auth_headers):
    """Test pagination parameters"""
    
    with patch("app.services.agent_service.AgentService.list_threads") as mock_list:
        mock_list.return_value = {
            "data": [MagicMock() for _ in range(5)],
            "has_more": True,
            "total": 50
        }
        
        response = client.get(
            "/api/threads?limit=5&offset=10",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        mock_list.assert_called_once()

@pytest.mark.asyncio
async def test_rate_limiting(client, auth_headers):
    """Test API rate limiting"""
    
    responses = []
    for _ in range(10):
        response = client.get("/api/health")
        responses.append(response.status_code)
    
    assert all(status == 200 for status in responses)

@pytest.mark.asyncio
async def test_cors_headers(client):
    """Test CORS headers in response"""
    
    response = client.options("/api/health")
    
    assert "access-control-allow-origin" in response.headers
    assert "access-control-allow-methods" in response.headers