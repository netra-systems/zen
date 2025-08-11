"""
Tests for MCP Service

Test MCP service integration with Netra platform.
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from app.services.mcp_service import MCPService, MCPClient, MCPToolExecution
from app.core.exceptions import NetraException


class TestMCPClient:
    """Test MCP Client model"""
    
    def test_client_creation(self):
        """Test client creation"""
        client = MCPClient(
            name="Test Client",
            client_type="claude",
            api_key_hash="hashed_key",
            permissions=["read", "write"],
            metadata={"version": "1.0"}
        )
        
        assert client.id != None
        assert client.name == "Test Client"
        assert client.client_type == "claude"
        assert client.api_key_hash == "hashed_key"
        assert client.permissions == ["read", "write"]
        assert client.metadata == {"version": "1.0"}
        assert isinstance(client.created_at, datetime)
        assert isinstance(client.last_active, datetime)
        
    def test_client_defaults(self):
        """Test client default values"""
        client = MCPClient(
            name="Test",
            client_type="cursor"
        )
        
        assert client.api_key_hash == None
        assert client.permissions == []
        assert client.metadata == {}


class TestMCPToolExecution:
    """Test MCP Tool Execution model"""
    
    def test_execution_creation(self):
        """Test execution record creation"""
        execution = MCPToolExecution(
            session_id="session123",
            tool_name="test_tool",
            input_params={"arg": "value"},
            output_result={"result": "success"},
            execution_time_ms=150,
            status="success"
        )
        
        assert execution.id != None
        assert execution.session_id == "session123"
        assert execution.tool_name == "test_tool"
        assert execution.input_params == {"arg": "value"}
        assert execution.output_result == {"result": "success"}
        assert execution.execution_time_ms == 150
        assert execution.status == "success"
        assert execution.error == None
        assert isinstance(execution.created_at, datetime)


class TestMCPService:
    """Test MCP service functionality"""
    
    @pytest.fixture
    def mock_services(self):
        """Create mock services"""
        return {
            "agent_service": AsyncMock(),
            "thread_service": AsyncMock(),
            "corpus_service": AsyncMock(),
            "synthetic_data_service": AsyncMock(),
            "security_service": Mock(),
            "supply_catalog_service": AsyncMock()
        }
        
    @pytest.fixture
    def mcp_service(self, mock_services):
        """Create MCP service"""
        return MCPService(**mock_services)
        
    def test_service_initialization(self, mcp_service):
        """Test service initialization"""
        assert mcp_service.agent_service != None
        assert mcp_service.thread_service != None
        assert mcp_service.corpus_service != None
        assert mcp_service.synthetic_data_service != None
        assert mcp_service.security_service != None
        assert mcp_service.supply_catalog_service != None
        assert mcp_service.mcp_server != None
        
    def test_tool_registration(self, mcp_service):
        """Test that Netra tools are registered"""
        registry = mcp_service.mcp_server.tool_registry
        
        # Check handlers are overridden
        assert registry.tools["run_agent"].handler == mcp_service.execute_agent
        assert registry.tools["get_agent_status"].handler == mcp_service.get_agent_status
        assert registry.tools["list_agents"].handler == mcp_service.list_available_agents
        assert registry.tools["analyze_workload"].handler == mcp_service.analyze_workload
        assert registry.tools["optimize_prompt"].handler == mcp_service.optimize_prompt
        assert registry.tools["query_corpus"].handler == mcp_service.query_corpus
        assert registry.tools["generate_synthetic_data"].handler == mcp_service.generate_synthetic_data
        assert registry.tools["create_thread"].handler == mcp_service.create_thread
        assert registry.tools["get_thread_history"].handler == mcp_service.get_thread_history
        
        # Check additional tools
        assert "get_supply_catalog" in registry.tools
        assert "execute_optimization_pipeline" in registry.tools
        
    def test_resource_registration(self, mcp_service):
        """Test that additional resources are registered"""
        manager = mcp_service.mcp_server.resource_manager
        
        assert "netra://optimization/history" in manager.resources
        assert "netra://config/models" in manager.resources
        
    @pytest.mark.asyncio
    async def test_execute_agent(self, mcp_service, mock_services):
        """Test agent execution"""
        mock_services["thread_service"].create_thread.return_value = "thread123"
        mock_services["agent_service"].execute_agent.return_value = {
            "run_id": "run456",
            "response": "Agent response"
        }
        
        result = await mcp_service.execute_agent({
            "agent_name": "TestAgent",
            "input_data": {"test": "data"},
            "config": {"option": "value"}
        }, "session789")
        
        assert result["type"] == "text"
        response = json.loads(result["text"])
        assert response["status"] == "success"
        assert response["thread_id"] == "thread123"
        assert response["run_id"] == "run456"
        
        # Verify calls
        mock_services["thread_service"].create_thread.assert_called_once()
        mock_services["agent_service"].execute_agent.assert_called_once_with(
            agent_name="TestAgent",
            thread_id="thread123",
            input_data={"test": "data"},
            config={"option": "value"}
        )
        
    @pytest.mark.asyncio
    async def test_execute_agent_error(self, mcp_service, mock_services):
        """Test agent execution error handling"""
        mock_services["thread_service"].create_thread.side_effect = Exception("Thread error")
        
        result = await mcp_service.execute_agent({
            "agent_name": "TestAgent",
            "input_data": {}
        }, None)
        
        assert result["type"] == "text"
        assert "Error executing agent" in result["text"]
        assert "Thread error" in result["text"]
        
    @pytest.mark.asyncio
    async def test_get_agent_status(self, mcp_service, mock_services):
        """Test getting agent status"""
        mock_services["agent_service"].get_run_status.return_value = {
            "status": "completed",
            "result": "Success"
        }
        
        result = await mcp_service.get_agent_status({
            "run_id": "run123"
        }, None)
        
        assert result["type"] == "text"
        status = json.loads(result["text"])
        assert status["status"] == "completed"
        
    @pytest.mark.asyncio
    async def test_list_available_agents(self, mcp_service, mock_services):
        """Test listing agents"""
        mock_services["agent_service"].list_agents.return_value = [
            {"name": "Agent1", "description": "First agent"},
            {"name": "Agent2", "description": "Second agent"}
        ]
        
        result = await mcp_service.list_available_agents({
            "category": "test"
        }, None)
        
        assert result["type"] == "text"
        agents = json.loads(result["text"])
        assert len(agents) == 2
        assert agents[0]["name"] == "Agent1"
        
    @pytest.mark.asyncio
    async def test_analyze_workload(self, mcp_service, mock_services):
        """Test workload analysis"""
        mock_services["agent_service"].analyze_workload.return_value = {
            "cost": 100,
            "latency": 250
        }
        
        result = await mcp_service.analyze_workload({
            "workload_data": {"test": "data"},
            "metrics": ["cost", "latency"]
        }, None)
        
        assert result["type"] == "text"
        analysis = json.loads(result["text"])
        assert analysis["cost"] == 100
        assert analysis["latency"] == 250
        
    @pytest.mark.asyncio
    async def test_optimize_prompt(self, mcp_service, mock_services):
        """Test prompt optimization"""
        mock_services["agent_service"].optimize_prompt.return_value = {
            "optimized": "Better prompt",
            "savings": "30%"
        }
        
        result = await mcp_service.optimize_prompt({
            "prompt": "Original prompt",
            "target": "cost",
            "model": "claude"
        }, None)
        
        assert result["type"] == "text"
        optimization = json.loads(result["text"])
        assert optimization["optimized"] == "Better prompt"
        
    @pytest.mark.asyncio
    async def test_query_corpus(self, mcp_service, mock_services):
        """Test corpus querying"""
        mock_services["corpus_service"].search.return_value = [
            {"id": "doc1", "score": 0.9},
            {"id": "doc2", "score": 0.8}
        ]
        
        result = await mcp_service.query_corpus({
            "query": "test query",
            "limit": 5,
            "filters": {"type": "document"}
        }, None)
        
        assert result["type"] == "text"
        results = json.loads(result["text"])
        assert len(results) == 2
        assert results[0]["id"] == "doc1"
        
    @pytest.mark.asyncio
    async def test_generate_synthetic_data(self, mcp_service, mock_services):
        """Test synthetic data generation"""
        mock_services["synthetic_data_service"].generate.return_value = [
            {"id": 1, "name": "Test1"},
            {"id": 2, "name": "Test2"}
        ]
        
        result = await mcp_service.generate_synthetic_data({
            "schema": {"type": "object"},
            "count": 2,
            "format": "json"
        }, None)
        
        assert "Generated 2 records" in result["text"]
        assert result["data"] == [
            {"id": 1, "name": "Test1"},
            {"id": 2, "name": "Test2"}
        ]
        
    @pytest.mark.asyncio
    async def test_create_thread(self, mcp_service, mock_services):
        """Test thread creation"""
        mock_services["thread_service"].create_thread.return_value = "thread123"
        
        result = await mcp_service.create_thread({
            "title": "Test Thread",
            "metadata": {"key": "value"}
        }, "session456")
        
        assert result["type"] == "text"
        response = json.loads(result["text"])
        assert response["thread_id"] == "thread123"
        assert response["title"] == "Test Thread"
        assert response["created"] == True
        
        # Check metadata includes session
        call_args = mock_services["thread_service"].create_thread.call_args
        assert call_args[1]["metadata"]["mcp_session"] == "session456"
        
    @pytest.mark.asyncio
    async def test_get_thread_history(self, mcp_service, mock_services):
        """Test getting thread history"""
        mock_services["thread_service"].get_thread_messages.return_value = [
            {"id": "msg1", "content": "Message 1"},
            {"id": "msg2", "content": "Message 2"}
        ]
        
        result = await mcp_service.get_thread_history({
            "thread_id": "thread123",
            "limit": 10
        }, None)
        
        assert result["type"] == "text"
        messages = json.loads(result["text"])
        assert len(messages) == 2
        assert messages[0]["id"] == "msg1"
        
    @pytest.mark.asyncio
    async def test_get_supply_catalog(self, mcp_service, mock_services):
        """Test getting supply catalog"""
        mock_services["supply_catalog_service"].get_catalog.return_value = {
            "models": ["model1", "model2"],
            "providers": ["provider1", "provider2"]
        }
        
        result = await mcp_service.get_supply_catalog({
            "filter": "available"
        }, None)
        
        assert result["type"] == "text"
        catalog = json.loads(result["text"])
        assert "models" in catalog
        assert "providers" in catalog
        
    @pytest.mark.asyncio
    async def test_execute_optimization_pipeline(self, mcp_service, mock_services):
        """Test optimization pipeline execution"""
        mock_services["thread_service"].create_thread.return_value = "thread789"
        mock_services["agent_service"].execute_agent.return_value = {
            "run_id": "pipeline123"
        }
        
        result = await mcp_service.execute_optimization_pipeline({
            "input_data": {"test": "data"},
            "optimization_goals": ["cost", "performance"]
        }, "session999")
        
        assert result["type"] == "text"
        response = json.loads(result["text"])
        assert response["status"] == "pipeline_started"
        assert response["thread_id"] == "thread789"
        assert response["run_id"] == "pipeline123"
        assert response["optimization_goals"] == ["cost", "performance"]
        
        # Verify supervisor agent was called
        mock_services["agent_service"].execute_agent.assert_called_once()
        call_args = mock_services["agent_service"].execute_agent.call_args
        assert call_args[1]["agent_name"] == "SupervisorAgent"
        assert call_args[1]["config"]["pipeline_mode"] == True
        
    @pytest.mark.asyncio
    async def test_register_client(self, mcp_service, mock_services):
        """Test client registration"""
        mock_services["security_service"].hash_password.return_value = "hashed_key"
        
        db_session = AsyncMock()
        client = await mcp_service.register_client(
            db_session=db_session,
            name="Test Client",
            client_type="claude",
            api_key="secret_key",
            permissions=["read"],
            metadata={"version": "1.0"}
        )
        
        assert client.name == "Test Client"
        assert client.client_type == "claude"
        assert client.api_key_hash == "hashed_key"
        assert client.permissions == ["read"]
        assert client.metadata == {"version": "1.0"}
        
        mock_services["security_service"].hash_password.assert_called_once_with("secret_key")
        
    @pytest.mark.asyncio
    async def test_register_client_error(self, mcp_service, mock_services):
        """Test client registration error"""
        mock_services["security_service"].hash_password.side_effect = Exception("Hash error")
        
        db_session = AsyncMock()
        with pytest.raises(NetraException) as exc_info:
            await mcp_service.register_client(
                db_session=db_session,
                name="Test",
                client_type="cursor",
                api_key="key"
            )
            
        assert "Failed to register MCP client" in str(exc_info.value)
        
    @pytest.mark.asyncio
    async def test_validate_client_access(self, mcp_service):
        """Test client access validation"""
        db_session = AsyncMock()
        
        # Currently returns True (placeholder)
        result = await mcp_service.validate_client_access(
            db_session=db_session,
            client_id="client123",
            required_permission="read"
        )
        
        assert result == True
        
    @pytest.mark.asyncio
    async def test_record_tool_execution(self, mcp_service):
        """Test recording tool execution"""
        db_session = AsyncMock()
        execution = MCPToolExecution(
            session_id="session123",
            tool_name="test_tool",
            input_params={},
            execution_time_ms=100,
            status="success"
        )
        
        # Should not raise error
        await mcp_service.record_tool_execution(db_session, execution)
        
    def test_get_mcp_server(self, mcp_service):
        """Test getting MCP server instance"""
        server = mcp_service.get_mcp_server()
        
        assert server != None
        assert server == mcp_service.mcp_server