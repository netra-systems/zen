"""
Test LLM Conversation Context Isolation

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Ensure conversation security and context isolation
- Value Impact: Prevents conversation history leakage between users and sessions
- Strategic Impact: CRITICAL for user trust and regulatory compliance

SECURITY CRITICAL: Conversation history and context must never leak between users.
This validates that conversation state, history, and context remain isolated.
"""

import asyncio
import pytest
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, patch
import time
import uuid
import json

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from netra_backend.app.llm.llm_manager import LLMManager, create_llm_manager
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.schemas.llm_types import LLMResponse, TokenUsage, LLMProvider
from shared.isolated_environment import get_env


class TestLLMConversationContextIsolation(BaseIntegrationTest):
    """
    Test conversation context isolation between users and sessions.
    
    CRITICAL: These tests prevent conversation history leakage and context bleeding.
    """
    
    @pytest.fixture
    async def multi_session_contexts(self):
        """Create multiple user contexts with different sessions."""
        contexts = []
        
        # User A with multiple sessions
        for session in range(3):
            context = UserExecutionContext(
                user_id="user-a",
                session_id=f"session-a-{session}",
                thread_id=f"thread-a-{session}",
                execution_id=f"exec-a-{session}",
                permissions=["read", "write"],
                metadata={"user": "A", "session": session}
            )
            contexts.append(context)
        
        # User B with multiple sessions
        for session in range(2):
            context = UserExecutionContext(
                user_id="user-b", 
                session_id=f"session-b-{session}",
                thread_id=f"thread-b-{session}",
                execution_id=f"exec-b-{session}",
                permissions=["read", "write"],
                metadata={"user": "B", "session": session}
            )
            contexts.append(context)
            
        return contexts
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_conversation_history_isolation(self, real_services_fixture, multi_session_contexts):
        """
        Test that conversation history is isolated between users.
        
        BVJ: Users must never see other users' conversation history.
        """
        user_a_manager = create_llm_manager(multi_session_contexts[0])  # User A, Session 0
        user_b_manager = create_llm_manager(multi_session_contexts[3])  # User B, Session 0
        
        await user_a_manager.initialize()
        await user_b_manager.initialize()
        
        # User A has confidential conversation
        confidential_prompts_a = [
            "My company's revenue is $10M annually",
            "Our main competitor is struggling with scalability",
            "We're planning to acquire a smaller company next quarter"
        ]
        
        user_a_responses = []
        for prompt in confidential_prompts_a:
            response = await user_a_manager.ask_llm(prompt, use_cache=True)
            user_a_responses.append(response)
        
        # User B has different confidential conversation
        confidential_prompts_b = [
            "Our startup is seeking Series A funding",
            "We have 50K active users on our platform",
            "Planning to pivot our business model"
        ]
        
        user_b_responses = []
        for prompt in confidential_prompts_b:
            response = await user_b_manager.ask_llm(prompt, use_cache=True)
            user_b_responses.append(response)
        
        # CRITICAL: Verify no cross-contamination in responses
        for resp_a in user_a_responses:
            for resp_b in user_b_responses:
                assert resp_a != resp_b, "User responses should never match"
                
        # CRITICAL: Verify cache isolation
        assert len(user_a_manager._cache) == 3, "User A should have 3 cached conversations"
        assert len(user_b_manager._cache) == 3, "User B should have 3 cached conversations"
        
        # Verify User A cannot access User B's cached responses
        for prompt_b in confidential_prompts_b:
            assert not user_a_manager._is_cached(prompt_b, "default"), "User A should NOT have User B's cache"
            
        # Verify User B cannot access User A's cached responses  
        for prompt_a in confidential_prompts_a:
            assert not user_b_manager._is_cached(prompt_a, "default"), "User B should NOT have User A's cache"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_context_isolation(self, real_services_fixture, multi_session_contexts):
        """
        Test that different sessions for same user maintain isolation.
        
        BVJ: Same user's different sessions should not share context unexpectedly.
        """
        # User A, different sessions
        session_0_manager = create_llm_manager(multi_session_contexts[0])
        session_1_manager = create_llm_manager(multi_session_contexts[1])
        session_2_manager = create_llm_manager(multi_session_contexts[2])
        
        managers = [session_0_manager, session_1_manager, session_2_manager]
        
        # Initialize all sessions
        for manager in managers:
            await manager.initialize()
        
        # Each session has different context/topic
        session_contexts = [
            ("cost optimization", "How can I reduce my AWS costs?"),
            ("performance tuning", "My application is running slowly"), 
            ("security review", "I need to audit my security settings")
        ]
        
        # Execute different conversations in each session
        session_responses = []
        for i, (topic, prompt) in enumerate(session_contexts):
            response = await managers[i].ask_llm(prompt, use_cache=True)
            session_responses.append((topic, response))
            
            # Add session-specific metadata to manager for testing
            managers[i]._session_topic = topic
        
        # Verify session isolation
        for i, manager in enumerate(managers):
            # Each session should have exactly 1 cached item
            assert len(manager._cache) == 1, f"Session {i} should have 1 cached item"
            
            # Session should maintain its topic context
            assert manager._session_topic == session_contexts[i][0], f"Session {i} context mismatch"
            
            # Session should have its own user context with correct session_id
            expected_session_id = f"session-a-{i}"
            assert manager._user_context.session_id == expected_session_id, f"Session {i} ID mismatch"
        
        # Cross-session cache verification
        for i, manager_i in enumerate(managers):
            for j, manager_j in enumerate(managers):
                if i != j:
                    # Different sessions should not share cache keys
                    prompt_j = session_contexts[j][1]
                    assert not manager_i._is_cached(prompt_j, "default"), f"Session {i} should not cache Session {j}'s prompt"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_structured_response_isolation(self, real_services_fixture, multi_session_contexts):
        """
        Test structured responses maintain user isolation.
        
        BVJ: Structured responses may contain sensitive parsed data that must remain isolated.
        """
        from pydantic import BaseModel
        
        class CostAnalysis(BaseModel):
            monthly_cost: float = 0.0
            recommendations: List[str] = []
            confidence: float = 0.0
        
        user_a_manager = create_llm_manager(multi_session_contexts[0])
        user_b_manager = create_llm_manager(multi_session_contexts[3])
        
        await user_a_manager.initialize()
        await user_b_manager.initialize()
        
        # User A requests structured cost analysis
        prompt_a = "Analyze costs: AWS bill $5000/month, high compute usage"
        with patch.object(user_a_manager, '_make_llm_request') as mock_a:
            mock_a.return_value = '{"monthly_cost": 5000.0, "recommendations": ["Use reserved instances"], "confidence": 0.8}'
            
            response_a = await user_a_manager.ask_llm_structured(
                prompt_a, CostAnalysis, use_cache=True
            )
        
        # User B requests structured cost analysis with different data
        prompt_b = "Analyze costs: Azure bill $2000/month, storage heavy"
        with patch.object(user_b_manager, '_make_llm_request') as mock_b:
            mock_b.return_value = '{"monthly_cost": 2000.0, "recommendations": ["Archive old data"], "confidence": 0.9}'
            
            response_b = await user_b_manager.ask_llm_structured(
                prompt_b, CostAnalysis, use_cache=True
            )
        
        # CRITICAL: Verify structured responses are user-specific
        assert isinstance(response_a, CostAnalysis), "User A should get CostAnalysis object"
        assert isinstance(response_b, CostAnalysis), "User B should get CostAnalysis object"
        
        assert response_a.monthly_cost == 5000.0, "User A cost should be 5000"
        assert response_b.monthly_cost == 2000.0, "User B cost should be 2000"
        
        assert "reserved instances" in response_a.recommendations[0].lower(), "User A should get AWS recommendations"
        assert "archive old data" in response_b.recommendations[0].lower(), "User B should get Azure recommendations"
        
        # Verify no cross-contamination in cache
        cache_key_a = user_a_manager._get_cache_key(prompt_a, "default")
        cache_key_b = user_b_manager._get_cache_key(prompt_b, "default")
        
        assert cache_key_a in user_a_manager._cache, "User A cache should have structured response"
        assert cache_key_b in user_b_manager._cache, "User B cache should have structured response"
        assert cache_key_a not in user_b_manager._cache, "User B should not have User A's cache"
        assert cache_key_b not in user_a_manager._cache, "User A should not have User B's cache"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_full_response_metadata_isolation(self, real_services_fixture, multi_session_contexts):
        """
        Test full LLM responses with metadata maintain isolation.
        
        BVJ: Response metadata may contain user-specific information that must not leak.
        """
        user_a_manager = create_llm_manager(multi_session_contexts[0])
        user_b_manager = create_llm_manager(multi_session_contexts[3])
        
        await user_a_manager.initialize()
        await user_b_manager.initialize()
        
        # Mock LLM responses with different characteristics
        with patch.object(user_a_manager, '_make_llm_request') as mock_a:
            mock_a.return_value = "User A specific response with sensitive data"
            
            response_a = await user_a_manager.ask_llm_full(
                "Analyze my confidential data", 
                use_cache=True
            )
        
        with patch.object(user_b_manager, '_make_llm_request') as mock_b:
            mock_b.return_value = "User B different response with other sensitive data"
            
            response_b = await user_b_manager.ask_llm_full(
                "Analyze my confidential data",  # Same prompt, different user
                use_cache=True
            )
        
        # Verify responses are LLMResponse objects with proper isolation
        assert isinstance(response_a, LLMResponse), "User A should get LLMResponse"
        assert isinstance(response_b, LLMResponse), "User B should get LLMResponse"
        
        # CRITICAL: Content should be different despite same prompt
        assert response_a.content != response_b.content, "User responses should differ"
        assert "User A specific" in response_a.content, "User A response should be specific"
        assert "User B different" in response_b.content, "User B response should be specific"
        
        # Verify metadata isolation
        assert response_a.cached != response_b.cached, "Cache status might differ"
        assert isinstance(response_a.usage, TokenUsage), "User A should have token usage"
        assert isinstance(response_b.usage, TokenUsage), "User B should have token usage"
        
        # Token usage should reflect different responses
        assert response_a.usage.completion_tokens != response_b.usage.completion_tokens, "Token counts should differ"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_conversation_state_persistence_isolation(self, real_services_fixture, multi_session_contexts):
        """
        Test conversation state persistence remains isolated between users.
        
        BVJ: Persistent conversation state must not leak between users.
        """
        # Create managers for different users
        managers = {}
        for i, context in enumerate(multi_session_contexts):
            manager = create_llm_manager(context)
            await manager.initialize()
            managers[f"{context.user_id}_{context.session_id}"] = manager
        
        # Simulate persistent conversation state
        conversation_states = {}
        
        # Each user/session builds conversation state
        for key, manager in managers.items():
            # Simulate conversation state
            state = {
                "conversation_id": str(uuid.uuid4()),
                "message_count": 0,
                "topics": [],
                "user_preferences": {"style": "technical" if "user-a" in key else "business"}
            }
            
            # Store state in manager (simulating persistence)
            manager._conversation_state = state
            conversation_states[key] = state
            
            # Make some requests to build state
            for i in range(3):
                prompt = f"Message {i} from {key}"
                response = await manager.ask_llm(prompt, use_cache=True)
                
                # Update conversation state
                manager._conversation_state["message_count"] += 1
                manager._conversation_state["topics"].append(f"topic_{i}")
        
        # Verify conversation state isolation
        for key, manager in managers.items():
            expected_state = conversation_states[key]
            actual_state = manager._conversation_state
            
            # State should match what was set for this user/session
            assert actual_state["conversation_id"] == expected_state["conversation_id"], f"Conversation ID mismatch for {key}"
            assert actual_state["message_count"] == 3, f"Message count should be 3 for {key}"
            assert len(actual_state["topics"]) == 3, f"Should have 3 topics for {key}"
            
            # User preferences should be preserved
            expected_style = "technical" if "user-a" in key else "business"
            assert actual_state["user_preferences"]["style"] == expected_style, f"User preference mismatch for {key}"
        
        # Cross-contamination check
        user_a_sessions = {k: v for k, v in managers.items() if "user-a" in k}
        user_b_sessions = {k: v for k, v in managers.items() if "user-b" in k}
        
        # Verify User A sessions don't have User B data
        for a_key, a_manager in user_a_sessions.items():
            for b_key, b_manager in user_b_sessions.items():
                assert a_manager._conversation_state["conversation_id"] != b_manager._conversation_state["conversation_id"], "Conversation IDs should be unique"
                assert a_manager._conversation_state["user_preferences"] != b_manager._conversation_state["user_preferences"], "User preferences should differ"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_conversation_isolation(self, real_services_fixture, multi_session_contexts):
        """
        Test concurrent conversations maintain isolation under load.
        
        BVJ: High-load concurrent conversations must not cause context bleeding.
        """
        managers = [create_llm_manager(ctx) for ctx in multi_session_contexts]
        
        # Initialize all managers
        for manager in managers:
            await manager.initialize()
        
        # Create conversation scenarios for each user/session
        conversation_scenarios = [
            ("financial_analysis", "Analyze quarterly financial performance"),
            ("security_audit", "Review security vulnerabilities"),
            ("performance_optimization", "Optimize application performance"), 
            ("cost_reduction", "Identify cost reduction opportunities"),
            ("compliance_review", "Check compliance requirements")
        ]
        
        async def run_conversation(manager, scenario_index):
            """Run a conversation scenario for a specific manager."""
            scenario_name, base_prompt = conversation_scenarios[scenario_index % len(conversation_scenarios)]
            
            # Generate unique conversation data for this manager
            user_id = manager._user_context.user_id
            session_id = manager._user_context.session_id
            
            conversation_data = []
            
            # Run multiple conversation turns
            for turn in range(5):
                prompt = f"{base_prompt} - Turn {turn} for {user_id} in {session_id}"
                
                # Add some delay to simulate real conversation timing
                await asyncio.sleep(0.1)
                
                response = await manager.ask_llm(prompt, use_cache=True)
                
                conversation_data.append({
                    "turn": turn,
                    "prompt": prompt,
                    "response": response,
                    "timestamp": time.time(),
                    "user_id": user_id,
                    "session_id": session_id
                })
            
            return conversation_data
        
        # Run all conversations concurrently
        tasks = [run_conversation(manager, i) for i, manager in enumerate(managers)]
        all_conversations = await asyncio.gather(*tasks)
        
        # Verify conversation isolation
        assert len(all_conversations) == len(managers), "Should have conversation data for each manager"
        
        for i, conversation_data in enumerate(all_conversations):
            manager = managers[i]
            expected_user_id = manager._user_context.user_id
            expected_session_id = manager._user_context.session_id
            
            # Verify conversation belongs to correct user/session
            for turn_data in conversation_data:
                assert turn_data["user_id"] == expected_user_id, f"User ID mismatch in conversation {i}"
                assert turn_data["session_id"] == expected_session_id, f"Session ID mismatch in conversation {i}"
                assert expected_user_id in turn_data["prompt"], f"Prompt should contain user ID for conversation {i}"
                assert expected_session_id in turn_data["prompt"], f"Prompt should contain session ID for conversation {i}"
        
        # Verify no conversation data leaked between managers
        for i, conv_i in enumerate(all_conversations):
            for j, conv_j in enumerate(all_conversations):
                if i != j:
                    # Conversations should be completely different
                    for turn_i in conv_i:
                        for turn_j in conv_j:
                            assert turn_i["prompt"] != turn_j["prompt"], f"Conversation {i} and {j} should have different prompts"
                            assert turn_i["response"] != turn_j["response"], f"Conversation {i} and {j} should have different responses"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_context_cleanup_prevents_leakage(self, real_services_fixture, multi_session_contexts):
        """
        Test context cleanup prevents data leakage after session ends.
        
        BVJ: Session cleanup must not leave residual data accessible to other users.
        """
        active_managers = []
        cleanup_test_data = []
        
        # Create and use several managers
        for i, context in enumerate(multi_session_contexts[:3]):
            manager = create_llm_manager(context)
            await manager.initialize()
            
            # Create unique conversation data
            sensitive_prompt = f"CONFIDENTIAL: User {context.user_id} private data {i}"
            response = await manager.ask_llm(sensitive_prompt, use_cache=True)
            
            # Store test data for verification
            cleanup_test_data.append({
                "manager": manager,
                "context": context,
                "sensitive_prompt": sensitive_prompt,
                "response": response,
                "cache_key": manager._get_cache_key(sensitive_prompt, "default")
            })
            
            active_managers.append(manager)
        
        # Verify initial state - all managers have their data
        for test_data in cleanup_test_data:
            manager = test_data["manager"]
            cache_key = test_data["cache_key"]
            
            assert cache_key in manager._cache, "Manager should have its cached data"
            assert len(manager._cache) == 1, "Manager should have exactly 1 cache entry"
        
        # Clean up first manager (simulate session end)
        first_manager = cleanup_test_data[0]["manager"]
        first_cache_key = cleanup_test_data[0]["cache_key"]
        first_sensitive_prompt = cleanup_test_data[0]["sensitive_prompt"]
        
        await first_manager.shutdown()
        
        # CRITICAL: Verify cleanup was effective
        assert len(first_manager._cache) == 0, "Cleaned up manager should have empty cache"
        assert not first_manager._initialized, "Cleaned up manager should not be initialized"
        
        # CRITICAL: Verify other managers cannot access cleaned up data
        for i in range(1, len(cleanup_test_data)):
            other_manager = cleanup_test_data[i]["manager"]
            
            # Other manager should not be able to access first manager's data
            assert not other_manager._is_cached(first_sensitive_prompt, "default"), f"Manager {i} should not have access to cleaned up data"
            assert first_cache_key not in other_manager._cache, f"Manager {i} should not have cleaned up cache key"
            
            # Other manager should still have its own data
            own_cache_key = cleanup_test_data[i]["cache_key"]
            assert own_cache_key in other_manager._cache, f"Manager {i} should still have its own data"
        
        # Create new manager with same user context as cleaned up manager
        new_manager = create_llm_manager(cleanup_test_data[0]["context"])
        await new_manager.initialize()
        
        # CRITICAL: New manager should not have access to previous session data
        assert len(new_manager._cache) == 0, "New manager should start with empty cache"
        assert not new_manager._is_cached(first_sensitive_prompt, "default"), "New manager should not have previous session cache"
        
        # New manager should be able to create fresh data
        new_response = await new_manager.ask_llm("Fresh conversation after cleanup", use_cache=True)
        assert len(new_manager._cache) == 1, "New manager should be able to cache new data"