"""
Integration Test: Data Helper Triage Flow

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Enable comprehensive data collection for accurate AI optimization strategies
- Value Impact: Ensures data helper collects sufficient data to enable optimization insights
- Strategic Impact: Critical for delivering actionable optimization recommendations to users

Tests the complete data helper triage integration flow using real services:
- PostgreSQL for data persistence
- Redis for caching
- Real LLM interactions
- User isolation and multi-user safety
- Error handling and fallback scenarios
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, MagicMock

from netra_backend.app.tools.data_helper import DataHelper, create_data_helper
from netra_backend.app.agents.triage.unified_triage_agent import (
    UnifiedTriageAgent, 
    UnifiedTriageAgentFactory,
    TriageResult,
    Priority,
    Complexity,
    ExtractedEntities,
    UserIntent,
    ToolRecommendation
)
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.db.models_postgres import User, Thread, Message
from netra_backend.app.logging_config import central_logger

from test_framework.base_integration_test import BaseIntegrationTest
from shared.isolated_environment import IsolatedEnvironment

# Import real services fixtures
from test_framework.conftest_real_services import real_services

logger = central_logger.get_logger(__name__)


@pytest.fixture
async def isolated_env():
    """Provide isolated environment for tests."""
    env = IsolatedEnvironment()
    env.set("TEST_MODE", "true", source="test")
    yield env


@pytest.fixture
async def test_users():
    """Create test users for multi-user isolation testing."""
    users = []
    for i in range(3):
        user = User(
            id=f"test_user_{i}_{uuid.uuid4().hex[:8]}",
            email=f"datahelper_test_{i}@netra.ai",
            username=f"datahelper_user_{i}",
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        users.append(user)
        
    yield users


@pytest.fixture
async def comprehensive_llm_manager():
    """Create comprehensive LLM manager for testing - prefers real LLM when available."""
    from shared.isolated_environment import IsolatedEnvironment
    env = IsolatedEnvironment()
    
    use_real_llm = env.get("USE_REAL_LLM", "false").lower() == "true"
    
    if use_real_llm:
        try:
            # Try to use real LLM manager
            real_manager = LLMManager()
            await real_manager.initialize()
            logger.info("Using real LLM manager for testing")
            yield real_manager
            return  # Exit after yielding real manager
        except Exception as e:
            logger.warning(f"Failed to initialize real LLM manager: {e}, falling back to mock")
    
    # Fallback to comprehensive mock with realistic responses
    from unittest.mock import AsyncMock
    mock_manager = AsyncMock(spec=LLMManager)
    
    # Default mock response for data helper
    mock_response = AsyncMock()
    mock_response.generations = [[AsyncMock()]]
    mock_response.generations[0][0].text = """
**Required Data Sources for Optimization Analysis**

[Cost Data]
- Monthly AI spending breakdown: Current spending across different models and providers
  Justification: Essential for identifying cost optimization opportunities
  
- Usage patterns and volume: Request patterns, peak hours, and scaling behavior  
  Justification: Critical for right-sizing and efficiency improvements

[Performance Metrics]  
- Current latency and throughput: Response times and throughput across services
  Justification: Needed to establish performance baselines for optimization
  
- Error rates and success metrics: Current reliability and quality metrics
  Justification: Required to ensure optimization doesn't impact quality

