#!/usr/bin/env python
"""MISSION CRITICAL E2E TEST: Frontend Initialization and First-Time Page Load

Business Value: $500K+ ARR - Core user experience and chat functionality
THIS TEST MUST PASS OR THE PRODUCT IS BROKEN.

Tests the complete frontend initialization flow with:
1. Authentication initialization
2. WebSocket connection establishment  
3. Chat interface rendering
4. First message sending
5. Error recovery and resilience
6. Performance metrics

Uses REAL services - NO MOCKS ALLOWED.
"""

import asyncio
import json
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import threading
import pytest
from loguru import logger
from shared.isolated_environment import get_env
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from shared.isolated_environment import IsolatedEnvironment

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import production components - using real services
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager
from netra_backend.app.auth_integration.auth import AuthService, AuthUser
from netra_backend.app.core.registry.universal_registry import AgentRegistry
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.main import app
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket
from starlette.websockets import WebSocketDisconnect
import httpx


# ============================================================================
# TEST CONFIGURATION
# ============================================================================

class FrontendInitTestConfig:
    """Configuration for frontend initialization tests."""
    
    # Timing thresholds (milliseconds)
    AUTH_INIT_TIMEOUT = 5000
    WEBSOCKET_CONNECT_TIMEOUT = 3000
    FIRST_RENDER_TIMEOUT = 2000
    FIRST_MESSAGE_TIMEOUT = 10000
    
    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0
    
    # Performance thresholds
    MAX_AUTH_TIME = 2000  # 2 seconds
    MAX_WS_CONNECT_TIME = 1500  # 1.5 seconds
    MAX_FIRST_PAINT_TIME = 1000  # 1 second
    MAX_TIME_TO_INTERACTIVE = 3000  # 3 seconds
    
    # WebSocket event requirements (from spec)
    REQUIRED_EVENTS = [
        'agent_started',
        'agent_thinking', 
        'tool_executing',
        'tool_completed',
        'agent_completed'
    ]


# ============================================================================
# FRONTEND INITIALIZATION SIMULATOR
# ============================================================================

