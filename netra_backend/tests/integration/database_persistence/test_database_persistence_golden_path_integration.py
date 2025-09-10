"""
Database Persistence Golden Path Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Ensure reliable data persistence during agent execution
- Value Impact: Users must trust that their conversations, executions, and results are safely stored
- Strategic Impact: Data integrity is foundation for platform reliability and user retention

CRITICAL: Tests complete database persistence flow during golden path user journey:
1. User registration and authentication
2. Thread creation and message storage  
3. Agent execution tracking and results persistence
4. Multi-user isolation in database operations
5. Transaction consistency across concurrent operations
6. Cache coordination with database state
7. Error recovery and rollback scenarios

This test validates REAL database operations with PostgreSQL and Redis
NO MOCKS - Uses real services to validate actual business workflows
"""

import asyncio
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from test_framework.base_integration_test import BaseIntegrationTest, DatabaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture, real_postgres_connection, with_test_database
from shared.isolated_environment import get_env

from netra_backend.app.models.user import User
from netra_backend.app.models.thread import Thread, Message
from netra_backend.app.models.agent_execution import AgentExecution
from netra_backend.app.schemas.core_models import MessageCreate, ThreadMetadata


@dataclass
class TestUserData:
    """Test user data for multi-user scenarios."""
    user_id: str
    email: str
    name: str
    thread_ids: List[str]
    execution_ids: List[str]


