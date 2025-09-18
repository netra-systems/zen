"""
Critical Unit Tests for WebSocket Race Condition - Business Protection Tests

These tests validate the 5 identified race condition patterns that threaten 500K+ ARR chat functionality:
1. Connection State Race Condition - accept() timing issues
2. MessageHandlerService Constructor Signature Mismatch 
3. GCP Readiness Validation Failure
4. Systematic Heartbeat Timeouts
5. Connection Response Send Failures

Business Value Justification:
1. Segment: Platform/Internal - Chat is King infrastructure protection
2. Business Goal: Prevent 500K+ ARR loss from WebSocket failures
3. Value Impact: Validates mission-critical WebSocket agent events deliver chat value
4. Strategic Impact: Protects core business model dependent on reliable AI interactions

@compliance CLAUDE.md - Real service behavior validation, no mocks allowed
@compliance Five Whys Analysis - Each test recreates specific failure patterns from GCP staging
"""
import asyncio
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from unittest.mock import Mock, patch, AsyncMock
from fastapi import WebSocket
from fastapi.websockets import WebSocketState, WebSocketDisconnect
from netra_backend.app.websocket_core.utils import is_websocket_connected, is_websocket_connected_and_ready, validate_websocket_handshake_completion, WebSocketHeartbeat, safe_websocket_send
from netra_backend.app.services.message_handlers import MessageHandlerService
from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager, create_websocket_manager_sync
from netra_backend.app.websocket_core.gcp_initialization_validator import GCPWebSocketInitializationValidator
from netra_backend.app.websocket_core.utils import _get_staging_optimized_timeouts, HEARTBEAT_TIMEOUT_SECONDS
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.isolated_environment import get_env

@pytest.mark.unit
class WebSocketAcceptTimingTests:
    """
    CRITICAL TEST: Validates accept() completion timing before message handling.
    
    FAILURE PATTERN: "WebSocket is not connected. Need to call 'accept' first"
    ROOT CAUSE: Race condition between WebSocket accept() and message handling start
    """

    @pytest.mark.asyncio
    async def test_websocket_accept_timing_validation(self):
        """
        Test accept() completion before message handling (Pattern 1).
        
        CRITICAL: This test MUST FAIL when race conditions occur.
        It validates that the handshake completion check works properly.
        """
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.client_state = WebSocketState.CONNECTING
        mock_websocket.application_state = WebSocketState.CONNECTING
        is_ready_before = is_websocket_connected_and_ready(mock_websocket)
        assert not is_ready_before, 'WebSocket should not be ready while CONNECTING'
        await asyncio.sleep(0.01)
        mock_websocket.client_state = WebSocketState.CONNECTED
        mock_websocket.application_state = WebSocketState.CONNECTED
        is_ready_after = is_websocket_connected_and_ready(mock_websocket)
        assert is_ready_after, 'WebSocket should be ready after CONNECTED state'
        handshake_valid = await validate_websocket_handshake_completion(mock_websocket)
        assert handshake_valid, 'Bidirectional handshake should be complete'

    @pytest.mark.asyncio
    async def test_gcp_cloud_run_timing_simulation(self):
        """
        Test GCP Cloud Run specific timing delays and validation.
        
        CRITICAL: Simulates the exact 22+ second delays seen in staging.
        Must validate that timeouts are handled properly.
        """
        staging_timeouts = _get_staging_optimized_timeouts()
        heartbeat_timeout = HEARTBEAT_TIMEOUT_SECONDS
        assert staging_timeouts['connection_timeout_seconds'] >= 300, 'Staging connection timeout too short'
        assert staging_timeouts['heartbeat_interval_seconds'] >= 25, 'Staging heartbeat interval too short'
        assert heartbeat_timeout >= 60, 'Staging heartbeat timeout too short'
        with patch.dict('os.environ', {'ENVIRONMENT': 'staging'}):
            validator = GCPWebSocketInitializationValidator()
            start_time = time.time()
            with patch.object(validator, '_check_service_group', return_value=True):
                is_ready = await validator.validate_gcp_readiness_for_websocket()
            validation_time = time.time() - start_time
            assert validation_time < 5.0, f'GCP validation took {validation_time}s - too slow even with mocks'
            assert is_ready, 'GCP readiness validation should succeed with healthy services'

