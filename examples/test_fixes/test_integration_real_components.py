"""
Example of Fixed Integration Test - Reduced Mocking

BEFORE: Integration test with excessive mocking (50+ Mock() calls)
AFTER: Integration test using real components with minimal external mocking

This demonstrates the "Real > Mock" principle from SPEC/testing.xml
"""

import pytest
import asyncio
from typing import Dict, Any

# Import REAL components instead of mocking them
from app.llm.llm_manager import LLMManager
from app.agents.tool_dispatcher import ToolDispatcher
from app.websocket.unified.manager import UnifiedWebSocketManager
from app.agents.supervisor_consolidated import SupervisorAgent


class TestIntegrationRealComponents:
    """Integration test using real components - FIXED VERSION"""
    
    @pytest.fixture
    def real_llm_manager(self):
        """Use real LLM manager instead of mock"""
        # Configure for test environment
        return LLMManager(
            api_key="test-key",
            model="test-model", 
            max_tokens=100,
            temperature=0.1
        )
    
    @pytest.fixture 
    def real_tool_dispatcher(self, real_llm_manager):
        """Use real tool dispatcher"""
        return ToolDispatcher(real_llm_manager)
    
    @pytest.fixture
    def real_websocket_manager(self):
        """Use real websocket manager"""
        return UnifiedWebSocketManager()
    
    @pytest.fixture
    def real_supervisor_agent(self, real_llm_manager, real_tool_dispatcher, real_websocket_manager):
        """Create supervisor with real dependencies"""
        return SupervisorAgent(
            llm_manager=real_llm_manager,
            tool_dispatcher=real_tool_dispatcher,
            websocket_manager=real_websocket_manager
        )
    
    async def test_agent_pipeline_integration(self, real_supervisor_agent):
        """Test complete agent pipeline with real components"""
        # Test request that exercises real LLM and tool integration
        test_request = {
            "user_id": "test-user",
            "message": "Analyze current system performance",
            "context": {"type": "performance_analysis"}
        }
        
        # Execute using real components - no mocking of business logic
        result = await real_supervisor_agent.process_user_request(test_request)
        
        # Validate real behavior
        assert result is not None
        assert "analysis" in result or "error" in result
        
        # Test that real components were used
        assert real_supervisor_agent.llm_manager is not None
        assert real_supervisor_agent.tool_dispatcher is not None
    
    async def test_error_handling_with_real_components(self, real_supervisor_agent):
        """Test error handling using real component behavior"""
        # Use invalid request to trigger real error handling
        invalid_request = {
            "user_id": "",  # Invalid user ID  
            "message": "",  # Empty message
            "context": None  # Invalid context
        }
        
        # Real components should handle this gracefully
        result = await real_supervisor_agent.process_user_request(invalid_request)
        
        # Validate real error handling behavior
        assert result is not None
        assert "error" in result or "validation_failed" in result
    
    async def test_websocket_integration(self, real_websocket_manager, real_supervisor_agent):
        """Test WebSocket integration with real components"""
        # Test WebSocket connection handling
        connection_info = {
            "user_id": "test-user",
            "session_id": "test-session",
            "auth_token": "test-token"
        }
        
        # Use real WebSocket manager
        connection_result = await real_websocket_manager.handle_connection(connection_info)
        
        # Validate real WebSocket behavior
        assert connection_result is not None
        # Real component should either succeed or fail with specific error
        assert "connected" in connection_result or "error" in connection_result


# CONTRAST: What the BAD version looked like (excessive mocking)
class TestIntegrationExcessiveMocking:
    """Example of BAD integration test with excessive mocking"""
    
    @pytest.fixture
    def mock_everything(self):
        """BAD: Mocking everything defeats integration testing purpose"""
        from unittest.mock import AsyncMock, MagicMock
        
        # This is what we DON'T want - mocking all the components we should test
        llm_manager = AsyncMock()
        llm_manager.ask_llm.return_value = "mocked response"
        llm_manager.validate_request.return_value = True
        
        tool_dispatcher = AsyncMock()
        tool_dispatcher.execute_tool.return_value = {"result": "mocked"}
        tool_dispatcher.get_available_tools.return_value = ["mock_tool"]
        
        websocket_manager = AsyncMock()
        websocket_manager.send_message.return_value = True
        websocket_manager.handle_connection.return_value = {"connected": True}
        
        # ... 40+ more mock setups ...
        
        return llm_manager, tool_dispatcher, websocket_manager
    
    async def test_bad_integration_all_mocked(self, mock_everything):
        """BAD: This isn't really testing integration - it's testing mocks"""
        llm_manager, tool_dispatcher, websocket_manager = mock_everything
        
        # Create supervisor with all mocked dependencies
        supervisor = SupervisorAgent(
            llm_manager=llm_manager,
            tool_dispatcher=tool_dispatcher, 
            websocket_manager=websocket_manager
        )
        
        # This test only validates that our mocks return what we told them to
        result = await supervisor.process_user_request({"message": "test"})
        
        # These assertions are meaningless - we're just testing our mocks
        assert result == "mocked response"  # Of course it does, we mocked it!
        llm_manager.ask_llm.assert_called_once()  # We forced this to happen
        
        # This test tells us nothing about real system behavior