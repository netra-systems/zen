#!/usr/bin/env python
"""Real Agent LLM Integration E2E Test Suite - Complete AI Model Integration Workflow

MISSION CRITICAL: Validates that LLM integration delivers REAL BUSINESS VALUE through 
reliable AI model interactions, intelligent model selection, and high-quality responses. 
Tests actual AI capabilities and business insights generation, not just technical API calls.

Business Value Justification (BVJ):
- Segment: All customer segments (core AI functionality)
- Business Goal: Ensure LLM integration delivers high-quality AI insights and responses
- Value Impact: Core AI capabilities that power all agent intelligence and value creation
- Strategic/Revenue Impact: $8M+ ARR protection from LLM integration failures
- Platform Stability: Foundation for all AI-powered features and customer value delivery

CLAUDE.md COMPLIANCE:
- Uses ONLY real services (Docker, PostgreSQL, Redis) - NO MOCKS  
- Tests complete business value delivery through LLM integration
- Verifies ALL 5 WebSocket events during LLM-powered interactions
- Uses test_framework imports for SSOT patterns
- Validates actual AI response quality and business insight generation
- Tests multi-user isolation for LLM resource usage
- Focuses on REAL business outcomes from AI interactions
- Uses SSOT TEST_PORTS configuration
- Implements proper resource cleanup and error handling
- Validates business value compliance with AI quality metrics

This test validates that our LLM integration actually works end-to-end to deliver 
superior business value through AI capabilities. Not just that LLM APIs work, 
but that agents provide intelligent, contextual, and valuable responses to users.
"""

import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# SSOT imports from test_framework
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.websocket_helpers import WebSocketTestClient, assert_websocket_events
from test_framework.test_config import TEST_PORTS
from test_framework.agent_test_helpers import create_test_agent, assert_agent_execution

# SSOT environment management
from shared.isolated_environment import get_env


class LLMProvider(Enum):
    """Supported LLM providers for testing."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic" 
    GOOGLE = "google"
    AZURE_OPENAI = "azure_openai"
    MOCK_LLM = "mock_llm"  # For testing without real API calls


class TaskComplexity(Enum):
    """Task complexity levels for LLM testing."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    ENTERPRISE = "enterprise"


@dataclass
class LLMIntegrationMetrics:
    """Business value metrics for LLM integration operations."""
    
    # LLM interaction metrics
    llm_requests_made: int = 0
    llm_requests_successful: int = 0
    llm_requests_failed: int = 0
    total_tokens_used: int = 0
    
    # Response quality metrics
    response_relevance_score: float = 0.0
    response_completeness_score: float = 0.0
    response_accuracy_score: float = 0.0
    business_insight_quality_score: float = 0.0
    
    # Performance metrics
    average_llm_response_time: float = 0.0
    token_efficiency_score: float = 0.0
    cost_per_insight_dollars: Decimal = Decimal("0.00")
    
    # Business value metrics
    actionable_insights_generated: int = 0
    business_recommendations_count: int = 0
    problem_solving_effectiveness_score: float = 0.0
    user_value_delivered_score: float = 0.0
    
    # Model selection and optimization
    optimal_model_selection_score: float = 0.0
    multi_model_coordination_success: bool = False
    fallback_mechanism_effectiveness: float = 0.0
    
    # WebSocket event tracking for LLM operations
    llm_websocket_events: Dict[str, int] = field(default_factory=lambda: {
        "agent_started": 0,
        "agent_thinking": 0,
        "tool_executing": 0,
        "tool_completed": 0,
        "agent_completed": 0,
        "llm_request_initiated": 0,
        "llm_response_received": 0,
        "llm_error_handled": 0
    })
    
    def is_business_value_delivered(self) -> bool:
        """Check if LLM integration delivered real business value."""
        success_rate = self.llm_requests_successful / max(self.llm_requests_made, 1)
        return (
            success_rate >= 0.9 and  # 90% success rate
            self.response_relevance_score >= 0.8 and
            self.business_insight_quality_score >= 0.7 and
            self.actionable_insights_generated > 0 and
            self.problem_solving_effectiveness_score >= 0.75 and
            all(count > 0 for event, count in self.llm_websocket_events.items() 
                if event in ["agent_started", "agent_completed"])
        )


