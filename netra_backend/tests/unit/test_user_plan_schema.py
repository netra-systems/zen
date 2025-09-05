"""Unit tests for UserPlan schema validation.

Tests to ensure UserPlan pydantic model correctly validates trial_period as integer.
Prevents schema type mismatches with database.
"""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from netra_backend.app.schemas.user_plan import (
    PlanFeatures,
    PlanTier,
    ToolAllowance,
    UserPlan,
)

class TestUserPlanSchema:
    """Test UserPlan schema validation."""
    
    def test_trial_period_accepts_integer_days(self):
        """Verify trial_period accepts integer value for trial days."""
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
            trial_period=14  # 14 days trial
        )
        
        assert plan.trial_period == 14
        assert isinstance(plan.trial_period, int)
    
    def test_trial_period_accepts_zero(self):
        """Verify trial_period accepts 0 to indicate no trial."""
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
            trial_period=0  # No trial
        )
        
        assert plan.trial_period == 0
        assert isinstance(plan.trial_period, int)
    
    def test_trial_period_defaults_to_zero(self):
        """Verify trial_period defaults to 0 when not provided."""
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
        
        assert plan.trial_period == 0
        assert isinstance(plan.trial_period, int)
    
    def test_trial_period_accepts_integer(self):
        """Verify trial_period accepts integer values for trial days."""
        features = PlanFeatures(
            permissions=["basic"],
            tool_allowances=[
                ToolAllowance(tool_name="test", limit=10, period="day")
            ]
        )
        
        # Should accept integer for trial days
        plan = UserPlan(
            user_id="test-user-int",
            tier=PlanTier.FREE,
            features=features,
            trial_period=7  # 7 days trial
        )
        
        # Should store as integer
        assert plan.trial_period == 7
        assert isinstance(plan.trial_period, int)
    
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
            trial_period=30,  # 30 days trial
            upgraded_from=PlanTier.FREE.value
        )
        
        assert plan.trial_period == 30
        assert plan.payment_status == "trial"
        assert plan.tier == PlanTier.PRO
        assert isinstance(plan.trial_period, int)