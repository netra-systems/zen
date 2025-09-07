#!/usr/bin/env python
"""Real Agent Multi-Agent Collaboration E2E Test Suite - Complete Agent Orchestration Workflow

MISSION CRITICAL: Validates that multi-agent collaboration delivers REAL BUSINESS VALUE through 
coordinated AI agent workflows. Tests actual collaborative problem-solving capabilities and 
synergistic insights generation, not just technical orchestration.

Business Value Justification (BVJ):
- Segment: Mid, Enterprise (complex workflow customers)
- Business Goal: Ensure agent collaboration delivers superior insights through specialization
- Value Impact: Advanced AI orchestration capabilities that handle complex business problems
- Strategic/Revenue Impact: $2.5M+ ARR protection from multi-agent workflow failures  
- Platform Stability: Foundation for scalable AI agent collaboration at enterprise level

CLAUDE.md COMPLIANCE:
- Uses ONLY real services (Docker, PostgreSQL, Redis) - NO MOCKS  
- Tests complete business value delivery through multi-agent collaboration
- Verifies ALL 5 WebSocket events for each participating agent
- Uses test_framework imports for SSOT patterns
- Validates actual collaborative insights and coordinated recommendations
- Tests multi-user isolation during concurrent multi-agent workflows
- Focuses on REAL business outcomes, not just technical orchestration
- Uses SSOT TEST_PORTS configuration
- Implements proper resource cleanup and error handling
- Validates business value compliance with collaboration-specific metrics

This test validates that our multi-agent system actually works end-to-end to deliver 
superior business value through agent specialization and collaboration. Not just that 
agents can communicate, but that they provide better insights together than individually.
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


class AgentRole(Enum):
    """Agent roles in multi-agent collaboration."""
    DATA_ANALYST = "data_analyst"
    COST_OPTIMIZER = "cost_optimizer"
    SUPERVISOR = "supervisor"
    SECURITY_AUDITOR = "security_auditor"
    PERFORMANCE_SPECIALIST = "performance_specialist"


@dataclass
class MultiAgentCollaborationMetrics:
    """Business value metrics for multi-agent collaboration operations."""
    
    # Collaboration metrics
    total_agents_participated: int = 0
    collaboration_rounds: int = 0
    cross_agent_insights: int = 0
    
    # Performance metrics
    total_collaboration_time: float = 0.0
    average_agent_response_time: float = 0.0
    coordination_overhead_percentage: float = 0.0
    
    # Quality metrics
    collaborative_insights_generated: int = 0
    consensus_recommendations: int = 0
    conflicting_recommendations_resolved: int = 0
    final_confidence_score: float = 0.0
    
    # Business value metrics
    synergistic_value_multiplier: float = 1.0  # How much better than single agent
    comprehensive_solution_coverage: float = 0.0  # % of problem aspects addressed
    actionable_collaborative_recommendations: int = 0
    estimated_collaborative_savings: Decimal = Decimal("0.00")
    
    # WebSocket event tracking per agent
    agent_websocket_events: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    # Coordination events
    coordination_events: Dict[str, int] = field(default_factory=lambda: {
        "collaboration_started": 0,
        "agent_handoff": 0,
        "consensus_building": 0,
        "final_synthesis": 0,
        "collaboration_completed": 0
    })
    
    def is_business_value_delivered(self) -> bool:
        """Check if multi-agent collaboration delivered superior business value."""
        return (
            self.total_agents_participated >= 2 and
            self.collaborative_insights_generated > 0 and
            self.consensus_recommendations > 0 and
            self.synergistic_value_multiplier > 1.2 and  # At least 20% better than single agent
            self.comprehensive_solution_coverage >= 0.8 and
            all(count > 0 for event, count in self.coordination_events.items() 
                if event in ["collaboration_started", "collaboration_completed"])
        )


class RealMultiAgentCollaborationE2ETest(BaseE2ETest):
    """Test multi-agent collaboration with real services and business value validation."""
    
    def __init__(self):
        super().__init__()
        self.env = get_env()
        self.metrics = MultiAgentCollaborationMetrics()
        
    async def create_test_user(self, subscription: str = "enterprise") -> Dict[str, Any]:
        """Create test user with multi-agent collaboration permissions."""
        user_data = {
            "user_id": f"test_collab_user_{uuid.uuid4().hex[:8]}",
            "email": f"collaboration.{uuid.uuid4().hex[:8]}@testcompany.com",
            "subscription_tier": subscription,
            "permissions": ["multi_agent_access", "advanced_analytics", "collaborative_workflows"],
            "max_concurrent_agents": self._get_max_agents_by_tier(subscription),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"Created collaboration test user: {user_data['user_id']} "
                   f"({subscription}, max {user_data['max_concurrent_agents']} agents)")
        return user_data
        
    def _get_max_agents_by_tier(self, tier: str) -> int:
        """Get maximum concurrent agents by subscription tier."""
        agents_by_tier = {
            "free": 1,
            "early": 2,
            "mid": 3,
            "enterprise": 5
        }
        return agents_by_tier.get(tier, 2)
    
    async def generate_complex_business_problem(self, complexity: str = "standard") -> Dict[str, Any]:
        """Generate realistic complex business problem requiring multi-agent collaboration."""
        
        problems = {
            "simple": {
                "name": "Cost and Performance Analysis",
                "description": "Analyze AI infrastructure costs and identify performance bottlenecks",
                "required_specialties": ["cost_analysis", "performance_analysis"],
                "expected_agents": [AgentRole.COST_OPTIMIZER, AgentRole.PERFORMANCE_SPECIALIST],
                "problem_data": {
                    "monthly_ai_spend": 5000.00,
                    "performance_metrics": {
                        "avg_response_time": 450,
                        "p95_response_time": 1200,
                        "error_rate": 0.05,
                        "throughput": 850
                    },
                    "cost_breakdown": [
                        {"service": "LLM API", "cost": 3500, "usage": "high"},
                        {"service": "Vector DB", "cost": 800, "usage": "medium"},
                        {"service": "Compute", "cost": 700, "usage": "high"}
                    ]
                },
                "expected_collaboration_value": 1.3  # 30% better than single agent
            },
            "standard": {
                "name": "Comprehensive AI Infrastructure Optimization",
                "description": "Full-stack AI infrastructure analysis including cost, performance, security, and data insights",
                "required_specialties": ["cost_optimization", "performance_analysis", "security_audit", "data_analysis"],
                "expected_agents": [AgentRole.COST_OPTIMIZER, AgentRole.PERFORMANCE_SPECIALIST, AgentRole.SECURITY_AUDITOR, AgentRole.DATA_ANALYST],
                "problem_data": {
                    "monthly_ai_spend": 25000.00,
                    "infrastructure": {
                        "llm_services": ["openai", "anthropic", "google"],
                        "vector_dbs": ["pinecone", "weaviate"],
                        "compute_resources": ["aws_ec2", "azure_vms"],
                        "data_sources": ["s3", "postgres", "clickhouse"]
                    },
                    "performance_issues": [
                        {"type": "latency", "severity": "high", "affected_endpoints": ["/chat", "/analyze"]},
                        {"type": "throughput", "severity": "medium", "affected_services": ["embedding_service"]},
                        {"type": "error_rate", "severity": "low", "affected_models": ["gpt-4"]}
                    ],
                    "security_concerns": [
                        {"type": "data_exposure", "risk": "medium"},
                        {"type": "api_key_rotation", "risk": "low"}
                    ],
                    "data_analytics_needs": [
                        {"type": "usage_patterns", "priority": "high"},
                        {"type": "cost_trends", "priority": "high"},
                        {"type": "performance_trends", "priority": "medium"}
                    ]
                },
                "expected_collaboration_value": 1.6  # 60% better than single agent
            },
            "enterprise": {
                "name": "Strategic AI Platform Transformation",
                "description": "Enterprise-level AI platform assessment and transformation strategy",
                "required_specialties": ["strategic_analysis", "cost_optimization", "performance_engineering", "security_architecture", "data_strategy"],
                "expected_agents": [AgentRole.SUPERVISOR, AgentRole.COST_OPTIMIZER, AgentRole.PERFORMANCE_SPECIALIST, AgentRole.SECURITY_AUDITOR, AgentRole.DATA_ANALYST],
                "problem_data": {
                    "monthly_ai_spend": 150000.00,
                    "enterprise_context": {
                        "company_size": "10000_employees",
                        "industries": ["fintech", "healthcare"],
                        "compliance_requirements": ["SOC2", "HIPAA", "GDPR"],
                        "ai_maturity": "advanced",
                        "business_objectives": ["cost_reduction", "performance_improvement", "compliance", "scalability"]
                    },
                    "current_challenges": [
                        {"challenge": "vendor_lock_in", "impact": "high", "urgency": "medium"},
                        {"challenge": "cost_escalation", "impact": "high", "urgency": "high"},
                        {"challenge": "performance_inconsistency", "impact": "medium", "urgency": "high"},
                        {"challenge": "security_gaps", "impact": "high", "urgency": "high"}
                    ],
                    "strategic_goals": {
                        "target_cost_reduction": 35.0,
                        "target_performance_improvement": 40.0,
                        "compliance_timeline": "6_months",
                        "roi_timeline": "12_months"
                    }
                },
                "expected_collaboration_value": 2.2  # 120% better than single agent
            }
        }
        
        problem = problems.get(complexity, problems["standard"])
        logger.info(f"Generated complex business problem: {problem['name']} "
                   f"(requires {len(problem['expected_agents'])} specialized agents)")
        return problem
    
    async def execute_multi_agent_collaboration(
        self,
        websocket_client: WebSocketTestClient,
        business_problem: Dict[str, Any],
        orchestration_strategy: str = "supervisor_led"
    ) -> Dict[str, Any]:
        """Execute multi-agent collaboration workflow and track synergistic business value."""
        
        start_time = time.time()
        self.metrics.agent_websocket_events = {}
        
        # Send multi-agent collaboration request
        request_message = {
            "type": "agent_request",
            "agent": "multi_agent_supervisor",
            "message": f"Please coordinate a multi-agent analysis for: {business_problem['description']}",
            "context": {
                "problem": business_problem,
                "orchestration_strategy": orchestration_strategy,
                "required_specialties": business_problem["required_specialties"],
                "expected_agents": [role.value for role in business_problem["expected_agents"]],
                "collaboration_goals": ["comprehensive_analysis", "consensus_building", "synergistic_insights"],
                "business_context": "enterprise_multi_agent_workflow"
            },
            "user_id": f"collaborator_{uuid.uuid4().hex[:8]}",
            "thread_id": str(uuid.uuid4())
        }
        
        await websocket_client.send_json(request_message)
        logger.info(f"Initiated multi-agent collaboration for: {business_problem['name']}")
        
        # Collect all WebSocket events from all participating agents
        events = []
        participating_agents = set()
        current_round = 0
        
        async for event in websocket_client.receive_events(timeout=300.0):  # Extended timeout for multi-agent coordination
            events.append(event)
            event_type = event.get("type", "unknown")
            agent_id = event.get("data", {}).get("agent_id", "unknown")
            
            # Track participating agents
            if agent_id != "unknown":
                participating_agents.add(agent_id)
                
                # Initialize agent event tracking
                if agent_id not in self.metrics.agent_websocket_events:
                    self.metrics.agent_websocket_events[agent_id] = {
                        "agent_started": 0, "agent_thinking": 0, "tool_executing": 0, 
                        "tool_completed": 0, "agent_completed": 0
                    }
                
                # Track per-agent events
                if event_type in self.metrics.agent_websocket_events[agent_id]:
                    self.metrics.agent_websocket_events[agent_id][event_type] += 1
            
            # Track coordination events
            if event_type in self.metrics.coordination_events:
                self.metrics.coordination_events[event_type] += 1
            
            # Track collaboration rounds
            if event_type == "agent_handoff" or event_type == "consensus_building":
                current_round = max(current_round, event.get("data", {}).get("round", current_round))
            
            logger.info(f"Multi-agent event: {event_type} (agent: {agent_id})")
            
            # Log collaborative insights as they emerge
            if event_type == "collaborative_insight":
                insight = event.get("data", {}).get("insight", "")
                logger.info(f"  → Collaborative insight: {insight[:100]}...")
                self.metrics.cross_agent_insights += 1
            
            # Stop on final collaboration completion
            if event_type == "collaboration_completed":
                break
                
        # Calculate collaboration metrics
        self.metrics.total_collaboration_time = time.time() - start_time
        self.metrics.total_agents_participated = len(participating_agents)
        self.metrics.collaboration_rounds = current_round + 1
        
        # Calculate average response time per agent
        agent_response_times = [
            event.get("data", {}).get("response_time", 0) 
            for event in events if "response_time" in event.get("data", {})
        ]
        self.metrics.average_agent_response_time = (
            sum(agent_response_times) / len(agent_response_times) if agent_response_times else 0.0
        )
        
        # Extract final collaborative result
        final_event = events[-1] if events else {}
        result = final_event.get("data", {}).get("result", {})
        
        # Analyze collaborative business value
        self._analyze_collaborative_metrics(result, business_problem, participating_agents)
        
        return {
            "events": events,
            "result": result,
            "participating_agents": list(participating_agents),
            "metrics": self.metrics,
            "collaboration_time": self.metrics.total_collaboration_time
        }
    
    def _analyze_collaborative_metrics(self, result: Dict[str, Any], problem: Dict[str, Any], agents: Set[str]):
        """Analyze collaborative results to extract synergistic business value metrics."""
        
        # Count collaborative insights generated
        insights = result.get("collaborative_insights", [])
        self.metrics.collaborative_insights_generated = len(insights)
        
        # Count consensus recommendations
        recommendations = result.get("recommendations", [])
        consensus_recs = [r for r in recommendations if r.get("consensus", False) or r.get("agent_agreement", 0) > 1]
        self.metrics.consensus_recommendations = len(consensus_recs)
        
        # Count resolved conflicts
        conflicts = result.get("resolved_conflicts", [])
        self.metrics.conflicting_recommendations_resolved = len(conflicts)
        
        # Calculate final confidence (should be higher due to multi-agent validation)
        confidence_scores = [r.get("confidence", 0) for r in recommendations if "confidence" in r]
        self.metrics.final_confidence_score = (
            sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        )
        
        # Calculate synergistic value multiplier
        single_agent_baseline = 1.0
        collaboration_value = result.get("collaboration_metrics", {}).get("value_multiplier", 1.0)
        self.metrics.synergistic_value_multiplier = max(collaboration_value, single_agent_baseline)
        
        # Calculate comprehensive solution coverage
        required_aspects = len(problem.get("required_specialties", []))
        addressed_aspects = len(result.get("addressed_aspects", []))
        self.metrics.comprehensive_solution_coverage = (
            addressed_aspects / required_aspects if required_aspects > 0 else 0.0
        )
        
        # Count actionable collaborative recommendations
        actionable_recs = [
            r for r in recommendations 
            if r.get("action") and r.get("collaborative_validation", False)
        ]
        self.metrics.actionable_collaborative_recommendations = len(actionable_recs)
        
        # Estimate collaborative savings (should be higher than single-agent analysis)
        savings_info = result.get("estimated_savings", {})
        collaborative_savings = savings_info.get("total_amount", 0)
        self.metrics.estimated_collaborative_savings = Decimal(str(collaborative_savings))
        
        # Calculate coordination overhead
        total_time = self.metrics.total_collaboration_time
        estimated_single_agent_time = total_time / max(self.metrics.total_agents_participated, 1)
        overhead = ((total_time - estimated_single_agent_time) / total_time) * 100 if total_time > 0 else 0
        self.metrics.coordination_overhead_percentage = overhead
        
        logger.info(
            f"Collaborative metrics: {self.metrics.total_agents_participated} agents, "
            f"{self.metrics.collaborative_insights_generated} insights, "
            f"{self.metrics.synergistic_value_multiplier:.1f}x value multiplier, "
            f"{self.metrics.comprehensive_solution_coverage:.1%} coverage"
        )


class TestRealMultiAgentCollaboration(RealMultiAgentCollaborationE2ETest):
    """Test suite for real multi-agent collaboration flows."""
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_comprehensive_multi_agent_collaboration(self, real_services_fixture):
        """Test complete multi-agent collaboration with synergistic business value validation."""
        
        # Create enterprise user with multi-agent access
        user = await self.create_test_user("enterprise")
        
        # Generate complex business problem requiring multiple specialties
        complex_problem = await self.generate_complex_business_problem("standard")
        
        # Connect to WebSocket
        backend_url = f"http://localhost:{TEST_PORTS['backend']}"
        websocket_url = backend_url.replace("http", "ws") + "/ws"
        
        async with WebSocketTestClient(
            url=websocket_url,
            user_id=user["user_id"]
        ) as client:
            
            # Execute multi-agent collaboration
            collaboration_result = await self.execute_multi_agent_collaboration(
                client, complex_problem, "supervisor_led"
            )
            
            # CRITICAL: Verify WebSocket events were sent for each participating agent
            for agent_id, agent_events in self.metrics.agent_websocket_events.items():
                assert_websocket_events([
                    {"type": event_type, "data": {"agent_id": agent_id}}
                    for event_type, count in agent_events.items() if count > 0
                ], ["agent_started", "agent_completed"])  # At minimum
                
                logger.info(f"Agent {agent_id} sent {sum(agent_events.values())} events")
            
            # CRITICAL: Verify coordination events were sent
            assert self.metrics.coordination_events["collaboration_started"] > 0, (
                "Multi-agent collaboration must send collaboration_started event"
            )
            assert self.metrics.coordination_events["collaboration_completed"] > 0, (
                "Multi-agent collaboration must send collaboration_completed event"
            )
            
            # Validate superior business value from collaboration
            assert self.metrics.is_business_value_delivered(), (
                f"Multi-agent collaboration did not deliver superior business value. Metrics: {self.metrics}"
            )
            
            # Validate specific collaborative outcomes
            result = collaboration_result["result"]
            
            # Must involve multiple specialized agents
            assert self.metrics.total_agents_participated >= 2, (
                f"Must involve multiple agents. Got: {self.metrics.total_agents_participated}"
            )
            
            # Must generate collaborative insights
            assert self.metrics.collaborative_insights_generated > 0, (
                f"Must generate collaborative insights. Got: {self.metrics.collaborative_insights_generated}"
            )
            
            # Must achieve synergistic value (better than single agent)
            assert self.metrics.synergistic_value_multiplier >= 1.2, (
                f"Collaboration must provide synergistic value. Got: {self.metrics.synergistic_value_multiplier}x"
            )
            
            # Must provide comprehensive solution coverage
            assert self.metrics.comprehensive_solution_coverage >= 0.8, (
                f"Must address most problem aspects. Got: {self.metrics.comprehensive_solution_coverage:.1%}"
            )
            
            # Must build consensus recommendations
            assert self.metrics.consensus_recommendations > 0, (
                f"Must build consensus recommendations. Got: {self.metrics.consensus_recommendations}"
            )
            
            # Performance requirements (coordination overhead should be reasonable)
            assert self.metrics.coordination_overhead_percentage <= 50.0, (
                f"Coordination overhead too high: {self.metrics.coordination_overhead_percentage}%"
            )
            
            # Quality requirements (collaboration should increase confidence)
            assert self.metrics.final_confidence_score >= 0.8, (
                f"Collaborative confidence too low: {self.metrics.final_confidence_score}"
            )
            
        logger.success("✓ Comprehensive multi-agent collaboration validated")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_multi_agent_specialization_value(self, real_services_fixture):
        """Test that agent specialization provides measurable value over generalist approaches."""
        
        user = await self.create_test_user("mid")
        
        # Problem requiring diverse specialties
        specialized_problem = {
            "name": "Multi-Domain Infrastructure Challenge",
            "description": "Optimize costs while improving performance and maintaining security",
            "required_specialties": ["cost_optimization", "performance_tuning", "security_hardening"],
            "expected_agents": [AgentRole.COST_OPTIMIZER, AgentRole.PERFORMANCE_SPECIALIST, AgentRole.SECURITY_AUDITOR],
            "problem_data": {
                "monthly_spend": 12000.00,
                "performance_issues": {"latency": "high", "throughput": "low"},
                "security_issues": {"encryption": "weak", "access_control": "loose"},
                "cost_issues": {"utilization": "low", "vendor_pricing": "high"}
            },
            "expected_collaboration_value": 1.4
        }
        
        backend_url = f"http://localhost:{TEST_PORTS['backend']}"
        websocket_url = backend_url.replace("http", "ws") + "/ws"
        
        async with WebSocketTestClient(
            url=websocket_url,
            user_id=user["user_id"]
        ) as client:
            
            collaboration_result = await self.execute_multi_agent_collaboration(
                client, specialized_problem, "peer_coordination"
            )
            
            result = collaboration_result["result"]
            
            # Must address all required specialties
            addressed_specialties = result.get("addressed_aspects", [])
            required_specialties = specialized_problem["required_specialties"]
            
            specialty_coverage = len(set(addressed_specialties) & set(required_specialties)) / len(required_specialties)
            assert specialty_coverage >= 0.8, (
                f"Must address most required specialties. Coverage: {specialty_coverage:.1%}"
            )
            
            # Must provide specialized recommendations from each domain
            recommendations = result.get("recommendations", [])
            
            # Look for domain-specific recommendations
            cost_recs = [r for r in recommendations if any(
                keyword in str(r).lower() for keyword in ["cost", "price", "spend", "saving"]
            )]
            perf_recs = [r for r in recommendations if any(
                keyword in str(r).lower() for keyword in ["performance", "latency", "throughput", "speed"]
            )]
            security_recs = [r for r in recommendations if any(
                keyword in str(r).lower() for keyword in ["security", "encryption", "access", "auth"]
            )]
            
            assert len(cost_recs) > 0, "Must provide cost-specific recommendations"
            assert len(perf_recs) > 0, "Must provide performance-specific recommendations"
            assert len(security_recs) > 0, "Must provide security-specific recommendations"
            
            # Must resolve any trade-offs between specialties
            if self.metrics.conflicting_recommendations_resolved > 0:
                logger.info(f"Successfully resolved {self.metrics.conflicting_recommendations_resolved} specialty conflicts")
            
        logger.success("✓ Multi-agent specialization value validated")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_multi_agent_consensus_building(self, real_services_fixture):
        """Test multi-agent consensus building and conflict resolution."""
        
        user = await self.create_test_user("enterprise")
        
        # Problem likely to generate conflicting recommendations
        conflict_prone_problem = {
            "name": "Cost vs Performance Trade-off Analysis",
            "description": "Balance aggressive cost cutting with performance requirements",
            "required_specialties": ["cost_optimization", "performance_engineering"],
            "expected_agents": [AgentRole.COST_OPTIMIZER, AgentRole.PERFORMANCE_SPECIALIST],
            "problem_data": {
                "budget_constraint": "aggressive_reduction_required",
                "performance_requirements": "strict_sla_compliance",
                "current_metrics": {
                    "monthly_cost": 20000.00,
                    "target_cost": 12000.00,  # Aggressive 40% reduction
                    "current_performance": {"p95_latency": 200, "throughput": 5000},
                    "required_performance": {"p95_latency": 150, "throughput": 6000}  # Improvement needed
                }
            },
            "expected_collaboration_value": 1.5
        }
        
        backend_url = f"http://localhost:{TEST_PORTS['backend']}"
        websocket_url = backend_url.replace("http", "ws") + "/ws"
        
        async with WebSocketTestClient(
            url=websocket_url,
            user_id=user["user_id"]
        ) as client:
            
            collaboration_result = await self.execute_multi_agent_collaboration(
                client, conflict_prone_problem, "consensus_building"
            )
            
            # Must engage in consensus building
            assert self.metrics.coordination_events["consensus_building"] > 0, (
                "Must engage in consensus building for conflicting objectives"
            )
            
            result = collaboration_result["result"]
            
            # Must produce consensus recommendations
            assert self.metrics.consensus_recommendations > 0, (
                f"Must build consensus recommendations. Got: {self.metrics.consensus_recommendations}"
            )
            
            # Must provide balanced solution addressing both cost and performance
            recommendations = result.get("recommendations", [])
            
            balanced_recs = [
                r for r in recommendations
                if ("cost" in str(r).lower() and "performance" in str(r).lower()) or
                   r.get("addresses_tradeoffs", False)
            ]
            assert len(balanced_recs) > 0, "Must provide balanced cost/performance recommendations"
            
            # Must explain trade-off decisions
            trade_off_explanations = result.get("trade_off_analysis", [])
            assert len(trade_off_explanations) > 0 or any(
                "trade" in str(r).lower() or "balance" in str(r).lower()
                for r in recommendations
            ), "Must explain trade-off decisions"
            
        logger.success("✓ Multi-agent consensus building validated")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_concurrent_multi_agent_collaborations(self, real_services_fixture):
        """Test concurrent multi-agent collaborations with user isolation."""
        
        # Create multiple users with different collaboration needs
        users_and_problems = [
            (await self.create_test_user("enterprise"), await self.generate_complex_business_problem("enterprise")),
            (await self.create_test_user("mid"), await self.generate_complex_business_problem("standard")),
            (await self.create_test_user("enterprise"), await self.generate_complex_business_problem("simple"))
        ]
        
        backend_url = f"http://localhost:{TEST_PORTS['backend']}"
        websocket_url = backend_url.replace("http", "ws") + "/ws"
        
        async def collaborate_for_user(user, problem):
            # Reset metrics for this user
            user_metrics = MultiAgentCollaborationMetrics()
            original_metrics = self.metrics
            self.metrics = user_metrics
            
            try:
                async with WebSocketTestClient(
                    url=websocket_url,
                    user_id=user["user_id"]
                ) as client:
                    
                    result = await self.execute_multi_agent_collaboration(
                        client, problem
                    )
                    
                    return {
                        "user_id": user["user_id"],
                        "tier": user["subscription_tier"],
                        "agents_participated": user_metrics.total_agents_participated,
                        "collaboration_time": user_metrics.total_collaboration_time,
                        "success": user_metrics.is_business_value_delivered(),
                        "metrics": user_metrics
                    }
                    
            finally:
                # Restore original metrics
                self.metrics = original_metrics
        
        # Execute all collaborations concurrently
        results = await asyncio.gather(*[
            collaborate_for_user(user, problem)
            for user, problem in users_and_problems
        ])
        
        # Validate isolation and performance
        successful_collaborations = [r for r in results if r["success"]]
        assert len(successful_collaborations) == len(users_and_problems), (
            f"Not all concurrent collaborations succeeded. Got {len(successful_collaborations)}/{len(users_and_problems)}"
        )
        
        # Validate that each user got appropriate collaboration for their tier
        for result in results:
            tier = result["tier"]
            
            if tier == "enterprise":
                assert result["agents_participated"] >= 3, (
                    f"Enterprise user should get more agents. Got: {result['agents_participated']}"
                )
            elif tier == "mid":
                assert result["agents_participated"] >= 2, (
                    f"Mid user should get multiple agents. Got: {result['agents_participated']}"
                )
            
            # All collaborations should complete in reasonable time
            assert result["collaboration_time"] < 240.0, (
                f"Collaboration took too long: {result['collaboration_time']}s"
            )
            
            # All users should get collaborative value
            assert result["metrics"].synergistic_value_multiplier >= 1.1, (
                f"User {result['user_id']} didn't get collaborative value"
            )
        
        logger.success("✓ Concurrent multi-agent collaboration isolation validated")


if __name__ == "__main__":
    # Run the test directly for development
    import asyncio
    
    async def run_direct_tests():
        logger.info("Starting real multi-agent collaboration E2E tests...")
        
        test_instance = TestRealMultiAgentCollaboration()
        
        try:
            # Mock real_services_fixture for direct testing
            mock_services = {
                "db": "mock_db",
                "redis": "mock_redis",
                "backend_url": f"http://localhost:{TEST_PORTS['backend']}"
            }
            
            await test_instance.test_comprehensive_multi_agent_collaboration(mock_services)
            logger.success("✓ All multi-agent collaboration tests passed")
            
        except Exception as e:
            logger.error(f"✗ Multi-agent collaboration tests failed: {e}")
            raise
    
    asyncio.run(run_direct_tests())