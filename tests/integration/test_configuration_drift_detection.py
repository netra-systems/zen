"""
Configuration Drift Detection Tests - Five Whys Root Cause Prevention

CRITICAL: This addresses the Five Whys finding:
"Missing automated tests that detect configuration inconsistencies"

These tests validate:
1. Automated detection of configuration drift between Docker and application
2. Environment-specific configuration consistency validation
3. Service configuration mismatch detection across deployment contexts
4. Configuration pattern compliance testing
5. Real-time drift monitoring and alerting validation

ROOT CAUSE ADDRESSED: WHY #4 - Process gap that allowed configuration drift
to go undetected, causing Redis port mapping mismatches and service failures.

Business Value: Platform/Internal - Configuration Reliability & Drift Prevention
Prevents configuration drift that causes service connection failures and deployment issues.
"""
import pytest
import os
import json
import yaml
import time
import tempfile
from typing import Dict, Any, List, Optional, Set, Tuple
from pathlib import Path
from unittest.mock import patch, MagicMock
from dataclasses import dataclass, field

from shared.isolated_environment import IsolatedEnvironment, get_env
from netra_backend.app.core.backend_environment import BackendEnvironment


@dataclass
class ConfigurationDriftReport:
    """Report of configuration drift detection results."""
    environment: str
    timestamp: float
    drift_detected: bool
    critical_drifts: List[str] = field(default_factory=list)
    warning_drifts: List[str] = field(default_factory=list)
    missing_configurations: List[str] = field(default_factory=list)
    extra_configurations: List[str] = field(default_factory=list)
    consistency_violations: List[str] = field(default_factory=list)
    
    def has_critical_issues(self) -> bool:
        """Check if there are critical configuration issues."""
        return len(self.critical_drifts) > 0 or len(self.missing_configurations) > 0
    
    def get_summary(self) -> str:
        """Get a summary of drift detection results."""
        if not self.drift_detected:
            return f"No configuration drift detected for {self.environment}"
        
        issues = []
        if self.critical_drifts:
            issues.append(f"{len(self.critical_drifts)} critical drifts")
        if self.warning_drifts:
            issues.append(f"{len(self.warning_drifts)} warning drifts")
        if self.missing_configurations:
            issues.append(f"{len(self.missing_configurations)} missing configs")
        if self.extra_configurations:
            issues.append(f"{len(self.extra_configurations)} extra configs")
        if self.consistency_violations:
            issues.append(f"{len(self.consistency_violations)} violations")
        
        return f"Configuration drift in {self.environment}: {', '.join(issues)}"


