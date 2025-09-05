#!/usr/bin/env python3
"""
Comprehensive WebSocket Event Pipeline Test Suite
CRITICAL: This tests the complete WebSocket event pipeline from multiple angles
          to ensure all 5 critical events are transmitted correctly.
"""

import asyncio
import sys
import os
import time
import traceback
from typing import Any, Dict, List, Optional, Set
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

# Add paths for imports
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('netra_backend'))

# Color output helpers
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_test_header(test_name: str):
    """Print formatted test header."""
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'='*80}{Colors.RESET}")
    print(f"{Colors.BLUE}{Colors.BOLD}TEST: {test_name}{Colors.RESET}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'='*80}{Colors.RESET}")

def print_result(passed: bool, message: str):
    """Print colored test result."""
    if passed:
        print(f"{Colors.GREEN}PASS:{Colors.RESET} {message}")
    else:
        print(f"{Colors.RED}FAIL:{Colors.RESET} {message}")

def print_warning(message: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}WARNING:{Colors.RESET} {message}")

def print_error(message: str):
    """Print error message."""
    print(f"{Colors.RED}ERROR:{Colors.RESET} {message}")

def print_info(message: str):
    """Print info message."""
    print(f"{Colors.BLUE}INFO:{Colors.RESET} {message}")

# Test 1: Import Chain Analysis
def test_import_chain():
    """Test if dependencies.py uses deprecated imports."""
    print_test_header("Import Chain Analysis")
    
    try:
        # Check what's imported in dependencies.py
        with open('netra_backend/app/dependencies.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check for deprecated import
        uses_deprecated = 'from netra_backend.app.websocket_core import get_websocket_manager' in content
        uses_factory = 'from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager' in content
        
        print_info(f"Uses deprecated get_websocket_manager: {uses_deprecated}")
        print_info(f"Uses factory create_websocket_manager: {uses_factory}")
        
        # Check actual usage in get_supervisor
        if 'websocket_manager = get_websocket_manager()' in content:
            print_error("CONFIRMED: Using deprecated singleton pattern in get_supervisor()")
            return False
        
        if 'websocket_manager = create_websocket_manager(' in content:
            print_result(True, "Using factory pattern in get_supervisor()")
            return True
            
        print_warning("Could not determine WebSocket manager usage pattern")
        return False
        
    except Exception as e:
        print_error(f"Import chain test failed: {e}")
        return False

# Test 2: Factory Implementation
async def test_factory_implementation():
    """Test if AgentWebSocketBridge factory methods work correctly."""
    print_test_header("Factory Implementation Test")
    
    try:
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
        
        # Create test context
        user_context = UserExecutionContext(
            user_id="test_user",
            request_id="test_request",
            thread_id="test_thread"
        )
        
        # Create bridge
        bridge = AgentWebSocketBridge()
        print_result(True, "AgentWebSocketBridge instantiated")
        
        # Test create_user_emitter
        try:
            # Mock the create_websocket_manager to avoid actual WebSocket connection
            with patch('netra_backend.app.services.agent_websocket_bridge.create_websocket_manager') as mock_create:
                mock_manager = MagicMock()
                mock_create.return_value = mock_manager
                
                emitter = await bridge.create_user_emitter(user_context)
                print_info(f"Emitter type: {type(emitter)}")
                
                # Check if it's a coroutine (the bug)
                if asyncio.iscoroutine(emitter):
                    print_error("BUG CONFIRMED: create_user_emitter returns coroutine instead of emitter!")
                    return False
                
                # Check critical methods
                critical_methods = [
                    'notify_agent_started',
                    'notify_agent_thinking', 
                    'notify_tool_executing',
                    'notify_tool_completed',
                    'notify_agent_completed'
                ]
                
                missing_methods = []
                for method in critical_methods:
                    if not hasattr(emitter, method):
                        missing_methods.append(method)
                
                if missing_methods:
                    print_error(f"Missing critical methods: {missing_methods}")
                    return False
                
                print_result(True, "All critical methods present on emitter")
                return True
                
        except Exception as e:
            print_error(f"Failed to create user emitter: {e}")
            traceback.print_exc()
            return False
            
    except ImportError as e:
        print_error(f"Import error: {e}")
        return False
    except Exception as e:
        print_error(f"Factory test failed: {e}")
        traceback.print_exc()
        return False

# Test 3: Agent Registry Integration
async def test_agent_registry_integration():
    """Test if AgentRegistry properly integrates with WebSocket."""
    print_test_header("Agent Registry Integration Test")
    
    try:
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.websocket_core import get_websocket_manager
        
        # Try to create AgentRegistry
        try:
            # First check what parameters it needs
            import inspect
            sig = inspect.signature(AgentRegistry.__init__)
            print_info(f"AgentRegistry.__init__ signature: {sig}")
            
            # Try creating with minimal parameters
            registry = AgentRegistry()
            print_error("AgentRegistry created without required parameters - unexpected!")
            
        except TypeError as e:
            error_msg = str(e)
            print_info(f"AgentRegistry initialization error: {error_msg}")
            
            if 'llm_manager' in error_msg:
                print_error("CONFIRMED: AgentRegistry missing llm_manager parameter")
                return False
            else:
                print_warning(f"Different initialization error: {error_msg}")
                return False
                
        # Test set_websocket_manager if registry exists
        if 'registry' in locals():
            if hasattr(registry, 'set_websocket_manager'):
                print_result(True, "Registry has set_websocket_manager method")
            else:
                print_error("Registry missing set_websocket_manager method")
                return False
                
        return True
        
    except ImportError as e:
        print_error(f"Import error: {e}")
        return False
    except Exception as e:
        print_error(f"Registry integration test failed: {e}")
        traceback.print_exc()
        return False

# Test 4: Complete Event Flow
async def test_complete_event_flow():
    """Test the complete event flow from agent to WebSocket."""
    print_test_header("Complete Event Flow Test")
    
    captured_events = []
    
    try:
        from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        
        # Create test context
        user_context = UserExecutionContext(
            user_id="test_user",
            request_id="test_request", 
            thread_id="test_thread"
        )
        
        # Mock WebSocket manager to capture events
        class MockWebSocketManager:
            async def send_to_user(self, user_id: str, message: Dict[str, Any]):
                captured_events.append(message)
                print_info(f"Captured event: {message.get('type', 'unknown')}")
        
        # Create bridge with mocked manager
        bridge = AgentWebSocketBridge()
        
        with patch('netra_backend.app.services.agent_websocket_bridge.create_websocket_manager') as mock_create:
            mock_manager = MockWebSocketManager()
            mock_create.return_value = mock_manager
            
            # Try to emit all critical events
            try:
                emitter = await bridge.create_user_emitter(user_context)
                
                # If emitter is a coroutine, it won't work
                if asyncio.iscoroutine(emitter):
                    print_error("Cannot test event flow - emitter is a coroutine!")
                    return False
                
                # Try to emit critical events
                if hasattr(emitter, 'notify_agent_started'):
                    await emitter.notify_agent_started("TestAgent", {"test": "data"})
                if hasattr(emitter, 'notify_agent_thinking'):
                    await emitter.notify_agent_thinking("Thinking about the problem...")
                if hasattr(emitter, 'notify_tool_executing'):
                    await emitter.notify_tool_executing("TestTool", {"param": "value"})
                if hasattr(emitter, 'notify_tool_completed'):
                    await emitter.notify_tool_completed("TestTool", {"result": "success"})
                if hasattr(emitter, 'notify_agent_completed'):
                    await emitter.notify_agent_completed("TestAgent", {"final": "result"})
                    
            except Exception as e:
                print_error(f"Failed to emit events: {e}")
                traceback.print_exc()
        
        # Check captured events
        event_types = [evt.get('type') for evt in captured_events]
        print_info(f"Captured event types: {event_types}")
        
        required_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        missing_events = [evt for evt in required_events if evt not in event_types]
        
        if missing_events:
            print_error(f"Missing critical events: {missing_events}")
            print_error(f"Only captured {len(captured_events)}/{len(required_events)} events")
            return False
        
        print_result(True, f"All {len(required_events)} critical events captured!")
        return True
        
    except Exception as e:
        print_error(f"Event flow test failed: {e}")
        traceback.print_exc()
        return False

# Test 5: Deprecation Warnings
def test_deprecation_warnings():
    """Test if deprecated code shows proper warnings."""
    print_test_header("Deprecation Warning Test")
    
    warnings_captured = []
    
    try:
        import warnings
        
        # Capture warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            # Try importing deprecated functions
            from netra_backend.app.websocket_core import get_websocket_manager
            
            # Call deprecated function
            try:
                manager = get_websocket_manager()
            except Exception as e:
                print_info(f"get_websocket_manager() raised exception: {e}")
            
            # Check for warnings
            for warning in w:
                warning_msg = str(warning.message)
                warnings_captured.append(warning_msg)
                if 'deprecated' in warning_msg.lower():
                    print_warning(f"Deprecation warning: {warning_msg}")
        
        if warnings_captured:
            print_result(True, f"Captured {len(warnings_captured)} warnings")
            return True
        else:
            print_error("No deprecation warnings captured")
            return False
            
    except Exception as e:
        print_error(f"Deprecation test failed: {e}")
        return False

# Test 6: Singleton vs Factory Pattern
async def test_singleton_vs_factory():
    """Test if system uses singleton or factory pattern."""
    print_test_header("Singleton vs Factory Pattern Test")
    
    try:
        from netra_backend.app.websocket_core import get_websocket_manager
        from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
        from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
        
        # Test singleton behavior
        manager1 = get_websocket_manager()
        manager2 = get_websocket_manager()
        
        if manager1 is manager2:
            print_warning("get_websocket_manager returns singleton (same instance)")
        else:
            print_info("get_websocket_manager returns different instances")
        
        # Test factory behavior
        context1 = UserExecutionContext(user_id="user1", request_id="req1", thread_id="thread1")
        context2 = UserExecutionContext(user_id="user2", request_id="req2", thread_id="thread2")
        
        factory_manager1 = create_websocket_manager(context1)
        factory_manager2 = create_websocket_manager(context2)
        
        if factory_manager1 is factory_manager2:
            print_error("Factory returns same instance for different users - SECURITY ISSUE!")
            return False
        else:
            print_result(True, "Factory creates isolated instances per user")
            return True
            
    except ImportError as e:
        print_error(f"Import error: {e}")
        return False
    except Exception as e:
        print_error(f"Pattern test failed: {e}")
        traceback.print_exc()
        return False

# Main test runner
async def run_all_tests():
    """Run all comprehensive tests."""
    print(f"\n{Colors.BOLD}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}WEBSOCKET EVENT PIPELINE COMPREHENSIVE TEST SUITE{Colors.RESET}")
    print(f"{Colors.BOLD}Testing all aspects of the WebSocket event pipeline{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*80}{Colors.RESET}")
    
    results = {}
    
    # Run synchronous tests
    results['Import Chain'] = test_import_chain()
    results['Deprecation Warnings'] = test_deprecation_warnings()
    
    # Run async tests
    results['Factory Implementation'] = await test_factory_implementation()
    results['Registry Integration'] = await test_agent_registry_integration()
    results['Complete Event Flow'] = await test_complete_event_flow()
    results['Singleton vs Factory'] = await test_singleton_vs_factory()
    
    # Print summary
    print(f"\n{Colors.BOLD}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}TEST SUMMARY{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*80}{Colors.RESET}")
    
    total_tests = len(results)
    passed_tests = sum(1 for passed in results.values() if passed)
    failed_tests = total_tests - passed_tests
    
    for test_name, passed in results.items():
        status = f"{Colors.GREEN}PASS{Colors.RESET}" if passed else f"{Colors.RED}FAIL{Colors.RESET}"
        print(f"  {test_name}: {status}")
    
    print(f"\n{Colors.BOLD}Results: {passed_tests}/{total_tests} tests passed{Colors.RESET}")
    
    if failed_tests > 0:
        print(f"{Colors.RED}{Colors.BOLD}FAILED: {failed_tests} tests FAILED - WebSocket pipeline is BROKEN!{Colors.RESET}")
        print(f"{Colors.RED}CRITICAL: Chat functionality will not work in staging/production!{Colors.RESET}")
        return False
    else:
        print(f"{Colors.GREEN}{Colors.BOLD}SUCCESS: All tests PASSED - WebSocket pipeline is working!{Colors.RESET}")
        return True

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)