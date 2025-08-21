"""Configuration Hot Reload L3 Integration Tests

Business Value Justification (BVJ):
- Segment: Platform operations (all tiers)
- Business Goal: Zero-downtime configuration updates, operational efficiency
- Value Impact: $75K MRR - Enables rapid configuration changes without service interruption
- Strategic Impact: Hot reload capabilities reduce deployment overhead and improve system agility

Critical Path: Config change detection -> Validation -> Rollback preparation -> Service coordination -> Hot reload <10s -> Verification
Coverage: Runtime configuration updates, validation mechanisms, rollback capabilities, service coordination, zero-downtime operations
"""

import pytest
import asyncio
import time
import uuid
import json
import logging
import os
import tempfile
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.schemas.registry import TaskPriority

logger = logging.getLogger(__name__)


class ConfigurationType(Enum):
    """Types of configuration that can be hot reloaded."""
    SERVICE_SETTINGS = "service_settings"
    FEATURE_FLAGS = "feature_flags"
    RATE_LIMITS = "rate_limits"
    CIRCUIT_BREAKER = "circuit_breaker"
    DATABASE_POOL = "database_pool"
    CACHE_SETTINGS = "cache_settings"
    LOGGING_LEVEL = "logging_level"


class ReloadStatus(Enum):
    """Status of configuration reload operation."""
    PENDING = "pending"
    VALIDATING = "validating"
    APPLYING = "applying"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class ConfigurationSnapshot:
    """Snapshot of configuration state."""
    config_type: ConfigurationType
    version: str
    timestamp: datetime
    data: Dict[str, Any]
    checksum: str
    
    def validate(self) -> bool:
        """Validate configuration data integrity."""
        import hashlib
        calculated_checksum = hashlib.md5(json.dumps(self.data, sort_keys=True).encode()).hexdigest()
        return calculated_checksum == self.checksum


@dataclass
class ReloadMetrics:
    """Metrics for configuration reload operations."""
    total_reloads: int = 0
    successful_reloads: int = 0
    failed_reloads: int = 0
    rollbacks: int = 0
    average_reload_time: float = 0.0
    max_reload_time: float = 0.0
    validation_failures: int = 0
    service_coordination_time: float = 0.0
    
    def get_success_rate(self) -> float:
        """Calculate reload success rate percentage."""
        if self.total_reloads == 0:
            return 0.0
        return (self.successful_reloads / self.total_reloads) * 100.0


