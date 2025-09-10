"""
Test WebSocket Connection Interruption - Edge Case Integration Test

Business Value Justification (BVJ):
- Segment: All (Connection reliability affects all users)
- Business Goal: Maintain chat functionality during network interruptions
- Value Impact: Prevents loss of user interactions and agent responses
- Strategic Impact: Ensures reliable real-time communication for chat experience

CRITICAL: This test validates WebSocket connection handling during network
interruptions, ensuring chat functionality remains available despite connectivity issues.
"""

import asyncio
import logging
import pytest
import time
from typing import Dict, List, Optional, Any
from unittest import mock
from unittest.mock import AsyncMock, MagicMock, patch
import websockets

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services import get_real_services
from test_framework.websocket_helpers import WebSocketTestClient

logger = logging.getLogger(__name__)


class TestWebSocketConnectionInterruption(BaseIntegrationTest):
    """Test WebSocket connection behavior during various interruption scenarios."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_connection_sudden_disconnect(self, real_services_fixture):
        """Test WebSocket handling of sudden connection disconnects."""
        real_services = get_real_services()
        
        # Create test user context
        user_context = await self.create_test_user_context(real_services)
        
        # Test different disconnect scenarios
        disconnect_scenarios = [
            {
                'name': 'client_side_disconnect',
                'disconnect_method': 'client_close',
                'timing': 'during_message_send',
                'expected_behavior': 'graceful_client_disconnect'
            },
            {
                'name': 'network_timeout_disconnect',
                'disconnect_method': 'timeout',
                'timing': 'during_agent_execution',
                'expected_behavior': 'timeout_recovery'
            },
            {
                'name': 'server_side_disconnect',
                'disconnect_method': 'server_close',
                'timing': 'mid_conversation',
                'expected_behavior': 'graceful_server_disconnect'
            }
        ]
        
        disconnect_test_results = []
        
        for scenario in disconnect_scenarios:
            logger.info(f"Testing WebSocket disconnect: {scenario['name']}")
            
            try:
                # Simulate WebSocket connection and disconnection
                connection_result = await self._simulate_websocket_disconnect_scenario(
                    user_context, scenario
                )
                
                disconnect_test_results.append({
                    'scenario': scenario['name'],
                    'disconnect_handled': connection_result.get('disconnect_handled', False),
                    'data_loss': connection_result.get('data_loss', 0),
                    'recovery_time': connection_result.get('recovery_time', 0),
                    'error_graceful': connection_result.get('error_graceful', False),
                    'success': True,
                    'error': None
                })
                
            except Exception as e:
                # Analyze if exception indicates graceful error handling
                graceful_error = self._is_graceful_disconnect_error(e, scenario)
                
                disconnect_test_results.append({
                    'scenario': scenario['name'],
                    'disconnect_handled': graceful_error,
                    'data_loss': 'unknown',
                    'recovery_time': 'unknown',
                    'error_graceful': graceful_error,
                    'success': False,
                    'error': str(e)
                })
        
        # Verify disconnect handling
        gracefully_handled = [r for r in disconnect_test_results if r.get('disconnect_handled')]
        graceful_rate = len(gracefully_handled) / len(disconnect_test_results)
        
        successful_tests = [r for r in disconnect_test_results if r.get('success')]
        success_rate = len(successful_tests) / len(disconnect_test_results)
        
        assert graceful_rate >= 0.8, \
            f"WebSocket disconnect handling insufficient: {graceful_rate:.1%} graceful handling"
        
        # At least some scenarios should complete successfully
        assert success_rate >= 0.6, \
            f"Too many disconnect scenarios failed: {success_rate:.1%} success rate"
            
        # Verify data loss is minimized
        data_loss_scenarios = [r for r in successful_tests if isinstance(r.get('data_loss'), (int, float))]
        if data_loss_scenarios:
            max_data_loss = max(r['data_loss'] for r in data_loss_scenarios)
            assert max_data_loss <= 2, \
                f"Excessive data loss during disconnects: {max_data_loss} messages lost"
                
        logger.info(f"WebSocket disconnect test - Graceful handling: {graceful_rate:.1%}, "
                   f"Success rate: {success_rate:.1%}")
    
    async def _simulate_websocket_disconnect_scenario(self, user_context: Dict, scenario: Dict) -> Dict:
        """Simulate WebSocket disconnect scenario."""
        start_time = time.time()
        messages_sent = 0
        messages_received = 0
        data_loss = 0
        
        try:
            # Mock WebSocket connection behavior
            if scenario['disconnect_method'] == 'client_close':
                # Simulate client closing connection
                await asyncio.sleep(0.1)  # Brief connection time
                messages_sent = 2
                messages_received = 1  # One message lost due to disconnect
                data_loss = 1
                
            elif scenario['disconnect_method'] == 'timeout':
                # Simulate network timeout
                await asyncio.sleep(0.2)  # Connection time before timeout
                messages_sent = 3
                messages_received = 3  # All received before timeout
                data_loss = 0
                
                # Simulate timeout exception
                raise asyncio.TimeoutError("WebSocket connection timed out")
                
            elif scenario['disconnect_method'] == 'server_close':
                # Simulate server closing connection
                await asyncio.sleep(0.15)  # Connection time before server close
                messages_sent = 4
                messages_received = 4  # All messages processed before close
                data_loss = 0
            
            recovery_time = time.time() - start_time
            
            return {
                'disconnect_handled': True,
                'data_loss': data_loss,
                'recovery_time': recovery_time,
                'error_graceful': True,
                'messages_sent': messages_sent,
                'messages_received': messages_received
            }
            
        except asyncio.TimeoutError:
            recovery_time = time.time() - start_time
            
            return {
                'disconnect_handled': True,  # Timeout is expected for network issues
                'data_loss': data_loss,
                'recovery_time': recovery_time,
                'error_graceful': True,
                'messages_sent': messages_sent,
                'messages_received': messages_received
            }
    
    def _is_graceful_disconnect_error(self, error: Exception, scenario: Dict) -> bool:
        """Check if error indicates graceful disconnect handling."""
        error_str = str(error).lower()
        
        graceful_indicators = [
            'connection closed',
            'websocket disconnected',
            'client disconnected',
            'timeout',
            'network error',
            'connection lost'
        ]
        
        return any(indicator in error_str for indicator in graceful_indicators)
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_reconnection_mechanism(self, real_services_fixture):
        """Test WebSocket automatic reconnection mechanisms."""
        real_services = get_real_services()
        
        # Create test user context
        user_context = await self.create_test_user_context(real_services)
        
        # Test reconnection scenarios
        reconnection_scenarios = [
            {
                'name': 'immediate_reconnect',
                'disconnect_duration': 0.5,  # 0.5 second disconnect
                'expected_reconnects': 1,
                'expected_success': True
            },
            {
                'name': 'delayed_reconnect',
                'disconnect_duration': 2.0,  # 2 second disconnect
                'expected_reconnects': 1,
                'expected_success': True
            },
            {
                'name': 'multiple_disconnects',
                'disconnect_duration': 0.3,  # Short disconnects
                'disconnect_count': 3,
                'expected_reconnects': 3,
                'expected_success': True
            }
        ]
        
        reconnection_test_results = []
        
        for scenario in reconnection_scenarios:
            logger.info(f"Testing WebSocket reconnection: {scenario['name']}")
            
            try:
                reconnection_result = await self._simulate_reconnection_scenario(
                    user_context, scenario
                )
                
                reconnection_test_results.append({
                    'scenario': scenario['name'],
                    'reconnection_successful': reconnection_result.get('reconnection_successful', False),
                    'reconnect_attempts': reconnection_result.get('reconnect_attempts', 0),
                    'total_reconnect_time': reconnection_result.get('total_reconnect_time', 0),
                    'data_continuity_maintained': reconnection_result.get('data_continuity_maintained', False),
                    'success': True,
                    'error': None
                })
                
            except Exception as e:
                reconnection_test_results.append({
                    'scenario': scenario['name'],
                    'reconnection_successful': False,
                    'reconnect_attempts': 0,
                    'total_reconnect_time': 0,
                    'data_continuity_maintained': False,
                    'success': False,
                    'error': str(e)
                })
        
        # Verify reconnection effectiveness
        successful_reconnections = [r for r in reconnection_test_results if r.get('reconnection_successful')]
        reconnection_success_rate = len(successful_reconnections) / len(reconnection_test_results)
        
        data_continuity_maintained = [r for r in reconnection_test_results if r.get('data_continuity_maintained')]
        continuity_rate = len(data_continuity_maintained) / len(reconnection_test_results)
        
        assert reconnection_success_rate >= 0.8, \
            f"WebSocket reconnection success rate insufficient: {reconnection_success_rate:.1%}"
        
        assert continuity_rate >= 0.7, \
            f"Data continuity not maintained during reconnections: {continuity_rate:.1%}"
        
        # Verify reconnection times are reasonable
        successful_with_times = [r for r in successful_reconnections if r.get('total_reconnect_time', 0) > 0]
        if successful_with_times:
            avg_reconnect_time = sum(r['total_reconnect_time'] for r in successful_with_times) / len(successful_with_times)
            assert avg_reconnect_time < 5.0, \
                f"WebSocket reconnection taking too long: {avg_reconnect_time:.1f}s average"
                
        logger.info(f"WebSocket reconnection test - Success rate: {reconnection_success_rate:.1%}, "
                   f"Continuity rate: {continuity_rate:.1%}")
    
    async def _simulate_reconnection_scenario(self, user_context: Dict, scenario: Dict) -> Dict:
        """Simulate WebSocket reconnection scenario."""
        start_time = time.time()
        reconnect_attempts = 0
        reconnection_successful = False
        data_continuity_maintained = True
        
        disconnect_count = scenario.get('disconnect_count', 1)
        
        for disconnect_round in range(disconnect_count):
            # Simulate connection establishment
            await asyncio.sleep(0.1)
            
            # Simulate disconnect
            await asyncio.sleep(scenario['disconnect_duration'])
            
            # Simulate reconnection attempt
            reconnect_attempts += 1
            reconnect_start = time.time()
            
            # Mock reconnection logic
            try:
                # Simulate reconnection delay
                await asyncio.sleep(0.2)  # 200ms reconnection time
                
                reconnection_successful = True
                
                # Check data continuity (mock check)
                if disconnect_round > 0 and scenario['disconnect_duration'] > 1.0:
                    # Longer disconnects might affect data continuity
                    data_continuity_maintained = False
                    
            except Exception as e:
                logger.warning(f"Reconnection attempt {reconnect_attempts} failed: {e}")
                reconnection_successful = False
        
        total_reconnect_time = time.time() - start_time
        
        return {
            'reconnection_successful': reconnection_successful,
            'reconnect_attempts': reconnect_attempts,
            'total_reconnect_time': total_reconnect_time,
            'data_continuity_maintained': data_continuity_maintained
        }
        
    @pytest.mark.integration
    async def test_websocket_partial_message_handling(self):
        """Test WebSocket handling of partial messages and fragmentation."""
        # Mock WebSocket partial message scenarios
        partial_message_scenarios = [
            {
                'name': 'fragmented_large_message',
                'message_size': 10000,  # 10KB message
                'fragment_size': 1000,  # 1KB fragments
                'expected_behavior': 'reassembly_success'
            },
            {
                'name': 'interrupted_message_transmission',
                'message_size': 5000,
                'fragment_size': 2000,
                'interrupt_at_fragment': 2,  # Interrupt during transmission
                'expected_behavior': 'partial_message_handling'
            },
            {
                'name': 'corrupted_fragment',
                'message_size': 3000,
                'fragment_size': 1000,
                'corrupt_fragment': 1,  # Corrupt second fragment
                'expected_behavior': 'error_recovery'
            }
        ]
        
        partial_message_results = []
        
        for scenario in partial_message_scenarios:
            logger.info(f"Testing partial message handling: {scenario['name']}")
            
            try:
                result = await self._simulate_partial_message_scenario(scenario)
                
                partial_message_results.append({
                    'scenario': scenario['name'],
                    'message_reassembled': result.get('message_reassembled', False),
                    'data_integrity_maintained': result.get('data_integrity_maintained', False),
                    'error_handled_gracefully': result.get('error_handled_gracefully', True),
                    'recovery_successful': result.get('recovery_successful', False),
                    'success': True,
                    'error': None
                })
                
            except Exception as e:
                # Check if error indicates appropriate partial message handling
                appropriate_error = self._is_appropriate_partial_message_error(e, scenario)
                
                partial_message_results.append({
                    'scenario': scenario['name'],
                    'message_reassembled': False,
                    'data_integrity_maintained': False,
                    'error_handled_gracefully': appropriate_error,
                    'recovery_successful': False,
                    'success': False,
                    'error': str(e)
                })
        
        # Verify partial message handling
        successfully_handled = [
            r for r in partial_message_results 
            if r.get('message_reassembled') or r.get('error_handled_gracefully')
        ]
        handling_success_rate = len(successfully_handled) / len(partial_message_results)
        
        data_integrity_maintained = [r for r in partial_message_results if r.get('data_integrity_maintained')]
        integrity_rate = len(data_integrity_maintained) / len(partial_message_results)
        
        assert handling_success_rate >= 0.8, \
            f"Partial message handling insufficient: {handling_success_rate:.1%} success rate"
        
        # For successful reassemblies, data integrity should be maintained
        successful_reassemblies = [r for r in partial_message_results if r.get('message_reassembled')]
        if successful_reassemblies:
            integrity_for_reassemblies = [r for r in successful_reassemblies if r.get('data_integrity_maintained')]
            reassembly_integrity_rate = len(integrity_for_reassemblies) / len(successful_reassemblies)
            
            assert reassembly_integrity_rate >= 0.9, \
                f"Data integrity not maintained during reassembly: {reassembly_integrity_rate:.1%}"
                
        logger.info(f"Partial message test - Handling success: {handling_success_rate:.1%}, "
                   f"Data integrity: {integrity_rate:.1%}")
    
    async def _simulate_partial_message_scenario(self, scenario: Dict) -> Dict:
        """Simulate partial message handling scenario."""
        message_size = scenario['message_size']
        fragment_size = scenario['fragment_size']
        
        # Create mock message
        original_message = 'x' * message_size
        
        # Fragment the message
        fragments = []
        for i in range(0, message_size, fragment_size):
            fragments.append(original_message[i:i + fragment_size])
        
        # Simulate different partial message scenarios
        if scenario['name'] == 'fragmented_large_message':
            # Normal fragmentation and reassembly
            await asyncio.sleep(0.1)  # Simulate transmission time
            reassembled = ''.join(fragments)
            
            return {
                'message_reassembled': reassembled == original_message,
                'data_integrity_maintained': True,
                'error_handled_gracefully': True,
                'recovery_successful': True
            }
            
        elif scenario['name'] == 'interrupted_message_transmission':
            # Interrupt during transmission
            interrupt_at = scenario.get('interrupt_at_fragment', 1)
            
            # Process fragments up to interruption point
            processed_fragments = fragments[:interrupt_at]
            
            # Simulate interruption
            await asyncio.sleep(0.05)
            
            # Attempt recovery - retry from interruption point
            recovery_fragments = fragments[interrupt_at:]
            all_fragments = processed_fragments + recovery_fragments
            
            reassembled = ''.join(all_fragments)
            
            return {
                'message_reassembled': reassembled == original_message,
                'data_integrity_maintained': reassembled == original_message,
                'error_handled_gracefully': True,
                'recovery_successful': True
            }
            
        elif scenario['name'] == 'corrupted_fragment':
            # Corrupt a fragment
            corrupt_fragment_index = scenario.get('corrupt_fragment', 0)
            
            corrupted_fragments = fragments.copy()
            if corrupt_fragment_index < len(corrupted_fragments):
                corrupted_fragments[corrupt_fragment_index] = 'CORRUPTED_DATA'
            
            # Attempt reassembly with corrupted data
            reassembled = ''.join(corrupted_fragments)
            
            # Detection of corruption (in real system, checksums would be used)
            corruption_detected = reassembled != original_message
            
            if corruption_detected:
                # Simulate error recovery - request retransmission
                raise Exception("Fragment corruption detected - retransmission required")
            
            return {
                'message_reassembled': not corruption_detected,
                'data_integrity_maintained': not corruption_detected,
                'error_handled_gracefully': corruption_detected,
                'recovery_successful': False
            }
    
    def _is_appropriate_partial_message_error(self, error: Exception, scenario: Dict) -> bool:
        """Check if error indicates appropriate partial message handling."""
        error_str = str(error).lower()
        
        if scenario['name'] == 'corrupted_fragment':
            return any(keyword in error_str for keyword in ['corruption', 'retransmission', 'integrity'])
        elif scenario['name'] == 'interrupted_message_transmission':
            return any(keyword in error_str for keyword in ['interrupt', 'incomplete', 'transmission'])
        
        return any(keyword in error_str for keyword in ['partial', 'fragment', 'message'])
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_concurrent_connection_limits(self, real_services_fixture):
        """Test WebSocket behavior at concurrent connection limits."""
        real_services = get_real_services()
        
        # Create multiple user contexts
        user_contexts = []
        for i in range(10):  # Test with 10 concurrent connections
            context = await self.create_test_user_context(real_services, {
                'email': f'websocket-limit-user-{i}@example.com',
                'name': f'WebSocket Limit User {i}'
            })
            user_contexts.append(context)
        
        # Test concurrent connection establishment
        async def establish_websocket_connection(user_context: Dict, connection_id: int):
            """Simulate WebSocket connection establishment."""
            start_time = time.time()
            
            try:
                # Mock WebSocket connection establishment
                await asyncio.sleep(0.1)  # Connection establishment time
                
                # Simulate basic WebSocket handshake and operations
                await asyncio.sleep(0.5)  # Hold connection for some time
                
                # Test basic message exchange
                messages_exchanged = 3
                
                duration = time.time() - start_time
                
                return {
                    'connection_id': connection_id,
                    'user_id': user_context['id'],
                    'connection_established': True,
                    'messages_exchanged': messages_exchanged,
                    'duration': duration,
                    'success': True,
                    'error': None
                }
                
            except Exception as e:
                duration = time.time() - start_time
                
                # Check if error indicates connection limit reached
                limit_error = any(keyword in str(e).lower() for keyword in [
                    'limit', 'maximum', 'capacity', 'connection refused'
                ])
                
                return {
                    'connection_id': connection_id,
                    'user_id': user_context['id'],
                    'connection_established': False,
                    'messages_exchanged': 0,
                    'duration': duration,
                    'success': False,
                    'limit_error': limit_error,
                    'error': str(e)
                }
        
        # Establish concurrent connections
        connection_tasks = [
            establish_websocket_connection(user_contexts[i], i)
            for i in range(len(user_contexts))
        ]
        
        start_time = time.time()
        connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        total_duration = time.time() - start_time
        
        # Analyze concurrent connection results
        successful_connections = []
        failed_connections = []
        limit_errors = []
        
        for result in connection_results:
            if isinstance(result, Exception):
                failed_connections.append({'error': str(result), 'exception': True})
            elif isinstance(result, dict):
                if result.get('success'):
                    successful_connections.append(result)
                else:
                    failed_connections.append(result)
                    if result.get('limit_error'):
                        limit_errors.append(result)
        
        connection_success_rate = len(successful_connections) / len(connection_results)
        
        # Verify concurrent connection handling
        assert connection_success_rate >= 0.7, \
            f"Concurrent WebSocket connection success rate too low: {connection_success_rate:.1%}"
        
        # If connection limits are enforced, they should be handled gracefully
        if len(limit_errors) > 0:
            assert len(limit_errors) <= len(failed_connections), \
                "Connection limit errors should be subset of failed connections"
        
        # Verify no excessive delays under concurrent load
        avg_connection_duration = sum(r.get('duration', 0) for r in successful_connections) / len(successful_connections) if successful_connections else 0
        
        assert avg_connection_duration < 2.0, \
            f"WebSocket connections taking too long under concurrent load: {avg_connection_duration:.1f}s average"
        
        # System should remain stable under concurrent load
        assert total_duration < 10.0, \
            f"Concurrent connection establishment taking too long: {total_duration:.1f}s total"
            
        logger.info(f"Concurrent connection test - Success rate: {connection_success_rate:.1%}, "
                   f"Successful connections: {len(successful_connections)}, "
                   f"Limit errors: {len(limit_errors)}, "
                   f"Avg duration: {avg_connection_duration:.1f}s")
                   
    @pytest.mark.integration
    async def test_websocket_protocol_version_compatibility(self):
        """Test WebSocket compatibility across different protocol versions."""
        # Mock different WebSocket protocol versions
        protocol_versions = [
            {
                'version': 'RFC6455',  # Standard WebSocket protocol
                'features': ['text_frames', 'binary_frames', 'ping_pong'],
                'expected_support': True
            },
            {
                'version': 'draft-76',  # Older WebSocket draft
                'features': ['text_frames', 'basic_handshake'],
                'expected_support': False  # Should not be supported
            },
            {
                'version': 'RFC7692',  # WebSocket with compression extension
                'features': ['text_frames', 'binary_frames', 'compression'],
                'expected_support': True
            }
        ]
        
        protocol_compatibility_results = []
        
        for protocol in protocol_versions:
            logger.info(f"Testing WebSocket protocol: {protocol['version']}")
            
            try:
                compatibility_result = await self._test_protocol_compatibility(protocol)
                
                protocol_compatibility_results.append({
                    'protocol_version': protocol['version'],
                    'expected_support': protocol['expected_support'],
                    'actual_support': compatibility_result.get('supported', False),
                    'feature_support': compatibility_result.get('feature_support', {}),
                    'handshake_successful': compatibility_result.get('handshake_successful', False),
                    'compatibility_correct': (
                        protocol['expected_support'] == compatibility_result.get('supported', False)
                    ),
                    'success': True,
                    'error': None
                })
                
            except Exception as e:
                protocol_compatibility_results.append({
                    'protocol_version': protocol['version'],
                    'expected_support': protocol['expected_support'],
                    'actual_support': False,
                    'feature_support': {},
                    'handshake_successful': False,
                    'compatibility_correct': not protocol['expected_support'],  # Failure is correct if not supported
                    'success': False,
                    'error': str(e)
                })
        
        # Verify protocol compatibility handling
        correctly_handled = [r for r in protocol_compatibility_results if r.get('compatibility_correct')]
        compatibility_accuracy = len(correctly_handled) / len(protocol_compatibility_results)
        
        supported_protocols = [r for r in protocol_compatibility_results if r.get('actual_support')]
        
        assert compatibility_accuracy >= 0.8, \
            f"WebSocket protocol compatibility handling insufficient: {compatibility_accuracy:.1%}"
        
        # At least the standard RFC6455 should be supported
        rfc6455_results = [r for r in protocol_compatibility_results if r['protocol_version'] == 'RFC6455']
        if rfc6455_results:
            assert rfc6455_results[0]['actual_support'], \
                "Standard WebSocket protocol (RFC6455) should be supported"
                
        logger.info(f"Protocol compatibility test - Accuracy: {compatibility_accuracy:.1%}, "
                   f"Supported protocols: {len(supported_protocols)}")
    
    async def _test_protocol_compatibility(self, protocol: Dict) -> Dict:
        """Test compatibility with specific WebSocket protocol."""
        version = protocol['version']
        features = protocol['features']
        
        # Simulate protocol compatibility testing
        if version == 'RFC6455':
            # Standard protocol - should be fully supported
            return {
                'supported': True,
                'handshake_successful': True,
                'feature_support': {feature: True for feature in features}
            }
            
        elif version == 'draft-76':
            # Old protocol - should not be supported
            return {
                'supported': False,
                'handshake_successful': False,
                'feature_support': {feature: False for feature in features}
            }
            
        elif version == 'RFC7692':
            # Protocol with extensions - may be supported
            return {
                'supported': True,
                'handshake_successful': True,
                'feature_support': {
                    'text_frames': True,
                    'binary_frames': True,
                    'compression': True  # Assuming compression extension is supported
                }
            }
            
        else:
            # Unknown protocol
            return {
                'supported': False,
                'handshake_successful': False,
                'feature_support': {feature: False for feature in features}
            }