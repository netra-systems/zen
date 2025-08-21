"""Cost Tracking and Billing Pipeline L4 Critical Test

Business Value Justification (BVJ):
- Segment: All paid tiers (core revenue mechanism)
- Business Goal: Ensure accurate cost tracking and billing across all AI operations
- Value Impact: Protects $25K+ MRR through accurate billing and prevents revenue leakage
- Strategic Impact: Critical for business sustainability, financial reporting, and customer trust

Critical Path:
Usage tracking -> Cost calculation -> Billing accumulation -> Quota enforcement -> 
Invoice generation -> Payment processing -> Usage analytics

Coverage: LLM usage tracking, cost calculation accuracy, billing pipeline integrity, quota enforcement
"""

import pytest
import asyncio
import json
import time
import uuid
from decimal import Decimal
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

from .l4_staging_critical_base import L4StagingCriticalPathTestBase, CriticalPathMetrics
from app.services.billing.cost_calculator import CostCalculator
from app.services.billing.usage_tracker import UsageTracker
from app.services.billing.invoice_generator import InvoiceGenerator


@dataclass
class BillingTestScenario:
    """Test scenario for billing pipeline validation."""
    tier: str
    monthly_quota: int
    cost_per_token: Decimal
    expected_operations: int
    test_duration_seconds: int


@dataclass
class UsageOperation:
    """Container for usage operation data."""
    operation_id: str
    user_id: str
    operation_type: str
    token_usage: int
    model_used: str
    cost_usd: Decimal
    timestamp: datetime


