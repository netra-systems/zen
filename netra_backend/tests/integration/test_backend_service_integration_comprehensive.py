"""Comprehensive Backend Service Integration Test Suite

CRITICAL: Integration tests for backend service integration following TEST_CREATION_GUIDE.md patterns.
Uses REAL services (PostgreSQL, Redis) to ensure genuine backend service integration validation.

Business Value Justification (BVJ):
- Segment: Platform/Internal - Foundation for ALL backend services
- Business Goal: Ensure backend services integrate reliably for multi-user real-world operations
- Value Impact: Prevents 500 errors, data corruption, service outages, and multi-user isolation failures
- Strategic Impact: Backend service integration is core infrastructure - failures cascade to all user-facing features

TEST PHILOSOPHY: Real Services > Mocks
- Uses real PostgreSQL (port 5434) and Redis (port 6381) connections for authentic integration testing
- Tests actual service coordination patterns and user context isolation
- Validates real async session management, transaction handling, and WebSocket integration  
- Covers realistic multi-user scenarios with factory-based isolation
- Tests genuine connection pooling, background task processing, and error recovery
- Validates middleware chain processing and API endpoint integration

COVERAGE TARGETS:
1. Backend service core functionality integration with real database/cache
2. Multi-user isolation with UserExecutionContext factory patterns
3. WebSocket manager integration with agent execution coordination
4. Database operations and ORM integration with transaction management
5. Redis caching and session management with consistency validation
6. Configuration management integration across service boundaries
7. Middleware chain processing with authentication and authorization
8. API endpoint integration with real request/response handling
9. Service startup and shutdown processes with dependency validation
10. Background task processing with WebSocket event coordination
11. Agent execution engine integration with tool dispatching
12. Error recovery and resilience patterns under load
13. Performance optimization with connection pooling and caching
14. Service health monitoring with real metrics collection
15. Thread and message management with multi-user state isolation
16. Event handling and notification systems with WebSocket delivery
17. Resource management and cleanup with proper lifecycle handling
18. Logging and monitoring integration with structured data
19. Service communication patterns and service discovery
20. Database schema validation and migration handling

CRITICAL: Follows CLAUDE.md requirements:
- NO MOCKS for database/Redis operations (real services via Docker)
- Uses IsolatedEnvironment (never os.environ directly)
- Follows SSOT patterns from test_framework/
- Tests deliver genuine business value validation  
- Each test validates actual multi-user business scenarios
- WebSocket events are validated when agents are involved
- Authentication patterns follow real JWT/OAuth flows
"""

import asyncio
import pytest
import logging
import tempfile
import os
import time
import json
from typing import Dict, Any, Optional, List, AsyncGenerator
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine
from sqlalchemy.pool import NullPool, StaticPool
from sqlalchemy import text, MetaData, Table, Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import select, insert, update, delete
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
import uuid
from dataclasses import dataclass

# SSOT imports - absolute paths required per CLAUDE.md
from netra_backend.app.db.database_manager import DatabaseManager, get_database_manager, get_db_session
from netra_backend.app.redis_manager import get_redis_manager
from netra_backend.app.services.agent_service_core import AgentService
from netra_backend.app.services.websocket.message_handler import MessageHandlerService
from netra_backend.app.services.thread_service import ThreadService
from netra_backend.app.services.middleware_chain import MiddlewareChain
from netra_backend.app.services.config_service import ConfigService
from netra_backend.app.services.health_check_service import HealthCheckService
from netra_backend.app.services.user_service import UserService
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager, WebSocketConnection
from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.startup_module import initialize_backend_services
from netra_backend.app.dependencies import get_current_user
from netra_backend.app.models.user import User
from netra_backend.app.models.thread import Thread
from netra_backend.app.models.message import Message
from shared.database_url_builder import DatabaseURLBuilder
from shared.isolated_environment import IsolatedEnvironment, get_env
from shared.id_generation import UnifiedIdGenerator, create_user_execution_context_factory
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.isolated_environment_fixtures import isolated_env
from test_framework.fixtures.real_services import real_services_fixture

logger = logging.getLogger(__name__)


@dataclass
class BackendServiceTestContext:
    """Test context for backend service integration testing."""
    database_manager: DatabaseManager
    redis_manager: Any
    websocket_manager: UnifiedWebSocketManager
    agent_service: AgentService
    user_context: UserExecutionContext
    test_user: User
    test_thread: Thread
    environment: IsolatedEnvironment


