"""Integration tests for OptimizationsCoreSubAgent with REAL LLM usage.

These tests validate actual optimization recommendation generation using real LLM,
real services, and actual system components - NO MOCKS.

Business Value: Ensures optimization recommendations deliver promised cost savings.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.core.isolated_environment import IsolatedEnvironment
from netra_backend.app.database import get_async_session
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

# Real environment configuration
env = IsolatedEnvironment()


@pytest.fixture
async def real_llm_manager():
    """Get real LLM manager instance with actual API credentials."""
    llm_manager = LLMManager()
    await llm_manager.initialize()
    yield llm_manager
    await llm_manager.cleanup()


@pytest.fixture
async def real_tool_dispatcher(real_llm_manager):
    """Get real tool dispatcher with actual tools loaded."""
    dispatcher = ToolDispatcher(llm_manager=real_llm_manager)
    return dispatcher


@pytest.fixture
async def real_optimization_agent(real_llm_manager, real_tool_dispatcher):
    """Create real OptimizationsCoreSubAgent instance."""
    agent = OptimizationsCoreSubAgent(
        llm_manager=real_llm_manager,
        tool_dispatcher=real_tool_dispatcher,
        websocket_manager=None  # Real websocket in production
    )
    yield agent
    await agent.cleanup()


class TestOptimizationsCoreAgentRealLLM:
    """Test suite for OptimizationsCoreSubAgent with real LLM interactions."""
    
    @pytest.mark.integration
    @pytest.mark.real_llm
    async def test_cost_optimization_recommendations_with_high_usage_patterns(
        self, real_optimization_agent, db_session
    ):
        """Test 1: Generate cost optimization for high-usage AI workloads using real LLM."""
        # Prepare real data context
        state = DeepAgentState(
            run_id="test_cost_opt_001",
            user_query="Analyze my GPT-4 usage and recommend cost optimizations",
            triage_result={
                "intent": "cost_optimization",
                "entities": ["gpt-4", "cost", "optimization"],
                "confidence": 0.95
            },
            data_result={
                "cost_breakdown": [
                    {
                        "model": "gpt-4",
                        "daily_cost": 450.00,
                        "request_count": 15000,
                        "avg_tokens": 2500,
                        "peak_hours": ["09:00-11:00", "14:00-16:00"]
                    },
                    {
                        "model": "gpt-3.5-turbo",
                        "daily_cost": 25.00,
                        "request_count": 50000,
                        "avg_tokens": 800
                    }
                ],
                "usage_patterns": {
                    "peak_load": "10am-4pm EST",
                    "low_usage": "12am-6am EST",
                    "weekly_pattern": "Mon-Fri heavy, weekends light"
                }
            }
        )
        
        context = ExecutionContext(
            state=state,
            request_id="req_001",
            user_id="enterprise_customer_001"
        )
        
        # Execute real LLM analysis
        result = await real_optimization_agent.execute(context)
        
        # Validate real optimization recommendations
        assert result["status"] == "success"
        assert "recommendations" in result
        assert len(result["recommendations"]) > 0
        
        # Check for specific optimization strategies
        recommendations_text = json.dumps(result["recommendations"]).lower()
        assert any([
            "batch" in recommendations_text,
            "cache" in recommendations_text,
            "gpt-3.5" in recommendations_text,
            "off-peak" in recommendations_text
        ])
        
        # Verify cost savings projection exists
        assert "projected_savings" in result
        assert result["projected_savings"]["percentage"] >= 10.0
        
        logger.info(f"Generated {len(result['recommendations'])} optimization recommendations")
    
    @pytest.mark.integration
    @pytest.mark.real_llm
    async def test_model_selection_optimization_with_quality_constraints(
        self, real_optimization_agent, db_session
    ):
        """Test 2: Optimize model selection while maintaining quality using real LLM."""
        state = DeepAgentState(
            run_id="test_model_opt_002",
            user_query="Optimize my model selection for customer support chatbot maintaining 95% accuracy",
            triage_result={
                "intent": "model_optimization",
                "entities": ["model", "accuracy", "customer_support"],
                "confidence": 0.92
            },
            data_result={
                "current_performance": {
                    "model": "gpt-4",
                    "accuracy": 0.97,
                    "latency_p95": 2.5,
                    "cost_per_request": 0.08,
                    "daily_requests": 25000
                },
                "quality_metrics": {
                    "customer_satisfaction": 0.94,
                    "resolution_rate": 0.89,
                    "escalation_rate": 0.11
                },
                "alternative_models": [
                    {"model": "gpt-3.5-turbo-16k", "estimated_accuracy": 0.93},
                    {"model": "claude-2", "estimated_accuracy": 0.95},
                    {"model": "mixtral-8x7b", "estimated_accuracy": 0.91}
                ]
            }
        )
        
        context = ExecutionContext(
            state=state,
            request_id="req_002",
            user_id="support_team_001"
        )
        
        # Execute real model optimization analysis
        result = await real_optimization_agent.execute(context)
        
        assert result["status"] == "success"
        assert "model_recommendations" in result
        
        # Verify quality-aware recommendations
        for rec in result["model_recommendations"]:
            if "accuracy" in rec:
                assert rec["accuracy"] >= 0.95  # Maintains quality constraint
        
        # Check for tiered approach
        assert "tiering_strategy" in result or "routing_strategy" in result
        
        logger.info(f"Model optimization maintained {result.get('expected_accuracy', 0):.2%} accuracy")
    
    @pytest.mark.integration
    @pytest.mark.real_llm
    async def test_prompt_optimization_for_token_reduction(
        self, real_optimization_agent, db_session
    ):
        """Test 3: Generate prompt optimization strategies using real LLM."""
        state = DeepAgentState(
            run_id="test_prompt_opt_003",
            user_query="How can I reduce token usage in my document summarization prompts?",
            triage_result={
                "intent": "prompt_optimization",
                "entities": ["tokens", "summarization", "prompts"],
                "confidence": 0.88
            },
            data_result={
                "current_prompts": {
                    "avg_prompt_tokens": 3500,
                    "avg_completion_tokens": 1200,
                    "prompt_samples": [
                        "Please carefully read and thoroughly analyze the following document...",
                        "You are an expert AI assistant specializing in comprehensive document analysis..."
                    ]
                },
                "token_distribution": {
                    "system_prompt": 1500,
                    "user_context": 1200,
                    "actual_content": 800
                }
            }
        )
        
        context = ExecutionContext(
            state=state,
            request_id="req_003",
            user_id="content_team_001"
        )
        
        # Execute prompt optimization with real LLM
        result = await real_optimization_agent.execute(context)
        
        assert result["status"] == "success"
        assert "prompt_optimizations" in result
        
        # Verify token reduction strategies
        assert "token_reduction_percentage" in result
        assert result["token_reduction_percentage"] >= 20.0
        
        # Check for specific techniques
        optimization_content = json.dumps(result).lower()
        optimization_techniques = [
            "compression", "template", "few-shot", "instruction",
            "concise", "restructure", "eliminate"
        ]
        assert any(tech in optimization_content for tech in optimization_techniques)
        
        logger.info(f"Prompt optimization achieved {result['token_reduction_percentage']:.1f}% reduction")
    
    @pytest.mark.integration
    @pytest.mark.real_llm
    async def test_workload_batching_optimization(
        self, real_optimization_agent, db_session
    ):
        """Test 4: Optimize AI workload batching strategies using real LLM."""
        state = DeepAgentState(
            run_id="test_batch_opt_004",
            user_query="Optimize batching for my real-time translation service",
            triage_result={
                "intent": "performance_optimization",
                "entities": ["batching", "translation", "real-time"],
                "confidence": 0.90
            },
            data_result={
                "workload_profile": {
                    "request_pattern": "bursty",
                    "avg_requests_per_second": 150,
                    "peak_requests_per_second": 500,
                    "avg_text_length": 125,
                    "latency_requirement_ms": 200
                },
                "current_batching": {
                    "enabled": False,
                    "requests_processed_individually": True,
                    "avg_latency_ms": 180,
                    "p99_latency_ms": 450
                },
                "infrastructure": {
                    "gpu_available": True,
                    "max_batch_size": 32,
                    "processing_time_per_batch_ms": 50
                }
            }
        )
        
        context = ExecutionContext(
            state=state,
            request_id="req_004",
            user_id="translation_service_001"
        )
        
        # Execute batching optimization with real LLM
        result = await real_optimization_agent.execute(context)
        
        assert result["status"] == "success"
        assert "batching_strategy" in result
        
        # Verify batching parameters
        strategy = result["batching_strategy"]
        assert "optimal_batch_size" in strategy
        assert "wait_timeout_ms" in strategy
        assert strategy["wait_timeout_ms"] <= 50  # Respects latency requirements
        
        # Check for adaptive batching
        assert "adaptive_rules" in strategy or "dynamic_adjustment" in result
        
        # Verify performance improvements
        assert "expected_improvements" in result
        improvements = result["expected_improvements"]
        assert improvements["throughput_increase_percentage"] >= 30.0
        
        logger.info(f"Batching optimization: {strategy['optimal_batch_size']} batch size")
    
    @pytest.mark.integration
    @pytest.mark.real_llm
    async def test_multi_region_deployment_optimization(
        self, real_optimization_agent, db_session
    ):
        """Test 5: Optimize multi-region AI deployment using real LLM analysis."""
        state = DeepAgentState(
            run_id="test_region_opt_005",
            user_query="Optimize my global AI service deployment across regions",
            triage_result={
                "intent": "infrastructure_optimization",
                "entities": ["deployment", "regions", "global"],
                "confidence": 0.87
            },
            data_result={
                "regional_usage": {
                    "us-east": {"requests": 450000, "latency_ms": 45, "cost": 2800},
                    "eu-west": {"requests": 380000, "latency_ms": 120, "cost": 2400},
                    "ap-southeast": {"requests": 290000, "latency_ms": 180, "cost": 1900},
                    "sa-east": {"requests": 80000, "latency_ms": 250, "cost": 600}
                },
                "current_deployment": {
                    "primary_region": "us-east",
                    "replicas": ["eu-west"],
                    "cdn_enabled": False,
                    "edge_caching": False
                },
                "compliance_requirements": {
                    "data_residency": ["eu-west requires local processing"],
                    "latency_sla_ms": 150
                }
            }
        )
        
        context = ExecutionContext(
            state=state,
            request_id="req_005",
            user_id="global_platform_001"
        )
        
        # Execute regional optimization with real LLM
        result = await real_optimization_agent.execute(context)
        
        assert result["status"] == "success"
        assert "regional_strategy" in result
        
        # Verify multi-region recommendations
        strategy = result["regional_strategy"]
        assert "recommended_regions" in strategy
        assert len(strategy["recommended_regions"]) >= 2
        
        # Check for edge optimization
        assert any([
            "edge" in json.dumps(result).lower(),
            "cdn" in json.dumps(result).lower(),
            "cache" in json.dumps(result).lower()
        ])
        
        # Verify compliance awareness
        assert "compliance_adherence" in result
        assert result["compliance_adherence"]["data_residency_compliant"] == True
        
        # Check cost-latency trade-offs
        assert "trade_off_analysis" in result
        assert "cost_impact" in result["trade_off_analysis"]
        assert "latency_improvement" in result["trade_off_analysis"]
        
        logger.info(f"Regional optimization: {len(strategy['recommended_regions'])} regions recommended")


if __name__ == "__main__":
    # Run tests with real services
    asyncio.run(pytest.main([__file__, "-v", "--real-llm"]))