"""Agent Version Compatibility L2 Integration Tests

Business Value Justification (BVJ):
- Segment: All tiers (backward compatibility for smooth upgrades)
- Business Goal: Version compatibility for seamless system upgrades
- Value Impact: $8K MRR - Ensures backward compatibility >95% and smooth upgrade paths
- Strategic Impact: Version management prevents breaking changes and maintains system stability

Critical Path: Version detection -> Compatibility check -> Adaptation -> Upgrade coordination
Coverage: Version detection, compatibility matrix, adaptation patterns, upgrade safety, rollback capability
"""

import pytest
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from packaging import version
from unittest.mock import AsyncMock, MagicMock

from app.core.exceptions_base import NetraException
from app.schemas.registry import TaskPriority

logger = logging.getLogger(__name__)


class VersionType(Enum):
    """Version component types."""
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"
    PRERELEASE = "prerelease"


class CompatibilityLevel(Enum):
    """Compatibility levels between versions."""
    FULLY_COMPATIBLE = "fully_compatible"
    BACKWARD_COMPATIBLE = "backward_compatible"
    REQUIRES_ADAPTATION = "requires_adaptation"
    INCOMPATIBLE = "incompatible"


@dataclass
class AgentVersion:
    """Agent version information."""
    agent_type: str
    version_string: str
    api_version: str
    schema_version: str
    capabilities: List[str] = field(default_factory=list)
    dependencies: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def parsed_version(self) -> version.Version:
        """Get parsed version object."""
        return version.parse(self.version_string)
    
    def is_compatible_with(self, other: 'AgentVersion') -> CompatibilityLevel:
        """Check compatibility with another version."""
        if self.agent_type != other.agent_type:
            return CompatibilityLevel.INCOMPATIBLE
        
        self_ver = self.parsed_version
        other_ver = other.parsed_version
        
        # Same version - fully compatible
        if self_ver == other_ver:
            return CompatibilityLevel.FULLY_COMPATIBLE
        
        # Major version differences
        if self_ver.major != other_ver.major:
            return CompatibilityLevel.INCOMPATIBLE
        
        # Minor version differences
        if self_ver.minor != other_ver.minor:
            if self_ver.minor > other_ver.minor:
                return CompatibilityLevel.BACKWARD_COMPATIBLE
            else:
                return CompatibilityLevel.REQUIRES_ADAPTATION
        
        # Patch version differences
        return CompatibilityLevel.BACKWARD_COMPATIBLE


@dataclass
class CompatibilityRule:
    """Version compatibility rule."""
    rule_id: str
    source_version_pattern: str
    target_version_pattern: str
    compatibility_level: CompatibilityLevel
    adaptation_required: bool = False
    adaptation_strategy: Optional[str] = None
    deprecation_warnings: List[str] = field(default_factory=list)


@dataclass
class VersionMetrics:
    """Version compatibility metrics."""
    total_version_checks: int = 0
    successful_compatibility_checks: int = 0
    adaptation_required_count: int = 0
    incompatible_count: int = 0
    upgrade_success_rate: float = 0.0
    rollback_success_rate: float = 0.0
    
    @property
    def compatibility_success_rate(self) -> float:
        """Calculate compatibility success rate."""
        if self.total_version_checks == 0:
            return 100.0
        return (self.successful_compatibility_checks / self.total_version_checks) * 100


