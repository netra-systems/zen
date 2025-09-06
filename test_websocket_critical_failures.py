#!/usr/bin/env python3
"""
WebSocket Event Pipeline Critical Failures Test Suite
MISSION CRITICAL: Comprehensive test suite exposing all WebSocket event pipeline failures

Business Value: $500K+ ARR - Core chat functionality broken
Created: 2025-01-05
Status: FAILING - These tests expose the critical issues

This test suite provides comprehensive coverage of the WebSocket event pipeline failures,
giving us concrete failing tests that must pass before the system can be considered fixed.
"""

import asyncio
import os
import sys
import time
import uuid
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from unittest.mock import Mock, AsyncMock, patch
import traceback

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.isolated_environment import get_env
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class TestResult:
    """Track individual test results."""
    test_name: str
    passed: bool
    error_message: Optional[str] = None
    duration_ms: float = 0.0
    critical_events_captured: List[str] = field(default_factory=list)
    
    def __str__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        msg = f"{status} {self.test_name} ({self.duration_ms:.2f}ms)"
        if self.error_message:
            msg += f"\n   Error: {self.error_message}"
        if self.critical_events_captured:
            msg += f"\n   Events: {', '.join(self.critical_events_captured)}"
        return msg


class CriticalEventCapture:
    """Capture and validate critical WebSocket events."""
    
    CRITICAL_EVENTS = {
        'agent_started',
        'agent_thinking', 
        'tool_executing',
        'tool_completed',
        'agent_completed'
    }
    
    def __init__(self):
        self.captured_events: List[Dict[str, Any]] = []
        self.event_types: Set[str] = set()
        
    async def capture_event(self, event_type: str, data: Dict[str, Any]):
        """Capture a WebSocket event."""
        self.captured_events.append({
            'type': event_type,
            'data': data,
            'timestamp': time.time()
        })
        self.event_types.add(event_type)
        
    def validate_critical_events(self) -> TestResult:
        """Validate all critical events were captured."""
        missing = self.CRITICAL_EVENTS - self.event_types
        if missing:
            return TestResult(
                test_name="Critical Events Validation",
                passed=False,
                error_message=f"Missing events: {missing}",
                critical_events_captured=list(self.event_types)
            )
        return TestResult(
            test_name="Critical Events Validation",
            passed=True,
            critical_events_captured=list(self.event_types)
        )