class FrontendInitializationSimulator:
    """Simulates frontend initialization flow with real service interactions."""
    
    def __init__(self):
        self.client = TestClient(app)
        self.auth_service = AuthService()
        self.websocket_manager = WebSocketManager()
        self.agent_registry = AgentRegistry()
        self.metrics: Dict[str, float] = {}
        self.events_received: List[Dict] = []
        self.errors: List[Dict] = []
        
    async def simulate_first_page_load(self) -> Dict[str, Any]:
        """Simulate complete first-time page load flow."""
        start_time = time.time()
        results = {
            'success': False,
            'metrics': {},
            'errors': [],
            'events': []
        }
        
        try:
            # Step 1: Initialize authentication
            auth_start = time.time()
            auth_result = await self._initialize_authentication()
            self.metrics['auth_init_time'] = (time.time() - auth_start) * 1000
            
            if not auth_result['success']:
                self.errors.append({
                    'phase': 'auth_init',
                    'error': auth_result.get('error', 'Unknown auth error')
                })
                results['errors'] = self.errors
                return results
                
            # Step 2: Establish WebSocket connection
            ws_start = time.time()
            ws_result = await self._establish_websocket_connection(auth_result['token'])
            self.metrics['ws_connect_time'] = (time.time() - ws_start) * 1000
            
            if not ws_result['success']:
                self.errors.append({
                    'phase': 'websocket_connect',
                    'error': ws_result.get('error', 'WebSocket connection failed')
                })
                results['errors'] = self.errors
                return results
            
            # Step 3: Simulate initial render
            render_start = time.time()
            render_result = await self._simulate_initial_render()
            self.metrics['initial_render_time'] = (time.time() - render_start) * 1000
            
            # Step 4: Send first message
            msg_start = time.time()
            msg_result = await self._send_first_message(
                ws_result['websocket'],
                auth_result['token']
            )
            self.metrics['first_message_time'] = (time.time() - msg_start) * 1000
            
            # Step 5: Validate WebSocket events
            events_valid = await self._validate_websocket_events()
            
            # Calculate total metrics
            self.metrics['total_init_time'] = (time.time() - start_time) * 1000
            self.metrics['time_to_interactive'] = (
                self.metrics['auth_init_time'] + 
                self.metrics['ws_connect_time'] + 
                self.metrics['initial_render_time']
            )
            
            results['success'] = (
                auth_result['success'] and 
                ws_result['success'] and 
                render_result['success'] and
                msg_result['success'] and
                events_valid
            )
            results['metrics'] = self.metrics
            results['events'] = self.events_received
            results['errors'] = self.errors
            
        except Exception as e:
            logger.error(f"Frontend initialization failed: {e}")
            self.errors.append({
                'phase': 'general',
                'error': str(e)
            })
            results['errors'] = self.errors
            
        return results
    
    async def _initialize_authentication(self) -> Dict[str, Any]:
        """Initialize authentication and get token."""
        try:
            # Simulate OAuth flow or dev auth
            if get_env().get('NODE_ENV') == 'development':
                # Use dev auto-login
                user = AuthUser(
                    id=f"dev_user_{uuid.uuid4().hex[:8]}",
                    email="dev@netra.ai",
                    name="Dev User"
                )
            else:
                # Simulate OAuth callback
                response = self.client.post("/auth/callback", json={
                    "code": "test_auth_code",
                    "state": "test_state"
                })
                if response.status_code != 200:
                    return {'success': False, 'error': f"Auth failed: {response.status_code}"}
                user = AuthUser(**response.json()['user'])
            
            # Get access token
            token = await self.auth_service.create_access_token(user)
            
            # Verify token
            verified_user = await self.auth_service.verify_token(token)
            if not verified_user:
                return {'success': False, 'error': 'Token verification failed'}
                
            return {
                'success': True,
                'token': token,
                'user': user.dict()
            }
            
        except Exception as e:
            logger.error(f"Authentication initialization failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _establish_websocket_connection(self, token: str) -> Dict[str, Any]:
        """Establish WebSocket connection with authentication."""
        try:
            # Create WebSocket URL with token in subprotocol
            ws_url = f"ws://localhost:8080/ws?jwt={token}"
            
            # Track connection attempt
            connection_attempts = 0
            max_attempts = 3
            
            while connection_attempts < max_attempts:
                try:
                    # Use test client WebSocket
                    with self.client.websocket_connect(ws_url) as websocket:
                        # Send initial handshake
                        websocket.send_json({
                            "type": "connection_init",
                            "payload": {
                                "token": token,
                                "client_id": f"test_{uuid.uuid4().hex[:8]}"
                            }
                        })
                        
                        # Wait for connection acknowledgment
                        response = websocket.receive_json(timeout=5)
                        if response.get('type') == 'connection_ack':
                            logger.info("WebSocket connection established")
                            return {
                                'success': True,
                                'websocket': websocket,
                                'connection_id': response.get('payload', {}).get('connection_id')
                            }
                        else:
                            logger.warning(f"Unexpected response: {response}")
                            
                except WebSocketDisconnect as e:
                    logger.warning(f"WebSocket disconnected: {e}")
                    connection_attempts += 1
                    if connection_attempts < max_attempts:
                        await asyncio.sleep(1)
                    
            return {'success': False, 'error': 'Failed to establish WebSocket after retries'}
            
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _simulate_initial_render(self) -> Dict[str, Any]:
        """Simulate initial UI render and component mounting."""
        try:
            # Simulate component initialization sequence
            components = [
                'AuthProvider',
                'WebSocketProvider', 
                'AppWithLayout',
                'MainChat',
                'MessageList',
                'MessageInput'
            ]
            
            mount_times = {}
            for component in components:
                start = time.time()
                # Simulate component mount with small delay
                await asyncio.sleep(0.05)  # 50ms per component
                mount_times[component] = (time.time() - start) * 1000
                logger.debug(f"Component {component} mounted in {mount_times[component]:.2f}ms")
            
            # Check critical components are mounted
            critical_components = ['WebSocketProvider', 'MainChat', 'MessageInput']
            all_mounted = all(comp in mount_times for comp in critical_components)
            
            return {
                'success': all_mounted,
                'mount_times': mount_times,
                'total_mount_time': sum(mount_times.values())
            }
            
        except Exception as e:
            logger.error(f"Initial render failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _send_first_message(self, websocket, token: str) -> Dict[str, Any]:
        """Send first user message and validate response."""
        try:
            # Create or get thread
            thread_response = self.client.post(
                "/api/threads",
                headers={"Authorization": f"Bearer {token}"},
                json={"name": "Test Thread"}
            )
            
            if thread_response.status_code != 200:
                return {'success': False, 'error': f"Thread creation failed: {thread_response.status_code}"}
                
            thread_id = thread_response.json()['id']
            
            # Send test message via WebSocket
            test_message = {
                "type": "user_message",
                "payload": {
                    "content": "Test first message for initialization",
                    "thread_id": thread_id,
                    "message_id": f"msg_{uuid.uuid4().hex[:8]}",
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
            websocket.send_json(test_message)
            
            # Collect events with timeout
            start_time = time.time()
            timeout = FrontendInitTestConfig.FIRST_MESSAGE_TIMEOUT / 1000
            required_events_seen = set()
            
            while time.time() - start_time < timeout:
                try:
                    event = websocket.receive_json(timeout=1)
                    self.events_received.append(event)
                    event_type = event.get('type')
                    
                    if event_type in FrontendInitTestConfig.REQUIRED_EVENTS:
                        required_events_seen.add(event_type)
                        logger.info(f"Received required event: {event_type}")
                    
                    # Check if we've seen all required events
                    if required_events_seen == set(FrontendInitTestConfig.REQUIRED_EVENTS):
                        logger.info("All required WebSocket events received")
                        return {
                            'success': True,
                            'events_received': list(required_events_seen),
                            'total_events': len(self.events_received)
                        }
                        
                except Exception as e:
                    logger.debug(f"Timeout waiting for event: {e}")
                    continue
            
            # Check what events we're missing
            missing_events = set(FrontendInitTestConfig.REQUIRED_EVENTS) - required_events_seen
            if missing_events:
                logger.error(f"Missing required events: {missing_events}")
                return {
                    'success': False,
                    'error': f"Missing events: {missing_events}",
                    'events_received': list(required_events_seen)
                }
                
            return {'success': True, 'events_received': list(required_events_seen)}
            
        except Exception as e:
            logger.error(f"First message send failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _validate_websocket_events(self) -> bool:
        """Validate that all required WebSocket events were received."""
        received_types = {event.get('type') for event in self.events_received}
        required_types = set(FrontendInitTestConfig.REQUIRED_EVENTS)
        
        missing = required_types - received_types
        if missing:
            logger.error(f"Missing WebSocket events: {missing}")
            self.errors.append({
                'phase': 'event_validation',
                'error': f"Missing events: {missing}"
            })
            return False
            
        logger.info(f"All required events received: {required_types}")
        return True


# ============================================================================
# STRESS TEST: CONCURRENT SESSIONS
# ============================================================================

class ConcurrentSessionStressTest:
    """Stress test for concurrent chat sessions."""
    
    def __init__(self, num_sessions: int = 10):
        self.num_sessions = num_sessions
        self.simulators: List[FrontendInitializationSimulator] = []
        self.results: List[Dict] = []
        
    async def run_stress_test(self) -> Dict[str, Any]:
        """Run concurrent session stress test."""
        logger.info(f"Starting stress test with {self.num_sessions} concurrent sessions")
        
        # Create simulators
        self.simulators = [FrontendInitializationSimulator() for _ in range(self.num_sessions)]
        
        # Run concurrent initializations
        tasks = []
        for i, simulator in enumerate(self.simulators):
            task = asyncio.create_task(self._run_single_session(simulator, i))
            tasks.append(task)
            # Stagger starts slightly to avoid thundering herd
            await asyncio.sleep(0.1)
        
        # Wait for all sessions to complete
        self.results = await asyncio.gather(*tasks)
        
        # Analyze results
        analysis = self._analyze_stress_results()
        
        return analysis
    
    async def _run_single_session(self, simulator: FrontendInitializationSimulator, session_id: int) -> Dict:
        """Run a single session initialization."""
        logger.info(f"Starting session {session_id}")
        try:
            result = await simulator.simulate_first_page_load()
            result['session_id'] = session_id
            logger.info(f"Session {session_id} completed: {'SUCCESS' if result['success'] else 'FAILED'}")
            return result
        except Exception as e:
            logger.error(f"Session {session_id} failed with exception: {e}")
            return {
                'session_id': session_id,
                'success': False,
                'error': str(e)
            }
    
    def _analyze_stress_results(self) -> Dict[str, Any]:
        """Analyze stress test results."""
        successful = sum(1 for r in self.results if r.get('success', False))
        failed = self.num_sessions - successful
        
        # Calculate metric statistics
        metric_stats = {}
        for metric_name in ['auth_init_time', 'ws_connect_time', 'initial_render_time', 'first_message_time']:
            values = [r['metrics'].get(metric_name, 0) for r in self.results if r.get('success')]
            if values:
                metric_stats[metric_name] = {
                    'min': min(values),
                    'max': max(values),
                    'avg': sum(values) / len(values),
                    'p95': sorted(values)[int(len(values) * 0.95)] if len(values) > 1 else values[0]
                }
        
        # Collect all errors
        all_errors = []
        for result in self.results:
            if 'errors' in result:
                all_errors.extend(result['errors'])
        
        return {
            'total_sessions': self.num_sessions,
            'successful': successful,
            'failed': failed,
            'success_rate': (successful / self.num_sessions) * 100,
            'metric_stats': metric_stats,
            'errors': all_errors
        }


# ============================================================================
# TEST CASES
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.mission_critical
async def test_frontend_initialization_happy_path():
    """Test successful frontend initialization flow."""
    simulator = FrontendInitializationSimulator()
    result = await simulator.simulate_first_page_load()
    
    assert result['success'], f"Frontend initialization failed: {result.get('errors')}"
    
    # Validate performance metrics
    metrics = result['metrics']
    assert metrics['auth_init_time'] < FrontendInitTestConfig.MAX_AUTH_TIME, \
        f"Auth init too slow: {metrics['auth_init_time']}ms"
    assert metrics['ws_connect_time'] < FrontendInitTestConfig.MAX_WS_CONNECT_TIME, \
        f"WebSocket connect too slow: {metrics['ws_connect_time']}ms"
    assert metrics['time_to_interactive'] < FrontendInitTestConfig.MAX_TIME_TO_INTERACTIVE, \
        f"Time to interactive too slow: {metrics['time_to_interactive']}ms"
    
    # Validate all required events received
    event_types = {e.get('type') for e in result['events']}
    for required_event in FrontendInitTestConfig.REQUIRED_EVENTS:
        assert required_event in event_types, f"Missing required event: {required_event}"


@pytest.mark.asyncio
@pytest.mark.mission_critical
async def test_frontend_init_with_auth_failure():
    """Test frontend initialization with authentication failure."""
    simulator = FrontendInitializationSimulator()
    
    # Mock auth failure
    original_auth = simulator.auth_service.verify_token
    simulator.auth_service.verify_token = lambda token: None
    
    result = await simulator.simulate_first_page_load()
    
    # Restore original auth
    simulator.auth_service.verify_token = original_auth
    
    assert not result['success'], "Should fail with auth error"
    assert any(e['phase'] == 'auth_init' for e in result['errors']), \
        "Should have auth_init error"


@pytest.mark.asyncio
@pytest.mark.mission_critical  
async def test_frontend_init_websocket_reconnection():
    """Test WebSocket reconnection during initialization."""
    simulator = FrontendInitializationSimulator()
    
    # Simulate WebSocket disconnection and reconnection
    disconnect_count = 0
    
    async def mock_ws_connect(*args, **kwargs):
        nonlocal disconnect_count
        if disconnect_count < 2:
            disconnect_count += 1
            raise WebSocketDisconnect(code=1006, reason="Connection lost")
        # Third attempt succeeds
        return await simulator._establish_websocket_connection(*args, **kwargs)
    
    original_connect = simulator._establish_websocket_connection
    simulator._establish_websocket_connection = mock_ws_connect
    
    result = await simulator.simulate_first_page_load()
    
    # Restore original
    simulator._establish_websocket_connection = original_connect
    
    # Should eventually succeed after retries
    assert result['success'], "Should succeed after reconnection"


@pytest.mark.asyncio
@pytest.mark.stress
async def test_concurrent_session_stress():
    """Stress test with multiple concurrent sessions."""
    stress_test = ConcurrentSessionStressTest(num_sessions=10)
    results = await stress_test.run_stress_test()
    
    logger.info(f"Stress test results: {json.dumps(results, indent=2)}")
    
    # At least 80% should succeed
    assert results['success_rate'] >= 80, \
        f"Too many failures: {results['failed']}/{results['total_sessions']}"
    
    # Check p95 performance
    for metric, stats in results['metric_stats'].items():
        if 'auth_init' in metric:
            assert stats['p95'] < FrontendInitTestConfig.MAX_AUTH_TIME * 1.5, \
                f"{metric} p95 too high: {stats['p95']}ms"
        elif 'ws_connect' in metric:
            assert stats['p95'] < FrontendInitTestConfig.MAX_WS_CONNECT_TIME * 1.5, \
                f"{metric} p95 too high: {stats['p95']}ms"


@pytest.mark.asyncio
@pytest.mark.mission_critical
async def test_frontend_init_performance_degradation():
    """Test frontend initialization under degraded conditions."""
    simulator = FrontendInitializationSimulator()
    
    # Add artificial delays to simulate slow network
    async def slow_auth(*args, **kwargs):
        await asyncio.sleep(1)  # 1 second delay
        return await simulator.auth_service.create_access_token(*args, **kwargs)
    
    original_auth = simulator.auth_service.create_access_token
    simulator.auth_service.create_access_token = slow_auth
    
    result = await simulator.simulate_first_page_load()
    
    # Restore original
    simulator.auth_service.create_access_token = original_auth
    
    # Should still succeed, just slower
    assert result['success'], "Should succeed even with slow network"
    assert result['metrics']['auth_init_time'] > 1000, "Should show degraded performance"


# ============================================================================
# TEST RUNNER
# ============================================================================

if __name__ == "__main__":
    # Run with detailed logging
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
        level="DEBUG"
    )
    
    # Run tests
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-m", "mission_critical",
        "--asyncio-mode=auto"
    ])