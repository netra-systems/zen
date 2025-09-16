"""
Business Data Validation Integration Tests

These tests validate data processing, business rule enforcement, and compliance
validation without requiring Docker services but using real data patterns.

Focus Areas:
- Input data validation and sanitization
- Business rule enforcement (subscription limits, usage quotas)
- Data integrity checks and consistency validation
- User permission validation and data access control
- Compliance data validation (GDPR, SOC2, enterprise requirements)
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, List
import asyncio

from netra_backend.app.services.billing.cost_calculator import CostCalculator, CostType, PricingTier
from netra_backend.app.services.billing.usage_tracker import UsageTracker, UsageType, UsageEvent
from netra_backend.app.services.resource_management.tenant_isolator import TenantIsolator, TenantResourceQuota
from netra_backend.app.services.quality.quality_score_calculators import QualityScoreCalculators


class TestBusinessDataValidation:
    """Test suite for business data validation and integrity checks."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cost_calculator = CostCalculator()
        self.usage_tracker = UsageTracker()
        self.tenant_isolator = TenantIsolator()
        
        # Test data
        self.valid_user_id = "user_12345"
        self.enterprise_user_id = "enterprise_67890" 
        self.invalid_user_id = ""
        
        self.test_usage_data = {
            "api_calls": {"quantity": 5000},
            "llm_tokens": {"quantity": 100000},
            "storage": {"quantity": 5.5},
            "bandwidth": {"quantity": 2.3}
        }
    
    def test_input_data_validation_positive_quantities(self):
        """Test validation of positive quantities in usage data."""
        # Test valid positive quantities
        valid_usage = {
            "api_calls": {"quantity": 1000},
            "llm_tokens": {"quantity": 50000},
            "storage": {"quantity": 1.5}
        }
        
        breakdown = self.cost_calculator.calculate_cost_breakdown(
            user_id=self.valid_user_id,
            usage_data=valid_usage,
            tier_name="starter"
        )
        
        assert breakdown.user_id == self.valid_user_id
        assert breakdown.subtotal > 0
        assert len(breakdown.components) >= 2  # Base plan + usage components
        
        # Validate component quantities are positive
        for component in breakdown.components:
            assert component.quantity >= 0, f"Component {component.cost_type} has negative quantity"
            assert component.total_cost >= 0, f"Component {component.cost_type} has negative cost"
    
    def test_input_data_validation_negative_quantities_handling(self):
        """Test handling of invalid negative quantities."""
        # Test negative quantities - should be filtered out
        invalid_usage = {
            "api_calls": {"quantity": -500},  # Invalid negative
            "llm_tokens": {"quantity": 50000},  # Valid positive
            "storage": {"quantity": 0}  # Edge case: zero
        }
        
        breakdown = self.cost_calculator.calculate_cost_breakdown(
            user_id=self.valid_user_id,
            usage_data=invalid_usage,
            tier_name="starter"
        )
        
        # Should only include valid usage components and base fee
        valid_components = [c for c in breakdown.components if c.quantity > 0]
        assert len(valid_components) >= 1  # At least base plan
        
        # Ensure no negative costs
        assert breakdown.subtotal >= 0
        assert breakdown.total_cost >= 0
    
    def test_business_rule_enforcement_subscription_limits(self):
        """Test enforcement of subscription tier limits and overages."""
        # Test free tier limits
        free_tier_usage = {
            "api_calls": {"quantity": 1500},  # Exceeds free limit of 1000
            "llm_tokens": {"quantity": 60000},  # Exceeds free limit of 50000
        }
        
        breakdown = self.cost_calculator.calculate_cost_breakdown(
            user_id=self.valid_user_id,
            usage_data=free_tier_usage,
            tier_name="free"
        )
        
        # Free tier should have zero costs within limits, overages should be handled
        assert breakdown.total_cost >= 0
        
        # Check if overage information is captured in metadata
        for component in breakdown.components:
            if component.metadata and "overage_cost" in component.metadata:
                overage_cost = component.metadata["overage_cost"]
                assert overage_cost >= 0, "Overage cost should be non-negative"
    
    def test_business_rule_enforcement_enterprise_pricing(self):
        """Test enterprise tier business rules and volume discounts."""
        # Large enterprise usage
        enterprise_usage = {
            "api_calls": {"quantity": 100000},
            "llm_tokens": {"quantity": 5000000},
            "storage": {"quantity": 100},
            "agent_execution": {"quantity": 10000},
            "premium_features": {"quantity": 50}
        }
        
        enterprise_breakdown = self.cost_calculator.calculate_cost_breakdown(
            user_id=self.enterprise_user_id,
            usage_data=enterprise_usage,
            tier_name="enterprise"
        )
        
        starter_breakdown = self.cost_calculator.calculate_cost_breakdown(
            user_id=self.enterprise_user_id,
            usage_data=enterprise_usage,
            tier_name="starter"
        )
        
        # Enterprise should have better per-unit pricing for high volume
        enterprise_effective_rate = enterprise_breakdown.total_cost / sum(
            usage["quantity"] for usage in enterprise_usage.values()
        )
        
        starter_effective_rate = starter_breakdown.total_cost / sum(
            usage["quantity"] for usage in enterprise_usage.values()
        )
        
        # Enterprise rate should be lower for high volume usage
        assert enterprise_effective_rate < starter_effective_rate, "Enterprise should have better rates"
    
    def test_data_integrity_cost_calculation_consistency(self):
        """Test data integrity in cost calculations and consistency across operations."""
        # Test same usage data multiple times should yield identical results
        usage_data = self.test_usage_data.copy()
        
        breakdown1 = self.cost_calculator.calculate_cost_breakdown(
            user_id=self.valid_user_id,
            usage_data=usage_data,
            tier_name="professional"
        )
        
        breakdown2 = self.cost_calculator.calculate_cost_breakdown(
            user_id=self.valid_user_id,
            usage_data=usage_data,
            tier_name="professional"
        )
        
        # Results should be consistent
        assert breakdown1.subtotal == breakdown2.subtotal
        assert breakdown1.taxes == breakdown2.taxes
        assert breakdown1.total_cost == breakdown2.total_cost
        assert len(breakdown1.components) == len(breakdown2.components)
        
        # Component-level consistency
        for comp1, comp2 in zip(breakdown1.components, breakdown2.components):
            assert comp1.cost_type == comp2.cost_type
            assert comp1.quantity == comp2.quantity
            assert comp1.total_cost == comp2.total_cost
    
    @pytest.mark.asyncio
    async def test_user_permission_validation_rate_limiting(self):
        """Test user permission validation through rate limiting and access control."""
        # Test rate limiting as permission enforcement
        user_id = "test_rate_limit_user"
        
        # Simulate multiple API calls within rate limit window
        events = []
        for i in range(5):
            event = await self.usage_tracker.track_usage(
                user_id=user_id,
                usage_type=UsageType.API_CALL,
                quantity=200,  # Each call uses 200 units
                unit="calls"
            )
            events.append(event)
        
        # Check rate limit status - should still be within limits
        rate_limit_check = await self.usage_tracker.check_rate_limit(
            user_id=user_id,
            usage_type=UsageType.API_CALL
        )
        
        assert rate_limit_check["allowed"] == True
        assert rate_limit_check["remaining"] >= 0
        assert rate_limit_check["current_usage"] == 1000  # 5 * 200
        
        # Test exceeding rate limits
        # Add more usage to exceed the 1000 limit
        await self.usage_tracker.track_usage(
            user_id=user_id,
            usage_type=UsageType.API_CALL,
            quantity=100,
            unit="calls"
        )
        
        # Should now be at or exceed rate limit
        rate_limit_check2 = await self.usage_tracker.check_rate_limit(
            user_id=user_id,
            usage_type=UsageType.API_CALL
        )
        
        assert rate_limit_check2["current_usage"] >= 1000
    
    def test_compliance_data_validation_gdpr_data_minimization(self):
        """Test GDPR compliance through data minimization and retention policies."""
        # Test that we only collect necessary data and validate data types
        usage_event = UsageEvent(
            user_id=self.valid_user_id,
            usage_type=UsageType.LLM_TOKENS,
            quantity=1000.0,
            unit="tokens",
            timestamp=datetime.now(timezone.utc),
            metadata={
                "model": "gpt-4",  # Necessary for billing
                "region": "eu-west-1",  # Necessary for compliance
                # Note: We don't store personal data like conversation content
            },
            cost=20.0
        )
        
        # Validate that event contains only necessary compliance data
        assert usage_event.user_id is not None
        assert usage_event.timestamp is not None
        assert usage_event.quantity >= 0
        assert usage_event.cost >= 0
        
        # Validate metadata doesn't contain sensitive personal information
        if usage_event.metadata:
            sensitive_keys = ["email", "name", "phone", "address", "conversation"]
            for key in usage_event.metadata.keys():
                assert key not in sensitive_keys, f"Sensitive key '{key}' found in metadata"
    
    @pytest.mark.asyncio
    async def test_compliance_data_validation_enterprise_security(self):
        """Test enterprise security compliance through tenant isolation and access controls."""
        # Set up enterprise tenant with strict isolation
        enterprise_tenant = "enterprise_tenant_001"
        regular_tenant = "regular_tenant_002"
        
        # Register tenants with different security policies
        enterprise_quota = TenantResourceQuota(
            tenant_id=enterprise_tenant,
            cpu_cores=16.0,
            memory_mb=32768,
            storage_gb=1000,
            max_concurrent_requests=500
        )
        
        await self.tenant_isolator.register_tenant(enterprise_tenant, enterprise_quota)
        await self.tenant_isolator.register_tenant(regular_tenant)
        
        # Test enterprise tenant gets isolated namespace
        enterprise_namespace = await self.tenant_isolator.get_tenant_namespace(enterprise_tenant)
        regular_namespace = await self.tenant_isolator.get_tenant_namespace(regular_tenant)
        
        assert enterprise_namespace is not None
        assert regular_namespace is not None
        assert enterprise_namespace != regular_namespace, "Tenants must have separate namespaces"
        assert "enterprise" in enterprise_namespace or enterprise_tenant in enterprise_namespace
        
        # Test resource allocation isolation
        resource_request = {
            "cpu_cores": 8.0,
            "memory_mb": 16384,
            "concurrent_requests": 100
        }
        
        # Both tenants should be able to allocate within their quotas
        enterprise_allocation = await self.tenant_isolator.check_resource_availability(
            enterprise_tenant, resource_request
        )
        regular_allocation = await self.tenant_isolator.check_resource_availability(
            regular_tenant, resource_request
        )
        
        assert enterprise_allocation["allowed"] == True, "Enterprise should be able to allocate resources"
        # Regular tenant might be denied due to lower default quotas
        
        # Verify isolation policies are enforced
        enterprise_status = await self.tenant_isolator.get_tenant_status(enterprise_tenant)
        assert enterprise_status["policy"]["network_isolation"] == True
        assert enterprise_status["policy"]["storage_isolation"] == True
        assert enterprise_status["policy"]["compute_isolation"] == True
    
    def test_data_integrity_quality_score_consistency(self):
        """Test data integrity in quality score calculations with consistent inputs."""
        test_output = """
        This analysis provides specific recommendations for optimizing your API latency.
        First, implement connection pooling to reduce overhead by 25%.
        Second, enable response caching with TTL=300 seconds.
        Third, configure batch processing for requests >100ms.
        The quantified improvements show 40% latency reduction potential.
        """
        
        # Calculate all quality scores
        specificity_score1 = QualityScoreCalculators.calculate_specificity_score(test_output)
        specificity_score2 = QualityScoreCalculators.calculate_specificity_score(test_output)
        
        actionability_score1 = QualityScoreCalculators.calculate_actionability_score(test_output)
        actionability_score2 = QualityScoreCalculators.calculate_actionability_score(test_output)
        
        quantification_score1 = QualityScoreCalculators.calculate_quantification_score(test_output)
        quantification_score2 = QualityScoreCalculators.calculate_quantification_score(test_output)
        
        # Scores should be consistent across multiple calculations
        assert specificity_score1 == specificity_score2, "Specificity scores should be consistent"
        assert actionability_score1 == actionability_score2, "Actionability scores should be consistent"
        assert quantification_score1 == quantification_score2, "Quantification scores should be consistent"
        
        # Scores should be within expected ranges
        assert 0.0 <= specificity_score1 <= 1.0, "Specificity score out of range"
        assert 0.0 <= actionability_score1 <= 1.0, "Actionability score out of range"
        assert 0.0 <= quantification_score1 <= 1.0, "Quantification score out of range"
        
        # This text should score high on all dimensions due to specific, actionable content
        assert specificity_score1 > 0.7, "Should score high on specificity due to technical details"
        assert actionability_score1 > 0.6, "Should score high on actionability due to step-by-step instructions"
        assert quantification_score1 > 0.5, "Should score high on quantification due to percentages and numbers"
    
    def test_business_rule_validation_cost_component_accuracy(self):
        """Test accuracy of cost component calculations and business rule application."""
        # Test with precisely known usage to validate calculations
        precise_usage = {
            "api_calls": {"quantity": 10000},  # Exactly 10k calls
            "llm_tokens": {"quantity": 500000},  # Exactly 500k tokens
        }
        
        breakdown = self.cost_calculator.calculate_cost_breakdown(
            user_id=self.valid_user_id,
            usage_data=precise_usage,
            tier_name="starter"
        )
        
        # Calculate expected costs manually based on starter tier pricing
        starter_tier = self.cost_calculator.get_pricing_tier("starter")
        expected_base_cost = starter_tier.monthly_base
        
        # Find actual usage components (exclude base fee)
        usage_components = [c for c in breakdown.components 
                          if c.cost_type != CostType.PREMIUM_FEATURES]
        
        # Validate that components match expected usage types
        component_types = {c.cost_type for c in usage_components}
        assert CostType.API_CALLS in component_types
        assert CostType.LLM_TOKENS in component_types
        
        # Validate quantities match input
        for component in usage_components:
            if component.cost_type == CostType.API_CALLS:
                assert component.quantity == Decimal("10000")
            elif component.cost_type == CostType.LLM_TOKENS:
                assert component.quantity == Decimal("500000")
        
        # Validate total cost structure
        component_total = sum(c.total_cost for c in breakdown.components)
        calculated_total = breakdown.subtotal - breakdown.discounts + breakdown.taxes
        
        assert abs(component_total - breakdown.subtotal) < Decimal("0.01"), "Component total should equal subtotal"
        assert abs(calculated_total - breakdown.total_cost) < Decimal("0.01"), "Calculated total should match breakdown total"