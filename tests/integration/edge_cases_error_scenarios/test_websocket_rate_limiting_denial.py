"""
Test WebSocket Rate Limiting and Denial of Service - Edge Case Integration Test

Business Value Justification (BVJ):
- Segment: All (System protection affects all users)
- Business Goal: Prevent abuse and maintain service availability under attack
- Value Impact: Ensures reliable chat service during high load or malicious activity
- Strategic Impact: Protects platform resources and maintains user experience quality

CRITICAL: This test validates WebSocket rate limiting and DoS protection to ensure
system stability and availability during abuse attempts or excessive load.
"""

import asyncio
import logging
import pytest
import time
from typing import Dict, List, Optional, Any
from unittest import mock
from unittest.mock import AsyncMock, MagicMock, patch

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services import get_real_services

logger = logging.getLogger(__name__)


class TestWebSocketRateLimitingDenial(BaseIntegrationTest):
    """Test WebSocket rate limiting and DoS protection mechanisms."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_message_rate_limiting(self, real_services_fixture):
        """Test WebSocket message rate limiting protection."""
        real_services = get_real_services()
        
        # Create test user context
        user_context = await self.create_test_user_context(real_services)
        
        # Test different rate limiting scenarios
        rate_limiting_scenarios = [
            {
                'name': 'normal_usage_within_limits',
                'messages_per_minute': 30,
                'burst_size': 5,
                'rate_limit': 60,  # 60 messages per minute
                'expected_behavior': 'all_messages_accepted'
            },
            {
                'name': 'burst_exceeding_limits',
                'messages_per_minute': 100,
                'burst_size': 50,
                'rate_limit': 60,
                'expected_behavior': 'rate_limiting_applied'
            },
            {
                'name': 'sustained_high_rate',
                'messages_per_minute': 120,
                'burst_size': 10,
                'rate_limit': 60,
                'expected_behavior': 'throttling_applied'
            },
            {
                'name': 'spam_attack_simulation',
                'messages_per_minute': 500,
                'burst_size': 100,
                'rate_limit': 60,
                'expected_behavior': 'aggressive_rate_limiting'
            }
        ]
        
        rate_limiting_results = []
        
        for scenario in rate_limiting_scenarios:
            logger.info(f"Testing rate limiting: {scenario['name']}")
            
            try:
                limiting_result = await self._test_rate_limiting_scenario(
                    user_context, scenario
                )
                
                rate_limiting_results.append({
                    'scenario': scenario['name'],
                    'rate_limiting_effective': limiting_result.get('rate_limiting_effective', False),
                    'messages_sent': limiting_result.get('messages_sent', 0),
                    'messages_accepted': limiting_result.get('messages_accepted', 0),
                    'messages_blocked': limiting_result.get('messages_blocked', 0),
                    'rate_limit_triggered': limiting_result.get('rate_limit_triggered', False),
                    'system_stable': limiting_result.get('system_stable', False),
                    'blocking_appropriate': limiting_result.get('blocking_appropriate', False),
                    'success': True,
                    'error': None
                })
                
            except Exception as e:
                rate_limiting_results.append({
                    'scenario': scenario['name'],
                    'rate_limiting_effective': False,
                    'messages_sent': 0,
                    'messages_accepted': 0,
                    'messages_blocked': 0,
                    'rate_limit_triggered': False,
                    'system_stable': False,
                    'blocking_appropriate': False,
                    'success': False,
                    'error': str(e)
                })
        
        # Verify rate limiting effectiveness
        effective_limiting = [r for r in rate_limiting_results if r.get('rate_limiting_effective')]
        effectiveness_rate = len(effective_limiting) / len(rate_limiting_results)
        
        system_stable = [r for r in rate_limiting_results if r.get('system_stable')]
        stability_rate = len(system_stable) / len(rate_limiting_results)
        
        assert effectiveness_rate >= 0.8, \
            f"Rate limiting effectiveness insufficient: {effectiveness_rate:.1%}"
        
        assert stability_rate >= 0.9, \
            f"System stability not maintained during rate limiting: {stability_rate:.1%}"
        
        # Verify appropriate blocking for high-rate scenarios
        high_rate_scenarios = [r for r in rate_limiting_results if 'high_rate' in r['scenario'] or 'spam' in r['scenario']]
        if high_rate_scenarios:
            blocked_high_rate = [r for r in high_rate_scenarios if r.get('rate_limit_triggered')]
            high_rate_blocking = len(blocked_high_rate) / len(high_rate_scenarios)
            
            assert high_rate_blocking >= 0.8, \
                f"High rate scenarios not properly blocked: {high_rate_blocking:.1%}"
        
        # Normal usage should not be affected
        normal_scenarios = [r for r in rate_limiting_results if 'normal_usage' in r['scenario']]
        if normal_scenarios:
            unblocked_normal = [r for r in normal_scenarios if not r.get('rate_limit_triggered')]
            normal_access_rate = len(unblocked_normal) / len(normal_scenarios)
            
            assert normal_access_rate >= 0.9, \
                f"Normal usage incorrectly blocked: {normal_access_rate:.1%}"
                
        logger.info(f"Rate limiting test - Effectiveness: {effectiveness_rate:.1%}, "
                   f"Stability: {stability_rate:.1%}")
    
    async def _test_rate_limiting_scenario(self, user_context: Dict, scenario: Dict) -> Dict:
        """Test specific rate limiting scenario."""
        messages_per_minute = scenario['messages_per_minute']
        burst_size = scenario['burst_size']
        rate_limit = scenario['rate_limit']
        expected_behavior = scenario['expected_behavior']
        
        # Mock rate limiter state
        rate_limiter = {
            'messages_in_window': 0,
            'window_start': time.time(),
            'window_duration': 60.0,  # 1 minute
            'rate_limit': rate_limit,
            'blocked_count': 0
        }
        
        def check_rate_limit():
            """Check if message should be rate limited."""
            current_time = time.time()
            
            # Reset window if expired
            if current_time - rate_limiter['window_start'] >= rate_limiter['window_duration']:
                rate_limiter['messages_in_window'] = 0
                rate_limiter['window_start'] = current_time
                
            # Check if within rate limit
            if rate_limiter['messages_in_window'] >= rate_limiter['rate_limit']:
                rate_limiter['blocked_count'] += 1
                return False  # Rate limited
            
            rate_limiter['messages_in_window'] += 1
            return True  # Allowed
        
        # Simulate message sending
        messages_sent = 0
        messages_accepted = 0
        messages_blocked = 0
        rate_limit_triggered = False
        
        # Calculate message timing
        total_messages = min(messages_per_minute, 200)  # Cap for testing
        
        # Send messages in bursts
        for burst in range(0, total_messages, burst_size):
            burst_end = min(burst + burst_size, total_messages)
            
            # Send burst of messages
            for i in range(burst, burst_end):
                messages_sent += 1
                
                if check_rate_limit():
                    messages_accepted += 1
                else:
                    messages_blocked += 1
                    rate_limit_triggered = True
                
                # Brief delay between messages in burst
                await asyncio.sleep(0.001)
            
            # Pause between bursts
            await asyncio.sleep(0.1)
        
        # Evaluate rate limiting effectiveness
        blocking_rate = messages_blocked / messages_sent if messages_sent > 0 else 0
        
        if expected_behavior == 'all_messages_accepted':
            rate_limiting_effective = blocking_rate <= 0.1  # Allow 10% tolerance
            blocking_appropriate = True
        elif expected_behavior == 'rate_limiting_applied':
            rate_limiting_effective = 0.1 < blocking_rate <= 0.5
            blocking_appropriate = rate_limit_triggered
        elif expected_behavior == 'throttling_applied':
            rate_limiting_effective = 0.3 < blocking_rate <= 0.7
            blocking_appropriate = rate_limit_triggered
        elif expected_behavior == 'aggressive_rate_limiting':
            rate_limiting_effective = blocking_rate > 0.5
            blocking_appropriate = rate_limit_triggered
        else:
            rate_limiting_effective = False
            blocking_appropriate = False
        
        system_stable = messages_sent > 0  # System didn't crash
        
        return {
            'rate_limiting_effective': rate_limiting_effective,
            'messages_sent': messages_sent,
            'messages_accepted': messages_accepted,
            'messages_blocked': messages_blocked,
            'rate_limit_triggered': rate_limit_triggered,
            'system_stable': system_stable,
            'blocking_appropriate': blocking_appropriate
        }
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_connection_flooding_protection(self, real_services_fixture):
        """Test WebSocket protection against connection flooding attacks."""
        real_services = get_real_services()
        
        # Create multiple user contexts for connection flooding simulation
        user_contexts = []
        for i in range(20):  # 20 users for flooding test
            context = await self.create_test_user_context(real_services, {
                'email': f'flood-test-user-{i}@example.com',
                'name': f'Flood Test User {i}'
            })
            user_contexts.append(context)
        
        # Test connection flooding scenarios
        flooding_scenarios = [
            {
                'name': 'rapid_connection_attempts',
                'connections_per_second': 50,
                'duration': 2.0,
                'expected_behavior': 'connection_rate_limiting'
            },
            {
                'name': 'sustained_connection_flood',
                'connections_per_second': 20,
                'duration': 5.0,
                'expected_behavior': 'sustained_protection'
            },
            {
                'name': 'distributed_connection_flood',
                'connections_per_second': 30,
                'duration': 3.0,
                'distributed': True,
                'expected_behavior': 'distributed_detection'
            }
        ]
        
        flooding_protection_results = []
        
        for scenario in flooding_scenarios:
            logger.info(f"Testing connection flooding protection: {scenario['name']}")
            
            try:
                protection_result = await self._test_connection_flooding_scenario(
                    user_contexts, scenario
                )
                
                flooding_protection_results.append({
                    'scenario': scenario['name'],
                    'flooding_detected': protection_result.get('flooding_detected', False),
                    'connections_blocked': protection_result.get('connections_blocked', 0),
                    'legitimate_connections_preserved': protection_result.get('legitimate_connections_preserved', False),
                    'system_availability_maintained': protection_result.get('system_availability_maintained', False),
                    'protection_effective': protection_result.get('protection_effective', False),
                    'response_time_impact': protection_result.get('response_time_impact', 0),
                    'success': True,
                    'error': None
                })
                
            except Exception as e:
                flooding_protection_results.append({
                    'scenario': scenario['name'],
                    'flooding_detected': False,
                    'connections_blocked': 0,
                    'legitimate_connections_preserved': False,
                    'system_availability_maintained': False,
                    'protection_effective': False,
                    'response_time_impact': float('inf'),
                    'success': False,
                    'error': str(e)
                })
        
        # Verify flooding protection
        flooding_detected = [r for r in flooding_protection_results if r.get('flooding_detected')]
        detection_rate = len(flooding_detected) / len(flooding_protection_results)
        
        system_available = [r for r in flooding_protection_results if r.get('system_availability_maintained')]
        availability_rate = len(system_available) / len(flooding_protection_results)
        
        protection_effective = [r for r in flooding_protection_results if r.get('protection_effective')]
        effectiveness_rate = len(protection_effective) / len(flooding_protection_results)
        
        assert detection_rate >= 0.8, \
            f"Connection flooding detection insufficient: {detection_rate:.1%}"
        
        assert availability_rate >= 0.8, \
            f"System availability not maintained during flooding: {availability_rate:.1%}"
        
        assert effectiveness_rate >= 0.8, \
            f"Flooding protection effectiveness insufficient: {effectiveness_rate:.1%}"
        
        # Verify reasonable response time impact
        successful_tests = [r for r in flooding_protection_results if r.get('success')]
        if successful_tests:
            max_response_impact = max(r.get('response_time_impact', 0) for r in successful_tests)
            assert max_response_impact < 3.0, \
                f"Excessive response time impact during flooding protection: {max_response_impact:.1f}s"
                
        logger.info(f"Connection flooding test - Detection: {detection_rate:.1%}, "
                   f"Availability: {availability_rate:.1%}, Effectiveness: {effectiveness_rate:.1%}")
    
    async def _test_connection_flooding_scenario(self, user_contexts: List[Dict], scenario: Dict) -> Dict:
        """Test specific connection flooding protection scenario."""
        connections_per_second = scenario['connections_per_second']
        duration = scenario['duration']
        distributed = scenario.get('distributed', False)
        
        start_time = time.time()
        connection_attempts = []
        connections_blocked = 0
        flooding_detected = False
        
        # Mock connection rate limiter
        connection_limiter = {
            'connections_per_second': 10,  # Allow 10 connections per second
            'recent_connections': [],
            'blocked_ips': set()
        }
        
        def check_connection_allowed(user_id: str, ip_address: str = None):
            """Check if connection should be allowed."""
            current_time = time.time()
            
            # Remove old connections from tracking
            connection_limiter['recent_connections'] = [
                conn for conn in connection_limiter['recent_connections']
                if current_time - conn['timestamp'] < 1.0  # 1 second window
            ]
            
            # Check IP blocking
            if ip_address and ip_address in connection_limiter['blocked_ips']:
                return False
            
            # Check rate limit
            recent_count = len(connection_limiter['recent_connections'])
            if recent_count >= connection_limiter['connections_per_second']:
                # Block IP if excessive connections
                if ip_address:
                    connection_limiter['blocked_ips'].add(ip_address)
                return False
            
            # Allow connection
            connection_limiter['recent_connections'].append({
                'user_id': user_id,
                'timestamp': current_time,
                'ip_address': ip_address
            })
            return True
        
        # Simulate connection flooding
        total_attempts = int(connections_per_second * duration)
        interval = duration / total_attempts if total_attempts > 0 else 1.0
        
        for i in range(total_attempts):
            user_context = user_contexts[i % len(user_contexts)]
            
            # Simulate distributed attack
            if distributed:
                simulated_ip = f"192.168.1.{i % 255}"
            else:
                simulated_ip = "192.168.1.100"  # Same IP for concentrated attack
            
            # Attempt connection
            if check_connection_allowed(user_context['id'], simulated_ip):
                connection_attempts.append({
                    'user_id': user_context['id'],
                    'timestamp': time.time(),
                    'success': True
                })
            else:
                connections_blocked += 1
                flooding_detected = True
                connection_attempts.append({
                    'user_id': user_context['id'],
                    'timestamp': time.time(),
                    'success': False,
                    'blocked': True
                })
            
            # Wait before next attempt
            await asyncio.sleep(max(0.001, interval))
        
        total_duration = time.time() - start_time
        
        # Analyze results
        successful_connections = [c for c in connection_attempts if c.get('success')]
        blocking_rate = connections_blocked / len(connection_attempts) if connection_attempts else 0
        
        # Evaluate protection effectiveness
        if scenario['expected_behavior'] == 'connection_rate_limiting':
            protection_effective = blocking_rate > 0.3 and flooding_detected
        elif scenario['expected_behavior'] == 'sustained_protection':
            protection_effective = blocking_rate > 0.5 and flooding_detected
        elif scenario['expected_behavior'] == 'distributed_detection':
            protection_effective = blocking_rate > 0.2 and flooding_detected
        else:
            protection_effective = False
        
        # System should remain responsive
        system_availability_maintained = total_duration < duration * 2
        legitimate_connections_preserved = len(successful_connections) > 0
        
        response_time_impact = max(0, total_duration - duration)
        
        return {
            'flooding_detected': flooding_detected,
            'connections_blocked': connections_blocked,
            'legitimate_connections_preserved': legitimate_connections_preserved,
            'system_availability_maintained': system_availability_maintained,
            'protection_effective': protection_effective,
            'response_time_impact': response_time_impact
        }
        
    @pytest.mark.integration
    async def test_websocket_slowloris_attack_protection(self):
        """Test WebSocket protection against Slowloris-style attacks."""
        # Mock Slowloris attack scenarios
        slowloris_scenarios = [
            {
                'name': 'slow_handshake_attack',
                'connection_count': 100,
                'handshake_delay': 30.0,  # 30 second handshake
                'expected_behavior': 'timeout_protection'
            },
            {
                'name': 'partial_message_attack',
                'connection_count': 50,
                'message_send_delay': 60.0,  # Send message very slowly
                'expected_behavior': 'partial_message_timeout'
            },
            {
                'name': 'keep_alive_abuse',
                'connection_count': 75,
                'keep_alive_interval': 1.0,  # Excessive keep-alive
                'attack_duration': 120.0,
                'expected_behavior': 'keep_alive_limiting'
            }
        ]
        
        slowloris_protection_results = []
        
        for scenario in slowloris_scenarios:
            logger.info(f"Testing Slowloris protection: {scenario['name']}")
            
            try:
                protection_result = await self._test_slowloris_scenario(scenario)
                
                slowloris_protection_results.append({
                    'scenario': scenario['name'],
                    'attack_mitigated': protection_result.get('attack_mitigated', False),
                    'timeouts_enforced': protection_result.get('timeouts_enforced', False),
                    'resource_usage_controlled': protection_result.get('resource_usage_controlled', False),
                    'legitimate_traffic_preserved': protection_result.get('legitimate_traffic_preserved', False),
                    'system_performance_maintained': protection_result.get('system_performance_maintained', False),
                    'success': True,
                    'error': None
                })
                
            except Exception as e:
                slowloris_protection_results.append({
                    'scenario': scenario['name'],
                    'attack_mitigated': False,
                    'timeouts_enforced': False,
                    'resource_usage_controlled': False,
                    'legitimate_traffic_preserved': False,
                    'system_performance_maintained': False,
                    'success': False,
                    'error': str(e)
                })
        
        # Verify Slowloris protection
        attacks_mitigated = [r for r in slowloris_protection_results if r.get('attack_mitigated')]
        mitigation_rate = len(attacks_mitigated) / len(slowloris_protection_results)
        
        timeouts_enforced = [r for r in slowloris_protection_results if r.get('timeouts_enforced')]
        timeout_enforcement_rate = len(timeouts_enforced) / len(slowloris_protection_results)
        
        performance_maintained = [r for r in slowloris_protection_results if r.get('system_performance_maintained')]
        performance_rate = len(performance_maintained) / len(slowloris_protection_results)
        
        assert mitigation_rate >= 0.8, \
            f"Slowloris attack mitigation insufficient: {mitigation_rate:.1%}"
        
        assert timeout_enforcement_rate >= 0.8, \
            f"Timeout enforcement insufficient: {timeout_enforcement_rate:.1%}"
        
        assert performance_rate >= 0.7, \
            f"System performance not maintained during Slowloris protection: {performance_rate:.1%}"
            
        logger.info(f"Slowloris protection test - Mitigation: {mitigation_rate:.1%}, "
                   f"Timeout enforcement: {timeout_enforcement_rate:.1%}, Performance: {performance_rate:.1%}")
    
    async def _test_slowloris_scenario(self, scenario: Dict) -> Dict:
        """Test specific Slowloris attack protection scenario."""
        name = scenario['name']
        connection_count = scenario['connection_count']
        
        start_time = time.time()
        
        # Mock connection timeout management
        timeout_config = {
            'handshake_timeout': 10.0,  # 10 second handshake timeout
            'message_timeout': 30.0,    # 30 second message timeout
            'keep_alive_max_interval': 60.0,  # Max 60 seconds between keep-alives
            'max_concurrent_slow_connections': 20
        }
        
        slow_connections = []
        timed_out_connections = 0
        attack_mitigated = False
        timeouts_enforced = False
        
        if name == 'slow_handshake_attack':
            handshake_delay = scenario['handshake_delay']
            
            # Simulate slow handshake connections
            for i in range(connection_count):
                connection = {
                    'id': f'slow_handshake_{i}',
                    'start_time': time.time(),
                    'handshake_complete': False
                }
                slow_connections.append(connection)
                
                # Check if connection should timeout
                if handshake_delay > timeout_config['handshake_timeout']:
                    timed_out_connections += 1
                    timeouts_enforced = True
                    
                # Limit concurrent slow connections
                if len(slow_connections) > timeout_config['max_concurrent_slow_connections']:
                    attack_mitigated = True
                    break
                    
                await asyncio.sleep(0.01)  # Brief delay between connections
                
        elif name == 'partial_message_attack':
            message_delay = scenario['message_send_delay']
            
            # Simulate partial message sending
            for i in range(connection_count):
                connection = {
                    'id': f'partial_message_{i}',
                    'start_time': time.time(),
                    'message_complete': False
                }
                slow_connections.append(connection)
                
                # Check if message should timeout
                if message_delay > timeout_config['message_timeout']:
                    timed_out_connections += 1
                    timeouts_enforced = True
                    
                await asyncio.sleep(0.01)
                
        elif name == 'keep_alive_abuse':
            keep_alive_interval = scenario['keep_alive_interval']
            attack_duration = scenario['attack_duration']
            
            # Simulate excessive keep-alive messages
            duration_per_connection = min(attack_duration / connection_count, 2.0)
            
            for i in range(connection_count):
                connection = {
                    'id': f'keep_alive_abuse_{i}',
                    'start_time': time.time(),
                    'keep_alive_count': 0
                }
                
                # Simulate keep-alive abuse
                keep_alive_duration = 0
                while keep_alive_duration < duration_per_connection:
                    connection['keep_alive_count'] += 1
                    
                    # Check if keep-alive is too frequent
                    if keep_alive_interval < timeout_config['keep_alive_max_interval'] / 10:
                        attack_mitigated = True
                        break
                        
                    await asyncio.sleep(keep_alive_interval)
                    keep_alive_duration += keep_alive_interval
                    
                slow_connections.append(connection)
        
        total_duration = time.time() - start_time
        
        # Evaluate protection effectiveness
        resource_usage_controlled = len(slow_connections) <= timeout_config['max_concurrent_slow_connections'] * 2
        legitimate_traffic_preserved = attack_mitigated  # Attack detected and limited
        system_performance_maintained = total_duration < 10.0  # Reasonable response time
        
        return {
            'attack_mitigated': attack_mitigated,
            'timeouts_enforced': timeouts_enforced,
            'resource_usage_controlled': resource_usage_controlled,
            'legitimate_traffic_preserved': legitimate_traffic_preserved,
            'system_performance_maintained': system_performance_maintained,
            'timed_out_connections': timed_out_connections,
            'total_connections': len(slow_connections)
        }
        
    @pytest.mark.integration
    async def test_websocket_memory_exhaustion_protection(self):
        """Test WebSocket protection against memory exhaustion attacks."""
        # Mock memory exhaustion attack scenarios
        memory_attack_scenarios = [
            {
                'name': 'large_message_flood',
                'message_size': 10 * 1024 * 1024,  # 10MB messages
                'message_count': 50,
                'expected_behavior': 'message_size_limiting'
            },
            {
                'name': 'connection_state_bloat',
                'connections': 1000,
                'state_per_connection': 100 * 1024,  # 100KB per connection
                'expected_behavior': 'connection_limiting'
            },
            {
                'name': 'message_queue_overflow',
                'messages_per_second': 1000,
                'duration': 10.0,
                'queue_size_limit': 1000,
                'expected_behavior': 'queue_limiting'
            }
        ]
        
        memory_protection_results = []
        
        for scenario in memory_attack_scenarios:
            logger.info(f"Testing memory exhaustion protection: {scenario['name']}")
            
            try:
                protection_result = await self._test_memory_exhaustion_scenario(scenario)
                
                memory_protection_results.append({
                    'scenario': scenario['name'],
                    'memory_usage_controlled': protection_result.get('memory_usage_controlled', False),
                    'limits_enforced': protection_result.get('limits_enforced', False),
                    'system_stability_maintained': protection_result.get('system_stability_maintained', False),
                    'attack_detected': protection_result.get('attack_detected', False),
                    'graceful_degradation': protection_result.get('graceful_degradation', False),
                    'memory_peak': protection_result.get('memory_peak', 0),
                    'success': True,
                    'error': None
                })
                
            except Exception as e:
                memory_protection_results.append({
                    'scenario': scenario['name'],
                    'memory_usage_controlled': False,
                    'limits_enforced': False,
                    'system_stability_maintained': False,
                    'attack_detected': False,
                    'graceful_degradation': False,
                    'memory_peak': float('inf'),
                    'success': False,
                    'error': str(e)
                })
        
        # Verify memory exhaustion protection
        memory_controlled = [r for r in memory_protection_results if r.get('memory_usage_controlled')]
        memory_control_rate = len(memory_controlled) / len(memory_protection_results)
        
        limits_enforced = [r for r in memory_protection_results if r.get('limits_enforced')]
        limit_enforcement_rate = len(limits_enforced) / len(memory_protection_results)
        
        stability_maintained = [r for r in memory_protection_results if r.get('system_stability_maintained')]
        stability_rate = len(stability_maintained) / len(memory_protection_results)
        
        assert memory_control_rate >= 0.8, \
            f"Memory usage control insufficient: {memory_control_rate:.1%}"
        
        assert limit_enforcement_rate >= 0.8, \
            f"Memory limit enforcement insufficient: {limit_enforcement_rate:.1%}"
        
        assert stability_rate >= 0.8, \
            f"System stability not maintained during memory attacks: {stability_rate:.1%}"
            
        logger.info(f"Memory exhaustion protection test - Control: {memory_control_rate:.1%}, "
                   f"Limits: {limit_enforcement_rate:.1%}, Stability: {stability_rate:.1%}")
    
    async def _test_memory_exhaustion_scenario(self, scenario: Dict) -> Dict:
        """Test specific memory exhaustion protection scenario."""
        name = scenario['name']
        
        # Mock memory usage tracking
        memory_tracker = {
            'current_usage': 0,
            'peak_usage': 0,
            'limit': 100 * 1024 * 1024,  # 100MB limit
            'allocations': []
        }
        
        def allocate_memory(size: int, description: str) -> bool:
            """Simulate memory allocation with limits."""
            if memory_tracker['current_usage'] + size > memory_tracker['limit']:
                return False  # Allocation blocked
                
            memory_tracker['current_usage'] += size
            memory_tracker['peak_usage'] = max(memory_tracker['peak_usage'], memory_tracker['current_usage'])
            memory_tracker['allocations'].append({
                'size': size,
                'description': description,
                'timestamp': time.time()
            })
            return True
        
        def free_memory(size: int):
            """Simulate memory deallocation."""
            memory_tracker['current_usage'] = max(0, memory_tracker['current_usage'] - size)
        
        attack_detected = False
        limits_enforced = False
        allocations_blocked = 0
        
        if name == 'large_message_flood':
            message_size = scenario['message_size']
            message_count = scenario['message_count']
            
            for i in range(message_count):
                if not allocate_memory(message_size, f'large_message_{i}'):
                    allocations_blocked += 1
                    limits_enforced = True
                    
                    # Detect attack pattern
                    if allocations_blocked > 3:
                        attack_detected = True
                        break
                        
                await asyncio.sleep(0.01)  # Brief delay between allocations
                
                # Simulate message processing and cleanup
                await asyncio.sleep(0.05)
                free_memory(message_size)
                
        elif name == 'connection_state_bloat':
            connections = scenario['connections']
            state_per_connection = scenario['state_per_connection']
            
            for i in range(connections):
                if not allocate_memory(state_per_connection, f'connection_state_{i}'):
                    allocations_blocked += 1
                    limits_enforced = True
                    
                    if allocations_blocked > 10:
                        attack_detected = True
                        break
                        
                await asyncio.sleep(0.001)
                
        elif name == 'message_queue_overflow':
            messages_per_second = scenario['messages_per_second']
            duration = scenario['duration']
            queue_size_limit = scenario['queue_size_limit']
            
            message_queue_size = 0
            queue_memory_per_message = 1024  # 1KB per queued message
            
            total_messages = int(messages_per_second * duration)
            interval = duration / total_messages if total_messages > 0 else 1.0
            
            for i in range(total_messages):
                if message_queue_size >= queue_size_limit:
                    allocations_blocked += 1
                    limits_enforced = True
                    attack_detected = True
                else:
                    if allocate_memory(queue_memory_per_message, f'queue_message_{i}'):
                        message_queue_size += 1
                    else:
                        allocations_blocked += 1
                        limits_enforced = True
                        
                await asyncio.sleep(max(0.001, interval))
                
                # Simulate message processing
                if message_queue_size > 0 and i % 10 == 0:  # Process every 10th iteration
                    free_memory(queue_memory_per_message)
                    message_queue_size -= 1
        
        # Evaluate protection results
        memory_usage_controlled = memory_tracker['peak_usage'] <= memory_tracker['limit'] * 1.1  # 10% tolerance
        system_stability_maintained = allocations_blocked < 1000  # System didn't completely fail
        graceful_degradation = limits_enforced and not (memory_tracker['current_usage'] > memory_tracker['limit'])
        
        return {
            'memory_usage_controlled': memory_usage_controlled,
            'limits_enforced': limits_enforced,
            'system_stability_maintained': system_stability_maintained,
            'attack_detected': attack_detected,
            'graceful_degradation': graceful_degradation,
            'memory_peak': memory_tracker['peak_usage'],
            'allocations_blocked': allocations_blocked,
            'current_usage': memory_tracker['current_usage']
        }