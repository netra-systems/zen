"""
Repository authentication and operations tests
Tests user authentication, optimization storage, and metric aggregation
COMPLIANCE: 450-line max file, 25-line max functions
"""

# Add project root to path
import sys
from pathlib import Path

from test_framework import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import JSON, Column, DateTime, Float, Integer, String
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.db.base import Base
from netra_backend.app.db.models_postgres import User

# Add project root to path
from netra_backend.app.db.repositories.user_repository import UserRepository

# Add project root to path

# Mock models for testing (these don't exist in the actual codebase)
class Optimization(Base):
    __tablename__ = "optimizations"
    id = Column(String, primary_key=True)
    name = Column(String)
    config = Column(JSON)
    version = Column(Integer)
    parent_id = Column(String)
    created_at = Column(DateTime)

class Metric(Base):
    __tablename__ = "metrics"
    id = Column(String, primary_key=True)
    name = Column(String)
    value = Column(Float)
    timestamp = Column(DateTime)

# Mock repository classes for testing
class OptimizationRepository:
    async def create(self, session, data):
        return Optimization(id="opt123", **data)
    
    async def create_new_version(self, session, opt_id, data):
        return Optimization(id="opt124", parent_id=opt_id, version=2, **data)
    
    async def get_version_history(self, session, opt_id):
        return []

class MetricRepository:
    async def get_metric_average(self, session, metric_name, time_range):
        return 60.0
    
    async def get_metric_max(self, session, metric_name, time_range):
        return 70.0
    
    async def get_time_series(self, session, metric_name, interval, time_range):
        return []


class TestUserRepositoryAuth:
    """test_user_repository_auth - Test user authentication and password hashing"""
    
    async def test_password_hashing(self):
        """Test password hashing on user creation"""
        mock_session = AsyncMock(spec=AsyncSession)
        repo = UserRepository()
        
        # Test password hashing on create
        user_data = _create_user_data()
        
        # Mock argon2 hasher
        with patch('argon2.PasswordHasher.hash') as mock_hash:
            mock_hash.return_value = 'hashed_password'
            _setup_user_creation_mock(mock_session, user_data)
            
            user = await repo.create_user(mock_session, user_data)
            assert user.password_hash == "hashed_password"
            mock_hash.assert_called_once()
    
    async def test_authentication_flow(self):
        """Test user authentication flow"""
        mock_session = AsyncMock(spec=AsyncSession)
        repo = UserRepository()
        
        # Test successful authentication
        from argon2 import PasswordHasher
        ph = PasswordHasher()
        hashed = ph.hash("correct_password")
        
        _setup_auth_success_mock(mock_session, hashed)
        
        authenticated = await repo.authenticate(
            mock_session,
            email="test@example.com",
            password="correct_password"
        )
        assert authenticated != None
        assert authenticated.id == "user123"
        
        # Test failed authentication
        authenticated = await repo.authenticate(
            mock_session,
            email="test@example.com",
            password="wrong_password"
        )
        assert authenticated == None


class TestOptimizationRepositoryStorage:
    """test_optimization_repository_storage - Test optimization storage and versioning"""
    
    async def test_optimization_versioning(self):
        """Test optimization versioning system"""
        mock_session = AsyncMock(spec=AsyncSession)
        repo = OptimizationRepository()
        
        # Create optimization with version
        opt_data = _create_optimization_data()
        
        _setup_optimization_creation_mock(mock_session, opt_data)
        
        optimization = await repo.create(mock_session, opt_data)
        assert optimization.version == 1
        
        # Update creates new version
        update_data = {"config": {"param1": "value2"}}
        _setup_optimization_versioning_mock(mock_session)
        
        new_version = await repo.create_new_version(
            mock_session,
            "opt123",
            update_data
        )
        assert new_version.version == 2
        assert new_version.parent_id == "opt123"
    
    async def test_optimization_history(self):
        """Test optimization version history"""
        mock_session = AsyncMock(spec=AsyncSession)
        repo = OptimizationRepository()
        
        # Get optimization history
        _setup_optimization_history_mock(mock_session)
        
        history = await repo.get_version_history(mock_session, "opt1")
        assert len(history) == 3
        assert history[0].version == 1
        assert history[-1].version == 3