class ConfigurationDriftDetector:
    """Detect configuration drift between expected and actual configurations."""
    
    def __init__(self):
        """Initialize configuration drift detector."""
        self.expected_configs = self._load_expected_configurations()
        self.drift_rules = self._load_drift_detection_rules()
    
    def _load_expected_configurations(self) -> Dict[str, Dict[str, Any]]:
        """Load expected configurations for different environments."""
        return {
            "development": {
                # Docker internal networking
                "POSTGRES_HOST": "dev-postgres",
                "POSTGRES_PORT": 5432,
                "REDIS_HOST": "dev-redis", 
                "REDIS_PORT": 6379,
                "AUTH_SERVICE_URL": "http://dev-auth:8081",
                "CLICKHOUSE_HOST": "dev-clickhouse",
                "CLICKHOUSE_PORT": 9000,
                "ENVIRONMENT": "development"
            },
            "test": {
                # External Docker access for testing
                "POSTGRES_HOST": "localhost",
                "POSTGRES_PORT": 5434,  # External port
                "REDIS_HOST": "localhost",
                "REDIS_PORT": 6381,     # External port
                "AUTH_SERVICE_URL": "http://localhost:8081",
                "CLICKHOUSE_HOST": "localhost",
                "CLICKHOUSE_PORT": 9002,  # External TCP port
                "ENVIRONMENT": "test"
            },
            "staging": {
                # Cloud deployment configuration
                "POSTGRES_HOST": ["staging-postgres-server", "*.googleapis.com"],  # Multiple valid patterns
                "POSTGRES_PORT": 5432,
                "REDIS_HOST": ["staging-redis-server", "*.googleapis.com"],
                "REDIS_PORT": 6379,
                "ENVIRONMENT": "staging"
            },
            "production": {
                # Production deployment configuration
                "POSTGRES_HOST": ["prod-postgres-server", "*.googleapis.com"],
                "POSTGRES_PORT": 5432,
                "REDIS_HOST": ["prod-redis-server", "*.googleapis.com"],
                "REDIS_PORT": 6379,
                "ENVIRONMENT": "production"
            }
        }
    
    def _load_drift_detection_rules(self) -> Dict[str, Any]:
        """Load rules for drift detection."""
        return {
            "critical_configs": [
                "ENVIRONMENT",
                "POSTGRES_HOST",
                "POSTGRES_PORT", 
                "REDIS_HOST",
                "REDIS_PORT"
            ],
            "warning_configs": [
                "AUTH_SERVICE_URL",
                "CLICKHOUSE_HOST",
                "CLICKHOUSE_PORT"
            ],
            "port_consistency_rules": {
                "development": {
                    "internal_ports": [5432, 6379, 9000, 8081, 8000],
                    "external_ports": [5433, 6380, 9001, 8081, 8000]
                },
                "test": {
                    "internal_ports": [5432, 6379, 9000],
                    "external_ports": [5434, 6381, 9002]
                }
            },
            "environment_specific_validations": {
                "development": {
                    "forbidden_hosts": ["localhost"],  # Should use service names
                    "required_service_patterns": ["dev-*"]
                },
                "test": {
                    "allowed_hosts": ["localhost", "test-*"],
                    "required_external_ports": [5434, 6381]
                },
                "staging": {
                    "forbidden_hosts": ["localhost", "dev-*", "test-*"],
                    "required_gcp_indicators": ["GCP_PROJECT", "K_SERVICE"]
                },
                "production": {
                    "forbidden_hosts": ["localhost", "dev-*", "test-*", "staging-*"],
                    "required_gcp_indicators": ["GCP_PROJECT", "K_SERVICE"],
                    "forbidden_debug_configs": ["DEBUG=true", "LOG_LEVEL=DEBUG"]
                }
            }
        }
    
    def detect_drift(self, environment: str, actual_config: Dict[str, Any]) -> ConfigurationDriftReport:
        """Detect configuration drift for a specific environment."""
        report = ConfigurationDriftReport(
            environment=environment,
            timestamp=time.time(),
            drift_detected=False
        )
        
        expected_config = self.expected_configs.get(environment, {})
        
        if not expected_config:
            report.consistency_violations.append(f"No expected configuration defined for environment: {environment}")
            report.drift_detected = True
            return report
        
        # Check critical configurations
        for config_key in self.drift_rules["critical_configs"]:
            drift_issue = self._check_config_drift(config_key, expected_config, actual_config, "critical")
            if drift_issue:
                report.critical_drifts.append(drift_issue)
                report.drift_detected = True
        
        # Check warning configurations
        for config_key in self.drift_rules["warning_configs"]:
            drift_issue = self._check_config_drift(config_key, expected_config, actual_config, "warning")
            if drift_issue:
                report.warning_drifts.append(drift_issue)
                report.drift_detected = True
        
        # Check environment-specific validations
        env_violations = self._check_environment_specific_validations(environment, actual_config)
        report.consistency_violations.extend(env_violations)
        if env_violations:
            report.drift_detected = True
        
        # Check port consistency
        port_violations = self._check_port_consistency(environment, actual_config)
        report.consistency_violations.extend(port_violations)
        if port_violations:
            report.drift_detected = True
        
        return report
    
    def _check_config_drift(self, config_key: str, expected_config: Dict[str, Any], 
                           actual_config: Dict[str, Any], severity: str) -> Optional[str]:
        """Check for drift in a specific configuration."""
        expected_value = expected_config.get(config_key)
        actual_value = actual_config.get(config_key)
        
        if expected_value is None:
            return None  # No expectation defined
        
        if actual_value is None:
            return f"Missing {severity} config: {config_key} (expected: {expected_value})"
        
        # Handle multiple valid patterns
        if isinstance(expected_value, list):
            for pattern in expected_value:
                if self._value_matches_pattern(actual_value, pattern):
                    return None  # Match found
            return f"{severity.capitalize()} config drift: {config_key} = {actual_value} (expected one of: {expected_value})"
        
        # Handle exact matches
        if isinstance(expected_value, (str, int, float, bool)):
            if actual_value != expected_value:
                return f"{severity.capitalize()} config drift: {config_key} = {actual_value} (expected: {expected_value})"
        
        return None
    
    def _value_matches_pattern(self, value: Any, pattern: Any) -> bool:
        """Check if a value matches a pattern."""
        if isinstance(pattern, str) and '*' in pattern:
            # Simple glob-style pattern matching
            if pattern.startswith('*'):
                return str(value).endswith(pattern[1:])
            elif pattern.endswith('*'):
                return str(value).startswith(pattern[:-1])
            else:
                # More complex pattern - for now just check if contained
                return pattern.replace('*', '') in str(value)
        else:
            return value == pattern
    
    def _check_environment_specific_validations(self, environment: str, actual_config: Dict[str, Any]) -> List[str]:
        """Check environment-specific validation rules."""
        violations = []
        env_rules = self.drift_rules["environment_specific_validations"].get(environment, {})
        
        # Check forbidden hosts
        forbidden_hosts = env_rules.get("forbidden_hosts", [])
        for config_key in ["POSTGRES_HOST", "REDIS_HOST", "CLICKHOUSE_HOST"]:
            actual_host = actual_config.get(config_key)
            if actual_host and any(forbidden in str(actual_host) for forbidden in forbidden_hosts):
                violations.append(f"Forbidden host in {environment}: {config_key}={actual_host}")
        
        # Check allowed hosts
        allowed_hosts = env_rules.get("allowed_hosts", [])
        if allowed_hosts:
            for config_key in ["POSTGRES_HOST", "REDIS_HOST"]:
                actual_host = actual_config.get(config_key)
                if actual_host and not any(self._value_matches_pattern(actual_host, allowed) for allowed in allowed_hosts):
                    violations.append(f"Host not allowed in {environment}: {config_key}={actual_host} (allowed: {allowed_hosts})")
        
        # Check required GCP indicators
        required_gcp = env_rules.get("required_gcp_indicators", [])
        for indicator in required_gcp:
            if not actual_config.get(indicator):
                violations.append(f"Missing required GCP indicator for {environment}: {indicator}")
        
        # Check forbidden debug configurations
        forbidden_debug = env_rules.get("forbidden_debug_configs", [])
        for forbidden_config in forbidden_debug:
            if '=' in forbidden_config:
                key, forbidden_value = forbidden_config.split('=', 1)
                if actual_config.get(key) == forbidden_value:
                    violations.append(f"Forbidden debug config in {environment}: {key}={forbidden_value}")
        
        return violations
    
    def _check_port_consistency(self, environment: str, actual_config: Dict[str, Any]) -> List[str]:
        """Check port consistency rules."""
        violations = []
        port_rules = self.drift_rules["port_consistency_rules"].get(environment, {})
        
        if not port_rules:
            return violations
        
        # Check internal vs external port usage
        postgres_port = actual_config.get("POSTGRES_PORT")
        redis_port = actual_config.get("REDIS_PORT")
        
        if environment == "development":
            # Development should use internal ports
            expected_internal = port_rules.get("internal_ports", [])
            if postgres_port and int(postgres_port) not in expected_internal:
                if int(postgres_port) in port_rules.get("external_ports", []):
                    violations.append(f"Development using external port: POSTGRES_PORT={postgres_port} (should use internal)")
            
            if redis_port and int(redis_port) not in expected_internal:
                if int(redis_port) in port_rules.get("external_ports", []):
                    violations.append(f"Development using external port: REDIS_PORT={redis_port} (should use internal)")
        
        elif environment == "test":
            # Test should use external ports for external access
            expected_external = port_rules.get("external_ports", [])
            if postgres_port and int(postgres_port) not in expected_external:
                violations.append(f"Test not using external port: POSTGRES_PORT={postgres_port} (should use external)")
            
            if redis_port and int(redis_port) not in expected_external:
                violations.append(f"Test not using external port: REDIS_PORT={redis_port} (should use external)")
        
        return violations


