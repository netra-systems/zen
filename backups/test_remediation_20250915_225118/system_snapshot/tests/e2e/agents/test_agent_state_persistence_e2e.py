"""E2E Tests for Agent State Persistence - State Saving/Loading Across Requests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - State persistence enables continuous conversations
- Business Goal: Ensure reliable agent conversation continuity and recovery capabilities
- Value Impact: Users experience seamless conversations that persist across sessions and recover from interruptions
- Strategic Impact: $500K+ ARR conversation continuity and reliability foundation

These E2E tests validate agent state persistence with complete system stack:
- Real authentication (JWT/OAuth) with session continuity
- Real WebSocket connections with state synchronization
- Real databases (PostgreSQL, Redis, ClickHouse) with persistent storage
- Agent state saving and loading across multiple requests
- Recovery from interruptions and failures
- Cross-request conversation history preservation
- Real LLM integration with conversation context retention

CRITICAL: ALL E2E tests MUST use authentication - no exceptions.
STAGING ONLY: These tests run against GCP staging environment only.
"""

import pytest
import asyncio
import uuid
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.websocket_helpers import WebSocketTestClient

from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.schemas.agent_models import DeepAgentState
from netra_backend.app.services.state_persistence_optimized import OptimizedStatePersistenceService
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge


@pytest.mark.e2e
class AgentStatePersistenceE2ETests(BaseE2ETest):
    """E2E tests for agent state persistence with authenticated full-stack integration."""

    @pytest.fixture
    async def authenticated_user(self):
        """Create authenticated user for E2E testing."""
        token, user_data = await create_authenticated_user(
            environment="staging",  # GCP staging only
            permissions=["read", "write", "agent_execute", "state_persist"]
        )
        return {
            "token": token,
            "user_data": user_data,
            "user_id": user_data["id"],
            "email": user_data["email"]
        }

    @pytest.fixture
    def auth_helper(self):
        """E2E authentication helper."""
        return E2EAuthHelper(environment="staging")

    @pytest.fixture
    async def websocket_client(self, authenticated_user, auth_helper):
        """Authenticated WebSocket client for E2E testing."""
        headers = auth_helper.get_websocket_headers(authenticated_user["token"])

        # Use staging GCP WebSocket endpoint
        staging_ws_url = "wss://staging.netra-apex.com/ws"
        client = WebSocketTestClient(
            url=staging_ws_url,
            headers=headers
        )
        await client.connect()
        yield client
        await client.disconnect()

    @pytest.fixture
    def state_persistence_service(self):
        """Real state persistence service for testing."""
        return OptimizedStatePersistenceService()

    @pytest.mark.asyncio
    async def test_agent_conversation_state_persistence_across_requests(
        self, authenticated_user, websocket_client, state_persistence_service
    ):
        """Test agent conversation state persistence across multiple requests.

        This test validates:
        - Agent state saving after each conversation turn
        - State loading before each new request
        - Conversation history preservation across sessions
        - Agent memory persistence across requests
        - WebSocket events for state persistence operations
        - Cross-request context continuity
        """
        user_id = authenticated_user["user_id"]
        thread_id = str(uuid.uuid4())

        # Define multi-turn conversation for persistence testing
        conversation_turns = [
            {
                "turn": 1,
                "message": "I'm planning a data analysis project for customer segmentation. Can you help me outline the approach?",
                "expected_context_retention": []  # First turn, no prior context
            },
            {
                "turn": 2,
                "message": "What specific data sources should I focus on for the customer segmentation you mentioned?",
                "expected_context_retention": ["data analysis project", "customer segmentation", "approach"]
            },
            {
                "turn": 3,
                "message": "How do I handle missing values in the demographic data we discussed?",
                "expected_context_retention": ["customer segmentation", "data sources", "demographic data"]
            },
            {
                "turn": 4,
                "message": "Can you create a detailed implementation timeline for everything we've planned?",
                "expected_context_retention": ["segmentation", "data sources", "demographic data", "missing values"]
            }
        ]

        # Track state persistence events
        persistence_events = []

        async def collect_persistence_events():
            """Collect WebSocket events related to state persistence."""
            while True:
                try:
                    event = await websocket_client.receive()
                    if event and any(keyword in str(event).lower() for keyword in ["state", "persistence", "save", "load"]):
                        persistence_events.append({
                            'timestamp': datetime.now(timezone.utc),
                            'event': json.loads(event) if isinstance(event, str) else event
                        })
                except Exception:
                    break

        # Start persistence event collection
        persistence_task = asyncio.create_task(collect_persistence_events())

        # Execute conversation turns with state persistence
        conversation_results = []
        agent_execution_core = AgentExecutionCore()

        try:
            for turn_data in conversation_turns:
                run_id = str(uuid.uuid4())
                turn_number = turn_data["turn"]

                # Load existing state (for turns 2+)
                if turn_number > 1:
                    loaded_state = await state_persistence_service.load_agent_state(
                        user_id=user_id,
                        thread_id=thread_id,
                        include_conversation_history=True,
                        include_agent_memory=True
                    )
                    assert loaded_state is not None, f"Should load state for turn {turn_number}"

                    # Validate context retention from previous turns
                    conversation_history = loaded_state.conversation_history or []
                    history_text = " ".join([msg.get("content", "") for msg in conversation_history]).lower()

                    for expected_context in turn_data["expected_context_retention"]:
                        assert expected_context.lower() in history_text, f"Turn {turn_number}: Expected context '{expected_context}' not found in history"

                    current_state = loaded_state
                else:
                    # Create initial state for first turn
                    current_state = DeepAgentState(
                        user_id=user_id,
                        thread_id=thread_id,
                        conversation_history=[],
                        context={},
                        agent_memory={
                            "conversation_context": {},
                            "project_details": {},
                            "state_persistence_test": True
                        },
                        workflow_state="conversation_active"
                    )

                # Execute agent turn with current state
                execution_result = await agent_execution_core.execute_with_state_persistence(
                    agent_state=current_state,
                    request=turn_data["message"],
                    run_id=run_id,
                    enable_state_saving=True,
                    enable_websocket_events=True
                )

                # Validate execution success
                assert execution_result is not None, f"Turn {turn_number} execution should succeed"
                assert execution_result.get("status") == "completed", f"Turn {turn_number} should complete successfully"

                # Save conversation result
                conversation_results.append({
                    "turn": turn_number,
                    "result": execution_result,
                    "message": turn_data["message"],
                    "timestamp": datetime.now(timezone.utc)
                })

                # Verify state was saved
                final_state = execution_result.get("final_state")
                assert final_state is not None, f"Turn {turn_number} should return final state"

                # Validate conversation history accumulation
                conversation_history = final_state.conversation_history or []
                expected_history_length = turn_number * 2  # User message + agent response per turn
                assert len(conversation_history) >= turn_number, f"Turn {turn_number}: Should accumulate conversation history (got {len(conversation_history)})"

                # Validate agent memory accumulation
                agent_memory = final_state.agent_memory or {}
                assert "conversation_context" in agent_memory, f"Turn {turn_number}: Should maintain conversation context"
                assert "state_persistence_test" in agent_memory, f"Turn {turn_number}: Should maintain test markers"

                # Short delay between turns to simulate real user behavior
                await asyncio.sleep(1.0)

            # Allow time for final persistence events
            await asyncio.sleep(2.0)

        finally:
            persistence_task.cancel()
            try:
                await persistence_task
            except asyncio.CancelledError:
                pass

        # VALIDATION: State persistence across conversation

        # 1. All turns should complete successfully
        successful_turns = [r for r in conversation_results if r["result"].get("status") == "completed"]
        assert len(successful_turns) >= 3, f"At least 3 turns should complete successfully, got {len(successful_turns)}"

        # 2. Validate conversation history growth
        for i, result in enumerate(conversation_results):
            if result["result"].get("status") == "completed":
                final_state = result["result"]["final_state"]
                history_length = len(final_state.conversation_history or [])
                turn_number = result["turn"]

                # History should grow with each turn (at least user message per turn)
                assert history_length >= turn_number, f"Turn {turn_number}: History should grow (got {history_length})"

        # 3. Validate context retention across turns
        if len(successful_turns) >= 2:
            last_turn = successful_turns[-1]
            final_state = last_turn["result"]["final_state"]
            final_response = last_turn["result"].get("final_response", "").lower()

            # Final response should reference earlier conversation elements
            early_turn_concepts = ["data analysis", "customer segmentation", "data sources"]
            concepts_referenced = sum(1 for concept in early_turn_concepts if concept in final_response)
            assert concepts_referenced >= 2, f"Final turn should reference earlier concepts (found {concepts_referenced})"

        # 4. Validate agent memory continuity
        if len(successful_turns) >= 2:
            memory_evolution = []
            for turn_result in successful_turns:
                final_state = turn_result["result"]["final_state"]
                agent_memory = final_state.agent_memory or {}
                memory_evolution.append({
                    "turn": turn_result["turn"],
                    "memory_keys": list(agent_memory.keys()),
                    "context_items": len(agent_memory.get("conversation_context", {}))
                })

            # Memory should accumulate over turns
            for i in range(1, len(memory_evolution)):
                current_context_items = memory_evolution[i]["context_items"]
                previous_context_items = memory_evolution[i-1]["context_items"]
                assert current_context_items >= previous_context_items, f"Agent memory should accumulate across turns"

        # 5. Validate persistence events
        assert len(persistence_events) >= 2, f"Should receive persistence events, got {len(persistence_events)}"

        save_events = [e for e in persistence_events if "save" in str(e.get("event", {})).lower()]
        load_events = [e for e in persistence_events if "load" in str(e.get("event", {})).lower()]

        assert len(save_events) >= 2, f"Should receive state save events, got {len(save_events)}"
        assert len(load_events) >= 1, f"Should receive state load events, got {len(load_events)}"

    @pytest.mark.asyncio
    async def test_agent_recovery_from_interruption_and_state_restoration(
        self, authenticated_user, websocket_client, state_persistence_service
    ):
        """Test agent recovery from interruptions with state restoration.

        This test validates:
        - Agent state saving before interruption/failure
        - State recovery after interruption
        - Conversation continuity after recovery
        - Partial execution state preservation
        - WebSocket events for recovery operations
        - Data integrity after recovery
        """
        user_id = authenticated_user["user_id"]
        thread_id = str(uuid.uuid4())

        # Create complex agent state before interruption
        pre_interruption_state = DeepAgentState(
            user_id=user_id,
            thread_id=thread_id,
            conversation_history=[
                {"role": "user", "content": "Help me build a machine learning pipeline for fraud detection"},
                {"role": "assistant", "content": "I'll help you create a comprehensive fraud detection ML pipeline. Let's start with data collection and feature engineering..."},
                {"role": "user", "content": "What specific features should I focus on for credit card fraud detection?"},
                {"role": "assistant", "content": "For credit card fraud detection, focus on these key features: transaction amount, time patterns, merchant categories, geographic locations..."},
            ],
            context={
                "project_type": "fraud_detection",
                "ml_pipeline_stage": "feature_engineering",
                "data_sources": ["transaction_logs", "user_profiles", "merchant_data"],
                "current_analysis": {
                    "completed_steps": ["data_collection_planning", "feature_identification"],
                    "current_step": "feature_engineering_implementation",
                    "next_steps": ["model_selection", "training", "evaluation"]
                }
            },
            agent_memory={
                "project_state": {
                    "fraud_detection_features": [
                        "transaction_amount",
                        "time_of_day",
                        "day_of_week",
                        "merchant_category",
                        "location_data",
                        "user_spending_patterns"
                    ],
                    "pipeline_components": {
                        "data_ingestion": "in_progress",
                        "feature_engineering": "active",
                        "model_training": "pending",
                        "evaluation": "pending"
                    }
                },
                "conversation_state": "deep_technical_discussion",
                "interruption_test_marker": "pre_interruption_checkpoint"
            },
            workflow_state="feature_engineering_active"
        )

        # Save state before simulated interruption
        run_id_before = str(uuid.uuid4())

        save_result = await state_persistence_service.save_agent_state(
            state=pre_interruption_state,
            run_id=run_id_before,
            checkpoint_type="interruption_test",
            enable_compression=True
        )
        assert save_result.get("status") == "success", "Pre-interruption state save should succeed"

        # Track recovery events
        recovery_events = []

        async def collect_recovery_events():
            """Collect WebSocket events related to recovery operations."""
            while True:
                try:
                    event = await websocket_client.receive()
                    if event and any(keyword in str(event).lower() for keyword in ["recovery", "restore", "interruption", "checkpoint"]):
                        recovery_events.append({
                            'timestamp': datetime.now(timezone.utc),
                            'event': json.loads(event) if isinstance(event, str) else event
                        })
                except Exception:
                    break

        # Start recovery event collection
        recovery_task = asyncio.create_task(collect_recovery_events())

        try:
            # Simulate interruption by waiting and then attempting recovery
            await asyncio.sleep(1.0)

            # Attempt state recovery
            recovered_state = await state_persistence_service.load_agent_state(
                user_id=user_id,
                thread_id=thread_id,
                checkpoint_type="interruption_test",
                include_conversation_history=True,
                include_agent_memory=True,
                enable_recovery_mode=True
            )

            # Validate recovery success
            assert recovered_state is not None, "State recovery should succeed"
            assert recovered_state.user_id == user_id, "Recovered state should maintain user ID"
            assert recovered_state.thread_id == thread_id, "Recovered state should maintain thread ID"

            # Validate conversation history preservation
            recovered_history = recovered_state.conversation_history or []
            original_history = pre_interruption_state.conversation_history or []
            assert len(recovered_history) == len(original_history), "Conversation history should be fully preserved"

            # Validate conversation content preservation
            for i, (original_msg, recovered_msg) in enumerate(zip(original_history, recovered_history)):
                assert original_msg.get("content") == recovered_msg.get("content"), f"Message {i} content should be preserved"
                assert original_msg.get("role") == recovered_msg.get("role"), f"Message {i} role should be preserved"

            # Validate context preservation
            recovered_context = recovered_state.context or {}
            original_context = pre_interruption_state.context or {}
            assert recovered_context.get("project_type") == original_context.get("project_type"), "Project type should be preserved"
            assert recovered_context.get("ml_pipeline_stage") == original_context.get("ml_pipeline_stage"), "Pipeline stage should be preserved"

            # Validate agent memory preservation
            recovered_memory = recovered_state.agent_memory or {}
            original_memory = pre_interruption_state.agent_memory or {}
            assert "interruption_test_marker" in recovered_memory, "Test markers should be preserved"
            assert recovered_memory.get("interruption_test_marker") == "pre_interruption_checkpoint", "Test marker values should be preserved"

            # Validate project state preservation
            recovered_project_state = recovered_memory.get("project_state", {})
            original_project_state = original_memory.get("project_state", {})

            recovered_features = recovered_project_state.get("fraud_detection_features", [])
            original_features = original_project_state.get("fraud_detection_features", [])
            assert len(recovered_features) == len(original_features), "Feature list should be fully preserved"
            assert set(recovered_features) == set(original_features), "All features should be preserved"

            # Test continuation after recovery
            continuation_message = "Now let's implement the feature engineering pipeline for those fraud detection features we discussed"
            run_id_after = str(uuid.uuid4())

            agent_execution_core = AgentExecutionCore()
            continuation_result = await agent_execution_core.execute_with_state_persistence(
                agent_state=recovered_state,
                request=continuation_message,
                run_id=run_id_after,
                enable_state_saving=True,
                recovery_mode=True
            )

            # Validate continuation success
            assert continuation_result is not None, "Post-recovery execution should succeed"
            assert continuation_result.get("status") == "completed", "Post-recovery execution should complete"

            # Validate context continuity in response
            final_response = continuation_result.get("final_response", "").lower()

            # Response should reference pre-interruption context
            pre_interruption_concepts = ["fraud detection", "feature engineering", "transaction", "pipeline"]
            context_references = sum(1 for concept in pre_interruption_concepts if concept in final_response)
            assert context_references >= 2, f"Post-recovery response should reference pre-interruption context (found {context_references})"

            # Validate enhanced state after continuation
            final_state = continuation_result.get("final_state")
            assert final_state is not None, "Should return enhanced final state"

            final_history = final_state.conversation_history or []
            # Should have original history + new user message + new agent response
            expected_min_history_length = len(original_history) + 1
            assert len(final_history) >= expected_min_history_length, f"History should grow after continuation (got {len(final_history)})"

            # Allow time for recovery events
            await asyncio.sleep(1.5)

        finally:
            recovery_task.cancel()
            try:
                await recovery_task
            except asyncio.CancelledError:
                pass

        # VALIDATION: Recovery and restoration

        # 1. Validate recovery events were generated
        assert len(recovery_events) >= 1, f"Should receive recovery events, got {len(recovery_events)}"

        # Check for specific recovery event types
        recovery_event_types = []
        for event_data in recovery_events:
            event = event_data.get("event", {})
            event_type = event.get("type", "").lower()
            if any(keyword in event_type for keyword in ["recovery", "restore", "checkpoint"]):
                recovery_event_types.append(event_type)

        assert len(recovery_event_types) >= 1, f"Should receive recovery-specific events, got {recovery_event_types}"

        # 2. Validate data integrity metrics
        integrity_metrics = {
            "conversation_history_preserved": len(recovered_history) == len(original_history),
            "context_preserved": recovered_context.get("project_type") == original_context.get("project_type"),
            "agent_memory_preserved": "interruption_test_marker" in recovered_memory,
            "workflow_state_preserved": recovered_state.workflow_state == pre_interruption_state.workflow_state
        }

        integrity_score = sum(integrity_metrics.values())
        assert integrity_score >= 3, f"Should maintain high data integrity (score: {integrity_score}/4)"

        # 3. Validate business continuity
        if continuation_result and continuation_result.get("status") == "completed":
            # Continuation should provide meaningful response building on recovered context
            continuation_response = continuation_result.get("final_response", "")
            assert len(continuation_response) >= 100, "Post-recovery response should be substantial"

            # Should reference the specific fraud detection project from recovered state
            business_context_indicators = ["fraud", "detection", "features", "pipeline", "implementation"]
            business_context_count = sum(1 for indicator in business_context_indicators if indicator in continuation_response.lower())
            assert business_context_count >= 3, f"Should maintain business context continuity (found {business_context_count} indicators)"

    @pytest.mark.asyncio
    async def test_cross_session_state_persistence_and_long_term_memory(
        self, authenticated_user, websocket_client, state_persistence_service
    ):
        """Test cross-session state persistence and long-term memory retention.

        This test validates:
        - State persistence across multiple disconnected sessions
        - Long-term memory retention beyond single conversations
        - Session metadata preservation
        - State consolidation from multiple sessions
        - Performance of state loading with large history
        - WebSocket events for session management
        """
        user_id = authenticated_user["user_id"]
        base_thread_id = str(uuid.uuid4())

        # Define multiple sessions to simulate long-term usage
        session_scenarios = [
            {
                "session_id": 1,
                "thread_id": f"{base_thread_id}_session_1",
                "session_context": "initial_data_science_consultation",
                "messages": [
                    "I want to start a customer analytics project for my e-commerce business",
                    "Help me identify the key metrics I should track for customer behavior analysis"
                ],
                "expected_memory_additions": ["customer_analytics", "e-commerce", "behavior_analysis"]
            },
            {
                "session_id": 2,
                "thread_id": f"{base_thread_id}_session_2",
                "session_context": "project_development",
                "messages": [
                    "Let's continue working on the customer analytics project we discussed. I've collected some initial data",
                    "What's the best approach for segmenting customers based on the behavior patterns we identified?"
                ],
                "expected_memory_additions": ["customer_segmentation", "data_collection", "behavior_patterns"],
                "expected_context_retention": ["customer_analytics", "e-commerce"]
            },
            {
                "session_id": 3,
                "thread_id": f"{base_thread_id}_session_3",
                "session_context": "implementation_guidance",
                "messages": [
                    "I've implemented the customer segmentation approach you suggested. Now I need help with the next phase",
                    "How do I measure the effectiveness of the customer behavior analysis and segmentation we've built?"
                ],
                "expected_memory_additions": ["implementation", "effectiveness_measurement", "segmentation_evaluation"],
                "expected_context_retention": ["customer_analytics", "behavior_analysis", "customer_segmentation"]
            }
        ]

        # Track cross-session events
        session_events = []

        async def collect_session_events():
            """Collect WebSocket events related to session management."""
            while True:
                try:
                    event = await websocket_client.receive()
                    if event and any(keyword in str(event).lower() for keyword in ["session", "long_term", "memory", "cross"]):
                        session_events.append({
                            'timestamp': datetime.now(timezone.utc),
                            'event': json.loads(event) if isinstance(event, str) else event
                        })
                except Exception:
                    break

        # Start session event collection
        session_task = asyncio.create_task(collect_session_events())

        session_results = []
        agent_execution_core = AgentExecutionCore()

        try:
            # Execute multiple sessions with cross-session state persistence
            for session_data in session_scenarios:
                session_id = session_data["session_id"]
                thread_id = session_data["thread_id"]

                # Load cross-session state for sessions 2+
                if session_id > 1:
                    # Load consolidated state from previous sessions
                    loaded_state = await state_persistence_service.load_consolidated_user_state(
                        user_id=user_id,
                        related_thread_patterns=[f"{base_thread_id}_session_*"],
                        include_long_term_memory=True,
                        max_history_length=50  # Limit for performance testing
                    )

                    assert loaded_state is not None, f"Should load consolidated state for session {session_id}"

                    # Validate cross-session context retention
                    agent_memory = loaded_state.agent_memory or {}
                    long_term_memory = agent_memory.get("long_term_memory", {})

                    for expected_context in session_data.get("expected_context_retention", []):
                        memory_contains_context = any(
                            expected_context.lower() in str(memory_value).lower()
                            for memory_value in long_term_memory.values()
                        )
                        assert memory_contains_context, f"Session {session_id}: Should retain context '{expected_context}' from previous sessions"

                    current_state = loaded_state
                else:
                    # Create initial state for first session
                    current_state = DeepAgentState(
                        user_id=user_id,
                        thread_id=thread_id,
                        conversation_history=[],
                        context={"session_context": session_data["session_context"]},
                        agent_memory={
                            "long_term_memory": {},
                            "session_history": {},
                            "cross_session_test": True
                        },
                        workflow_state="cross_session_learning"
                    )

                # Execute messages within session
                session_responses = []
                for message in session_data["messages"]:
                    run_id = str(uuid.uuid4())

                    execution_result = await agent_execution_core.execute_with_cross_session_persistence(
                        agent_state=current_state,
                        request=message,
                        run_id=run_id,
                        session_id=f"session_{session_id}",
                        enable_long_term_memory=True,
                        enable_cross_session_learning=True
                    )

                    assert execution_result is not None, f"Session {session_id} message execution should succeed"
                    assert execution_result.get("status") == "completed", f"Session {session_id} should complete successfully"

                    session_responses.append({
                        "message": message,
                        "result": execution_result,
                        "timestamp": datetime.now(timezone.utc)
                    })

                    # Update current state for next message
                    current_state = execution_result.get("final_state", current_state)

                # Validate session memory accumulation
                final_session_state = session_responses[-1]["result"].get("final_state")
                final_memory = final_session_state.agent_memory or {}
                long_term_memory = final_memory.get("long_term_memory", {})

                # Check that session added expected memory concepts
                for expected_addition in session_data["expected_memory_additions"]:
                    memory_contains_addition = any(
                        expected_addition.lower() in str(memory_value).lower()
                        for memory_value in long_term_memory.values()
                    )
                    assert memory_contains_addition, f"Session {session_id}: Should add '{expected_addition}' to long-term memory"

                session_results.append({
                    "session_id": session_id,
                    "thread_id": thread_id,
                    "responses": session_responses,
                    "final_state": final_session_state
                })

                # Simulate session break (disconnect/reconnect)
                await asyncio.sleep(0.5)

            # Allow time for session events
            await asyncio.sleep(2.0)

        finally:
            session_task.cancel()
            try:
                await session_task
            except asyncio.CancelledError:
                pass

        # VALIDATION: Cross-session persistence and long-term memory

        # 1. All sessions should complete successfully
        successful_sessions = [s for s in session_results if all(r["result"].get("status") == "completed" for r in s["responses"])]
        assert len(successful_sessions) >= 2, f"At least 2 sessions should complete successfully, got {len(successful_sessions)}"

        # 2. Validate long-term memory growth across sessions
        memory_evolution = []
        for session_result in successful_sessions:
            final_state = session_result["final_state"]
            agent_memory = final_state.agent_memory or {}
            long_term_memory = agent_memory.get("long_term_memory", {})

            memory_evolution.append({
                "session_id": session_result["session_id"],
                "memory_keys": list(long_term_memory.keys()),
                "memory_size": len(str(long_term_memory)),
                "concepts_count": len(long_term_memory)
            })

        # Memory should grow with each session
        for i in range(1, len(memory_evolution)):
            current_concepts = memory_evolution[i]["concepts_count"]
            previous_concepts = memory_evolution[i-1]["concepts_count"]
            assert current_concepts >= previous_concepts, f"Long-term memory should grow across sessions: {current_concepts} >= {previous_concepts}"

        # 3. Validate cross-session context awareness in responses
        if len(successful_sessions) >= 2:
            last_session = successful_sessions[-1]
            last_responses = last_session["responses"]

            # Final responses should reference concepts from earlier sessions
            all_response_text = " ".join([r["result"].get("final_response", "") for r in last_responses]).lower()

            early_session_concepts = ["customer_analytics", "e-commerce", "behavior_analysis"]
            cross_session_references = sum(1 for concept in early_session_concepts if concept in all_response_text)
            assert cross_session_references >= 2, f"Final session should reference earlier session concepts (found {cross_session_references})"

        # 4. Validate session management events
        assert len(session_events) >= 1, f"Should receive session management events, got {len(session_events)}"

        # 5. Validate performance with accumulated state
        if len(successful_sessions) >= 2:
            # Later sessions should complete within reasonable time despite accumulated state
            session_times = []
            for session_result in successful_sessions:
                session_start = min(r["timestamp"] for r in session_result["responses"])
                session_end = max(r["timestamp"] for r in session_result["responses"])
                session_duration = (session_end - session_start).total_seconds()
                session_times.append(session_duration)

            # Performance should not degrade significantly with accumulated state
            first_session_time = session_times[0]
            last_session_time = session_times[-1]

            # Allow for some performance degradation but not excessive (within 3x of first session)
            performance_ratio = last_session_time / first_session_time if first_session_time > 0 else 1
            assert performance_ratio <= 3.0, f"Performance degradation too high: {performance_ratio:.2f}x (times: {session_times})"

        # 6. Validate business value - comprehensive project continuity
        if len(successful_sessions) >= 3:
            # Final session should demonstrate comprehensive understanding of entire project
            final_session = successful_sessions[-1]
            final_responses = [r["result"].get("final_response", "") for r in final_session["responses"]]
            complete_final_response = " ".join(final_responses).lower()

            project_continuity_indicators = [
                "customer analytics",
                "segmentation",
                "implementation",
                "effectiveness",
                "measurement",
                "e-commerce"
            ]

            continuity_score = sum(1 for indicator in project_continuity_indicators if indicator in complete_final_response)
            assert continuity_score >= 4, f"Should demonstrate comprehensive project understanding (score: {continuity_score}/6)"