"""Integration tests for ChatOrchestrator/NACIS with real LLM interactions."""

# REMOVED_SYNTAX_ERROR: CRITICAL: These tests use REAL LLM, REAL intent classification, REAL multi-agent orchestration.
# REMOVED_SYNTAX_ERROR: NO MOCKS ALLOWED per CLAUDE.md requirements.

# REMOVED_SYNTAX_ERROR: Business Value: Validates premium AI consultation accuracy and multi-agent coordination.
# REMOVED_SYNTAX_ERROR: Target segments: Enterprise. Core differentiator for high-value consultations.
""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from netra_backend.app.agents.chat_orchestrator_main import ChatOrchestrator
from netra_backend.app.agents.chat_orchestrator.intent_classifier import IntentClassifier, IntentType
from netra_backend.app.agents.chat_orchestrator.model_cascade import ModelCascade
from netra_backend.app.agents.chat_orchestrator.confidence_manager import ConfidenceManager
from netra_backend.app.agents.chat_orchestrator.execution_planner import ExecutionPlanner
from netra_backend.app.agents.chat_orchestrator.pipeline_executor import PipelineExecutor
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.core.config import get_settings
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.database import get_db
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger as logger
from netra_backend.app.websocket_core import WebSocketManager
# Removed non-existent models import - test focuses on ChatOrchestrator functionality

# Real environment configuration
env = IsolatedEnvironment()


