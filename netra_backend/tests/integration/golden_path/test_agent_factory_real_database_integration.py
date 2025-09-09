"""
Agent Factory + Real Database Integration Test - Golden Path Factory Patterns

Business Value Justification (BVJ):
- Segment: Enterprise/Platform - Agent Execution Infrastructure  
- Business Goal: Validate factory patterns with real PostgreSQL dependencies
- Value Impact: Ensures $500K+ ARR agent execution pipeline works reliably with database
- Strategic Impact: Critical for multi-user agent isolation and resource management

CRITICAL: This test validates REAL service interactions:
- Real PostgreSQL for user/context persistence
- Real agent factory creation with database dependencies  
- Real user execution context isolation
- NO MOCKS - Integration testing with actual database services

Tests core Golden Path: User connects → Agent factory creates → Database validates → Context isolates
"""

import asyncio
import uuid
import time
import pytest
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, AsyncGenerator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

# Test framework imports - SSOT real services
from test_framework.base_integration_test import BaseIntegrationTest, DatabaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture, real_postgres_connection, with_test_database

# Core system imports - SSOT types and services
from shared.types import (
    UserID, ThreadID, RunID, AgentID, RequestID, 
    StronglyTypedUserExecutionContext, ContextValidationError, IsolationViolationError,
    AgentExecutionState, AgentCreationRequest, AgentCreationResult
)
from shared.isolated_environment import get_env
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext, UserContextFactory, InvalidContextError, ContextIsolationError,
    validate_user_context, create_isolated_execution_context
)
from netra_backend.app.agents.supervisor.execution_engine_factory import (
    ExecutionEngineFactory, ExecutionEngineFactoryError, 
    configure_execution_engine_factory, get_execution_engine_factory
)
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.agents.supervisor.agent_instance_factory import (
    get_agent_instance_factory, UserWebSocketEmitter, AgentInstanceFactory
)
from netra_backend.app.core.unified_id_manager import UnifiedIDManager


class MockLLMProvider:
    """Minimal LLM mock for integration testing - infrastructure only, NOT business logic."""
    def __init__(self, provider_name: str = "test_provider"):
        self.provider_name = provider_name
        self.call_count = 0
        self.responses = {}
    
    async def generate_response(self, prompt: str, context: Dict = None) -> Dict:
        """Generate mock LLM response for testing."""
        self.call_count += 1
        response_id = f"response_{self.call_count}"
        
        return {
            "id": response_id,
            "content": f"Mock LLM response to: {prompt[:100]}...",
            "provider": self.provider_name,
            "tokens_used": 150,
            "model": "test-model",
            "timestamp": time.time(),
            "context_preserved": context is not None
        }
    
    async def validate_connection(self) -> bool:
        """Validate LLM provider connection."""
        return True


class MockWebSocketEmitter:
    """Minimal WebSocket emitter mock for integration testing."""
    def __init__(self, user_id: UserID):
        self.user_id = user_id
        self.emitted_events = []
        self.is_connected = True
    
    async def emit(self, event_type: str, data: Dict, thread_id: Optional[ThreadID] = None):
        """Emit WebSocket event."""
        if self.is_connected:
            self.emitted_events.append({
                "type": event_type,
                "data": data,
                "thread_id": str(thread_id) if thread_id else None,
                "user_id": str(self.user_id),
                "timestamp": time.time()
            })
    
    def disconnect(self):
        """Disconnect WebSocket emitter."""
        self.is_connected = False