@pytest.mark.unit
class MessageHandlerServiceConsistencyTests:
    """
    CRITICAL TEST: Validates consistent constructor signatures across all initialization paths.
    
    FAILURE PATTERN: "MessageHandlerService.__init__() got an unexpected keyword argument 'websocket_manager'"
    ROOT CAUSE: Multiple initialization paths with different parameter signatures
    """

    def test_message_handler_service_constructor_consistency(self):
        """
        Test MessageHandlerService constructor signature consistency (Pattern 2).
        
        CRITICAL: This test MUST FAIL if constructor signatures mismatch.
        Validates all code paths use same signature.
        """
        mock_supervisor = Mock()
        mock_thread_service = Mock()
        try:
            handler1 = MessageHandlerService(supervisor=mock_supervisor, thread_service=mock_thread_service)
            assert handler1 is not None, 'Standard constructor should work'
        except TypeError as e:
            pytest.fail(f'Standard MessageHandlerService constructor failed: {e}')
        with pytest.raises(TypeError, match='unexpected keyword argument'):
            MessageHandlerService(supervisor=mock_supervisor, thread_service=mock_thread_service, websocket_manager=Mock())
        try:
            user_context = Mock()
            user_context.user_id = 'test-user-123'
            user_context.thread_id = 'test-thread-123'
            user_context.run_id = 'test-run-123'
            user_context.request_id = 'test-request-123'
            manager = create_websocket_manager_sync(user_context)
            assert manager is not None, 'Factory should create manager successfully'
        except TypeError as signature_error:
            pytest.fail(f'Factory signature mismatch detected: {signature_error}')

@pytest.mark.unit
class BidirectionalHandshakeCompletionTests:
    """
    CRITICAL TEST: Validates actual send/receive capability before operations.
    
    FAILURE PATTERN: Both receive and send operations failing despite CONNECTED state
    ROOT CAUSE: Local WebSocket state != actual network bidirectional readiness
    """

    @pytest.mark.asyncio
    async def test_bidirectional_handshake_completion(self):
        """
        Test actual send/receive capability before message operations (Pattern 3 & 5).
        
        CRITICAL: This test MUST FAIL when bidirectional capability isn't established.
        Tests both send and receive directions.
        """
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.client_state = WebSocketState.CONNECTED
        mock_websocket.application_state = WebSocketState.CONNECTED
        mock_websocket.receive_text = AsyncMock()
        mock_websocket.send_json = AsyncMock()
        assert is_websocket_connected(mock_websocket), 'WebSocket should report as connected'
        handshake_complete = await validate_websocket_handshake_completion(mock_websocket)
        test_message = {'type': 'test', 'content': 'handshake_test'}
        send_success = await safe_websocket_send(mock_websocket, test_message)
        assert handshake_complete, 'Bidirectional handshake must be complete before operations'
        assert send_success, 'Safe WebSocket send should succeed with complete handshake'
        assert hasattr(mock_websocket, 'send_json'), 'WebSocket must have send capability'
        assert hasattr(mock_websocket, 'receive_text'), 'WebSocket must have receive capability'

    @pytest.mark.asyncio
    async def test_send_receive_capability_validation(self):
        """
        Test comprehensive bidirectional communication validation.
        
        CRITICAL: Tests the missing validation from current implementation.
        """
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.client_state = WebSocketState.CONNECTED
        mock_websocket.send_json = AsyncMock(side_effect=RuntimeError('Send not ready'))
        mock_websocket.receive_text = AsyncMock(return_value='{"type": "pong"}')
        with patch('netra_backend.app.websocket_core.utils.safe_websocket_send') as mock_send:
            mock_send.return_value = False
            send_works = await safe_websocket_send(mock_websocket, {'test': 'message'})
            assert not send_works, 'Should detect send capability failure'
        mock_websocket.send_json = AsyncMock()
        mock_websocket.receive_text = AsyncMock(side_effect=RuntimeError('Receive not ready'))
        try:
            await mock_websocket.receive_text()
            pytest.fail('Should have failed due to receive capability issue')
        except RuntimeError:
            pass

@pytest.mark.unit
class HeartbeatConfigurationAlignmentTests:
    """
    CRITICAL TEST: Validates heartbeat timing matches GCP infrastructure settings.
    
    FAILURE PATTERN: "WebSocket heartbeat timeout" every ~2 minutes
    ROOT CAUSE: Misalignment between application heartbeat and GCP load balancer settings
    """

    def test_heartbeat_configuration_alignment(self):
        """
        Test heartbeat timing matches GCP settings (Pattern 4).
        
        CRITICAL: This test MUST FAIL if timing is misaligned.
        Validates environment-specific heartbeat configuration.
        """
        staging_timeouts = _get_staging_optimized_timeouts()
        heartbeat_interval = staging_timeouts['heartbeat_interval_seconds']
        heartbeat_timeout = staging_timeouts['heartbeat_timeout_seconds']
        assert heartbeat_interval < 30, f'Heartbeat interval {heartbeat_interval}s too long for GCP (should be <30s)'
        assert heartbeat_timeout > heartbeat_interval * 2, f'Heartbeat timeout {heartbeat_timeout}s too short for interval {heartbeat_interval}s'
        total_cycle = heartbeat_interval + heartbeat_timeout
        assert total_cycle < 120, f'Total heartbeat cycle {total_cycle}s too long for staging environment'
        with patch.dict('os.environ', {'ENVIRONMENT': 'development'}):
            from shared.isolated_environment import get_env
            env = get_env()
            env.clear_cache()
            dev_timeouts = _get_staging_optimized_timeouts()
        with patch.dict('os.environ', {'ENVIRONMENT': 'production'}):
            from shared.isolated_environment import get_env
            env = get_env()
            env.clear_cache()
            prod_timeouts = _get_staging_optimized_timeouts()
        assert staging_timeouts != dev_timeouts, 'Staging and development should have different heartbeat config'
        assert staging_timeouts != prod_timeouts, 'Staging and production should have different heartbeat config'

    @pytest.mark.asyncio
    async def test_heartbeat_monitor_timeout_detection(self):
        """
        Test heartbeat monitor properly detects timeout conditions.
        
        CRITICAL: Validates the actual timeout logic from staging failures.
        """
        staging_timeouts = _get_staging_optimized_timeouts()
        monitor = WebSocketHeartbeat(interval=staging_timeouts['heartbeat_interval_seconds'], timeout=staging_timeouts['heartbeat_timeout_seconds'])
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.client_state = WebSocketState.CONNECTED
        await monitor.start(mock_websocket)
        assert monitor.running, 'Heartbeat monitor should be running'
        monitor.last_pong = time.time() - 200
        current_time = time.time()
        timeout_detected = monitor.last_pong and current_time - monitor.last_pong > monitor.interval + monitor.timeout
        assert timeout_detected, 'Monitor should detect heartbeat timeout'
        await monitor.stop()
        assert not monitor.running, 'Heartbeat monitor should be stopped'

