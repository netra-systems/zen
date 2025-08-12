"""
Tests for MCP Integration with FastMCP 2

Tests the Model Context Protocol server implementation.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.mcp.netra_mcp_server import NetraMCPServer
from app.services.mcp_service import MCPService, MCPClient, MCPToolExecution


@pytest.fixture
def mock_services():
    """Create mock services for testing"""
    return {
        "agent_service": AsyncMock(),
        "thread_service": AsyncMock(),
        "corpus_service": AsyncMock(),
        "synthetic_data_service": AsyncMock(),
        "security_service": AsyncMock(),
        "supply_catalog_service": AsyncMock(),
        "llm_manager": AsyncMock()
    }


@pytest.fixture
def mcp_server(mock_services):
    """Create MCP server with mock services"""
    server = NetraMCPServer(name="test-server", version="1.0.0")
    server.set_services(**mock_services)
    return server


@pytest.fixture
def mcp_service(mock_services):
    """Create MCP service with mock services"""
    return MCPService(**mock_services)


class TestNetraMCPServer:
    """Test NetraMCPServer functionality"""
    
    def test_server_initialization(self):
        """Test server initializes correctly"""
        server = NetraMCPServer(name="test", version="1.0.0")
        assert server.mcp is not None
        assert server.mcp.name == "test"
        assert server.mcp.version == "1.0.0"
    
    def test_service_injection(self, mock_services):
        """Test service injection works"""
        server = NetraMCPServer()
        server.set_services(**mock_services)
        
        assert server.agent_service == mock_services["agent_service"]
        assert server.thread_service == mock_services["thread_service"]
        assert server.corpus_service == mock_services["corpus_service"]
    
    @pytest.mark.asyncio
    async def test_list_agents_tool(self, mcp_server):
        """Test list_agents tool"""
        app = mcp_server.get_app()
        
        # Get the tool function
        tool_func = app._tool_manager.tools.get("list_agents")
        assert tool_func is not None
        
        # Execute tool
        result = await tool_func()
        agents = json.loads(result)
        
        assert isinstance(agents, list)
        assert len(agents) > 0
        assert any(a["name"] == "SupervisorAgent" for a in agents)
    
    @pytest.mark.asyncio
    async def test_run_agent_tool(self, mcp_server, mock_services):
        """Test run_agent tool execution"""
        # Setup mock response
        mock_services["agent_service"].execute_agent.return_value = {
            "run_id": "test-run-123",
            "response": "Agent executed successfully"
        }
        mock_services["thread_service"].create_thread.return_value = "thread-123"
        
        app = mcp_server.get_app()
        tool_func = app._tool_manager.tools.get("run_agent")
        assert tool_func is not None
        
        # Execute tool
        result = await tool_func(
            agent_name="TestAgent",
            input_data={"test": "data"},
            config={"debug": True}
        )
        
        result_data = json.loads(result)
        assert result_data["status"] == "success"
        assert result_data["thread_id"] == "thread-123"
        assert result_data["run_id"] == "test-run-123"
    
    @pytest.mark.asyncio
    async def test_analyze_workload_tool(self, mcp_server, mock_services):
        """Test analyze_workload tool"""
        mock_services["agent_service"].analyze_workload.return_value = {
            "cost": 100.0,
            "latency": 200,
            "throughput": 1000
        }
        
        app = mcp_server.get_app()
        tool_func = app._tool_manager.tools.get("analyze_workload")
        assert tool_func is not None
        
        result = await tool_func(
            workload_data={"requests": 1000},
            metrics=["cost", "latency"]
        )
        
        result_data = json.loads(result)
        assert "cost" in result_data
        assert result_data["cost"] == 100.0
    
    @pytest.mark.asyncio
    async def test_query_corpus_tool(self, mcp_server, mock_services):
        """Test query_corpus tool"""
        mock_services["corpus_service"].search.return_value = [
            {"id": "doc1", "content": "Test document"}
        ]
        
        app = mcp_server.get_app()
        tool_func = app._tool_manager.tools.get("query_corpus")
        assert tool_func is not None
        
        result = await tool_func(
            query="test query",
            limit=5
        )
        
        result_data = json.loads(result)
        assert isinstance(result_data, list)
        assert len(result_data) == 1
    
    @pytest.mark.asyncio
    async def test_resource_optimization_history(self, mcp_server):
        """Test optimization history resource"""
        app = mcp_server.get_app()
        
        # Get resource function
        resource_func = app._resource_manager.resources.get("netra://optimization/history")
        assert resource_func is not None
        
        # Read resource
        result = await resource_func()
        history = json.loads(result)
        
        assert "optimizations" in history
        assert isinstance(history["optimizations"], list)
        assert "total_savings" in history
    
    @pytest.mark.asyncio
    async def test_resource_model_configs(self, mcp_server):
        """Test model configurations resource"""
        app = mcp_server.get_app()
        
        resource_func = app._resource_manager.resources.get("netra://config/models")
        assert resource_func is not None
        
        result = await resource_func()
        configs = json.loads(result)
        
        assert "models" in configs
        assert "claude-3-opus" in configs["models"]
        assert "context_window" in configs["models"]["claude-3-opus"]
    
    @pytest.mark.asyncio
    async def test_prompt_optimization_request(self, mcp_server):
        """Test optimization request prompt"""
        app = mcp_server.get_app()
        
        prompt_func = app._prompt_manager.prompts.get("optimization_request")
        assert prompt_func is not None
        
        messages = await prompt_func(
            workload_description="Test workload",
            monthly_budget=5000.0,
            quality_requirements="high"
        )
        
        assert isinstance(messages, list)
        assert len(messages) > 0
        assert messages[0]["role"] == "user"
        assert "Test workload" in messages[0]["content"]
        assert "5,000.00" in messages[0]["content"]


class TestMCPService:
    """Test MCPService functionality"""
    
    def test_service_initialization(self, mock_services):
        """Test service initializes correctly"""
        service = MCPService(**mock_services)
        
        assert service.agent_service == mock_services["agent_service"]
        assert service.mcp_server is not None
        assert isinstance(service.active_sessions, dict)
    
    @pytest.mark.asyncio
    async def test_register_client(self, mcp_service, mock_services):
        """Test client registration"""
        mock_db = AsyncMock()
        mock_services["security_service"].hash_password.return_value = "hashed_key"
        
        # Mock repository response
        mock_client = MagicMock()
        mock_client.id = "client-123"
        mock_client.name = "Test Client"
        mock_client.client_type = "test"
        mock_client.api_key_hash = "hashed_key"
        mock_client.permissions = ["read", "write"]
        mock_client.metadata = {}
        mock_client.created_at = datetime.utcnow()
        mock_client.last_active = datetime.utcnow()
        
        with patch.object(mcp_service.client_repository, 'create_client', return_value=mock_client):
            client = await mcp_service.register_client(
                db_session=mock_db,
                name="Test Client",
                client_type="test",
                api_key="test_key",
                permissions=["read", "write"]
            )
        
        assert isinstance(client, MCPClient)
        assert client.name == "Test Client"
        assert client.client_type == "test"
    
    @pytest.mark.asyncio
    async def test_create_session(self, mcp_service):
        """Test session creation"""
        session_id = await mcp_service.create_session(
            client_id="client-123",
            metadata={"test": "data"}
        )
        
        assert session_id is not None
        assert session_id in mcp_service.active_sessions
        
        session = mcp_service.active_sessions[session_id]
        assert session["client_id"] == "client-123"
        assert session["metadata"]["test"] == "data"
    
    @pytest.mark.asyncio
    async def test_get_session(self, mcp_service):
        """Test getting session information"""
        # Create session
        session_id = await mcp_service.create_session(client_id="client-123")
        
        # Get session
        session = await mcp_service.get_session(session_id)
        assert session is not None
        assert session["id"] == session_id
        assert session["client_id"] == "client-123"
        
        # Try non-existent session
        none_session = await mcp_service.get_session("non-existent")
        assert none_session is None
    
    @pytest.mark.asyncio
    async def test_update_session_activity(self, mcp_service):
        """Test updating session activity"""
        session_id = await mcp_service.create_session()
        initial_activity = mcp_service.active_sessions[session_id]["last_activity"]
        initial_count = mcp_service.active_sessions[session_id]["request_count"]
        
        # Update activity
        await mcp_service.update_session_activity(session_id)
        
        session = mcp_service.active_sessions[session_id]
        assert session["last_activity"] >= initial_activity
        assert session["request_count"] == initial_count + 1
    
    @pytest.mark.asyncio
    async def test_close_session(self, mcp_service):
        """Test closing session"""
        session_id = await mcp_service.create_session()
        assert session_id in mcp_service.active_sessions
        
        await mcp_service.close_session(session_id)
        assert session_id not in mcp_service.active_sessions
    
    @pytest.mark.asyncio
    async def test_cleanup_inactive_sessions(self, mcp_service):
        """Test cleaning up inactive sessions"""
        from datetime import timedelta
        
        # Create sessions
        active_session = await mcp_service.create_session()
        inactive_session = await mcp_service.create_session()
        
        # Make one session inactive
        mcp_service.active_sessions[inactive_session]["last_activity"] = (
            datetime.utcnow() - timedelta(minutes=61)
        )
        
        # Clean up
        await mcp_service.cleanup_inactive_sessions(timeout_minutes=60)
        
        assert active_session in mcp_service.active_sessions
        assert inactive_session not in mcp_service.active_sessions
    
    @pytest.mark.asyncio
    async def test_get_server_info(self, mcp_service):
        """Test getting server information"""
        info = await mcp_service.get_server_info()
        
        assert info["name"] == "Netra MCP Server"
        assert info["version"] == "2.0.0"
        assert info["protocol"] == "MCP"
        assert info["implementation"] == "FastMCP 2"
        assert "tools_available" in info
        assert "resources_available" in info
        assert "prompts_available" in info
    
    @pytest.mark.asyncio
    async def test_record_tool_execution(self, mcp_service):
        """Test recording tool execution"""
        mock_db = AsyncMock()
        
        execution = MCPToolExecution(
            session_id="session-123",
            client_id="client-123",
            tool_name="test_tool",
            input_params={"test": "input"},
            output_result={"result": "success"},
            execution_time_ms=100,
            status="success"
        )
        
        mock_db_execution = MagicMock()
        mock_db_execution.id = "exec-123"
        
        with patch.object(mcp_service.execution_repository, 'record_execution', return_value=mock_db_execution):
            with patch.object(mcp_service.execution_repository, 'update_execution_result'):
                await mcp_service.record_tool_execution(mock_db, execution)
        
        # Verify methods were called
        mcp_service.execution_repository.record_execution.assert_called_once()
        mcp_service.execution_repository.update_execution_result.assert_called_once()


class TestMCPIntegration:
    """Integration tests for MCP"""
    
    @pytest.mark.asyncio
    async def test_full_tool_execution_flow(self, mcp_service, mock_services):
        """Test complete tool execution flow"""
        # Setup mocks
        mock_services["agent_service"].execute_agent.return_value = {
            "run_id": "run-123",
            "response": "Success"
        }
        mock_services["thread_service"].create_thread.return_value = "thread-123"
        
        # Create session
        session_id = await mcp_service.create_session(client_id="client-123")
        
        # Get server and execute tool
        server = mcp_service.get_mcp_server()
        app = server.get_app()
        
        tool_func = app._tool_manager.tools.get("run_agent")
        result = await tool_func(
            agent_name="SupervisorAgent",
            input_data={"task": "optimize"},
            config={}
        )
        
        # Verify result
        result_data = json.loads(result)
        assert result_data["status"] == "success"
        assert result_data["run_id"] == "run-123"
        
        # Update session activity
        await mcp_service.update_session_activity(session_id)
        session = await mcp_service.get_session(session_id)
        assert session["request_count"] == 1
    
    @pytest.mark.asyncio
    async def test_error_handling(self, mcp_server, mock_services):
        """Test error handling in tools"""
        # Make service raise error
        mock_services["agent_service"].execute_agent.side_effect = Exception("Test error")
        
        app = mcp_server.get_app()
        tool_func = app._tool_manager.tools.get("run_agent")
        
        result = await tool_func(
            agent_name="TestAgent",
            input_data={"test": "data"}
        )
        
        result_data = json.loads(result)
        assert result_data["status"] == "error"
        assert "Test error" in result_data["error"]


@pytest.mark.smoke
class TestMCPSmoke:
    """Smoke tests for MCP functionality"""
    
    def test_mcp_server_creation(self):
        """Test basic server creation"""
        server = NetraMCPServer()
        assert server is not None
        assert server.mcp is not None
    
    def test_mcp_service_creation(self, mock_services):
        """Test basic service creation"""
        with patch('app.services.mcp_service.MCPClientRepository'), \
             patch('app.services.mcp_service.MCPToolExecutionRepository'):
            service = MCPService(**mock_services)
            assert service is not None
            assert service.mcp_server is not None
    
    @pytest.mark.asyncio
    async def test_basic_tool_availability(self):
        """Test that basic tools are available"""
        server = NetraMCPServer()
        app = server.get_app()
        
        # Check core tools exist - FastMCP uses _tools attribute
        assert "run_agent" in app._tool_manager._tools
        assert "list_agents" in app._tool_manager._tools
        assert "analyze_workload" in app._tool_manager._tools
        assert "optimize_prompt" in app._tool_manager._tools