class WebSocketPipelineTests:
    """Comprehensive test suite for WebSocket event pipeline."""
    
    def __init__(self):
        self.results: List[TestResult] = []
        
    async def test_import_chain_singleton_issue(self) -> TestResult:
        """Test #1: Verify singleton import chain issue."""
        start = time.time()
        try:
            from netra_backend.app.websocket_core import get_websocket_manager
            manager = get_websocket_manager()
            
            # Check if using deprecated singleton
            is_singleton = "netra_backend.app.websocket_core.unified_manager.UnifiedWebSocketManager" in str(type(manager))
            
            if is_singleton:
                return TestResult(
                    test_name="Import Chain (Singleton Issue)",
                    passed=False,
                    error_message="Using deprecated singleton WebSocket manager",
                    duration_ms=(time.time() - start) * 1000
                )
            
            return TestResult(
                test_name="Import Chain (Singleton Issue)",
                passed=True,
                duration_ms=(time.time() - start) * 1000
            )
            
        except Exception as e:
            return TestResult(
                test_name="Import Chain (Singleton Issue)",
                passed=False,
                error_message=str(e),
                duration_ms=(time.time() - start) * 1000
            )
    
    async def test_create_user_emitter_async_issue(self) -> TestResult:
        """Test #2: Verify create_user_emitter async/await issue."""
        start = time.time()
        try:
            from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
            from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
            
            user_context = UserExecutionContext(
                user_id="test_user",
                thread_id="test_thread",
                run_id="test_run"
            )
            
            bridge = create_agent_websocket_bridge(user_context)
            
            # Test if create_user_emitter is async and not being awaited
            if hasattr(bridge, 'create_user_emitter'):
                emitter_result = bridge.create_user_emitter(user_context)
                
                # Check if it's a coroutine (async not awaited)
                if asyncio.iscoroutine(emitter_result):
                    # Try to await it
                    emitter = await emitter_result
                    
                    # Check for critical methods
                    critical_methods = [
                        'notify_agent_started',
                        'notify_agent_thinking',
                        'notify_tool_executing', 
                        'notify_tool_completed',
                        'notify_agent_completed'
                    ]
                    
                    missing = [m for m in critical_methods if not hasattr(emitter, m)]
                    
                    if missing:
                        return TestResult(
                            test_name="create_user_emitter Async Issue",
                            passed=False,
                            error_message=f"Emitter missing methods: {missing}",
                            duration_ms=(time.time() - start) * 1000
                        )
                    
                    return TestResult(
                        test_name="create_user_emitter Async Issue",
                        passed=True,
                        duration_ms=(time.time() - start) * 1000
                    )
                else:
                    # Not a coroutine, check if it has the methods directly
                    missing = [m for m in critical_methods if not hasattr(emitter_result, m)]
                    if missing:
                        return TestResult(
                            test_name="create_user_emitter Async Issue",
                            passed=False,
                            error_message=f"Returned non-awaitable object missing methods: {missing}",
                            duration_ms=(time.time() - start) * 1000
                        )
                    return TestResult(
                        test_name="create_user_emitter Async Issue",
                        passed=True,
                        duration_ms=(time.time() - start) * 1000
                    )
            else:
                return TestResult(
                    test_name="create_user_emitter Async Issue",
                    passed=False,
                    error_message="Bridge missing create_user_emitter method",
                    duration_ms=(time.time() - start) * 1000
                )
                
        except Exception as e:
            return TestResult(
                test_name="create_user_emitter Async Issue",
                passed=False,
                error_message=str(e),
                duration_ms=(time.time() - start) * 1000
            )
    
    async def test_agent_registry_initialization(self) -> TestResult:
        """Test #3: Verify AgentRegistry initialization with llm_manager."""
        start = time.time()
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
            from netra_backend.app.llm.client_unified import ResilientLLMClient
            from netra_backend.app.llm.llm_manager import LLMManager
            
            # Try to create AgentRegistry without llm_manager (should fail)
            try:
                registry = AgentRegistry()
                return TestResult(
                    test_name="AgentRegistry Initialization",
                    passed=False,
                    error_message="AgentRegistry allowed creation without llm_manager",
                    duration_ms=(time.time() - start) * 1000
                )
            except TypeError as e:
                # Expected - now try with proper llm_manager
                base_llm_manager = LLMManager()
                # Create ResilientLLMClient with proper LLM manager
                llm_manager = ResilientLLMClient(base_llm_manager)
                registry = AgentRegistry(llm_manager=llm_manager)
                
                # Check if set_websocket_manager exists
                if not hasattr(registry, 'set_websocket_manager'):
                    return TestResult(
                        test_name="AgentRegistry Initialization",
                        passed=False,
                        error_message="Registry missing set_websocket_manager method",
                        duration_ms=(time.time() - start) * 1000
                    )
                
                return TestResult(
                    test_name="AgentRegistry Initialization",
                    passed=True,
                    duration_ms=(time.time() - start) * 1000
                )
                
        except Exception as e:
            return TestResult(
                test_name="AgentRegistry Initialization",
                passed=False,
                error_message=str(e),
                duration_ms=(time.time() - start) * 1000
            )
    
    async def test_websocket_manager_factory_pattern(self) -> TestResult:
        """Test #4: Verify WebSocket manager factory pattern works."""
        start = time.time()
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
            from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
            
            user_context = UserExecutionContext(
                user_id="test_user_1",
                thread_id="test_thread_1",
                run_id="test_run_1"
            )
            
            manager1 = create_websocket_manager(user_context)
            
            # Create another context
            user_context2 = UserExecutionContext(
                user_id="test_user_2",
                thread_id="test_thread_2",
                run_id="test_run_2"
            )
            
            manager2 = create_websocket_manager(user_context2)
            
            # Managers should be different instances (not singleton)
            if manager1 is manager2:
                return TestResult(
                    test_name="WebSocket Manager Factory Pattern",
                    passed=False,
                    error_message="Factory returning same instance (singleton behavior)",
                    duration_ms=(time.time() - start) * 1000
                )
            
            return TestResult(
                test_name="WebSocket Manager Factory Pattern",
                passed=True,
                duration_ms=(time.time() - start) * 1000
            )
            
        except Exception as e:
            return TestResult(
                test_name="WebSocket Manager Factory Pattern",
                passed=False,
                error_message=str(e),
                duration_ms=(time.time() - start) * 1000
            )
    
    async def test_end_to_end_event_flow(self) -> TestResult:
        """Test #5: Verify end-to-end event flow with proper async handling."""
        start = time.time()
        event_capture = CriticalEventCapture()
        
        try:
            from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
            from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
            from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
            
            # Create user context
            user_context = UserExecutionContext(
                user_id="test_user",
                thread_id="test_thread",
                run_id="test_run"
            )
            
            # Create WebSocket manager
            manager = create_websocket_manager(user_context)
            
            # Mock the send_to_thread method to capture events
            async def mock_send(thread_id: str, message: Dict[str, Any]):
                await event_capture.capture_event(message.get('type', 'unknown'), message)
                return True
            
            manager.send_to_thread = mock_send
            
            # Create bridge
            bridge = create_agent_websocket_bridge(user_context)
            bridge._websocket_manager = manager
            
            # Create emitter (handle async properly)
            emitter_coro = bridge.create_user_emitter(user_context)
            if asyncio.iscoroutine(emitter_coro):
                emitter = await emitter_coro
            else:
                emitter = emitter_coro
            
            # Test all critical events
            if hasattr(emitter, 'notify_agent_started'):
                await emitter.notify_agent_started("TestAgent", {"run_id": "test"})
            
            if hasattr(emitter, 'notify_agent_thinking'):
                await emitter.notify_agent_thinking("Processing...", {"step": 1})
            
            if hasattr(emitter, 'notify_tool_executing'):
                await emitter.notify_tool_executing("analyzer", {"type": "data"})
            
            if hasattr(emitter, 'notify_tool_completed'):
                await emitter.notify_tool_completed("analyzer", {"result": "done"})
            
            if hasattr(emitter, 'notify_agent_completed'):
                await emitter.notify_agent_completed("TestAgent", {"status": "success"})
            
            # Validate captured events
            validation_result = event_capture.validate_critical_events()
            
            return TestResult(
                test_name="End-to-End Event Flow",
                passed=validation_result.passed,
                error_message=validation_result.error_message,
                critical_events_captured=list(event_capture.event_types),
                duration_ms=(time.time() - start) * 1000
            )
            
        except Exception as e:
            return TestResult(
                test_name="End-to-End Event Flow",
                passed=False,
                error_message=f"{type(e).__name__}: {str(e)}",
                critical_events_captured=list(event_capture.event_types),
                duration_ms=(time.time() - start) * 1000
            )
    
    async def test_concurrent_user_isolation(self) -> TestResult:
        """Test #6: Verify concurrent users have isolated event streams."""
        start = time.time()
        user1_events = []
        user2_events = []
        
        try:
            from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
            from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
            from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
            
            # Create two user contexts
            user1_context = UserExecutionContext(
                user_id="user1",
                thread_id="thread1",
                run_id="run1"
            )
            
            user2_context = UserExecutionContext(
                user_id="user2",
                thread_id="thread2",
                run_id="run2"
            )
            
            # Create managers and bridges for each user
            manager1 = create_websocket_manager(user1_context)
            manager2 = create_websocket_manager(user2_context)
            
            # Mock send methods
            async def mock_send1(thread_id: str, message: Dict[str, Any]):
                user1_events.append(message)
                return True
            
            async def mock_send2(thread_id: str, message: Dict[str, Any]):
                user2_events.append(message)
                return True
            
            manager1.send_to_thread = mock_send1
            manager2.send_to_thread = mock_send2
            
            bridge1 = create_agent_websocket_bridge(user1_context)
            bridge1._websocket_manager = manager1
            
            bridge2 = create_agent_websocket_bridge(user2_context)
            bridge2._websocket_manager = manager2
            
            # Create emitters
            emitter1_coro = bridge1.create_user_emitter(user1_context)
            emitter1 = await emitter1_coro if asyncio.iscoroutine(emitter1_coro) else emitter1_coro
            
            emitter2_coro = bridge2.create_user_emitter(user2_context)
            emitter2 = await emitter2_coro if asyncio.iscoroutine(emitter2_coro) else emitter2_coro
            
            # Send events from each user
            if hasattr(emitter1, 'notify_agent_started'):
                await emitter1.notify_agent_started("Agent1", {"user": "user1"})
            
            if hasattr(emitter2, 'notify_agent_started'):
                await emitter2.notify_agent_started("Agent2", {"user": "user2"})
            
            # Verify isolation
            if len(user1_events) == 0 or len(user2_events) == 0:
                return TestResult(
                    test_name="Concurrent User Isolation",
                    passed=False,
                    error_message="Events not captured for one or both users",
                    duration_ms=(time.time() - start) * 1000
                )
            
            # Check for cross-contamination
            user1_has_user2_data = any("user2" in str(e) for e in user1_events)
            user2_has_user1_data = any("user1" in str(e) for e in user2_events)
            
            if user1_has_user2_data or user2_has_user1_data:
                return TestResult(
                    test_name="Concurrent User Isolation",
                    passed=False,
                    error_message="Cross-user event contamination detected",
                    duration_ms=(time.time() - start) * 1000
                )
            
            return TestResult(
                test_name="Concurrent User Isolation",
                passed=True,
                duration_ms=(time.time() - start) * 1000
            )
            
        except Exception as e:
            return TestResult(
                test_name="Concurrent User Isolation",
                passed=False,
                error_message=str(e),
                duration_ms=(time.time() - start) * 1000
            )
    
    async def run_all_tests(self) -> List[TestResult]:
        """Run all tests in the suite."""
        test_methods = [
            self.test_import_chain_singleton_issue,
            self.test_create_user_emitter_async_issue,
            self.test_agent_registry_initialization,
            self.test_websocket_manager_factory_pattern,
            self.test_end_to_end_event_flow,
            self.test_concurrent_user_isolation
        ]
        
        for test_method in test_methods:
            try:
                result = await test_method()
                self.results.append(result)
                print(result)
            except Exception as e:
                self.results.append(TestResult(
                    test_name=test_method.__name__,
                    passed=False,
                    error_message=f"Test execution failed: {e}"
                ))
                print(f"FAIL {test_method.__name__}: {e}")
        
        return self.results


