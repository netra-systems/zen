"""Fixtures Tests - Split from test_free_tier_value_demonstration_integration.py"""

import pytest
import pytest_asyncio
import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List
from decimal import Decimal
from app.db.models_user import User, ToolUsageLog
from app.services.cost_calculator import CostCalculatorService, CostTier
from app.schemas.llm_base_types import LLMProvider, TokenUsage
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
import tempfile
from sqlalchemy import select

    def cost_calculator(self):
        """Setup cost calculator service"""
        return CostCalculatorService()

    def savings_tracker(self):
        """Setup savings tracking analytics"""
        tracker = Mock()
        tracker.track_preview_shown = AsyncMock()
        tracker.track_conversion_from_preview = AsyncMock()
        tracker.calculate_conversion_lift = AsyncMock()
        return tracker
