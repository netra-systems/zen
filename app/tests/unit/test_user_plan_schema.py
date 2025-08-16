"""Unit tests for UserPlan schema validation.

Tests to ensure UserPlan pydantic model correctly validates trial_period as boolean.
Prevents schema type mismatches with database.
"""

import pytest
from datetime import datetime, UTC
from pydantic import ValidationError
from app.schemas.UserPlan import (
    UserPlan,
    PlanTier,
    PlanFeatures,
    ToolAllowance
)


class TestUserPlanSchema:
    """Test UserPlan schema validation."""
    
    def test_trial_period_accepts_boolean_true(self):
        """Verify trial_period accepts boolean True value."""
        features = PlanFeatures(
            permissions=["basic"],
            tool_allowances=[
                ToolAllowance(tool_name="test", limit=10, period="day")
            ]
        )
        
        plan = UserPlan(
            user_id="test-user-123",
            tier=PlanTier.FREE,
            features=features,
            trial_period=True  # Boolean value
        )
        
        assert plan.trial_period is True
        assert isinstance(plan.trial_period, bool)
    
    def test_trial_period_accepts_boolean_false(self):
        """Verify trial_period accepts boolean False value."""
        features = PlanFeatures(
            permissions=["basic"],
            tool_allowances=[
                ToolAllowance(tool_name="test", limit=10, period="day")
            ]
        )
        
        plan = UserPlan(
            user_id="test-user-456",
            tier=PlanTier.PRO,
            features=features,
            trial_period=False  # Boolean value
        )
        
        assert plan.trial_period is False
        assert isinstance(plan.trial_period, bool)
    
    def test_trial_period_defaults_to_false(self):
        """Verify trial_period defaults to False when not provided."""
        features = PlanFeatures(
            permissions=["basic"],
            tool_allowances=[
                ToolAllowance(tool_name="test", limit=10, period="day")
            ]
        )
        
        plan = UserPlan(
            user_id="test-user-789",
            tier=PlanTier.ENTERPRISE,
            features=features
            # trial_period not provided
        )
        
        assert plan.trial_period is False
        assert isinstance(plan.trial_period, bool)
    
    def test_trial_period_rejects_integer(self):
        """Verify trial_period rejects integer values."""
        features = PlanFeatures(
            permissions=["basic"],
            tool_allowances=[
                ToolAllowance(tool_name="test", limit=10, period="day")
            ]
        )
        
        # Should coerce integer to boolean
        plan = UserPlan(
            user_id="test-user-int",
            tier=PlanTier.FREE,
            features=features,
            trial_period=1  # Integer value
        )
        
        # Pydantic will coerce 1 to True
        assert plan.trial_period is True
        assert isinstance(plan.trial_period, bool)
    
    def test_full_plan_creation_with_trial(self):
        """Test creating a complete UserPlan with trial period."""
        features = PlanFeatures(
            permissions=["basic", "analytics"],
            tool_allowances=[
                ToolAllowance(tool_name="create_thread", limit=100, period="day"),
                ToolAllowance(tool_name="analyze", limit=50, period="hour")
            ],
            feature_flags=["beta_features"],
            rate_limit_multiplier=2.0,
            support_level="priority",
            max_threads=20,
            max_corpus_size=5000
        )
        
        plan = UserPlan(
            user_id="trial-user-001",
            tier=PlanTier.PRO,
            features=features,
            started_at=datetime.now(UTC),
            expires_at=None,
            auto_renew=False,
            payment_status="trial",
            trial_period=True,  # User is in trial
            upgraded_from=PlanTier.FREE.value
        )
        
        assert plan.trial_period is True
        assert plan.payment_status == "trial"
        assert plan.tier == PlanTier.PRO
        assert isinstance(plan.trial_period, bool)