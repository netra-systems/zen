"""Test database schema consistency.

Tests to ensure SQLAlchemy models match database migrations.
Prevents type mismatches and schema drift.
"""""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import pytest
from sqlalchemy import JSON, Boolean, DateTime, Integer, String, inspect

from netra_backend.app.db.base import Base

from netra_backend.app.db.models_user import ToolUsageLog, User

class TestSchemaConsistency:
    """Test database schema consistency."""

    def test_user_trial_period_is_integer(self):
        """Verify trial_period is Integer in User model."""
        mapper = inspect(User)
        trial_period_col = mapper.columns['trial_period']

        # Check column type is Integer
        assert isinstance(trial_period_col.type, Integer)
        assert trial_period_col.nullable is False  # Not nullable since Mapped[int] without Optional
        assert trial_period_col.default.arg == 0

        def test_user_model_types_match_expectations(self):
            """Verify all User model column types match expected types."""
            mapper = inspect(User)

            expected_types = {
            'id': String,
            'email': String,
            'full_name': String,
            'is_active': Boolean,
            'is_superuser': Boolean,
            'is_developer': Boolean,
            'plan_tier': String,
            'plan_expires_at': DateTime,
            'feature_flags': JSON,
            'tool_permissions': JSON,
            'plan_started_at': DateTime,
            'auto_renew': Boolean,
            'payment_status': String,
            'trial_period': Integer,  # Critical: must be Integer (days)
            }

            for col_name, expected_type in expected_types.items():
                col = mapper.columns.get(col_name)
                assert col is not None, f"Column {col_name} not found"
                assert isinstance(col.type, expected_type), (
                f"Column {col_name} type mismatch: "
                f"expected {expected_type}, got {type(col.type)}"
                )

                def test_tool_usage_log_types(self):
                    """Verify ToolUsageLog model column types."""
                    mapper = inspect(ToolUsageLog)

                    expected_types = {
                    'id': String,
                    'user_id': String,
                    'tool_name': String,
                    'category': String,
                    'execution_time_ms': Integer,
                    'tokens_used': Integer,
                    'cost_cents': Integer,
                    'status': String,
                    'plan_tier': String,
                    'permission_check_result': JSON,
                    'arguments': JSON,
                    'created_at': DateTime,
                    }

                    for col_name, expected_type in expected_types.items():
                        col = mapper.columns.get(col_name)
                        assert col is not None, f"Column {col_name} not found"
                        assert isinstance(col.type, expected_type), (
                        f"Column {col_name} type mismatch: "
                        f"expected {expected_type}, got {type(col.type)}"
                        )