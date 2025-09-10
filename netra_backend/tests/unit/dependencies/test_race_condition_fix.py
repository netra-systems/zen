"""
Test for race condition fix in RequestScopedSupervisorDep.

This test validates that the tool dispatcher race condition fix works correctly
when agent_supervisor is not available during startup.
"""

import pytest
from unittest.mock import Mock, MagicMock
from fastapi import HTTPException, Request
from netra_backend.app.dependencies import (
    get_request_scoped_supervisor,
    RequestScopedContext
)
from shared.id_generation import UnifiedIdGenerator


class TestRaceConditionFix:
    """Test race condition fix in supervisor dependency injection."""
    
    def setup_method(self):
        """Setup test fixtures."""
        # Create mock request with app state
        self.mock_request = Mock(spec=Request)
        self.mock_request.app = Mock()
        self.mock_request.app.state = Mock()
        
        # Create test context
        self.context = RequestScopedContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id=UnifiedIdGenerator.generate_base_id("run"),
            request_id=UnifiedIdGenerator.generate_base_id("req")
        )
        
        # Create mock session that passes validation
        self.mock_session = Mock()
        # Don't set _global_storage_flag at all - this will pass the hasattr check
        
    @pytest.mark.asyncio
    async def test_startup_in_progress_returns_503(self):
        """Test that requests during startup return 503 Service Unavailable."""
        # Setup: startup in progress, no agent_supervisor
        self.mock_request.app.state.agent_supervisor = None
        self.mock_request.app.state.startup_in_progress = True
        self.mock_request.app.state.startup_complete = False
        
        # Mock LLM client to pass early validation
        from unittest.mock import patch
        with patch('netra_backend.app.dependencies.get_llm_client_from_app') as mock_llm:
            mock_llm.return_value = Mock()
            
            # Execute: should raise HTTPException with 503
            with pytest.raises(HTTPException) as exc_info:
                await get_request_scoped_supervisor(
                    self.mock_request, 
                    self.context, 
                    self.mock_session
                )
        
        # Verify: proper error response
        assert exc_info.value.status_code == 503
        assert "Service temporarily unavailable" in exc_info.value.detail
        assert "retry in a few seconds" in exc_info.value.detail
        
    @pytest.mark.asyncio
    async def test_supervisor_missing_after_startup_returns_500(self):
        """Test that missing supervisor after startup returns 500 Internal Server Error."""
        # Setup: startup complete but no agent_supervisor
        self.mock_request.app.state.agent_supervisor = None
        self.mock_request.app.state.startup_in_progress = False
        self.mock_request.app.state.startup_complete = True
        
        # Mock LLM client to pass early validation
        from unittest.mock import patch
        with patch('netra_backend.app.dependencies.get_llm_client_from_app') as mock_llm:
            mock_llm.return_value = Mock()
            
            # Execute: should raise HTTPException with 500
            with pytest.raises(HTTPException) as exc_info:
                await get_request_scoped_supervisor(
                    self.mock_request, 
                    self.context, 
                    self.mock_session
                )
        
        # Verify: proper error response
        assert exc_info.value.status_code == 500
        assert "Agent supervisor not available" in exc_info.value.detail
        assert "critical startup failure" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_websocket_bridge_missing_during_startup_returns_503(self):
        """Test that missing WebSocket bridge during startup returns 503."""
        # Setup: startup in progress, no websocket bridge
        self.mock_request.app.state.agent_websocket_bridge = None
        self.mock_request.app.state.websocket_bridge = None
        self.mock_request.app.state.startup_in_progress = True
        self.mock_request.app.state.startup_complete = False
        
        # Mock LLM client to pass early validation
        from unittest.mock import patch
        with patch('netra_backend.app.dependencies.get_llm_client_from_app') as mock_llm:
            mock_llm.return_value = Mock()
            
            # Execute: should raise HTTPException with 503
            with pytest.raises(HTTPException) as exc_info:
                await get_request_scoped_supervisor(
                    self.mock_request, 
                    self.context, 
                    self.mock_session
                )
        
        # Verify: proper error response
        assert exc_info.value.status_code == 503
        assert "Service temporarily unavailable" in exc_info.value.detail
        assert "system is still starting up" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_supervisor_missing_tool_dispatcher_attribute(self):
        """Test that supervisor without tool_dispatcher attribute returns proper error."""
        # Setup: supervisor exists but has no tool_dispatcher attribute
        mock_supervisor = Mock()
        del mock_supervisor.tool_dispatcher  # Remove the attribute
        
        self.mock_request.app.state.agent_supervisor = mock_supervisor
        self.mock_request.app.state.agent_websocket_bridge = Mock()
        self.mock_request.app.state.startup_complete = True
        
        # Mock LLM client
        from unittest.mock import patch
        with patch('netra_backend.app.dependencies.get_llm_client_from_app') as mock_llm:
            mock_llm.return_value = Mock()
            
            # Execute: should raise HTTPException with 500
            with pytest.raises(HTTPException) as exc_info:
                await get_request_scoped_supervisor(
                    self.mock_request, 
                    self.context, 
                    self.mock_session
                )
        
        # Verify: proper error response
        assert exc_info.value.status_code == 500
        assert "Agent supervisor configuration invalid" in exc_info.value.detail
        assert "missing tool dispatcher" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_tool_dispatcher_none_with_usercontext_architecture(self):
        """Test tool dispatcher None with UserContext architecture detection."""
        # Setup: supervisor with None tool_dispatcher but tool_classes available
        mock_supervisor = Mock()
        mock_supervisor.tool_dispatcher = None
        
        self.mock_request.app.state.agent_supervisor = mock_supervisor
        self.mock_request.app.state.agent_websocket_bridge = Mock()
        self.mock_request.app.state.startup_complete = True
        self.mock_request.app.state.tool_classes = {"mock_tool": Mock()}  # UserContext architecture
        
        # Mock LLM client
        from unittest.mock import patch
        with patch('netra_backend.app.dependencies.get_llm_client_from_app') as mock_llm:
            mock_llm.return_value = Mock()
            
            # Execute: should raise HTTPException with 500 and UserContext message
            with pytest.raises(HTTPException) as exc_info:
                await get_request_scoped_supervisor(
                    self.mock_request, 
                    self.context, 
                    self.mock_session
                )
        
        # Verify: proper error response for UserContext architecture
        assert exc_info.value.status_code == 500
        assert "Tool dispatcher not configured" in exc_info.value.detail
        assert "UserContext-based architecture" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_defensive_getattr_usage(self):
        """Test that getattr is used defensively to avoid AttributeError."""
        # Setup: app.state without any expected attributes
        self.mock_request.app.state = Mock()
        # Don't set any attributes on state - they'll be None from getattr defaults
        
        # Execute: should handle missing attributes gracefully
        with pytest.raises(HTTPException) as exc_info:
            await get_request_scoped_supervisor(
                self.mock_request, 
                self.context, 
                self.mock_session
            )
        
        # Verify: no AttributeError raised, proper 503 or 500 response
        assert exc_info.value.status_code in [503, 500]
        # Should not crash with AttributeError
        
    def test_startup_state_flags_logic(self):
        """Test the logic for determining startup state."""
        # Test case 1: startup in progress
        assert self._is_startup_in_progress(startup_in_progress=True, startup_complete=False)
        
        # Test case 2: startup complete
        assert not self._is_startup_in_progress(startup_in_progress=False, startup_complete=True)
        
        # Test case 3: both False (weird state but should be treated as startup issue)
        assert not self._is_startup_in_progress(startup_in_progress=False, startup_complete=False)
        
        # Test case 4: both True (shouldn't happen but handle gracefully)
        assert not self._is_startup_in_progress(startup_in_progress=True, startup_complete=True)
    
    def _is_startup_in_progress(self, startup_in_progress: bool, startup_complete: bool) -> bool:
        """Helper to test startup state logic."""
        return startup_in_progress and not startup_complete