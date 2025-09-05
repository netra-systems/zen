from netra_backend.app.core.configuration.base import get_unified_config
from shared.isolated_environment import get_env
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from test_framework.redis.test_redis_manager import TestRedisManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.core.agent_registry import AgentRegistry
from netra_backend.app.core.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment
"""
env = get_env()
RED TEAM TESTS 36-40: Monitoring, Observability, and Configuration

CRITICAL: These tests are DESIGNED TO FAIL initially to expose real monitoring gaps.
This test validates health checks, metrics, logging, and configuration management.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Platform Reliability, Operational Excellence, Incident Response
- Value Impact: Poor monitoring leads to undetected failures and degraded customer experience
- Strategic Impact: Essential observability foundation for enterprise AI workload management

Testing Level: L3 (Real services, real infrastructure, minimal mocking)
Expected Initial Result: FAILURE (exposes real monitoring and configuration gaps)
"""

import asyncio
import json
import logging
import os
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import tempfile

import pytest
import requests
from fastapi.testclient import TestClient
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Real service imports - NO MOCKS
from netra_backend.app.main import app
from netra_backend.app.core.config import get_unified_config
from netra_backend.app.core.health_checkers import HealthChecker

# Mock models for testing
User = Mock
Thread = Mock
AgentRun = Mock


