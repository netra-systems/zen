"""
Tests for MCP Resource Manager

Test resource registration, discovery, and access.
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from app.mcp.resources.resource_manager import ResourceManager, Resource, ResourceAccess
from app.core.exceptions import NetraException


class TestResource:
    """Test Resource model"""
    
    def test_resource_creation(self):
        """Test resource creation"""
        resource = Resource(
            uri="netra://test/resource",
            name="Test Resource",
            description="Test description",
            mimeType="application/json",
            metadata={"key": "value"},
            requires_auth=False,
            permissions=["read", "write"]
        )
        
        assert resource.uri == "netra://test/resource"
        assert resource.name == "Test Resource"
        assert resource.description == "Test description"
        assert resource.mimeType == "application/json"
        assert resource.metadata == {"key": "value"}
        assert resource.requires_auth is False
        assert resource.permissions == ["read", "write"]
        
    def test_resource_defaults(self):
        """Test resource default values"""
        resource = Resource(
            uri="netra://test",
            name="Test"
        )
        
        assert resource.description is None
        assert resource.mimeType == "application/json"
        assert resource.metadata == {}
        assert resource.requires_auth is True
        assert resource.permissions == []


class TestResourceAccess:
    """Test ResourceAccess model"""
    
    def test_access_creation(self):
        """Test access record creation"""
        access = ResourceAccess(
            resource_uri="netra://test",
            session_id="session123",
            access_type="write",
            success=False,
            error="Permission denied"
        )
        
        assert access.resource_uri == "netra://test"
        assert access.session_id == "session123"
        assert access.access_type == "write"
        assert access.success is False
        assert access.error == "Permission denied"
        assert isinstance(access.accessed_at, datetime)
        
    def test_access_defaults(self):
        """Test access record defaults"""
        access = ResourceAccess(
            resource_uri="netra://test",
            session_id=None
        )
        
        assert access.access_type == "read"
        assert access.success is True
        assert access.error is None


class TestResourceManager:
    """Test resource manager functionality"""
    
    @pytest.fixture
    def manager(self):
        """Create resource manager"""
        return ResourceManager()
        
    def test_manager_initialization(self, manager):
        """Test manager initialization with built-in resources"""
        assert len(manager.resources) > 0
        
        # Check key resources are registered
        assert "netra://threads" in manager.resources
        assert "netra://threads/{thread_id}" in manager.resources
        assert "netra://agents" in manager.resources
        assert "netra://corpus" in manager.resources
        assert "netra://metrics/workload" in manager.resources
        assert "netra://synthetic-data/schemas" in manager.resources
        assert "netra://supply/models" in manager.resources
        
    def test_register_resource(self, manager):
        """Test registering a new resource"""
        resource = Resource(
            uri="netra://custom/resource",
            name="Custom Resource"
        )
        
        manager.register_resource(resource)
        
        assert "netra://custom/resource" in manager.resources
        assert manager.resources["netra://custom/resource"] == resource
        
    def test_register_resource_overwrite(self, manager, caplog):
        """Test overwriting existing resource"""
        resource1 = Resource(uri="netra://test", name="First")
        resource2 = Resource(uri="netra://test", name="Second")
        
        manager.register_resource(resource1)
        manager.register_resource(resource2)
        
        assert manager.resources["netra://test"].name == "Second"
        assert "Overwriting existing resource" in caplog.text
        
    def test_unregister_resource(self, manager):
        """Test unregistering a resource"""
        resource = Resource(uri="netra://temp", name="Temp")
        manager.register_resource(resource)
        
        assert "netra://temp" in manager.resources
        
        manager.unregister_resource("netra://temp")
        
        assert "netra://temp" not in manager.resources
        
    @pytest.mark.asyncio
    async def test_list_resources(self, manager):
        """Test listing available resources"""
        resources = await manager.list_resources()
        
        assert isinstance(resources, list)
        assert len(resources) > 0
        
        # Check resource format
        resource = resources[0]
        assert "uri" in resource
        assert "name" in resource
        assert "mimeType" in resource
        
    @pytest.mark.asyncio
    async def test_list_resources_with_description(self, manager):
        """Test listing resources includes description when present"""
        resource = Resource(
            uri="netra://test",
            name="Test",
            description="Test description"
        )
        manager.register_resource(resource)
        
        resources = await manager.list_resources()
        test_resource = next(r for r in resources if r["uri"] == "netra://test")
        
        assert "description" in test_resource
        assert test_resource["description"] == "Test description"
        
    @pytest.mark.asyncio
    async def test_read_resource_invalid_scheme(self, manager):
        """Test reading resource with invalid scheme"""
        with pytest.raises(NetraException) as exc_info:
            await manager.read_resource("http://invalid/scheme")
        
        assert "Invalid resource scheme" in str(exc_info.value)
        
    @pytest.mark.asyncio
    async def test_read_resource_unknown_path(self, manager):
        """Test reading resource with unknown path"""
        with pytest.raises(NetraException) as exc_info:
            await manager.read_resource("netra://unknown/path")
        
        assert "Unknown resource path" in str(exc_info.value)
        
    @pytest.mark.asyncio
    async def test_read_threads_resource_list(self, manager):
        """Test reading threads list resource"""
        content = await manager.read_resource("netra://threads")
        
        assert isinstance(content, list)
        assert len(content) > 0
        assert content[0]["type"] == "text"
        
        threads = json.loads(content[0]["text"])
        assert isinstance(threads, list)
        assert "id" in threads[0]
        assert "title" in threads[0]
        
    @pytest.mark.asyncio
    async def test_read_threads_resource_specific(self, manager):
        """Test reading specific thread resource"""
        content = await manager.read_resource("netra://threads/thread123")
        
        assert isinstance(content, list)
        assert "thread123" in content[0]["text"]
        
    @pytest.mark.asyncio
    async def test_read_threads_resource_invalid_path(self, manager):
        """Test reading threads with invalid path"""
        with pytest.raises(NetraException) as exc_info:
            await manager.read_resource("netra://threads/too/many/parts")
        
        assert "Invalid threads resource path" in str(exc_info.value)
        
    @pytest.mark.asyncio
    async def test_read_agents_resource_list(self, manager):
        """Test reading agents list resource"""
        content = await manager.read_resource("netra://agents")
        
        assert isinstance(content, list)
        agents_data = json.loads(content[0]["text"])
        assert "agents" in agents_data
        assert isinstance(agents_data["agents"], list)
        
    @pytest.mark.asyncio
    async def test_read_agents_resource_state(self, manager):
        """Test reading agent state resource"""
        content = await manager.read_resource("netra://agents/TestAgent/state")
        
        assert isinstance(content, list)
        assert "TestAgent" in content[0]["text"]
        
    @pytest.mark.asyncio
    async def test_read_agents_resource_invalid_path(self, manager):
        """Test reading agents with invalid path"""
        with pytest.raises(NetraException) as exc_info:
            await manager.read_resource("netra://agents/invalid/path/structure")
        
        assert "Invalid agents resource path" in str(exc_info.value)
        
    @pytest.mark.asyncio
    async def test_read_corpus_resource(self, manager):
        """Test reading corpus resource"""
        content = await manager.read_resource("netra://corpus")
        
        assert isinstance(content, list)
        assert "Corpus overview" in content[0]["text"]
        
    @pytest.mark.asyncio
    async def test_read_corpus_search_resource(self, manager):
        """Test reading corpus search resource"""
        content = await manager.read_resource("netra://corpus/search")
        
        assert isinstance(content, list)
        assert "search interface" in content[0]["text"]
        
    @pytest.mark.asyncio
    async def test_read_metrics_workload_resource(self, manager):
        """Test reading workload metrics resource"""
        content = await manager.read_resource("netra://metrics/workload")
        
        assert isinstance(content, list)
        metrics = json.loads(content[0]["text"])
        assert "avg_latency_ms" in metrics
        assert "requests_per_second" in metrics
        
    @pytest.mark.asyncio
    async def test_read_metrics_optimization_resource(self, manager):
        """Test reading optimization metrics resource"""
        content = await manager.read_resource("netra://metrics/optimization")
        
        assert isinstance(content, list)
        metrics = json.loads(content[0]["text"])
        assert "cost_reduction" in metrics
        assert "latency_improvement" in metrics
        
    @pytest.mark.asyncio
    async def test_read_metrics_invalid_type(self, manager):
        """Test reading metrics with invalid type"""
        with pytest.raises(NetraException) as exc_info:
            await manager.read_resource("netra://metrics/invalid")
        
        assert "Unknown metric type" in str(exc_info.value)
        
    @pytest.mark.asyncio
    async def test_read_synthetic_data_schemas(self, manager):
        """Test reading synthetic data schemas"""
        content = await manager.read_resource("netra://synthetic-data/schemas")
        
        assert isinstance(content, list)
        data = json.loads(content[0]["text"])
        assert "schemas" in data
        assert isinstance(data["schemas"], list)
        
    @pytest.mark.asyncio
    async def test_read_synthetic_data_generated(self, manager):
        """Test reading generated synthetic data"""
        content = await manager.read_resource("netra://synthetic-data/generated")
        
        assert isinstance(content, list)
        assert "generated" in content[0]["text"].lower()
        
    @pytest.mark.asyncio
    async def test_read_supply_models(self, manager):
        """Test reading supply models"""
        content = await manager.read_resource("netra://supply/models")
        
        assert isinstance(content, list)
        data = json.loads(content[0]["text"])
        assert "models" in data
        assert isinstance(data["models"], list)
        assert "name" in data["models"][0]
        assert "provider" in data["models"][0]
        
    @pytest.mark.asyncio
    async def test_read_supply_providers(self, manager):
        """Test reading supply providers"""
        content = await manager.read_resource("netra://supply/providers")
        
        assert isinstance(content, list)
        data = json.loads(content[0]["text"])
        assert "providers" in data
        assert isinstance(data["providers"], list)
        
    @pytest.mark.asyncio
    async def test_access_logging_success(self, manager):
        """Test access logging for successful read"""
        await manager.read_resource("netra://threads", "session123")
        
        assert len(manager.access_log) == 1
        access = manager.access_log[0]
        assert access.resource_uri == "netra://threads"
        assert access.session_id == "session123"
        assert access.access_type == "read"
        assert access.success is True
        assert access.error is None
        
    @pytest.mark.asyncio
    async def test_access_logging_error(self, manager):
        """Test access logging for failed read"""
        try:
            await manager.read_resource("netra://invalid/path", "session456")
        except:
            pass
            
        assert len(manager.access_log) == 1
        access = manager.access_log[0]
        assert access.resource_uri == "netra://invalid/path"
        assert access.session_id == "session456"
        assert access.success is False
        assert access.error is not None
        
    @pytest.mark.asyncio
    async def test_shutdown(self, manager):
        """Test manager shutdown"""
        manager.register_resource(Resource(uri="netra://test", name="Test"))
        manager.access_log.append(ResourceAccess(
            resource_uri="netra://test",
            session_id="session"
        ))
        
        await manager.shutdown()
        
        assert len(manager.resources) == 0
        assert len(manager.access_log) == 0