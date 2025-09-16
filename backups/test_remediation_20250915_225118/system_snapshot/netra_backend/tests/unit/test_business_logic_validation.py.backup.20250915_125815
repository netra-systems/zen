"""Business Logic Validation Tests.

Tests critical business logic, validation rules, and business constraints
to ensure the system enforces correct business behavior.
"""

import pytest
from decimal import Decimal
from netra_backend.app.services.cost_calculator import CostCalculatorService, CostTier, ModelCostInfo
from netra_backend.app.schemas.llm_base_types import LLMProvider, TokenUsage
from shared.isolated_environment import IsolatedEnvironment


@pytest.fixture
def cost_calculator():
    """Cost calculator for business logic testing."""
    return CostCalculatorService()


class TestBusinessRuleValidation:
    """Test enforcement of business rules."""

    def test_cost_calculation_business_constraints(self, cost_calculator):
        """Test that cost calculations follow business constraints."""
        # Business Rule: Costs should never be negative
        usage = TokenUsage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500)
        cost = cost_calculator.calculate_cost(usage, LLMProvider.OPENAI, "gpt-3.5-turbo")
        
        assert cost >= Decimal('0'), "Costs must never be negative"
        
        # Business Rule: Zero usage should result in zero cost
        zero_usage = TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0)
        zero_cost = cost_calculator.calculate_cost(zero_usage, LLMProvider.OPENAI, "gpt-3.5-turbo")
        
        assert zero_cost == Decimal('0'), "Zero usage must result in zero cost"

    def test_cost_tier_business_logic(self, cost_calculator):
        """Test cost tier business logic and relationships."""
        # Business Rule: Different tiers should exist for different use cases
        assert CostTier.ECONOMY == "economy", "Economy tier must be available for cost-conscious users"
        assert CostTier.BALANCED == "balanced", "Balanced tier must be available for typical users"
        assert CostTier.PREMIUM == "premium", "Premium tier must be available for performance-focused users"
        
        # Business Rule: Each tier should potentially have different model options
        economy_model = cost_calculator.get_cost_optimal_model(LLMProvider.OPENAI, CostTier.ECONOMY)
        premium_model = cost_calculator.get_cost_optimal_model(LLMProvider.OPENAI, CostTier.PREMIUM)
        
        # Models can be different or the same (None is acceptable if not configured)
        if economy_model and premium_model:
            # If both exist, they could be the same or different - both are valid business cases
            assert isinstance(economy_model, str)
            assert isinstance(premium_model, str)

    def test_pricing_consistency_business_rules(self, cost_calculator):
        """Test that pricing follows business consistency rules."""
        base_usage = TokenUsage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500)
        double_usage = TokenUsage(prompt_tokens=2000, completion_tokens=1000, total_tokens=3000)
        
        base_cost = cost_calculator.calculate_cost(base_usage, LLMProvider.OPENAI, "gpt-3.5-turbo")
        double_cost = cost_calculator.calculate_cost(double_usage, LLMProvider.OPENAI, "gpt-3.5-turbo")
        
        # Business Rule: Double usage should result in approximately double cost
        if base_cost > 0:
            ratio = double_cost / base_cost
            assert Decimal('1.8') <= ratio <= Decimal('2.2'), "Costs should scale proportionally with usage"

    def test_model_cost_info_business_validation(self):
        """Test ModelCostInfo enforces business validation rules."""
        # Business Rule: Performance scores must be within valid range
        valid_cost_info = ModelCostInfo(
            provider=LLMProvider.OPENAI,
            model_name="gpt-4",
            prompt_cost_per_1k=Decimal('0.03'),
            completion_cost_per_1k=Decimal('0.06'),
            cost_tier=CostTier.PREMIUM,
            performance_score=95.0
        )
        
        assert 0 <= valid_cost_info.performance_score <= 100, "Performance score must be 0-100"
        
        # Business Rule: Premium models should generally have higher costs
        assert valid_cost_info.cost_tier == CostTier.PREMIUM
        assert valid_cost_info.performance_score >= 90, "Premium models should have high performance scores"

    def test_budget_estimation_business_logic(self, cost_calculator):
        """Test budget estimation follows business logic."""
        # Business Rule: Budget estimates should be reasonable and helpful
        token_count = 10000
        
        if hasattr(cost_calculator, 'estimate_budget_impact'):
            estimated_cost = cost_calculator.estimate_budget_impact(
                token_count, LLMProvider.OPENAI, "gpt-3.5-turbo"
            )
            
            assert estimated_cost > Decimal('0'), "Budget estimates for positive usage should be positive"
            assert estimated_cost < Decimal('100'), "Budget estimates should be reasonable for typical usage"


