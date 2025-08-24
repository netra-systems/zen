"""
Tool Permission Service - Business Requirements Tests
Functions refactored to ≤8 lines each using helper functions
"""

import sys
from pathlib import Path

import pytest

from netra_backend.app.schemas.UserPlan import (
    PLAN_DEFINITIONS,
    PlanFeatures,
    PlanTier,
    UserPlan,
)

from netra_backend.app.services.tool_permission_service import ToolPermissionService
from netra_backend.tests.helpers.tool_permission_helpers import (
    assert_business_requirements_result,
    create_business_requirements,
    create_developer_context,
    create_sample_context,
    create_user_plan,
)

@pytest.fixture
def service():
    """Create ToolPermissionService without Redis"""
    return ToolPermissionService()

@pytest.fixture
def sample_context():
    """Create sample tool execution context"""
    return create_sample_context()

@pytest.fixture
def developer_context():
    """Create developer execution context"""
    return create_developer_context()

class TestBusinessRequirements:
    """Test business requirements checking"""
    
    def test_check_business_requirements_plan_tier_pass(self, service, sample_context):
        """Test business requirements check with valid plan tier"""
        requirements = create_business_requirements(plan_tiers=["pro", "enterprise"])
        user_plan = create_user_plan(PlanTier.PRO)
        sample_context.user_plan = "pro"
        result = service._check_business_requirements(requirements, sample_context, user_plan)
        assert_business_requirements_result(result, True)
    
    def test_check_business_requirements_plan_tier_fail(self, service, sample_context):
        """Test business requirements check with invalid plan tier"""
        requirements = create_business_requirements(plan_tiers=["pro", "enterprise"])
        user_plan = create_user_plan(PlanTier.FREE)
        sample_context.user_plan = "free"
        result = service._check_business_requirements(requirements, sample_context, user_plan)
        assert_business_requirements_result(result, False)
    
    def test_check_business_requirements_feature_flags_pass(self, service, sample_context):
        """Test business requirements check with valid feature flags"""
        requirements = create_business_requirements(feature_flags=["data_operations"])
        user_plan = UserPlan(
            user_id="test_user",
            tier=PlanTier.PRO,
            features=PlanFeatures(permissions=[], tool_allowances=[], feature_flags=["data_operations"])
        )
        result = service._check_business_requirements(requirements, sample_context, user_plan)
        assert_business_requirements_result(result, True)
    
    def test_check_business_requirements_feature_flags_fail(self, service, sample_context):
        """Test business requirements check with missing feature flags"""
        requirements = create_business_requirements(feature_flags=["advanced_optimization"])
        user_plan = UserPlan(
            user_id="test_user",
            tier=PlanTier.PRO,
            features=PlanFeatures(permissions=[], tool_allowances=[], feature_flags=["data_operations"])
        )
        result = service._check_business_requirements(requirements, sample_context, user_plan)
        assert_business_requirements_result(result, False)
    
    def test_check_business_requirements_role_pass(self, service, sample_context):
        """Test business requirements check with valid role"""
        requirements = create_business_requirements(role_requirements=["admin"])
        sample_context.user_roles = ["admin", "user"]
        user_plan = create_user_plan(PlanTier.ENTERPRISE)
        result = service._check_business_requirements(requirements, sample_context, user_plan)
        assert_business_requirements_result(result, True)
    
    def test_check_business_requirements_role_fail(self, service, sample_context):
        """Test business requirements check with missing role"""
        requirements = create_business_requirements(role_requirements=["admin"])
        sample_context.user_roles = ["user"]
        user_plan = create_user_plan(PlanTier.ENTERPRISE)
        result = service._check_business_requirements(requirements, sample_context, user_plan)
        assert_business_requirements_result(result, False)
    
    def test_check_business_requirements_developer_status_pass(self, service, developer_context):
        """Test business requirements check with valid developer status"""
        requirements = create_business_requirements(developer_status=True)
        user_plan = create_user_plan(PlanTier.ENTERPRISE, "dev_user")
        result = service._check_business_requirements(requirements, developer_context, user_plan)
        assert_business_requirements_result(result, True)
    
    def test_check_business_requirements_developer_status_fail(self, service, sample_context):
        """Test business requirements check with invalid developer status"""
        requirements = create_business_requirements(developer_status=True)
        sample_context.is_developer = False
        user_plan = create_user_plan(PlanTier.ENTERPRISE)
        result = service._check_business_requirements(requirements, sample_context, user_plan)
        assert_business_requirements_result(result, False)
    
    def test_check_business_requirements_environment_pass(self, service, developer_context):
        """Test business requirements check with valid environment"""
        requirements = create_business_requirements(environment=["development", "staging"])
        user_plan = create_user_plan(PlanTier.ENTERPRISE, "dev_user")
        result = service._check_business_requirements(requirements, developer_context, user_plan)
        assert_business_requirements_result(result, True)
    
    def test_check_business_requirements_environment_fail(self, service, sample_context):
        """Test business requirements check with invalid environment"""
        requirements = create_business_requirements(environment=["development", "staging"])
        sample_context.environment = "production"
        user_plan = create_user_plan(PlanTier.ENTERPRISE)
        result = service._check_business_requirements(requirements, sample_context, user_plan)
        assert_business_requirements_result(result, False)
    
    def test_check_business_requirements_all_conditions(self, service, developer_context):
        """Test business requirements check with all conditions"""
        requirements = create_business_requirements(
            plan_tiers=["enterprise"],
            feature_flags=["advanced_features"],
            role_requirements=["developer"],
            developer_status=True,
            environment=["development"]
        )
        user_plan = UserPlan(
            user_id="dev_user",
            tier=PlanTier.ENTERPRISE,
            features=PlanFeatures(permissions=[], tool_allowances=[], feature_flags=["advanced_features"])
        )
        developer_context.user_plan = "enterprise"
        result = service._check_business_requirements(requirements, developer_context, user_plan)
        assert_business_requirements_result(result, True)

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])