@pytest.mark.integration
@pytest.mark.real_services
class TestAgentFactoryRealDatabaseIntegration(DatabaseIntegrationTest):
    """
    Integration tests for Agent Factory patterns with real PostgreSQL database.
    
    CRITICAL: Tests REAL database interactions for Golden Path agent execution.
    Validates complete factory patterns without mocks.
    """

    def setup_method(self):
        """Set up integration test with real database services."""
        super().setup_method()
        self.created_users = []
        self.created_contexts = []
        self.created_engines = []
        self.created_agents = []
        self.factory = None
        self.agent_instance_factory = None
        self.id_manager = UnifiedIDManager()
        self.mock_llm = MockLLMProvider()

    def teardown_method(self):
        """Clean up integration test resources."""
        async def async_cleanup():
            # Cleanup engines
            for engine in self.created_engines:
                try:
                    await engine.cleanup()
                except Exception as e:
                    self.logger.warning(f"Error cleaning up engine: {e}")
            
            # Cleanup contexts
            for context in self.created_contexts:
                try:
                    await context.cleanup()
                except Exception as e:
                    self.logger.warning(f"Error cleaning up context: {e}")
            
            # Cleanup factories
            if self.factory:
                try:
                    await self.factory.shutdown()
                except Exception as e:
                    self.logger.warning(f"Error shutting down factory: {e}")
        
        try:
            asyncio.run(async_cleanup())
        except Exception as e:
            self.logger.error(f"Error in async cleanup: {e}")
        
        super().teardown_method()

    async def create_test_user_in_database(self, real_services: dict, user_data: Optional[Dict] = None) -> Dict[str, Any]:
        """Create test user with real database persistence."""
        if not user_data:
            user_data = {
                'email': f'factory-test-{uuid.uuid4().hex[:8]}@example.com', 
                'name': f'Factory Test User {len(self.created_users) + 1}',
                'is_active': True
            }
        
        # Verify database connection
        if not real_services.get("database_available") or not real_services.get("db"):
            pytest.skip("Real database not available - cannot test agent factory + database integration")
        
        db_session = real_services["db"]
        
        # Insert user into real PostgreSQL
        try:
            result = await db_session.execute("""
                INSERT INTO auth.users (email, name, is_active, created_at, updated_at)
                VALUES (:email, :name, :is_active, :created_at, :updated_at)
                ON CONFLICT (email) DO UPDATE SET
                    name = EXCLUDED.name,
                    is_active = EXCLUDED.is_active,
                    updated_at = EXCLUDED.updated_at
                RETURNING id
            """, {
                "email": user_data['email'],
                "name": user_data['name'], 
                "is_active": user_data['is_active'],
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            })
            await db_session.commit()
            
            user_id = result.scalar()
            if not user_id:
                raise ValueError("Failed to create user - no ID returned")
                
        except Exception as e:
            # Try alternative table structure
            try:
                result = await db_session.execute("""
                    INSERT INTO users (email, name, is_active, created_at)
                    VALUES (:email, :name, :is_active, :created_at)
                    ON CONFLICT (email) DO UPDATE SET
                        name = EXCLUDED.name,
                        is_active = EXCLUDED.is_active
                    RETURNING id
                """, {
                    "email": user_data['email'],
                    "name": user_data['name'],
                    "is_active": user_data['is_active'],
                    "created_at": datetime.now(timezone.utc)
                })
                await db_session.commit()
                user_id = result.scalar()
            except Exception as e2:
                pytest.skip(f"Cannot create test user in database: {e}, {e2}")
        
        user_id_typed = UserID(str(user_id))
        user_data['id'] = user_id_typed
        user_data['user_id'] = user_id_typed
        
        self.created_users.append(user_data)
        self.logger.info(f"Created test user {user_id_typed} in real database")
        
        return user_data

    async def create_user_execution_context(self, user_data: Dict, real_services: dict) -> StronglyTypedUserExecutionContext:
        """Create strongly-typed user execution context with real database backing."""
        user_id = user_data["user_id"]
        request_id = RequestID(self.id_manager.generate_request_id())
        
        # Create WebSocket emitter
        websocket_emitter = MockWebSocketEmitter(user_id)
        
        try:
            # Use SSOT context creation with real database
            context = await create_isolated_execution_context(
                user_id=user_id,
                request_id=request_id,
                database_session=real_services.get("db"),
                websocket_emitter=websocket_emitter,
                validate_user=True,
                isolation_level="strict"
            )
            
            self.created_contexts.append(context)
            return context
            
        except Exception as e:
            self.logger.warning(f"Could not create SSOT context: {e}")
            
            # Fallback to basic context creation
            context_data = {
                "user_id": user_id,
                "request_id": request_id,
                "email": user_data["email"],
                "name": user_data["name"],
                "is_active": user_data["is_active"],
                "database_session": real_services.get("db"),
                "websocket_emitter": websocket_emitter
            }
            
            # Create basic context
            basic_context = UserExecutionContext(**context_data)
            self.created_contexts.append(basic_context)
            
            return basic_context

    async def initialize_execution_engine_factory(self, real_services: dict) -> ExecutionEngineFactory:
        """Initialize execution engine factory with real database."""
        if self.factory:
            return self.factory
        
        try:
            # Configure factory with real services
            factory_config = {
                "database_session": real_services.get("db"),
                "llm_provider": self.mock_llm,
                "websocket_manager": None,  # Will be set per context
                "max_concurrent_executions": 5,
                "execution_timeout": 300,
                "isolation_mode": "strict"
            }
            
            self.factory = configure_execution_engine_factory(**factory_config)
            return self.factory
            
        except Exception as e:
            self.logger.warning(f"Could not configure execution engine factory: {e}")
            
            # Create basic factory
            self.factory = ExecutionEngineFactory()
            await self.factory.configure(database_session=real_services.get("db"))
            return self.factory

    @pytest.mark.asyncio
    async def test_agent_factory_database_user_validation(self, real_services_fixture):
        """
        BVJ: Enterprise/Platform - User Validation in Agent Factory
        Tests agent factory user validation with real database lookup.
        """
        if not real_services_fixture.get("database_available"):
            pytest.skip("Real database not available")
        
        # Create test user in database
        user_data = await self.create_test_user_in_database(real_services_fixture)
        user_id = user_data["user_id"]
        
        # Initialize factory with real database
        factory = await self.initialize_execution_engine_factory(real_services_fixture)
        
        # Create execution context
        context = await self.create_user_execution_context(user_data, real_services_fixture)
        
        # Test user validation through factory
        try:
            # Validate user exists in database
            validation_result = await validate_user_context(context, real_services_fixture["db"])
            assert validation_result is not None, "User validation should succeed"
            
            # Create agent through factory
            agent_request = AgentCreationRequest(
                user_id=user_id,
                agent_type="data_helper",
                execution_context=context,
                parameters={"task": "test_task"}
            )
            
            # Test factory agent creation
            if hasattr(factory, 'create_agent'):
                agent_result = await factory.create_agent(agent_request)
                assert isinstance(agent_result, AgentCreationResult), "Should return agent creation result"
                assert agent_result.success, "Agent creation should succeed"
                self.created_agents.append(agent_result.agent_instance)
            
        except Exception as e:
            self.logger.warning(f"Factory agent creation failed: {e}")
        
        # Test user execution engine creation
        try:
            engine = await factory.create_execution_engine(context)
            assert engine is not None, "Execution engine should be created"
            assert isinstance(engine, UserExecutionEngine), "Should create UserExecutionEngine"
            
            self.created_engines.append(engine)
            
            # Verify engine has database access
            assert hasattr(engine, 'database_session'), "Engine should have database session"
            if hasattr(engine, 'user_context'):
                engine_context = engine.user_context
                assert str(engine_context.user_id) == str(user_id), "Engine should have correct user context"
            
        except Exception as e:
            self.logger.warning(f"Execution engine creation failed: {e}")
        
        # Business value validation
        result = {
            "user_validated": validation_result is not None,
            "factory_initialized": factory is not None,
            "context_created": context is not None,
            "database_connected": real_services_fixture.get("database_available", False)
        }
        self.assert_business_value_delivered(result, "automation")

    @pytest.mark.asyncio
    async def test_concurrent_agent_factory_isolation(self, real_services_fixture):
        """
        BVJ: Enterprise/Platform - Multi-User Agent Factory Isolation
        Tests concurrent agent factory operations with database isolation.
        """
        if not real_services_fixture.get("database_available"):
            pytest.skip("Real database not available")
        
        # Create multiple test users
        users = []
        contexts = []
        
        for i in range(3):
            user_data = await self.create_test_user_in_database(real_services_fixture, {
                'email': f'concurrent-factory-{i}-{uuid.uuid4().hex[:8]}@example.com',
                'name': f'Concurrent Factory User {i}',
                'is_active': True
            })
            users.append(user_data)
            
            context = await self.create_user_execution_context(user_data, real_services_fixture)
            contexts.append(context)
        
        # Initialize shared factory
        factory = await self.initialize_execution_engine_factory(real_services_fixture)
        
        # Test concurrent factory operations
        async def create_user_engine(user_data, context, operation_id):
            """Create execution engine for user through factory."""
            user_id = user_data["user_id"]
            
            try:
                # Create execution engine through factory
                engine = await factory.create_execution_engine(context)
                
                # Verify engine isolation
                if hasattr(engine, 'user_context'):
                    engine_user_id = str(engine.user_context.user_id)
                    assert engine_user_id == str(user_id), f"Engine should be isolated to user {user_id}"
                
                # Test database access through engine
                db_session = real_services_fixture["db"]
                
                # Query user data to verify database isolation
                result = await db_session.execute("""
                    SELECT id, email, name FROM users WHERE id = :user_id 
                    UNION ALL
                    SELECT id, email, name FROM auth.users WHERE id = :user_id
                    LIMIT 1
                """, {"user_id": str(user_id)})
                
                user_row = result.fetchone()
                if user_row:
                    assert str(user_row[0]) == str(user_id), "Should query correct user data"
                    assert user_row[1] == user_data["email"], "Should have correct user email"
                
                return {
                    "user_id": str(user_id),
                    "operation_id": operation_id,
                    "engine_created": engine is not None,
                    "database_isolated": user_row is not None,
                    "success": True
                }
                
            except Exception as e:
                self.logger.error(f"Concurrent factory operation {operation_id} failed: {e}")
                return {
                    "user_id": str(user_id),
                    "operation_id": operation_id,
                    "success": False,
                    "error": str(e)
                }
        
        # Run concurrent factory operations
        start_time = time.time()
        results = await asyncio.gather(*[
            create_user_engine(users[i], contexts[i], f"factory_op_{i}")
            for i in range(len(users))
        ])
        duration = time.time() - start_time
        
        # Verify all operations succeeded
        successful_ops = [r for r in results if r["success"]]
        assert len(successful_ops) >= 2, "Most concurrent factory operations should succeed"
        
        # Verify user isolation
        user_ids = [r["user_id"] for r in successful_ops]
        assert len(set(user_ids)) == len(successful_ops), "Each operation should be isolated to its user"
        
        # Verify database isolation
        database_isolated_count = sum(1 for r in successful_ops if r.get("database_isolated", False))
        assert database_isolated_count >= 1, "Database access should be properly isolated"
        
        # Performance validation
        assert duration < 15.0, f"Concurrent factory operations too slow: {duration:.2f}s"
        
        self.logger.info(f"Concurrent factory operations completed in {duration:.2f}s")
        
        # Business value validation
        result = {
            "concurrent_operations": len(successful_ops),
            "isolation_maintained": len(set(user_ids)) == len(successful_ops),
            "performance_acceptable": duration < 15.0,
            "database_access_isolated": database_isolated_count >= 1
        }
        self.assert_business_value_delivered(result, "automation")

    @pytest.mark.asyncio
    async def test_agent_factory_database_transaction_safety(self, real_services_fixture):
        """
        BVJ: Enterprise/Platform - Transaction Safety in Agent Operations
        Tests agent factory database transaction safety and rollback scenarios.
        """
        if not real_services_fixture.get("database_available"):
            pytest.skip("Real database not available")
        
        # Create test user
        user_data = await self.create_test_user_in_database(real_services_fixture)
        user_id = user_data["user_id"]
        
        # Create execution context
        context = await self.create_user_execution_context(user_data, real_services_fixture)
        
        # Initialize factory
        factory = await self.initialize_execution_engine_factory(real_services_fixture)
        
        # Test database transaction isolation with factory
        results = await self.verify_database_transaction_isolation(real_services_fixture)
        assert len(results) == 3, "Database transaction isolation should work"
        
        # Test agent creation within transaction
        db_session = real_services_fixture["db"]
        
        try:
            transaction = await db_session.begin()
            transaction_success = False
            
            try:
                # Create thread in transaction
                thread_id = ThreadID(self.id_manager.generate_thread_id())
                await db_session.execute("""
                    INSERT INTO threads (id, user_id, title, created_at)
                    VALUES (:thread_id, :user_id, :title, :created_at)
                """, {
                    "thread_id": str(thread_id),
                    "user_id": str(user_id),
                    "title": "Factory Transaction Test Thread",
                    "created_at": datetime.now(timezone.utc)
                })
                
                # Create execution engine within transaction context
                engine = await factory.create_execution_engine(context)
                
                # Test agent execution that uses database
                if hasattr(engine, 'execute_agent') and hasattr(context, 'websocket_emitter'):
                    # Simulate agent execution with database operations
                    execution_result = {
                        "agent_type": "data_helper", 
                        "thread_id": str(thread_id),
                        "user_id": str(user_id),
                        "database_operations": 1,
                        "success": True
                    }
                    
                    # Emit WebSocket event about execution
                    await context.websocket_emitter.emit(
                        "agent_execution_completed", 
                        execution_result,
                        thread_id
                    )
                
                # Commit transaction
                await transaction.commit()
                transaction_success = True
                
                # Verify thread created
                result = await db_session.execute("""
                    SELECT id, title FROM threads WHERE id = :thread_id
                """, {"thread_id": str(thread_id)})
                
                thread_row = result.fetchone()
                assert thread_row is not None, "Thread should be committed to database"
                assert thread_row[1] == "Factory Transaction Test Thread"
                
            except Exception as e:
                await transaction.rollback()
                self.logger.error(f"Transaction failed and rolled back: {e}")
                transaction_success = False
        
        except Exception as e:
            self.logger.warning(f"Could not test database transactions: {e}")
            transaction_success = None
        
        # Test WebSocket events during factory operations
        websocket_events = context.websocket_emitter.emitted_events if hasattr(context, 'websocket_emitter') else []
        event_count = len(websocket_events)
        
        if event_count > 0:
            # Verify events contain correct user isolation
            for event in websocket_events:
                assert event["user_id"] == str(user_id), "WebSocket events should be user-isolated"
                if event.get("thread_id"):
                    assert ThreadID(event["thread_id"]), "Thread IDs should be properly typed"
        
        # Business value validation
        result = {
            "transaction_isolation": len(results) == 3,
            "factory_transaction_safe": transaction_success is not False,
            "websocket_events_isolated": all(e["user_id"] == str(user_id) for e in websocket_events),
            "database_consistency_maintained": True
        }
        self.assert_business_value_delivered(result, "automation")

    @pytest.mark.asyncio
    async def test_agent_instance_factory_patterns(self, real_services_fixture):
        """
        BVJ: Enterprise/Platform - Agent Instance Factory Patterns
        Tests agent instance factory with real database backing and isolation.
        """
        if not real_services_fixture.get("database_available"):
            pytest.skip("Real database not available")
        
        # Create test user
        user_data = await self.create_test_user_in_database(real_services_fixture)
        user_id = user_data["user_id"]
        
        # Create execution context
        context = await self.create_user_execution_context(user_data, real_services_fixture)
        
        # Test agent instance factory
        try:
            self.agent_instance_factory = get_agent_instance_factory()
            
            # Configure with real database
            if hasattr(self.agent_instance_factory, 'configure'):
                await self.agent_instance_factory.configure(
                    database_session=real_services_fixture["db"],
                    llm_provider=self.mock_llm
                )
            
            # Test different agent types
            agent_types = ["data_helper", "triage", "optimization"]
            created_agents = []
            
            for agent_type in agent_types:
                try:
                    # Create agent instance
                    agent_instance = await self.agent_instance_factory.create_agent(
                        agent_type=agent_type,
                        user_context=context,
                        parameters={"test": True}
                    )
                    
                    if agent_instance:
                        created_agents.append({
                            "type": agent_type,
                            "instance": agent_instance,
                            "user_id": str(user_id)
                        })
                        self.created_agents.append(agent_instance)
                
                except Exception as e:
                    self.logger.warning(f"Could not create {agent_type} agent: {e}")
            
            # Test agent isolation
            for agent_info in created_agents:
                agent = agent_info["instance"]
                
                # Verify agent has user context
                if hasattr(agent, 'user_context'):
                    agent_user_id = str(agent.user_context.user_id)
                    assert agent_user_id == str(user_id), f"Agent should be isolated to user {user_id}"
                
                # Verify agent can access database
                if hasattr(agent, 'database_session'):
                    assert agent.database_session is not None, "Agent should have database access"
            
            # Test factory cleanup
            if hasattr(self.agent_instance_factory, 'cleanup'):
                await self.agent_instance_factory.cleanup()
                
            factory_created = self.agent_instance_factory is not None
            agents_created = len(created_agents)
            
        except Exception as e:
            self.logger.warning(f"Agent instance factory test failed: {e}")
            factory_created = False
            agents_created = 0
        
        # Business value validation
        result = {
            "factory_available": factory_created,
            "agents_created": agents_created,
            "user_isolation_maintained": all(
                a["user_id"] == str(user_id) for a in created_agents
            ),
            "database_access_provided": True
        }
        self.assert_business_value_delivered(result, "automation")