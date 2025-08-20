"""Fixtures Tests - Split from test_supply_research_optimization.py

        BVJ: Core value proposition - intelligent model selection saves customers 15-25%
        on AI costs. Higher savings = larger performance fees = direct revenue growth.
        Each optimized customer represents $5-15K additional annual revenue.
"""

import pytest
import pytest_asyncio
import asyncio
import uuid
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List, Tuple
from app.agents.supply_researcher.research_engine import SupplyResearchEngine
from app.agents.supply_researcher.data_extractor import SupplyDataExtractor
from app.agents.supply_researcher.parsers import SupplyRequestParser
from app.services.supply_research.schedule_manager import ScheduleManager
from app.agents.supply_researcher.models import ResearchType
from app.db.models_user import User, ToolUsageLog
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
import tempfile

    def supply_research_components(self):
        """Setup supply research and optimization components"""
        return self._init_supply_research_components()

    def cost_optimization_scenarios(self):
        """Setup various cost optimization test scenarios"""
        return self._create_cost_optimization_scenarios()