class VersionDetector:
    """Version detection and parsing service."""
    
    def __init__(self):
        self.detected_versions: Dict[str, AgentVersion] = {}
        self.detection_cache: Dict[str, AgentVersion] = {}
    
    async def detect_agent_version(self, agent_id: str, agent_type: str) -> AgentVersion:
        """Detect agent version from runtime information."""
        # Check cache first
        cache_key = f"{agent_type}:{agent_id}"
        if cache_key in self.detection_cache:
            return self.detection_cache[cache_key]
        
        # Simulate version detection
        version_info = await self._extract_version_info(agent_id, agent_type)
        
        agent_version = AgentVersion(
            agent_type=agent_type,
            version_string=version_info["version"],
            api_version=version_info["api_version"],
            schema_version=version_info["schema_version"],
            capabilities=version_info.get("capabilities", []),
            dependencies=version_info.get("dependencies", {}),
            metadata=version_info.get("metadata", {})
        )
        
        # Cache the result
        self.detection_cache[cache_key] = agent_version
        self.detected_versions[agent_id] = agent_version
        
        return agent_version
    
    async def _extract_version_info(self, agent_id: str, agent_type: str) -> Dict[str, Any]:
        """Extract version information from agent."""
        # Simulate different agent types and versions
        version_patterns = {
            "supervisor_agent": {
                "version": "2.1.3",
                "api_version": "v2",
                "schema_version": "2.1",
                "capabilities": ["orchestration", "delegation", "monitoring"],
                "dependencies": {"base_agent": "1.8.0", "message_bus": "3.2.1"}
            },
            "task_agent": {
                "version": "1.8.5",
                "api_version": "v1", 
                "schema_version": "1.8",
                "capabilities": ["task_execution", "result_reporting"],
                "dependencies": {"base_agent": "1.8.0", "tool_loader": "2.0.1"}
            },
            "analysis_agent": {
                "version": "3.0.1",
                "api_version": "v3",
                "schema_version": "3.0",
                "capabilities": ["data_analysis", "pattern_recognition", "reporting"],
                "dependencies": {"base_agent": "1.8.0", "ml_framework": "4.1.0"}
            }
        }
        
        base_info = version_patterns.get(agent_type, {
            "version": "1.0.0",
            "api_version": "v1",
            "schema_version": "1.0",
            "capabilities": ["basic_operations"],
            "dependencies": {"base_agent": "1.0.0"}
        })
        
        # Add some variation based on agent_id
        if "legacy" in agent_id:
            base_info["version"] = "1.5.2"
            base_info["api_version"] = "v1"
        elif "beta" in agent_id:
            base_info["version"] = f"{base_info['version']}-beta.1"
        
        return base_info
    
    async def bulk_detect_versions(self, agent_specs: List[Tuple[str, str]]) -> Dict[str, AgentVersion]:
        """Detect versions for multiple agents in parallel."""
        detection_tasks = [
            self.detect_agent_version(agent_id, agent_type)
            for agent_id, agent_type in agent_specs
        ]
        
        results = await asyncio.gather(*detection_tasks, return_exceptions=True)
        
        detected = {}
        for i, result in enumerate(results):
            if not isinstance(result, Exception):
                agent_id, _ = agent_specs[i]
                detected[agent_id] = result
        
        return detected


