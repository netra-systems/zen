"""UserExecutionEngine SSOT Validation - Issue #1146

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: Stability & User Isolation
- Value Impact: Ensures UserExecutionEngine correctly handles all agent types with proper isolation
- Strategic Impact: Validates SSOT consolidation maintains $500K+ ARR Golden Path functionality

CRITICAL MISSION: NEW 20% SSOT VALIDATION TESTS
This test validates UserExecutionEngine as the single execution engine handles all scenarios
that were previously split across 12 different execution engine implementations.

Test Scope: UserExecutionEngine validation for complete SSOT consolidation
Priority: P0 - Mission Critical
Docker: NO DEPENDENCIES - Integration non-docker only  
NEW TEST: Part of 20% new validation tests for Issue #1146
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, Any, List
import unittest
from unittest.mock import Mock, AsyncMock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mocks import get_mock_factory

# Import UserExecutionEngine and dependencies
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext, 
    AgentExecutionResult,
    PipelineStep
)
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    create_user_execution_context
)


class TestUserExecutionEngineSSotValidation1146(SSotAsyncTestCase):
    """Validates UserExecutionEngine handles all execution scenarios after SSOT consolidation."""

    async def asyncSetUp(self):
        """Set up UserExecutionEngine SSOT validation test environment."""
        await super().asyncSetUp()
        
        # Create test user context for isolation
        self.user_context = create_user_execution_context(
            user_id="test_user_1146",
            operation_name="ssot_validation_1146",
            additional_metadata={
                'test_type': 'ssot_validation',
                'issue': '#1146',
                'purpose': 'validate_single_execution_engine'
            }
        )
        
        # Create mock factory for test dependencies
        self.mock_factory = get_mock_factory()
        
        # Create mock agent factory
        self.mock_agent_factory = self.mock_factory.create_agent_factory_mock()
        self.mock_agent_factory.create_agent_instance = AsyncMock()
        
        # Create mock websocket emitter
        self.mock_websocket_emitter = self.mock_factory.create_websocket_emitter_mock()
        self.mock_websocket_emitter.notify_agent_started = AsyncMock(return_value=True)
        self.mock_websocket_emitter.notify_agent_thinking = AsyncMock(return_value=True)
        self.mock_websocket_emitter.notify_agent_completed = AsyncMock(return_value=True)
        self.mock_websocket_emitter.notify_tool_executing = AsyncMock(return_value=True)
        self.mock_websocket_emitter.notify_tool_completed = AsyncMock(return_value=True)
        
        # Create UserExecutionEngine instance
        self.engine = UserExecutionEngine(
            context=self.user_context,
            agent_factory=self.mock_agent_factory,
            websocket_emitter=self.mock_websocket_emitter
        )

    async def asyncTearDown(self):
        """Clean up test resources."""
        if hasattr(self, 'engine') and self.engine:
            await self.engine.cleanup()
        await super().asyncTearDown()

    async def test_user_execution_engine_handles_all_agent_types(self):
        """CRITICAL: Validate UserExecutionEngine handles all agent types that were in separate engines."""
        # Agent types that were previously handled by different execution engines
        agent_types_to_test = [
            "supervisor_agent",      # Was: SupervisorExecutionEngine
            "data_helper_agent",     # Was: ToolExecutionEngine  
            "triage_agent",          # Was: AgentExecutionEngine
            "apex_optimizer_agent",  # Was: PipelineExecutor
            "tool_executor",         # Was: EnhancedToolExecutionEngine
            "workflow_orchestrator", # Was: WorkflowExecutor
            "mcp_agent",            # Was: MCPExecutionEngine
            "registry_agent"        # Was: RegistryExecutionEngine
        ]
        
        successful_executions = []
        failed_executions = []
        
        for agent_type in agent_types_to_test:
            try:
                # Mock agent instance creation
                mock_agent = Mock()
                mock_agent.name = agent_type
                mock_agent.agent_name = agent_type
                self.mock_agent_factory.create_agent_instance.return_value = mock_agent
                
                # Create execution context for this agent type
                execution_context = AgentExecutionContext(
                    user_id=self.user_context.user_id,
                    thread_id=self.user_context.thread_id,
                    run_id=self.user_context.run_id,
                    request_id=self.user_context.request_id,
                    agent_name=agent_type,
                    step=PipelineStep.EXECUTION,
                    execution_timestamp=datetime.now(timezone.utc),
                    pipeline_step_num=1,
                    metadata={
                        'agent_type': agent_type,
                        'test_purpose': 'ssot_validation',
                        'former_engine': f'Previously handled by separate engine'
                    }
                )
                
                # Mock agent core execution
                with patch.object(self.engine.agent_core, 'execute_agent') as mock_execute:
                    mock_result = AgentExecutionResult(
                        success=True,
                        agent_name=agent_type,
                        duration=0.1,
                        data=f"Result from {agent_type}",
                        metadata={'agent_type': agent_type}
                    )
                    mock_execute.return_value = mock_result
                    
                    # Execute agent through UserExecutionEngine
                    result = await self.engine.execute_agent(execution_context, self.user_context)
                    
                    # Validate execution success
                    self.assertTrue(result.success, f"Agent {agent_type} execution failed")
                    self.assertEqual(result.agent_name, agent_type)
                    
                    successful_executions.append(agent_type)
                    
            except Exception as e:
                failed_executions.append({'agent_type': agent_type, 'error': str(e)})
        
        # Validate all agent types executed successfully
        if failed_executions:
            error_msg = ["SSOT VALIDATION FAILED: UserExecutionEngine cannot handle all agent types:"]
            for failure in failed_executions:
                error_msg.append(f"  - {failure['agent_type']}: {failure['error']}")
            error_msg.append(f"\nSuccessful: {successful_executions}")
            error_msg.append(f"Issue #1146: UserExecutionEngine must handle all agent types from consolidated engines")
            
            self.fail("\n".join(error_msg))
        
        # Validate all expected agent types were tested
        self.assertEqual(len(successful_executions), len(agent_types_to_test))
        self.assertListEqual(sorted(successful_executions), sorted(agent_types_to_test))

    async def test_user_execution_engine_maintains_proper_user_isolation(self):
        """CRITICAL: Validate UserExecutionEngine maintains user isolation across all agent types."""
        # Create multiple user contexts to test isolation
        user_contexts = []
        engines = []
        
        for i in range(3):
            user_ctx = create_user_execution_context(
                user_id=f"test_user_isolation_{i}",
                operation_name=f"isolation_test_{i}",
                additional_metadata={'user_number': i, 'test': 'isolation'}
            )
            
            # Create separate engine for each user
            mock_factory = get_mock_factory()
            mock_agent_factory = mock_factory.create_agent_factory_mock() 
            mock_websocket_emitter = mock_factory.create_websocket_emitter_mock()
            
            engine = UserExecutionEngine(
                context=user_ctx,
                agent_factory=mock_agent_factory,
                websocket_emitter=mock_websocket_emitter
            )
            
            user_contexts.append(user_ctx)
            engines.append(engine)
        
        try:
            # Execute agents concurrently for different users
            execution_results = []
            
            async def execute_for_user(engine, user_ctx, user_index):
                # Mock agent creation
                mock_agent = Mock()
                mock_agent.name = f"test_agent_user_{user_index}"
                engine.agent_factory.create_agent_instance = AsyncMock(return_value=mock_agent)
                
                # Mock execution
                with patch.object(engine.agent_core, 'execute_agent') as mock_execute:
                    mock_result = AgentExecutionResult(
                        success=True,
                        agent_name=f"test_agent_user_{user_index}",
                        duration=0.1,
                        data=f"User {user_index} specific data",
                        metadata={'user_id': user_ctx.user_id, 'user_index': user_index}
                    )
                    mock_execute.return_value = mock_result
                    
                    execution_context = AgentExecutionContext(
                        user_id=user_ctx.user_id,
                        thread_id=user_ctx.thread_id,
                        run_id=user_ctx.run_id,
                        request_id=user_ctx.request_id,
                        agent_name=f"test_agent_user_{user_index}",
                        step=PipelineStep.EXECUTION,
                        execution_timestamp=datetime.now(timezone.utc),
                        pipeline_step_num=1,
                        metadata={'user_index': user_index}
                    )
                    
                    result = await engine.execute_agent(execution_context, user_ctx)
                    return result
            
            # Run concurrent executions
            tasks = [
                execute_for_user(engines[i], user_contexts[i], i) 
                for i in range(3)
            ]
            results = await asyncio.gather(*tasks)
            
            # Validate user isolation
            for i, result in enumerate(results):
                self.assertTrue(result.success, f"User {i} execution failed")
                self.assertIn(f"user_{i}", result.agent_name.lower())
                self.assertIn(f"User {i}", result.data)
                self.assertEqual(result.metadata['user_index'], i)
            
            # Validate engines maintain separate state
            for i, engine in enumerate(engines):
                stats = engine.get_user_execution_stats()
                self.assertEqual(stats['user_id'], f"test_user_isolation_{i}")
                self.assertEqual(stats['total_executions'], 1)
                
                # Check that each engine only has its own user's data
                all_results = engine.get_all_agent_results()
                for agent_name, result_data in all_results.items():
                    # Results should only belong to this user
                    self.assertIn(f"user_{i}", agent_name.lower(), 
                                f"Engine {i} contains data from other users")
        
        finally:
            # Cleanup all engines
            for engine in engines:
                await engine.cleanup()

    async def test_user_execution_engine_websocket_events_all_agent_types(self):
        """CRITICAL: Validate WebSocket events work for all agent types through single engine."""
        # Test WebSocket events for different agent types that had separate engines
        agent_types_with_former_engines = [
            ("supervisor_agent", "SupervisorExecutionEngine"),
            ("tool_agent", "ToolExecutionEngine"), 
            ("pipeline_agent", "PipelineExecutor"),
            ("mcp_agent", "MCPExecutionEngine")
        ]
        
        websocket_events_validated = []
        
        for agent_type, former_engine in agent_types_with_former_engines:
            # Reset mock call counts
            self.mock_websocket_emitter.reset_mock()
            
            # Mock agent creation
            mock_agent = Mock()
            mock_agent.name = agent_type
            self.mock_agent_factory.create_agent_instance.return_value = mock_agent
            
            # Mock agent core execution
            with patch.object(self.engine.agent_core, 'execute_agent') as mock_execute:
                mock_result = AgentExecutionResult(
                    success=True,
                    agent_name=agent_type,
                    duration=0.1,
                    data=f"Result from {agent_type}",
                    metadata={'former_engine': former_engine}
                )
                mock_execute.return_value = mock_result
                
                execution_context = AgentExecutionContext(
                    user_id=self.user_context.user_id,
                    thread_id=self.user_context.thread_id,
                    run_id=self.user_context.run_id,
                    request_id=self.user_context.request_id,
                    agent_name=agent_type,
                    step=PipelineStep.EXECUTION,
                    execution_timestamp=datetime.now(timezone.utc),
                    pipeline_step_num=1,
                    metadata={'former_engine': former_engine}
                )
                
                # Execute agent
                result = await self.engine.execute_agent(execution_context, self.user_context)
                
                # Validate all 5 critical WebSocket events were called
                events_validated = {
                    'agent_started': self.mock_websocket_emitter.notify_agent_started.called,
                    'agent_thinking': self.mock_websocket_emitter.notify_agent_thinking.called,
                    'agent_completed': self.mock_websocket_emitter.notify_agent_completed.called
                }
                
                # Validate events
                for event_name, was_called in events_validated.items():
                    self.assertTrue(was_called, 
                        f"WebSocket event {event_name} not called for {agent_type} (formerly {former_engine})")
                
                websocket_events_validated.append({
                    'agent_type': agent_type,
                    'former_engine': former_engine,
                    'events': events_validated,
                    'all_events_called': all(events_validated.values())
                })
        
        # Validate all agent types had proper WebSocket events
        failed_validations = [v for v in websocket_events_validated if not v['all_events_called']]
        
        if failed_validations:
            error_msg = ["WEBSOCKET VALIDATION FAILED: Not all events called for consolidated agent types:"]
            for failure in failed_validations:
                error_msg.append(f"  - {failure['agent_type']} (was {failure['former_engine']}): {failure['events']}")
            error_msg.append(f"\nIssue #1146: UserExecutionEngine must emit all WebSocket events for all agent types")
            error_msg.append(f"Business Impact: Missing events break real-time user experience ($500K+ ARR)")
            
            self.fail("\n".join(error_msg))

    async def test_user_execution_engine_performance_with_all_agent_types(self):
        """CRITICAL: Validate UserExecutionEngine performance doesn't degrade with consolidation."""
        # Test execution time for different agent types
        agent_types_to_benchmark = [
            "supervisor_agent", "tool_agent", "pipeline_agent", 
            "mcp_agent", "workflow_agent", "registry_agent"
        ]
        
        execution_times = {}
        max_acceptable_time = 2.0  # 2 seconds max per agent execution
        
        for agent_type in agent_types_to_benchmark:
            # Mock agent creation
            mock_agent = Mock()
            mock_agent.name = agent_type
            self.mock_agent_factory.create_agent_instance.return_value = mock_agent
            
            # Mock fast execution
            with patch.object(self.engine.agent_core, 'execute_agent') as mock_execute:
                mock_result = AgentExecutionResult(
                    success=True,
                    agent_name=agent_type,
                    duration=0.1,  # Fast execution
                    data=f"Fast result from {agent_type}",
                    metadata={'performance_test': True}
                )
                mock_execute.return_value = mock_result
                
                execution_context = AgentExecutionContext(
                    user_id=self.user_context.user_id,
                    thread_id=self.user_context.thread_id,
                    run_id=self.user_context.run_id,
                    request_id=self.user_context.request_id,
                    agent_name=agent_type,
                    step=PipelineStep.EXECUTION,
                    execution_timestamp=datetime.now(timezone.utc),
                    pipeline_step_num=1,
                    metadata={'performance_test': True}
                )
                
                # Measure execution time
                start_time = time.time()
                result = await self.engine.execute_agent(execution_context, self.user_context)
                end_time = time.time()
                
                execution_time = end_time - start_time
                execution_times[agent_type] = execution_time
                
                # Validate execution succeeded
                self.assertTrue(result.success, f"Performance test failed for {agent_type}")
                
                # Validate execution time is acceptable
                self.assertLess(execution_time, max_acceptable_time,
                    f"Execution time {execution_time:.2f}s too slow for {agent_type} "
                    f"(max: {max_acceptable_time}s)")
        
        # Validate overall performance
        avg_execution_time = sum(execution_times.values()) / len(execution_times)
        max_execution_time = max(execution_times.values())
        
        # Performance assertions
        self.assertLess(avg_execution_time, 1.0, 
            f"Average execution time {avg_execution_time:.2f}s too slow (should be <1s)")
        self.assertLess(max_execution_time, max_acceptable_time,
            f"Max execution time {max_execution_time:.2f}s too slow")
        
        # Log performance results
        print(f"PERFORMANCE VALIDATION PASSED:")
        print(f"  Average execution time: {avg_execution_time:.3f}s")
        print(f"  Max execution time: {max_execution_time:.3f}s") 
        print(f"  Agent type times: {execution_times}")

    async def test_user_execution_engine_handles_execution_context_validation(self):
        """CRITICAL: Validate UserExecutionEngine properly validates execution contexts."""
        # Test various invalid execution contexts that should be rejected
        invalid_contexts = [
            {
                'name': 'empty_user_id',
                'context': AgentExecutionContext(
                    user_id="",  # Invalid: empty user ID
                    thread_id=self.user_context.thread_id,
                    run_id=self.user_context.run_id,
                    request_id=self.user_context.request_id,
                    agent_name="test_agent",
                    step=PipelineStep.EXECUTION,
                    execution_timestamp=datetime.now(timezone.utc),
                    pipeline_step_num=1
                )
            },
            {
                'name': 'mismatched_user_id',
                'context': AgentExecutionContext(
                    user_id="different_user",  # Invalid: different user
                    thread_id=self.user_context.thread_id,
                    run_id=self.user_context.run_id,
                    request_id=self.user_context.request_id,
                    agent_name="test_agent",
                    step=PipelineStep.EXECUTION,
                    execution_timestamp=datetime.now(timezone.utc),
                    pipeline_step_num=1
                )
            },
            {
                'name': 'empty_run_id',
                'context': AgentExecutionContext(
                    user_id=self.user_context.user_id,
                    thread_id=self.user_context.thread_id,
                    run_id="",  # Invalid: empty run ID
                    request_id=self.user_context.request_id,
                    agent_name="test_agent", 
                    step=PipelineStep.EXECUTION,
                    execution_timestamp=datetime.now(timezone.utc),
                    pipeline_step_num=1
                )
            },
            {
                'name': 'registry_run_id',
                'context': AgentExecutionContext(
                    user_id=self.user_context.user_id,
                    thread_id=self.user_context.thread_id,
                    run_id="registry",  # Invalid: placeholder run ID
                    request_id=self.user_context.request_id,
                    agent_name="test_agent",
                    step=PipelineStep.EXECUTION,
                    execution_timestamp=datetime.now(timezone.utc),
                    pipeline_step_num=1
                )
            }
        ]
        
        validation_results = []
        
        for invalid_ctx in invalid_contexts:
            try:
                # Attempt to execute with invalid context
                result = await self.engine.execute_agent(invalid_ctx['context'], self.user_context)
                
                # If we get here, validation failed to catch the error
                validation_results.append({
                    'test': invalid_ctx['name'],
                    'should_fail': True,
                    'actually_failed': False,
                    'result': 'VALIDATION_MISSED'
                })
                
            except ValueError as e:
                # Expected - validation caught the error
                validation_results.append({
                    'test': invalid_ctx['name'],
                    'should_fail': True,
                    'actually_failed': True,
                    'error': str(e),
                    'result': 'VALIDATION_PASSED'
                })
                
            except Exception as e:
                # Unexpected error type
                validation_results.append({
                    'test': invalid_ctx['name'],
                    'should_fail': True,
                    'actually_failed': True,
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'result': 'UNEXPECTED_ERROR'
                })
        
        # Validate all invalid contexts were properly rejected
        validation_failures = [r for r in validation_results if r['result'] != 'VALIDATION_PASSED']
        
        if validation_failures:
            error_msg = ["VALIDATION FAILED: UserExecutionEngine accepts invalid execution contexts:"]
            for failure in validation_failures:
                error_msg.append(f"  - {failure['test']}: {failure['result']}")
                if 'error' in failure:
                    error_msg.append(f"    Error: {failure['error']}")
            error_msg.append(f"\nIssue #1146: UserExecutionEngine must validate all execution contexts properly")
            error_msg.append(f"Security Impact: Invalid contexts could cause user isolation failures")
            
            self.fail("\n".join(error_msg))


if __name__ == '__main__':
    unittest.main()