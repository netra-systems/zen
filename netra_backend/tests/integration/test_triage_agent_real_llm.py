"""Integration tests for TriageSubAgent with REAL LLM usage.

These tests validate actual triage and intent classification using real LLM,
real services, and actual system components - NO MOCKS.

Business Value: Ensures accurate user intent classification for proper routing.
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.triage_sub_agent.agent import TriageSubAgent
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.core.isolated_environment import IsolatedEnvironment
from netra_backend.app.database import get_db_session
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

# Real environment configuration
env = IsolatedEnvironment()


@pytest.fixture
async def real_llm_manager():
    """Get real LLM manager instance with actual API credentials."""
    from netra_backend.app.core.config import get_settings
    settings = get_settings()
    llm_manager = LLMManager(settings)
    yield llm_manager


@pytest.fixture
async def real_tool_dispatcher():
    """Get real tool dispatcher with actual tools loaded."""
    dispatcher = ToolDispatcher()
    return dispatcher


@pytest.fixture
async def real_triage_agent(real_llm_manager, real_tool_dispatcher):
    """Create real TriageSubAgent instance."""
    agent = TriageSubAgent(
        llm_manager=real_llm_manager,
        tool_dispatcher=real_tool_dispatcher,
        websocket_manager=None  # Real websocket in production
    )
    yield agent
    # Cleanup not needed for tests


class TestTriageSubAgentRealLLM:
    """Test suite for TriageSubAgent with real LLM interactions."""
    
    @pytest.mark.integration
    @pytest.mark.real_llm
    async def test_complex_multi_intent_query_classification(
        self, real_triage_agent, db_session
    ):
        """Test 1: Classify complex queries with multiple intents using real LLM."""
        # Complex query with multiple intents
        state = DeepAgentState(
            run_id="test_triage_001",
            user_query="I need to optimize my GPT-4 costs while also setting up monitoring alerts for when usage exceeds $500/day, and generate a report comparing last month's usage to this month",
            triage_result={},
            data_result={}
        )
        
        context = ExecutionContext(
            run_id=state.run_id,
            agent_name="TriageSubAgent",
            state=state,
            user_id="enterprise_user_001"
        )
        
        # Execute real LLM triage
        result = await real_triage_agent.execute(context)
        
        # Validate multi-intent detection
        assert result["status"] == "success"
        assert "intents" in result
        assert len(result["intents"]) >= 2  # Should detect multiple intents
        
        # Check for specific intent categories
        intent_types = [intent["type"] for intent in result["intents"]]
        assert "cost_optimization" in intent_types or "optimization" in intent_types
        assert "monitoring" in intent_types or "alerting" in intent_types
        assert "reporting" in intent_types or "analytics" in intent_types
        
        # Verify entity extraction
        assert "entities" in result
        entities = result["entities"]
        assert any("gpt-4" in str(e).lower() for e in entities)
        assert any("500" in str(e) or "cost" in str(e).lower() for e in entities)
        
        # Check confidence scores
        for intent in result["intents"]:
            assert "confidence" in intent
            assert 0 <= intent["confidence"] <= 1.0
        
        logger.info(f"Classified {len(result['intents'])} intents from complex query")
    
    @pytest.mark.integration
    @pytest.mark.real_llm
    async def test_ambiguous_query_clarification_generation(
        self, real_triage_agent, db_session
    ):
        """Test 2: Generate clarification questions for ambiguous queries using real LLM."""
        # Ambiguous query requiring clarification
        state = DeepAgentState(
            run_id="test_triage_002",
            user_query="Make it faster",
            triage_result={},
            data_result={
                "context": {
                    "recent_topics": ["api_latency", "model_inference", "database_queries"],
                    "user_role": "developer"
                }
            }
        )
        
        context = ExecutionContext(
            run_id=state.run_id,
            agent_name="TriageSubAgent",
            state=state,
            user_id="dev_user_002"
        )
        
        # Execute triage with ambiguous input
        result = await real_triage_agent.execute(context)
        
        assert result["status"] == "success"
        assert "needs_clarification" in result
        assert result["needs_clarification"] == True
        
        # Check for clarification questions
        assert "clarification_questions" in result
        questions = result["clarification_questions"]
        assert len(questions) >= 2
        
        # Verify questions are contextual
        questions_text = " ".join(questions).lower()
        assert any([
            "api" in questions_text,
            "model" in questions_text,
            "database" in questions_text,
            "performance" in questions_text,
            "latency" in questions_text
        ])
        
        # Check for suggested interpretations
        assert "possible_interpretations" in result
        assert len(result["possible_interpretations"]) >= 2
        
        logger.info(f"Generated {len(questions)} clarification questions")
    
    @pytest.mark.integration
    @pytest.mark.real_llm
    async def test_technical_jargon_and_acronym_understanding(
        self, real_triage_agent, db_session
    ):
        """Test 3: Understand technical jargon and acronyms using real LLM."""
        # Query with technical terms and acronyms
        state = DeepAgentState(
            run_id="test_triage_003",
            user_query="Need to implement RAG with FAISS for our LLM pipeline using HF transformers and optimize the RLHF loop",
            triage_result={},
            data_result={}
        )
        
        context = ExecutionContext(
            run_id=state.run_id,
            agent_name="TriageSubAgent",
            state=state,
            user_id="ml_engineer_003"
        )
        
        # Execute triage with technical query
        result = await real_triage_agent.execute(context)
        
        assert result["status"] == "success"
        assert "intents" in result
        
        # Verify technical understanding
        assert "technical_components" in result
        components = result["technical_components"]
        
        # Check acronym expansion
        assert "acronym_expansions" in result
        expansions = result["acronym_expansions"]
        assert "RAG" in expansions  # Retrieval Augmented Generation
        assert "FAISS" in expansions  # Facebook AI Similarity Search
        assert "LLM" in expansions  # Large Language Model
        assert "RLHF" in expansions  # Reinforcement Learning from Human Feedback
        
        # Verify correct categorization
        assert "category" in result
        assert result["category"] in ["ml_engineering", "ai_infrastructure", "implementation"]
        
        # Check for implementation steps suggestion
        assert "suggested_workflow" in result or "implementation_steps" in result
        
        logger.info(f"Recognized {len(expansions)} technical acronyms")
    
    @pytest.mark.integration
    @pytest.mark.real_llm
    async def test_urgency_and_priority_detection(
        self, real_triage_agent, db_session
    ):
        """Test 4: Detect urgency and priority levels from user queries using real LLM."""
        # Test various urgency levels
        test_cases = [
            {
                "query": "URGENT: Production API is returning 500 errors and customers can't access the service!",
                "expected_urgency": "critical",
                "expected_priority": 1
            },
            {
                "query": "When you get a chance, could you look into optimizing our test suite performance?",
                "expected_urgency": "low",
                "expected_priority": 3
            },
            {
                "query": "We need to fix the billing calculation bug before month-end closing tomorrow",
                "expected_urgency": "high",
                "expected_priority": 1
            }
        ]
        
        for i, test_case in enumerate(test_cases):
            state = DeepAgentState(
                run_id=f"test_triage_004_{i}",
                user_query=test_case["query"],
                triage_result={},
                data_result={}
            )
            
            context = ExecutionContext(
                run_id=state.run_id,
                agent_name="TriageSubAgent",
                state=state,
                user_id="ops_team_004"
            )
            
            # Execute urgency detection
            result = await real_triage_agent.execute(context)
            
            assert result["status"] == "success"
            assert "urgency_level" in result
            assert "priority_score" in result
            
            # Verify urgency detection accuracy
            detected_urgency = result["urgency_level"]
            assert detected_urgency == test_case["expected_urgency"]
            
            # Check priority scoring
            priority = result["priority_score"]
            assert priority == test_case["expected_priority"]
            
            # Verify escalation recommendations
            if detected_urgency == "critical":
                assert "escalation_required" in result
                assert result["escalation_required"] == True
                assert "escalation_path" in result
            
            # Check for time sensitivity detection
            assert "time_sensitive" in result
            if "tomorrow" in test_case["query"] or "URGENT" in test_case["query"]:
                assert result["time_sensitive"] == True
            
            logger.info(f"Detected urgency: {detected_urgency}, priority: {priority}")
    
    @pytest.mark.integration
    @pytest.mark.real_llm
    async def test_context_aware_routing_decisions(
        self, real_triage_agent, db_session
    ):
        """Test 5: Make context-aware routing decisions using real LLM."""
        # Query with rich context
        state = DeepAgentState(
            run_id="test_triage_005",
            user_query="Show me the optimization recommendations from last week's analysis",
            triage_result={},
            data_result={
                "user_history": [
                    {"timestamp": "2024-01-15", "query": "Analyze GPT-4 usage patterns", "agent": "optimization"},
                    {"timestamp": "2024-01-17", "query": "Generate cost report", "agent": "reporting"},
                    {"timestamp": "2024-01-19", "query": "Implement caching strategy", "agent": "implementation"}
                ],
                "session_context": {
                    "current_project": "cost_reduction_q1",
                    "active_workspace": "optimization_dashboard",
                    "user_preferences": {"default_view": "weekly_summary"}
                }
            }
        )
        
        context = ExecutionContext(
            run_id=state.run_id,
            agent_name="TriageSubAgent",
            state=state,
            user_id="analyst_005"
        )
        
        # Execute context-aware triage
        result = await real_triage_agent.execute(context)
        
        assert result["status"] == "success"
        assert "routing_decision" in result
        
        routing = result["routing_decision"]
        assert "primary_agent" in routing
        assert "secondary_agents" in routing
        
        # Verify context awareness
        assert routing["primary_agent"] in ["reporting", "optimization"]
        
        # Check for context references
        assert "context_factors" in result
        factors = result["context_factors"]
        assert "historical_pattern" in factors
        assert "workspace_relevance" in factors
        
        # Verify data requirements identified
        assert "required_data" in result
        required = result["required_data"]
        assert "date_range" in required
        assert "last_week" in str(required["date_range"]) or "7_days" in str(required["date_range"])
        
        # Check for follow-up suggestions
        assert "suggested_follow_ups" in result
        assert len(result["suggested_follow_ups"]) > 0
        
        logger.info(f"Routed to {routing['primary_agent']} with {len(routing['secondary_agents'])} secondary agents")


if __name__ == "__main__":
    # Run tests with real services
    asyncio.run(pytest.main([__file__, "-v", "--real-llm"]))