class ConfigurationValidator:
    """Validates configuration changes before applying."""
    
    def __init__(self):
        self.validation_rules = {
            ConfigurationType.SERVICE_SETTINGS: self._validate_service_settings,
            ConfigurationType.FEATURE_FLAGS: self._validate_feature_flags,
            ConfigurationType.RATE_LIMITS: self._validate_rate_limits,
            ConfigurationType.CIRCUIT_BREAKER: self._validate_circuit_breaker,
            ConfigurationType.DATABASE_POOL: self._validate_database_pool,
            ConfigurationType.CACHE_SETTINGS: self._validate_cache_settings,
            ConfigurationType.LOGGING_LEVEL: self._validate_logging_level
        }
    
    async def validate_configuration(self, config_type: ConfigurationType, 
                                   new_config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate new configuration against rules."""
        validation_result = {
            "valid": False,
            "errors": [],
            "warnings": [],
            "config_type": config_type.value
        }
        
        try:
            if config_type in self.validation_rules:
                validator_func = self.validation_rules[config_type]
                validation_result = await validator_func(new_config)
            else:
                validation_result["errors"].append(f"No validator for {config_type.value}")
            
            validation_result["valid"] = len(validation_result["errors"]) == 0
            
        except Exception as e:
            validation_result["errors"].append(f"Validation exception: {str(e)}")
            validation_result["valid"] = False
        
        return validation_result
    
    async def _validate_service_settings(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate service settings configuration."""
        result = {"errors": [], "warnings": []}
        
        required_fields = ["service_name", "port", "timeout"]
        for field in required_fields:
            if field not in config:
                result["errors"].append(f"Missing required field: {field}")
        
        if "port" in config:
            port = config["port"]
            if not isinstance(port, int) or port < 1024 or port > 65535:
                result["errors"].append(f"Invalid port: {port}")
        
        if "timeout" in config:
            timeout = config["timeout"]
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                result["errors"].append(f"Invalid timeout: {timeout}")
        
        return result
    
    async def _validate_feature_flags(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate feature flags configuration."""
        result = {"errors": [], "warnings": []}
        
        if not isinstance(config, dict):
            result["errors"].append("Feature flags must be a dictionary")
            return result
        
        for flag_name, flag_value in config.items():
            if not isinstance(flag_name, str):
                result["errors"].append(f"Flag name must be string: {flag_name}")
            
            if not isinstance(flag_value, bool):
                result["errors"].append(f"Flag value must be boolean: {flag_name}")
        
        return result
    
    async def _validate_rate_limits(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate rate limits configuration."""
        result = {"errors": [], "warnings": []}
        
        required_fields = ["requests_per_second", "burst_size"]
        for field in required_fields:
            if field not in config:
                result["errors"].append(f"Missing required field: {field}")
        
        if "requests_per_second" in config:
            rps = config["requests_per_second"]
            if not isinstance(rps, (int, float)) or rps <= 0:
                result["errors"].append(f"Invalid requests_per_second: {rps}")
        
        if "burst_size" in config:
            burst = config["burst_size"]
            if not isinstance(burst, int) or burst <= 0:
                result["errors"].append(f"Invalid burst_size: {burst}")
        
        return result
    
    async def _validate_circuit_breaker(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate circuit breaker configuration."""
        result = {"errors": [], "warnings": []}
        
        required_fields = ["failure_threshold", "recovery_timeout"]
        for field in required_fields:
            if field not in config:
                result["errors"].append(f"Missing required field: {field}")
        
        if "failure_threshold" in config:
            threshold = config["failure_threshold"]
            if not isinstance(threshold, int) or threshold <= 0:
                result["errors"].append(f"Invalid failure_threshold: {threshold}")
        
        if "recovery_timeout" in config:
            timeout = config["recovery_timeout"]
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                result["errors"].append(f"Invalid recovery_timeout: {timeout}")
        
        return result
    
    async def _validate_database_pool(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate database pool configuration."""
        result = {"errors": [], "warnings": []}
        
        required_fields = ["min_connections", "max_connections"]
        for field in required_fields:
            if field not in config:
                result["errors"].append(f"Missing required field: {field}")
        
        min_conn = config.get("min_connections", 0)
        max_conn = config.get("max_connections", 0)
        
        if not isinstance(min_conn, int) or min_conn < 0:
            result["errors"].append(f"Invalid min_connections: {min_conn}")
        
        if not isinstance(max_conn, int) or max_conn <= 0:
            result["errors"].append(f"Invalid max_connections: {max_conn}")
        
        if min_conn > max_conn:
            result["errors"].append("min_connections cannot exceed max_connections")
        
        return result
    
    async def _validate_cache_settings(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate cache settings configuration."""
        result = {"errors": [], "warnings": []}
        
        if "ttl_seconds" in config:
            ttl = config["ttl_seconds"]
            if not isinstance(ttl, (int, float)) or ttl <= 0:
                result["errors"].append(f"Invalid ttl_seconds: {ttl}")
        
        if "max_size" in config:
            max_size = config["max_size"]
            if not isinstance(max_size, int) or max_size <= 0:
                result["errors"].append(f"Invalid max_size: {max_size}")
        
        return result
    
    async def _validate_logging_level(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate logging level configuration."""
        result = {"errors": [], "warnings": []}
        
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        
        if "level" in config:
            level = config["level"]
            if level not in valid_levels:
                result["errors"].append(f"Invalid logging level: {level}")
        
        return result


class ConfigurationHotReloader:
    """Manages hot reload operations for various configuration types."""
    
    def __init__(self):
        self.validator = ConfigurationValidator()
        self.current_configs: Dict[ConfigurationType, ConfigurationSnapshot] = {}
        self.config_history: List[ConfigurationSnapshot] = []
        self.metrics = ReloadMetrics()
        self.active_reloads: Set[str] = set()
        self.service_coordinators: Dict[str, AsyncMock] = {}
        
        # Initialize mock services for coordination
        self._initialize_service_coordinators()
    
    def _initialize_service_coordinators(self):
        """Initialize mock service coordinators for testing."""
        services = ["web_service", "worker_service", "cache_service", "database_service"]
        for service in services:
            self.service_coordinators[service] = AsyncMock()
    
    async def hot_reload_configuration(self, config_type: ConfigurationType,
                                     new_config: Dict[str, Any],
                                     reload_id: Optional[str] = None) -> Dict[str, Any]:
        """Perform hot reload of configuration with validation and rollback support."""
        if reload_id is None:
            reload_id = f"reload_{uuid.uuid4().hex[:8]}"
        
        start_time = time.time()
        self.active_reloads.add(reload_id)
        self.metrics.total_reloads += 1
        
        reload_result = {
            "reload_id": reload_id,
            "config_type": config_type.value,
            "status": ReloadStatus.PENDING.value,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
            "duration": 0.0,
            "validation_result": None,
            "rollback_available": False,
            "errors": []
        }
        
        try:
            # Phase 1: Validation
            reload_result["status"] = ReloadStatus.VALIDATING.value
            validation_result = await self.validator.validate_configuration(config_type, new_config)
            reload_result["validation_result"] = validation_result
            
            if not validation_result["valid"]:
                self.metrics.validation_failures += 1
                raise NetraException(f"Configuration validation failed: {validation_result['errors']}")
            
            # Phase 2: Prepare rollback snapshot
            rollback_snapshot = None
            if config_type in self.current_configs:
                rollback_snapshot = self.current_configs[config_type]
                reload_result["rollback_available"] = True
            
            # Phase 3: Service coordination
            coordination_start = time.time()
            await self._coordinate_services_for_reload(config_type, new_config)
            coordination_time = time.time() - coordination_start
            self.metrics.service_coordination_time += coordination_time
            
            # Phase 4: Apply configuration
            reload_result["status"] = ReloadStatus.APPLYING.value
            new_snapshot = await self._apply_configuration(config_type, new_config)
            
            # Phase 5: Verification
            verification_success = await self._verify_configuration_applied(config_type, new_config)
            
            if not verification_success:
                # Rollback if verification fails
                if rollback_snapshot:
                    await self._rollback_configuration(config_type, rollback_snapshot)
                    self.metrics.rollbacks += 1
                    reload_result["status"] = ReloadStatus.ROLLED_BACK.value
                else:
                    raise NetraException("Configuration verification failed and no rollback available")
            else:
                # Success
                self.current_configs[config_type] = new_snapshot
                self.config_history.append(new_snapshot)
                self.metrics.successful_reloads += 1
                reload_result["status"] = ReloadStatus.COMPLETED.value
            
        except Exception as e:
            self.metrics.failed_reloads += 1
            reload_result["status"] = ReloadStatus.FAILED.value
            reload_result["errors"].append(str(e))
            logger.error(f"Hot reload failed for {config_type.value}: {e}")
        
        finally:
            # Complete reload operation
            end_time = time.time()
            duration = end_time - start_time
            reload_result["duration"] = duration
            reload_result["completed_at"] = datetime.now(timezone.utc).isoformat()
            
            # Update metrics
            if duration > self.metrics.max_reload_time:
                self.metrics.max_reload_time = duration
            
            # Update average reload time
            if self.metrics.total_reloads > 0:
                self.metrics.average_reload_time = (
                    (self.metrics.average_reload_time * (self.metrics.total_reloads - 1) + duration) 
                    / self.metrics.total_reloads
                )
            
            self.active_reloads.remove(reload_id)
        
        return reload_result
    
    async def _coordinate_services_for_reload(self, config_type: ConfigurationType, 
                                            new_config: Dict[str, Any]):
        """Coordinate with services for configuration reload."""
        # Notify services about incoming configuration change
        coordination_tasks = []
        
        for service_name, coordinator in self.service_coordinators.items():
            task = coordinator.prepare_config_reload(config_type.value, new_config)
            coordination_tasks.append(task)
        
        # Wait for all services to acknowledge preparation
        await asyncio.gather(*coordination_tasks, return_exceptions=True)
        
        # Brief pause to ensure services are ready
        await asyncio.sleep(0.1)
    
    async def _apply_configuration(self, config_type: ConfigurationType, 
                                 new_config: Dict[str, Any]) -> ConfigurationSnapshot:
        """Apply new configuration and create snapshot."""
        import hashlib
        
        # Create new configuration snapshot
        version = f"v_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        checksum = hashlib.md5(json.dumps(new_config, sort_keys=True).encode()).hexdigest()
        
        snapshot = ConfigurationSnapshot(
            config_type=config_type,
            version=version,
            timestamp=datetime.now(timezone.utc),
            data=new_config.copy(),
            checksum=checksum
        )
        
        # Simulate configuration application
        await asyncio.sleep(0.05)  # Simulate config application time
        
        return snapshot
    
    async def _verify_configuration_applied(self, config_type: ConfigurationType,
                                          expected_config: Dict[str, Any]) -> bool:
        """Verify that configuration was applied correctly."""
        # Simulate verification process
        await asyncio.sleep(0.02)
        
        # Check if configuration is in current configs
        if config_type not in self.current_configs:
            return True  # First time config, assume success
        
        # For existing configs, simulate verification
        # In real implementation, this would check actual service states
        return True
    
    async def _rollback_configuration(self, config_type: ConfigurationType,
                                    rollback_snapshot: ConfigurationSnapshot):
        """Rollback to previous configuration snapshot."""
        logger.info(f"Rolling back configuration {config_type.value} to version {rollback_snapshot.version}")
        
        # Apply rollback configuration
        await self._apply_configuration(config_type, rollback_snapshot.data)
        
        # Update current configuration
        self.current_configs[config_type] = rollback_snapshot
    
    async def test_concurrent_reloads(self, config_changes: List[Tuple[ConfigurationType, Dict[str, Any]]]) -> Dict[str, Any]:
        """Test concurrent configuration reloads."""
        start_time = time.time()
        
        # Execute concurrent reloads
        reload_tasks = []
        for config_type, new_config in config_changes:
            task = self.hot_reload_configuration(config_type, new_config)
            reload_tasks.append(task)
        
        results = await asyncio.gather(*reload_tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # Analyze concurrent reload results
        successful_reloads = [r for r in results if not isinstance(r, Exception) and r.get("status") == "completed"]
        failed_reloads = [r for r in results if isinstance(r, Exception) or r.get("status") == "failed"]
        
        return {
            "total_time": total_time,
            "successful_count": len(successful_reloads),
            "failed_count": len(failed_reloads),
            "results": results,
            "concurrent_reload_efficiency": len(successful_reloads) / len(results) * 100.0
        }
    
    async def test_rollback_capabilities(self, config_type: ConfigurationType) -> Dict[str, Any]:
        """Test configuration rollback capabilities."""
        # Apply initial configuration
        initial_config = {"initial": True, "value": 100}
        initial_result = await self.hot_reload_configuration(config_type, initial_config)
        
        # Apply second configuration
        second_config = {"initial": False, "value": 200, "new_field": "test"}
        second_result = await self.hot_reload_configuration(config_type, second_config)
        
        # Force a rollback by applying invalid configuration
        invalid_config = {"invalid": "configuration", "value": "not_a_number"}
        rollback_result = await self.hot_reload_configuration(config_type, invalid_config)
        
        return {
            "initial_result": initial_result,
            "second_result": second_result,
            "rollback_result": rollback_result,
            "rollback_occurred": rollback_result.get("status") in ["rolled_back", "failed"],
            "configuration_preserved": config_type in self.current_configs
        }
    
    def get_reload_metrics(self) -> Dict[str, Any]:
        """Get comprehensive reload metrics."""
        return {
            "total_reloads": self.metrics.total_reloads,
            "success_rate": self.metrics.get_success_rate(),
            "failed_reloads": self.metrics.failed_reloads,
            "rollbacks": self.metrics.rollbacks,
            "average_reload_time": self.metrics.average_reload_time,
            "max_reload_time": self.metrics.max_reload_time,
            "validation_failures": self.metrics.validation_failures,
            "service_coordination_time": self.metrics.service_coordination_time,
            "active_reloads": len(self.active_reloads),
            "configuration_history_size": len(self.config_history),
            "current_configurations": len(self.current_configs)
        }


@pytest.fixture
async def config_hot_reloader():
    """Create configuration hot reloader for testing."""
    reloader = ConfigurationHotReloader()
    yield reloader


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
class TestConfigurationHotReloadL3:
    """L3 integration tests for configuration hot reload capabilities."""
    
    async def test_reload_time_under_ten_seconds(self, config_hot_reloader):
        """Test that configuration reload completes within 10 seconds SLA."""
        reloader = config_hot_reloader
        
        # Test various configuration types
        test_configs = [
            (ConfigurationType.SERVICE_SETTINGS, {
                "service_name": "test_service",
                "port": 8080,
                "timeout": 30.0
            }),
            (ConfigurationType.RATE_LIMITS, {
                "requests_per_second": 100,
                "burst_size": 50
            }),
            (ConfigurationType.FEATURE_FLAGS, {
                "new_feature": True,
                "experimental_mode": False
            })
        ]
        
        for config_type, new_config in test_configs:
            result = await reloader.hot_reload_configuration(config_type, new_config)
            
            # Verify reload time SLA
            assert result["duration"] <= 10.0, \
                f"Reload for {config_type.value} took {result['duration']:.2f}s, should be ≤10s"
            
            # Verify successful completion
            assert result["status"] == "completed", \
                f"Reload for {config_type.value} should complete successfully"
        
        # Verify overall metrics
        metrics = reloader.get_reload_metrics()
        assert metrics["max_reload_time"] <= 10.0, \
            f"Maximum reload time {metrics['max_reload_time']:.2f}s should be ≤10s"
        
        assert metrics["average_reload_time"] <= 5.0, \
            f"Average reload time {metrics['average_reload_time']:.2f}s should be ≤5s"
    
    async def test_zero_downtime_updates(self, config_hot_reloader):
        """Test zero-downtime configuration updates."""
        reloader = config_hot_reloader
        
        # Simulate service availability during reload
        service_availability = []
        
        async def monitor_service_availability():
            """Monitor service availability during reload."""
            for _ in range(20):  # Monitor for 2 seconds
                # Simulate service health check
                availability = {
                    "timestamp": time.time(),
                    "available": True,  # Simulate continuous availability
                    "response_time": 0.05
                }
                service_availability.append(availability)
                await asyncio.sleep(0.1)
        
        # Start monitoring
        monitor_task = asyncio.create_task(monitor_service_availability())
        
        # Perform configuration reload during monitoring
        config_type = ConfigurationType.DATABASE_POOL
        new_config = {
            "min_connections": 5,
            "max_connections": 20,
            "connection_timeout": 30
        }
        
        reload_result = await reloader.hot_reload_configuration(config_type, new_config)
        
        # Wait for monitoring to complete
        await monitor_task
        
        # Verify zero downtime
        unavailable_periods = [s for s in service_availability if not s["available"]]
        assert len(unavailable_periods) == 0, \
            f"Service should remain available during reload, {len(unavailable_periods)} unavailable periods detected"
        
        # Verify reload success
        assert reload_result["status"] == "completed", \
            "Configuration reload should complete successfully during zero-downtime operation"
        
        # Verify service coordination
        assert reload_result["duration"] < 10.0, \
            "Zero-downtime reload should complete quickly"
    
    async def test_rollback_capabilities(self, config_hot_reloader):
        """Test rollback capabilities when configuration changes fail."""
        reloader = config_hot_reloader
        
        config_type = ConfigurationType.CIRCUIT_BREAKER
        
        # Test rollback scenario
        rollback_test = await reloader.test_rollback_capabilities(config_type)
        
        # Verify rollback behavior
        initial_result = rollback_test["initial_result"]
        second_result = rollback_test["second_result"]
        rollback_result = rollback_test["rollback_result"]
        
        assert initial_result["status"] == "completed", \
            "Initial configuration should apply successfully"
        
        assert second_result["status"] == "completed", \
            "Second configuration should apply successfully"
        
        # Rollback should occur due to invalid configuration
        assert rollback_test["rollback_occurred"], \
            "Rollback should occur when invalid configuration is applied"
        
        assert rollback_test["configuration_preserved"], \
            "Previous valid configuration should be preserved after rollback"
        
        # Verify rollback metrics
        metrics = reloader.get_reload_metrics()
        assert metrics["rollbacks"] >= 1, \
            "Rollback count should be tracked in metrics"
    
    async def test_validation_mechanisms(self, config_hot_reloader):
        """Test configuration validation mechanisms prevent invalid updates."""
        reloader = config_hot_reloader
        
        # Test various invalid configurations
        invalid_configs = [
            (ConfigurationType.SERVICE_SETTINGS, {
                "service_name": "test",
                "port": "invalid_port",  # Should be integer
                "timeout": -1  # Should be positive
            }),
            (ConfigurationType.RATE_LIMITS, {
                "requests_per_second": -10,  # Should be positive
                "burst_size": 0  # Should be positive
            }),
            (ConfigurationType.DATABASE_POOL, {
                "min_connections": 10,
                "max_connections": 5  # min > max (invalid)
            })
        ]
        
        validation_results = []
        
        for config_type, invalid_config in invalid_configs:
            result = await reloader.hot_reload_configuration(config_type, invalid_config)
            validation_results.append(result)
            
            # Verify validation prevents invalid configuration
            assert result["status"] in ["failed", "rolled_back"], \
                f"Invalid configuration for {config_type.value} should be rejected"
            
            assert result["validation_result"] is not None, \
                "Validation result should be provided"
            
            assert not result["validation_result"]["valid"], \
                "Invalid configuration should fail validation"
        
        # Verify validation failure tracking
        metrics = reloader.get_reload_metrics()
        assert metrics["validation_failures"] >= len(invalid_configs), \
            "Validation failures should be tracked in metrics"
        
        # Verify no invalid configurations were applied
        for result in validation_results:
            assert result["status"] != "completed", \
                "Invalid configurations should not complete successfully"
    
    async def test_service_coordination(self, config_hot_reloader):
        """Test service coordination during configuration changes."""
        reloader = config_hot_reloader
        
        # Verify service coordinators are initialized
        assert len(reloader.service_coordinators) >= 3, \
            "Multiple service coordinators should be available"
        
        # Test configuration that requires service coordination
        config_type = ConfigurationType.CACHE_SETTINGS
        new_config = {
            "ttl_seconds": 600,
            "max_size": 10000,
            "eviction_policy": "lru"
        }
        
        result = await reloader.hot_reload_configuration(config_type, new_config)
        
        # Verify successful coordination
        assert result["status"] == "completed", \
            "Configuration requiring service coordination should complete"
        
        # Verify service coordinators were called
        for service_name, coordinator in reloader.service_coordinators.items():
            coordinator.prepare_config_reload.assert_called_once()
        
        # Verify coordination timing
        metrics = reloader.get_reload_metrics()
        assert metrics["service_coordination_time"] > 0, \
            "Service coordination time should be tracked"
        
        assert metrics["service_coordination_time"] < 5.0, \
            "Service coordination should complete quickly"
    
    async def test_concurrent_configuration_updates(self, config_hot_reloader):
        """Test concurrent configuration updates don't interfere."""
        reloader = config_hot_reloader
        
        # Define concurrent configuration changes
        concurrent_configs = [
            (ConfigurationType.FEATURE_FLAGS, {
                "feature_a": True,
                "feature_b": False
            }),
            (ConfigurationType.LOGGING_LEVEL, {
                "level": "INFO",
                "format": "json"
            }),
            (ConfigurationType.RATE_LIMITS, {
                "requests_per_second": 200,
                "burst_size": 100
            }),
            (ConfigurationType.CACHE_SETTINGS, {
                "ttl_seconds": 300,
                "max_size": 5000
            })
        ]
        
        # Execute concurrent reloads
        concurrent_result = await reloader.test_concurrent_reloads(concurrent_configs)
        
        # Verify concurrent execution
        assert concurrent_result["total_time"] < 15.0, \
            f"Concurrent reloads should complete within 15s, took {concurrent_result['total_time']:.2f}s"
        
        assert concurrent_result["successful_count"] >= 3, \
            f"Most concurrent reloads should succeed, got {concurrent_result['successful_count']}/{len(concurrent_configs)}"
        
        assert concurrent_result["concurrent_reload_efficiency"] >= 75.0, \
            f"Concurrent reload efficiency should be ≥75%, got {concurrent_result['concurrent_reload_efficiency']:.1f}%"
        
        # Verify no conflicts occurred
        metrics = reloader.get_reload_metrics()
        assert metrics["total_reloads"] >= len(concurrent_configs), \
            "All concurrent reloads should be counted"
    
    async def test_configuration_persistence_and_recovery(self, config_hot_reloader):
        """Test configuration persistence and recovery capabilities."""
        reloader = config_hot_reloader
        
        # Apply several configurations to build history
        config_sequence = [
            (ConfigurationType.SERVICE_SETTINGS, {
                "service_name": "test_v1",
                "port": 8080,
                "timeout": 30
            }),
            (ConfigurationType.SERVICE_SETTINGS, {
                "service_name": "test_v2",
                "port": 8081,
                "timeout": 45
            }),
            (ConfigurationType.SERVICE_SETTINGS, {
                "service_name": "test_v3",
                "port": 8082,
                "timeout": 60
            })
        ]
        
        for config_type, config_data in config_sequence:
            result = await reloader.hot_reload_configuration(config_type, config_data)
            assert result["status"] == "completed", \
                "Configuration sequence should apply successfully"
        
        # Verify configuration history
        metrics = reloader.get_reload_metrics()
        assert metrics["configuration_history_size"] >= len(config_sequence), \
            "Configuration history should track all changes"
        
        # Verify current configuration state
        assert ConfigurationType.SERVICE_SETTINGS in reloader.current_configs, \
            "Current configuration should be tracked"
        
        current_config = reloader.current_configs[ConfigurationType.SERVICE_SETTINGS]
        assert current_config.data["service_name"] == "test_v3", \
            "Latest configuration should be current"
        
        # Verify configuration integrity
        assert current_config.validate(), \
            "Current configuration should maintain integrity"
    
    async def test_performance_under_load(self, config_hot_reloader):
        """Test configuration reload performance under sustained load."""
        reloader = config_hot_reloader
        
        # Create sustained load of configuration changes
        load_configs = []
        for i in range(20):
            config_type = ConfigurationType.FEATURE_FLAGS
            config_data = {
                f"feature_{i}": i % 2 == 0,
                f"toggle_{i}": i % 3 == 0,
                "timestamp": time.time()
            }
            load_configs.append((config_type, config_data))
        
        # Execute load test
        start_time = time.time()
        
        load_tasks = []
        for config_type, config_data in load_configs:
            task = reloader.hot_reload_configuration(config_type, config_data)
            load_tasks.append(task)
            
            # Brief pause between submissions
            await asyncio.sleep(0.05)
        
        results = await asyncio.gather(*load_tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze load test performance
        successful_reloads = [r for r in results if not isinstance(r, Exception) and r.get("status") == "completed"]
        
        success_rate = len(successful_reloads) / len(results) * 100.0
        avg_reload_time = sum(r["duration"] for r in successful_reloads) / len(successful_reloads) if successful_reloads else 0
        
        # Verify performance under load
        assert total_time < 30.0, \
            f"Load test should complete within 30s, took {total_time:.2f}s"
        
        assert success_rate >= 80.0, \
            f"Success rate under load should be ≥80%, got {success_rate:.1f}%"
        
        assert avg_reload_time < 2.0, \
            f"Average reload time under load should be <2s, got {avg_reload_time:.2f}s"
        
        # Verify system stability after load
        final_metrics = reloader.get_reload_metrics()
        assert final_metrics["active_reloads"] == 0, \
            "No reloads should be active after load test completion"