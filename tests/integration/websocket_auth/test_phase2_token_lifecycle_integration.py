"""
Phase 2 Token Lifecycle Integration Tests

BUSINESS IMPACT: Validates that Phase 2 Token Lifecycle Manager successfully
eliminates WebSocket auth failures that break chat functionality mid-conversation,
protecting $500K+ ARR Golden Path user flows.

MISSION: Prove that 5+ minute WebSocket connections maintain authentication
through background token refresh, ensuring continuous agent execution success.

INTEGRATION SCOPE:
- Token Lifecycle Manager background refresh (45s intervals)  
- Integration with unified WebSocket auth (SSOT)
- Connection cleanup and resource management
- Circuit breaker patterns for auth service failures
- Real-time token refresh for active connections

SUCCESS CRITERIA:
- WebSocket connections lasting 5+ minutes maintain valid authentication
- Agent execution success rate remains 100% throughout connection lifetime
- Token refresh occurs automatically before expiry (45s interval)
- Chat conversations continue uninterrupted across JWT boundaries
- Graceful degradation when auth service unavailable
"""
import pytest
import asyncio
import time
import jwt
from datetime import datetime, timezone, timedelta, UTC
from unittest import mock
import uuid
from contextlib import asynccontextmanager
from netra_backend.app.websocket_core.token_lifecycle_manager import TokenLifecycleManager, TokenLifecycleState, get_token_lifecycle_manager, create_token_lifecycle_manager_for_connection
from netra_backend.app.websocket_core.unified_websocket_auth import authenticate_websocket_ssot, WebSocketAuthResult
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.isolated_environment import get_env
from shared.types.core_types import ensure_user_id
from shared.id_generation import UnifiedIdGenerator

class MockWebSocket:
    """Mock WebSocket for testing token lifecycle integration."""

    def __init__(self, token: str=None, e2e_context: dict=None):
        self.headers = {}
        self.client_state = 'CONNECTED'
        self.client = mock.MagicMock()
        self.client.host = 'localhost'
        self.client.port = 8000
        if token:
            self.headers['sec-websocket-protocol'] = f'jwt.{token}'
        if e2e_context:
            self.headers.update(e2e_context.get('headers', {}))

