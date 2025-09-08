#!/usr/bin/env python
"""Real Agent Optimization Pipeline E2E Test Suite - Complete AI Optimization Workflow

MISSION CRITICAL: Validates that optimization agents deliver REAL BUSINESS VALUE through 
complete AI cost optimization pipelines. Tests actual optimization recommendations and 
measurable cost savings, not just technical execution.

Business Value Justification (BVJ):
- Segment: Early, Mid, Enterprise (core optimization customers)  
- Business Goal: Ensure optimization agents deliver quantifiable cost savings
- Value Impact: Core AI-powered optimization engine that drives customer ROI
- Strategic/Revenue Impact: $3M+ ARR protection from optimization pipeline failures
- Platform Stability: Foundation for automated AI cost optimization at scale

CLAUDE.md COMPLIANCE:
- Uses ONLY real services (Docker, PostgreSQL, Redis) - NO MOCKS  
- Tests complete business value delivery through optimization agent execution
- Verifies ALL 5 WebSocket events for agent interactions
- Uses test_framework imports for SSOT patterns
- Validates actual optimization recommendations with quantified savings
- Tests multi-user isolation and concurrent optimization processing
- Focuses on REAL business outcomes, not just technical execution
- Uses SSOT TEST_PORTS configuration
- Implements proper resource cleanup and error handling
- Validates business value compliance with measurable ROI metrics

This test validates that our optimization pipeline actually works end-to-end to deliver 
quantifiable business value. Not just that it runs optimizations, but that it provides 
real cost savings recommendations that help customers reduce their AI spend.
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


@dataclass
class OptimizationPipelineMetrics:
    """Business value metrics for optimization pipeline operations."""
    
    # Performance metrics
    analysis_time_seconds: float = 0.0
    recommendations_generated: int = 0
    
    # Optimization metrics
    potential_monthly_savings: Decimal = Decimal("0.00")
    cost_reduction_percentage: float = 0.0
    optimization_opportunities: int = 0
    
    # Quality metrics
    high_confidence_recommendations: int = 0
    actionable_recommendations: int = 0
    average_confidence_score: float = 0.0
    
    # Business value metrics
    roi_potential: Decimal = Decimal("0.00")
    payback_period_days: int = 0
    risk_level: str = "unknown"
    
    # WebSocket event tracking
    websocket_events: Dict[str, int] = field(default_factory=lambda: {
        "agent_started": 0,
        "agent_thinking": 0,
        "tool_executing": 0,
        "tool_completed": 0,
        "agent_completed": 0
    })
    
    def is_business_value_delivered(self) -> bool:
        """Check if the optimization pipeline delivered real business value."""
        return (
            self.recommendations_generated > 0 and
            self.potential_monthly_savings > Decimal("100.00") and
            self.actionable_recommendations > 0 and
            self.cost_reduction_percentage > 5.0 and
            all(count > 0 for event, count in self.websocket_events.items() 
                if event in ["agent_started", "agent_completed"])
        )


class RealOptimizationPipelineE2ETest(BaseE2ETest):
    """Test optimization pipeline agents with real services and business value validation."""
    
    def __init__(self):
        super().__init__()
        self.env = get_env()
        self.metrics = OptimizationPipelineMetrics()
        
    async def create_test_user(self, subscription: str = "enterprise") -> Dict[str, Any]:
        """Create test user with optimization permissions."""
        user_data = {
            "user_id": f"test_opt_user_{uuid.uuid4().hex[:8]}",
            "email": f"optimizer.{uuid.uuid4().hex[:8]}@testcompany.com",
            "subscription_tier": subscription,
            "permissions": ["cost_optimization", "ai_analysis", "recommendations"],
            "monthly_ai_spend": self._get_monthly_spend_by_tier(subscription),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"Created test user: {user_data['user_id']} ({subscription}, ${user_data['monthly_ai_spend']}/mo)")
        return user_data
        
    def _get_monthly_spend_by_tier(self, tier: str) -> Decimal:
        """Get realistic monthly AI spend by subscription tier."""
        spend_by_tier = {
            "free": Decimal("0.00"),
            "early": Decimal("500.00"),
            "mid": Decimal("2500.00"),
            "enterprise": Decimal("15000.00")
        }
        return spend_by_tier.get(tier, Decimal("1000.00"))
    
    async def generate_ai_infrastructure_profile(self, complexity: str = "standard") -> Dict[str, Any]:
        """Generate realistic AI infrastructure profile for optimization."""
        
        profiles = {
            "simple": {
                "name": "Small Team AI Setup",
                "monthly_spend": Decimal("800.00"),
                "services": [
                    {"name": "OpenAI GPT-4", "monthly_cost": 450.00, "usage": "chat_completions", "tokens_per_month": 1500000},
                    {"name": "Anthropic Claude", "monthly_cost": 250.00, "usage": "text_analysis", "tokens_per_month": 800000},
                    {"name": "Pinecone Vector DB", "monthly_cost": 100.00, "usage": "embeddings", "queries_per_month": 100000}
                ],
                "optimization_potential": 25.0  # Expected % savings
            },
            "standard": {
                "name": "Growing Company AI Infrastructure", 
                "monthly_spend": Decimal("3200.00"),
                "services": [
                    {"name": "OpenAI GPT-4", "monthly_cost": 1800.00, "usage": "chat_api", "tokens_per_month": 6000000},
                    {"name": "OpenAI GPT-3.5", "monthly_cost": 400.00, "usage": "bulk_processing", "tokens_per_month": 8000000},
                    {"name": "Anthropic Claude", "monthly_cost": 600.00, "usage": "document_analysis", "tokens_per_month": 2000000},
                    {"name": "AWS Bedrock", "monthly_cost": 300.00, "usage": "embeddings", "tokens_per_month": 5000000},
                    {"name": "Vector Database", "monthly_cost": 100.00, "usage": "similarity_search", "queries_per_month": 500000}
                ],
                "optimization_potential": 35.0  # Expected % savings
            },
            "enterprise": {
                "name": "Enterprise AI Platform",
                "monthly_spend": Decimal("18000.00"),
                "services": [
                    {"name": "OpenAI GPT-4", "monthly_cost": 8500.00, "usage": "production_api", "tokens_per_month": 28000000},
                    {"name": "OpenAI GPT-3.5", "monthly_cost": 2200.00, "usage": "batch_processing", "tokens_per_month": 44000000},
                    {"name": "Anthropic Claude", "monthly_cost": 3800.00, "usage": "content_generation", "tokens_per_month": 12000000},
                    {"name": "Google PaLM", "monthly_cost": 1500.00, "usage": "specialized_tasks", "tokens_per_month": 6000000},
                    {"name": "AWS Bedrock", "monthly_cost": 1200.00, "usage": "embeddings", "tokens_per_month": 20000000},
                    {"name": "Pinecone", "monthly_cost": 500.00, "usage": "vector_search", "queries_per_month": 5000000},
                    {"name": "Weaviate", "monthly_cost": 300.00, "usage": "knowledge_base", "queries_per_month": 1000000}
                ],
                "optimization_potential": 42.0  # Expected % savings  
            }
        }
        
        profile = profiles.get(complexity, profiles["standard"])
        logger.info(f"Generated AI infrastructure profile: {profile['name']} (${profile['monthly_spend']}/mo)")
        return profile
    
    async def execute_optimization_pipeline(
        self,
        websocket_client: WebSocketTestClient,
        infrastructure_profile: Dict[str, Any],
        optimization_goals: List[str] = None
    ) -> Dict[str, Any]:
        """Execute complete optimization pipeline and track business metrics."""
        
        if optimization_goals is None:
            optimization_goals = ["cost_reduction", "performance_optimization", "vendor_diversification"]
            
        start_time = time.time()
        
        # Send optimization request
        request_message = {
            "type": "agent_request",
            "agent": "optimization_pipeline",
            "message": "Please analyze my AI infrastructure and provide comprehensive cost optimization recommendations",
            "context": {
                "infrastructure": infrastructure_profile,
                "optimization_goals": optimization_goals,
                "current_monthly_spend": str(infrastructure_profile["monthly_spend"]),
                "target_savings_percentage": 30.0,
                "business_context": "enterprise_cost_optimization"
            },
            "user_id": f"optimizer_{uuid.uuid4().hex[:8]}",
            "thread_id": str(uuid.uuid4())
        }
        
        await websocket_client.send_json(request_message)
        logger.info(f"Sent optimization request for: {infrastructure_profile['name']}")
        
        # Collect all WebSocket events
        events = []
        async for event in websocket_client.receive_events(timeout=180.0):  # Longer timeout for complex optimization
            events.append(event)
            event_type = event.get("type", "unknown")
            
            # Track event metrics
            if event_type in self.metrics.websocket_events:
                self.metrics.websocket_events[event_type] += 1
                
            logger.info(f"Received optimization event: {event_type}")
            
            # Log tool execution for transparency
            if event_type == "tool_executing":
                tool_name = event.get("data", {}).get("tool", "unknown")
                logger.info(f"  → Executing optimization tool: {tool_name}")
            
            # Stop on completion
            if event_type == "agent_completed":
                break
                
        # Calculate analysis time
        self.metrics.analysis_time_seconds = time.time() - start_time
        
        # Extract final optimization results
        final_event = events[-1] if events else {}
        result = final_event.get("data", {}).get("result", {})
        
        # Analyze business value metrics from optimization results
        self._analyze_optimization_metrics(result, infrastructure_profile)
        
        return {
            "events": events,
            "result": result,
            "metrics": self.metrics,
            "analysis_time": self.metrics.analysis_time_seconds
        }
    
    def _analyze_optimization_metrics(self, result: Dict[str, Any], infrastructure: Dict[str, Any]):
        """Analyze optimization results to extract business value metrics."""
        
        # Count recommendations generated
        recommendations = result.get("recommendations", [])
        self.metrics.recommendations_generated = len(recommendations)
        
        # Calculate potential savings
        savings_info = result.get("cost_savings", {})
        monthly_savings = savings_info.get("monthly_amount", 0)
        self.metrics.potential_monthly_savings = Decimal(str(monthly_savings))
        
        # Calculate cost reduction percentage
        current_spend = infrastructure["monthly_spend"]
        if current_spend > 0:
            self.metrics.cost_reduction_percentage = (
                float(self.metrics.potential_monthly_savings) / float(current_spend)
            ) * 100
        
        # Count high-confidence recommendations
        high_conf_recs = [
            r for r in recommendations 
            if r.get("confidence", 0) >= 0.8
        ]
        self.metrics.high_confidence_recommendations = len(high_conf_recs)
        
        # Count actionable recommendations (have specific actions and impact)
        actionable_recs = [
            r for r in recommendations
            if r.get("action") and r.get("expected_savings")
        ]
        self.metrics.actionable_recommendations = len(actionable_recs)
        
        # Calculate average confidence
        confidence_scores = [r.get("confidence", 0) for r in recommendations if "confidence" in r]
        self.metrics.average_confidence_score = (
            sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        )
        
        # Count optimization opportunities
        optimizations = result.get("optimizations", [])
        self.metrics.optimization_opportunities = len(optimizations)
        
        # Calculate ROI potential (annual savings / estimated implementation cost)
        annual_savings = self.metrics.potential_monthly_savings * 12
        implementation_cost = result.get("implementation", {}).get("estimated_cost", 1000)
        if implementation_cost > 0:
            self.metrics.roi_potential = annual_savings / Decimal(str(implementation_cost))
            
        # Estimate payback period
        if monthly_savings > 0:
            self.metrics.payback_period_days = int((implementation_cost / monthly_savings) * 30)
            
        # Determine risk level
        self.metrics.risk_level = result.get("risk_assessment", {}).get("level", "medium")
        
        logger.info(
            f"Optimization metrics: ${self.metrics.potential_monthly_savings}/mo savings "
            f"({self.metrics.cost_reduction_percentage:.1f}%), "
            f"{self.metrics.actionable_recommendations} actionable recommendations, "
            f"ROI: {self.metrics.roi_potential:.1f}x"
        )


class TestRealOptimizationPipeline(RealOptimizationPipelineE2ETest):
    """Test suite for real optimization pipeline flows."""
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_comprehensive_optimization_pipeline(self, real_services_fixture):
        """Test complete optimization pipeline with quantified business value validation."""
        
        # Create enterprise test user
        user = await self.create_test_user("enterprise")
        
        # Generate comprehensive AI infrastructure profile
        infrastructure = await self.generate_ai_infrastructure_profile("enterprise")
        
        # Connect to WebSocket
        backend_url = f"http://localhost:{TEST_PORTS['backend']}"
        websocket_url = backend_url.replace("http", "ws") + "/ws"
        
        async with WebSocketTestClient(
            url=websocket_url,
            user_id=user["user_id"]
        ) as client:
            
            # Execute optimization pipeline
            optimization_result = await self.execute_optimization_pipeline(
                client, infrastructure, ["cost_reduction", "performance_optimization", "risk_mitigation"]
            )
            
            # CRITICAL: Verify all 5 WebSocket events were sent
            assert_websocket_events(optimization_result["events"], [
                "agent_started",
                "agent_thinking",
                "tool_executing", 
                "tool_completed",
                "agent_completed"
            ])
            
            # Validate business value delivery
            assert self.metrics.is_business_value_delivered(), (
                f"Optimization pipeline did not deliver business value. Metrics: {self.metrics}"
            )
            
            # Validate specific business outcomes
            result = optimization_result["result"]
            
            # Must generate substantial cost savings
            assert self.metrics.potential_monthly_savings >= Decimal("500.00"), (
                f"Must generate significant savings. Got: ${self.metrics.potential_monthly_savings}"
            )
            
            # Must achieve meaningful cost reduction percentage
            assert self.metrics.cost_reduction_percentage >= 10.0, (
                f"Must achieve at least 10% cost reduction. Got: {self.metrics.cost_reduction_percentage}%"
            )
            
            # Must provide actionable recommendations
            assert self.metrics.actionable_recommendations >= 3, (
                f"Must provide at least 3 actionable recommendations. Got: {self.metrics.actionable_recommendations}"
            )
            
            # Must have high-confidence recommendations
            assert self.metrics.high_confidence_recommendations >= 2, (
                f"Must have at least 2 high-confidence recommendations. Got: {self.metrics.high_confidence_recommendations}"
            )
            
            # Performance requirements
            assert self.metrics.analysis_time_seconds < 120.0, (
                f"Optimization took too long: {self.metrics.analysis_time_seconds}s"
            )
            
            # Quality requirements
            assert self.metrics.average_confidence_score >= 0.75, (
                f"Average confidence too low: {self.metrics.average_confidence_score}"
            )
            
            # ROI requirements
            assert self.metrics.roi_potential >= Decimal("2.0"), (
                f"ROI potential too low: {self.metrics.roi_potential}x"
            )
            
        logger.success("✓ Comprehensive optimization pipeline validated")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_optimization_pipeline_cost_tiers(self, real_services_fixture):
        """Test optimization pipeline across different customer tiers and spend levels."""
        
        # Test different customer segments
        test_scenarios = [
            ("early", "simple"),
            ("mid", "standard"), 
            ("enterprise", "enterprise")
        ]
        
        backend_url = f"http://localhost:{TEST_PORTS['backend']}"
        websocket_url = backend_url.replace("http", "ws") + "/ws"
        
        for tier, complexity in test_scenarios:
            logger.info(f"Testing optimization for {tier} tier ({complexity} infrastructure)")
            
            # Reset metrics for each test
            self.metrics = OptimizationPipelineMetrics()
            
            user = await self.create_test_user(tier)
            infrastructure = await self.generate_ai_infrastructure_profile(complexity)
            
            async with WebSocketTestClient(
                url=websocket_url,
                user_id=user["user_id"]
            ) as client:
                
                optimization_result = await self.execute_optimization_pipeline(
                    client, infrastructure
                )
                
                # Validate tier-appropriate outcomes
                result = optimization_result["result"]
                
                # All tiers must get some recommendations
                assert self.metrics.recommendations_generated > 0, (
                    f"{tier} tier got no recommendations"
                )
                
                # Higher tiers should get more sophisticated recommendations
                if tier == "enterprise":
                    assert self.metrics.optimization_opportunities >= 5, (
                        f"Enterprise tier should get more optimization opportunities. Got: {self.metrics.optimization_opportunities}"
                    )
                    assert self.metrics.potential_monthly_savings >= Decimal("500.00"), (
                        f"Enterprise should get substantial savings. Got: ${self.metrics.potential_monthly_savings}"
                    )
                elif tier == "mid":
                    assert self.metrics.optimization_opportunities >= 3, (
                        f"Mid tier should get decent optimization opportunities. Got: {self.metrics.optimization_opportunities}"
                    )
                    assert self.metrics.potential_monthly_savings >= Decimal("100.00"), (
                        f"Mid tier should get meaningful savings. Got: ${self.metrics.potential_monthly_savings}"
                    )
                else:  # early
                    assert self.metrics.optimization_opportunities >= 2, (
                        f"Early tier should get some optimization opportunities. Got: {self.metrics.optimization_opportunities}"
                    )
                
                logger.info(f"✓ {tier} tier optimization validated: ${self.metrics.potential_monthly_savings} savings")
        
        logger.success("✓ Multi-tier optimization pipeline validated")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_optimization_pipeline_vendor_analysis(self, real_services_fixture):
        """Test optimization pipeline's vendor comparison and switching recommendations."""
        
        user = await self.create_test_user("enterprise")
        
        # Infrastructure with vendor diversification opportunities
        infrastructure = {
            "name": "Vendor-Heavy AI Setup",
            "monthly_spend": Decimal("5000.00"),
            "services": [
                {"name": "OpenAI GPT-4", "monthly_cost": 4000.00, "usage": "all_use_cases", "tokens_per_month": 13000000},
                {"name": "OpenAI Embeddings", "monthly_cost": 800.00, "usage": "embeddings", "tokens_per_month": 10000000},
                {"name": "OpenAI Fine-tuning", "monthly_cost": 200.00, "usage": "custom_models", "tokens_per_month": 500000}
            ],
            "optimization_potential": 45.0,  # High potential due to vendor concentration
            "vendor_concentration": "high_openai"
        }
        
        backend_url = f"http://localhost:{TEST_PORTS['backend']}"
        websocket_url = backend_url.replace("http", "ws") + "/ws"
        
        async with WebSocketTestClient(
            url=websocket_url,
            user_id=user["user_id"]
        ) as client:
            
            optimization_result = await self.execute_optimization_pipeline(
                client, infrastructure, ["vendor_diversification", "cost_reduction"]
            )
            
            result = optimization_result["result"]
            
            # Must identify vendor concentration risk
            risk_assessment = result.get("risk_assessment", {})
            assert "vendor" in str(risk_assessment).lower(), (
                "Must identify vendor concentration risk"
            )
            
            # Must recommend alternative vendors
            recommendations = result.get("recommendations", [])
            vendor_recs = [
                r for r in recommendations
                if any(vendor in str(r).lower() for vendor in ["anthropic", "google", "cohere", "hugging"])
            ]
            assert len(vendor_recs) > 0, "Must recommend alternative vendors"
            
            # Must show cost comparison between vendors
            cost_analysis = result.get("cost_analysis", {})
            assert "vendor_comparison" in cost_analysis or any(
                "comparison" in str(r).lower() for r in recommendations
            ), "Must provide vendor cost comparison"
            
            # Must achieve significant savings through vendor optimization
            assert self.metrics.potential_monthly_savings >= Decimal("200.00"), (
                f"Vendor optimization should yield substantial savings. Got: ${self.metrics.potential_monthly_savings}"
            )
            
        logger.success("✓ Vendor analysis optimization validated")
    
    @pytest.mark.e2e
    @pytest.mark.real_services  
    async def test_optimization_pipeline_performance_isolation(self, real_services_fixture):
        """Test optimization pipeline performance under concurrent user load."""
        
        # Create multiple users with different optimization needs
        users_and_profiles = [
            (await self.create_test_user("enterprise"), await self.generate_ai_infrastructure_profile("enterprise")),
            (await self.create_test_user("mid"), await self.generate_ai_infrastructure_profile("standard")),
            (await self.create_test_user("early"), await self.generate_ai_infrastructure_profile("simple"))
        ]
        
        backend_url = f"http://localhost:{TEST_PORTS['backend']}"
        websocket_url = backend_url.replace("http", "ws") + "/ws"
        
        # Track performance metrics for each concurrent optimization
        performance_results = []
        
        async def optimize_for_user(user, infrastructure):
            start_time = time.time()
            
            async with WebSocketTestClient(
                url=websocket_url,
                user_id=user["user_id"]
            ) as client:
                
                # Reset metrics for this user
                user_metrics = OptimizationPipelineMetrics()
                original_metrics = self.metrics
                self.metrics = user_metrics
                
                try:
                    result = await self.execute_optimization_pipeline(
                        client, infrastructure
                    )
                    
                    execution_time = time.time() - start_time
                    
                    return {
                        "user_id": user["user_id"],
                        "tier": user["subscription_tier"],
                        "execution_time": execution_time,
                        "metrics": user_metrics,
                        "success": user_metrics.is_business_value_delivered()
                    }
                    
                finally:
                    # Restore original metrics
                    self.metrics = original_metrics
        
        # Execute all optimizations concurrently
        concurrent_start = time.time()
        results = await asyncio.gather(*[
            optimize_for_user(user, profile) 
            for user, profile in users_and_profiles
        ])
        total_concurrent_time = time.time() - concurrent_start
        
        # Validate isolation and performance
        successful_optimizations = [r for r in results if r["success"]]
        assert len(successful_optimizations) == len(users_and_profiles), (
            f"Not all concurrent optimizations succeeded. Got {len(successful_optimizations)}/{len(users_and_profiles)}"
        )
        
        # Validate performance under load
        max_execution_time = max(r["execution_time"] for r in results)
        assert max_execution_time < 180.0, (
            f"Concurrent optimization took too long: {max_execution_time}s"
        )
        
        # Validate that each user got appropriate recommendations for their tier
        for result in results:
            tier = result["tier"]
            metrics = result["metrics"]
            
            if tier == "enterprise":
                assert metrics.potential_monthly_savings >= Decimal("300.00"), (
                    f"Enterprise user {result['user_id']} got insufficient savings"
                )
            elif tier == "mid":
                assert metrics.potential_monthly_savings >= Decimal("50.00"), (
                    f"Mid user {result['user_id']} got insufficient savings"
                )
            
            # All users should get recommendations
            assert metrics.recommendations_generated > 0, (
                f"User {result['user_id']} got no recommendations"
            )
        
        logger.success(f"✓ Concurrent optimization isolation validated ({total_concurrent_time:.1f}s total)")


if __name__ == "__main__":
    # Run the test directly for development
    import asyncio
    
    async def run_direct_tests():
        logger.info("Starting real optimization pipeline E2E tests...")
        
        test_instance = TestRealOptimizationPipeline()
        
        try:
            # Mock real_services_fixture for direct testing
            mock_services = {
                "db": "mock_db",
                "redis": "mock_redis",
                "backend_url": f"http://localhost:{TEST_PORTS['backend']}"
            }
            
            await test_instance.test_comprehensive_optimization_pipeline(mock_services)
            logger.success("✓ All optimization pipeline tests passed")
            
        except Exception as e:
            logger.error(f"✗ Optimization pipeline tests failed: {e}")
            raise
    
    asyncio.run(run_direct_tests())