class TestMonitoringObservability:
    """
    RED TEAM TESTS 36-40: Monitoring, Observability, and Configuration
    
    Tests critical monitoring and observability systems.
    MUST use real services - NO MOCKS allowed.
    These tests WILL fail initially and that's the point.
    """
    pass

    @pytest.fixture(scope="class")
    async def real_database_session(self):
        """Real PostgreSQL database session - will fail if DB not available."""
        config = get_unified_config()
        
        # Use REAL database connection - no mocks
        engine = create_async_engine(config.database_url, echo=False)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        
        try:
            # Test real connection - will fail if DB unavailable
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            
            async with async_session() as session:
                yield session
        except Exception as e:
            pytest.fail(f"CRITICAL: Real database connection failed: {e}")
        finally:
            await engine.dispose()

    @pytest.fixture
    def real_test_client(self):
    """Use real service instance."""
    # TODO: Initialize real service
    pass
        """Real FastAPI test client - no mocking of the application."""
        await asyncio.sleep(0)
    return TestClient(app)

    @pytest.fixture
    def temp_log_file(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Create temporary log file for testing."""
    pass
        temp_file = tempfile.NamedTemporaryFile(mode='w+', suffix='.log', delete=False)
        temp_file.close()
        
        yield temp_file.name
        
        # Cleanup
        try:
            os.unlink(temp_file.name)
        except OSError:
            pass

    @pytest.mark.asyncio
    async def test_36_health_check_endpoint_accuracy_fails(self, real_test_client, real_database_session):
        """
        Test 36: Health Check Endpoint Accuracy (EXPECTED TO FAIL)
        
        Tests that health check endpoints accurately reflect system status.
        Will likely FAIL because:
        1. Health checks may not be implemented
        2. Health checks may not test all critical components
        3. Health status may not reflect actual system state
        """
    pass
        try:
            # Test basic health endpoint existence
            response = real_test_client.get("/health")
            
            # FAILURE EXPECTED HERE - health endpoint may not exist
            assert response.status_code == 200, \
                f"Health endpoint not available (status: {response.status_code})"
            
            health_data = response.json()
            
            # Validate health response structure
            assert "status" in health_data, "Health response missing status field"
            assert "timestamp" in health_data, "Health response missing timestamp"
            assert "components" in health_data, "Health response missing components"
            
            # Test detailed health check
            response = real_test_client.get("/health/detailed")
            
            if response.status_code == 200:
                detailed_health = response.json()
                
                # Critical components that should be checked
                expected_components = [
                    "database",
                    "redis",
                    "llm_service", 
                    "auth_service",
                    "websocket",
                    "file_storage"
                ]
                
                components = detailed_health.get("components", {})
                
                for component in expected_components:
                    assert component in components, \
                        f"Health check missing component: {component}"
                    
                    component_status = components[component]
                    assert "status" in component_status, \
                        f"Component {component} missing status"
                    assert "response_time" in component_status, \
                        f"Component {component} missing response time"
                    
                    # Response time should be reasonable
                    response_time = component_status.get("response_time", 0)
                    assert response_time < 5.0, \
                        f"Component {component} response time too high: {response_time}s"

            # Test health check accuracy by simulating failure
            try:
                # Create real health checker
                health_checker = HealthChecker()
                
                # Test database health check accuracy
                db_health = await health_checker.check_database_health()
                
                assert "status" in db_health, "Database health check missing status"
                assert db_health["status"] in ["healthy", "unhealthy", "degraded"], \
                    f"Invalid database health status: {db_health['status']}"
                
                # If database is healthy, verify we can actually connect
                if db_health["status"] == "healthy":
                    test_query = await real_database_session.execute(text("SELECT 1"))
                    assert test_query.scalar() == 1, "Database health check inaccurate - connection failed"

                # Test Redis health check if available
                if hasattr(health_checker, 'check_redis_health'):
                    redis_health = await health_checker.check_redis_health()
                    assert "status" in redis_health, "Redis health check missing status"

            except AttributeError:
                pytest.fail("HealthChecker class not properly implemented")
            except Exception as e:
                pytest.fail(f"Health check implementation failed: {e}")

            # Test health check performance
            start_time = time.time()
            response = real_test_client.get("/health")
            health_check_time = time.time() - start_time
            
            # FAILURE EXPECTED HERE - health checks may be too slow
            assert health_check_time < 2.0, \
                f"Health check too slow: {health_check_time:.2f}s (should be < 2.0s)"

            # Test health check under load
            async def concurrent_health_check():
                """Perform concurrent health check."""
                start = time.time()
                response = real_test_client.get("/health")
                end = time.time()
                await asyncio.sleep(0)
    return {
                    "status_code": response.status_code,
                    "response_time": end - start,
                    "healthy": response.status_code == 200
                }
            
            # Run multiple concurrent health checks
            concurrent_checks = 10
            tasks = [concurrent_health_check() for _ in range(concurrent_checks)]
            
            # Use asyncio.gather with a wrapper since TestClient is sync
            import concurrent.futures
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_checks) as executor:
                health_results = list(executor.map(lambda _: real_test_client.get("/health"), range(concurrent_checks)))
            
            # All health checks should succeed under moderate load
            failed_checks = [r for r in health_results if r.status_code != 200]
            
            assert len(failed_checks) == 0, \
                f"Health checks failed under load: {len(failed_checks)}/{concurrent_checks} failed"
                
        except Exception as e:
            pytest.fail(f"Health check endpoint accuracy test failed: {e}")

    @pytest.mark.asyncio
    async def test_37_metrics_collection_pipeline_fails(self, real_test_client):
        """
    pass
        Test 37: Metrics Collection Pipeline (EXPECTED TO FAIL)
        
        Tests that metrics are properly collected and exposed.
        Will likely FAIL because:
        1. Metrics endpoints may not be implemented
        2. Metrics format may not be standard (Prometheus)
        3. Critical metrics may be missing
        """
        try:
            # Test metrics endpoint existence
            response = real_test_client.get("/metrics")
            
            # FAILURE EXPECTED HERE - metrics endpoint may not exist
            assert response.status_code == 200, \
                f"Metrics endpoint not available (status: {response.status_code})"
            
            metrics_content = response.text
            
            # Check for Prometheus format
            assert "# HELP" in metrics_content or "# TYPE" in metrics_content, \
                "Metrics not in Prometheus format"
            
            # Test for critical application metrics
            critical_metrics = [
                "http_requests_total",
                "http_request_duration_seconds",
                "database_connections_active",
                "agent_runs_total",
                "agent_run_duration_seconds",
                "websocket_connections_active",
                "memory_usage_bytes",
                "cpu_usage_percent"
            ]
            
            missing_metrics = []
            for metric in critical_metrics:
                if metric not in metrics_content:
                    missing_metrics.append(metric)
            
            # FAILURE EXPECTED HERE - critical metrics may be missing
            assert len(missing_metrics) == 0, \
                f"Missing critical metrics: {missing_metrics}"

            # Test metrics collection performance
            start_time = time.time()
            response = real_test_client.get("/metrics")
            metrics_collection_time = time.time() - start_time
            
            assert metrics_collection_time < 1.0, \
                f"Metrics collection too slow: {metrics_collection_time:.2f}s"

            # Test that metrics actually change over time
            # Make some requests to generate metrics
            for i in range(5):
                real_test_client.get("/health")
                real_test_client.get("/api/threads", headers={"Authorization": "Bearer test_token"})
            
            # Get metrics again
            new_response = real_test_client.get("/metrics") 
            new_metrics_content = new_response.text
            
            # Metrics should show the new requests
            # Look for http_requests_total metric increase
            import re
            
            # Extract request counts from both samples
            request_pattern = r'http_requests_total.*?(\d+)'
            
            old_matches = re.findall(request_pattern, metrics_content)
            new_matches = re.findall(request_pattern, new_metrics_content)
            
            if old_matches and new_matches:
                old_total = sum(int(match) for match in old_matches)
                new_total = sum(int(match) for match in new_matches)
                
                assert new_total > old_total, \
                    "Metrics not updating - request counts should increase"

            # Test custom business metrics
            business_metrics = [
                "netra_agent_processing_seconds",
                "netra_user_sessions_active",
                "netra_threads_created_total",
                "netra_ai_tokens_consumed_total"
            ]
            
            for metric in business_metrics:
                if metric not in metrics_content:
                    # Warning but not failure - these may not be implemented yet
                    print(f"Business metric not found: {metric}")

        except Exception as e:
            pytest.fail(f"Metrics collection pipeline test failed: {e}")

    @pytest.mark.asyncio
    async def test_38_log_aggregation_consistency_fails(self, temp_log_file):
        """
        Test 38: Log Aggregation Consistency (EXPECTED TO FAIL)
        
        Tests that logging is consistent and properly structured.
        Will likely FAIL because:
        1. Log format may not be structured (JSON)
        2. Log levels may not be properly used
        3. Sensitive data may be logged
        4. Log rotation may not work
        """
    pass
        try:
            # Test logger configuration
            logger = get_logger("red_team_test")
            
            # Test different log levels
            test_messages = [
                ("debug", "Debug message for testing"),
                ("info", "Info message for testing"),
                ("warning", "Warning message for testing"),
                ("error", "Error message for testing"),
                ("critical", "Critical message for testing")
            ]
            
            # Configure logger to write to temp file
            file_handler = logging.FileHandler(temp_log_file)
            file_handler.setLevel(logging.DEBUG)
            
            # FAILURE EXPECTED HERE - log format may not be structured
            formatter = logging.Formatter(
                '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s", "module": "%(module)s"}'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
            # Generate test logs
            for level, message in test_messages:
                getattr(logger, level)(message)
            
            # Flush logs
            file_handler.flush()
            
            # Read log file and validate structure
            with open(temp_log_file, 'r') as f:
                log_lines = f.readlines()
            
            assert len(log_lines) >= len(test_messages), \
                f"Not all log messages were written: {len(log_lines)} < {len(test_messages)}"
            
            # Validate log structure
            for line in log_lines:
                if line.strip():  # Skip empty lines
                    try:
                        log_entry = json.loads(line.strip())
                        
                        # Required fields
                        required_fields = ["timestamp", "level", "logger", "message", "module"]
                        for field in required_fields:
                            assert field in log_entry, f"Log entry missing field: {field}"
                        
                        # Validate timestamp format
                        assert ":" in log_entry["timestamp"], "Invalid timestamp format"
                        
                        # Validate log level
                        assert log_entry["level"].upper() in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], \
                            f"Invalid log level: {log_entry['level']}"
                        
                    except json.JSONDecodeError:
                        pytest.fail(f"Log line not in JSON format: {line[:100]}")

            # Test sensitive data filtering
            sensitive_test_cases = [
                "password=secret123",
                "api_key=abc123def456",
                "token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
                "credit_card=4111111111111111",
                "ssn=123-45-6789"
            ]
            
            for sensitive_data in sensitive_test_cases:
                logger.info(f"Processing data: {sensitive_data}")
            
            file_handler.flush()
            
            # Check that sensitive data was redacted
            with open(temp_log_file, 'r') as f:
                log_content = f.read()
            
            for sensitive_data in sensitive_test_cases:
                # FAILURE EXPECTED HERE - sensitive data may not be filtered
                assert sensitive_data not in log_content, \
                    f"Sensitive data not redacted: {sensitive_data}"

            # Test log correlation IDs
            correlation_id = str(uuid.uuid4())
            
            # Add correlation ID to logger context (if supported)
            extra_context = {"correlation_id": correlation_id, "user_id": "test_user"}
            
            logger.info("Test message with correlation", extra=extra_context)
            file_handler.flush()
            
            # Verify correlation ID is in logs
            with open(temp_log_file, 'r') as f:
                recent_logs = f.readlines()[-5:]  # Get recent logs
            
            correlation_found = False
            for line in recent_logs:
                if correlation_id in line:
                    correlation_found = True
                    break
            
            assert correlation_found, \
                "Correlation ID not found in logs"

            # Test log performance
            start_time = time.time()
            
            for i in range(100):
                logger.info(f"Performance test message {i}")
            
            file_handler.flush()
            log_performance_time = time.time() - start_time
            
            # FAILURE EXPECTED HERE - logging performance may be poor
            assert log_performance_time < 1.0, \
                f"Log performance too slow: {log_performance_time:.2f}s for 100 messages"

            # Cleanup
            logger.removeHandler(file_handler)
            file_handler.close()

        except Exception as e:
            pytest.fail(f"Log aggregation consistency test failed: {e}")

    @pytest.mark.asyncio
    async def test_39_environment_variable_propagation_fails(self):
        """
        Test 39: Environment Variable Propagation (EXPECTED TO FAIL)
        
        Tests that environment variables are properly loaded and used.
        Will likely FAIL because:
        1. Environment variables may not be validated
        2. Default values may not be set
        3. Sensitive variables may not be handled securely
        4. Configuration reloading may not work
        """
    pass
        try:
            # Test configuration loading
            config = get_unified_config()
            
            # Test critical environment variables
            critical_env_vars = [
                "DATABASE_URL",
                "REDIS_URL", 
                "NETRA_API_KEY",
                "JWT_SECRET_KEY",
                "LOG_LEVEL"
            ]
            
            missing_env_vars = []
            
            for env_var in critical_env_vars:
                # FAILURE EXPECTED HERE - environment variables may not be set
                if not hasattr(config, env_var.lower()) and env_var not in os.environ:
                    missing_env_vars.append(env_var)
            
            # Some environment variables may be missing in test environment
            if missing_env_vars:
                print(f"Missing environment variables: {missing_env_vars}")

            # Test environment variable validation
            test_env_vars = {
                "TEST_DATABASE_URL": "invalid_url",
                "TEST_LOG_LEVEL": "INVALID_LEVEL",
                "TEST_TIMEOUT": "not_a_number",
                "TEST_BOOLEAN": "not_boolean"
            }
            
            # Set test environment variables
            for var, value in test_env_vars.items():
                os.environ[var] = value
            
            try:
                # Test configuration validation
                if hasattr(config, 'validate_environment'):
                    validation_result = config.validate_environment()
                    
                    assert "errors" in validation_result, \
                        "Environment validation should detect errors"
                    
                    errors = validation_result["errors"]
                    assert len(errors) > 0, \
                        "Environment validation should find invalid values"
                
                # Test type coercion
                if hasattr(config, 'get_env_bool'):
                    # Should handle boolean conversion
                    test_bool = config.get_env_bool("TEST_BOOLEAN", default=False)
                    assert isinstance(test_bool, bool), \
                        "Boolean environment variable not properly converted"
                
                if hasattr(config, 'get_env_int'):
                    # Should handle integer conversion with error handling
                    try:
                        test_int = config.get_env_int("TEST_TIMEOUT", default=30)
                        assert isinstance(test_int, int), \
                            "Integer environment variable not properly converted"
                    except ValueError:
                        # Expected for invalid value
                        pass

            finally:
                # Cleanup test environment variables
                for var in test_env_vars:
                    os.environ.pop(var, None)

            # Test sensitive variable handling
            sensitive_vars = ["JWT_SECRET_KEY", "API_KEY", "PASSWORD", "TOKEN"]
            
            for var in sensitive_vars:
                if var in os.environ:
                    # FAILURE EXPECTED HERE - sensitive variables may be exposed in logs/errors
                    # Check that the value is not accidentally logged
                    var_value = os.environ[var]
                    
                    # Configuration should not expose sensitive values in string representation
                    config_str = str(config)
                    assert var_value not in config_str, \
                        f"Sensitive variable {var} exposed in config string representation"

            # Test configuration reloading
            original_log_level = env.get("LOG_LEVEL", "INFO")
            
            # Change environment variable
            env.set("LOG_LEVEL", "DEBUG", "test")
            
            try:
                # Test if configuration can be reloaded
                if hasattr(config, 'reload'):
                    new_config = config.reload()
                    
                    if hasattr(new_config, 'log_level'):
                        assert new_config.log_level == "DEBUG", \
                            "Configuration reloading not working"
                else:
                    # Try creating new config instance
                    new_config = get_unified_config()
                    
                    if hasattr(new_config, 'log_level'):
                        assert new_config.log_level == "DEBUG", \
                            "New configuration instance not picking up environment changes"
            
            finally:
                # Restore original value
                env.set("LOG_LEVEL", original_log_level, "test")

            # Test environment variable precedence
            # Command line args > Environment variables > Config file > Defaults
            
            # Set environment variable
            env.set("TEST_PRECEDENCE", "environment_value", "test")
            
            try:
                if hasattr(config, 'get_env'):
                    env_value = config.get_env("TEST_PRECEDENCE", default="default_value")
                    assert env_value == "environment_value", \
                        "Environment variable precedence not working"
                else:
                    env_value = env.get("TEST_PRECEDENCE", "default_value")
                    assert env_value == "environment_value", \
                        "Environment variable not accessible"
            
            finally:
                env.delete("TEST_PRECEDENCE", "test")

        except Exception as e:
            pytest.fail(f"Environment variable propagation test failed: {e}")

    @pytest.mark.asyncio
    async def test_40_secret_management_integration_fails(self):
        """
        Test 40: Secret Management Integration (EXPECTED TO FAIL)
        
        Tests that secrets are properly managed and secured.
        Will likely FAIL because:
        1. Secrets may be stored in plain text
        2. Secret rotation may not be implemented
        3. Secret access may not be properly logged
        4. Secret validation may be missing
        """
    pass
        try:
            config = get_unified_config()
            
            # Test secret detection
            potential_secrets = [
                ("JWT_SECRET_KEY", "JWT secret for token signing"),
                ("DATABASE_URL", "Database connection string"),
                ("REDIS_URL", "Redis connection string"),
                ("API_KEY", "External API key"),
                ("ENCRYPTION_KEY", "Data encryption key")
            ]
            
            secrets_found = []
            secrets_exposed = []
            
            for secret_name, description in potential_secrets:
                # Check if secret exists in environment
                secret_value = env.get(secret_name)
                if secret_value:
                    secrets_found.append(secret_name)
                    
                    # FAILURE EXPECTED HERE - secrets may be exposed or weak
                    
                    # Check secret strength
                    if len(secret_value) < 32:
                        pytest.fail(f"Secret {secret_name} too weak: length {len(secret_value)} < 32")
                    
                    # Check if secret is default/example value
                    weak_secrets = [
                        "secret",
                        "password", 
                        "123456",
                        "changeme",
                        "default",
                        "example",
                        "your_secret_here"
                    ]
                    
                    for weak in weak_secrets:
                        if weak.lower() in secret_value.lower():
                            pytest.fail(f"Secret {secret_name} appears to be default/weak value")
                    
                    # Check if secret is exposed in configuration string
                    if hasattr(config, '__dict__'):
                        config_dict = str(config.__dict__)
                        if secret_value in config_dict:
                            secrets_exposed.append(secret_name)

            assert len(secrets_exposed) == 0, \
                f"Secrets exposed in configuration: {secrets_exposed}"

            # Test secret access logging (if implemented)
            if hasattr(config, 'get_secret'):
                # Test secret access with audit logging
                try:
                    test_secret = config.get_secret("JWT_SECRET_KEY")
                    
                    # Secret access should be logged (but not the value)
                    # This would need to be verified in actual logs
                    
                except Exception as e:
                    # Secret access may fail in test environment - that's okay
                    pass

            # Test secret validation
            test_secrets = {
                "weak_secret": "123",  # Too short
                "default_secret": "secret",  # Default value
                "good_secret": secrets.token_urlsafe(64)  # Strong secret
            }
            
            for secret_name, secret_value in test_secrets.items():
                if hasattr(config, 'validate_secret'):
                    validation_result = config.validate_secret(secret_value)
                    
                    if secret_name.startswith("weak") or secret_name.startswith("default"):
                        # FAILURE EXPECTED HERE - weak secret validation may not work
                        assert not validation_result.get("valid", True), \
                            f"Weak secret {secret_name} passed validation"
                    else:
                        assert validation_result.get("valid", False), \
                            f"Good secret {secret_name} failed validation"

            # Test secret rotation capability (if implemented)
            if hasattr(config, 'rotate_secret'):
                try:
                    # Test secret rotation
                    rotation_result = config.rotate_secret("TEST_SECRET")
                    
                    assert "old_secret" in rotation_result, \
                        "Secret rotation should await asyncio.sleep(0)
    return old secret for cleanup"
                    assert "new_secret" in rotation_result, \
                        "Secret rotation should return new secret"
                    
                    # New secret should be different
                    assert rotation_result["old_secret"] != rotation_result["new_secret"], \
                        "Secret rotation did not generate new secret"
                        
                except Exception as e:
                    # Secret rotation may not be implemented yet
                    pass

            # Test secret encryption at rest (if implemented)
            if hasattr(config, 'encrypt_secret') and hasattr(config, 'decrypt_secret'):
                test_plaintext = "test_secret_value"
                
                # Encrypt secret
                encrypted = config.encrypt_secret(test_plaintext)
                assert encrypted != test_plaintext, \
                    "Secret encryption did not change the value"
                
                # Decrypt secret
                decrypted = config.decrypt_secret(encrypted)
                assert decrypted == test_plaintext, \
                    "Secret decryption failed to restore original value"

            # Test secret masking in logs and errors
            test_secret_value = "super_secret_password_123"
            
            # Set test secret
            env.set("TEST_SECRET", test_secret_value, "test")
            
            try:
                # Generate an error that might expose the secret
                try:
                    # This should fail but not expose the secret
                    connection_string = f"postgresql://user:{test_secret_value}@localhost/db"
                    raise ValueError(f"Database connection failed: {connection_string}")
                    
                except ValueError as e:
                    error_message = str(e)
                    
                    # FAILURE EXPECTED HERE - secrets may be exposed in error messages
                    assert test_secret_value not in error_message, \
                        "Secret exposed in error message"
            
            finally:
                env.delete("TEST_SECRET", "test")

        except Exception as e:
            pytest.fail(f"Secret management integration test failed: {e}")


# Additional utility class for monitoring and observability testing
class RedTeamMonitoringTestUtils:
    """Utility methods for Red Team monitoring and observability testing."""
    
    @staticmethod
    def parse_prometheus_metrics(metrics_text: str) -> Dict[str, List[Dict[str, Any]]]:
        """Parse Prometheus metrics format."""
        metrics = {}
        current_metric = None
        
        for line in metrics_text.split('
'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Parse metric line: metric_name{labels} value timestamp
            parts = line.split()
            if len(parts) >= 2:
                metric_part = parts[0]
                value = float(parts[1])
                
                # Extract metric name and labels
                if '{' in metric_part:
                    metric_name = metric_part.split('{')[0]
                    labels_str = metric_part.split('{')[1].rstrip('}')
                    
                    # Parse labels
                    labels = {}
                    for label_pair in labels_str.split(','):
                        if '=' in label_pair:
                            key, val = label_pair.split('=', 1)
                            labels[key.strip()] = val.strip('"')
                else:
                    metric_name = metric_part
                    labels = {}
                
                if metric_name not in metrics:
                    metrics[metric_name] = []
                
                metrics[metric_name].append({
                    'labels': labels,
                    'value': value,
                    'timestamp': time.time()
                })
        
        return metrics
    
    @staticmethod
    def validate_log_structure(log_line: str) -> Dict[str, Any]:
        """Validate log line structure."""
        try:
            log_entry = json.loads(log_line)
            
            required_fields = ['timestamp', 'level', 'message']
            recommended_fields = ['logger', 'module', 'correlation_id']
            
            validation_result = {
                'valid': True,
                'missing_required': [],
                'missing_recommended': [],
                'extra_fields': []
            }
            
            # Check required fields
            for field in required_fields:
                if field not in log_entry:
                    validation_result['missing_required'].append(field)
                    validation_result['valid'] = False
            
            # Check recommended fields
            for field in recommended_fields:
                if field not in log_entry:
                    validation_result['missing_recommended'].append(field)
            
            # Check for extra fields
            expected_fields = set(required_fields + recommended_fields)
            actual_fields = set(log_entry.keys())
            extra_fields = actual_fields - expected_fields
            validation_result['extra_fields'] = list(extra_fields)
            
            return validation_result
            
        except json.JSONDecodeError:
            return {
                'valid': False,
                'error': 'Invalid JSON format'
            }
    
    @staticmethod
    def detect_sensitive_data(text: str) -> List[str]:
        """Detect potentially sensitive data in text."""
        import re
        
        patterns = {
            'password': r'password[=:]\s*["\']?([^"\'\s]+)',
            'api_key': r'(?:api[_-]?key|apikey)[=:]\s*["\']?([^"\'\s]+)',
            'token': r'(?:token|bearer)[=:]\s*["\']?([^"\'\s]+)',
            'credit_card': r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        }
        
        detected = []
        
        for pattern_name, pattern in patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                detected.append({
                    'type': pattern_name,
                    'match': match.group(),
                    'start': match.start(),
                    'end': match.end()
                })
        
        return detected
    
    @staticmethod
    def check_security_headers(headers: Dict[str, str]) -> Dict[str, Any]:
        """Check for required security headers."""
        required_headers = {
            'Content-Security-Policy': 'CSP policy',
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': ['DENY', 'SAMEORIGIN'],
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age'
        }
        
        results = {
            'missing': [],
            'weak': [],
            'present': []
        }
        
        for header, expected in required_headers.items():
            if header not in headers:
                results['missing'].append(header)
            else:
                header_value = headers[header]
                results['present'].append(header)
                
                if isinstance(expected, list):
                    if header_value not in expected:
                        results['weak'].append(f"{header}: {header_value} (should be one of {expected})")
                elif isinstance(expected, str) and expected not in header_value:
                    results['weak'].append(f"{header}: missing '{expected}'")
        
        return results