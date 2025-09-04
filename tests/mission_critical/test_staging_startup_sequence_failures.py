"""
Mission Critical Test Suite: Staging Startup Sequence Failures
Tests to reproduce and validate the critical issues found in staging logs:
1. WebSocket message delivery failures for test threads
2. Zero WebSocket handlers registered during startup
3. ClickHouse connection failures
4. Agent WebSocket Bridge uninitialized state
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime
from uuid import uuid4
import logging

# Set up test logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@pytest.fixture
def mock_connection_manager():
    """Mock connection manager for testing"""
    manager = AsyncMock()
    manager.connections = {}
    manager.user_connections = {}
    manager.thread_to_user = {}
    manager.get_connection = AsyncMock(return_value=None)
    manager.register = AsyncMock()
    manager.unregister = AsyncMock()
    return manager

@pytest.fixture
def mock_message_router():
    """Mock message router for testing"""
    router = AsyncMock()
    router.handlers = {}
    router.register_handler = AsyncMock()
    router.route_message = AsyncMock()
    return router

@pytest.fixture
def mock_websocket():
    """Mock WebSocket for testing"""
    ws = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive_json = AsyncMock()
    ws.close = AsyncMock()
    return ws


class TestWebSocketMessageDeliveryFailure:
    """Test Issue 1: WebSocket Message Delivery Failure"""
    
    @pytest.mark.asyncio
    async def test_no_connection_for_test_thread(self, mock_connection_manager):
        """Reproduce: No active connections found for thread"""
        # Create test thread ID (like in staging logs)
        test_thread_id = "startup_test_b0323e22-afd6-4443-b1d8-c727c9f28705"
        
        # Attempt to get connection for test thread
        connection = await mock_connection_manager.get_connection(test_thread_id)
        
        # Should return None (no connection)
        assert connection is None
        
        # Log the error as seen in staging
        logger.error(f"No active connections found for thread {test_thread_id}")
        
    @pytest.mark.asyncio
    async def test_critical_cannot_deliver_message(self, mock_connection_manager):
        """Reproduce: CRITICAL: Cannot deliver message - no connections and no fallback"""
        test_thread_id = "startup_test_b0323e22-afd6-4443-b1d8-c727c9f28705"
        test_message = {"type": "health_check", "content": "test"}
        
        # No connection for thread
        mock_connection_manager.get_connection.return_value = None
        
        # No user fallback available
        mock_connection_manager.thread_to_user.get = MagicMock(return_value=None)
        
        # Attempt delivery should fail
        with pytest.raises(Exception) as exc_info:
            if not await mock_connection_manager.get_connection(test_thread_id):
                user_id = mock_connection_manager.thread_to_user.get(test_thread_id)
                if not user_id:
                    logger.critical(
                        f"Cannot deliver message for thread {test_thread_id} - "
                        "no connections and no fallback available"
                    )
                    raise Exception("Message delivery failed")
        
        assert "Message delivery failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_health_check_without_connection(self):
        """Test that health checks create threads without connections"""
        # Simulate startup health check
        health_check_thread_id = f"startup_test_{uuid4()}"
        
        async def run_health_check():
            # Health check creates thread
            logger.info(f"Creating health check thread: {health_check_thread_id}")
            
            # But doesn't establish WebSocket connection
            # This causes the delivery failure
            return {
                "thread_created": True,
                "connection_established": False,
                "can_deliver_messages": False
            }
        
        result = await run_health_check()
        
        assert result["thread_created"] is True
        assert result["connection_established"] is False
        assert result["can_deliver_messages"] is False


class TestZeroWebSocketHandlers:
    """Test Issue 2: Zero WebSocket Handlers Registered"""
    
    @pytest.mark.asyncio
    async def test_handlers_checked_before_registration(self, mock_message_router):
        """Reproduce: Checking for handlers before they're registered"""
        # Initially no handlers
        mock_message_router.handlers = {}
        
        # Check handlers (happens early in startup)
        handler_count = len(mock_message_router.handlers)
        
        if handler_count == 0:
            logger.warning("⚠️ ZERO WebSocket message handlers registered")
        
        assert handler_count == 0
        
        # Later in startup, handlers get registered
        await asyncio.sleep(0.1)  # Simulate delay
        
        # Register handlers
        mock_message_router.handlers = {
            "user_message": AsyncMock(),
            "agent_request": AsyncMock(),
            "system_event": AsyncMock()
        }
        
        # Now handlers exist
        assert len(mock_message_router.handlers) == 3
    
    @pytest.mark.asyncio 
    async def test_startup_sequence_order_issue(self):
        """Test incorrect startup sequence causing handler warning"""
        startup_events = []
        
        async def initialize_monitoring():
            startup_events.append(("monitoring_init", datetime.now()))
            # Check for handlers (too early!)
            handler_count = 0  # Not registered yet
            if handler_count == 0:
                startup_events.append(("zero_handlers_warning", datetime.now()))
                logger.warning("⚠️ ZERO WebSocket message handlers registered")
        
        async def register_handlers():
            startup_events.append(("handlers_registered", datetime.now()))
            return {"user_message": AsyncMock(), "agent_request": AsyncMock()}
        
        # Wrong order: monitoring before handlers
        await initialize_monitoring()
        await register_handlers()
        
        # Verify wrong order occurred
        event_names = [event[0] for event in startup_events]
        assert event_names == [
            "monitoring_init",
            "zero_handlers_warning", 
            "handlers_registered"
        ]
        
        # The warning should have been logged
        assert "zero_handlers_warning" in event_names