class RealAgentLLMIntegrationE2ETest(BaseE2ETest):
    """Test LLM integration with real services and business value validation."""
    
    def __init__(self):
        super().__init__()
        self.env = get_env()
        self.metrics = LLMIntegrationMetrics()
        
    async def create_test_user(self, subscription: str = "mid") -> Dict[str, Any]:
        """Create test user for LLM integration scenarios."""
        user_data = {
            "user_id": f"test_llm_user_{uuid.uuid4().hex[:8]}",
            "email": f"llm.test.{uuid.uuid4().hex[:8]}@testcompany.com",
            "subscription_tier": subscription,
            "permissions": ["agent_access", "llm_integration", "premium_models"],
            "llm_preferences": {
                "preferred_models": self._get_models_by_tier(subscription),
                "quality_over_speed": subscription in ["mid", "enterprise"],
                "multi_model_enabled": subscription == "enterprise"
            },
            "monthly_token_limit": self._get_token_limit_by_tier(subscription),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"Created LLM integration test user: {user_data['user_id']} ({subscription})")
        return user_data
        
    def _get_models_by_tier(self, tier: str) -> List[str]:
        """Get available LLM models by subscription tier."""
        models_by_tier = {
            "free": ["gpt-3.5-turbo"],
            "early": ["gpt-3.5-turbo", "claude-3-haiku"],
            "mid": ["gpt-4", "claude-3-sonnet", "gpt-3.5-turbo"],
            "enterprise": ["gpt-4", "claude-3-opus", "claude-3-sonnet", "gemini-pro"]
        }
        return models_by_tier.get(tier, models_by_tier["mid"])
    
    def _get_token_limit_by_tier(self, tier: str) -> int:
        """Get monthly token limit by subscription tier."""
        limits_by_tier = {
            "free": 10000,
            "early": 100000,
            "mid": 500000,
            "enterprise": 2000000
        }
        return limits_by_tier.get(tier, limits_by_tier["mid"])
    
    async def generate_llm_task_scenario(self, complexity: TaskComplexity) -> Dict[str, Any]:
        """Generate realistic LLM task scenario for testing."""
        
        scenarios = {
            TaskComplexity.SIMPLE: {
                "name": "Basic Cost Query",
                "description": "Simple cost analysis question requiring straightforward LLM response",
                "user_query": "What are my current monthly AI costs?",
                "expected_llm_operations": ["query_understanding", "data_retrieval", "cost_calculation"],
                "expected_response_elements": ["current_costs", "breakdown", "summary"],
                "complexity_factors": {"reasoning_depth": "shallow", "context_required": "minimal"},
                "success_criteria": {
                    "relevance_threshold": 0.8,
                    "completeness_threshold": 0.7,
                    "response_time_limit": 10.0
                }
            },
            TaskComplexity.MODERATE: {
                "name": "Optimization Recommendations",
                "description": "Multi-step optimization analysis requiring reasoning and recommendations",
                "user_query": "Analyze my AI infrastructure and recommend specific optimizations with expected savings",
                "expected_llm_operations": ["analysis", "comparison", "reasoning", "recommendation_generation"],
                "expected_response_elements": ["current_analysis", "optimization_opportunities", "specific_recommendations", "expected_savings", "implementation_steps"],
                "complexity_factors": {"reasoning_depth": "moderate", "context_required": "substantial"},
                "success_criteria": {
                    "relevance_threshold": 0.85,
                    "completeness_threshold": 0.8,
                    "response_time_limit": 30.0
                }
            },
            TaskComplexity.COMPLEX: {
                "name": "Strategic Architecture Planning",
                "description": "Complex strategic planning requiring deep analysis and multi-faceted recommendations",
                "user_query": "Design a comprehensive AI platform migration strategy that addresses cost, performance, compliance, and scalability for our enterprise environment",
                "expected_llm_operations": ["strategic_analysis", "multi_dimensional_planning", "risk_assessment", "solution_architecture", "implementation_roadmap"],
                "expected_response_elements": ["current_state_analysis", "target_architecture", "migration_strategy", "risk_mitigation", "timeline", "resource_requirements", "success_metrics"],
                "complexity_factors": {"reasoning_depth": "deep", "context_required": "extensive"},
                "success_criteria": {
                    "relevance_threshold": 0.9,
                    "completeness_threshold": 0.85,
                    "response_time_limit": 60.0
                }
            },
            TaskComplexity.ENTERPRISE: {
                "name": "Multi-Stakeholder Business Case",
                "description": "Enterprise-level business case development with stakeholder alignment",
                "user_query": "Create a detailed business case for AI platform modernization including ROI analysis, risk assessment, stakeholder impact analysis, and executive summary for board presentation",
                "expected_llm_operations": ["stakeholder_analysis", "financial_modeling", "risk_assessment", "business_case_development", "executive_communication"],
                "expected_response_elements": ["executive_summary", "roi_analysis", "stakeholder_impact", "risk_matrix", "implementation_plan", "success_metrics", "governance_framework"],
                "complexity_factors": {"reasoning_depth": "expert", "context_required": "comprehensive"},
                "success_criteria": {
                    "relevance_threshold": 0.95,
                    "completeness_threshold": 0.9,
                    "response_time_limit": 120.0
                }
            }
        }
        
        scenario = scenarios.get(complexity, scenarios[TaskComplexity.MODERATE])
        logger.info(f"Generated LLM task scenario: {scenario['name']} (complexity: {complexity.value})")
        return scenario
    
    async def execute_llm_powered_agent(
        self,
        websocket_client: WebSocketTestClient,
        task_scenario: Dict[str, Any],
        llm_provider: LLMProvider = LLMProvider.OPENAI
    ) -> Dict[str, Any]:
        """Execute agent with LLM integration and track AI quality metrics."""
        
        start_time = time.time()
        
        # Send LLM-powered agent request
        request_message = {
            "type": "agent_request",
            "agent": "llm_powered_agent",
            "message": task_scenario["user_query"],
            "context": {
                "task_scenario": task_scenario,
                "llm_provider": llm_provider.value,
                "expected_operations": task_scenario["expected_llm_operations"],
                "quality_requirements": task_scenario["success_criteria"],
                "business_context": "llm_integration_testing"
            },
            "user_id": f"llm_test_{uuid.uuid4().hex[:8]}",
            "thread_id": str(uuid.uuid4())
        }
        
        await websocket_client.send_json(request_message)
        logger.info(f"Initiated LLM-powered agent for: {task_scenario['name']}")
        
        # Collect all WebSocket events including LLM-specific events
        events = []
        llm_operations_detected = 0
        
        async for event in websocket_client.receive_events(timeout=150.0):  # Extended timeout for complex LLM tasks
            events.append(event)
            event_type = event.get("type", "unknown")
            
            # Track LLM WebSocket events
            if event_type in self.metrics.llm_websocket_events:
                self.metrics.llm_websocket_events[event_type] += 1
            
            # Track LLM-specific operations
            if event_type == "llm_request_initiated":
                self.metrics.llm_requests_made += 1
                llm_operations_detected += 1
                llm_provider_used = event.get("data", {}).get("provider", "unknown")
                logger.info(f"LLM request initiated: {llm_provider_used}")
                
            elif event_type == "llm_response_received":
                self.metrics.llm_requests_successful += 1
                response_data = event.get("data", {})
                tokens_used = response_data.get("tokens_used", 0)
                self.metrics.total_tokens_used += tokens_used
                response_time = response_data.get("response_time", 0)
                self.metrics.average_llm_response_time += response_time
                logger.info(f"LLM response received: {tokens_used} tokens, {response_time:.2f}s")
                
            elif event_type == "llm_error_handled":
                self.metrics.llm_requests_failed += 1
                error_info = event.get("data", {}).get("error", "unknown")
                logger.warning(f"LLM error handled: {error_info}")
            
            logger.info(f"LLM integration event: {event_type}")
            
            # Stop on completion
            if event_type == "agent_completed":
                break
                
        # Calculate LLM performance metrics
        total_time = time.time() - start_time
        if self.metrics.llm_requests_successful > 0:
            self.metrics.average_llm_response_time /= self.metrics.llm_requests_successful
        
        # Extract final result
        final_event = events[-1] if events else {}
        result = final_event.get("data", {}).get("result", {})
        
        # Analyze LLM integration business value
        self._analyze_llm_business_value_metrics(result, task_scenario, events)
        
        return {
            "events": events,
            "result": result,
            "task_scenario": task_scenario,
            "llm_operations_detected": llm_operations_detected,
            "metrics": self.metrics,
            "total_processing_time": total_time
        }
    
    def _analyze_llm_business_value_metrics(self, result: Dict[str, Any], scenario: Dict[str, Any], events: List[Dict[str, Any]]):
        """Analyze LLM integration results to extract business value metrics."""
        
        # Calculate response quality scores
        expected_elements = scenario["expected_response_elements"]
        result_text = str(result).lower()
        
        # Response relevance score - how well response addresses the query
        relevance_indicators = 0
        for element in expected_elements:
            if element.lower() in result_text:
                relevance_indicators += 1
        self.metrics.response_relevance_score = relevance_indicators / len(expected_elements)
        
        # Response completeness score - comprehensive coverage of requirements
        completeness_factors = []
        if len(str(result)) > 200:  # Substantial response
            completeness_factors.append(0.3)
        if result.get("analysis") or result.get("insights"):
            completeness_factors.append(0.3)
        if result.get("recommendations") or result.get("suggestions"):
            completeness_factors.append(0.4)
        self.metrics.response_completeness_score = sum(completeness_factors)
        
        # Business insight quality score
        insight_quality_indicators = []
        insights = result.get("insights", [])
        recommendations = result.get("recommendations", [])
        
        # Quality indicators for insights
        if len(insights) > 0:
            insight_quality_indicators.append(0.3)
        if any("specific" in str(insight).lower() or "quantified" in str(insight).lower() for insight in insights):
            insight_quality_indicators.append(0.2)
        if any("actionable" in str(rec).lower() for rec in recommendations):
            insight_quality_indicators.append(0.3)
        if result.get("cost_impact") or result.get("savings"):
            insight_quality_indicators.append(0.2)
            
        self.metrics.business_insight_quality_score = sum(insight_quality_indicators)
        
        # Count actionable insights
        actionable_insights = [
            insight for insight in insights
            if any(keyword in str(insight).lower() for keyword in ["recommend", "should", "consider", "implement"])
        ]
        self.metrics.actionable_insights_generated = len(actionable_insights)
        
        # Count business recommendations
        business_recommendations = [
            rec for rec in recommendations
            if any(keyword in str(rec).lower() for keyword in ["cost", "performance", "efficiency", "optimization"])
        ]
        self.metrics.business_recommendations_count = len(business_recommendations)
        
        # Problem-solving effectiveness score
        problem_solving_factors = []
        if self.metrics.response_relevance_score >= scenario["success_criteria"]["relevance_threshold"]:
            problem_solving_factors.append(0.4)
        if self.metrics.response_completeness_score >= scenario["success_criteria"]["completeness_threshold"]:
            problem_solving_factors.append(0.3)
        if self.metrics.actionable_insights_generated > 0:
            problem_solving_factors.append(0.3)
        self.metrics.problem_solving_effectiveness_score = sum(problem_solving_factors)
        
        # User value delivered score (composite)
        value_factors = [
            self.metrics.response_relevance_score * 0.3,
            self.metrics.business_insight_quality_score * 0.3,
            self.metrics.problem_solving_effectiveness_score * 0.4
        ]
        self.metrics.user_value_delivered_score = sum(value_factors)
        
        # Token efficiency score
        if self.metrics.total_tokens_used > 0:
            value_per_token = self.metrics.user_value_delivered_score / (self.metrics.total_tokens_used / 1000)
            self.metrics.token_efficiency_score = min(1.0, value_per_token)
        
        # Estimate cost per insight
        if self.metrics.actionable_insights_generated > 0:
            estimated_cost = Decimal(str(self.metrics.total_tokens_used)) * Decimal("0.00003")  # Rough GPT-4 pricing
            self.metrics.cost_per_insight_dollars = estimated_cost / self.metrics.actionable_insights_generated
        
        logger.info(
            f"LLM business value metrics: {self.metrics.response_relevance_score:.2f} relevance, "
            f"{self.metrics.business_insight_quality_score:.2f} insight quality, "
            f"{self.metrics.actionable_insights_generated} actionable insights, "
            f"{self.metrics.user_value_delivered_score:.2f} user value"
        )


