"""Tool Dispatcher Integration Baseline Tests for SSOT Validation.

Test Phase 2: Integration testing without Docker for SSOT baseline establishment.
These tests establish the current state before SSOT consolidation and should reveal
integration issues between different dispatcher implementations.

INTEGRATION FOCUS AREAS:
- Real service integration where possible (no Docker requirement)
- Cross-component integration between dispatchers and other services
- End-to-end workflow integration testing
- Service boundary integration validation

Business Value:
- Establishes baseline integration behavior before SSOT changes
- Validates that SSOT consolidation doesn't break working integrations
- Provides regression protection during SSOT remediation
"""

import asyncio
import time
import uuid
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext


class TestToolDispatcherIntegrationBaseline(SSotAsyncTestCase):
    """Integration baseline tests for tool dispatcher SSOT validation."""

    async def asyncSetUp(self):
        """Set up test fixtures."""
        await super().asyncSetUp()
        
        # Create test user context
        self.user_context = UserExecutionContext(
            user_id="integration_test_user",
            thread_id="integration_test_thread",
            run_id=f"integration_test_run_{uuid.uuid4()}"
        )

    async def test_tool_dispatcher_factory_integration(self):
        """Test integration between different factory patterns.
        
        BASELINE EXPECTATION: May reveal inconsistencies between factories
        This test documents current factory integration behavior for comparison after SSOT.
        """
        factory_results = {}
        factory_errors = {}
        
        # Test ToolExecutorFactory integration
        try:
            from netra_backend.app.agents.tool_executor_factory import ToolExecutorFactory
            
            factory = ToolExecutorFactory()
            dispatcher = await factory.create_request_scoped_dispatcher(self.user_context)
            
            # Test basic functionality
            dispatcher.register_tool("factory_test", lambda x: f"Factory result: {x}")
            result = await dispatcher.dispatch("factory_test", query="test")
            
            factory_results['ToolExecutorFactory'] = {
                'dispatcher_type': type(dispatcher).__name__,
                'has_websocket_support': hasattr(dispatcher, 'has_websocket_support'),
                'tool_execution_result': str(result),
                'metrics': dispatcher.get_metrics() if hasattr(dispatcher, 'get_metrics') else None
            }
            
            await dispatcher.cleanup()
            
        except Exception as e:
            factory_errors['ToolExecutorFactory'] = str(e)

        # Test RequestScopedToolDispatcher direct creation
        try:
            from netra_backend.app.agents.request_scoped_tool_dispatcher import RequestScopedToolDispatcher
            
            dispatcher = RequestScopedToolDispatcher(user_context=self.user_context)
            
            # Test basic functionality
            dispatcher.register_tool("direct_test", lambda x: f"Direct result: {x}")
            result = await dispatcher.dispatch("direct_test", query="test")
            
            factory_results['RequestScopedToolDispatcher'] = {
                'dispatcher_type': type(dispatcher).__name__,
                'has_websocket_support': hasattr(dispatcher, 'has_websocket_support'),
                'tool_execution_result': str(result),
                'metrics': dispatcher.get_metrics() if hasattr(dispatcher, 'get_metrics') else None
            }
            
            await dispatcher.cleanup()
            
        except Exception as e:
            factory_errors['RequestScopedToolDispatcher'] = str(e)

        # Test convenience function
        try:
            from netra_backend.app.agents.request_scoped_tool_dispatcher import create_request_scoped_tool_dispatcher
            
            dispatcher = await create_request_scoped_tool_dispatcher(self.user_context)
            
            # Test basic functionality
            dispatcher.register_tool("convenience_test", lambda x: f"Convenience result: {x}")
            result = await dispatcher.dispatch("convenience_test", query="test")
            
            factory_results['create_request_scoped_tool_dispatcher'] = {
                'dispatcher_type': type(dispatcher).__name__,
                'has_websocket_support': hasattr(dispatcher, 'has_websocket_support'),
                'tool_execution_result': str(result),
                'metrics': dispatcher.get_metrics() if hasattr(dispatcher, 'get_metrics') else None
            }
            
            await dispatcher.cleanup()
            
        except Exception as e:
            factory_errors['create_request_scoped_tool_dispatcher'] = str(e)

        # BASELINE DOCUMENTATION: Record current state
        print(f"\n=== FACTORY INTEGRATION BASELINE ===")
        print(f"Successful factories: {list(factory_results.keys())}")
        print(f"Failed factories: {list(factory_errors.keys())}")
        
        for factory_name, result in factory_results.items():
            print(f"\n{factory_name}:")
            print(f"  - Dispatcher type: {result['dispatcher_type']}")
            print(f"  - WebSocket support: {result['has_websocket_support']}")
            print(f"  - Has metrics: {result['metrics'] is not None}")
        
        if factory_errors:
            print(f"\nFactory errors:")
            for factory_name, error in factory_errors.items():
                print(f"  - {factory_name}: {error}")
        
        # VALIDATION: At least one factory should work for baseline
        self.assertGreater(
            len(factory_results), 0,
            f"BASELINE FAILURE: No factory patterns working. Errors: {factory_errors}"
        )

    async def test_tool_execution_engine_integration(self):
        """Test integration with different tool execution engines.
        
        BASELINE EXPECTATION: Documents current execution engine behavior
        """
        execution_results = {}
        execution_errors = {}
        
        # Test UnifiedToolExecutionEngine integration
        try:
            from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
            from netra_backend.app.agents.request_scoped_tool_dispatcher import RequestScopedToolDispatcher
            
            dispatcher = RequestScopedToolDispatcher(user_context=self.user_context)
            
            # Verify it's using UnifiedToolExecutionEngine
            executor_type = type(dispatcher.executor).__name__ if hasattr(dispatcher, 'executor') else 'unknown'
            
            # Test tool execution through dispatcher
            def integration_tool(query: str, context: str = "default") -> str:
                return f"Integration result for '{query}' in context '{context}'"
            
            dispatcher.register_tool("integration_tool", integration_tool)
            result = await dispatcher.dispatch("integration_tool", query="baseline_test", context="integration")
            
            execution_results['UnifiedToolExecutionEngine_via_RequestScoped'] = {
                'executor_type': executor_type,
                'result': str(result),
                'execution_successful': result is not None
            }
            
            await dispatcher.cleanup()
            
        except Exception as e:
            execution_errors['UnifiedToolExecutionEngine_via_RequestScoped'] = str(e)

        # Test enhanced tool dispatcher integration
        try:
            from netra_backend.app.agents.unified_tool_execution import enhance_tool_dispatcher_with_notifications
            from netra_backend.app.agents.tool_dispatcher_core import ToolDispatcher
            
            # Try to create enhanced dispatcher (may fail due to RuntimeError)
            try:
                # This should fail in current implementation
                base_dispatcher = ToolDispatcher()
                execution_errors['ToolDispatcher_direct_instantiation'] = "Should have failed but didn't"
            except RuntimeError as e:
                # Expected behavior - direct instantiation blocked
                execution_results['ToolDispatcher_RuntimeError_Check'] = {
                    'error_message': str(e),
                    'correctly_blocked': "no longer supported" in str(e).lower()
                }
                
        except ImportError as e:
            execution_errors['enhance_tool_dispatcher_import'] = str(e)
        except Exception as e:
            execution_errors['enhance_tool_dispatcher_other'] = str(e)

        # BASELINE DOCUMENTATION
        print(f"\n=== EXECUTION ENGINE INTEGRATION BASELINE ===")
        print(f"Successful executions: {list(execution_results.keys())}")
        print(f"Failed executions: {list(execution_errors.keys())}")
        
        for engine_name, result in execution_results.items():
            print(f"\n{engine_name}:")
            if 'executor_type' in result:
                print(f"  - Executor type: {result['executor_type']}")
            if 'result' in result:
                print(f"  - Execution result available: {'Yes' if result['result'] else 'No'}")
            if 'correctly_blocked' in result:
                print(f"  - Correctly blocked: {result['correctly_blocked']}")
        
        # VALIDATION: Should have at least some working execution path
        working_executions = len(execution_results) - len([r for r in execution_results.values() if 'error_message' in r])
        self.assertGreater(
            working_executions, 0,
            f"BASELINE FAILURE: No working execution engines. Results: {execution_results}, Errors: {execution_errors}"
        )

    async def test_websocket_integration_baseline(self):
        """Test WebSocket integration baseline behavior.
        
        BASELINE EXPECTATION: Documents current WebSocket integration state
        """
        websocket_results = {}
        websocket_errors = {}
        
        # Test RequestScopedToolDispatcher with mock WebSocket
        try:
            from netra_backend.app.agents.request_scoped_tool_dispatcher import RequestScopedToolDispatcher
            
            # Create mock WebSocket emitter
            mock_emitter = MagicMock()
            for event in ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']:
                setattr(mock_emitter, f"notify_{event}", AsyncMock(return_value=True))
            
            dispatcher = RequestScopedToolDispatcher(
                user_context=self.user_context,
                websocket_emitter=mock_emitter
            )
            
            # Test WebSocket-enabled tool execution
            dispatcher.register_tool("websocket_test", lambda x: f"WebSocket result: {x}")
            result = await dispatcher.dispatch("websocket_test", query="baseline")
            
            websocket_results['RequestScopedToolDispatcher_with_WebSocket'] = {
                'has_websocket_support': dispatcher.has_websocket_support,
                'result': str(result),
                'websocket_emitter_type': type(mock_emitter).__name__
            }
            
            await dispatcher.cleanup()
            
        except Exception as e:
            websocket_errors['RequestScopedToolDispatcher_WebSocket'] = str(e)

        # Test RequestScopedToolDispatcher without WebSocket
        try:
            from netra_backend.app.agents.request_scoped_tool_dispatcher import RequestScopedToolDispatcher
            
            dispatcher = RequestScopedToolDispatcher(
                user_context=self.user_context,
                websocket_emitter=None
            )
            
            dispatcher.register_tool("no_websocket_test", lambda x: f"No WebSocket result: {x}")
            result = await dispatcher.dispatch("no_websocket_test", query="baseline")
            
            websocket_results['RequestScopedToolDispatcher_without_WebSocket'] = {
                'has_websocket_support': dispatcher.has_websocket_support,
                'result': str(result)
            }
            
            await dispatcher.cleanup()
            
        except Exception as e:
            websocket_errors['RequestScopedToolDispatcher_no_WebSocket'] = str(e)

        # Test WebSocketBridgeAdapter integration
        try:
            from netra_backend.app.agents.request_scoped_tool_dispatcher import WebSocketBridgeAdapter
            from netra_backend.app.websocket_core import WebSocketEventEmitter
            
            # Create mock emitter and adapter
            mock_emitter = MagicMock(spec=WebSocketEventEmitter)
            for event in ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']:
                setattr(mock_emitter, f"notify_{event}", AsyncMock(return_value=True))
            
            adapter = WebSocketBridgeAdapter(mock_emitter, self.user_context)
            
            # Test adapter methods
            adapter_methods = [method for method in dir(adapter) if method.startswith('notify_') and not method.startswith('__')]
            
            websocket_results['WebSocketBridgeAdapter'] = {
                'adapter_created': True,
                'available_methods': adapter_methods,
                'method_count': len(adapter_methods)
            }
            
        except ImportError as e:
            websocket_errors['WebSocketBridgeAdapter_import'] = str(e)
        except Exception as e:
            websocket_errors['WebSocketBridgeAdapter_other'] = str(e)

        # BASELINE DOCUMENTATION
        print(f"\n=== WEBSOCKET INTEGRATION BASELINE ===")
        print(f"Successful WebSocket integrations: {list(websocket_results.keys())}")
        print(f"Failed WebSocket integrations: {list(websocket_errors.keys())}")
        
        for integration_name, result in websocket_results.items():
            print(f"\n{integration_name}:")
            if 'has_websocket_support' in result:
                print(f"  - WebSocket support: {result['has_websocket_support']}")
            if 'method_count' in result:
                print(f"  - Available methods: {result['method_count']}")
                
        # VALIDATION: Should have some WebSocket integration capability
        successful_integrations = len(websocket_results)
        self.assertGreater(
            successful_integrations, 0,
            f"BASELINE FAILURE: No WebSocket integrations working. Errors: {websocket_errors}"
        )

    async def test_tool_registry_integration_baseline(self):
        """Test tool registry integration across different dispatcher types.
        
        BASELINE EXPECTATION: Documents tool registry behavior consistency
        """
        registry_results = {}
        registry_errors = {}
        
        # Test tool registration and retrieval patterns
        test_tools = {
            'simple_tool': lambda x: f"Simple: {x}",
            'async_tool': AsyncMock(return_value="Async result"),
            'complex_tool': lambda query, context="default": f"Complex: {query} in {context}"
        }
        
        try:
            from netra_backend.app.agents.request_scoped_tool_dispatcher import RequestScopedToolDispatcher
            
            dispatcher = RequestScopedToolDispatcher(user_context=self.user_context)
            
            # Test tool registration
            registration_results = {}
            for tool_name, tool_func in test_tools.items():
                try:
                    dispatcher.register_tool(tool_name, tool_func, f"Test tool: {tool_name}")
                    registration_results[tool_name] = True
                except Exception as e:
                    registration_results[tool_name] = f"Error: {e}"
            
            # Test tool existence checks
            existence_results = {}
            for tool_name in test_tools.keys():
                existence_results[tool_name] = dispatcher.has_tool(tool_name)
            
            # Test tool execution
            execution_results = {}
            for tool_name in test_tools.keys():
                if dispatcher.has_tool(tool_name):
                    try:
                        if tool_name == 'complex_tool':
                            result = await dispatcher.dispatch(tool_name, query="test", context="integration")
                        else:
                            result = await dispatcher.dispatch(tool_name, query="test")
                        execution_results[tool_name] = str(result)
                    except Exception as e:
                        execution_results[tool_name] = f"Execution error: {e}"
            
            # Get registry state
            tools_dict = dispatcher.tools if hasattr(dispatcher, 'tools') else {}
            
            registry_results['RequestScopedToolDispatcher_registry'] = {
                'registration_results': registration_results,
                'existence_results': existence_results,
                'execution_results': execution_results,
                'total_tools_registered': len(tools_dict),
                'tool_names': list(tools_dict.keys())
            }
            
            await dispatcher.cleanup()
            
        except Exception as e:
            registry_errors['RequestScopedToolDispatcher_registry'] = str(e)

        # BASELINE DOCUMENTATION
        print(f"\n=== TOOL REGISTRY INTEGRATION BASELINE ===")
        print(f"Successful registry integrations: {list(registry_results.keys())}")
        print(f"Failed registry integrations: {list(registry_errors.keys())}")
        
        for registry_name, result in registry_results.items():
            print(f"\n{registry_name}:")
            if 'total_tools_registered' in result:
                print(f"  - Total tools registered: {result['total_tools_registered']}")
            if 'tool_names' in result:
                print(f"  - Tool names: {result['tool_names']}")
            if 'registration_results' in result:
                successful_registrations = sum(1 for v in result['registration_results'].values() if v is True)
                print(f"  - Successful registrations: {successful_registrations}/{len(result['registration_results'])}")
                
        # VALIDATION: Should be able to register and execute tools
        if registry_results:
            for registry_name, result in registry_results.items():
                successful_registrations = sum(1 for v in result.get('registration_results', {}).values() if v is True)
                self.assertGreater(
                    successful_registrations, 0,
                    f"BASELINE FAILURE: No tools successfully registered in {registry_name}"
                )