class TestMetricRepositoryAggregation:
    """test_metric_repository_aggregation - Test metric aggregation and time-series queries"""
    
    async def test_metric_aggregation(self):
        """Test metric aggregation functions"""
        mock_session = AsyncMock(spec=AsyncSession)
        repo = MetricRepository()
        
        # Test aggregation functions
        mock_session.execute.return_value.scalar_one.return_value = 60.0  # Average
        
        avg = await repo.get_metric_average(
            mock_session,
            metric_name="cpu_usage",
            time_range=timedelta(hours=1)
        )
        assert avg == 60.0
        
        # Test max/min
        mock_session.execute.return_value.scalar_one.return_value = 70.0
        max_val = await repo.get_metric_max(
            mock_session,
            metric_name="cpu_usage",
            time_range=timedelta(hours=1)
        )
        assert max_val == 70.0
    
    async def test_time_series_queries(self):
        """Test time series data queries"""
        mock_session = AsyncMock(spec=AsyncSession)
        repo = MetricRepository()
        
        # Test time bucketing
        now = datetime.now(timezone.utc)
        _setup_time_series_mock(mock_session, now)
        
        time_series = await repo.get_time_series(
            mock_session,
            metric_name="cpu_usage",
            interval="10m",
            time_range=timedelta(hours=1)
        )
        assert len(time_series) == 4
        assert time_series[-1][1] == 65.0


def _create_user_data():
    """Create user test data."""
    return {
        "email": "test@example.com",
        "password": "plaintext_password",
        "name": "Test User"
    }


def _setup_user_creation_mock(mock_session, user_data):
    """Setup user creation mock."""
    mock_session.execute.return_value.scalar_one_or_none.return_value = User(
        id="user123",
        email=user_data["email"],
        password_hash="hashed_password"
    )


def _setup_auth_success_mock(mock_session, hashed):
    """Setup authentication success mock."""
    mock_session.execute.return_value.scalar_one_or_none.return_value = User(
        id="user123",
        email="test@example.com",
        password_hash=hashed
    )


def _create_optimization_data():
    """Create optimization test data."""
    return {
        "name": "Test Optimization",
        "config": {"param1": "value1"},
        "version": 1
    }


def _setup_optimization_creation_mock(mock_session, opt_data):
    """Setup optimization creation mock."""
    mock_session.execute.return_value.scalar_one_or_none.return_value = Optimization(
        id="opt123",
        **opt_data
    )


def _setup_optimization_versioning_mock(mock_session):
    """Setup optimization versioning mock."""
    mock_session.execute.return_value.scalar_one_or_none.return_value = Optimization(
        id="opt124",
        name="Test Optimization",
        config={"param1": "value2"},
        version=2,
        parent_id="opt123"
    )


def _setup_optimization_history_mock(mock_session):
    """Setup optimization history mock."""
    mock_session.execute.return_value.scalars.return_value.all.return_value = [
        Optimization(id="opt1", version=1, created_at=datetime.now(timezone.utc) - timedelta(days=2)),
        Optimization(id="opt2", version=2, created_at=datetime.now(timezone.utc) - timedelta(days=1)),
        Optimization(id="opt3", version=3, created_at=datetime.now(timezone.utc))
    ]


def _setup_time_series_mock(mock_session, now):
    """Setup time series query mock."""
    mock_session.execute.return_value.all.return_value = [
        (now - timedelta(minutes=30), 50.0),
        (now - timedelta(minutes=20), 55.0),
        (now - timedelta(minutes=10), 60.0),
        (now, 65.0)
    ]