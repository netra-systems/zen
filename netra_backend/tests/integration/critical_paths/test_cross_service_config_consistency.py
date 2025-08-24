"""Cross-Service Configuration Consistency L3 Integration Tests

Business Value Justification (BVJ):
- Segment: Platform stability (all tiers)
- Business Goal: Prevent configuration drift and service inconsistencies
- Value Impact: $50K MRR - Configuration inconsistencies cause 25% of integration failures
- Strategic Impact: Ensures microservice ecosystem operates with synchronized configurations

Critical Path: Configuration synchronization -> Consistency validation -> Drift detection -> Version compatibility -> Service discovery integration -> Reconciliation
Coverage: Multi-service config sync, version compatibility checks, drift detection mechanisms, automated reconciliation, service mesh integration
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import AsyncMock, MagicMock, MagicMock, patch

import pytest

from netra_backend.app.config import get_config

from netra_backend.app.redis_manager import RedisManager
from test_framework.mock_utils import mock_justified

logger = logging.getLogger(__name__)

class ConfigSyncStatus(Enum):
    """Configuration synchronization status."""
    SYNCHRONIZED = "synchronized"
    DRIFT_DETECTED = "drift_detected"
    VERSION_MISMATCH = "version_mismatch"
    SYNC_IN_PROGRESS = "sync_in_progress"
    SYNC_FAILED = "sync_failed"

@dataclass
class ServiceConfigState:
    """Service configuration state."""
    service_name: str
    version: str
    config_hash: str
    last_updated: datetime
    config_data: Dict[str, Any]
    dependencies: Set[str] = field(default_factory=set)
    status: ConfigSyncStatus = ConfigSyncStatus.SYNCHRONIZED

@dataclass
class ConfigDriftResult:
    """Configuration drift detection result."""
    service_name: str
    drift_detected: bool
    drift_severity: str  # low, medium, high, critical
    drift_fields: List[str] = field(default_factory=list)
    expected_values: Dict[str, Any] = field(default_factory=dict)
    actual_values: Dict[str, Any] = field(default_factory=dict)
    drift_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class ConsistencyCheckResult:
    """Configuration consistency check result."""
    check_timestamp: datetime
    total_services: int
    consistent_services: int
    inconsistent_services: int
    accuracy_percentage: float
    drift_results: List[ConfigDriftResult] = field(default_factory=list)
    version_mismatches: List[Tuple[str, str, str]] = field(default_factory=list)  # service, expected, actual
    reconciliation_needed: List[str] = field(default_factory=list)

class CrossServiceConfigConsistencyManager:
    """Manages cross-service configuration consistency validation and synchronization."""
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self.service_configs: Dict[str, ServiceConfigState] = {}
        self.consistency_check_interval = 60  # seconds
        self.drift_detection_threshold = 0.001  # 99.9% accuracy requirement
        self.config_version_tolerance = 2  # Allow 2 versions behind
        
        # Define service configuration templates
        self.service_templates = {
            "auth_service": {
                "required_configs": ["jwt_secret", "token_expiry", "refresh_expiry", "oauth_config"],
                "shared_configs": ["redis_config", "database_config", "logging_config"],
                "critical_configs": ["jwt_secret", "oauth_config"],
                "version_key": "auth_service_version"
            },
            "api_service": {
                "required_configs": ["rate_limits", "cors_config", "auth_endpoints"],
                "shared_configs": ["redis_config", "database_config", "logging_config"],
                "critical_configs": ["auth_endpoints", "rate_limits"],
                "version_key": "api_service_version"
            },
            "websocket_service": {
                "required_configs": ["max_connections", "heartbeat_interval", "auth_integration"],
                "shared_configs": ["redis_config", "auth_endpoints", "logging_config"],
                "critical_configs": ["auth_integration", "max_connections"],
                "version_key": "websocket_service_version"
            },
            "llm_service": {
                "required_configs": ["model_configs", "rate_limits", "timeout_config"],
                "shared_configs": ["redis_config", "logging_config"],
                "critical_configs": ["model_configs", "timeout_config"],
                "version_key": "llm_service_version"
            }
        }
        
        # Mock shared configuration values
        self.shared_config_values = {
            "redis_config": {
                "host": "redis.netra.internal",
                "port": 6379,
                "db": 0,
                "timeout": 5
            },
            "database_config": {
                "host": "postgres.netra.internal",
                "port": 5432,
                "database": "netra_main",
                "pool_size": 20
            },
            "logging_config": {
                "level": "INFO",
                "format": "json",
                "output": "stdout"
            },
            "auth_endpoints": {
                "token_url": "https://auth.netrasystems.ai/token",
                "validate_url": "https://auth.netrasystems.ai/validate",
                "refresh_url": "https://auth.netrasystems.ai/refresh"
            }
        }
    
    async def register_service_config(self, service_name: str, config_data: Dict[str, Any], 
                                    version: str = "1.0.0") -> ServiceConfigState:
        """Register service configuration for consistency tracking."""
        config_hash = self._calculate_config_hash(config_data)
        
        service_state = ServiceConfigState(
            service_name=service_name,
            version=version,
            config_hash=config_hash,
            last_updated=datetime.now(timezone.utc),
            config_data=config_data.copy(),
            dependencies=self._extract_dependencies(service_name, config_data)
        )
        
        self.service_configs[service_name] = service_state
        
        # Cache in Redis if available
        if self.redis_client:
            await self._cache_service_config(service_state)
        
        return service_state
    
    def _calculate_config_hash(self, config_data: Dict[str, Any]) -> str:
        """Calculate deterministic hash of configuration data."""
        # Sort keys for consistent hashing
        sorted_config = json.dumps(config_data, sort_keys=True)
        return hashlib.sha256(sorted_config.encode()).hexdigest()[:16]
    
    def _extract_dependencies(self, service_name: str, config_data: Dict[str, Any]) -> Set[str]:
        """Extract service dependencies from configuration."""
        dependencies = set()
        
        if service_name in self.service_templates:
            template = self.service_templates[service_name]
            
            # Check for shared config dependencies
            for shared_config in template["shared_configs"]:
                if shared_config in config_data:
                    dependencies.add(shared_config)
            
            # Check for service-specific dependencies
            if "auth_endpoints" in config_data:
                dependencies.add("auth_service")
            if "database_config" in config_data:
                dependencies.add("database_service")
            if "redis_config" in config_data:
                dependencies.add("redis_service")
        
        return dependencies
    
    async def _cache_service_config(self, service_state: ServiceConfigState):
        """Cache service configuration state in Redis."""
        try:
            key = f"service_config:{service_state.service_name}"
            value = {
                "version": service_state.version,
                "config_hash": service_state.config_hash,
                "last_updated": service_state.last_updated.isoformat(),
                "config_data": service_state.config_data,
                "dependencies": list(service_state.dependencies),
                "status": service_state.status.value
            }
            await self.redis_client.set(key, json.dumps(value), ex=3600)
        except Exception as e:
            logger.warning(f"Failed to cache service config for {service_state.service_name}: {e}")
    
    async def check_cross_service_consistency(self) -> ConsistencyCheckResult:
        """Check configuration consistency across all registered services."""
        check_timestamp = datetime.now(timezone.utc)
        total_services = len(self.service_configs)
        
        if total_services == 0:
            return ConsistencyCheckResult(
                check_timestamp=check_timestamp,
                total_services=0,
                consistent_services=0,
                inconsistent_services=0,
                accuracy_percentage=100.0
            )
        
        # Detect configuration drift
        drift_results = []
        version_mismatches = []
        reconciliation_needed = []
        
        for service_name, service_state in self.service_configs.items():
            # Check for configuration drift
            drift_result = await self._detect_configuration_drift(service_name, service_state)
            if drift_result.drift_detected:
                drift_results.append(drift_result)
                if drift_result.drift_severity in ["high", "critical"]:
                    reconciliation_needed.append(service_name)
            
            # Check version compatibility
            version_mismatch = await self._check_version_compatibility(service_name, service_state)
            if version_mismatch:
                version_mismatches.append(version_mismatch)
                reconciliation_needed.append(service_name)
        
        # Calculate consistency metrics
        inconsistent_services = len(set(reconciliation_needed))
        consistent_services = total_services - inconsistent_services
        accuracy_percentage = (consistent_services / total_services) * 100.0
        
        return ConsistencyCheckResult(
            check_timestamp=check_timestamp,
            total_services=total_services,
            consistent_services=consistent_services,
            inconsistent_services=inconsistent_services,
            accuracy_percentage=accuracy_percentage,
            drift_results=drift_results,
            version_mismatches=version_mismatches,
            reconciliation_needed=list(set(reconciliation_needed))
        )
    
    async def _detect_configuration_drift(self, service_name: str, 
                                        service_state: ServiceConfigState) -> ConfigDriftResult:
        """Detect configuration drift for a specific service."""
        drift_result = ConfigDriftResult(
            service_name=service_name,
            drift_detected=False,
            drift_severity="low"
        )
        
        if service_name not in self.service_templates:
            return drift_result
        
        template = self.service_templates[service_name]
        
        # Check shared configurations for drift
        for shared_config_key in template["shared_configs"]:
            if shared_config_key in service_state.config_data:
                expected_config = self.shared_config_values.get(shared_config_key, {})
                actual_config = service_state.config_data[shared_config_key]
                
                # Compare configurations
                config_diff = self._compare_configs(expected_config, actual_config)
                if config_diff:
                    drift_result.drift_detected = True
                    drift_result.drift_fields.extend(config_diff)
                    drift_result.expected_values[shared_config_key] = expected_config
                    drift_result.actual_values[shared_config_key] = actual_config
                    
                    # Determine severity
                    if shared_config_key in template["critical_configs"]:
                        drift_result.drift_severity = "critical"
                    elif drift_result.drift_severity not in ["high", "critical"]:
                        drift_result.drift_severity = "medium"
        
        # Check required configurations
        for required_config in template["required_configs"]:
            if required_config not in service_state.config_data:
                drift_result.drift_detected = True
                drift_result.drift_fields.append(f"missing_{required_config}")
                drift_result.drift_severity = "high"
        
        return drift_result
    
    def _compare_configs(self, expected: Dict[str, Any], actual: Dict[str, Any]) -> List[str]:
        """Compare two configuration dictionaries and return differences."""
        differences = []
        
        # Check for missing or different values
        for key, expected_value in expected.items():
            if key not in actual:
                differences.append(f"missing_{key}")
            elif actual[key] != expected_value:
                differences.append(f"changed_{key}")
        
        # Check for unexpected values
        for key in actual:
            if key not in expected:
                differences.append(f"unexpected_{key}")
        
        return differences
    
    async def _check_version_compatibility(self, service_name: str, 
                                         service_state: ServiceConfigState) -> Optional[Tuple[str, str, str]]:
        """Check version compatibility for a service."""
        if service_name not in self.service_templates:
            return None
        
        template = self.service_templates[service_name]
        version_key = template["version_key"]
        
        # Get expected version from shared config or latest known version
        expected_version = self._get_expected_version(service_name)
        actual_version = service_state.version
        
        if not self._is_version_compatible(expected_version, actual_version):
            return (service_name, expected_version, actual_version)
        
        return None
    
    def _get_expected_version(self, service_name: str) -> str:
        """Get expected version for a service."""
        # For testing, use mock version mapping
        version_mapping = {
            "auth_service": "2.1.0",
            "api_service": "1.8.0",
            "websocket_service": "1.5.0",
            "llm_service": "3.0.0"
        }
        return version_mapping.get(service_name, "1.0.0")
    
    def _is_version_compatible(self, expected: str, actual: str) -> bool:
        """Check if versions are compatible within tolerance."""
        try:
            expected_parts = [int(x) for x in expected.split('.')]
            actual_parts = [int(x) for x in actual.split('.')]
            
            # Major version must match
            if expected_parts[0] != actual_parts[0]:
                return False
            
            # Minor version tolerance
            minor_diff = expected_parts[1] - actual_parts[1]
            return abs(minor_diff) <= self.config_version_tolerance
        except (ValueError, IndexError):
            return False
    
    async def reconcile_service_configuration(self, service_name: str) -> bool:
        """Reconcile service configuration to fix drift and version issues."""
        if service_name not in self.service_configs:
            return False
        
        service_state = self.service_configs[service_name]
        
        # Update shared configurations
        if service_name in self.service_templates:
            template = self.service_templates[service_name]
            updated = False
            
            for shared_config_key in template["shared_configs"]:
                expected_config = self.shared_config_values.get(shared_config_key)
                if expected_config:
                    service_state.config_data[shared_config_key] = expected_config.copy()
                    updated = True
            
            if updated:
                # Update service state
                service_state.config_hash = self._calculate_config_hash(service_state.config_data)
                service_state.last_updated = datetime.now(timezone.utc)
                service_state.status = ConfigSyncStatus.SYNCHRONIZED
                
                # Update version to expected
                service_state.version = self._get_expected_version(service_name)
                
                # Cache updated state
                if self.redis_client:
                    await self._cache_service_config(service_state)
                
                return True
        
        return False
    
    async def perform_bulk_reconciliation(self, service_names: List[str]) -> Dict[str, bool]:
        """Perform bulk reconciliation for multiple services."""
        reconciliation_tasks = []
        
        for service_name in service_names:
            task = self.reconcile_service_configuration(service_name)
            reconciliation_tasks.append(task)
        
        results = await asyncio.gather(*reconciliation_tasks, return_exceptions=True)
        
        reconciliation_results = {}
        for i, service_name in enumerate(service_names):
            if isinstance(results[i], bool):
                reconciliation_results[service_name] = results[i]
            else:
                reconciliation_results[service_name] = False
        
        return reconciliation_results
    
    async def simulate_service_discovery_integration(self) -> Dict[str, Any]:
        """Simulate service discovery integration for configuration propagation."""
        discovery_results = {}
        
        for service_name, service_state in self.service_configs.items():
            # Simulate service discovery update
            await asyncio.sleep(0.01)  # Simulate network delay
            
            discovery_info = {
                "service_name": service_name,
                "config_version": service_state.version,
                "config_hash": service_state.config_hash,
                "last_updated": service_state.last_updated.isoformat(),
                "status": service_state.status.value,
                "endpoints": self._generate_service_endpoints(service_name),
                "health_status": "healthy"
            }
            
            discovery_results[service_name] = discovery_info
        
        return discovery_results
    
    def _generate_service_endpoints(self, service_name: str) -> List[Dict[str, Any]]:
        """Generate mock service endpoints for service discovery."""
        base_ports = {
            "auth_service": 8001,
            "api_service": 8000,
            "websocket_service": 8002,
            "llm_service": 8003
        }
        
        port = base_ports.get(service_name, 8000)
        
        return [
            {
                "host": f"{service_name}-1.netra.internal",
                "port": port,
                "zone": "us-central1-a",
                "weight": 100
            },
            {
                "host": f"{service_name}-2.netra.internal",
                "port": port,
                "zone": "us-central1-b",
                "weight": 100
            }
        ]

@pytest.fixture
async def redis_client():
    """Create Redis client for configuration caching."""
    try:
        import redis.asyncio as redis
        client = redis.Redis(host="localhost", port=6379, decode_responses=True, db=2)
        # Test connection
        await client.ping()
        yield client
        await client.close()
    except Exception:
        # If Redis not available, return None
        yield None

@pytest.fixture
async def consistency_manager(redis_client):
    """Create cross-service configuration consistency manager."""
    yield CrossServiceConfigConsistencyManager(redis_client)

@pytest.mark.L3
@pytest.mark.integration
class TestCrossServiceConfigConsistencyL3:
    """L3 integration tests for cross-service configuration consistency."""
    
    @pytest.mark.asyncio
    async def test_service_config_registration_and_tracking(self, consistency_manager):
        """Test service configuration registration and state tracking."""
        # Register multiple services
        auth_config = {
            "jwt_secret": "test_secret",
            "token_expiry": 3600,
            "oauth_config": {"client_id": "test_client"},
            "redis_config": consistency_manager.shared_config_values["redis_config"],
            "database_config": consistency_manager.shared_config_values["database_config"]
        }
        
        api_config = {
            "rate_limits": {"requests_per_minute": 1000},
            "cors_config": {"origins": ["https://app.netrasystems.ai"]},
            "auth_endpoints": consistency_manager.shared_config_values["auth_endpoints"],
            "redis_config": consistency_manager.shared_config_values["redis_config"]
        }
        
        # Register services
        auth_state = await consistency_manager.register_service_config("auth_service", auth_config, "2.1.0")
        api_state = await consistency_manager.register_service_config("api_service", api_config, "1.8.0")
        
        # Verify registration
        assert auth_state.service_name == "auth_service"
        assert auth_state.version == "2.1.0"
        assert len(auth_state.config_hash) == 16  # SHA256 truncated
        assert "redis_config" in auth_state.dependencies
        assert "database_config" in auth_state.dependencies
        
        assert api_state.service_name == "api_service"
        assert api_state.version == "1.8.0"
        assert "auth_service" in api_state.dependencies
        assert "redis_config" in api_state.dependencies
        
        # Verify services are tracked
        assert len(consistency_manager.service_configs) == 2
    
    @pytest.mark.asyncio
    async def test_configuration_drift_detection_accuracy(self, consistency_manager):
        """Test configuration drift detection with >99.9% accuracy requirement."""
        # Register service with correct configuration
        correct_config = {
            "max_connections": 1000,
            "heartbeat_interval": 30,
            "auth_integration": {"enabled": True},
            "redis_config": consistency_manager.shared_config_values["redis_config"],
            "auth_endpoints": consistency_manager.shared_config_values["auth_endpoints"]
        }
        
        await consistency_manager.register_service_config("websocket_service", correct_config, "1.5.0")
        
        # Check consistency (should be perfect)
        result = await consistency_manager.check_cross_service_consistency()
        assert result.accuracy_percentage >= 99.9, f"Accuracy {result.accuracy_percentage}% below 99.9% requirement"
        assert result.consistent_services == 1
        assert result.inconsistent_services == 0
        
        # Introduce configuration drift
        drifted_config = correct_config.copy()
        drifted_config["redis_config"] = {
            "host": "wrong-redis-host",  # Drift in shared config
            "port": 6380,  # Wrong port
            "db": 1,  # Wrong database
            "timeout": 10  # Wrong timeout
        }
        
        await consistency_manager.register_service_config("websocket_service", drifted_config, "1.5.0")
        
        # Check consistency (should detect drift)
        result = await consistency_manager.check_cross_service_consistency()
        assert result.accuracy_percentage < 99.9  # Should detect the drift
        assert result.inconsistent_services == 1
        assert len(result.drift_results) == 1
        
        drift_result = result.drift_results[0]
        assert drift_result.drift_detected
        assert drift_result.service_name == "websocket_service"
        assert len(drift_result.drift_fields) >= 4  # host, port, db, timeout changes
    
    @pytest.mark.asyncio
    async def test_version_compatibility_checking(self, consistency_manager):
        """Test version compatibility validation across services."""
        # Register services with various version scenarios
        test_cases = [
            ("auth_service", "2.1.0", True),   # Exact match
            ("api_service", "1.8.0", True),   # Exact match
            ("websocket_service", "1.4.0", True),  # Within tolerance (1 minor version)
            ("llm_service", "2.0.0", False),  # Major version mismatch
            ("auth_service", "1.0.0", False), # Too old (major version mismatch)
        ]
        
        version_mismatch_count = 0
        
        for service_name, version, should_be_compatible in test_cases:
            if service_name in consistency_manager.service_templates:
                config_data = {
                    "test_config": "value",
                    "redis_config": consistency_manager.shared_config_values["redis_config"]
                }
                
                await consistency_manager.register_service_config(service_name, config_data, version)
                
                if not should_be_compatible:
                    version_mismatch_count += 1
        
        # Check consistency
        result = await consistency_manager.check_cross_service_consistency()
        
        # Should detect version mismatches
        assert len(result.version_mismatches) == version_mismatch_count
        assert result.inconsistent_services == version_mismatch_count
        
        # Verify specific version mismatches
        mismatched_services = [vm[0] for vm in result.version_mismatches]
        assert "llm_service" in mismatched_services  # Major version mismatch
    
    @pytest.mark.asyncio
    async def test_configuration_reconciliation_mechanisms(self, consistency_manager):
        """Test automated configuration reconciliation."""
        # Register service with drift
        drifted_config = {
            "jwt_secret": "test_secret",
            "token_expiry": 3600,
            "oauth_config": {"client_id": "test_client"},
            "redis_config": {
                "host": "wrong-host",  # Incorrect shared config
                "port": 6380,
                "db": 1
            },
            "database_config": {
                "host": "wrong-db-host",  # Incorrect shared config
                "port": 5433
            }
        }
        
        await consistency_manager.register_service_config("auth_service", drifted_config, "1.0.0")
        
        # Verify drift exists
        pre_reconcile_result = await consistency_manager.check_cross_service_consistency()
        assert pre_reconcile_result.inconsistent_services == 1
        assert len(pre_reconcile_result.drift_results) == 1
        
        # Perform reconciliation
        reconcile_success = await consistency_manager.reconcile_service_configuration("auth_service")
        assert reconcile_success, "Reconciliation should succeed"
        
        # Verify reconciliation fixed the issues
        post_reconcile_result = await consistency_manager.check_cross_service_consistency()
        assert post_reconcile_result.consistent_services == 1
        assert post_reconcile_result.inconsistent_services == 0
        
        # Verify configuration was corrected
        auth_service_state = consistency_manager.service_configs["auth_service"]
        assert auth_service_state.config_data["redis_config"] == consistency_manager.shared_config_values["redis_config"]
        assert auth_service_state.config_data["database_config"] == consistency_manager.shared_config_values["database_config"]
        assert auth_service_state.version == "2.1.0"  # Should update to expected version
    
    @pytest.mark.asyncio
    async def test_bulk_reconciliation_performance(self, consistency_manager):
        """Test bulk reconciliation performance across multiple services."""
        # Register multiple services with various issues
        services_with_issues = [
            ("auth_service", {"drift": True, "version": "1.0.0"}),
            ("api_service", {"drift": True, "version": "1.6.0"}),
            ("websocket_service", {"drift": False, "version": "1.3.0"}),
            ("llm_service", {"drift": True, "version": "2.8.0"})
        ]
        
        for service_name, issues in services_with_issues:
            if service_name in consistency_manager.service_templates:
                config_data = {"test_config": "value"}
                
                if issues["drift"]:
                    # Add incorrect shared config
                    config_data["redis_config"] = {
                        "host": "wrong-host",
                        "port": 6380
                    }
                else:
                    # Add correct shared config
                    config_data["redis_config"] = consistency_manager.shared_config_values["redis_config"]
                
                await consistency_manager.register_service_config(service_name, config_data, issues["version"])
        
        # Perform bulk reconciliation
        service_names = [s[0] for s in services_with_issues 
                        if s[0] in consistency_manager.service_templates]
        
        start_time = time.time()
        reconciliation_results = await consistency_manager.perform_bulk_reconciliation(service_names)
        reconciliation_time = time.time() - start_time
        
        # Performance assertion
        assert reconciliation_time < 10.0, f"Bulk reconciliation took {reconciliation_time}s, should be <10s"
        
        # Verify all reconciliations succeeded
        successful_reconciliations = sum(1 for success in reconciliation_results.values() if success)
        assert successful_reconciliations == len(service_names), "All reconciliations should succeed"
        
        # Verify consistency after reconciliation
        final_result = await consistency_manager.check_cross_service_consistency()
        assert final_result.accuracy_percentage >= 99.9, "Consistency should be restored"
    
    @pytest.mark.asyncio
    async def test_service_discovery_integration(self, consistency_manager):
        """Test service discovery integration for configuration propagation."""
        # Register services
        services_configs = {
            "auth_service": {
                "jwt_secret": "secret",
                "redis_config": consistency_manager.shared_config_values["redis_config"]
            },
            "api_service": {
                "rate_limits": {"rpm": 1000},
                "auth_endpoints": consistency_manager.shared_config_values["auth_endpoints"]
            },
            "websocket_service": {
                "max_connections": 1000,
                "redis_config": consistency_manager.shared_config_values["redis_config"]
            }
        }
        
        for service_name, config in services_configs.items():
            await consistency_manager.register_service_config(service_name, config, "1.0.0")
        
        # Simulate service discovery integration
        discovery_results = await consistency_manager.simulate_service_discovery_integration()
        
        # Verify discovery results
        assert len(discovery_results) == len(services_configs)
        
        for service_name, discovery_info in discovery_results.items():
            assert discovery_info["service_name"] == service_name
            assert "config_version" in discovery_info
            assert "config_hash" in discovery_info
            assert "endpoints" in discovery_info
            assert discovery_info["health_status"] == "healthy"
            
            # Verify endpoints are generated
            endpoints = discovery_info["endpoints"]
            assert len(endpoints) >= 2  # At least 2 instances
            for endpoint in endpoints:
                assert "host" in endpoint
                assert "port" in endpoint
                assert "zone" in endpoint
    
    @pytest.mark.asyncio
    async def test_real_time_drift_detection(self, consistency_manager):
        """Test real-time drift detection as configurations change."""
        # Register initial configuration
        initial_config = {
            "model_configs": {"gpt4": {"max_tokens": 4000}},
            "rate_limits": {"rpm": 100},
            "redis_config": consistency_manager.shared_config_values["redis_config"]
        }
        
        await consistency_manager.register_service_config("llm_service", initial_config, "3.0.0")
        
        # Verify initial consistency
        result1 = await consistency_manager.check_cross_service_consistency()
        assert result1.accuracy_percentage >= 99.9
        
        # Simulate configuration change that introduces drift
        modified_config = initial_config.copy()
        modified_config["redis_config"] = {
            "host": "modified-redis-host",
            "port": 6379,
            "db": 0,
            "timeout": 5
        }
        
        await consistency_manager.register_service_config("llm_service", modified_config, "3.0.0")
        
        # Check for drift detection
        result2 = await consistency_manager.check_cross_service_consistency()
        assert result2.accuracy_percentage < 99.9
        assert len(result2.drift_results) == 1
        
        drift_result = result2.drift_results[0]
        assert drift_result.drift_detected
        assert "changed_host" in drift_result.drift_fields
        
        # Fix the drift
        await consistency_manager.reconcile_service_configuration("llm_service")
        
        # Verify drift is resolved
        result3 = await consistency_manager.check_cross_service_consistency()
        assert result3.accuracy_percentage >= 99.9
        assert len(result3.drift_results) == 0
    
    @mock_justified("L3: Cross-service configuration consistency testing with controlled service simulation")
    @pytest.mark.asyncio
    async def test_consistency_monitoring_reliability(self, consistency_manager):
        """Test reliability and accuracy of consistency monitoring system."""
        # Setup comprehensive test scenario
        test_scenarios = [
            # Scenario 1: All services consistent
            {
                "name": "all_consistent",
                "services": {
                    "auth_service": {"correct": True, "version": "2.1.0"},
                    "api_service": {"correct": True, "version": "1.8.0"},
                    "websocket_service": {"correct": True, "version": "1.5.0"}
                },
                "expected_accuracy": 100.0
            },
            # Scenario 2: Partial drift
            {
                "name": "partial_drift",
                "services": {
                    "auth_service": {"correct": True, "version": "2.1.0"},
                    "api_service": {"correct": False, "version": "1.8.0"},  # Drift
                    "websocket_service": {"correct": True, "version": "1.5.0"}
                },
                "expected_accuracy": 66.7  # 2/3 consistent
            },
            # Scenario 3: Version mismatches
            {
                "name": "version_mismatches",
                "services": {
                    "auth_service": {"correct": True, "version": "1.0.0"},  # Old version
                    "api_service": {"correct": True, "version": "1.8.0"},
                    "websocket_service": {"correct": True, "version": "2.0.0"}  # Wrong major version
                },
                "expected_accuracy": 33.3  # Only api_service consistent
            }
        ]
        
        reliability_results = []
        
        for scenario in test_scenarios:
            # Clear previous state
            consistency_manager.service_configs.clear()
            
            # Setup scenario
            for service_name, service_config in scenario["services"].items():
                if service_name in consistency_manager.service_templates:
                    config_data = {"test_config": "value"}
                    
                    if service_config["correct"]:
                        # Use correct shared config
                        config_data["redis_config"] = consistency_manager.shared_config_values["redis_config"]
                    else:
                        # Use incorrect shared config (drift)
                        config_data["redis_config"] = {
                            "host": "wrong-host",
                            "port": 6380
                        }
                    
                    await consistency_manager.register_service_config(
                        service_name, 
                        config_data, 
                        service_config["version"]
                    )
            
            # Run consistency check multiple times for reliability
            consistency_results = []
            for _ in range(5):
                result = await consistency_manager.check_cross_service_consistency()
                consistency_results.append(result.accuracy_percentage)
            
            # Calculate reliability metrics
            avg_accuracy = sum(consistency_results) / len(consistency_results)
            accuracy_variance = sum((x - avg_accuracy) ** 2 for x in consistency_results) / len(consistency_results)
            
            reliability_results.append({
                "scenario": scenario["name"],
                "expected_accuracy": scenario["expected_accuracy"],
                "actual_accuracy": avg_accuracy,
                "accuracy_variance": accuracy_variance,
                "consistent_results": all(abs(r - avg_accuracy) < 1.0 for r in consistency_results)
            })
        
        # Assert reliability requirements
        for result in reliability_results:
            # Accuracy should be within 5% of expected
            accuracy_difference = abs(result["actual_accuracy"] - result["expected_accuracy"])
            assert accuracy_difference <= 5.0, f"Accuracy difference {accuracy_difference}% too high for {result['scenario']}"
            
            # Results should be consistent across runs
            assert result["consistent_results"], f"Inconsistent results for {result['scenario']}"
            
            # Low variance indicates reliable detection
            assert result["accuracy_variance"] < 4.0, f"High variance {result['accuracy_variance']} for {result['scenario']}"

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])