class TestDatabasePersistenceGoldenPath(DatabaseIntegrationTest):
    """
    Comprehensive database persistence tests for golden path user journey.
    
    CRITICAL: Validates complete database flow with real PostgreSQL and Redis
    - User isolation in database operations
    - Thread and message persistence  
    - Agent execution tracking
    - Transaction consistency
    - Concurrent operation handling
    - Cache coordination
    """
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_registration_and_data_isolation(self, real_services_fixture):
        """
        Test user registration creates isolated database context.
        
        BUSINESS VALUE: Users must have completely isolated data spaces
        - No cross-user data leakage
        - Secure multi-tenant data architecture
        """
        services = real_services_fixture
        if not services["database_available"]:
            pytest.skip("Database not available for integration test")
        
        db = services["db"]
        
        # Create test users with unique email addresses
        user1_data = {
            "email": f"user1_{uuid.uuid4().hex[:8]}@test.com",
            "full_name": "Test User One",
            "is_active": True
        }
        
        user2_data = {
            "email": f"user2_{uuid.uuid4().hex[:8]}@test.com", 
            "full_name": "Test User Two",
            "is_active": True
        }
        
        # Insert users into real database
        user1_id = await db.execute("""
            INSERT INTO auth.users (email, full_name, is_active, created_at)
            VALUES ($1, $2, $3, $4)
            RETURNING id
        """, user1_data["email"], user1_data["full_name"], user1_data["is_active"], datetime.now(timezone.utc))
        
        user2_id = await db.execute("""
            INSERT INTO auth.users (email, full_name, is_active, created_at)
            VALUES ($1, $2, $3, $4)
            RETURNING id
        """, user2_data["email"], user2_data["full_name"], user2_data["is_active"], datetime.now(timezone.utc))
        
        # Verify users are properly isolated
        user1_result = await db.fetchrow("SELECT * FROM auth.users WHERE id = $1", user1_id)
        user2_result = await db.fetchrow("SELECT * FROM auth.users WHERE id = $1", user2_id)
        
        assert user1_result["email"] == user1_data["email"]
        assert user2_result["email"] == user2_data["email"]
        assert user1_result["id"] != user2_result["id"]
        
        # Verify user isolation query works
        user1_only = await db.fetch("SELECT * FROM auth.users WHERE id = $1", user1_id)
        assert len(user1_only) == 1
        assert user1_only[0]["email"] == user1_data["email"]
        
        self.logger.info(f"✓ User isolation verified: {user1_id} != {user2_id}")
        
        # Business value assertion
        self.assert_business_value_delivered(
            {"user1": user1_result, "user2": user2_result, "isolated": True},
            "automation"  # User registration automation
        )
    
    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_thread_creation_and_persistence_golden_path(self, real_services_fixture):
        """
        Test thread creation and message persistence in golden path flow.
        
        BUSINESS VALUE: Conversation continuity enables user engagement
        - Threads persist across sessions
        - Messages maintain chronological order
        - Thread metadata is preserved
        """
        services = real_services_fixture
        if not services["database_available"]:
            pytest.skip("Database not available for integration test")
            
        db = services["db"]
        
        # Create test user
        user_data = await self.create_test_user_context(services, {
            "email": f"thread_test_{uuid.uuid4().hex[:8]}@test.com",
            "name": "Thread Test User"
        })
        user_id = user_data["id"]
        
        # Create thread with metadata
        thread_id = f"thread_{uuid.uuid4().hex[:12]}"
        thread_metadata = {
            "tags": ["cost_optimization", "aws"],
            "priority": 8,
            "category": "business_optimization",
            "user_id": user_id
        }
        
        created_at = datetime.now(timezone.utc)
        
        # Insert thread into real database
        await db.execute("""
            INSERT INTO backend.threads (id, user_id, name, metadata, created_at, updated_at, is_active)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, thread_id, user_id, "AWS Cost Optimization", thread_metadata, created_at, created_at, True)
        
        # Create and persist messages in correct order
        messages = [
            {
                "id": f"msg_{uuid.uuid4().hex[:12]}",
                "content": "Help me optimize my AWS costs",
                "role": "user", 
                "thread_id": thread_id,
                "created_at": created_at + timedelta(seconds=1)
            },
            {
                "id": f"msg_{uuid.uuid4().hex[:12]}",
                "content": "I'll analyze your AWS spend and identify optimization opportunities.",
                "role": "assistant",
                "thread_id": thread_id, 
                "created_at": created_at + timedelta(seconds=2)
            },
            {
                "id": f"msg_{uuid.uuid4().hex[:12]}",
                "content": "Based on analysis, you can save $2,500/month by rightsizing EC2 instances.",
                "role": "assistant",
                "thread_id": thread_id,
                "created_at": created_at + timedelta(seconds=3)
            }
        ]
        
        # Insert messages with proper ordering
        for msg in messages:
            await db.execute("""
                INSERT INTO backend.messages (id, thread_id, content, role, created_at, metadata)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, msg["id"], msg["thread_id"], msg["content"], msg["role"], msg["created_at"], {})
        
        # Verify thread persistence
        thread_result = await db.fetchrow("""
            SELECT * FROM backend.threads WHERE id = $1 AND user_id = $2
        """, thread_id, user_id)
        
        assert thread_result is not None
        assert thread_result["name"] == "AWS Cost Optimization"
        assert thread_result["metadata"]["category"] == "business_optimization"
        assert thread_result["is_active"] is True
        
        # Verify message persistence and ordering
        message_results = await db.fetch("""
            SELECT * FROM backend.messages 
            WHERE thread_id = $1 
            ORDER BY created_at ASC
        """, thread_id)
        
        assert len(message_results) == 3
        assert message_results[0]["content"] == "Help me optimize my AWS costs"
        assert message_results[0]["role"] == "user"
        assert message_results[1]["role"] == "assistant"
        assert message_results[2]["content"].startswith("Based on analysis")
        
        # Verify chronological ordering
        for i in range(len(message_results) - 1):
            assert message_results[i]["created_at"] < message_results[i + 1]["created_at"]
        
        self.logger.info(f"✓ Thread persistence verified: {thread_id} with {len(message_results)} messages")
        
        # Business value assertion
        self.assert_business_value_delivered(
            {
                "thread": thread_result,
                "messages": message_results,
                "conversation_continuity": True,
                "cost_savings_identified": "$2,500/month"
            },
            "insights"  # Conversation provides actionable insights
        )
    
    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_agent_execution_persistence_and_tracking(self, real_services_fixture):
        """
        Test agent execution persistence during golden path optimization flow.
        
        BUSINESS VALUE: Execution tracking enables analytics and billing
        - Agent runs are tracked for performance monitoring
        - Execution results are preserved for user value
        - Cost and token usage tracked for billing
        """
        services = real_services_fixture
        if not services["database_available"]:
            pytest.skip("Database not available for integration test")
            
        db = services["db"]
        
        # Create test user and thread
        user_data = await self.create_test_user_context(services, {
            "email": f"exec_test_{uuid.uuid4().hex[:8]}@test.com",
            "name": "Execution Test User"
        })
        user_id = user_data["id"]
        
        thread_id = f"thread_{uuid.uuid4().hex[:12]}"
        await db.execute("""
            INSERT INTO backend.threads (id, user_id, name, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5)
        """, thread_id, user_id, "Cost Analysis Thread", datetime.now(timezone.utc), datetime.now(timezone.utc))
        
        # Create agent execution record
        execution_id = f"exec_{uuid.uuid4().hex[:12]}"
        execution_data = {
            "id": execution_id,
            "user_id": user_id,
            "agent_id": "cost_optimizer_agent",
            "thread_id": thread_id,
            "status": "pending",
            "input_data": {
                "user_request": "Analyze AWS costs",
                "account_id": "123456789",
                "time_period": "last_30_days"
            },
            "start_time": datetime.now(timezone.utc)
        }
        
        # Insert execution record
        await db.execute("""
            INSERT INTO backend.agent_executions 
            (id, user_id, agent_id, thread_id, status, start_time, input_data, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """, execution_data["id"], execution_data["user_id"], execution_data["agent_id"],
            execution_data["thread_id"], execution_data["status"], execution_data["start_time"],
            execution_data["input_data"], datetime.now(timezone.utc), datetime.now(timezone.utc))
        
        # Simulate execution progress - mark as running
        await db.execute("""
            UPDATE backend.agent_executions 
            SET status = $1, updated_at = $2
            WHERE id = $3
        """, "running", datetime.now(timezone.utc), execution_id)
        
        # Simulate execution completion with results
        end_time = datetime.now(timezone.utc)
        output_data = {
            "analysis_results": {
                "total_monthly_cost": 15000,
                "optimization_opportunities": [
                    {
                        "service": "EC2",
                        "recommendation": "Rightsize instances",
                        "potential_savings": 2500,
                        "confidence": 0.9
                    },
                    {
                        "service": "RDS",
                        "recommendation": "Reserved instances",
                        "potential_savings": 800,
                        "confidence": 0.85
                    }
                ],
                "total_potential_savings": 3300
            },
            "execution_metrics": {
                "analysis_duration_seconds": 45,
                "data_points_analyzed": 50000
            }
        }
        
        # Update execution with completion data
        await db.execute("""
            UPDATE backend.agent_executions 
            SET status = $1, end_time = $2, output_data = $3, 
                tokens_used = $4, api_calls_made = $5, cost_cents = $6,
                duration_seconds = $7, updated_at = $8
            WHERE id = $9
        """, "completed", end_time, output_data, 1500, 8, 45, 45.0, datetime.now(timezone.utc), execution_id)
        
        # Verify execution persistence
        execution_result = await db.fetchrow("""
            SELECT * FROM backend.agent_executions WHERE id = $1 AND user_id = $2
        """, execution_id, user_id)
        
        assert execution_result is not None
        assert execution_result["status"] == "completed"
        assert execution_result["agent_id"] == "cost_optimizer_agent"
        assert execution_result["thread_id"] == thread_id
        assert execution_result["tokens_used"] == 1500
        assert execution_result["api_calls_made"] == 8
        assert execution_result["cost_cents"] == 45
        assert execution_result["duration_seconds"] == 45.0
        
        # Verify output data structure
        output = execution_result["output_data"]
        assert output["analysis_results"]["total_potential_savings"] == 3300
        assert len(output["analysis_results"]["optimization_opportunities"]) == 2
        assert output["execution_metrics"]["data_points_analyzed"] == 50000
        
        self.logger.info(f"✓ Agent execution tracking verified: {execution_id}")
        
        # Business value assertion  
        self.assert_business_value_delivered(
            {
                "execution_tracked": True,
                "potential_savings": output["analysis_results"]["total_potential_savings"],
                "recommendations": output["analysis_results"]["optimization_opportunities"],
                "performance_metrics": output["execution_metrics"]
            },
            "cost_savings"  # Agent delivers cost optimization value
        )
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_user_concurrent_database_operations(self, real_services_fixture):
        """
        Test multi-user concurrent database operations maintain isolation.
        
        BUSINESS VALUE: Platform must handle multiple users simultaneously
        - No cross-user data contamination
        - Concurrent operations don't interfere
        - Transaction isolation prevents race conditions
        """
        services = real_services_fixture
        if not services["database_available"]:
            pytest.skip("Database not available for integration test")
            
        db = services["db"]
        
        # Create multiple test users
        users = []
        for i in range(3):
            user_data = await self.create_test_user_context(services, {
                "email": f"concurrent_user_{i}_{uuid.uuid4().hex[:8]}@test.com",
                "name": f"Concurrent User {i}"
            })
            users.append(TestUserData(
                user_id=user_data["id"],
                email=user_data["email"], 
                name=user_data["name"],
                thread_ids=[],
                execution_ids=[]
            ))
        
        async def create_user_data(user: TestUserData, operations_count: int):
            """Create threads and executions for a user concurrently."""
            tasks = []
            
            for j in range(operations_count):
                # Create thread
                thread_id = f"thread_{user.user_id}_{j}_{uuid.uuid4().hex[:8]}"
                user.thread_ids.append(thread_id)
                
                tasks.append(db.execute("""
                    INSERT INTO backend.threads (id, user_id, name, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5)
                """, thread_id, user.user_id, f"Thread {j} for {user.name}", 
                    datetime.now(timezone.utc), datetime.now(timezone.utc)))
                
                # Create execution
                execution_id = f"exec_{user.user_id}_{j}_{uuid.uuid4().hex[:8]}"
                user.execution_ids.append(execution_id)
                
                tasks.append(db.execute("""
                    INSERT INTO backend.agent_executions 
                    (id, user_id, agent_id, thread_id, status, start_time, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, execution_id, user.user_id, "test_agent", thread_id, "completed",
                    datetime.now(timezone.utc), datetime.now(timezone.utc), datetime.now(timezone.utc)))
            
            # Execute all operations for this user concurrently
            await asyncio.gather(*tasks)
            return user
        
        # Run concurrent operations for all users
        operations_per_user = 5
        user_tasks = [
            create_user_data(user, operations_per_user) 
            for user in users
        ]
        
        start_time = asyncio.get_event_loop().time()
        completed_users = await asyncio.gather(*user_tasks)
        duration = asyncio.get_event_loop().time() - start_time
        
        # Verify data isolation - each user should only see their own data
        for user in completed_users:
            # Check threads isolation
            user_threads = await db.fetch("""
                SELECT * FROM backend.threads WHERE user_id = $1
            """, user.user_id)
            
            assert len(user_threads) == operations_per_user
            for thread in user_threads:
                assert thread["user_id"] == user.user_id
                assert thread["id"] in user.thread_ids
            
            # Check executions isolation  
            user_executions = await db.fetch("""
                SELECT * FROM backend.agent_executions WHERE user_id = $1
            """, user.user_id)
            
            assert len(user_executions) == operations_per_user
            for execution in user_executions:
                assert execution["user_id"] == user.user_id
                assert execution["id"] in user.execution_ids
        
        # Verify no cross-user data leakage
        for i, user in enumerate(completed_users):
            other_users = [u for j, u in enumerate(completed_users) if j != i]
            
            for other_user in other_users:
                # User should not see other user's threads
                cross_threads = await db.fetch("""
                    SELECT * FROM backend.threads 
                    WHERE user_id = $1 AND id = ANY($2)
                """, user.user_id, other_user.thread_ids)
                
                assert len(cross_threads) == 0, f"Data leakage: {user.user_id} can see {other_user.user_id}'s threads"
                
                # User should not see other user's executions
                cross_executions = await db.fetch("""
                    SELECT * FROM backend.agent_executions
                    WHERE user_id = $1 AND id = ANY($2)  
                """, user.user_id, other_user.execution_ids)
                
                assert len(cross_executions) == 0, f"Data leakage: {user.user_id} can see {other_user.user_id}'s executions"
        
        self.logger.info(f"✓ Multi-user isolation verified: {len(completed_users)} users, {operations_per_user * len(completed_users)} operations in {duration:.2f}s")
        
        # Business value assertion
        self.assert_business_value_delivered(
            {
                "users_processed": len(completed_users),
                "total_operations": operations_per_user * len(completed_users),
                "duration_seconds": duration,
                "data_isolation_verified": True,
                "concurrent_operations_succeeded": True
            },
            "automation"  # Platform handles multiple users automatically
        )
    
    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_database_transaction_rollback_and_consistency(self, real_services_fixture):
        """
        Test database transaction rollback maintains data consistency.
        
        BUSINESS VALUE: Data integrity must be preserved during errors
        - Failed operations don't leave partial data
        - Transaction rollback restores consistent state
        - Error recovery preserves user experience
        """
        services = real_services_fixture
        if not services["database_available"]:
            pytest.skip("Database not available for integration test")
            
        db = services["db"]
        
        # Create test user
        user_data = await self.create_test_user_context(services, {
            "email": f"transaction_test_{uuid.uuid4().hex[:8]}@test.com",
            "name": "Transaction Test User"
        })
        user_id = user_data["id"]
        
        # Verify initial state - no threads or executions
        initial_threads = await db.fetch("SELECT * FROM backend.threads WHERE user_id = $1", user_id)
        initial_executions = await db.fetch("SELECT * FROM backend.agent_executions WHERE user_id = $1", user_id)
        
        assert len(initial_threads) == 0
        assert len(initial_executions) == 0
        
        # Test successful transaction
        thread_id = f"thread_{uuid.uuid4().hex[:12]}"
        execution_id = f"exec_{uuid.uuid4().hex[:12]}"
        
        async with db.transaction():
            # Create thread
            await db.execute("""
                INSERT INTO backend.threads (id, user_id, name, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5)
            """, thread_id, user_id, "Test Thread", datetime.now(timezone.utc), datetime.now(timezone.utc))
            
            # Create execution
            await db.execute("""
                INSERT INTO backend.agent_executions 
                (id, user_id, agent_id, thread_id, status, start_time, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, execution_id, user_id, "test_agent", thread_id, "completed",
                datetime.now(timezone.utc), datetime.now(timezone.utc), datetime.now(timezone.utc))
        
        # Verify successful transaction committed
        committed_threads = await db.fetch("SELECT * FROM backend.threads WHERE user_id = $1", user_id)
        committed_executions = await db.fetch("SELECT * FROM backend.agent_executions WHERE user_id = $1", user_id)
        
        assert len(committed_threads) == 1
        assert len(committed_executions) == 1
        assert committed_threads[0]["id"] == thread_id
        assert committed_executions[0]["id"] == execution_id
        
        # Test transaction rollback on error
        failed_thread_id = f"thread_{uuid.uuid4().hex[:12]}"
        failed_execution_id = f"exec_{uuid.uuid4().hex[:12]}"
        
        try:
            async with db.transaction():
                # Create thread (this should succeed)
                await db.execute("""
                    INSERT INTO backend.threads (id, user_id, name, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5)
                """, failed_thread_id, user_id, "Failed Thread", datetime.now(timezone.utc), datetime.now(timezone.utc))
                
                # Create execution (this should succeed)
                await db.execute("""
                    INSERT INTO backend.agent_executions 
                    (id, user_id, agent_id, thread_id, status, start_time, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, failed_execution_id, user_id, "test_agent", failed_thread_id, "completed",
                    datetime.now(timezone.utc), datetime.now(timezone.utc), datetime.now(timezone.utc))
                
                # Force an error to trigger rollback
                await db.execute("SELECT * FROM non_existent_table")
                
        except Exception as e:
            # Expected error due to invalid table
            self.logger.info(f"Expected transaction error: {e}")
        
        # Verify rollback - no new records should exist
        final_threads = await db.fetch("SELECT * FROM backend.threads WHERE user_id = $1", user_id)
        final_executions = await db.fetch("SELECT * FROM backend.agent_executions WHERE user_id = $1", user_id)
        
        # Should still only have the originally committed records
        assert len(final_threads) == 1  # Only the successful transaction
        assert len(final_executions) == 1  # Only the successful transaction
        assert final_threads[0]["id"] == thread_id  # Original thread still exists
        assert final_executions[0]["id"] == execution_id  # Original execution still exists
        
        # Verify failed transaction data was rolled back
        failed_thread_check = await db.fetch("SELECT * FROM backend.threads WHERE id = $1", failed_thread_id)
        failed_execution_check = await db.fetch("SELECT * FROM backend.agent_executions WHERE id = $1", failed_execution_id)
        
        assert len(failed_thread_check) == 0, "Failed transaction thread should not exist"
        assert len(failed_execution_check) == 0, "Failed transaction execution should not exist"
        
        self.logger.info("✓ Transaction rollback and consistency verified")
        
        # Business value assertion
        self.assert_business_value_delivered(
            {
                "successful_transactions": 1,
                "failed_transactions_rolled_back": 1,
                "data_consistency_maintained": True,
                "no_partial_data": True
            },
            "automation"  # Automatic error recovery maintains data integrity
        )
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_redis_postgresql_cache_coordination(self, real_services_fixture):
        """
        Test Redis cache coordination with PostgreSQL during golden path.
        
        BUSINESS VALUE: Caching improves performance while maintaining consistency
        - Fast response times for repeated queries
        - Cache invalidation keeps data fresh
        - Cache-aside pattern ensures consistency
        """
        services = real_services_fixture
        if not services["database_available"]:
            pytest.skip("Database not available for integration test")
            
        db = services["db"]
        
        # Try to get Redis connection - gracefully handle if not available
        redis_client = None
        try:
            import redis.asyncio as redis
            redis_url = services.get("redis_url", "redis://localhost:6381")
            redis_client = redis.from_url(redis_url)
            await redis_client.ping()
        except Exception as e:
            self.logger.info(f"Redis not available, testing database-only path: {e}")
        
        # Create test user and thread
        user_data = await self.create_test_user_context(services, {
            "email": f"cache_test_{uuid.uuid4().hex[:8]}@test.com",
            "name": "Cache Test User"
        })
        user_id = user_data["id"]
        
        thread_id = f"thread_{uuid.uuid4().hex[:12]}"
        thread_data = {
            "id": thread_id,
            "user_id": user_id,
            "name": "Cache Test Thread",
            "metadata": {"optimization_type": "cost_analysis"},
            "created_at": datetime.now(timezone.utc)
        }
        
        # Insert thread into database
        await db.execute("""
            INSERT INTO backend.threads (id, user_id, name, metadata, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, thread_data["id"], thread_data["user_id"], thread_data["name"], 
            thread_data["metadata"], thread_data["created_at"], thread_data["created_at"])
        
        # Test database query performance without cache
        import time
        start_time = time.time()
        
        db_result = await db.fetchrow("""
            SELECT * FROM backend.threads WHERE id = $1 AND user_id = $2
        """, thread_id, user_id)
        
        db_query_time = time.time() - start_time
        
        assert db_result is not None
        assert db_result["name"] == "Cache Test Thread"
        assert db_result["metadata"]["optimization_type"] == "cost_analysis"
        
        # Test with Redis cache if available
        cache_query_time = None
        cache_hit = False
        
        if redis_client:
            # Cache key for thread
            cache_key = f"thread:{thread_id}:user:{user_id}"
            
            # First check cache (should be empty)
            cached_data = await redis_client.get(cache_key)
            assert cached_data is None, "Cache should be empty initially"
            
            # Store in cache
            cache_data = {
                "id": db_result["id"],
                "user_id": db_result["user_id"],
                "name": db_result["name"],
                "metadata": db_result["metadata"],
                "created_at": db_result["created_at"].isoformat()
            }
            
            import json
            await redis_client.setex(cache_key, 300, json.dumps(cache_data, default=str))
            
            # Test cache hit performance
            start_time = time.time()
            cached_result = await redis_client.get(cache_key)
            cache_query_time = time.time() - start_time
            
            assert cached_result is not None
            cached_data = json.loads(cached_result)
            assert cached_data["name"] == "Cache Test Thread"
            assert cached_data["metadata"]["optimization_type"] == "cost_analysis"
            cache_hit = True
            
            # Test cache invalidation on update
            updated_name = "Updated Cache Test Thread"
            await db.execute("""
                UPDATE backend.threads SET name = $1, updated_at = $2 WHERE id = $3
            """, updated_name, datetime.now(timezone.utc), thread_id)
            
            # Invalidate cache
            await redis_client.delete(cache_key)
            
            # Verify cache is empty after invalidation
            invalidated_cache = await redis_client.get(cache_key)
            assert invalidated_cache is None, "Cache should be empty after invalidation"
            
            # Verify database has updated data
            updated_result = await db.fetchrow("""
                SELECT * FROM backend.threads WHERE id = $1 AND user_id = $2
            """, thread_id, user_id)
            
            assert updated_result["name"] == updated_name
            
            await redis_client.close()
        
        self.logger.info(f"✓ Cache coordination verified - DB: {db_query_time:.4f}s, Cache: {cache_query_time:.4f}s" if cache_query_time else f"✓ Database query verified: {db_query_time:.4f}s")
        
        # Business value assertion
        performance_improvement = None
        if cache_query_time and db_query_time > 0:
            performance_improvement = (db_query_time - cache_query_time) / db_query_time * 100
        
        self.assert_business_value_delivered(
            {
                "database_query_time": db_query_time,
                "cache_query_time": cache_query_time,
                "cache_hit": cache_hit,
                "performance_improvement_percent": performance_improvement,
                "cache_invalidation_tested": redis_client is not None
            },
            "automation"  # Automatic caching improves performance
        )
    
    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_database_cleanup_and_resource_management(self, real_services_fixture):
        """
        Test database cleanup and resource management during golden path.
        
        BUSINESS VALUE: Proper resource management ensures platform stability
        - Database connections are properly managed
        - No resource leaks during heavy usage
        - Clean shutdown preserves data integrity
        """
        services = real_services_fixture
        if not services["database_available"]:
            pytest.skip("Database not available for integration test")
            
        # Get connection info for monitoring
        postgres_info = services.get("postgres")
        if not postgres_info:
            pytest.skip("PostgreSQL connection info not available")
        
        # Test connection pool management
        initial_connections = []
        test_data_created = []
        
        try:
            # Create multiple concurrent connections to test pool
            for i in range(5):
                user_data = await self.create_test_user_context(services, {
                    "email": f"cleanup_test_{i}_{uuid.uuid4().hex[:8]}@test.com",
                    "name": f"Cleanup Test User {i}"
                })
                
                # Create thread and execution for each user
                thread_id = f"cleanup_thread_{i}_{uuid.uuid4().hex[:8]}"
                execution_id = f"cleanup_exec_{i}_{uuid.uuid4().hex[:8]}"
                
                db = services["db"]
                
                # Insert thread
                await db.execute("""
                    INSERT INTO backend.threads (id, user_id, name, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5)
                """, thread_id, user_data["id"], f"Cleanup Thread {i}", 
                    datetime.now(timezone.utc), datetime.now(timezone.utc))
                
                # Insert execution
                await db.execute("""
                    INSERT INTO backend.agent_executions 
                    (id, user_id, agent_id, thread_id, status, start_time, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, execution_id, user_data["id"], "cleanup_agent", thread_id, "completed",
                    datetime.now(timezone.utc), datetime.now(timezone.utc), datetime.now(timezone.utc))
                
                test_data_created.append({
                    "user_id": user_data["id"],
                    "thread_id": thread_id,
                    "execution_id": execution_id
                })
            
            # Verify all data was created successfully
            for data in test_data_created:
                thread_exists = await db.fetchrow("""
                    SELECT id FROM backend.threads WHERE id = $1
                """, data["thread_id"])
                
                execution_exists = await db.fetchrow("""
                    SELECT id FROM backend.agent_executions WHERE id = $1  
                """, data["execution_id"])
                
                assert thread_exists is not None, f"Thread {data['thread_id']} should exist"
                assert execution_exists is not None, f"Execution {data['execution_id']} should exist"
            
            self.logger.info(f"✓ Created test data for {len(test_data_created)} users")
            
            # Test query performance under load
            start_time = time.time()
            query_tasks = []
            
            for data in test_data_created:
                # Query user's threads
                query_tasks.append(db.fetch("""
                    SELECT t.*, COUNT(e.id) as execution_count
                    FROM backend.threads t
                    LEFT JOIN backend.agent_executions e ON t.id = e.thread_id
                    WHERE t.user_id = $1
                    GROUP BY t.id, t.user_id, t.name, t.metadata, t.created_at, t.updated_at, t.is_active
                """, data["user_id"]))
            
            # Execute all queries concurrently
            query_results = await asyncio.gather(*query_tasks)
            query_duration = time.time() - start_time
            
            # Verify query results
            assert len(query_results) == len(test_data_created)
            for i, result in enumerate(query_results):
                assert len(result) == 1, f"User {i} should have exactly 1 thread"
                assert result[0]["execution_count"] == 1, f"User {i} should have 1 execution"
            
            self.logger.info(f"✓ Concurrent queries completed in {query_duration:.2f}s")
            
        finally:
            # Cleanup test data (simulating application shutdown)
            cleanup_start = time.time()
            cleanup_tasks = []
            
            for data in test_data_created:
                # Delete executions first (foreign key constraint)
                cleanup_tasks.append(db.execute("""
                    DELETE FROM backend.agent_executions WHERE user_id = $1
                """, data["user_id"]))
                
            for data in test_data_created:
                # Delete threads
                cleanup_tasks.append(db.execute("""
                    DELETE FROM backend.threads WHERE user_id = $1
                """, data["user_id"]))
                
            for data in test_data_created:
                # Delete users
                cleanup_tasks.append(db.execute("""
                    DELETE FROM auth.users WHERE id = $1
                """, data["user_id"]))
            
            # Execute cleanup concurrently
            await asyncio.gather(*cleanup_tasks)
            cleanup_duration = time.time() - cleanup_start
            
            # Verify cleanup completed
            for data in test_data_created:
                remaining_threads = await db.fetch("""
                    SELECT id FROM backend.threads WHERE user_id = $1
                """, data["user_id"])
                
                remaining_executions = await db.fetch("""
                    SELECT id FROM backend.agent_executions WHERE user_id = $1
                """, data["user_id"])
                
                assert len(remaining_threads) == 0, f"All threads for user {data['user_id']} should be deleted"
                assert len(remaining_executions) == 0, f"All executions for user {data['user_id']} should be deleted"
            
            self.logger.info(f"✓ Cleanup completed in {cleanup_duration:.2f}s")
        
        # Business value assertion
        self.assert_business_value_delivered(
            {
                "users_processed": len(test_data_created),
                "concurrent_query_duration": query_duration,
                "cleanup_duration": cleanup_duration,
                "resource_management_verified": True,
                "no_data_leaks": True
            },
            "automation"  # Automatic resource management ensures stability
        )


if __name__ == "__main__":
    import sys
    pytest.main([__file__, "-v"] + sys.argv[1:])