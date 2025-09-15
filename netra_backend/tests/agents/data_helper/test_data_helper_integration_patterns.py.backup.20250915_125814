"""
Data Helper Agent Integration Patterns Unit Tests

This test suite provides comprehensive coverage of the DataHelperAgent's integration
patterns with other system components, including triage result processing, tool dispatcher
communication, and WebSocket event integration.

Business Value: Platform/Internal - Ensures reliable integration patterns for data
collection workflows, supporting seamless AI optimization agent coordination.

SSOT Compliance: Uses unified BaseTestCase patterns with real service integration patterns.
"""

from unittest.mock import AsyncMock, MagicMock, patch, call
from typing import Dict, Any, List

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.agents.data_helper_agent import DataHelperAgent


class TestDataHelperIntegrationPatterns(SSotAsyncTestCase):
    """Test suite for Data Helper Agent integration patterns."""
    
    async def setUp(self):
        """Set up test fixtures for integration testing."""
        await super().setUp()
        
        # Create agent with mocked dependencies
        self.mock_llm_manager = MagicMock()
        self.mock_llm_manager.agenerate = AsyncMock()
        
        self.mock_tool_dispatcher = MagicMock()
        
        self.agent = DataHelperAgent(
            llm_manager=self.mock_llm_manager,
            tool_dispatcher=self.mock_tool_dispatcher
        )
        
        # Mock WebSocket and metadata methods
        self.agent.emit_thinking = AsyncMock()
        self.agent.emit_tool_executing = AsyncMock()
        self.agent.emit_tool_completed = AsyncMock()
        self.agent.emit_error = AsyncMock()
        self.agent.store_metadata_result = MagicMock()
        
        # Sample user context for testing
        self.test_user_context = MagicMock()
        self.test_user_context.user_id = "integration_test_user"
        self.test_user_context.run_id = "integration_test_run"
        self.test_user_context.metadata = {
            'user_request': 'Optimize my system performance for high traffic',
            'triage_result': {
                'category': 'performance',
                'priority': 'high',
                'complexity': 'medium',
                'data_sufficiency': 'insufficient',
                'identified_areas': ['database', 'caching', 'network'],
                'recommendations': ['gather metrics', 'analyze bottlenecks']
            }
        }
    
    async def test_triage_result_integration_with_comprehensive_analysis(self):
        """Test integration with comprehensive triage result analysis."""
        # Create complex triage result with multiple analysis dimensions
        comprehensive_triage = {
            'category': 'performance_optimization',
            'priority': 'critical',
            'complexity': 'high',
            'data_sufficiency': 'insufficient',
            'confidence_score': 0.85,
            'identified_bottlenecks': [
                {'type': 'database', 'severity': 'high', 'area': 'query_performance'},
                {'type': 'application', 'severity': 'medium', 'area': 'memory_usage'},
                {'type': 'network', 'severity': 'low', 'area': 'bandwidth_utilization'}
            ],
            'required_data_categories': ['metrics', 'logs', 'configurations'],
            'suggested_timeframe': '7_days',
            'business_impact': 'high_user_experience_degradation'
        }
        
        # Update context with comprehensive triage result
        self.test_user_context.metadata['triage_result'] = comprehensive_triage
        
        # Mock successful tool response that integrates triage analysis
        mock_tool_response = {
            'success': True,
            'data_request': {
                'user_instructions': 'Comprehensive data collection based on triage analysis',
                'structured_items': [
                    {
                        'category': 'Database Performance',
                        'data_point': 'Query execution times',
                        'justification': 'High severity database bottleneck identified',
                        'required': True
                    },
                    {
                        'category': 'Application Metrics', 
                        'data_point': 'Memory usage patterns',
                        'justification': 'Medium severity memory usage issue',
                        'required': True
                    }
                ],
                'priority_mapping': {
                    'high': ['database_metrics'],
                    'medium': ['application_metrics'],
                    'low': ['network_metrics']
                }
            }
        }
        
        with patch.object(self.agent.data_helper_tool, 'generate_data_request', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_tool_response
            
            # Execute with comprehensive triage context
            result = await self.agent._execute_with_user_context(self.test_user_context)
            
            # Verify triage result was passed correctly to tool
            tool_call_args = mock_generate.call_args.kwargs
            passed_triage = tool_call_args['triage_result']
            
            # Verify all triage analysis components were preserved
            self.assertEqual(passed_triage['confidence_score'], 0.85)
            self.assertEqual(len(passed_triage['identified_bottlenecks']), 3)
            self.assertEqual(passed_triage['business_impact'], 'high_user_experience_degradation')
            
            # Verify tool executing event includes triage confidence
            tool_executing_call = self.agent.emit_tool_executing.call_args[0][1]
            self.assertTrue(tool_executing_call['triage_result_available'])
            
            # Verify result metadata includes triage integration
            metadata_calls = self.agent.store_metadata_result.call_args_list
            data_result_call = next(call for call in metadata_calls if call[0][1] == 'data_result')
            stored_result = data_result_call[0][2]
            
            self.assertTrue(stored_result['success'])
            self.assertIn('priority_mapping', stored_result['data_request'])
        
        # Record triage integration success
        self.record_metric("triage_integration_complexity", len(comprehensive_triage['identified_bottlenecks']))
        self.record_metric("triage_comprehensive_integration_success", True)
    
    async def test_tool_dispatcher_communication_patterns(self):
        """Test communication patterns with UnifiedToolDispatcher."""
        # Mock tool dispatcher with various interaction patterns
        dispatcher_interactions = []
        
        def track_dispatcher_call(method_name, *args, **kwargs):
            dispatcher_interactions.append({
                'method': method_name,
                'args': args,
                'kwargs': kwargs,
                'timestamp': self.get_test_context().test_id
            })
            return MagicMock()  # Return mock result
        
        # Configure tool dispatcher with tracking
        self.mock_tool_dispatcher.execute_tool = MagicMock(
            side_effect=lambda *args, **kwargs: track_dispatcher_call('execute_tool', *args, **kwargs)
        )
        self.mock_tool_dispatcher.get_available_tools = MagicMock(
            side_effect=lambda *args, **kwargs: track_dispatcher_call('get_available_tools', *args, **kwargs)
        )
        
        # Mock successful data helper tool execution
        with patch.object(self.agent.data_helper_tool, 'generate_data_request', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = {
                'success': True,
                'data_request': {
                    'user_instructions': 'Tool dispatcher integration test',
                    'structured_items': [{'category': 'Test', 'data_point': 'Test data'}]
                }
            }
            
            # Execute agent
            await self.agent._execute_with_user_context(self.test_user_context)
            
            # Verify agent has access to tool dispatcher
            self.assertEqual(self.agent.tool_dispatcher, self.mock_tool_dispatcher)
            
            # Verify data helper tool was used (primary integration)
            mock_generate.assert_called_once()
            
            # Verify tool dispatcher is available for extended functionality
            # (The DataHelperAgent doesn't directly use tool dispatcher in current implementation,
            # but it's available for future enhancements)
            self.assertIsNotNone(self.agent.tool_dispatcher)
            
            # Test potential tool dispatcher integration scenarios
            if hasattr(self.agent, 'use_additional_tools'):
                # Future enhancement: agent could use additional tools via dispatcher
                additional_tools = self.agent.tool_dispatcher.get_available_tools()
                self.assertIsNotNone(additional_tools)
        
        # Record tool dispatcher integration success
        self.record_metric("tool_dispatcher_available", True)
        self.record_metric("primary_tool_integration_success", True)
    
    async def test_websocket_event_sequence_and_timing(self):
        """Test WebSocket event emission sequence and timing patterns."""
        # Track WebSocket event sequence
        event_sequence = []
        
        def track_thinking(*args):
            event_sequence.append(('thinking', args, len(event_sequence)))
            
        def track_tool_executing(*args):
            event_sequence.append(('tool_executing', args, len(event_sequence)))
            
        def track_tool_completed(*args):
            event_sequence.append(('tool_completed', args, len(event_sequence)))
            
        def track_error(*args):
            event_sequence.append(('error', args, len(event_sequence)))
        
        # Configure event tracking
        self.agent.emit_thinking = AsyncMock(side_effect=track_thinking)
        self.agent.emit_tool_executing = AsyncMock(side_effect=track_tool_executing)
        self.agent.emit_tool_completed = AsyncMock(side_effect=track_tool_completed)
        self.agent.emit_error = AsyncMock(side_effect=track_error)
        
        # Test successful execution sequence
        with patch.object(self.agent.data_helper_tool, 'generate_data_request', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = {
                'success': True,
                'data_request': {
                    'user_instructions': 'WebSocket integration test instructions',
                    'structured_items': [
                        {'category': 'Performance', 'data_point': 'Response times'},
                        {'category': 'Usage', 'data_point': 'Traffic patterns'}
                    ]
                }
            }
            
            # Execute agent
            await self.agent._execute_with_user_context(self.test_user_context)
            
            # Verify event sequence and timing
            self.assertEqual(len(event_sequence), 3)  # thinking, tool_executing, tool_completed
            
            # Verify correct sequence order
            self.assertEqual(event_sequence[0][0], 'thinking')
            self.assertEqual(event_sequence[1][0], 'tool_executing')
            self.assertEqual(event_sequence[2][0], 'tool_completed')
            
            # Verify thinking event content
            thinking_args = event_sequence[0][1]
            self.assertIn("Analyzing user request", thinking_args[0])
            
            # Verify tool executing event content
            tool_executing_args = event_sequence[1][1]
            self.assertEqual(tool_executing_args[0], "data_helper")
            tool_params = tool_executing_args[1]
            self.assertIn('user_request_length', tool_params)
            self.assertIn('triage_result_available', tool_params)
            self.assertIn('previous_results_count', tool_params)
            
            # Verify tool completed event content
            tool_completed_args = event_sequence[2][1]
            self.assertEqual(tool_completed_args[0], "data_helper")
            completion_params = tool_completed_args[1]
            self.assertTrue(completion_params['success'])
            self.assertTrue(completion_params['data_request_generated'])
            self.assertEqual(completion_params['structured_items_count'], 2)
            
            # Verify no error events were emitted
            error_events = [event for event in event_sequence if event[0] == 'error']
            self.assertEqual(len(error_events), 0)
        
        # Record WebSocket integration success
        self.record_metric("websocket_event_sequence_length", len(event_sequence))
        self.record_metric("websocket_sequence_integration_success", True)
    
    async def test_previous_agent_results_processing_and_context_building(self):
        """Test processing of previous agent results for context building."""
        # Create complex previous results from multiple agents
        complex_previous_results = {
            'triage_result': {
                'agent_name': 'triage_agent',
                'execution_time': '2023-12-09T10:30:00Z',
                'result': {
                    'category': 'performance',
                    'identified_issues': ['slow_queries', 'memory_leaks'],
                    'confidence': 0.92
                }
            },
            'optimizations_result': {
                'agent_name': 'apex_optimizer_agent',
                'execution_time': '2023-12-09T10:35:00Z',
                'result': {
                    'recommendations': [
                        {'type': 'database_indexing', 'priority': 'high'},
                        {'type': 'caching_strategy', 'priority': 'medium'}
                    ],
                    'estimated_improvement': '40%'
                }
            },
            'synthetic_data_result': {
                'agent_name': 'synthetic_data_agent',
                'execution_time': '2023-12-09T10:40:00Z',
                'result': {
                    'generated_scenarios': ['high_load', 'peak_traffic'],
                    'data_points': 150
                }
            }
        }
        
        # Update context with previous results
        self.test_user_context.metadata.update(complex_previous_results)
        
        # Mock tool response that incorporates previous results
        with patch.object(self.agent.data_helper_tool, 'generate_data_request', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = {
                'success': True,
                'data_request': {
                    'user_instructions': 'Data collection based on previous agent analysis',
                    'structured_items': [
                        {'category': 'Database', 'data_point': 'Query performance metrics'},
                        {'category': 'Caching', 'data_point': 'Cache hit ratios'},
                        {'category': 'Load Testing', 'data_point': 'High load scenario data'}
                    ],
                    'context_integration': 'previous_results_incorporated'
                }
            }
            
            # Execute agent
            await self.agent._execute_with_user_context(self.test_user_context)
            
            # Verify previous results were extracted and passed to tool
            tool_call_args = mock_generate.call_args.kwargs
            passed_previous_results = tool_call_args['previous_results']
            
            # Verify all previous agent results were included
            self.assertIn('triage_result', passed_previous_results)
            self.assertIn('optimizations_result', passed_previous_results)
            self.assertIn('synthetic_data_result', passed_previous_results)
            
            # Verify result structure preservation
            triage_in_previous = passed_previous_results['triage_result']
            self.assertEqual(triage_in_previous['agent_name'], 'triage_agent')
            self.assertEqual(triage_in_previous['result']['confidence'], 0.92)
            
            optimizations_in_previous = passed_previous_results['optimizations_result']
            self.assertEqual(optimizations_in_previous['result']['estimated_improvement'], '40%')
            
            # Verify tool executing event includes previous results count
            tool_executing_call = self.agent.emit_tool_executing.call_args[0][1]
            self.assertEqual(tool_executing_call['previous_results_count'], 3)
            
            # Verify context building in metadata storage
            metadata_calls = self.agent.store_metadata_result.call_args_list
            data_result_call = next(call for call in metadata_calls if call[0][1] == 'data_result')
            stored_result = data_result_call[0][2]
            
            self.assertIn('context_integration', stored_result['data_request'])
            self.assertEqual(stored_result['data_request']['context_integration'], 'previous_results_incorporated')
        
        # Record previous results integration success
        self.record_metric("previous_results_agents_count", len(complex_previous_results))
        self.record_metric("context_building_integration_success", True)
    
    async def test_metadata_storage_patterns_and_result_persistence(self):
        """Test metadata storage patterns and result persistence across execution."""
        # Track all metadata storage operations
        metadata_operations = []
        
        def track_metadata_storage(context, key, value):
            metadata_operations.append({
                'context_user_id': context.user_id,
                'context_run_id': context.run_id,
                'key': key,
                'value': value,
                'operation_index': len(metadata_operations)
            })
        
        self.agent.store_metadata_result = MagicMock(side_effect=track_metadata_storage)
        
        # Mock successful tool execution
        with patch.object(self.agent.data_helper_tool, 'generate_data_request', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = {
                'success': True,
                'data_request': {
                    'user_instructions': 'Metadata storage test instructions',
                    'structured_items': [
                        {'category': 'Test Category', 'data_point': 'Test data point'},
                        {'category': 'Another Category', 'data_point': 'Another data point'}
                    ],
                    'raw_response': 'Mock LLM response for metadata test'
                },
                'generation_metadata': {
                    'llm_tokens_used': 150,
                    'processing_time': 2.5
                }
            }
            
            # Execute agent
            await self.agent._execute_with_user_context(self.test_user_context)
            
            # Verify metadata storage operations
            self.assertGreater(len(metadata_operations), 0)
            
            # Find and verify specific metadata storage calls
            data_result_ops = [op for op in metadata_operations if op['key'] == 'data_result']
            self.assertEqual(len(data_result_ops), 1)
            
            data_result_op = data_result_ops[0]
            self.assertEqual(data_result_op['context_user_id'], self.test_user_context.user_id)
            self.assertEqual(data_result_op['context_run_id'], self.test_user_context.run_id)
            
            # Verify data result content
            stored_data_result = data_result_op['value']
            self.assertTrue(stored_data_result['success'])
            self.assertIn('data_request', stored_data_result)
            self.assertIn('generation_metadata', stored_data_result)
            
            # Verify data_request_generated flag storage
            flag_ops = [op for op in metadata_operations if op['key'] == 'data_request_generated']
            self.assertEqual(len(flag_ops), 1)
            self.assertTrue(flag_ops[0]['value'])
            
            # Verify all operations used correct context
            for operation in metadata_operations:
                self.assertEqual(operation['context_user_id'], self.test_user_context.user_id)
                self.assertEqual(operation['context_run_id'], self.test_user_context.run_id)
            
            # Verify operation sequence (data_result should be stored before flag)
            data_result_index = data_result_ops[0]['operation_index']
            flag_index = flag_ops[0]['operation_index']
            self.assertLess(data_result_index, flag_index)
        
        # Record metadata storage success
        self.record_metric("metadata_operations_count", len(metadata_operations))
        self.record_metric("metadata_storage_integration_success", True)
    
    async def test_error_handling_integration_with_websocket_notifications(self):
        """Test error handling integration with WebSocket error notifications."""
        # Track error handling integration
        error_integration_tracking = {
            'websocket_errors': [],
            'metadata_errors': [],
            'tool_execution_errors': []
        }
        
        def track_websocket_error(*args):
            error_integration_tracking['websocket_errors'].append(args)
            
        def track_metadata_error(context, key, value):
            if 'error' in key:
                error_integration_tracking['metadata_errors'].append({
                    'key': key,
                    'value': value,
                    'context_user': context.user_id
                })
        
        self.agent.emit_error = AsyncMock(side_effect=track_websocket_error)
        self.agent.store_metadata_result = MagicMock(side_effect=track_metadata_error)
        
        # Force tool execution error
        with patch.object(self.agent.data_helper_tool, 'generate_data_request', new_callable=AsyncMock) as mock_generate:
            mock_generate.side_effect = RuntimeError("Integration test error for error handling")
            
            # Execute agent (should handle error gracefully)
            result = await self.agent._execute_with_user_context(self.test_user_context)
            
            # Verify result context is returned even with error
            self.assertEqual(result, self.test_user_context)
            
            # Verify WebSocket error notification was sent
            self.assertEqual(len(error_integration_tracking['websocket_errors']), 1)
            
            websocket_error_args = error_integration_tracking['websocket_errors'][0]
            self.assertIn("Integration test error", websocket_error_args[0])
            self.assertEqual(websocket_error_args[1], "RuntimeError")
            
            # Verify error metadata was stored
            self.assertGreater(len(error_integration_tracking['metadata_errors']), 0)
            
            # Find error-specific metadata
            error_metadata = [md for md in error_integration_tracking['metadata_errors'] 
                            if md['key'] == 'data_helper_error']
            self.assertEqual(len(error_metadata), 1)
            self.assertEqual(error_metadata[0]['context_user'], self.test_user_context.user_id)
            self.assertIn("Integration test error", error_metadata[0]['value'])
            
            # Find fallback message metadata
            fallback_metadata = [md for md in error_integration_tracking['metadata_errors']
                                if md['key'] == 'data_helper_fallback_message']
            self.assertEqual(len(fallback_metadata), 1)
            self.assertIsInstance(fallback_metadata[0]['value'], str)
            self.assertGreater(len(fallback_metadata[0]['value']), 20)
        
        # Record error integration success
        self.record_metric("error_websocket_notifications", len(error_integration_tracking['websocket_errors']))
        self.record_metric("error_metadata_operations", len(error_integration_tracking['metadata_errors']))
        self.record_metric("error_handling_integration_success", True)
    
    async def test_end_to_end_integration_workflow_simulation(self):
        """Test complete end-to-end integration workflow simulation."""
        # Simulate complete workflow from triage through data collection request
        workflow_stages = []
        
        # Stage 1: Enhanced triage result input
        enhanced_triage_result = {
            'category': 'comprehensive_optimization',
            'priority': 'critical',
            'complexity': 'high', 
            'data_sufficiency': 'insufficient',
            'analysis_depth': 'detailed',
            'identified_optimization_areas': [
                {'area': 'database_performance', 'impact': 'high', 'data_needed': 'query_metrics'},
                {'area': 'application_scaling', 'impact': 'medium', 'data_needed': 'resource_usage'},
                {'area': 'user_experience', 'impact': 'high', 'data_needed': 'response_times'}
            ],
            'business_context': {
                'user_base_size': 'large',
                'performance_requirements': 'strict',
                'budget_constraints': 'medium'
            }
        }
        
        workflow_stages.append('triage_analysis_complete')
        
        # Stage 2: Previous optimization attempts
        previous_optimization_results = {
            'optimizations_result': {
                'agent_name': 'apex_optimizer_agent',
                'result': {
                    'attempted_optimizations': ['database_indexing', 'connection_pooling'],
                    'success_rate': 0.65,
                    'remaining_issues': ['complex_query_optimization', 'memory_management']
                }
            },
            'action_plan_result': {
                'agent_name': 'action_plan_agent',
                'result': {
                    'planned_phases': ['data_collection', 'analysis', 'implementation'],
                    'current_phase': 'data_collection',
                    'data_requirements': 'comprehensive_metrics'
                }
            }
        }
        
        workflow_stages.append('previous_results_available')
        
        # Update context with workflow data
        self.test_user_context.metadata['triage_result'] = enhanced_triage_result
        self.test_user_context.metadata.update(previous_optimization_results)
        
        # Stage 3: Execute data helper with comprehensive integration
        workflow_execution_tracking = {
            'websocket_events': [],
            'tool_interactions': [],
            'metadata_persistence': []
        }
        
        def track_websocket_events(event_type, *args):
            workflow_execution_tracking['websocket_events'].append({
                'type': event_type,
                'args': args,
                'stage': len(workflow_execution_tracking['websocket_events'])
            })
        
        self.agent.emit_thinking = AsyncMock(side_effect=lambda *args: track_websocket_events('thinking', *args))
        self.agent.emit_tool_executing = AsyncMock(side_effect=lambda *args: track_websocket_events('tool_executing', *args))
        self.agent.emit_tool_completed = AsyncMock(side_effect=lambda *args: track_websocket_events('tool_completed', *args))
        
        def track_metadata_persistence(context, key, value):
            workflow_execution_tracking['metadata_persistence'].append({
                'key': key,
                'value_type': type(value).__name__,
                'has_data_request': 'data_request' in str(value) if isinstance(value, dict) else False
            })
        
        self.agent.store_metadata_result = MagicMock(side_effect=track_metadata_persistence)
        
        # Mock comprehensive tool response
        with patch.object(self.agent.data_helper_tool, 'generate_data_request', new_callable=AsyncMock) as mock_generate:
            comprehensive_response = {
                'success': True,
                'data_request': {
                    'user_instructions': 'Comprehensive data collection for end-to-end optimization workflow',
                    'structured_items': [
                        {
                            'category': 'Database Performance',
                            'data_point': 'Query execution plans and timing',
                            'justification': 'Critical for complex query optimization',
                            'required': True
                        },
                        {
                            'category': 'Resource Usage',
                            'data_point': 'Memory allocation patterns',
                            'justification': 'Required for memory management optimization',
                            'required': True
                        },
                        {
                            'category': 'User Experience',
                            'data_point': 'Response time percentiles',
                            'justification': 'Essential for user experience validation',
                            'required': True
                        }
                    ],
                    'workflow_integration': {
                        'addresses_triage_findings': True,
                        'builds_on_previous_attempts': True,
                        'supports_action_plan': True
                    }
                },
                'workflow_metadata': {
                    'integration_completeness': 1.0,
                    'data_sufficiency_improvement': 'high',
                    'next_phase_readiness': True
                }
            }
            
            def track_tool_interaction(*args, **kwargs):
                workflow_execution_tracking['tool_interactions'].append({
                    'args': args,
                    'kwargs': kwargs,
                    'triage_complexity': len(kwargs.get('triage_result', {}).get('identified_optimization_areas', [])),
                    'previous_results_count': len(kwargs.get('previous_results', {}))
                })
                return comprehensive_response
            
            mock_generate.side_effect = track_tool_interaction
            
            # Execute end-to-end workflow
            workflow_stages.append('data_helper_execution_start')
            result = await self.agent._execute_with_user_context(self.test_user_context)
            workflow_stages.append('data_helper_execution_complete')
            
            # Verify end-to-end workflow integration
            self.assertEqual(result, self.test_user_context)
            
            # Verify workflow stage completion
            self.assertEqual(len(workflow_stages), 4)
            self.assertIn('data_helper_execution_complete', workflow_stages)
            
            # Verify WebSocket events for workflow transparency
            websocket_events = workflow_execution_tracking['websocket_events']
            self.assertEqual(len(websocket_events), 3)  # thinking, tool_executing, tool_completed
            
            # Verify tool interaction captured workflow complexity
            tool_interactions = workflow_execution_tracking['tool_interactions']
            self.assertEqual(len(tool_interactions), 1)
            
            interaction = tool_interactions[0]
            self.assertEqual(interaction['triage_complexity'], 3)  # 3 optimization areas
            self.assertEqual(interaction['previous_results_count'], 2)  # 2 previous results
            
            # Verify metadata persistence includes workflow data
            metadata_ops = workflow_execution_tracking['metadata_persistence']
            self.assertGreater(len(metadata_ops), 0)
            
            # Find data result persistence
            data_result_ops = [op for op in metadata_ops if op['key'] == 'data_result']
            self.assertEqual(len(data_result_ops), 1)
            self.assertTrue(data_result_ops[0]['has_data_request'])
        
        # Record end-to-end integration success
        self.record_metric("workflow_stages_completed", len(workflow_stages))
        self.record_metric("workflow_complexity_score", 
                          len(enhanced_triage_result['identified_optimization_areas']) + 
                          len(previous_optimization_results))
        self.record_metric("end_to_end_integration_success", True)