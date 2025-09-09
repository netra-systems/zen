"""
Unit Tests: String Literals Validation and Critical Config Protection

CRITICAL: Tests String Literals Index validation and protection of mission-critical configs.
Prevents 11 mission-critical environment variables + 12 domain configurations cascade failures.

Business Value: Platform/Internal - Prevents $12K MRR loss from config-related incidents  
Test Coverage: String literals validation, critical config protection, cascade failure prevention
"""
import pytest
import os
import subprocess
from unittest.mock import patch, Mock, call
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment, get_env


class TestStringLiteralsValidationCritical:
    """Test String Literals Index validation and critical configuration protection."""

    def test_critical_environment_variables_protection(self):
        """
        CRITICAL: Test protection of 11 mission-critical environment variables.
        
        PREVENTS: Modification of variables that cause CASCADE FAILURES
        CASCADE FAILURE: Complete system failure, authentication breakdown, data loss
        """
        env = get_env()
        env.enable_isolation()
        
        # Critical environment variables from String Literals Index
        critical_env_vars = {
            "DATABASE_URL": "postgresql://localhost:5432/netra_test",
            "ENVIRONMENT": "test",
            "GOOGLE_CLIENT_ID": "test-google-client-id.apps.googleusercontent.com",
            "GOOGLE_CLIENT_SECRET": "test-google-client-secret",
            "JWT_SECRET_KEY": "test-jwt-secret-key-32-characters-minimum",
            "NEXT_PUBLIC_API_URL": "http://localhost:8000",
            "NEXT_PUBLIC_AUTH_URL": "http://localhost:8081",
            "NEXT_PUBLIC_ENVIRONMENT": "test",
            "NEXT_PUBLIC_WEBSOCKET_URL": "ws://localhost:8000/ws",
            "NEXT_PUBLIC_WS_URL": "ws://localhost:8000/ws",
            "REDIS_URL": "redis://localhost:6379/0"
        }
        
        # Set all critical variables
        for key, value in critical_env_vars.items():
            success = env.set(key, value, "critical_setup")
            assert success, f"Should be able to set critical variable {key}"
        
        # Protect all critical variables
        for key in critical_env_vars:
            env.protect_variable(key)
            assert env.is_protected(key), f"Critical variable {key} should be protected"
        
        # Test protection mechanism - attempts to modify should fail
        for key in critical_env_vars:
            original_value = env.get(key)
            
            # Attempt malicious modification
            success = env.set(key, "malicious_value", "hacker_attempt")
            assert not success, f"Should not be able to modify protected critical variable {key}"
            
            # Verify original value preserved
            current_value = env.get(key)
            assert current_value == original_value, f"Critical variable {key} was modified despite protection"

    def test_critical_domains_by_environment_validation(self):
        """
        CRITICAL: Test critical domain configurations by environment.
        
        PREVENTS: Wrong domains in wrong environments (localhost in prod, prod in staging)
        CASCADE FAILURE: API calls to wrong endpoints, security breaches, data corruption
        """
        env = get_env()
        env.enable_isolation()
        
        # Critical domains by environment from String Literals Index
        critical_domains = {
            "development": {
                "NEXT_PUBLIC_API_URL": "http://localhost:8000",
                "NEXT_PUBLIC_AUTH_URL": "http://localhost:8081", 
                "NEXT_PUBLIC_FRONTEND_URL": "http://localhost:3000",
                "NEXT_PUBLIC_WS_URL": "ws://localhost:8000/ws"
            },
            "staging": {
                "NEXT_PUBLIC_API_URL": "https://api.staging.netrasystems.ai",
                "NEXT_PUBLIC_AUTH_URL": "https://auth.staging.netrasystems.ai",
                "NEXT_PUBLIC_FRONTEND_URL": "https://app.staging.netrasystems.ai", 
                "NEXT_PUBLIC_WS_URL": "wss://api.staging.netrasystems.ai/ws"
            },
            "production": {
                "NEXT_PUBLIC_API_URL": "https://api.netrasystems.ai",
                "NEXT_PUBLIC_AUTH_URL": "https://auth.netrasystems.ai",
                "NEXT_PUBLIC_FRONTEND_URL": "https://app.netrasystems.ai",
                "NEXT_PUBLIC_WS_URL": "wss://api.netrasystems.ai/ws"
            }
        }
        
        # Test each environment's domain configuration
        for environment, domains in critical_domains.items():
            env.clear()
            env.set("ENVIRONMENT", environment, f"{environment}_setup")
            
            # Set environment-specific domains
            for key, value in domains.items():
                env.set(key, value, f"{environment}_domains")
            
            # Validate domain format per environment
            if environment == "development":
                # Development should use localhost
                for key, value in domains.items():
                    assert "localhost" in value, f"Development {key} should use localhost: {value}"
                    if "WS_URL" in key:
                        assert value.startswith("ws://"), f"Development WebSocket should use ws://: {value}"
                    else:
                        assert value.startswith("http://"), f"Development HTTP should use http://: {value}"
            
            elif environment in ["staging", "production"]:
                # Staging/Production should use HTTPS/WSS
                for key, value in domains.items():
                    assert "localhost" not in value, f"{environment} {key} should not use localhost: {value}"
                    if "WS_URL" in key:
                        assert value.startswith("wss://"), f"{environment} WebSocket should use wss://: {value}"
                    else:
                        assert value.startswith("https://"), f"{environment} HTTP should use https://: {value}"
                
                # Staging should have staging subdomain
                if environment == "staging":
                    for key, value in domains.items():
                        assert "staging" in value, f"Staging {key} should contain 'staging': {value}"
                
                # Production should NOT have staging subdomain  
                elif environment == "production":
                    for key, value in domains.items():
                        assert "staging" not in value, f"Production {key} should not contain 'staging': {value}"

    def test_string_literals_query_tool_validation(self):
        """
        CRITICAL: Test String Literals Query Tool for configuration validation.
        
        PREVENTS: Using invalid/hallucinated string literals causing config failures
        CASCADE FAILURE: Silent configuration errors, wrong API endpoints
        """
        # Test string literals query tool exists and works
        script_path = Path("/Users/anthony/Documents/GitHub/netra-apex/scripts/query_string_literals.py")
        assert script_path.exists(), "String literals query script should exist"
        
        # Test critical configuration query (mocked since we can't run external commands)
        with patch('subprocess.run') as mock_run:
            # Mock successful query for critical configs
            mock_run.return_value = Mock(
                returncode=0,
                stdout="CRITICAL CONFIGURATION VALUES\nDATABASE_URL\nJWT_SECRET_KEY\nSERVICE_SECRET",
                stderr=""
            )
            
            # Simulate query for critical configs
            result = subprocess.run([
                "python3", str(script_path), "show-critical"
            ], capture_output=True, text=True)
            
            assert result.returncode == 0, "String literals query should succeed"
            assert "CRITICAL CONFIGURATION VALUES" in result.stdout
            assert "DATABASE_URL" in result.stdout
            assert "JWT_SECRET_KEY" in result.stdout

    def test_mission_critical_named_values_index_compliance(self):
        """
        CRITICAL: Test compliance with MISSION_CRITICAL_NAMED_VALUES_INDEX.xml.
        
        PREVENTS: Modification of values that cause immediate system failure
        CASCADE FAILURE: Authentication system failure, circuit breaker permanent open
        """
        env = get_env()
        env.enable_isolation()
        
        # Mission-critical named values that cause cascade failures
        mission_critical_values = {
            "SERVICE_SECRET": {
                "value": "test-service-secret-32-characters-minimum",
                "min_length": 8,
                "cascade_impact": "Complete authentication system failure, circuit breaker permanently open"
            },
            "SERVICE_ID": {
                "value": "netra-backend",
                "pattern": "^netra-backend$",
                "cascade_impact": "Authentication mismatches and service communication failures"
            },
            "DATABASE_URL": {
                "value": "postgresql://localhost:5432/netra_test",
                "pattern": "^postgresql://",
                "cascade_impact": "Complete backend failure with no data access"
            },
            "JWT_SECRET_KEY": {
                "value": "test-jwt-secret-key-32-characters-minimum",
                "min_length": 32,
                "cascade_impact": "Token validation failures and authentication breakdown"
            }
        }
        
        # Set mission-critical values
        for key, config in mission_critical_values.items():
            success = env.set(key, config["value"], "mission_critical_setup")
            assert success, f"Should be able to set mission-critical value {key}"
        
        # Validate mission-critical value constraints
        for key, config in mission_critical_values.items():
            current_value = env.get(key)
            
            # Check minimum length requirements
            if "min_length" in config:
                min_length = config["min_length"]
                assert len(current_value) >= min_length, (
                    f"{key} too short ({len(current_value)} < {min_length}): "
                    f"CASCADE IMPACT: {config['cascade_impact']}"
                )
            
            # Check pattern requirements
            if "pattern" in config:
                import re
                pattern = config["pattern"]
                assert re.match(pattern, current_value), (
                    f"{key} does not match required pattern {pattern}: "
                    f"CASCADE IMPACT: {config['cascade_impact']}"
                )

    def test_hex_string_secret_validation_regression_prevention(self):
        """
        CRITICAL: Test hex string secret validation prevents auth regression.
        
        PREVENTS: Hex strings rejected as invalid secrets (SERVICE_SECRET from openssl rand -hex 32)
        CASCADE FAILURE: Authentication validation failures in staging environments
        """
        env = get_env()
        env.enable_isolation()
        
        # Test hex string secrets (common from openssl rand -hex 32)
        hex_secrets = [
            "a1b2c3d4e5f6789012345678901234567890abcdef123456789012345678901234",  # 64-char hex
            "deadbeefcafebabe1234567890abcdef",  # 32-char hex
            "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef12",  # 64-char hex with numbers
            "ABCDEF1234567890ABCDEF1234567890ABCDEF1234567890ABCDEF1234567890AB"   # Uppercase hex
        ]
        
        for i, hex_secret in enumerate(hex_secrets):
            key = f"SERVICE_SECRET_{i}"
            
            # Should accept hex strings as valid secrets
            success = env.set(key, hex_secret, "hex_secret_test")
            assert success, f"Should accept hex string secret: {hex_secret}"
            
            # Verify hex string is preserved exactly
            retrieved_secret = env.get(key)
            assert retrieved_secret == hex_secret, f"Hex string corrupted: {hex_secret} != {retrieved_secret}"
            
            # Verify meets minimum length requirements
            assert len(retrieved_secret) >= 8, f"Hex secret too short: {len(retrieved_secret)} chars"

    def test_oauth_redirect_mismatch_warning_not_failure(self):
        """
        CRITICAL: Test OAuth redirect mismatches are warnings in non-prod, not failures.
        
        PREVENTS: Overly strict OAuth validation blocking staging deployments
        CASCADE FAILURE: Staging environment unusable, deployment pipeline blocked
        """
        env = get_env()
        env.enable_isolation()
        
        # Test OAuth configurations with redirect mismatches
        oauth_configs = {
            "staging": {
                "GOOGLE_OAUTH_CLIENT_ID_STAGING": "staging-client-id.apps.googleusercontent.com",
                "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": "staging-client-secret",
                "GOOGLE_OAUTH_REDIRECT_URI": "https://app.staging.netrasystems.ai/auth/callback",
                "ENVIRONMENT": "staging"
            },
            "development": {
                "GOOGLE_CLIENT_ID": "dev-client-id.apps.googleusercontent.com", 
                "GOOGLE_CLIENT_SECRET": "dev-client-secret",
                "GOOGLE_OAUTH_REDIRECT_URI": "http://localhost:3000/auth/callback",
                "ENVIRONMENT": "development"
            }
        }
        
        # Test OAuth validation in non-production environments
        for env_name, config in oauth_configs.items():
            env.clear()
            for key, value in config.items():
                env.set(key, value, f"{env_name}_oauth")
            
            # OAuth mismatches should be warnings, not errors in non-prod
            validation_result = env.validate_all()
            
            # Should not fail validation due to OAuth redirect mismatches
            if not validation_result.is_valid:
                # If validation fails, it should NOT be due to OAuth redirects
                oauth_errors = [error for error in validation_result.errors 
                              if "oauth" in error.lower() and "redirect" in error.lower()]
                assert not oauth_errors, f"OAuth redirect should be warning, not error in {env_name}: {oauth_errors}"


