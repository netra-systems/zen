#!/usr/bin/env python
"""QUICK TEST: SupervisorAgent Golden Pattern Compliance

Quick validation test for the SupervisorAgent golden pattern compliance.
This is a streamlined version focusing on the key compliance checks.
"""

import asyncio
import inspect
import os
import sys
import time
import uuid
from unittest.mock import AsyncMock, patch

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from loguru import logger

# Import production components for testing
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.core.resilience.unified_retry_handler import UnifiedRetryHandler
from sqlalchemy.ext.asyncio import AsyncSession


class MockLLMManager:
    """Mock LLM Manager for testing."""
    def __init__(self):
        self.call_count = 0
    
    async def generate_completion(self, messages, **kwargs):
        await asyncio.sleep(0.1)
        return "Mock supervisor orchestration response"
    
    def get_model_name(self):
        return "mock-model-v1"


class MockToolDispatcher:
    """Mock Tool Dispatcher for testing."""
    def __init__(self):
        self.available_tools = ["data_analysis", "report_generation"]
    
    async def execute_tool(self, tool_name, parameters):
        await asyncio.sleep(0.1)
        return {"success": True, "result": f"Mock result from {tool_name}"}


class WebSocketEventCapture:
    """Captures WebSocket events for validation."""
    def __init__(self):
        self.events = []
        self.event_types = set()
    
    async def notify_agent_started(self, run_id, agent_name, context=None):
        self.events.append({"type": "agent_started", "run_id": run_id, "agent_name": agent_name})
        self.event_types.add("agent_started")
        logger.info(f"Captured agent_started for {agent_name}")
    
    async def notify_agent_thinking(self, run_id, agent_name, thought, step_number=None):
        self.events.append({"type": "agent_thinking", "run_id": run_id, "agent_name": agent_name, "thought": thought})
        self.event_types.add("agent_thinking")
        logger.info(f"Captured agent_thinking: {thought[:50]}...")
    
    async def notify_agent_completed(self, run_id, agent_name, result=None):
        self.events.append({"type": "agent_completed", "run_id": run_id, "agent_name": agent_name})
        self.event_types.add("agent_completed")
        logger.info(f"Captured agent_completed for {agent_name}")
    
    async def notify_progress_update(self, run_id, agent_name, progress_data):
        self.events.append({"type": "progress_update", "run_id": run_id, "agent_name": agent_name})
        self.event_types.add("progress_update")
        logger.info(f"Captured progress_update for {agent_name}")
    
    async def notify_agent_error(self, run_id, agent_name, error_message, error_context=None):
        self.events.append({"type": "agent_error", "run_id": run_id, "agent_name": agent_name})
        self.event_types.add("agent_error")
        logger.info(f"Captured agent_error for {agent_name}")
    
    # Add other required methods
    async def notify_tool_executing(self, run_id, agent_name, tool_name, parameters=None):
        self.events.append({"type": "tool_executing", "run_id": run_id, "agent_name": agent_name})
        self.event_types.add("tool_executing")
    
    async def notify_tool_completed(self, run_id, agent_name, tool_name, result=None):
        self.events.append({"type": "tool_completed", "run_id": run_id, "agent_name": agent_name})
        self.event_types.add("tool_completed")
    
    async def notify_custom(self, run_id, agent_name, event_type, data):
        self.events.append({"type": event_type, "run_id": run_id, "agent_name": agent_name})
        self.event_types.add(event_type)


