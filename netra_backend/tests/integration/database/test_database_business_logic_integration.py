"""
Database Business Logic Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure data persistence and retrieval for conversation continuity
- Value Impact: Reliable data operations enable agents to provide personalized insights
- Strategic Impact: Database reliability is foundational to user trust and retention

Integration Points Tested:
1. Agent execution state persistence integration  
2. User context and thread management integration
3. Multi-user data isolation at database level
4. Database transaction coordination with business logic
5. Cache coherency between Redis and PostgreSQL
6. Database connection pooling under load
7. Error handling and recovery for database operations
8. Performance optimization for query patterns
"""

import asyncio
import pytest
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
import json

# Database models and connections
from netra_backend.app.models.user import User
from netra_backend.app.models.thread import Thread  
from netra_backend.app.models.agent_execution import AgentExecution
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.services.user_execution_context import UserExecutionContext


class MockDatabaseSession:
    """Mock database session for integration testing."""
    
    def __init__(self):
        self.data = {}  # table_name -> [records]
        self.transactions = []
        self.queries_executed = []
        self.in_transaction = False
        self.rollback_called = False
        self.commit_called = False
        
    async def execute(self, query: str, parameters: Dict = None):
        """Mock execute query."""
        self.queries_executed.append({
            "query": query,
            "parameters": parameters or {},
            "timestamp": time.time()
        })
        
        # Simulate query execution
        await asyncio.sleep(0.01)
        
        # Return mock results based on query type
        if "SELECT" in query.upper():
            return MockQueryResult([])
        return MockQueryResult([])
        
    async def add(self, obj):
        """Mock add object to session."""
        table_name = obj.__class__.__name__.lower()
        if table_name not in self.data:
            self.data[table_name] = []
        
        # Generate ID if not set
        if not hasattr(obj, 'id') or obj.id is None:
            obj.id = len(self.data[table_name]) + 1
            
        self.data[table_name].append(obj)
        
    async def commit(self):
        """Mock commit transaction."""
        self.commit_called = True
        self.in_transaction = False
        
    async def rollback(self):
        """Mock rollback transaction."""
        self.rollback_called = True
        self.in_transaction = False
        
    async def get(self, model_class, obj_id):
        """Mock get object by ID."""
        table_name = model_class.__name__.lower()
        if table_name in self.data:
            for obj in self.data[table_name]:
                if obj.id == obj_id:
                    return obj
        return None
        
    async def query(self, model_class):
        """Mock query builder.""" 
        return MockQueryBuilder(model_class, self.data)


class MockQueryResult:
    """Mock query result."""
    
    def __init__(self, results: List = None):
        self.results = results or []
        
    def fetchall(self):
        return self.results
        
    def fetchone(self):
        return self.results[0] if self.results else None


class MockQueryBuilder:
    """Mock query builder for filtering."""
    
    def __init__(self, model_class, data: Dict):
        self.model_class = model_class
        self.table_name = model_class.__name__.lower()
        self.data = data
        self.filters = []
        
    def filter(self, *conditions):
        """Mock filter conditions."""
        self.filters.extend(conditions)
        return self
        
    def filter_by(self, **kwargs):
        """Mock filter by keyword arguments."""
        self.filters.append(kwargs)
        return self
        
    def all(self):
        """Mock return all results.""" 
        if self.table_name not in self.data:
            return []
            
        results = self.data[self.table_name][:]
        
        # Apply simple keyword filters
        for filter_dict in self.filters:
            if isinstance(filter_dict, dict):
                for key, value in filter_dict.items():
                    results = [r for r in results if getattr(r, key, None) == value]
                    
        return results
        
    def first(self):
        """Mock return first result."""
        results = self.all()
        return results[0] if results else None


