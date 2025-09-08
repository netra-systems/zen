"""
Test Cost Calculation Business Logic - Core Unit Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Revenue integrity and cost optimization accuracy
- Value Impact: Ensures accurate billing calculations prevent revenue leakage and customer disputes
- Strategic Impact: CRITICAL - Billing accuracy directly impacts business sustainability and customer trust

This test suite validates the core business logic for cost calculations that determine
customer billing amounts across all pricing tiers.
"""

import pytest
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone, timedelta
from test_framework.base import BaseTestCase
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.services.billing.cost_calculator import (
    CostCalculator,
    CostType,
    CostComponent,
    CostBreakdown,
    PricingTier
)


class TestCostCalculationBusinessValue(BaseTestCase):
    """Test cost calculation delivers accurate billing for business value."""
    
    def setup_method(self):
        """Setup test environment with isolated configuration."""
        super().setup_method()
        self.env = IsolatedEnvironment()
        self.calculator = CostCalculator()
        
        # Reset to clean state for each test
        self.calculator.discount_rules = []
        
    def teardown_method(self):
        """Clean up test environment."""
        super().teardown_method()
        
    @pytest.mark.unit
    def test_free_tier_respects_usage_limits(self):
        """Test that free tier correctly applies usage limits preventing overcharges."""
        # Given: Usage within free tier limits
        usage_data = {
            "api_calls": {"quantity": 500},  # Under 1000 limit
            "llm_tokens": {"quantity": 25000},  # Under 50000 limit
            "storage": {"quantity": 0.5}  # Under 1GB limit
        }
        
        # When: Calculate cost for free tier
        breakdown = self.calculator.calculate_cost_breakdown(
            user_id="free_user_123",
            usage_data=usage_data,
            tier_name="free"
        )
        
        # Then: Total cost should be zero (no overages)
        assert breakdown.total_cost == Decimal("0.00")
        assert breakdown.subtotal == Decimal("0.00")
        assert len(breakdown.components) == 0  # No billable components
        
        # And: Usage metadata should be preserved
        assert breakdown.user_id == "free_user_123"
        assert breakdown.metadata["tier"] == "free"
        
    @pytest.mark.unit
    def test_free_tier_applies_overage_charges_correctly(self):
        """Test that free tier charges overages when limits exceeded."""
        # Given: Usage exceeding free tier limits
        usage_data = {
            "api_calls": {"quantity": 1500},  # Exceeds 1000 limit by 500
            "llm_tokens": {"quantity": 75000},  # Exceeds 50000 limit by 25000
        }
        
        # When: Calculate cost for free tier
        breakdown = self.calculator.calculate_cost_breakdown(
            user_id="free_user_overage",
            usage_data=usage_data,
            tier_name="free"
        )
        
        # Then: Should have overage charges
        assert breakdown.subtotal > Decimal("0.00")
        assert len(breakdown.components) > 0
        
        # And: Each component should have correct overage metadata
        for component in breakdown.components:
            assert component.metadata is not None
            assert "overage_cost" in component.metadata
            assert component.metadata["overage_cost"] > 0
            
    @pytest.mark.unit
    def test_pricing_tier_cost_calculations_accuracy(self):
        """Test accurate cost calculations across different pricing tiers."""
        usage_data = {
            "api_calls": {"quantity": 10000},
            "llm_tokens": {"quantity": 100000},
            "storage": {"quantity": 5}
        }
        
        tiers_to_test = ["starter", "professional", "enterprise"]
        tier_costs = {}
        
        for tier_name in tiers_to_test:
            breakdown = self.calculator.calculate_cost_breakdown(
                user_id=f"test_user_{tier_name}",
                usage_data=usage_data,
                tier_name=tier_name
            )
            tier_costs[tier_name] = breakdown.total_cost
            
            # Each tier should have valid cost structure
            assert breakdown.subtotal >= Decimal("0.00")
            assert breakdown.total_cost >= breakdown.subtotal  # After taxes
            assert len(breakdown.components) > 0
        
        # Enterprise should be cheapest per unit for high usage
        assert tier_costs["enterprise"] <= tier_costs["professional"]
        assert tier_costs["professional"] <= tier_costs["starter"]
        
    @pytest.mark.unit
    def test_cost_component_calculation_precision(self):
        """Test that cost calculations maintain decimal precision for financial accuracy."""
        usage_data = {
            "llm_tokens": {"quantity": 123456},  # Odd number to test precision
            "api_calls": {"quantity": 7891}
        }
        
        breakdown = self.calculator.calculate_cost_breakdown(
            user_id="precision_test_user",
            usage_data=usage_data,
            tier_name="professional"
        )
        
        # All monetary values should be rounded to 2 decimal places
        assert breakdown.subtotal.as_tuple().exponent >= -2
        assert breakdown.total_cost.as_tuple().exponent >= -2
        assert breakdown.taxes.as_tuple().exponent >= -2
        
        for component in breakdown.components:
            assert component.total_cost.as_tuple().exponent >= -2
            assert component.unit_price.as_tuple().exponent >= -6  # Allow more precision for unit prices
            
    @pytest.mark.unit
    def test_tax_calculation_by_region(self):
        """Test that tax calculations vary correctly by region for compliance."""
        usage_data = {
            "api_calls": {"quantity": 1000}
        }
        
        # Test different regions
        regions = ["default", "enterprise", "eu", "canada"]
        expected_tax_rates = {
            "default": Decimal("0.08"),
            "enterprise": Decimal("0.00"),
            "eu": Decimal("0.20"), 
            "canada": Decimal("0.13")
        }
        
        for region in regions:
            breakdown = self.calculator.calculate_cost_breakdown(
                user_id=f"tax_test_{region}",
                usage_data=usage_data,
                tier_name="starter",
                region=region
            )
            
            if breakdown.subtotal > 0:
                expected_tax = (breakdown.subtotal * expected_tax_rates[region]).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                assert breakdown.taxes == expected_tax
                assert breakdown.metadata["tax_rate"] == float(expected_tax_rates[region])
                
    @pytest.mark.unit
    def test_monthly_base_fee_application(self):
        """Test that monthly base fees are applied correctly to paid tiers."""
        # Test with minimal usage to isolate base fee
        usage_data = {
            "api_calls": {"quantity": 1}
        }
        
        tiers_with_base_fees = {
            "starter": Decimal("10.00"),
            "professional": Decimal("50.00"), 
            "enterprise": Decimal("500.00")
        }
        
        for tier_name, expected_base_fee in tiers_with_base_fees.items():
            breakdown = self.calculator.calculate_cost_breakdown(
                user_id=f"base_fee_test_{tier_name}",
                usage_data=usage_data,
                tier_name=tier_name
            )
            
            # Find the monthly fee component
            monthly_fee_component = None
            for component in breakdown.components:
                if "Monthly Fee" in component.description:
                    monthly_fee_component = component
                    break
                    
            assert monthly_fee_component is not None
            assert monthly_fee_component.total_cost == expected_base_fee
            assert monthly_fee_component.unit == "month"
            
    @pytest.mark.unit  
    def test_cost_breakdown_completeness(self):
        """Test that cost breakdown contains all required fields for business reporting."""
        usage_data = {
            "api_calls": {"quantity": 5000},
            "llm_tokens": {"quantity": 50000},
            "storage": {"quantity": 2},
            "bandwidth": {"quantity": 10}
        }
        
        breakdown = self.calculator.calculate_cost_breakdown(
            user_id="completeness_test_user",
            usage_data=usage_data,
            tier_name="professional"
        )
        
        # Verify all required fields are present
        assert breakdown.user_id is not None
        assert breakdown.period_start is not None
        assert breakdown.period_end is not None
        assert isinstance(breakdown.components, list)
        assert breakdown.subtotal is not None
        assert breakdown.discounts is not None
        assert breakdown.taxes is not None
        assert breakdown.total_cost is not None
        assert breakdown.currency == "USD"
        
        # Verify mathematical relationship
        expected_total = breakdown.subtotal - breakdown.discounts + breakdown.taxes
        assert breakdown.total_cost == expected_total
        
        # Each component should be complete
        for component in breakdown.components:
            assert component.cost_type is not None
            assert component.quantity > 0
            assert component.unit_price is not None
            assert component.total_cost is not None
            assert component.unit is not None
            assert component.description is not None
            
    @pytest.mark.unit
    def test_monthly_cost_estimation_accuracy(self):
        """Test that monthly cost estimation provides accurate projections for sales."""
        usage_projections = {
            "api_calls": 15000.0,
            "llm_tokens": 200000.0,
            "storage": 5.0,
            "bandwidth": 20.0
        }
        
        estimate = self.calculator.estimate_monthly_cost(
            usage_projections=usage_projections,
            tier_name="professional"
        )
        
        # Verify estimation structure
        assert estimate["tier"] == "professional"
        assert "projected_monthly_cost" in estimate
        assert estimate["projected_monthly_cost"] > 0
        assert "breakdown_by_type" in estimate
        assert "subtotal" in estimate
        assert "discounts" in estimate  
        assert "taxes" in estimate
        
        # Breakdown should match input projections
        breakdown = estimate["breakdown_by_type"]
        for cost_type, projected_quantity in usage_projections.items():
            if cost_type in breakdown:
                assert breakdown[cost_type]["quantity"] == projected_quantity
                assert breakdown[cost_type]["total_cost"] >= 0
                
    @pytest.mark.unit
    def test_tier_comparison_business_logic(self):
        """Test tier comparison functionality for customer upgrade decisions."""
        usage_projections = {
            "api_calls": 25000.0,
            "llm_tokens": 500000.0,
            "storage": 10.0
        }
        
        comparison = self.calculator.compare_tier_costs(usage_projections)
        
        # Verify comparison structure
        assert "comparisons" in comparison
        assert "cheapest_tier" in comparison
        assert "cheapest_cost" in comparison
        assert "usage_projections" in comparison
        
        # All tiers should be compared
        comparisons = comparison["comparisons"]
        expected_tiers = ["free", "starter", "professional", "enterprise"]
        for tier in expected_tiers:
            assert tier in comparisons
            assert "projected_monthly_cost" in comparisons[tier]
            
        # Cheapest tier should actually be cheapest
        cheapest_tier = comparison["cheapest_tier"]
        cheapest_cost = comparison["cheapest_cost"]
        
        for tier_name, tier_data in comparisons.items():
            if tier_name != cheapest_tier:
                assert tier_data["projected_monthly_cost"] >= cheapest_cost
                
    @pytest.mark.unit
    def test_cost_calculator_statistics_tracking(self):
        """Test that cost calculator tracks usage statistics for business analytics."""
        initial_stats = self.calculator.get_stats()
        initial_calculations = initial_stats["calculations_performed"]
        
        # Perform several calculations
        usage_data = {"api_calls": {"quantity": 1000}}
        
        for i in range(3):
            self.calculator.calculate_cost_breakdown(
                user_id=f"stats_test_{i}",
                usage_data=usage_data,
                tier_name="starter"
            )
            
        final_stats = self.calculator.get_stats()
        
        # Statistics should be updated
        assert final_stats["calculations_performed"] == initial_calculations + 3
        assert final_stats["total_cost_calculated"] > 0
        assert final_stats["average_calculation_value"] > 0
        assert "starter" in final_stats["calculations_by_tier"]
        
    @pytest.mark.unit
    def test_disabled_calculator_prevents_calculations(self):
        """Test that disabled calculator prevents cost calculations for maintenance mode."""
        # Given: Calculator is disabled
        self.calculator.disable()
        
        usage_data = {"api_calls": {"quantity": 1000}}
        
        # When/Then: Calculation should raise runtime error
        with pytest.raises(RuntimeError, match="Cost calculator is disabled"):
            self.calculator.calculate_cost_breakdown(
                user_id="disabled_test",
                usage_data=usage_data,
                tier_name="starter"
            )
            
        # And: Calculator can be re-enabled
        self.calculator.enable()
        
        # Should work after re-enabling
        breakdown = self.calculator.calculate_cost_breakdown(
            user_id="enabled_test",
            usage_data=usage_data,
            tier_name="starter"
        )
        assert breakdown.total_cost >= 0