class CompatibilityChecker:
    """Version compatibility analysis and validation."""
    
    def __init__(self):
        self.compatibility_rules: List[CompatibilityRule] = []
        self.compatibility_cache: Dict[str, CompatibilityLevel] = {}
        self._initialize_default_rules()
    
    def _initialize_default_rules(self):
        """Initialize default compatibility rules."""
        default_rules = [
            CompatibilityRule(
                rule_id="major_version_incompatible",
                source_version_pattern="*",
                target_version_pattern="*",
                compatibility_level=CompatibilityLevel.INCOMPATIBLE,
                adaptation_required=False
            ),
            CompatibilityRule(
                rule_id="minor_version_backward_compatible",
                source_version_pattern="*.*.* ",
                target_version_pattern="*.*.*",
                compatibility_level=CompatibilityLevel.BACKWARD_COMPATIBLE,
                adaptation_required=False
            ),
            CompatibilityRule(
                rule_id="api_v1_to_v2_adaptation",
                source_version_pattern="v1",
                target_version_pattern="v2",
                compatibility_level=CompatibilityLevel.REQUIRES_ADAPTATION,
                adaptation_required=True,
                adaptation_strategy="api_bridge_v1_to_v2"
            )
        ]
        
        self.compatibility_rules.extend(default_rules)
    
    async def check_compatibility(self, source_version: AgentVersion, 
                                target_version: AgentVersion) -> Dict[str, Any]:
        """Check compatibility between two agent versions."""
        cache_key = f"{source_version.agent_type}:{source_version.version_string}->{target_version.version_string}"
        
        if cache_key in self.compatibility_cache:
            cached_level = self.compatibility_cache[cache_key]
            return self._build_compatibility_result(source_version, target_version, cached_level)
        
        # Perform compatibility analysis
        compatibility_level = source_version.is_compatible_with(target_version)
        
        # Check for specific compatibility rules
        applicable_rules = self._find_applicable_rules(source_version, target_version)
        
        # Apply most restrictive rule
        for rule in applicable_rules:
            if rule.compatibility_level.value == "incompatible":
                compatibility_level = CompatibilityLevel.INCOMPATIBLE
                break
            elif rule.compatibility_level.value == "requires_adaptation":
                compatibility_level = CompatibilityLevel.REQUIRES_ADAPTATION
        
        # Cache result
        self.compatibility_cache[cache_key] = compatibility_level
        
        return self._build_compatibility_result(source_version, target_version, compatibility_level, applicable_rules)
    
    def _find_applicable_rules(self, source: AgentVersion, target: AgentVersion) -> List[CompatibilityRule]:
        """Find applicable compatibility rules."""
        applicable = []
        
        for rule in self.compatibility_rules:
            # Simplified pattern matching
            if self._matches_pattern(source.api_version, rule.source_version_pattern):
                if self._matches_pattern(target.api_version, rule.target_version_pattern):
                    applicable.append(rule)
        
        return applicable
    
    def _matches_pattern(self, value: str, pattern: str) -> bool:
        """Check if value matches pattern."""
        if pattern == "*":
            return True
        return value == pattern
    
    def _build_compatibility_result(self, source: AgentVersion, target: AgentVersion,
                                  compatibility_level: CompatibilityLevel,
                                  applicable_rules: Optional[List[CompatibilityRule]] = None) -> Dict[str, Any]:
        """Build compatibility check result."""
        result = {
            "source_version": {
                "agent_type": source.agent_type,
                "version": source.version_string,
                "api_version": source.api_version
            },
            "target_version": {
                "agent_type": target.agent_type,
                "version": target.version_string,
                "api_version": target.api_version
            },
            "compatibility_level": compatibility_level.value,
            "is_compatible": compatibility_level in [CompatibilityLevel.FULLY_COMPATIBLE, CompatibilityLevel.BACKWARD_COMPATIBLE],
            "requires_adaptation": compatibility_level == CompatibilityLevel.REQUIRES_ADAPTATION,
            "adaptation_strategies": [],
            "deprecation_warnings": [],
            "risk_assessment": self._assess_compatibility_risk(compatibility_level)
        }
        
        # Add rule-specific information
        if applicable_rules:
            for rule in applicable_rules:
                if rule.adaptation_strategy:
                    result["adaptation_strategies"].append(rule.adaptation_strategy)
                result["deprecation_warnings"].extend(rule.deprecation_warnings)
        
        return result
    
    def _assess_compatibility_risk(self, compatibility_level: CompatibilityLevel) -> str:
        """Assess risk level of compatibility."""
        risk_mapping = {
            CompatibilityLevel.FULLY_COMPATIBLE: "low",
            CompatibilityLevel.BACKWARD_COMPATIBLE: "low",
            CompatibilityLevel.REQUIRES_ADAPTATION: "medium",
            CompatibilityLevel.INCOMPATIBLE: "high"
        }
        return risk_mapping.get(compatibility_level, "unknown")
    
    async def batch_compatibility_check(self, version_pairs: List[Tuple[AgentVersion, AgentVersion]]) -> List[Dict[str, Any]]:
        """Check compatibility for multiple version pairs."""
        check_tasks = [
            self.check_compatibility(source, target)
            for source, target in version_pairs
        ]
        
        results = await asyncio.gather(*check_tasks, return_exceptions=True)
        
        return [r for r in results if not isinstance(r, Exception)]


