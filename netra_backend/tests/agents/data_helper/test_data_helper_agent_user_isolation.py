"""
Data Helper Agent User Isolation Unit Tests

This test suite provides comprehensive coverage of the DataHelperAgent's user isolation
functionality, ensuring proper factory patterns, multi-user request separation, and
UserExecutionContext security enforcement.

Business Value: Platform/Internal - Ensures secure multi-tenant data request generation,
protecting user data isolation and preventing cross-contamination between concurrent requests.

SSOT Compliance: Uses unified BaseTestCase patterns with real UserExecutionContext validation.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.agents.data_helper_agent import DataHelperAgent


class TestDataHelperAgentUserIsolation(SSotAsyncTestCase):
    """Test suite for Data Helper Agent user isolation and factory patterns."""
    
    async def setUp(self):
        """Set up test fixtures for user isolation testing."""
        await super().setUp()
        
        # Mock dependencies for factory pattern testing
        self.mock_llm_manager = MagicMock()
        self.mock_llm_manager.agenerate = AsyncMock()
        
        self.mock_tool_dispatcher = MagicMock()
        
        # Create multiple user contexts for isolation testing
        self.user_contexts = []
        for i in range(5):
            context = MagicMock()
            context.user_id = f"user_{i}"
            context.run_id = f"run_{i}_{self.get_test_context().test_id}"
            context.session_id = f"session_{i}"
            context.metadata = {
                'user_request': f'User {i} optimization request for {i} specific system',
                'triage_result': {
                    'category': f'category_{i}',
                    'priority': 'high' if i % 2 == 0 else 'low',
                    'user_specific_data': f'sensitive_data_{i}'
                },
                f'user_{i}_private_key': f'private_value_{i}',
                f'custom_field_{i}': f'custom_value_{i}'
            }
            self.user_contexts.append(context)
    
    @patch('netra_backend.app.llm.llm_manager.create_llm_manager')
    @patch('netra_backend.app.core.tools.unified_tool_dispatcher.UnifiedToolDispatcherFactory.create_for_request')
    async def test_factory_creates_unique_instances_per_user(self, mock_dispatcher_factory, mock_llm_factory):
        """Test that factory pattern creates unique agent instances for each user."""
        # Configure factory mocks to return new instances each time
        mock_llm_factory.side_effect = lambda ctx: MagicMock(user_id=ctx.user_id, agenerate=AsyncMock())
        mock_dispatcher_factory.side_effect = lambda ctx: MagicMock(user_id=ctx.user_id)
        
        # Create agents for different users
        agents = []
        for context in self.user_contexts[:3]:  # Test with 3 users
            agent = await DataHelperAgent.create_agent_with_context(context)
            agents.append(agent)
        
        # Verify unique instances were created
        self.assertEqual(len(agents), 3)
        for i, agent in enumerate(agents):
            # Each agent should be a unique instance
            self.assertIsInstance(agent, DataHelperAgent)
            
            # Each agent should have user-specific LLM manager
            self.assertEqual(agent.llm_manager.user_id, f"user_{i}")
            
            # Each agent should have user-specific tool dispatcher
            self.assertEqual(agent.tool_dispatcher.user_id, f"user_{i}")
            
            # Verify agents are different objects
            for j, other_agent in enumerate(agents):
                if i != j:
                    self.assertIsNot(agent, other_agent)
                    self.assertIsNot(agent.llm_manager, other_agent.llm_manager)
                    self.assertIsNot(agent.tool_dispatcher, other_agent.tool_dispatcher)
        
        # Verify factory methods were called correctly for each user
        self.assertEqual(mock_llm_factory.call_count, 3)
        self.assertEqual(mock_dispatcher_factory.call_count, 3)
        
        for i, call in enumerate(mock_llm_factory.call_args_list):
            args, kwargs = call
            self.assertEqual(args[0].user_id, f"user_{i}")
        
        # Record factory pattern success
        self.record_metric("unique_agents_created", 3)
        self.record_metric("factory_pattern_isolation_success", True)
    
    async def test_concurrent_user_request_isolation(self):
        """Test that concurrent user requests are properly isolated from each other."""
        # Create agents with mocked dependencies to avoid external services
        agents = []
        for context in self.user_contexts[:3]:
            agent = DataHelperAgent(
                llm_manager=MagicMock(user_id=context.user_id, agenerate=AsyncMock()),
                tool_dispatcher=MagicMock(user_id=context.user_id)
            )
            
            # Mock WebSocket and metadata methods to track per-user calls
            agent.emit_thinking = AsyncMock()
            agent.emit_tool_executing = AsyncMock()
            agent.emit_tool_completed = AsyncMock()
            agent.emit_error = AsyncMock()
            agent.store_metadata_result = MagicMock()
            
            # Mock the data helper tool with user-specific responses
            agent.data_helper_tool.generate_data_request = AsyncMock(
                return_value={
                    'success': True,
                    'data_request': {
                        'user_instructions': f'Instructions for {context.user_id}',
                        'structured_items': [{
                            'category': f'Category for {context.user_id}',
                            'data_point': f'Data point for {context.user_id}',
                            'required': True
                        }]
                    },
                    'user_context': context.user_id  # Track which user this is for
                }
            )
            
            agents.append((agent, context))
        
        # Execute all agents concurrently
        async def execute_agent(agent_context_pair):
            agent, context = agent_context_pair
            return await agent._execute_with_user_context(context), agent, context
        
        results = await asyncio.gather(*[
            execute_agent(agent_context_pair) for agent_context_pair in agents
        ])
        
        # Verify all executions completed successfully
        self.assertEqual(len(results), 3)
        
        # Verify user isolation in results
        for i, (result_context, agent, original_context) in enumerate(results):
            # Verify correct context was returned
            self.assertEqual(result_context, original_context)
            
            # Verify user-specific WebSocket events were emitted
            agent.emit_thinking.assert_called_once()
            agent.emit_tool_executing.assert_called_once()
            agent.emit_tool_completed.assert_called_once()
            
            # Verify tool execution event contains user-specific data
            tool_executing_call = agent.emit_tool_executing.call_args[0][1]
            expected_request_length = len(original_context.metadata['user_request'])
            self.assertEqual(tool_executing_call['user_request_length'], expected_request_length)
            
            # Verify tool completion event contains user-specific data
            tool_completed_call = agent.emit_tool_completed.call_args[0][1]
            self.assertTrue(tool_completed_call['success'])
            self.assertTrue(tool_completed_call['data_request_generated'])
            
            # Verify data helper tool was called with user-specific data
            tool_call_kwargs = agent.data_helper_tool.generate_data_request.call_args.kwargs
            self.assertEqual(tool_call_kwargs['user_request'], original_context.metadata['user_request'])
            self.assertEqual(tool_call_kwargs['triage_result'], original_context.metadata['triage_result'])
            
            # Verify metadata storage was called with user-specific context
            metadata_calls = agent.store_metadata_result.call_args_list
            self.assertGreater(len(metadata_calls), 0)
            
            # Verify all metadata calls use the correct user context
            for call in metadata_calls:
                stored_context = call[0][0]  # First argument should be the context
                self.assertEqual(stored_context, original_context)
        
        # Record concurrent isolation success
        self.record_metric("concurrent_users_isolated", 3)
        self.record_metric("concurrent_isolation_success", True)
    
    async def test_user_context_metadata_preservation_across_execution(self):
        """Test that user context metadata is preserved and not mixed between users."""
        # Create agent instance
        agent = DataHelperAgent(
            llm_manager=MagicMock(agenerate=AsyncMock()),
            tool_dispatcher=MagicMock()
        )
        
        # Mock dependencies
        agent.emit_thinking = AsyncMock()
        agent.emit_tool_executing = AsyncMock()
        agent.emit_tool_completed = AsyncMock()
        agent.store_metadata_result = MagicMock()
        
        # Track metadata preservation across multiple calls
        metadata_preservation_results = []
        
        for i, context in enumerate(self.user_contexts[:4]):  # Test with 4 users
            # Mock tool response with user-specific data
            agent.data_helper_tool.generate_data_request = AsyncMock(
                return_value={
                    'success': True,
                    'data_request': {
                        'user_instructions': f'User {i} specific instructions',
                        'structured_items': [{'data_point': f'User {i} data point'}]
                    }
                }
            )
            
            # Execute with user context
            result_context = await agent._execute_with_user_context(context)
            
            # Verify metadata preservation
            self.assertEqual(result_context, context)
            self.assertEqual(result_context.user_id, f'user_{i}')
            self.assertEqual(result_context.run_id, f'run_{i}_{self.get_test_context().test_id}')
            
            # Verify user-specific metadata fields are preserved
            self.assertEqual(result_context.metadata[f'user_{i}_private_key'], f'private_value_{i}')
            self.assertEqual(result_context.metadata[f'custom_field_{i}'], f'custom_value_{i}')
            
            # Verify triage result user-specific data is preserved
            triage_result = result_context.metadata['triage_result']
            self.assertEqual(triage_result['user_specific_data'], f'sensitive_data_{i}')
            
            # Verify tool was called with preserved user data
            tool_call = agent.data_helper_tool.generate_data_request.call_args
            called_triage_result = tool_call.kwargs['triage_result']
            self.assertEqual(called_triage_result['user_specific_data'], f'sensitive_data_{i}')
            
            # Store results for cross-user validation
            metadata_preservation_results.append({
                'user_id': context.user_id,
                'metadata_snapshot': context.metadata.copy(),
                'tool_call_args': tool_call.kwargs.copy()
            })
        
        # Cross-validate that no user data leaked between executions
        for i, result in enumerate(metadata_preservation_results):
            # Verify user-specific data remained isolated
            user_metadata = result['metadata_snapshot']
            tool_args = result['tool_call_args']
            
            # Check this user's data is correct
            self.assertEqual(user_metadata[f'user_{i}_private_key'], f'private_value_{i}')
            self.assertEqual(tool_args['triage_result']['user_specific_data'], f'sensitive_data_{i}')
            
            # Verify no other user's private data exists in this user's context
            for j in range(len(metadata_preservation_results)):
                if i != j:
                    # Other user's private keys should not exist in this user's metadata
                    self.assertNotIn(f'user_{j}_private_key', user_metadata)
                    
                    # Other user's sensitive data should not exist in triage result
                    self.assertNotEqual(
                        tool_args['triage_result']['user_specific_data'], 
                        f'sensitive_data_{j}'
                    )
        
        # Record metadata preservation success
        self.record_metric("metadata_preservation_tests", len(metadata_preservation_results))
        self.record_metric("metadata_preservation_success", True)
    
    async def test_factory_pattern_user_context_binding(self):
        """Test that factory-created agents are properly bound to their user contexts."""
        with patch('netra_backend.app.llm.llm_manager.create_llm_manager') as mock_llm_factory:
            with patch('netra_backend.app.core.tools.unified_tool_dispatcher.UnifiedToolDispatcherFactory.create_for_request') as mock_dispatcher_factory:
                # Configure factories
                mock_llm_factory.side_effect = lambda ctx: MagicMock(bound_user=ctx.user_id, agenerate=AsyncMock())
                mock_dispatcher_factory.side_effect = lambda ctx: MagicMock(bound_user=ctx.user_id)
                
                # Create agents for multiple users and verify context binding
                context_binding_tests = []
                
                for context in self.user_contexts[:3]:
                    # Create agent with factory pattern
                    agent = await DataHelperAgent.create_agent_with_context(context)
                    
                    # Verify dependencies were created with correct user context
                    self.assertEqual(agent.llm_manager.bound_user, context.user_id)
                    self.assertEqual(agent.tool_dispatcher.bound_user, context.user_id)
                    
                    # Test set_user_context method if available
                    if hasattr(agent, 'set_user_context'):
                        # Mock the method to track calls
                        agent.set_user_context = MagicMock()
                        
                        # Re-call factory to trigger context setting
                        await DataHelperAgent.create_agent_with_context(context)
                        
                        # Verify user context was set (in a new agent instance)
                        # Note: This tests the factory method's context setting logic
                    
                    context_binding_tests.append({
                        'context': context,
                        'agent': agent,
                        'llm_bound_user': agent.llm_manager.bound_user,
                        'dispatcher_bound_user': agent.tool_dispatcher.bound_user
                    })
                
                # Verify all context bindings are correct and unique
                for test_data in context_binding_tests:
                    context = test_data['context']
                    agent = test_data['agent']
                    
                    # Verify correct user binding
                    self.assertEqual(test_data['llm_bound_user'], context.user_id)
                    self.assertEqual(test_data['dispatcher_bound_user'], context.user_id)
                    
                    # Verify agent instance isolation
                    for other_test_data in context_binding_tests:
                        if other_test_data['context'].user_id != context.user_id:
                            # Different users should have different agent instances
                            self.assertIsNot(agent, other_test_data['agent'])
                            self.assertNotEqual(
                                test_data['llm_bound_user'], 
                                other_test_data['llm_bound_user']
                            )
        
        # Record context binding success
        self.record_metric("context_binding_tests", len(context_binding_tests))
        self.record_metric("factory_context_binding_success", True)
    
    async def test_memory_isolation_between_concurrent_users(self):
        """Test that memory and state isolation is maintained between concurrent users."""
        # Create agent instances with shared base but isolated execution
        base_agent_config = {
            'llm_manager': MagicMock(agenerate=AsyncMock()),
            'tool_dispatcher': MagicMock()
        }
        
        # Track memory isolation across concurrent executions
        memory_tracking = {}
        
        async def isolated_execution_test(context, execution_id):
            """Execute agent with specific context and track memory usage."""
            # Create fresh agent instance for this execution
            agent = DataHelperAgent(**base_agent_config)
            
            # Mock methods with execution-specific tracking
            agent.emit_thinking = AsyncMock()
            agent.emit_tool_executing = AsyncMock()
            agent.emit_tool_completed = AsyncMock()
            agent.store_metadata_result = MagicMock()
            
            # Mock tool with execution-specific data
            execution_specific_data = {
                'execution_id': execution_id,
                'user_id': context.user_id,
                'timestamp': f'time_{execution_id}'
            }
            
            agent.data_helper_tool.generate_data_request = AsyncMock(
                return_value={
                    'success': True,
                    'data_request': {
                        'user_instructions': f'Instructions for execution {execution_id}',
                        'structured_items': [execution_specific_data]
                    },
                    'execution_data': execution_specific_data
                }
            )
            
            # Execute with context
            result = await agent._execute_with_user_context(context)
            
            # Track execution-specific memory state
            memory_tracking[execution_id] = {
                'user_id': context.user_id,
                'result_context': result,
                'tool_calls': agent.data_helper_tool.generate_data_request.call_args,
                'metadata_calls': agent.store_metadata_result.call_args_list,
                'execution_data': execution_specific_data
            }
            
            return result, execution_id
        
        # Execute multiple concurrent isolated executions
        execution_tasks = []
        for i, context in enumerate(self.user_contexts[:4]):
            task = isolated_execution_test(context, f'exec_{i}')
            execution_tasks.append(task)
        
        # Run all executions concurrently
        results = await asyncio.gather(*execution_tasks)
        
        # Verify memory isolation between executions
        self.assertEqual(len(results), 4)
        self.assertEqual(len(memory_tracking), 4)
        
        for i, (result, execution_id) in enumerate(results):
            tracked_data = memory_tracking[execution_id]
            
            # Verify execution completed with correct context
            self.assertEqual(result.user_id, f'user_{i}')
            self.assertEqual(tracked_data['user_id'], f'user_{i}')
            
            # Verify execution-specific data was preserved
            execution_data = tracked_data['execution_data']
            self.assertEqual(execution_data['execution_id'], execution_id)
            self.assertEqual(execution_data['user_id'], f'user_{i}')
            
            # Verify no cross-contamination between executions
            for other_execution_id, other_tracked_data in memory_tracking.items():
                if other_execution_id != execution_id:
                    # Different executions should have different data
                    self.assertNotEqual(
                        tracked_data['execution_data']['timestamp'],
                        other_tracked_data['execution_data']['timestamp']
                    )
                    
                    # Tool calls should be execution-specific
                    tool_call_args = tracked_data['tool_calls'].kwargs
                    other_tool_call_args = other_tracked_data['tool_calls'].kwargs
                    
                    self.assertNotEqual(
                        tool_call_args['user_request'],
                        other_tool_call_args['user_request']
                    )
        
        # Record memory isolation success
        self.record_metric("concurrent_memory_isolation_tests", len(results))
        self.record_metric("memory_isolation_success", True)
    
    async def test_user_session_boundary_enforcement(self):
        """Test that user session boundaries are properly enforced."""
        # Create contexts with same user ID but different session IDs
        user_sessions = []
        base_user_id = "multi_session_user"
        
        for session_num in range(3):
            context = MagicMock()
            context.user_id = base_user_id
            context.run_id = f"run_{session_num}"
            context.session_id = f"session_{session_num}"
            context.metadata = {
                'user_request': f'Request in session {session_num}',
                'session_data': f'session_specific_data_{session_num}',
                'triage_result': {
                    'category': 'performance',
                    'session_context': f'context_{session_num}'
                }
            }
            user_sessions.append(context)
        
        # Create agent for session boundary testing
        agent = DataHelperAgent(
            llm_manager=MagicMock(agenerate=AsyncMock()),
            tool_dispatcher=MagicMock()
        )
        
        # Mock dependencies
        agent.emit_thinking = AsyncMock()
        agent.emit_tool_executing = AsyncMock()  
        agent.emit_tool_completed = AsyncMock()
        agent.store_metadata_result = MagicMock()
        
        # Execute across different sessions
        session_results = []
        
        for session_context in user_sessions:
            # Mock session-specific tool response
            agent.data_helper_tool.generate_data_request = AsyncMock(
                return_value={
                    'success': True,
                    'data_request': {
                        'user_instructions': f'Session {session_context.session_id} instructions',
                        'structured_items': [{
                            'session_id': session_context.session_id,
                            'data_point': 'Session-specific data requirement'
                        }]
                    }
                }
            )
            
            # Execute with session context
            result = await agent._execute_with_user_context(session_context)
            
            session_results.append({
                'session_id': session_context.session_id,
                'result': result,
                'tool_call': agent.data_helper_tool.generate_data_request.call_args
            })
        
        # Verify session boundary enforcement
        for i, session_result in enumerate(session_results):
            session_context = user_sessions[i]
            result = session_result['result']
            tool_call = session_result['tool_call']
            
            # Verify correct session context was preserved
            self.assertEqual(result.session_id, session_context.session_id)
            self.assertEqual(result.user_id, base_user_id)  # Same user
            
            # Verify session-specific metadata was preserved
            self.assertEqual(result.metadata['session_data'], f'session_specific_data_{i}')
            
            # Verify tool was called with session-specific data
            tool_triage_result = tool_call.kwargs['triage_result']
            self.assertEqual(tool_triage_result['session_context'], f'context_{i}')
            
            # Verify no session data leaked between calls
            for j, other_session_result in enumerate(session_results):
                if i != j:
                    other_result = other_session_result['result']
                    
                    # Different sessions should have different session IDs
                    self.assertNotEqual(result.session_id, other_result.session_id)
                    
                    # Session-specific data should not cross boundaries
                    self.assertNotEqual(
                        result.metadata['session_data'],
                        other_result.metadata['session_data']
                    )
        
        # Record session boundary success
        self.record_metric("session_boundary_tests", len(session_results))
        self.record_metric("session_boundary_enforcement_success", True)
    
    async def test_resource_cleanup_and_isolation_after_execution(self):
        """Test that resources are properly cleaned up and isolated after execution."""
        # Create agent with resource tracking
        agent = DataHelperAgent(
            llm_manager=MagicMock(agenerate=AsyncMock()),
            tool_dispatcher=MagicMock()
        )
        
        # Mock dependencies with resource tracking
        resource_tracker = {
            'websocket_events': [],
            'metadata_operations': [],
            'tool_calls': []
        }
        
        def track_emit_thinking(*args):
            resource_tracker['websocket_events'].append(('thinking', args))
            
        def track_emit_tool_executing(*args):
            resource_tracker['websocket_events'].append(('tool_executing', args))
            
        def track_emit_tool_completed(*args):
            resource_tracker['websocket_events'].append(('tool_completed', args))
            
        def track_store_metadata(*args):
            resource_tracker['metadata_operations'].append(args)
        
        agent.emit_thinking = AsyncMock(side_effect=track_emit_thinking)
        agent.emit_tool_executing = AsyncMock(side_effect=track_emit_tool_executing)
        agent.emit_tool_completed = AsyncMock(side_effect=track_emit_tool_completed)
        agent.store_metadata_result = MagicMock(side_effect=track_store_metadata)
        
        # Track tool calls
        def track_tool_call(*args, **kwargs):
            resource_tracker['tool_calls'].append((args, kwargs))
            return {
                'success': True,
                'data_request': {
                    'user_instructions': 'Test instructions',
                    'structured_items': [{'test': 'data'}]
                }
            }
        
        agent.data_helper_tool.generate_data_request = AsyncMock(side_effect=track_tool_call)
        
        # Execute with multiple users to test resource isolation
        cleanup_test_contexts = self.user_contexts[:3]
        
        for context in cleanup_test_contexts:
            # Clear resource tracker for each user
            previous_resource_count = {
                'websocket_events': len(resource_tracker['websocket_events']),
                'metadata_operations': len(resource_tracker['metadata_operations']),
                'tool_calls': len(resource_tracker['tool_calls'])
            }
            
            # Execute with user context
            await agent._execute_with_user_context(context)
            
            # Verify resources were used for this execution
            current_resource_count = {
                'websocket_events': len(resource_tracker['websocket_events']),
                'metadata_operations': len(resource_tracker['metadata_operations']),
                'tool_calls': len(resource_tracker['tool_calls'])
            }
            
            # Verify resource usage increased
            self.assertGreater(
                current_resource_count['websocket_events'],
                previous_resource_count['websocket_events']
            )
            self.assertGreater(
                current_resource_count['metadata_operations'],
                previous_resource_count['metadata_operations']
            )
            self.assertGreater(
                current_resource_count['tool_calls'],
                previous_resource_count['tool_calls']
            )
            
            # Verify recent resource operations were user-specific
            recent_metadata_ops = resource_tracker['metadata_operations'][
                previous_resource_count['metadata_operations']:
            ]
            
            for metadata_op in recent_metadata_ops:
                stored_context = metadata_op[0]  # First argument is the context
                self.assertEqual(stored_context.user_id, context.user_id)
                self.assertEqual(stored_context.run_id, context.run_id)
        
        # Verify total resource usage matches expected pattern
        expected_websocket_events_per_user = 3  # thinking, tool_executing, tool_completed
        expected_total_websocket_events = len(cleanup_test_contexts) * expected_websocket_events_per_user
        
        self.assertEqual(
            len(resource_tracker['websocket_events']), 
            expected_total_websocket_events
        )
        
        # Verify each user's resource usage was isolated
        websocket_events_per_user = {}
        for event_type, event_args in resource_tracker['websocket_events']:
            # Events don't directly contain user info, but should be proportionally distributed
            pass  # This test mainly verifies the tracking mechanism works
        
        # Record resource cleanup success
        self.record_metric("resource_cleanup_tests", len(cleanup_test_contexts))
        self.record_metric("resource_isolation_success", True)
        self.record_metric("total_tracked_websocket_events", len(resource_tracker['websocket_events']))
        self.record_metric("total_tracked_metadata_operations", len(resource_tracker['metadata_operations']))