"""Agent Version Compatibility L2 Integration Tests

Business Value Justification (BVJ):
- Segment: Enterprise (AI operations continuity)
- Business Goal: Seamless version upgrades and backwards compatibility
- Value Impact: Protects $8K MRR from version upgrade disruptions
- Strategic Impact: Enables rolling deployments and gradual migrations

Critical Path: Version detection -> Compatibility check -> Migration -> Validation
Coverage: Real agent versioning, compatibility matrix, gradual rollout strategies
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from netra_backend.app.agents.base import BaseSubAgent
from netra_backend.app.agents.supervisor.agent_manager import AgentManager
from netra_backend.app.core.circuit_breaker import CircuitBreaker
from netra_backend.app.core.config import get_settings
from netra_backend.app.core.database_connection_manager import DatabaseConnectionManager

# Add project root to path
# Real components for L2 testing
from netra_backend.app.services.redis_service import RedisService

logger = logging.getLogger(__name__)


class VersionCompatibility(Enum):
    """Version compatibility levels."""
    FULLY_COMPATIBLE = "fully_compatible"
    BACKWARDS_COMPATIBLE = "backwards_compatible"
    BREAKING_CHANGE = "breaking_change"
    INCOMPATIBLE = "incompatible"


@dataclass
class AgentVersion:
    """Represents an agent version."""
    major: int
    minor: int
    patch: int
    
    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"
    
    @classmethod
    def from_string(cls, version_str: str) -> "AgentVersion":
        """Parse version from string."""
        parts = version_str.split(".")
        return cls(int(parts[0]), int(parts[1]), int(parts[2]))
    
    def is_compatible_with(self, other: "AgentVersion") -> VersionCompatibility:
        """Check compatibility with another version."""
        if self.major != other.major:
            return VersionCompatibility.INCOMPATIBLE
        
        if self.minor > other.minor:
            return VersionCompatibility.BACKWARDS_COMPATIBLE
        elif self.minor < other.minor:
            return VersionCompatibility.BREAKING_CHANGE
        else:
            return VersionCompatibility.FULLY_COMPATIBLE


@dataclass
class AgentVersionInfo:
    """Complete agent version information."""
    agent_type: str
    version: AgentVersion
    api_version: str
    features: List[str]
    deprecated_features: List[str]
    required_dependencies: Dict[str, str]
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_type": self.agent_type,
            "version": str(self.version),
            "api_version": self.api_version,
            "features": self.features,
            "deprecated_features": self.deprecated_features,
            "required_dependencies": self.required_dependencies,
            "created_at": self.created_at.isoformat()
        }


class VersionRegistry:
    """Manages agent version registry."""
    
    def __init__(self, redis_service: RedisService):
        self.redis_service = redis_service
        self.registry_key = "agent_version_registry"
        
    async def register_version(self, version_info: AgentVersionInfo) -> bool:
        """Register a new agent version."""
        try:
            key = f"{self.registry_key}:{version_info.agent_type}:{version_info.version}"
            data = json.dumps(version_info.to_dict())
            
            await self.redis_service.client.setex(key, 86400, data)  # 24h TTL
            
            # Add to type index
            type_key = f"{self.registry_key}:types:{version_info.agent_type}"
            await self.redis_service.client.sadd(type_key, str(version_info.version))
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to register version {version_info.version}: {e}")
            return False
    
    async def get_version_info(self, agent_type: str, version: str) -> Optional[AgentVersionInfo]:
        """Get version information."""
        try:
            key = f"{self.registry_key}:{agent_type}:{version}"
            data = await self.redis_service.client.get(key)
            
            if data:
                info_dict = json.loads(data)
                info_dict["version"] = AgentVersion.from_string(info_dict["version"])
                info_dict["created_at"] = datetime.fromisoformat(info_dict["created_at"])
                return AgentVersionInfo(**info_dict)
                
            return None
            
        except Exception as e:
            logger.error(f"Failed to get version info: {e}")
            return None
    
    async def get_available_versions(self, agent_type: str) -> List[str]:
        """Get all available versions for an agent type."""
        try:
            type_key = f"{self.registry_key}:types:{agent_type}"
            versions = await self.redis_service.client.smembers(type_key)
            return sorted([v.decode() if isinstance(v, bytes) else v for v in versions])
            
        except Exception as e:
            logger.error(f"Failed to get available versions: {e}")
            return []


class CompatibilityChecker:
    """Checks version compatibility between agents."""
    
    def __init__(self, version_registry: VersionRegistry):
        self.version_registry = version_registry
        
    async def check_compatibility(self, agent_type: str, 
                                current_version: str, 
                                target_version: str) -> Tuple[VersionCompatibility, List[str]]:
        """Check compatibility between versions."""
        issues = []
        
        current_info = await self.version_registry.get_version_info(agent_type, current_version)
        target_info = await self.version_registry.get_version_info(agent_type, target_version)
        
        if not current_info or not target_info:
            return VersionCompatibility.INCOMPATIBLE, ["Version information not found"]
        
        # Check version compatibility
        compatibility = current_info.version.is_compatible_with(target_info.version)
        
        # Check API compatibility
        if current_info.api_version != target_info.api_version:
            issues.append(f"API version mismatch: {current_info.api_version} vs {target_info.api_version}")
            if compatibility == VersionCompatibility.FULLY_COMPATIBLE:
                compatibility = VersionCompatibility.BACKWARDS_COMPATIBLE
        
        # Check deprecated features
        for feature in current_info.features:
            if feature in target_info.deprecated_features:
                issues.append(f"Feature '{feature}' is deprecated in target version")
        
        # Check dependency compatibility
        for dep, version in current_info.required_dependencies.items():
            if dep in target_info.required_dependencies:
                if version != target_info.required_dependencies[dep]:
                    issues.append(f"Dependency '{dep}' version mismatch")
        
        return compatibility, issues
    
    async def find_upgrade_path(self, agent_type: str, 
                              current_version: str, 
                              target_version: str) -> List[str]:
        """Find safe upgrade path between versions."""
        available_versions = await self.version_registry.get_available_versions(agent_type)
        
        current_ver = AgentVersion.from_string(current_version)
        target_ver = AgentVersion.from_string(target_version)
        
        # Simple linear upgrade path
        upgrade_path = [current_version]
        
        for version_str in sorted(available_versions):
            version = AgentVersion.from_string(version_str)
            
            if (version.major == current_ver.major and 
                version.minor > current_ver.minor and 
                version.minor <= target_ver.minor):
                
                upgrade_path.append(version_str)
        
        if target_version not in upgrade_path:
            upgrade_path.append(target_version)
        
        return upgrade_path


class MigrationManager:
    """Manages agent version migrations."""
    
    def __init__(self, compatibility_checker: CompatibilityChecker):
        self.compatibility_checker = compatibility_checker
        self.active_migrations = {}
        
    async def plan_migration(self, agent_type: str, 
                           current_version: str, 
                           target_version: str) -> Dict[str, Any]:
        """Plan a version migration."""
        compatibility, issues = await self.compatibility_checker.check_compatibility(
            agent_type, current_version, target_version
        )
        
        upgrade_path = await self.compatibility_checker.find_upgrade_path(
            agent_type, current_version, target_version
        )
        
        migration_plan = {
            "agent_type": agent_type,
            "current_version": current_version,
            "target_version": target_version,
            "compatibility": compatibility.value,
            "issues": issues,
            "upgrade_path": upgrade_path,
            "estimated_duration": len(upgrade_path) * 60,  # 60s per step
            "rollback_supported": compatibility != VersionCompatibility.INCOMPATIBLE,
            "created_at": datetime.now().isoformat()
        }
        
        return migration_plan
    
    async def execute_migration_step(self, migration_id: str, step: str) -> bool:
        """Execute a single migration step."""
        try:
            # Simulate migration step execution
            await asyncio.sleep(0.1)  # Simulate work
            
            # Update migration progress
            if migration_id not in self.active_migrations:
                self.active_migrations[migration_id] = {
                    "completed_steps": [],
                    "current_step": step,
                    "status": "in_progress"
                }
            
            self.active_migrations[migration_id]["completed_steps"].append(step)
            
            return True
            
        except Exception as e:
            logger.error(f"Migration step failed: {e}")
            return False
    
    async def rollback_migration(self, migration_id: str) -> bool:
        """Rollback a migration."""
        try:
            if migration_id in self.active_migrations:
                self.active_migrations[migration_id]["status"] = "rolled_back"
                return True
            return False
            
        except Exception as e:
            logger.error(f"Migration rollback failed: {e}")
            return False


class AgentVersionManager:
    """Manages agent version compatibility testing."""
    
    def __init__(self):
        self.redis_service = None
        self.version_registry = None
        self.compatibility_checker = None
        self.migration_manager = None
        
    async def initialize_services(self):
        """Initialize required services."""
        self.redis_service = RedisService()
        await self.redis_service.initialize()
        
        self.version_registry = VersionRegistry(self.redis_service)
        self.compatibility_checker = CompatibilityChecker(self.version_registry)
        self.migration_manager = MigrationManager(self.compatibility_checker)
        
        # Register test versions
        await self.register_test_versions()
        
    async def register_test_versions(self):
        """Register test agent versions."""
        test_versions = [
            AgentVersionInfo(
                agent_type="test_agent",
                version=AgentVersion(1, 0, 0),
                api_version="v1",
                features=["basic_processing", "simple_chat"],
                deprecated_features=[],
                required_dependencies={"redis": "6.0", "postgres": "13.0"},
                created_at=datetime.now() - timedelta(days=30)
            ),
            AgentVersionInfo(
                agent_type="test_agent",
                version=AgentVersion(1, 1, 0),
                api_version="v1.1",
                features=["basic_processing", "simple_chat", "enhanced_memory"],
                deprecated_features=["simple_chat"],
                required_dependencies={"redis": "6.2", "postgres": "13.0"},
                created_at=datetime.now() - timedelta(days=15)
            ),
            AgentVersionInfo(
                agent_type="test_agent",
                version=AgentVersion(1, 2, 0),
                api_version="v1.2",
                features=["basic_processing", "advanced_chat", "enhanced_memory"],
                deprecated_features=["simple_chat"],
                required_dependencies={"redis": "6.2", "postgres": "14.0"},
                created_at=datetime.now()
            )
        ]
        
        for version_info in test_versions:
            await self.version_registry.register_version(version_info)
    
    async def cleanup(self):
        """Clean up resources."""
        if self.redis_service:
            await self.redis_service.shutdown()


@pytest.fixture
async def version_manager():
    """Create version manager for testing."""
    manager = AgentVersionManager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_version_registration_and_retrieval(version_manager):
    """Test version registration and retrieval."""
    manager = version_manager
    
    # Test retrieving registered versions
    version_info = await manager.version_registry.get_version_info("test_agent", "1.0.0")
    
    assert version_info is not None
    assert version_info.agent_type == "test_agent"
    assert str(version_info.version) == "1.0.0"
    assert "basic_processing" in version_info.features
    
    # Test getting available versions
    versions = await manager.version_registry.get_available_versions("test_agent")
    assert len(versions) >= 3
    assert "1.0.0" in versions
    assert "1.1.0" in versions
    assert "1.2.0" in versions


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_version_compatibility_check(version_manager):
    """Test version compatibility checking."""
    manager = version_manager
    
    # Test fully compatible versions (same version)
    compatibility, issues = await manager.compatibility_checker.check_compatibility(
        "test_agent", "1.0.0", "1.0.0"
    )
    assert compatibility == VersionCompatibility.FULLY_COMPATIBLE
    assert len(issues) == 0
    
    # Test backwards compatible versions
    compatibility, issues = await manager.compatibility_checker.check_compatibility(
        "test_agent", "1.0.0", "1.1.0"
    )
    assert compatibility == VersionCompatibility.BACKWARDS_COMPATIBLE
    assert len(issues) >= 1  # API version mismatch


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_upgrade_path_calculation(version_manager):
    """Test upgrade path calculation."""
    manager = version_manager
    
    # Test upgrade path from 1.0.0 to 1.2.0
    upgrade_path = await manager.compatibility_checker.find_upgrade_path(
        "test_agent", "1.0.0", "1.2.0"
    )
    
    assert len(upgrade_path) >= 3
    assert upgrade_path[0] == "1.0.0"
    assert upgrade_path[-1] == "1.2.0"
    assert "1.1.0" in upgrade_path


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_migration_planning(version_manager):
    """Test migration planning."""
    manager = version_manager
    
    # Plan migration from 1.0.0 to 1.2.0
    migration_plan = await manager.migration_manager.plan_migration(
        "test_agent", "1.0.0", "1.2.0"
    )
    
    assert migration_plan["agent_type"] == "test_agent"
    assert migration_plan["current_version"] == "1.0.0"
    assert migration_plan["target_version"] == "1.2.0"
    assert migration_plan["compatibility"] == "backwards_compatible"
    assert len(migration_plan["upgrade_path"]) >= 3
    assert migration_plan["rollback_supported"] is True


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_migration_execution(version_manager):
    """Test migration step execution."""
    manager = version_manager
    
    migration_id = "test_migration_001"
    
    # Execute migration steps
    step1_result = await manager.migration_manager.execute_migration_step(
        migration_id, "1.0.0_to_1.1.0"
    )
    assert step1_result is True
    
    step2_result = await manager.migration_manager.execute_migration_step(
        migration_id, "1.1.0_to_1.2.0"
    )
    assert step2_result is True
    
    # Check migration state
    migration_state = manager.migration_manager.active_migrations[migration_id]
    assert len(migration_state["completed_steps"]) == 2
    assert migration_state["status"] == "in_progress"


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_migration_rollback(version_manager):
    """Test migration rollback."""
    manager = version_manager
    
    migration_id = "test_rollback_001"
    
    # Start migration
    await manager.migration_manager.execute_migration_step(migration_id, "step1")
    
    # Rollback migration
    rollback_result = await manager.migration_manager.rollback_migration(migration_id)
    assert rollback_result is True
    
    # Check rollback state
    migration_state = manager.migration_manager.active_migrations[migration_id]
    assert migration_state["status"] == "rolled_back"


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_concurrent_version_operations(version_manager):
    """Test concurrent version operations."""
    manager = version_manager
    
    # Register multiple versions concurrently
    version_infos = []
    for i in range(5):
        version_info = AgentVersionInfo(
            agent_type=f"concurrent_agent_{i}",
            version=AgentVersion(1, 0, 0),
            api_version="v1",
            features=["feature1"],
            deprecated_features=[],
            required_dependencies={},
            created_at=datetime.now()
        )
        version_infos.append(version_info)
    
    # Register concurrently
    register_tasks = [
        manager.version_registry.register_version(info) 
        for info in version_infos
    ]
    results = await asyncio.gather(*register_tasks)
    
    assert all(results)
    
    # Retrieve concurrently
    retrieve_tasks = [
        manager.version_registry.get_version_info(f"concurrent_agent_{i}", "1.0.0")
        for i in range(5)
    ]
    retrieved_infos = await asyncio.gather(*retrieve_tasks)
    
    assert len(retrieved_infos) == 5
    assert all(info is not None for info in retrieved_infos)


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_version_compatibility_performance(version_manager):
    """Benchmark version compatibility performance."""
    manager = version_manager
    
    # Performance test for compatibility checks
    start_time = time.time()
    
    compatibility_tasks = []
    for i in range(50):
        task = manager.compatibility_checker.check_compatibility(
            "test_agent", "1.0.0", "1.2.0"
        )
        compatibility_tasks.append(task)
    
    results = await asyncio.gather(*compatibility_tasks)
    check_time = time.time() - start_time
    
    assert len(results) == 50
    assert all(result[0] == VersionCompatibility.BACKWARDS_COMPATIBLE for result in results)
    
    # Performance assertions
    assert check_time < 2.0  # 50 checks in under 2 seconds
    avg_check_time = check_time / 50
    assert avg_check_time < 0.04  # Average check under 40ms
    
    logger.info(f"Performance: {avg_check_time*1000:.1f}ms per compatibility check")


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_version_registry_persistence(version_manager):
    """Test version registry persistence."""
    manager = version_manager
    
    # Register a new version
    test_version = AgentVersionInfo(
        agent_type="persistence_test",
        version=AgentVersion(2, 0, 0),
        api_version="v2",
        features=["new_feature"],
        deprecated_features=[],
        required_dependencies={"redis": "7.0"},
        created_at=datetime.now()
    )
    
    register_result = await manager.version_registry.register_version(test_version)
    assert register_result is True
    
    # Retrieve and verify
    retrieved_version = await manager.version_registry.get_version_info(
        "persistence_test", "2.0.0"
    )
    
    assert retrieved_version is not None
    assert retrieved_version.agent_type == "persistence_test"
    assert str(retrieved_version.version) == "2.0.0"
    assert retrieved_version.api_version == "v2"
    assert "new_feature" in retrieved_version.features