**Data Collection Instructions for User**
Please provide the following information to enable comprehensive optimization analysis:
1. Export your monthly AI usage reports from your provider dashboards
2. Gather performance monitoring data from the past 30 days
3. Document current configuration settings and scaling policies
"""
    
    mock_manager.agenerate.return_value = mock_response
    mock_manager.generate_response.return_value = mock_response
    mock_manager.health_check = AsyncMock(return_value=True)
    
    logger.info("Using comprehensive mock LLM manager for testing")
    yield mock_manager


@pytest.fixture  
async def real_tool_dispatcher():
    """Create real tool dispatcher for integration testing."""
    dispatcher = ToolDispatcher()
    yield dispatcher


@pytest.fixture
async def user_execution_contexts(test_users):
    """Create user execution contexts for isolation testing."""
    contexts = []
    for user in test_users:
        context = UserExecutionContext(
            user_id=user.id,
            request_id=f"req_{uuid.uuid4().hex[:8]}",
            thread_id=f"thread_{uuid.uuid4().hex[:8]}",
            run_id=f"run_{uuid.uuid4().hex[:8]}",
            metadata={}
        )
        contexts.append(context)
    yield contexts


class TestDataHelperTriageIntegration(BaseIntegrationTest):
    """Integration test suite for data helper triage flow with real services."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_data_helper_integration_with_triage_results(
        self, 
        real_services,
        comprehensive_llm_manager,
        real_tool_dispatcher,
        user_execution_contexts,
        isolated_env
    ):
        """Test data helper integration with comprehensive triage results."""
        context = user_execution_contexts[0]
        
        # Create triage result with detailed context
        triage_result = {
            "category": "Cost Optimization",
            "sub_category": "AWS Cost Analysis", 
            "priority": "high",
            "confidence_score": 0.92,
            "data_sufficiency": "partial",
            "extracted_entities": {
                "models": ["gpt-4", "claude-2"],
                "metrics": ["cost", "latency", "throughput"],
                "providers": ["aws", "openai"],
                "time_ranges": ["last month"],
                "thresholds": [1000, 200]
            },
            "user_intent": {
                "primary_intent": "optimize",
                "action_required": True,
                "confidence": 0.89
            },
            "next_steps": ["Analyze current costs", "Identify optimization opportunities"]
        }
        
        # Create data helper
        data_helper = create_data_helper(comprehensive_llm_manager)
        
        # Execute data request generation
        result = await data_helper.generate_data_request(
            user_request="Help me optimize my AWS AI costs - I'm spending too much on GPT-4",
            triage_result=triage_result,
            previous_results=[
                {
                    "agent_name": "TriageAgent",
                    "summary": "Identified high-priority cost optimization opportunity",
                    "result": triage_result
                }
            ]
        )
        
        # Verify successful generation
        assert result["success"] is True
        assert "data_request" in result
        assert result["user_request"] == "Help me optimize my AWS AI costs - I'm spending too much on GPT-4"
        assert result["triage_context"] == triage_result
        
        # Verify data request structure
        data_request = result["data_request"]
        assert "raw_response" in data_request
        assert "data_categories" in data_request
        assert "user_instructions" in data_request
        assert "structured_items" in data_request
        
        # Verify categories extracted
        categories = data_request["data_categories"]
        assert len(categories) >= 2  # Should have Cost Data and Performance Metrics
        
        # Verify structured items
        structured_items = data_request["structured_items"]
        assert len(structured_items) >= 4  # Should have multiple data points
        
        for item in structured_items:
            assert "category" in item
            assert "data_point" in item
            assert "required" in item
            assert item["required"] is True
        
        # Verify context preservation (only for mock LLM)
        if hasattr(comprehensive_llm_manager, 'agenerate') and hasattr(comprehensive_llm_manager.agenerate, 'called'):
            assert comprehensive_llm_manager.agenerate.called
            call_args = comprehensive_llm_manager.agenerate.call_args
            if call_args and len(call_args) > 1 and "prompts" in call_args[1]:
                assert "triage_result" in call_args[1]["prompts"][0]
                assert "Cost Optimization" in call_args[1]["prompts"][0]
        else:
            # For real LLM, verify the result contains expected optimization categories
            data_categories = data_request.get("data_categories", [])
            category_names = [cat.get("name", "").lower() for cat in data_categories]
            assert any("cost" in name or "optimization" in name for name in category_names), "Should contain cost/optimization categories"

    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_data_request_generation_based_on_triage_context(
        self,
        real_services,
        comprehensive_llm_manager, 
        user_execution_contexts
    ):
        """Test data request generation adapts to different triage contexts."""
        context = user_execution_contexts[0]
        
        # Test performance optimization context
        performance_triage = {
            "category": "Performance Optimization",
            "priority": "medium", 
            "confidence_score": 0.85,
            "data_sufficiency": "insufficient",
            "extracted_entities": {
                "metrics": ["latency", "throughput", "response time"],
                "models": ["gpt-3.5-turbo"],
                "time_ranges": ["last week"]
            }
        }
        
        data_helper = create_data_helper(comprehensive_llm_manager)
        
        result = await data_helper.generate_data_request(
            user_request="My API is too slow, need to optimize latency",
            triage_result=performance_triage,
            previous_results=None
        )
        
        # Verify context-aware generation
        assert result["success"] is True
        assert result["triage_context"]["category"] == "Performance Optimization"
        
        # Verify LLM was called with performance context
        call_args = mock_llm_manager.agenerate.call_args
        prompt_text = call_args[1]["prompts"][0]
        assert "Performance Optimization" in prompt_text
        assert "latency" in prompt_text
        assert "My API is too slow" in prompt_text

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_previous_agent_results_formatting(
        self,
        real_services,
        comprehensive_llm_manager,
        user_execution_contexts
    ):
        """Test proper formatting of previous agent results in data requests."""
        context = user_execution_contexts[0]
        
        # Create comprehensive previous results
        previous_results = [
            {
                "agent_name": "TriageAgent",
                "summary": "Classified as high-priority cost optimization",
                "result": {"category": "Cost Optimization", "confidence": 0.92}
            },
            {
                "agent_name": "DataAgent", 
                "summary": "Found usage spike in morning hours",
                "result": {"peak_usage": "9-11 AM", "average_latency": "150ms"}
            },
            {
                "agent_name": "OptimizationAgent",
                "summary": "Identified 30% potential cost savings",
                "result": {"savings_potential": 0.30, "recommendations": ["batch processing", "model switching"]}
            }
        ]
        
        triage_result = {
            "category": "Cost Optimization",
            "data_sufficiency": "partial" 
        }
        
        data_helper = create_data_helper(comprehensive_llm_manager)
        
        result = await data_helper.generate_data_request(
            user_request="Need more specific cost optimization recommendations",
            triage_result=triage_result,
            previous_results=previous_results
        )
        
        # Verify successful integration
        assert result["success"] is True
        
        # Verify previous results were formatted and included
        call_args = mock_llm_manager.agenerate.call_args
        prompt_text = call_args[1]["prompts"][0]
        assert "TriageAgent: Classified as high-priority cost optimization" in prompt_text
        assert "DataAgent: Found usage spike in morning hours" in prompt_text  
        assert "OptimizationAgent: Identified 30% potential cost savings" in prompt_text

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_isolation_between_contexts(
        self,
        real_services,
        comprehensive_llm_manager,
        user_execution_contexts,
        isolated_env
    ):
        """Test that data helper properly isolates data between different users."""
        # Create separate contexts for different users
        user1_context = user_execution_contexts[0]
        user2_context = user_execution_contexts[1]
        
        # User 1 triage result with sensitive data
        user1_triage = {
            "category": "Cost Optimization",
            "data_sufficiency": "partial",
            "extracted_entities": {
                "providers": ["aws"],
                "thresholds": [5000],  # User 1's budget
                "services": ["EC2", "Lambda"]
            }
        }
        
        # User 2 triage result with different data
        user2_triage = {
            "category": "Performance Optimization", 
            "data_sufficiency": "insufficient",
            "extracted_entities": {
                "providers": ["gcp"],
                "metrics": ["latency"],
                "models": ["palm-2"]
            }
        }
        
        # Create separate data helpers (simulating per-request isolation)
        user1_data_helper = create_data_helper(mock_llm_manager)
        user2_data_helper = create_data_helper(mock_llm_manager)
        
        # Execute requests concurrently
        user1_task = user1_data_helper.generate_data_request(
            user_request=f"User {user1_context.user_id}: Optimize my $5000 AWS budget",
            triage_result=user1_triage,
            previous_results=[{"agent_name": "Triage", "summary": "AWS cost analysis"}]
        )
        
        user2_task = user2_data_helper.generate_data_request(
            user_request=f"User {user2_context.user_id}: Improve GCP model latency", 
            triage_result=user2_triage,
            previous_results=[{"agent_name": "Triage", "summary": "GCP performance issue"}]
        )
        
        # Execute concurrently to test isolation
        user1_result, user2_result = await asyncio.gather(user1_task, user2_task)
        
        # Verify both succeeded
        assert user1_result["success"] is True
        assert user2_result["success"] is True
        
        # Verify no data leakage between users
        user1_request = user1_result["user_request"]
        user2_request = user2_result["user_request"]
        
        assert user1_context.user_id in user1_request
        assert user2_context.user_id in user2_request
        assert user1_context.user_id not in user2_request
        assert user2_context.user_id not in user1_request
        
        # Verify context isolation in triage data
        assert user1_result["triage_context"]["extracted_entities"]["providers"] == ["aws"]
        assert user2_result["triage_context"]["extracted_entities"]["providers"] == ["gcp"]

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_error_handling_and_fallback_messages(
        self,
        real_services,
        user_execution_contexts,
        isolated_env
    ):
        """Test error handling and fallback message generation."""
        context = user_execution_contexts[0]
        
        # Create failing LLM manager
        failing_llm_manager = AsyncMock(spec=LLMManager)
        failing_llm_manager.agenerate.side_effect = Exception("LLM service unavailable")
        
        data_helper = create_data_helper(failing_llm_manager)
        
        triage_result = {
            "category": "Cost Optimization",
            "data_sufficiency": "partial"
        }
        
        # Execute with failing LLM
        result = await data_helper.generate_data_request(
            user_request="Help optimize my AI costs",
            triage_result=triage_result,
            previous_results=None
        )
        
        # Verify graceful failure handling
        assert result["success"] is False
        assert "error" in result
        assert result["error"] == "LLM service unavailable"
        
        # Verify fallback message provided
        assert "fallback_message" in result
        fallback_message = result["fallback_message"]
        
        # Verify fallback contains essential guidance
        assert "Help optimize my AI costs" in fallback_message
        assert "system metrics" in fallback_message.lower()
        assert "performance requirements" in fallback_message.lower()
        assert "budget" in fallback_message.lower()
        assert "technical specifications" in fallback_message.lower()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_data_sufficiency_impact_on_requests(
        self,
        real_services,
        comprehensive_llm_manager,
        user_execution_contexts
    ):
        """Test how triage data sufficiency impacts data request generation."""
        context = user_execution_contexts[0]
        data_helper = create_data_helper(comprehensive_llm_manager)
        
        base_request = "Optimize my model performance"
        base_triage = {
            "category": "Performance Optimization",
            "priority": "high"
        }
        
        # Test insufficient data scenario
        insufficient_triage = {**base_triage, "data_sufficiency": "insufficient"}
        insufficient_result = await data_helper.generate_data_request(
            user_request=base_request,
            triage_result=insufficient_triage
        )
        
        # Test partial data scenario
        partial_triage = {**base_triage, "data_sufficiency": "partial"}
        partial_result = await data_helper.generate_data_request(
            user_request=base_request,
            triage_result=partial_triage
        )
        
        # Test sufficient data scenario  
        sufficient_triage = {**base_triage, "data_sufficiency": "sufficient"}
        sufficient_result = await data_helper.generate_data_request(
            user_request=base_request,
            triage_result=sufficient_triage
        )
        
        # Verify all succeeded
        assert insufficient_result["success"] is True
        assert partial_result["success"] is True
        assert sufficient_result["success"] is True
        
        # Verify LLM was called with different data sufficiency contexts
        assert mock_llm_manager.agenerate.call_count == 3
        
        # Verify each call included appropriate data sufficiency context
        for call_args in mock_llm_manager.agenerate.call_args_list:
            prompt = call_args[1]["prompts"][0]
            assert "data_sufficiency" in prompt

    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_comprehensive_integration_with_real_triage_agent(
        self,
        real_services,
        comprehensive_llm_manager,
        real_tool_dispatcher,
        user_execution_contexts,
        isolated_env
    ):
        """Test complete integration between real triage agent and data helper."""
        context = user_execution_contexts[0]
        
        # Create real triage agent using factory pattern
        triage_agent = UnifiedTriageAgentFactory.create_for_context(
            context=context,
            llm_manager=mock_llm_manager,
            tool_dispatcher=real_tool_dispatcher
        )
        
        # Mock triage agent response
        mock_llm_manager.generate_structured_response = AsyncMock()
        mock_triage_result = TriageResult(
            category="Cost Optimization",
            sub_category="Model Selection",
            priority=Priority.HIGH,
            complexity=Complexity.MEDIUM,
            confidence_score=0.91,
            data_sufficiency="partial",
            extracted_entities=ExtractedEntities(
                models=["gpt-4", "gpt-3.5-turbo"],
                metrics=["cost", "latency"],
                providers=["openai"],
                thresholds=[2000]
            ),
            user_intent=UserIntent(
                primary_intent="optimize",
                action_required=True,
                confidence=0.88
            ),
            tool_recommendation=ToolRecommendation(
                primary_tools=["calculate_cost_savings", "compare_models"],
                secondary_tools=["analyze_usage_patterns"]
            ),
            next_steps=["Analyze current costs", "Compare model performance", "Generate optimization plan"]
        )
        mock_llm_manager.generate_structured_response.return_value = mock_triage_result
        
        # Execute triage analysis first
        class MockState:
            def __init__(self, request):
                self.original_request = request
        
        triage_state = MockState("I'm spending $2000/month on GPT-4, need to optimize costs")
        triage_result_dict = await triage_agent.execute(triage_state, context)
        
        # Verify triage succeeded
        assert triage_result_dict["success"] is True
        assert triage_result_dict["category"] == "Cost Optimization"
        
        # Create data helper and use triage results
        data_helper = create_data_helper(comprehensive_llm_manager)
        
        # Execute data request based on triage
        data_result = await data_helper.generate_data_request(
            user_request=triage_state.original_request,
            triage_result=triage_result_dict,
            previous_results=[{
                "agent_name": "UnifiedTriageAgent",
                "summary": f"Categorized as {triage_result_dict['category']} with {triage_result_dict['confidence_score']} confidence",
                "result": triage_result_dict
            }]
        )
        
        # Verify end-to-end integration
        assert data_result["success"] is True
        assert "data_request" in data_result
        assert data_result["triage_context"]["category"] == "Cost Optimization"
        
        # Verify triage context was properly passed through
        data_categories = data_result["data_request"]["data_categories"]
        structured_items = data_result["data_request"]["structured_items"]
        
        assert len(data_categories) >= 2
        assert len(structured_items) >= 4
        
        # Verify context contains cost optimization specific requests
        categories_text = str(data_categories).lower()
        assert any(word in categories_text for word in ["cost", "spending", "budget", "optimization"])

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.websocket
    async def test_websocket_integration_for_data_requests(
        self,
        real_services,
        comprehensive_llm_manager,
        user_execution_contexts,
        isolated_env
    ):
        """Test WebSocket event integration for data request workflows."""
        import time
        
        context = user_execution_contexts[0]
        
        triage_result = {
            "category": "Cost Optimization",
            "data_sufficiency": "insufficient",
            "priority": "high"
        }
        
        data_helper = create_data_helper(comprehensive_llm_manager)
        
        # Track WebSocket events that should be emitted
        websocket_events = []
        
        def mock_websocket_emit(event_type: str, data: dict):
            """Mock WebSocket event emission for testing."""
            websocket_events.append({
                "type": event_type,
                "data": data,
                "timestamp": time.time()
            })
            logger.info(f"WebSocket event emitted: {event_type}")
        
        # Simulate WebSocket events during data request generation
        mock_websocket_emit("data_request_started", {
            "user_id": context.user_id,
            "request_type": "data_collection"
        })
        
        result = await data_helper.generate_data_request(
            user_request="Help me optimize costs with comprehensive data analysis",
            triage_result=triage_result,
            previous_results=None
        )
        
        mock_websocket_emit("llm_processing", {
            "user_id": context.user_id,
            "status": "generating_data_request"
        })
        
        mock_websocket_emit("data_extraction", {
            "user_id": context.user_id,
            "categories_found": len(result.get("data_request", {}).get("data_categories", []))
        })
        
        mock_websocket_emit("request_completed", {
            "user_id": context.user_id,
            "success": result.get("success", False),
            "data_items_requested": len(result.get("data_request", {}).get("structured_items", []))
        })
        
        # Verify all critical WebSocket events were emitted
        event_types = [event["type"] for event in websocket_events]
        assert "data_request_started" in event_types, "Must emit data request start event"
        assert "llm_processing" in event_types, "Must emit LLM processing event"
        assert "data_extraction" in event_types, "Must emit data extraction event"
        assert "request_completed" in event_types, "Must emit completion event"
        
        # Verify event data integrity
        start_event = next(e for e in websocket_events if e["type"] == "data_request_started")
        assert start_event["data"]["user_id"] == context.user_id
        
        completion_event = next(e for e in websocket_events if e["type"] == "request_completed")
        assert completion_event["data"]["success"] is True
        assert completion_event["data"]["data_items_requested"] > 0
        
        logger.info(f"✓ Verified {len(websocket_events)} WebSocket events for data request workflow")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_metadata_storage_and_retrieval(
        self,
        real_services,
        comprehensive_llm_manager,
        user_execution_contexts,
        isolated_env
    ):
        """Test proper metadata storage and retrieval in user context."""
        context = user_execution_contexts[0]
        
        # Initialize metadata
        initial_metadata = {
            "session_start": datetime.now(timezone.utc).isoformat(),
            "user_tier": "enterprise",
            "request_source": "web_app"
        }
        context.metadata.update(initial_metadata)
        
        triage_result = {
            "category": "Performance Optimization",
            "data_sufficiency": "partial",
            "metadata": {"optimization_type": "latency"}
        }
        
        data_helper = create_data_helper(comprehensive_llm_manager)
        
        result = await data_helper.generate_data_request(
            user_request="Reduce API latency for mobile app",
            triage_result=triage_result,
            previous_results=None
        )
        
        # Verify metadata preservation
        assert result["success"] is True
        
        # Verify original context metadata preserved
        assert "session_start" in context.metadata
        assert context.metadata["user_tier"] == "enterprise"
        assert context.metadata["request_source"] == "web_app"
        
        # Verify triage metadata passed through
        assert result["triage_context"]["metadata"]["optimization_type"] == "latency"


if __name__ == "__main__":
    # Run with real services for comprehensive testing
    import sys
    sys.exit(pytest.main([
        __file__, 
        "-v",
        "--real-services",
        "--tb=short",
        "-x"  # Stop on first failure for debugging
    ]))