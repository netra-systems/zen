"""
Unit Test for User Database Models

Business Value Justification (BVJ):
- Segment: Enterprise/Mid
- Business Goal: User Management and Golden Path Authentication
- Value Impact: Ensures user data integrity for Golden Path authentication and authorization
- Strategic Impact: Protects $500K+ ARR user accounts and subscription data integrity

CRITICAL: NO MOCKS except for external dependencies. Tests use real business logic.
Tests user models that are essential for Golden Path user authentication and management.
"""

import pytest
import uuid
from datetime import datetime, timezone
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.db.models_user import User, Secret, ToolUsageLog


class UserModelTests(SSotBaseTestCase):
    """Test suite for User model following SSOT patterns."""
    
    def setup_method(self, method):
        """Setup using SSOT test infrastructure."""
        super().setup_method(method)
        self.record_metric("test_category", "user_model_validation")
    
    def test_user_model_initialization(self):
        """
        Test User model initializes with proper defaults.
        
        BVJ: Ensures new Golden Path users get proper default settings
        """
        user = User(
            email="test@example.com",
            full_name="Test User"
        )
        
        # Check default values
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.is_active is True
        assert user.is_superuser is False
        assert user.is_developer is False
        assert user.role == "standard_user"
        assert user.plan_tier == "free"
        assert user.auto_renew is False
        assert user.payment_status == "active"
        assert user.trial_period == 0
        
        self.record_metric("user_model_defaults", "passed")
    
    def test_user_id_generation(self):
        """
        Test User ID is properly generated as UUID.
        
        BVJ: Ensures unique user identification for Golden Path operations
        """
        user1 = User(email="test1@example.com")
        user2 = User(email="test2@example.com")
        
        # IDs should be generated
        assert user1.id is not None
        assert user2.id is not None
        
        # IDs should be different
        assert user1.id != user2.id
        
        # IDs should be valid UUIDs
        uuid.UUID(user1.id)  # Should not raise exception
        uuid.UUID(user2.id)  # Should not raise exception
        
        self.record_metric("user_id_generation", "passed")
    
    def test_user_json_fields_initialization(self):
        """
        Test User JSON fields initialize as empty dictionaries.
        
        BVJ: Ensures proper initialization of permissions and feature flags for Golden Path
        """
        user = User(email="test@example.com")
        
        assert user.permissions == {}
        assert user.feature_flags == {}
        assert user.tool_permissions == {}
        
        # Should be able to set JSON values
        user.permissions = {"read": True, "write": False}
        user.feature_flags = {"beta_features": True}
        user.tool_permissions = {"advanced_tools": True}
        
        assert user.permissions["read"] is True
        assert user.feature_flags["beta_features"] is True
        assert user.tool_permissions["advanced_tools"] is True
        
        self.record_metric("user_json_fields", "passed")
    
    def test_user_plan_tier_validation(self):
        """
        Test User plan tier accepts valid values.
        
        BVJ: Ensures proper plan tier management for Golden Path billing
        """
        valid_plans = ["free", "pro", "enterprise", "developer"]
        
        for plan in valid_plans:
            user = User(email=f"test_{plan}@example.com", plan_tier=plan)
            assert user.plan_tier == plan
        
        self.record_metric("user_plan_validation", "passed")
    
    def test_user_role_validation(self):
        """
        Test User role accepts valid values.
        
        BVJ: Ensures proper role-based access control for Golden Path features
        """
        valid_roles = ["standard_user", "power_user", "developer", "admin", "super_admin"]
        
        for role in valid_roles:
            user = User(email=f"test_{role}@example.com", role=role)
            assert user.role == role
        
        self.record_metric("user_role_validation", "passed")


class SecretModelTests(SSotBaseTestCase):
    """Test suite for Secret model following SSOT patterns."""
    
    def setup_method(self, method):
        """Setup using SSOT test infrastructure."""
        super().setup_method(method)
        self.record_metric("test_category", "secret_model_validation")
    
    def test_secret_model_initialization(self):
        """
        Test Secret model initializes properly.
        
        BVJ: Ensures secure API key storage for Golden Path tool integrations
        """
        user_id = str(uuid.uuid4())
        secret = Secret(
            user_id=user_id,
            key="openai_api_key",
            encrypted_value="encrypted_value_here"
        )
        
        assert secret.user_id == user_id
        assert secret.key == "openai_api_key"
        assert secret.encrypted_value == "encrypted_value_here"
        assert secret.id is not None
        
        self.record_metric("secret_model_init", "passed")


class ToolUsageLogModelTests(SSotBaseTestCase):
    """Test suite for ToolUsageLog model following SSOT patterns."""
    
    def setup_method(self, method):
        """Setup using SSOT test infrastructure."""
        super().setup_method(method)
        self.record_metric("test_category", "tool_usage_log_validation")
    
    def test_tool_usage_log_initialization(self):
        """
        Test ToolUsageLog model initializes properly.
        
        BVJ: Ensures proper tracking of Golden Path tool usage for billing and analytics
        """
        user_id = str(uuid.uuid4())
        log = ToolUsageLog(
            user_id=user_id,
            tool_name="data_analysis",
            category="analytics",
            execution_time_ms=1500,
            tokens_used=100,
            cost_cents=5,
            status="success",
            plan_tier="pro"
        )
        
        assert log.user_id == user_id
        assert log.tool_name == "data_analysis"
        assert log.category == "analytics"
        assert log.execution_time_ms == 1500
        assert log.tokens_used == 100
        assert log.cost_cents == 5
        assert log.status == "success"
        assert log.plan_tier == "pro"
        assert log.id is not None
        
        self.record_metric("tool_usage_log_init", "passed")
    
    def test_tool_usage_log_status_values(self):
        """
        Test ToolUsageLog accepts valid status values.
        
        BVJ: Ensures accurate tool execution tracking for Golden Path analytics
        """
        user_id = str(uuid.uuid4())
        valid_statuses = ["success", "error", "permission_denied", "rate_limited"]
        
        for status in valid_statuses:
            log = ToolUsageLog(
                user_id=user_id,
                tool_name="test_tool",
                status=status,
                plan_tier="free"
            )
            assert log.status == status
        
        self.record_metric("tool_usage_status_validation", "passed")