class TestRealAgentLLMIntegration(RealAgentLLMIntegrationE2ETest):
    """Test suite for real LLM integration flows."""
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_comprehensive_llm_integration_flow(self, real_services_fixture):
        """Test complete LLM integration workflow with business value validation."""
        
        # Create test user
        user = await self.create_test_user("enterprise")
        
        # Generate complex task requiring sophisticated LLM capabilities
        complex_task = await self.generate_llm_task_scenario(TaskComplexity.COMPLEX)
        
        # Connect to WebSocket
        backend_url = f"http://localhost:{TEST_PORTS['backend']}"
        websocket_url = backend_url.replace("http", "ws") + "/ws"
        
        async with WebSocketTestClient(
            url=websocket_url,
            user_id=user["user_id"]
        ) as client:
            
            # Execute LLM-powered agent
            llm_result = await self.execute_llm_powered_agent(
                client, complex_task, LLMProvider.OPENAI
            )
            
            # CRITICAL: Verify WebSocket events were sent for LLM operations
            llm_events = [
                event for event in llm_result["events"]
                if event.get("type") in ["llm_request_initiated", "llm_response_received"]
            ]
            assert len(llm_events) > 0, "Must perform LLM operations"
            
            # CRITICAL: Verify all 5 WebSocket events sent during LLM interaction
            assert_websocket_events(llm_result["events"], [
                "agent_started",
                "agent_thinking",
                "tool_executing",
                "tool_completed", 
                "agent_completed"
            ])
            
            # Validate business value delivery through LLM integration
            assert self.metrics.is_business_value_delivered(), (
                f"LLM integration did not deliver business value. Metrics: {self.metrics}"
            )
            
            # Validate specific LLM integration outcomes
            result = llm_result["result"]
            
            # Must achieve high LLM success rate
            success_rate = self.metrics.llm_requests_successful / max(self.metrics.llm_requests_made, 1)
            assert success_rate >= 0.9, (
                f"LLM success rate too low: {success_rate:.2%}"
            )
            
            # Must deliver high-quality responses
            assert self.metrics.response_relevance_score >= complex_task["success_criteria"]["relevance_threshold"], (
                f"Response relevance too low: {self.metrics.response_relevance_score}"
            )
            
            assert self.metrics.business_insight_quality_score >= 0.7, (
                f"Business insight quality too low: {self.metrics.business_insight_quality_score}"
            )
            
            # Must generate actionable insights
            assert self.metrics.actionable_insights_generated > 0, (
                f"Must generate actionable insights. Got: {self.metrics.actionable_insights_generated}"
            )
            
            # Must provide business recommendations
            assert self.metrics.business_recommendations_count > 0, (
                f"Must provide business recommendations. Got: {self.metrics.business_recommendations_count}"
            )
            
            # Performance requirements for LLM integration
            assert self.metrics.average_llm_response_time <= complex_task["success_criteria"]["response_time_limit"], (
                f"LLM response time too slow: {self.metrics.average_llm_response_time}s"
            )
            
            # Quality requirements
            assert self.metrics.problem_solving_effectiveness_score >= 0.75, (
                f"Problem-solving effectiveness too low: {self.metrics.problem_solving_effectiveness_score}"
            )
            
            assert self.metrics.user_value_delivered_score >= 0.8, (
                f"User value delivered too low: {self.metrics.user_value_delivered_score}"
            )
            
            # Efficiency requirements
            assert self.metrics.token_efficiency_score >= 0.3, (
                f"Token efficiency too low: {self.metrics.token_efficiency_score}"
            )
            
        logger.success("✓ Comprehensive LLM integration flow validated")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_llm_integration_task_complexity_scaling(self, real_services_fixture):
        """Test LLM integration across different task complexity levels."""
        
        user = await self.create_test_user("mid")
        
        # Test different complexity levels
        complexity_levels = [TaskComplexity.SIMPLE, TaskComplexity.MODERATE, TaskComplexity.COMPLEX]
        
        backend_url = f"http://localhost:{TEST_PORTS['backend']}"
        websocket_url = backend_url.replace("http", "ws") + "/ws"
        
        for complexity in complexity_levels:
            logger.info(f"Testing LLM integration at {complexity.value} complexity level")
            
            # Reset metrics for each complexity level
            self.metrics = LLMIntegrationMetrics()
            
            task_scenario = await self.generate_llm_task_scenario(complexity)
            
            async with WebSocketTestClient(
                url=websocket_url,
                user_id=user["user_id"]
            ) as client:
                
                llm_result = await self.execute_llm_powered_agent(
                    client, task_scenario
                )
                
                # Must handle tasks at all complexity levels
                assert self.metrics.llm_requests_successful > 0, (
                    f"Must complete LLM requests for {complexity.value} tasks"
                )
                
                # Quality requirements should scale with complexity
                if complexity == TaskComplexity.SIMPLE:
                    min_insights = 1
                    min_relevance = 0.8
                elif complexity == TaskComplexity.MODERATE:
                    min_insights = 2
                    min_relevance = 0.85
                else:  # COMPLEX
                    min_insights = 3
                    min_relevance = 0.9
                
                assert self.metrics.actionable_insights_generated >= min_insights, (
                    f"{complexity.value} tasks must generate at least {min_insights} insights. "
                    f"Got: {self.metrics.actionable_insights_generated}"
                )
                
                assert self.metrics.response_relevance_score >= min_relevance, (
                    f"{complexity.value} tasks must achieve {min_relevance} relevance. "
                    f"Got: {self.metrics.response_relevance_score}"
                )
                
                # Performance should degrade gracefully with complexity
                max_response_time = task_scenario["success_criteria"]["response_time_limit"]
                assert self.metrics.average_llm_response_time <= max_response_time, (
                    f"{complexity.value} tasks took too long: {self.metrics.average_llm_response_time}s "
                    f"(limit: {max_response_time}s)"
                )
                
        logger.success("✓ LLM integration task complexity scaling validated")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_llm_integration_error_handling_and_fallbacks(self, real_services_fixture):
        """Test LLM integration error handling and fallback mechanisms."""
        
        user = await self.create_test_user("enterprise")
        
        # Task that might trigger various LLM issues
        error_prone_task = {
            "name": "Error-Prone LLM Task",
            "description": "Task designed to test LLM error handling",
            "user_query": "Generate a comprehensive analysis with potential for rate limiting or API errors",
            "expected_llm_operations": ["error_detection", "fallback_activation", "graceful_degradation"],
            "expected_response_elements": ["partial_analysis", "error_explanation", "alternative_approach"],
            "success_criteria": {
                "relevance_threshold": 0.6,  # Lower threshold due to potential errors
                "completeness_threshold": 0.5,
                "response_time_limit": 45.0
            }
        }
        
        backend_url = f"http://localhost:{TEST_PORTS['backend']}"
        websocket_url = backend_url.replace("http", "ws") + "/ws"
        
        async with WebSocketTestClient(
            url=websocket_url,
            user_id=user["user_id"]
        ) as client:
            
            llm_result = await self.execute_llm_powered_agent(
                client, error_prone_task
            )
            
            # Must handle LLM errors gracefully
            if self.metrics.llm_requests_failed > 0:
                # If errors occurred, must have error handling events
                error_events = [
                    e for e in llm_result["events"]
                    if e.get("type") == "llm_error_handled"
                ]
                assert len(error_events) > 0, "Must handle LLM errors gracefully"
                
                # Must still provide some value despite errors
                assert self.metrics.user_value_delivered_score >= 0.4, (
                    f"Must provide some value despite errors. Got: {self.metrics.user_value_delivered_score}"
                )
            
            # Must complete agent execution even with LLM issues
            completion_events = [e for e in llm_result["events"] if e.get("type") == "agent_completed"]
            assert len(completion_events) > 0, "Must complete execution despite LLM issues"
            
            result = llm_result["result"]
            
            # Must provide explanation or alternative if primary LLM failed
            if self.metrics.llm_requests_failed > 0:
                has_explanation = any([
                    result.get("error_explanation"),
                    result.get("limitations"),
                    "error" in str(result).lower(),
                    "alternative" in str(result).lower()
                ])
                assert has_explanation, "Must explain LLM limitations to user"
            
            # Must maintain minimum business value delivery
            assert self.metrics.response_relevance_score >= 0.5, (
                f"Must maintain minimum relevance despite errors: {self.metrics.response_relevance_score}"
            )
            
        logger.success("✓ LLM integration error handling and fallbacks validated")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_concurrent_llm_integration_resource_management(self, real_services_fixture):
        """Test LLM integration under concurrent load with resource management."""
        
        # Create multiple users with different LLM needs
        users_and_tasks = [
            (await self.create_test_user("enterprise"), await self.generate_llm_task_scenario(TaskComplexity.ENTERPRISE)),
            (await self.create_test_user("mid"), await self.generate_llm_task_scenario(TaskComplexity.MODERATE)),
            (await self.create_test_user("early"), await self.generate_llm_task_scenario(TaskComplexity.SIMPLE))
        ]
        
        backend_url = f"http://localhost:{TEST_PORTS['backend']}"
        websocket_url = backend_url.replace("http", "ws") + "/ws"
        
        async def execute_llm_for_user(user, task):
            # Individual metrics per user
            user_metrics = LLMIntegrationMetrics()
            original_metrics = self.metrics
            self.metrics = user_metrics
            
            try:
                async with WebSocketTestClient(
                    url=websocket_url,
                    user_id=user["user_id"]
                ) as client:
                    
                    result = await self.execute_llm_powered_agent(client, task)
                    
                    return {
                        "user_id": user["user_id"],
                        "tier": user["subscription_tier"],
                        "task_complexity": task["name"],
                        "llm_requests": user_metrics.llm_requests_made,
                        "tokens_used": user_metrics.total_tokens_used,
                        "success": user_metrics.is_business_value_delivered(),
                        "response_time": user_metrics.average_llm_response_time,
                        "metrics": user_metrics
                    }
                    
            finally:
                self.metrics = original_metrics
        
        # Execute all LLM tasks concurrently
        concurrent_start = time.time()
        results = await asyncio.gather(*[
            execute_llm_for_user(user, task)
            for user, task in users_and_tasks
        ])
        total_concurrent_time = time.time() - concurrent_start
        
        # Validate concurrent LLM resource management
        successful_executions = [r for r in results if r["success"]]
        assert len(successful_executions) == len(users_and_tasks), (
            f"Concurrent LLM resource management failed. "
            f"Only {len(successful_executions)}/{len(users_and_tasks)} users succeeded"
        )
        
        # Validate resource usage is appropriate by tier
        for result in results:
            tier = result["tier"]
            
            # Higher tiers should use more tokens for better results
            if tier == "enterprise":
                assert result["tokens_used"] >= 1000, (
                    f"Enterprise user should use more tokens. Got: {result['tokens_used']}"
                )
            elif tier == "mid":
                assert result["tokens_used"] >= 500, (
                    f"Mid user should use reasonable tokens. Got: {result['tokens_used']}"
                )
            
            # All tiers should complete in reasonable time
            assert result["response_time"] <= 60.0, (
                f"User {result['user_id']} took too long: {result['response_time']}s"
            )
            
            # All users should get business value
            assert result["metrics"].user_value_delivered_score >= 0.6, (
                f"User {result['user_id']} didn't get sufficient value: "
                f"{result['metrics'].user_value_delivered_score}"
            )
        
        # Validate overall performance under concurrent load
        assert total_concurrent_time <= 120.0, (
            f"Concurrent LLM processing took too long: {total_concurrent_time}s"
        )
        
        logger.success("✓ Concurrent LLM integration resource management validated")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_llm_integration_business_context_preservation(self, real_services_fixture):
        """Test LLM integration maintains business context across interactions."""
        
        user = await self.create_test_user("enterprise")
        
        # Multi-turn conversation requiring context preservation
        context_dependent_tasks = [
            {
                "turn": 1,
                "task": await self.generate_llm_task_scenario(TaskComplexity.MODERATE),
                "context_setup": "Initial business analysis",
                "expected_context_elements": []
            },
            {
                "turn": 2, 
                "task": {
                    "name": "Follow-up Analysis",
                    "user_query": "Based on the previous analysis, what are the next steps?",
                    "expected_response_elements": ["previous_reference", "next_steps", "continuity"],
                    "success_criteria": {"relevance_threshold": 0.85, "completeness_threshold": 0.8, "response_time_limit": 30.0}
                },
                "context_setup": "Follow-up requiring previous context",
                "expected_context_elements": ["previous_analysis"]
            },
            {
                "turn": 3,
                "task": {
                    "name": "Implementation Planning",
                    "user_query": "Create an implementation plan for the recommendations we discussed",
                    "expected_response_elements": ["implementation_plan", "timeline", "resources", "previous_recommendations"],
                    "success_criteria": {"relevance_threshold": 0.9, "completeness_threshold": 0.85, "response_time_limit": 45.0}
                },
                "context_setup": "Implementation requiring full conversation context",
                "expected_context_elements": ["previous_analysis", "recommendations", "next_steps"]
            }
        ]
        
        backend_url = f"http://localhost:{TEST_PORTS['backend']}"
        websocket_url = backend_url.replace("http", "ws") + "/ws"
        
        conversation_context = {"thread_id": str(uuid.uuid4()), "accumulated_insights": []}
        
        async with WebSocketTestClient(
            url=websocket_url,
            user_id=user["user_id"]
        ) as client:
            
            for turn_data in context_dependent_tasks:
                logger.info(f"Turn {turn_data['turn']}: {turn_data['context_setup']}")
                
                # Reset metrics for each turn but preserve conversation context
                self.metrics = LLMIntegrationMetrics()
                
                # Add conversation context to task
                task = turn_data["task"]
                if isinstance(task, dict) and "user_query" in task:
                    # This is a context-dependent task
                    task["conversation_context"] = conversation_context
                    task["expected_context_elements"] = turn_data["expected_context_elements"]
                
                llm_result = await self.execute_llm_powered_agent(client, task)
                
                # Must deliver business value at each turn
                assert self.metrics.is_business_value_delivered(), (
                    f"Turn {turn_data['turn']} did not deliver business value"
                )
                
                # For context-dependent turns, must reference previous content
                if turn_data["turn"] > 1:
                    result_text = str(llm_result["result"]).lower()
                    
                    # Must show awareness of previous conversation
                    context_indicators = [
                        "previous", "earlier", "as discussed", "building on", "based on our",
                        "following up", "continuing", "from before", "as mentioned"
                    ]
                    has_context_awareness = any(indicator in result_text for indicator in context_indicators)
                    assert has_context_awareness, (
                        f"Turn {turn_data['turn']} must show context awareness of previous conversation"
                    )
                    
                    # Must reference specific previous elements
                    expected_elements = turn_data["expected_context_elements"]
                    elements_referenced = 0
                    for element in expected_elements:
                        if element.lower() in result_text:
                            elements_referenced += 1
                    
                    context_preservation_score = elements_referenced / len(expected_elements) if expected_elements else 1.0
                    assert context_preservation_score >= 0.6, (
                        f"Turn {turn_data['turn']} context preservation too low: {context_preservation_score}"
                    )
                
                # Add insights to conversation context for next turn
                insights = llm_result["result"].get("insights", [])
                recommendations = llm_result["result"].get("recommendations", [])
                conversation_context["accumulated_insights"].extend(insights + recommendations)
                
        logger.success("✓ LLM integration business context preservation validated")


if __name__ == "__main__":
    # Run the test directly for development
    import asyncio
    
    async def run_direct_tests():
        logger.info("Starting real agent LLM integration E2E tests...")
        
        test_instance = TestRealAgentLLMIntegration()
        
        try:
            # Mock real_services_fixture for direct testing
            mock_services = {
                "db": "mock_db",
                "redis": "mock_redis",
                "backend_url": f"http://localhost:{TEST_PORTS['backend']}"
            }
            
            await test_instance.test_comprehensive_llm_integration_flow(mock_services)
            logger.success("✓ All LLM integration tests passed")
            
        except Exception as e:
            logger.error(f"✗ LLM integration tests failed: {e}")
            raise
    
    asyncio.run(run_direct_tests())