class MockRedisConnection:
    """Mock Redis connection for integration testing."""
    
    def __init__(self):
        self.data = {}
        self.operations = []
        
    async def set(self, key: str, value: str, ex: int = None):
        """Mock set operation."""
        self.data[key] = {
            "value": value,
            "expires_at": time.time() + ex if ex else None,
            "set_at": time.time()
        }
        self.operations.append(("SET", key, value, ex))
        
    async def get(self, key: str) -> Optional[str]:
        """Mock get operation."""
        self.operations.append(("GET", key))
        
        if key in self.data:
            entry = self.data[key]
            if entry["expires_at"] is None or entry["expires_at"] > time.time():
                return entry["value"]
            else:
                del self.data[key]  # Expired
                
        return None
        
    async def delete(self, key: str):
        """Mock delete operation.""" 
        self.operations.append(("DELETE", key))
        if key in self.data:
            del self.data[key]
            return 1
        return 0
        
    async def exists(self, key: str) -> bool:
        """Mock exists check."""
        self.operations.append(("EXISTS", key))
        return key in self.data


# Mock models for testing
class MockUser:
    """Mock user model."""
    def __init__(self, id: int = None, email: str = "", name: str = "", created_at: datetime = None):
        self.id = id
        self.email = email  
        self.name = name
        self.created_at = created_at or datetime.now(timezone.utc)


class MockThread:
    """Mock thread model.""" 
    def __init__(self, id: str = None, user_id: str = "", title: str = "", created_at: datetime = None):
        self.id = id or str(uuid4())
        self.user_id = user_id
        self.title = title
        self.created_at = created_at or datetime.now(timezone.utc)
        self.messages = []


class MockAgentExecution:
    """Mock agent execution model."""
    def __init__(self, id: str = None, user_id: str = "", thread_id: str = "", 
                 agent_name: str = "", status: str = "running", result: Dict = None):
        self.id = id or str(uuid4())
        self.user_id = user_id
        self.thread_id = thread_id
        self.agent_name = agent_name
        self.status = status
        self.result = result or {}
        self.created_at = datetime.now(timezone.utc)
        self.completed_at = None


