# REMOVED_SYNTAX_ERROR: '''Integration tests for TriageSubAgent with REAL LLM usage.

# REMOVED_SYNTAX_ERROR: These tests validate actual triage and intent classification using real LLM,
# REMOVED_SYNTAX_ERROR: real services, and actual system components - NO MOCKS.

# REMOVED_SYNTAX_ERROR: Business Value: Ensures accurate user intent classification for proper routing.
""

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


# REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def real_llm_manager():
    # REMOVED_SYNTAX_ERROR: """Get real LLM manager instance with actual API credentials."""
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.config import get_settings
    # REMOVED_SYNTAX_ERROR: settings = get_settings()
    # REMOVED_SYNTAX_ERROR: llm_manager = LLMManager(settings)
    # REMOVED_SYNTAX_ERROR: yield llm_manager


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def real_tool_dispatcher():
    # REMOVED_SYNTAX_ERROR: """Get real tool dispatcher with actual tools loaded."""
    # REMOVED_SYNTAX_ERROR: dispatcher = ToolDispatcher()
    # REMOVED_SYNTAX_ERROR: return dispatcher


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def real_triage_agent(real_llm_manager, real_tool_dispatcher):
    # REMOVED_SYNTAX_ERROR: """Create real TriageSubAgent instance."""
    # REMOVED_SYNTAX_ERROR: agent = TriageSubAgent( )
    # REMOVED_SYNTAX_ERROR: llm_manager=real_llm_manager,
    # REMOVED_SYNTAX_ERROR: tool_dispatcher=real_tool_dispatcher,
    # REMOVED_SYNTAX_ERROR: websocket_manager=None  # Real websocket in production
    
    # REMOVED_SYNTAX_ERROR: yield agent
    # Cleanup not needed for tests