async def main():
    """Run the comprehensive test suite."""
    print("=" * 80)
    print("WEBSOCKET EVENT PIPELINE CRITICAL FAILURES TEST SUITE")
    print("Business Impact: $500K+ ARR at risk")
    print("=" * 80)
    print()
    
    test_suite = WebSocketPipelineTests()
    results = await test_suite.run_all_tests()
    
    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{status} {result.test_name}")
        if result.error_message:
            print(f"   -> {result.error_message}")
    
    print()
    print(f"Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("SUCCESS: All tests passed! WebSocket event pipeline is working!")
        return True
    else:
        print("FAILURE: WebSocket event pipeline has critical issues that must be fixed!")
        print()
        print("Required fixes:")
        if any("singleton" in str(r.error_message).lower() for r in results if not r.passed):
            print("  1. Replace singleton WebSocket manager with factory pattern")
        if any("async" in str(r.error_message).lower() or "coroutine" in str(r.error_message).lower() for r in results if not r.passed):
            print("  2. Fix create_user_emitter async/await handling")
        if any("llm_manager" in str(r.error_message).lower() for r in results if not r.passed):
            print("  3. Fix AgentRegistry initialization with proper dependencies")
        if any("isolation" in str(r.error_message).lower() for r in results if not r.passed):
            print("  4. Ensure proper user isolation in concurrent scenarios")
        
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)