"""
Realistic Test Fixtures - Core
Core fixture generator with user and organization data.
Compliance: <300 lines, 25-line max functions, modular design.
"""

import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from netra_backend.app import schemas
from netra_backend.app.db import models_postgres as models
from netra_backend.app.services.realistic_test_data_service import (
    RealisticDataPatterns,
    RealisticTestDataService,
)

class CoreTestFixtures:
    """Generator for core realistic test fixtures"""
    
    def __init__(self):
        self.data_service = RealisticTestDataService()
        self.fixture_cache = {}
        
    def generate_production_seed_data(
        self,
        scale: str = "small"
    ) -> Dict[str, Any]:
        """
        Generate core production-like seed data
        
        Args:
            scale: Data scale - "small" (dev), "medium" (staging), "large" (prod-like)
            
        Returns:
            Core seed data package
        """
        scale_configs = self._get_scale_configs()
        config = scale_configs.get(scale, scale_configs["small"])
        
        return {
            "users": self._generate_users(config["users"], config["organizations"]),
            "organizations": self._generate_organizations(config["organizations"])
        }
    
    def _get_scale_configs(self) -> Dict[str, Dict[str, int]]:
        """Get configuration settings for different scales"""
        return {
            "small": {
                "users": 10,
                "organizations": 2,
                "workload_days": 7,
                "log_volume": 10000,
                "models": 3
            },
            "medium": {
                "users": 100,
                "organizations": 10,
                "workload_days": 30,
                "log_volume": 100000,
                "models": 5
            },
            "large": {
                "users": 1000,
                "organizations": 50,
                "workload_days": 90,
                "log_volume": 1000000,
                "models": 10
            }
        }
    
    def _generate_users(self, count: int, org_count: int) -> List[Dict[str, Any]]:
        """Generate realistic user data"""
        users = []
        roles = ["admin", "developer", "analyst", "viewer"]
        for i in range(count):
            user = self._create_user_data(i, org_count, roles)
            users.append(user)
        return users
    
    def _create_user_data(self, index: int, org_count: int, roles: List[str]) -> Dict[str, Any]:
        """Create complete user data structure"""
        base_info = self._build_user_base_info(index, org_count, roles)
        timestamps = self._build_user_timestamps(index)
        api_keys = self._build_user_api_keys(index)
        preferences = self._build_user_preferences(index)
        
        return {**base_info, **timestamps, "api_keys": api_keys, "preferences": preferences}
    
    def _build_user_base_info(self, index: int, org_count: int, roles: List[str]) -> Dict[str, Any]:
        """Build basic user information"""
        org_id = index % org_count
        return {
            "id": f"user_{index:04d}",
            "email": f"user{index}@example.com",
            "name": f"Test User {index}",
            "organization_id": f"org_{org_id:03d}",
            "role": roles[index % len(roles)]
        }
    
    def _build_user_timestamps(self, index: int) -> Dict[str, str]:
        """Build user timestamp data"""
        created_date = datetime.now(timezone.utc) - timedelta(days=index)
        last_login_date = datetime.now(timezone.utc) - timedelta(hours=index % 48)
        return {
            "created_at": created_date.isoformat(),
            "last_login": last_login_date.isoformat()
        }
    
    def _build_user_api_keys(self, user_index: int) -> List[Dict[str, Any]]:
        """Build user API keys"""
        keys = []
        for j in range(2):
            key_data = self._create_api_key(user_index, j)
            keys.append(key_data)
        return keys
    
    def _create_api_key(self, user_index: int, key_index: int) -> Dict[str, Any]:
        """Create individual API key data"""
        created_time = datetime.now(timezone.utc)
        last_used_time = created_time - timedelta(hours=key_index * 24)
        return {
            "key": f"sk-test-{user_index:04d}-{key_index:02d}",
            "name": f"Key {key_index}",
            "created_at": created_time.isoformat(),
            "last_used": last_used_time.isoformat()
        }
    
    def _build_user_preferences(self, index: int) -> Dict[str, Any]:
        """Build user preferences"""
        return {
            "theme": "dark" if index % 2 else "light",
            "notifications": True,
            "timezone": "UTC"
        }
    
    def _generate_organizations(self, count: int) -> List[Dict[str, Any]]:
        """Generate realistic organization data"""
        org_types = ["enterprise", "startup", "academic", "non-profit"]
        industries = ["tech", "finance", "healthcare", "retail", "education"]
        
        orgs = []
        for i in range(count):
            org = self._create_organization_data(i, org_types, industries)
            orgs.append(org)
        
        return orgs
    
    def _create_organization_data(self, index: int, org_types: List[str], industries: List[str]) -> Dict[str, Any]:
        """Create complete organization data structure"""
        base_info = self._build_org_base_info(index, org_types, industries)
        subscription = self._build_org_subscription(index)
        settings = self._build_org_settings(index)
        
        return {**base_info, "subscription": subscription, "settings": settings}
    
    def _build_org_base_info(self, index: int, org_types: List[str], industries: List[str]) -> Dict[str, Any]:
        """Build basic organization information"""
        created_date = datetime.now(timezone.utc) - timedelta(days=index * 30)
        return {
            "id": f"org_{index:03d}",
            "name": f"Organization {index}",
            "type": org_types[index % len(org_types)],
            "industry": industries[index % len(industries)],
            "created_at": created_date.isoformat()
        }
    
    def _build_org_subscription(self, index: int) -> Dict[str, Any]:
        """Build organization subscription data"""
        plans = ["basic", "pro", "enterprise"]
        return {
            "plan": plans[index % 3],
            "seats": 10 * (index + 1),
            "usage_limit": 100000 * (index + 1),
            "billing_cycle": "monthly" if index % 2 else "annual"
        }
    
    def _build_org_settings(self, index: int) -> Dict[str, Any]:
        """Build organization settings"""
        return {
            "data_retention_days": 90,
            "audit_logging": True,
            "sso_enabled": index % 3 == 0,
            "ip_whitelist": []
        }

# Pytest fixtures using the core generator
@pytest.fixture
def core_fixtures():
    """Provide core test fixtures"""
    return CoreTestFixtures()

@pytest.fixture
def small_core_data(core_fixtures):
    """Small-scale core data for development"""
    return core_fixtures.generate_production_seed_data("small")

@pytest.fixture
def medium_core_data(core_fixtures):
    """Medium-scale core data for staging"""
    return core_fixtures.generate_production_seed_data("medium")

@pytest.fixture
def large_core_data(core_fixtures):
    """Large-scale core data for production-like testing"""
    return core_fixtures.generate_production_seed_data("large")