class TestConfigurationDriftDetection:
    """Test configuration drift detection functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_environment(self):
        """Setup clean environment for each test."""
        self.env = get_env()
        self.env.enable_isolation(backup_original=True)
        self.drift_detector = ConfigurationDriftDetector()
        yield
        self.env.reset_to_original()
    
    def test_development_configuration_drift_detection(self):
        """Test drift detection for development environment."""
        # Test with correct development configuration
        correct_dev_config = {
            "ENVIRONMENT": "development",
            "POSTGRES_HOST": "dev-postgres",
            "POSTGRES_PORT": 5432,
            "REDIS_HOST": "dev-redis",
            "REDIS_PORT": 6379,
            "AUTH_SERVICE_URL": "http://dev-auth:8081"
        }
        
        report = self.drift_detector.detect_drift("development", correct_dev_config)
        assert not report.drift_detected, f"Correct config should not show drift: {report.get_summary()}"
        assert len(report.critical_drifts) == 0
        assert len(report.warning_drifts) == 0
        
        # Test with incorrect development configuration (drift present)
        drifted_dev_config = {
            "ENVIRONMENT": "development",
            "POSTGRES_HOST": "localhost",  # Should be "dev-postgres"
            "POSTGRES_PORT": 5434,         # Should be 5432 (internal)
            "REDIS_HOST": "wrong-redis",   # Should be "dev-redis"
            "REDIS_PORT": 6381,            # Should be 6379 (internal)
        }
        
        drift_report = self.drift_detector.detect_drift("development", drifted_dev_config)
        assert drift_report.drift_detected, "Drift should be detected"
        assert len(drift_report.critical_drifts) >= 3, f"Should detect multiple critical drifts: {drift_report.critical_drifts}"
        
        # Check specific drift detections
        critical_drift_text = ' '.join(drift_report.critical_drifts)
        assert "POSTGRES_HOST" in critical_drift_text
        assert "REDIS_HOST" in critical_drift_text
        assert "POSTGRES_PORT" in critical_drift_text or "REDIS_PORT" in critical_drift_text
    
    def test_test_environment_configuration_drift_detection(self):
        """Test drift detection for test environment."""
        # Correct test configuration (external Docker access)
        correct_test_config = {
            "ENVIRONMENT": "test",
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": 5434,  # External port
            "REDIS_HOST": "localhost",
            "REDIS_PORT": 6381,     # External port
        }
        
        report = self.drift_detector.detect_drift("test", correct_test_config)
        assert not report.drift_detected, f"Correct test config should not show drift: {report.get_summary()}"
        
        # Incorrect test configuration (using internal ports)
        internal_ports_config = {
            "ENVIRONMENT": "test",
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": 5432,  # Internal port - wrong for test
            "REDIS_HOST": "localhost", 
            "REDIS_PORT": 6379,     # Internal port - wrong for test
        }
        
        drift_report = self.drift_detector.detect_drift("test", internal_ports_config)
        assert drift_report.drift_detected, "Should detect port configuration drift"
        
        # Should detect port consistency violations
        port_violations = [v for v in drift_report.consistency_violations if "port" in v.lower()]
        assert len(port_violations) >= 1, f"Should detect port violations: {drift_report.consistency_violations}"
    
    def test_staging_environment_configuration_drift_detection(self):
        """Test drift detection for staging environment."""
        # Correct staging configuration
        correct_staging_config = {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": "staging-postgres-server",
            "POSTGRES_PORT": 5432,
            "REDIS_HOST": "staging-redis-server.googleapis.com",  # GCP pattern
            "REDIS_PORT": 6379,
            "GCP_PROJECT": "netra-staging",
            "K_SERVICE": "netra-backend-staging"
        }
        
        report = self.drift_detector.detect_drift("staging", correct_staging_config)
        assert not report.drift_detected, f"Correct staging config should not show drift: {report.get_summary()}"
        
        # Incorrect staging configuration (using development service names)
        dev_names_in_staging = {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": "dev-postgres",  # Development service name in staging!
            "POSTGRES_PORT": 5432,
            "REDIS_HOST": "dev-redis",        # Development service name in staging!
            "REDIS_PORT": 6379,
            # Missing GCP indicators
        }
        
        drift_report = self.drift_detector.detect_drift("staging", dev_names_in_staging)
        assert drift_report.drift_detected, "Should detect staging configuration drift"
        
        # Should detect forbidden hosts and missing GCP indicators
        violations = drift_report.consistency_violations
        forbidden_violations = [v for v in violations if "forbidden" in v.lower()]
        gcp_violations = [v for v in violations if "gcp" in v.lower()]
        
        assert len(forbidden_violations) >= 1, f"Should detect forbidden dev hosts: {violations}"
        assert len(gcp_violations) >= 1, f"Should detect missing GCP indicators: {violations}"
    
    def test_production_environment_configuration_drift_detection(self):
        """Test drift detection for production environment."""
        # Correct production configuration
        correct_prod_config = {
            "ENVIRONMENT": "production",
            "POSTGRES_HOST": "prod-postgres-server.googleapis.com",
            "POSTGRES_PORT": 5432,
            "REDIS_HOST": "prod-redis-server.googleapis.com",
            "REDIS_PORT": 6379,
            "GCP_PROJECT": "netra-production",
            "K_SERVICE": "netra-backend-production",
            "LOG_LEVEL": "INFO"  # Not DEBUG
        }
        
        report = self.drift_detector.detect_drift("production", correct_prod_config)
        assert not report.drift_detected, f"Correct production config should not show drift: {report.get_summary()}"
        
        # Dangerous production configuration 
        dangerous_prod_config = {
            "ENVIRONMENT": "production",
            "POSTGRES_HOST": "localhost",     # Dangerous in production
            "REDIS_HOST": "staging-redis",    # Staging resource in production!
            "DEBUG": "true",                  # Debug enabled in production!
            "LOG_LEVEL": "DEBUG",             # Debug logging in production!
            # Missing GCP indicators
        }
        
        drift_report = self.drift_detector.detect_drift("production", dangerous_prod_config)
        assert drift_report.drift_detected, "Should detect dangerous production configuration"
        assert drift_report.has_critical_issues(), "Production drift should be critical"
        
        # Should detect multiple serious violations
        all_violations = drift_report.critical_drifts + drift_report.consistency_violations
        localhost_violations = [v for v in all_violations if "localhost" in v.lower()]
        debug_violations = [v for v in all_violations if "debug" in v.lower()]
        
        assert len(localhost_violations) >= 1, "Should detect localhost usage in production"
        assert len(debug_violations) >= 1, "Should detect debug configuration in production"
    
    def test_missing_configuration_detection(self):
        """Test detection of missing critical configurations."""
        # Configuration with missing critical values
        incomplete_config = {
            "ENVIRONMENT": "staging",
            # Missing POSTGRES_HOST, POSTGRES_PORT, REDIS_HOST, REDIS_PORT
            "AUTH_SERVICE_URL": "http://some-auth-service:8081"
        }
        
        drift_report = self.drift_detector.detect_drift("staging", incomplete_config)
        assert drift_report.drift_detected, "Should detect missing configurations"
        assert len(drift_report.critical_drifts) >= 3, f"Should detect missing critical configs: {drift_report.critical_drifts}"
        
        # Check that specific missing configurations are identified
        missing_configs = ' '.join(drift_report.critical_drifts)
        assert "POSTGRES_HOST" in missing_configs
        assert "REDIS_HOST" in missing_configs
        assert "Missing" in missing_configs
    
    def test_configuration_pattern_matching(self):
        """Test configuration pattern matching for flexible validation."""
        # Test GCP-style hostnames with patterns
        gcp_config = {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": "postgres-instance.c.netra-staging.internal",  # GCP internal pattern
            "POSTGRES_PORT": 5432,
            "REDIS_HOST": "redis-cluster.googleapis.com",                    # GCP service pattern
            "REDIS_PORT": 6379,
            "GCP_PROJECT": "netra-staging"
        }
        
        drift_report = self.drift_detector.detect_drift("staging", gcp_config)
        
        # Should not detect drift for valid GCP patterns
        host_drifts = [d for d in drift_report.critical_drifts if "HOST" in d]
        assert len(host_drifts) == 0, f"GCP patterns should be valid: {host_drifts}"
    
    def test_drift_detection_performance_validation(self):
        """Test that drift detection performs efficiently with large configurations."""
        # Large configuration with many keys
        large_config = {
            "ENVIRONMENT": "development",
            "POSTGRES_HOST": "dev-postgres",
            "POSTGRES_PORT": 5432,
            "REDIS_HOST": "dev-redis", 
            "REDIS_PORT": 6379,
        }
        
        # Add many additional configuration keys
        for i in range(100):
            large_config[f"CUSTOM_CONFIG_{i}"] = f"value_{i}"
        
        start_time = time.time()
        drift_report = self.drift_detector.detect_drift("development", large_config)
        detection_time = time.time() - start_time
        
        # Should complete quickly (under 1 second for reasonable size)
        assert detection_time < 1.0, f"Drift detection too slow: {detection_time:.3f}s"
        
        # Should still detect drift correctly
        assert not drift_report.drift_detected, "Large config without drift should pass"


class TestRealTimeConfigurationMonitoring:
    """Test real-time configuration drift monitoring."""
    
    @pytest.fixture(autouse=True)
    def setup_environment(self):
        """Setup environment."""
        self.env = get_env()
        self.env.enable_isolation(backup_original=True)
        yield
        self.env.reset_to_original()
    
    def test_backend_environment_configuration_monitoring(self):
        """Test monitoring BackendEnvironment for configuration changes."""
        # Initial correct configuration
        initial_config = {
            "ENVIRONMENT": "development",
            "POSTGRES_HOST": "dev-postgres",
            "POSTGRES_PORT": "5432",
            "REDIS_HOST": "dev-redis",
            "REDIS_PORT": "6379"
        }
        
        for key, value in initial_config.items():
            self.env.set(key, value, "monitoring_test")
        
        backend_env = BackendEnvironment()
        drift_detector = ConfigurationDriftDetector()
        
        # Get initial configuration from BackendEnvironment
        initial_backend_config = {
            "ENVIRONMENT": backend_env.get_environment(),
            "POSTGRES_HOST": backend_env.get_postgres_host(),
            "POSTGRES_PORT": backend_env.get_postgres_port(),
            "REDIS_HOST": backend_env.get_redis_host(),
            "REDIS_PORT": backend_env.get_redis_port()
        }
        
        # Should have no drift initially
        initial_report = drift_detector.detect_drift("development", initial_backend_config)
        assert not initial_report.drift_detected, f"Initial config should be clean: {initial_report.get_summary()}"
        
        # Simulate configuration change (drift introduction)
        self.env.set("POSTGRES_HOST", "localhost", "drift_introduction")
        self.env.set("REDIS_PORT", "6381", "drift_introduction")  # External port
        
        # Create new BackendEnvironment instance to pick up changes
        drifted_backend_env = BackendEnvironment()
        
        drifted_config = {
            "ENVIRONMENT": drifted_backend_env.get_environment(),
            "POSTGRES_HOST": drifted_backend_env.get_postgres_host(),
            "POSTGRES_PORT": drifted_backend_env.get_postgres_port(),
            "REDIS_HOST": drifted_backend_env.get_redis_host(),
            "REDIS_PORT": drifted_backend_env.get_redis_port()
        }
        
        # Should detect drift
        drift_report = drift_detector.detect_drift("development", drifted_config)
        assert drift_report.drift_detected, "Should detect configuration drift after changes"
        assert len(drift_report.critical_drifts) >= 1, f"Should detect critical drift: {drift_report.critical_drifts}"
    
    def test_configuration_drift_alerting_integration(self):
        """Test integration with alerting systems for configuration drift."""
        drift_detector = ConfigurationDriftDetector()
        
        # Configuration that would cause critical service failures
        critical_failure_config = {
            "ENVIRONMENT": "production",
            "POSTGRES_HOST": "dev-postgres",    # Development service in production!
            "POSTGRES_PORT": 5434,              # Wrong port
            "REDIS_HOST": "localhost",          # Localhost in production!
            "REDIS_PORT": 6381,                 # Wrong port
            "DEBUG": "true"                     # Debug in production!
        }
        
        drift_report = drift_detector.detect_drift("production", critical_failure_config)
        
        # Should detect as critical drift requiring immediate attention
        assert drift_report.has_critical_issues(), "Should identify as critical issues"
        assert len(drift_report.critical_drifts) >= 2, "Multiple critical issues should be detected"
        
        # Simulate alert generation
        alert_needed = drift_report.has_critical_issues()
        alert_severity = "CRITICAL" if len(drift_report.critical_drifts) >= 3 else "WARNING"
        alert_message = drift_report.get_summary()
        
        assert alert_needed is True, "Alert should be triggered for critical drift"
        assert alert_severity == "CRITICAL", "Should be critical severity"
        assert "production" in alert_message.lower(), "Alert should specify environment"


class TestConfigurationDriftPrevention:
    """Test configuration drift prevention mechanisms."""
    
    @pytest.fixture(autouse=True)
    def setup_environment(self):
        """Setup environment."""
        self.env = get_env()
        self.env.enable_isolation(backup_original=True)
        yield
        self.env.reset_to_original()
    
    def test_configuration_validation_on_backend_environment_initialization(self):
        """Test that BackendEnvironment initialization can detect configuration issues."""
        # Test with problematic configuration
        problematic_config = {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": "localhost",      # Wrong for staging
            "POSTGRES_PORT": "invalid_port",   # Invalid port
            "REDIS_HOST": "",                  # Empty host
            "REDIS_PORT": "6379"               # Should be validated port for staging
        }
        
        for key, value in problematic_config.items():
            self.env.set(key, value, "validation_on_init_test")
        
        # BackendEnvironment should handle invalid configurations gracefully
        backend_env = BackendEnvironment()
        
        # Invalid port should be handled with fallback
        postgres_port = backend_env.get_postgres_port()
        assert postgres_port == 5432, f"Invalid port should fallback to default: {postgres_port}"
        
        # Empty host should use fallback
        redis_host = backend_env.get_redis_host()
        assert redis_host == "localhost", f"Empty host should use default: {redis_host}"
        
        # Environment detection should still work
        assert backend_env.get_environment() == "staging"
        
        # Validation should report issues
        validation_result = backend_env.validate()
        assert not validation_result["valid"], "Validation should fail for problematic config"
        assert len(validation_result["issues"]) > 0, "Should report validation issues"
    
    def test_configuration_drift_prevention_through_validation(self):
        """Test preventing configuration drift through proactive validation."""
        drift_detector = ConfigurationDriftDetector()
        
        # Simulate deployment process validation
        proposed_configs = [
            {
                "name": "good_staging_config",
                "config": {
                    "ENVIRONMENT": "staging",
                    "POSTGRES_HOST": "staging-postgres.googleapis.com",
                    "POSTGRES_PORT": 5432,
                    "REDIS_HOST": "staging-redis.googleapis.com",
                    "REDIS_PORT": 6379,
                    "GCP_PROJECT": "netra-staging"
                },
                "should_pass": True
            },
            {
                "name": "bad_staging_config",
                "config": {
                    "ENVIRONMENT": "staging",
                    "POSTGRES_HOST": "dev-postgres",  # Development service in staging!
                    "POSTGRES_PORT": 5432,
                    "REDIS_HOST": "localhost",        # Localhost in staging!
                    "REDIS_PORT": 6379
                    # Missing GCP_PROJECT
                },
                "should_pass": False
            }
        ]
        
        validation_results = {}
        
        for test_case in proposed_configs:
            config_name = test_case["name"]
            config = test_case["config"]
            should_pass = test_case["should_pass"]
            
            drift_report = drift_detector.detect_drift("staging", config)
            validation_results[config_name] = {
                "passed": not drift_report.drift_detected,
                "report": drift_report
            }
            
            if should_pass:
                assert not drift_report.drift_detected, f"Good config {config_name} should pass: {drift_report.get_summary()}"
            else:
                assert drift_report.drift_detected, f"Bad config {config_name} should fail: {drift_report.get_summary()}"
        
        # Validation should prevent deployment of bad configurations
        good_config_passed = validation_results["good_staging_config"]["passed"]
        bad_config_blocked = not validation_results["bad_staging_config"]["passed"]
        
        assert good_config_passed, "Good configuration should be allowed"
        assert bad_config_blocked, "Bad configuration should be blocked"
    
    def test_docker_compose_consistency_validation(self):
        """Test validation of docker-compose.yml consistency with configuration."""
        # Load actual docker-compose.yml file
        compose_file = Path(__file__).parent.parent.parent / "docker-compose.yml"
        
        if not compose_file.exists():
            pytest.skip("docker-compose.yml not found")
        
        with open(compose_file, 'r') as f:
            compose_data = yaml.safe_load(f)
        
        # Extract expected configurations from docker-compose.yml
        dev_postgres_service = compose_data['services'].get('dev-postgres', {})
        dev_redis_service = compose_data['services'].get('dev-redis', {})
        dev_backend_service = compose_data['services'].get('dev-backend', {})
        
        # Parse environment variables from dev-backend service
        backend_env_vars = dev_backend_service.get('environment', {})
        
        # Convert to format expected by drift detector
        docker_compose_config = {}
        for key, value in backend_env_vars.items():
            if isinstance(value, str):
                docker_compose_config[key] = value
        
        # Add expected environment
        docker_compose_config["ENVIRONMENT"] = "development"
        
        # Validate that docker-compose configuration passes drift detection
        drift_detector = ConfigurationDriftDetector()
        drift_report = drift_detector.detect_drift("development", docker_compose_config)
        
        # Docker-compose configuration should be consistent
        # Note: Some differences may be acceptable (e.g., defaults vs explicit values)
        critical_drifts = [d for d in drift_report.critical_drifts if "POSTGRES_HOST" in d or "REDIS_HOST" in d]
        
        # Should not have critical service host/port mismatches
        assert len(critical_drifts) == 0, f"Docker-compose should have consistent service configuration: {critical_drifts}"


class TestConfigurationDriftReporting:
    """Test configuration drift reporting and documentation."""
    
    @pytest.fixture(autouse=True)
    def setup_environment(self):
        """Setup environment."""
        self.env = get_env()
        self.env.enable_isolation(backup_original=True)
        yield
        self.env.reset_to_original()
    
    def test_drift_report_generation(self):
        """Test comprehensive drift report generation."""
        drift_detector = ConfigurationDriftDetector()
        
        # Create configuration with multiple types of drift
        multi_drift_config = {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": "dev-postgres",      # Critical: wrong service
            "POSTGRES_PORT": 5434,                # Critical: wrong port
            "REDIS_HOST": "localhost",            # Critical: forbidden host
            "REDIS_PORT": 6381,                   # Critical: wrong port
            "AUTH_SERVICE_URL": "http://localhost:8081",  # Warning: localhost
            "CLICKHOUSE_HOST": "test-clickhouse", # Warning: test service
            "DEBUG": "true"                       # Violation: debug in staging
            # Missing: GCP_PROJECT (missing critical config)
        }
        
        drift_report = drift_detector.detect_drift("staging", multi_drift_config)
        
        # Validate comprehensive reporting
        assert drift_report.drift_detected is True
        assert len(drift_report.critical_drifts) >= 3, f"Should detect multiple critical drifts: {drift_report.critical_drifts}"
        assert len(drift_report.warning_drifts) >= 1, f"Should detect warning drifts: {drift_report.warning_drifts}"
        assert len(drift_report.consistency_violations) >= 2, f"Should detect violations: {drift_report.consistency_violations}"
        
        # Test report summary
        summary = drift_report.get_summary()
        assert "staging" in summary
        assert "critical" in summary.lower()
        assert "warning" in summary.lower()
        
        # Test report serialization (for logging/alerting)
        report_data = {
            "environment": drift_report.environment,
            "timestamp": drift_report.timestamp,
            "drift_detected": drift_report.drift_detected,
            "critical_count": len(drift_report.critical_drifts),
            "warning_count": len(drift_report.warning_drifts),
            "violation_count": len(drift_report.consistency_violations),
            "summary": drift_report.get_summary()
        }
        
        # Should be serializable for external systems
        json_report = json.dumps(report_data)
        assert json_report is not None
        
        # Should contain key information
        parsed_report = json.loads(json_report)
        assert parsed_report["environment"] == "staging"
        assert parsed_report["drift_detected"] is True
        assert parsed_report["critical_count"] >= 3
    
    def test_drift_report_historical_tracking(self):
        """Test tracking configuration drift over time."""
        drift_detector = ConfigurationDriftDetector()
        
        # Simulate configuration evolution over time
        config_timeline = [
            {
                "timestamp": time.time() - 3600,  # 1 hour ago
                "config": {
                    "ENVIRONMENT": "development",
                    "POSTGRES_HOST": "dev-postgres",
                    "POSTGRES_PORT": 5432,
                    "REDIS_HOST": "dev-redis",
                    "REDIS_PORT": 6379
                },
                "description": "Initial correct config"
            },
            {
                "timestamp": time.time() - 1800,  # 30 minutes ago
                "config": {
                    "ENVIRONMENT": "development",
                    "POSTGRES_HOST": "localhost",  # Drift introduced
                    "POSTGRES_PORT": 5432,
                    "REDIS_HOST": "dev-redis",
                    "REDIS_PORT": 6379
                },
                "description": "Postgres host changed to localhost"
            },
            {
                "timestamp": time.time(),  # Now
                "config": {
                    "ENVIRONMENT": "development",
                    "POSTGRES_HOST": "localhost",
                    "POSTGRES_PORT": 5432,
                    "REDIS_HOST": "localhost",     # More drift
                    "REDIS_PORT": 6381             # External port
                },
                "description": "Redis config also drifted"
            }
        ]
        
        drift_history = []
        
        for timeline_entry in config_timeline:
            config = timeline_entry["config"]
            description = timeline_entry["description"]
            
            drift_report = drift_detector.detect_drift("development", config)
            
            drift_history.append({
                "description": description,
                "timestamp": timeline_entry["timestamp"],
                "drift_detected": drift_report.drift_detected,
                "critical_drifts": len(drift_report.critical_drifts),
                "total_issues": len(drift_report.critical_drifts) + len(drift_report.warning_drifts) + len(drift_report.consistency_violations)
            })
        
        # Should show progression of drift
        assert drift_history[0]["drift_detected"] is False, "Initial config should be clean"
        assert drift_history[1]["drift_detected"] is True, "First drift should be detected"
        assert drift_history[2]["drift_detected"] is True, "Continued drift should be detected"
        
        # Should show increasing drift severity
        assert drift_history[2]["total_issues"] > drift_history[1]["total_issues"], "Drift should worsen over time"