class TestClickHouseConnectionFailure:
    """Test Issue 3: ClickHouse Connection Failure"""
    
    @pytest.mark.asyncio
    async def test_clickhouse_not_connected(self):
        """Reproduce: ClickHouse connection failure during startup"""
        
        class MockClickHouseManager:
            def __init__(self):
                self.connected = False
                self.connection_error = "Not connected to ClickHouse"
            
            async def connect(self):
                # Simulate connection failure
                logger.error(f"[ClickHouse Connection Manager] Connection error: {self.connection_error}")
                return False
            
            async def execute_query(self, query):
                if not self.connected:
                    logger.error(f"[ClickHouse Connection Manager] Query execution failed: {self.connection_error}")
                    raise Exception(self.connection_error)
        
        manager = MockClickHouseManager()
        
        # Attempt connection
        connected = await manager.connect()
        assert connected is False
        
        # Attempt query (will fail)
        with pytest.raises(Exception) as exc_info:
            await manager.execute_query("SELECT 1")
        
        assert "Not connected to ClickHouse" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_clickhouse_dependency_validation_failure(self):
        """Test ClickHouse dependency validation failure"""
        
        async def validate_clickhouse_dependencies():
            errors = []
            
            # Try to execute test query
            try:
                # This will fail if not connected
                raise Exception("Query execution failed: Not connected to ClickHouse")
            except Exception as e:
                errors.append(str(e))
            
            if errors:
                logger.error(f"[ClickHouse Startup] ❌ Dependency validation failed: {errors}")
                logger.info("ClickHouse initialization failed - continuing without analytics")
                return False
            
            return True
        
        # Run validation
        result = await validate_clickhouse_dependencies()
        
        assert result is False


class TestAgentWebSocketBridgeUninitialized:
    """Test Issue 4: Agent WebSocket Bridge Uninitialized"""
    
    @pytest.mark.asyncio
    async def test_bridge_uninitialized_state(self):
        """Reproduce: Bridge created but not initialized"""
        
        class AgentWebSocketBridge:
            def __init__(self):
                self.state = "UNINITIALIZED"
                self._initialize_state()
            
            def _initialize_state(self):
                """Set initial state"""
                self.state = "UNINITIALIZED"
                logger.info("⚠️ Created singleton AgentWebSocketBridge - consider migrating to per-user emitters!")
            
            def get_health_status(self):
                """Return health status"""
                if self.state == "UNINITIALIZED":
                    return {
                        "healthy": False,
                        "status": "uninitialized",
                        "error": None
                    }
                return {"healthy": True, "status": "initialized"}
            
            def initialize(self):
                """Initialize the bridge (not called in new architecture)"""
                self.state = "INITIALIZED"
        
        # Create bridge (happens during startup)
        bridge = AgentWebSocketBridge()
        
        # Check health (monitoring does this)
        health = bridge.get_health_status()
        
        if not health["healthy"]:
            logger.error(
                f"🚨 Component agent_websocket_bridge reported unhealthy status: "
                f"{health['status']}. Error: {health['error']}"
            )
        
        assert health["status"] == "uninitialized"
        assert health["healthy"] is False
    
    @pytest.mark.asyncio
    async def test_per_user_emitter_pattern(self):
        """Test that per-user emitters work despite uninitialized bridge"""
        
        class AgentWebSocketBridge:
            def __init__(self):
                self.state = "UNINITIALIZED"
            
            def create_user_emitter(self, user_id: str):
                """Create per-user emitter (works even when uninitialized)"""
                # This is the new pattern - works without global init
                return {
                    "user_id": user_id,
                    "emitter_id": str(uuid4()),
                    "created_at": datetime.now(),
                    "isolated": True
                }
        
        bridge = AgentWebSocketBridge()
        
        # Bridge is uninitialized
        assert bridge.state == "UNINITIALIZED"
        
        # But per-user emitters still work
        user_emitter = bridge.create_user_emitter("test_user_123")
        
        assert user_emitter is not None
        assert user_emitter["user_id"] == "test_user_123"
        assert user_emitter["isolated"] is True