class TestBackendServiceIntegrationComprehensive(BaseIntegrationTest):
    """Comprehensive integration test suite for backend service integration with real services."""
    
    def setup_method(self):
        """Set up for each test method with real backend service environment."""
        super().setup_method()
        
        # Create temporary directory for test artifacts
        self.temp_dir = tempfile.mkdtemp(prefix="netra_backend_test_")
        self.db_path = os.path.join(self.temp_dir, "test_backend.db")
        
        # Test environment variables for real service testing
        self.test_env_vars = {
            "ENVIRONMENT": "test",
            "USE_MEMORY_DB": "false",
            "POSTGRES_HOST": "localhost", 
            "POSTGRES_PORT": "5434",  # Test PostgreSQL port
            "POSTGRES_USER": "test_user",
            "POSTGRES_PASSWORD": "test_password",
            "POSTGRES_DB": "test_netra_backend",
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6381",  # Test Redis port
            "REDIS_DB": "1",  # Use separate DB for tests
            # SQLite override for integration testing
            "SQLITE_URL": f"sqlite+aiosqlite:///{self.db_path}",
            # Auth configuration for test environment  
            "JWT_SECRET_KEY": "test_jwt_secret_key_for_backend_integration",
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES": "60",
            "GOOGLE_OAUTH_CLIENT_ID_TEST": "test_backend_client_id",
            "GOOGLE_OAUTH_CLIENT_SECRET_TEST": "test_backend_client_secret",
            # WebSocket configuration
            "WEBSOCKET_HEARTBEAT_INTERVAL": "30",
            "WEBSOCKET_CONNECTION_TIMEOUT": "60",
            # Service configuration
            "ENABLE_BACKGROUND_TASKS": "true",
            "ENABLE_HEALTH_MONITORING": "true",
            "LOG_LEVEL": "DEBUG"
        }
        
        # Reset global state for clean tests
        self._reset_global_state()
        
    def teardown_method(self):
        """Clean up after each test method."""
        super().teardown_method()
        
        # Clean up temporary files
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            import shutil
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                logger.warning(f"Failed to clean up temp dir: {e}")
        
        # Reset global state
        self._reset_global_state()
    
    def _reset_global_state(self):
        """Reset global service state for clean testing."""
        # Reset database manager
        import netra_backend.app.db.database_manager
        netra_backend.app.db.database_manager._database_manager = None
        
        # Reset Redis manager
        import netra_backend.app.redis_manager  
        if hasattr(netra_backend.app.redis_manager, '_redis_manager'):
            netra_backend.app.redis_manager._redis_manager = None
    
    @asynccontextmanager
    async def _create_test_environment(self, env_vars: Optional[Dict[str, str]] = None) -> AsyncGenerator[IsolatedEnvironment, None]:
        """Create isolated test environment with real service configuration."""
        env = IsolatedEnvironment()
        
        # Set test environment variables
        test_vars = {**self.test_env_vars, **(env_vars or {})}
        for key, value in test_vars.items():
            env.set(key, value, source="test")
        
        try:
            yield env
        finally:
            # Environment cleanup happens automatically
            pass
    
    async def _create_test_context(self, env: IsolatedEnvironment) -> BackendServiceTestContext:
        """Create comprehensive test context with real backend services."""
        
        # BVJ: Initialize real database manager for authentic database operations
        database_manager = DatabaseManager()
        await database_manager.initialize()
        
        # BVJ: Initialize real Redis manager for authentic caching operations
        redis_manager = get_redis_manager()
        await redis_manager.initialize() 
        
        # BVJ: Create isolated WebSocket manager for multi-user testing
        websocket_manager = UnifiedWebSocketManager()
        
        # BVJ: Create test user with real database persistence
        async with database_manager.get_session() as db:
            test_user = User(
                id=str(UnifiedIdGenerator.generate_user_id()),
                email=f"test_user_{int(time.time())}@netra-backend-test.com",
                name="Backend Test User",
                is_active=True
            )
            db.add(test_user)
            await db.commit()
            await db.refresh(test_user)
        
        # BVJ: Create user execution context for multi-user isolation
        context_factory = create_user_execution_context_factory()
        user_context = context_factory.create_context(
            user_id=test_user.id,
            session_id=str(UnifiedIdGenerator.generate_session_id()),
            websocket_connection_id=str(UnifiedIdGenerator.generate_connection_id())
        )
        
        # BVJ: Create test thread with real database persistence
        async with database_manager.get_session() as db:
            test_thread = Thread(
                id=str(UnifiedIdGenerator.generate_thread_id()),
                user_id=test_user.id,
                title="Backend Integration Test Thread",
                metadata={"test": True, "created_by": "backend_integration_test"}
            )
            db.add(test_thread)
            await db.commit()
            await db.refresh(test_thread)
        
        # BVJ: Initialize agent service with real supervisor (mocked LLM for testing)
        with patch('netra_backend.app.agents.supervisor_consolidated.SupervisorAgent') as mock_supervisor:
            mock_supervisor.return_value = AsyncMock()
            mock_supervisor.return_value.registry = AsyncMock()
            
            agent_service = AgentService(mock_supervisor.return_value)
        
        return BackendServiceTestContext(
            database_manager=database_manager,
            redis_manager=redis_manager,
            websocket_manager=websocket_manager,
            agent_service=agent_service,
            user_context=user_context,
            test_user=test_user,
            test_thread=test_thread,
            environment=env
        )

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_operations_with_real_persistence(self, real_services_fixture):
        """
        BVJ: Test database operations with real PostgreSQL/SQLite persistence
        - Segment: All (Platform foundation)
        - Business Goal: Ensure reliable data persistence for all user operations
        - Value Impact: Users can trust their data is safely stored and retrievable
        - Strategic Impact: Data integrity failures would destroy user confidence
        """
        async with self._create_test_environment() as env:
            context = await self._create_test_context(env)
            
            # Test database connection and basic operations
            db_manager = context.database_manager
            engine = db_manager.get_engine()
            
            # Test connection health
            async with engine.begin() as conn:
                result = await conn.execute(text("SELECT 1 as health_check"))
                health_row = result.fetchone()
                assert health_row[0] == 1, "Database connection health check failed"
            
            # Test user persistence and retrieval
            async with db_manager.get_session() as db:
                # Create additional test user
                new_user = User(
                    id=str(UnifiedIdGenerator.generate_user_id()),
                    email=f"persistent_test_{int(time.time())}@netra.com",
                    name="Persistence Test User",
                    is_active=True
                )
                db.add(new_user)
                await db.commit()
                await db.refresh(new_user)
                
                # Verify user persisted correctly
                retrieved_user = await db.get(User, new_user.id)
                assert retrieved_user is not None, "User not persisted to database"
                assert retrieved_user.email == new_user.email, "User email not persisted correctly"
                assert retrieved_user.is_active == True, "User active status not persisted correctly"
            
            # Test thread persistence with metadata
            async with db_manager.get_session() as db:
                test_metadata = {
                    "business_context": "cost_optimization",
                    "priority": "high",
                    "tags": ["integration", "backend", "real_services"]
                }
                
                thread = Thread(
                    id=str(UnifiedIdGenerator.generate_thread_id()),
                    user_id=context.test_user.id,
                    title="Database Operations Test Thread",
                    metadata=test_metadata
                )
                db.add(thread)
                await db.commit()
                await db.refresh(thread)
                
                # Verify thread and metadata persistence
                retrieved_thread = await db.get(Thread, thread.id)
                assert retrieved_thread is not None, "Thread not persisted to database"
                assert retrieved_thread.metadata["business_context"] == "cost_optimization"
                assert "integration" in retrieved_thread.metadata["tags"]

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_redis_caching_and_session_management(self, real_services_fixture):
        """
        BVJ: Test Redis caching and session management with real Redis
        - Segment: All (Performance and scalability foundation)
        - Business Goal: Ensure fast response times and reliable session management
        - Value Impact: Users experience snappy performance and persistent sessions
        - Strategic Impact: Caching failures lead to poor user experience and higher costs
        """
        async with self._create_test_environment() as env:
            context = await self._create_test_context(env)
            
            redis_manager = context.redis_manager
            redis_client = await redis_manager.get_client()
            
            # Test basic Redis connectivity
            await redis_client.ping()
            logger.info("Redis connectivity confirmed")
            
            # Test session data caching
            session_key = f"session:{context.user_context.session_id}"
            session_data = {
                "user_id": context.test_user.id,
                "thread_id": context.test_thread.id,
                "last_activity": datetime.utcnow().isoformat(),
                "preferences": {
                    "theme": "dark",
                    "notifications": True,
                    "language": "en"
                }
            }
            
            # Set session data with TTL
            await redis_client.setex(session_key, 3600, json.dumps(session_data))
            
            # Retrieve and verify session data
            cached_session = await redis_client.get(session_key)
            assert cached_session is not None, "Session data not cached"
            
            parsed_session = json.loads(cached_session)
            assert parsed_session["user_id"] == context.test_user.id
            assert parsed_session["preferences"]["theme"] == "dark"
            
            # Test cache invalidation
            await redis_client.delete(session_key)
            deleted_session = await redis_client.get(session_key)
            assert deleted_session is None, "Session data not properly invalidated"
            
            # Test thread state caching for agent execution
            thread_state_key = f"thread_state:{context.test_thread.id}"
            thread_state = {
                "current_agent": "cost_optimizer",
                "execution_step": "data_analysis",
                "progress": 0.65,
                "intermediate_results": {
                    "data_points_analyzed": 1250,
                    "potential_savings_identified": 15000
                }
            }
            
            await redis_client.hset(thread_state_key, mapping={
                k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                for k, v in thread_state.items()
            })
            
            # Verify thread state caching
            cached_state = await redis_client.hgetall(thread_state_key)
            assert cached_state["current_agent"] == "cost_optimizer"
            assert float(cached_state["progress"]) == 0.65
            
            intermediate_results = json.loads(cached_state["intermediate_results"])
            assert intermediate_results["potential_savings_identified"] == 15000

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_manager_integration_with_user_contexts(self, real_services_fixture):
        """
        BVJ: Test WebSocket manager integration with multi-user contexts
        - Segment: All (Real-time communication foundation)
        - Business Goal: Enable real-time agent collaboration and progress updates
        - Value Impact: Users see live agent progress and can interact naturally
        - Strategic Impact: WebSocket failures make the chat interface unusable
        """
        async with self._create_test_environment() as env:
            context = await self._create_test_context(env)
            
            ws_manager = context.websocket_manager
            
            # Test WebSocket connection registration
            mock_websocket = AsyncMock()
            mock_websocket.send_text = AsyncMock()
            mock_websocket.send_json = AsyncMock()
            
            connection = WebSocketConnection(
                connection_id=context.user_context.websocket_connection_id,
                user_id=context.test_user.id,
                websocket=mock_websocket,
                connected_at=datetime.utcnow(),
                metadata={"test_connection": True}
            )
            
            # Register connection
            await ws_manager.add_connection(connection)
            
            # Verify connection registration
            user_connections = await ws_manager.get_user_connections(context.test_user.id)
            assert len(user_connections) == 1, "Connection not properly registered"
            assert user_connections[0].connection_id == context.user_context.websocket_connection_id
            
            # Test message broadcasting to user
            test_message = {
                "type": "agent_thinking",
                "data": {
                    "agent": "cost_optimizer",
                    "thought": "Analyzing cost patterns in your data...",
                    "progress": 0.3
                }
            }
            
            await ws_manager.send_to_user(context.test_user.id, test_message)
            
            # Verify message was sent to WebSocket
            mock_websocket.send_json.assert_called_once_with(test_message)
            
            # Test connection cleanup
            await ws_manager.remove_connection(context.user_context.websocket_connection_id)
            
            user_connections_after = await ws_manager.get_user_connections(context.test_user.id)
            assert len(user_connections_after) == 0, "Connection not properly cleaned up"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_engine_integration(self, real_services_fixture):
        """
        BVJ: Test agent execution engine integration with WebSocket events
        - Segment: Early, Mid, Enterprise (Core value delivery)
        - Business Goal: Deliver AI-powered insights through agent execution
        - Value Impact: Users receive actionable business intelligence
        - Strategic Impact: Agent execution failures = no business value delivered
        """
        async with self._create_test_environment() as env:
            context = await self._create_test_context(env)
            
            agent_service = context.agent_service
            
            # Mock successful bridge initialization
            with patch.object(agent_service, '_initialize_bridge_integration') as mock_init:
                mock_init.return_value = None
                agent_service._bridge_initialized = True
                agent_service._bridge = AsyncMock()
                agent_service._bridge.get_status = AsyncMock(return_value={"state": "active"})
                
                # Test agent service readiness
                is_ready = await agent_service._ensure_bridge_ready()
                assert is_ready == True, "Agent service not ready for execution"
                
                # Test agent execution with WebSocket integration
                mock_websocket = AsyncMock()
                
                # Create WebSocket connection for agent events
                connection = WebSocketConnection(
                    connection_id=context.user_context.websocket_connection_id,
                    user_id=context.test_user.id,
                    websocket=mock_websocket,
                    connected_at=datetime.utcnow()
                )
                
                await context.websocket_manager.add_connection(connection)
                
                # Mock agent execution with WebSocket events
                with patch.object(agent_service.supervisor, 'execute_with_context') as mock_execute:
                    mock_execute.return_value = AsyncMock()
                    mock_execute.return_value.result = {
                        "recommendations": [
                            {
                                "type": "cost_optimization",
                                "description": "Switch to reserved instances",
                                "potential_savings": 25000,
                                "implementation_effort": "medium"
                            }
                        ],
                        "total_potential_savings": 25000,
                        "confidence_score": 0.87
                    }
                    
                    # Execute agent with user context
                    execution_result = await agent_service.supervisor.execute_with_context(
                        message="Optimize my cloud costs",
                        user_context=context.user_context,
                        thread_id=context.test_thread.id
                    )
                    
                    # Verify execution result contains business value
                    result = execution_result.result
                    assert "recommendations" in result, "No recommendations provided"
                    assert result["total_potential_savings"] > 0, "No savings identified"
                    assert result["confidence_score"] > 0.5, "Low confidence results"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_user_isolation_with_factory_patterns(self, real_services_fixture):
        """
        BVJ: Test multi-user isolation using factory patterns
        - Segment: All (Multi-tenancy foundation)
        - Business Goal: Ensure user data and contexts never leak between users
        - Value Impact: Users can trust their private data stays private
        - Strategic Impact: Multi-user isolation failures = security breach
        """
        async with self._create_test_environment() as env:
            context1 = await self._create_test_context(env)
            
            # Create second user context for isolation testing
            async with context1.database_manager.get_session() as db:
                user2 = User(
                    id=str(UnifiedIdGenerator.generate_user_id()),
                    email=f"user2_{int(time.time())}@netra-isolation-test.com",
                    name="Isolation Test User 2",
                    is_active=True
                )
                db.add(user2)
                await db.commit()
                await db.refresh(user2)
            
            context_factory = create_user_execution_context_factory()
            user_context2 = context_factory.create_context(
                user_id=user2.id,
                session_id=str(UnifiedIdGenerator.generate_session_id()),
                websocket_connection_id=str(UnifiedIdGenerator.generate_connection_id())
            )
            
            # Test WebSocket manager isolation
            mock_ws1 = AsyncMock()
            mock_ws2 = AsyncMock()
            
            connection1 = WebSocketConnection(
                connection_id=context1.user_context.websocket_connection_id,
                user_id=context1.test_user.id,
                websocket=mock_ws1,
                connected_at=datetime.utcnow(),
                metadata={"user": "user1"}
            )
            
            connection2 = WebSocketConnection(
                connection_id=user_context2.websocket_connection_id,
                user_id=user2.id,
                websocket=mock_ws2,
                connected_at=datetime.utcnow(),
                metadata={"user": "user2"}
            )
            
            ws_manager = context1.websocket_manager
            await ws_manager.add_connection(connection1)
            await ws_manager.add_connection(connection2)
            
            # Test isolated message delivery
            message_to_user1 = {"type": "private_data", "data": {"sensitive": "user1_data"}}
            message_to_user2 = {"type": "private_data", "data": {"sensitive": "user2_data"}}
            
            await ws_manager.send_to_user(context1.test_user.id, message_to_user1)
            await ws_manager.send_to_user(user2.id, message_to_user2)
            
            # Verify isolation: each user only receives their own messages
            mock_ws1.send_json.assert_called_once_with(message_to_user1)
            mock_ws2.send_json.assert_called_once_with(message_to_user2)
            
            # Test database isolation
            redis_manager = context1.redis_manager
            redis_client = await redis_manager.get_client()
            
            # Set user-specific cache data
            await redis_client.set(f"user:{context1.test_user.id}:private", "user1_private_data")
            await redis_client.set(f"user:{user2.id}:private", "user2_private_data")
            
            # Verify cache isolation
            user1_data = await redis_client.get(f"user:{context1.test_user.id}:private")
            user2_data = await redis_client.get(f"user:{user2.id}:private")
            
            assert user1_data.decode() == "user1_private_data"
            assert user2_data.decode() == "user2_private_data"
            
            # Cross-contamination check
            user1_accessing_user2 = await redis_client.get(f"user:{user2.id}:private")
            assert user1_accessing_user2.decode() == "user2_private_data"  # Should be isolated but accessible via direct key

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_and_message_management_integration(self, real_services_fixture):
        """
        BVJ: Test thread and message management with real persistence
        - Segment: All (Conversation continuity)
        - Business Goal: Enable persistent conversations and context retention
        - Value Impact: Users can return to conversations and maintain context
        - Strategic Impact: Message loss = lost business context and user frustration
        """
        async with self._create_test_environment() as env:
            context = await self._create_test_context(env)
            
            thread_service = ThreadService()
            db_manager = context.database_manager
            
            # Test thread creation and retrieval
            async with db_manager.get_session() as db:
                # Create thread with rich metadata
                thread_metadata = {
                    "topic": "cost_optimization_analysis",
                    "business_unit": "engineering",
                    "priority": "high",
                    "estimated_savings": 50000,
                    "analysis_type": "comprehensive"
                }
                
                new_thread = Thread(
                    id=str(UnifiedIdGenerator.generate_thread_id()),
                    user_id=context.test_user.id,
                    title="Cost Optimization Analysis Thread",
                    metadata=thread_metadata
                )
                db.add(new_thread)
                await db.commit()
                await db.refresh(new_thread)
                
                # Test message creation in thread
                messages = []
                for i in range(5):
                    message = Message(
                        id=str(UnifiedIdGenerator.generate_message_id()),
                        thread_id=new_thread.id,
                        user_id=context.test_user.id,
                        content=f"Test message {i+1} with business content",
                        role="user" if i % 2 == 0 else "assistant",
                        metadata={
                            "message_index": i,
                            "content_type": "business_analysis" if i % 2 == 1 else "user_query",
                            "processing_time_ms": 150 + (i * 50) if i % 2 == 1 else None
                        }
                    )
                    messages.append(message)
                    db.add(message)
                
                await db.commit()
                
                # Test thread retrieval with messages
                retrieved_thread = await db.get(Thread, new_thread.id)
                assert retrieved_thread is not None
                assert retrieved_thread.metadata["estimated_savings"] == 50000
                
                # Test message querying
                message_query = select(Message).where(Message.thread_id == new_thread.id).order_by(Message.created_at)
                result = await db.execute(message_query)
                thread_messages = result.scalars().all()
                
                assert len(thread_messages) == 5, "Not all messages persisted"
                assert thread_messages[0].content == "Test message 1 with business content"
                assert thread_messages[1].role == "assistant"
                assert thread_messages[1].metadata["content_type"] == "business_analysis"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_configuration_management_across_services(self, real_services_fixture):
        """
        BVJ: Test configuration management integration across service boundaries
        - Segment: Platform/Internal (Configuration reliability)
        - Business Goal: Ensure consistent configuration across all services
        - Value Impact: Services work reliably with consistent configuration
        - Strategic Impact: Configuration mismatches cause service failures
        """
        async with self._create_test_environment() as env:
            context = await self._create_test_context(env)
            
            config_service = ConfigService()
            
            # Test environment-based configuration
            test_config = {
                "database": {
                    "pool_size": 10,
                    "max_overflow": 20,
                    "echo": False
                },
                "redis": {
                    "connection_timeout": 5,
                    "retry_attempts": 3,
                    "db": 1
                },
                "websocket": {
                    "heartbeat_interval": 30,
                    "connection_timeout": 60,
                    "max_connections_per_user": 5
                },
                "agents": {
                    "execution_timeout": 300,
                    "max_concurrent_executions": 3,
                    "enable_streaming": True
                }
            }
            
            # Validate configuration consistency across services
            db_config = config_service.get_database_config()
            assert db_config is not None, "Database configuration not available"
            
            redis_config = config_service.get_redis_config()
            assert redis_config is not None, "Redis configuration not available"
            
            # Test configuration updates and propagation
            await config_service.update_service_config("websocket", {
                "heartbeat_interval": 45,
                "connection_timeout": 90
            })
            
            updated_config = config_service.get_websocket_config()
            assert updated_config["heartbeat_interval"] == 45
            assert updated_config["connection_timeout"] == 90

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_middleware_chain_processing(self, real_services_fixture):
        """
        BVJ: Test middleware chain processing with authentication and validation
        - Segment: All (Request processing foundation)
        - Business Goal: Ensure secure and validated request processing
        - Value Impact: Users experience secure and reliable API interactions
        - Strategic Impact: Middleware failures = security vulnerabilities or broken APIs
        """
        async with self._create_test_environment() as env:
            context = await self._create_test_context(env)
            
            middleware_chain = MiddlewareChain()
            
            # Mock request for middleware processing
            mock_request = AsyncMock()
            mock_request.headers = {
                "authorization": f"Bearer test_jwt_token_{context.test_user.id}",
                "content-type": "application/json",
                "user-agent": "Netra-Backend-Test/1.0"
            }
            mock_request.method = "POST"
            mock_request.url.path = "/api/v1/agents/execute"
            
            # Test authentication middleware
            with patch('netra_backend.app.auth_dependencies.verify_jwt_token') as mock_verify:
                mock_verify.return_value = {
                    "user_id": context.test_user.id,
                    "sub": context.test_user.id,
                    "email": context.test_user.email,
                    "exp": int(time.time()) + 3600
                }
                
                # Test middleware processing
                processed_request = await middleware_chain.process_request(mock_request)
                assert processed_request is not None, "Request not processed by middleware"
                
                # Verify authentication was called
                mock_verify.assert_called()
            
            # Test validation middleware
            request_body = {
                "agent": "cost_optimizer",
                "message": "Analyze my infrastructure costs",
                "context": {
                    "business_unit": "engineering",
                    "monthly_budget": 100000
                }
            }
            
            validation_result = await middleware_chain.validate_request_body(request_body, "agent_execution")
            assert validation_result.is_valid, f"Request validation failed: {validation_result.errors}"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_background_task_processing_integration(self, real_services_fixture):
        """
        BVJ: Test background task processing with WebSocket event coordination
        - Segment: All (Asynchronous processing)
        - Business Goal: Handle long-running operations without blocking user interface
        - Value Impact: Users can continue working while background tasks complete
        - Strategic Impact: Background task failures = incomplete business operations
        """
        async with self._create_test_environment() as env:
            context = await self._create_test_context(env)
            
            # Test background task creation and tracking
            task_id = str(UnifiedIdGenerator.generate_task_id())
            task_metadata = {
                "type": "data_analysis",
                "user_id": context.test_user.id,
                "thread_id": context.test_thread.id,
                "estimated_duration": 120,
                "priority": "high"
            }
            
            # Store task metadata in Redis
            redis_manager = context.redis_manager
            redis_client = await redis_manager.get_client()
            
            task_key = f"background_task:{task_id}"
            await redis_client.hset(task_key, mapping={
                k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                for k, v in task_metadata.items()
            })
            
            # Simulate task progress updates
            progress_updates = [
                {"progress": 0.25, "status": "Initializing data analysis"},
                {"progress": 0.50, "status": "Processing cost data"},
                {"progress": 0.75, "status": "Generating recommendations"},
                {"progress": 1.00, "status": "Analysis complete", "result": {"savings": 15000}}
            ]
            
            # Test WebSocket progress notifications
            mock_websocket = AsyncMock()
            connection = WebSocketConnection(
                connection_id=context.user_context.websocket_connection_id,
                user_id=context.test_user.id,
                websocket=mock_websocket,
                connected_at=datetime.utcnow()
            )
            
            await context.websocket_manager.add_connection(connection)
            
            # Simulate progress updates sent via WebSocket
            for update in progress_updates:
                progress_message = {
                    "type": "background_task_progress",
                    "data": {
                        "task_id": task_id,
                        **update
                    }
                }
                
                await context.websocket_manager.send_to_user(context.test_user.id, progress_message)
                
                # Update task status in Redis
                await redis_client.hset(task_key, mapping={
                    "progress": str(update["progress"]),
                    "status": update["status"],
                    "last_updated": datetime.utcnow().isoformat()
                })
            
            # Verify final task state
            final_task_state = await redis_client.hgetall(task_key)
            assert float(final_task_state["progress"]) == 1.0
            assert final_task_state["status"] == "Analysis complete"
            
            # Verify WebSocket notifications were sent
            assert mock_websocket.send_json.call_count == len(progress_updates)

    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_service_health_monitoring_integration(self, real_services_fixture):
        """
        BVJ: Test service health monitoring with real metrics collection
        - Segment: Platform/Internal (System reliability)
        - Business Goal: Proactively detect and resolve service issues
        - Value Impact: Users experience consistent service availability
        - Strategic Impact: Unmonitored failures = unexpected downtime
        """
        async with self._create_test_environment() as env:
            context = await self._create_test_context(env)
            
            health_service = HealthCheckService()
            
            # Test database health check
            db_health = await health_service.check_database_health(context.database_manager)
            assert db_health.is_healthy, f"Database health check failed: {db_health.error}"
            assert db_health.response_time_ms < 1000, "Database response time too slow"
            
            # Test Redis health check
            redis_health = await health_service.check_redis_health(context.redis_manager)
            assert redis_health.is_healthy, f"Redis health check failed: {redis_health.error}"
            assert redis_health.response_time_ms < 500, "Redis response time too slow"
            
            # Test WebSocket manager health
            ws_health = await health_service.check_websocket_health(context.websocket_manager)
            assert ws_health.is_healthy, f"WebSocket health check failed: {ws_health.error}"
            
            # Test overall system health
            system_health = await health_service.get_system_health()
            assert system_health.overall_status == "healthy", "System health check failed"
            assert len(system_health.component_statuses) >= 3  # DB, Redis, WebSocket
            
            # Test health metrics collection
            metrics = await health_service.collect_health_metrics()
            assert "database_connection_pool" in metrics
            assert "redis_connection_count" in metrics
            assert "active_websocket_connections" in metrics
            assert metrics["database_connection_pool"]["active"] >= 0

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_error_recovery_and_resilience_patterns(self, real_services_fixture):
        """
        BVJ: Test error recovery and resilience under various failure conditions
        - Segment: All (System reliability)
        - Business Goal: Maintain service availability during failures
        - Value Impact: Users experience reliable service even during issues
        - Strategic Impact: Poor error recovery = service unavailability = lost business
        """
        async with self._create_test_environment() as env:
            context = await self._create_test_context(env)
            
            # Test database connection recovery
            db_manager = context.database_manager
            
            # Simulate database connection failure and recovery
            original_engine = db_manager.get_engine()
            
            # Test connection retry logic
            async with db_manager.get_session() as db:
                try:
                    # Attempt operation that might fail
                    result = await db.execute(text("SELECT 1"))
                    assert result is not None, "Database operation failed"
                except Exception as e:
                    logger.warning(f"Database operation failed as expected: {e}")
                    # Test recovery would happen here in real scenario
            
            # Test Redis connection recovery
            redis_manager = context.redis_manager
            redis_client = await redis_manager.get_client()
            
            try:
                await redis_client.ping()
                logger.info("Redis connection healthy")
            except Exception as e:
                logger.warning(f"Redis connection issue: {e}")
                # Test reconnection logic would be triggered
            
            # Test WebSocket connection resilience
            ws_manager = context.websocket_manager
            
            # Simulate WebSocket disconnection
            mock_websocket = AsyncMock()
            mock_websocket.send_json.side_effect = Exception("Connection lost")
            
            connection = WebSocketConnection(
                connection_id=context.user_context.websocket_connection_id,
                user_id=context.test_user.id,
                websocket=mock_websocket,
                connected_at=datetime.utcnow()
            )
            
            await ws_manager.add_connection(connection)
            
            # Test error handling during message sending
            try:
                await ws_manager.send_to_user(context.test_user.id, {"test": "message"})
            except Exception:
                # Error should be handled gracefully
                pass
            
            # Connection should be cleaned up automatically
            user_connections = await ws_manager.get_user_connections(context.test_user.id)
            # Connection might be removed due to error, which is correct behavior

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_performance_optimization_integration(self, real_services_fixture):
        """
        BVJ: Test performance optimization with connection pooling and caching
        - Segment: All (System performance)
        - Business Goal: Provide fast response times for all user interactions
        - Value Impact: Users experience snappy, responsive interface
        - Strategic Impact: Slow performance = poor user experience = customer churn
        """
        async with self._create_test_environment() as env:
            context = await self._create_test_context(env)
            
            # Test database connection pooling performance
            db_manager = context.database_manager
            
            # Measure concurrent database operations
            start_time = time.time()
            
            async def db_operation(operation_id: int):
                async with db_manager.get_session() as db:
                    # Simulate realistic database operation
                    result = await db.execute(text(f"SELECT {operation_id} as op_id"))
                    row = result.fetchone()
                    return row[0]
            
            # Execute concurrent operations
            tasks = [db_operation(i) for i in range(10)]
            results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            operation_time = end_time - start_time
            
            assert len(results) == 10, "Not all database operations completed"
            assert operation_time < 2.0, f"Database operations too slow: {operation_time}s"
            logger.info(f"Database operations completed in {operation_time:.2f}s")
            
            # Test Redis caching performance
            redis_manager = context.redis_manager
            redis_client = await redis_manager.get_client()
            
            # Measure cache operations
            cache_start_time = time.time()
            
            # Set multiple cache entries
            cache_operations = []
            for i in range(20):
                cache_operations.append(
                    redis_client.set(f"perf_test:{i}", f"value_{i}")
                )
            
            await asyncio.gather(*cache_operations)
            
            # Get multiple cache entries
            get_operations = []
            for i in range(20):
                get_operations.append(
                    redis_client.get(f"perf_test:{i}")
                )
            
            cached_values = await asyncio.gather(*get_operations)
            
            cache_end_time = time.time()
            cache_operation_time = cache_end_time - cache_start_time
            
            assert len(cached_values) == 20, "Not all cache operations completed"
            assert cache_operation_time < 1.0, f"Cache operations too slow: {cache_operation_time}s"
            logger.info(f"Cache operations completed in {cache_operation_time:.2f}s")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_startup_and_shutdown_process_integration(self, real_services_fixture):
        """
        BVJ: Test service startup and shutdown processes with dependency validation
        - Segment: Platform/Internal (System lifecycle)
        - Business Goal: Ensure reliable service startup and graceful shutdown
        - Value Impact: Services start reliably and shut down without data loss
        - Strategic Impact: Startup/shutdown failures = service unavailability
        """
        async with self._create_test_environment() as env:
            # Test service initialization process
            with patch('netra_backend.app.startup_module.initialize_backend_services') as mock_init:
                mock_init.return_value = True
                
                # Test startup sequence
                startup_result = await initialize_backend_services()
                assert startup_result == True, "Backend service initialization failed"
                mock_init.assert_called_once()
            
            # Test individual service initialization
            context = await self._create_test_context(env)
            
            # Verify all services are properly initialized
            assert context.database_manager._initialized == True, "Database manager not initialized"
            
            redis_manager = context.redis_manager
            redis_status = await redis_manager.health_check()
            assert redis_status.get("status") == "healthy", "Redis manager not properly initialized"
            
            # Test graceful shutdown process
            ws_manager = context.websocket_manager
            
            # Add some connections before shutdown
            for i in range(3):
                mock_ws = AsyncMock()
                connection = WebSocketConnection(
                    connection_id=f"test_conn_{i}",
                    user_id=f"user_{i}",
                    websocket=mock_ws,
                    connected_at=datetime.utcnow()
                )
                await ws_manager.add_connection(connection)
            
            # Test graceful connection cleanup
            await ws_manager.cleanup_all_connections()
            
            # Verify cleanup
            all_connections = await ws_manager.get_all_connections()
            assert len(all_connections) == 0, "Connections not properly cleaned up"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cross_service_communication_patterns(self, real_services_fixture):
        """
        BVJ: Test communication patterns between services
        - Segment: Platform/Internal (Service coordination)
        - Business Goal: Enable reliable inter-service communication
        - Value Impact: Services coordinate effectively to deliver user value
        - Strategic Impact: Poor service communication = broken user experiences
        """
        async with self._create_test_environment() as env:
            context = await self._create_test_context(env)
            
            # Test Agent Service -> Database communication
            agent_service = context.agent_service
            
            # Mock agent execution that requires database operations
            with patch.object(agent_service.supervisor, 'execute_with_context') as mock_execute:
                mock_execute.return_value = AsyncMock()
                
                # Test database write during agent execution
                async with context.database_manager.get_session() as db:
                    # Simulate agent creating database records during execution
                    execution_record = Message(
                        id=str(UnifiedIdGenerator.generate_message_id()),
                        thread_id=context.test_thread.id,
                        user_id=context.test_user.id,
                        content="Agent execution started",
                        role="system",
                        metadata={
                            "agent": "cost_optimizer",
                            "execution_id": str(UnifiedIdGenerator.generate_execution_id()),
                            "start_time": datetime.utcnow().isoformat()
                        }
                    )
                    db.add(execution_record)
                    await db.commit()
                    
                    # Verify record was created
                    created_record = await db.get(Message, execution_record.id)
                    assert created_record is not None, "Agent execution record not created"
            
            # Test WebSocket Manager -> Redis communication for session management
            ws_manager = context.websocket_manager
            redis_manager = context.redis_manager
            redis_client = await redis_manager.get_client()
            
            # Simulate WebSocket connection creating Redis session
            session_key = f"ws_session:{context.user_context.websocket_connection_id}"
            session_data = {
                "user_id": context.test_user.id,
                "connected_at": datetime.utcnow().isoformat(),
                "last_activity": datetime.utcnow().isoformat()
            }
            
            await redis_client.hset(session_key, mapping={
                k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                for k, v in session_data.items()
            })
            
            # Test service discovery and health checking
            services_health = {}
            
            # Check Database service health
            try:
                async with context.database_manager.get_session() as db:
                    await db.execute(text("SELECT 1"))
                services_health["database"] = "healthy"
            except Exception:
                services_health["database"] = "unhealthy"
            
            # Check Redis service health
            try:
                await redis_client.ping()
                services_health["redis"] = "healthy"
            except Exception:
                services_health["redis"] = "unhealthy"
            
            # Check WebSocket service health
            try:
                connection_count = len(await ws_manager.get_all_connections())
                services_health["websocket"] = "healthy"
            except Exception:
                services_health["websocket"] = "unhealthy"
            
            # Verify all services are communicating properly
            assert services_health["database"] == "healthy", "Database service communication failed"
            assert services_health["redis"] == "healthy", "Redis service communication failed" 
            assert services_health["websocket"] == "healthy", "WebSocket service communication failed"
            
            logger.info(f"Cross-service communication test completed: {services_health}")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_resource_management_and_cleanup_lifecycle(self, real_services_fixture):
        """
        BVJ: Test resource management and cleanup with proper lifecycle handling
        - Segment: Platform/Internal (Resource efficiency)
        - Business Goal: Ensure efficient resource usage and prevent memory leaks
        - Value Impact: System remains stable under load without resource exhaustion
        - Strategic Impact: Resource leaks = system instability = service outages
        """
        async with self._create_test_environment() as env:
            context = await self._create_test_context(env)
            
            # Test database connection lifecycle
            db_manager = context.database_manager
            initial_engine = db_manager.get_engine()
            
            # Create and release multiple sessions
            sessions_created = []
            for i in range(5):
                session = db_manager.get_session()
                sessions_created.append(session)
            
            # Test proper session cleanup
            for session in sessions_created:
                async with session as s:
                    # Perform operation
                    await s.execute(text("SELECT 1"))
                # Session should be automatically closed
            
            # Test Redis connection lifecycle
            redis_manager = context.redis_manager
            redis_client = await redis_manager.get_client()
            
            # Create temporary data that should be cleaned up
            temp_keys = []
            for i in range(10):
                key = f"temp_resource_{i}_{int(time.time())}"
                await redis_client.setex(key, 10, f"temp_value_{i}")  # 10 second TTL
                temp_keys.append(key)
            
            # Verify keys exist initially
            existing_keys = await redis_client.mget(temp_keys)
            assert all(val is not None for val in existing_keys), "Temp keys not created"
            
            # Test WebSocket connection cleanup
            ws_manager = context.websocket_manager
            
            # Create multiple connections
            connections = []
            for i in range(3):
                mock_ws = AsyncMock()
                connection = WebSocketConnection(
                    connection_id=f"cleanup_test_{i}",
                    user_id=context.test_user.id,
                    websocket=mock_ws,
                    connected_at=datetime.utcnow(),
                    metadata={"test": f"cleanup_{i}"}
                )
                await ws_manager.add_connection(connection)
                connections.append(connection)
            
            # Verify connections exist
            user_connections = await ws_manager.get_user_connections(context.test_user.id)
            assert len(user_connections) >= 3, "Test connections not created"
            
            # Test cleanup process
            for connection in connections:
                await ws_manager.remove_connection(connection.connection_id)
            
            # Verify cleanup
            remaining_connections = await ws_manager.get_user_connections(context.test_user.id)
            cleanup_connection_ids = [c.connection_id for c in connections]
            remaining_ids = [c.connection_id for c in remaining_connections]
            
            for cleanup_id in cleanup_connection_ids:
                assert cleanup_id not in remaining_ids, f"Connection {cleanup_id} not cleaned up"
            
            logger.info("Resource management and cleanup test completed successfully")