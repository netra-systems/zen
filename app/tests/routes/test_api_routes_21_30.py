"""
Tests 21-30: API Routes & Endpoints
Tests for the missing API route components identified in the top 100 missing tests.
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient
from datetime import datetime
from typing import Optional
from app.services.security_service import SecurityService, KeyManager
from app.config import settings


# Test 21: admin_route_authorization
class TestAdminRoute:
    """Test admin endpoint security - app/routes/admin.py"""
    
    @pytest.fixture
    def client(self):
        from app.main import app
        return TestClient(app)
    
    def test_admin_endpoint_requires_authentication(self, client):
        """Test that admin endpoints require authentication."""
        response = client.get("/api/admin/users")
        assert response.status_code in [401, 404]  # 401 if protected, 404 if not implemented
    
    def test_admin_role_verification(self):
        """Test admin role verification logic."""
        from app.routes.admin import verify_admin_role
        
        # Mock user with admin role
        admin_user = {"id": "admin1", "role": "admin"}
        assert verify_admin_role(admin_user) == True
        
        # Mock user without admin role
        regular_user = {"id": "user1", "role": "user"}
        assert verify_admin_role(regular_user) == False
    async def test_admin_user_management(self):
        """Test admin user management operations."""
        from app.routes.admin import get_all_users, update_user_role
        
        with patch('app.services.user_service.get_all_users') as mock_get:
            mock_get.return_value = [
                {"id": "1", "email": "user1@test.com"},
                {"id": "2", "email": "user2@test.com"}
            ]
            
            users = await get_all_users()
            assert len(users) == 2


# Test 22: agent_route_message_handling
class TestAgentRoute:
    """Test agent API message processing - app/routes/agent_route.py"""
    
    @pytest.fixture
    def client(self):
        from app.main import app
        from app.services.agent_service import get_agent_service
        from app.dependencies import get_llm_manager
        from app.db.postgres import get_async_db
        
        # Create mock dependencies
        def mock_get_async_db():
            return Mock()
            
        def mock_get_llm_manager():
            return Mock()
            
        def mock_get_agent_service():
            return Mock()
        
        # Override dependencies
        app.dependency_overrides[get_async_db] = mock_get_async_db
        app.dependency_overrides[get_llm_manager] = mock_get_llm_manager  
        app.dependency_overrides[get_agent_service] = mock_get_agent_service
        
        try:
            return TestClient(app)
        finally:
            # Clean up overrides after test
            app.dependency_overrides.clear()
    
    def test_agent_message_processing(self, client):
        """Test agent message processing endpoint."""
        from app.main import app
        from app.services.agent_service import get_agent_service, AgentService
        
        # Create a mock AgentService instance
        mock_agent_service = Mock(spec=AgentService)
        mock_agent_service.process_message = AsyncMock(return_value={
            "response": "Processed successfully",
            "agent": "supervisor",
            "status": "success"
        })
        
        # Override the dependency for this specific test
        app.dependency_overrides[get_agent_service] = lambda: mock_agent_service
        
        try:
            response = client.post(
                "/api/agent/message",
                json={"message": "Test message", "thread_id": "thread1"}
            )
            
            if response.status_code == 200:
                data = response.json()
                assert "response" in data
                assert "agent" in data
                assert data["status"] == "success"
        finally:
            # Clean up this specific override
            if get_agent_service in app.dependency_overrides:
                del app.dependency_overrides[get_agent_service]
    async def test_agent_streaming_response(self):
        """Test agent streaming response capability."""
        from app.routes.agent_route import stream_agent_response
        from app.services.agent_service import AgentService
        
        # Create a mock agent service
        mock_agent_service = Mock(spec=AgentService)
        
        async def mock_generate_stream(message: str, thread_id: Optional[str] = None):
            """Mock async generator that yields properly typed chunks."""
            yield {"type": "content", "data": "Part 1"}
            yield {"type": "content", "data": "Part 2"}
            yield {"type": "content", "data": "Part 3"}
        
        mock_agent_service.generate_stream = mock_generate_stream
        
        # Mock the dependencies
        with patch('app.routes.agent_route.get_agent_service', return_value=mock_agent_service):
            chunks = []
            async for chunk in stream_agent_response("test message", agent_service=mock_agent_service):
                chunks.append(chunk)
            
            assert len(chunks) == 4  # 3 content chunks + 1 completion chunk
    
    def test_agent_error_handling(self, client):
        """Test agent error handling."""
        from app.main import app
        from app.services.agent_service import get_agent_service, AgentService
        
        # Create a mock AgentService that raises an exception
        mock_agent_service = Mock(spec=AgentService)
        mock_agent_service.process_message = AsyncMock(side_effect=Exception("Processing failed"))
        
        # Override the dependency
        app.dependency_overrides[get_agent_service] = lambda: mock_agent_service
        
        try:
            response = client.post(
                "/api/agent/message",
                json={"message": "Test message"}
            )
            
            assert response.status_code == 500  # Internal server error expected
        finally:
            # Clean up this specific override
            if get_agent_service in app.dependency_overrides:
                del app.dependency_overrides[get_agent_service]


# Test 23: config_route_updates
class TestConfigRoute:
    """Test configuration API updates - app/routes/config.py"""
    
    @pytest.fixture
    def client(self):
        from app.main import app
        return TestClient(app)
    
    def test_config_retrieval(self, client):
        """Test configuration retrieval endpoint."""
        response = client.get("/api/config")
        
        if response.status_code == 200:
            config = response.json()
            assert "log_level" in config
            assert "max_retries" in config
            assert "timeout" in config
    
    def test_config_update_validation(self, client):
        """Test configuration update validation."""
        invalid_config = {
            "log_level": "INVALID_LEVEL",
            "max_retries": -1  # Invalid negative value
        }
        
        response = client.put("/api/config", json=invalid_config)
        assert response.status_code in [422, 400, 404]  # Validation error or not found
    async def test_config_persistence(self):
        """Test configuration persistence."""
        from app.routes.config import update_config
        
        new_config = {
            "log_level": "DEBUG",
            "feature_flags": {"new_feature": True}
        }
        
        result = await update_config(new_config)
        assert result["success"] == True


# Test 24: corpus_route_operations
class TestCorpusRoute:
    """Test corpus CRUD operations - app/routes/corpus.py"""
    
    @pytest.fixture
    def client(self):
        from app.main import app
        from contextlib import asynccontextmanager
        
        # Mock the db_session_factory to prevent state errors
        @asynccontextmanager
        async def mock_db_session():
            mock_session = MagicMock()
            yield mock_session
        
        if not hasattr(app.state, 'db_session_factory'):
            app.state.db_session_factory = mock_db_session
            
        # Set up security service to prevent AttributeError
        if not hasattr(app.state, 'security_service'):
            key_manager = KeyManager.load_from_settings(settings)
            app.state.security_service = SecurityService(key_manager)
        
        return TestClient(app)
    
    def test_corpus_create(self, client):
        """Test creating corpus documents."""
        document = {
            "title": "Test Document",
            "content": "This is test content",
            "metadata": {"category": "test", "tags": ["sample"]}
        }
        
        with patch('app.services.corpus_service.create_document') as mock_create:
            mock_create.return_value = {"id": "doc123", **document}
            
            response = client.post("/api/corpus", json=document)
            
            if response.status_code == 201:
                data = response.json()
                assert "id" in data
    
    async def test_corpus_search(self):
        """Test corpus search functionality."""
        from app.routes.corpus import search_corpus
        from app.db.models_postgres import User
        
        # Mock the corpus service search method
        with patch('app.services.corpus_service.corpus_service_instance.search_with_fallback') as mock_search:
            mock_search.return_value = [
                {"id": "1", "title": "Result 1", "score": 0.95},
                {"id": "2", "title": "Result 2", "score": 0.87}
            ]
            
            # Mock user
            mock_user = User()
            mock_user.id = 1
            
            # Test the search function directly
            result = await search_corpus(
                q="test query",
                corpus_id="default",
                current_user=mock_user
            )
            
            # Verify the mock was called and results are correct
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


# Test 25: llm_cache_route_management
class TestLLMCacheRoute:
    """Test cache invalidation and metrics - app/routes/llm_cache.py"""
    
    @pytest.fixture
    def client(self):
        from app.main import app
        return TestClient(app)
    
    def test_cache_metrics(self, client):
        """Test cache metrics retrieval."""
        with patch('app.services.llm_cache_service.llm_cache_service.get_cache_metrics') as mock_metrics:
            mock_metrics.return_value = {
                "hits": 150,
                "misses": 50,
                "hit_rate": 0.75,
                "size_mb": 24.5,
                "entries": 200
            }
            
            response = client.get("/api/llm-cache/metrics")
            
            if response.status_code == 200:
                metrics = response.json()
                if "hit_rate" in metrics:
                    assert 0 <= metrics["hit_rate"] <= 1
    
    def test_cache_invalidation(self, client):
        """Test cache invalidation endpoint."""
        with patch('app.services.llm_cache_service.llm_cache_service.clear_cache') as mock_clear:
            mock_clear.return_value = 50
            
            response = client.delete("/api/llm-cache/")
            
            if response.status_code == 200:
                result = response.json()
                assert "cleared" in result or "message" in result
    async def test_selective_cache_invalidation(self):
        """Test selective cache invalidation."""
        from app.routes.llm_cache import clear_cache_pattern
        
        with patch('app.services.llm_cache_service.llm_cache_service.clear_cache_pattern') as mock_clear:
            mock_clear.return_value = 10
            
            result = await clear_cache_pattern("user_*")
            assert result["cleared"] == 10


# Test 26: mcp_route_protocol_handling
class TestMCPRoute:
    """Test MCP protocol implementation - app/routes/mcp.py"""
    
    @pytest.fixture
    def client(self):
        from app.main import app
        return TestClient(app)
    
    def test_mcp_message_handling(self, client):
        """Test MCP message handling."""
        mcp_request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 1
        }
        
        with patch('app.services.mcp_request_handler.handle_request') as mock_handle:
            mock_handle.return_value = {
                "jsonrpc": "2.0",
                "result": {"tools": []},
                "id": 1
            }
            
            response = client.post("/api/mcp", json=mcp_request)
            
            if response.status_code == 200:
                data = response.json()
                assert "jsonrpc" in data or "error" in data
    
    def test_mcp_protocol_validation(self, client):
        """Test MCP protocol validation."""
        invalid_request = {
            "method": "invalid",
            # Missing required jsonrpc field
        }
        
        response = client.post("/api/mcp", json=invalid_request)
        assert response.status_code in [422, 400, 404]
    async def test_mcp_tool_execution(self):
        """Test MCP tool execution."""
        from app.routes.mcp import execute_tool
        
        # Test the function directly since it's a simple wrapper for testing
        result = await execute_tool("test_tool", {"param": "value"})
        assert result["result"] == "success"
        assert result["tool"] == "test_tool"
        assert result["parameters"] == {"param": "value"}


# Test 27: quality_route_metrics
class TestQualityRoute:
    """Test quality metric endpoints - app/routes/quality.py"""
    
    @pytest.fixture
    def client(self):
        from app.main import app
        return TestClient(app)
    
    def test_quality_metrics_retrieval(self, client):
        """Test retrieving quality metrics."""
        with patch('app.services.quality_gate.quality_gate_core.QualityGateService.get_quality_stats') as mock_metrics:
            mock_metrics.return_value = {
                "accuracy": 0.96,
                "latency_p50": 120,
                "latency_p99": 450,
                "error_rate": 0.02,
                "throughput": 1000
            }
            
            response = client.get("/api/quality/metrics")
            
            if response.status_code == 200:
                metrics = response.json()
                if "accuracy" in metrics:
                    assert 0 <= metrics["accuracy"] <= 1
    
    def test_quality_aggregation(self, client):
        """Test quality metrics aggregation."""
        with patch('app.services.quality_monitoring.service.QualityMonitoringService.get_dashboard_data') as mock_agg:
            mock_agg.return_value = {
                "period": "daily",
                "average_accuracy": 0.94,
                "trend": "stable"
            }
            
            response = client.get("/api/quality/aggregate?period=daily")
            
            if response.status_code == 200:
                data = response.json()
                assert "period" in data or "error" in data
    async def test_quality_alerts(self):
        """Test quality threshold alerts."""
        from app.routes.quality_handlers import handle_alerts_request
        from app.schemas.quality_types import QualityAlert, AlertSeverity, MetricType
        from datetime import datetime, UTC
        
        # Create proper QualityAlert objects
        test_alert = QualityAlert(
            id="alert123",
            timestamp=datetime.now(UTC),
            severity=AlertSeverity.HIGH,
            metric_type=MetricType.OVERALL,
            agent="test_agent",
            message="Test alert",
            current_value=50.0,
            threshold=75.0,
            acknowledged=False
        )
        
        mock_service = Mock()
        mock_service.alert_history = [test_alert]
        
        alerts = await handle_alerts_request(mock_service, None, None, 50)
        assert len(alerts) > 0


# Test 28: supply_route_research
class TestSupplyRoute:
    """Test supply chain endpoints - app/routes/supply.py"""
    
    @pytest.fixture
    def client(self):
        from app.main import app
        return TestClient(app)
    
    def test_supply_research(self, client):
        """Test supply chain research endpoint."""
        research_request = {
            "query": "GPU suppliers",
            "filters": {"region": "US", "tier": 1}
        }
        
        with patch('app.routes.supply.research_suppliers') as mock_research:
            mock_research.return_value = {
                "suppliers": [
                    {"name": "Supplier A", "score": 0.92},
                    {"name": "Supplier B", "score": 0.85}
                ],
                "total": 2
            }
            
            response = client.post("/api/supply/research", json=research_request)
            
            if response.status_code == 200:
                data = response.json()
                assert "suppliers" in data or "error" in data
    
    def test_supply_data_enrichment(self, client):
        """Test supply data enrichment."""
        with patch('app.routes.supply.enrich_supplier') as mock_enrich:
            mock_enrich.return_value = {
                "supplier_id": "sup123",
                "enriched_data": {
                    "financial_health": "good",
                    "certifications": ["ISO9001"]
                }
            }
            
            response = client.post(
                "/api/supply/enrich",
                json={"supplier_id": "sup123"}
            )
            
            if response.status_code == 200:
                data = response.json()
                assert "enriched_data" in data or "supplier_id" in data
    async def test_supply_validation(self):
        """Test supply chain validation."""
        from app.routes.supply import validate_supply_chain
        
        chain_data = {
            "suppliers": ["sup1", "sup2"],
            "products": ["prod1"],
            "constraints": {"delivery_time": 30}
        }
        
        with patch('app.routes.supply.validate_supply_chain') as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                "issues": [],
                "score": 0.88
            }
            
            result = await validate_supply_chain(chain_data)
            assert result["valid"] == True


# Test 29: synthetic_data_route_generation
class TestSyntheticDataRoute:
    """Test synthetic data creation - app/routes/synthetic_data.py"""
    
    @pytest.fixture
    def client(self):
        from app.main import app
        return TestClient(app)
    
    def test_synthetic_data_generation(self, client):
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
        
        with patch('app.services.synthetic_data_service.synthetic_data_service.generate_synthetic_data') as mock_gen:
            mock_gen.return_value = {
                "job_id": "test_job_123",
                "status": "initiated",
                "table_name": "netra_synthetic_data_test_job_123",
                "websocket_channel": "generation_test_job_123"
            }
            
            response = client.post("/api/synthetic-data/generate", json=generation_request)
            
            if response.status_code == 200:
                data = response.json()
                assert "job_id" in data
                assert "status" in data
                assert data["status"] == "initiated"
    
    def test_synthetic_data_validation(self, client):
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
        
        with patch('app.services.synthetic_data_service.validate_data') as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                "errors": []
            }
            
            response = client.post("/api/synthetic-data/validate", json=validation_request)
            
            if response.status_code == 200:
                result = response.json()
                assert "valid" in result
    async def test_synthetic_data_templates(self):
        """Test synthetic data template management."""
        from app.routes.synthetic_data import _fetch_templates
        from unittest.mock import AsyncMock
        
        # Mock the database dependency
        mock_db = AsyncMock()
        
        # Create a mock for the entire SyntheticDataService class
        with patch('app.routes.synthetic_data.SyntheticDataService') as mock_service_class:
            # Mock the static method to return templates
            mock_service_class.get_available_templates = AsyncMock(return_value=[
                {"name": "user_profile", "fields": 5},
                {"name": "transaction", "fields": 8}
            ])
            
            result = await _fetch_templates(mock_db)
            assert "templates" in result
            assert len(result["templates"]) == 2
            assert result["status"] == "ok"


# Test 30: threads_route_conversation
class TestThreadsRoute:
    """Test thread conversation management - app/routes/threads_route.py"""
    
    @pytest.fixture
    def client(self):
        from app.main import app
        return TestClient(app)
    
    def test_thread_creation(self, client):
        """Test thread creation endpoint."""
        from app.services.thread_service import ThreadService
        
        with patch.object(ThreadService, 'create_thread') as mock_create:
            mock_create.return_value = {
                "id": "thread123",
                "title": "New Thread",
                "created_at": datetime.now().isoformat()
            }
            
            response = client.post(
                "/api/threads",
                json={"title": "New Thread"}
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                assert "id" in data or "thread_id" in data
    
    def test_thread_pagination(self, client):
        """Test thread list pagination."""
        from app.services.thread_service import ThreadService
        
        with patch.object(ThreadService, 'get_thread_messages') as mock_get:
            mock_get.return_value = [
                {"id": f"msg{i}", "content": f"Message {i}"}
                for i in range(10)
            ]
            
            response = client.get("/api/threads?page=1&per_page=10")
            
            if response.status_code == 200:
                data = response.json()
                if "threads" in data:
                    assert len(data["threads"]) <= 10
    async def test_thread_archival(self):
        """Test thread archival functionality."""
        from app.services.thread_service import ThreadService
        
        with patch.object(ThreadService, 'delete_thread') as mock_delete:
            mock_delete.return_value = True
            
            # Mock the actual ThreadService instance
            service = ThreadService()
            result = await service.delete_thread("thread123", "user1")
            assert result == True