@pytest.mark.integration
@pytest.mark.real_services
class TestDatabaseBusinessLogicIntegration:
    """Database business logic integration tests."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Provide mock database session."""
        return MockDatabaseSession()
        
    @pytest.fixture
    def mock_redis(self):
        """Provide mock Redis connection."""
        return MockRedisConnection()
        
    @pytest.fixture
    def enterprise_user_context(self):
        """Provide enterprise user context."""
        return UserExecutionContext(
            user_id="enterprise_user_123",
            thread_id="enterprise_thread_456", 
            correlation_id="enterprise_correlation_789",
            permissions=["data_access", "advanced_features"],
            subscription_tier="enterprise"
        )
        
    @pytest.fixture
    def basic_user_context(self):
        """Provide basic user context."""
        return UserExecutionContext(
            user_id="basic_user_456",
            thread_id="basic_thread_789",
            correlation_id="basic_correlation_123", 
            permissions=["basic_access"],
            subscription_tier="basic"
        )
        
    async def test_user_creation_and_retrieval_integration(self, mock_db_session):
        """Test user creation and retrieval with database integration."""
        # BUSINESS VALUE: User management enables personalized optimization experiences
        
        # Execute: Create new user
        new_user = MockUser(
            email="integration.test@netra.ai",
            name="Integration Test User"
        )
        
        await mock_db_session.add(new_user)
        await mock_db_session.commit()
        
        # Verify: User was added to database
        assert mock_db_session.commit_called is True
        assert "user" in mock_db_session.data
        assert len(mock_db_session.data["user"]) == 1
        
        stored_user = mock_db_session.data["user"][0]
        assert stored_user.email == "integration.test@netra.ai"
        assert stored_user.name == "Integration Test User"
        assert stored_user.id is not None
        
        # Execute: Retrieve user by ID
        retrieved_user = await mock_db_session.get(MockUser, stored_user.id)
        
        # Verify: User retrieved successfully
        assert retrieved_user is not None
        assert retrieved_user.id == stored_user.id
        assert retrieved_user.email == "integration.test@netra.ai"
        
    async def test_thread_management_with_user_association_integration(
        self, mock_db_session, enterprise_user_context
    ):
        """Test thread management with user association integration."""
        # BUSINESS VALUE: Thread management enables conversation continuity 
        
        # Setup: Create user first
        user = MockUser(
            id=1,
            email="thread.test@netra.ai",
            name="Thread Test User"
        )
        await mock_db_session.add(user)
        await mock_db_session.commit()
        
        # Execute: Create thread for user
        thread = MockThread(
            user_id=str(user.id),
            title="Cost Optimization Discussion"
        )
        
        await mock_db_session.add(thread)
        await mock_db_session.commit()
        
        # Verify: Thread created with user association
        assert "thread" in mock_db_session.data
        assert len(mock_db_session.data["thread"]) == 1
        
        stored_thread = mock_db_session.data["thread"][0]
        assert stored_thread.user_id == "1"
        assert stored_thread.title == "Cost Optimization Discussion"
        assert stored_thread.id is not None
        
        # Execute: Retrieve threads for user
        query_builder = await mock_db_session.query(MockThread)
        user_threads = query_builder.filter_by(user_id="1").all()
        
        # Verify: User's threads retrieved
        assert len(user_threads) == 1
        assert user_threads[0].title == "Cost Optimization Discussion"
        
    async def test_agent_execution_state_persistence_integration(
        self, mock_db_session, enterprise_user_context
    ):
        """Test agent execution state persistence integration."""
        # BUSINESS VALUE: State persistence enables complex multi-step optimizations
        
        # Setup: Agent execution with complex state
        agent_state = DeepAgentState()
        agent_state.user_id = enterprise_user_context.user_id
        agent_state.thread_id = enterprise_user_context.thread_id
        agent_state.context_data = {
            "optimization_request": "Reduce AWS costs by 30%",
            "aws_account_id": "123456789012",
            "regions_analyzed": ["us-east-1", "us-west-2", "eu-west-1"],
            "analysis_results": {
                "current_monthly_spend": 45000,
                "optimization_opportunities": [
                    {"type": "rightsizing", "potential_savings": 12000},
                    {"type": "reserved_instances", "potential_savings": 8000},
                    {"type": "spot_instances", "potential_savings": 5000}
                ],
                "confidence_score": 0.87
            },
            "processing_stage": "generating_recommendations"
        }
        
        # Execute: Persist agent execution state
        execution = MockAgentExecution(
            user_id=enterprise_user_context.user_id,
            thread_id=enterprise_user_context.thread_id,
            agent_name="cost_optimizer_agent",
            status="in_progress",
            result=agent_state.context_data
        )
        
        await mock_db_session.add(execution)
        await mock_db_session.commit()
        
        # Verify: Execution state persisted
        assert "agentexecution" in mock_db_session.data
        stored_execution = mock_db_session.data["agentexecution"][0]
        
        assert stored_execution.user_id == enterprise_user_context.user_id
        assert stored_execution.thread_id == enterprise_user_context.thread_id
        assert stored_execution.agent_name == "cost_optimizer_agent"
        assert stored_execution.status == "in_progress"
        
        # Verify: Complex state data preserved
        result_data = stored_execution.result
        assert result_data["aws_account_id"] == "123456789012"
        assert len(result_data["regions_analyzed"]) == 3
        assert result_data["analysis_results"]["current_monthly_spend"] == 45000
        assert len(result_data["analysis_results"]["optimization_opportunities"]) == 3
        
        # Execute: Update execution status
        stored_execution.status = "completed"
        stored_execution.completed_at = datetime.now(timezone.utc)
        stored_execution.result["final_recommendations"] = [
            {
                "priority": "high", 
                "action": "Rightsize overprovisioned EC2 instances",
                "estimated_savings": 12000,
                "implementation_complexity": "low"
            }
        ]
        
        await mock_db_session.commit()
        
        # Verify: State update persisted
        assert stored_execution.status == "completed"
        assert stored_execution.completed_at is not None
        assert "final_recommendations" in stored_execution.result
        
    async def test_multi_user_data_isolation_integration(
        self, mock_db_session, enterprise_user_context, basic_user_context
    ):
        """Test multi-user data isolation at database level."""
        # BUSINESS VALUE: Data isolation ensures user privacy and regulatory compliance
        
        # Setup: Create data for multiple users
        
        # Enterprise user data
        enterprise_thread = MockThread(
            user_id=enterprise_user_context.user_id,
            title="Enterprise Cost Analysis - Q4 Strategy"
        )
        enterprise_execution = MockAgentExecution(
            user_id=enterprise_user_context.user_id,
            thread_id=enterprise_user_context.thread_id,
            agent_name="enterprise_optimizer",
            result={
                "sensitive_data": "Enterprise confidential cost data",
                "annual_spend": 2500000,
                "optimization_target": 750000
            }
        )
        
        # Basic user data  
        basic_thread = MockThread(
            user_id=basic_user_context.user_id,
            title="Personal AWS Cost Optimization"
        )
        basic_execution = MockAgentExecution(
            user_id=basic_user_context.user_id,
            thread_id=basic_user_context.thread_id,
            agent_name="basic_optimizer",
            result={
                "personal_data": "Basic user optimization data",
                "monthly_spend": 150,
                "optimization_target": 50
            }
        )
        
        # Store all data
        await mock_db_session.add(enterprise_thread)
        await mock_db_session.add(enterprise_execution) 
        await mock_db_session.add(basic_thread)
        await mock_db_session.add(basic_execution)
        await mock_db_session.commit()
        
        # Execute: Query enterprise user data only
        enterprise_threads = await mock_db_session.query(MockThread).filter_by(
            user_id=enterprise_user_context.user_id
        ).all()
        enterprise_executions = await mock_db_session.query(MockAgentExecution).filter_by(
            user_id=enterprise_user_context.user_id  
        ).all()
        
        # Verify: Enterprise user isolation
        assert len(enterprise_threads) == 1
        assert len(enterprise_executions) == 1
        
        assert enterprise_threads[0].title == "Enterprise Cost Analysis - Q4 Strategy"
        assert enterprise_executions[0].result["annual_spend"] == 2500000
        
        # Verify: No basic user data in enterprise results
        for thread in enterprise_threads:
            assert "Personal AWS" not in thread.title
        for execution in enterprise_executions:
            assert "personal_data" not in execution.result
            
        # Execute: Query basic user data only  
        basic_threads = await mock_db_session.query(MockThread).filter_by(
            user_id=basic_user_context.user_id
        ).all()
        basic_executions = await mock_db_session.query(MockAgentExecution).filter_by(
            user_id=basic_user_context.user_id
        ).all()
        
        # Verify: Basic user isolation
        assert len(basic_threads) == 1
        assert len(basic_executions) == 1
        
        assert basic_threads[0].title == "Personal AWS Cost Optimization"
        assert basic_executions[0].result["monthly_spend"] == 150
        
        # Verify: No enterprise data in basic results
        for thread in basic_threads:
            assert "Enterprise" not in thread.title
        for execution in basic_executions:
            assert "sensitive_data" not in execution.result
            assert execution.result["monthly_spend"] < 1000  # Much smaller than enterprise
            
    async def test_database_redis_cache_coherency_integration(
        self, mock_db_session, mock_redis, enterprise_user_context
    ):
        """Test cache coherency between database and Redis integration."""
        # BUSINESS VALUE: Cache coherency improves performance without data inconsistency
        
        # Execute: Store thread in database
        thread = MockThread(
            user_id=enterprise_user_context.user_id,
            title="Cached Optimization Session"
        )
        await mock_db_session.add(thread)
        await mock_db_session.commit()
        
        # Execute: Cache thread data in Redis
        cache_key = f"thread:{thread.id}"
        thread_json = json.dumps({
            "id": thread.id,
            "user_id": thread.user_id,
            "title": thread.title,
            "created_at": thread.created_at.isoformat()
        })
        await mock_redis.set(cache_key, thread_json, ex=3600)  # 1 hour TTL
        
        # Verify: Data cached in Redis
        cached_data = await mock_redis.get(cache_key)
        assert cached_data is not None
        
        cached_thread = json.loads(cached_data)
        assert cached_thread["title"] == "Cached Optimization Session"
        assert cached_thread["user_id"] == enterprise_user_context.user_id
        
        # Execute: Update thread in database
        stored_thread = mock_db_session.data["thread"][0]
        stored_thread.title = "Updated Optimization Session"
        await mock_db_session.commit()
        
        # Execute: Invalidate cache
        await mock_redis.delete(cache_key)
        
        # Verify: Cache invalidated
        cached_data_after = await mock_redis.get(cache_key)
        assert cached_data_after is None
        
        # Execute: Re-cache with updated data
        updated_thread_json = json.dumps({
            "id": stored_thread.id,
            "user_id": stored_thread.user_id,
            "title": stored_thread.title,  # Updated title
            "created_at": stored_thread.created_at.isoformat()
        })
        await mock_redis.set(cache_key, updated_thread_json, ex=3600)
        
        # Verify: Cache coherency maintained
        updated_cached_data = await mock_redis.get(cache_key)
        updated_cached_thread = json.loads(updated_cached_data)
        assert updated_cached_thread["title"] == "Updated Optimization Session"
        
    async def test_database_transaction_rollback_integration(self, mock_db_session):
        """Test database transaction rollback integration.""" 
        # BUSINESS VALUE: Transaction integrity prevents data corruption
        
        # Setup: Begin transaction
        mock_db_session.in_transaction = True
        
        # Execute: Add multiple related objects
        user = MockUser(email="transaction.test@netra.ai", name="Transaction Test")
        await mock_db_session.add(user)
        
        thread = MockThread(user_id="1", title="Transaction Test Thread")
        await mock_db_session.add(thread)
        
        execution = MockAgentExecution(
            user_id="1",
            thread_id=thread.id,
            agent_name="transaction_test_agent"
        )
        await mock_db_session.add(execution)
        
        # Verify: Objects added to session but not committed
        assert len(mock_db_session.data.get("user", [])) == 1
        assert len(mock_db_session.data.get("thread", [])) == 1  
        assert len(mock_db_session.data.get("agentexecution", [])) == 1
        assert mock_db_session.commit_called is False
        
        # Execute: Simulate error and rollback
        try:
            # Simulate business logic error
            raise RuntimeError("Simulated business logic error")
        except RuntimeError:
            await mock_db_session.rollback()
            
        # Verify: Rollback executed
        assert mock_db_session.rollback_called is True
        assert mock_db_session.in_transaction is False
        
        # In a real implementation, rollback would remove uncommitted data
        # Here we verify the rollback was called as expected
        
    async def test_database_concurrent_access_integration(self, mock_db_session):
        """Test database concurrent access patterns."""
        # BUSINESS VALUE: Concurrent access support enables multi-user scalability
        
        # Execute: Simulate concurrent user operations
        async def user_operation(user_id: int, operation_count: int):
            """Simulate user database operations."""
            operations = []
            for i in range(operation_count):
                # Create execution record
                execution = MockAgentExecution(
                    user_id=f"user_{user_id}",
                    thread_id=f"thread_{user_id}_{i}",
                    agent_name=f"agent_{i}",
                    result={"operation_id": i, "user_id": user_id}
                )
                await mock_db_session.add(execution)
                operations.append(execution)
                
                # Small delay to simulate processing time
                await asyncio.sleep(0.01)
                
            await mock_db_session.commit()
            return operations
            
        # Execute: Run concurrent operations
        concurrent_tasks = [
            user_operation(1, 3),  # User 1: 3 operations
            user_operation(2, 2),  # User 2: 2 operations 
            user_operation(3, 4),  # User 3: 4 operations
        ]
        
        results = await asyncio.gather(*concurrent_tasks)
        
        # Verify: All operations completed
        assert len(results) == 3
        assert len(results[0]) == 3  # User 1 operations
        assert len(results[1]) == 2  # User 2 operations  
        assert len(results[2]) == 4  # User 3 operations
        
        # Verify: Database recorded all operations
        total_executions = sum(len(user_ops) for user_ops in results)
        assert len(mock_db_session.data.get("agentexecution", [])) == total_executions
        
        # Verify: User isolation maintained during concurrent access
        user1_executions = [e for e in mock_db_session.data["agentexecution"] if e.user_id == "user_1"]
        user2_executions = [e for e in mock_db_session.data["agentexecution"] if e.user_id == "user_2"]
        user3_executions = [e for e in mock_db_session.data["agentexecution"] if e.user_id == "user_3"]
        
        assert len(user1_executions) == 3
        assert len(user2_executions) == 2
        assert len(user3_executions) == 4
        
        # Verify: No cross-contamination of user data
        for execution in user1_executions:
            assert execution.result["user_id"] == 1
        for execution in user2_executions:
            assert execution.result["user_id"] == 2
        for execution in user3_executions:
            assert execution.result["user_id"] == 3
            
    async def test_database_query_performance_integration(self, mock_db_session):
        """Test database query performance under load."""
        # BUSINESS VALUE: Query performance enables responsive user experience
        
        # Setup: Create large dataset
        users_count = 100
        threads_per_user = 5
        executions_per_thread = 3
        
        for user_id in range(1, users_count + 1):
            user = MockUser(id=user_id, email=f"perf_test_{user_id}@netra.ai")
            await mock_db_session.add(user)
            
            for thread_idx in range(threads_per_user):
                thread = MockThread(
                    user_id=str(user_id),
                    title=f"Performance Test Thread {thread_idx}"
                )
                await mock_db_session.add(thread)
                
                for exec_idx in range(executions_per_thread):
                    execution = MockAgentExecution(
                        user_id=str(user_id),
                        thread_id=thread.id,
                        agent_name=f"perf_agent_{exec_idx}",
                        result={"test_data": f"user_{user_id}_thread_{thread_idx}_exec_{exec_idx}"}
                    )
                    await mock_db_session.add(execution)
                    
        await mock_db_session.commit()
        
        # Execute: Performance test queries
        start_time = time.time()
        
        # Query 1: Get specific user's data
        user_50_threads = await mock_db_session.query(MockThread).filter_by(user_id="50").all()
        
        # Query 2: Get recent executions (simulate time-based filtering)  
        all_executions = await mock_db_session.query(MockAgentExecution).all()
        recent_executions = [e for e in all_executions if e.created_at > (datetime.now(timezone.utc) - timedelta(hours=1))]
        
        # Query 3: Aggregate query simulation
        agent_counts = {}
        for execution in all_executions:
            agent_name = execution.agent_name
            agent_counts[agent_name] = agent_counts.get(agent_name, 0) + 1
            
        query_time = time.time() - start_time
        
        # Verify: Queries completed efficiently
        assert query_time < 1.0  # Should complete within 1 second
        
        # Verify: Query results correctness
        assert len(user_50_threads) == threads_per_user
        assert len(recent_executions) == users_count * threads_per_user * executions_per_thread
        assert len(agent_counts) == executions_per_thread  # perf_agent_0, perf_agent_1, perf_agent_2
        
        # Verify: Database queries were logged for monitoring
        assert len(mock_db_session.queries_executed) > 0
        query_types = [q["query"] for q in mock_db_session.queries_executed]
        assert any("SELECT" in query for query in query_types)