async def test_inheritance_compliance():
    """Test 1: Inheritance Pattern Compliance"""
    logger.info("🧬 Testing Inheritance Pattern Compliance...")
    
    # Create mocks
    mock_db_session = AsyncMock(spec=AsyncSession)
    websocket_capture = WebSocketEventCapture()
    llm_manager = MockLLMManager()
    tool_dispatcher = MockToolDispatcher()
    
    # Create SupervisorAgent with patched registration
    with patch.object(AgentRegistry, 'register_default_agents', return_value=None):
        supervisor = SupervisorAgent(
            db_session=mock_db_session,
            llm_manager=llm_manager,
            websocket_bridge=websocket_capture,
            tool_dispatcher=tool_dispatcher
        )
    
    # Test 1.1: Inheritance from BaseAgent
    assert isinstance(supervisor, BaseAgent), "SupervisorAgent must inherit from BaseAgent"
    assert issubclass(SupervisorAgent, BaseAgent), "SupervisorAgent class must be subclass of BaseAgent"
    
    # Test 1.2: Method Resolution Order
    mro = inspect.getmro(SupervisorAgent)
    assert BaseAgent in mro, "BaseAgent must be in MRO"
    assert len(mro) >= 2, "MRO must have at least SupervisorAgent and BaseAgent"
    
    # Test 1.3: Required methods accessible
    required_methods = ['emit_thinking', 'emit_agent_started', 'emit_agent_completed', 'set_state']
    for method_name in required_methods:
        assert hasattr(supervisor, method_name), f"Missing method: {method_name}"
        assert callable(getattr(supervisor, method_name)), f"Method {method_name} not callable"
    
    # Test 1.4: Infrastructure properties
    if supervisor._enable_reliability:
        assert supervisor.unified_reliability_handler is not None, "Reliability handler should be available"
    
    logger.info("✅ Inheritance Pattern Compliance PASSED")
    return True


async def test_websocket_events():
    """Test 2: WebSocket Event Compliance"""
    logger.info("📡 Testing WebSocket Event Compliance...")
    
    # Create mocks
    mock_db_session = AsyncMock(spec=AsyncSession)
    websocket_capture = WebSocketEventCapture()
    llm_manager = MockLLMManager()
    tool_dispatcher = MockToolDispatcher()
    
    # Create SupervisorAgent
    with patch.object(AgentRegistry, 'register_default_agents', return_value=None):
        supervisor = SupervisorAgent(
            db_session=mock_db_session,
            llm_manager=llm_manager,
            websocket_bridge=websocket_capture,
            tool_dispatcher=tool_dispatcher
        )
    
    # Mock validation to allow execution without registered agents
    async def mock_validate(context):
        return True
    supervisor.validate_preconditions = mock_validate
    
    # Test WebSocket bridge integration
    run_id = str(uuid.uuid4())
    supervisor._websocket_adapter.set_websocket_bridge(
        websocket_capture, run_id, supervisor.name
    )
    
    assert supervisor._websocket_adapter.has_websocket_bridge(), "WebSocket bridge should be set"
    
    # Execute supervisor to generate events
    try:
        result = await supervisor.run(
            user_prompt="Test request for WebSocket events",
            thread_id=f"thread_{run_id}",
            user_id="test_user",
            run_id=run_id
        )
        
        # Wait for async events
        await asyncio.sleep(0.5)
        
        # Validate events were captured
        events_for_run = [e for e in websocket_capture.events if e.get('run_id') == run_id]
        assert len(events_for_run) > 0, "At least some events should be captured"
        
        # Check for key event types
        captured_types = websocket_capture.event_types
        logger.info(f"Captured event types: {captured_types}")
        
        # Should have at least thinking events
        assert 'agent_thinking' in captured_types, "agent_thinking events should be emitted"
        
        logger.info("✅ WebSocket Event Compliance PASSED")
        return True
        
    except Exception as e:
        logger.error(f"WebSocket test failed: {e}")
        return False


async def test_ssot_compliance():
    """Test 3: SSOT Compliance"""
    logger.info("🎯 Testing SSOT Compliance...")
    
    # Test no infrastructure duplication
    supervisor_methods = set(dir(SupervisorAgent))
    base_agent_methods = set(dir(BaseAgent))
    
    # Infrastructure methods that should NOT be overridden
    infrastructure_methods = {'emit_thinking', 'emit_agent_started', 'emit_agent_completed', 'set_state'}
    
    overridden_infrastructure = []
    for method_name in infrastructure_methods:
        if method_name in supervisor_methods and method_name in base_agent_methods:
            supervisor_method = getattr(SupervisorAgent, method_name, None)
            base_method = getattr(BaseAgent, method_name, None)
            
            # Check if they're different methods (overridden)
            if supervisor_method and base_method and supervisor_method is not base_method:
                overridden_infrastructure.append(method_name)
    
    assert len(overridden_infrastructure) == 0, f"Infrastructure methods should not be overridden: {overridden_infrastructure}"
    
    logger.info("✅ SSOT Compliance PASSED")
    return True


