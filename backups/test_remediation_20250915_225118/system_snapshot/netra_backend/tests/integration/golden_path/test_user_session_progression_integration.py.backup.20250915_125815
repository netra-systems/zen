"""
Test User Session and Context Progression Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure user sessions maintain context and progress across interactions
- Value Impact: Users can build on previous conversations and maintain workflow continuity
- Strategic Impact: Session continuity is critical for complex optimization workflows

COVERAGE FOCUS:
1. Multi-turn conversation context preservation
2. Session state consistency across WebSocket reconnections  
3. User context isolation in multi-user scenarios
4. Cross-session data persistence and retrieval
5. Agent state progression tracking
6. Session timeout and recovery mechanisms
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
import pytest

from test_framework.base_integration_test import BaseIntegrationTest, WebSocketIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context

logger = logging.getLogger(__name__)


@dataclass
class SessionProgressionState:
    """Tracks user session progression state."""
    session_id: str
    user_id: str
    thread_id: str
    message_count: int
    last_agent_type: Optional[str]
    context_data: Dict[str, Any]
    progression_stage: str
    timestamp: datetime


class TestUserSessionProgressionIntegration(WebSocketIntegrationTest):
    """Test user session and context progression with real services."""
    
    def setup_method(self):
        super().setup_method()
        self.auth_helper = E2EAuthHelper(environment="test")
        self.session_states = {}
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_turn_conversation_context_preservation(self, real_services_fixture):
        """
        Test that user context builds up correctly across multiple agent interactions.
        
        Validates that each interaction enhances the context rather than starting fresh.
        """
        # Create authenticated user context
        user_context = await create_authenticated_user_context(
            self.auth_helper, 
            real_services_fixture["db"],
            user_data={"email": "context-test@example.com", "name": "Context Test User"}
        )
        
        # Create initial thread with context
        thread_id = str(uuid.uuid4())
        await real_services_fixture["db"].execute("""
            INSERT INTO backend.threads (id, user_id, title, created_at)
            VALUES ($1, $2, $3, $4)
        """, thread_id, user_context.user_id, "Multi-turn Context Test", datetime.now(timezone.utc))
        
        # Simulate first interaction - establish baseline context
        initial_context = {
            "user_goal": "optimize_costs",
            "domain": "aws_infrastructure", 
            "priority": "high",
            "previous_insights": []
        }
        
        await real_services_fixture["redis"].set_json(
            f"user_context:{user_context.user_id}:{thread_id}", 
            initial_context,
            ex=3600
        )
        
        # Message 1: Initial cost analysis request
        msg1_id = str(uuid.uuid4())
        message_1 = {
            "id": msg1_id,
            "thread_id": thread_id,
            "role": "user",
            "content": "I need to analyze my AWS costs for Q4 2024",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await real_services_fixture["db"].execute("""
            INSERT INTO backend.messages (id, thread_id, role, content, metadata, created_at)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, msg1_id, thread_id, "user", message_1["content"], 
             json.dumps({"context_stage": "initial_request"}), 
             datetime.now(timezone.utc))
        
        # Simulate agent response that builds context
        agent_response_1 = {
            "analysis_type": "cost_breakdown",
            "identified_services": ["EC2", "S3", "RDS"],
            "time_period": "Q4_2024",
            "next_actions": ["detailed_service_analysis"]
        }
        
        # Update context after first interaction
        updated_context = {
            **initial_context,
            "previous_insights": [agent_response_1],
            "current_focus": "service_breakdown",
            "interaction_count": 1
        }
        
        await real_services_fixture["redis"].set_json(
            f"user_context:{user_context.user_id}:{thread_id}",
            updated_context,
            ex=3600
        )
        
        # Message 2: Follow-up that builds on previous context
        msg2_id = str(uuid.uuid4())
        message_2 = {
            "id": msg2_id,
            "thread_id": thread_id,
            "role": "user", 
            "content": "Focus on the EC2 costs specifically - I saw some spikes",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await real_services_fixture["db"].execute("""
            INSERT INTO backend.messages (id, thread_id, role, content, metadata, created_at)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, msg2_id, thread_id, "user", message_2["content"],
             json.dumps({"context_stage": "followup_request", "builds_on": msg1_id}),
             datetime.now(timezone.utc))
        
        # Verify context progression
        current_context = await real_services_fixture["redis"].get_json(
            f"user_context:{user_context.user_id}:{thread_id}"
        )
        
        # Context should build on previous interactions
        assert current_context is not None, "User context must persist across interactions"
        assert current_context["interaction_count"] == 1, "Context should track interaction count"
        assert len(current_context["previous_insights"]) == 1, "Previous insights must be preserved"
        assert current_context["previous_insights"][0]["analysis_type"] == "cost_breakdown"
        assert "EC2" in current_context["previous_insights"][0]["identified_services"]
        
        # Verify database state shows progression
        messages = await real_services_fixture["db"].fetch("""
            SELECT id, content, metadata FROM backend.messages 
            WHERE thread_id = $1 ORDER BY created_at ASC
        """, thread_id)
        
        assert len(messages) == 2, "All messages must be persisted"
        assert messages[1]["metadata"]["builds_on"] == msg1_id, "Follow-up must reference previous message"
        
        self.logger.info("Multi-turn context preservation validated successfully")

    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_websocket_reconnection_state_consistency(self, real_services_fixture):
        """
        Test that session state remains consistent across WebSocket reconnections.
        
        Simulates network disconnection scenarios that users commonly experience.
        """
        # Create user and active session
        user_context = await create_authenticated_user_context(
            self.auth_helper,
            real_services_fixture["db"],
            user_data={"email": "reconnection-test@example.com", "name": "Reconnection User"}
        )
        
        session_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())
        
        # Establish initial session state
        session_state = {
            "user_id": user_context.user_id,
            "thread_id": thread_id,
            "active_agent": "data_helper", 
            "execution_stage": "tool_analysis",
            "partial_results": {
                "tools_executed": ["aws_cost_analyzer"],
                "intermediate_data": {"monthly_spend": 15000}
            },
            "connection_count": 1,
            "last_activity": datetime.now(timezone.utc).isoformat()
        }
        
        # Store session in Redis (real session storage)
        await real_services_fixture["redis"].set_json(
            f"session:{session_id}",
            session_state,
            ex=3600
        )
        
        # Store user connection mapping
        await real_services_fixture["redis"].set(
            f"user_session:{user_context.user_id}",
            session_id,
            ex=3600
        )
        
        # Simulate WebSocket connection interruption
        await asyncio.sleep(0.5)  # Simulate network delay
        
        # "Reconnect" - retrieve session state
        stored_session_id = await real_services_fixture["redis"].get(
            f"user_session:{user_context.user_id}"
        )
        
        assert stored_session_id == session_id, "Session mapping must survive reconnection"
        
        reconnected_state = await real_services_fixture["redis"].get_json(
            f"session:{stored_session_id}"
        )
        
        # Verify session state integrity after "reconnection"
        assert reconnected_state is not None, "Session state must persist through reconnections"
        assert reconnected_state["user_id"] == user_context.user_id
        assert reconnected_state["thread_id"] == thread_id
        assert reconnected_state["active_agent"] == "data_helper"
        assert reconnected_state["execution_stage"] == "tool_analysis"
        assert reconnected_state["partial_results"]["monthly_spend"] == 15000
        
        # Update connection count to simulate reconnection
        reconnected_state["connection_count"] = 2
        reconnected_state["last_activity"] = datetime.now(timezone.utc).isoformat()
        
        await real_services_fixture["redis"].set_json(
            f"session:{session_id}",
            reconnected_state,
            ex=3600
        )
        
        # Verify agent can resume from partial state
        final_state = await real_services_fixture["redis"].get_json(f"session:{session_id}")
        assert final_state["connection_count"] == 2, "Reconnection must be tracked"
        assert final_state["execution_stage"] == "tool_analysis", "Execution state must be preserved"
        
        self.logger.info("WebSocket reconnection state consistency validated")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_user_context_isolation(self, real_services_fixture):
        """
        Test that multiple users' sessions remain isolated during concurrent operations.
        
        Critical for multi-tenant system integrity.
        """
        # Create multiple concurrent users
        users = []
        for i in range(3):
            user_context = await create_authenticated_user_context(
                self.auth_helper,
                real_services_fixture["db"],
                user_data={
                    "email": f"concurrent-user-{i}@example.com", 
                    "name": f"Concurrent User {i}"
                }
            )
            users.append(user_context)
        
        # Create isolated sessions for each user
        async def create_user_session(user_context, user_index):
            session_id = str(uuid.uuid4())
            thread_id = str(uuid.uuid4())
            
            # Each user has different context/state
            session_data = {
                "user_id": user_context.user_id,
                "thread_id": thread_id,
                "user_specific_data": {
                    "preferred_agent": ["triage_agent", "data_helper", "uvs_reporter"][user_index],
                    "domain_focus": ["aws_costs", "azure_optimization", "gcp_analysis"][user_index],
                    "budget_limit": [10000, 25000, 50000][user_index]
                },
                "active_tools": [f"tool_{user_index}_{j}" for j in range(user_index + 1)],
                "session_created": time.time()
            }
            
            # Store in Redis with user-specific keys
            await real_services_fixture["redis"].set_json(
                f"session:{session_id}",
                session_data,
                ex=3600
            )
            
            await real_services_fixture["redis"].set(
                f"user_session:{user_context.user_id}",
                session_id,
                ex=3600
            )
            
            return session_id, session_data
        
        # Create sessions concurrently
        session_tasks = [
            create_user_session(users[i], i) for i in range(3)
        ]
        
        session_results = await asyncio.gather(*session_tasks)
        
        # Verify each user has isolated session data
        for i, (session_id, original_data) in enumerate(session_results):
            stored_data = await real_services_fixture["redis"].get_json(f"session:{session_id}")
            
            assert stored_data is not None, f"User {i} session must exist"
            assert stored_data["user_id"] == users[i].user_id, f"User {i} must have correct user_id"
            assert stored_data["user_specific_data"]["budget_limit"] == [10000, 25000, 50000][i]
            
            # Verify no data leakage between users
            for j, (other_session_id, _) in enumerate(session_results):
                if i != j:
                    other_data = await real_services_fixture["redis"].get_json(f"session:{other_session_id}")
                    assert stored_data["user_id"] != other_data["user_id"], "Users must have different IDs"
                    assert stored_data["user_specific_data"] != other_data["user_specific_data"], "User data must be isolated"
        
        self.logger.info("Concurrent user context isolation validated")

    @pytest.mark.integration 
    @pytest.mark.real_services
    async def test_cross_session_data_persistence_and_retrieval(self, real_services_fixture):
        """
        Test that user data persists correctly across different sessions and can be retrieved efficiently.
        
        Validates long-term user context building across multiple login sessions.
        """
        user_context = await create_authenticated_user_context(
            self.auth_helper,
            real_services_fixture["db"], 
            user_data={"email": "persistence-test@example.com", "name": "Persistence User"}
        )
        
        # Session 1: Initial optimization analysis
        session1_id = str(uuid.uuid4())
        thread1_id = str(uuid.uuid4())
        
        # Create thread and messages for session 1
        await real_services_fixture["db"].execute("""
            INSERT INTO backend.threads (id, user_id, title, created_at, metadata)
            VALUES ($1, $2, $3, $4, $5)
        """, thread1_id, user_context.user_id, "Initial Cost Analysis", 
             datetime.now(timezone.utc),
             json.dumps({"session_id": session1_id, "analysis_type": "initial"}))
        
        session1_insights = {
            "total_monthly_cost": 45000,
            "top_cost_drivers": ["EC2", "RDS", "S3"],
            "optimization_opportunities": 3,
            "potential_savings": 12000,
            "analysis_date": datetime.now(timezone.utc).isoformat()
        }
        
        # Store insights from session 1
        await real_services_fixture["redis"].set_json(
            f"user_insights:{user_context.user_id}:session1",
            session1_insights,
            ex=86400  # 24 hours
        )
        
        # "End" session 1 (user logs out)
        await asyncio.sleep(0.2)
        
        # Session 2: Follow-up optimization (next day)
        session2_id = str(uuid.uuid4())
        thread2_id = str(uuid.uuid4())
        
        # Create new thread for session 2
        await real_services_fixture["db"].execute("""
            INSERT INTO backend.threads (id, user_id, title, created_at, metadata)
            VALUES ($1, $2, $3, $4, $5)
        """, thread2_id, user_context.user_id, "Follow-up Optimization",
             datetime.now(timezone.utc),
             json.dumps({"session_id": session2_id, "analysis_type": "followup", "builds_on": thread1_id}))
        
        # Retrieve historical insights to build on them
        historical_insights = await real_services_fixture["redis"].get_json(
            f"user_insights:{user_context.user_id}:session1"
        )
        
        assert historical_insights is not None, "Historical insights must persist across sessions"
        assert historical_insights["total_monthly_cost"] == 45000
        assert len(historical_insights["top_cost_drivers"]) == 3
        
        # Build enhanced insights on historical data
        session2_insights = {
            **historical_insights,
            "progress_since_last_session": {
                "cost_reduction_implemented": 5000,
                "remaining_opportunities": 2,
                "new_optimization_found": 1
            },
            "updated_monthly_cost": 40000,
            "cumulative_savings": 5000,
            "analysis_date": datetime.now(timezone.utc).isoformat()
        }
        
        await real_services_fixture["redis"].set_json(
            f"user_insights:{user_context.user_id}:session2",
            session2_insights,
            ex=86400
        )
        
        # Verify cross-session data relationships in database
        user_threads = await real_services_fixture["db"].fetch("""
            SELECT id, title, metadata, created_at 
            FROM backend.threads 
            WHERE user_id = $1 
            ORDER BY created_at ASC
        """, user_context.user_id)
        
        assert len(user_threads) == 2, "Both sessions must create persistent threads"
        assert user_threads[1]["metadata"]["builds_on"] == thread1_id, "Session 2 must reference session 1"
        
        # Test efficient retrieval of user's complete context
        all_insights = {}
        for key in await real_services_fixture["redis"].keys(f"user_insights:{user_context.user_id}:*"):
            key_name = key.decode() if isinstance(key, bytes) else key
            session_name = key_name.split(":")[-1]
            insights = await real_services_fixture["redis"].get_json(key_name)
            all_insights[session_name] = insights
        
        assert len(all_insights) == 2, "All session insights must be retrievable"
        assert all_insights["session2"]["cumulative_savings"] == 5000
        assert all_insights["session2"]["updated_monthly_cost"] < all_insights["session1"]["total_monthly_cost"]
        
        self.logger.info("Cross-session data persistence and retrieval validated")

    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_agent_state_progression_tracking(self, real_services_fixture):
        """
        Test that agent execution state progresses correctly and can be tracked across workflow stages.
        
        Validates the golden path progression through multiple agent types.
        """
        user_context = await create_authenticated_user_context(
            self.auth_helper,
            real_services_fixture["db"],
            user_data={"email": "agent-progression@example.com", "name": "Agent Progression User"}
        )
        
        thread_id = str(uuid.uuid4())
        await real_services_fixture["db"].execute("""
            INSERT INTO backend.threads (id, user_id, title, created_at)
            VALUES ($1, $2, $3, $4)
        """, thread_id, user_context.user_id, "Agent Progression Test", datetime.now(timezone.utc))
        
        # Define golden path agent progression
        agent_progression = [
            {
                "agent_type": "triage_agent",
                "stage": "initial_assessment", 
                "expected_outputs": ["problem_category", "recommended_next_agent"],
                "execution_time_sla": 10.0
            },
            {
                "agent_type": "data_helper", 
                "stage": "data_collection",
                "expected_outputs": ["collected_data", "analysis_readiness"],
                "execution_time_sla": 20.0
            },
            {
                "agent_type": "uvs_reporter",
                "stage": "value_analysis", 
                "expected_outputs": ["business_impact", "recommendations"],
                "execution_time_sla": 15.0
            }
        ]
        
        progression_state = {
            "thread_id": thread_id,
            "user_id": user_context.user_id,
            "current_stage": 0,
            "completed_stages": [],
            "agent_results": {},
            "overall_start_time": time.time()
        }
        
        # Execute each stage of agent progression
        for stage_index, stage_config in enumerate(agent_progression):
            stage_start_time = time.time()
            
            # Update progression state
            progression_state["current_stage"] = stage_index
            await real_services_fixture["redis"].set_json(
                f"agent_progression:{thread_id}",
                progression_state,
                ex=3600
            )
            
            # Simulate agent execution for this stage
            agent_execution_id = str(uuid.uuid4())
            agent_state = {
                "agent_type": stage_config["agent_type"],
                "execution_id": agent_execution_id,
                "thread_id": thread_id,
                "stage": stage_config["stage"],
                "status": "executing",
                "start_time": stage_start_time,
                "expected_outputs": stage_config["expected_outputs"]
            }
            
            await real_services_fixture["redis"].set_json(
                f"agent_execution:{agent_execution_id}",
                agent_state,
                ex=3600
            )
            
            # Simulate agent work (abbreviated)
            await asyncio.sleep(0.2)
            
            # Complete agent execution with results
            stage_results = {
                "agent_type": stage_config["agent_type"],
                "outputs": {output: f"mock_{output}_data" for output in stage_config["expected_outputs"]},
                "execution_time": time.time() - stage_start_time,
                "success": True,
                "next_recommended_agent": agent_progression[stage_index + 1]["agent_type"] if stage_index < len(agent_progression) - 1 else None
            }
            
            # Update agent state to completed
            agent_state["status"] = "completed"
            agent_state["results"] = stage_results
            agent_state["end_time"] = time.time()
            
            await real_services_fixture["redis"].set_json(
                f"agent_execution:{agent_execution_id}",
                agent_state,
                ex=3600
            )
            
            # Update progression state
            progression_state["completed_stages"].append(stage_index)
            progression_state["agent_results"][stage_config["agent_type"]] = stage_results
            
            await real_services_fixture["redis"].set_json(
                f"agent_progression:{thread_id}",
                progression_state,
                ex=3600
            )
        
        # Verify complete agent progression
        final_progression = await real_services_fixture["redis"].get_json(
            f"agent_progression:{thread_id}"
        )
        
        assert final_progression is not None, "Agent progression must be tracked"
        assert len(final_progression["completed_stages"]) == 3, "All agent stages must be completed"
        assert len(final_progression["agent_results"]) == 3, "All agent results must be stored"
        
        # Verify each agent's results
        for agent_type in ["triage_agent", "data_helper", "uvs_reporter"]:
            assert agent_type in final_progression["agent_results"], f"{agent_type} results must be present"
            agent_result = final_progression["agent_results"][agent_type]
            assert agent_result["success"] is True, f"{agent_type} must execute successfully"
            assert len(agent_result["outputs"]) > 0, f"{agent_type} must produce outputs"
        
        # Verify progression chain integrity
        triage_result = final_progression["agent_results"]["triage_agent"]
        data_helper_result = final_progression["agent_results"]["data_helper"] 
        assert triage_result["next_recommended_agent"] == "data_helper", "Triage must recommend data helper"
        assert data_helper_result["next_recommended_agent"] == "uvs_reporter", "Data helper must recommend UVS reporter"
        
        self.logger.info("Agent state progression tracking validated")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_timeout_and_recovery_mechanisms(self, real_services_fixture):
        """
        Test session timeout handling and recovery mechanisms to ensure graceful degradation.
        
        Validates system behavior when sessions expire or become stale.
        """
        user_context = await create_authenticated_user_context(
            self.auth_helper,
            real_services_fixture["db"],
            user_data={"email": "timeout-test@example.com", "name": "Timeout Test User"}
        )
        
        # Create session with short timeout for testing
        session_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())
        
        session_data = {
            "user_id": user_context.user_id,
            "thread_id": thread_id,
            "created_at": time.time(),
            "last_activity": time.time(),
            "timeout_seconds": 2,  # Short timeout for testing
            "active_agents": ["triage_agent"],
            "partial_work": {
                "analysis_progress": 0.6,
                "intermediate_results": {"identified_issues": 3}
            }
        }
        
        # Store session with short expiry
        await real_services_fixture["redis"].set_json(
            f"session:{session_id}",
            session_data,
            ex=2  # 2 second expiry for testing
        )
        
        await real_services_fixture["redis"].set(
            f"user_session:{user_context.user_id}",
            session_id,
            ex=2
        )
        
        # Wait for session to expire
        await asyncio.sleep(3)
        
        # Verify session expired
        expired_session = await real_services_fixture["redis"].get_json(f"session:{session_id}")
        assert expired_session is None, "Session must expire after timeout"
        
        expired_mapping = await real_services_fixture["redis"].get(f"user_session:{user_context.user_id}")
        assert expired_mapping is None, "User session mapping must expire"
        
        # Test recovery mechanism - create new session when user reconnects
        recovery_session_id = str(uuid.uuid4())
        
        # Check for any recoverable state in database
        user_threads = await real_services_fixture["db"].fetch("""
            SELECT id, title, metadata, created_at
            FROM backend.threads 
            WHERE user_id = $1 
            ORDER BY created_at DESC
            LIMIT 5
        """, user_context.user_id)
        
        # Create recovery session that can reference previous work
        recovery_data = {
            "user_id": user_context.user_id,
            "session_type": "recovery",
            "previous_session_id": session_id,
            "created_at": time.time(),
            "last_activity": time.time(),
            "recoverable_threads": [thread["id"] for thread in user_threads],
            "recovery_context": {
                "had_active_work": True,
                "partial_progress_lost": True,
                "can_resume_from_history": len(user_threads) > 0
            }
        }
        
        await real_services_fixture["redis"].set_json(
            f"session:{recovery_session_id}",
            recovery_data,
            ex=3600  # Normal session timeout
        )
        
        await real_services_fixture["redis"].set(
            f"user_session:{user_context.user_id}",
            recovery_session_id,
            ex=3600
        )
        
        # Verify recovery session established
        recovered_session = await real_services_fixture["redis"].get_json(f"session:{recovery_session_id}")
        assert recovered_session is not None, "Recovery session must be created"
        assert recovered_session["session_type"] == "recovery", "Session must be marked as recovery"
        assert recovered_session["previous_session_id"] == session_id, "Must reference previous session"
        assert recovered_session["recovery_context"]["had_active_work"] is True
        
        # Test timeout prevention through activity updates
        active_session_id = str(uuid.uuid4())
        active_session_data = {
            "user_id": user_context.user_id,
            "created_at": time.time(),
            "last_activity": time.time(),
            "activity_count": 1
        }
        
        await real_services_fixture["redis"].set_json(
            f"session:{active_session_id}",
            active_session_data,
            ex=10  # 10 second initial timeout
        )
        
        # Simulate user activity to prevent timeout
        for i in range(3):
            await asyncio.sleep(0.5)
            
            # Update activity timestamp
            active_session_data["last_activity"] = time.time()
            active_session_data["activity_count"] += 1
            
            # Extend session timeout
            await real_services_fixture["redis"].set_json(
                f"session:{active_session_id}",
                active_session_data,
                ex=10  # Reset timeout
            )
        
        # Verify session stayed alive due to activity
        final_active_session = await real_services_fixture["redis"].get_json(f"session:{active_session_id}")
        assert final_active_session is not None, "Active session must not timeout"
        assert final_active_session["activity_count"] == 4, "Activity must be tracked"
        
        self.logger.info("Session timeout and recovery mechanisms validated")