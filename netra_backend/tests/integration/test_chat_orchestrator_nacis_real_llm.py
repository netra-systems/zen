"""Integration tests for ChatOrchestrator/NACIS with real LLM interactions.

CRITICAL: These tests use REAL LLM, REAL intent classification, REAL multi-agent orchestration.
NO MOCKS ALLOWED per CLAUDE.md requirements.

Business Value: Validates premium AI consultation accuracy and multi-agent coordination.
Target segments: Enterprise. Core differentiator for high-value consultations.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.chat_orchestrator_main import ChatOrchestrator
from netra_backend.app.agents.chat_orchestrator.intent_classifier import IntentClassifier, IntentType
from netra_backend.app.agents.chat_orchestrator.model_cascade import ModelCascade
from netra_backend.app.agents.chat_orchestrator.confidence_manager import ConfidenceManager
from netra_backend.app.agents.chat_orchestrator.execution_planner import ExecutionPlanner
from netra_backend.app.agents.chat_orchestrator.pipeline_executor import PipelineExecutor
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.core.isolated_environment import IsolatedEnvironment
from netra_backend.app.core.database import get_async_session
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger as logger
from netra_backend.app.websocket.websocket_manager import WebSocketManager
from netra_backend.app.models.sql_models import ConversationHistory, AgentExecution

# Real environment configuration
env = IsolatedEnvironment()


class TestChatOrchestratorNACISRealLLM:
    """Test suite for ChatOrchestrator/NACIS with real LLM and multi-agent orchestration."""

    @pytest.fixture
    async def real_database_session(self):
        """Get real database session for testing."""
        async for session in get_async_session():
            yield session
            await session.rollback()

    @pytest.fixture
    async def real_chat_orchestrator(self, real_database_session):
        """Create real ChatOrchestrator instance with all dependencies."""
        session = real_database_session
        
        # Initialize real services
        llm_manager = LLMManager()
        await llm_manager.initialize()
        
        websocket_manager = WebSocketManager()
        tool_dispatcher = ToolDispatcher(llm_manager=llm_manager)
        await tool_dispatcher.initialize_tools(session)
        
        orchestrator = ChatOrchestrator(
            db_session=session,
            llm_manager=llm_manager,
            websocket_manager=websocket_manager,
            tool_dispatcher=tool_dispatcher,
            cache_manager=None,  # Real cache in production
            semantic_cache_enabled=True
        )
        
        yield orchestrator
        
        await llm_manager.cleanup()

    @pytest.fixture
    def complex_conversation_contexts(self):
        """Create complex conversation contexts for testing."""
        return [
            {
                "query": "Compare GPT-4, Claude 2, and Gemini Pro for enterprise document processing. Consider cost, accuracy, and compliance requirements.",
                "intent": "model_comparison",
                "complexity": "high",
                "requires_research": True
            },
            {
                "query": "My AI costs increased 300% last month. Analyze the root cause and provide immediate remediation steps.",
                "intent": "cost_analysis",
                "complexity": "critical",
                "requires_data_analysis": True
            },
            {
                "query": "Design a multi-region AI deployment strategy for a fintech application with strict latency and data residency requirements.",
                "intent": "architecture_design",
                "complexity": "expert",
                "requires_planning": True
            },
            {
                "query": "How can I implement prompt caching to reduce token usage without affecting response quality?",
                "intent": "optimization_guidance",
                "complexity": "medium",
                "requires_examples": True
            },
            {
                "query": "What are the security implications of using vector databases for RAG systems in healthcare?",
                "intent": "security_assessment",
                "complexity": "high",
                "requires_compliance_check": True
            }
        ]

    @pytest.mark.asyncio
    async def test_1_multi_agent_orchestration_with_complex_query(
        self, real_chat_orchestrator, real_database_session, complex_conversation_contexts
    ):
        """Test 1: Orchestrate multiple agents for complex query resolution using real LLM."""
        orchestrator = await real_chat_orchestrator
        session = real_database_session
        context = complex_conversation_contexts[0]  # Model comparison query
        
        # Create execution context
        state = DeepAgentState(
            user_query=context["query"],
            run_id=f"nacis_test_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            user_id="enterprise_user_001",
            tenant_id="enterprise_tenant_001",
            conversation_id=f"conv_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        )
        
        exec_context = ExecutionContext(
            run_id=state.run_id,
            user_id=state.user_id,
            tenant_id=state.tenant_id,
            state=state,
            metadata={
                "test_type": "multi_agent_orchestration",
                "complexity": context["complexity"],
                "llm_mode": "real"
            }
        )
        
        # Execute orchestration
        result = await orchestrator.execute(exec_context)
        
        # Validate orchestration results
        assert result is not None
        assert result.get("status") == "success"
        assert "response" in result
        assert "agents_involved" in result
        assert "confidence_score" in result
        
        # Check multi-agent involvement
        agents = result["agents_involved"]
        assert len(agents) >= 2  # Should involve multiple agents for complex query
        
        expected_agents = ["triage", "data", "optimization"]
        assert any(agent in agents for agent in expected_agents)
        
        # Validate response quality
        response = result["response"]
        assert len(response) > 100  # Substantial response
        
        # Should mention all three models
        assert all(model in response.lower() for model in ["gpt-4", "claude", "gemini"])
        
        # Check for comparison aspects
        comparison_aspects = ["cost", "accuracy", "compliance"]
        assert sum(aspect in response.lower() for aspect in comparison_aspects) >= 2
        
        # Verify confidence score
        assert result["confidence_score"] >= 0.7  # High confidence for researched response
        
        # Check execution trace
        assert "execution_trace" in result
        trace = result["execution_trace"]
        assert "planning_phase" in trace
        assert "execution_phase" in trace
        assert "validation_phase" in trace
        
        logger.info(f"Orchestrated {len(agents)} agents with confidence {result['confidence_score']:.2f}")

    @pytest.mark.asyncio
    async def test_2_intent_classification_and_routing_accuracy(
        self, real_chat_orchestrator, real_database_session, complex_conversation_contexts
    ):
        """Test 2: Verify intent classification and routing accuracy with real LLM."""
        orchestrator = await real_chat_orchestrator
        session = real_database_session
        
        # Test intent classification for all contexts
        classification_results = []
        
        for context in complex_conversation_contexts:
            state = DeepAgentState(
                user_query=context["query"],
                run_id=f"intent_test_{context['intent']}_{datetime.utcnow().strftime('%H%M%S')}",
                user_id="test_user",
                tenant_id="test_tenant"
            )
            
            # Use the intent classifier component
            intent_classifier = IntentClassifier(orchestrator.llm_manager)
            
            # Classify intent
            intent_result = await intent_classifier.classify(
                query=context["query"],
                conversation_history=[]
            )
            
            # Validate classification
            assert intent_result is not None
            assert "intent_type" in intent_result
            assert "confidence" in intent_result
            assert "sub_intents" in intent_result
            assert "required_capabilities" in intent_result
            
            # Check confidence threshold
            assert intent_result["confidence"] >= 0.6
            
            # Verify routing decision
            assert "routing_decision" in intent_result
            routing = intent_result["routing_decision"]
            assert "primary_agent" in routing
            assert "supporting_agents" in routing
            
            # Store classification result
            classification_results.append({
                "expected_intent": context["intent"],
                "classified_intent": intent_result["intent_type"],
                "confidence": intent_result["confidence"],
                "routing": routing,
                "match": context["intent"] in str(intent_result["intent_type"]).lower()
            })
            
            logger.info(f"Intent '{context['intent']}' classified as '{intent_result['intent_type']}' with confidence {intent_result['confidence']:.2f}")
        
        # Calculate classification accuracy
        accuracy = sum(r["match"] for r in classification_results) / len(classification_results)
        assert accuracy >= 0.8  # 80% accuracy minimum
        
        # Verify routing consistency
        for result in classification_results:
            routing = result["routing"]
            if "cost" in result["expected_intent"]:
                assert "cost_optimizer" in routing["primary_agent"].lower() or \
                       "optimization" in routing["primary_agent"].lower()
            elif "security" in result["expected_intent"]:
                assert "security" in routing["primary_agent"].lower() or \
                       "compliance" in routing["primary_agent"].lower()
                       
        logger.info(f"Intent classification accuracy: {accuracy:.1%}")

    @pytest.mark.asyncio
    async def test_3_model_cascade_with_quality_escalation(
        self, real_chat_orchestrator, real_database_session
    ):
        """Test 3: Test model cascade with quality-based escalation using real LLMs."""
        orchestrator = await real_chat_orchestrator
        session = real_database_session
        
        # Create queries of varying complexity
        test_queries = [
            {
                "query": "What is the token limit for GPT-3.5?",
                "expected_model": "gpt-3.5-turbo",
                "complexity": "simple"
            },
            {
                "query": "Explain the mathematical foundations of attention mechanisms in transformers and their computational complexity.",
                "expected_model": "gpt-4",
                "complexity": "complex"
            },
            {
                "query": "Design a fault-tolerant distributed training system for LLMs with automatic failover and checkpointing.",
                "expected_model": "claude-2",
                "complexity": "expert"
            }
        ]
        
        # Initialize model cascade
        model_cascade = ModelCascade(orchestrator.llm_manager)
        
        cascade_results = []
        
        for test_case in test_queries:
            # Execute cascade
            cascade_result = await model_cascade.execute(
                query=test_case["query"],
                quality_threshold=0.8,
                max_escalations=3
            )
            
            # Validate cascade result
            assert cascade_result is not None
            assert "response" in cascade_result
            assert "model_used" in cascade_result
            assert "quality_score" in cascade_result
            assert "escalation_count" in cascade_result
            assert "total_tokens" in cascade_result
            assert "total_cost" in cascade_result
            
            # Check quality achievement
            assert cascade_result["quality_score"] >= 0.7
            
            # Verify escalation behavior
            if test_case["complexity"] == "simple":
                assert cascade_result["escalation_count"] == 0
            elif test_case["complexity"] == "complex":
                assert cascade_result["escalation_count"] <= 1
            else:  # expert
                assert cascade_result["escalation_count"] <= 2
                
            cascade_results.append({
                "complexity": test_case["complexity"],
                "model_used": cascade_result["model_used"],
                "quality_score": cascade_result["quality_score"],
                "escalations": cascade_result["escalation_count"],
                "cost": cascade_result["total_cost"]
            })
            
            logger.info(f"Query complexity '{test_case['complexity']}' handled by {cascade_result['model_used']} with quality {cascade_result['quality_score']:.2f}")
        
        # Verify cost optimization
        simple_cost = next(r["cost"] for r in cascade_results if r["complexity"] == "simple")
        expert_cost = next(r["cost"] for r in cascade_results if r["complexity"] == "expert")
        assert expert_cost > simple_cost  # Complex queries should cost more
        
        # Check model selection appropriateness
        simple_model = next(r["model_used"] for r in cascade_results if r["complexity"] == "simple")
        assert "3.5" in simple_model or "small" in simple_model.lower()

    @pytest.mark.asyncio
    async def test_4_confidence_based_fact_checking_and_verification(
        self, real_chat_orchestrator, real_database_session
    ):
        """Test 4: Confidence-based fact checking and response verification with real LLM."""
        orchestrator = await real_chat_orchestrator
        session = real_database_session
        
        # Test queries with factual claims
        test_queries = [
            {
                "query": "GPT-4 has 1.76 trillion parameters and was trained on 13 trillion tokens.",
                "contains_claim": True,
                "claim_verifiable": True
            },
            {
                "query": "What are the best practices for prompt engineering?",
                "contains_claim": False,
                "claim_verifiable": False
            },
            {
                "query": "Claude 2 can process 100K tokens and costs $0.01 per 1K tokens for input.",
                "contains_claim": True,
                "claim_verifiable": True
            }
        ]
        
        confidence_manager = ConfidenceManager(orchestrator.llm_manager)
        
        verification_results = []
        
        for test_case in test_queries:
            state = DeepAgentState(
                user_query=test_case["query"],
                run_id=f"confidence_test_{datetime.utcnow().strftime('%H%M%S')}",
                user_id="test_user",
                tenant_id="test_tenant"
            )
            
            # Generate initial response
            initial_response = await orchestrator.llm_manager.generate(
                prompt=test_case["query"],
                model="gpt-3.5-turbo"
            )
            
            # Perform confidence assessment and fact checking
            confidence_result = await confidence_manager.assess_response(
                query=test_case["query"],
                response=initial_response,
                require_fact_check=test_case["contains_claim"]
            )
            
            # Validate confidence assessment
            assert confidence_result is not None
            assert "confidence_score" in confidence_result
            assert "fact_check_results" in confidence_result
            assert "requires_escalation" in confidence_result
            assert "verified_response" in confidence_result
            
            # Check fact checking for claims
            if test_case["contains_claim"]:
                fact_checks = confidence_result["fact_check_results"]
                assert len(fact_checks) > 0
                
                for fact_check in fact_checks:
                    assert "claim" in fact_check
                    assert "verification_status" in fact_check
                    assert "confidence" in fact_check
                    assert "source" in fact_check or "reasoning" in fact_check
                    
            # Verify escalation logic
            if confidence_result["confidence_score"] < 0.7:
                assert confidence_result["requires_escalation"] == True
                
            verification_results.append({
                "query_type": "claim" if test_case["contains_claim"] else "guidance",
                "confidence_score": confidence_result["confidence_score"],
                "fact_checks_performed": len(confidence_result["fact_check_results"]),
                "escalation_required": confidence_result["requires_escalation"]
            })
            
            logger.info(f"Confidence assessment: {confidence_result['confidence_score']:.2f}, Fact checks: {len(confidence_result['fact_check_results'])}")
        
        # Verify fact checking was performed for claims
        claim_results = [r for r in verification_results if r["query_type"] == "claim"]
        assert all(r["fact_checks_performed"] > 0 for r in claim_results)
        
        # Non-claim queries should have minimal fact checking
        guidance_results = [r for r in verification_results if r["query_type"] == "guidance"]
        assert all(r["fact_checks_performed"] == 0 for r in guidance_results)

    @pytest.mark.asyncio
    async def test_5_end_to_end_conversation_flow_with_context_retention(
        self, real_chat_orchestrator, real_database_session
    ):
        """Test 5: Complete E2E conversation flow with context retention and multi-turn dialogue."""
        orchestrator = await real_chat_orchestrator
        session = real_database_session
        
        # Multi-turn conversation scenario
        conversation_turns = [
            {
                "turn": 1,
                "query": "I need to optimize my AI infrastructure. We're currently spending $50K/month on OpenAI APIs.",
                "expected_context": ["cost", "optimization", "openai"]
            },
            {
                "turn": 2,
                "query": "What specific models are you recommending as alternatives?",
                "expected_context": ["models", "alternatives", "previous_cost_context"]
            },
            {
                "turn": 3,
                "query": "How would I implement the caching strategy you mentioned?",
                "expected_context": ["caching", "implementation", "cost_reduction"]
            },
            {
                "turn": 4,
                "query": "Can you provide a phased migration plan from our current setup?",
                "expected_context": ["migration", "phased", "openai_to_alternative"]
            },
            {
                "turn": 5,
                "query": "What monitoring should I set up to track the improvements?",
                "expected_context": ["monitoring", "metrics", "improvement_tracking"]
            }
        ]
        
        conversation_id = f"e2e_conv_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        conversation_history = []
        
        for turn_data in conversation_turns:
            # Create state with conversation history
            state = DeepAgentState(
                user_query=turn_data["query"],
                run_id=f"{conversation_id}_turn_{turn_data['turn']}",
                user_id="enterprise_user",
                tenant_id="enterprise_tenant",
                conversation_id=conversation_id,
                conversation_history=conversation_history
            )
            
            exec_context = ExecutionContext(
                run_id=state.run_id,
                user_id=state.user_id,
                tenant_id=state.tenant_id,
                state=state,
                metadata={
                    "conversation_turn": turn_data["turn"],
                    "test_type": "e2e_conversation"
                }
            )
            
            # Execute orchestration for this turn
            result = await orchestrator.execute(exec_context)
            
            # Validate turn result
            assert result is not None
            assert result.get("status") == "success"
            assert "response" in result
            assert len(result["response"]) > 50
            
            # Check context retention
            response_lower = result["response"].lower()
            
            if turn_data["turn"] > 1:
                # Should reference previous context
                assert any(
                    context_term in response_lower 
                    for context_term in ["previous", "mentioned", "discussed", "earlier", "above"]
                )
                
            # Verify expected context elements
            context_matches = sum(
                1 for expected in turn_data["expected_context"]
                if expected.replace("_", " ") in response_lower
            )
            assert context_matches >= len(turn_data["expected_context"]) * 0.5
            
            # Store in conversation history
            conversation_entry = ConversationHistory(
                id=f"{conversation_id}_{turn_data['turn']}",
                conversation_id=conversation_id,
                user_id=state.user_id,
                turn_number=turn_data["turn"],
                user_message=turn_data["query"],
                assistant_message=result["response"],
                metadata=json.dumps({
                    "confidence_score": result.get("confidence_score", 0),
                    "agents_involved": result.get("agents_involved", []),
                    "execution_time_ms": result.get("execution_time_ms", 0)
                }),
                created_at=datetime.utcnow()
            )
            session.add(conversation_entry)
            
            # Update conversation history for next turn
            conversation_history.append({
                "role": "user",
                "content": turn_data["query"]
            })
            conversation_history.append({
                "role": "assistant",
                "content": result["response"]
            })
            
            logger.info(f"Turn {turn_data['turn']} completed with {len(result['response'])} chars response")
        
        await session.commit()
        
        # Verify conversation coherence
        saved_conversation = await session.execute(
            select(ConversationHistory)
            .where(ConversationHistory.conversation_id == conversation_id)
            .order_by(ConversationHistory.turn_number)
        )
        saved_turns = saved_conversation.scalars().all()
        
        assert len(saved_turns) == len(conversation_turns)
        
        # Check for progressive refinement
        first_response = saved_turns[0].assistant_message
        last_response = saved_turns[-1].assistant_message
        
        # Last response should be more specific/actionable than first
        assert "monitor" in last_response.lower()
        assert any(metric in last_response.lower() for metric in ["latency", "cost", "error", "throughput"])
        
        # Verify context building
        migration_turn = saved_turns[3].assistant_message  # Turn 4 about migration
        assert "phase" in migration_turn.lower()
        assert "$50" in migration_turn or "50k" in migration_turn.lower() or "fifty" in migration_turn.lower()
        
        logger.info(f"E2E conversation completed with {len(conversation_turns)} turns and full context retention")


if __name__ == "__main__":
    # Run tests with real LLM
    asyncio.run(pytest.main([__file__, "-v", "--real-llm"]))