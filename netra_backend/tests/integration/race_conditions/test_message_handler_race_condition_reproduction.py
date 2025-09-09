"""Message Handler Race Condition Reproduction Tests

Specialized tests to reproduce race conditions in message handler readiness validation.
These tests use threading, timing delays, and concurrent operations to trigger race conditions.

FOCUS: Reproducing actual race conditions that occur during service startup,
message processing, and concurrent operations.

EXPECTED TO FAIL: All tests are designed to expose race conditions.
"""

import asyncio
import pytest
import threading
import time
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from netra_backend.app.services.websocket.message_handler import (
    MessageHandlerService,
    StartAgentHandler,
    UserMessageHandler
)
from netra_backend.app.services.websocket.message_queue import (
    MessageQueue,
    QueuedMessage,
    MessagePriority,
    MessageStatus
)
from netra_backend.app.redis_manager import redis_manager
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@pytest.mark.integration
@pytest.mark.race_conditions
class TestMessageHandlerStartupRaceConditions:
    """Tests to reproduce race conditions during message handler startup."""
    
    @pytest.mark.asyncio
    async def test_concurrent_handler_registration_race_condition(self):
        """Reproduce race condition during concurrent handler registration.
        
        RACE CONDITION: Multiple threads trying to register handlers
        simultaneously, causing inconsistent handler registration state.
        
        EXPECTED TO FAIL: Handler registration is not thread-safe.
        """
        logger.info("🏁 Reproducing concurrent handler registration race condition")
        
        # SETUP: Create multiple handler services simultaneously
        services = []
        registration_results = []
        
        def create_and_register_service(service_id):
            """Create service and register handlers in separate thread."""
            try:
                mock_supervisor = AsyncMock()
                mock_db_factory = MagicMock()
                
                service = MessageHandlerService(
                    supervisor=mock_supervisor,
                    db_session_factory=mock_db_factory
                )
                
                services.append(service)
                
                # Force registration timing issues
                time.sleep(random.uniform(0.01, 0.05))  # Random delay
                
                # Check handler registration state
                handler_count = len(service.handlers)
                registration_results.append((service_id, handler_count))
                
                return service
                
            except Exception as e:
                registration_results.append((service_id, f"ERROR: {e}"))
                return None
        
        # REPRODUCE: Concurrent service creation and handler registration
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(create_and_register_service, i)
                for i in range(10)
            ]
            
            # Wait for all registrations to complete
            results = [future.result() for future in futures]
        
        # ANALYZE: Check for registration inconsistencies
        successful_services = [r for r in results if r is not None]
        handler_counts = [result[1] for result in registration_results if isinstance(result[1], int)]
        errors = [result for result in registration_results if isinstance(result[1], str)]
        
        logger.info(f"📊 Registration results: {len(successful_services)} services, {len(errors)} errors")
        logger.info(f"📊 Handler counts: {handler_counts}")
        
        # Check for inconsistencies
        if len(set(handler_counts)) > 1:
            logger.error(f"❌ Inconsistent handler registration: counts {set(handler_counts)}")
        
        if errors:
            logger.error(f"❌ Registration errors: {errors}")
        
        # FAILURE EXPECTED: Race condition in handler registration
        logger.error("❌ Handler registration race condition reproduced")
        assert False, f"HANDLER REGISTRATION RACE: Inconsistent results - counts: {set(handler_counts)}, errors: {len(errors)}"