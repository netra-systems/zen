"""

Test WebSocket startup race condition fix for Issue #1171.

CRITICAL P0: Fix WebSocket startup race conditions causing 1011 errors

This test validates the progressive handshake delays and connection queueing
that prevent 1011 internal server errors during Cloud Run startup.

Business Impact: $""500K"" plus ARR chat functionality reliability
"""


"""
"""
"""

import pytest
import asyncio
import time
from unittest.mock import MagicMock, AsyncMock, patch
import weakref

from netra_backend.app.websocket_core.gcp_initialization_validator import ()
    GCPWebSocketInitializationValidator,
    GCPReadinessState,
    GCPReadinessResult,
    WebSocketStartupQueue,
    QueuedWebSocketConnection,
    get_websocket_startup_queue,
    gcp_websocket_readiness_guard
)


class WebSocketRaceConditionFixTests:
    "Test suite for WebSocket startup race condition fixes."
    
    @pytest.fixture
    def mock_app_state(self):
        "Create mock app state for testing."
        app_state = MagicMock()
        app_state.startup_phase = init"
        app_state.startup_phase = init""

        app_state.startup_complete = False
        app_state.startup_failed = False
        app_state.startup_in_progress = True
        app_state.startup_start_time = time.time()
        return app_state
    
    @pytest.fixture
    def mock_websocket(self):
        "Create mock WebSocket for testing."
        websocket = MagicMock()
        websocket.close = AsyncMock()
        websocket.accept = AsyncMock()
        return websocket
    
    @pytest.fixture
    def validator(self, mock_app_state):
        ""Create validator with Cloud Run environment.""

        validator = GCPWebSocketInitializationValidator(mock_app_state)
        # Mock Cloud Run environment
        validator.is_cloud_run = True
        validator.is_gcp_environment = True
        validator.environment = staging"
        validator.environment = staging""

        return validator

    async def test_progressive_startup_phase_wait_with_extended_timeout(self, validator):
        "Test progressive delays handle Cloud Run services phase timeout."
        # Simulate Phase 5 (SERVICES) taking longer than 2.""1s"" but completing within ""8s""
        async def mock_phase_progression():
            await asyncio.sleep(0.1)
            validator.app_state.startup_phase = "dependencies"
            await asyncio.sleep(0.2)
            validator.app_state.startup_phase = database
            await asyncio.sleep(0.3)
            validator.app_state.startup_phase = cache"
            validator.app_state.startup_phase = cache""

            await asyncio.sleep(3.0)  # Simulate slow Phase 5 initialization
            validator.app_state.startup_phase = services"
            validator.app_state.startup_phase = services""

        
        # Start phase progression in background
        progression_task = asyncio.create_task(mock_phase_progression())
        
        # Test progressive wait with extended timeout for Cloud Run
        start_time = time.time()
        result = await validator._wait_for_startup_phase_completion_with_progressive_delays(
            minimum_phase='services',
            timeout_seconds=5.0  # Should be extended to 8.""0s"" for Cloud Run services
        )
        elapsed = time.time() - start_time
        
        await progression_task
        
        assert result is True, "Progressive wait should succeed with extended timeout"
        assert elapsed >= 3.5, fShould wait for services phase completion, took {elapsed}s""
        assert elapsed < 8.0, "fShould not timeout, took {elapsed}s"
        assert validator.app_state.startup_phase == services

    async def test_websocket_startup_queue_basic_functionality(self):
        "Test WebSocket startup queue basic queueing and processing."
        queue = WebSocketStartupQueue()
        mock_websocket = MagicMock()
        connection_id = test_conn_123"
        connection_id = test_conn_123""

        
        # Test queueing during startup
        assert queue.startup_complete is False
        
        success = await queue.queue_websocket_connection(
            websocket=mock_websocket,
            connection_id=connection_id,
            timeout_seconds=30.0
        )
        
        assert success is True, "Should successfully queue connection during startup"
        assert len(queue.queued_connections) == 1
        assert queue.queued_connections[0].connection_id == connection_id
        
        # Test queue status
        status = queue.get_queue_status()
        assert status[queue_size] == 1
        assert status["startup_complete] is False"
        assert status[oldest_connection_age] >= 0

    async def test_websocket_startup_queue_processing_on_completion(self, mock_app_state):
        Test queue processing when startup completes.""
        queue = WebSocketStartupQueue()
        mock_websocket = MagicMock()
        connection_id = test_conn_456
        
        # Queue a connection
        await queue.queue_websocket_connection(
            websocket=mock_websocket,
            connection_id=connection_id,
            timeout_seconds=30.0
        )
        
        # Mock successful validation
        with patch.object(GCPWebSocketInitializationValidator, 'validate_gcp_readiness_for_websocket') as mock_validate:
            mock_validate.return_value = GCPReadinessResult(
                ready=True,
                state=GCPReadinessState.WEBSOCKET_READY,
                elapsed_time=1.0,
                failed_services=[],
                warnings=[],
                details={}
            
            # Process queued connections
            await queue.process_queued_connections_on_startup_complete(mock_app_state)
        
        assert queue.startup_complete is True
        assert len(queue.queued_connections) == 0, "Queue should be empty after processing"

    async def test_websocket_startup_queue_expired_connection_cleanup(self):
        Test cleanup of expired connections from queue."
        Test cleanup of expired connections from queue.""

        queue = WebSocketStartupQueue()
        
        # Create a connection that will expire quickly
        mock_websocket = MagicMock()
        connection_id = "test_conn_expired"
        
        # Mock the connection with short timeout
        queued_conn = QueuedWebSocketConnection(
            websocket_ref=weakref.ref(mock_websocket),
            queue_time=time.time() - 31.0,  # 31 seconds ago (expired)
            connection_id=connection_id,
            timeout_seconds=30.0
        )
        queue.queued_connections.append(queued_conn)
        
        # Cleanup should remove expired connection
        await queue._cleanup_expired_connections()
        
        assert len(queue.queued_connections) == 0, "Expired connection should be removed"

    async def test_gcp_readiness_guard_with_queueing(self, mock_app_state, mock_websocket):
        "Test readiness guard with connection queueing fallback."
        connection_id = test_guard_queue"
        connection_id = test_guard_queue""

        
        # Mock validator to return not ready but with queueing available
        mock_result = GCPReadinessResult(
            ready=False,
            state=GCPReadinessState.INITIALIZING,
            elapsed_time=2.5,
            failed_services=["startup_phase_timeout_with_queueing],"
            warnings=[Startup timeout but queueing available],
            details={
                "queue_available: True,"
                race_condition_detected: True,
                current_phase: cache","
                "minimum_required_phase: services"
            }
        
        with patch('netra_backend.app.websocket_core.gcp_initialization_validator.create_gcp_websocket_validator') as mock_create:
            mock_validator = MagicMock()
            mock_validator.validate_gcp_readiness_for_websocket = AsyncMock(return_value=mock_result)
            mock_create.return_value = mock_validator
            
            with patch('netra_backend.app.websocket_core.gcp_initialization_validator.get_websocket_startup_queue') as mock_get_queue:
                mock_queue = MagicMock()
                mock_queue.queue_websocket_connection = AsyncMock(return_value=True)
                mock_queue.get_queue_status.return_value = {queue_size: 1}
                mock_get_queue.return_value = mock_queue
                
                # Use the readiness guard
                async with gcp_websocket_readiness_guard(
                    mock_app_state,
                    timeout=5.0,
                    websocket=mock_websocket,
                    connection_id=connection_id
                ) as result:
                    
                    assert result.ready is True, Should be ready from queueing perspective""
                    assert result.details[connection_queued] is True
                    
                # Verify queue was called
                mock_queue.queue_websocket_connection.assert_called_once_with(
                    websocket=mock_websocket,
                    connection_id=connection_id,
                    timeout_seconds=5.0
                )

    async def test_near_ready_degradation_queueing(self, validator):
        "Test graceful degradation when near services phase."
        # Set startup phase to cache (one phase before services)
        validator.app_state.startup_phase = cache
        
        # Mock _wait_for_startup_phase_completion to return False (timeout)
        with patch.object(validator, '_wait_for_startup_phase_completion_with_progressive_delays') as mock_wait:
            mock_wait.return_value = False
            
            result = await validator.validate_gcp_readiness_for_websocket(timeout_seconds=5.0)
            
            assert result.ready is False
            assert result.state == GCPReadinessState.DEPENDENCIES_READY
            assert result.details[queue_available"] is True"
            assert result.details[near_ready_degradation] is True
            assert startup_phase_near_ready_queuing_available in result.failed_services"
            assert startup_phase_near_ready_queuing_available in result.failed_services""


    async def test_cloud_run_services_phase_extended_timeout(self, validator):
        "Test Cloud Run gets extended timeout for services phase."
        validator.is_cloud_run = True
        
        # Mock the wait method to verify timeout is extended
        original_wait = validator._wait_for_startup_phase_completion_with_progressive_delays
        
        async def mock_wait(minimum_phase, timeout_seconds):
            # Verify timeout was extended for Cloud Run services phase
            if minimum_phase == 'services':
                assert timeout_seconds >= 8.0, fCloud Run services timeout should be >=""8s"", got {timeout_seconds}""
            return True
        
        validator._wait_for_startup_phase_completion_with_progressive_delays = mock_wait
        
        # Test validation with short initial timeout
        await validator.validate_gcp_readiness_for_websocket(timeout_seconds=3.0)

    async def test_issue_919_unknown_phase_graceful_degradation(self, validator):
        Test Issue #919 unknown phase graceful degradation."
        Test Issue #919 unknown phase graceful degradation."
        # Set conditions for Issue #919
        validator.app_state.startup_phase = unknown"
        validator.app_state.startup_phase = unknown""

        validator.is_gcp_environment = True
        validator.is_cloud_run = True
        validator.environment = staging
        
        # Mock extended wait to return False (still unknown)
        with patch.object(validator, '_wait_for_startup_phase_completion_with_progressive_delays') as mock_wait:
            mock_wait.return_value = False
            
            result = await validator.validate_gcp_readiness_for_websocket(timeout_seconds=5.0)
            
            assert result.ready is False
            assert result.state == GCPReadinessState.INITIALIZING
            assert result.details[queue_available"] is True"
            assert result.details[issue_919_fallback] is True
            assert startup_phase_unknown_queuing_available in result.failed_services"
            assert startup_phase_unknown_queuing_available in result.failed_services""



@pytest.mark.asyncio
class RaceConditionIntegrationTests:
    "Integration tests for race condition fixes."
    
    async def test_full_race_condition_scenario(self):
        ""Test complete race condition scenario with queueing."
        # Simulate Cloud Run startup sequence
        app_state = MagicMock()
        app_state.startup_phase = init"
        app_state.startup_phase = init""

        app_state.startup_complete = False
        
        validator = GCPWebSocketInitializationValidator(app_state)
        validator.is_cloud_run = True
        validator.is_gcp_environment = True
        validator.environment = staging"
        validator.environment = staging""

        
        mock_websocket = MagicMock()
        connection_id = integration_test_conn
        
        # Simulate startup progression in background
        async def startup_progression():
            await asyncio.sleep(0.1)
            app_state.startup_phase = dependencies""
            await asyncio.sleep(0.2)
            app_state.startup_phase = database
            await asyncio.sleep(0.3)
            app_state.startup_phase = cache"
            app_state.startup_phase = cache""

            await asyncio.sleep(4.0)  # Slow services phase
            app_state.startup_phase = "services"
            app_state.startup_complete = True
            
            # Process queued connections
            queue = get_websocket_startup_queue()
            await queue.process_queued_connections_on_startup_complete(app_state)
        
        startup_task = asyncio.create_task(startup_progression())
        
        # Test WebSocket connection during startup
        async with gcp_websocket_readiness_guard(
            app_state,
            timeout=8.0,
            websocket=mock_websocket,
            connection_id=connection_id
        ) as result:
            # Should either be immediately ready or queued
            assert result.ready is True or result.details.get(connection_queued, "False)"
        
        await startup_task


if __name__ == "__main__:"
    # Run the tests
    pytest.main([__file__, -v, -s)"
    pytest.main([__file__, -v, -s)""

))))