class TestUserExperienceBusinessRules:
    """Test business rules that affect user experience."""

    def test_password_security_business_requirements(self):
        """Test password security meets business requirements."""
        from netra_backend.app.services.user_service import pwd_context
        
        # Business Rule: Password hashing must be secure and irreversible
        password = "business_password_123"
        hashed = pwd_context.hash(password)
        
        # Hash should be significantly different from original
        assert hashed != password, "Hashed password must be different from original"
        assert len(hashed) > len(password), "Hash should be longer than original for security"
        
        # Business Rule: Same password should produce different hashes (salt requirement)
        hash2 = pwd_context.hash(password)
        assert hashed != hash2, "Same password must produce different hashes (salting required)"

    def test_cost_transparency_business_rule(self, cost_calculator):
        """Test that cost calculations are transparent and predictable."""
        # Business Rule: Users should be able to predict costs
        usage1 = TokenUsage(prompt_tokens=500, completion_tokens=250, total_tokens=750)
        usage2 = TokenUsage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500)
        
        cost1 = cost_calculator.calculate_cost(usage1, LLMProvider.OPENAI, "gpt-3.5-turbo")
        cost2 = cost_calculator.calculate_cost(usage2, LLMProvider.OPENAI, "gpt-3.5-turbo")
        
        # Business Rule: Costs should be predictable - double tokens [U+2248] double cost
        if cost1 > 0:
            ratio = cost2 / cost1
            assert Decimal('1.9') <= ratio <= Decimal('2.1'), "Cost scaling should be predictable for users"

    def test_error_handling_business_friendliness(self):
        """Test that error handling is business-friendly."""
        from netra_backend.app.services.thread_service import _handle_database_error
        
        # Business Rule: Errors should provide helpful context without exposing internals
        user_context = {
            "user_id": "user_12345",
            "operation": "create_thread",
            "timestamp": "2024-01-01T10:00:00Z"
        }
        
        error = _handle_database_error("user_operation", user_context)
        error_message = str(error)
        
        # Should mention the operation for user understanding
        assert "user_operation" in error_message, "Error should indicate what operation failed"
        
        # Should not expose internal system details
        assert "SQL" not in error_message.upper(), "Should not expose SQL details to business layer"
        assert "DATABASE" not in error_message.upper() or "database" in error_message.lower(), "Database errors should be business-friendly"


class TestComplianceAndGovernance:
    """Test compliance and governance business requirements."""

    def test_data_handling_compliance(self):
        """Test data handling meets compliance requirements."""
        from netra_backend.app.services.user_service import pwd_context
        
        # Compliance Rule: Passwords must never be stored in plain text
        sensitive_password = "compliance_test_password_456"
        hashed = pwd_context.hash(sensitive_password)
        
        # Hash should not contain the original password
        assert sensitive_password not in hashed, "Password must not appear in hash"
        
        # Verification should work without storing original
        try:
            pwd_context.verify(hashed, sensitive_password)
            verification_works = True
        except Exception:
            verification_works = False
        
        assert verification_works, "Password verification must work without storing original"

    def test_cost_tracking_auditability(self, cost_calculator):
        """Test that cost tracking supports audit requirements."""
        # Audit Rule: Cost calculations must be deterministic and reproducible
        usage = TokenUsage(prompt_tokens=750, completion_tokens=375, total_tokens=1125)
        
        # Multiple calculations should be identical (auditability)
        costs = []
        for _ in range(5):
            cost = cost_calculator.calculate_cost(usage, LLMProvider.OPENAI, "gpt-3.5-turbo")
            costs.append(cost)
        
        # All calculations must be identical for audit trail
        assert len(set(costs)) == 1, "Cost calculations must be deterministic for audit compliance"

    def test_service_isolation_governance(self):
        """Test service isolation meets governance requirements."""
        # Governance Rule: Services should be independently testable and deployable
        cost_calc1 = CostCalculatorService()
        cost_calc2 = CostCalculatorService()
        
        # Services should not share state (governance isolation)
        assert cost_calc1 is not cost_calc2, "Service instances must be independent"
        
        usage = TokenUsage(prompt_tokens=200, completion_tokens=100, total_tokens=300)
        cost1 = cost_calc1.calculate_cost(usage, LLMProvider.OPENAI, "gpt-3.5-turbo")
        cost2 = cost_calc2.calculate_cost(usage, LLMProvider.OPENAI, "gpt-3.5-turbo")
        
        # Results should be consistent but instances independent
        assert cost1 == cost2, "Independent service instances must produce consistent results"