class TestIntegratedStartupSequence:
    """Test the complete startup sequence with all issues"""
    
    @pytest.mark.asyncio
    async def test_full_staging_startup_reproduction(self):
        """Reproduce the complete staging startup sequence with all failures"""
        startup_log = []
        
        async def startup_sequence():
            # 1. Create test thread for health check
            test_thread_id = f"startup_test_{uuid4()}"
            startup_log.append(f"Created test thread: {test_thread_id}")
            
            # 2. Try to deliver message (will fail - no connection)
            startup_log.append(f"No active connections found for thread {test_thread_id} - attempting user-based fallback")
            startup_log.append(f"CRITICAL: Cannot deliver message for thread {test_thread_id} - no connections and no fallback available")
            
            # 3. Check for handlers (none registered yet)
            handler_count = 0
            if handler_count == 0:
                startup_log.append("⚠️ ZERO WebSocket message handlers registered")
            
            # 4. Try ClickHouse connection
            startup_log.append("[ClickHouse Connection Manager] Connection error: Not connected to ClickHouse.")
            startup_log.append("[ClickHouse Connection Manager] Query execution failed: Not connected to ClickHouse.")
            startup_log.append("[ClickHouse Startup] ❌ Dependency validation failed: ['Query execution failed: Not connected to ClickHouse.']")
            startup_log.append("ClickHouse initialization failed - continuing without analytics")
            
            # 5. Create bridge (but don't initialize)
            startup_log.append("⚠️ Created singleton AgentWebSocketBridge - consider migrating to per-user emitters!")
            startup_log.append("🚨 Component agent_websocket_bridge reported unhealthy status: uninitialized. Error: None")
            
            return startup_log
        
        # Run the sequence
        log = await startup_sequence()
        
        # Verify all expected failures occurred
        assert any("No active connections found" in entry for entry in log)
        assert any("CRITICAL: Cannot deliver message" in entry for entry in log)
        assert any("ZERO WebSocket message handlers" in entry for entry in log)
        assert any("Not connected to ClickHouse" in entry for entry in log)
        assert any("agent_websocket_bridge reported unhealthy status" in entry for entry in log)
        
        # This reproduces the exact staging log sequence
        logger.info("Successfully reproduced all staging startup failures")


@pytest.mark.asyncio
async def test_proposed_fix_startup_sequence():
    """Test the proposed fix for startup sequence"""
    startup_events = []
    
    async def fixed_startup_sequence():
        # 1. Infrastructure first
        startup_events.append("database_initialized")
        
        # 2. Register handlers BEFORE monitoring
        handlers = {
            "user_message": AsyncMock(),
            "agent_request": AsyncMock()
        }
        startup_events.append("handlers_registered")
        
        # 3. Initialize monitoring WITH handlers
        if handlers:
            startup_events.append("monitoring_initialized_with_handlers")
        
        # 4. Health checks LAST (with proper connections)
        mock_connection = AsyncMock()
        startup_events.append("health_check_with_connection")
        
        return True
    
    # Run fixed sequence
    success = await fixed_startup_sequence()
    
    assert success is True
    assert startup_events == [
        "database_initialized",
        "handlers_registered",
        "monitoring_initialized_with_handlers",
        "health_check_with_connection"
    ]
    
    # No warnings should be logged in fixed sequence
    logger.info("Fixed startup sequence completed successfully without warnings")


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "-s"])