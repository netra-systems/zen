"""
Test Configuration SSOT: IsolatedEnvironment Access Patterns

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Prevent cascade failures from configuration violations
- Value Impact: Ensures $120K+ MRR golden path stability through proper environment isolation
- Strategic Impact: Eliminates $80K+ failures from environment pollution and configuration drift

This test validates that all services properly use IsolatedEnvironment SSOT patterns
instead of direct os.environ access, preventing cascade failures that could
bring down the entire system.
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import IsolatedEnvironment, get_env


class TestIsolatedEnvironmentAccessPatterns(BaseIntegrationTest):
    """Test IsolatedEnvironment SSOT compliance and access patterns."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_isolated_environment_prevents_os_environ_pollution(self, real_services_fixture):
        """
        Test that IsolatedEnvironment isolation prevents os.environ pollution.
        
        This test validates the core SSOT principle that environment changes
        in isolation mode don't affect the system environment, preventing
        cascade failures from test pollution.
        """
        # Setup isolated environment
        env = get_env()
        env.enable_isolation()
        
        # Store original os.environ state
        original_test_var = os.environ.get("CONFIG_SSOT_TEST_VAR")
        original_critical_var = os.environ.get("SERVICE_SECRET")
        
        try:
            # Set variables in isolated environment with source tracking
            env.set("CONFIG_SSOT_TEST_VAR", "isolated_value", "test_isolation")
            env.set("SERVICE_SECRET", "test_secret_value", "test_isolation") 
            
            # CRITICAL: Verify isolation - os.environ should NOT be affected
            assert os.environ.get("CONFIG_SSOT_TEST_VAR") != "isolated_value"
            assert env.get("CONFIG_SSOT_TEST_VAR") == "isolated_value"
            
            # Verify critical SERVICE_SECRET is isolated to prevent production leakage
            if original_critical_var:
                assert os.environ.get("SERVICE_SECRET") == original_critical_var
            else:
                assert "SERVICE_SECRET" not in os.environ
            
            # Verify source tracking works
            debug_info = env.get_debug_info()
            assert "CONFIG_SSOT_TEST_VAR" in debug_info["variable_sources"]
            assert debug_info["variable_sources"]["CONFIG_SSOT_TEST_VAR"] == "test_isolation"
            
            # Test environment cleanup
            env.delete("CONFIG_SSOT_TEST_VAR")
            assert env.get("CONFIG_SSOT_TEST_VAR") is None
            
        finally:
            # Ensure test cleanup doesn't affect system
            env.reset_to_original()
            assert os.environ.get("CONFIG_SSOT_TEST_VAR") == original_test_var
            if original_critical_var:
                assert os.environ.get("SERVICE_SECRET") == original_critical_var

    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_isolated_environment_source_tracking_compliance(self, real_services_fixture):
        """
        Test that all configuration changes include proper source tracking.
        
        Source tracking is CRITICAL for debugging configuration cascade failures
        that cost $80K+ in business value. Every configuration change must be traceable.
        """
        env = get_env()
        env.enable_isolation()
        
        # Test missing source tracking should fail in strict mode
        with pytest.raises((ValueError, TypeError)):
            # This should fail because source is required for SSOT compliance
            env.set("TEST_VAR_NO_SOURCE", "value")  # No source parameter
        
        # Test proper source tracking
        test_sources = [
            ("auth_service", "AUTH_SECRET", "test_auth_value"),
            ("backend_service", "DATABASE_URL", "test_db_url"),
            ("test_framework", "REDIS_URL", "test_redis_url"),
            ("deployment_script", "SERVICE_SECRET", "test_service_secret")
        ]
        
        for source, var_name, value in test_sources:
            env.set(var_name, value, source)
            
            # Verify value set correctly
            assert env.get(var_name) == value
            
            # Verify source tracking
            debug_info = env.get_debug_info()
            assert var_name in debug_info["variable_sources"]
            assert debug_info["variable_sources"][var_name] == source
        
        # Test source tracking survives environment operations
        env.delete("AUTH_SECRET")
        debug_info = env.get_debug_info()
        # After deletion, source should be removed from tracking
        assert "AUTH_SECRET" not in debug_info["variable_sources"]
        
        # Critical: Test mission-critical variable source tracking
        env.set("SERVICE_SECRET", "critical_test_value", "ssot_compliance_test")
        debug_info = env.get_debug_info()
        assert debug_info["variable_sources"]["SERVICE_SECRET"] == "ssot_compliance_test"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_isolated_environment_file_loading_ssot_patterns(self, real_services_fixture):
        """
        Test that .env file loading follows SSOT patterns with proper source attribution.
        
        File loading is a common source of configuration drift when not properly
        managed through SSOT patterns. This prevents cascade failures from
        inconsistent environment loading.
        """
        env = get_env()
        env.enable_isolation()
        
        # Create temporary .env file with test configuration
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as temp_file:
            test_env_content = """
# Test configuration for SSOT validation
CONFIG_TEST_VAR=file_loaded_value
DATABASE_HOST=localhost
POSTGRES_USER=testuser
POSTGRES_PASSWORD=testpass
SERVICE_SECRET=file_service_secret
ENVIRONMENT=testing
"""
            temp_file.write(test_env_content.strip())
            temp_file.flush()
            
            try:
                # Load file with source tracking
                env.load_from_file(Path(temp_file.name), "test_env_file")
                
                # Verify all variables loaded correctly
                assert env.get("CONFIG_TEST_VAR") == "file_loaded_value" 
                assert env.get("DATABASE_HOST") == "localhost"
                assert env.get("POSTGRES_USER") == "testuser"
                assert env.get("SERVICE_SECRET") == "file_service_secret"
                assert env.get("ENVIRONMENT") == "testing"
                
                # CRITICAL: Verify source tracking for file-loaded variables
                debug_info = env.get_debug_info()
                file_loaded_vars = [
                    "CONFIG_TEST_VAR", "DATABASE_HOST", "POSTGRES_USER", 
                    "POSTGRES_PASSWORD", "SERVICE_SECRET", "ENVIRONMENT"
                ]
                
                for var_name in file_loaded_vars:
                    assert var_name in debug_info["variable_sources"]
                    assert debug_info["variable_sources"][var_name] == "test_env_file"
                
                # Test file loading doesn't pollute os.environ in isolation mode
                assert os.environ.get("CONFIG_TEST_VAR") != "file_loaded_value"
                
                # Test override behavior - programmatic sets should override file values
                env.set("CONFIG_TEST_VAR", "override_value", "programmatic_override")
                assert env.get("CONFIG_TEST_VAR") == "override_value"
                
                # Source should be updated
                debug_info = env.get_debug_info()
                assert debug_info["variable_sources"]["CONFIG_TEST_VAR"] == "programmatic_override"
                
            finally:
                # Cleanup
                os.unlink(temp_file.name)
                env.reset_to_original()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_isolated_environment_thread_safety_validation(self, real_services_fixture):
        """
        Test that IsolatedEnvironment operations are thread-safe under concurrent access.
        
        Thread safety is CRITICAL for multi-user systems. Configuration race conditions
        can cause cascade failures where user contexts leak between sessions,
        potentially exposing sensitive data and causing $120K+ MRR impact.
        """
        import threading
        import time
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        env = get_env()
        env.enable_isolation()
        
        # Test data for concurrent operations
        thread_count = 10
        operations_per_thread = 50
        test_results = []
        errors = []
        
        def thread_worker(thread_id: int):
            """Worker function for concurrent environment operations"""
            thread_results = []
            thread_errors = []
            
            try:
                for i in range(operations_per_thread):
                    var_name = f"THREAD_{thread_id}_VAR_{i}"
                    var_value = f"thread_{thread_id}_value_{i}"
                    source_name = f"thread_{thread_id}_source"
                    
                    # Set variable with source tracking
                    env.set(var_name, var_value, source_name)
                    
                    # Immediately read back to verify
                    retrieved_value = env.get(var_name)
                    if retrieved_value != var_value:
                        thread_errors.append(f"Value mismatch: {var_name} expected {var_value}, got {retrieved_value}")
                    
                    # Verify source tracking
                    debug_info = env.get_debug_info()
                    if var_name not in debug_info["variable_sources"]:
                        thread_errors.append(f"Missing source tracking for {var_name}")
                    elif debug_info["variable_sources"][var_name] != source_name:
                        thread_errors.append(f"Wrong source for {var_name}: expected {source_name}, got {debug_info['variable_sources'][var_name]}")
                    
                    thread_results.append((var_name, var_value, source_name))
                    
                    # Small delay to increase chances of race conditions
                    time.sleep(0.001)
                    
            except Exception as e:
                thread_errors.append(f"Thread {thread_id} exception: {str(e)}")
            
            return thread_results, thread_errors
        
        # Execute concurrent operations
        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            futures = [executor.submit(thread_worker, i) for i in range(thread_count)]
            
            for future in as_completed(futures):
                try:
                    results, thread_errors = future.result()
                    test_results.extend(results)
                    errors.extend(thread_errors)
                except Exception as e:
                    errors.append(f"Future exception: {str(e)}")
        
        # CRITICAL: No thread safety errors should occur
        assert not errors, f"Thread safety violations detected: {errors}"
        
        # Verify all operations completed successfully
        expected_total_ops = thread_count * operations_per_thread
        assert len(test_results) == expected_total_ops, f"Expected {expected_total_ops} operations, got {len(test_results)}"
        
        # Verify all variables are still accessible and have correct values
        for var_name, expected_value, expected_source in test_results:
            actual_value = env.get(var_name)
            assert actual_value == expected_value, f"Post-concurrent value mismatch: {var_name}"
            
            debug_info = env.get_debug_info()
            assert var_name in debug_info["variable_sources"]
            assert debug_info["variable_sources"][var_name] == expected_source
        
        # Cleanup
        env.reset_to_original()