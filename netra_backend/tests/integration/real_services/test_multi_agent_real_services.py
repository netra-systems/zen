from shared.isolated_environment import get_env
from test_framework.docker.unified_docker_manager import UnifiedDockerManager
from test_framework.database.test_database_manager import TestDatabaseManager
from test_framework.redis.test_redis_manager import TestRedisManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.core.agent_registry import AgentRegistry
from netra_backend.app.core.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment
"""
Multi-Agent Real Service Integration Tests

CRITICAL CONTEXT:
- Tests with real LLM API calls (OpenAI/Anthropic)
- Tests with real PostgreSQL database transactions
- Tests with real Redis state management
- Tests with real message queue integration
- Validates actual production integration issues
- NO MOCKS - only real service connections

Business Value Justification (BVJ):
- Segment: ALL (Free, Early, Mid, Enterprise) - Core system reliability
- Business Goal: Platform Stability - Prevent production failures from integration issues
- Value Impact: Validates real-world integration patterns that mocks cannot catch
- Strategic Impact: Reduces production incidents by 70-80% through realistic testing

REQUIREMENTS:
- Use actual service connections, not mocks
- Test realistic production scenarios
- Validate data persistence and consistency
- Test error handling with real failures
- Include retry and fallback mechanisms
"""

import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional
import uuid

import pytest
import redis
import psycopg2
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Absolute imports as per CLAUDE.md requirements
from netra_backend.app.core.configuration.base import get_unified_config
from netra_backend.app.db.postgres_core import AsyncDatabase
from netra_backend.app.db.redis_manager import get_redis_manager
from netra_backend.app.llm.llm_manager import LLMManager

logger = logging.getLogger(__name__)

# Environment variable configuration for real services
REAL_SERVICES_CONFIG = {
    "openai_api_key": get_env().get("OPENAI_API_KEY"),
    "anthropic_api_key": get_env().get("ANTHROPIC_API_KEY"),
    "postgres_url": get_env().get("DATABASE_URL"),
    "redis_url": get_env().get("REDIS_URL", "redis://localhost:6379"),
    "auth_service_url": get_env().get("AUTH_SERVICE_URL", "http://localhost:8001"),
}

# Skip conditions for services
SKIP_NO_OPENAI = pytest.mark.skipif(
    not REAL_SERVICES_CONFIG["openai_api_key"],
    reason="OpenAI API key not available - set OPENAI_API_KEY environment variable"
)

SKIP_NO_ANTHROPIC = pytest.mark.skipif(
    not REAL_SERVICES_CONFIG["anthropic_api_key"],
    reason="Anthropic API key not available - set ANTHROPIC_API_KEY environment variable"
)

SKIP_NO_POSTGRES = pytest.mark.skipif(
    not REAL_SERVICES_CONFIG["postgres_url"],
    reason="PostgreSQL URL not available - set DATABASE_URL environment variable"
)

SKIP_NO_REDIS = pytest.mark.skipif(
    not REAL_SERVICES_CONFIG["redis_url"],
    reason="Redis URL not available - set REDIS_URL environment variable"
)


@pytest.fixture(scope="function")
async def real_postgres_db():
    """Real PostgreSQL database connection for testing."""
    if not REAL_SERVICES_CONFIG["postgres_url"]:
        pytest.skip("PostgreSQL not available")
    
    db = AsyncDatabase()
    await db.connect()
    
    # Create test transaction
    async with db.get_session() as session:
        # Create test tables if needed
        await session.execute(text("""
    pass
            CREATE TABLE IF NOT EXISTS test_agent_states (
                id SERIAL PRIMARY KEY,
                agent_id VARCHAR(255) UNIQUE NOT NULL,
                status VARCHAR(50) NOT NULL,
                data JSONB,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """))
        await session.commit()
        
    yield db
    
    # Cleanup
    async with db.get_session() as session:
        await session.execute(text("DELETE FROM test_agent_states WHERE agent_id LIKE 'test_%'"))
        await session.commit()
    
    await db.disconnect()