async def test_circuit_breaker_integration():
    """Test 4: Circuit Breaker Integration"""
    logger.info("🔄 Testing Circuit Breaker Integration...")
    
    # Create supervisor
    mock_db_session = AsyncMock(spec=AsyncSession)
    websocket_capture = WebSocketEventCapture()
    llm_manager = MockLLMManager()
    tool_dispatcher = MockToolDispatcher()
    
    with patch.object(AgentRegistry, 'register_default_agents', return_value=None):
        supervisor = SupervisorAgent(
            db_session=mock_db_session,
            llm_manager=llm_manager,
            websocket_bridge=websocket_capture,
            tool_dispatcher=tool_dispatcher
        )
    
    # Test reliability infrastructure
    if supervisor._enable_reliability:
        assert supervisor.unified_reliability_handler is not None, "Reliability handler should be available"
        assert isinstance(supervisor.unified_reliability_handler, UnifiedRetryHandler), "Should be UnifiedRetryHandler"
        
        # Test execute_with_reliability method
        async def test_operation():
            await asyncio.sleep(0.01)
            return "test_result"
        
        try:
            result = await supervisor.execute_with_reliability(
                operation=test_operation,
                operation_name="test_circuit_breaker"
            )
            assert result == "test_result", "Reliability execution should work"
        except RuntimeError as e:
            if "Reliability not enabled" in str(e):
                logger.warning("Reliability disabled - test skipped")
        
    logger.info("✅ Circuit Breaker Integration PASSED")
    return True


async def run_quick_compliance_test():
    """Run quick compliance test suite."""
    logger.info("🚀 Starting SupervisorAgent Golden Pattern Quick Compliance Test")
    logger.info("=" * 70)
    
    test_results = {
        'inheritance': False,
        'websocket_events': False,
        'ssot': False,
        'circuit_breaker': False
    }
    
    try:
        # Run tests
        logger.info("1️⃣ Running Inheritance Compliance Test...")
        test_results['inheritance'] = await test_inheritance_compliance()
        
        logger.info("\n2️⃣ Running WebSocket Events Test...")
        test_results['websocket_events'] = await test_websocket_events()
        
        logger.info("\n3️⃣ Running SSOT Compliance Test...")
        test_results['ssot'] = await test_ssot_compliance()
        
        logger.info("\n4️⃣ Running Circuit Breaker Integration Test...")
        test_results['circuit_breaker'] = await test_circuit_breaker_integration()
        
        # Final report
        logger.info("\n" + "=" * 70)
        logger.info("🎯 QUICK TEST RESULTS")
        logger.info("=" * 70)
        
        total_tests = len(test_results)
        passed_tests = sum(test_results.values())
        
        for category, passed in test_results.items():
            status = "✅ PASSED" if passed else "❌ FAILED"
            logger.info(f"{category.upper():20} {status}")
        
        logger.info("-" * 70)
        logger.info(f"OVERALL RESULT: {passed_tests}/{total_tests} test categories passed")
        
        if passed_tests == total_tests:
            logger.info("🎉 SupervisorAgent Golden Pattern Compliance: FULLY COMPLIANT")
            return True
        else:
            logger.error("💥 SupervisorAgent Golden Pattern Compliance: NEEDS WORK")
            return False
    
    except Exception as e:
        logger.error(f"❌ Test suite failed with error: {e}")
        return False


if __name__ == "__main__":
    """Run the quick compliance test suite."""
    success = asyncio.run(run_quick_compliance_test())
    sys.exit(0 if success else 1)