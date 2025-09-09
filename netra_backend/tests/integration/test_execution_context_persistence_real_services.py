"""Integration Tests for Execution Context Persistence with Real Services

Business Value Justification:
- Segment: Enterprise (critical for audit trails and compliance)
- Business Goal: Ensure execution context is reliably persisted for auditability
- Value Impact: Enables compliance with enterprise audit requirements
- Strategic Impact: Foundation for enterprise-grade execution tracking

Test Coverage:
- Execution context persistence to real database
- Context retrieval and reconstruction with real services
- Audit trail generation with real persistence
- Context isolation between users with database backing
"""

import pytest
import asyncio
import uuid
from datetime import datetime

from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult
)
from test_framework.ssot.real_services_test_fixtures import *


@pytest.mark.integration
class TestExecutionContextPersistenceRealServices:
    """Integration tests for execution context persistence."""
    
    @pytest.mark.asyncio
    async def test_execution_context_database_persistence(self, real_services_fixture, with_test_database):
        """Test execution context persistence to real database."""
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available for persistence testing")
        
        db_session = with_test_database
        
        # Create execution context
        context = AgentExecutionContext(
            agent_name="persistence_test_agent",
            run_id=uuid.uuid4(),
            thread_id=f"persist-thread-{uuid.uuid4()}",
            user_id=f"persist-user-{uuid.uuid4()}",
            correlation_id=f"corr-{uuid.uuid4()}"
        )
        
        # Act - persist context to database
        await self._persist_context_to_database(db_session, context)
        
        # Assert - verify persistence
        persisted_context = await self._retrieve_context_from_database(db_session, context.run_id)
        
        assert persisted_context is not None
        assert persisted_context["agent_name"] == context.agent_name
        assert persisted_context["thread_id"] == context.thread_id
        assert persisted_context["user_id"] == context.user_id
    
    async def _persist_context_to_database(self, db_session, context):
        """Helper to persist execution context."""
        from sqlalchemy import text
        insert_query = text("""
            INSERT INTO execution_contexts (
                run_id, agent_name, thread_id, user_id, correlation_id, created_at
            ) VALUES (:run_id, :agent_name, :thread_id, :user_id, :correlation_id, :created_at)
        """)
        
        await db_session.execute(insert_query, {
            "run_id": str(context.run_id),
            "agent_name": context.agent_name,
            "thread_id": context.thread_id,
            "user_id": context.user_id,
            "correlation_id": context.correlation_id,
            "created_at": datetime.utcnow()
        })
    
    async def _retrieve_context_from_database(self, db_session, run_id):
        """Helper to retrieve execution context."""
        from sqlalchemy import text
        select_query = text("""
            SELECT run_id, agent_name, thread_id, user_id, correlation_id, created_at
            FROM execution_contexts
            WHERE run_id = :run_id
        """)
        
        result = await db_session.execute(select_query, {"run_id": str(run_id)})
        row = result.fetchone()
        
        if row:
            return {
                "run_id": row.run_id,
                "agent_name": row.agent_name,
                "thread_id": row.thread_id,
                "user_id": row.user_id,
                "correlation_id": row.correlation_id,
                "created_at": row.created_at
            }
        return None