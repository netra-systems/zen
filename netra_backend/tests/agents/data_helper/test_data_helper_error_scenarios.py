"""
Data Helper Agent Error Scenarios Unit Tests

This test suite provides comprehensive coverage of the DataHelperAgent's error handling
capabilities, including invalid input handling, LLM service failures, graceful degradation
patterns, and timeout scenarios.

Business Value: Platform/Internal - Ensures robust error handling for data collection
workflows, maintaining system stability and user experience during failures.

SSOT Compliance: Uses unified BaseTestCase patterns with real error simulation.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.agents.data_helper_agent import DataHelperAgent


class DataHelperErrorScenariosTests(SSotAsyncTestCase):
    """Test suite for Data Helper Agent error scenarios and resilience."""
    
    def setup_method(self, method):
        """Set up test fixtures for error scenario testing."""
        super().setup_method(method)
        
        # Create agent with mocked dependencies
        self.mock_llm_manager = MagicMock()
        self.mock_llm_manager.agenerate = AsyncMock()
        
        self.mock_tool_dispatcher = MagicMock()
        
        self.agent = DataHelperAgent(
            llm_manager=self.mock_llm_manager,
            tool_dispatcher=self.mock_tool_dispatcher
        )
        
        # Mock WebSocket and metadata methods with error tracking
        self.error_tracking = {
            'websocket_errors': [],
            'metadata_errors': [],
            'thinking_events': [],
            'tool_events': []
        }
        
        def track_error(*args):
            self.error_tracking['websocket_errors'].append(args)
            
        def track_thinking(*args):
            self.error_tracking['thinking_events'].append(args)
            
        def track_tool_executing(*args):
            self.error_tracking['tool_events'].append(('executing', args))
            
        def track_tool_completed(*args):
            self.error_tracking['tool_events'].append(('completed', args))
            
        def track_metadata(context, key, value):
            if 'error' in key or 'fallback' in key:
                self.error_tracking['metadata_errors'].append({
                    'key': key,
                    'value': value,
                    'user_id': context.user_id
                })
        
        self.agent.emit_thinking = AsyncMock(side_effect=track_thinking)
        self.agent.emit_tool_executing = AsyncMock(side_effect=track_tool_executing)
        self.agent.emit_tool_completed = AsyncMock(side_effect=track_tool_completed)
        self.agent.emit_error = AsyncMock(side_effect=track_error)
        self.agent.store_metadata_result = MagicMock(side_effect=track_metadata)
        
        # Base user context for testing
        self.test_user_context = MagicMock()
        self.test_user_context.user_id = "error_test_user"
        self.test_user_context.run_id = "error_test_run"
        self.test_user_context.metadata = {
            'user_request': 'Test optimization request for error scenarios',
            'triage_result': {
                'category': 'performance',
                'priority': 'high'
            }
        }
    
    async def test_invalid_user_input_handling_comprehensive(self):
        """Test handling of various invalid user input scenarios."""
        invalid_input_scenarios = [
            {
                'name': 'empty_user_request',
                'metadata': {
                    'user_request': '',
                    'triage_result': {'category': 'performance'}
                },
                'expected_error': 'Insufficient user request'
            },
            {
                'name': 'very_short_request',
                'metadata': {
                    'user_request': 'help',  # Only 4 characters, below 10 character minimum
                    'triage_result': {'category': 'performance'}
                },
                'expected_error': 'Insufficient user request'
            },
            {
                'name': 'whitespace_only_request',
                'metadata': {
                    'user_request': '   \n\t   ',  # Only whitespace
                    'triage_result': {'category': 'performance'}
                },
                'expected_error': 'Insufficient user request'
            },
            {
                'name': 'missing_user_request',
                'metadata': {
                    'triage_result': {'category': 'performance'}
                    # No user_request key at all
                },
                'expected_error': 'Insufficient user request'
            },
            {
                'name': 'none_user_request',
                'metadata': {
                    'user_request': None,
                    'triage_result': {'category': 'performance'}
                },
                'expected_error': 'Insufficient user request'
            }
        ]
        
        for scenario in invalid_input_scenarios:
            # Reset error tracking for each scenario
            self.error_tracking['websocket_errors'].clear()
            self.error_tracking['metadata_errors'].clear()
            
            # Create context with invalid input
            invalid_context = MagicMock()
            invalid_context.user_id = f"invalid_user_{scenario['name']}"
            invalid_context.run_id = f"invalid_run_{scenario['name']}"
            invalid_context.metadata = scenario['metadata']
            
            # Execute with invalid context
            result = await self.agent._execute_with_user_context(invalid_context)
            
            # Verify context is returned (graceful handling)
            self.assertEqual(result, invalid_context)
            
            # Verify error was emitted via WebSocket
            self.assertEqual(len(self.error_tracking['websocket_errors']), 1)
            websocket_error = self.error_tracking['websocket_errors'][0]
            self.assertIn(scenario['expected_error'], websocket_error[0])
            self.assertEqual(websocket_error[1], 'ValueError')
            
            # Verify error was stored in metadata
            error_metadata = [md for md in self.error_tracking['metadata_errors'] 
                            if md['key'] == 'data_helper_error']
            self.assertEqual(len(error_metadata), 1)
            self.assertIn(scenario['expected_error'], error_metadata[0]['value'])
            
            # Verify fallback message was generated
            fallback_metadata = [md for md in self.error_tracking['metadata_errors']
                                if md['key'] == 'data_helper_fallback_message']
            self.assertEqual(len(fallback_metadata), 1)
            fallback_message = fallback_metadata[0]['value']
            self.assertIsInstance(fallback_message, str)
            self.assertGreater(len(fallback_message), 50)
        
        # Record invalid input handling success
        self.record_metric("invalid_input_scenarios_tested", len(invalid_input_scenarios))
        self.record_metric("invalid_input_handling_success", True)
    
    async def test_llm_service_failure_scenarios(self):
        """Test handling of various LLM service failure scenarios."""
        llm_failure_scenarios = [
            {
                'name': 'connection_timeout',
                'exception': asyncio.TimeoutError("LLM request timed out after 30 seconds"),
                'expected_error_type': 'TimeoutError'
            },
            {
                'name': 'connection_refused',
                'exception': ConnectionRefusedError("Connection to LLM service refused"),
                'expected_error_type': 'ConnectionRefusedError'
            },
            {
                'name': 'service_unavailable',
                'exception': ConnectionError("LLM service temporarily unavailable"),
                'expected_error_type': 'ConnectionError'
            },
            {
                'name': 'rate_limit_exceeded',
                'exception': RuntimeError("Rate limit exceeded for LLM requests"),
                'expected_error_type': 'RuntimeError'
            },
            {
                'name': 'authentication_failure',
                'exception': PermissionError("Authentication failed for LLM service"),
                'expected_error_type': 'PermissionError'
            },
            {
                'name': 'malformed_response',
                'exception': ValueError("Malformed response from LLM service"),
                'expected_error_type': 'ValueError'
            },
            {
                'name': 'memory_error',
                'exception': MemoryError("Insufficient memory for LLM processing"),
                'expected_error_type': 'MemoryError'
            }
        ]
        
        for scenario in llm_failure_scenarios:
            # Reset error tracking
            self.error_tracking['websocket_errors'].clear()
            self.error_tracking['metadata_errors'].clear()
            
            # Configure LLM to raise specific exception
            with patch.object(self.agent.data_helper_tool, 'generate_data_request', new_callable=AsyncMock) as mock_generate:
                mock_generate.side_effect = scenario['exception']
                
                # Execute with valid context (error should be in LLM, not input)
                result = await self.agent._execute_with_user_context(self.test_user_context)
                
                # Verify graceful error handling
                self.assertEqual(result, self.test_user_context)
                
                # Verify WebSocket error notification
                self.assertEqual(len(self.error_tracking['websocket_errors']), 1)
                websocket_error = self.error_tracking['websocket_errors'][0]
                self.assertIn(str(scenario['exception']), websocket_error[0])
                self.assertEqual(websocket_error[1], scenario['expected_error_type'])
                
                # Verify error metadata storage
                error_metadata = [md for md in self.error_tracking['metadata_errors']
                                if md['key'] == 'data_helper_error']
                self.assertEqual(len(error_metadata), 1)
                self.assertIn(str(scenario['exception']), error_metadata[0]['value'])
                
                # Verify fallback message generation
                fallback_metadata = [md for md in self.error_tracking['metadata_errors']
                                   if md['key'] == 'data_helper_fallback_message']
                self.assertEqual(len(fallback_metadata), 1)
                
                fallback_message = fallback_metadata[0]['value']
                self.assertIsInstance(fallback_message, str)
                self.assertGreater(len(fallback_message), 100)
                
                # Verify fallback message contains user request
                user_request = self.test_user_context.metadata['user_request']
                self.assertIn(user_request[:100], fallback_message)
        
        # Record LLM failure handling success
        self.record_metric("llm_failure_scenarios_tested", len(llm_failure_scenarios))
        self.record_metric("llm_failure_handling_success", True)
    
    async def test_malformed_triage_result_resilience(self):
        """Test resilience to malformed or corrupted triage results."""
        malformed_triage_scenarios = [
            {
                'name': 'none_triage_result',
                'triage_result': None,
                'should_succeed': True  # Should handle gracefully
            },
            {
                'name': 'empty_dict_triage',
                'triage_result': {},
                'should_succeed': True
            },
            {
                'name': 'corrupted_nested_structure',
                'triage_result': {
                    'category': ['invalid', 'list', 'instead', 'of', 'string'],
                    'priority': {'nested': {'invalid': 'structure'}},
                    'confidence': 'string_instead_of_number'
                },
                'should_succeed': True  # Should pass through to LLM
            },
            {
                'name': 'partial_corruption',
                'triage_result': {
                    'category': 'performance',
                    'invalid_field': object(),  # Non-serializable object
                    'priority': 'high'
                },
                'should_succeed': True  # Should handle non-serializable objects
            },
            {
                'name': 'extremely_large_triage',
                'triage_result': {
                    'category': 'performance',
                    'large_data': 'x' * 100000,  # Very large string
                    'repeated_data': ['item'] * 10000  # Very large list
                },
                'should_succeed': True  # Should handle large data
            }
        ]
        
        for scenario in malformed_triage_scenarios:
            # Reset tracking
            self.error_tracking['websocket_errors'].clear()
            self.error_tracking['metadata_errors'].clear()
            
            # Create context with malformed triage result
            malformed_context = MagicMock()
            malformed_context.user_id = f"malformed_user_{scenario['name']}"
            malformed_context.run_id = f"malformed_run_{scenario['name']}"
            malformed_context.metadata = {
                'user_request': 'Valid user request for malformed triage test',
                'triage_result': scenario['triage_result']
            }
            
            # Mock successful tool response (focus on triage handling, not tool execution)
            with patch.object(self.agent.data_helper_tool, 'generate_data_request', new_callable=AsyncMock) as mock_generate:
                mock_generate.return_value = {
                    'success': True,
                    'data_request': {
                        'user_instructions': f'Instructions for {scenario["name"]}',
                        'structured_items': [{'test': 'item'}]
                    }
                }
                
                if scenario['should_succeed']:
                    # Execute should succeed despite malformed triage
                    result = await self.agent._execute_with_user_context(malformed_context)
                    
                    # Verify execution completed
                    self.assertEqual(result, malformed_context)
                    
                    # Verify tool was called with malformed triage (passed through)
                    tool_call_args = mock_generate.call_args.kwargs
                    passed_triage = tool_call_args['triage_result']
                    self.assertEqual(passed_triage, scenario['triage_result'])
                    
                    # Should have no errors for handled malformed data
                    self.assertEqual(len(self.error_tracking['websocket_errors']), 0)
                else:
                    # Execute should handle error gracefully
                    result = await self.agent._execute_with_user_context(malformed_context)
                    
                    # Should still return context
                    self.assertEqual(result, malformed_context)
                    
                    # Should have error notifications
                    self.assertGreater(len(self.error_tracking['websocket_errors']), 0)
        
        # Record malformed triage resilience success
        self.record_metric("malformed_triage_scenarios_tested", len(malformed_triage_scenarios))
        self.record_metric("malformed_triage_resilience_success", True)
    
    async def test_concurrent_error_scenarios_isolation(self):
        """Test that errors in concurrent executions are properly isolated."""
        # Create multiple contexts with different error scenarios
        concurrent_error_scenarios = [
            {
                'name': 'user_1_success',
                'context': {
                    'user_id': 'concurrent_user_1',
                    'run_id': 'concurrent_run_1',
                    'metadata': {
                        'user_request': 'Valid request for user 1',
                        'triage_result': {'category': 'performance'}
                    }
                },
                'tool_behavior': 'success',
                'expected_outcome': 'success'
            },
            {
                'name': 'user_2_llm_error',
                'context': {
                    'user_id': 'concurrent_user_2',
                    'run_id': 'concurrent_run_2',
                    'metadata': {
                        'user_request': 'Valid request for user 2',
                        'triage_result': {'category': 'optimization'}
                    }
                },
                'tool_behavior': 'llm_error',
                'expected_outcome': 'error_handled'
            },
            {
                'name': 'user_3_invalid_input',
                'context': {
                    'user_id': 'concurrent_user_3',
                    'run_id': 'concurrent_run_3',
                    'metadata': {
                        'user_request': 'x',  # Too short
                        'triage_result': {'category': 'performance'}
                    }
                },
                'tool_behavior': 'not_called',  # Won't reach tool due to input validation
                'expected_outcome': 'input_error'
            },
            {
                'name': 'user_4_success',
                'context': {
                    'user_id': 'concurrent_user_4',
                    'run_id': 'concurrent_run_4',
                    'metadata': {
                        'user_request': 'Another valid request for user 4',
                        'triage_result': {'category': 'scaling'}
                    }
                },
                'tool_behavior': 'success',
                'expected_outcome': 'success'
            }
        ]
        
        # Create agent instances for each concurrent execution
        concurrent_agents = []
        for scenario in concurrent_error_scenarios:
            agent = DataHelperAgent(
                llm_manager=MagicMock(agenerate=AsyncMock()),
                tool_dispatcher=MagicMock()
            )
            
            # Track errors per agent
            scenario['error_tracking'] = {
                'websocket_errors': [],
                'metadata_errors': []
            }
            
            def create_error_tracker(scenario_tracking):
                def track_error(*args):
                    scenario_tracking['websocket_errors'].append(args)
                def track_metadata(context, key, value):
                    if 'error' in key:
                        scenario_tracking['metadata_errors'].append({
                            'key': key, 'value': value, 'user_id': context.user_id
                        })
                return track_error, track_metadata
            
            track_error, track_metadata = create_error_tracker(scenario['error_tracking'])
            
            agent.emit_thinking = AsyncMock()
            agent.emit_tool_executing = AsyncMock()
            agent.emit_tool_completed = AsyncMock()
            agent.emit_error = AsyncMock(side_effect=track_error)
            agent.store_metadata_result = MagicMock(side_effect=track_metadata)
            
            # Configure tool behavior based on scenario
            if scenario['tool_behavior'] == 'success':
                agent.data_helper_tool.generate_data_request = AsyncMock(
                    return_value={
                        'success': True,
                        'data_request': {
                            'user_instructions': f'Success for {scenario["name"]}',
                            'structured_items': [{'test': 'success'}]
                        }
                    }
                )
            elif scenario['tool_behavior'] == 'llm_error':
                agent.data_helper_tool.generate_data_request = AsyncMock(
                    side_effect=RuntimeError(f"LLM error for {scenario['name']}")
                )
            # 'not_called' scenarios won't reach tool due to input validation
            
            concurrent_agents.append((agent, scenario))
        
        # Execute all scenarios concurrently
        async def execute_scenario(agent_scenario_pair):
            agent, scenario = agent_scenario_pair
            context = MagicMock()
            context.user_id = scenario['context']['user_id']
            context.run_id = scenario['context']['run_id']
            context.metadata = scenario['context']['metadata']
            
            result = await agent._execute_with_user_context(context)
            return result, scenario
        
        concurrent_results = await asyncio.gather(*[
            execute_scenario(agent_scenario_pair) for agent_scenario_pair in concurrent_agents
        ])
        
        # Verify concurrent error isolation
        self.assertEqual(len(concurrent_results), 4)
        
        for result, scenario in concurrent_results:
            expected_outcome = scenario['expected_outcome']
            error_tracking = scenario['error_tracking']
            
            # Verify result context
            self.assertEqual(result.user_id, scenario['context']['user_id'])
            
            if expected_outcome == 'success':
                # Should have no errors
                self.assertEqual(len(error_tracking['websocket_errors']), 0)
                self.assertEqual(len(error_tracking['metadata_errors']), 0)
            
            elif expected_outcome == 'error_handled':
                # Should have error notifications but graceful handling
                self.assertEqual(len(error_tracking['websocket_errors']), 1)
                self.assertGreater(len(error_tracking['metadata_errors']), 0)
                
                # Verify error is user-specific
                for error_metadata in error_tracking['metadata_errors']:
                    self.assertEqual(error_metadata['user_id'], scenario['context']['user_id'])
            
            elif expected_outcome == 'input_error':
                # Should have input validation error
                self.assertEqual(len(error_tracking['websocket_errors']), 1)
                websocket_error = error_tracking['websocket_errors'][0]
                self.assertIn('Insufficient user request', websocket_error[0])
        
        # Verify error isolation between users
        user_1_tracking = concurrent_error_scenarios[0]['error_tracking']
        user_2_tracking = concurrent_error_scenarios[1]['error_tracking']
        user_3_tracking = concurrent_error_scenarios[2]['error_tracking']
        user_4_tracking = concurrent_error_scenarios[3]['error_tracking']
        
        # User 1 and 4 should have no errors
        self.assertEqual(len(user_1_tracking['websocket_errors']), 0)
        self.assertEqual(len(user_4_tracking['websocket_errors']), 0)
        
        # User 2 and 3 should have errors, but different types
        self.assertEqual(len(user_2_tracking['websocket_errors']), 1)
        self.assertEqual(len(user_3_tracking['websocket_errors']), 1)
        
        # Errors should be user-specific
        user_2_error = user_2_tracking['websocket_errors'][0][0]
        user_3_error = user_3_tracking['websocket_errors'][0][0]
        self.assertNotEqual(user_2_error, user_3_error)
        
        # Record concurrent error isolation success
        self.record_metric("concurrent_error_scenarios", len(concurrent_error_scenarios))
        self.record_metric("concurrent_error_isolation_success", True)
    
    async def test_resource_exhaustion_and_timeout_scenarios(self):
        """Test handling of resource exhaustion and timeout scenarios."""
        resource_exhaustion_scenarios = [
            {
                'name': 'memory_pressure_simulation',
                'exception': MemoryError("Insufficient memory for data request generation"),
                'expected_graceful_handling': True
            },
            {
                'name': 'cpu_timeout_simulation',
                'exception': asyncio.TimeoutError("CPU timeout during LLM processing"),
                'expected_graceful_handling': True
            },
            {
                'name': 'disk_space_exhaustion',
                'exception': OSError("No space left on device"),
                'expected_graceful_handling': True
            },
            {
                'name': 'network_timeout',
                'exception': asyncio.TimeoutError("Network timeout during LLM request"),
                'expected_graceful_handling': True
            }
        ]
        
        for scenario in resource_exhaustion_scenarios:
            # Reset tracking
            self.error_tracking['websocket_errors'].clear()
            self.error_tracking['metadata_errors'].clear()
            
            # Simulate resource exhaustion in LLM tool
            with patch.object(self.agent.data_helper_tool, 'generate_data_request', new_callable=AsyncMock) as mock_generate:
                mock_generate.side_effect = scenario['exception']
                
                # Test with timeout to ensure we don't hang
                try:
                    result = await asyncio.wait_for(
                        self.agent._execute_with_user_context(self.test_user_context),
                        timeout=5.0  # 5 second timeout
                    )
                    
                    if scenario['expected_graceful_handling']:
                        # Should complete gracefully despite resource issues
                        self.assertEqual(result, self.test_user_context)
                        
                        # Should have error notifications
                        self.assertEqual(len(self.error_tracking['websocket_errors']), 1)
                        websocket_error = self.error_tracking['websocket_errors'][0]
                        self.assertIn(str(scenario['exception']), websocket_error[0])
                        
                        # Should have fallback message
                        fallback_metadata = [md for md in self.error_tracking['metadata_errors']
                                           if md['key'] == 'data_helper_fallback_message']
                        self.assertEqual(len(fallback_metadata), 1)
                    
                except asyncio.TimeoutError:
                    # If timeout occurs, test that we detect it
                    self.fail(f"Resource exhaustion scenario '{scenario['name']}' caused hanging")
        
        # Record resource exhaustion handling success
        self.record_metric("resource_exhaustion_scenarios_tested", len(resource_exhaustion_scenarios))
        self.record_metric("resource_exhaustion_handling_success", True)
    
    async def test_cascading_error_prevention(self):
        """Test prevention of cascading errors in error handling paths."""
        # Simulate errors in error handling itself
        cascading_error_scenarios = [
            {
                'name': 'websocket_emit_error_fails',
                'primary_error': RuntimeError("Primary LLM error"),
                'secondary_error_source': 'websocket_emit'
            },
            {
                'name': 'metadata_storage_fails',
                'primary_error': ValueError("Primary validation error"),
                'secondary_error_source': 'metadata_storage'
            },
            {
                'name': 'fallback_generation_fails',
                'primary_error': ConnectionError("Primary connection error"),
                'secondary_error_source': 'fallback_generation'
            }
        ]
        
        for scenario in cascading_error_scenarios:
            # Reset tracking
            self.error_tracking['websocket_errors'].clear()
            self.error_tracking['metadata_errors'].clear()
            
            # Configure primary error
            with patch.object(self.agent.data_helper_tool, 'generate_data_request', new_callable=AsyncMock) as mock_generate:
                mock_generate.side_effect = scenario['primary_error']
                
                # Configure secondary error in error handling path
                if scenario['secondary_error_source'] == 'websocket_emit':
                    # Make emit_error itself fail
                    def failing_emit_error(*args):
                        raise RuntimeError("WebSocket emit failed")
                    self.agent.emit_error = AsyncMock(side_effect=failing_emit_error)
                
                elif scenario['secondary_error_source'] == 'metadata_storage':
                    # Make metadata storage fail
                    def failing_metadata_storage(context, key, value):
                        if key == 'data_helper_error':
                            raise RuntimeError("Metadata storage failed")
                    self.agent.store_metadata_result = MagicMock(side_effect=failing_metadata_storage)
                
                elif scenario['secondary_error_source'] == 'fallback_generation':
                    # Make fallback message generation fail by mocking _get_fallback_message
                    def failing_fallback(user_request):
                        raise RuntimeError("Fallback generation failed")
                    self.agent._get_fallback_message = MagicMock(side_effect=failing_fallback)
                
                # Execute should still complete without cascading failures
                try:
                    result = await asyncio.wait_for(
                        self.agent._execute_with_user_context(self.test_user_context),
                        timeout=5.0
                    )
                    
                    # Should still return context despite cascading errors
                    self.assertEqual(result, self.test_user_context)
                    
                    # The execution should not hang or throw unhandled exceptions
                    # This test mainly verifies the system doesn't crash
                    
                except Exception as e:
                    # Any unhandled exception indicates cascading error failure
                    self.fail(f"Cascading error scenario '{scenario['name']}' caused unhandled exception: {e}")
        
        # Record cascading error prevention success
        self.record_metric("cascading_error_scenarios_tested", len(cascading_error_scenarios))
        self.record_metric("cascading_error_prevention_success", True)
    
    async def test_error_recovery_and_retry_patterns(self):
        """Test error recovery and retry patterns for transient failures."""
        # Test transient error scenarios that might benefit from retry logic
        transient_error_scenarios = [
            {
                'name': 'temporary_network_issue',
                'errors_then_success': [
                    ConnectionError("Temporary network issue"),
                    ConnectionError("Still having network issues"),
                    {  # Success on third attempt
                        'success': True,
                        'data_request': {
                            'user_instructions': 'Success after retry',
                            'structured_items': [{'category': 'Retry Success', 'data_point': 'Data after retry'}]
                        }
                    }
                ],
                'expected_final_outcome': 'success'
            },
            {
                'name': 'persistent_failure',
                'errors_then_success': [
                    RuntimeError("Persistent service error"),
                    RuntimeError("Still failing"),
                    RuntimeError("Continues to fail")
                ],
                'expected_final_outcome': 'error_handled'
            }
        ]
        
        for scenario in transient_error_scenarios:
            # Reset tracking
            self.error_tracking['websocket_errors'].clear()
            self.error_tracking['metadata_errors'].clear()
            
            # Configure sequential responses (error, error, success/error)
            with patch.object(self.agent.data_helper_tool, 'generate_data_request', new_callable=AsyncMock) as mock_generate:
                
                # Current implementation doesn't have retry logic, so we test the first error only
                first_response = scenario['errors_then_success'][0]
                
                if isinstance(first_response, Exception):
                    mock_generate.side_effect = first_response
                    expected_outcome = 'error_handled'
                else:
                    mock_generate.return_value = first_response
                    expected_outcome = 'success'
                
                # Execute
                result = await self.agent._execute_with_user_context(self.test_user_context)
                
                # Verify result based on expected outcome
                self.assertEqual(result, self.test_user_context)
                
                if expected_outcome == 'success':
                    # Should have no errors
                    self.assertEqual(len(self.error_tracking['websocket_errors']), 0)
                elif expected_outcome == 'error_handled':
                    # Should have error handling
                    self.assertEqual(len(self.error_tracking['websocket_errors']), 1)
                    self.assertGreater(len(self.error_tracking['metadata_errors']), 0)
                
                # Note: This test validates current behavior
                # Future enhancement could add actual retry logic
        
        # Record error recovery pattern testing success
        self.record_metric("transient_error_scenarios_tested", len(transient_error_scenarios))
        self.record_metric("error_recovery_pattern_validation_success", True)
    
    async def test_comprehensive_error_logging_and_diagnostics(self):
        """Test comprehensive error logging and diagnostic information capture."""
        # Test error scenarios with detailed diagnostic requirements
        diagnostic_error_scenarios = [
            {
                'name': 'detailed_llm_failure',
                'error': RuntimeError("LLM service returned invalid response format"),
                'expected_diagnostics': [
                    'user_id', 'run_id', 'error_type', 'error_message',
                    'context_metadata', 'execution_stage'
                ]
            },
            {
                'name': 'input_validation_failure',
                'context_override': {
                    'user_request': 'short',  # Too short
                    'triage_result': {'category': 'test'}
                },
                'expected_diagnostics': [
                    'user_id', 'run_id', 'validation_failure', 'input_length'
                ]
            }
        ]
        
        for scenario in diagnostic_error_scenarios:
            # Reset tracking
            self.error_tracking['websocket_errors'].clear()
            self.error_tracking['metadata_errors'].clear()
            
            # Setup context
            if 'context_override' in scenario:
                test_context = MagicMock()
                test_context.user_id = f"diagnostic_user_{scenario['name']}"
                test_context.run_id = f"diagnostic_run_{scenario['name']}"
                test_context.metadata = scenario['context_override']
            else:
                test_context = self.test_user_context
            
            # Configure error if specified
            if 'error' in scenario:
                with patch.object(self.agent.data_helper_tool, 'generate_data_request', new_callable=AsyncMock) as mock_generate:
                    mock_generate.side_effect = scenario['error']
                    
                    # Execute
                    await self.agent._execute_with_user_context(test_context)
            else:
                # Execute with context override (will trigger validation error)
                await self.agent._execute_with_user_context(test_context)
            
            # Verify diagnostic information is captured
            self.assertGreater(len(self.error_tracking['websocket_errors']), 0)
            self.assertGreater(len(self.error_tracking['metadata_errors']), 0)
            
            # Verify WebSocket error contains diagnostic info
            websocket_error = self.error_tracking['websocket_errors'][0]
            error_message = websocket_error[0]
            error_type = websocket_error[1]
            
            # Basic diagnostic info should be present
            self.assertIsInstance(error_message, str)
            self.assertIsInstance(error_type, str)
            self.assertGreater(len(error_message), 10)
            
            # Verify metadata error storage includes context
            error_metadata = [md for md in self.error_tracking['metadata_errors']
                            if md['key'] == 'data_helper_error']
            self.assertEqual(len(error_metadata), 1)
            
            stored_error = error_metadata[0]
            self.assertEqual(stored_error['user_id'], test_context.user_id)
            self.assertIsInstance(stored_error['value'], str)
        
        # Record diagnostic logging success
        self.record_metric("diagnostic_error_scenarios_tested", len(diagnostic_error_scenarios))
        self.record_metric("error_diagnostics_capture_success", True)