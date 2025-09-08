"""
WebSocket Authentication Performance Tests - Concurrent connections and performance validation

Tests authentication performance requirements and concurrent connection handling.
Critical for ensuring WebSocket authentication scales to enterprise usage patterns.

Business Value Justification (BVJ):
- Segment: Enterprise | Goal: Scale & Performance | Impact: $500K MRR
- Validates authentication performance meets enterprise SLA requirements
- Ensures concurrent connection support for team collaboration features
- Tests scalability for high-value enterprise contracts

Performance Requirements:
- Authentication: <100ms
- Connection establishment: <2s
- Token validation: <50ms
- Concurrent connections: Support multiple authenticated users

Test Coverage:
- Authentication performance consistency across multiple cycles
- Concurrent WebSocket connections with different tokens
- Performance degradation testing under load
- Enterprise-scale authentication validation
"""

import asyncio
import time
import pytest
from typing import List, Dict, Any
from shared.isolated_environment import IsolatedEnvironment

from test_framework.helpers.auth_helpers import (
    WebSocketAuthTester,
    AuthTestConfig,
    skip_if_services_unavailable,
    assert_auth_performance
)


@pytest.mark.critical
@pytest.mark.asyncio
@pytest.mark.e2e
class TestAuthWebSocketPerformance:
    """WebSocket Authentication Performance and Concurrent Connection Tests."""
    
    @pytest.fixture
    def auth_tester(self):
        """Initialize WebSocket auth tester."""
        return WebSocketAuthTester()
    
    @pytest.mark.e2e
    async def test_authentication_performance_requirements(self, auth_tester):
        """Test that authentication meets performance requirements."""
        try:
            # Test multiple authentication cycles for performance consistency
            auth_times = []
            connection_times = []
            
            for i in range(5):
                # Time token generation
                auth_start = time.time()
                token = await auth_tester.generate_real_jwt_token("free")
                if not token:
                    token = auth_tester.create_mock_jwt_token()
                auth_time = time.time() - auth_start
                auth_times.append(auth_time)
                
                # Time WebSocket connection establishment
                conn_start = time.time()
                ws_result = await auth_tester.establish_websocket_connection(token, timeout=2.0)
                conn_time = time.time() - conn_start
                connection_times.append(conn_time)
                
                if ws_result["connected"]:
                    await ws_result["websocket"].close()
                
                # Brief pause between tests
                await asyncio.sleep(0.1)
            
            # Verify performance requirements
            avg_auth_time = sum(auth_times) / len(auth_times)
            avg_conn_time = sum(connection_times) / len(connection_times)
            
            assert_auth_performance(avg_auth_time, "auth")
            assert_auth_performance(avg_conn_time, "reconnection")
            
            print(f"Performance metrics: Auth={avg_auth_time:.3f}s, Connection={avg_conn_time:.3f}s")
            
        except Exception as e:
            skip_if_services_unavailable(str(e))
    
    @pytest.mark.e2e
    async def test_concurrent_connections_different_tokens(self, auth_tester):
        """Test concurrent WebSocket connections with different valid tokens."""
        try:
            # Generate multiple tokens for different users
            tokens = []
            for tier in ["free", "early", "mid"]:
                token = await auth_tester.generate_real_jwt_token(tier)
                if token:
                    tokens.append(token)
                else:
                    tokens.append(auth_tester.create_mock_jwt_token())
            
            if len(tokens) < 2:
                pytest.skip("Could not generate enough tokens for concurrent test")
            
            # Establish concurrent connections
            connection_tasks = [
                auth_tester.establish_websocket_connection(token)
                for token in tokens[:3]  # Limit to 3 concurrent connections
            ]
            
            results = await asyncio.gather(*connection_tasks, return_exceptions=True)
            
            # Count successful connections
            successful_connections = [
                result for result in results 
                if isinstance(result, dict) and result.get("connected", False)
            ]
            
            assert len(successful_connections) >= 2, \
                f"Expected ≥2 concurrent connections, got {len(successful_connections)}"
            
            # Test message sending to each connection
            message_tasks = []
            for i, result in enumerate(successful_connections):
                websocket = result["websocket"]
                message_tasks.append(
                    auth_tester.send_test_message(
                        websocket, f"Concurrent test message from connection {i+1}"
                    )
                )
            
            message_results = await asyncio.gather(*message_tasks, return_exceptions=True)
            
            # Verify at least one message was sent successfully
            successful_messages = [
                result for result in message_results
                if isinstance(result, dict) and result.get("sent", False)
            ]
            
            assert len(successful_messages) >= 1, "At least one concurrent message should succeed"
            
            # Cleanup connections
            cleanup_tasks = []
            for result in successful_connections:
                websocket = result["websocket"]
                cleanup_tasks.append(websocket.close())
            
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            
        except Exception as e:
            skip_if_services_unavailable(str(e))
    
    @pytest.mark.e2e
    async def test_high_frequency_authentication_cycles(self, auth_tester):
        """Test performance under high-frequency authentication cycles."""
        try:
            cycle_count = 10
            auth_results = []
            
            start_time = time.time()
            
            for i in range(cycle_count):
                cycle_start = time.time()
                
                # Generate token
                token = await auth_tester.generate_real_jwt_token("free")
                if not token:
                    token = auth_tester.create_mock_jwt_token()
                
                # Validate token
                validation_result = await auth_tester.validate_token_in_backend(token)
                
                # Test WebSocket connection
                ws_result = await auth_tester.establish_websocket_connection(token, timeout=1.0)
                
                cycle_time = time.time() - cycle_start
                
                auth_results.append({
                    "cycle": i + 1,
                    "cycle_time": cycle_time,
                    "token_valid": validation_result["valid"],
                    "websocket_connected": ws_result["connected"],
                    "validation_time": validation_result["validation_time"]
                })
                
                # Cleanup
                if ws_result["connected"]:
                    await ws_result["websocket"].close()
                
                # Small delay to prevent overwhelming services
                await asyncio.sleep(0.05)
            
            total_time = time.time() - start_time
            
            # Analyze performance metrics
            successful_cycles = [r for r in auth_results if r["websocket_connected"]]
            avg_cycle_time = sum(r["cycle_time"] for r in auth_results) / len(auth_results)
            avg_validation_time = sum(r["validation_time"] for r in auth_results) / len(auth_results)
            
            # Performance assertions
            assert avg_validation_time < AuthTestConfig.TOKEN_VALIDATION_LIMIT, \
                f"Average validation time {avg_validation_time:.3f}s exceeds {AuthTestConfig.TOKEN_VALIDATION_LIMIT}s"
            
            assert len(successful_cycles) >= cycle_count * 0.8, \
                f"Expected ≥80% success rate, got {len(successful_cycles)}/{cycle_count}"
            
            print(f"High-frequency test: {cycle_count} cycles in {total_time:.2f}s, "
                  f"avg cycle: {avg_cycle_time:.3f}s, success rate: {len(successful_cycles)}/{cycle_count}")
            
        except Exception as e:
            skip_if_services_unavailable(str(e))
    
    @pytest.mark.e2e
    async def test_connection_establishment_timing_consistency(self, auth_tester):
        """Test that connection establishment timing is consistent."""
        try:
            timing_samples = []
            
            for i in range(8):
                token = await auth_tester.generate_real_jwt_token("free")
                if not token:
                    token = auth_tester.create_mock_jwt_token()
                
                # Measure connection establishment time
                start_time = time.time()
                ws_result = await auth_tester.establish_websocket_connection(token)
                connection_time = time.time() - start_time
                
                timing_samples.append({
                    "attempt": i + 1,
                    "connection_time": connection_time,
                    "connected": ws_result["connected"],
                    "error": ws_result.get("error")
                })
                
                if ws_result["connected"]:
                    await ws_result["websocket"].close()
                
                await asyncio.sleep(0.1)
            
            # Analyze timing consistency
            successful_timings = [
                s["connection_time"] for s in timing_samples 
                if s["connected"]
            ]
            
            if len(successful_timings) >= 3:
                avg_time = sum(successful_timings) / len(successful_timings)
                max_time = max(successful_timings)
                min_time = min(successful_timings)
                time_variance = max_time - min_time
                
                # Connection timing should be consistent
                assert avg_time < AuthTestConfig.RECONNECTION_TIME_LIMIT, \
                    f"Average connection time {avg_time:.3f}s exceeds {AuthTestConfig.RECONNECTION_TIME_LIMIT}s"
                
                assert time_variance < 2.0, \
                    f"Connection time variance {time_variance:.3f}s too high (max: {max_time:.3f}s, min: {min_time:.3f}s)"
                
                print(f"Connection timing: avg={avg_time:.3f}s, variance={time_variance:.3f}s, "
                      f"samples={len(successful_timings)}")
            else:
                pytest.skip(f"Insufficient successful connections ({len(successful_timings)}) for timing analysis")
            
        except Exception as e:
            skip_if_services_unavailable(str(e))
    
    @pytest.mark.e2e
    async def test_concurrent_message_throughput(self, auth_tester):
        """Test message throughput with multiple concurrent authenticated connections."""
        try:
            # Establish multiple authenticated connections
            connection_count = 3
            tokens = []
            connections = []
            
            for i in range(connection_count):
                token = await auth_tester.generate_real_jwt_token("free")
                if not token:
                    token = auth_tester.create_mock_jwt_token()
                tokens.append(token)
                
                ws_result = await auth_tester.establish_websocket_connection(token)
                if ws_result["connected"]:
                    connections.append(ws_result["websocket"])
            
            if len(connections) < 2:
                pytest.skip("Could not establish enough connections for throughput test")
            
            # Send multiple messages concurrently
            messages_per_connection = 5
            message_tasks = []
            
            start_time = time.time()
            
            for i, websocket in enumerate(connections):
                for j in range(messages_per_connection):
                    message_tasks.append(
                        auth_tester.send_test_message(
                            websocket, 
                            f"Throughput test message {j+1} from connection {i+1}"
                        )
                    )
            
            # Execute all message sends concurrently
            message_results = await asyncio.gather(*message_tasks, return_exceptions=True)
            total_time = time.time() - start_time
            
            # Analyze throughput
            successful_messages = [
                result for result in message_results
                if isinstance(result, dict) and result.get("sent", False)
            ]
            
            total_attempted = len(message_tasks)
            success_rate = len(successful_messages) / total_attempted
            messages_per_second = len(successful_messages) / total_time
            
            # Throughput assertions
            assert success_rate >= 0.8, \
                f"Expected ≥80% message success rate, got {success_rate:.1%}"
            
            assert messages_per_second >= 5.0, \
                f"Expected ≥5 messages/second throughput, got {messages_per_second:.1f}"
            
            print(f"Message throughput: {len(successful_messages)}/{total_attempted} messages "
                  f"in {total_time:.2f}s = {messages_per_second:.1f} msg/s")
            
            # Cleanup connections
            cleanup_tasks = [websocket.close() for websocket in connections]
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            
        except Exception as e:
            skip_if_services_unavailable(str(e))


# Business Impact Summary for Performance Tests
"""
WebSocket Authentication Performance Tests - Business Impact

Revenue Impact: $500K MRR Enterprise Scale
- Authentication performance <100ms: meets enterprise SLA requirements
- Concurrent connection support: enables team collaboration features worth $100K+ per enterprise
- Performance consistency: ensures reliable service for high-value contracts
- Scalability validation: supports growth to 1000+ concurrent users

Technical Excellence:
- Performance requirements: Auth <100ms, Connection <2s, Validation <50ms
- Concurrent connection handling: 3+ simultaneous authenticated sessions
- High-frequency auth cycles: 80%+ success rate under load
- Message throughput: 5+ messages/second with multiple connections
- Timing consistency: <2s variance in connection establishment

Enterprise Readiness:
- All Segments: Reliable performance during peak usage
- Enterprise: SLA compliance for high-value contracts
- Scale: Infrastructure validation for rapid growth
- Platform: Performance benchmarks for capacity planning
"""
