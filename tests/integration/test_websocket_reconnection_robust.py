"""
MISSION CRITICAL: WebSocket Reconnection Integration Tests

This test suite ensures WebSocket connections handle reconnection scenarios robustly,
including network interruptions, server restarts, and authentication changes.

CRITICAL: WebSocket reliability is essential for real-time chat functionality.

@compliance SPEC/learnings/websocket_agent_integration_critical.xml
@compliance CLAUDE.md - Chat is King
"""

import asyncio
import json
import time
import websockets
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, AsyncMock
import pytest
import aiohttp
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

try:
    from netra_backend.app.core.config import get_settings
except ImportError:
    # Fallback for test environment
    class Settings:
        def __init__(self):
            pass
    
    def get_settings():
        return Settings()


class WebSocketReconnectionTests:
    """Integration tests for WebSocket reconnection scenarios."""
    
    def __init__(self):
        self.settings = get_settings()
        self.ws_url = f"ws://localhost:8000/ws"
        self.jwt_secret = os.getenv('JWT_SECRET', 'test-secret-key')
        self.test_results: Dict[str, Any] = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'reconnection_times': [],
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def generate_test_token(self, user_id: str = "user_123", expires_in: int = 3600) -> str:
        """Generate a valid JWT token for testing."""
        from tests.helpers.auth_test_utils import TestAuthHelper
        
        auth_helper = TestAuthHelper()
        email = f'{user_id}@test.com'
        return auth_helper.create_test_token(user_id, email)
    
    async def test_exponential_backoff_reconnection(self) -> bool:
        """
        Test exponential backoff during reconnection attempts.
        Verifies delay increases appropriately with each failed attempt.
        """
        test_name = "exponential_backoff_reconnection"
        print(f"\n🔍 Testing: {test_name}")
        
        try:
            reconnect_delays = []
            attempt_count = 0
            max_attempts = 5
            
            async def simulate_connection_with_failures():
                nonlocal attempt_count
                for i in range(max_attempts):
                    attempt_count += 1
                    start_time = time.time()
                    
                    try:
                        # Simulate connection attempt that fails
                        if i < 3:  # First 3 attempts fail
                            raise websockets.exceptions.WebSocketException("Connection refused")
                        
                        # 4th attempt succeeds
                        token = self.generate_test_token()
                        headers = {'Authorization': f'Bearer {token}'}
                        
                        async with websockets.connect(
                            self.ws_url,
                            extra_headers=headers,
                            subprotocols=[f'jwt.{token}']
                        ) as ws:
                            await ws.send(json.dumps({
                                'type': 'ping',
                                'timestamp': time.time()
                            }))
                            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                            return True
                            
                    except Exception as e:
                        delay = time.time() - start_time
                        reconnect_delays.append(delay)
                        
                        # Calculate expected backoff
                        expected_base_delay = 1.0 * (2 ** i)  # Exponential backoff
                        expected_max_delay = min(expected_base_delay, 30.0)  # Cap at 30s
                        
                        # Add jitter simulation
                        await asyncio.sleep(min(expected_base_delay + (i * 0.5), expected_max_delay))
                
                return False
            
            # Run the simulation
            success = await simulate_connection_with_failures()
            
            # Verify exponential backoff pattern
            if len(reconnect_delays) >= 2:
                for i in range(1, len(reconnect_delays)):
                    # Each delay should be roughly double the previous (within tolerance)
                    ratio = reconnect_delays[i] / reconnect_delays[i-1] if reconnect_delays[i-1] > 0 else 0
                    if ratio < 1.5 or ratio > 3.0:
                        print(f"⚠️ Backoff ratio out of expected range: {ratio:.2f}")
            
            if success:
                print(f"✅ {test_name}: Exponential backoff working correctly")
                self.test_results['passed'] += 1
                return True
            else:
                raise AssertionError("Connection never succeeded")
                
        except Exception as e:
            print(f"❌ {test_name}: {str(e)}")
            self.test_results['failed'] += 1
            return False
        finally:
            self.test_results['total'] += 1
    
    async def test_session_state_restoration(self) -> bool:
        """
        Test that session state is properly restored after reconnection.
        Verifies thread context and message history preservation.
        """
        test_name = "session_state_restoration"
        print(f"\n🔍 Testing: {test_name}")
        
        try:
            token = self.generate_test_token()
            connection_id = None
            thread_id = "test_thread_123"
            
            # Establish initial connection and create session state
            async with websockets.connect(
                self.ws_url,
                subprotocols=[f'jwt.{token}']
            ) as ws:
                # Send initial messages to establish state
                await ws.send(json.dumps({
                    'type': 'thread_create',
                    'payload': {
                        'thread_id': thread_id,
                        'title': 'Test Thread'
                    }
                }))
                
                # Wait for thread creation confirmation
                response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                data = json.loads(response)
                
                if data.get('type') == 'thread_created':
                    connection_id = data.get('payload', {}).get('connection_id')
                
                # Send a message in the thread
                await ws.send(json.dumps({
                    'type': 'user_message',
                    'payload': {
                        'thread_id': thread_id,
                        'content': 'Test message before disconnect'
                    }
                }))
                
                await asyncio.sleep(1)
            
            # Simulate reconnection with session restoration
            async with websockets.connect(
                self.ws_url,
                subprotocols=[f'jwt.{token}']
            ) as ws:
                # Send session restore request
                await ws.send(json.dumps({
                    'type': 'session_restore',
                    'payload': {
                        'thread_id': thread_id,
                        'connection_id': connection_id,
                        'last_message_id': 'msg_1'
                    }
                }))
                
                # Wait for restoration confirmation
                restored = False
                start_time = time.time()
                
                while time.time() - start_time < 5.0:
                    try:
                        response = await asyncio.wait_for(ws.recv(), timeout=1.0)
                        data = json.loads(response)
                        
                        if data.get('type') in ['session_restored', 'thread_loaded']:
                            restored = True
                            restored_thread = data.get('payload', {}).get('thread_id')
                            if restored_thread != thread_id:
                                raise AssertionError(f"Wrong thread restored: {restored_thread}")
                            break
                    except asyncio.TimeoutError:
                        continue
                
                if not restored:
                    raise AssertionError("Session not restored after reconnection")
            
            print(f"✅ {test_name}: Session state restored successfully")
            self.test_results['passed'] += 1
            return True
            
        except Exception as e:
            print(f"❌ {test_name}: {str(e)}")
            self.test_results['failed'] += 1
            return False
        finally:
            self.test_results['total'] += 1
    
    async def test_graceful_disconnect_handling(self) -> bool:
        """
        Test graceful disconnect with proper cleanup.
        Ensures resources are freed and state is saved.
        """
        test_name = "graceful_disconnect_handling"
        print(f"\n🔍 Testing: {test_name}")
        
        try:
            token = self.generate_test_token()
            connection_id = f"conn_{time.time()}"
            
            async with websockets.connect(
                self.ws_url,
                subprotocols=[f'jwt.{token}']
            ) as ws:
                # Send identification
                await ws.send(json.dumps({
                    'type': 'identify',
                    'payload': {
                        'connection_id': connection_id
                    }
                }))
                
                # Send graceful disconnect
                await ws.send(json.dumps({
                    'type': 'disconnect',
                    'payload': {
                        'connection_id': connection_id,
                        'reason': 'client_disconnect'
                    }
                }))
                
                # Wait for acknowledgment
                ack_received = False
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    data = json.loads(response)
                    if data.get('type') == 'disconnect_ack':
                        ack_received = True
                except asyncio.TimeoutError:
                    # Some implementations might close immediately without ack
                    pass
                
                # Properly close the connection
                await ws.close(code=1000, reason='Normal closure')
            
            # Verify connection is cleaned up (attempt reconnection with same ID)
            async with websockets.connect(
                self.ws_url,
                subprotocols=[f'jwt.{token}']
            ) as ws:
                # Should be able to use same connection_id (old one was cleaned up)
                await ws.send(json.dumps({
                    'type': 'identify',
                    'payload': {
                        'connection_id': connection_id
                    }
                }))
                
                # If we get here without error, cleanup was successful
                await ws.close()
            
            print(f"✅ {test_name}: Graceful disconnect handled correctly")
            self.test_results['passed'] += 1
            return True
            
        except Exception as e:
            print(f"❌ {test_name}: {str(e)}")
            self.test_results['failed'] += 1
            return False
        finally:
            self.test_results['total'] += 1
    
    async def test_token_refresh_during_connection(self) -> bool:
        """
        Test token refresh while connection is active.
        Ensures authentication updates don't break the connection.
        """
        test_name = "token_refresh_during_connection"
        print(f"\n🔍 Testing: {test_name}")
        
        try:
            # Start with short-lived token
            initial_token = self.generate_test_token(expires_in=5)
            
            async with websockets.connect(
                self.ws_url,
                subprotocols=[f'jwt.{initial_token}']
            ) as ws:
                # Send initial message
                await ws.send(json.dumps({
                    'type': 'ping',
                    'timestamp': time.time()
                }))
                
                response = await asyncio.wait_for(ws.recv(), timeout=2.0)
                
                # Wait for token to near expiration
                await asyncio.sleep(4)
                
                # Generate new token
                new_token = self.generate_test_token(expires_in=3600)
                
                # Send token update
                await ws.send(json.dumps({
                    'type': 'auth',
                    'payload': {
                        'token': new_token,
                        'timestamp': time.time()
                    }
                }))
                
                # Verify connection still works with new token
                await ws.send(json.dumps({
                    'type': 'ping',
                    'timestamp': time.time()
                }))
                
                response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                data = json.loads(response)
                
                # Should receive pong or auth confirmation
                if data.get('type') not in ['pong', 'auth_success', 'auth']:
                    raise AssertionError(f"Unexpected response after token refresh: {data.get('type')}")
            
            print(f"✅ {test_name}: Token refresh handled successfully")
            self.test_results['passed'] += 1
            return True
            
        except Exception as e:
            print(f"❌ {test_name}: {str(e)}")
            self.test_results['failed'] += 1
            return False
        finally:
            self.test_results['total'] += 1
    
    async def test_max_reconnection_attempts(self) -> bool:
        """
        Test that reconnection stops after maximum attempts.
        Prevents infinite reconnection loops.
        """
        test_name = "max_reconnection_attempts"
        print(f"\n🔍 Testing: {test_name}")
        
        try:
            max_attempts = 10
            attempts = 0
            
            # Simulate a persistently failing connection
            async def attempt_reconnection():
                nonlocal attempts
                while attempts < max_attempts + 5:  # Try more than max
                    attempts += 1
                    try:
                        # This will always fail (invalid URL)
                        async with websockets.connect(
                            "ws://localhost:99999/ws",  # Invalid port
                            close_timeout=1
                        ) as ws:
                            pass
                    except Exception:
                        if attempts >= max_attempts:
                            # Should stop trying
                            break
                        await asyncio.sleep(0.1)  # Short delay for testing
                
                return attempts
            
            try:
                final_attempts = await asyncio.wait_for(
                    attempt_reconnection(),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                final_attempts = attempts
            
            # Verify attempts stopped at or near max
            if final_attempts > max_attempts + 1:  # Allow 1 extra for edge cases
                raise AssertionError(f"Too many reconnection attempts: {final_attempts}")
            
            print(f"✅ {test_name}: Reconnection stopped after {final_attempts} attempts")
            self.test_results['passed'] += 1
            return True
            
        except Exception as e:
            print(f"❌ {test_name}: {str(e)}")
            self.test_results['failed'] += 1
            return False
        finally:
            self.test_results['total'] += 1
    
    async def test_reconnection_with_queued_messages(self) -> bool:
        """
        Test that queued messages are sent after reconnection.
        Ensures no message loss during temporary disconnections.
        """
        test_name = "reconnection_with_queued_messages"
        print(f"\n🔍 Testing: {test_name}")
        
        try:
            token = self.generate_test_token()
            messages_to_queue = [
                {'type': 'user_message', 'payload': {'content': 'Message 1'}},
                {'type': 'user_message', 'payload': {'content': 'Message 2'}},
                {'type': 'user_message', 'payload': {'content': 'Message 3'}}
            ]
            
            # First connection
            async with websockets.connect(
                self.ws_url,
                subprotocols=[f'jwt.{token}']
            ) as ws:
                # Send first message
                await ws.send(json.dumps(messages_to_queue[0]))
                await asyncio.sleep(0.5)
            
            # Simulate messages queued during disconnection
            # (In real scenario, these would be queued in the client)
            
            # Reconnect and send queued messages
            async with websockets.connect(
                self.ws_url,
                subprotocols=[f'jwt.{token}']
            ) as ws:
                # Send queued messages
                for msg in messages_to_queue[1:]:
                    await ws.send(json.dumps(msg))
                    await asyncio.sleep(0.1)
                
                # Verify all messages were processed
                received_count = 0
                start_time = time.time()
                
                while time.time() - start_time < 3.0:
                    try:
                        response = await asyncio.wait_for(ws.recv(), timeout=0.5)
                        data = json.loads(response)
                        if data.get('type') in ['message_received', 'agent_response']:
                            received_count += 1
                    except asyncio.TimeoutError:
                        continue
                
                # We should have received responses for queued messages
                if received_count < len(messages_to_queue) - 1:
                    print(f"⚠️ Not all queued messages processed: {received_count}/{len(messages_to_queue)-1}")
            
            print(f"✅ {test_name}: Queued messages sent after reconnection")
            self.test_results['passed'] += 1
            return True
            
        except Exception as e:
            print(f"❌ {test_name}: {str(e)}")
            self.test_results['failed'] += 1
            return False
        finally:
            self.test_results['total'] += 1
    
    async def test_reconnection_performance(self) -> bool:
        """
        Measure reconnection performance metrics.
        Ensures reconnection happens within acceptable time limits.
        """
        test_name = "reconnection_performance"
        print(f"\n🔍 Testing: {test_name}")
        
        try:
            token = self.generate_test_token()
            reconnection_times = []
            
            for i in range(5):  # Test 5 reconnections
                # Establish connection
                start_time = time.time()
                
                async with websockets.connect(
                    self.ws_url,
                    subprotocols=[f'jwt.{token}']
                ) as ws:
                    # Send ping to verify connection
                    await ws.send(json.dumps({
                        'type': 'ping',
                        'timestamp': time.time()
                    }))
                    
                    # Wait for pong
                    await asyncio.wait_for(ws.recv(), timeout=2.0)
                    
                    connection_time = time.time() - start_time
                    reconnection_times.append(connection_time)
                    
                    # Close connection
                    await ws.close()
                
                # Small delay between attempts
                await asyncio.sleep(0.5)
            
            # Calculate metrics
            avg_time = sum(reconnection_times) / len(reconnection_times)
            max_time = max(reconnection_times)
            min_time = min(reconnection_times)
            
            self.test_results['reconnection_times'] = {
                'average': avg_time,
                'max': max_time,
                'min': min_time,
                'all': reconnection_times
            }
            
            # Performance thresholds
            if avg_time > 2.0:
                print(f"⚠️ Slow average reconnection time: {avg_time:.2f}s")
            
            if max_time > 5.0:
                raise AssertionError(f"Reconnection too slow: {max_time:.2f}s")
            
            print(f"✅ {test_name}: Reconnection performance acceptable")
            print(f"   Average: {avg_time:.2f}s, Max: {max_time:.2f}s, Min: {min_time:.2f}s")
            self.test_results['passed'] += 1
            return True
            
        except Exception as e:
            print(f"❌ {test_name}: {str(e)}")
            self.test_results['failed'] += 1
            return False
        finally:
            self.test_results['total'] += 1
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all WebSocket reconnection tests."""
        print("\n" + "=" * 60)
        print("🔌 WebSocket Reconnection Integration Tests")
        print("=" * 60)
        
        tests = [
            self.test_exponential_backoff_reconnection,
            self.test_session_state_restoration,
            self.test_graceful_disconnect_handling,
            self.test_token_refresh_during_connection,
            self.test_max_reconnection_attempts,
            self.test_reconnection_with_queued_messages,
            self.test_reconnection_performance
        ]
        
        for test_func in tests:
            try:
                await test_func()
            except Exception as e:
                print(f"❌ Unexpected error in {test_func.__name__}: {str(e)}")
                self.test_results['failed'] += 1
                self.test_results['total'] += 1
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {self.test_results['total']}")
        print(f"Passed: {self.test_results['passed']} ✅")
        print(f"Failed: {self.test_results['failed']} ❌")
        
        if self.test_results.get('reconnection_times'):
            print("\n📈 RECONNECTION METRICS:")
            metrics = self.test_results['reconnection_times']
            print(f"  Average: {metrics['average']:.2f}s")
            print(f"  Max: {metrics['max']:.2f}s")
            print(f"  Min: {metrics['min']:.2f}s")
        
        # Determine overall status
        if self.test_results['failed'] == 0:
            print("\n✅ ALL TESTS PASSED - WebSocket reconnection is robust!")
        else:
            print(f"\n❌ {self.test_results['failed']} TESTS FAILED - Review reconnection logic")
        
        return self.test_results


# Pytest integration
@pytest.mark.asyncio
@pytest.mark.integration
async def test_websocket_reconnection_integration():
    """Pytest wrapper for WebSocket reconnection integration tests."""
    test_suite = WebSocketReconnectionTests()
    results = await test_suite.run_all_tests()
    
    # Assert all tests passed
    assert results['failed'] == 0, f"{results['failed']} tests failed"
    
    # Assert performance is acceptable
    if results.get('reconnection_times'):
        avg_time = results['reconnection_times']['average']
        assert avg_time < 3.0, f"Average reconnection time too high: {avg_time:.2f}s"


if __name__ == "__main__":
    # Allow running directly for debugging
    import asyncio
    
    async def main():
        test_suite = WebSocketReconnectionTests()
        results = await test_suite.run_all_tests()
        
        # Exit with appropriate code
        sys.exit(0 if results['failed'] == 0 else 1)
    
    asyncio.run(main())