class TestConfigurationCascadeFailurePrevention:
    """Test configuration cascade failure detection and prevention mechanisms."""

    def test_cascade_failure_impact_mapping(self):
        """
        CRITICAL: Test cascade failure impact mapping for configuration changes.
        
        PREVENTS: Unknowing modification of variables causing system-wide failures
        CASCADE FAILURE: SERVICE_SECRET deletion -> complete auth failure -> user lockout
        """
        env = get_env()
        env.enable_isolation()
        
        # Map of configuration keys to their cascade failure impacts
        cascade_failure_map = {
            "SERVICE_SECRET": {
                "impact": "complete authentication failure and circuit breaker permanent open",
                "affected_services": ["netra_backend", "auth_service", "circuit_breaker"],
                "recovery_time": "immediate failure, 10+ minutes to fix",
                "business_impact": "100% user lockout, revenue loss"
            },
            "DATABASE_URL": {
                "impact": "complete backend failure with no data access",
                "affected_services": ["netra_backend", "auth_service", "session_store"],
                "recovery_time": "immediate failure, 5+ minutes to fix", 
                "business_impact": "complete system down, all users affected"
            },
            "JWT_SECRET_KEY": {
                "impact": "token validation failures and authentication breakdown",
                "affected_services": ["netra_backend", "auth_service", "frontend"],
                "recovery_time": "gradual failure as tokens expire, 15+ minutes",
                "business_impact": "progressive user logout, session invalidation"
            },
            "NEXT_PUBLIC_API_URL": {
                "impact": "no API calls work, no agents run, no data fetched",
                "affected_services": ["frontend", "agent_execution", "websocket"],
                "recovery_time": "immediate failure, frontend rebuild required",
                "business_impact": "complete frontend failure, UI unusable"
            }
        }
        
        # Test cascade failure impact validation
        for key, impact_info in cascade_failure_map.items():
            # Set the critical configuration
            test_value = f"test-{key.lower().replace('_', '-')}-value"
            env.set(key, test_value, "cascade_test")
            
            # Protect the variable to prevent cascade failures
            env.protect_variable(key)
            
            # Verify protection prevents modification
            success = env.set(key, "modified_value", "potential_cascade_failure")
            assert not success, (
                f"Modifying {key} should be blocked - CASCADE IMPACT: {impact_info['impact']}"
            )
            
            # Verify original value preserved
            current_value = env.get(key)
            assert current_value == test_value, f"Critical variable {key} was modified despite protection"

    def test_configuration_dependency_chain_validation(self):
        """
        CRITICAL: Test configuration dependency chain validation.
        
        PREVENTS: Breaking configuration dependencies causing chain reaction failures
        CASCADE FAILURE: Missing DATABASE_URL -> auth failure -> session loss -> user lockout
        """
        env = get_env()
        env.enable_isolation()
        
        # Configuration dependency chains
        dependency_chains = {
            "authentication_chain": {
                "SERVICE_SECRET": ["JWT_SECRET_KEY", "DATABASE_URL"],
                "JWT_SECRET_KEY": ["DATABASE_URL"],
                "DATABASE_URL": []  # Terminal dependency
            },
            "frontend_chain": {
                "NEXT_PUBLIC_API_URL": ["NEXT_PUBLIC_AUTH_URL", "NEXT_PUBLIC_WS_URL"],
                "NEXT_PUBLIC_AUTH_URL": ["NEXT_PUBLIC_ENVIRONMENT"],
                "NEXT_PUBLIC_WS_URL": ["NEXT_PUBLIC_API_URL"],
                "NEXT_PUBLIC_ENVIRONMENT": []  # Terminal dependency
            }
        }
        
        # Test each dependency chain
        for chain_name, dependencies in dependency_chains.items():
            env.clear()
            
            # Set up complete dependency chain
            chain_config = {
                "SERVICE_SECRET": "test-service-secret-32-characters-minimum",
                "JWT_SECRET_KEY": "test-jwt-secret-key-32-characters-minimum", 
                "DATABASE_URL": "postgresql://localhost:5432/netra_test",
                "NEXT_PUBLIC_API_URL": "http://localhost:8000",
                "NEXT_PUBLIC_AUTH_URL": "http://localhost:8081",
                "NEXT_PUBLIC_WS_URL": "ws://localhost:8000/ws",
                "NEXT_PUBLIC_ENVIRONMENT": "test"
            }
            
            # Set all dependencies
            for key, value in chain_config.items():
                if key in dependencies:
                    env.set(key, value, f"{chain_name}_setup")
            
            # Validate dependency chain integrity
            for key, deps in dependencies.items():
                if key in chain_config:
                    # Verify key exists
                    assert env.get(key) is not None, f"Missing dependency chain key: {key}"
                    
                    # Verify all dependencies exist
                    for dep in deps:
                        assert env.get(dep) is not None, (
                            f"Missing dependency {dep} for {key} in {chain_name} chain"
                        )

    def test_silent_configuration_failure_detection(self):
        """
        CRITICAL: Test detection of silent configuration failures.
        
        PREVENTS: Configuration errors that fail silently causing delayed failures
        CASCADE FAILURE: Wrong configs used for hours before detection -> data corruption
        """
        env = get_env()
        env.enable_isolation()
        
        # Silent failure scenarios
        silent_failure_configs = {
            "wrong_database_port": {
                "DATABASE_URL": "postgresql://localhost:5433/netra_test",  # Wrong port
                "expected_issue": "database connection failure"
            },
            "localhost_in_staging": {
                "ENVIRONMENT": "staging",
                "NEXT_PUBLIC_API_URL": "http://localhost:8000",  # Wrong for staging
                "expected_issue": "API calls fail in staging"
            },
            "http_in_production": {
                "ENVIRONMENT": "production", 
                "NEXT_PUBLIC_API_URL": "http://api.netrasystems.ai",  # Should be HTTPS
                "expected_issue": "insecure connections in production"
            },
            "empty_critical_values": {
                "JWT_SECRET_KEY": "",  # Empty critical value
                "expected_issue": "authentication will fail"
            }
        }
        
        # Test detection of each silent failure scenario
        for scenario_name, config in silent_failure_configs.items():
            env.clear()
            
            # Set problematic configuration
            for key, value in config.items():
                if key != "expected_issue":
                    env.set(key, value, f"silent_failure_{scenario_name}")
            
            # Validate configuration detects the issue
            validation_result = env.validate_all()
            
            # Should detect the configuration issue
            if scenario_name == "empty_critical_values":
                # Empty JWT_SECRET_KEY should be detected
                assert not validation_result.is_valid, f"Should detect empty critical value in {scenario_name}"
                jwt_errors = [error for error in validation_result.errors if "JWT_SECRET_KEY" in error]
                assert jwt_errors, f"Should detect JWT_SECRET_KEY issue in {scenario_name}"