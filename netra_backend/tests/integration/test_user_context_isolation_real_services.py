"""Integration Tests for User Context Isolation with Real Services

Business Value Justification:
- Segment: Enterprise (critical for multi-tenant security)
- Business Goal: Ensure complete user data isolation in multi-tenant environment
- Value Impact: Prevents data leakage that could cause regulatory violations
- Strategic Impact: Foundation for enterprise-grade security and compliance

CRITICAL TEST PURPOSE:
These integration tests validate user context isolation with real service backends
to ensure no data leakage between concurrent users.

Test Coverage:
- User context isolation in database transactions
- Memory isolation between user sessions
- WebSocket event isolation with real connections
- Tool execution isolation with real services
- State persistence isolation across users
- Recovery isolation during service failures
"""

import pytest
import asyncio
import uuid
import json
from typing import Dict, Any, List
from datetime import datetime

from netra_backend.app.services.user_execution_context import (
    UserExecutionContext, 
    UserExecutionContextFactory
)
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from test_framework.ssot.real_services_test_fixtures import *


@pytest.mark.integration
class TestUserContextIsolationRealServices:
    """Integration tests for user context isolation with real services."""
    
    @pytest.mark.asyncio
    async def test_database_transaction_isolation_real_services(self, real_services_fixture, with_test_database):
        """Test database transaction isolation between concurrent users."""
        # Arrange - verify database is available
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available for isolation testing")
        
        db_session = with_test_database
        
        # Create isolated user contexts
        user1_context = UserExecutionContextFactory.create_isolated_context(
            user_id=f"isolation-user1-{uuid.uuid4()}",
            thread_id=f"user1-thread-{uuid.uuid4()}",
            request_id=f"user1-request-{uuid.uuid4()}"
        )
        
        user2_context = UserExecutionContextFactory.create_isolated_context(
            user_id=f"isolation-user2-{uuid.uuid4()}",
            thread_id=f"user2-thread-{uuid.uuid4()}",  
            request_id=f"user2-request-{uuid.uuid4()}"
        )
        
        # Create user-specific sensitive data
        user1_sensitive_data = {
            "account_id": f"acc1-{uuid.uuid4()}",
            "billing_info": {"card": "****1234", "limit": 5000},
            "personal_data": {"ssn": "***-**-1111", "address": "123 User1 St"}
        }
        
        user2_sensitive_data = {
            "account_id": f"acc2-{uuid.uuid4()}",
            "billing_info": {"card": "****5678", "limit": 10000},
            "personal_data": {"ssn": "***-**-2222", "address": "456 User2 Ave"}
        }
        
        # Act - execute concurrent database transactions for both users
        
        async def user1_database_operations():
            """Database operations for user 1 with transaction isolation."""
            try:
                async with db_session.begin():
                    # Insert user1-specific data
                    from sqlalchemy import text
                    insert_query = text("""
                        INSERT INTO user_data (user_id, account_id, sensitive_data, created_at)
                        VALUES (:user_id, :account_id, :sensitive_data, :created_at)
                    """)
                    
                    await db_session.execute(insert_query, {
                        "user_id": user1_context.user_id,
                        "account_id": user1_sensitive_data["account_id"],
                        "sensitive_data": json.dumps(user1_sensitive_data),
                        "created_at": datetime.utcnow()
                    })
                    
                    # Simulate processing time where data is vulnerable
                    await asyncio.sleep(0.2)
                    
                    # Update user1 data
                    update_query = text("""
                        UPDATE user_data 
                        SET last_accessed = :timestamp 
                        WHERE user_id = :user_id
                    """)
                    
                    await db_session.execute(update_query, {
                        "user_id": user1_context.user_id,
                        "timestamp": datetime.utcnow()
                    })
                    
                    # Query user1 data to verify isolation
                    select_query = text("""
                        SELECT user_id, account_id, sensitive_data 
                        FROM user_data 
                        WHERE user_id = :user_id
                    """)
                    
                    result = await db_session.execute(select_query, {
                        "user_id": user1_context.user_id
                    })
                    user1_record = result.fetchone()
                    
                    return {
                        "user_id": user1_context.user_id,
                        "data_found": user1_record is not None,
                        "account_id": user1_record.account_id if user1_record else None,
                        "sensitive_data": json.loads(user1_record.sensitive_data) if user1_record else None
                    }
            
            except Exception as e:
                return {"error": str(e), "user_id": user1_context.user_id}
        
        async def user2_database_operations():
            """Database operations for user 2 with transaction isolation."""
            try:
                async with db_session.begin():
                    # Insert user2-specific data
                    from sqlalchemy import text
                    insert_query = text("""
                        INSERT INTO user_data (user_id, account_id, sensitive_data, created_at)
                        VALUES (:user_id, :account_id, :sensitive_data, :created_at)
                    """)
                    
                    await db_session.execute(insert_query, {
                        "user_id": user2_context.user_id,
                        "account_id": user2_sensitive_data["account_id"],
                        "sensitive_data": json.dumps(user2_sensitive_data),
                        "created_at": datetime.utcnow()
                    })
                    
                    # Simulate processing time where data is vulnerable
                    await asyncio.sleep(0.15)
                    
                    # Query ALL user data to test isolation
                    select_all_query = text("""
                        SELECT user_id, account_id, sensitive_data 
                        FROM user_data 
                        ORDER BY created_at DESC
                    """)
                    
                    result = await db_session.execute(select_all_query)
                    all_records = result.fetchall()
                    
                    # Should only see user2's data within this transaction
                    user2_records = [r for r in all_records if r.user_id == user2_context.user_id]
                    other_user_records = [r for r in all_records if r.user_id != user2_context.user_id]
                    
                    return {
                        "user_id": user2_context.user_id,
                        "user2_records_count": len(user2_records),
                        "other_user_records_count": len(other_user_records),
                        "total_records": len(all_records),
                        "isolation_verified": len(other_user_records) == 0 or all(
                            r.user_id != user1_context.user_id for r in other_user_records
                        )
                    }
            
            except Exception as e:
                return {"error": str(e), "user_id": user2_context.user_id}
        
        # Execute concurrent database operations
        user1_result, user2_result = await asyncio.gather(
            user1_database_operations(),
            user2_database_operations(),
            return_exceptions=True
        )
        
        # Assert - verify database transaction isolation
        assert not isinstance(user1_result, Exception), f"User1 database operation failed: {user1_result}"
        assert not isinstance(user2_result, Exception), f"User2 database operation failed: {user2_result}"
        
        # Verify user1 data integrity
        assert user1_result["data_found"] == True
        assert user1_result["user_id"] == user1_context.user_id
        assert user1_result["account_id"] == user1_sensitive_data["account_id"]
        
        # Verify user1 sensitive data not leaked
        user1_retrieved_data = user1_result["sensitive_data"]
        assert user1_retrieved_data["billing_info"]["card"] == "****1234"
        assert user1_retrieved_data["personal_data"]["ssn"] == "***-**-1111"
        
        # Verify user2 isolation
        assert user2_result["user_id"] == user2_context.user_id
        assert user2_result["user2_records_count"] >= 1
        
        # Critical: Verify no cross-contamination
        if "sensitive_data" in user1_result and user1_result["sensitive_data"]:
            assert "****5678" not in str(user1_result["sensitive_data"])  # User2's card not in User1's data
            assert "User2 Ave" not in str(user1_result["sensitive_data"])  # User2's address not in User1's data
    
    @pytest.mark.asyncio  
    async def test_memory_isolation_between_user_sessions_real_services(self, real_services_fixture):
        """Test memory isolation between concurrent user sessions."""
        # Arrange
        # Create user contexts with sensitive in-memory data
        user1_context = UserExecutionContextFactory.create_isolated_context(
            user_id=f"memory-user1-{uuid.uuid4()}",
            thread_id=f"mem1-thread-{uuid.uuid4()}"
        )
        
        user2_context = UserExecutionContextFactory.create_isolated_context(
            user_id=f"memory-user2-{uuid.uuid4()}",
            thread_id=f"mem2-thread-{uuid.uuid4()}"
        )
        
        # Add sensitive data to user contexts
        user1_context.add_sensitive_data("api_keys", {
            "aws_key": "AKIA1234567890USER1",
            "openai_key": "sk-user1-secret-key-123"
        })
        
        user1_context.add_sensitive_data("user_preferences", {
            "theme": "dark",
            "notifications": True,
            "private_notes": "User1 confidential notes"
        })
        
        user2_context.add_sensitive_data("api_keys", {
            "aws_key": "AKIA9876543210USER2", 
            "openai_key": "sk-user2-secret-key-456"
        })
        
        user2_context.add_sensitive_data("user_preferences", {
            "theme": "light",
            "notifications": False,
            "private_notes": "User2 confidential notes"
        })
        
        # Act - execute concurrent operations that access sensitive data
        
        async def user1_memory_operations():
            """Memory operations for user 1."""
            # Simulate agent execution with memory access
            state = DeepAgentState(user_id=user1_context.user_id)
            
            # Access user1's sensitive data
            api_keys = user1_context.get_sensitive_data("api_keys")
            preferences = user1_context.get_sensitive_data("user_preferences")
            
            # Store in agent state
            state.user_data = {
                "api_key_preview": api_keys["aws_key"][:10] + "...",
                "user_theme": preferences["theme"],
                "notes_length": len(preferences["private_notes"])
            }
            
            # Simulate processing delay where memory could leak
            await asyncio.sleep(0.3)
            
            # Return sensitive data access results
            return {
                "user_id": user1_context.user_id,
                "api_key_preview": state.user_data["api_key_preview"],
                "theme": state.user_data["user_theme"],
                "notes_length": state.user_data["notes_length"],
                "full_api_keys": api_keys,  # This should be isolated
                "full_preferences": preferences  # This should be isolated
            }
        
        async def user2_memory_operations():
            """Memory operations for user 2."""
            # Simulate agent execution with memory access
            state = DeepAgentState(user_id=user2_context.user_id)
            
            # Access user2's sensitive data
            api_keys = user2_context.get_sensitive_data("api_keys")
            preferences = user2_context.get_sensitive_data("user_preferences")
            
            # Store in agent state
            state.user_data = {
                "api_key_preview": api_keys["aws_key"][:10] + "...",
                "user_theme": preferences["theme"],
                "notes_length": len(preferences["private_notes"])
            }
            
            # Simulate processing delay
            await asyncio.sleep(0.25)
            
            # Try to access user1's data (should fail or return None)
            try:
                user1_data = user2_context.get_sensitive_data("user1_api_keys")  # Should not exist
            except:
                user1_data = None
            
            return {
                "user_id": user2_context.user_id,
                "api_key_preview": state.user_data["api_key_preview"],
                "theme": state.user_data["user_theme"],
                "notes_length": state.user_data["notes_length"],
                "full_api_keys": api_keys,
                "full_preferences": preferences,
                "user1_data_access": user1_data  # Should be None
            }
        
        # Execute concurrent memory operations
        user1_result, user2_result = await asyncio.gather(
            user1_memory_operations(),
            user2_memory_operations(),
            return_exceptions=True
        )
        
        # Assert - verify memory isolation
        assert not isinstance(user1_result, Exception), f"User1 memory operation failed: {user1_result}"
        assert not isinstance(user2_result, Exception), f"User2 memory operation failed: {user2_result}"
        
        # Verify each user gets their own data
        assert user1_result["user_id"] == user1_context.user_id
        assert user2_result["user_id"] == user2_context.user_id
        
        assert user1_result["theme"] == "dark"
        assert user2_result["theme"] == "light"
        
        assert user1_result["api_key_preview"].startswith("AKIA123456")
        assert user2_result["api_key_preview"].startswith("AKIA987654")
        
        # Critical: Verify no cross-contamination
        user1_full_keys = user1_result["full_api_keys"]
        user2_full_keys = user2_result["full_api_keys"]
        
        # User1 should not have User2's keys
        assert "USER2" not in user1_full_keys["aws_key"]
        assert "sk-user2" not in user1_full_keys["openai_key"]
        
        # User2 should not have User1's keys  
        assert "USER1" not in user2_full_keys["aws_key"]
        assert "sk-user1" not in user2_full_keys["openai_key"]
        
        # User2 should not be able to access User1's data
        assert user2_result["user1_data_access"] is None
        
        # Verify private notes isolation
        user1_notes = user1_result["full_preferences"]["private_notes"]
        user2_notes = user2_result["full_preferences"]["private_notes"]
        
        assert "User1 confidential" in user1_notes
        assert "User2 confidential" in user2_notes
        assert "User1" not in user2_notes
        assert "User2" not in user1_notes
    
    @pytest.mark.asyncio
    async def test_agent_execution_state_isolation_real_services(self, real_services_fixture, with_test_database):
        """Test agent execution state isolation with real database persistence."""
        # Arrange - verify database is available
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available for agent state isolation testing")
        
        db_session = with_test_database
        
        # Create isolated user contexts
        user1_context = UserExecutionContextFactory.create_isolated_context(
            user_id=f"agent-user1-{uuid.uuid4()}",
            thread_id=f"agent1-thread-{uuid.uuid4()}"
        )
        
        user2_context = UserExecutionContextFactory.create_isolated_context(
            user_id=f"agent-user2-{uuid.uuid4()}",
            thread_id=f"agent2-thread-{uuid.uuid4()}"
        )
        
        # Create agent states with user-specific data
        user1_state = DeepAgentState(
            user_id=user1_context.user_id,
            thread_id=user1_context.thread_id,
            agent_name="cost_optimizer",
            user_data={
                "account_type": "enterprise",
                "cost_threshold": 10000,
                "sensitive_configs": {"budget_alerts": True, "auto_optimize": False}
            }
        )
        
        user2_state = DeepAgentState(
            user_id=user2_context.user_id,
            thread_id=user2_context.thread_id,
            agent_name="cost_optimizer",
            user_data={
                "account_type": "startup",
                "cost_threshold": 1000,
                "sensitive_configs": {"budget_alerts": False, "auto_optimize": True}
            }
        )
        
        # Create mock agent registry
        from netra_backend.app.core.registry.universal_registry import AgentRegistry
        registry = AgentRegistry()
        
        # Create mock agent that accesses user state
        class IsolationTestAgent:
            def __init__(self):
                self.name = "cost_optimizer"
            
            async def execute(self, context, state):
                """Execute with access to user state."""
                # Access user-specific configuration
                user_config = state.user_data
                account_type = user_config["account_type"]
                threshold = user_config["cost_threshold"]
                
                # Simulate cost analysis with user-specific logic
                if account_type == "enterprise":
                    analysis_depth = "comprehensive"
                    recommendations = ["advanced_reserved_instances", "multi_az_optimization"]
                else:
                    analysis_depth = "basic"
                    recommendations = ["spot_instances", "rightsizing"]
                
                return {
                    "user_id": state.user_id,
                    "account_type": account_type,
                    "threshold": threshold,
                    "analysis_depth": analysis_depth,
                    "recommendations": recommendations,
                    "state_isolation_test": True
                }
        
        isolation_agent = IsolationTestAgent()
        registry.register_agent(isolation_agent)
        
        # Create execution cores with database session
        execution_core1 = AgentExecutionCore(
            registry=registry,
            database_session=db_session,
            user_context=user1_context
        )
        
        execution_core2 = AgentExecutionCore(
            registry=registry,
            database_session=db_session,
            user_context=user2_context
        )
        
        # Act - execute agents concurrently with state isolation
        from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
        
        user1_exec_context = AgentExecutionContext(
            agent_name="cost_optimizer",
            run_id=uuid.uuid4(),
            thread_id=user1_context.thread_id,
            user_id=user1_context.user_id
        )
        
        user2_exec_context = AgentExecutionContext(
            agent_name="cost_optimizer", 
            run_id=uuid.uuid4(),
            thread_id=user2_context.thread_id,
            user_id=user2_context.user_id
        )
        
        # Execute both agents concurrently
        user1_result, user2_result = await asyncio.gather(
            execution_core1.execute_agent(user1_exec_context, user1_state),
            execution_core2.execute_agent(user2_exec_context, user2_state),
            return_exceptions=True
        )
        
        # Assert - verify agent execution state isolation
        assert not isinstance(user1_result, Exception), f"User1 agent execution failed: {user1_result}"
        assert not isinstance(user2_result, Exception), f"User2 agent execution failed: {user2_result}"
        
        assert user1_result.success == True
        assert user2_result.success == True
        
        # Verify user-specific results
        user1_data = user1_result.data
        user2_data = user2_result.data
        
        assert user1_data["user_id"] == user1_context.user_id
        assert user2_data["user_id"] == user2_context.user_id
        
        # Verify user-specific business logic was applied
        assert user1_data["account_type"] == "enterprise"
        assert user2_data["account_type"] == "startup"
        
        assert user1_data["analysis_depth"] == "comprehensive"  
        assert user2_data["analysis_depth"] == "basic"
        
        assert user1_data["threshold"] == 10000
        assert user2_data["threshold"] == 1000
        
        # Verify recommendations are user-specific
        user1_recs = user1_data["recommendations"]
        user2_recs = user2_data["recommendations"]
        
        assert "advanced_reserved_instances" in user1_recs
        assert "advanced_reserved_instances" not in user2_recs
        
        assert "spot_instances" in user2_recs
        assert "spot_instances" not in user1_recs
        
        # Critical: Verify complete isolation - no data leakage
        assert user1_data["user_id"] != user2_data["user_id"]
        assert user1_result.thread_id != user2_result.thread_id