"""Utilities Tests - Split from test_supply_research_optimization.py

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

    def _init_supply_research_components(self):
        """Initialize supply research and optimization components"""
        # Research engine with mock data sources
        research_engine = Mock(spec=SupplyResearchEngine)
        research_engine.research_model_pricing = AsyncMock(side_effect=self._mock_pricing_research)
        research_engine.research_model_capabilities = AsyncMock(side_effect=self._mock_capability_research)
        
        # Data extractor for processing research results
        data_extractor = Mock(spec=SupplyDataExtractor)
        data_extractor.extract_pricing_data = Mock(side_effect=self._mock_extract_pricing)
        data_extractor.extract_performance_metrics = Mock(side_effect=self._mock_extract_performance)
        
        # Cost impact simulator (mocked without spec)
        cost_simulator = Mock()
        cost_simulator.simulate_cost_impact = AsyncMock(side_effect=self._mock_cost_simulation)
        
        # Schedule manager for research automation
        schedule_manager = ScheduleManager()
        
        return {
            "research_engine": research_engine,
            "data_extractor": data_extractor,
            "cost_simulator": cost_simulator,
            "schedule_manager": schedule_manager
        }

    def _mock_extract_pricing(self, research_data):
        """Mock pricing data extraction"""
        return {
            "input_cost_per_1k": research_data.get("input_cost", 0),
            "output_cost_per_1k": research_data.get("output_cost", 0),
            "currency": research_data.get("currency", "USD"),
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

    def _mock_extract_performance(self, capability_data):
        """Mock performance metrics extraction"""
        return {
            "overall_score": sum(capability_data.values()) / len(capability_data),
            "strengths": [k for k, v in capability_data.items() if v >= 85],
            "weaknesses": [k for k, v in capability_data.items() if v < 75],
            "speed_rating": capability_data.get("speed", 0)
        }

    def _create_cost_optimization_scenarios(self):
        """Create various cost optimization test scenarios"""
        return {
            "high_volume_analysis": {
                "current_model": "gpt-4",
                "usage_pattern": "analysis_heavy",
                "monthly_tokens": 2000000,
                "cost_sensitivity": "high",
                "performance_requirements": "medium"
            },
            "real_time_optimization": {
                "current_model": "claude-3-5-sonnet", 
                "usage_pattern": "real_time_queries",
                "monthly_tokens": 500000,
                "cost_sensitivity": "medium",
                "performance_requirements": "high"
            },
            "batch_processing": {
                "current_model": "gemini-pro",
                "usage_pattern": "batch_processing",
                "monthly_tokens": 5000000,
                "cost_sensitivity": "very_high",
                "performance_requirements": "low"
            }
        }

    def _calculate_daily_cost(self, model, tokens):
        """Calculate daily cost based on model and token usage"""
        # Simplified cost calculation for testing
        cost_per_1k = {
            "gpt-4": 45,  # $0.045 per 1k tokens average
            "claude-3-5-sonnet": 30,  # $0.030 per 1k tokens average
            "gemini-pro": 10,  # $0.010 per 1k tokens average
            "gemini-2.5-flash": 2   # $0.002 per 1k tokens average
        }
        
        return int((tokens / 1000) * cost_per_1k.get(model, 20))

    def _meets_performance_requirements(self, performance, requirements):
        """Check if model performance meets customer requirements"""
        overall_score = performance["overall_score"]
        
        thresholds = {
            "low": 70,
            "medium": 80,
            "high": 85
        }
        
        return overall_score >= thresholds.get(requirements, 80)

    def _calculate_cost_comparison(self, pricing, usage_analysis):
        """Calculate cost comparison between models"""
        current_monthly_cost = usage_analysis["total_cost"]
        
        # Simplified cost calculation based on input/output costs
        new_cost_per_1k = (pricing["input_cost_per_1k"] + pricing["output_cost_per_1k"]) / 2
        current_cost_per_1k = 0.045  # Average current cost
        
        cost_multiplier = new_cost_per_1k / current_cost_per_1k
        projected_cost = current_monthly_cost * cost_multiplier
        savings = current_monthly_cost - projected_cost
        
        return {
            "current_cost": current_monthly_cost,
            "projected_cost": projected_cost,
            "cost_savings": savings,
            "savings_percentage": (savings / current_monthly_cost) * 100
        }

    def _calculate_emergency_savings(self, trigger):
        """Calculate potential emergency savings"""
        excess_cost = max(0, trigger["current_cost"] - trigger["threshold"])
        potential_savings = excess_cost * 0.6  # 60% potential savings
        
        return {
            "immediate_savings": potential_savings,
            "monthly_impact": potential_savings * 1.5,
            "confidence": 0.8
        }
