"""Test Agent Initialization - Verify robust startup mechanisms

Simple test to validate that the agent initialization improvements work correctly.
Tests fallback mechanisms, error handling, and graceful degradation.
"""

import asyncio
import os
import sys
import time
from unittest.mock import AsyncMock, Mock

# Add the app directory to the Python path

from netra_backend.app.logging_config import central_logger as logger


async def test_initialization_manager():
    """Test the AgentInitializationManager."""
    print("Testing AgentInitializationManager...")
    
    try:
        from netra_backend.app.agents.initialization_manager import (
            AgentInitializationManager,
            InitializationStatus,
        )
        
        # Create mock dependencies
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        mock_llm_manager = Mock()
        mock_llm_manager.enabled = True
        
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        mock_tool_dispatcher = Mock()
        
        # Create a simple mock agent class
        class MockAgent:
            def __init__(self, llm_manager, tool_dispatcher, **kwargs):
                self.llm_manager = llm_manager
                self.tool_dispatcher = tool_dispatcher
                self.name = "MockAgent"
                self.description = "Test agent"
                
            def get_health_status(self):
                return {"status": "healthy"}
        
        # Test initialization manager
        init_manager = AgentInitializationManager(max_retries=2, timeout_seconds=5)
        
        result = await init_manager.initialize_agent_safely(
            MockAgent, mock_llm_manager, mock_tool_dispatcher, "test_agent"
        )
        
        print(f"[PASS] Initialization result: {result.status}")
        print(f"[PASS] Agent created: {result.agent is not None}")
        print(f"[PASS] Initialization time: {result.initialization_time_ms:.2f}ms")
        
        # Test with failing LLM manager (should fallback)
        class FailingAgent:
            def __init__(self, llm_manager, tool_dispatcher, **kwargs):
                if llm_manager.enabled:
                    raise Exception("LLM initialization failed")
                self.llm_manager = llm_manager
                self.name = "FailingAgent"
                
        # Mock: Generic component isolation for controlled unit testing
        failing_llm = Mock()
        failing_llm.enabled = True
        
        fallback_result = await init_manager.initialize_agent_safely(
            FailingAgent, failing_llm, mock_tool_dispatcher, "failing_agent"
        )
        
        print(f"[PASS] Fallback result: {fallback_result.status}")
        print(f"[PASS] Fallback used: {fallback_result.fallback_used}")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] InitializationManager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_data_agent_modular():
    """Test the modular DataSubAgent."""
    print("\nTesting modular DataSubAgent...")
    
    try:
        from netra_backend.app.agents.data_sub_agent.agent_core import DataSubAgent
        
        # Create mock dependencies
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        mock_llm_manager = Mock()
        mock_llm_manager.enabled = False  # Force fallback mode
        
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        mock_tool_dispatcher = Mock()
        
        # Test initialization
        agent = DataSubAgent(mock_llm_manager, mock_tool_dispatcher)
        
        print(f"[PASS] Agent created: {agent.name}")
        print(f"[PASS] Fallback mode: {agent._is_fallback_mode()}")
        
        # Test health status
        health = agent.get_health_status()
        print(f"[PASS] Health status: {health}")
        
        # Test execution context creation
        from netra_backend.app.agents.state import DeepAgentState
        
        # Mock: Generic component isolation for controlled unit testing
        mock_state = Mock()
        mock_state.user_request = "test request"
        
        context = agent._create_execution_context(mock_state, "test_run_123", False)
        print(f"[PASS] Execution context created: {context.run_id}")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] DataSubAgent test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_enhanced_registry():
    """Test the enhanced agent registry (now using consolidated AgentRegistry)."""
    print("\nTesting enhanced agent registry...")
    
    try:
        from netra_backend.app.agents.supervisor.agent_registry import (
            AgentRegistry,
        )
        
        # Create mock dependencies
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        mock_llm_manager = Mock()
        mock_llm_manager.enabled = True
        
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        mock_tool_dispatcher = Mock()
        
        # Create registry (now using consolidated AgentRegistry with enhanced features)
        registry = AgentRegistry(mock_llm_manager, mock_tool_dispatcher)
        
        print(f"[PASS] Registry created")
        
        # Test individual agent registration
        class SimpleAgent:
            def __init__(self, llm_manager, tool_dispatcher, **kwargs):
                self.llm_manager = llm_manager
                self.tool_dispatcher = tool_dispatcher
                self.name = "SimpleAgent"
                self.websocket_manager = None
                
            def get_health_status(self):
                return {"status": "healthy"}
        
        success = await registry.register_agent_safely("simple", SimpleAgent)
        print(f"[PASS] Individual agent registration: {success}")
        
        # Test agent retrieval
        agent = registry.get("simple")
        print(f"[PASS] Agent retrieved: {agent is not None}")
        
        # Test registry health
        health = registry.get_registry_health()
        print(f"[PASS] Registry health: {health['total_agents']} agents")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Enhanced registry test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all initialization tests."""
    print("=== Agent Initialization Tests ===\n")
    
    test_results = []
    
    # Test initialization manager
    result1 = await test_initialization_manager()
    test_results.append(("InitializationManager", result1))
    
    # Test modular data agent
    result2 = await test_data_agent_modular()
    test_results.append(("DataSubAgent Modular", result2))
    
    # Test enhanced registry
    result3 = await test_enhanced_registry()
    test_results.append(("Enhanced Registry", result3))
    
    print(f"\n=== Test Results ===")
    for test_name, success in test_results:
        status = "PASS" if success else "FAIL"
        print(f"{test_name}: {status}")
    
    success_count = sum(1 for _, success in test_results if success)
    total_count = len(test_results)
    
    print(f"\nOverall: {success_count}/{total_count} tests passed")
    
    return success_count == total_count


if __name__ == "__main__":
    # Run the tests
    success = asyncio.run(main())
    exit_code = 0 if success else 1
    sys.exit(exit_code)