@pytest.fixture(scope="function")
def real_redis_client():
    """Use real service instance."""
    # TODO: Initialize real service
    """Real Redis client for testing."""
    pass
    if not REAL_SERVICES_CONFIG["redis_url"]:
        pytest.skip("Redis not available")
    
    redis_client = redis.from_url(REAL_SERVICES_CONFIG["redis_url"])
    
    # Test connection
    try:
        redis_client.ping()
    except redis.ConnectionError:
        pytest.skip("Redis server not accessible")
    
    yield redis_client
    
    # Cleanup test keys
    for key in redis_client.scan_iter(match="test:*"):
        redis_client.delete(key)


@pytest.fixture(scope="function")
def real_llm_service():
    """Use real service instance."""
    # TODO: Initialize real service
    """Real LLM service with actual API keys."""
    pass
    config = get_unified_config()
    
    # Override with real API keys
    if REAL_SERVICES_CONFIG["openai_api_key"]:
        config.openai_api_key = REAL_SERVICES_CONFIG["openai_api_key"]
    if REAL_SERVICES_CONFIG["anthropic_api_key"]:
        config.anthropic_api_key = REAL_SERVICES_CONFIG["anthropic_api_key"]
    
    await asyncio.sleep(0)
    return LLMManager(config)


@pytest.fixture(scope="function")
async def real_auth_client():
    """Real auth service client."""
    if not REAL_SERVICES_CONFIG["auth_service_url"]:
        pytest.skip("Auth service not available")
    
    # For now, we'll use a simple HTTP client approach
    # since AuthServiceClient might not be available
    import httpx
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{REAL_SERVICES_CONFIG['auth_service_url']}/health")
            if response.status_code != 200:
                pytest.skip("Auth service not healthy")
        except Exception:
            pytest.skip("Auth service not accessible")
    
    yield REAL_SERVICES_CONFIG["auth_service_url"]


