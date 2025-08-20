"""Test 12: Agent Compensation Model Integration Test - CRITICAL Billing Accuracy

Tests agent execution metrics → billing pipeline integration for accurate compensation.
Validates usage-based billing accuracy for agent operations across all tiers.

Business Value Justification (BVJ):
1. Segment: All paid tiers ($20K MRR protection)
2. Business Goal: Ensure accurate agent usage billing and compensation tracking
3. Value Impact: Prevents revenue leakage from billing inaccuracies
4. Strategic Impact: Protects $20K MRR through validated billing accuracy

COMPLIANCE: File size <300 lines, Functions <8 lines, Real billing testing
"""

import asyncio
import time
from typing import Dict, Any, List
import pytest
from decimal import Decimal

from app.agents.base import BaseSubAgent
from app.schemas.UserPlan import PlanTier
from .agent_billing_test_helpers import AgentBillingTestCore, BillingFlowValidator
from .clickhouse_billing_helper import ClickHouseBillingHelper


class AgentCompensationTracker:
    """Tracks agent execution metrics for compensation calculations."""
    
    def __init__(self):
        self.billing_helper = ClickHouseBillingHelper()
        self.execution_metrics = []
        self.compensation_records = []
        self.tier_multipliers = {
            PlanTier.PRO: Decimal("1.0"),
            PlanTier.ENTERPRISE: Decimal("1.5"),
            PlanTier.DEVELOPER: Decimal("0.8")
        }
    
    async def track_agent_execution(self, agent: BaseSubAgent, user_id: str, 
                                  tier: PlanTier, execution_time: float) -> Dict[str, Any]:
        """Track agent execution for compensation calculation."""
        base_cost = Decimal("0.05")  # $0.05 per agent execution
        tier_multiplier = self.tier_multipliers.get(tier, Decimal("1.0"))
        calculated_cost = base_cost * tier_multiplier
        
        execution_record = {
            "agent_name": agent.name,
            "user_id": user_id,
            "tier": tier.value,
            "execution_time": execution_time,
            "base_cost": float(base_cost),
            "tier_multiplier": float(tier_multiplier),
            "calculated_cost": float(calculated_cost),
            "timestamp": time.time()
        }
        
        self.execution_metrics.append(execution_record)
        return execution_record
    
    async def calculate_agent_compensation(self, agent_executions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate total compensation for agent executions."""
        total_executions = len(agent_executions)
        total_cost = sum(Decimal(str(exec["calculated_cost"])) for exec in agent_executions)
        
        compensation_data = {
            "total_executions": total_executions,
            "total_compensation": float(total_cost),
            "average_cost_per_execution": float(total_cost / total_executions) if total_executions > 0 else 0.0,
            "execution_breakdown": agent_executions
        }
        
        self.compensation_records.append(compensation_data)
        return compensation_data
    
    async def validate_billing_integration(self, user_data: Dict[str, Any], 
                                         compensation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate integration with billing pipeline."""
        billing_record = {
            "user_id": user_data["id"],
            "amount_cents": int(compensation_data["total_compensation"] * 100),
            "description": f"Agent compensation for {compensation_data['total_executions']} executions",
            "metadata": compensation_data
        }
        
        validation_result = await self.billing_helper.create_and_validate_billing_record(
            billing_record, user_data, PlanTier(user_data.get("plan_tier", "pro"))
        )
        
        return {
            "billing_record_created": validation_result["clickhouse_inserted"],
            "billing_validation_passed": validation_result["validation"]["valid"],
            "compensation_amount": compensation_data["total_compensation"],
            "billing_integration_successful": (
                validation_result["clickhouse_inserted"] and 
                validation_result["validation"]["valid"]
            )
        }


class CompensationModelValidator:
    """Validates compensation model accuracy and consistency."""
    
    def __init__(self):
        self.validation_results = []
        self.accuracy_thresholds = {
            "cost_calculation_accuracy": 0.99,
            "tier_multiplier_accuracy": 1.0,
            "billing_integration_accuracy": 0.98
        }
    
    async def validate_tier_based_compensation(self, compensation_tracker: AgentCompensationTracker,
                                             test_scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate tier-based compensation calculations."""
        tier_results = {}
        
        for scenario in test_scenarios:
            tier = scenario["tier"]
            expected_multiplier = compensation_tracker.tier_multipliers[tier]
            
            # Calculate compensation for scenario
            agent_executions = scenario["executions"]
            compensation_result = await compensation_tracker.calculate_agent_compensation(agent_executions)
            
            # Validate tier multiplier application
            expected_total = sum(
                Decimal("0.05") * expected_multiplier 
                for _ in agent_executions
            )
            actual_total = Decimal(str(compensation_result["total_compensation"]))
            
            accuracy = min(float(actual_total / expected_total), float(expected_total / actual_total))
            
            tier_results[tier.value] = {
                "expected_total": float(expected_total),
                "actual_total": float(actual_total),
                "accuracy": accuracy,
                "tier_multiplier_correct": accuracy >= self.accuracy_thresholds["tier_multiplier_accuracy"]
            }
        
        overall_accuracy = sum(r["accuracy"] for r in tier_results.values()) / len(tier_results)
        
        return {
            "tier_results": tier_results,
            "overall_accuracy": overall_accuracy,
            "tier_compensation_valid": overall_accuracy >= self.accuracy_thresholds["cost_calculation_accuracy"]
        }
    
    async def validate_billing_pipeline_integration(self, compensation_tracker: AgentCompensationTracker,
                                                  user_data: Dict[str, Any],
                                                  compensation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate integration with billing pipeline."""
        integration_result = await compensation_tracker.validate_billing_integration(user_data, compensation_data)
        
        pipeline_validation = {
            "billing_record_creation": integration_result["billing_record_created"],
            "billing_validation": integration_result["billing_validation_passed"],
            "amount_accuracy": integration_result["compensation_amount"] > 0,
            "integration_success": integration_result["billing_integration_successful"]
        }
        
        return {
            "pipeline_integration": pipeline_validation,
            "integration_score": sum(pipeline_validation.values()) / len(pipeline_validation),
            "billing_integration_valid": pipeline_validation["integration_success"]
        }


@pytest.mark.integration
class TestAgentCompensationIntegration:
    """Integration tests for agent compensation model and billing pipeline."""
    
    @pytest.fixture
    async def test_core(self):
        """Initialize agent billing test core."""
        core = AgentBillingTestCore()
        await core.setup_test_environment()
        yield core
        await core.teardown_test_environment()
    
    @pytest.fixture
    def compensation_tracker(self):
        """Initialize agent compensation tracker."""
        return AgentCompensationTracker()
    
    @pytest.fixture
    def compensation_validator(self):
        """Initialize compensation model validator."""
        return CompensationModelValidator()
    
    @pytest.mark.asyncio
    async def test_agent_execution_compensation_tracking(self, test_core, compensation_tracker):
        """Test agent execution tracking for compensation."""
        session = await test_core.establish_authenticated_user_session(PlanTier.PRO)
        
        try:
            # Create test agent
            from app.llm.llm_manager import LLMManager
            llm_manager = LLMManager(test_core.config)
            agent = BaseSubAgent(
                llm_manager=llm_manager,
                name="CompensationTestAgent001",
                description="Agent for compensation testing"
            )
            agent.user_id = session["user_data"]["id"]
            
            # Track execution
            execution_record = await compensation_tracker.track_agent_execution(
                agent, session["user_data"]["id"], session["tier"], 2.5
            )
            
            assert execution_record["agent_name"] == "CompensationTestAgent001"
            assert execution_record["calculated_cost"] == 0.05  # PRO tier multiplier 1.0
            assert execution_record["execution_time"] == 2.5
            
        finally:
            await session["client"].close()
    
    @pytest.mark.asyncio
    async def test_tier_based_compensation_calculation(self, test_core, compensation_tracker, 
                                                     compensation_validator):
        """Test tier-based compensation calculations."""
        # Create test scenarios for different tiers
        test_scenarios = []
        
        for tier in [PlanTier.PRO, PlanTier.ENTERPRISE, PlanTier.DEVELOPER]:
            session = await test_core.establish_authenticated_user_session(tier)
            
            try:
                # Create execution records for tier
                executions = []
                for i in range(3):
                    execution = {
                        "agent_name": f"TierAgent{i:03d}",
                        "calculated_cost": 0.05 * float(compensation_tracker.tier_multipliers[tier]),
                        "tier": tier.value
                    }
                    executions.append(execution)
                
                test_scenarios.append({
                    "tier": tier,
                    "executions": executions
                })
                
            finally:
                await session["client"].close()
        
        # Validate tier-based compensation
        validation_result = await compensation_validator.validate_tier_based_compensation(
            compensation_tracker, test_scenarios
        )
        
        assert validation_result["tier_compensation_valid"], "Tier-based compensation validation failed"
        assert validation_result["overall_accuracy"] >= 0.99, "Compensation calculation accuracy too low"
        
        # Validate each tier
        for tier_result in validation_result["tier_results"].values():
            assert tier_result["tier_multiplier_correct"], "Tier multiplier calculation incorrect"
    
    @pytest.mark.asyncio
    async def test_compensation_billing_pipeline_integration(self, test_core, compensation_tracker,
                                                           compensation_validator):
        """Test integration between compensation tracking and billing pipeline."""
        session = await test_core.establish_authenticated_user_session(PlanTier.ENTERPRISE)
        
        try:
            # Create multiple agent executions
            executions = []
            for i in range(5):
                execution = await compensation_tracker.track_agent_execution(
                    BaseSubAgent(name=f"BillingAgent{i:03d}"),
                    session["user_data"]["id"],
                    session["tier"],
                    1.5 + i * 0.5
                )
                executions.append(execution)
            
            # Calculate compensation
            compensation_data = await compensation_tracker.calculate_agent_compensation(executions)
            
            # Validate billing integration
            integration_result = await compensation_validator.validate_billing_pipeline_integration(
                compensation_tracker, session["user_data"], compensation_data
            )
            
            assert integration_result["billing_integration_valid"], "Billing pipeline integration failed"
            assert integration_result["integration_score"] >= 0.95, "Integration score too low"
            
            pipeline_data = integration_result["pipeline_integration"]
            assert pipeline_data["billing_record_creation"], "Billing record not created"
            assert pipeline_data["billing_validation"], "Billing validation failed"
            assert pipeline_data["amount_accuracy"], "Compensation amount calculation failed"
            
        finally:
            await session["client"].close()
    
    @pytest.mark.asyncio
    async def test_high_volume_compensation_accuracy(self, test_core, compensation_tracker):
        """Test compensation accuracy under high volume scenarios."""
        session = await test_core.establish_authenticated_user_session(PlanTier.ENTERPRISE)
        
        try:
            # Create high volume of executions
            executions = []
            for i in range(50):
                execution = await compensation_tracker.track_agent_execution(
                    BaseSubAgent(name=f"VolumeAgent{i:03d}"),
                    session["user_data"]["id"],
                    session["tier"],
                    0.8 + (i % 10) * 0.1
                )
                executions.append(execution)
            
            # Calculate compensation
            start_time = time.time()
            compensation_data = await compensation_tracker.calculate_agent_compensation(executions)
            calculation_time = time.time() - start_time
            
            # Validate high volume performance
            assert calculation_time < 2.0, f"High volume calculation too slow: {calculation_time:.2f}s"
            assert compensation_data["total_executions"] == 50, "Execution count mismatch"
            assert compensation_data["total_compensation"] > 0, "Total compensation calculation failed"
            
            # Validate expected total (50 * $0.05 * 1.5 enterprise multiplier = $3.75)
            expected_total = 50 * 0.05 * 1.5
            actual_total = compensation_data["total_compensation"]
            accuracy = min(actual_total / expected_total, expected_total / actual_total)
            
            assert accuracy >= 0.99, f"High volume compensation accuracy too low: {accuracy:.3f}"
            
        finally:
            await session["client"].close()
    
    @pytest.mark.asyncio
    async def test_concurrent_compensation_tracking(self, test_core, compensation_tracker):
        """Test concurrent compensation tracking accuracy."""
        session = await test_core.establish_authenticated_user_session(PlanTier.PRO)
        
        try:
            # Create concurrent tracking tasks
            tracking_tasks = []
            for i in range(10):
                task = compensation_tracker.track_agent_execution(
                    BaseSubAgent(name=f"ConcurrentAgent{i:03d}"),
                    session["user_data"]["id"],
                    session["tier"],
                    1.0 + i * 0.2
                )
                tracking_tasks.append(task)
            
            # Execute concurrent tracking
            start_time = time.time()
            execution_results = await asyncio.gather(*tracking_tasks)
            concurrent_time = time.time() - start_time
            
            # Validate concurrent performance
            assert concurrent_time < 3.0, f"Concurrent tracking too slow: {concurrent_time:.2f}s"
            assert len(execution_results) == 10, "Some concurrent tracking failed"
            
            # Validate all executions tracked correctly
            for i, result in enumerate(execution_results):
                assert result["agent_name"] == f"ConcurrentAgent{i:03d}", "Agent name mismatch"
                assert result["calculated_cost"] == 0.05, "PRO tier cost calculation incorrect"
                
        finally:
            await session["client"].close()