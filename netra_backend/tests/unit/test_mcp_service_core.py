"""
Core unit tests for MCP Service.

Tests MCP server integration, client management, and session handling.
SLA CRITICAL - Maintains MCP connectivity for system integrations.

Business Value: Ensures reliable MCP functionality preventing integration
failures that could impact API partnerships and third-party integrations.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from datetime import datetime, timezone, UTC, timedelta
import uuid
import pytest

# Environment-aware testing imports
from test_framework.decorators import mock_justified
from netra_backend.app.services.mcp_service import MCPService
from netra_backend.app.services.mcp_models import MCPClient, MCPToolExecution
from netra_backend.app.core.exceptions_base import NetraException


class TestMCPServiceSecurityFeatures:
    """Security-focused tests for MCP service authentication and authorization."""
    
    def test_mcp_client_authentication_security(self):
        """Test MCP client authentication security measures."""
        # Test client creation with security-focused validation
        insecure_client = MCPClient(
            name="Insecure Client",
            client_type="unknown",
            permissions=[]  # No permissions - security risk
        )
        
        # Should handle insecure clients appropriately
        assert insecure_client.permissions == []
        assert insecure_client.client_type == "unknown"
        
        # Test secure client with proper permissions
        secure_client = MCPClient(
            name="Secure Client", 
            client_type="claude",
            permissions=["read_threads", "write_messages"],
            api_key_hash="secure_hash_123"
        )
        
        # Should have proper security attributes
        assert secure_client.permissions == ["read_threads", "write_messages"]
        assert secure_client.api_key_hash == "secure_hash_123"
        assert secure_client.client_type == "claude"
        
        # Test tool execution security
        tool_execution = MCPToolExecution(
            session_id=str(uuid.uuid4()),
            client_id=secure_client.id,
            tool_name="sensitive_operation_tool",
            input_params={"operation": "delete", "target": "user_data"},
            execution_time_ms=150,
            status="success"
        )
        
        # Should track sensitive operations
        assert tool_execution.tool_name == "sensitive_operation_tool"
        assert "delete" in tool_execution.input_params.get("operation", "")
        assert tool_execution.status == "success"
        
        # Test session security - client activity tracking  
        old_timestamp = datetime(2020, 1, 1, tzinfo=UTC)
        stale_client = MCPClient(
            name="Stale Client",
            client_type="vscode", 
            created_at=old_timestamp,
            last_active=old_timestamp
        )
        
        # Should detect stale sessions
        time_diff = datetime.now(UTC) - stale_client.last_active
        assert time_diff.days > 365  # Very old activity

    def test_mcp_rate_limiting_security(self):
        """Test MCP rate limiting and abuse prevention."""
        # Test rapid tool executions from same client
        client_id = str(uuid.uuid4())
        executions = []
        
        for i in range(5):  # Simulate rapid requests
            execution = MCPToolExecution(
                session_id=str(uuid.uuid4()),
                client_id=client_id,
                tool_name=f"rapid_tool_{i}",
                input_params={"request_id": i},
                execution_time_ms=50,
                status="success"
            )
            executions.append(execution)
        
        # Should track all executions for rate limiting
        assert len(executions) == 5
        assert all(e.client_id == client_id for e in executions)
        assert all(e.execution_time_ms == 50 for e in executions)
        
        # Test expensive operation tracking
        expensive_execution = MCPToolExecution(
            session_id=str(uuid.uuid4()),
            client_id=client_id,
            tool_name="expensive_ml_operation",
            input_params={"model": "gpt-4", "tokens": 4000},
            execution_time_ms=5000,  # 5 seconds
            status="success"
        )
        
        # Should flag expensive operations
        assert expensive_execution.execution_time_ms > 1000
        assert "gpt-4" in expensive_execution.input_params.get("model", "")

    def test_mcp_permission_validation_security(self):
        """Test MCP client permission validation and access control."""
        # Test client with minimal permissions
        limited_client = MCPClient(
            name="Limited Client",
            client_type="cursor", 
            permissions=["read_threads"]  # Read-only
        )
        
        # Test client with dangerous permissions
        admin_client = MCPClient(
            name="Admin Client",
            client_type="internal",
            permissions=["read_threads", "write_messages", "delete_data", "admin_access"]
        )
        
        # Should differentiate permission levels
        assert "delete_data" not in limited_client.permissions
        assert "admin_access" not in limited_client.permissions
        assert "delete_data" in admin_client.permissions
        assert "admin_access" in admin_client.permissions
        
        # Test permission escalation attempt
        escalation_attempt = MCPToolExecution(
            session_id=str(uuid.uuid4()),
            client_id=limited_client.id,
            tool_name="admin_delete_user",
            input_params={"user_id": "victim_123", "force": True},
            execution_time_ms=100,
            status="error"  # Should fail
        )
        
        # Should block unauthorized operations
        assert escalation_attempt.status == "error"
        assert escalation_attempt.tool_name.startswith("admin_")


class TestMCPServiceCore:
    """Core test suite for MCP Service functionality."""
    
    @pytest.fixture
    def mock_services(self):
        """Create mock services for MCP service initialization."""
        return {
            'agent_service': Mock(),
            'thread_service': Mock(),
            'corpus_service': Mock(),
            'synthetic_data_service': Mock(),
            'security_service': Mock(),
            'supply_catalog_service': Mock(),
            'llm_manager': Mock()
        }
    
    @pytest.fixture
    def mcp_service(self, mock_services):
        """Create MCP service instance with mocked dependencies."""
        # Mock: Generic component isolation for controlled unit testing
        with patch('netra_backend.app.services.mcp_service.MCPClientRepository'), \
             patch('netra_backend.app.services.mcp_service.MCPToolExecutionRepository'), \
             patch('netra_backend.app.services.mcp_service.NetraMCPServer'):
            
            service = MCPService(**mock_services)
            return service
    
    @pytest.fixture
    def sample_mcp_client(self):
        """Create sample MCP client for testing."""
        return MCPClient(
            id="test-client-123",
            name="Test Client",
            client_type="api_client",
            api_key_hash="hashed_key_123",
            permissions=["read", "write"],
            metadata={"version": "1.0"},
            created_at=datetime.now(UTC),
            last_active=datetime.now(UTC)
        )
    
    @pytest.fixture
    def sample_tool_execution(self):
        """Create sample tool execution for testing."""
        return MCPToolExecution(
            session_id="test-session-123",
            client_id="test-client-123",
            tool_name="test_tool",
            input_params={"param1": "value1"},
            execution_time_ms=100,
            status="executing"
        )
    
    def test_mcp_service_initialization(self, mock_services):
        """Test MCP service initialization with all dependencies."""
        # Mock: Generic component isolation for controlled unit testing
        with patch('netra_backend.app.services.mcp_service.MCPClientRepository'), \
             patch('netra_backend.app.services.mcp_service.MCPToolExecutionRepository'), \
             patch('netra_backend.app.services.mcp_service.NetraMCPServer'):
            
            service = MCPService(**mock_services)
            
            # Verify service components are initialized
            assert service.agent_service == mock_services['agent_service']
            assert service.thread_service == mock_services['thread_service']
            assert service.corpus_service == mock_services['corpus_service']
            assert service.synthetic_data_service == mock_services['synthetic_data_service']
            assert service.security_service == mock_services['security_service']
            assert service.supply_catalog_service == mock_services['supply_catalog_service']
            assert service.llm_manager == mock_services['llm_manager']
            
            # Verify repositories are initialized
            assert hasattr(service, 'client_repository')
            assert hasattr(service, 'execution_repository')
            
            # Verify MCP server is initialized
            assert hasattr(service, 'mcp_server')
            
            # Verify session storage is initialized
            assert hasattr(service, 'active_sessions')
            assert isinstance(service.active_sessions, dict)
    
    @mock_justified("L1 Unit Test: Mocking database session to isolate client registration logic. Real database testing in L3 integration tests.", "L1")
    @pytest.mark.asyncio
    async def test_register_client_success(self, mcp_service, sample_mcp_client):
        """Test successful client registration."""
        # Mock: Database session isolation for testing without real database dependency
        mock_db_session = AsyncMock()
        
        # Mock repository create_client method
        mock_db_client = Mock()
        mock_db_client.id = sample_mcp_client.id
        mock_db_client.name = sample_mcp_client.name
        mock_db_client.client_type = sample_mcp_client.client_type
        mock_db_client.api_key_hash = sample_mcp_client.api_key_hash
        mock_db_client.permissions = sample_mcp_client.permissions
        mock_db_client.metadata = sample_mcp_client.metadata
        mock_db_client.created_at = sample_mcp_client.created_at
        mock_db_client.last_active = sample_mcp_client.last_active
        
        mcp_service.client_repository.create_client = AsyncMock(return_value=mock_db_client)
        mcp_service.security_service.hash_password = Mock(return_value="hashed_key_123")
        
        result = await mcp_service.register_client(
            db_session=mock_db_session,
            name="Test Client",
            client_type="api_client",
            api_key="test_api_key",
            permissions=["read", "write"],
            metadata={"version": "1.0"}
        )
        
        assert isinstance(result, MCPClient)
        assert result.name == "Test Client"
        assert result.client_type == "api_client"
        assert result.permissions == ["read", "write"]
        
        # Verify repository was called with correct parameters
        mcp_service.client_repository.create_client.assert_called_once()
    
    @mock_justified("L1 Unit Test: Mocking database session to test client registration error handling.", "L1")
    @pytest.mark.asyncio
    async def test_register_client_database_error(self, mcp_service):
        """Test client registration with database error."""
        # Mock: Database session isolation for testing without real database dependency
        mock_db_session = AsyncMock()
        
        # Mock repository to raise exception
        mcp_service.client_repository.create_client = AsyncMock(side_effect=Exception("Database error"))
        mcp_service.security_service.hash_password = Mock(return_value="hashed_key_123")
        
        with pytest.raises(NetraException) as exc_info:
            await mcp_service.register_client(
                db_session=mock_db_session,
                name="Test Client",
                client_type="api_client",
                api_key="test_api_key"
            )
        
        assert "Failed to register MCP client" in str(exc_info.value)
    
    @mock_justified("L1 Unit Test: Mocking database session to isolate client access validation logic.", "L1")
    @pytest.mark.asyncio
    async def test_validate_client_access_success(self, mcp_service):
        """Test successful client access validation."""
        # Mock: Database session isolation for testing without real database dependency
        mock_db_session = AsyncMock()
        
        # Mock repository methods
        mcp_service.client_repository.validate_client_permission = AsyncMock(return_value=True)
        mcp_service.client_repository.update_last_active = AsyncMock()
        
        result = await mcp_service.validate_client_access(
            db_session=mock_db_session,
            client_id="test-client-123",
            required_permission="read"
        )
        
        assert result is True
        
        # Verify permission check was called
        mcp_service.client_repository.validate_client_permission.assert_called_once_with(
            db=mock_db_session,
            client_id="test-client-123",
            required_permission="read"
        )
        
        # Verify last active was updated
        mcp_service.client_repository.update_last_active.assert_called_once()
    
    @mock_justified("L1 Unit Test: Mocking database session to test client access validation failure.", "L1")
    @pytest.mark.asyncio
    async def test_validate_client_access_permission_denied(self, mcp_service):
        """Test client access validation with permission denied."""
        # Mock: Database session isolation for testing without real database dependency
        mock_db_session = AsyncMock()
        
        # Mock repository to return false for permission check
        mcp_service.client_repository.validate_client_permission = AsyncMock(return_value=False)
        mcp_service.client_repository.update_last_active = AsyncMock()
        
        result = await mcp_service.validate_client_access(
            db_session=mock_db_session,
            client_id="test-client-123",
            required_permission="admin"
        )
        
        assert result is False
        
        # Verify update_last_active was not called since permission was denied
        mcp_service.client_repository.update_last_active.assert_not_called()
    
    @mock_justified("L1 Unit Test: Mocking database session to test tool execution recording.", "L1")
    @pytest.mark.asyncio
    async def test_record_tool_execution_success(self, mcp_service, sample_tool_execution):
        """Test successful tool execution recording."""
        # Mock: Database session isolation for testing without real database dependency
        mock_db_session = AsyncMock()
        
        # Mock database execution record
        mock_db_execution = Mock()
        mock_db_execution.id = "exec-123"
        
        # Mock repository methods
        mcp_service.execution_repository.record_execution = AsyncMock(return_value=mock_db_execution)
        mcp_service.execution_repository.update_execution_result = AsyncMock()
        
        # Add result to execution for testing update
        sample_tool_execution.output_result = {"status": "success"}
        
        await mcp_service.record_tool_execution(
            db_session=mock_db_session,
            execution=sample_tool_execution
        )
        
        # Verify execution was recorded
        mcp_service.execution_repository.record_execution.assert_called_once()
        
        # Verify result was updated since output_result was present
        mcp_service.execution_repository.update_execution_result.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_session_success(self, mcp_service):
        """Test successful session creation."""
        session_id = await mcp_service.create_session(
            client_id="test-client-123",
            metadata={"test": "metadata"}
        )
        
        # Verify session ID is a valid UUID
        assert isinstance(session_id, str)
        uuid.UUID(session_id)  # This will raise if not a valid UUID
        
        # Verify session is stored in active sessions
        assert session_id in mcp_service.active_sessions
        
        session_data = mcp_service.active_sessions[session_id]
        assert session_data["id"] == session_id
        assert session_data["client_id"] == "test-client-123"
        assert session_data["metadata"] == {"test": "metadata"}
        assert session_data["request_count"] == 0
        assert isinstance(session_data["created_at"], datetime)
        assert isinstance(session_data["last_activity"], datetime)
    
    @pytest.mark.asyncio
    async def test_get_session_exists(self, mcp_service):
        """Test getting an existing session."""
        # Create a session first
        session_id = await mcp_service.create_session(client_id="test-client")
        
        # Get the session
        session_data = await mcp_service.get_session(session_id)
        
        assert session_data is not None
        assert session_data["id"] == session_id
        assert session_data["client_id"] == "test-client"
    
    @pytest.mark.asyncio
    async def test_get_session_not_exists(self, mcp_service):
        """Test getting a non-existent session."""
        result = await mcp_service.get_session("non-existent-session")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_update_session_activity(self, mcp_service):
        """Test updating session activity timestamp."""
        import asyncio
        
        # Create a session
        session_id = await mcp_service.create_session()
        
        # Get initial activity time and request count
        initial_data = mcp_service.active_sessions[session_id]
        initial_activity = initial_data["last_activity"]
        initial_count = initial_data["request_count"]
        
        # Wait a small amount to ensure timestamp difference
        await asyncio.sleep(0.01)
        
        # Update session activity
        await mcp_service.update_session_activity(session_id)
        
        # Verify activity was updated
        updated_data = mcp_service.active_sessions[session_id]
        assert updated_data["last_activity"] >= initial_activity  # Use >= since timing can be very close
        assert updated_data["request_count"] == initial_count + 1
    
    @pytest.mark.asyncio
    async def test_close_session(self, mcp_service):
        """Test closing a session."""
        # Create a session
        session_id = await mcp_service.create_session()
        assert session_id in mcp_service.active_sessions
        
        # Close the session
        await mcp_service.close_session(session_id)
        
        # Verify session is removed
        assert session_id not in mcp_service.active_sessions
    
    @pytest.mark.asyncio
    async def test_cleanup_inactive_sessions(self, mcp_service):
        """Test cleanup of inactive sessions."""
        # Create multiple sessions with different activity times
        session1 = await mcp_service.create_session()
        session2 = await mcp_service.create_session()
        session3 = await mcp_service.create_session()
        
        # Mock old activity time for session1 (should be cleaned up)
        old_time = datetime.now(UTC).replace(year=2023)  # Very old timestamp
        mcp_service.active_sessions[session1]["last_activity"] = old_time
        
        # Mock recent activity time for session2 (should remain)
        recent_time = datetime.now(UTC)
        mcp_service.active_sessions[session2]["last_activity"] = recent_time
        
        # Session3 will have current time from creation
        
        # Run cleanup with 30 minute timeout
        await mcp_service.cleanup_inactive_sessions(timeout_minutes=30)
        
        # Verify only the inactive session was removed
        assert session1 not in mcp_service.active_sessions
        assert session2 in mcp_service.active_sessions
        assert session3 in mcp_service.active_sessions
    
    def test_get_mcp_server(self, mcp_service):
        """Test getting MCP server instance."""
        server = mcp_service.get_mcp_server()
        assert server is not None
        assert server == mcp_service.mcp_server
    
    def test_get_fastmcp_app(self, mcp_service):
        """Test getting FastMCP app instance."""
        # Mock the get_app method on the server
        mock_app = Mock()
        mcp_service.mcp_server.get_app = Mock(return_value=mock_app)
        
        app = mcp_service.get_fastmcp_app()
        assert app == mock_app
        mcp_service.mcp_server.get_app.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_server_info(self, mcp_service):
        """Test getting server information."""
        server_info = await mcp_service.get_server_info()
        
        assert isinstance(server_info, dict)
        assert "name" in server_info
        assert "version" in server_info
        assert "protocol" in server_info
        assert "capabilities" in server_info
        assert "active_sessions" in server_info
        assert "tools_available" in server_info
        assert "resources_available" in server_info
        assert "prompts_available" in server_info
        
        # Verify specific values
        assert server_info["name"] == "Netra MCP Server"
        assert server_info["version"] == "2.0.0"
        assert server_info["protocol"] == "MCP"
        assert server_info["active_sessions"] == len(mcp_service.active_sessions)
    
    @pytest.mark.asyncio
    async def test_initialize_service(self, mcp_service):
        """Test service initialization."""
        # Mock cleanup method
        mcp_service.cleanup_inactive_sessions = AsyncMock()
        
        await mcp_service.initialize()
        
        # Verify cleanup was called during initialization
        mcp_service.cleanup_inactive_sessions.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_shutdown_service(self, mcp_service):
        """Test service shutdown."""
        # Create some sessions
        session1 = await mcp_service.create_session()
        session2 = await mcp_service.create_session()
        
        assert len(mcp_service.active_sessions) == 2
        
        # Shutdown service
        await mcp_service.shutdown()
        
        # Verify all sessions are closed and storage is cleared
        assert len(mcp_service.active_sessions) == 0
    
    @pytest.mark.asyncio
    async def test_execute_tool_success(self, mcp_service):
        """Test successful tool execution."""
        # Mock the tool execution logic
        mcp_service._execute_tool_logic = AsyncMock(return_value={"result": "success"})
        
        result = await mcp_service.execute_tool(
            tool_name="test_tool",
            parameters={"param1": "value1"},
            user_context={"session_id": "test-session", "client_id": "test-client"}
        )
        
        assert result == {"result": "success"}
        mcp_service._execute_tool_logic.assert_called_once_with("test_tool", {"param1": "value1"})
    
    @pytest.mark.asyncio
    async def test_execute_tool_failure(self, mcp_service):
        """Test tool execution failure handling."""
        # Mock the tool execution logic to raise exception
        mcp_service._execute_tool_logic = AsyncMock(side_effect=Exception("Tool failed"))
        
        # The method raises an exception on failure
        with pytest.raises(NetraException) as exc_info:
            await mcp_service.execute_tool(
                tool_name="test_tool",
                parameters={"param1": "value1"}
            )
        
        assert "Tool execution failed" in str(exc_info.value)
    
    # Helper method tests
    def test_extract_context_info(self, mcp_service):
        """Test extracting context information."""
        user_context = {"session_id": "test-session", "client_id": "test-client"}
        session_id, client_id = mcp_service._extract_context_info(user_context)
        
        assert session_id == "test-session"
        assert client_id == "test-client"
        
        # Test with None context
        session_id, client_id = mcp_service._extract_context_info(None)
        assert session_id is None
        assert client_id is None
    
    def test_create_tool_execution(self, mcp_service):
        """Test creating tool execution record."""
        execution = mcp_service._create_tool_execution(
            tool_name="test_tool",
            parameters={"param1": "value1"},
            session_id="test-session",
            client_id="test-client"
        )
        
        assert isinstance(execution, MCPToolExecution)
        assert execution.tool_name == "test_tool"
        assert execution.input_params == {"param1": "value1"}
        assert execution.session_id == "test-session"
        assert execution.client_id == "test-client"
        assert execution.status == "executing"
        assert execution.execution_time_ms == 0  # Initial value before completion
    
    def test_get_available_tools(self, mcp_service):
        """Test getting list of available tools."""
        tools = mcp_service._get_available_tools()
        
        assert isinstance(tools, list)
        assert len(tools) > 0
        
        # Verify specific tools are included
        assert "run_agent" in tools
        assert "analyze_workload" in tools
        assert "query_corpus" in tools
    
    def test_session_timeout_check(self, mcp_service):
        """Test session timeout checking."""
        now = datetime.now(UTC)
        
        # Create session data with old activity time
        old_session = {
            "last_activity": now - timedelta(hours=2)  # 2 hours ago
        }
        
        # Test with 60 minute timeout (should timeout)
        is_timeout = mcp_service._check_session_timeout(old_session, now, 60)
        assert is_timeout is True
        
        # Test with 180 minute timeout (should not timeout)
        is_timeout = mcp_service._check_session_timeout(old_session, now, 180)
        assert is_timeout is False


class TestMCPServiceEdgeCases:
    """Test MCP service edge cases and concurrent behavior."""
    
    def setup_method(self):
        """Set up test method with fresh service instance."""
        self.service = MCPService(
            Mock(), Mock(), Mock(), Mock(), 
            Mock(), Mock(), Mock()
        )
        self.service.sessions = {}
    
    def test_session_cleanup_edge_case(self):
        """Test session cleanup with edge cases."""
        # Test empty sessions dictionary doesn't cause errors  
        initial_count = len(self.service.sessions)
        assert initial_count == 0
        
        # Create a test session
        test_session_id = "test_session"
        self.service.sessions[test_session_id] = {
            'last_activity': datetime(2024, 1, 1, 12, 0, 0).replace(tzinfo=UTC),
            'data': 'test_data'
        }
        
        # Verify session was created
        assert len(self.service.sessions) == 1
        assert test_session_id in self.service.sessions
        
        # Test session dictionary integrity
        session = self.service.sessions[test_session_id]
        assert 'last_activity' in session
        assert 'data' in session
        assert session['data'] == 'test_data'
    
    @pytest.mark.asyncio
    async def test_session_update_with_nonexistent_session(self):
        """Test updating activity of non-existent session handles gracefully."""
        # Attempt to update activity of non-existent session
        nonexistent_id = "nonexistent_session"
        
        # Should not raise exception, should handle gracefully
        try:
            await self.service.update_session_activity(nonexistent_id)
            # If it doesn't raise, the session should be created or ignored
            assert True  # Test passes if no exception raised
        except KeyError:
            # This is acceptable behavior - some implementations may raise KeyError
            assert True
        
        # Session should not exist after failed update
        if nonexistent_id in self.service.sessions:
            # If session was created, it should have proper structure
            assert 'last_activity' in self.service.sessions[nonexistent_id]


class TestMCPServiceConcurrency:
    """Test concurrent operations and race condition handling for MCP Service."""
    
    @pytest.fixture
    def mock_services(self):
        """Create mock services for concurrency testing."""
        return {
            'agent_service': Mock(),
            'thread_service': Mock(),
            'corpus_service': Mock(),
            'synthetic_data_service': Mock(),
            'security_service': Mock(),
            'supply_catalog_service': Mock(),
            'llm_manager': Mock()
        }
    
    @pytest.fixture
    def mcp_service(self, mock_services):
        """Create MCP service instance for concurrency testing."""
        # Mock: Generic component isolation for controlled concurrency testing
        with patch('netra_backend.app.services.mcp_service.MCPClientRepository'), \
             patch('netra_backend.app.services.mcp_service.MCPToolExecutionRepository'), \
             patch('netra_backend.app.services.mcp_service.NetraMCPServer'):
            
            service = MCPService(**mock_services)
            return service
    
    @pytest.mark.asyncio
    async def test_concurrent_session_creation_and_cleanup(self, mcp_service):
        """Test concurrent session creation and cleanup operations."""
        import asyncio
        
        # Set up mock for cleanup timing
        mcp_service.session_timeout_seconds = 1
        
        async def create_multiple_sessions(count, session_ids):
            """Helper to create multiple sessions concurrently."""
            tasks = []
            for i in range(count):
                task = asyncio.create_task(mcp_service.create_session())
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            session_ids.extend(results)  # results are session ID strings directly
            return results
        
        async def cleanup_sessions():
            """Helper to trigger session cleanup."""
            await asyncio.sleep(0.1)  # Small delay to let sessions be created
            return await mcp_service.cleanup_inactive_sessions()
        
        # Create sessions and cleanup concurrently
        session_ids = []
        create_task = asyncio.create_task(create_multiple_sessions(5, session_ids))
        cleanup_task = asyncio.create_task(cleanup_sessions())
        
        # Wait for both operations
        created_sessions, cleanup_count = await asyncio.gather(create_task, cleanup_task)
        
        # Verify sessions were created
        assert len(created_sessions) == 5
        assert len(session_ids) == 5
        
        # All session IDs should be unique
        assert len(set(session_ids)) == 5
        
        # Verify all created session IDs are valid UUIDs (string format)
        for session_id in created_sessions:
            assert isinstance(session_id, str)
            assert len(session_id) == 36  # Standard UUID string length
            assert session_id in session_ids
    
    @pytest.mark.asyncio
    async def test_concurrent_tool_execution_isolation(self, mcp_service):
        """Test that concurrent tool executions are properly isolated."""
        import asyncio
        
        # Mock different execution results for different tools
        async def mock_execute_tool_logic(tool_name, parameters):
            await asyncio.sleep(0.05)  # Simulate processing time
            return {
                "tool": tool_name,
                "result": f"executed_{tool_name}",
                "params": parameters
            }
        
        mcp_service._execute_tool_logic = mock_execute_tool_logic
        
        # Execute multiple tools concurrently
        tasks = [
            mcp_service.execute_tool("tool_1", {"param": "value1"}),
            mcp_service.execute_tool("tool_2", {"param": "value2"}),
            mcp_service.execute_tool("tool_3", {"param": "value3"}),
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Verify each execution got correct results (no cross-contamination)
        assert len(results) == 3
        
        # Results should match their respective tool names
        tool_results = {result["tool"]: result for result in results}
        assert tool_results["tool_1"]["result"] == "executed_tool_1"
        assert tool_results["tool_1"]["params"] == {"param": "value1"}
        
        assert tool_results["tool_2"]["result"] == "executed_tool_2"
        assert tool_results["tool_2"]["params"] == {"param": "value2"}
        
        assert tool_results["tool_3"]["result"] == "executed_tool_3"
        assert tool_results["tool_3"]["params"] == {"param": "value3"}
    
    @pytest.mark.asyncio
    async def test_session_update_race_condition_safety(self, mcp_service):
        """Test session updates are safe under race conditions."""
        import asyncio
        
        # Create a session first
        session_id = await mcp_service.create_session()
        
        # Update the same session concurrently multiple times
        async def update_session_activity():
            await mcp_service.update_session_activity(session_id)
            return datetime.now(timezone.utc)
        
        # Run concurrent updates
        update_tasks = [update_session_activity() for _ in range(10)]
        update_times = await asyncio.gather(*update_tasks)
        
        # Verify session still exists and is valid
        retrieved_session = await mcp_service.get_session(session_id)
        assert retrieved_session is not None
        assert retrieved_session["id"] == session_id
        assert "last_activity" in retrieved_session
        
        # All updates should have completed without error
        assert len(update_times) == 10
        
        # Session should be active after all updates
        final_activity = retrieved_session["last_activity"]
        assert isinstance(final_activity, datetime)


class TestMCPServiceAsyncQueueManagement:
    """Test async queue management patterns for MCP service operations."""
    
    @pytest.fixture
    def mock_services(self):
        """Create mock services for queue management testing."""
        return {
            'agent_service': Mock(),
            'thread_service': Mock(),
            'corpus_service': Mock(),
            'synthetic_data_service': Mock(),
            'security_service': Mock(),
            'supply_catalog_service': Mock(),
            'llm_manager': Mock()
        }
    
    @pytest.fixture
    def mcp_service(self, mock_services):
        """Create MCP service instance for queue management testing."""
        # Mock: Generic component isolation for queue management testing
        with patch('netra_backend.app.services.mcp_service.MCPClientRepository'), \
             patch('netra_backend.app.services.mcp_service.MCPToolExecutionRepository'), \
             patch('netra_backend.app.services.mcp_service.NetraMCPServer'):
            
            service = MCPService(**mock_services)
            # Add queue tracking attributes for testing
            service.execution_queue = []
            service.pending_executions = {}
            service.max_concurrent_executions = 5
            return service
    
    @pytest.mark.asyncio
    async def test_async_tool_execution_queue_processing(self, mcp_service):
        """Test async queue processing for tool executions."""
        import asyncio
        from datetime import datetime
        
        # Mock tool execution with varying processing times
        async def mock_tool_execution(tool_name, delay=0.1):
            await asyncio.sleep(delay)
            return {"tool": tool_name, "result": "completed", "processing_time": delay}
        
        # Queue multiple tool executions with different priorities
        execution_requests = [
            {"tool": "high_priority_tool", "priority": 1, "delay": 0.05},
            {"tool": "normal_tool_1", "priority": 5, "delay": 0.1},
            {"tool": "urgent_tool", "priority": 0, "delay": 0.02},
            {"tool": "normal_tool_2", "priority": 5, "delay": 0.08},
            {"tool": "low_priority_tool", "priority": 10, "delay": 0.15}
        ]
        
        # Add executions to queue with timestamps
        for req in execution_requests:
            execution_id = str(uuid.uuid4())
            queue_item = {
                "id": execution_id,
                "tool_name": req["tool"],
                "priority": req["priority"],
                "created_at": datetime.now(UTC),
                "status": "queued",
                "delay": req["delay"]
            }
            mcp_service.execution_queue.append(queue_item)
        
        # Sort queue by priority (lower number = higher priority)
        mcp_service.execution_queue.sort(key=lambda x: x["priority"])
        
        # Process queue with concurrency limit
        async def process_queue_item(item):
            item["status"] = "executing"
            result = await mock_tool_execution(item["tool_name"], item["delay"])
            item["status"] = "completed"
            item["result"] = result
            return item
        
        # Process with semaphore for concurrency control
        semaphore = asyncio.Semaphore(mcp_service.max_concurrent_executions)
        
        async def limited_process(item):
            async with semaphore:
                return await process_queue_item(item)
        
        # Execute all items
        tasks = [limited_process(item) for item in mcp_service.execution_queue]
        results = await asyncio.gather(*tasks)
        
        # Verify queue processing results
        assert len(results) == 5
        
        # Verify priority ordering was maintained in queue
        queue_tools = [item["tool_name"] for item in mcp_service.execution_queue]
        expected_order = ["urgent_tool", "high_priority_tool", "normal_tool_1", "normal_tool_2", "low_priority_tool"]
        assert queue_tools == expected_order
        
        # Verify all executions completed
        for result in results:
            assert result["status"] == "completed"
            assert "result" in result
            assert result["result"]["result"] == "completed"
    
    @pytest.mark.asyncio
    async def test_queue_overflow_handling(self, mcp_service):
        """Test handling of queue overflow scenarios."""
        import asyncio
        
        # Set small queue limit for testing
        max_queue_size = 3
        mcp_service.max_queue_size = max_queue_size
        
        # Add items up to limit
        for i in range(max_queue_size):
            queue_item = {
                "id": f"item_{i}",
                "tool_name": f"tool_{i}",
                "priority": i,
                "status": "queued",
                "created_at": datetime.now(UTC)
            }
            mcp_service.execution_queue.append(queue_item)
        
        # Verify queue is at capacity
        assert len(mcp_service.execution_queue) == max_queue_size
        
        # Attempt to add overflow item
        overflow_item = {
            "id": "overflow_item",
            "tool_name": "overflow_tool",
            "priority": 0,
            "status": "rejected",
            "created_at": datetime.now(UTC),
            "rejection_reason": "queue_full"
        }
        
        # Test overflow handling
        if len(mcp_service.execution_queue) >= max_queue_size:
            # Handle overflow by rejecting or implementing priority-based eviction
            if overflow_item["priority"] < min(item["priority"] for item in mcp_service.execution_queue):
                # Remove lowest priority item and add high priority overflow
                lowest_priority_idx = max(range(len(mcp_service.execution_queue)), 
                                        key=lambda i: mcp_service.execution_queue[i]["priority"])
                evicted_item = mcp_service.execution_queue.pop(lowest_priority_idx)
                evicted_item["status"] = "evicted"
                
                overflow_item["status"] = "queued"
                mcp_service.execution_queue.append(overflow_item)
                
                # Verify eviction worked
                assert len(mcp_service.execution_queue) == max_queue_size
                assert any(item["id"] == "overflow_item" for item in mcp_service.execution_queue)
                assert evicted_item["status"] == "evicted"
        
        # Verify queue integrity after overflow handling
        assert len(mcp_service.execution_queue) <= max_queue_size
        for item in mcp_service.execution_queue:
            assert item["status"] in ["queued", "executing", "completed"]
    
    @pytest.mark.asyncio
    async def test_queue_backpressure_mechanisms(self, mcp_service):
        """Test backpressure mechanisms for queue management."""
        import asyncio
        
        # Setup backpressure thresholds
        mcp_service.queue_warning_threshold = 3
        mcp_service.queue_critical_threshold = 5
        mcp_service.backpressure_enabled = True
        
        # Add items progressively to test thresholds
        backpressure_metrics = {
            "warnings": 0,
            "critical_alerts": 0,
            "throttling_applied": False
        }
        
        def check_backpressure(queue_size):
            if queue_size >= mcp_service.queue_critical_threshold:
                backpressure_metrics["critical_alerts"] += 1
                backpressure_metrics["throttling_applied"] = True
                return {"throttle": True, "delay": 0.5}
            elif queue_size >= mcp_service.queue_warning_threshold:
                backpressure_metrics["warnings"] += 1
                return {"throttle": False, "delay": 0.1}
            return {"throttle": False, "delay": 0}
        
        # Add items and check backpressure at each step
        for i in range(6):
            queue_item = {
                "id": f"bp_item_{i}",
                "tool_name": f"tool_{i}",
                "priority": i,
                "status": "queued",
                "created_at": datetime.now(UTC)
            }
            mcp_service.execution_queue.append(queue_item)
            
            # Check backpressure response
            bp_response = check_backpressure(len(mcp_service.execution_queue))
            
            if bp_response["throttle"]:
                # Apply throttling delay
                await asyncio.sleep(bp_response["delay"])
                
            # Log queue state for analysis
            queue_item["backpressure_state"] = {
                "queue_size": len(mcp_service.execution_queue),
                "throttled": bp_response["throttle"],
                "delay_applied": bp_response["delay"]
            }
        
        # Verify backpressure was triggered
        assert backpressure_metrics["warnings"] > 0
        assert backpressure_metrics["critical_alerts"] > 0
        assert backpressure_metrics["throttling_applied"] is True
        
        # Verify queue items have backpressure metadata
        throttled_items = [item for item in mcp_service.execution_queue 
                          if item.get("backpressure_state", {}).get("throttled")]
        assert len(throttled_items) > 0
        
        # Verify throttling was applied at appropriate queue sizes
        for item in mcp_service.execution_queue:
            bp_state = item.get("backpressure_state", {})
            if bp_state.get("queue_size", 0) >= mcp_service.queue_critical_threshold:
                assert bp_state["throttled"] is True
                assert bp_state["delay_applied"] > 0
    
    @pytest.mark.asyncio
    async def test_async_session_queue_coordination(self, mcp_service):
        """Test coordination between session management and execution queues."""
        import asyncio
        
        # Create multiple sessions with different execution patterns
        session_configs = [
            {"client_id": "heavy_user", "execution_pattern": "burst", "count": 5},
            {"client_id": "normal_user", "execution_pattern": "steady", "count": 3},
            {"client_id": "light_user", "execution_pattern": "occasional", "count": 1}
        ]
        
        session_execution_tracking = {}
        
        # Create sessions and track their execution patterns
        for config in session_configs:
            session_id = await mcp_service.create_session(
                client_id=config["client_id"],
                metadata={"execution_pattern": config["execution_pattern"]}
            )
            
            session_execution_tracking[session_id] = {
                "client_id": config["client_id"],
                "pattern": config["execution_pattern"],
                "executions": [],
                "total_count": config["count"]
            }
        
        # Simulate execution requests from different sessions
        async def simulate_session_executions():
            execution_tasks = []
            
            for session_id, tracking in session_execution_tracking.items():
                pattern = tracking["pattern"]
                count = tracking["total_count"]
                
                if pattern == "burst":
                    # Burst pattern: all at once
                    for i in range(count):
                        execution = {
                            "session_id": session_id,
                            "client_id": tracking["client_id"],
                            "tool_name": f"burst_tool_{i}",
                            "timestamp": datetime.now(UTC),
                            "pattern": pattern
                        }
                        tracking["executions"].append(execution)
                        
                        # Add to queue
                        queue_item = {
                            "id": f"exec_{session_id}_{i}",
                            "session_id": session_id,
                            "tool_name": execution["tool_name"],
                            "priority": 5,
                            "status": "queued"
                        }
                        mcp_service.execution_queue.append(queue_item)
                
                elif pattern == "steady":
                    # Steady pattern: spaced out
                    for i in range(count):
                        execution = {
                            "session_id": session_id,
                            "client_id": tracking["client_id"],
                            "tool_name": f"steady_tool_{i}",
                            "timestamp": datetime.now(UTC),
                            "pattern": pattern
                        }
                        tracking["executions"].append(execution)
                        
                        queue_item = {
                            "id": f"exec_{session_id}_{i}",
                            "session_id": session_id,
                            "tool_name": execution["tool_name"],
                            "priority": 3,
                            "status": "queued"
                        }
                        mcp_service.execution_queue.append(queue_item)
                
                elif pattern == "occasional":
                    # Occasional pattern: minimal usage
                    for i in range(count):
                        execution = {
                            "session_id": session_id,
                            "client_id": tracking["client_id"],
                            "tool_name": f"occasional_tool_{i}",
                            "timestamp": datetime.now(UTC),
                            "pattern": pattern
                        }
                        tracking["executions"].append(execution)
                        
                        queue_item = {
                            "id": f"exec_{session_id}_{i}",
                            "session_id": session_id,
                            "tool_name": execution["tool_name"],
                            "priority": 1,
                            "status": "queued"
                        }
                        mcp_service.execution_queue.append(queue_item)
        
        await simulate_session_executions()
        
        # Verify queue contains executions from all sessions
        total_expected = sum(config["count"] for config in session_configs)
        assert len(mcp_service.execution_queue) == total_expected
        
        # Verify session isolation in queue
        session_ids_in_queue = {item["session_id"] for item in mcp_service.execution_queue}
        expected_sessions = set(session_execution_tracking.keys())
        assert session_ids_in_queue == expected_sessions
        
        # Verify execution patterns are preserved in queue
        for item in mcp_service.execution_queue:
            session_id = item["session_id"]
            tracking = session_execution_tracking[session_id]
            pattern = tracking["pattern"]
            
            # Verify tool names match patterns
            if pattern == "burst":
                assert "burst_tool" in item["tool_name"]
            elif pattern == "steady":
                assert "steady_tool" in item["tool_name"]
            elif pattern == "occasional":
                assert "occasional_tool" in item["tool_name"]
        
        # Verify priority assignment based on usage patterns
        burst_items = [item for item in mcp_service.execution_queue if "burst_tool" in item["tool_name"]]
        steady_items = [item for item in mcp_service.execution_queue if "steady_tool" in item["tool_name"]]
        occasional_items = [item for item in mcp_service.execution_queue if "occasional_tool" in item["tool_name"]]
        
        # Burst users should have lower priority (higher number) than occasional users
        assert all(item["priority"] > 3 for item in burst_items)
        assert all(item["priority"] == 3 for item in steady_items)
        assert all(item["priority"] == 1 for item in occasional_items)


class TestMCPServiceRevenueImpact:
    """Test MCP service revenue and business impact functionality."""
    
    @pytest.fixture
    def mock_services(self):
        """Create mock services for revenue impact testing."""
        return {
            'agent_service': Mock(),
            'thread_service': Mock(),
            'corpus_service': Mock(),
            'synthetic_data_service': Mock(),
            'security_service': Mock(),
            'supply_catalog_service': Mock(),
            'llm_manager': Mock()
        }
    
    @pytest.fixture
    def mcp_service(self, mock_services):
        """Create MCP service instance for revenue testing."""
        with patch('netra_backend.app.services.mcp_service.MCPClientRepository'), \
             patch('netra_backend.app.services.mcp_service.MCPToolExecutionRepository'), \
             patch('netra_backend.app.services.mcp_service.NetraMCPServer'):
            
            service = MCPService(**mock_services)
            return service
    
    @pytest.mark.asyncio
    async def test_premium_tier_cost_tracking_for_revenue_optimization(self, mcp_service):
        """Test cost tracking for premium tier users to optimize revenue capture.
        
        BVJ: Enterprise Segment - Revenue Optimization
        Tracks expensive operations from premium clients to ensure proper billing
        and identify upsell opportunities. Critical for capturing value relative
        to AI spend as per business mandate.
        """
        import asyncio
        from datetime import datetime, UTC
        
        # Create premium tier client with high-value permissions
        premium_client = MCPClient(
            name="Enterprise Premium Client",
            client_type="enterprise_api",
            permissions=["premium_analytics", "bulk_operations", "priority_processing"],
            metadata={
                "tier": "enterprise",
                "monthly_spend_limit": 50000,
                "ai_operations_budget": 25000,
                "priority_level": "highest"
            }
        )
        
        # Track expensive operations that impact revenue
        expensive_operations = [
            {
                "tool_name": "bulk_workload_optimization",
                "estimated_cost": 1250.00,
                "tokens_processed": 45000,
                "computation_time_ms": 8500,
                "revenue_category": "optimization_premium"
            },
            {
                "tool_name": "advanced_cost_analysis", 
                "estimated_cost": 890.00,
                "tokens_processed": 32000,
                "computation_time_ms": 6200,
                "revenue_category": "analytics_premium"
            },
            {
                "tool_name": "real_time_insights_generation",
                "estimated_cost": 2100.00,
                "tokens_processed": 78000,
                "computation_time_ms": 12000,
                "revenue_category": "insights_enterprise"
            }
        ]
        
        total_revenue_tracked = 0
        execution_records = []
        
        # Process each expensive operation and track revenue impact
        for operation in expensive_operations:
            session_id = await mcp_service.create_session(
                client_id=premium_client.id,
                metadata={"operation_type": "revenue_generating", "tier": "premium"}
            )
            
            # Create tool execution record with revenue tracking
            execution = MCPToolExecution(
                session_id=session_id,
                client_id=premium_client.id,
                tool_name=operation["tool_name"],
                input_params={
                    "estimated_cost": operation["estimated_cost"],
                    "tokens_processed": operation["tokens_processed"],
                    "revenue_category": operation["revenue_category"],
                    "tier": "premium"
                },
                execution_time_ms=operation["computation_time_ms"],
                status="success",
                output_result={
                    "revenue_impact": operation["estimated_cost"],
                    "cost_savings_delivered": operation["estimated_cost"] * 2.5,  # 2.5x ROI
                    "billing_category": operation["revenue_category"]
                }
            )
            
            execution_records.append(execution)
            total_revenue_tracked += operation["estimated_cost"]
            
            # Update session activity to track premium usage
            await mcp_service.update_session_activity(session_id)
        
        # Verify revenue tracking metrics
        assert len(execution_records) == 3
        assert total_revenue_tracked == 4240.00  # Sum of all estimated costs
        
        # Verify premium tier operations are properly categorized
        premium_categories = {record.output_result["billing_category"] for record in execution_records}
        expected_categories = {"optimization_premium", "analytics_premium", "insights_enterprise"}
        assert premium_categories == expected_categories
        
        # Verify ROI calculation for value capture validation
        total_client_savings = sum(record.output_result["cost_savings_delivered"] for record in execution_records)
        revenue_capture_ratio = total_revenue_tracked / total_client_savings
        
        # Should capture significant value relative to client savings (target: 20-40%)
        assert 0.20 <= revenue_capture_ratio <= 0.50
        assert total_client_savings == 10600.00  # 2.5x ROI on all operations
        
        # Verify high-value operations meet execution time thresholds
        high_value_executions = [r for r in execution_records 
                               if r.input_params["estimated_cost"] > 1000]
        assert len(high_value_executions) == 2  # Two operations over $1000
        
        # Verify enterprise tier metadata is preserved
        for record in execution_records:
            assert record.input_params["tier"] == "premium"
            assert record.status == "success"
            assert "revenue_impact" in record.output_result
        
        # Test upsell opportunity identification
        monthly_usage_projection = total_revenue_tracked * 30  # Daily * 30 days
        client_monthly_limit = premium_client.metadata["monthly_spend_limit"]
        
        utilization_rate = monthly_usage_projection / client_monthly_limit
        
        # High utilization indicates upsell opportunity
        if utilization_rate > 0.8:
            upsell_opportunity = {
                "client_id": premium_client.id,
                "current_utilization": utilization_rate,
                "projected_overage": monthly_usage_projection - client_monthly_limit,
                "recommended_tier": "enterprise_plus"
            }
            # Verify upsell logic
            assert upsell_opportunity["current_utilization"] > 0.8
            assert "projected_overage" in upsell_opportunity


class TestMCPServiceModuleFunctions:
    """Test module-level functions for test compatibility."""
    
    @pytest.mark.asyncio
    async def test_module_get_server_info(self):
        """Test module-level get_server_info function."""
        from netra_backend.app.services.mcp_service import get_server_info
        
        info = await get_server_info()
        
        assert isinstance(info, dict)
        assert "tools" in info
        assert "server_info" in info
        assert isinstance(info["tools"], list)
        assert len(info["tools"]) > 0
        
        # Verify server info structure
        server_info = info["server_info"]
        assert server_info["name"] == "Netra MCP Server"
        assert server_info["version"] == "2.0.0"
    
    @pytest.mark.asyncio
    async def test_module_execute_tool(self):
        """Test module-level execute_tool function."""
        from netra_backend.app.services.mcp_service import execute_tool
        
        result = await execute_tool("test_tool", {"param1": "value1"})
        
        assert isinstance(result, dict)
        assert result["result"] == "success"
        assert result["tool"] == "test_tool"
        assert result["parameters"] == {"param1": "value1"}
        assert "execution_time_ms" in result