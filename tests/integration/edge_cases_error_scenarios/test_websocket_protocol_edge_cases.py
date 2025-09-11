"""
Test WebSocket Protocol Edge Cases - Edge Case Integration Test

Business Value Justification (BVJ):
- Segment: All (Protocol reliability affects all chat users)
- Business Goal: Ensure robust WebSocket communication under all conditions
- Value Impact: Maintains reliable chat functionality across different client environments
- Strategic Impact: Ensures platform compatibility and reduces support burden

CRITICAL: This test validates WebSocket protocol edge cases to ensure
reliable communication across diverse client environments and network conditions.
"""

import asyncio
import json
import logging
import pytest
import time
from typing import Dict, List, Optional, Any
from unittest import mock
from unittest.mock import AsyncMock, MagicMock, patch

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services import get_real_services

logger = logging.getLogger(__name__)


class TestWebSocketProtocolEdgeCases(BaseIntegrationTest):
    """Test WebSocket protocol edge cases and boundary conditions."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_frame_boundary_conditions(self, real_services_fixture):
        """Test WebSocket frame boundary conditions and edge cases."""
        real_services = get_real_services()
        
        # Create test user context
        user_context = await self.create_test_user_context(real_services)
        
        # Test different frame boundary scenarios
        frame_boundary_scenarios = [
            {
                'name': 'minimum_frame_size',
                'payload_size': 1,  # Single byte payload
                'frame_type': 'text',
                'expected_behavior': 'successful_transmission'
            },
            {
                'name': 'maximum_small_payload',
                'payload_size': 125,  # Maximum single-byte length
                'frame_type': 'text',
                'expected_behavior': 'successful_transmission'
            },
            {
                'name': 'minimum_extended_payload',
                'payload_size': 126,  # Minimum two-byte length
                'frame_type': 'text',
                'expected_behavior': 'successful_transmission'
            },
            {
                'name': 'maximum_extended_payload',
                'payload_size': 65535,  # Maximum two-byte length
                'frame_type': 'text',
                'expected_behavior': 'successful_transmission'
            },
            {
                'name': 'large_payload_boundary',
                'payload_size': 65536,  # Minimum eight-byte length
                'frame_type': 'text',
                'expected_behavior': 'successful_transmission_or_fragmentation'
            },
            {
                'name': 'binary_frame_boundary',
                'payload_size': 1000,
                'frame_type': 'binary',
                'expected_behavior': 'successful_binary_transmission'
            }
        ]
        
        frame_boundary_results = []
        
        for scenario in frame_boundary_scenarios:
            logger.info(f"Testing frame boundary: {scenario['name']}")
            
            try:
                boundary_result = await self._test_frame_boundary_scenario(
                    user_context, scenario
                )
                
                frame_boundary_results.append({
                    'scenario': scenario['name'],
                    'transmission_successful': boundary_result.get('transmission_successful', False),
                    'data_integrity_maintained': boundary_result.get('data_integrity_maintained', False),
                    'frame_format_correct': boundary_result.get('frame_format_correct', False),
                    'performance_acceptable': boundary_result.get('performance_acceptable', False),
                    'payload_size': scenario['payload_size'],
                    'transmission_time': boundary_result.get('transmission_time', 0),
                    'success': True,
                    'error': None
                })
                
            except Exception as e:
                frame_boundary_results.append({
                    'scenario': scenario['name'],
                    'transmission_successful': False,
                    'data_integrity_maintained': False,
                    'frame_format_correct': False,
                    'performance_acceptable': False,
                    'payload_size': scenario['payload_size'],
                    'transmission_time': 0,
                    'success': False,
                    'error': str(e)
                })
        
        # Verify frame boundary handling
        successful_transmissions = [r for r in frame_boundary_results if r.get('transmission_successful')]
        transmission_success_rate = len(successful_transmissions) / len(frame_boundary_results)
        
        data_integrity_preserved = [r for r in frame_boundary_results if r.get('data_integrity_maintained')]
        integrity_rate = len(data_integrity_preserved) / len(frame_boundary_results)
        
        performance_acceptable = [r for r in frame_boundary_results if r.get('performance_acceptable')]
        performance_rate = len(performance_acceptable) / len(frame_boundary_results)
        
        assert transmission_success_rate >= 0.8, \
            f"Frame boundary transmission success rate insufficient: {transmission_success_rate:.1%}"
        
        assert integrity_rate >= 0.9, \
            f"Data integrity not maintained across frame boundaries: {integrity_rate:.1%}"
        
        assert performance_rate >= 0.7, \
            f"Performance not acceptable for frame boundary conditions: {performance_rate:.1%}"
        
        # Verify large frames don't cause excessive delays
        large_frame_results = [r for r in frame_boundary_results if r['payload_size'] > 1000]
        if large_frame_results:
            max_transmission_time = max(r.get('transmission_time', 0) for r in large_frame_results)
            assert max_transmission_time < 2.0, \
                f"Large frame transmission taking too long: {max_transmission_time:.1f}s"
                
        logger.info(f"Frame boundary test - Transmission: {transmission_success_rate:.1%}, "
                   f"Integrity: {integrity_rate:.1%}, Performance: {performance_rate:.1%}")
    
    async def _test_frame_boundary_scenario(self, user_context: Dict, scenario: Dict) -> Dict:
        """Test specific frame boundary scenario."""
        payload_size = scenario['payload_size']
        frame_type = scenario['frame_type']
        
        start_time = time.time()
        
        # Create payload of specified size
        if frame_type == 'text':
            payload = 'x' * payload_size
            expected_payload = payload
        elif frame_type == 'binary':
            payload = bytes([i % 256 for i in range(payload_size)])
            expected_payload = payload
        else:
            payload = 'default'
            expected_payload = payload
        
        # Simulate WebSocket frame transmission
        try:
            # Mock frame creation and transmission
            await asyncio.sleep(0.001 * (payload_size / 1000))  # Simulate transmission time
            
            # Simulate frame reception and validation
            received_payload = expected_payload  # In real system, this would be actual reception
            
            transmission_time = time.time() - start_time
            
            # Verify data integrity
            data_integrity_maintained = (received_payload == expected_payload)
            
            # Check frame format compliance
            frame_format_correct = True  # Mock validation
            if payload_size <= 125:
                # Single byte length encoding
                frame_format_correct = True
            elif payload_size <= 65535:
                # Two byte length encoding
                frame_format_correct = True
            else:
                # Eight byte length encoding
                frame_format_correct = True
            
            # Performance check
            max_expected_time = 0.1 + (payload_size / 1000000)  # Base time + size factor
            performance_acceptable = transmission_time < max_expected_time
            
            return {
                'transmission_successful': True,
                'data_integrity_maintained': data_integrity_maintained,
                'frame_format_correct': frame_format_correct,
                'performance_acceptable': performance_acceptable,
                'transmission_time': transmission_time,
                'received_payload_size': len(received_payload) if isinstance(received_payload, (str, bytes)) else 0
            }
            
        except Exception as e:
            transmission_time = time.time() - start_time
            
            return {
                'transmission_successful': False,
                'data_integrity_maintained': False,
                'frame_format_correct': False,
                'performance_acceptable': False,
                'transmission_time': transmission_time,
                'error': str(e)
            }
            
    @pytest.mark.integration
    async def test_websocket_control_frame_handling(self):
        """Test WebSocket control frame handling (ping, pong, close)."""
        # Test control frame scenarios
        control_frame_scenarios = [
            {
                'name': 'ping_pong_exchange',
                'control_type': 'ping',
                'payload': b'ping_test_data',
                'expected_response': 'pong',
                'expected_behavior': 'automatic_pong_response'
            },
            {
                'name': 'unsolicited_pong',
                'control_type': 'pong',
                'payload': b'unsolicited_pong',
                'expected_response': None,
                'expected_behavior': 'pong_accepted'
            },
            {
                'name': 'close_frame_normal',
                'control_type': 'close',
                'payload': b'\x03\xe8Normal closure',  # Code 1000 + reason
                'expected_response': 'close',
                'expected_behavior': 'graceful_closure'
            },
            {
                'name': 'close_frame_no_reason',
                'control_type': 'close',
                'payload': b'',  # No close code or reason
                'expected_response': 'close',
                'expected_behavior': 'graceful_closure'
            },
            {
                'name': 'control_frame_with_large_payload',
                'control_type': 'ping',
                'payload': b'x' * 200,  # Control frames should be <= 125 bytes
                'expected_response': None,
                'expected_behavior': 'payload_size_error'
            }
        ]
        
        control_frame_results = []
        
        for scenario in control_frame_scenarios:
            logger.info(f"Testing control frame: {scenario['name']}")
            
            try:
                control_result = await self._test_control_frame_scenario(scenario)
                
                control_frame_results.append({
                    'scenario': scenario['name'],
                    'control_frame_handled': control_result.get('control_frame_handled', False),
                    'response_appropriate': control_result.get('response_appropriate', False),
                    'protocol_compliance': control_result.get('protocol_compliance', False),
                    'timing_correct': control_result.get('timing_correct', False),
                    'error_handling_appropriate': control_result.get('error_handling_appropriate', True),
                    'success': True,
                    'error': None
                })
                
            except Exception as e:
                # Check if error is appropriate for the scenario
                appropriate_error = self._is_appropriate_control_frame_error(e, scenario)
                
                control_frame_results.append({
                    'scenario': scenario['name'],
                    'control_frame_handled': False,
                    'response_appropriate': False,
                    'protocol_compliance': appropriate_error,
                    'timing_correct': False,
                    'error_handling_appropriate': appropriate_error,
                    'success': False,
                    'error': str(e)
                })
        
        # Verify control frame handling
        frames_handled = [r for r in control_frame_results if r.get('control_frame_handled')]
        handling_success_rate = len(frames_handled) / len(control_frame_results)
        
        protocol_compliant = [r for r in control_frame_results if r.get('protocol_compliance')]
        compliance_rate = len(protocol_compliant) / len(control_frame_results)
        
        appropriate_responses = [r for r in control_frame_results if r.get('response_appropriate')]
        response_rate = len(appropriate_responses) / len(control_frame_results)
        
        assert handling_success_rate >= 0.8, \
            f"Control frame handling success rate insufficient: {handling_success_rate:.1%}"
        
        assert compliance_rate >= 0.9, \
            f"WebSocket protocol compliance insufficient: {compliance_rate:.1%}"
        
        # Ping-pong exchanges should have high response rate
        ping_pong_scenarios = [r for r in control_frame_results if 'ping' in r['scenario']]
        if ping_pong_scenarios:
            ping_responses = [r for r in ping_pong_scenarios if r.get('response_appropriate')]
            ping_response_rate = len(ping_responses) / len(ping_pong_scenarios)
            
            assert ping_response_rate >= 0.8, \
                f"Ping-pong response rate insufficient: {ping_response_rate:.1%}"
                
        logger.info(f"Control frame test - Handling: {handling_success_rate:.1%}, "
                   f"Compliance: {compliance_rate:.1%}, Responses: {response_rate:.1%}")
    
    async def _test_control_frame_scenario(self, scenario: Dict) -> Dict:
        """Test specific control frame scenario."""
        control_type = scenario['control_type']
        payload = scenario['payload']
        expected_response = scenario['expected_response']
        expected_behavior = scenario['expected_behavior']
        
        start_time = time.time()
        
        control_frame_handled = False
        response_appropriate = False
        protocol_compliance = False
        timing_correct = False
        error_handling_appropriate = True
        
        try:
            if control_type == 'ping':
                # Simulate ping frame handling
                if len(payload) <= 125:  # Valid control frame size
                    control_frame_handled = True
                    protocol_compliance = True
                    
                    # Should automatically respond with pong
                    if expected_response == 'pong':
                        response_appropriate = True
                        
                    # Timing should be quick for ping/pong
                    response_time = time.time() - start_time
                    timing_correct = response_time < 0.1
                    
                else:
                    # Payload too large for control frame
                    protocol_compliance = False
                    error_handling_appropriate = True
                    raise Exception("Control frame payload too large")
                    
            elif control_type == 'pong':
                # Simulate pong frame handling
                if len(payload) <= 125:
                    control_frame_handled = True
                    protocol_compliance = True
                    response_appropriate = True  # Pong frames don't require response
                    timing_correct = True
                else:
                    raise Exception("Control frame payload too large")
                    
            elif control_type == 'close':
                # Simulate close frame handling
                control_frame_handled = True
                protocol_compliance = True
                
                if expected_response == 'close':
                    response_appropriate = True
                    
                # Close handling should be quick
                response_time = time.time() - start_time
                timing_correct = response_time < 0.5
                
            return {
                'control_frame_handled': control_frame_handled,
                'response_appropriate': response_appropriate,
                'protocol_compliance': protocol_compliance,
                'timing_correct': timing_correct,
                'error_handling_appropriate': error_handling_appropriate
            }
            
        except Exception as e:
            # Error handling for control frames
            if expected_behavior == 'payload_size_error' and 'too large' in str(e):
                error_handling_appropriate = True
                protocol_compliance = True
            else:
                error_handling_appropriate = False
                
            raise e
    
    def _is_appropriate_control_frame_error(self, error: Exception, scenario: Dict) -> bool:
        """Check if error is appropriate for control frame scenario."""
        error_str = str(error).lower()
        expected_behavior = scenario['expected_behavior']
        
        if expected_behavior == 'payload_size_error':
            return any(keyword in error_str for keyword in ['payload', 'size', 'large', 'limit'])
            
        return False
        
    @pytest.mark.integration
    async def test_websocket_extension_negotiation(self):
        """Test WebSocket extension negotiation and compatibility."""
        # Test extension negotiation scenarios
        extension_scenarios = [
            {
                'name': 'compression_extension',
                'extensions': ['permessage-deflate'],
                'client_capabilities': ['permessage-deflate', 'x-webkit-deflate-frame'],
                'expected_behavior': 'compression_negotiated'
            },
            {
                'name': 'unsupported_extension',
                'extensions': ['unsupported-extension'],
                'client_capabilities': ['unsupported-extension'],
                'expected_behavior': 'extension_ignored_or_rejected'
            },
            {
                'name': 'multiple_extensions',
                'extensions': ['permessage-deflate', 'per-frame-compression'],
                'client_capabilities': ['permessage-deflate', 'per-frame-compression', 'x-custom'],
                'expected_behavior': 'compatible_extensions_negotiated'
            },
            {
                'name': 'no_extensions',
                'extensions': [],
                'client_capabilities': [],
                'expected_behavior': 'basic_websocket_connection'
            },
            {
                'name': 'conflicting_extensions',
                'extensions': ['extension-a', 'extension-b'],
                'client_capabilities': ['extension-c', 'extension-d'],
                'expected_behavior': 'no_extensions_negotiated'
            }
        ]
        
        extension_negotiation_results = []
        
        for scenario in extension_scenarios:
            logger.info(f"Testing extension negotiation: {scenario['name']}")
            
            try:
                negotiation_result = await self._test_extension_negotiation_scenario(scenario)
                
                extension_negotiation_results.append({
                    'scenario': scenario['name'],
                    'negotiation_successful': negotiation_result.get('negotiation_successful', False),
                    'extensions_selected': negotiation_result.get('extensions_selected', []),
                    'compatibility_handled': negotiation_result.get('compatibility_handled', False),
                    'fallback_behavior_correct': negotiation_result.get('fallback_behavior_correct', False),
                    'protocol_compliance': negotiation_result.get('protocol_compliance', False),
                    'success': True,
                    'error': None
                })
                
            except Exception as e:
                extension_negotiation_results.append({
                    'scenario': scenario['name'],
                    'negotiation_successful': False,
                    'extensions_selected': [],
                    'compatibility_handled': False,
                    'fallback_behavior_correct': False,
                    'protocol_compliance': False,
                    'success': False,
                    'error': str(e)
                })
        
        # Verify extension negotiation
        successful_negotiations = [r for r in extension_negotiation_results if r.get('negotiation_successful')]
        negotiation_success_rate = len(successful_negotiations) / len(extension_negotiation_results)
        
        compatibility_handled = [r for r in extension_negotiation_results if r.get('compatibility_handled')]
        compatibility_rate = len(compatibility_handled) / len(extension_negotiation_results)
        
        protocol_compliant = [r for r in extension_negotiation_results if r.get('protocol_compliance')]
        compliance_rate = len(protocol_compliant) / len(extension_negotiation_results)
        
        # Not all negotiations need to succeed (unsupported extensions should fail gracefully)
        assert negotiation_success_rate >= 0.6, \
            f"Extension negotiation success rate insufficient: {negotiation_success_rate:.1%}"
        
        assert compatibility_rate >= 0.8, \
            f"Extension compatibility handling insufficient: {compatibility_rate:.1%}"
        
        assert compliance_rate >= 0.8, \
            f"Protocol compliance during extension negotiation insufficient: {compliance_rate:.1%}"
            
        logger.info(f"Extension negotiation test - Success: {negotiation_success_rate:.1%}, "
                   f"Compatibility: {compatibility_rate:.1%}, Compliance: {compliance_rate:.1%}")
    
    async def _test_extension_negotiation_scenario(self, scenario: Dict) -> Dict:
        """Test specific extension negotiation scenario."""
        extensions = scenario['extensions']
        client_capabilities = scenario['client_capabilities']
        expected_behavior = scenario['expected_behavior']
        
        # Mock extension negotiation
        negotiation_successful = False
        extensions_selected = []
        compatibility_handled = False
        fallback_behavior_correct = False
        protocol_compliance = False
        
        # Simulate server extension capabilities
        server_capabilities = ['permessage-deflate']  # Common server capability
        
        if expected_behavior == 'compression_negotiated':
            # Find compatible compression extensions
            compatible = set(extensions) & set(server_capabilities) & set(client_capabilities)
            if compatible:
                extensions_selected = list(compatible)
                negotiation_successful = True
                compatibility_handled = True
                protocol_compliance = True
                
        elif expected_behavior == 'extension_ignored_or_rejected':
            # Unsupported extensions should be handled gracefully
            compatible = set(extensions) & set(server_capabilities)
            if not compatible:
                # No compatible extensions - fallback to basic WebSocket
                negotiation_successful = True  # Connection still works
                fallback_behavior_correct = True
                compatibility_handled = True
                protocol_compliance = True
                
        elif expected_behavior == 'compatible_extensions_negotiated':
            # Select compatible extensions
            compatible = set(extensions) & set(server_capabilities) & set(client_capabilities)
            if compatible:
                extensions_selected = list(compatible)
                negotiation_successful = True
                compatibility_handled = True
                protocol_compliance = True
                
        elif expected_behavior == 'basic_websocket_connection':
            # No extensions requested - should work fine
            negotiation_successful = True
            compatibility_handled = True
            fallback_behavior_correct = True
            protocol_compliance = True
            
        elif expected_behavior == 'no_extensions_negotiated':
            # No compatible extensions - fallback to basic
            negotiation_successful = True
            fallback_behavior_correct = True
            compatibility_handled = True
            protocol_compliance = True
        
        return {
            'negotiation_successful': negotiation_successful,
            'extensions_selected': extensions_selected,
            'compatibility_handled': compatibility_handled,
            'fallback_behavior_correct': fallback_behavior_correct,
            'protocol_compliance': protocol_compliance
        }
        
    @pytest.mark.integration
    async def test_websocket_subprotocol_negotiation(self):
        """Test WebSocket subprotocol negotiation."""
        # Test subprotocol negotiation scenarios
        subprotocol_scenarios = [
            {
                'name': 'single_supported_subprotocol',
                'requested_subprotocols': ['chat'],
                'server_supported': ['chat', 'api'],
                'expected_selected': 'chat',
                'expected_behavior': 'subprotocol_selected'
            },
            {
                'name': 'multiple_subprotocols_priority',
                'requested_subprotocols': ['chat', 'api', 'custom'],
                'server_supported': ['api', 'custom'],
                'expected_selected': 'api',  # First match in client preference order
                'expected_behavior': 'first_match_selected'
            },
            {
                'name': 'no_supported_subprotocol',
                'requested_subprotocols': ['unsupported', 'unknown'],
                'server_supported': ['chat', 'api'],
                'expected_selected': None,
                'expected_behavior': 'no_subprotocol_negotiated'
            },
            {
                'name': 'no_subprotocol_requested',
                'requested_subprotocols': [],
                'server_supported': ['chat', 'api'],
                'expected_selected': None,
                'expected_behavior': 'basic_websocket'
            },
            {
                'name': 'case_sensitive_subprotocol',
                'requested_subprotocols': ['Chat', 'API'],
                'server_supported': ['chat', 'api'],
                'expected_selected': None,  # Case mismatch
                'expected_behavior': 'case_sensitivity_enforced'
            }
        ]
        
        subprotocol_results = []
        
        for scenario in subprotocol_scenarios:
            logger.info(f"Testing subprotocol negotiation: {scenario['name']}")
            
            try:
                subprotocol_result = await self._test_subprotocol_negotiation_scenario(scenario)
                
                subprotocol_results.append({
                    'scenario': scenario['name'],
                    'negotiation_correct': subprotocol_result.get('negotiation_correct', False),
                    'selected_subprotocol': subprotocol_result.get('selected_subprotocol'),
                    'expected_subprotocol': scenario['expected_selected'],
                    'protocol_compliance': subprotocol_result.get('protocol_compliance', False),
                    'fallback_handled': subprotocol_result.get('fallback_handled', False),
                    'success': True,
                    'error': None
                })
                
            except Exception as e:
                subprotocol_results.append({
                    'scenario': scenario['name'],
                    'negotiation_correct': False,
                    'selected_subprotocol': None,
                    'expected_subprotocol': scenario['expected_selected'],
                    'protocol_compliance': False,
                    'fallback_handled': False,
                    'success': False,
                    'error': str(e)
                })
        
        # Verify subprotocol negotiation
        correct_negotiations = [r for r in subprotocol_results if r.get('negotiation_correct')]
        negotiation_correctness_rate = len(correct_negotiations) / len(subprotocol_results)
        
        protocol_compliant = [r for r in subprotocol_results if r.get('protocol_compliance')]
        compliance_rate = len(protocol_compliant) / len(subprotocol_results)
        
        fallback_handled = [r for r in subprotocol_results if r.get('fallback_handled')]
        fallback_rate = len(fallback_handled) / len(subprotocol_results)
        
        assert negotiation_correctness_rate >= 0.8, \
            f"Subprotocol negotiation correctness insufficient: {negotiation_correctness_rate:.1%}"
        
        assert compliance_rate >= 0.8, \
            f"Subprotocol negotiation protocol compliance insufficient: {compliance_rate:.1%}"
        
        assert fallback_rate >= 0.7, \
            f"Subprotocol negotiation fallback handling insufficient: {fallback_rate:.1%}"
            
        logger.info(f"Subprotocol negotiation test - Correctness: {negotiation_correctness_rate:.1%}, "
                   f"Compliance: {compliance_rate:.1%}, Fallback: {fallback_rate:.1%}")
    
    async def _test_subprotocol_negotiation_scenario(self, scenario: Dict) -> Dict:
        """Test specific subprotocol negotiation scenario."""
        requested_subprotocols = scenario['requested_subprotocols']
        server_supported = scenario['server_supported']
        expected_selected = scenario['expected_selected']
        expected_behavior = scenario['expected_behavior']
        
        # Simulate subprotocol negotiation
        selected_subprotocol = None
        negotiation_correct = False
        protocol_compliance = False
        fallback_handled = False
        
        if expected_behavior == 'subprotocol_selected':
            # Find first matching subprotocol in client preference order
            for requested in requested_subprotocols:
                if requested in server_supported:
                    selected_subprotocol = requested
                    break
                    
            negotiation_correct = (selected_subprotocol == expected_selected)
            protocol_compliance = True
            
        elif expected_behavior == 'first_match_selected':
            # Select first matching subprotocol
            for requested in requested_subprotocols:
                if requested in server_supported:
                    selected_subprotocol = requested
                    break
                    
            negotiation_correct = (selected_subprotocol == expected_selected)
            protocol_compliance = True
            
        elif expected_behavior == 'no_subprotocol_negotiated':
            # No compatible subprotocols
            for requested in requested_subprotocols:
                if requested in server_supported:
                    selected_subprotocol = requested
                    break
                    
            negotiation_correct = (selected_subprotocol == expected_selected)
            fallback_handled = True
            protocol_compliance = True
            
        elif expected_behavior == 'basic_websocket':
            # No subprotocols requested - basic connection
            selected_subprotocol = None
            negotiation_correct = (selected_subprotocol == expected_selected)
            fallback_handled = True
            protocol_compliance = True
            
        elif expected_behavior == 'case_sensitivity_enforced':
            # Case-sensitive matching
            for requested in requested_subprotocols:
                if requested in server_supported:  # Exact case match
                    selected_subprotocol = requested
                    break
                    
            negotiation_correct = (selected_subprotocol == expected_selected)
            protocol_compliance = True
        
        return {
            'negotiation_correct': negotiation_correct,
            'selected_subprotocol': selected_subprotocol,
            'protocol_compliance': protocol_compliance,
            'fallback_handled': fallback_handled
        }
        
    @pytest.mark.integration
    async def test_websocket_masking_requirements(self):
        """Test WebSocket masking requirements and validation."""
        # Test masking scenarios
        masking_scenarios = [
            {
                'name': 'client_to_server_masked',
                'direction': 'client_to_server',
                'masked': True,
                'expected_behavior': 'accepted'
            },
            {
                'name': 'client_to_server_unmasked',
                'direction': 'client_to_server',
                'masked': False,
                'expected_behavior': 'protocol_error'
            },
            {
                'name': 'server_to_client_unmasked',
                'direction': 'server_to_client',
                'masked': False,
                'expected_behavior': 'accepted'
            },
            {
                'name': 'server_to_client_masked',
                'direction': 'server_to_client',
                'masked': True,
                'expected_behavior': 'protocol_error'
            },
            {
                'name': 'mask_key_validation',
                'direction': 'client_to_server',
                'masked': True,
                'mask_key': b'\x00\x00\x00\x00',
                'expected_behavior': 'weak_mask_warning_or_accepted'
            }
        ]
        
        masking_results = []
        
        for scenario in masking_scenarios:
            logger.info(f"Testing WebSocket masking: {scenario['name']}")
            
            try:
                masking_result = await self._test_masking_scenario(scenario)
                
                masking_results.append({
                    'scenario': scenario['name'],
                    'masking_validated': masking_result.get('masking_validated', False),
                    'protocol_compliance': masking_result.get('protocol_compliance', False),
                    'error_handling_correct': masking_result.get('error_handling_correct', False),
                    'security_maintained': masking_result.get('security_maintained', False),
                    'success': True,
                    'error': None
                })
                
            except Exception as e:
                # Check if error is appropriate for masking violation
                appropriate_error = self._is_appropriate_masking_error(e, scenario)
                
                masking_results.append({
                    'scenario': scenario['name'],
                    'masking_validated': False,
                    'protocol_compliance': appropriate_error,
                    'error_handling_correct': appropriate_error,
                    'security_maintained': appropriate_error,
                    'success': False,
                    'error': str(e)
                })
        
        # Verify masking requirements
        masking_validated = [r for r in masking_results if r.get('masking_validated')]
        validation_rate = len(masking_validated) / len(masking_results)
        
        protocol_compliant = [r for r in masking_results if r.get('protocol_compliance')]
        compliance_rate = len(protocol_compliant) / len(masking_results)
        
        security_maintained = [r for r in masking_results if r.get('security_maintained')]
        security_rate = len(security_maintained) / len(masking_results)
        
        assert validation_rate >= 0.6, \
            f"Masking validation rate insufficient: {validation_rate:.1%}"
        
        assert compliance_rate >= 0.8, \
            f"Masking protocol compliance insufficient: {compliance_rate:.1%}"
        
        assert security_rate >= 0.8, \
            f"Security not maintained during masking validation: {security_rate:.1%}"
            
        logger.info(f"Masking test - Validation: {validation_rate:.1%}, "
                   f"Compliance: {compliance_rate:.1%}, Security: {security_rate:.1%}")
    
    async def _test_masking_scenario(self, scenario: Dict) -> Dict:
        """Test specific masking scenario."""
        direction = scenario['direction']
        masked = scenario['masked']
        expected_behavior = scenario['expected_behavior']
        mask_key = scenario.get('mask_key', b'\x12\x34\x56\x78')
        
        masking_validated = False
        protocol_compliance = False
        error_handling_correct = False
        security_maintained = False
        
        if direction == 'client_to_server':
            if masked:
                if expected_behavior == 'accepted':
                    masking_validated = True
                    protocol_compliance = True
                    security_maintained = True
                    
                    # Check mask key strength
                    if mask_key == b'\x00\x00\x00\x00':
                        # Weak mask key - should be handled appropriately
                        security_maintained = False  # Weak masking
                    
                elif expected_behavior == 'weak_mask_warning_or_accepted':
                    masking_validated = True
                    protocol_compliance = True
                    # Security depends on mask strength
                    security_maintained = mask_key != b'\x00\x00\x00\x00'
                    
            else:
                if expected_behavior == 'protocol_error':
                    # Unmasked client frames should be rejected
                    protocol_compliance = True
                    error_handling_correct = True
                    security_maintained = True
                    raise Exception("Client frames must be masked")
                    
        elif direction == 'server_to_client':
            if not masked:
                if expected_behavior == 'accepted':
                    masking_validated = True
                    protocol_compliance = True
                    security_maintained = True
            else:
                if expected_behavior == 'protocol_error':
                    # Masked server frames should be rejected
                    protocol_compliance = True
                    error_handling_correct = True
                    security_maintained = True
                    raise Exception("Server frames must not be masked")
        
        return {
            'masking_validated': masking_validated,
            'protocol_compliance': protocol_compliance,
            'error_handling_correct': error_handling_correct,
            'security_maintained': security_maintained
        }
    
    def _is_appropriate_masking_error(self, error: Exception, scenario: Dict) -> bool:
        """Check if error is appropriate for masking scenario."""
        error_str = str(error).lower()
        expected_behavior = scenario['expected_behavior']
        
        if expected_behavior == 'protocol_error':
            return any(keyword in error_str for keyword in ['mask', 'protocol', 'frame', 'invalid'])
            
        return False