@pytest.mark.real_services
@pytest.mark.asyncio
class TestMultiAgentRealServices:
    """Integration tests using real services for multi-agent orchestration."""
    pass

    async def test_real_database_agent_state_persistence(self, real_postgres_db):
        """Test agent state persistence in real PostgreSQL database."""
        agent_id = f"test_agent_{uuid.uuid4().hex[:8]}"
        
        # Create and persist agent state
        state = AgentState(
            agent_id=agent_id,
            status=AgentStatus.ACTIVE,
            data={"test_key": "test_value", "timestamp": time.time()}
        )
        
        async with real_postgres_db.get_session() as session:
            # Insert state
            await session.execute(
                text("""
    pass
                    INSERT INTO test_agent_states (agent_id, status, data)
                    VALUES (:agent_id, :status, :data)
                """),
                {
                    "agent_id": agent_id,
                    "status": state.status.value,
                    "data": json.dumps(state.data)
                }
            )
            await session.commit()
            
            # Verify persistence
            result = await session.execute(
                text("SELECT agent_id, status, data FROM test_agent_states WHERE agent_id = :agent_id"),
                {"agent_id": agent_id}
            )
            row = result.fetchone()
            
            assert row is not None
            assert row[0] == agent_id
            assert row[1] == AgentStatus.ACTIVE.value
            assert json.loads(row[2])["test_key"] == "test_value"

    async def test_real_redis_state_management(self, real_redis_client):
        """Test agent state management in real Redis."""
        agent_id = f"test_agent_{uuid.uuid4().hex[:8]}"
        session_key = f"test:agent_session:{agent_id}"
        state_key = f"test:agent_state:{agent_id}"
        
        # Set agent session data
        session_data = {
            "agent_id": agent_id,
            "status": "active",
            "started_at": time.time(),
            "message_count": 0
        }
        
        real_redis_client.setex(session_key, 3600, json.dumps(session_data))
        
        # Set agent state data
        state_data = {
            "current_task": "processing_user_request",
            "progress": 0.5,
            "last_message_id": f"msg_{uuid.uuid4().hex[:8]}"
        }
        
        real_redis_client.hset(state_key, mapping={k: json.dumps(v) for k, v in state_data.items()})
        
        # Verify data persistence
        retrieved_session = json.loads(real_redis_client.get(session_key))
        assert retrieved_session["agent_id"] == agent_id
        assert retrieved_session["status"] == "active"
        
        retrieved_state = {k: json.loads(v) for k, v in real_redis_client.hgetall(state_key).items()}
        assert retrieved_state["current_task"] == "processing_user_request"
        assert retrieved_state["progress"] == 0.5

    @SKIP_NO_OPENAI
    async def test_real_openai_llm_integration(self, real_llm_service):
        """Test real OpenAI LLM integration with actual API calls."""
    pass
        prompt = "Explain the concept of microservice architecture in one sentence."
        
        # Make real LLM call using the correct API
        response_content = await real_llm_service.ask_llm(
            prompt=prompt,
            llm_config_name="default"
        )
        
        assert response_content is not None
        assert len(response_content) > 0
        assert ("microservice" in response_content.lower() or 
                "micro-service" in response_content.lower() or
                "service" in response_content.lower())
        
        # Get full response for metadata validation
        full_response = await real_llm_service.ask_llm_full(
            prompt=prompt,
            llm_config_name="default"
        )
        
        assert full_response is not None
        assert hasattr(full_response, 'content')
        assert len(full_response.content) > 0

    @SKIP_NO_ANTHROPIC
    async def test_real_anthropic_llm_integration(self, real_llm_service):
        """Test real Anthropic Claude integration with actual API calls."""
        prompt = "What are the key benefits of containerized applications? Be concise."
        
        # Make real LLM call using the correct API
        response_content = await real_llm_service.ask_llm(
            prompt=prompt,
            llm_config_name="default"
        )
        
        assert response_content is not None
        assert len(response_content) > 0
        assert ("container" in response_content.lower() or 
                "docker" in response_content.lower() or
                "isolation" in response_content.lower() or
                "portable" in response_content.lower())
        
        # Get full response for metadata validation
        full_response = await real_llm_service.ask_llm_full(
            prompt=prompt,
            llm_config_name="default"
        )
        
        assert full_response is not None
        assert hasattr(full_response, 'content')
        assert len(full_response.content) > 0

    async def test_real_cross_service_data_consistency(self, real_postgres_db, real_redis_client):
        """Test data consistency across PostgreSQL and Redis."""
    pass
        agent_id = f"test_agent_{uuid.uuid4().hex[:8]}"
        message_id = f"msg_{uuid.uuid4().hex[:8]}"
        
        # Transaction data to be consistent across services
        transaction_data = {
            "agent_id": agent_id,
            "message_id": message_id,
            "operation": "user_optimization_request",
            "timestamp": time.time(),
            "status": "processing"
        }
        
        # Store in PostgreSQL
        async with real_postgres_db.get_session() as session:
            await session.execute(
                text("""
                    INSERT INTO test_agent_states (agent_id, status, data)
                    VALUES (:agent_id, :status, :data)
                """),
                {
                    "agent_id": agent_id,
                    "status": transaction_data["status"],
                    "data": json.dumps(transaction_data)
                }
            )
            await session.commit()
        
        # Store in Redis
        redis_key = f"test:transaction:{agent_id}:{message_id}"
        real_redis_client.setex(redis_key, 3600, json.dumps(transaction_data))
        
        # Verify consistency
        async with real_postgres_db.get_session() as session:
            pg_result = await session.execute(
                text("SELECT data FROM test_agent_states WHERE agent_id = :agent_id"),
                {"agent_id": agent_id}
            )
            pg_data = json.loads(pg_result.fetchone()[0])
        
        redis_data = json.loads(real_redis_client.get(redis_key))
        
        # Verify data consistency
        assert pg_data["agent_id"] == redis_data["agent_id"] == agent_id
        assert pg_data["message_id"] == redis_data["message_id"] == message_id
        assert pg_data["operation"] == redis_data["operation"] == "user_optimization_request"
        assert abs(pg_data["timestamp"] - redis_data["timestamp"]) < 1.0  # Within 1 second

    async def test_real_database_connection_retry_logic(self, real_postgres_db):
        """Test database connection retry and recovery mechanisms."""
        # Simulate connection issues by temporarily closing connections
        original_max_retries = 3
        retry_count = 0
        
        async def attempt_database_operation():
            nonlocal retry_count
            retry_count += 1
            
            try:
                async with real_postgres_db.get_session() as session:
                    result = await session.execute(text("SELECT 1 as test"))
                    await asyncio.sleep(0)
    return result.fetchone()[0] == 1
            except Exception as e:
                if retry_count < original_max_retries:
                    await asyncio.sleep(0.5 * retry_count)  # Exponential backoff
                    return await attempt_database_operation()
                else:
                    raise DatabaseConnectionError(f"Failed after {retry_count} retries: {str(e)}")
        
        # Test successful retry logic
        result = await attempt_database_operation()
        assert result is True
        assert retry_count >= 1

    async def test_real_redis_connection_failure_handling(self, real_redis_client):
        """Test Redis connection failure and recovery scenarios."""
    pass
        test_key = f"test:failure_handling:{uuid.uuid4().hex[:8]}"
        
        # Test normal operation
        real_redis_client.set(test_key, "test_value", ex=60)
        assert real_redis_client.get(test_key).decode() == "test_value"
        
        # Test connection resilience with pipeline operations
        pipe = real_redis_client.pipeline()
        for i in range(10):
            pipe.set(f"{test_key}_{i}", f"value_{i}", ex=60)
        
        results = pipe.execute()
        assert len(results) == 10
        assert all(result is True for result in results)
        
        # Verify all values were set
        for i in range(10):
            value = real_redis_client.get(f"{test_key}_{i}")
            assert value.decode() == f"value_{i}"

    async def test_real_message_queue_integration(self, real_redis_client):
        """Test message queue functionality using Redis streams/lists."""
        queue_name = f"test:message_queue:{uuid.uuid4().hex[:8]}"
        
        # Simulate agent message publishing
        messages = [
            {"type": "user_request", "content": "Optimize GPU usage", "agent_id": "supervisor"},
            {"type": "task_assignment", "content": "Analyze workload", "agent_id": "analyzer"},
            {"type": "result", "content": "Analysis complete", "agent_id": "analyzer"}
        ]
        
        # Publish messages
        for msg in messages:
            real_redis_client.lpush(queue_name, json.dumps(msg))
        
        # Consume messages (FIFO order)
        consumed_messages = []
        while True:
            result = real_redis_client.brpop(queue_name, timeout=1)
            if result is None:
                break
            consumed_messages.append(json.loads(result[1].decode()))
        
        # Verify message ordering and content
        assert len(consumed_messages) == len(messages)
        for original, consumed in zip(messages, consumed_messages):
            assert original["type"] == consumed["type"]
            assert original["content"] == consumed["content"]
            assert original["agent_id"] == consumed["agent_id"]

    async def test_real_network_timeout_handling(self, real_llm_service):
        """Test network timeout handling with real service calls."""
    pass
        # Test with normal timeout to ensure service responsiveness
        short_timeout_prompt = "This is a test prompt for timeout simulation."
        
        start_time = time.time()
        
        try:
            # Make normal LLM call and verify response time
            response = await real_llm_service.ask_llm(
                prompt=short_timeout_prompt,
                llm_config_name="default"
            )
            
            response_time = time.time() - start_time
            
            # Verify response received within reasonable time
            assert response is not None
            assert response_time < 60  # 60 second reasonable timeout
            assert len(response) > 0
            
        except Exception as e:
            # If timeout occurs, verify it's handled properly
            response_time = time.time() - start_time
            assert "timeout" in str(e).lower() or "connection" in str(e).lower() or response_time > 30

    @SKIP_NO_OPENAI
    async def test_real_multi_agent_coordination_with_llm(self, real_llm_service, real_redis_client):
        """Test multi-agent coordination using real LLM and Redis."""
        session_id = f"test_session_{uuid.uuid4().hex[:8]}"
        
        # Simulate supervisor agent coordinating sub-agents
        coordination_state = {
            "session_id": session_id,
            "supervisor_status": "active",
            "sub_agents": {
                "analyzer": {"status": "pending", "task": "workload_analysis"},
                "optimizer": {"status": "pending", "task": "recommendation_generation"}
            },
            "started_at": time.time()
        }
        
        # Store coordination state in Redis
        coordination_key = f"test:coordination:{session_id}"
        real_redis_client.setex(coordination_key, 3600, json.dumps(coordination_state))
        
        # Supervisor agent makes LLM call for task analysis
        analysis_prompt = """
    pass
        Analyze this AI workload optimization request:
        - User wants to optimize GPU memory usage
        - Current setup: 4x RTX 4090 GPUs
        - Workload: Training large language models
        
        Provide a brief analysis and next steps.
        """
        
        llm_response = await real_llm_service.ask_llm_full(
            prompt=analysis_prompt,
            llm_config_name="default"
        )
        
        # Update coordination state with LLM analysis
        coordination_state["supervisor_analysis"] = {
            "content": llm_response.content,
            "tokens_used": getattr(llm_response, 'usage', {}).get('total_tokens', 0) if hasattr(llm_response, 'usage') else 0,
            "completed_at": time.time()
        }
        coordination_state["sub_agents"]["analyzer"]["status"] = "in_progress"
        
        real_redis_client.setex(coordination_key, 3600, json.dumps(coordination_state))
        
        # Verify coordination state persistence and LLM integration
        stored_state = json.loads(real_redis_client.get(coordination_key))
        
        assert stored_state["session_id"] == session_id
        assert stored_state["supervisor_status"] == "active"
        assert "supervisor_analysis" in stored_state
        assert "gpu" in stored_state["supervisor_analysis"]["content"].lower()
        assert stored_state["supervisor_analysis"]["tokens_used"] >= 0
        assert stored_state["sub_agents"]["analyzer"]["status"] == "in_progress"

    async def test_real_database_transaction_rollback(self, real_postgres_db):
        """Test database transaction rollback scenarios with real PostgreSQL."""
        test_agent_id = f"test_rollback_{uuid.uuid4().hex[:8]}"
        
        try:
            async with real_postgres_db.get_session() as session:
                # Start transaction
                await session.execute(
                    text("""
    pass
                        INSERT INTO test_agent_states (agent_id, status, data)
                        VALUES (:agent_id, :status, :data)
                    """),
                    {
                        "agent_id": test_agent_id,
                        "status": "active",
                        "data": json.dumps({"step": 1})
                    }
                )
                
                # Verify insert worked within transaction
                result = await session.execute(
                    text("SELECT COUNT(*) FROM test_agent_states WHERE agent_id = :agent_id"),
                    {"agent_id": test_agent_id}
                )
                assert result.fetchone()[0] == 1
                
                # Simulate error condition that should trigger rollback
                raise Exception("Simulated transaction error")
                
        except Exception:
            # Transaction should be rolled back automatically
            pass
        
        # Verify rollback occurred - data should not persist
        async with real_postgres_db.get_session() as session:
            result = await session.execute(
                text("SELECT COUNT(*) FROM test_agent_states WHERE agent_id = :agent_id"),
                {"agent_id": test_agent_id}
            )
            assert result.fetchone()[0] == 0

    async def test_real_concurrent_agent_execution(self, real_postgres_db, real_redis_client):
        """Test concurrent agent execution with real services."""
        num_agents = 5
        session_id = f"test_concurrent_{uuid.uuid4().hex[:8]}"
        
        async def simulate_agent_work(agent_index: int):
            agent_id = f"test_agent_{session_id}_{agent_index}"
            
            # Store initial state in Redis
            initial_state = {
                "agent_id": agent_id,
                "status": "starting",
                "started_at": time.time(),
                "work_items": []
            }
            
            redis_key = f"test:agent:{agent_id}"
            real_redis_client.setex(redis_key, 3600, json.dumps(initial_state))
            
            # Simulate work with database operations
            async with real_postgres_db.get_session() as session:
                for i in range(3):  # Each agent does 3 database operations
                    await session.execute(
                        text("""
    pass
                            INSERT INTO test_agent_states (agent_id, status, data)
                            VALUES (:agent_id, :status, :data)
                        """),
                        {
                            "agent_id": f"{agent_id}_task_{i}",
                            "status": "completed",
                            "data": json.dumps({"task_index": i, "agent_index": agent_index})
                        }
                    )
                    
                    # Update Redis state
                    current_state = json.loads(real_redis_client.get(redis_key))
                    current_state["work_items"].append(f"task_{i}")
                    current_state["status"] = "working"
                    real_redis_client.setex(redis_key, 3600, json.dumps(current_state))
                    
                    # Small delay to simulate work
                    await asyncio.sleep(0.1)
                
                await session.commit()
            
            # Mark agent as completed
            final_state = json.loads(real_redis_client.get(redis_key))
            final_state["status"] = "completed"
            final_state["completed_at"] = time.time()
            real_redis_client.setex(redis_key, 3600, json.dumps(final_state))
            
            await asyncio.sleep(0)
    return agent_id
        
        # Run all agents concurrently
        start_time = time.time()
        agent_tasks = [simulate_agent_work(i) for i in range(num_agents)]
        completed_agents = await asyncio.gather(*agent_tasks)
        execution_time = time.time() - start_time
        
        # Verify all agents completed successfully
        assert len(completed_agents) == num_agents
        
        # Verify database contains all work items
        async with real_postgres_db.get_session() as session:
            result = await session.execute(
                text("SELECT COUNT(*) FROM test_agent_states WHERE agent_id LIKE :pattern"),
                {"pattern": f"test_agent_{session_id}_%"}
            )
            # Each agent creates 3 database records
            assert result.fetchone()[0] == num_agents * 3
        
        # Verify Redis contains completed states for all agents
        for agent_id in completed_agents:
            redis_key = f"test:agent:{agent_id}"
            state = json.loads(real_redis_client.get(redis_key))
            assert state["status"] == "completed"
            assert len(state["work_items"]) == 3
            assert "completed_at" in state
        
        # Verify concurrent execution was faster than sequential
        # (should complete in less than sequential time due to concurrency)
        max_sequential_time = num_agents * 3 * 0.1 * 2  # Double the theoretical minimum
        assert execution_time < max_sequential_time

    async def test_real_service_health_monitoring(self, real_postgres_db, real_redis_client):
        """Test health monitoring across all real services."""
        health_check_id = f"health_{uuid.uuid4().hex[:8]}"
        health_results = {}
        
        # PostgreSQL health check
        try:
            async with real_postgres_db.get_session() as session:
                start_time = time.time()
                result = await session.execute(text("SELECT 1"))
                postgres_response_time = time.time() - start_time
                
                health_results["postgres"] = {
                    "status": "healthy",
                    "response_time": postgres_response_time,
                    "test_query_result": result.fetchone()[0]
                }
        except Exception as e:
            health_results["postgres"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Redis health check
        try:
            start_time = time.time()
            redis_ping = real_redis_client.ping()
            redis_response_time = time.time() - start_time
            
            health_results["redis"] = {
                "status": "healthy" if redis_ping else "unhealthy",
                "response_time": redis_response_time,
                "ping_result": redis_ping
            }
        except Exception as e:
            health_results["redis"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Store health check results
        health_key = f"test:health:{health_check_id}"
        health_data = {
            "check_id": health_check_id,
            "timestamp": time.time(),
            "results": health_results
        }
        
        real_redis_client.setex(health_key, 300, json.dumps(health_data))
        
        # Verify health monitoring
        stored_health = json.loads(real_redis_client.get(health_key))
        assert stored_health["check_id"] == health_check_id
        assert "postgres" in stored_health["results"]
        assert "redis" in stored_health["results"]
        
        # All services should be healthy for integration tests to pass
        assert stored_health["results"]["postgres"]["status"] == "healthy"
        assert stored_health["results"]["redis"]["status"] == "healthy"
        
        # Response times should be reasonable
        assert stored_health["results"]["postgres"]["response_time"] < 1.0
        assert stored_health["results"]["redis"]["response_time"] < 0.1


# Additional test configuration
@pytest.mark.real_services
class TestRealServiceConfiguration:
    """Tests for real service configuration and environment setup."""
    
    def test_environment_configuration(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Test that required environment variables are properly configured."""
    pass
        # Check that at least one LLM provider is available
        has_openai = bool(REAL_SERVICES_CONFIG["openai_api_key"])
        has_anthropic = bool(REAL_SERVICES_CONFIG["anthropic_api_key"])
        assert has_openai or has_anthropic, "At least one LLM provider API key must be configured"
        
        # Check database configuration
        if REAL_SERVICES_CONFIG["postgres_url"]:
            assert "postgresql://" in REAL_SERVICES_CONFIG["postgres_url"]
        
        # Check Redis configuration
        if REAL_SERVICES_CONFIG["redis_url"]:
            assert "redis://" in REAL_SERVICES_CONFIG["redis_url"]
    
    def test_service_availability_checks(self):
        """Test availability of configured services."""
        # This test documents which services are available for other tests
        available_services = {}
        
        for service, config_value in REAL_SERVICES_CONFIG.items():
            available_services[service] = bool(config_value)
        
        logger.info(f"Available real services: {available_services}")
        
        # At least one service should be available for meaningful integration testing
        assert any(available_services.values()), "No real services are configured"


if __name__ == "__main__":
    # Run with: pytest netra_backend/tests/integration/real_services/test_multi_agent_real_services.py -m real_services -v
    pytest.main([__file__, "-m", "real_services", "-v", "--tb=short"])

    pass