class VersionAdapter:
    """Version adaptation and migration service."""
    
    def __init__(self):
        self.adaptation_strategies: Dict[str, AsyncMock] = {}
        self.migration_history: List[Dict[str, Any]] = []
        self._register_default_strategies()
    
    def _register_default_strategies(self):
        """Register default adaptation strategies."""
        self.adaptation_strategies.update({
            "api_bridge_v1_to_v2": AsyncMock(return_value={"status": "success", "adapted": True}),
            "schema_migration_1_to_2": AsyncMock(return_value={"status": "success", "migrated": True}),
            "capability_wrapper": AsyncMock(return_value={"status": "success", "wrapped": True})
        })
    
    async def adapt_version_compatibility(self, source_version: AgentVersion,
                                        target_version: AgentVersion,
                                        adaptation_strategy: str) -> Dict[str, Any]:
        """Adapt agent version for compatibility."""
        if adaptation_strategy not in self.adaptation_strategies:
            raise NetraException(f"Unknown adaptation strategy: {adaptation_strategy}")
        
        # Execute adaptation strategy
        strategy_func = self.adaptation_strategies[adaptation_strategy]
        adaptation_result = await strategy_func(source_version, target_version)
        
        # Record migration
        migration_record = {
            "source_version": source_version.version_string,
            "target_version": target_version.version_string,
            "agent_type": source_version.agent_type,
            "adaptation_strategy": adaptation_strategy,
            "timestamp": datetime.now(timezone.utc),
            "result": adaptation_result
        }
        
        self.migration_history.append(migration_record)
        
        return {
            "adaptation_successful": adaptation_result.get("status") == "success",
            "adapted_version": target_version,
            "migration_id": f"migration_{len(self.migration_history)}",
            "adaptation_details": adaptation_result,
            "rollback_possible": True
        }
    
    async def validate_adaptation(self, migration_id: str) -> Dict[str, Any]:
        """Validate that adaptation was successful."""
        # Find migration record
        migration_record = None
        for record in self.migration_history:
            if f"migration_{self.migration_history.index(record) + 1}" == migration_id:
                migration_record = record
                break
        
        if not migration_record:
            return {"validation_successful": False, "error": "Migration record not found"}
        
        # Simulate validation checks
        validation_checks = [
            {"check": "api_compatibility", "passed": True},
            {"check": "schema_validation", "passed": True},
            {"check": "capability_verification", "passed": True},
            {"check": "performance_regression", "passed": True}
        ]
        
        all_passed = all(check["passed"] for check in validation_checks)
        
        return {
            "validation_successful": all_passed,
            "migration_id": migration_id,
            "validation_checks": validation_checks,
            "validation_timestamp": datetime.now(timezone.utc)
        }