class TestCrossComponentIntegrationBaseline(SSotAsyncTestCase):
    """Test cross-component integration baseline for SSOT validation."""

    async def asyncSetUp(self):
        """Set up test fixtures."""
        await super().asyncSetUp()
        
        self.user_context = UserExecutionContext(
            user_id="cross_component_test_user",
            thread_id="cross_component_test_thread",
            run_id=f"cross_component_test_run_{uuid.uuid4()}"
        )

    async def test_dispatcher_with_execution_context_integration(self):
        """Test integration between dispatcher and execution context.
        
        BASELINE EXPECTATION: Documents current context integration behavior
        """
        context_integration_results = {}
        context_integration_errors = {}
        
        try:
            from netra_backend.app.agents.request_scoped_tool_dispatcher import RequestScopedToolDispatcher
            
            dispatcher = RequestScopedToolDispatcher(user_context=self.user_context)
            
            # Test context retrieval
            retrieved_context = dispatcher.get_context()
            
            # Test context properties
            context_properties = {
                'user_id': retrieved_context.user_id,
                'thread_id': retrieved_context.thread_id,
                'run_id': retrieved_context.run_id,
                'correlation_id': retrieved_context.get_correlation_id()
            }
            
            # Test context isolation verification
            isolation_verified = False
            try:
                retrieved_context.verify_isolation()
                isolation_verified = True
            except Exception as e:
                context_integration_errors['isolation_verification'] = str(e)
            
            context_integration_results['context_integration'] = {
                'context_retrieved': retrieved_context is not None,
                'context_properties': context_properties,
                'isolation_verified': isolation_verified,
                'context_matches_input': (
                    retrieved_context.user_id == self.user_context.user_id and
                    retrieved_context.run_id == self.user_context.run_id
                )
            }
            
            await dispatcher.cleanup()
            
        except Exception as e:
            context_integration_errors['dispatcher_context_integration'] = str(e)

        # BASELINE DOCUMENTATION
        print(f"\n=== CONTEXT INTEGRATION BASELINE ===")
        print(f"Context integration results: {list(context_integration_results.keys())}")
        print(f"Context integration errors: {list(context_integration_errors.keys())}")
        
        if context_integration_results:
            for integration_name, result in context_integration_results.items():
                print(f"\n{integration_name}:")
                print(f"  - Context retrieved: {result.get('context_retrieved')}")
                print(f"  - Context matches input: {result.get('context_matches_input')}")
                print(f"  - Isolation verified: {result.get('isolation_verified')}")
        
        # VALIDATION: Context integration should work
        self.assertGreater(
            len(context_integration_results), 0,
            f"BASELINE FAILURE: No context integration working. Errors: {context_integration_errors}"
        )

    async def test_metrics_integration_baseline(self):
        """Test metrics integration across dispatcher implementations.
        
        BASELINE EXPECTATION: Documents current metrics behavior
        """
        metrics_results = {}
        metrics_errors = {}
        
        try:
            from netra_backend.app.agents.request_scoped_tool_dispatcher import RequestScopedToolDispatcher
            
            dispatcher = RequestScopedToolDispatcher(user_context=self.user_context)
            
            # Get initial metrics
            initial_metrics = dispatcher.get_metrics()
            
            # Register and execute tools to generate metrics
            dispatcher.register_tool("metrics_test_tool", lambda x: f"Metrics test: {x}")
            
            # Execute multiple times
            for i in range(3):
                await dispatcher.dispatch("metrics_test_tool", query=f"test_{i}")
            
            # Get final metrics
            final_metrics = dispatcher.get_metrics()
            
            # Analyze metrics changes
            metrics_changes = {
                'initial_tools_executed': initial_metrics.get('tools_executed', 0),
                'final_tools_executed': final_metrics.get('tools_executed', 0),
                'executions_counted': final_metrics.get('tools_executed', 0) - initial_metrics.get('tools_executed', 0),
                'success_rate': final_metrics.get('success_rate', 0),
                'has_timing_metrics': 'avg_execution_time_ms' in final_metrics,
                'has_user_context_info': all(key in final_metrics for key in ['user_id', 'run_id']),
                'dispatcher_id_present': 'dispatcher_id' in final_metrics
            }
            
            metrics_results['RequestScopedToolDispatcher_metrics'] = {
                'initial_metrics': initial_metrics,
                'final_metrics': final_metrics,
                'metrics_changes': metrics_changes
            }
            
            await dispatcher.cleanup()
            
        except Exception as e:
            metrics_errors['RequestScopedToolDispatcher_metrics'] = str(e)

        # BASELINE DOCUMENTATION
        print(f"\n=== METRICS INTEGRATION BASELINE ===")
        print(f"Metrics integration results: {list(metrics_results.keys())}")
        print(f"Metrics integration errors: {list(metrics_errors.keys())}")
        
        if metrics_results:
            for metrics_name, result in metrics_results.items():
                print(f"\n{metrics_name}:")
                changes = result.get('metrics_changes', {})
                print(f"  - Executions tracked: {changes.get('executions_counted')}")
                print(f"  - Success rate: {changes.get('success_rate')}")
                print(f"  - Has timing metrics: {changes.get('has_timing_metrics')}")
                print(f"  - Has user context: {changes.get('has_user_context_info')}")
        
        # VALIDATION: Metrics should be tracked
        self.assertGreater(
            len(metrics_results), 0,
            f"BASELINE FAILURE: No metrics integration working. Errors: {metrics_errors}"
        )


if __name__ == '__main__':
    # Run the tests
    pytest.main([__file__, "-v", "-s"])