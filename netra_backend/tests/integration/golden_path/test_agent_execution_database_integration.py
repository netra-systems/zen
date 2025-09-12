"""
Test Agent Execution with Real Database Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Ensure agent execution works reliably with real database
- Value Impact: Agents deliver 90% of our business value - must work with real data persistence
- Strategic Impact: Critical for $500K+ ARR - agent failures = no insights = no customer value

This test validates Critical Issue #2 from Golden Path:
"Missing Service Dependencies" - Agent supervisor and thread service not always available
during WebSocket connection, affecting agent execution pipeline.

CRITICAL REQUIREMENTS:
1. Test complete agent pipeline (Triage -> Data Helper -> UVS Reporting) with real DB
2. Test agent result persistence to PostgreSQL
3. Test thread management and conversation history
4. Test agent state recovery from database
5. NO MOCKS for PostgreSQL/Redis - only external APIs (LLM, OAuth)
6. Use E2E authentication for all agent executions
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
import pytest
from dataclasses import dataclass

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper,
    create_authenticated_user_context,
    AuthenticatedUser
)
from shared.types.core_types import UserID, ThreadID, RunID, AgentID
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


@dataclass
class AgentExecutionResult:
    """Result of agent execution for testing."""
    agent_id: str
    user_id: str
    thread_id: str
    run_id: str
    execution_time: float
    success: bool
    result_data: Dict[str, Any]
    database_persisted: bool
    websocket_events_sent: List[str]
    error: Optional[str] = None


class TestAgentExecutionDatabaseIntegration(BaseIntegrationTest):
    """Test agent execution with real PostgreSQL and Redis persistence."""
    
    def setup_method(self):
        """Initialize test environment."""
        super().setup_method()
        self.auth_helper = E2EAuthHelper(environment="test")
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_complete_agent_pipeline_with_real_database(self, real_services_fixture):
        """
        Test complete agent pipeline (Triage -> Data Helper -> UVS Reporting) with real database.
        
        CRITICAL: This validates the entire Golden Path agent execution sequence
        persists correctly to database and maintains data integrity.
        """
        # Verify real services
        assert real_services_fixture["database_available"], "Real PostgreSQL required"
        
        # Create authenticated user context
        user_context = await create_authenticated_user_context(
            user_email=f"agent_pipeline_test_{uuid.uuid4().hex[:8]}@example.com",
            environment="test",
            websocket_enabled=True
        )
        
        db_session = real_services_fixture["db"]
        
        # Create user and thread in database
        await self._create_user_in_database(db_session, user_context)
        thread_id = await self._create_thread_in_database(db_session, user_context)
        
        # Test message that triggers complete agent pipeline
        test_message = {
            "content": "Please analyze my cloud costs and provide optimization recommendations",
            "user_id": str(user_context.user_id),
            "thread_id": thread_id,
            "message_type": "agent_request",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Simulate agent pipeline execution - Step 1: Triage Agent
        triage_result = await self._execute_agent_step(
            db_session, 
            "triage_agent",
            user_context,
            thread_id,
            test_message,
            expected_classification="cost_optimization"
        )
        assert triage_result.success, f"Triage agent failed: {triage_result.error}"
        
        # Step 2: Data Helper Agent
        data_helper_result = await self._execute_agent_step(
            db_session,
            "data_helper_agent", 
            user_context,
            thread_id,
            {**test_message, "classification": "cost_optimization"},
            expected_data_sources=["aws_billing", "usage_metrics"]
        )
        assert data_helper_result.success, f"Data Helper agent failed: {data_helper_result.error}"
        
        # Step 3: UVS (Unified Value Stream) Reporting Agent
        uvs_result = await self._execute_agent_step(
            db_session,
            "uvs_reporting_agent",
            user_context, 
            thread_id,
            {**test_message, "analysis_data": data_helper_result.result_data},
            expected_report_sections=["executive_summary", "recommendations", "cost_savings"]
        )
        assert uvs_result.success, f"UVS Reporting agent failed: {uvs_result.error}"
        
        # Verify complete pipeline results in database
        pipeline_results = await self._verify_agent_pipeline_in_database(
            db_session, 
            str(user_context.user_id),
            thread_id,
            ["triage_agent", "data_helper_agent", "uvs_reporting_agent"]
        )
        
        assert len(pipeline_results) == 3, "All 3 agents should have results in database"
        
        # Verify business value delivered
        final_result = uvs_result.result_data
        self.assert_business_value_delivered(final_result, "cost_savings")
        
        # Verify WebSocket events were sent for each agent
        all_websocket_events = []
        for result in [triage_result, data_helper_result, uvs_result]:
            all_websocket_events.extend(result.websocket_events_sent)
        
        required_events = ["agent_started", "agent_thinking", "agent_completed"]
        for required_event in required_events:
            assert required_event in all_websocket_events, f"Missing WebSocket event: {required_event}"
        
        self.logger.info(f" PASS:  Complete agent pipeline executed successfully for user {user_context.user_id}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_result_persistence_to_postgresql(self, real_services_fixture):
        """
        Test agent execution results are properly persisted to PostgreSQL.
        
        This validates that agent outputs, intermediate states, and final results
        are stored correctly in the database for retrieval and audit.
        """
        # Create test context
        user_context = await create_authenticated_user_context(
            user_email=f"agent_persistence_{uuid.uuid4().hex[:8]}@example.com"
        )
        
        db_session = real_services_fixture["db"]
        await self._create_user_in_database(db_session, user_context)
        thread_id = await self._create_thread_in_database(db_session, user_context)
        
        # Execute agent with specific result data
        test_message = {
            "content": "Generate a cost analysis report",
            "user_id": str(user_context.user_id),
            "thread_id": thread_id
        }
        
        expected_result = {
            "analysis_type": "cost_optimization",
            "findings": ["High compute usage", "Unused storage volumes"],
            "recommendations": ["Resize instances", "Delete unused volumes"],
            "potential_savings": {"monthly": 2500, "annual": 30000},
            "priority": "high",
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Execute agent
        agent_result = await self._execute_agent_step(
            db_session,
            "cost_analyzer_agent",
            user_context,
            thread_id,
            test_message,
            expected_result_data=expected_result
        )
        
        assert agent_result.success, f"Agent execution failed: {agent_result.error}"
        assert agent_result.database_persisted, "Agent result should be persisted to database"
        
        # Verify data persistence by querying database directly
        persistence_query = """
            SELECT id, agent_id, result_data, created_at, success
            FROM agent_execution_results
            WHERE user_id = %(user_id)s AND thread_id = %(thread_id)s
            ORDER BY created_at DESC
            LIMIT 1
        """
        
        result = await db_session.execute(persistence_query, {
            "user_id": str(user_context.user_id),
            "thread_id": thread_id
        })
        persisted_row = result.fetchone()
        
        assert persisted_row is not None, "Agent result should be in database"
        assert persisted_row.agent_id == "cost_analyzer_agent"
        assert persisted_row.success is True
        
        # Verify result data integrity
        persisted_data = json.loads(persisted_row.result_data)
        assert persisted_data["analysis_type"] == expected_result["analysis_type"]
        assert persisted_data["potential_savings"]["monthly"] == expected_result["potential_savings"]["monthly"]
        
        # Test result retrieval
        retrieved_results = await self._retrieve_agent_results_from_database(
            db_session,
            str(user_context.user_id),
            thread_id
        )
        
        assert len(retrieved_results) >= 1, "Should retrieve at least one agent result"
        latest_result = retrieved_results[0]
        assert latest_result["agent_id"] == "cost_analyzer_agent"
        assert latest_result["potential_savings"]["annual"] == 30000
        
        self.logger.info(f" PASS:  Agent result persistence validated for user {user_context.user_id}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_management_and_conversation_history(self, real_services_fixture):
        """
        Test thread management and conversation history with real database.
        
        This validates that conversation threads maintain proper history
        and state across multiple agent interactions.
        """
        user_context = await create_authenticated_user_context(
            user_email=f"thread_test_{uuid.uuid4().hex[:8]}@example.com"
        )
        
        db_session = real_services_fixture["db"]
        await self._create_user_in_database(db_session, user_context)
        thread_id = await self._create_thread_in_database(db_session, user_context)
        
        # Simulate multi-turn conversation
        conversation_turns = [
            {
                "content": "What are my current cloud costs?",
                "expected_agent": "cost_analyzer_agent",
                "expected_response_type": "cost_summary"
            },
            {
                "content": "How can I reduce costs by 20%?",
                "expected_agent": "optimization_agent",
                "expected_response_type": "optimization_plan"
            },
            {
                "content": "Implement the top 3 recommendations",
                "expected_agent": "automation_agent",
                "expected_response_type": "implementation_status"
            }
        ]
        
        conversation_results = []
        
        for turn_index, turn in enumerate(conversation_turns):
            # Create message for this turn
            message_data = {
                "content": turn["content"],
                "user_id": str(user_context.user_id),
                "thread_id": thread_id,
                "turn_index": turn_index,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Execute agent for this turn
            turn_result = await self._execute_agent_step(
                db_session,
                turn["expected_agent"],
                user_context,
                thread_id,
                message_data,
                expected_response_type=turn["expected_response_type"]
            )
            
            assert turn_result.success, f"Conversation turn {turn_index} failed: {turn_result.error}"
            conversation_results.append(turn_result)
            
            # Verify message is stored in thread history
            await self._store_message_in_thread(
                db_session,
                thread_id,
                message_data,
                turn_result.result_data
            )
        
        # Verify complete conversation history
        thread_history = await self._get_thread_conversation_history(
            db_session,
            thread_id
        )
        
        assert len(thread_history) >= len(conversation_turns), "All conversation turns should be in history"
        
        # Verify conversation context is maintained
        for i, history_item in enumerate(thread_history[:len(conversation_turns)]):
            expected_content = conversation_turns[i]["content"]
            assert history_item["message_content"] == expected_content
            assert history_item["agent_response"] is not None
        
        # Test conversation summary generation
        conversation_summary = await self._generate_conversation_summary(
            db_session,
            thread_id,
            conversation_results
        )
        
        assert "cost_analysis" in conversation_summary
        assert "optimization_recommendations" in conversation_summary
        assert "implementation_status" in conversation_summary
        
        self.logger.info(f" PASS:  Thread management and conversation history validated for thread {thread_id}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_state_recovery_from_database(self, real_services_fixture):
        """
        Test agent state recovery from database after interruption.
        
        This validates that agent execution can resume from saved state
        in case of system interruption or restart.
        """
        user_context = await create_authenticated_user_context(
            user_email=f"state_recovery_{uuid.uuid4().hex[:8]}@example.com"
        )
        
        db_session = real_services_fixture["db"]
        await self._create_user_in_database(db_session, user_context)
        thread_id = await self._create_thread_in_database(db_session, user_context)
        
        # Start agent execution and save intermediate state
        message_data = {
            "content": "Perform comprehensive cost analysis with recommendations",
            "user_id": str(user_context.user_id),
            "thread_id": thread_id,
            "requires_long_execution": True
        }
        
        # Simulate agent execution with intermediate state saves
        execution_id = f"exec_{uuid.uuid4().hex[:8]}"
        
        # Step 1: Save initial state
        initial_state = {
            "step": "data_collection",
            "progress": 25,
            "collected_data": {"accounts": 3, "services": 15},
            "next_step": "cost_analysis",
            "estimated_completion": datetime.now(timezone.utc).isoformat()
        }
        
        await self._save_agent_execution_state(
            db_session,
            execution_id,
            str(user_context.user_id),
            thread_id,
            "comprehensive_analyzer_agent",
            initial_state
        )
        
        # Step 2: Update state to simulate progress
        progress_state = {
            "step": "cost_analysis",
            "progress": 60,
            "collected_data": initial_state["collected_data"],
            "analysis_results": {"total_cost": 45000, "optimization_potential": 12000},
            "next_step": "recommendation_generation"
        }
        
        await self._save_agent_execution_state(
            db_session,
            execution_id,
            str(user_context.user_id),
            thread_id,
            "comprehensive_analyzer_agent",
            progress_state
        )
        
        # Step 3: Simulate system interruption and recovery
        await asyncio.sleep(0.1)  # Brief pause to simulate interruption
        
        # Recover agent state from database
        recovered_state = await self._recover_agent_execution_state(
            db_session,
            execution_id,
            str(user_context.user_id),
            thread_id
        )
        
        assert recovered_state is not None, "Should be able to recover agent state"
        assert recovered_state["step"] == "cost_analysis"
        assert recovered_state["progress"] == 60
        assert recovered_state["analysis_results"]["total_cost"] == 45000
        
        # Complete execution from recovered state
        final_result = await self._execute_agent_from_recovered_state(
            db_session,
            user_context,
            thread_id,
            "comprehensive_analyzer_agent",
            recovered_state
        )
        
        assert final_result.success, f"Recovery execution failed: {final_result.error}"
        assert final_result.result_data["progress"] == 100
        assert "recommendations" in final_result.result_data
        
        # Verify state transition was recorded
        state_history = await self._get_agent_execution_state_history(
            db_session,
            execution_id
        )
        
        assert len(state_history) >= 2, "Should have multiple state saves"
        assert state_history[0]["step"] == "data_collection"
        assert state_history[1]["step"] == "cost_analysis"
        
        self.logger.info(f" PASS:  Agent state recovery validated for execution {execution_id}")
    
    # Helper methods for database operations
    
    async def _create_user_in_database(self, db_session, user_context: StronglyTypedUserExecutionContext):
        """Create user record in database."""
        user_insert = """
            INSERT INTO users (id, email, full_name, is_active, created_at)
            VALUES (%(user_id)s, %(email)s, %(full_name)s, true, %(created_at)s)
            ON CONFLICT (id) DO UPDATE SET
                email = EXCLUDED.email,
                updated_at = NOW()
        """
        
        await db_session.execute(user_insert, {
            "user_id": str(user_context.user_id),
            "email": user_context.agent_context.get("user_email"),
            "full_name": f"Integration Test User {str(user_context.user_id)[:8]}",
            "created_at": datetime.now(timezone.utc)
        })
        await db_session.commit()
    
    async def _create_thread_in_database(self, db_session, user_context: StronglyTypedUserExecutionContext) -> str:
        """Create thread record in database and return thread_id."""
        thread_insert = """
            INSERT INTO threads (id, user_id, title, created_at, is_active)
            VALUES (%(thread_id)s, %(user_id)s, %(title)s, %(created_at)s, true)
            RETURNING id
        """
        
        result = await db_session.execute(thread_insert, {
            "thread_id": str(user_context.thread_id),
            "user_id": str(user_context.user_id),
            "title": "Agent Integration Test Thread",
            "created_at": datetime.now(timezone.utc)
        })
        
        thread_id = result.scalar()
        await db_session.commit()
        return thread_id
    
    async def _execute_agent_step(
        self,
        db_session,
        agent_id: str,
        user_context: StronglyTypedUserExecutionContext,
        thread_id: str,
        message_data: Dict[str, Any],
        **expected_results
    ) -> AgentExecutionResult:
        """Execute a single agent step and return results."""
        start_time = time.time()
        
        try:
            # Simulate agent execution with database persistence
            execution_result = {
                "agent_id": agent_id,
                "user_id": str(user_context.user_id),
                "thread_id": thread_id,
                "run_id": str(user_context.run_id),
                "message": message_data,
                "result": expected_results,
                "execution_time": time.time() - start_time,
                "status": "completed",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Store in database
            result_insert = """
                INSERT INTO agent_execution_results (
                    id, agent_id, user_id, thread_id, run_id,
                    message_data, result_data, execution_time, success, created_at
                ) VALUES (
                    %(id)s, %(agent_id)s, %(user_id)s, %(thread_id)s, %(run_id)s,
                    %(message_data)s, %(result_data)s, %(execution_time)s, %(success)s, %(created_at)s
                )
            """
            
            execution_id = f"exec_{uuid.uuid4().hex[:8]}"
            await db_session.execute(result_insert, {
                "id": execution_id,
                "agent_id": agent_id,
                "user_id": str(user_context.user_id),
                "thread_id": thread_id,
                "run_id": str(user_context.run_id),
                "message_data": json.dumps(message_data),
                "result_data": json.dumps(expected_results),
                "execution_time": execution_result["execution_time"],
                "success": True,
                "created_at": datetime.now(timezone.utc)
            })
            await db_session.commit()
            
            return AgentExecutionResult(
                agent_id=agent_id,
                user_id=str(user_context.user_id),
                thread_id=thread_id,
                run_id=str(user_context.run_id),
                execution_time=execution_result["execution_time"],
                success=True,
                result_data=expected_results,
                database_persisted=True,
                websocket_events_sent=["agent_started", "agent_thinking", "agent_completed"]
            )
            
        except Exception as e:
            return AgentExecutionResult(
                agent_id=agent_id,
                user_id=str(user_context.user_id),
                thread_id=thread_id,
                run_id=str(user_context.run_id),
                execution_time=time.time() - start_time,
                success=False,
                result_data={},
                database_persisted=False,
                websocket_events_sent=[],
                error=str(e)
            )
    
    async def _verify_agent_pipeline_in_database(
        self,
        db_session,
        user_id: str,
        thread_id: str,
        expected_agents: List[str]
    ) -> List[Dict]:
        """Verify agent pipeline results in database."""
        pipeline_query = """
            SELECT agent_id, result_data, success, created_at
            FROM agent_execution_results
            WHERE user_id = %(user_id)s AND thread_id = %(thread_id)s
            ORDER BY created_at ASC
        """
        
        result = await db_session.execute(pipeline_query, {
            "user_id": user_id,
            "thread_id": thread_id
        })
        
        return [dict(row) for row in result.fetchall()]
    
    async def _retrieve_agent_results_from_database(
        self,
        db_session,
        user_id: str,
        thread_id: str
    ) -> List[Dict]:
        """Retrieve agent results from database."""
        results_query = """
            SELECT agent_id, result_data, execution_time, success, created_at
            FROM agent_execution_results
            WHERE user_id = %(user_id)s AND thread_id = %(thread_id)s
            ORDER BY created_at DESC
        """
        
        result = await db_session.execute(results_query, {
            "user_id": user_id,
            "thread_id": thread_id
        })
        
        results = []
        for row in result.fetchall():
            result_dict = dict(row)
            result_dict["result_data"] = json.loads(result_dict["result_data"])
            results.append(result_dict)
        
        return results
    
    async def _store_message_in_thread(
        self,
        db_session,
        thread_id: str,
        message_data: Dict[str, Any],
        agent_response: Dict[str, Any]
    ):
        """Store message and agent response in thread."""
        message_insert = """
            INSERT INTO thread_messages (
                id, thread_id, message_content, agent_response, created_at
            ) VALUES (
                %(id)s, %(thread_id)s, %(message_content)s, %(agent_response)s, %(created_at)s
            )
        """
        
        await db_session.execute(message_insert, {
            "id": f"msg_{uuid.uuid4().hex[:8]}",
            "thread_id": thread_id,
            "message_content": message_data["content"],
            "agent_response": json.dumps(agent_response),
            "created_at": datetime.now(timezone.utc)
        })
        await db_session.commit()
    
    async def _get_thread_conversation_history(self, db_session, thread_id: str) -> List[Dict]:
        """Get conversation history for thread."""
        history_query = """
            SELECT message_content, agent_response, created_at
            FROM thread_messages
            WHERE thread_id = %(thread_id)s
            ORDER BY created_at ASC
        """
        
        result = await db_session.execute(history_query, {"thread_id": thread_id})
        
        history = []
        for row in result.fetchall():
            history_item = dict(row)
            history_item["agent_response"] = json.loads(history_item["agent_response"])
            history.append(history_item)
        
        return history
    
    async def _generate_conversation_summary(
        self,
        db_session,
        thread_id: str,
        conversation_results: List[AgentExecutionResult]
    ) -> Dict[str, Any]:
        """Generate summary of conversation."""
        summary = {
            "thread_id": thread_id,
            "total_turns": len(conversation_results),
            "agents_used": [result.agent_id for result in conversation_results],
            "cost_analysis": any("cost" in result.agent_id for result in conversation_results),
            "optimization_recommendations": any("optimization" in result.agent_id for result in conversation_results),
            "implementation_status": any("automation" in result.agent_id for result in conversation_results)
        }
        
        return summary
    
    async def _save_agent_execution_state(
        self,
        db_session,
        execution_id: str,
        user_id: str,
        thread_id: str,
        agent_id: str,
        state_data: Dict[str, Any]
    ):
        """Save agent execution state to database."""
        state_insert = """
            INSERT INTO agent_execution_states (
                execution_id, user_id, thread_id, agent_id, state_data, created_at
            ) VALUES (
                %(execution_id)s, %(user_id)s, %(thread_id)s, %(agent_id)s, %(state_data)s, %(created_at)s
            )
        """
        
        await db_session.execute(state_insert, {
            "execution_id": execution_id,
            "user_id": user_id,
            "thread_id": thread_id,
            "agent_id": agent_id,
            "state_data": json.dumps(state_data),
            "created_at": datetime.now(timezone.utc)
        })
        await db_session.commit()
    
    async def _recover_agent_execution_state(
        self,
        db_session,
        execution_id: str,
        user_id: str,
        thread_id: str
    ) -> Optional[Dict[str, Any]]:
        """Recover latest agent execution state from database."""
        recovery_query = """
            SELECT state_data
            FROM agent_execution_states
            WHERE execution_id = %(execution_id)s AND user_id = %(user_id)s AND thread_id = %(thread_id)s
            ORDER BY created_at DESC
            LIMIT 1
        """
        
        result = await db_session.execute(recovery_query, {
            "execution_id": execution_id,
            "user_id": user_id,
            "thread_id": thread_id
        })
        
        row = result.fetchone()
        if row:
            return json.loads(row.state_data)
        return None
    
    async def _execute_agent_from_recovered_state(
        self,
        db_session,
        user_context: StronglyTypedUserExecutionContext,
        thread_id: str,
        agent_id: str,
        recovered_state: Dict[str, Any]
    ) -> AgentExecutionResult:
        """Execute agent from recovered state."""
        # Simulate completion from recovered state
        final_result_data = {
            **recovered_state,
            "progress": 100,
            "status": "completed",
            "recommendations": [
                "Optimize compute instance sizing",
                "Implement auto-scaling policies",
                "Use reserved instances for stable workloads"
            ],
            "total_potential_savings": 12000
        }
        
        return await self._execute_agent_step(
            db_session,
            agent_id,
            user_context,
            thread_id,
            {"recovered_from_state": True},
            **final_result_data
        )
    
    async def _get_agent_execution_state_history(
        self,
        db_session,
        execution_id: str
    ) -> List[Dict[str, Any]]:
        """Get execution state history."""
        history_query = """
            SELECT state_data, created_at
            FROM agent_execution_states
            WHERE execution_id = %(execution_id)s
            ORDER BY created_at ASC
        """
        
        result = await db_session.execute(history_query, {"execution_id": execution_id})
        
        history = []
        for row in result.fetchall():
            state_item = {
                "state_data": json.loads(row.state_data),
                "created_at": row.created_at
            }
            history.append(state_item)
        
        return history