# REMOVED_SYNTAX_ERROR: class TestTriageSubAgentRealLLM:
    # REMOVED_SYNTAX_ERROR: """Test suite for TriageSubAgent with real LLM interactions."""

    # REMOVED_SYNTAX_ERROR: @pytest.mark.integration
    # REMOVED_SYNTAX_ERROR: @pytest.mark.real_llm
    # Removed problematic line: async def test_complex_multi_intent_query_classification( )
    # REMOVED_SYNTAX_ERROR: self, real_triage_agent, db_session
    # REMOVED_SYNTAX_ERROR: ):
        # REMOVED_SYNTAX_ERROR: """Test 1: Classify complex queries with multiple intents using real LLM."""
        # Complex query with multiple intents
        # REMOVED_SYNTAX_ERROR: state = DeepAgentState( )
        # REMOVED_SYNTAX_ERROR: run_id="test_triage_001",
        # REMOVED_SYNTAX_ERROR: user_query="I need to optimize my GPT-4 costs while also setting up monitoring alerts for when usage exceeds $500/day, and generate a report comparing last month"s usage to this month",
        # REMOVED_SYNTAX_ERROR: triage_result={},
        # REMOVED_SYNTAX_ERROR: data_result={}
        

        # Execute real LLM triage
        # REMOVED_SYNTAX_ERROR: await real_triage_agent.execute(state, state.run_id, stream_updates=False)

        # Get result from state
        # REMOVED_SYNTAX_ERROR: result = state.triage_result

        # Validate triage result
        # REMOVED_SYNTAX_ERROR: assert result["status"] == "success"
        # REMOVED_SYNTAX_ERROR: assert "category" in result
        # REMOVED_SYNTAX_ERROR: assert result["category"] != "Error"

        # Check for user intent which contains multiple intents
        # REMOVED_SYNTAX_ERROR: assert "user_intent" in result
        # REMOVED_SYNTAX_ERROR: user_intent = result["user_intent"]
        # REMOVED_SYNTAX_ERROR: assert "primary_intent" in user_intent
        # REMOVED_SYNTAX_ERROR: assert "secondary_intents" in user_intent
        # Complex query should have secondary intents
        # REMOVED_SYNTAX_ERROR: assert len(user_intent.get("secondary_intents", [])) >= 1

        # Verify entity extraction
        # REMOVED_SYNTAX_ERROR: assert "extracted_entities" in result
        # REMOVED_SYNTAX_ERROR: entities = result["extracted_entities"]
        # REMOVED_SYNTAX_ERROR: assert "models_mentioned" in entities
        # REMOVED_SYNTAX_ERROR: assert "metrics_mentioned" in entities
        # Should extract GPT-4 and cost/usage metrics
        # REMOVED_SYNTAX_ERROR: assert any("gpt" in model.lower() for model in entities.get("models_mentioned", []))

        # Check confidence score
        # REMOVED_SYNTAX_ERROR: assert "confidence_score" in result
        # REMOVED_SYNTAX_ERROR: assert 0 <= result["confidence_score"] <= 1.0

        # REMOVED_SYNTAX_ERROR: logger.info("formatted_string"context": { )
            # REMOVED_SYNTAX_ERROR: "recent_topics": ["api_latency", "model_inference", "database_queries"],
            # REMOVED_SYNTAX_ERROR: "user_role": "developer"
            
            
            

            # Execute triage with ambiguous input
            # REMOVED_SYNTAX_ERROR: await real_triage_agent.execute(state, state.run_id, stream_updates=False)

            # Get result from state
            # REMOVED_SYNTAX_ERROR: result = state.triage_result

            # REMOVED_SYNTAX_ERROR: assert result["status"] == "success"
            # REMOVED_SYNTAX_ERROR: assert "category" in result

            # Ambiguous queries should have lower confidence
            # REMOVED_SYNTAX_ERROR: assert "confidence_score" in result
            # REMOVED_SYNTAX_ERROR: assert result["confidence_score"] < 0.8  # Lower confidence for ambiguous

            # Check that a category was still assigned
            # REMOVED_SYNTAX_ERROR: assert result["category"] != "Error"

            # Check validation status might have warnings
            # REMOVED_SYNTAX_ERROR: if "validation_status" in result:
                # REMOVED_SYNTAX_ERROR: validation = result["validation_status"]
                # Ambiguous queries might have warnings
                # REMOVED_SYNTAX_ERROR: if "warnings" in validation:
                    # REMOVED_SYNTAX_ERROR: assert isinstance(validation["warnings"], list)

                    # Check that intent was detected even if ambiguous
                    # REMOVED_SYNTAX_ERROR: assert "user_intent" in result
                    # REMOVED_SYNTAX_ERROR: assert result["user_intent"]["primary_intent"] is not None

                    # REMOVED_SYNTAX_ERROR: logger.info("formatted_string"status"] == "success"
                        # REMOVED_SYNTAX_ERROR: assert "category" in result

                        # Should categorize appropriately for technical/ML query
                        # REMOVED_SYNTAX_ERROR: assert result["category"] != "Error"
                        # REMOVED_SYNTAX_ERROR: assert result["category"] != "General Inquiry"

                        # Check entity extraction
                        # REMOVED_SYNTAX_ERROR: assert "extracted_entities" in result
                        # REMOVED_SYNTAX_ERROR: entities = result["extracted_entities"]

                        # Should extract model mentions (RAG, LLM, etc.)
                        # REMOVED_SYNTAX_ERROR: models = entities.get("models_mentioned", [])
                        # REMOVED_SYNTAX_ERROR: assert isinstance(models, list)
                        # Could extract LLM or other model-related terms

                        # Check user intent
                        # REMOVED_SYNTAX_ERROR: assert "user_intent" in result
                        # REMOVED_SYNTAX_ERROR: intent = result["user_intent"]
                        # REMOVED_SYNTAX_ERROR: assert intent["primary_intent"] is not None

                        # Should have reasonable confidence for technical query
                        # REMOVED_SYNTAX_ERROR: assert result["confidence_score"] >= 0.5

                        # REMOVED_SYNTAX_ERROR: logger.info("formatted_string"query": "When you get a chance, could you look into optimizing our test suite performance?",
                            # REMOVED_SYNTAX_ERROR: "expected_urgency": "low",
                            # REMOVED_SYNTAX_ERROR: "expected_priority": 3
                            # REMOVED_SYNTAX_ERROR: },
                            # REMOVED_SYNTAX_ERROR: { )
                            # REMOVED_SYNTAX_ERROR: "query": "We need to fix the billing calculation bug before month-end closing tomorrow",
                            # REMOVED_SYNTAX_ERROR: "expected_urgency": "high",
                            # REMOVED_SYNTAX_ERROR: "expected_priority": 1
                            
                            

                            # REMOVED_SYNTAX_ERROR: for i, test_case in enumerate(test_cases):
                                # REMOVED_SYNTAX_ERROR: state = DeepAgentState( )
                                # REMOVED_SYNTAX_ERROR: run_id="formatted_string",
                                # REMOVED_SYNTAX_ERROR: user_query=test_case["query"],
                                # REMOVED_SYNTAX_ERROR: triage_result={},
                                # REMOVED_SYNTAX_ERROR: data_result={}
                                

                                # Execute urgency detection
                                # REMOVED_SYNTAX_ERROR: await real_triage_agent.execute(state, state.run_id, stream_updates=False)

                                # Get result from state
                                # REMOVED_SYNTAX_ERROR: result = state.triage_result

                                # REMOVED_SYNTAX_ERROR: assert result["status"] == "success"
                                # REMOVED_SYNTAX_ERROR: assert "priority" in result
                                # REMOVED_SYNTAX_ERROR: assert "category" in result

                                # Get detected priority (maps to urgency)
                                # REMOVED_SYNTAX_ERROR: detected_priority = result["priority"]

                                # Map priority to expected values
                                # REMOVED_SYNTAX_ERROR: priority_map = { )
                                # REMOVED_SYNTAX_ERROR: "critical": ["critical", "high"],
                                # REMOVED_SYNTAX_ERROR: "high": ["high", "medium"],
                                # REMOVED_SYNTAX_ERROR: "normal": ["medium", "low"]
                                

                                # Check priority is reasonable for the urgency level
                                # REMOVED_SYNTAX_ERROR: expected_urgency = test_case["expected_urgency"]
                                # REMOVED_SYNTAX_ERROR: assert detected_priority in priority_map.get(expected_urgency, ["medium"])

                                # Check key parameters for time sensitivity
                                # REMOVED_SYNTAX_ERROR: if "key_parameters" in result:
                                    # REMOVED_SYNTAX_ERROR: params = result["key_parameters"]
                                    # REMOVED_SYNTAX_ERROR: if "URGENT" in test_case["query"] or "immediately" in test_case["query"]:
                                        # Should detect high time sensitivity
                                        # REMOVED_SYNTAX_ERROR: if params.get("time_sensitivity"):
                                            # REMOVED_SYNTAX_ERROR: assert "high" in params["time_sensitivity"].lower() or \
                                            # REMOVED_SYNTAX_ERROR: "urgent" in params["time_sensitivity"].lower()

                                            # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

                                            # REMOVED_SYNTAX_ERROR: @pytest.mark.integration
                                            # REMOVED_SYNTAX_ERROR: @pytest.mark.real_llm
                                            # Removed problematic line: async def test_context_aware_routing_decisions( )
                                            # REMOVED_SYNTAX_ERROR: self, real_triage_agent, db_session
                                            # REMOVED_SYNTAX_ERROR: ):
                                                # REMOVED_SYNTAX_ERROR: """Test 5: Make context-aware routing decisions using real LLM."""
                                                # Query with rich context
                                                # REMOVED_SYNTAX_ERROR: state = DeepAgentState( )
                                                # REMOVED_SYNTAX_ERROR: run_id="test_triage_005",
                                                # REMOVED_SYNTAX_ERROR: user_query="Show me the optimization recommendations from last week"s analysis",
                                                # REMOVED_SYNTAX_ERROR: triage_result={},
                                                # REMOVED_SYNTAX_ERROR: data_result={ )
                                                # REMOVED_SYNTAX_ERROR: "user_history": [ )
                                                # REMOVED_SYNTAX_ERROR: {"timestamp": "2024-01-15", "query": "Analyze GPT-4 usage patterns", "agent": "optimization"},
                                                # REMOVED_SYNTAX_ERROR: {"timestamp": "2024-01-17", "query": "Generate cost report", "agent": "reporting"},
                                                # REMOVED_SYNTAX_ERROR: {"timestamp": "2024-01-19", "query": "Implement caching strategy", "agent": "implementation"}
                                                # REMOVED_SYNTAX_ERROR: ],
                                                # REMOVED_SYNTAX_ERROR: "session_context": { )
                                                # REMOVED_SYNTAX_ERROR: "current_project": "cost_reduction_q1",
                                                # REMOVED_SYNTAX_ERROR: "active_workspace": "optimization_dashboard",
                                                # REMOVED_SYNTAX_ERROR: "user_preferences": {"default_view": "weekly_summary"}
                                                
                                                
                                                

                                                # Execute context-aware triage
                                                # REMOVED_SYNTAX_ERROR: await real_triage_agent.execute(state, state.run_id, stream_updates=False)

                                                # Get result from state
                                                # REMOVED_SYNTAX_ERROR: result = state.triage_result

                                                # REMOVED_SYNTAX_ERROR: assert result["status"] == "success"
                                                # REMOVED_SYNTAX_ERROR: assert "routing_decision" in result

                                                # Check suggested workflow which contains routing info
                                                # REMOVED_SYNTAX_ERROR: workflow = result.get("suggested_workflow", {})
                                                # REMOVED_SYNTAX_ERROR: assert "next_agent" in workflow

                                                # Should route to appropriate agent
                                                # REMOVED_SYNTAX_ERROR: next_agent = workflow["next_agent"]
                                                # REMOVED_SYNTAX_ERROR: assert next_agent in ["DataSubAgent", "OptimizationsCoreAgent", "SupplyResearcherAgent"]

                                                # Check extracted entities for context
                                                # REMOVED_SYNTAX_ERROR: assert "extracted_entities" in result
                                                # REMOVED_SYNTAX_ERROR: entities = result["extracted_entities"]
                                                # Should extract time ranges from "last week"
                                                # REMOVED_SYNTAX_ERROR: assert "time_ranges" in entities

                                                # Check required data sources
                                                # REMOVED_SYNTAX_ERROR: assert "required_data_sources" in workflow
                                                # REMOVED_SYNTAX_ERROR: assert isinstance(workflow["required_data_sources"], list)

                                                # Check tool recommendations
                                                # REMOVED_SYNTAX_ERROR: assert "tool_recommendations" in result
                                                # REMOVED_SYNTAX_ERROR: assert isinstance(result["tool_recommendations"], list)

                                                # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")


                                                # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                                                    # Run tests with real services
                                                    # REMOVED_SYNTAX_ERROR: asyncio.run(pytest.main([__file__, "-v", "--real-llm"]))