class CostTrackingBillingL4Test(L4StagingCriticalPathTestBase):
    """L4 test for cost tracking and billing pipeline in staging environment."""
    
    def __init__(self):
        super().__init__("Cost Tracking and Billing Pipeline")
        self.cost_calculator: Optional[CostCalculator] = None
        self.usage_tracker: Optional[UsageTracker] = None
        self.invoice_generator: Optional[InvoiceGenerator] = None
        self.test_scenarios: List[BillingTestScenario] = []
        self.usage_operations: List[UsageOperation] = []
        self.billing_test_data: Dict[str, Any] = {}
        
    async def setup_test_specific_environment(self) -> None:
        """Setup billing-specific test environment."""
        # Initialize billing services
        self.cost_calculator = CostCalculator()
        await self.cost_calculator.initialize()
        
        self.usage_tracker = UsageTracker()
        await self.usage_tracker.initialize()
        
        self.invoice_generator = InvoiceGenerator()
        await self.invoice_generator.initialize()
        
        # Define test scenarios for different billing tiers
        self.test_scenarios = [
            BillingTestScenario(
                tier="free",
                monthly_quota=1000,
                cost_per_token=Decimal("0.001"),
                expected_operations=50,
                test_duration_seconds=30
            ),
            BillingTestScenario(
                tier="early",
                monthly_quota=10000,
                cost_per_token=Decimal("0.0008"),
                expected_operations=100,
                test_duration_seconds=45
            ),
            BillingTestScenario(
                tier="mid",
                monthly_quota=50000,
                cost_per_token=Decimal("0.0006"),
                expected_operations=200,
                test_duration_seconds=60
            ),
            BillingTestScenario(
                tier="enterprise",
                monthly_quota=1000000,
                cost_per_token=Decimal("0.0004"),
                expected_operations=500,
                test_duration_seconds=90
            )
        ]
        
        # Validate billing service connectivity
        await self._validate_billing_service_connectivity()
    
    async def _validate_billing_service_connectivity(self) -> None:
        """Validate billing service endpoints are accessible."""
        billing_endpoints = [
            f"{self.service_endpoints.billing}/health",
            f"{self.service_endpoints.billing}/cost-calculator/health",
            f"{self.service_endpoints.billing}/usage-tracker/health",
            f"{self.service_endpoints.billing}/invoicing/health"
        ]
        
        failed_endpoints = []
        
        for endpoint in billing_endpoints:
            try:
                response = await self.test_client.get(endpoint, timeout=10.0)
                if response.status_code != 200:
                    failed_endpoints.append(f"{endpoint} (HTTP {response.status_code})")
            except Exception as e:
                failed_endpoints.append(f"{endpoint} ({str(e)})")
        
        if failed_endpoints:
            raise RuntimeError(f"Billing service endpoints unavailable: {', '.join(failed_endpoints)}")
    
    async def execute_critical_path_test(self) -> Dict[str, Any]:
        """Execute cost tracking and billing pipeline critical path test."""
        test_results = {
            "phase_1_user_setup": None,
            "phase_2_usage_generation": None,
            "phase_3_cost_calculation": None,
            "phase_4_quota_enforcement": None,
            "phase_5_billing_aggregation": None,
            "phase_6_invoice_generation": None,
            "service_calls": 0
        }
        
        try:
            # Phase 1: Setup users for each billing tier
            user_setup_result = await self._setup_billing_tier_users()
            test_results["phase_1_user_setup"] = user_setup_result
            test_results["service_calls"] += user_setup_result.get("service_calls", 0)
            
            if not user_setup_result["success"]:
                return test_results
            
            # Phase 2: Generate realistic usage patterns
            usage_result = await self._generate_realistic_usage_patterns()
            test_results["phase_2_usage_generation"] = usage_result
            test_results["service_calls"] += usage_result.get("service_calls", 0)
            
            if not usage_result["success"]:
                return test_results
            
            # Phase 3: Validate cost calculation accuracy
            cost_calculation_result = await self._validate_cost_calculation_accuracy()
            test_results["phase_3_cost_calculation"] = cost_calculation_result
            test_results["service_calls"] += cost_calculation_result.get("service_calls", 0)
            
            # Phase 4: Test quota enforcement mechanisms
            quota_enforcement_result = await self._test_quota_enforcement()
            test_results["phase_4_quota_enforcement"] = quota_enforcement_result
            test_results["service_calls"] += quota_enforcement_result.get("service_calls", 0)
            
            # Phase 5: Validate billing aggregation
            billing_aggregation_result = await self._validate_billing_aggregation()
            test_results["phase_5_billing_aggregation"] = billing_aggregation_result
            test_results["service_calls"] += billing_aggregation_result.get("service_calls", 0)
            
            # Phase 6: Test invoice generation
            invoice_generation_result = await self._test_invoice_generation()
            test_results["phase_6_invoice_generation"] = invoice_generation_result
            test_results["service_calls"] += invoice_generation_result.get("service_calls", 0)
            
            return test_results
            
        except Exception as e:
            return {"success": False, "error": str(e), "test_results": test_results}
    
    async def _setup_billing_tier_users(self) -> Dict[str, Any]:
        """Setup test users for each billing tier."""
        try:
            tier_users = {}
            setup_operations = 0
            
            for scenario in self.test_scenarios:
                # Create user with billing configuration
                user_data = await self.create_test_user_with_billing(scenario.tier)
                
                if user_data["success"]:
                    tier_users[scenario.tier] = user_data
                    
                    # Configure tier-specific quotas and rates
                    quota_config = await self._configure_tier_quotas(
                        user_data["user_id"], scenario
                    )
                    user_data["quota_config"] = quota_config
                    
                setup_operations += 2  # user creation + quota config
            
            successful_setups = len(tier_users)
            
            self.billing_test_data["tier_users"] = tier_users
            
            return {
                "success": successful_setups >= 3,  # Need at least 3 tiers
                "total_tiers": len(self.test_scenarios),
                "successful_setups": successful_setups,
                "tier_users": tier_users,
                "service_calls": setup_operations
            }
            
        except Exception as e:
            return {"success": False, "error": str(e), "service_calls": 0}
    
    async def _configure_tier_quotas(self, user_id: str, 
                                   scenario: BillingTestScenario) -> Dict[str, Any]:
        """Configure quotas and rates for specific billing tier."""
        try:
            quota_config = {
                "user_id": user_id,
                "tier": scenario.tier,
                "monthly_quota_tokens": scenario.monthly_quota,
                "cost_per_token_usd": float(scenario.cost_per_token),
                "quota_reset_date": (datetime.utcnow() + timedelta(days=30)).isoformat(),
                "overage_allowed": scenario.tier in ["mid", "enterprise"],
                "overage_rate_multiplier": 1.5 if scenario.tier == "enterprise" else 2.0
            }
            
            quota_endpoint = f"{self.service_endpoints.billing}/quotas/configure"
            response = await self.test_client.post(
                quota_endpoint,
                json=quota_config,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code in [200, 201]:
                return {"success": True, "quota_data": response.json()}
            else:
                return {"success": False, "error": f"Quota config failed: {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _generate_realistic_usage_patterns(self) -> Dict[str, Any]:
        """Generate realistic usage patterns for each billing tier."""
        try:
            usage_patterns = {}
            total_operations = 0
            
            for scenario in self.test_scenarios:
                tier_users = self.billing_test_data["tier_users"]
                
                if scenario.tier not in tier_users:
                    continue
                
                user_data = tier_users[scenario.tier]
                user_id = user_data["user_id"]
                access_token = user_data["access_token"]
                
                # Generate tier-appropriate usage patterns
                usage_pattern = await self._simulate_tier_usage_pattern(
                    user_id, access_token, scenario
                )
                
                usage_patterns[scenario.tier] = usage_pattern
                total_operations += usage_pattern.get("operations_count", 0)
            
            self.billing_test_data["usage_patterns"] = usage_patterns
            
            return {
                "success": len(usage_patterns) >= 3,
                "total_usage_operations": total_operations,
                "tier_patterns": usage_patterns,
                "service_calls": total_operations
            }
            
        except Exception as e:
            return {"success": False, "error": str(e), "service_calls": 0}
    
    async def _simulate_tier_usage_pattern(self, user_id: str, access_token: str, 
                                         scenario: BillingTestScenario) -> Dict[str, Any]:
        """Simulate realistic usage pattern for a specific tier."""
        try:
            operations = []
            models_for_tier = self._get_models_for_tier(scenario.tier)
            
            # Generate usage operations based on tier characteristics
            for i in range(scenario.expected_operations):
                # Vary operation types and sizes realistically
                operation_type = self._get_weighted_operation_type(scenario.tier)
                model_used = self._select_model_for_operation(models_for_tier, operation_type)
                token_usage = self._calculate_realistic_token_usage(operation_type, scenario.tier)
                
                # Create usage operation
                usage_operation = await self._execute_billable_operation(
                    user_id, access_token, operation_type, model_used, token_usage
                )
                
                if usage_operation["success"]:
                    operations.append(usage_operation)
                
                # Add realistic delays between operations
                await asyncio.sleep(0.1)
            
            # Calculate total usage for this tier
            total_tokens = sum(op.get("token_usage", 0) for op in operations)
            total_cost = sum(Decimal(str(op.get("cost_usd", 0))) for op in operations)
            
            return {
                "success": len(operations) >= scenario.expected_operations * 0.8,
                "operations_count": len(operations),
                "total_tokens_used": total_tokens,
                "total_cost_usd": float(total_cost),
                "operations": operations
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _get_models_for_tier(self, tier: str) -> List[str]:
        """Get available models for billing tier."""
        tier_models = {
            "free": ["gemini-1.5-flash"],
            "early": ["gemini-1.5-flash", "gpt-4o-mini"],
            "mid": ["gemini-1.5-flash", "gpt-4o-mini", "gpt-4o", "claude-3-haiku"],
            "enterprise": ["gemini-1.5-flash", "gpt-4o-mini", "gpt-4o", "claude-3-haiku", "claude-3-sonnet", "gpt-4"]
        }
        return tier_models.get(tier, ["gemini-1.5-flash"])
    
    def _get_weighted_operation_type(self, tier: str) -> str:
        """Get weighted operation type based on tier usage patterns."""
        import random
        
        tier_operations = {
            "free": ["chat_completion", "simple_analysis"],
            "early": ["chat_completion", "simple_analysis", "code_generation"],
            "mid": ["chat_completion", "complex_analysis", "code_generation", "optimization"],
            "enterprise": ["chat_completion", "complex_analysis", "code_generation", "optimization", "batch_processing"]
        }
        
        operations = tier_operations.get(tier, ["chat_completion"])
        return random.choice(operations)
    
    def _select_model_for_operation(self, available_models: List[str], 
                                  operation_type: str) -> str:
        """Select appropriate model for operation type."""
        # Simple model selection logic
        if operation_type in ["simple_analysis", "chat_completion"]:
            return available_models[0]  # Use most cost-effective model
        else:
            return available_models[-1] if len(available_models) > 1 else available_models[0]
    
    def _calculate_realistic_token_usage(self, operation_type: str, tier: str) -> int:
        """Calculate realistic token usage for operation."""
        import random
        
        base_tokens = {
            "chat_completion": (100, 500),
            "simple_analysis": (200, 800),
            "code_generation": (500, 2000),
            "complex_analysis": (1000, 5000),
            "optimization": (2000, 8000),
            "batch_processing": (5000, 20000)
        }
        
        min_tokens, max_tokens = base_tokens.get(operation_type, (100, 500))
        
        # Enterprise tier typically uses more tokens per operation
        if tier == "enterprise":
            max_tokens = int(max_tokens * 1.5)
        elif tier == "free":
            max_tokens = int(max_tokens * 0.5)
        
        return random.randint(min_tokens, max_tokens)
    
    async def _execute_billable_operation(self, user_id: str, access_token: str,
                                        operation_type: str, model_used: str, 
                                        token_usage: int) -> Dict[str, Any]:
        """Execute a billable operation and track usage."""
        try:
            operation_id = f"op_{uuid.uuid4().hex[:12]}"
            
            # Execute operation via API
            operation_data = {
                "user_id": user_id,
                "operation_id": operation_id,
                "operation_type": operation_type,
                "model_requested": model_used,
                "estimated_tokens": token_usage,
                "billing_test": True
            }
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            operation_endpoint = f"{self.service_endpoints.backend}/api/ai/execute"
            response = await self.test_client.post(
                operation_endpoint,
                json=operation_data,
                headers=headers
            )
            
            if response.status_code == 200:
                result_data = response.json()
                actual_tokens = result_data.get("tokens_used", token_usage)
                cost_usd = result_data.get("cost_usd", 0.0)
                
                # Track usage operation
                usage_op = UsageOperation(
                    operation_id=operation_id,
                    user_id=user_id,
                    operation_type=operation_type,
                    token_usage=actual_tokens,
                    model_used=model_used,
                    cost_usd=Decimal(str(cost_usd)),
                    timestamp=datetime.utcnow()
                )
                
                self.usage_operations.append(usage_op)
                
                return {
                    "success": True,
                    "operation_id": operation_id,
                    "token_usage": actual_tokens,
                    "cost_usd": cost_usd,
                    "model_used": model_used
                }
            else:
                return {"success": False, "error": f"Operation failed: {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _validate_cost_calculation_accuracy(self) -> Dict[str, Any]:
        """Validate that cost calculations are accurate across all operations."""
        try:
            validation_results = []
            
            # Group operations by user for validation
            user_operations = {}
            for op in self.usage_operations:
                if op.user_id not in user_operations:
                    user_operations[op.user_id] = []
                user_operations[op.user_id].append(op)
            
            for user_id, operations in user_operations.items():
                # Calculate expected total cost
                expected_total = sum(op.cost_usd for op in operations)
                
                # Query actual billing total from system
                billing_query = await self._query_user_billing_total(user_id)
                
                if billing_query["success"]:
                    actual_total = Decimal(str(billing_query["total_cost_usd"]))
                    cost_accuracy = self._calculate_cost_accuracy(expected_total, actual_total)
                    
                    validation_results.append({
                        "user_id": user_id,
                        "success": cost_accuracy >= 0.99,  # 99% accuracy required
                        "expected_total": float(expected_total),
                        "actual_total": float(actual_total),
                        "accuracy": cost_accuracy,
                        "operations_count": len(operations)
                    })
                else:
                    validation_results.append({
                        "user_id": user_id,
                        "success": False,
                        "error": billing_query.get("error", "Unknown error")
                    })
            
            successful_validations = [r for r in validation_results if r.get("success", False)]
            
            return {
                "success": len(successful_validations) >= len(validation_results) * 0.9,
                "total_validations": len(validation_results),
                "successful_validations": len(successful_validations),
                "validation_results": validation_results,
                "service_calls": len(user_operations)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e), "service_calls": 0}
    
    async def _query_user_billing_total(self, user_id: str) -> Dict[str, Any]:
        """Query total billing amount for user."""
        try:
            billing_endpoint = f"{self.service_endpoints.billing}/users/{user_id}/total"
            response = await self.test_client.get(billing_endpoint)
            
            if response.status_code == 200:
                billing_data = response.json()
                return {
                    "success": True,
                    "total_cost_usd": billing_data.get("total_cost_usd", 0.0),
                    "billing_data": billing_data
                }
            else:
                return {"success": False, "error": f"Billing query failed: {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _calculate_cost_accuracy(self, expected: Decimal, actual: Decimal) -> float:
        """Calculate cost accuracy percentage."""
        if expected == 0:
            return 1.0 if actual == 0 else 0.0
        
        difference = abs(expected - actual)
        accuracy = 1.0 - (float(difference) / float(expected))
        return max(0.0, accuracy)
    
    async def _test_quota_enforcement(self) -> Dict[str, Any]:
        """Test quota enforcement mechanisms."""
        try:
            enforcement_results = []
            
            # Test quota enforcement for free tier (should hit limits)
            free_tier_user = self.billing_test_data["tier_users"].get("free")
            if free_tier_user:
                quota_test = await self._test_quota_limit_enforcement(
                    free_tier_user["user_id"], 
                    free_tier_user["access_token"],
                    quota_limit=1000
                )
                enforcement_results.append(quota_test)
            
            # Test overage handling for paid tiers
            for tier in ["early", "mid", "enterprise"]:
                tier_user = self.billing_test_data["tier_users"].get(tier)
                if tier_user:
                    overage_test = await self._test_overage_billing(
                        tier_user["user_id"],
                        tier_user["access_token"],
                        tier
                    )
                    enforcement_results.append(overage_test)
            
            successful_enforcements = [r for r in enforcement_results if r.get("success", False)]
            
            return {
                "success": len(successful_enforcements) >= len(enforcement_results) * 0.8,
                "total_enforcement_tests": len(enforcement_results),
                "successful_enforcements": len(successful_enforcements),
                "enforcement_results": enforcement_results,
                "service_calls": len(enforcement_results) * 3  # quota check + operation + validation
            }
            
        except Exception as e:
            return {"success": False, "error": str(e), "service_calls": 0}
    
    async def _test_quota_limit_enforcement(self, user_id: str, access_token: str,
                                          quota_limit: int) -> Dict[str, Any]:
        """Test that quota limits are properly enforced."""
        try:
            # Attempt operation that would exceed quota
            large_operation = {
                "user_id": user_id,
                "operation_type": "quota_test",
                "estimated_tokens": quota_limit + 100,  # Exceed quota
                "model_requested": "gemini-1.5-flash"
            }
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            operation_endpoint = f"{self.service_endpoints.backend}/api/ai/execute"
            response = await self.test_client.post(
                operation_endpoint,
                json=large_operation,
                headers=headers
            )
            
            # Should be rejected due to quota
            quota_enforced = response.status_code == 429  # Too Many Requests
            
            return {
                "user_id": user_id,
                "success": quota_enforced,
                "response_code": response.status_code,
                "quota_enforced": quota_enforced
            }
            
        except Exception as e:
            return {"user_id": user_id, "success": False, "error": str(e)}
    
    async def _test_overage_billing(self, user_id: str, access_token: str, 
                                  tier: str) -> Dict[str, Any]:
        """Test overage billing for paid tiers."""
        try:
            # For paid tiers, overage should be allowed but billed at higher rate
            overage_operation = {
                "user_id": user_id,
                "operation_type": "overage_test",
                "estimated_tokens": 10000,  # Large operation
                "model_requested": "gpt-4o"
            }
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            operation_endpoint = f"{self.service_endpoints.backend}/api/ai/execute"
            response = await self.test_client.post(
                operation_endpoint,
                json=overage_operation,
                headers=headers
            )
            
            # Should be allowed for paid tiers
            overage_allowed = response.status_code == 200
            
            if overage_allowed:
                result_data = response.json()
                overage_rate_applied = result_data.get("overage_rate_applied", False)
                
                return {
                    "user_id": user_id,
                    "tier": tier,
                    "success": overage_allowed and overage_rate_applied,
                    "overage_allowed": overage_allowed,
                    "overage_rate_applied": overage_rate_applied
                }
            else:
                return {
                    "user_id": user_id,
                    "tier": tier,
                    "success": False,
                    "error": "Overage not allowed for paid tier"
                }
                
        except Exception as e:
            return {"user_id": user_id, "tier": tier, "success": False, "error": str(e)}
    
    async def _validate_billing_aggregation(self) -> Dict[str, Any]:
        """Validate billing aggregation across time periods."""
        try:
            # Query billing aggregation for test period
            aggregation_endpoint = f"{self.service_endpoints.billing}/aggregation/test-period"
            response = await self.test_client.get(aggregation_endpoint)
            
            if response.status_code != 200:
                return {"success": False, "error": f"Aggregation query failed: {response.status_code}"}
            
            aggregation_data = response.json()
            
            # Validate aggregation completeness
            expected_users = len(self.billing_test_data["tier_users"])
            actual_users = len(aggregation_data.get("user_totals", []))
            
            # Validate total amounts
            calculated_total = sum(op.cost_usd for op in self.usage_operations)
            reported_total = Decimal(str(aggregation_data.get("total_revenue", 0)))
            
            aggregation_accuracy = self._calculate_cost_accuracy(calculated_total, reported_total)
            
            return {
                "success": actual_users >= expected_users * 0.9 and aggregation_accuracy >= 0.99,
                "expected_users": expected_users,
                "actual_users": actual_users,
                "calculated_total": float(calculated_total),
                "reported_total": float(reported_total),
                "aggregation_accuracy": aggregation_accuracy,
                "service_calls": 1
            }
            
        except Exception as e:
            return {"success": False, "error": str(e), "service_calls": 0}
    
    async def _test_invoice_generation(self) -> Dict[str, Any]:
        """Test invoice generation functionality."""
        try:
            invoice_results = []
            
            # Generate invoices for paid tier users
            for tier in ["early", "mid", "enterprise"]:
                tier_user = self.billing_test_data["tier_users"].get(tier)
                if not tier_user:
                    continue
                
                invoice_result = await self._generate_test_invoice(
                    tier_user["user_id"], tier
                )
                invoice_results.append(invoice_result)
            
            successful_invoices = [r for r in invoice_results if r.get("success", False)]
            
            return {
                "success": len(successful_invoices) >= len(invoice_results) * 0.8,
                "total_invoice_attempts": len(invoice_results),
                "successful_invoices": len(successful_invoices),
                "invoice_results": invoice_results,
                "service_calls": len(invoice_results)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e), "service_calls": 0}
    
    async def _generate_test_invoice(self, user_id: str, tier: str) -> Dict[str, Any]:
        """Generate test invoice for user."""
        try:
            invoice_data = {
                "user_id": user_id,
                "billing_period": "test_period",
                "tier": tier,
                "invoice_type": "test_invoice"
            }
            
            invoice_endpoint = f"{self.service_endpoints.billing}/invoices/generate"
            response = await self.test_client.post(
                invoice_endpoint,
                json=invoice_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code in [200, 201]:
                invoice_result = response.json()
                return {
                    "user_id": user_id,
                    "tier": tier,
                    "success": True,
                    "invoice_id": invoice_result.get("invoice_id"),
                    "total_amount": invoice_result.get("total_amount"),
                    "invoice_data": invoice_result
                }
            else:
                return {
                    "user_id": user_id,
                    "tier": tier,
                    "success": False,
                    "error": f"Invoice generation failed: {response.status_code}"
                }
                
        except Exception as e:
            return {"user_id": user_id, "tier": tier, "success": False, "error": str(e)}
    
    async def validate_critical_path_results(self, results: Dict[str, Any]) -> bool:
        """Validate billing pipeline meets business requirements."""
        try:
            # Validate all critical phases completed successfully
            critical_phases = [
                results.get("phase_1_user_setup", {}).get("success", False),
                results.get("phase_2_usage_generation", {}).get("success", False),
                results.get("phase_3_cost_calculation", {}).get("success", False),
                results.get("phase_4_quota_enforcement", {}).get("success", False),
                results.get("phase_5_billing_aggregation", {}).get("success", False)
            ]
            
            if not all(critical_phases):
                failed_phases = [f"phase_{i+1}" for i, success in enumerate(critical_phases) if not success]
                self.test_metrics.errors.append(f"Failed critical phases: {', '.join(failed_phases)}")
                return False
            
            # Validate business metrics for billing accuracy
            business_requirements = {
                "max_response_time_seconds": 2.0,  # Billing operations should be fast
                "min_success_rate_percent": 99.0,  # High accuracy required for billing
                "max_error_count": 0  # Zero tolerance for billing errors
            }
            
            return await self.validate_business_metrics(business_requirements)
            
        except Exception as e:
            self.test_metrics.errors.append(f"Result validation failed: {str(e)}")
            return False
    
    async def cleanup_test_specific_resources(self) -> None:
        """Clean up billing test data and services."""
        # Clean up billing services
        for service in [self.cost_calculator, self.usage_tracker, self.invoice_generator]:
            if service:
                try:
                    await service.shutdown()
                except Exception:
                    pass


# Pytest fixtures and test functions
@pytest.fixture
async def cost_tracking_billing_test():
    """Create cost tracking billing test instance."""
    test = CostTrackingBillingL4Test()
    await test.initialize_l4_environment()
    yield test
    await test.cleanup_l4_resources()


@pytest.mark.asyncio
@pytest.mark.staging
async def test_cost_tracking_billing_pipeline_l4(cost_tracking_billing_test):
    """Test complete cost tracking and billing pipeline in staging."""
    # Execute complete critical path test
    metrics = await cost_tracking_billing_test.run_complete_critical_path_test()
    
    # Validate test success
    assert metrics.success is True, f"Cost tracking billing test failed: {metrics.errors}"
    
    # Validate performance requirements
    assert metrics.duration < 300.0, f"Test took too long: {metrics.duration:.2f}s"
    assert metrics.success_rate >= 99.0, f"Success rate too low: {metrics.success_rate:.1f}%"
    assert metrics.error_count == 0, f"Billing errors not acceptable: {metrics.error_count}"
    
    # Validate business impact
    assert metrics.service_calls >= 20, "Insufficient billing operation coverage"
    
    # Log test results for financial monitoring
    print(f"Cost Tracking Billing Test Results:")
    print(f"  Duration: {metrics.duration:.2f}s")
    print(f"  Success Rate: {metrics.success_rate:.1f}%")
    print(f"  Service Calls: {metrics.service_calls}")
    print(f"  Total Operations: {len(cost_tracking_billing_test.usage_operations)}")


@pytest.mark.asyncio
@pytest.mark.staging
async def test_billing_accuracy_validation_l4(cost_tracking_billing_test):
    """Test billing accuracy across different tiers."""
    # Setup users and generate usage
    await cost_tracking_billing_test._setup_billing_tier_users()
    await cost_tracking_billing_test._generate_realistic_usage_patterns()
    
    # Validate cost calculation accuracy
    accuracy_results = await cost_tracking_billing_test._validate_cost_calculation_accuracy()
    
    assert accuracy_results["success"] is True, "Cost calculation accuracy failed"
    assert len(accuracy_results["validation_results"]) >= 3, "Insufficient tier coverage"
    
    # Validate individual accuracy scores
    for result in accuracy_results["validation_results"]:
        if result.get("success"):
            assert result["accuracy"] >= 0.99, f"Accuracy too low for user {result['user_id']}: {result['accuracy']}"


@pytest.mark.asyncio
@pytest.mark.staging
async def test_quota_enforcement_across_tiers_l4(cost_tracking_billing_test):
    """Test quota enforcement works correctly across all billing tiers."""
    # Setup tier users
    await cost_tracking_billing_test._setup_billing_tier_users()
    
    # Test quota enforcement
    enforcement_results = await cost_tracking_billing_test._test_quota_enforcement()
    
    assert enforcement_results["success"] is True, "Quota enforcement failed"
    assert enforcement_results["successful_enforcements"] >= 3, "Insufficient enforcement coverage"
    
    # Validate specific enforcement behaviors
    for result in enforcement_results["enforcement_results"]:
        if "tier" in result:
            tier = result["tier"]
            if tier == "free":
                # Free tier should have strict quota enforcement
                assert result.get("quota_enforced", False), f"Free tier quota not enforced for {result['user_id']}"
            else:
                # Paid tiers should allow overage with proper billing
                assert result.get("overage_allowed", False), f"Paid tier {tier} overage not allowed"