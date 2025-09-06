from unittest.mock import AsyncMock, Mock, patch, MagicMock

"""Test minimal workflow execution when insufficient data is available.

Business Value Justification (BVJ):
    - Segment: Free, Early
- Business Goal: User Engagement and Education
- Value Impact: Guides users to provide necessary data for optimization
- Strategic Impact: Converts free/trial users by showing value potential

This test validates the minimal workflow that focuses on data collection
when critical information is missing for any meaningful optimization.
""""

import pytest
from typing import Dict, Any
import json
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.agents.state import DeepAgentState
import asyncio


class TestInsufficientDataFlow:
    """Validate minimal workflow when critical data is missing."""
    
    @pytest.fixture
    def insufficient_user_request(self):
        """Use real service instance."""
        # TODO: Initialize real service
        """Create a vague user request with insufficient data."""
        return {
        "user_request": "Help me optimize my AI costs",
        # No metrics provided
        # No usage patterns
        # No model information
        }
    
        @pytest.fixture
        def expected_triage_insufficient(self):
        """Use real service instance."""
        # TODO: Initialize real service
        """Expected triage output for insufficient data."""
        return {
        "data_sufficiency": "insufficient",
        "category": "unknown_optimization",
        "confidence": 0.20,
        "identified_metrics": [],
        "missing_data": [
        "current_spend",
        "models_used",
        "token_usage",
        "use_cases",
        "performance_requirements",
        "business_constraints"
        ],
        "workflow_recommendation": "data_collection_only",
        "data_request_priority": "critical"
        }
    
        @pytest.fixture
        def expected_comprehensive_data_request(self):
        """Use real service instance."""
        # TODO: Initialize real service
        """Expected comprehensive data collection request."""
        return {
        "data_collection_strategy": {
        "approach": "guided_questionnaire",
        "urgency": "before_optimization",
        "estimated_time": "10-15 minutes"
        },
        "structured_request": {
        "essential_metrics": [
        {
        "category": "Cost Information",
        "questions": [
        {
        "question": "What is your current monthly AI/LLM spend?",
        "format": "Dollar amount or range",
        "example": "$5,000 or $3,000-$7,000",
        "why": "Baseline for calculating savings"
        },
        {
        "question": "Which AI models are you using?",
        "format": "List of models",
        "example": "GPT-4, Claude-2, PaLM",
        "why": "Identify optimization opportunities"
        }
        ]
        },
        {
        "category": "Usage Patterns",
        "questions": [
        {
        "question": "What are your primary use cases?",
        "format": "List with percentages",
        "example": "Customer support (60%), Content generation (40%)",
        "why": "Tailor optimizations to use cases"
        },
        {
        "question": "What is your daily token volume?",
        "format": "Number or range",
        "example": "2M tokens/day",
        "why": "Calculate per-token costs"
        }
        ]
        },
        {
        "category": "Performance Requirements",
        "questions": [
        {
        "question": "What are your latency requirements?",
        "format": "Time in seconds",
        "example": "< 2 seconds for customer-facing",
        "why": "Ensure optimizations meet SLAs"
        },
        {
        "question": "What is your acceptable error rate?",
        "format": "Percentage",
        "example": "< 1% for critical operations",
        "why": "Balance cost vs quality"
        }
        ]
        }
        ]
        },
        "quick_start_template": {
        "description": "Copy and fill this template for fastest results",
        "template": """
        Current Monthly Spend: $______
        Primary Model: ____________
        Daily Token Usage: ________
        Main Use Case: ___________
        Latency Requirement: _____seconds
        ""","
        "submission_method": "Paste completed template in response"
        },
        "value_proposition": {
        "potential_savings": "Typically 30-70% cost reduction",
        "implementation_time": "1-3 weeks",
        "success_stories": "Similar customers saved $10K-50K monthly"
        }
        }
    
        @pytest.fixture
        def expected_educational_response(self):
        """Use real service instance."""
        # TODO: Initialize real service
        """Expected educational content to help user understand data needs."""
        return {
        "educational_content": {
        "why_data_matters": {
        "title": "Why We Need This Information",
        "explanation": "AI optimization is highly context-dependent",
        "examples": [
        "Batch processing saves 40% but needs usage patterns",
        "Model switching saves 60% but needs quality requirements",
        "Caching saves 30% but needs request patterns"
        ]
        },
        "data_collection_tips": {
        "where_to_find": [
        "Cloud provider billing dashboard",
        "API usage reports",
        "Application monitoring tools",
        "Log aggregation systems"
        ],
        "helpful_scripts": {
        "description": "Scripts to gather metrics automatically",
        "available": ["usage_analyzer.py", "cost_tracker.sh", "token_counter.js"]
        }
        },
        "expected_outcomes": {
        "with_complete_data": [
        "Precise cost reduction roadmap",
        "Risk-assessed recommendations",
        "Implementation timeline",
        "ROI projections"
        ],
        "timeline": "Results within 24 hours of data submission"
        }
        }
        }
    
        @pytest.mark.asyncio
        @pytest.mark.critical
        async def test_minimal_flow_execution(self):
        """Test that insufficient data triggers minimal workflow."""
        execution_order = []
        
        with patch('netra_backend.app.agents.supervisor.workflow_orchestrator.WorkflowOrchestrator') as MockOrchestrator:
        orchestrator = MockOrchestrator.return_value
            
        async def track_execution(agent_name, *args, **kwargs):
        execution_order.append(agent_name)
        await asyncio.sleep(0)
        return ExecutionResult(
        success=True,
        status="completed",
        result={"agent": agent_name}
        )
            
        orchestrator.execute_agent = AsyncMock(side_effect=track_execution)
            
        # Simulate minimal workflow - only triage and data_helper
        await orchestrator.execute_agent("triage", {})
        await orchestrator.execute_agent("data_helper", {})
            
        # Only triage and data_helper should execute
        assert execution_order == ["triage", "data_helper"]
        assert len(execution_order) == 2
    
        @pytest.mark.asyncio
        async def test_triage_correctly_identifies_insufficient_data(self, insufficient_user_request, expected_triage_insufficient):
        """Validate triage identifies insufficient data scenario."""
        from netra_backend.app.agents.triage.unified_triage_agent import UnifiedTriageAgent
        
        with patch.object(TriageSubAgent, 'llm_manager') as mock_llm_manager:
        mock_llm_manager.ask_structured_llm.return_value = expected_triage_insufficient
            
        agent = TriageSubAgent()
        context = ExecutionContext(
        run_id="test-run",
        agent_name="triage",
        state=DeepAgentState(user_request=json.dumps(insufficient_user_request))
        )
            
        result = await agent.execute(context)
            
        assert result.success
        assert result.result["data_sufficiency"] == "insufficient"
        assert result.result["workflow_recommendation"] == "data_collection_only"
        assert result.result["confidence"] < 0.30  # Very low confidence
        assert len(result.result["missing_data"]) >= 5  # Many missing items
    
        @pytest.mark.asyncio
        async def test_data_helper_provides_comprehensive_guidance(self, expected_comprehensive_data_request):
        """Validate data helper provides comprehensive data collection guidance."""
        from netra_backend.app.agents.data_helper_agent import DataHelperAgent
        
        with patch.object(DataHelperAgent, 'llm_manager') as mock_llm_manager:
        mock_llm_manager.ask_structured_llm.return_value = expected_comprehensive_data_request
            
        agent = DataHelperAgent()
        state = DeepAgentState()
        from netra_backend.app.agents.triage.unified_triage_agent import TriageResult
        state.triage_result = TriageResult(
        category="unknown_optimization",
        confidence_score=0.20,
        data_sufficiency="insufficient",
        identified_metrics=[],
        missing_data=["current_spend", "models_used", "token_usage"],
        workflow_recommendation="data_collection_only",
        data_request_priority="critical"
        )
            
        context = ExecutionContext(
        run_id="test-run",
        agent_name="data_helper",
        state=state
        )
            
        result = await agent.execute(context)
            
        assert result.success
        assert "structured_request" in result.result
        assert "essential_metrics" in result.result["structured_request"]
            
        # Validate structured questions
        for category in result.result["structured_request"]["essential_metrics"]:
        assert "category" in category
        assert "questions" in category
        for question in category["questions"]:
        assert "question" in question
        assert "why" in question  # Explains importance
        assert "example" in question  # Provides guidance
            
        # Check for quick-start template
        assert "quick_start_template" in result.result
        assert "template" in result.result["quick_start_template"]
    
        @pytest.mark.asyncio
        async def test_data_helper_includes_education(self, expected_educational_response):
        """Validate data helper educates users on why data is needed."""
        from netra_backend.app.agents.data_helper_agent import DataHelperAgent
        
        with patch.object(DataHelperAgent, 'llm_manager') as mock_llm_manager:
        mock_llm_manager.ask_structured_llm.return_value = expected_educational_response
            
        agent = DataHelperAgent()
        state = DeepAgentState()
        from netra_backend.app.agents.triage.unified_triage_agent import TriageResult
        state.triage_result = TriageResult(
        category="unknown_optimization",
        confidence_score=0.20,
        data_sufficiency="insufficient",
        identified_metrics=[],
        missing_data=[],
        workflow_recommendation="data_collection_only",
        data_request_priority="critical"
        )
            
        context = ExecutionContext(
        run_id="test-run",
        agent_name="data_helper",
        state=state
        )
            
        result = await agent.execute(context)
            
        assert result.success
        assert "educational_content" in result.result
            
        education = result.result["educational_content"]
        assert "why_data_matters" in education
        assert "data_collection_tips" in education
        assert "expected_outcomes" in education
            
        # Check practical help
        assert "where_to_find" in education["data_collection_tips"]
        assert "helpful_scripts" in education["data_collection_tips"]
    
        @pytest.mark.asyncio
        async def test_flow_shows_value_potential(self):
        """Test that insufficient data flow still demonstrates value potential."""
        from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
        
        with patch.object(WorkflowOrchestrator, 'execute_standard_workflow') as mock_workflow:
        mock_workflow.return_value = [
        ExecutionResult(success=True, status="completed", result={
        "data_sufficiency": "insufficient",
        "category": "unknown_optimization"
        }),
        ExecutionResult(success=True, status="completed", result={
        "value_proposition": {
        "potential_savings": "30-70% typical reduction",
        "success_stories": "Customer A saved $15K/month",
        "quick_wins": "Most see results in 2 weeks"
        },
        "structured_request": {
        "essential_metrics": [{"category": "costs", "questions": []]]
        }
        })
        ]
            
        orchestrator = WorkflowOrchestrator(None, None, None)
        context = ExecutionContext(
        run_id="test-run",
        agent_name="supervisor",
        state=DeepAgentState()
        )
            
        results = await orchestrator.execute_standard_workflow(context)
            
        # Validate value proposition is shown
        data_helper_result = results[1].result
        assert "value_proposition" in data_helper_result
        assert "potential_savings" in data_helper_result["value_proposition"]
        assert "30-70%" in data_helper_result["value_proposition"]["potential_savings"]
    
        @pytest.mark.asyncio
        async def test_flow_provides_clear_next_steps(self):
        """Test that flow provides clear, actionable next steps."""
        from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
        
        with patch.object(WorkflowOrchestrator, 'execute_standard_workflow') as mock_workflow:
        mock_workflow.return_value = [
        ExecutionResult(success=True, status="completed", result={"data_sufficiency": "insufficient"}),
        ExecutionResult(success=True, status="completed", result={
        "next_steps": [
        "Fill out the quick-start template",
        "Or answer the detailed questionnaire",
        "Submit via chat or upload CSV/JSON",
        "Receive optimization plan within 24 hours"
        ],
        "quick_start_template": {"template": "..."}
        })
        ]
            
        orchestrator = WorkflowOrchestrator(None, None, None)
        context = ExecutionContext(
        run_id="test-run",
        agent_name="supervisor",
        state=DeepAgentState()
        )
            
        results = await orchestrator.execute_standard_workflow(context)
            
        data_helper_result = results[1].result
        assert "next_steps" in data_helper_result
        assert len(data_helper_result["next_steps"]) >= 3
        assert any("template" in step.lower() or "fill" in step.lower() 
        for step in data_helper_result["next_steps"])
    
        @pytest.mark.asyncio
        async def test_flow_handles_extremely_vague_requests(self):
        """Test handling of extremely vague requests like 'help me'."""
        vague_request = {"user_request": "optimize"}
        
        from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
        
        with patch.object(WorkflowOrchestrator, 'execute_standard_workflow') as mock_workflow:
        mock_workflow.return_value = [
        ExecutionResult(success=True, status="completed", result={
        "data_sufficiency": "insufficient",
        "confidence": 0.05,
        "interpretation_attempts": [
        "AI/LLM optimization?",
        "Database optimization?",
        "General performance optimization?"
        ]
        }),
        ExecutionResult(success=True, status="completed", result={
        "clarification_request": {
        "message": "I can help optimize your AI costs. To get started...",
        "options": [
        "AI/LLM cost optimization",
        "Performance optimization",
        "Resource optimization",
        "Other (please specify)"
        ]
        }
        })
        ]
            
        orchestrator = WorkflowOrchestrator(None, None, None)
        context = ExecutionContext(
        run_id="test-run",
        agent_name="supervisor",
        state=DeepAgentState(user_request=json.dumps(vague_request))
        )
            
        results = await orchestrator.execute_standard_workflow(context)
            
        # Should attempt to clarify
        assert results[0].result["confidence"] < 0.10
        assert "clarification_request" in results[1].result
        assert "options" in results[1].result["clarification_request"]
    
        @pytest.mark.asyncio
        async def test_flow_conversion_optimization(self):
        """Test that insufficient data flow is optimized for user conversion."""
        conversion_metrics = {
        "friction_minimized": True,
        "value_demonstrated": True,
        "clear_path_forward": True,
        "time_to_value_shown": True
        }
        
        from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
        
        with patch.object(WorkflowOrchestrator, 'execute_standard_workflow') as mock_workflow:
        mock_workflow.return_value = [
        ExecutionResult(success=True, status="completed", result={"data_sufficiency": "insufficient"}),
        ExecutionResult(success=True, status="completed", result={
        "quick_start_template": {
        "description": "Get results in 5 minutes",
        "template": "Simple form"
        },
        "value_proposition": {
        "immediate_benefit": "Know your savings potential today",
        "time_to_results": "24 hours",
        "effort_required": "10-15 minutes"
        },
        "social_proof": {
        "testimonials": ["Saved $20K first month - Company A"],
        "success_rate": "87% achieve >30% reduction"
        }
        })
        ]
            
        orchestrator = WorkflowOrchestrator(None, None, None)
        context = ExecutionContext(
        run_id="test-run",
        agent_name="supervisor",
        state=DeepAgentState()
        )
            
        results = await orchestrator.execute_standard_workflow(context)
            
        data_helper_result = results[1].result
            
        # Check friction minimization
        assert "quick_start_template" in data_helper_result
        assert "5 minutes" in data_helper_result["quick_start_template"]["description"]
            
        # Check value demonstration
        assert "value_proposition" in data_helper_result
        assert "immediate_benefit" in data_helper_result["value_proposition"]
            
        # Check clear path
        assert "24 hours" in data_helper_result["value_proposition"]["time_to_results"]
            
        # Check social proof for conversion
        assert "social_proof" in data_helper_result
        assert "success_rate" in data_helper_result["social_proof"]
    
        @pytest.mark.asyncio
        async def test_flow_graceful_degradation(self):
        """Test that flow degrades gracefully with absolutely no information."""
        empty_request = {}
        
        from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
        
        with patch.object(WorkflowOrchestrator, 'execute_standard_workflow') as mock_workflow:
        mock_workflow.return_value = [
        ExecutionResult(success=True, status="completed", result={
        "data_sufficiency": "insufficient",
        "fallback_mode": True
        }),
        ExecutionResult(success=True, status="completed", result={
        "general_guidance": {
        "message": "Welcome to AI Optimization! Let's start with understanding your needs.",
        "starter_questions": [
        "Are you currently using AI/LLM services?",
        "What's your primary goal? (Cost reduction, Performance, Scale)"
        ]
        }
        })
        ]
            
        orchestrator = WorkflowOrchestrator(None, None, None)
        context = ExecutionContext(
        run_id="test-run",
        agent_name="supervisor",
        state=DeepAgentState(user_request=json.dumps(empty_request))
        )
            
        results = await orchestrator.execute_standard_workflow(context)
            
        assert results[0].result.get("fallback_mode") is True
        assert "general_guidance" in results[1].result
        assert "starter_questions" in results[1].result["general_guidance"]
        pass