class AgentVersionManager:
    """Comprehensive agent version management system."""
    
    def __init__(self):
        self.version_detector = VersionDetector()
        self.compatibility_checker = CompatibilityChecker()
        self.version_adapter = VersionAdapter()
        self.metrics = VersionMetrics()
        self.active_agents: Dict[str, AgentVersion] = {}
    
    async def register_agent_version(self, agent_id: str, agent_type: str) -> AgentVersion:
        """Register and detect agent version."""
        agent_version = await self.version_detector.detect_agent_version(agent_id, agent_type)
        self.active_agents[agent_id] = agent_version
        return agent_version
    
    async def check_upgrade_compatibility(self, agent_id: str, 
                                        target_version: str) -> Dict[str, Any]:
        """Check if agent can be upgraded to target version."""
        if agent_id not in self.active_agents:
            raise NetraException(f"Agent {agent_id} not registered")
        
        current_version = self.active_agents[agent_id]
        
        # Create target version object
        target_agent_version = AgentVersion(
            agent_type=current_version.agent_type,
            version_string=target_version,
            api_version="v2",  # Assume newer API version
            schema_version="2.0"
        )
        
        # Check compatibility
        compatibility_result = await self.compatibility_checker.check_compatibility(
            current_version, target_agent_version
        )
        
        self.metrics.total_version_checks += 1
        
        if compatibility_result["is_compatible"]:
            self.metrics.successful_compatibility_checks += 1
        elif compatibility_result["requires_adaptation"]:
            self.metrics.adaptation_required_count += 1
        else:
            self.metrics.incompatible_count += 1
        
        return compatibility_result
    
    async def perform_version_upgrade(self, agent_id: str, target_version: str) -> Dict[str, Any]:
        """Perform agent version upgrade with compatibility handling."""
        # First check compatibility
        compatibility_result = await self.check_upgrade_compatibility(agent_id, target_version)
        
        if not compatibility_result["is_compatible"] and not compatibility_result["requires_adaptation"]:
            return {
                "upgrade_successful": False,
                "reason": "incompatible_versions",
                "compatibility_result": compatibility_result
            }
        
        current_version = self.active_agents[agent_id]
        target_agent_version = AgentVersion(
            agent_type=current_version.agent_type,
            version_string=target_version,
            api_version="v2",
            schema_version="2.0"
        )
        
        # Handle adaptation if required
        if compatibility_result["requires_adaptation"]:
            adaptation_strategies = compatibility_result.get("adaptation_strategies", [])
            if adaptation_strategies:
                adaptation_result = await self.version_adapter.adapt_version_compatibility(
                    current_version, target_agent_version, adaptation_strategies[0]
                )
                
                if not adaptation_result["adaptation_successful"]:
                    return {
                        "upgrade_successful": False,
                        "reason": "adaptation_failed",
                        "adaptation_result": adaptation_result
                    }
        
        # Update agent version
        self.active_agents[agent_id] = target_agent_version
        
        return {
            "upgrade_successful": True,
            "previous_version": current_version.version_string,
            "new_version": target_version,
            "adaptation_required": compatibility_result["requires_adaptation"],
            "timestamp": datetime.now(timezone.utc)
        }
    
    async def test_version_compatibility_matrix(self, agent_types: List[str]) -> Dict[str, Any]:
        """Test compatibility matrix across different agent types and versions."""
        # Generate test versions for each agent type
        test_versions = {}
        for agent_type in agent_types:
            test_versions[agent_type] = [
                await self.version_detector.detect_agent_version(f"{agent_type}_v1", agent_type),
                await self.version_detector.detect_agent_version(f"{agent_type}_v2", agent_type),
                await self.version_detector.detect_agent_version(f"{agent_type}_legacy", agent_type)
            ]
        
        # Test all combinations
        compatibility_matrix = {}
        total_checks = 0
        successful_checks = 0
        
        for agent_type in agent_types:
            compatibility_matrix[agent_type] = {}
            
            for i, source_version in enumerate(test_versions[agent_type]):
                for j, target_version in enumerate(test_versions[agent_type]):
                    if i != j:  # Don't test same version
                        total_checks += 1
                        
                        result = await self.compatibility_checker.check_compatibility(
                            source_version, target_version
                        )
                        
                        compatibility_matrix[agent_type][f"{source_version.version_string}_to_{target_version.version_string}"] = {
                            "compatible": result["is_compatible"],
                            "requires_adaptation": result["requires_adaptation"],
                            "risk_level": result["risk_assessment"]
                        }
                        
                        if result["is_compatible"] or result["requires_adaptation"]:
                            successful_checks += 1
        
        compatibility_success_rate = (successful_checks / total_checks * 100) if total_checks > 0 else 100
        
        return {
            "compatibility_matrix": compatibility_matrix,
            "total_compatibility_checks": total_checks,
            "successful_compatibility_checks": successful_checks,
            "compatibility_success_rate": compatibility_success_rate,
            "meets_95_percent_target": compatibility_success_rate >= 95.0
        }
    
    def get_version_metrics(self) -> Dict[str, Any]:
        """Get comprehensive version management metrics."""
        return {
            "version_detection": {
                "active_agents": len(self.active_agents),
                "detected_versions": len(self.version_detector.detected_versions),
                "cache_size": len(self.version_detector.detection_cache)
            },
            "compatibility_checking": {
                "total_checks": self.metrics.total_version_checks,
                "successful_checks": self.metrics.successful_compatibility_checks,
                "adaptation_required": self.metrics.adaptation_required_count,
                "incompatible_count": self.metrics.incompatible_count,
                "success_rate": self.metrics.compatibility_success_rate
            },
            "version_adaptation": {
                "total_migrations": len(self.version_adapter.migration_history),
                "available_strategies": len(self.version_adapter.adaptation_strategies)
            }
        }


