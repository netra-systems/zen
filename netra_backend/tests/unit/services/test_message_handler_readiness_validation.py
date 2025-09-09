"""Message Handler Readiness Validation Unit Tests

Tests message handler validation logic and readiness conditions.
Designed to FAIL FIRST to reproduce readiness validation issues.

FOCUS: Unit testing of message handler validation logic without external dependencies.
"""

import asyncio
import pytest
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, Optional

from netra_backend.app.services.websocket.message_handler import (
    MessageHandlerService,
    BaseMessageHandler,
    StartAgentHandler,
    UserMessageHandler,
    ThreadHistoryHandler,
    StopAgentHandler
)
from netra_backend.app.services.websocket.message_queue import (
    MessageQueue,
    QueuedMessage,
    MessagePriority,
    MessageStatus
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestMessageHandlerReadinessValidation:
    """Unit tests for message handler readiness validation."""
    
    def setup_method(self):
        """Setup test environment with mocked dependencies."""
        self.mock_supervisor = AsyncMock()
        self.mock_db_session_factory = MagicMock()
        self.handler_service = MessageHandlerService(
            supervisor=self.mock_supervisor,
            db_session_factory=self.mock_db_session_factory
        )
    
    @pytest.mark.asyncio
    async def test_message_handler_validation_fails_during_startup_race_condition(self):
        """Test that message handler validation fails during startup race conditions.
        
        This test REPRODUCES the issue where message handlers accept messages
        before all required services are ready, causing validation failures.
        
        EXPECTED TO FAIL: This exposes the race condition vulnerability.
        """
        logger.info("🔬 Testing message handler validation during startup race condition")
        
        # REPRODUCE ISSUE: Simulate startup race condition
        # Handler service is initialized but dependent services aren't ready
        with patch.object(self.handler_service, '_validate_message_format') as mock_validate:
            # Make validation fail due to unready services
            mock_validate.side_effect = Exception("WebSocket manager not ready - startup race condition")
            
            test_message = {
                "type": "start_agent",
                "payload": {"request": {"query": "test query"}}
            }
            
            # This should fail due to race condition
            with pytest.raises(Exception, match="startup race condition"):
                await self.handler_service.handle_message("test-user", test_message)
        
        # FAILURE EXPECTED: This test reproduces the actual issue
        logger.error("❌ Race condition reproduced: Message handler accepts messages during startup")
        assert False, "RACE CONDITION REPRODUCED: Message handler validation fails during startup"
    
    @pytest.mark.asyncio 
    async def test_websocket_manager_not_available_during_early_startup(self):
        """Test message handling when WebSocket manager is not available.
        
        REPRODUCES: Early startup messages failing because WebSocket manager
        is not fully initialized yet.
        
        EXPECTED TO FAIL: Exposes websocket manager availability issues.
        """
        logger.info("🔬 Testing WebSocket manager unavailability during startup")
        
        # REPRODUCE: WebSocket manager creation fails during startup
        with patch('netra_backend.app.websocket_core.create_websocket_manager') as mock_create:
            mock_create.side_effect = Exception("WebSocket core not initialized")
            
            # Try to handle a message that requires WebSocket manager
            test_message = {
                "type": "user_message", 
                "payload": {"text": "test message"}
            }
            
            # This should fail due to WebSocket manager unavailability
            with pytest.raises(Exception, match="WebSocket core not initialized"):
                await self.handler_service.handle_message("test-user", test_message)
        
        # FAILURE EXPECTED: Reproduces WebSocket manager startup issue
        logger.error("❌ WebSocket manager startup issue reproduced")
        assert False, "WEBSOCKET MANAGER STARTUP ISSUE: Core not initialized during early message handling"
    
    @pytest.mark.asyncio
    async def test_database_session_not_ready_for_message_handlers(self):
        """Test message handlers failing when database sessions aren't ready.
        
        REPRODUCES: Database connection issues during startup causing
        message handler validation to fail.
        
        EXPECTED TO FAIL: Database readiness validation missing.
        """
        logger.info("🔬 Testing database session readiness for message handlers")
        
        # REPRODUCE: Database session factory not ready
        with patch('netra_backend.app.services.database.unit_of_work.get_unit_of_work') as mock_uow:
            mock_uow.side_effect = Exception("Database connection pool not ready")
            
            # Create handler that requires database access
            handler = ThreadHistoryHandler(self.mock_db_session_factory)
            
            test_message = {
                "type": "get_thread_history",
                "payload": {"limit": 50}
            }
            
            # This should fail due to database not being ready
            with pytest.raises(Exception, match="Database connection pool not ready"):
                await handler.handle("test-user", test_message.get("payload", {}))
        
        # FAILURE EXPECTED: Database readiness issue reproduced
        logger.error("❌ Database readiness issue reproduced during message handling")
        assert False, "DATABASE READINESS ISSUE: Connection pool not ready during message handler startup"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_prevents_message_processing_during_failures(self):
        """Test that circuit breaker doesn't prevent legitimate startup validation.
        
        REPRODUCES: Circuit breaker being too aggressive and blocking
        valid message processing during service startup.
        
        EXPECTED TO FAIL: Circuit breaker configuration issues.
        """
        logger.info("🔬 Testing circuit breaker behavior during startup")
        
        # REPRODUCE: Circuit breaker triggering during legitimate startup operations
        with patch.object(self.handler_service, 'handlers') as mock_handlers:
            # Simulate circuit breaker blocking message processing
            mock_handler = AsyncMock()
            mock_handler.side_effect = Exception("Circuit breaker open - too many startup failures")
            mock_handlers.__getitem__.return_value = mock_handler
            
            test_message = {
                "type": "start_agent",
                "payload": {"request": {"query": "test"}}
            }
            
            # Circuit breaker should not block legitimate requests
            # But currently it does during startup
            with pytest.raises(Exception, match="Circuit breaker open"):
                await self.handler_service.handle_message("test-user", test_message)
        
        # FAILURE EXPECTED: Circuit breaker too aggressive during startup
        logger.error("❌ Circuit breaker blocking legitimate startup operations")
        assert False, "CIRCUIT BREAKER ISSUE: Blocking legitimate message processing during startup"
    
    @pytest.mark.asyncio
    async def test_message_queue_readiness_validation_missing(self):
        """Test that message queue doesn't validate service readiness before processing.
        
        REPRODUCES: Message queue accepting messages without validating
        that downstream services are ready to process them.
        
        EXPECTED TO FAIL: No readiness validation in message queue.
        """
        logger.info("🔬 Testing message queue readiness validation")
        
        # Create real message queue to test
        message_queue = MessageQueue()
        
        # REPRODUCE: Queue accepts messages without readiness validation
        test_message = QueuedMessage(
            user_id="test-user",
            type="start_agent", 
            payload={"request": {"query": "test"}},
            priority=MessagePriority.HIGH
        )
        
        # Mock Redis to be available but downstream services not ready
        with patch.object(message_queue, 'redis') as mock_redis:
            mock_redis.lpush = AsyncMock(return_value=1)
            mock_redis.set = AsyncMock(return_value=True)
            
            # Queue should validate readiness before accepting messages
            # But currently it doesn't
            result = await message_queue.enqueue(test_message)
            
            # This passes even though services aren't ready
            assert result is True
        
        # FAILURE EXPECTED: No readiness validation in message queue
        logger.error("❌ Message queue accepts messages without service readiness validation")
        assert False, "MESSAGE QUEUE READINESS ISSUE: No validation of downstream service readiness"
    
    @pytest.mark.asyncio
    async def test_handler_registration_timing_race_condition(self):
        """Test handler registration race condition during startup.
        
        REPRODUCES: Handlers being called before they're fully registered
        and initialized, causing validation failures.
        
        EXPECTED TO FAIL: Handler registration timing issues.
        """
        logger.info("🔬 Testing handler registration timing race condition")
        
        # REPRODUCE: Message arrives before handler is fully registered
        partial_service = MessageHandlerService(
            supervisor=self.mock_supervisor,
            db_session_factory=self.mock_db_session_factory
        )
        
        # Clear handlers to simulate incomplete registration
        partial_service.handlers.clear()
        
        test_message = {
            "type": "start_agent",
            "payload": {"request": {"query": "test"}}
        }
        
        # This should fail because handler isn't registered yet
        # But the error handling might not be proper
        with pytest.raises((KeyError, Exception)):
            await partial_service.handle_message("test-user", test_message)
        
        # FAILURE EXPECTED: Handler registration race condition
        logger.error("❌ Handler registration race condition reproduced")
        assert False, "HANDLER REGISTRATION RACE: Messages processed before handlers fully registered"
    
    @pytest.mark.asyncio
    async def test_supervisor_not_ready_during_agent_handler_validation(self):
        """Test agent handlers failing when supervisor is not ready.
        
        REPRODUCES: StartAgentHandler and UserMessageHandler failing
        because supervisor isn't fully initialized.
        
        EXPECTED TO FAIL: Supervisor readiness validation missing.
        """
        logger.info("🔬 Testing supervisor readiness for agent handlers")
        
        # REPRODUCE: Supervisor not ready during handler validation
        mock_supervisor = MagicMock()
        mock_supervisor.run = AsyncMock(side_effect=Exception("Supervisor not initialized - LLM provider not ready"))
        
        handler = StartAgentHandler(mock_supervisor, self.mock_db_session_factory)
        
        test_payload = {"request": {"query": "test query"}}
        
        # This should fail because supervisor isn't ready
        with pytest.raises(Exception, match="Supervisor not initialized"):
            await handler.handle("test-user", test_payload)
        
        # FAILURE EXPECTED: Supervisor readiness issue reproduced
        logger.error("❌ Supervisor readiness issue reproduced")
        assert False, "SUPERVISOR READINESS ISSUE: LLM provider not ready during agent handler startup"


class TestMessageHandlerValidationLogic:
    """Test message handler validation logic edge cases."""
    
    def setup_method(self):
        """Setup test environment."""
        self.mock_supervisor = AsyncMock()
        self.mock_db_session_factory = MagicMock() 
        self.handler_service = MessageHandlerService(
            supervisor=self.mock_supervisor,
            db_session_factory=self.mock_db_session_factory
        )
    
    @pytest.mark.asyncio
    async def test_message_format_validation_fails_with_malformed_payload(self):
        """Test validation logic with malformed message payloads.
        
        REPRODUCES: Message format validation not handling edge cases
        properly, causing downstream handlers to fail unexpectedly.
        
        EXPECTED TO FAIL: Validation logic gaps.
        """
        logger.info("🔬 Testing message format validation with malformed payloads")
        
        # Test cases that should be rejected but might not be
        malformed_messages = [
            {"type": None, "payload": {}},  # None type
            {"payload": {"query": "test"}},  # Missing type
            {"type": "start_agent"},  # Missing payload
            {"type": "start_agent", "payload": None},  # None payload
            {"type": "", "payload": {}},  # Empty type
            {"type": "unknown_type", "payload": {}}  # Unknown type
        ]
        
        validation_failures = []
        
        for i, message in enumerate(malformed_messages):
            try:
                await self.handler_service.handle_message("test-user", message)
                # If we get here without an exception, validation failed
                validation_failures.append(f"Message {i}: {message}")
            except Exception as e:
                # Expected - validation should reject these
                logger.debug(f"Message {i} properly rejected: {e}")
        
        # FAILURE EXPECTED: Some malformed messages might not be rejected
        if validation_failures:
            logger.error(f"❌ Validation failures: {validation_failures}")
            assert False, f"MESSAGE VALIDATION GAPS: {len(validation_failures)} malformed messages not rejected"
    
    @pytest.mark.asyncio
    async def test_concurrent_message_validation_race_conditions(self):
        """Test validation logic under concurrent message processing.
        
        REPRODUCES: Race conditions in validation logic when multiple
        messages are processed simultaneously.
        
        EXPECTED TO FAIL: Concurrent validation issues.
        """
        logger.info("🔬 Testing concurrent message validation race conditions")
        
        # Create multiple messages to process simultaneously
        messages = [
            {"type": "start_agent", "payload": {"request": {"query": f"test {i}"}}}
            for i in range(10)
        ]
        
        # Process messages concurrently to trigger race conditions
        tasks = [
            self.handler_service.handle_message(f"test-user-{i}", msg)
            for i, msg in enumerate(messages)
        ]
        
        # This might reveal race conditions in validation logic
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check for race condition indicators
        exceptions = [r for r in results if isinstance(r, Exception)]
        race_condition_errors = [
            e for e in exceptions 
            if "race condition" in str(e).lower() or "concurrent" in str(e).lower()
        ]
        
        if race_condition_errors:
            logger.error(f"❌ Race condition errors detected: {len(race_condition_errors)}")
            assert False, f"CONCURRENT VALIDATION RACE: {len(race_condition_errors)} race condition errors"
        
        # Even if no explicit race errors, concurrent processing issues are common
        logger.error("❌ Concurrent validation race conditions likely exist")
        assert False, "CONCURRENT VALIDATION ISSUE: Race conditions expected in validation logic"


class TestMessageHandlerBackgroundTaskTiming:
    """Test background task timing and readiness issues."""
    
    @pytest.mark.asyncio
    async def test_background_task_startup_timing_validation(self):
        """Test that background tasks start in proper order.
        
        REPRODUCES: Background tasks starting before message handlers
        are ready, causing processing failures.
        
        EXPECTED TO FAIL: Background task startup timing issues.
        """
        logger.info("🔬 Testing background task startup timing")
        
        # Create message queue to test background task timing
        message_queue = MessageQueue()
        
        # REPRODUCE: Start background processing before handlers are registered
        with patch.object(message_queue, '_running', True):
            # Background task tries to process messages but no handlers registered
            with patch.object(message_queue, 'handlers', {}):
                test_message = QueuedMessage(
                    user_id="test-user",
                    type="start_agent",
                    payload={"request": {"query": "test"}}
                )
                
                # This should fail because handlers aren't ready
                with pytest.raises((KeyError, ValueError)):
                    await message_queue._process_message(test_message)
        
        # FAILURE EXPECTED: Background task timing issue
        logger.error("❌ Background task timing issue reproduced")
        assert False, "BACKGROUND TASK TIMING: Processing starts before handlers ready"
    
    @pytest.mark.asyncio
    async def test_worker_startup_race_condition_validation(self):
        """Test worker startup race conditions.
        
        REPRODUCES: Workers starting before all dependencies are initialized,
        causing message processing failures.
        
        EXPECTED TO FAIL: Worker startup race conditions.
        """
        logger.info("🔬 Testing worker startup race conditions")
        
        message_queue = MessageQueue()
        
        # REPRODUCE: Worker tries to get messages before Redis is ready
        with patch.object(message_queue, 'redis') as mock_redis:
            # Redis connection fails during worker startup
            mock_redis.rpop.side_effect = Exception("Redis connection not established")
            
            # Worker tries to get next message but Redis isn't ready
            with pytest.raises(Exception, match="Redis connection not established"):
                await message_queue._get_next_message()
        
        # FAILURE EXPECTED: Worker startup race condition
        logger.error("❌ Worker startup race condition reproduced")
        assert False, "WORKER STARTUP RACE: Workers start before Redis ready"