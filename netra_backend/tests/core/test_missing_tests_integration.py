"""
Integration Tests - Focused module for API routes and cross-service integration
Tests 21-30 from original missing tests covering:
- Admin route authorization
- Agent route message handling  
- Config route updates
- Corpus route operations
- LLM cache route management
- MCP route protocol handling
- Quality route metrics
- Supply route research
- Synthetic data route generation
- Threads route conversation management
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


class TestAdminRouteIntegration:
    """Test admin endpoint security integration."""
    
    @pytest.fixture
    def client(self):
        from netra_backend.app.routes.mcp.main import app
        return TestClient(app)
    
    def test_admin_endpoint_requires_auth(self, client):
        """Test admin endpoints require authentication."""
        response = client.get("/api/admin/users")
        assert response.status_code == 401
    
    def test_admin_endpoint_requires_admin_role(self, client):
        """Test admin endpoints require admin role."""
        user_token = "Bearer user_token_456"
        with patch('app.auth.verify_token') as mock_verify:
            mock_verify.return_value = {"user_id": "123", "role": "user"}
            response = client.get("/api/admin/users", headers={"Authorization": user_token})
            assert response.status_code == 403


class TestAgentRouteIntegration:
    """Test agent API message processing integration."""
    
    @pytest.fixture
    def client(self):
        from netra_backend.app.routes.mcp.main import app
        return TestClient(app)
    
    def test_agent_message_processing(self, client):
        """Test agent processes messages correctly."""
        with patch('app.services.agent_service.process_message') as mock_process:
            mock_process.return_value = {"response": "Processed"}
            response = client.post("/api/agent/message", json={"message": "Test message"})
            assert response.status_code == 200
            assert response.json()["response"] == "Processed"
    
    def test_agent_error_handling(self, client):
        """Test agent handles errors gracefully."""
        with patch('app.services.agent_service.process_message') as mock_process:
            mock_process.side_effect = Exception("Processing error")
            response = client.post("/api/agent/message", json={"message": "Test message"})
            assert response.status_code == 500
            assert "error" in response.json()


class TestConfigRouteIntegration:
    """Test configuration API updates integration."""
    
    @pytest.fixture
    def client(self):
        from netra_backend.app.routes.mcp.main import app
        return TestClient(app)
    
    def test_config_update_validation(self, client):
        """Test configuration updates are validated."""
        invalid_config = {"invalid_field": "value"}
        response = client.put("/api/config", json=invalid_config)
        assert response.status_code == 422
    
    def test_config_retrieval(self, client):
        """Test configuration can be retrieved."""
        with patch('app.services.config_service.get_config') as mock_get:
            mock_get.return_value = {"log_level": "INFO"}
            response = client.get("/api/config")
            assert response.status_code == 200
            assert response.json()["log_level"] == "INFO"


class TestCorpusRouteIntegration:
    """Test corpus CRUD operations integration."""
    
    @pytest.fixture
    def client(self):
        from netra_backend.app.routes.mcp.main import app
        return TestClient(app)
    
    def test_corpus_create_operation(self, client):
        """Test creating corpus entries."""
        corpus_data = {"title": "Test Document", "content": "Test content"}
        with patch('app.services.corpus_service.create_document') as mock_create:
            mock_create.return_value = {"id": "123", **corpus_data}
            response = client.post("/api/corpus", json=corpus_data)
            assert response.status_code == 201
            assert response.json()["id"] == "123"
    
    def test_corpus_search_functionality(self, client):
        """Test corpus search."""
        with patch('app.services.corpus_service.search') as mock_search:
            mock_search.return_value = [{"id": "1", "title": "Result 1", "score": 0.9}]
            response = client.get("/api/corpus/search?q=test")
            assert response.status_code == 200
            results = response.json()
            assert len(results) == 1


class TestLLMCacheRouteIntegration:
    """Test cache invalidation and metrics integration."""
    
    @pytest.fixture
    def client(self):
        from netra_backend.app.routes.mcp.main import app
        return TestClient(app)
    
    def test_cache_invalidation(self, client):
        """Test cache can be invalidated."""
        with patch('app.services.llm_cache_service.invalidate') as mock_invalidate:
            mock_invalidate.return_value = {"cleared": 10}
            response = client.delete("/api/llm-cache")
            assert response.status_code == 200
            assert response.json()["cleared"] == 10


class TestMCPRouteIntegration:
    """Test MCP protocol implementation integration."""
    
    @pytest.fixture
    def client(self):
        from netra_backend.app.routes.mcp.main import app
        return TestClient(app)
    
    def test_mcp_message_routing(self, client):
        """Test MCP message routing."""
        mcp_message = {"type": "request", "method": "test_method", "params": {"key": "value"}}
        with patch('app.services.mcp_service.handle_message') as mock_handle:
            mock_handle.return_value = {"status": "success"}
            response = client.post("/api/mcp", json=mcp_message)
            assert response.status_code == 200
            assert response.json()["status"] == "success"


class TestQualityRouteIntegration:
    """Test quality metric endpoints integration."""
    
    @pytest.fixture
    def client(self):
        from netra_backend.app.routes.mcp.main import app
        return TestClient(app)
    
    def test_quality_metrics_retrieval(self, client):
        """Test retrieving quality metrics."""
        with patch('app.services.quality_service.get_metrics') as mock_metrics:
            mock_metrics.return_value = {"accuracy": 0.95, "error_rate": 0.01}
            response = client.get("/api/quality/metrics")
            assert response.status_code == 200
            metrics = response.json()
            assert metrics["accuracy"] > 0.9


class TestSupplyRouteIntegration:
    """Test supply chain endpoints integration."""
    
    @pytest.fixture
    def client(self):
        from netra_backend.app.routes.mcp.main import app
        return TestClient(app)
    
    def test_supply_research_endpoint(self, client):
        """Test supply chain research endpoint."""
        research_request = {"query": "GPU suppliers", "region": "US", "max_results": 10}
        with patch('app.services.supply_service.research') as mock_research:
            mock_research.return_value = {"suppliers": [{"name": "Supplier A", "score": 0.9}]}
            response = client.post("/api/supply/research", json=research_request)
            assert response.status_code == 200
            assert len(response.json()["suppliers"]) == 1


class TestSyntheticDataRouteIntegration:
    """Test synthetic data creation integration."""
    
    @pytest.fixture
    def client(self):
        from netra_backend.app.routes.mcp.main import app
        return TestClient(app)
    
    def test_synthetic_data_generation(self, client):
        """Test synthetic data generation endpoint."""
        generation_request = {"schema": {"user_id": "uuid", "name": "name"}, "count": 100}
        with patch('app.services.synthetic_data_service.generate') as mock_generate:
            mock_generate.return_value = {"data": [{"user_id": "123", "name": "John"}] * 100}
            response = client.post("/api/synthetic-data/generate", json=generation_request)
            assert response.status_code == 200


class TestThreadsRouteIntegration:
    """Test thread conversation management integration."""
    
    @pytest.fixture
    def client(self):
        from netra_backend.app.routes.mcp.main import app
        return TestClient(app)
    
    def test_thread_pagination(self, client):
        """Test thread list pagination."""
        with patch('app.services.thread_service.get_threads') as mock_get:
            mock_get.return_value = {"threads": [{"id": f"thread_{i}"} for i in range(10)]}
            response = client.get("/api/threads?page=1&per_page=10")
            assert response.status_code == 200
            data = response.json()
            assert len(data["threads"]) == 10


class TestCrossServiceIntegration:
    """Test cross-service integration scenarios."""
    
    @pytest.fixture
    def client(self):
        from netra_backend.app.routes.mcp.main import app
        return TestClient(app)
    
    def test_agent_corpus_integration(self, client):
        """Test agent can access corpus data."""
        with patch('app.services.agent_service.process_message') as mock_agent:
            with patch('app.services.corpus_service.search') as mock_corpus:
                mock_corpus.return_value = [{"content": "Test result"}]
                mock_agent.return_value = {"response": "Found results"}
                response = client.post("/api/agent/message", json={"message": "Search corpus"})
                assert response.status_code == 200
    
    def test_quality_metrics_from_multiple_services(self, client):
        """Test quality metrics aggregate from multiple services."""
        with patch('app.services.quality_service.get_metrics') as mock_quality:
            mock_quality.return_value = {"agent_accuracy": 0.95, "corpus_coverage": 0.88}
            response = client.get("/api/quality/metrics")
            assert response.status_code == 200
            metrics = response.json()
            assert "agent_accuracy" in metrics


# Run integration tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-k", "integration"])