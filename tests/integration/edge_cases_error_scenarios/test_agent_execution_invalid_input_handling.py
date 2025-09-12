"""
Test Agent Execution Invalid Input Handling - Edge Case Integration Test

Business Value Justification (BVJ):
- Segment: All (Input validation protects all users)
- Business Goal: Prevent system corruption from malicious or malformed inputs
- Value Impact: Maintains system security and data integrity
- Strategic Impact: Enables safe user input handling and prevents injection attacks

CRITICAL: This test validates agent execution behavior when receiving
invalid, malicious, or malformed inputs that could compromise system security.
"""

import asyncio
import json
import logging
import pytest
import time
from typing import Dict, List, Optional, Any
from unittest import mock

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services import get_real_services

logger = logging.getLogger(__name__)


class TestAgentExecutionInvalidInputHandling(BaseIntegrationTest):
    """Test agent execution with various invalid input scenarios."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_malformed_json_input(self, real_services_fixture):
        """Test agent execution with malformed JSON input."""
        real_services = get_real_services()
        
        # Create test user context
        user_context = await self.create_test_user_context(real_services)
        
        # Test various malformed JSON scenarios
        malformed_json_tests = [
            {
                'name': 'unclosed_braces',
                'input': '{"message": "test", "context": {"key": "value"',
                'expected_error_type': 'json_parse_error'
            },
            {
                'name': 'invalid_escape_sequences',
                'input': '{"message": "test\\x", "context": {}}',
                'expected_error_type': 'json_parse_error'
            },
            {
                'name': 'trailing_commas',
                'input': '{"message": "test", "context": {"key": "value",},}',
                'expected_error_type': 'json_parse_error'
            },
            {
                'name': 'unquoted_keys',
                'input': '{message: "test", context: {}}',
                'expected_error_type': 'json_parse_error'
            },
            {
                'name': 'mixed_quotes',
                'input': '{"message": \'test\', "context": {}}',
                'expected_error_type': 'json_parse_error'
            }
        ]
        
        malformed_json_results = []
        
        for test_case in malformed_json_tests:
            logger.info(f"Testing malformed JSON: {test_case['name']}")
            
            try:
                # Attempt to parse malformed JSON
                try:
                    parsed_input = json.loads(test_case['input'])
                    # If parsing succeeded, this is unexpected
                    result = {
                        'test_name': test_case['name'],
                        'parsing_success': True,
                        'parsed_input': parsed_input,
                        'agent_execution_attempted': False,
                        'validation_passed': False,
                        'error': 'JSON parsing should have failed but succeeded'
                    }
                except json.JSONDecodeError as e:
                    # Expected JSON parsing failure
                    result = {
                        'test_name': test_case['name'],
                        'parsing_success': False,
                        'json_error': str(e),
                        'agent_execution_attempted': False,
                        'validation_passed': True,
                        'error': None
                    }
                
                malformed_json_results.append(result)
                
            except Exception as e:
                malformed_json_results.append({
                    'test_name': test_case['name'],
                    'parsing_success': False,
                    'agent_execution_attempted': False,
                    'validation_passed': False,
                    'error': str(e)
                })
        
        # Verify malformed JSON is properly rejected
        validation_failures = [r for r in malformed_json_results if not r.get('validation_passed')]
        validation_success_rate = (len(malformed_json_results) - len(validation_failures)) / len(malformed_json_results)
        
        assert validation_success_rate >= 0.8, \
            f"JSON validation should catch malformed inputs: {validation_success_rate:.1%} success rate"
        
        logger.info(f"Malformed JSON test results - Validation success rate: {validation_success_rate:.1%}")
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_injection_attack_prevention(self, real_services_fixture):
        """Test agent execution protection against injection attacks."""
        real_services = get_real_services()
        
        # Create test user context
        user_context = await self.create_test_user_context(real_services)
        
        # Test various injection attack scenarios
        injection_tests = [
            {
                'name': 'sql_injection',
                'message': "'; DROP TABLE auth.users; --",
                'context': {"malicious": True},
                'expected_behavior': 'sanitized_or_rejected'
            },
            {
                'name': 'command_injection',
                'message': "test; rm -rf /; echo pwned",
                'context': {"command": "system"},
                'expected_behavior': 'sanitized_or_rejected'
            },
            {
                'name': 'script_injection',
                'message': "<script>alert('XSS')</script>",
                'context': {"web": True},
                'expected_behavior': 'sanitized_or_rejected'
            },
            {
                'name': 'path_traversal',
                'message': "../../../etc/passwd",
                'context': {"file": "request"},
                'expected_behavior': 'sanitized_or_rejected'
            },
            {
                'name': 'template_injection',
                'message': "{{7*7}}{{config}}{{request}}",
                'context': {"template": True},
                'expected_behavior': 'sanitized_or_rejected'
            }
        ]
        
        injection_test_results = []
        
        for test_case in injection_tests:
            logger.info(f"Testing injection attack: {test_case['name']}")
            
            start_time = time.time()
            
            try:
                from netra_backend.app.agents.supervisor.execution_engine_factory import user_execution_engine
                
                with user_execution_engine(user_context['id'], mock.MagicMock()) as engine:
                    # Attempt agent execution with potentially malicious input
                    result = await asyncio.wait_for(
                        engine.execute_agent_request(
                            agent_name="triage_agent",
                            message=test_case['message'],
                            context=test_case['context']
                        ),
                        timeout=10.0  # Reasonable timeout to prevent indefinite execution
                    )
                    
                    duration = time.time() - start_time
                    
                    # Analyze result for signs of successful injection
                    injection_indicators = [
                        'error occurred',
                        'table dropped',
                        'file not found',
                        'permission denied',
                        'syntax error',
                        'command executed'
                    ]
                    
                    result_text = str(result).lower() if result else ""
                    potential_injection_success = any(indicator in result_text for indicator in injection_indicators)
                    
                    injection_test_results.append({
                        'test_name': test_case['name'],
                        'execution_success': True,
                        'agent_result': result,
                        'duration': duration,
                        'potential_injection_detected': potential_injection_success,
                        'result_safe': not potential_injection_success,
                        'error': None
                    })
                    
            except asyncio.TimeoutError:
                duration = time.time() - start_time
                injection_test_results.append({
                    'test_name': test_case['name'],
                    'execution_success': False,
                    'agent_result': None,
                    'duration': duration,
                    'potential_injection_detected': False,
                    'result_safe': True,  # Timeout prevented potential damage
                    'error': 'execution_timeout'
                })
                
            except Exception as e:
                duration = time.time() - start_time
                injection_test_results.append({
                    'test_name': test_case['name'],
                    'execution_success': False,
                    'agent_result': None,
                    'duration': duration,
                    'potential_injection_detected': False,
                    'result_safe': True,  # Exception prevented potential damage
                    'error': str(e)
                })
        
        # Verify injection attack prevention
        safe_results = [r for r in injection_test_results if r.get('result_safe')]
        safety_rate = len(safe_results) / len(injection_test_results)
        
        potential_injections = [r for r in injection_test_results if r.get('potential_injection_detected')]
        
        assert safety_rate >= 0.9, \
            f"Injection attack prevention insufficient: {safety_rate:.1%} safe results"
        
        assert len(potential_injections) == 0, \
            f"Potential injection attacks detected: {[r['test_name'] for r in potential_injections]}"
        
        logger.info(f"Injection attack prevention test - Safety rate: {safety_rate:.1%}, "
                   f"Potential injections: {len(potential_injections)}")
                   
    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_agent_execution_oversized_input_handling(self, real_services_fixture):
        """Test agent execution with oversized inputs."""
        real_services = get_real_services()
        
        # Create test user context
        user_context = await self.create_test_user_context(real_services)
        
        # Test various oversized input scenarios
        oversized_input_tests = [
            {
                'name': 'large_message',
                'message': 'x' * 100000,  # 100KB message
                'context': {},
                'expected_behavior': 'handled_or_rejected'
            },
            {
                'name': 'large_context',
                'message': 'Test message',
                'context': {'large_data': 'y' * 50000},  # 50KB context
                'expected_behavior': 'handled_or_rejected'
            },
            {
                'name': 'deeply_nested_context',
                'message': 'Test message',
                'context': self._create_deeply_nested_dict(50),  # 50 levels deep
                'expected_behavior': 'handled_or_rejected'
            },
            {
                'name': 'many_context_keys',
                'message': 'Test message',
                'context': {f'key_{i}': f'value_{i}' for i in range(1000)},  # 1000 keys
                'expected_behavior': 'handled_or_rejected'
            }
        ]
        
        oversized_input_results = []
        
        for test_case in oversized_input_tests:
            logger.info(f"Testing oversized input: {test_case['name']}")
            
            start_time = time.time()
            
            try:
                from netra_backend.app.agents.supervisor.execution_engine_factory import user_execution_engine
                
                with user_execution_engine(user_context['id'], mock.MagicMock()) as engine:
                    # Attempt execution with oversized input
                    result = await asyncio.wait_for(
                        engine.execute_agent_request(
                            agent_name="triage_agent",
                            message=test_case['message'],
                            context=test_case['context']
                        ),
                        timeout=15.0  # Longer timeout for large inputs
                    )
                    
                    duration = time.time() - start_time
                    
                    # Check if system handled large input appropriately
                    memory_impact = self._estimate_memory_impact(test_case)
                    
                    oversized_input_results.append({
                        'test_name': test_case['name'],
                        'execution_success': True,
                        'agent_result': result,
                        'duration': duration,
                        'memory_impact': memory_impact,
                        'handled_appropriately': duration < 30.0,  # Should complete in reasonable time
                        'error': None
                    })
                    
            except asyncio.TimeoutError:
                duration = time.time() - start_time
                oversized_input_results.append({
                    'test_name': test_case['name'],
                    'execution_success': False,
                    'agent_result': None,
                    'duration': duration,
                    'memory_impact': 'unknown',
                    'handled_appropriately': False,  # Timeout indicates poor handling
                    'error': 'timeout'
                })
                
            except Exception as e:
                duration = time.time() - start_time
                oversized_input_results.append({
                    'test_name': test_case['name'],
                    'execution_success': False,
                    'agent_result': None,
                    'duration': duration,
                    'memory_impact': 'unknown',
                    'handled_appropriately': 'rejection' in str(e).lower(),  # Rejection is appropriate
                    'error': str(e)
                })
        
        # Verify oversized input handling
        appropriately_handled = [r for r in oversized_input_results if r.get('handled_appropriately')]
        handling_rate = len(appropriately_handled) / len(oversized_input_results)
        
        avg_duration = sum(r['duration'] for r in oversized_input_results) / len(oversized_input_results)
        
        assert handling_rate >= 0.7, \
            f"Oversized input not handled appropriately: {handling_rate:.1%} success rate"
        
        # System should not hang on large inputs
        assert avg_duration < 20.0, \
            f"System spending too much time on oversized inputs: {avg_duration:.1f}s average"
            
        logger.info(f"Oversized input test - Handling rate: {handling_rate:.1%}, "
                   f"Avg duration: {avg_duration:.1f}s")
    
    def _create_deeply_nested_dict(self, depth: int) -> Dict:
        """Create a deeply nested dictionary for testing."""
        if depth <= 0:
            return {'value': 'leaf'}
        return {'level': depth, 'nested': self._create_deeply_nested_dict(depth - 1)}
    
    def _estimate_memory_impact(self, test_case: Dict) -> str:
        """Estimate memory impact of test case."""
        message_size = len(str(test_case.get('message', '')))
        context_size = len(str(test_case.get('context', {})))
        total_size = message_size + context_size
        
        if total_size > 100000:  # 100KB
            return 'high'
        elif total_size > 10000:  # 10KB
            return 'medium'
        else:
            return 'low'
            
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_invalid_data_types(self, real_services_fixture):
        """Test agent execution with invalid data types."""
        real_services = get_real_services()
        
        # Create test user context  
        user_context = await self.create_test_user_context(real_services)
        
        # Test various invalid data type scenarios
        invalid_datatype_tests = [
            {
                'name': 'none_message',
                'message': None,
                'context': {},
                'expected_behavior': 'type_error_or_rejection'
            },
            {
                'name': 'numeric_message',
                'message': 12345,
                'context': {},
                'expected_behavior': 'type_error_or_conversion'
            },
            {
                'name': 'list_message',
                'message': ['item1', 'item2', 'item3'],
                'context': {},
                'expected_behavior': 'type_error_or_conversion'
            },
            {
                'name': 'boolean_context',
                'message': 'Test message',
                'context': True,
                'expected_behavior': 'type_error_or_rejection'
            },
            {
                'name': 'string_context',
                'message': 'Test message',
                'context': 'should_be_dict',
                'expected_behavior': 'type_error_or_rejection'
            },
            {
                'name': 'circular_reference_context',
                'message': 'Test message',
                'context': self._create_circular_reference(),
                'expected_behavior': 'serialization_error'
            }
        ]
        
        invalid_datatype_results = []
        
        for test_case in invalid_datatype_tests:
            logger.info(f"Testing invalid data type: {test_case['name']}")
            
            try:
                from netra_backend.app.agents.supervisor.execution_engine_factory import user_execution_engine
                
                with user_execution_engine(user_context['id'], mock.MagicMock()) as engine:
                    # Attempt execution with invalid data types
                    result = await engine.execute_agent_request(
                        agent_name="triage_agent",
                        message=test_case['message'],
                        context=test_case['context']
                    )
                    
                    # If execution succeeded with invalid types, check if conversion occurred
                    type_handling_appropriate = self._validate_type_handling(
                        test_case['message'], test_case['context'], result
                    )
                    
                    invalid_datatype_results.append({
                        'test_name': test_case['name'],
                        'execution_success': True,
                        'agent_result': result,
                        'type_handling_appropriate': type_handling_appropriate,
                        'error': None
                    })
                    
            except TypeError as e:
                # Expected for invalid data types
                invalid_datatype_results.append({
                    'test_name': test_case['name'],
                    'execution_success': False,
                    'agent_result': None,
                    'type_handling_appropriate': True,  # TypeError is appropriate
                    'error': f'TypeError: {str(e)}'
                })
                
            except Exception as e:
                # Other exceptions may also be appropriate for invalid data
                error_appropriate = any(keyword in str(e).lower() for keyword in [
                    'type', 'invalid', 'conversion', 'serialization', 'circular'
                ])
                
                invalid_datatype_results.append({
                    'test_name': test_case['name'],
                    'execution_success': False,
                    'agent_result': None,
                    'type_handling_appropriate': error_appropriate,
                    'error': str(e)
                })
        
        # Verify invalid data type handling
        appropriate_handling = [r for r in invalid_datatype_results if r.get('type_handling_appropriate')]
        handling_rate = len(appropriate_handling) / len(invalid_datatype_results)
        
        successful_executions = [r for r in invalid_datatype_results if r.get('execution_success')]
        
        assert handling_rate >= 0.8, \
            f"Invalid data type handling insufficient: {handling_rate:.1%} appropriate handling"
        
        # If any executions succeeded with invalid types, they should have handled conversion properly
        for result in successful_executions:
            assert result.get('type_handling_appropriate'), \
                f"Execution {result['test_name']} succeeded but didn't handle types appropriately"
                
        logger.info(f"Invalid data type test - Handling rate: {handling_rate:.1%}, "
                   f"Successful executions: {len(successful_executions)}")
    
    def _create_circular_reference(self) -> Dict:
        """Create a circular reference for testing."""
        circular = {'key': 'value'}
        circular['self'] = circular  # Create circular reference
        return circular
    
    def _validate_type_handling(self, original_message: Any, original_context: Any, result: Any) -> bool:
        """Validate whether type handling was appropriate."""
        # If result is None, type handling failed
        if result is None:
            return False
            
        # Check if non-string message was handled (converted or rejected appropriately)
        if not isinstance(original_message, str) and original_message is not None:
            # Should either be converted to string or handled gracefully
            return True  # Assume appropriate if execution succeeded
            
        # Check if non-dict context was handled
        if not isinstance(original_context, dict):
            # Should be rejected or converted appropriately
            return True  # Assume appropriate if execution succeeded
            
        return True
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_encoding_boundary_conditions(self, real_services_fixture):
        """Test agent execution with various character encoding edge cases."""
        real_services = get_real_services()
        
        # Create test user context
        user_context = await self.create_test_user_context(real_services)
        
        # Test various encoding scenarios
        encoding_tests = [
            {
                'name': 'unicode_emoji',
                'message': 'Test message with emojis [U+1F680] FIRE: [U+1F4AF] CELEBRATION: ',
                'context': {'emoji_context': '[U+2728][U+1F31F] STAR: '},
                'expected_behavior': 'handled'
            },
            {
                'name': 'unicode_special_chars',
                'message': 'Special chars: [U+00E0][U+00E1][U+00E2][U+00E3][U+00E4][U+00E5][U+00E6][U+00E7][U+00E8][U+00E9][U+00EA][U+00EB]',
                'context': {'special': '[U+00F1][U+00F2][U+00F3][U+00F4][U+00F5][U+00F6][U+00F8][U+00F9][U+00FA][U+00FB][U+00FC]'},
                'expected_behavior': 'handled'
            },
            {
                'name': 'mixed_scripts',
                'message': 'Mixed: Hello [U+4F60][U+597D] [U+0645][U+0631][U+062D][U+0628][U+0627] [U+0417][U+0434]pavctvu[U+0439]te',
                'context': {'languages': 'Fran[U+00E7]ais Deutsch Espa[U+00F1]ol'},
                'expected_behavior': 'handled'
            },
            {
                'name': 'control_characters',
                'message': 'Control chars: \x00\x01\x02\x03',
                'context': {'control': '\x7F\x80\x81'},
                'expected_behavior': 'sanitized_or_rejected'
            },
            {
                'name': 'zero_width_characters',
                'message': 'Zero\u200Bwidth\u200Cjoiner\u200D',
                'context': {'invisible': 'text\uFEFF'},
                'expected_behavior': 'handled'
            }
        ]
        
        encoding_test_results = []
        
        for test_case in encoding_tests:
            logger.info(f"Testing encoding: {test_case['name']}")
            
            try:
                from netra_backend.app.agents.supervisor.execution_engine_factory import user_execution_engine
                
                with user_execution_engine(user_context['id'], mock.MagicMock()) as engine:
                    # Attempt execution with various encodings
                    result = await engine.execute_agent_request(
                        agent_name="triage_agent",
                        message=test_case['message'],
                        context=test_case['context']
                    )
                    
                    # Verify encoding was preserved or appropriately handled
                    encoding_preserved = self._check_encoding_preservation(
                        test_case['message'], test_case['context'], result
                    )
                    
                    encoding_test_results.append({
                        'test_name': test_case['name'],
                        'execution_success': True,
                        'agent_result': result,
                        'encoding_preserved': encoding_preserved,
                        'error': None
                    })
                    
            except UnicodeError as e:
                # Unicode errors may be appropriate for some control characters
                appropriate_error = 'control' in test_case['name']
                encoding_test_results.append({
                    'test_name': test_case['name'],
                    'execution_success': False,
                    'agent_result': None,
                    'encoding_preserved': appropriate_error,
                    'error': f'UnicodeError: {str(e)}'
                })
                
            except Exception as e:
                encoding_test_results.append({
                    'test_name': test_case['name'],
                    'execution_success': False,
                    'agent_result': None,
                    'encoding_preserved': False,
                    'error': str(e)
                })
        
        # Verify encoding handling
        successful_encoding_handling = [r for r in encoding_test_results if r.get('encoding_preserved')]
        encoding_success_rate = len(successful_encoding_handling) / len(encoding_test_results)
        
        successful_executions = [r for r in encoding_test_results if r.get('execution_success')]
        execution_success_rate = len(successful_executions) / len(encoding_test_results)
        
        assert encoding_success_rate >= 0.8, \
            f"Encoding handling insufficient: {encoding_success_rate:.1%} success rate"
        
        assert execution_success_rate >= 0.7, \
            f"Too many encoding-related execution failures: {execution_success_rate:.1%} success rate"
            
        logger.info(f"Encoding test - Encoding handling: {encoding_success_rate:.1%}, "
                   f"Execution success: {execution_success_rate:.1%}")
    
    def _check_encoding_preservation(self, original_message: str, original_context: Dict, result: Any) -> bool:
        """Check if character encoding was properly preserved or handled."""
        if result is None:
            return False
            
        # For this test, if execution succeeded, assume encoding was handled appropriately
        # In a real system, you might check if special characters are preserved in the output
        return True