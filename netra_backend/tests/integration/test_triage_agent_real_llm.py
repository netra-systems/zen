"""Integration tests for TriageSubAgent with REAL LLM usage.

These tests validate actual triage and intent classification using real LLM,
real services, and actual system components - NO MOCKS.

Business Value: Ensures accurate user intent classification for proper routing.
""""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.triage.unified_triage_agent import UnifiedTriageAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.database import get_db
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
        
        # Execute real LLM triage
        await real_triage_agent.execute(state, state.run_id, stream_updates=False)
        
        # Get result from state
        result = state.triage_result
        
        # Validate triage result
        assert result["status"] == "success"
        assert "category" in result
        assert result["category"] != "Error"
        
        # Check for user intent which contains multiple intents
        assert "user_intent" in result
        user_intent = result["user_intent"]
        assert "primary_intent" in user_intent
        assert "secondary_intents" in user_intent
        # Complex query should have secondary intents
        assert len(user_intent.get("secondary_intents", [])) >= 1
        
        # Verify entity extraction
        assert "extracted_entities" in result
        entities = result["extracted_entities"]
        assert "models_mentioned" in entities
        assert "metrics_mentioned" in entities
        # Should extract GPT-4 and cost/usage metrics
        assert any("gpt" in model.lower() for model in entities.get("models_mentioned", []))
        
        # Check confidence score
        assert "confidence_score" in result
        assert 0 <= result["confidence_score"] <= 1.0
        
        logger.info(f"Classified query into category: {result['category']]")
    
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
        
        # Execute triage with ambiguous input
        await real_triage_agent.execute(state, state.run_id, stream_updates=False)
        
        # Get result from state
        result = state.triage_result
        
        assert result["status"] == "success"
        assert "category" in result
        
        # Ambiguous queries should have lower confidence
        assert "confidence_score" in result
        assert result["confidence_score"] < 0.8  # Lower confidence for ambiguous
        
        # Check that a category was still assigned
        assert result["category"] != "Error"
        
        # Check validation status might have warnings
        if "validation_status" in result:
            validation = result["validation_status"]
            # Ambiguous queries might have warnings
            if "warnings" in validation:
                assert isinstance(validation["warnings"], list)
        
        # Check that intent was detected even if ambiguous
        assert "user_intent" in result
        assert result["user_intent"]["primary_intent"] is not None
        
        logger.info(f"Handled ambiguous query with confidence: {result['confidence_score']]")
    
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
        
        # Execute triage with technical query
        await real_triage_agent.execute(state, state.run_id, stream_updates=False)
        
        # Get result from state
        result = state.triage_result
        
        assert result["status"] == "success"
        assert "category" in result
        
        # Should categorize appropriately for technical/ML query
        assert result["category"] != "Error"
        assert result["category"] != "General Inquiry"
        
        # Check entity extraction
        assert "extracted_entities" in result
        entities = result["extracted_entities"]
        
        # Should extract model mentions (RAG, LLM, etc.)
        models = entities.get("models_mentioned", [])
        assert isinstance(models, list)
        # Could extract LLM or other model-related terms
        
        # Check user intent
        assert "user_intent" in result
        intent = result["user_intent"]
        assert intent["primary_intent"] is not None
        
        # Should have reasonable confidence for technical query
        assert result["confidence_score"] >= 0.5
        
        logger.info(f"Understood technical query with category: {result['category']]")
    
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
            
            # Execute urgency detection
            await real_triage_agent.execute(state, state.run_id, stream_updates=False)
            
            # Get result from state
            result = state.triage_result
            
            assert result["status"] == "success"
            assert "priority" in result
            assert "category" in result
            
            # Get detected priority (maps to urgency)
            detected_priority = result["priority"]
            
            # Map priority to expected values
            priority_map = {
                "critical": ["critical", "high"],
                "high": ["high", "medium"],
                "normal": ["medium", "low"]
            }
            
            # Check priority is reasonable for the urgency level
            expected_urgency = test_case["expected_urgency"]
            assert detected_priority in priority_map.get(expected_urgency, ["medium"])
            
            # Check key parameters for time sensitivity
            if "key_parameters" in result:
                params = result["key_parameters"]
                if "URGENT" in test_case["query"] or "immediately" in test_case["query"]:
                    # Should detect high time sensitivity
                    if params.get("time_sensitivity"):
                        assert "high" in params["time_sensitivity"].lower() or \
                               "urgent" in params["time_sensitivity"].lower()
            
            logger.info(f"Detected priority: {detected_priority} for {expected_urgency} urgency")
    
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
        
        # Execute context-aware triage
        await real_triage_agent.execute(state, state.run_id, stream_updates=False)
        
        # Get result from state
        result = state.triage_result
        
        assert result["status"] == "success"
        assert "routing_decision" in result
        
        # Check suggested workflow which contains routing info
        workflow = result.get("suggested_workflow", {})
        assert "next_agent" in workflow
        
        # Should route to appropriate agent
        next_agent = workflow["next_agent"]
        assert next_agent in ["DataSubAgent", "OptimizationsCoreAgent", "SupplyResearcherAgent"]
        
        # Check extracted entities for context
        assert "extracted_entities" in result
        entities = result["extracted_entities"]
        # Should extract time ranges from "last week"
        assert "time_ranges" in entities
        
        # Check required data sources
        assert "required_data_sources" in workflow
        assert isinstance(workflow["required_data_sources"], list)
        
        # Check tool recommendations
        assert "tool_recommendations" in result
        assert isinstance(result["tool_recommendations"], list)
        
        logger.info(f"Context-aware routing to: {next_agent}")


if __name__ == "__main__":
    # Run tests with real services
    asyncio.run(pytest.main([__file__, "-v", "--real-llm"]))