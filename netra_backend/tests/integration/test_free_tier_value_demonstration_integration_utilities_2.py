"""Utilities_2 Tests - Split from test_free_tier_value_demonstration_integration.py"""

import sys
from pathlib import Path
from test_framework.database.test_database_manager import DatabaseTestManager
from auth_service.core.auth_manager import AuthManager
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import asyncio
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from netra_backend.app.db.base import Base

from netra_backend.app.db.models_user import ToolUsageLog, User
from netra_backend.app.schemas.llm_base_types import LLMProvider, TokenUsage
from netra_backend.app.services.cost_calculator import CostCalculatorService, CostTier

class TestSyntaxFix:
    """Test class for orphaned methods"""

    def _calculate_roi_timeline(self, current_cost, optimized_cost):
        """Calculate ROI timeline in days"""
        monthly_savings = max(0, current_cost - optimized_cost)
        if monthly_savings <= 0:
            return 365  # No savings
        
        # Break-even calculation
        pro_plan_cost = 29.00
        return int((pro_plan_cost / monthly_savings) * 30)

    def _assess_usage_predictability(self, usage_data):
        """Assess how predictable the user's usage pattern is"""
        if usage_data["total_requests"] < 50:
            return "low"
        elif usage_data["avg_daily_requests"] > 0.5 and usage_data["total_requests"] > 200:
            return "high"
        else:
            return "medium"

    def _calculate_confidence_score(self, usage_data):
        """Calculate confidence score for savings projection"""
        base_score = 0.6
        
        # More data = higher confidence
        if usage_data["total_requests"] > 100:
            base_score += 0.2
        
        # Consistent usage = higher confidence
        if usage_data["avg_daily_requests"] > 1:
            base_score += 0.15
        
        # Multiple models = better optimization potential
        if len(usage_data["models_used"]) > 1:
            base_score += 0.1
        
        return min(1.0, base_score)

    def _calculate_value_score(self, usage_data, current_cost):
        """Calculate value score for free users (features vs cost)"""
        # For free users, emphasize feature value over cost savings
        base_score = 5.0
        
        # High usage = more value from premium features
        if usage_data["total_requests"] > 200:
            base_score += 2.0
        elif usage_data["total_requests"] > 100:
            base_score += 1.5
        
        # Multiple models = more optimization benefit
        if len(usage_data["models_used"]) > 1:
            base_score += 1.0
        
        # Active users get more value
        if usage_data["avg_daily_requests"] > 5:
            base_score += 1.5
        
        return min(10.0, base_score)
