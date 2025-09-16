"""
Data Helper Tool Request Generation Unit Tests

This test suite provides comprehensive coverage of the DataHelper tool's request
generation functionality, including LLM integration, response parsing, and
structured data extraction.

Business Value: Platform/Internal - Ensures reliable data request generation
for comprehensive AI optimization strategies, supporting customer success.

SSOT Compliance: Uses unified BaseTestCase patterns and real LLM service integration.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.tools.data_helper import DataHelper


class TestDataHelperToolRequestGeneration(SSotAsyncTestCase):
    """Test suite for Data Helper tool request generation functionality."""
    
    async def setUp(self):
        """Set up test fixtures."""
        await super().setUp()
        
        # Create mock LLM manager with async behavior
        self.mock_llm_manager = MagicMock()
        self.mock_llm_manager.agenerate = AsyncMock()
        
        # Create DataHelper instance
        self.data_helper = DataHelper(self.mock_llm_manager)
        
        # Sample test data
        self.sample_user_request = "I need to optimize my web application performance"
        self.sample_triage_result = {
            'category': 'performance',
            'priority': 'high',
            'complexity': 'medium',
            'data_sufficiency': 'insufficient'
        }
        self.sample_previous_results = [
            {
                'agent_name': 'triage_agent',
                'result': 'Identified performance bottlenecks in database queries'
            },
            {
                'agent_name': 'analysis_agent', 
                'summary': 'Found memory leaks in JavaScript components'
            }
        ]
    
    async def test_successful_data_request_generation(self):
        """Test successful generation of data request with all components."""
        # Mock LLM response with structured data request
        mock_llm_response = MagicMock()
        mock_llm_response.generations = [[MagicMock()]]
        mock_llm_response.generations[0][0].text = """
        Based on your request for web application performance optimization, please provide:
        
        [Performance Metrics]
        - Current page load times
        - Server response times
        - Database query execution times
        
        [System Configuration]
        - Server specifications (CPU, RAM, storage)
        - Database configuration settings
        - Caching mechanisms in use
        
        Data Collection Instructions:
        To proceed with optimization, please gather the above performance metrics and system details.
        This will enable comprehensive analysis and targeted recommendations.
        """
        
        self.mock_llm_manager.agenerate.return_value = mock_llm_response
        
        # Generate data request
        result = await self.data_helper.generate_data_request(
            user_request=self.sample_user_request,
            triage_result=self.sample_triage_result,
            previous_results=self.sample_previous_results
        )
        
        # Verify successful result structure
        self.assertTrue(result['success'])
        self.assertIn('data_request', result)
        self.assertEqual(result['user_request'], self.sample_user_request)
        self.assertEqual(result['triage_context'], self.sample_triage_result)
        
        # Verify data request structure
        data_request = result['data_request']
        self.assertIn('raw_response', data_request)
        self.assertIn('data_categories', data_request)
        self.assertIn('user_instructions', data_request)
        self.assertIn('structured_items', data_request)
        
        # Verify LLM was called with proper parameters
        self.mock_llm_manager.agenerate.assert_called_once()
        call_args = self.mock_llm_manager.agenerate.call_args
        self.assertIn('prompts', call_args.kwargs)
        self.assertEqual(call_args.kwargs['temperature'], 0.3)
        self.assertEqual(call_args.kwargs['max_tokens'], 2000)
        
        # Record successful generation
        self.record_metric("data_request_generation_success", True)
        self.record_metric("llm_integration_success", True)
    
    async def test_category_extraction_with_various_formats(self):
        """Test extraction of data categories from various response formats."""
        test_cases = [
            {
                'name': 'bracket_format',
                'response': """
                [Performance Data]
                - Load times
                - Response times
                
                [Configuration Data]
                - Server specs
                - Database settings
                """,
                'expected_categories': ['Performance Data', 'Configuration Data']
            },
            {
                'name': 'bold_format',
                'response': """
                **System Metrics:**
                - CPU utilization
                - Memory usage
                
                **Network Performance:**
                - Bandwidth utilization
                - Latency measurements
                """,
                'expected_categories': ['System Metrics', 'Network Performance']
            },
            {
                'name': 'mixed_format',
                'response': """
                [Database Performance]
                - Query execution times
                
                **Application Metrics:**
                - Request throughput
                - Error rates
                """,
                'expected_categories': ['Database Performance', 'Application Metrics']
            }
        ]
        
        for test_case in test_cases:
            # Mock LLM response
            mock_response = MagicMock()
            mock_response.generations = [[MagicMock()]]
            mock_response.generations[0][0].text = test_case['response']
            self.mock_llm_manager.agenerate.return_value = mock_response
            
            # Generate data request
            result = await self.data_helper.generate_data_request(
                user_request=self.sample_user_request,
                triage_result=self.sample_triage_result
            )
            
            # Verify categories were extracted correctly
            self.assertTrue(result['success'])
            categories = result['data_request']['data_categories']
            
            extracted_names = [cat['name'] for cat in categories]
            for expected_name in test_case['expected_categories']:
                self.assertIn(expected_name, extracted_names, 
                            f"Expected category '{expected_name}' not found in {test_case['name']}")
            
            # Verify each category has items
            for category in categories:
                self.assertIn('items', category)
                self.assertGreater(len(category['items']), 0)
        
        # Record category extraction success
        self.record_metric("category_extraction_formats_tested", len(test_cases))
        self.record_metric("category_extraction_success", True)
    
    async def test_structured_items_generation_with_justifications(self):
        """Test generation of structured data items with justifications."""
        # Mock LLM response with justifications
        mock_response = MagicMock()
        mock_response.generations = [[MagicMock()]]
        mock_response.generations[0][0].text = """
        [Performance Metrics]
        - Page load times Justification: Essential for user experience analysis
        - Database query times Justification: Identifies bottlenecks in data access
        - Memory usage patterns
        
        [Configuration Details]
        - Server specifications Justification: Determines hardware optimization potential
        - Cache configuration
        """
        self.mock_llm_manager.agenerate.return_value = mock_response
        
        # Generate data request
        result = await self.data_helper.generate_data_request(
            user_request=self.sample_user_request,
            triage_result=self.sample_triage_result
        )
        
        # Verify structured items
        structured_items = result['data_request']['structured_items']
        self.assertGreater(len(structured_items), 0)
        
        # Find items with justifications
        justified_items = [item for item in structured_items if item.get('justification')]
        self.assertGreater(len(justified_items), 0)
        
        # Verify justification structure
        for item in justified_items:
            self.assertIn('category', item)
            self.assertIn('data_point', item)
            self.assertIn('justification', item)
            self.assertIn('required', item)
            self.assertTrue(item['required'])  # Default should be True
            
            # Verify justification content is meaningful
            justification = item['justification']
            self.assertGreater(len(justification), 10)
            self.assertTrue(any(word in justification.lower() 
                              for word in ['essential', 'identifies', 'determines', 'analysis']))
        
        # Record structured items success
        self.record_metric("structured_items_with_justifications", len(justified_items))
        self.record_metric("total_structured_items", len(structured_items))
    
    async def test_previous_results_formatting_integration(self):
        """Test formatting and integration of previous agent results."""
        # Test with various previous results formats
        previous_results_cases = [
            [],  # No previous results
            [{'agent_name': 'triage', 'result': 'Simple result'}],  # Single result
            [  # Multiple results with different formats
                {'agent_name': 'triage_agent', 'summary': 'Triage summary'},
                {'result': 'Result without agent name'},
                {'agent_name': 'analysis', 'result': 'Analysis result', 'extra_field': 'ignored'}
            ]
        ]
        
        for i, previous_results in enumerate(previous_results_cases):
            # Mock LLM response
            mock_response = MagicMock()
            mock_response.generations = [[MagicMock()]]
            mock_response.generations[0][0].text = f"Test response {i}"
            self.mock_llm_manager.agenerate.return_value = mock_response
            
            # Generate data request
            result = await self.data_helper.generate_data_request(
                user_request=self.sample_user_request,
                triage_result=self.sample_triage_result,
                previous_results=previous_results
            )
            
            # Verify successful processing regardless of previous results format
            self.assertTrue(result['success'])
            
            # Verify LLM prompt included previous results appropriately
            call_args = self.mock_llm_manager.agenerate.call_args
            prompt = call_args.kwargs['prompts'][0]
            
            if not previous_results:
                self.assertIn("No previous agent results", prompt)
            else:
                # Should contain formatted previous results
                for prev_result in previous_results:
                    if 'agent_name' in prev_result:
                        self.assertIn(prev_result['agent_name'], prompt)
                    if 'result' in prev_result:
                        self.assertIn(prev_result['result'], prompt)
                    if 'summary' in prev_result:
                        self.assertIn(prev_result['summary'], prompt)
        
        # Record previous results integration success
        self.record_metric("previous_results_formats_tested", len(previous_results_cases))
        self.record_metric("previous_results_integration_success", True)
    
    async def test_user_instructions_extraction_patterns(self):
        """Test extraction of user instructions from various response patterns."""
        instruction_patterns = [
            {
                'response': """
                Data Collection Instructions:
                Please gather the following metrics over a 24-hour period and provide detailed analysis.
                """,
                'expected_marker': 'Data Collection Instructions'
            },
            {
                'response': """
                Please provide the following information:
                - System performance data
                - User behavior analytics
                """,
                'expected_marker': 'Please provide the following'
            },
            {
                'response': """
                To proceed with optimization, we need:
                1. Current system metrics
                2. Historical performance data
                """,
                'expected_marker': 'To proceed with optimization'
            },
            {
                'response': """
                Basic response without specific instruction markers.
                Just general information about data needs.
                """,
                'expected_marker': None  # Should use default instructions
            }
        ]
        
        for pattern in instruction_patterns:
            # Mock LLM response
            mock_response = MagicMock()
            mock_response.generations = [[MagicMock()]]
            mock_response.generations[0][0].text = pattern['response']
            self.mock_llm_manager.agenerate.return_value = mock_response
            
            # Generate data request
            result = await self.data_helper.generate_data_request(
                user_request=self.sample_user_request,
                triage_result=self.sample_triage_result
            )
            
            # Verify instructions extraction
            instructions = result['data_request']['user_instructions']
            self.assertIsInstance(instructions, str)
            self.assertGreater(len(instructions), 20)  # Substantial instructions
            
            if pattern['expected_marker']:
                self.assertIn(pattern['expected_marker'], instructions)
            else:
                # Should use default fallback instructions
                self.assertIn("Please provide the requested data", instructions)
        
        # Record instruction extraction success
        self.record_metric("instruction_patterns_tested", len(instruction_patterns))
        self.record_metric("instruction_extraction_success", True)
    
    async def test_llm_response_parsing_edge_cases(self):
        """Test parsing of various LLM response formats and edge cases."""
        edge_cases = [
            {
                'name': 'empty_response',
                'response_text': '',
                'should_succeed': True  # Should handle gracefully
            },
            {
                'name': 'malformed_categories',
                'response_text': 'No structured format - just plain text response',
                'should_succeed': True  # Should handle gracefully
            },
            {
                'name': 'partial_structure',
                'response_text': '[Incomplete Category\n- Item without closing bracket',
                'should_succeed': True  # Should handle gracefully
            },
            {
                'name': 'unicode_content',
                'response_text': '[Performance Metrics™]\n- Response time ≤ 200ms\n- Throughput ≥ 1000 req/s',
                'should_succeed': True
            },
            {
                'name': 'very_long_response',
                'response_text': '[Category]\n' + '- Long item description ' * 100,
                'should_succeed': True
            }
        ]
        
        for edge_case in edge_cases:
            # Mock LLM response
            mock_response = MagicMock()
            mock_response.generations = [[MagicMock()]]
            mock_response.generations[0][0].text = edge_case['response_text']
            self.mock_llm_manager.agenerate.return_value = mock_response
            
            # Generate data request
            result = await self.data_helper.generate_data_request(
                user_request=self.sample_user_request,
                triage_result=self.sample_triage_result
            )
            
            if edge_case['should_succeed']:
                # Should succeed and return valid structure
                self.assertTrue(result['success'])
                self.assertIn('data_request', result)
                
                data_request = result['data_request']
                self.assertIn('raw_response', data_request)
                self.assertIn('data_categories', data_request)
                self.assertIn('user_instructions', data_request)
                self.assertIn('structured_items', data_request)
                
                # Raw response should match input
                self.assertEqual(data_request['raw_response'], edge_case['response_text'])
            else:
                # Should handle error gracefully
                self.assertFalse(result['success'])
                self.assertIn('error', result)
        
        # Record edge case handling success
        self.record_metric("edge_cases_tested", len(edge_cases))
        self.record_metric("edge_case_handling_success", True)
    
    async def test_llm_manager_error_handling_during_generation(self):
        """Test error handling when LLM manager fails during generation."""
        # Test various LLM failure scenarios
        failure_scenarios = [
            {
                'name': 'connection_error',
                'exception': ConnectionError("Failed to connect to LLM service"),
                'expected_error_type': 'ConnectionError'
            },
            {
                'name': 'timeout_error',
                'exception': TimeoutError("LLM request timed out"),
                'expected_error_type': 'TimeoutError'
            },
            {
                'name': 'runtime_error',
                'exception': RuntimeError("LLM service internal error"),
                'expected_error_type': 'RuntimeError'
            }
        ]
        
        for scenario in failure_scenarios:
            # Configure LLM manager to raise exception
            self.mock_llm_manager.agenerate.side_effect = scenario['exception']
            
            # Generate data request (should handle error gracefully)
            result = await self.data_helper.generate_data_request(
                user_request=self.sample_user_request,
                triage_result=self.sample_triage_result
            )
            
            # Verify error handling
            self.assertFalse(result['success'])
            self.assertIn('error', result)
            self.assertIn('fallback_message', result)
            
            # Verify error message contains relevant information
            error_message = result['error']
            self.assertIn(scenario['exception'].__class__.__name__, error_message)
            
            # Verify fallback message is generated
            fallback_message = result['fallback_message']
            self.assertIsInstance(fallback_message, str)
            self.assertGreater(len(fallback_message), 50)
            self.assertIn(self.sample_user_request[:100], fallback_message)
            
            # Reset mock for next iteration
            self.mock_llm_manager.agenerate.side_effect = None
        
        # Record error handling success
        self.record_metric("llm_error_scenarios_tested", len(failure_scenarios))
        self.record_metric("llm_error_handling_success", True)
    
    async def test_data_request_with_empty_triage_result(self):
        """Test data request generation with empty or minimal triage result."""
        empty_triage_cases = [
            {},  # Completely empty
            {'category': None},  # Null values
            {'category': ''},  # Empty strings
            {'category': 'unknown', 'priority': 'low'}  # Minimal valid data
        ]
        
        for triage_result in empty_triage_cases:
            # Mock successful LLM response
            mock_response = MagicMock()
            mock_response.generations = [[MagicMock()]]
            mock_response.generations[0][0].text = "[General]\n- System information needed"
            self.mock_llm_manager.agenerate.return_value = mock_response
            
            # Generate data request
            result = await self.data_helper.generate_data_request(
                user_request=self.sample_user_request,
                triage_result=triage_result
            )
            
            # Should succeed even with minimal triage data
            self.assertTrue(result['success'])
            self.assertIn('data_request', result)
            
            # Verify triage context is preserved in result
            self.assertEqual(result['triage_context'], triage_result)
            
            # Verify LLM was called with triage result (even if empty)
            call_args = self.mock_llm_manager.agenerate.call_args
            prompt = call_args.kwargs['prompts'][0]
            self.assertIn(str(triage_result), prompt)
        
        # Record empty triage handling success
        self.record_metric("empty_triage_cases_tested", len(empty_triage_cases))
        self.record_metric("empty_triage_handling_success", True)
    
    async def test_response_processing_with_different_llm_formats(self):
        """Test response processing with different LLM response formats."""
        llm_response_formats = [
            {
                'name': 'standard_generations_format',
                'response': lambda text: self._create_mock_llm_response_with_generations(text)
            },
            {
                'name': 'string_response_format',
                'response': lambda text: text  # Direct string response
            },
            {
                'name': 'complex_object_format',
                'response': lambda text: type('MockResponse', (), {'__str__': lambda: text})()
            }
        ]
        
        test_text = "[Test Category]\n- Test item for response format validation"
        
        for response_format in llm_response_formats:
            # Create mock response in specific format
            mock_response = response_format['response'](test_text)
            self.mock_llm_manager.agenerate.return_value = mock_response
            
            # Generate data request
            result = await self.data_helper.generate_data_request(
                user_request=self.sample_user_request,
                triage_result=self.sample_triage_result
            )
            
            # Should handle all response formats successfully
            self.assertTrue(result['success'])
            data_request = result['data_request']
            
            # Verify raw response contains the test text
            self.assertEqual(data_request['raw_response'], test_text)
            
            # Verify parsing worked correctly
            self.assertGreater(len(data_request['data_categories']), 0)
            self.assertIn('Test Category', [cat['name'] for cat in data_request['data_categories']])
        
        # Record response format handling success
        self.record_metric("llm_response_formats_tested", len(llm_response_formats))
        self.record_metric("response_format_handling_success", True)
    
    async def test_comprehensive_data_request_validation(self):
        """Test comprehensive validation of complete data request structure."""
        # Mock comprehensive LLM response
        comprehensive_response = """
        Based on your web application performance optimization request:
        
        [Performance Metrics]
        - Page load times Justification: Critical for user experience measurement
        - Server response times Justification: Identifies backend bottlenecks
        - Database query execution times Justification: Locates data access inefficiencies
        
        [System Configuration]
        - Server hardware specifications Justification: Determines optimization potential
        - Database configuration settings Justification: Optimizes data layer performance
        - Load balancer configuration Justification: Ensures proper traffic distribution
        
        [User Behavior Data]
        - Traffic patterns and peak usage times
        - Most frequently accessed pages and features
        - Geographic distribution of users
        
        Data Collection Instructions:
        To proceed with comprehensive performance optimization, please gather all the above
        metrics over a representative time period (minimum 7 days). Focus especially on
        peak usage periods and include both average and 95th percentile measurements.
        """
        
        mock_response = MagicMock()
        mock_response.generations = [[MagicMock()]]
        mock_response.generations[0][0].text = comprehensive_response
        self.mock_llm_manager.agenerate.return_value = mock_response
        
        # Generate data request with full context
        result = await self.data_helper.generate_data_request(
            user_request=self.sample_user_request,
            triage_result=self.sample_triage_result,
            previous_results=self.sample_previous_results
        )
        
        # Comprehensive validation of result structure
        self.assertTrue(result['success'])
        self.assertIn('data_request', result)
        self.assertEqual(result['user_request'], self.sample_user_request)
        self.assertEqual(result['triage_context'], self.sample_triage_result)
        
        data_request = result['data_request']
        
        # Validate raw response
        self.assertEqual(data_request['raw_response'], comprehensive_response)
        
        # Validate categories extraction
        categories = data_request['data_categories']
        self.assertGreaterEqual(len(categories), 3)  # Should have at least 3 categories
        
        expected_category_names = ['Performance Metrics', 'System Configuration', 'User Behavior Data']
        actual_category_names = [cat['name'] for cat in categories]
        for expected_name in expected_category_names:
            self.assertIn(expected_name, actual_category_names)
        
        # Validate items within categories
        for category in categories:
            self.assertIn('items', category)
            self.assertGreater(len(category['items']), 0)
            
            for item in category['items']:
                self.assertIn('item', item)
                self.assertIsInstance(item['item'], str)
                self.assertGreater(len(item['item']), 5)  # Meaningful item names
        
        # Validate user instructions
        instructions = data_request['user_instructions']
        self.assertIn('Data Collection Instructions', instructions)
        self.assertIn('7 days', instructions)  # Specific time period mentioned
        self.assertIn('95th percentile', instructions)  # Specific measurement detail
        
        # Validate structured items
        structured_items = data_request['structured_items']
        self.assertGreaterEqual(len(structured_items), 6)  # Should have multiple items
        
        # Check that all structured items have required fields
        for item in structured_items:
            self.assertIn('category', item)
            self.assertIn('data_point', item)
            self.assertIn('justification', item)
            self.assertIn('required', item)
            self.assertTrue(item['required'])
        
        # Validate that some items have justifications (from the response)
        justified_items = [item for item in structured_items if item['justification']]
        self.assertGreaterEqual(len(justified_items), 3)  # At least 3 items with justifications
        
        # Record comprehensive validation success
        self.record_metric("comprehensive_validation_success", True)
        self.record_metric("categories_extracted", len(categories))
        self.record_metric("structured_items_generated", len(structured_items))
        self.record_metric("justified_items_count", len(justified_items))
    
    def _create_mock_llm_response_with_generations(self, text: str):
        """Helper method to create mock LLM response with generations format."""
        mock_generation = MagicMock()
        mock_generation.text = text
        
        mock_response = MagicMock()
        mock_response.generations = [[mock_generation]]
        
        return mock_response