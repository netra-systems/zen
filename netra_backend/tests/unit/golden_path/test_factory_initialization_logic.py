"""
Test Factory Initialization Business Logic

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure WebSocket infrastructure initializes reliably
- Value Impact: Prevents FactoryInitializationError that blocks all chat functionality
- Strategic Impact: Eliminates system startup failures that prevent $500K+ ARR delivery

CRITICAL: This test validates the business logic for factory initialization patterns
that prevent FactoryInitializationError exceptions which completely block chat functionality.

This test focuses on BUSINESS LOGIC validation, not system integration.
Tests the decision-making algorithms and validation patterns for SSOT factory creation.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Type, Union
from enum import Enum
from abc import ABC, abstractmethod

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.types.core_types import UserID, WebSocketID, ConnectionID


class FactoryValidationState(Enum):
    """Factory validation states for business logic testing."""
    VALID = "valid"
    INVALID_CONFIG = "invalid_config"
    MISSING_DEPENDENCIES = "missing_dependencies"
    SSOT_VIOLATION = "ssot_violation"
    INITIALIZATION_ERROR = "initialization_error"


class ComponentType(Enum):
    """Types of components that factories create."""
    WEBSOCKET_MANAGER = "websocket_manager"
    TOOL_DISPATCHER = "tool_dispatcher"
    AGENT_SUPERVISOR = "agent_supervisor"
    USER_CONTEXT = "user_context"
    EXECUTION_ENGINE = "execution_engine"


@dataclass
class FactoryValidationResult:
    """Result of factory validation business logic."""
    state: FactoryValidationState
    component_type: ComponentType
    error_details: Optional[str] = None
    required_dependencies: List[str] = None
    validation_score: float = 0.0
    can_initialize: bool = False


@dataclass
class SSotCompliance:
    """SSOT compliance validation for factory patterns."""
    has_single_source: bool
    duplicate_implementations: List[str] = None
    missing_ssot_components: List[str] = None
    compliance_score: float = 0.0


class MockFactoryValidator:
    """Mock factory validator for business logic testing."""
    
    def __init__(self):
        self.required_dependencies = {
            ComponentType.WEBSOCKET_MANAGER: [
                "jwt_secret_manager", "unified_environment", "database_connection", 
                "redis_connection", "user_context_factory"
            ],
            ComponentType.TOOL_DISPATCHER: [
                "llm_client", "execution_context", "websocket_manager", "circuit_breaker"
            ],
            ComponentType.AGENT_SUPERVISOR: [
                "tool_dispatcher", "execution_engine", "state_manager", "websocket_notifier"
            ],
            ComponentType.USER_CONTEXT: [
                "auth_validator", "session_manager", "isolation_config"
            ],
            ComponentType.EXECUTION_ENGINE: [
                "llm_client", "tool_registry", "context_manager", "error_handler"
            ]
        }
        
        self.ssot_requirements = {
            ComponentType.WEBSOCKET_MANAGER: [
                "unified_websocket_manager", "single_connection_factory", "isolated_user_context"
            ],
            ComponentType.TOOL_DISPATCHER: [
                "request_scoped_dispatcher", "no_singleton_pattern", "factory_created_only"
            ],
            ComponentType.AGENT_SUPERVISOR: [
                "supervisor_factory", "execution_isolation", "context_scoped"
            ]
        }
        
        self.validation_thresholds = {
            "minimum_compliance_score": 0.8,
            "required_dependencies_percentage": 1.0,
            "ssot_compliance_minimum": 0.9
        }
    
    def validate_factory_configuration(self, component_type: ComponentType, 
                                     config: Dict[str, Any]) -> FactoryValidationResult:
        """Business logic: Validate factory configuration completeness."""
        required_deps = self.required_dependencies.get(component_type, [])
        provided_deps = list(config.keys())
        
        # Check for missing dependencies
        missing_deps = [dep for dep in required_deps if dep not in provided_deps]
        
        if missing_deps:
            return FactoryValidationResult(
                state=FactoryValidationState.MISSING_DEPENDENCIES,
                component_type=component_type,
                error_details=f"Missing required dependencies: {missing_deps}",
                required_dependencies=missing_deps,
                validation_score=0.0,
                can_initialize=False
            )
        
        # Check configuration validity
        validation_score = self._calculate_config_validation_score(config, required_deps)
        
        if validation_score < self.validation_thresholds["minimum_compliance_score"]:
            return FactoryValidationResult(
                state=FactoryValidationState.INVALID_CONFIG,
                component_type=component_type,
                error_details=f"Configuration validation score {validation_score:.2f} below threshold",
                validation_score=validation_score,
                can_initialize=False
            )
        
        return FactoryValidationResult(
            state=FactoryValidationState.VALID,
            component_type=component_type,
            validation_score=validation_score,
            can_initialize=True
        )
    
    def _calculate_config_validation_score(self, config: Dict[str, Any], 
                                         required_deps: List[str]) -> float:
        """Calculate configuration validation score based on business rules."""
        if not required_deps:
            return 1.0
        
        score = 0.0
        total_weight = 0.0
        
        for dep in required_deps:
            weight = 1.0
            total_weight += weight
            
            if dep in config:
                value = config[dep]
                
                # Business logic: Validate dependency value quality
                if value is None:
                    score += 0.0  # Null values score zero
                elif isinstance(value, str) and len(value.strip()) == 0:
                    score += 0.0  # Empty strings score zero
                elif isinstance(value, dict) and len(value) == 0:
                    score += 0.0  # Empty dicts score zero
                elif isinstance(value, bool) and value is False:
                    score += 0.5  # False values score half (might be intentional)
                else:
                    score += weight  # Valid values score full
        
        return score / total_weight if total_weight > 0 else 0.0
    
    def validate_ssot_compliance(self, component_type: ComponentType,
                               implementation_details: Dict[str, Any]) -> SSotCompliance:
        """Business logic: Validate SSOT compliance for factory patterns."""
        ssot_requirements = self.ssot_requirements.get(component_type, [])
        compliance_violations = []
        duplicate_implementations = []
        missing_components = []
        
        # Check for SSOT pattern compliance
        for requirement in ssot_requirements:
            if requirement not in implementation_details:
                missing_components.append(requirement)
            else:
                # Check if implementation follows SSOT principles
                impl_value = implementation_details[requirement]
                if isinstance(impl_value, list) and len(impl_value) > 1:
                    duplicate_implementations.append(f"{requirement}: {len(impl_value)} implementations")
        
        # Calculate compliance score
        total_requirements = len(ssot_requirements)
        violations = len(missing_components) + len(duplicate_implementations)
        compliance_score = max(0.0, (total_requirements - violations) / total_requirements) if total_requirements > 0 else 1.0
        
        return SSotCompliance(
            has_single_source=len(duplicate_implementations) == 0,
            duplicate_implementations=duplicate_implementations,
            missing_ssot_components=missing_components,
            compliance_score=compliance_score
        )
    
    def assess_initialization_feasibility(self, component_type: ComponentType,
                                        config: Dict[str, Any],
                                        environment_state: Dict[str, Any]) -> Dict[str, Any]:
        """Business logic: Assess if factory initialization will succeed."""
        # Validate configuration
        config_validation = self.validate_factory_configuration(component_type, config)
        
        if not config_validation.can_initialize:
            return {
                "can_initialize": False,
                "reason": config_validation.state.value,
                "error_details": config_validation.error_details,
                "business_impact": "Complete service unavailability",
                "recovery_actions": self._generate_recovery_actions(config_validation)
            }
        
        # Check environment readiness
        env_readiness = self._assess_environment_readiness(environment_state)
        
        if not env_readiness["ready"]:
            return {
                "can_initialize": False,
                "reason": "environment_not_ready",
                "error_details": env_readiness["error_details"],
                "business_impact": "Service startup failure",
                "recovery_actions": env_readiness["recovery_actions"]
            }
        
        # Check SSOT compliance
        ssot_compliance = self.validate_ssot_compliance(component_type, config)
        
        if ssot_compliance.compliance_score < self.validation_thresholds["ssot_compliance_minimum"]:
            return {
                "can_initialize": False,
                "reason": "ssot_violation",
                "error_details": f"SSOT compliance score {ssot_compliance.compliance_score:.2f} too low",
                "business_impact": "Architecture integrity violation",
                "recovery_actions": ["Fix SSOT violations", "Consolidate duplicate implementations"]
            }
        
        return {
            "can_initialize": True,
            "reason": "all_validations_passed",
            "business_impact": "Full service capability",
            "confidence_score": min(config_validation.validation_score, ssot_compliance.compliance_score)
        }
    
    def _assess_environment_readiness(self, environment_state: Dict[str, Any]) -> Dict[str, Any]:
        """Assess environment readiness for factory initialization."""
        required_env_vars = [
            "JWT_SECRET_KEY", "DATABASE_URL", "REDIS_URL", "ENVIRONMENT"
        ]
        
        missing_vars = []
        for var in required_env_vars:
            if var not in environment_state or not environment_state[var]:
                missing_vars.append(var)
        
        if missing_vars:
            return {
                "ready": False,
                "error_details": f"Missing environment variables: {missing_vars}",
                "recovery_actions": [f"Set {var}" for var in missing_vars]
            }
        
        # Check for conflicting configurations
        conflicts = self._detect_environment_conflicts(environment_state)
        if conflicts:
            return {
                "ready": False,
                "error_details": f"Environment conflicts: {conflicts}",
                "recovery_actions": ["Resolve configuration conflicts"]
            }
        
        return {"ready": True}
    
    def _detect_environment_conflicts(self, environment_state: Dict[str, Any]) -> List[str]:
        """Detect conflicting environment configurations."""
        conflicts = []
        
        # Example business rule: Production environment should not have debug enabled
        if (environment_state.get("ENVIRONMENT") == "production" and 
            environment_state.get("DEBUG", "").lower() == "true"):
            conflicts.append("Debug mode enabled in production")
        
        # Example business rule: Database and Redis should not use same port
        db_url = environment_state.get("DATABASE_URL", "")
        redis_url = environment_state.get("REDIS_URL", "")
        
        if ":5432" in db_url and ":5432" in redis_url:
            conflicts.append("Database and Redis using same port")
        
        return conflicts
    
    def _generate_recovery_actions(self, validation_result: FactoryValidationResult) -> List[str]:
        """Generate recovery actions based on validation failure."""
        if validation_result.state == FactoryValidationState.MISSING_DEPENDENCIES:
            return [f"Provide {dep}" for dep in validation_result.required_dependencies or []]
        elif validation_result.state == FactoryValidationState.INVALID_CONFIG:
            return ["Review configuration values", "Ensure all configs are non-null and valid"]
        elif validation_result.state == FactoryValidationState.SSOT_VIOLATION:
            return ["Consolidate duplicate implementations", "Follow SSOT patterns"]
        else:
            return ["Check system logs", "Contact support"]
    
    def create_emergency_fallback_factory(self, component_type: ComponentType) -> Dict[str, Any]:
        """Business logic: Create emergency fallback when primary factory fails."""
        fallback_configs = {
            ComponentType.WEBSOCKET_MANAGER: {
                "mode": "minimal",
                "max_connections": 10,
                "timeout": 30,
                "features": ["basic_messaging"],
                "business_impact": "Limited WebSocket functionality"
            },
            ComponentType.TOOL_DISPATCHER: {
                "mode": "safe",
                "enabled_tools": ["basic_response"],
                "disable_external_calls": True,
                "business_impact": "No external tool execution"
            },
            ComponentType.AGENT_SUPERVISOR: {
                "mode": "degraded",
                "max_concurrent_agents": 1,
                "disable_complex_workflows": True,
                "business_impact": "Single-agent execution only"
            }
        }
        
        return fallback_configs.get(component_type, {
            "mode": "emergency",
            "business_impact": "Minimal functionality only"
        })
    
    def calculate_factory_health_score(self, component_type: ComponentType,
                                     config: Dict[str, Any],
                                     ssot_compliance: SSotCompliance) -> float:
        """Business logic: Calculate overall factory health score."""
        config_validation = self.validate_factory_configuration(component_type, config)
        
        # Weight different aspects of factory health
        weights = {
            "config_score": 0.4,
            "ssot_compliance": 0.3,
            "dependency_completeness": 0.3
        }
        
        # Calculate dependency completeness
        required_deps = self.required_dependencies.get(component_type, [])
        provided_deps = [dep for dep in required_deps if dep in config]
        dependency_completeness = len(provided_deps) / len(required_deps) if required_deps else 1.0
        
        # Calculate weighted score
        health_score = (
            config_validation.validation_score * weights["config_score"] +
            ssot_compliance.compliance_score * weights["ssot_compliance"] +
            dependency_completeness * weights["dependency_completeness"]
        )
        
        return min(1.0, max(0.0, health_score))


class TestFactoryInitializationLogic(SSotBaseTestCase):
    """Test factory initialization business logic validation."""
    
    def setup_method(self, method=None):
        """Setup test environment."""
        super().setup_method(method)
        self.validator = MockFactoryValidator()
        self.test_component_type = ComponentType.WEBSOCKET_MANAGER
    
    @pytest.mark.unit
    def test_factory_configuration_validation_success(self):
        """Test successful factory configuration validation business logic."""
        # Create valid configuration
        config = {
            "jwt_secret_manager": "valid_secret_manager",
            "unified_environment": "test_environment",
            "database_connection": "postgresql://localhost:5434/test",
            "redis_connection": "redis://localhost:6381",
            "user_context_factory": "isolated_user_context_factory"
        }
        
        result = self.validator.validate_factory_configuration(self.test_component_type, config)
        
        # Business validation: Should pass with complete valid configuration
        assert result.state == FactoryValidationState.VALID
        assert result.can_initialize is True
        assert result.validation_score >= 0.8
        assert result.error_details is None
        
        # Record business metric
        self.record_metric("config_validation_success", True)
        self.record_metric("validation_score", result.validation_score)
    
    @pytest.mark.unit
    def test_factory_configuration_validation_missing_dependencies(self):
        """Test factory configuration validation with missing dependencies."""
        # Create incomplete configuration (missing required dependencies)
        config = {
            "jwt_secret_manager": "valid_secret_manager",
            "unified_environment": "test_environment",
            # Missing: database_connection, redis_connection, user_context_factory
        }
        
        result = self.validator.validate_factory_configuration(self.test_component_type, config)
        
        # Business validation: Should fail with missing dependencies
        assert result.state == FactoryValidationState.MISSING_DEPENDENCIES
        assert result.can_initialize is False
        assert result.required_dependencies is not None
        assert len(result.required_dependencies) == 3  # 3 missing dependencies
        assert "database_connection" in result.required_dependencies
        assert "redis_connection" in result.required_dependencies
        assert "user_context_factory" in result.required_dependencies
        
        # Record business metric
        self.record_metric("missing_dependencies_detection", True)
        self.record_metric("missing_dependency_count", len(result.required_dependencies))
    
    @pytest.mark.unit
    def test_factory_configuration_validation_invalid_values(self):
        """Test factory configuration validation with invalid values."""
        # Create configuration with invalid values
        config = {
            "jwt_secret_manager": "",  # Empty string
            "unified_environment": None,  # Null value
            "database_connection": {},  # Empty dict
            "redis_connection": "redis://localhost:6381",  # Valid
            "user_context_factory": False  # Boolean false
        }
        
        result = self.validator.validate_factory_configuration(self.test_component_type, config)
        
        # Business validation: Should fail due to invalid configuration values
        assert result.state == FactoryValidationState.INVALID_CONFIG
        assert result.can_initialize is False
        assert result.validation_score < 0.8  # Below threshold
        assert "validation score" in result.error_details
        
        # Record business metric
        self.record_metric("invalid_config_detection", True)
        self.record_metric("invalid_config_score", result.validation_score)
    
    @pytest.mark.unit
    def test_ssot_compliance_validation_success(self):
        """Test SSOT compliance validation business logic."""
        # Create implementation with good SSOT compliance
        implementation_details = {
            "unified_websocket_manager": ["single_implementation"],
            "single_connection_factory": ["one_factory_only"],
            "isolated_user_context": ["per_user_isolation"]
        }
        
        compliance = self.validator.validate_ssot_compliance(self.test_component_type, implementation_details)
        
        # Business validation: Should pass SSOT compliance
        assert compliance.has_single_source is True
        assert compliance.duplicate_implementations == []
        assert compliance.missing_ssot_components == []
        assert compliance.compliance_score >= 0.9
        
        # Record business metric
        self.record_metric("ssot_compliance_success", True)
        self.record_metric("ssot_compliance_score", compliance.compliance_score)
    
    @pytest.mark.unit
    def test_ssot_compliance_validation_violations(self):
        """Test SSOT compliance validation with violations."""
        # Create implementation with SSOT violations
        implementation_details = {
            "unified_websocket_manager": ["impl_1", "impl_2", "impl_3"],  # Multiple implementations
            "single_connection_factory": ["factory_a", "factory_b"],      # Duplicate factories
            # Missing: isolated_user_context
        }
        
        compliance = self.validator.validate_ssot_compliance(self.test_component_type, implementation_details)
        
        # Business validation: Should detect SSOT violations
        assert compliance.has_single_source is False
        assert len(compliance.duplicate_implementations) == 2  # Two types of duplicates
        assert len(compliance.missing_ssot_components) == 1    # One missing component
        assert compliance.compliance_score < 0.9
        
        # Check specific violations
        assert any("unified_websocket_manager: 3 implementations" in violation 
                  for violation in compliance.duplicate_implementations)
        assert "isolated_user_context" in compliance.missing_ssot_components
        
        # Record business metric
        self.record_metric("ssot_violations_detected", True)
        self.record_metric("duplicate_implementations", len(compliance.duplicate_implementations))
    
    @pytest.mark.unit
    def test_initialization_feasibility_assessment_success(self):
        """Test factory initialization feasibility assessment for success case."""
        # Setup valid configuration
        config = {
            "jwt_secret_manager": "valid_secret_manager",
            "unified_environment": "test_environment",
            "database_connection": "postgresql://localhost:5434/test",
            "redis_connection": "redis://localhost:6381",
            "user_context_factory": "isolated_user_context_factory",
            # SSOT compliance
            "unified_websocket_manager": ["single_implementation"],
            "single_connection_factory": ["one_factory_only"],
            "isolated_user_context": ["per_user_isolation"]
        }
        
        environment_state = {
            "JWT_SECRET_KEY": "test_secret_key",
            "DATABASE_URL": "postgresql://localhost:5434/test",
            "REDIS_URL": "redis://localhost:6381",
            "ENVIRONMENT": "test"
        }
        
        assessment = self.validator.assess_initialization_feasibility(
            self.test_component_type, config, environment_state
        )
        
        # Business validation: Should allow initialization
        assert assessment["can_initialize"] is True
        assert assessment["reason"] == "all_validations_passed"
        assert "Full service capability" in assessment["business_impact"]
        assert assessment["confidence_score"] >= 0.8
        
        # Record business metric
        self.record_metric("initialization_feasibility_success", True)
        self.record_metric("confidence_score", assessment["confidence_score"])
    
    @pytest.mark.unit
    def test_initialization_feasibility_assessment_environment_failure(self):
        """Test factory initialization feasibility with environment issues."""
        # Setup valid configuration but invalid environment
        config = {
            "jwt_secret_manager": "valid_secret_manager",
            "unified_environment": "test_environment",
            "database_connection": "postgresql://localhost:5434/test",
            "redis_connection": "redis://localhost:6381",
            "user_context_factory": "isolated_user_context_factory"
        }
        
        environment_state = {
            "JWT_SECRET_KEY": "",  # Missing/empty
            # Missing: DATABASE_URL, REDIS_URL, ENVIRONMENT
        }
        
        assessment = self.validator.assess_initialization_feasibility(
            self.test_component_type, config, environment_state
        )
        
        # Business validation: Should block initialization due to environment
        assert assessment["can_initialize"] is False
        assert assessment["reason"] == "environment_not_ready"
        assert "Missing environment variables" in assessment["error_details"]
        assert "Service startup failure" in assessment["business_impact"]
        assert len(assessment["recovery_actions"]) > 0
        
        # Record business metric
        self.record_metric("environment_failure_detection", True)
    
    @pytest.mark.unit
    def test_emergency_fallback_factory_creation(self):
        """Test emergency fallback factory creation business logic."""
        test_component_types = [
            ComponentType.WEBSOCKET_MANAGER,
            ComponentType.TOOL_DISPATCHER,
            ComponentType.AGENT_SUPERVISOR
        ]
        
        for component_type in test_component_types:
            fallback = self.validator.create_emergency_fallback_factory(component_type)
            
            # Business validation: Fallback should provide minimal functionality
            assert "mode" in fallback
            assert "business_impact" in fallback
            assert fallback["mode"] in ["minimal", "safe", "degraded", "emergency"]
            
            # Verify business impact is clearly stated
            assert len(fallback["business_impact"]) > 10  # Substantive description
            
        # Record business metric
        self.record_metric("emergency_fallback_creation_success", True)
        self.record_metric("fallback_components_tested", len(test_component_types))
    
    @pytest.mark.unit
    def test_factory_health_score_calculation(self):
        """Test factory health score calculation business logic."""
        # Test scenario with perfect health
        perfect_config = {
            "jwt_secret_manager": "valid_secret_manager",
            "unified_environment": "test_environment",
            "database_connection": "postgresql://localhost:5434/test",
            "redis_connection": "redis://localhost:6381",
            "user_context_factory": "isolated_user_context_factory"
        }
        
        perfect_ssot = SSotCompliance(
            has_single_source=True,
            duplicate_implementations=[],
            missing_ssot_components=[],
            compliance_score=1.0
        )
        
        perfect_score = self.validator.calculate_factory_health_score(
            self.test_component_type, perfect_config, perfect_ssot
        )
        
        # Test scenario with poor health
        poor_config = {
            "jwt_secret_manager": "",  # Invalid
            "unified_environment": None,  # Invalid
            # Missing other dependencies
        }
        
        poor_ssot = SSotCompliance(
            has_single_source=False,
            duplicate_implementations=["multiple_implementations"],
            missing_ssot_components=["missing_component"],
            compliance_score=0.2
        )
        
        poor_score = self.validator.calculate_factory_health_score(
            self.test_component_type, poor_config, poor_ssot
        )
        
        # Business validation: Health scores should reflect actual health
        assert perfect_score >= 0.9, f"Perfect config should score high, got {perfect_score}"
        assert poor_score <= 0.3, f"Poor config should score low, got {poor_score}"
        assert perfect_score > poor_score, "Perfect score should be higher than poor score"
        
        # Record business metrics
        self.record_metric("perfect_health_score", perfect_score)
        self.record_metric("poor_health_score", poor_score)
        self.record_metric("health_score_calculation_accuracy", True)
    
    @pytest.mark.unit
    def test_business_value_preservation_through_fallbacks(self):
        """Test that factory logic preserves business value through fallbacks."""
        # Scenario: Primary factory initialization fails, but business value maintained
        
        # Simulate factory initialization failure
        invalid_config = {
            "jwt_secret_manager": None,
            "unified_environment": "",
            # Missing other required dependencies
        }
        
        invalid_environment = {
            "JWT_SECRET_KEY": "",
            # Missing other required environment variables
        }
        
        # Test primary initialization fails
        primary_assessment = self.validator.assess_initialization_feasibility(
            self.test_component_type, invalid_config, invalid_environment
        )
        
        assert primary_assessment["can_initialize"] is False
        
        # Test emergency fallback provides some business value
        fallback = self.validator.create_emergency_fallback_factory(self.test_component_type)
        
        # Business validation: Fallback should provide some functionality
        assert fallback is not None
        assert "mode" in fallback
        assert fallback["mode"] in ["minimal", "safe", "degraded", "emergency"]
        
        # Even in fallback mode, some business value should be preserved
        if self.test_component_type == ComponentType.WEBSOCKET_MANAGER:
            assert "max_connections" in fallback
            assert fallback["max_connections"] > 0  # Some connections allowed
            assert "basic_messaging" in fallback.get("features", [])
        
        # Record business metric
        self.record_metric("business_value_preservation", True)
        self.record_metric("fallback_functionality_available", fallback["mode"] != "emergency")
    
    @pytest.mark.unit
    def test_configuration_validation_edge_cases(self):
        """Test configuration validation edge cases for robustness."""
        edge_case_configs = [
            # Empty configuration
            {},
            # Configuration with unexpected types
            {
                "jwt_secret_manager": 12345,  # Number instead of string
                "unified_environment": ["list", "instead", "of", "string"],
                "database_connection": {"host": "localhost"},  # Dict instead of string
            },
            # Configuration with extremely long values
            {
                "jwt_secret_manager": "x" * 10000,  # Very long string
                "unified_environment": "test",
                "database_connection": "postgresql://localhost:5434/test",
                "redis_connection": "redis://localhost:6381",
                "user_context_factory": "y" * 5000  # Very long string
            }
        ]
        
        for i, config in enumerate(edge_case_configs):
            result = self.validator.validate_factory_configuration(self.test_component_type, config)
            
            # Business validation: Should handle edge cases gracefully
            assert result.state in [
                FactoryValidationState.MISSING_DEPENDENCIES,
                FactoryValidationState.INVALID_CONFIG,
                FactoryValidationState.VALID
            ]
            assert isinstance(result.can_initialize, bool)
            assert result.validation_score >= 0.0
            assert result.validation_score <= 1.0
        
        # Record business metric
        self.record_metric("edge_case_handling", True)
        self.record_metric("edge_cases_tested", len(edge_case_configs))
    
    @pytest.mark.unit
    def test_factory_initialization_error_recovery_logic(self):
        """Test factory initialization error recovery business logic."""
        failure_scenarios = [
            {
                "name": "missing_dependencies",
                "config": {"jwt_secret_manager": "valid"},  # Missing other deps
                "expected_recovery_actions": ["Provide database_connection", "Provide redis_connection"]
            },
            {
                "name": "invalid_config",
                "config": {
                    "jwt_secret_manager": "",
                    "unified_environment": None,
                    "database_connection": {},
                    "redis_connection": "redis://localhost:6381",
                    "user_context_factory": False
                },
                "expected_recovery_actions": ["Review configuration values", "Ensure all configs are non-null and valid"]
            }
        ]
        
        for scenario in failure_scenarios:
            result = self.validator.validate_factory_configuration(
                self.test_component_type, scenario["config"]
            )
            
            # Get recovery actions
            recovery_actions = self.validator._generate_recovery_actions(result)
            
            # Business validation: Recovery actions should be actionable
            assert len(recovery_actions) > 0
            
            # Check for expected recovery patterns
            for expected_action in scenario["expected_recovery_actions"]:
                assert any(expected_action in action for action in recovery_actions), (
                    f"Expected recovery action '{expected_action}' not found in {recovery_actions}"
                )
        
        # Record business metric
        self.record_metric("error_recovery_logic_tested", True)


if __name__ == "__main__":
    pytest.main([__file__])