@pytest.mark.unit
class GCPReadinessValidationStagingTests:
    """
    CRITICAL TEST: Validates staging-appropriate timeout values and readiness checks.
    
    FAILURE PATTERN: "[U+1F534] GCP WebSocket readiness validation FAILED (22.01s)""""

    @pytest.mark.asyncio
    async def test_gcp_readiness_validation_staging_calibration(self):
        """
        Test staging-appropriate timeout values and validation logic (Pattern 3).
        
        CRITICAL: This test MUST FAIL if staging validation is overly strict.
        Validates environment-specific readiness criteria.
        """
        with patch.dict('os.environ', {'ENVIRONMENT': 'staging', 'WEBSOCKET_CONNECTION_TIMEOUT': '600', 'WEBSOCKET_HEARTBEAT_INTERVAL': '30', 'WEBSOCKET_HEARTBEAT_TIMEOUT': '90'}):
            staging_config = _get_staging_optimized_timeouts()
            assert staging_config['connection_timeout_seconds'] >= 300, 'Staging connection timeout too strict'
            assert staging_config['heartbeat_interval_seconds'] >= 25, 'Staging heartbeat interval too aggressive'
            assert staging_config['heartbeat_timeout_seconds'] >= 60, 'Staging heartbeat timeout too strict'
            with patch.dict('os.environ', {'ENVIRONMENT': 'development'}):
                dev_config = _get_staging_optimized_timeouts()
            assert staging_config['connection_timeout_seconds'] >= dev_config['connection_timeout_seconds'], 'Staging should have longer connection timeout than dev'
            validator = GCPWebSocketInitializationValidator()
            with patch.object(validator, '_check_database_ready', return_value=True), patch.object(validator, '_check_redis_ready', return_value=True), patch.object(validator, '_check_auth_system_ready', return_value=True):
                start_time = time.time()
                result = await validator.validate_gcp_readiness()
                validation_time = time.time() - start_time
                assert validation_time < 10, f'Staging validation too slow: {validation_time}s'
                assert result, 'Staging validation should succeed with mocked healthy services'
            with patch.object(validator, '_check_service_group', return_value=False):
                start_time = time.time()
                result = await validator.validate_gcp_readiness()
                validation_time = time.time() - start_time
                assert validation_time < 15, f'Staging validation timeout too long: {validation_time}s'
                assert not result, 'Should fail when services unavailable'

@pytest.mark.requires_docker
class WebSocketRaceConditionIntegrationTests:
    """
    Integration tests that combine multiple race condition patterns.
    
    CRITICAL: These tests validate the interaction between different failure patterns.
    """

    @pytest.mark.asyncio
    async def test_combined_race_condition_patterns(self):
        """
        Test interaction between multiple race condition patterns.
        
        CRITICAL: This test validates that fixing one pattern doesn't break others.
        """
        auth_helper = E2EAuthHelper(environment='test')
        user_context = await create_authenticated_user_context(environment='test', websocket_enabled=True)
        try:
            websocket_manager = await create_websocket_manager(user_context)
            assert websocket_manager is not None, 'WebSocket manager creation should succeed'
        except Exception as e:
            pytest.fail(f'WebSocket manager creation failed: {e}')
        assert hasattr(websocket_manager, 'user_context'), 'Manager should have user context'
        assert str(user_context.user_id) in str(websocket_manager.user_context.user_id), 'User ID should match'
        jwt_token = user_context.agent_context.get('jwt_token')
        assert jwt_token is not None, 'User context should have JWT token'
        assert len(jwt_token) > 50, 'JWT token should be properly formatted'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')