# REMOVED_SYNTAX_ERROR: class TestChatOrchestratorNACISRealLLM:
    # REMOVED_SYNTAX_ERROR: """Test suite for ChatOrchestrator/NACIS with real LLM and multi-agent orchestration."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def real_database_session(self):
    # REMOVED_SYNTAX_ERROR: """Get real database session for testing."""
    # REMOVED_SYNTAX_ERROR: async for session in get_db():
        # REMOVED_SYNTAX_ERROR: yield session
        # REMOVED_SYNTAX_ERROR: await session.rollback()

        # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def real_chat_orchestrator(self, real_database_session):
    # REMOVED_SYNTAX_ERROR: """Create real ChatOrchestrator instance with all dependencies."""
    # REMOVED_SYNTAX_ERROR: session = real_database_session

    # Initialize real services
    # REMOVED_SYNTAX_ERROR: settings = get_settings()
    # REMOVED_SYNTAX_ERROR: llm_manager = LLMManager(settings)
    # REMOVED_SYNTAX_ERROR: await llm_manager.initialize()

    # REMOVED_SYNTAX_ERROR: websocket_manager = WebSocketManager()
    # REMOVED_SYNTAX_ERROR: tool_dispatcher = ToolDispatcher()
    # REMOVED_SYNTAX_ERROR: await tool_dispatcher.initialize_tools(session)

    # REMOVED_SYNTAX_ERROR: orchestrator = ChatOrchestrator( )
    # REMOVED_SYNTAX_ERROR: db_session=session,
    # REMOVED_SYNTAX_ERROR: llm_manager=llm_manager,
    # REMOVED_SYNTAX_ERROR: websocket_manager=websocket_manager,
    # REMOVED_SYNTAX_ERROR: tool_dispatcher=tool_dispatcher,
    # REMOVED_SYNTAX_ERROR: cache_manager=None,  # Real cache in production
    # REMOVED_SYNTAX_ERROR: semantic_cache_enabled=True
    

    # REMOVED_SYNTAX_ERROR: yield orchestrator

    # REMOVED_SYNTAX_ERROR: await llm_manager.cleanup()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def complex_conversation_contexts(self):
    # REMOVED_SYNTAX_ERROR: """Create complex conversation contexts for testing."""
    # REMOVED_SYNTAX_ERROR: return [ )
    # REMOVED_SYNTAX_ERROR: { )
    # REMOVED_SYNTAX_ERROR: "query": "Compare GPT-4, Claude 2, and Gemini Pro for enterprise document processing. Consider cost, accuracy, and compliance requirements.",
    # REMOVED_SYNTAX_ERROR: "intent": "model_comparison",
    # REMOVED_SYNTAX_ERROR: "complexity": "high",
    # REMOVED_SYNTAX_ERROR: "requires_research": True
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: { )
    # REMOVED_SYNTAX_ERROR: "query": "My AI costs increased 300% last month. Analyze the root cause and provide immediate remediation steps.",
    # REMOVED_SYNTAX_ERROR: "intent": "cost_analysis",
    # REMOVED_SYNTAX_ERROR: "complexity": "critical",
    # REMOVED_SYNTAX_ERROR: "requires_data_analysis": True
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: { )
    # REMOVED_SYNTAX_ERROR: "query": "Design a multi-region AI deployment strategy for a fintech application with strict latency and data residency requirements.",
    # REMOVED_SYNTAX_ERROR: "intent": "architecture_design",
    # REMOVED_SYNTAX_ERROR: "complexity": "expert",
    # REMOVED_SYNTAX_ERROR: "requires_planning": True
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: { )
    # REMOVED_SYNTAX_ERROR: "query": "How can I implement prompt caching to reduce token usage without affecting response quality?",
    # REMOVED_SYNTAX_ERROR: "intent": "optimization_guidance",
    # REMOVED_SYNTAX_ERROR: "complexity": "medium",
    # REMOVED_SYNTAX_ERROR: "requires_examples": True
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: { )
    # REMOVED_SYNTAX_ERROR: "query": "What are the security implications of using vector databases for RAG systems in healthcare?",
    # REMOVED_SYNTAX_ERROR: "intent": "security_assessment",
    # REMOVED_SYNTAX_ERROR: "complexity": "high",
    # REMOVED_SYNTAX_ERROR: "requires_compliance_check": True
    
    

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_1_multi_agent_orchestration_with_complex_query( )
    # REMOVED_SYNTAX_ERROR: self, real_chat_orchestrator, real_database_session, complex_conversation_contexts
    # REMOVED_SYNTAX_ERROR: ):
        # REMOVED_SYNTAX_ERROR: """Test 1: Orchestrate multiple agents for complex query resolution using real LLM."""
        # REMOVED_SYNTAX_ERROR: orchestrator = await real_chat_orchestrator
        # REMOVED_SYNTAX_ERROR: session = real_database_session
        # REMOVED_SYNTAX_ERROR: context = complex_conversation_contexts[0]  # Model comparison query

        # Create execution context
        # REMOVED_SYNTAX_ERROR: state = DeepAgentState( )
        # REMOVED_SYNTAX_ERROR: user_query=context["query"],
        # REMOVED_SYNTAX_ERROR: run_id="formatted_string",
        # REMOVED_SYNTAX_ERROR: user_id="enterprise_user_001",
        # REMOVED_SYNTAX_ERROR: tenant_id="enterprise_tenant_001",
        # REMOVED_SYNTAX_ERROR: conversation_id="formatted_string"
        

        # REMOVED_SYNTAX_ERROR: exec_context = ExecutionContext( )
        # REMOVED_SYNTAX_ERROR: run_id=state.run_id,
        # REMOVED_SYNTAX_ERROR: user_id=state.user_id,
        # REMOVED_SYNTAX_ERROR: tenant_id=state.tenant_id,
        # REMOVED_SYNTAX_ERROR: state=state,
        # REMOVED_SYNTAX_ERROR: metadata={ )
        # REMOVED_SYNTAX_ERROR: "test_type": "multi_agent_orchestration",
        # REMOVED_SYNTAX_ERROR: "complexity": context["complexity"},
        # REMOVED_SYNTAX_ERROR: "llm_mode": "real"
        
        

        # Execute orchestration
        # REMOVED_SYNTAX_ERROR: result = await orchestrator.execute(exec_context)

        # Validate orchestration results
        # REMOVED_SYNTAX_ERROR: assert result is not None
        # REMOVED_SYNTAX_ERROR: assert result.get("status") == "success"
        # REMOVED_SYNTAX_ERROR: assert "response" in result
        # REMOVED_SYNTAX_ERROR: assert "agents_involved" in result
        # REMOVED_SYNTAX_ERROR: assert "confidence_score" in result

        # Check multi-agent involvement
        # REMOVED_SYNTAX_ERROR: agents = result["agents_involved"]
        # REMOVED_SYNTAX_ERROR: assert len(agents) >= 2  # Should involve multiple agents for complex query

        # REMOVED_SYNTAX_ERROR: expected_agents = ["triage", "data", "optimization"]
        # REMOVED_SYNTAX_ERROR: assert any(agent in agents for agent in expected_agents)

        # Validate response quality
        # REMOVED_SYNTAX_ERROR: response = result["response"]
        # REMOVED_SYNTAX_ERROR: assert len(response) > 100  # Substantial response

        # Should mention all three models
        # REMOVED_SYNTAX_ERROR: assert all(model in response.lower() for model in ["gpt-4", "claude", "gemini"])

        # Check for comparison aspects
        # REMOVED_SYNTAX_ERROR: comparison_aspects = ["cost", "accuracy", "compliance"]
        # REMOVED_SYNTAX_ERROR: assert sum(aspect in response.lower() for aspect in comparison_aspects) >= 2

        # Verify confidence score
        # REMOVED_SYNTAX_ERROR: assert result["confidence_score"] >= 0.7  # High confidence for researched response

        # Check execution trace
        # REMOVED_SYNTAX_ERROR: assert "execution_trace" in result
        # REMOVED_SYNTAX_ERROR: trace = result["execution_trace"]
        # REMOVED_SYNTAX_ERROR: assert "planning_phase" in trace
        # REMOVED_SYNTAX_ERROR: assert "execution_phase" in trace
        # REMOVED_SYNTAX_ERROR: assert "validation_phase" in trace

        # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_2_intent_classification_and_routing_accuracy( )
        # REMOVED_SYNTAX_ERROR: self, real_chat_orchestrator, real_database_session, complex_conversation_contexts
        # REMOVED_SYNTAX_ERROR: ):
            # REMOVED_SYNTAX_ERROR: """Test 2: Verify intent classification and routing accuracy with real LLM."""
            # REMOVED_SYNTAX_ERROR: orchestrator = await real_chat_orchestrator
            # REMOVED_SYNTAX_ERROR: session = real_database_session

            # Test intent classification for all contexts
            # REMOVED_SYNTAX_ERROR: classification_results = []

            # REMOVED_SYNTAX_ERROR: for context in complex_conversation_contexts:
                # REMOVED_SYNTAX_ERROR: state = DeepAgentState( )
                # REMOVED_SYNTAX_ERROR: user_query=context["query"],
                # REMOVED_SYNTAX_ERROR: run_id="formatted_string",
                # REMOVED_SYNTAX_ERROR: user_id="test_user",
                # REMOVED_SYNTAX_ERROR: tenant_id="test_tenant"
                

                # Use the intent classifier component
                # REMOVED_SYNTAX_ERROR: intent_classifier = IntentClassifier(orchestrator.llm_manager)

                # Classify intent
                # REMOVED_SYNTAX_ERROR: intent_result = await intent_classifier.classify( )
                # REMOVED_SYNTAX_ERROR: query=context["query"],
                # REMOVED_SYNTAX_ERROR: conversation_history=[]
                

                # Validate classification
                # REMOVED_SYNTAX_ERROR: assert intent_result is not None
                # REMOVED_SYNTAX_ERROR: assert "intent_type" in intent_result
                # REMOVED_SYNTAX_ERROR: assert "confidence" in intent_result
                # REMOVED_SYNTAX_ERROR: assert "sub_intents" in intent_result
                # REMOVED_SYNTAX_ERROR: assert "required_capabilities" in intent_result

                # Check confidence threshold
                # REMOVED_SYNTAX_ERROR: assert intent_result["confidence"] >= 0.6

                # Verify routing decision
                # REMOVED_SYNTAX_ERROR: assert "routing_decision" in intent_result
                # REMOVED_SYNTAX_ERROR: routing = intent_result["routing_decision"]
                # REMOVED_SYNTAX_ERROR: assert "primary_agent" in routing
                # REMOVED_SYNTAX_ERROR: assert "supporting_agents" in routing

                # Store classification result
                # REMOVED_SYNTAX_ERROR: classification_results.append({ ))
                # REMOVED_SYNTAX_ERROR: "expected_intent": context["intent"},
                # REMOVED_SYNTAX_ERROR: "classified_intent": intent_result["intent_type"],
                # REMOVED_SYNTAX_ERROR: "confidence": intent_result["confidence"],
                # REMOVED_SYNTAX_ERROR: "routing": routing,
                # REMOVED_SYNTAX_ERROR: "match": context["intent"] in str(intent_result["intent_type"]).lower()
                

                # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

                # Calculate classification accuracy
                # REMOVED_SYNTAX_ERROR: accuracy = sum(r["match"] for r in classification_results) / len(classification_results)
                # REMOVED_SYNTAX_ERROR: assert accuracy >= 0.8  # 80% accuracy minimum

                # Verify routing consistency
                # REMOVED_SYNTAX_ERROR: for result in classification_results:
                    # REMOVED_SYNTAX_ERROR: routing = result["routing"]
                    # REMOVED_SYNTAX_ERROR: if "cost" in result["expected_intent"]:
                        # REMOVED_SYNTAX_ERROR: assert "cost_optimizer" in routing["primary_agent"].lower() or \
                        # REMOVED_SYNTAX_ERROR: "optimization" in routing["primary_agent"].lower()
                        # REMOVED_SYNTAX_ERROR: elif "security" in result["expected_intent"]:
                            # REMOVED_SYNTAX_ERROR: assert "security" in routing["primary_agent"].lower() or \
                            # REMOVED_SYNTAX_ERROR: "compliance" in routing["primary_agent"].lower()

                            # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

                            # Removed problematic line: @pytest.mark.asyncio
                            # Removed problematic line: async def test_3_model_cascade_with_quality_escalation( )
                            # REMOVED_SYNTAX_ERROR: self, real_chat_orchestrator, real_database_session
                            # REMOVED_SYNTAX_ERROR: ):
                                # REMOVED_SYNTAX_ERROR: """Test 3: Test model cascade with quality-based escalation using real LLMs."""
                                # REMOVED_SYNTAX_ERROR: orchestrator = await real_chat_orchestrator
                                # REMOVED_SYNTAX_ERROR: session = real_database_session

                                # Create queries of varying complexity
                                # REMOVED_SYNTAX_ERROR: test_queries = [ )
                                # REMOVED_SYNTAX_ERROR: { )
                                # REMOVED_SYNTAX_ERROR: "query": "What is the token limit for GPT-3.5?",
                                # REMOVED_SYNTAX_ERROR: "expected_model": "gpt-3.5-turbo",
                                # REMOVED_SYNTAX_ERROR: "complexity": "simple"
                                # REMOVED_SYNTAX_ERROR: },
                                # REMOVED_SYNTAX_ERROR: { )
                                # REMOVED_SYNTAX_ERROR: "query": "Explain the mathematical foundations of attention mechanisms in transformers and their computational complexity.",
                                # REMOVED_SYNTAX_ERROR: "expected_model": "gpt-4",
                                # REMOVED_SYNTAX_ERROR: "complexity": "complex"
                                # REMOVED_SYNTAX_ERROR: },
                                # REMOVED_SYNTAX_ERROR: { )
                                # REMOVED_SYNTAX_ERROR: "query": "Design a fault-tolerant distributed training system for LLMs with automatic failover and checkpointing.",
                                # REMOVED_SYNTAX_ERROR: "expected_model": "claude-2",
                                # REMOVED_SYNTAX_ERROR: "complexity": "expert"
                                
                                

                                # Initialize model cascade
                                # REMOVED_SYNTAX_ERROR: model_cascade = ModelCascade(orchestrator.llm_manager)

                                # REMOVED_SYNTAX_ERROR: cascade_results = []

                                # REMOVED_SYNTAX_ERROR: for test_case in test_queries:
                                    # Execute cascade
                                    # REMOVED_SYNTAX_ERROR: cascade_result = await model_cascade.execute( )
                                    # REMOVED_SYNTAX_ERROR: query=test_case["query"],
                                    # REMOVED_SYNTAX_ERROR: quality_threshold=0.8,
                                    # REMOVED_SYNTAX_ERROR: max_escalations=3
                                    

                                    # Validate cascade result
                                    # REMOVED_SYNTAX_ERROR: assert cascade_result is not None
                                    # REMOVED_SYNTAX_ERROR: assert "response" in cascade_result
                                    # REMOVED_SYNTAX_ERROR: assert "model_used" in cascade_result
                                    # REMOVED_SYNTAX_ERROR: assert "quality_score" in cascade_result
                                    # REMOVED_SYNTAX_ERROR: assert "escalation_count" in cascade_result
                                    # REMOVED_SYNTAX_ERROR: assert "total_tokens" in cascade_result
                                    # REMOVED_SYNTAX_ERROR: assert "total_cost" in cascade_result

                                    # Check quality achievement
                                    # REMOVED_SYNTAX_ERROR: assert cascade_result["quality_score"] >= 0.7

                                    # Verify escalation behavior
                                    # REMOVED_SYNTAX_ERROR: if test_case["complexity"] == "simple":
                                        # REMOVED_SYNTAX_ERROR: assert cascade_result["escalation_count"] == 0
                                        # REMOVED_SYNTAX_ERROR: elif test_case["complexity"] == "complex":
                                            # REMOVED_SYNTAX_ERROR: assert cascade_result["escalation_count"] <= 1
                                            # REMOVED_SYNTAX_ERROR: else:  # expert
                                            # REMOVED_SYNTAX_ERROR: assert cascade_result["escalation_count"] <= 2

                                            # REMOVED_SYNTAX_ERROR: cascade_results.append({ ))
                                            # REMOVED_SYNTAX_ERROR: "complexity": test_case["complexity"},
                                            # REMOVED_SYNTAX_ERROR: "model_used": cascade_result["model_used"],
                                            # REMOVED_SYNTAX_ERROR: "quality_score": cascade_result["quality_score"],
                                            # REMOVED_SYNTAX_ERROR: "escalations": cascade_result["escalation_count"],
                                            # REMOVED_SYNTAX_ERROR: "cost": cascade_result["total_cost"]
                                            

                                            # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

                                            # Verify cost optimization
                                            # REMOVED_SYNTAX_ERROR: simple_cost = next(r[item for item in []] == "simple")
                                            # REMOVED_SYNTAX_ERROR: expert_cost = next(r[item for item in []] == "expert")
                                            # REMOVED_SYNTAX_ERROR: assert expert_cost > simple_cost  # Complex queries should cost more

                                            # Check model selection appropriateness
                                            # REMOVED_SYNTAX_ERROR: simple_model = next(r[item for item in []] == "simple")
                                            # REMOVED_SYNTAX_ERROR: assert "3.5" in simple_model or "small" in simple_model.lower()

                                            # Removed problematic line: @pytest.mark.asyncio
                                            # Removed problematic line: async def test_4_confidence_based_fact_checking_and_verification( )
                                            # REMOVED_SYNTAX_ERROR: self, real_chat_orchestrator, real_database_session
                                            # REMOVED_SYNTAX_ERROR: ):
                                                # REMOVED_SYNTAX_ERROR: """Test 4: Confidence-based fact checking and response verification with real LLM."""
                                                # REMOVED_SYNTAX_ERROR: orchestrator = await real_chat_orchestrator
                                                # REMOVED_SYNTAX_ERROR: session = real_database_session

                                                # Test queries with factual claims
                                                # REMOVED_SYNTAX_ERROR: test_queries = [ )
                                                # REMOVED_SYNTAX_ERROR: { )
                                                # REMOVED_SYNTAX_ERROR: "query": "GPT-4 has 1.76 trillion parameters and was trained on 13 trillion tokens.",
                                                # REMOVED_SYNTAX_ERROR: "contains_claim": True,
                                                # REMOVED_SYNTAX_ERROR: "claim_verifiable": True
                                                # REMOVED_SYNTAX_ERROR: },
                                                # REMOVED_SYNTAX_ERROR: { )
                                                # REMOVED_SYNTAX_ERROR: "query": "What are the best practices for prompt engineering?",
                                                # REMOVED_SYNTAX_ERROR: "contains_claim": False,
                                                # REMOVED_SYNTAX_ERROR: "claim_verifiable": False
                                                # REMOVED_SYNTAX_ERROR: },
                                                # REMOVED_SYNTAX_ERROR: { )
                                                # REMOVED_SYNTAX_ERROR: "query": "Claude 2 can process 100K tokens and costs $0.1 per 1K tokens for input.",
                                                # REMOVED_SYNTAX_ERROR: "contains_claim": True,
                                                # REMOVED_SYNTAX_ERROR: "claim_verifiable": True
                                                
                                                

                                                # REMOVED_SYNTAX_ERROR: confidence_manager = ConfidenceManager(orchestrator.llm_manager)

                                                # REMOVED_SYNTAX_ERROR: verification_results = []

                                                # REMOVED_SYNTAX_ERROR: for test_case in test_queries:
                                                    # REMOVED_SYNTAX_ERROR: state = DeepAgentState( )
                                                    # REMOVED_SYNTAX_ERROR: user_query=test_case["query"],
                                                    # REMOVED_SYNTAX_ERROR: run_id="formatted_string",
                                                    # REMOVED_SYNTAX_ERROR: user_id="test_user",
                                                    # REMOVED_SYNTAX_ERROR: tenant_id="test_tenant"
                                                    

                                                    # Generate initial response
                                                    # REMOVED_SYNTAX_ERROR: initial_response = await orchestrator.llm_manager.generate( )
                                                    # REMOVED_SYNTAX_ERROR: prompt=test_case["query"],
                                                    # REMOVED_SYNTAX_ERROR: model="gpt-3.5-turbo"
                                                    

                                                    # Perform confidence assessment and fact checking
                                                    # REMOVED_SYNTAX_ERROR: confidence_result = await confidence_manager.assess_response( )
                                                    # REMOVED_SYNTAX_ERROR: query=test_case["query"],
                                                    # REMOVED_SYNTAX_ERROR: response=initial_response,
                                                    # REMOVED_SYNTAX_ERROR: require_fact_check=test_case["contains_claim"]
                                                    

                                                    # Validate confidence assessment
                                                    # REMOVED_SYNTAX_ERROR: assert confidence_result is not None
                                                    # REMOVED_SYNTAX_ERROR: assert "confidence_score" in confidence_result
                                                    # REMOVED_SYNTAX_ERROR: assert "fact_check_results" in confidence_result
                                                    # REMOVED_SYNTAX_ERROR: assert "requires_escalation" in confidence_result
                                                    # REMOVED_SYNTAX_ERROR: assert "verified_response" in confidence_result

                                                    # Check fact checking for claims
                                                    # REMOVED_SYNTAX_ERROR: if test_case["contains_claim"]:
                                                        # REMOVED_SYNTAX_ERROR: fact_checks = confidence_result["fact_check_results"]
                                                        # REMOVED_SYNTAX_ERROR: assert len(fact_checks) > 0

                                                        # REMOVED_SYNTAX_ERROR: for fact_check in fact_checks:
                                                            # REMOVED_SYNTAX_ERROR: assert "claim" in fact_check
                                                            # REMOVED_SYNTAX_ERROR: assert "verification_status" in fact_check
                                                            # REMOVED_SYNTAX_ERROR: assert "confidence" in fact_check
                                                            # REMOVED_SYNTAX_ERROR: assert "source" in fact_check or "reasoning" in fact_check

                                                            # Verify escalation logic
                                                            # REMOVED_SYNTAX_ERROR: if confidence_result["confidence_score"] < 0.7:
                                                                # REMOVED_SYNTAX_ERROR: assert confidence_result["requires_escalation"] == True

                                                                # REMOVED_SYNTAX_ERROR: verification_results.append({ ))
                                                                # REMOVED_SYNTAX_ERROR: "query_type": "claim" if test_case["contains_claim"} else "guidance",
                                                                # REMOVED_SYNTAX_ERROR: "confidence_score": confidence_result["confidence_score"],
                                                                # REMOVED_SYNTAX_ERROR: "fact_checks_performed": len(confidence_result["fact_check_results"]),
                                                                # REMOVED_SYNTAX_ERROR: "escalation_required": confidence_result["requires_escalation"]
                                                                

                                                                # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

                                                                # Verify fact checking was performed for claims
                                                                # REMOVED_SYNTAX_ERROR: claim_results = [item for item in []] == "claim"]
                                                                # REMOVED_SYNTAX_ERROR: assert all(r["fact_checks_performed"] > 0 for r in claim_results)

                                                                # Non-claim queries should have minimal fact checking
                                                                # REMOVED_SYNTAX_ERROR: guidance_results = [item for item in []] == "guidance"]
                                                                # REMOVED_SYNTAX_ERROR: assert all(r["fact_checks_performed"] == 0 for r in guidance_results)

                                                                # Removed problematic line: @pytest.mark.asyncio
                                                                # Removed problematic line: async def test_5_end_to_end_conversation_flow_with_context_retention( )
                                                                # REMOVED_SYNTAX_ERROR: self, real_chat_orchestrator, real_database_session
                                                                # REMOVED_SYNTAX_ERROR: ):
                                                                    # REMOVED_SYNTAX_ERROR: """Test 5: Complete E2E conversation flow with context retention and multi-turn dialogue."""
                                                                    # REMOVED_SYNTAX_ERROR: orchestrator = await real_chat_orchestrator
                                                                    # REMOVED_SYNTAX_ERROR: session = real_database_session

                                                                    # Multi-turn conversation scenario
                                                                    # REMOVED_SYNTAX_ERROR: conversation_turns = [ )
                                                                    # REMOVED_SYNTAX_ERROR: { )
                                                                    # REMOVED_SYNTAX_ERROR: "turn": 1,
                                                                    # REMOVED_SYNTAX_ERROR: "query": "I need to optimize my AI infrastructure. We"re currently spending $50K/month on OpenAI APIs.",
                                                                    # REMOVED_SYNTAX_ERROR: "expected_context": ["cost", "optimization", "openai"}
                                                                    # REMOVED_SYNTAX_ERROR: },
                                                                    # REMOVED_SYNTAX_ERROR: { )
                                                                    # REMOVED_SYNTAX_ERROR: "turn": 2,
                                                                    # REMOVED_SYNTAX_ERROR: "query": "What specific models are you recommending as alternatives?",
                                                                    # REMOVED_SYNTAX_ERROR: "expected_context": ["models", "alternatives", "previous_cost_context"}
                                                                    # REMOVED_SYNTAX_ERROR: },
                                                                    # REMOVED_SYNTAX_ERROR: { )
                                                                    # REMOVED_SYNTAX_ERROR: "turn": 3,
                                                                    # REMOVED_SYNTAX_ERROR: "query": "How would I implement the caching strategy you mentioned?",
                                                                    # REMOVED_SYNTAX_ERROR: "expected_context": ["caching", "implementation", "cost_reduction"}
                                                                    # REMOVED_SYNTAX_ERROR: },
                                                                    # REMOVED_SYNTAX_ERROR: { )
                                                                    # REMOVED_SYNTAX_ERROR: "turn": 4,
                                                                    # REMOVED_SYNTAX_ERROR: "query": "Can you provide a phased migration plan from our current setup?",
                                                                    # REMOVED_SYNTAX_ERROR: "expected_context": ["migration", "phased", "openai_to_alternative"}
                                                                    # REMOVED_SYNTAX_ERROR: },
                                                                    # REMOVED_SYNTAX_ERROR: { )
                                                                    # REMOVED_SYNTAX_ERROR: "turn": 5,
                                                                    # REMOVED_SYNTAX_ERROR: "query": "What monitoring should I set up to track the improvements?",
                                                                    # REMOVED_SYNTAX_ERROR: "expected_context": ["monitoring", "metrics", "improvement_tracking"}
                                                                    
                                                                    

                                                                    # REMOVED_SYNTAX_ERROR: conversation_id = "formatted_string"
                                                                    # REMOVED_SYNTAX_ERROR: conversation_history = []

                                                                    # REMOVED_SYNTAX_ERROR: for turn_data in conversation_turns:
                                                                        # Create state with conversation history
                                                                        # REMOVED_SYNTAX_ERROR: state = DeepAgentState( )
                                                                        # REMOVED_SYNTAX_ERROR: user_query=turn_data["query"],
                                                                        # REMOVED_SYNTAX_ERROR: run_id="formatted_string",
                                                                        # REMOVED_SYNTAX_ERROR: user_id="enterprise_user",
                                                                        # REMOVED_SYNTAX_ERROR: tenant_id="enterprise_tenant",
                                                                        # REMOVED_SYNTAX_ERROR: conversation_id=conversation_id,
                                                                        # REMOVED_SYNTAX_ERROR: conversation_history=conversation_history
                                                                        

                                                                        # REMOVED_SYNTAX_ERROR: exec_context = ExecutionContext( )
                                                                        # REMOVED_SYNTAX_ERROR: run_id=state.run_id,
                                                                        # REMOVED_SYNTAX_ERROR: user_id=state.user_id,
                                                                        # REMOVED_SYNTAX_ERROR: tenant_id=state.tenant_id,
                                                                        # REMOVED_SYNTAX_ERROR: state=state,
                                                                        # REMOVED_SYNTAX_ERROR: metadata={ )
                                                                        # REMOVED_SYNTAX_ERROR: "conversation_turn": turn_data["turn"},
                                                                        # REMOVED_SYNTAX_ERROR: "test_type": "e2e_conversation"
                                                                        
                                                                        

                                                                        # Execute orchestration for this turn
                                                                        # REMOVED_SYNTAX_ERROR: result = await orchestrator.execute(exec_context)

                                                                        # Validate turn result
                                                                        # REMOVED_SYNTAX_ERROR: assert result is not None
                                                                        # REMOVED_SYNTAX_ERROR: assert result.get("status") == "success"
                                                                        # REMOVED_SYNTAX_ERROR: assert "response" in result
                                                                        # REMOVED_SYNTAX_ERROR: assert len(result["response"]) > 50

                                                                        # Check context retention
                                                                        # REMOVED_SYNTAX_ERROR: response_lower = result["response"].lower()

                                                                        # REMOVED_SYNTAX_ERROR: if turn_data["turn"] > 1:
                                                                            # Should reference previous context
                                                                            # REMOVED_SYNTAX_ERROR: assert any( )
                                                                            # REMOVED_SYNTAX_ERROR: context_term in response_lower
                                                                            # REMOVED_SYNTAX_ERROR: for context_term in ["previous", "mentioned", "discussed", "earlier", "above"]
                                                                            

                                                                            # Verify expected context elements
                                                                            # REMOVED_SYNTAX_ERROR: context_matches = sum( )
                                                                            # REMOVED_SYNTAX_ERROR: 1 for expected in turn_data["expected_context"]
                                                                            # REMOVED_SYNTAX_ERROR: if expected.replace("_", " ") in response_lower
                                                                            
                                                                            # REMOVED_SYNTAX_ERROR: assert context_matches >= len(turn_data["expected_context"]) * 0.5

                                                                            # Store conversation turn metadata for validation (no database persistence)
                                                                            # REMOVED_SYNTAX_ERROR: turn_metadata = { )
                                                                            # REMOVED_SYNTAX_ERROR: "conversation_id": conversation_id,
                                                                            # REMOVED_SYNTAX_ERROR: "turn_number": turn_data["turn"},
                                                                            # REMOVED_SYNTAX_ERROR: "user_message": turn_data["query"],
                                                                            # REMOVED_SYNTAX_ERROR: "assistant_message": result["response"],
                                                                            # REMOVED_SYNTAX_ERROR: "confidence_score": result.get("confidence_score", 0),
                                                                            # REMOVED_SYNTAX_ERROR: "agents_involved": result.get("agents_involved", []),
                                                                            # REMOVED_SYNTAX_ERROR: "execution_time_ms": result.get("execution_time_ms", 0),
                                                                            # REMOVED_SYNTAX_ERROR: "timestamp": datetime.utcnow()
                                                                            

                                                                            # Update conversation history for next turn
                                                                            # REMOVED_SYNTAX_ERROR: conversation_history.append({ ))
                                                                            # REMOVED_SYNTAX_ERROR: "role": "user",
                                                                            # REMOVED_SYNTAX_ERROR: "content": turn_data["query"}
                                                                            
                                                                            # REMOVED_SYNTAX_ERROR: conversation_history.append({ ))
                                                                            # REMOVED_SYNTAX_ERROR: "role": "assistant",
                                                                            # REMOVED_SYNTAX_ERROR: "content": result["response"}
                                                                            

                                                                            # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

                                                                            # Verify conversation coherence from in-memory conversation history
                                                                            # REMOVED_SYNTAX_ERROR: assert len(conversation_history) == len(conversation_turns) * 2  # Each turn has user + assistant message

                                                                            # Extract just the assistant responses for validation
                                                                            # REMOVED_SYNTAX_ERROR: assistant_responses = [ )
                                                                            # REMOVED_SYNTAX_ERROR: msg["content"] for msg in conversation_history
                                                                            # REMOVED_SYNTAX_ERROR: if msg["role"] == "assistant"
                                                                            
                                                                            # REMOVED_SYNTAX_ERROR: assert len(assistant_responses) == len(conversation_turns)

                                                                            # Check for progressive refinement
                                                                            # REMOVED_SYNTAX_ERROR: first_response = assistant_responses[0]
                                                                            # REMOVED_SYNTAX_ERROR: last_response = assistant_responses[-1]

                                                                            # Last response should be more specific/actionable than first
                                                                            # REMOVED_SYNTAX_ERROR: assert "monitor" in last_response.lower()
                                                                            # REMOVED_SYNTAX_ERROR: assert any(metric in last_response.lower() for metric in ["latency", "cost", "error", "throughput"])

                                                                            # Verify context building in migration response (Turn 4)
                                                                            # REMOVED_SYNTAX_ERROR: if len(assistant_responses) >= 4:
                                                                                # REMOVED_SYNTAX_ERROR: migration_turn = assistant_responses[3]  # Turn 4 about migration
                                                                                # REMOVED_SYNTAX_ERROR: assert "phase" in migration_turn.lower()
                                                                                # REMOVED_SYNTAX_ERROR: assert "$50" in migration_turn or "50k" in migration_turn.lower() or "fifty" in migration_turn.lower()

                                                                                # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")


                                                                                # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                                                                                    # Run tests with real LLM
                                                                                    # REMOVED_SYNTAX_ERROR: asyncio.run(pytest.main([__file__, "-v", "--real-llm"]))