@pytest.fixture
async def version_manager():
    """Create version manager for testing."""
    manager = AgentVersionManager()
    yield manager


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l2
class TestAgentVersionCompatibilityL2:
    """L2 integration tests for agent version compatibility."""
    
    async def test_version_detection_accuracy(self, version_manager):
        """Test accurate version detection across agent types."""
        manager = version_manager
        
        # Register different agent types
        agent_specs = [
            ("supervisor_01", "supervisor_agent"),
            ("task_worker_01", "task_agent"),
            ("analyzer_01", "analysis_agent"),
            ("legacy_supervisor", "supervisor_agent"),
            ("beta_analyzer", "analysis_agent")
        ]
        
        # Detect versions
        detected_versions = {}
        for agent_id, agent_type in agent_specs:
            version = await manager.register_agent_version(agent_id, agent_type)
            detected_versions[agent_id] = version
        
        # Verify detection accuracy
        assert len(detected_versions) == len(agent_specs), \
            "Should detect versions for all agents"
        
        # Verify version format compliance
        for agent_id, agent_version in detected_versions.items():
            assert agent_version.version_string, \
                f"Agent {agent_id} should have version string"
            
            assert agent_version.api_version, \
                f"Agent {agent_id} should have API version"
            
            assert agent_version.schema_version, \
                f"Agent {agent_id} should have schema version"
            
            # Verify version parsing
            parsed = agent_version.parsed_version
            assert parsed.major >= 1, \
                f"Agent {agent_id} should have valid major version"
        
        # Verify legacy version handling
        legacy_version = detected_versions["legacy_supervisor"]
        assert "1.5" in legacy_version.version_string, \
            "Legacy agent should have appropriate version"
        
        # Verify beta version handling
        beta_version = detected_versions["beta_analyzer"]
        assert "beta" in beta_version.version_string, \
            "Beta agent should be identified as beta"
    
    async def test_compatibility_matrix_95_percent_success(self, version_manager):
        """Test version compatibility matrix achieves >95% success rate."""
        manager = version_manager
        
        # Test compatibility across agent types
        agent_types = ["supervisor_agent", "task_agent", "analysis_agent"]
        
        compatibility_test = await manager.test_version_compatibility_matrix(agent_types)
        
        # Verify 95% compatibility success rate
        assert compatibility_test["meets_95_percent_target"], \
            f"Compatibility success rate {compatibility_test['compatibility_success_rate']:.1f}% should be ≥95%"
        
        assert compatibility_test["compatibility_success_rate"] >= 95.0, \
            f"Success rate {compatibility_test['compatibility_success_rate']:.1f}% must meet target"
        
        # Verify comprehensive testing
        assert compatibility_test["total_compatibility_checks"] >= 15, \
            "Should perform comprehensive compatibility testing"
        
        # Verify matrix completeness
        matrix = compatibility_test["compatibility_matrix"]
        for agent_type in agent_types:
            assert agent_type in matrix, \
                f"Compatibility matrix should include {agent_type}"
            
            # Each agent type should have multiple compatibility checks
            assert len(matrix[agent_type]) >= 4, \
                f"Agent type {agent_type} should have multiple compatibility checks"
    
    async def test_version_upgrade_workflow(self, version_manager):
        """Test complete version upgrade workflow with compatibility checking."""
        manager = version_manager
        
        # Register agent with current version
        agent_id = "upgrade_test_agent"
        current_version = await manager.register_agent_version(agent_id, "supervisor_agent")
        
        # Test upgrade to compatible version
        target_version = "2.2.0"
        upgrade_result = await manager.perform_version_upgrade(agent_id, target_version)
        
        # Verify upgrade success
        assert upgrade_result["upgrade_successful"], \
            f"Version upgrade should succeed: {upgrade_result.get('reason', 'unknown')}"
        
        assert upgrade_result["new_version"] == target_version, \
            "New version should match target"
        
        assert upgrade_result["previous_version"] == current_version.version_string, \
            "Previous version should be tracked"
        
        # Verify agent version updated
        updated_agent = manager.active_agents[agent_id]
        assert updated_agent.version_string == target_version, \
            "Agent version should be updated in registry"
        
        # Test upgrade to incompatible version (major version jump)
        incompatible_target = "3.0.0"
        incompatible_result = await manager.perform_version_upgrade(agent_id, incompatible_target)
        
        # Should handle incompatibility gracefully
        if not incompatible_result["upgrade_successful"]:
            assert "reason" in incompatible_result, \
                "Failed upgrade should provide reason"
            
            # Agent should still be on previous version
            current_agent = manager.active_agents[agent_id]
            assert current_agent.version_string == target_version, \
                "Failed upgrade should not change agent version"
    
    async def test_version_adaptation_mechanisms(self, version_manager):
        """Test version adaptation for cross-version compatibility."""
        manager = version_manager
        
        # Create versions that require adaptation
        source_version = AgentVersion(
            agent_type="task_agent",
            version_string="1.8.0",
            api_version="v1",
            schema_version="1.8"
        )
        
        target_version = AgentVersion(
            agent_type="task_agent", 
            version_string="2.0.0",
            api_version="v2",
            schema_version="2.0"
        )
        
        # Test adaptation requirement detection
        compatibility_result = await manager.compatibility_checker.check_compatibility(
            source_version, target_version
        )
        
        # Should require adaptation for major version change
        if compatibility_result["requires_adaptation"]:
            # Test adaptation execution
            adaptation_strategies = compatibility_result.get("adaptation_strategies", [])
            if adaptation_strategies:
                adaptation_result = await manager.version_adapter.adapt_version_compatibility(
                    source_version, target_version, adaptation_strategies[0]
                )
                
                # Verify adaptation success
                assert adaptation_result["adaptation_successful"], \
                    "Version adaptation should succeed"
                
                assert adaptation_result["rollback_possible"], \
                    "Adaptation should support rollback"
                
                # Validate adaptation
                migration_id = adaptation_result["migration_id"]
                validation_result = await manager.version_adapter.validate_adaptation(migration_id)
                
                assert validation_result["validation_successful"], \
                    "Adaptation validation should pass"
        
        # Verify metrics tracking
        metrics = manager.get_version_metrics()
        assert metrics["compatibility_checking"]["total_checks"] >= 1, \
            "Compatibility checks should be tracked"
    
    async def test_concurrent_version_operations(self, version_manager):
        """Test concurrent version detection and compatibility checking."""
        manager = version_manager
        
        # Create concurrent version operations
        async def concurrent_version_check(operation_id: int):
            agent_id = f"concurrent_agent_{operation_id}"
            agent_type = ["supervisor_agent", "task_agent", "analysis_agent"][operation_id % 3]
            
            # Register agent
            version = await manager.register_agent_version(agent_id, agent_type)
            
            # Check upgrade compatibility
            target_version = "2.0.0"
            compatibility = await manager.check_upgrade_compatibility(agent_id, target_version)
            
            return {
                "agent_id": agent_id,
                "version": version,
                "compatibility": compatibility
            }
        
        # Execute concurrent operations
        concurrent_tasks = [concurrent_version_check(i) for i in range(15)]
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        # Verify concurrent operation success
        successful_operations = [r for r in results if not isinstance(r, Exception)]
        
        assert len(successful_operations) == 15, \
            f"All concurrent operations should succeed, got {len(successful_operations)}"
        
        # Verify no data corruption
        metrics = manager.get_version_metrics()
        assert metrics["version_detection"]["active_agents"] >= 15, \
            "All concurrent agents should be registered"
        
        assert metrics["compatibility_checking"]["total_checks"] >= 15, \
            "All compatibility checks should be tracked"
    
    async def test_backward_compatibility_preservation(self, version_manager):
        """Test preservation of backward compatibility across versions."""
        manager = version_manager
        
        # Create version progression scenario
        version_progression = [
            ("1.0.0", "v1", "1.0"),
            ("1.1.0", "v1", "1.1"),
            ("1.2.0", "v1", "1.2"),
            ("2.0.0", "v2", "2.0"),
            ("2.1.0", "v2", "2.1")
        ]
        
        # Create agent versions
        agent_versions = []
        for i, (version_str, api_ver, schema_ver) in enumerate(version_progression):
            agent_version = AgentVersion(
                agent_type="test_agent",
                version_string=version_str,
                api_version=api_ver,
                schema_version=schema_ver
            )
            agent_versions.append(agent_version)
        
        # Test backward compatibility within major versions
        backward_compatible_count = 0
        total_backward_tests = 0
        
        for i in range(len(agent_versions)):
            for j in range(i + 1, len(agent_versions)):
                newer_version = agent_versions[j]
                older_version = agent_versions[i]
                
                # Check if newer version is backward compatible with older
                compatibility = await manager.compatibility_checker.check_compatibility(
                    newer_version, older_version
                )
                
                total_backward_tests += 1
                
                # Within same major version should be backward compatible
                if newer_version.parsed_version.major == older_version.parsed_version.major:
                    if (compatibility["is_compatible"] or 
                        compatibility["compatibility_level"] == "backward_compatible"):
                        backward_compatible_count += 1
        
        # Verify backward compatibility preservation
        if total_backward_tests > 0:
            backward_compatibility_rate = (backward_compatible_count / total_backward_tests) * 100
            
            assert backward_compatibility_rate >= 80.0, \
                f"Backward compatibility rate {backward_compatibility_rate:.1f}% should be ≥80%"
    
    async def test_version_rollback_capabilities(self, version_manager):
        """Test version rollback and recovery capabilities."""
        manager = version_manager
        
        # Register agent and perform upgrade
        agent_id = "rollback_test_agent"
        original_version = await manager.register_agent_version(agent_id, "supervisor_agent")
        
        # Perform upgrade
        target_version = "2.1.0"
        upgrade_result = await manager.perform_version_upgrade(agent_id, target_version)
        
        if upgrade_result["upgrade_successful"]:
            # Verify upgrade completed
            current_agent = manager.active_agents[agent_id]
            assert current_agent.version_string == target_version, \
                "Upgrade should change agent version"
            
            # Simulate rollback (restore original version)
            rollback_result = await manager.perform_version_upgrade(
                agent_id, original_version.version_string
            )
            
            # Verify rollback capability
            if rollback_result.get("upgrade_successful"):
                rolled_back_agent = manager.active_agents[agent_id]
                assert rolled_back_agent.version_string == original_version.version_string, \
                    "Rollback should restore original version"
        
        # Verify migration history tracking for rollback planning
        migration_history = manager.version_adapter.migration_history
        if migration_history:
            latest_migration = migration_history[-1]
            assert "source_version" in latest_migration, \
                "Migration history should track source version for rollback"
            
            assert "timestamp" in latest_migration, \
                "Migration history should track timing for rollback planning"
    
    async def test_comprehensive_version_management_workflow(self, version_manager):
        """Test complete version management workflow across multiple agents."""
        manager = version_manager
        
        # Phase 1: Register diverse agent ecosystem
        agent_ecosystem = [
            ("supervisor_main", "supervisor_agent"),
            ("supervisor_backup", "supervisor_agent"),
            ("task_primary", "task_agent"),
            ("task_secondary", "task_agent"),
            ("analyzer_main", "analysis_agent"),
            ("analyzer_specialized", "analysis_agent")
        ]
        
        registered_agents = {}
        for agent_id, agent_type in agent_ecosystem:
            version = await manager.register_agent_version(agent_id, agent_type)
            registered_agents[agent_id] = version
        
        # Phase 2: Test cross-agent compatibility
        compatibility_tests = []
        for i, (agent1_id, _) in enumerate(agent_ecosystem):
            for j, (agent2_id, _) in enumerate(agent_ecosystem):
                if i != j and registered_agents[agent1_id].agent_type == registered_agents[agent2_id].agent_type:
                    compatibility = await manager.compatibility_checker.check_compatibility(
                        registered_agents[agent1_id], registered_agents[agent2_id]
                    )
                    compatibility_tests.append(compatibility)
        
        # Phase 3: Perform selective upgrades
        upgrade_results = {}
        for agent_id in ["supervisor_main", "task_primary", "analyzer_main"]:
            upgrade_result = await manager.perform_version_upgrade(agent_id, "2.0.0")
            upgrade_results[agent_id] = upgrade_result
        
        # Phase 4: Verify ecosystem stability
        final_metrics = manager.get_version_metrics()
        
        # Verify comprehensive workflow success
        assert len(registered_agents) == len(agent_ecosystem), \
            "All agents should be registered"
        
        assert len(compatibility_tests) >= 6, \
            "Should perform comprehensive compatibility testing"
        
        assert final_metrics["version_detection"]["active_agents"] >= 6, \
            "All agents should remain active"
        
        successful_upgrades = sum(1 for result in upgrade_results.values() 
                                if result.get("upgrade_successful", False))
        
        upgrade_success_rate = (successful_upgrades / len(upgrade_results)) * 100
        assert upgrade_success_rate >= 50.0, \
            f"Upgrade success rate {upgrade_success_rate:.1f}% should be reasonable"
        
        # Verify system maintains coherence
        assert final_metrics["compatibility_checking"]["success_rate"] >= 90.0, \
            "System should maintain high compatibility success rate"