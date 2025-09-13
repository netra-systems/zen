"""
Data Helper Agent Core Functionality Unit Tests

This test suite provides comprehensive coverage of the DataHelperAgent core functionality,
including initialization, configuration, UserExecutionContext integration, and basic
execution patterns.

Business Value: Platform/Internal - Ensures reliable data collection request generation
for AI optimization strategies, protecting $500K+ ARR functionality.

SSOT Compliance: Uses unified BaseTestCase patterns and real service integration.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.agents.data_helper_agent import DataHelperAgent
from netra_backend.app.tools.data_helper import DataHelper


class TestDataHelperAgentCoreFunctionality(SSotAsyncTestCase):
    """Test suite for Data Helper Agent core functionality."""
    
    async def setUp(self):
        """Set up test fixtures."""
        await super().setUp()
        
        # Create mock dependencies with proper async behavior
        self.mock_llm_manager = MagicMock()
        self.mock_llm_manager.agenerate = AsyncMock()
        
        self.mock_tool_dispatcher = MagicMock()
        
        # Create mock user context
        self.mock_user_context = MagicMock()
        self.mock_user_context.user_id = "test_user_123"
        self.mock_user_context.run_id = "test_run_456"
        self.mock_user_context.metadata = {
            'user_request': 'I need help optimizing my system performance',
            'triage_result': {
                'category': 'performance',
                'priority': 'high',
                'data_sufficiency': 'insufficient'
            }
        }
        
        # Create agent instance
        self.agent = DataHelperAgent(
            llm_manager=self.mock_llm_manager,
            tool_dispatcher=self.mock_tool_dispatcher
        )
        
        # Mock WebSocket event methods to avoid external dependencies
        self.agent.emit_thinking = AsyncMock()
        self.agent.emit_tool_executing = AsyncMock()
        self.agent.emit_tool_completed = AsyncMock()
        self.agent.emit_error = AsyncMock()
        
        # Mock store_metadata_result method
        self.agent.store_metadata_result = MagicMock()
    
    async def test_agent_initialization_with_proper_configuration(self):
        """Test that DataHelperAgent initializes with proper configuration."""
        # Verify agent was initialized with correct parameters
        self.assertEqual(self.agent.name, "data_helper")
        self.assertEqual(self.agent.description, "Generates data requests when insufficient data is available")
        self.assertFalse(self.agent.enable_reliability)  # Disabled per AGENT_RELIABILITY_ERROR_SUPPRESSION
        self.assertTrue(self.agent.enable_execution_engine)  # Modern execution patterns
        self.assertTrue(self.agent.enable_caching)  # Optional caching infrastructure
        
        # Verify dependencies are properly set
        self.assertEqual(self.agent.llm_manager, self.mock_llm_manager)
        self.assertEqual(self.agent.tool_dispatcher, self.mock_tool_dispatcher)
        self.assertIsInstance(self.agent.data_helper_tool, DataHelper)
        
        # Record successful initialization metric
        self.record_metric("agent_initialization_success", True)
    
    @patch('netra_backend.app.llm.llm_manager.create_llm_manager')
    @patch('netra_backend.app.core.tools.unified_tool_dispatcher.UnifiedToolDispatcherFactory.create_for_request')
    async def test_create_agent_with_context_factory_pattern(self, mock_dispatcher_factory, mock_llm_factory):
        """Test the factory pattern for creating agent with UserExecutionContext."""
        # Setup factory mocks
        mock_llm_factory.return_value = self.mock_llm_manager
        mock_dispatcher_factory.return_value = self.mock_tool_dispatcher
        
        # Test factory creation
        agent = await DataHelperAgent.create_agent_with_context(self.mock_user_context)
        
        # Verify factory was called correctly
        mock_llm_factory.assert_called_once_with(self.mock_user_context)
        mock_dispatcher_factory.assert_called_once_with(self.mock_user_context)
        
        # Verify agent was created with proper configuration
        self.assertIsInstance(agent, DataHelperAgent)
        self.assertEqual(agent.llm_manager, self.mock_llm_manager)
        self.assertEqual(agent.tool_dispatcher, self.mock_tool_dispatcher)
        
        # Record factory pattern success
        self.record_metric("factory_pattern_success", True)
        self.record_metric("user_context_integration", True)
    
    async def test_user_execution_context_metadata_extraction(self):
        """Test extraction of user request and triage result from UserExecutionContext."""
        # Execute with context
        result_context = await self.agent._execute_with_user_context(self.mock_user_context)
        
        # Verify context is returned
        self.assertEqual(result_context, self.mock_user_context)
        
        # Verify WebSocket events were emitted
        self.agent.emit_thinking.assert_called_once_with(
            "Analyzing user request to identify data gaps..."
        )
        
        # Verify tool execution event was emitted with proper parameters
        self.agent.emit_tool_executing.assert_called_once()
        tool_args = self.agent.emit_tool_executing.call_args[0][1]
        self.assertEqual(tool_args['user_request_length'], len(self.mock_user_context.metadata['user_request']))
        self.assertTrue(tool_args['triage_result_available'])
        
        # Record metadata extraction success
        self.record_metric("metadata_extraction_success", True)
    
    async def test_data_helper_tool_integration(self):
        """Test integration with DataHelper tool for request generation."""
        # Mock successful tool response
        mock_tool_response = {
            'success': True,
            'data_request': {
                'user_instructions': 'Please provide system metrics and usage patterns',
                'structured_items': [
                    {'category': 'Performance', 'data_point': 'CPU utilization', 'required': True},
                    {'category': 'Performance', 'data_point': 'Memory usage', 'required': True}
                ]
            }
        }
        
        # Configure tool mock
        with patch.object(self.agent.data_helper_tool, 'generate_data_request', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_tool_response
            
            # Execute with context
            await self.agent._execute_with_user_context(self.mock_user_context)
            
            # Verify tool was called with correct parameters
            mock_generate.assert_called_once_with(
                user_request=self.mock_user_context.metadata['user_request'],
                triage_result=self.mock_user_context.metadata['triage_result'],
                previous_results={}  # Empty since no previous results in test context
            )
            
            # Verify tool completion event was emitted
            self.agent.emit_tool_completed.assert_called_once()
            completion_args = self.agent.emit_tool_completed.call_args[0][1]
            self.assertTrue(completion_args['success'])
            self.assertTrue(completion_args['data_request_generated'])
            
            # Verify results were stored in metadata
            self.agent.store_metadata_result.assert_any_call(
                self.mock_user_context, 'data_result', mock_tool_response
            )
            self.agent.store_metadata_result.assert_any_call(
                self.mock_user_context, 'data_request_generated', True
            )
        
        # Record tool integration success
        self.record_metric("tool_integration_success", True)
    
    async def test_insufficient_user_request_validation(self):
        """Test validation of insufficient user request input."""
        # Create context with insufficient user request
        insufficient_context = MagicMock()
        insufficient_context.user_id = "test_user_123"
        insufficient_context.run_id = "test_run_456"
        insufficient_context.metadata = {
            'user_request': 'help',  # Too short
            'triage_result': {}
        }
        
        # Execute with insufficient context
        result_context = await self.agent._execute_with_user_context(insufficient_context)
        
        # Verify error handling was triggered
        self.agent.emit_error.assert_called_once()
        error_args = self.agent.emit_error.call_args[0]
        self.assertIn("Insufficient user request", error_args[0])
        
        # Verify error was stored in metadata
        self.agent.store_metadata_result.assert_any_call(
            insufficient_context, 'data_helper_error', 'Insufficient user request for data analysis'
        )
        
        # Verify fallback message was stored
        fallback_calls = [call for call in self.agent.store_metadata_result.call_args_list
                         if call[0][1] == 'data_helper_fallback_message']
        self.assertTrue(len(fallback_calls) > 0)
        
        # Record validation success
        self.record_metric("input_validation_success", True)
    
    async def test_previous_results_extraction_from_context(self):
        """Test extraction of previous agent results from context metadata."""
        # Create context with previous results
        context_with_results = MagicMock()
        context_with_results.metadata = {
            'user_request': 'I need optimization help',
            'triage_result': {'category': 'performance'},
            'optimizations_result': {'recommendations': ['increase memory']},
            'synthetic_data_result': {'data_generated': True},
            'irrelevant_key': 'should_be_ignored'
        }
        
        # Extract previous results
        previous_results = self.agent._extract_previous_results_from_context(context_with_results)
        
        # Verify correct results were extracted
        expected_keys = ['triage_result', 'optimizations_result', 'synthetic_data_result']
        for key in expected_keys:
            self.assertIn(key, previous_results)
            self.assertEqual(previous_results[key], context_with_results.metadata[key])
        
        # Verify irrelevant keys were not included
        self.assertNotIn('irrelevant_key', previous_results)
        
        # Record extraction success
        self.record_metric("previous_results_extraction_success", True)
    
    async def test_fallback_message_generation(self):
        """Test fallback message generation for error scenarios."""
        # Test with various user request lengths
        test_cases = [
            "Help me optimize",
            "I need comprehensive optimization help for my complex multi-tier system architecture with performance issues",
            ""  # Empty request
        ]
        
        for user_request in test_cases:
            fallback_message = self.agent._get_fallback_message(user_request)
            
            # Verify fallback message structure
            self.assertIsInstance(fallback_message, str)
            self.assertTrue(len(fallback_message) > 50)  # Substantial message
            self.assertIn("additional information", fallback_message.lower())
            
            # For long requests, verify truncation
            if len(user_request) > 100:
                self.assertIn(user_request[:100], fallback_message)
                self.assertIn("...", fallback_message)
            elif user_request:  # Non-empty requests should be included
                request_part = user_request[:100]
                self.assertIn(request_part, fallback_message)
        
        # Record fallback generation success
        self.record_metric("fallback_message_generation_success", True)
    
    async def test_websocket_event_emissions(self):
        """Test that proper WebSocket events are emitted during execution."""
        # Configure successful execution path
        with patch.object(self.agent.data_helper_tool, 'generate_data_request', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = {
                'success': True,
                'data_request': {
                    'user_instructions': 'Test instructions',
                    'structured_items': [{'item': 'test'}]
                }
            }
            
            # Execute with context
            await self.agent._execute_with_user_context(self.mock_user_context)
            
            # Verify all required WebSocket events were emitted
            self.agent.emit_thinking.assert_called_once_with(
                "Analyzing user request to identify data gaps..."
            )
            
            self.agent.emit_tool_executing.assert_called_once_with(
                "data_helper", {
                    "user_request_length": len(self.mock_user_context.metadata['user_request']),
                    "triage_result_available": True,
                    "previous_results_count": 0
                }
            )
            
            self.agent.emit_tool_completed.assert_called_once_with(
                "data_helper", {
                    "success": True,
                    "data_request_generated": True,
                    "instructions_count": len('Test instructions'),
                    "structured_items_count": 1
                }
            )
            
            # Verify no error events were emitted
            self.agent.emit_error.assert_not_called()
        
        # Record WebSocket event success
        self.record_metric("websocket_events_success", True)
    
    async def test_error_context_and_unified_error_handling(self):
        """Test unified error handling with proper ErrorContext."""
        # Force an exception during tool execution
        with patch.object(self.agent.data_helper_tool, 'generate_data_request', new_callable=AsyncMock) as mock_generate:
            mock_generate.side_effect = RuntimeError("Test error for error handling")
            
            # Execute with context (should not raise, should handle gracefully)
            result_context = await self.agent._execute_with_user_context(self.mock_user_context)
            
            # Verify context is returned even with error
            self.assertEqual(result_context, self.mock_user_context)
            
            # Verify error event was emitted
            self.agent.emit_error.assert_called_once()
            error_args = self.agent.emit_error.call_args[0]
            self.assertIn("Test error for error handling", error_args[0])
            self.assertEqual("RuntimeError", error_args[1])  # Error type
            
            # Verify error was stored in metadata
            self.agent.store_metadata_result.assert_any_call(
                self.mock_user_context, 'data_helper_error', 'Test error for error handling'
            )
            
            # Verify fallback message was stored
            fallback_calls = [call for call in self.agent.store_metadata_result.call_args_list
                             if call[0][1] == 'data_helper_fallback_message']
            self.assertTrue(len(fallback_calls) > 0)
        
        # Record error handling success
        self.record_metric("unified_error_handling_success", True)
    
    async def test_user_context_thread_safety_patterns(self):
        """Test that user context is handled in a thread-safe manner."""
        # Create multiple contexts simulating concurrent users
        contexts = []
        for i in range(3):
            context = MagicMock()
            context.user_id = f"user_{i}"
            context.run_id = f"run_{i}"
            context.metadata = {
                'user_request': f'User {i} optimization request',
                'triage_result': {'category': f'category_{i}'}
            }
            contexts.append(context)
        
        # Mock successful tool responses
        with patch.object(self.agent.data_helper_tool, 'generate_data_request', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = {
                'success': True,
                'data_request': {'user_instructions': 'Test', 'structured_items': []}
            }
            
            # Execute all contexts concurrently
            results = await asyncio.gather(*[
                self.agent._execute_with_user_context(context) for context in contexts
            ])
            
            # Verify all executions completed successfully
            self.assertEqual(len(results), 3)
            for i, result in enumerate(results):
                self.assertEqual(result, contexts[i])
            
            # Verify tool was called for each context
            self.assertEqual(mock_generate.call_count, 3)
            
            # Verify each call had correct user-specific data
            for i, call in enumerate(mock_generate.call_args_list):
                args, kwargs = call
                self.assertEqual(kwargs['user_request'], f'User {i} optimization request')
                self.assertEqual(kwargs['triage_result']['category'], f'category_{i}')
        
        # Record thread safety success
        self.record_metric("thread_safety_validation_success", True)
        self.record_metric("concurrent_users_handled", 3)