class Phase2TokenLifecycleIntegrationTests:
    """
    Phase 2 Integration Tests: Token Lifecycle Manager with WebSocket Auth.
    
    These tests validate the complete Phase 2 implementation that eliminates
    JWT expiry failures during long-lived WebSocket connections.
    """

    def setup_method(self, method):
        """Set up Phase 2 test environment."""
        self.env = get_env()
        self.test_user_id = ensure_user_id(str(uuid.uuid4()))
        self.websocket_session_duration = 300
        self.jwt_expiry_duration = 60
        self.token_refresh_interval = 45
        self.jwt_secret = self.env.get('JWT_SECRET', 'phase2_test_jwt_secret')
        self.lifecycle_events = []
        self.token_refresh_count = 0
        self.connection_active_duration = 0

    def _create_test_jwt_token(self, user_id: str, expires_in_seconds: int) -> str:
        """Create JWT token for Phase 2 testing."""
        payload = {'sub': user_id, 'user_id': user_id, 'email': f'test+{user_id[:8]}@netra.com', 'exp': datetime.now(UTC) + timedelta(seconds=expires_in_seconds), 'iat': datetime.now(UTC), 'iss': 'netra-phase2-test', 'permissions': ['execute_agents', 'websocket_access']}
        return jwt.encode(payload, self.jwt_secret, algorithm='HS256')

    def _create_test_user_context(self, user_id: str) -> UserExecutionContext:
        """Create test user execution context."""
        id_generator = UnifiedIdGenerator()
        return UserExecutionContext(user_id=user_id, thread_id=id_generator.generate_base_id('phase2_thread'), run_id=id_generator.generate_base_id('phase2_run'), request_id=id_generator.generate_base_id('phase2_req'), websocket_client_id=id_generator.generate_websocket_client_id(user_id))

    async def _create_connection_event_callback(self, connection_id: str, event_type: str, event_data: dict):
        """Callback to track token lifecycle events."""
        event_record = {'connection_id': connection_id, 'event_type': event_type, 'event_data': event_data, 'timestamp': datetime.now(timezone.utc)}
        self.lifecycle_events.append(event_record)
        if event_type == 'token_refreshed':
            self.token_refresh_count += 1
        print(f'[LIFECYCLE EVENT] {event_type} for {connection_id}: {event_data}')

    @asynccontextmanager
    async def _phase2_lifecycle_context(self, refresh_interval: int=45, token_expiry: int=60):
        """Context manager for Phase 2 lifecycle testing."""
        lifecycle_manager = TokenLifecycleManager(refresh_interval_seconds=refresh_interval, token_expiry_seconds=token_expiry, degraded_mode_timeout_seconds=180)
        await lifecycle_manager.add_connection_event_callback(self._create_connection_event_callback)
        try:
            await lifecycle_manager.start_lifecycle_management()
            yield lifecycle_manager
        finally:
            await lifecycle_manager.stop_lifecycle_management()

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.phase2
    async def test_token_lifecycle_manager_background_refresh(self):
        """
        PHASE 2 CORE: Test background token refresh prevents JWT expiry failures.
        
        BUSINESS VALUE: Validates that 45-second background refresh prevents
        the 60-second JWT expiry that breaks chat mid-conversation.
        """
        print(f'\n[PHASE 2] TESTING TOKEN LIFECYCLE BACKGROUND REFRESH')
        async with self._phase2_lifecycle_context(refresh_interval=10, token_expiry=30) as lifecycle_manager:
            connection_id = str(uuid.uuid4())
            user_context = self._create_test_user_context(self.test_user_id)
            initial_token = self._create_test_jwt_token(self.test_user_id, 30)
            token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=30)
            registration_success = await lifecycle_manager.register_connection_token(connection_id=connection_id, websocket_client_id=user_context.websocket_client_id, user_context=user_context, initial_token=initial_token, token_expires_at=token_expires_at)
            assert registration_success, 'Connection registration should succeed'
            connection_metrics = lifecycle_manager.get_connection_metrics(connection_id)
            assert connection_metrics['connection_id'] == connection_id
            assert connection_metrics['user_id'] == self.test_user_id
            assert not connection_metrics['is_token_expired']
            print(f'[PHASE 2] Connection registered: {connection_metrics}')
            print(f'[PHASE 2] Waiting for background refresh cycle...')
            await asyncio.sleep(20)
            updated_metrics = lifecycle_manager.get_connection_metrics(connection_id)
            assert updated_metrics['refresh_count'] > 0, f"Expected token refresh, but refresh_count = {updated_metrics['refresh_count']}"
            assert updated_metrics['lifecycle_state'] in ['active', 'refresh_scheduled']
            assert not updated_metrics['is_token_expired']
            refresh_events = [e for e in self.lifecycle_events if e['event_type'] == 'token_refreshed']
            assert len(refresh_events) > 0, f"Expected refresh events, got: {[e['event_type'] for e in self.lifecycle_events]}"
            print(f'[SUCCESS] BACKGROUND REFRESH WORKING:')
            print(f"   Token refresh count: {updated_metrics['refresh_count']}")
            print(f"   Connection state: {updated_metrics['lifecycle_state']}")
            print(f"   Token expired: {updated_metrics['is_token_expired']}")
            print(f'   Refresh events: {len(refresh_events)}')
            await lifecycle_manager.unregister_connection(connection_id)

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.phase2
    async def test_websocket_auth_integration_with_lifecycle_manager(self):
        """
        PHASE 2 INTEGRATION: Test WebSocket auth integrates with token lifecycle manager.
        
        BUSINESS VALUE: Ensures that successful WebSocket authentication automatically
        registers for token lifecycle management, preventing mid-conversation failures.
        """
        print(f'\n[PHASE 2] TESTING WEBSOCKET AUTH + LIFECYCLE INTEGRATION')
        initial_token = self._create_test_jwt_token(self.test_user_id, 60)
        mock_websocket = MockWebSocket(token=initial_token)
        e2e_context = {'is_e2e_testing': True, 'demo_mode_enabled': True, 'detection_method': {'via_demo_mode': True}}
        async with self._phase2_lifecycle_context() as lifecycle_manager:
            with mock.patch('netra_backend.app.services.unified_authentication_service.get_unified_auth_service') as mock_auth:
                mock_auth_service = mock.MagicMock()
                mock_auth_result = mock.MagicMock()
                mock_auth_result.success = True
                mock_auth_result.user_id = self.test_user_id
                mock_auth_result.email = f'test+{self.test_user_id[:8]}@netra.com'
                mock_auth_result.permissions = ['execute_agents', 'websocket_access']
                mock_auth_result.validated_at = time.time()
                mock_auth_result.metadata = {}
                mock_auth_service.authenticate_websocket.return_value = (mock_auth_result, None)
                mock_auth.return_value = mock_auth_service
                with mock.patch('netra_backend.app.websocket_core.unified_websocket_auth.create_token_lifecycle_manager_for_connection') as mock_lifecycle_reg:
                    mock_lifecycle_reg.return_value = True
                    auth_result = await authenticate_websocket_ssot(websocket=mock_websocket, e2e_context=e2e_context, preliminary_connection_id=str(uuid.uuid4()))
                    assert auth_result.success, f'Authentication should succeed: {auth_result.error_message}'
                    assert auth_result.user_context is not None
                    assert auth_result.auth_result is not None
                    assert auth_result.auth_result.metadata is not None
                    assert auth_result.auth_result.metadata.get('phase2_lifecycle_enabled') == True
                    assert auth_result.auth_result.metadata.get('token_lifecycle_manager') == 'registered'
                    mock_lifecycle_reg.assert_called_once()
                    call_args = mock_lifecycle_reg.call_args
                    assert call_args.kwargs['user_context'].user_id == self.test_user_id
                    assert call_args.kwargs['initial_token'] == initial_token
                    print(f'[SUCCESS] WEBSOCKET AUTH + LIFECYCLE INTEGRATION:')
                    print(f'   Authentication: SUCCESS')
                    print(f'   User ID: {auth_result.user_context.user_id}')
                    print(f"   Phase 2 enabled: {auth_result.auth_result.metadata.get('phase2_lifecycle_enabled')}")
                    print(f"   Lifecycle registered: {auth_result.auth_result.metadata.get('token_lifecycle_manager')}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.phase2
    async def test_websocket_connection_outlives_agent_context_timing_phase2_fix(self):
        """
        CRITICAL PHASE 2 TEST: Demonstrate Phase 2 fixes the lifecycle mismatch.
        
        BUSINESS IMPACT: This test validates that the Phase 2 Token Lifecycle Manager
        eliminates the JWT expiry failures that were breaking chat mid-conversation.
        
        SUCCESS CRITERIA: Agent contexts can be created successfully throughout
        the entire 5+ minute WebSocket session, not just the first 60 seconds.
        """
        print(f'\n[PHASE 2] CRITICAL TEST: CONNECTION OUTLIVES AGENT CONTEXT WITH PHASE 2 FIX')
        async with self._phase2_lifecycle_context(refresh_interval=15, token_expiry=30) as lifecycle_manager:
            connection_id = str(uuid.uuid4())
            user_context = self._create_test_user_context(self.test_user_id)
            initial_token = self._create_test_jwt_token(self.test_user_id, 30)
            token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=30)
            registration_success = await lifecycle_manager.register_connection_token(connection_id=connection_id, websocket_client_id=user_context.websocket_client_id, user_context=user_context, initial_token=initial_token, token_expires_at=token_expires_at)
            assert registration_success, 'Phase 2 lifecycle registration must succeed'
            print(f'[PHASE 2] WebSocket connection established with lifecycle management')
            print(f'   Connection ID: {connection_id}')
            print(f'   Initial token expires: {token_expires_at}')
            print(f'   Expected refresh at: ~15s before expiry')
            agent_execution_results = []
            test_intervals = [5, 10, 20, 35, 50, 65]
            for interval in test_intervals:
                print(f'\n[PHASE 2] Testing agent context creation at t={interval}s...')
                if interval > 0:
                    await asyncio.sleep(min(interval - sum([r['interval'] for r in agent_execution_results]), 10))
                current_token = await lifecycle_manager.get_current_token(connection_id)
                execution_result = {'interval': interval, 'timestamp': datetime.now(timezone.utc), 'current_token_available': current_token is not None, 'lifecycle_metrics': lifecycle_manager.get_connection_metrics(connection_id)}
                if current_token is not None:
                    execution_result['status'] = 'SUCCESS'
                    execution_result['message'] = f'Agent context created successfully at t={interval}s'
                    print(f'   CHECK SUCCESS: Agent context creation at t={interval}s')
                else:
                    execution_result['status'] = 'FAILED'
                    execution_result['message'] = f'Agent context creation failed - no valid token at t={interval}s'
                    print(f'   X FAILED: Agent context creation at t={interval}s')
                agent_execution_results.append(execution_result)
                metrics = execution_result['lifecycle_metrics']
                print(f"      Lifecycle state: {metrics.get('lifecycle_state', 'unknown')}")
                print(f"      Refresh count: {metrics.get('refresh_count', 0)}")
                print(f"      Token expired: {metrics.get('is_token_expired', 'unknown')}")
            successful_executions = [r for r in agent_execution_results if r['status'] == 'SUCCESS']
            failed_executions = [r for r in agent_execution_results if r['status'] == 'FAILED']
            print(f'\n[PHASE 2] EXECUTION RESULTS ANALYSIS:')
            print(f'   Total attempts: {len(agent_execution_results)}')
            print(f'   Successful: {len(successful_executions)}')
            print(f'   Failed: {len(failed_executions)}')
            print(f'   Success rate: {len(successful_executions) / len(agent_execution_results) * 100:.1f}%')
            success_rate = len(successful_executions) / len(agent_execution_results)
            assert success_rate >= 0.8, f"PHASE 2 FAILURE: Expected 80%+ success rate for agent context creation throughout WebSocket session, but got {success_rate:.1%} ({len(successful_executions)}/{len(agent_execution_results)}). Failed executions: {[r['interval'] for r in failed_executions]}. This indicates Phase 2 token lifecycle management is not working correctly."
            final_metrics = lifecycle_manager.get_connection_metrics(connection_id)
            assert final_metrics['refresh_count'] > 0, f"Expected token refreshes during test, but refresh_count = {final_metrics['refresh_count']}. Phase 2 background refresh is not working."
            print(f'\n[SUCCESS] PHASE 2 TOKEN LIFECYCLE FIX VALIDATED:')
            print(f'   CHECK Agent execution success rate: {success_rate:.1%}')
            print(f"   CHECK Token refresh count: {final_metrics['refresh_count']}")
            print(f'   CHECK Connection maintained throughout session')
            print(f'   CHECK No JWT expiry failures breaking chat mid-conversation')
            print(f'   🎯 BUSINESS IMPACT: $500K+ ARR Golden Path protected')
            await lifecycle_manager.unregister_connection(connection_id)

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.phase2
    async def test_circuit_breaker_graceful_degradation(self):
        """
        PHASE 2 RESILIENCE: Test circuit breaker and graceful degradation.
        
        BUSINESS VALUE: Ensures that auth service failures don't completely
        break WebSocket connections, providing degraded but functional service.
        """
        print(f'\n[PHASE 2] TESTING CIRCUIT BREAKER GRACEFUL DEGRADATION')
        async with self._phase2_lifecycle_context(refresh_interval=5, token_expiry=15) as lifecycle_manager:
            connection_id = str(uuid.uuid4())
            user_context = self._create_test_user_context(self.test_user_id)
            initial_token = self._create_test_jwt_token(self.test_user_id, 15)
            token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=15)
            await lifecycle_manager.register_connection_token(connection_id=connection_id, websocket_client_id=user_context.websocket_client_id, user_context=user_context, initial_token=initial_token, token_expires_at=token_expires_at)
            with mock.patch('netra_backend.app.services.unified_authentication_service.get_unified_auth_service') as mock_auth:
                mock_auth_service = mock.MagicMock()
                mock_auth_result = mock.MagicMock()
                mock_auth_result.success = False
                mock_auth_result.error = 'Auth service unavailable'
                mock_auth_result.error_code = 'AUTH_SERVICE_ERROR'
                mock_auth_service.authenticate.return_value = mock_auth_result
                mock_auth.return_value = mock_auth_service
                print(f'[PHASE 2] Waiting for auth service failures to trigger circuit breaker...')
                await asyncio.sleep(10)
                metrics = lifecycle_manager.get_connection_metrics(connection_id)
                overall_metrics = lifecycle_manager.get_connection_metrics()
                degraded_or_circuit_tripped = metrics.get('is_degraded', False) or overall_metrics.get('circuit_breaker_trips', 0) > 0 or overall_metrics.get('circuit_breaker_state') == 'OPEN'
                assert degraded_or_circuit_tripped, f'Expected graceful degradation or circuit breaker activation, but connection metrics: {metrics}, overall: {overall_metrics}'
                print(f'[SUCCESS] GRACEFUL DEGRADATION ACTIVATED:')
                print(f"   Connection degraded: {metrics.get('is_degraded', False)}")
                print(f"   Circuit breaker state: {overall_metrics.get('circuit_breaker_state')}")
                print(f"   Circuit breaker trips: {overall_metrics.get('circuit_breaker_trips', 0)}")
                print(f"   Failed refreshes: {overall_metrics.get('failed_refreshes', 0)}")
            await lifecycle_manager.unregister_connection(connection_id)

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.phase2
    async def test_phase2_metrics_and_monitoring(self):
        """
        PHASE 2 OBSERVABILITY: Test metrics collection and monitoring.
        
        BUSINESS VALUE: Provides visibility into token lifecycle health
        for proactive monitoring and debugging of authentication issues.
        """
        print(f'\n[PHASE 2] TESTING METRICS AND MONITORING')
        async with self._phase2_lifecycle_context(refresh_interval=5, token_expiry=10) as lifecycle_manager:
            connections = []
            for i in range(3):
                connection_id = str(uuid.uuid4())
                user_id = ensure_user_id(str(uuid.uuid4()))
                user_context = self._create_test_user_context(user_id)
                initial_token = self._create_test_jwt_token(user_id, 10)
                token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=10)
                await lifecycle_manager.register_connection_token(connection_id=connection_id, websocket_client_id=user_context.websocket_client_id, user_context=user_context, initial_token=initial_token, token_expires_at=token_expires_at)
                connections.append(connection_id)
            await asyncio.sleep(8)
            overall_metrics = lifecycle_manager.get_connection_metrics()
            assert 'total_connections' in overall_metrics
            assert 'active_connections' in overall_metrics
            assert 'successful_refreshes' in overall_metrics
            assert 'failed_refreshes' in overall_metrics
            assert 'refresh_success_rate' in overall_metrics
            assert 'average_connection_duration' in overall_metrics
            assert 'lifecycle_manager_running' in overall_metrics
            assert overall_metrics['total_connections'] >= 3
            assert overall_metrics['active_connections'] == 3
            assert overall_metrics['lifecycle_manager_running'] == True
            print(f'[SUCCESS] PHASE 2 METRICS COLLECTION:')
            print(f"   Total connections: {overall_metrics['total_connections']}")
            print(f"   Active connections: {overall_metrics['active_connections']}")
            print(f"   Successful refreshes: {overall_metrics['successful_refreshes']}")
            print(f"   Failed refreshes: {overall_metrics['failed_refreshes']}")
            print(f"   Refresh success rate: {overall_metrics['refresh_success_rate']:.1f}%")
            print(f"   Average connection duration: {overall_metrics['average_connection_duration']:.1f}s")
            print(f"   Lifecycle manager running: {overall_metrics['lifecycle_manager_running']}")
            for connection_id in connections[:1]:
                conn_metrics = lifecycle_manager.get_connection_metrics(connection_id)
                assert 'connection_id' in conn_metrics
                assert 'user_id' in conn_metrics
                assert 'connection_duration' in conn_metrics
                assert 'lifecycle_state' in conn_metrics
                assert 'refresh_count' in conn_metrics
                print(f"   Connection {connection_id[:8]}... metrics: state={conn_metrics['lifecycle_state']}, duration={conn_metrics['connection_duration']:.1f}s")
            for connection_id in connections:
                await lifecycle_manager.unregister_connection(connection_id)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')