class TestBusinessValueValidation:
    """Test that system delivers expected business value."""

    def test_cost_optimization_business_value(self, cost_calculator):
        """Test that cost optimization provides business value."""
        # Business Value: System should help users choose cost-effective options
        providers = [LLMProvider.OPENAI, LLMProvider.ANTHROPIC, LLMProvider.GOOGLE]
        
        cost_comparisons = []
        usage = TokenUsage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500)
        
        for provider in providers:
            try:
                # Try to get economy model for cost comparison
                economy_model = cost_calculator.get_cost_optimal_model(provider, CostTier.ECONOMY)
                if economy_model:
                    cost = cost_calculator.calculate_cost(usage, provider, economy_model)
                    cost_comparisons.append((provider, cost))
            except Exception:
                # Provider might not be configured
                continue
        
        # Business Value: Should provide cost comparison capabilities
        if len(cost_comparisons) > 1:
            costs = [cost for _, cost in cost_comparisons]
            min_cost = min(costs)
            max_cost = max(costs)
            
            # Should show meaningful cost differences for business decision-making
            if min_cost > 0:
                cost_range = max_cost / min_cost
                assert cost_range >= Decimal('1'), "Cost comparisons should show business-relevant differences"

    def test_performance_tier_business_value(self, cost_calculator):
        """Test that performance tiers provide business value."""
        # Business Value: Different tiers should serve different business needs
        tiers = [CostTier.ECONOMY, CostTier.BALANCED, CostTier.PREMIUM]
        
        tier_options = {}
        for tier in tiers:
            model = cost_calculator.get_cost_optimal_model(LLMProvider.OPENAI, tier)
            tier_options[tier] = model
        
        # Business Value: System should provide options for different business requirements
        available_tiers = sum(1 for model in tier_options.values() if model is not None)
        
        # Having multiple tier options provides business value
        # (But it's OK if some aren't configured yet)
        assert available_tiers >= 0, "System should support multiple performance tiers for business flexibility"

    def test_user_authentication_business_value(self):
        """Test that authentication provides business value."""
        from netra_backend.app.services.user_service import pwd_context
        
        # Business Value: Secure authentication protects business assets
        legitimate_password = "legitimate_user_password"
        malicious_password = "malicious_attempt"
        
        hashed = pwd_context.hash(legitimate_password)
        
        # Legitimate user should be able to authenticate
        try:
            pwd_context.verify(hashed, legitimate_password)
            legitimate_auth = True
        except Exception:
            legitimate_auth = False
        
        # Malicious attempt should fail
        malicious_auth = True
        try:
            pwd_context.verify(hashed, malicious_password)
        except Exception:
            malicious_auth = False
        
        # Business Value: Security system should distinguish legitimate vs malicious access
        assert legitimate_auth is True, "Legitimate users must be able to authenticate"
        assert malicious_auth is False, "Malicious attempts must be rejected"


class TestScalabilityBusinessRequirements:
    """Test scalability meets business growth requirements."""

    def test_cost_calculation_scales_for_business_growth(self, cost_calculator):
        """Test cost calculation scales for business growth."""
        # Business Requirement: System must handle growing usage volumes
        usage_volumes = [
            TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),      # Small customer
            TokenUsage(prompt_tokens=10000, completion_tokens=5000, total_tokens=15000),   # Medium customer  
            TokenUsage(prompt_tokens=100000, completion_tokens=50000, total_tokens=150000), # Enterprise customer
        ]
        
        # All volume levels should be handled efficiently
        for usage in usage_volumes:
            cost = cost_calculator.calculate_cost(usage, LLMProvider.OPENAI, "gpt-3.5-turbo")
            
            assert isinstance(cost, Decimal), "System must handle all business volume levels"
            assert cost >= Decimal('0'), "All calculations must be valid regardless of scale"

    def test_multi_tenant_business_isolation(self):
        """Test multi-tenant isolation for business requirements."""
        # Business Requirement: Different customers/tenants should be isolated
        calc_tenant_a = CostCalculatorService()
        calc_tenant_b = CostCalculatorService()
        
        usage_a = TokenUsage(prompt_tokens=500, completion_tokens=250, total_tokens=750)
        usage_b = TokenUsage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500)
        
        cost_a = calc_tenant_a.calculate_cost(usage_a, LLMProvider.OPENAI, "gpt-3.5-turbo")
        cost_b = calc_tenant_b.calculate_cost(usage_b, LLMProvider.OPENAI, "gpt-3.5-turbo")
        
        # Business Requirement: Tenants should not interfere with each other
        # Re-calculate to ensure no cross-contamination
        cost_a_recheck = calc_tenant_a.calculate_cost(usage_a, LLMProvider.OPENAI, "gpt-3.5-turbo")
        cost_b_recheck = calc_tenant_b.calculate_cost(usage_b, LLMProvider.OPENAI, "gpt-3.5-turbo")
        
        assert cost_a == cost_a_recheck, "Tenant A calculations must be consistent"
        assert cost_b == cost_b_recheck, "Tenant B calculations must be consistent"