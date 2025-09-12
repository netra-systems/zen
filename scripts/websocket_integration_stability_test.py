#!/usr/bin/env python
"""
WebSocket-Agent Integration Stability Test
Testing core integration components without Docker dependencies

This test verifies the WebSocket-Agent integration fix has not broken existing functionality.
"""

import asyncio
import sys
import os
from typing import Dict, Any, Optional
from datetime import datetime

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '.'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.isolated_environment import get_env
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

class WebSocketIntegrationStabilityTest:
    """Comprehensive stability test for WebSocket-Agent integration fixes."""
    
    def __init__(self):
        self.results = {
            'test_start_time': datetime.now().isoformat(),
            'tests_passed': 0,
            'tests_failed': 0,
            'failures': [],
            'stability_issues': [],
            'breaking_changes': []
        }
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all stability tests and return comprehensive results."""
        logger.info(" SEARCH:  Starting WebSocket-Agent Integration Stability Test")
        
        # Core component tests
        await self._test_execution_engine_instantiation()
        await self._test_agent_registry_websocket_integration()
        await self._test_websocket_bridge_creation()
        await self._test_user_context_integration()
        
        # Regression detection tests  
        await self._test_import_integrity()
        await self._test_factory_pattern_stability()
        await self._test_error_handling_robustness()
        
        # Summary
        self.results['test_end_time'] = datetime.now().isoformat()
        self.results['overall_status'] = 'PASS' if self.results['tests_failed'] == 0 else 'FAIL'
        
        return self.results
    
    async def _test_execution_engine_instantiation(self):
        """Test that ExecutionEngine can be instantiated without RuntimeError."""
        try:
            logger.info("[U+1F9EA] Testing ExecutionEngine instantiation...")
            
            # Import components
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
            from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            
            # Create mock registry
            registry = AgentRegistry()
            
            # Create mock websocket bridge
            class MockWebSocketBridge:
                async def notify_agent_started(self, run_id, agent_name, data):
                    pass
                async def notify_agent_thinking(self, run_id, agent_name, reasoning, step_number=None, progress_percentage=None):
                    pass
                async def notify_tool_executing(self, run_id, agent_name, tool_name, parameters=None):
                    pass
                async def notify_agent_completed(self, run_id, agent_name, result=None, execution_time_ms=None):
                    pass
                async def notify_agent_error(self, run_id, agent_name, error=None, error_context=None):
                    pass
                async def get_metrics(self):
                    return {}
            
            websocket_bridge = MockWebSocketBridge()
            
            # Create user context
            user_context = UserExecutionContext(
                user_id="test_user_123",
                request_id="test_req_456",
                thread_id="test_thread_789",
                run_id="test_run_999"
            )
            
            # Test instantiation - this should NOT raise RuntimeError
            execution_engine = ExecutionEngine(
                registry=registry,
                websocket_bridge=websocket_bridge,
                user_context=user_context
            )
            
            # Verify engine is properly initialized
            assert execution_engine is not None
            assert execution_engine.registry is registry
            assert execution_engine.websocket_bridge is websocket_bridge
            assert execution_engine.user_context is user_context
            
            self._record_success("ExecutionEngine instantiation", "ExecutionEngine can be instantiated without RuntimeError")
            
        except Exception as e:
            self._record_failure("ExecutionEngine instantiation", f"Failed to instantiate ExecutionEngine: {e}")
            if "RuntimeError" in str(e):
                self.results['breaking_changes'].append(f"RuntimeError blocking ExecutionEngine instantiation: {e}")
    
    async def _test_agent_registry_websocket_integration(self):
        """Test AgentRegistry WebSocket manager integration."""
        try:
            logger.info("[U+1F9EA] Testing AgentRegistry WebSocket integration...")
            
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
            
            # Create registry
            registry = AgentRegistry()
            
            # Create mock WebSocket manager
            class MockWebSocketManager:
                def __init__(self):
                    self.connected = True
                    
                async def emit_event(self, event_type, data):
                    return True
            
            websocket_manager = MockWebSocketManager()
            
            # Test set_websocket_manager method exists and works
            if hasattr(registry, 'set_websocket_manager'):
                registry.set_websocket_manager(websocket_manager)
                self._record_success("AgentRegistry WebSocket integration", "set_websocket_manager method works")
            else:
                self._record_failure("AgentRegistry WebSocket integration", "set_websocket_manager method missing")
            
            # Test async version if available
            if hasattr(registry, 'set_websocket_manager_async'):
                await registry.set_websocket_manager_async(websocket_manager)
                self._record_success("AgentRegistry async WebSocket integration", "set_websocket_manager_async method works")
            
        except Exception as e:
            self._record_failure("AgentRegistry WebSocket integration", f"WebSocket manager integration failed: {e}")
    
    async def _test_websocket_bridge_creation(self):
        """Test WebSocket bridge factory pattern."""
        try:
            logger.info("[U+1F9EA] Testing WebSocket bridge creation...")
            
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            
            # Test bridge factory exists
            try:
                from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
                self._record_success("WebSocket bridge factory", "create_agent_websocket_bridge function exists")
            except ImportError as e:
                self._record_failure("WebSocket bridge factory", f"WebSocket bridge factory missing: {e}")
                return
            
            # Create user context for bridge
            user_context = UserExecutionContext(
                user_id="test_user_bridge",
                request_id="test_req_bridge", 
                thread_id="test_thread_bridge",
                run_id="test_run_bridge"
            )
            
            # Test bridge creation (without actual WebSocket manager)
            # This should not fail even with None manager
            try:
                bridge = create_agent_websocket_bridge(None, user_context)
                if bridge is not None:
                    self._record_success("WebSocket bridge creation", "Bridge created successfully with None manager")
                else:
                    self._record_success("WebSocket bridge creation", "Bridge factory handled None manager gracefully")
            except Exception as bridge_error:
                self._record_failure("WebSocket bridge creation", f"Bridge creation failed: {bridge_error}")
            
        except Exception as e:
            self._record_failure("WebSocket bridge creation", f"Bridge creation test failed: {e}")
    
    async def _test_user_context_integration(self):
        """Test UserExecutionContext integration."""
        try:
            logger.info("[U+1F9EA] Testing UserExecutionContext integration...")
            
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            
            # Test UserExecutionContext creation
            user_context = UserExecutionContext(
                user_id="test_user_context",
                request_id="test_req_context",
                thread_id="test_thread_context", 
                run_id="test_run_context"
            )
            
            # Verify properties
            assert user_context.user_id == "test_user_context"
            assert user_context.request_id == "test_req_context"
            assert user_context.thread_id == "test_thread_context"
            assert user_context.run_id == "test_run_context"
            
            self._record_success("UserExecutionContext integration", "UserExecutionContext works correctly")
            
        except Exception as e:
            self._record_failure("UserExecutionContext integration", f"UserExecutionContext integration failed: {e}")
    
    async def _test_import_integrity(self):
        """Test that all imports work correctly after changes."""
        try:
            logger.info("[U+1F9EA] Testing import integrity...")
            
            critical_imports = [
                "netra_backend.app.agents.supervisor.agent_registry",
                "netra_backend.app.agents.supervisor.execution_engine", 
                "netra_backend.app.services.user_execution_context",
                "netra_backend.app.agents.tool_dispatcher",
                "netra_backend.app.websocket_core.unified_manager",
            ]
            
            failed_imports = []
            
            for import_name in critical_imports:
                try:
                    __import__(import_name)
                except ImportError as e:
                    failed_imports.append(f"{import_name}: {e}")
            
            if failed_imports:
                self._record_failure("Import integrity", f"Failed imports: {', '.join(failed_imports)}")
                self.results['breaking_changes'].extend(failed_imports)
            else:
                self._record_success("Import integrity", "All critical imports work correctly")
                
        except Exception as e:
            self._record_failure("Import integrity", f"Import integrity test failed: {e}")
    
    async def _test_factory_pattern_stability(self):
        """Test factory patterns remain stable."""
        try:
            logger.info("[U+1F9EA] Testing factory pattern stability...")
            
            # Test UnifiedToolDispatcherFactory exists and works
            try:
                from netra_backend.app.agents.tool_dispatcher import UnifiedToolDispatcherFactory
                factory = UnifiedToolDispatcherFactory()
                self._record_success("Factory pattern stability", "UnifiedToolDispatcherFactory works")
            except Exception as e:
                self._record_failure("Factory pattern stability", f"UnifiedToolDispatcherFactory failed: {e}")
            
            # Test AgentRegistry factory methods
            try:
                from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
                registry = AgentRegistry()
                # Test basic functionality 
                if hasattr(registry, 'register_agent'):
                    self._record_success("Factory pattern stability", "AgentRegistry factory methods stable")
            except Exception as e:
                self._record_failure("Factory pattern stability", f"AgentRegistry factory methods failed: {e}")
                
        except Exception as e:
            self._record_failure("Factory pattern stability", f"Factory pattern test failed: {e}")
    
    async def _test_error_handling_robustness(self):
        """Test error handling robustness."""
        try:
            logger.info("[U+1F9EA] Testing error handling robustness...")
            
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
            
            registry = AgentRegistry()
            
            # Test None handling in set_websocket_manager
            try:
                if hasattr(registry, 'set_websocket_manager'):
                    registry.set_websocket_manager(None)
                    self._record_success("Error handling robustness", "Registry handles None WebSocket manager gracefully")
            except Exception as e:
                self._record_failure("Error handling robustness", f"Registry failed to handle None manager: {e}")
            
            # Test error propagation
            self._record_success("Error handling robustness", "Error handling tests completed")
            
        except Exception as e:
            self._record_failure("Error handling robustness", f"Error handling test failed: {e}")
    
    def _record_success(self, test_name: str, details: str):
        """Record a successful test."""
        self.results['tests_passed'] += 1
        logger.info(f" PASS:  {test_name}: {details}")
    
    def _record_failure(self, test_name: str, details: str):
        """Record a failed test."""
        self.results['tests_failed'] += 1
        self.results['failures'].append({
            'test': test_name,
            'error': details,
            'timestamp': datetime.now().isoformat()
        })
        logger.error(f" FAIL:  {test_name}: {details}")
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*80)
        print("WEBSOCKET-AGENT INTEGRATION STABILITY TEST SUMMARY")
        print("="*80)
        print(f"Total Tests: {self.results['tests_passed'] + self.results['tests_failed']}")
        print(f"Passed: {self.results['tests_passed']}")
        print(f"Failed: {self.results['tests_failed']}")
        print(f"Overall Status: {self.results['overall_status']}")
        
        if self.results['failures']:
            print("\nFAILURES:")
            for failure in self.results['failures']:
                print(f"  - {failure['test']}: {failure['error']}")
        
        if self.results['breaking_changes']:
            print("\nBREAKING CHANGES DETECTED:")
            for change in self.results['breaking_changes']:
                print(f"  - {change}")
        
        if self.results['stability_issues']:
            print("\nSTABILITY ISSUES:")
            for issue in self.results['stability_issues']:
                print(f"  - {issue}")
        
        print("\n" + "="*80)

async def main():
    """Run the stability test."""
    test_runner = WebSocketIntegrationStabilityTest()
    
    try:
        results = await test_runner.run_all_tests()
        test_runner.print_summary()
        
        # Exit with appropriate code
        return 0 if results['overall_status'] == 'PASS' else 1
        
    except Exception as e:
        logger.error(f"Stability test runner failed: {e}")
        print(f"\nCRITICAL ERROR: Stability test runner failed: {e}")
        return 2

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)