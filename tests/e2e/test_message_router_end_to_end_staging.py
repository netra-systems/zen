"""
E2E Tests for MessageRouter on Staging Environment - GitHub Issue #217

Business Value Justification:
- Segment: Platform/Production (Enterprise reliability)
- Business Goal: Production-grade chat reliability
- Value Impact: Validate complete user message routing end-to-end
- Strategic Impact: Ensure $500K+ ARR chat works in production-like environment

These tests are designed to FAIL initially to reproduce real-world routing issues.
Tests run against staging GCP environment with real services (no Docker required).
"""

import asyncio
import json
import uuid
import time
from typing import Dict, List, Any, Optional
import requests
import websockets
from urllib.parse import urljoin

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment


class TestMessageRouterEndToEndStaging(SSotAsyncTestCase):
    """E2E tests for MessageRouter against staging environment."""
    
    async def asyncSetUp(self):
        """Set up E2E test environment for staging."""
        await super().asyncSetUp()
        
        # Get staging environment configuration
        self.env = IsolatedEnvironment()
        self.staging_base_url = self.env.get_env('STAGING_BASE_URL', 'https://netra-staging.example.com')
        self.staging_ws_url = self.env.get_env('STAGING_WS_URL', 'wss://netra-staging.example.com/ws')
        
        # Test credentials for staging
        self.test_user_email = self.env.get_env('STAGING_TEST_USER_EMAIL', 'test@example.com')
        self.test_user_password = self.env.get_env('STAGING_TEST_PASSWORD', 'test_password')
        
        # Track E2E test state
        self.staging_auth_token = None
        self.staging_user_id = None
        self.websocket_connections = []
        self.e2e_failures = []
        self.golden_path_events = []
        
    async def asyncTearDown(self):
        """Clean up E2E resources."""
        # Close all WebSocket connections
        for ws in self.websocket_connections:
            try:
                await ws.close()
            except Exception:
                pass
        
        await super().asyncTearDown()
        
    async def authenticate_staging_user(self) -> bool:
        """Authenticate against staging environment."""
        try:
            auth_url = urljoin(self.staging_base_url, '/auth/login')
            auth_data = {
                'email': self.test_user_email,
                'password': self.test_user_password
            }
            
            response = requests.post(auth_url, json=auth_data, timeout=10)
            
            if response.status_code == 200:
                auth_result = response.json()
                self.staging_auth_token = auth_result.get('access_token')
                self.staging_user_id = auth_result.get('user_id')
                return True
            else:
                self.e2e_failures.append({
                    'step': 'authentication',
                    'error': f'Auth failed: {response.status_code}',
                    'response': response.text
                })
                return False
                
        except Exception as e:
            self.e2e_failures.append({
                'step': 'authentication',
                'error': str(e),
                'context': 'staging authentication'
            })
            return False
            
    async def create_staging_websocket_connection(self) -> Optional[Any]:
        """Create WebSocket connection to staging environment."""
        try:
            # Construct WebSocket URL with auth
            ws_url = f"{self.staging_ws_url}?token={self.staging_auth_token}"
            
            # Connect to staging WebSocket
            websocket = await websockets.connect(
                ws_url,
                extra_headers={'Authorization': f'Bearer {self.staging_auth_token}'},
                timeout=10
            )
            
            self.websocket_connections.append(websocket)
            return websocket
            
        except Exception as e:
            self.e2e_failures.append({
                'step': 'websocket_connection',
                'error': str(e),
                'context': 'staging WebSocket connection'
            })
            return None
            
    async def test_complete_user_message_routing_staging(self):
        """
        Test complete user message routing end-to-end on staging.
        This should FAIL initially, revealing real-world routing issues.
        """
        # Step 1: Authenticate
        auth_success = await self.authenticate_staging_user()
        
        # This should FAIL if auth is broken
        self.assertTrue(
            auth_success,
            f"STAGING AUTH FAILURE: Cannot authenticate test user. "
            f"Failures: {self.e2e_failures}"
        )
        
        # Step 2: Establish WebSocket connection
        websocket = await self.create_staging_websocket_connection()
        
        # This should FAIL if WebSocket connection fails
        self.assertIsNotNone(
            websocket,
            f"STAGING WEBSOCKET FAILURE: Cannot connect to staging WebSocket. "
            f"Failures: {self.e2e_failures}"
        )
        
        try:
            # Step 3: Send user message through staging MessageRouter
            user_message = {
                'type': 'user_message',
                'content': {
                    'text': 'Help me analyze my AI infrastructure costs',
                    'user_id': self.staging_user_id,
                    'timestamp': time.time()
                },
                'user_id': self.staging_user_id,
                'id': str(uuid.uuid4())
            }
            
            await websocket.send(json.dumps(user_message))
            self.golden_path_events.append({
                'step': 'user_message_sent',
                'timestamp': time.time(),
                'success': True
            })
            
            # Step 4: Wait for agent events to be routed back
            expected_events = [
                'agent_started',
                'agent_thinking', 
                'tool_executing',
                'tool_completed',
                'agent_completed'
            ]
            
            received_events = []
            timeout_start = time.time()
            timeout_duration = 30  # 30 seconds timeout
            
            while len(received_events) < len(expected_events):
                if time.time() - timeout_start > timeout_duration:
                    break
                    
                try:
                    # Wait for message with timeout
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    
                    try:
                        parsed_message = json.loads(message)
                        event_type = parsed_message.get('type', '')
                        
                        if event_type in expected_events:
                            received_events.append({
                                'type': event_type,
                                'timestamp': time.time(),
                                'content': parsed_message
                            })
                            
                            self.golden_path_events.append({
                                'step': f'received_{event_type}',
                                'timestamp': time.time(),
                                'success': True
                            })
                            
                    except json.JSONDecodeError:
                        self.e2e_failures.append({
                            'step': 'message_parsing',
                            'error': 'Invalid JSON received',
                            'raw_message': message
                        })
                        
                except asyncio.TimeoutError:
                    # Continue waiting, but track timeout
                    self.e2e_failures.append({
                        'step': 'event_timeout',
                        'error': 'Timeout waiting for agent events',
                        'expected_remaining': [e for e in expected_events 
                                             if e not in [r['type'] for r in received_events]]
                    })
                    
            # Step 5: Validate complete golden path
            missing_events = [e for e in expected_events 
                            if e not in [r['type'] for r in received_events]]
            
            # This assertion should FAIL, revealing missing events
            self.assertEqual(
                len(missing_events), 0,
                f"STAGING GOLDEN PATH FAILURE: Missing {len(missing_events)} critical events. "
                f"Missing: {missing_events}. Received: {[r['type'] for r in received_events]}. "
                f"All failures: {self.e2e_failures}"
            )
            
        except Exception as e:
            # This should FAIL, revealing the E2E issue
            self.fail(
                f"STAGING E2E EXCEPTION: {e}. "
                f"Golden path events: {self.golden_path_events}. "
                f"All failures: {self.e2e_failures}"
            )
            
    async def test_multiple_concurrent_users_staging_isolation(self):
        """
        Test multiple concurrent users on staging have isolated routing.
        This should FAIL initially, revealing user isolation issues in production.
        """
        concurrent_failures = []
        user_sessions = []
        
        try:
            # Create multiple user sessions
            num_concurrent_users = 3
            
            for i in range(num_concurrent_users):
                # Authenticate each user (using same creds for test)
                auth_success = await self.authenticate_staging_user()
                
                if auth_success:
                    # Create WebSocket for each user
                    websocket = await self.create_staging_websocket_connection()
                    
                    if websocket:
                        user_sessions.append({
                            'user_index': i,
                            'user_id': f"{self.staging_user_id}_session_{i}",
                            'websocket': websocket,
                            'messages_sent': [],
                            'messages_received': []
                        })
                    else:
                        concurrent_failures.append({
                            'user_index': i,
                            'error': 'WebSocket connection failed',
                            'step': 'connection_creation'
                        })
                else:
                    concurrent_failures.append({
                        'user_index': i,
                        'error': 'Authentication failed',
                        'step': 'authentication'
                    })
            
            # Send concurrent messages from all users
            async def send_user_message(session: Dict) -> Dict:
                """Send message from a specific user session."""
                try:
                    message = {
                        'type': 'user_message',
                        'content': {
                            'text': f'Concurrent message from user {session["user_index"]}',
                            'user_id': session['user_id'],
                            'session_marker': f'session_{session["user_index"]}'
                        },
                        'user_id': session['user_id'],
                        'id': str(uuid.uuid4())
                    }
                    
                    await session['websocket'].send(json.dumps(message))
                    session['messages_sent'].append(message)
                    
                    # Wait for response
                    try:
                        response = await asyncio.wait_for(
                            session['websocket'].recv(),
                            timeout=10.0
                        )
                        
                        parsed_response = json.loads(response)
                        session['messages_received'].append(parsed_response)
                        
                        return {
                            'user_index': session['user_index'],
                            'success': True,
                            'response_received': True
                        }
                        
                    except asyncio.TimeoutError:
                        return {
                            'user_index': session['user_index'],
                            'success': False,
                            'error': 'Response timeout'
                        }
                        
                except Exception as e:
                    concurrent_failures.append({
                        'user_index': session['user_index'],
                        'error': str(e),
                        'step': 'message_sending'
                    })
                    
                    return {
                        'user_index': session['user_index'],
                        'success': False,
                        'error': str(e)
                    }
            
            # Execute concurrent messaging
            if user_sessions:
                tasks = [send_user_message(session) for session in user_sessions]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Check for isolation violations
                failed_users = [
                    r for r in results 
                    if isinstance(r, dict) and not r.get('success', False)
                ]
                
                # This assertion should FAIL, revealing isolation issues
                self.assertEqual(
                    len(failed_users), 0,
                    f"STAGING USER ISOLATION FAILURE: {len(failed_users)} users failed. "
                    f"Failed users: {failed_users}. "
                    f"Concurrent failures: {concurrent_failures}"
                )
            else:
                # This should FAIL if no user sessions created
                self.fail(
                    f"STAGING SESSION CREATION FAILURE: No user sessions created. "
                    f"Failures: {concurrent_failures}"
                )
                
        except Exception as e:
            # This should FAIL, revealing the concurrent user issue
            self.fail(
                f"STAGING CONCURRENT USER EXCEPTION: {e}. "
                f"Sessions: {len(user_sessions)}. Failures: {concurrent_failures}"
            )
            
    async def test_business_critical_websocket_event_sequence_staging(self):
        """
        Test the business-critical WebSocket event sequence on staging.
        This should FAIL initially, revealing missing business-critical events.
        """
        business_critical_events = []
        sequence_violations = []
        
        try:
            # Authenticate and connect
            auth_success = await self.authenticate_staging_user()
            self.assertTrue(auth_success, "Authentication required for business critical test")
            
            websocket = await self.create_staging_websocket_connection()
            self.assertIsNotNone(websocket, "WebSocket connection required for business critical test")
            
            # Send business-critical user message
            critical_message = {
                'type': 'user_message',
                'content': {
                    'text': 'I need to reduce my AI costs by 30% while maintaining quality',
                    'user_id': self.staging_user_id,
                    'priority': 'business_critical',
                    'timestamp': time.time()
                },
                'user_id': self.staging_user_id,
                'id': str(uuid.uuid4())
            }
            
            await websocket.send(json.dumps(critical_message))
            
            # Define business-critical event sequence
            critical_event_sequence = [
                {'type': 'agent_started', 'max_wait': 5.0, 'business_critical': True},
                {'type': 'agent_thinking', 'max_wait': 10.0, 'business_critical': True},
                {'type': 'tool_executing', 'max_wait': 15.0, 'business_critical': True},
                {'type': 'tool_completed', 'max_wait': 10.0, 'business_critical': True},
                {'type': 'agent_completed', 'max_wait': 5.0, 'business_critical': True}
            ]
            
            # Track event sequence timing
            sequence_start = time.time()
            
            for expected_event in critical_event_sequence:
                event_start = time.time()
                event_received = False
                
                try:
                    # Wait for specific event with timeout
                    while time.time() - event_start < expected_event['max_wait']:
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                            parsed_message = json.loads(message)
                            
                            if parsed_message.get('type') == expected_event['type']:
                                business_critical_events.append({
                                    'type': expected_event['type'],
                                    'timestamp': time.time(),
                                    'latency': time.time() - event_start,
                                    'total_latency': time.time() - sequence_start,
                                    'content': parsed_message
                                })
                                event_received = True
                                break
                                
                        except asyncio.TimeoutError:
                            continue
                            
                    if not event_received:
                        sequence_violations.append({
                            'missing_event': expected_event['type'],
                            'max_wait_exceeded': expected_event['max_wait'],
                            'business_critical': expected_event['business_critical'],
                            'total_sequence_time': time.time() - sequence_start
                        })
                        
                except Exception as e:
                    sequence_violations.append({
                        'event': expected_event['type'],
                        'error': str(e),
                        'context': 'business critical event sequence'
                    })
            
            # Validate business-critical sequence completion
            missing_critical_events = [
                v for v in sequence_violations 
                if v.get('business_critical', False)
            ]
            
            # This assertion should FAIL, revealing missing business-critical events
            self.assertEqual(
                len(missing_critical_events), 0,
                f"BUSINESS CRITICAL EVENT FAILURE: {len(missing_critical_events)} critical events missing. "
                f"Missing: {missing_critical_events}. "
                f"Received events: {[e['type'] for e in business_critical_events]}. "
                f"All violations: {sequence_violations}"
            )
            
        except Exception as e:
            # This should FAIL, revealing the business-critical issue
            self.fail(
                f"BUSINESS CRITICAL SEQUENCE EXCEPTION: {e}. "
                f"Events received: {business_critical_events}. "
                f"Violations: {sequence_violations}"
            )


if __name__ == "__main__":
    # Run E2E tests
    import unittest
    unittest.main(verbosity=2)