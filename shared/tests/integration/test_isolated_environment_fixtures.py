"""
Test Fixtures for IsolatedEnvironment Integration Tests

This module provides comprehensive fixtures and utilities specifically for testing
IsolatedEnvironment functionality in realistic integration scenarios.

Business Value: Platform/Internal - Test Infrastructure Stability
Ensures consistent and reliable testing of the critical IsolatedEnvironment SSOT module.
"""

import pytest
import tempfile
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Generator
from contextlib import contextmanager

from shared.isolated_environment import IsolatedEnvironment


@pytest.fixture
def clean_isolated_env() -> Generator[IsolatedEnvironment, None, None]:
    """
    Provide a clean IsolatedEnvironment instance for testing.
    
    This fixture ensures each test gets a fresh, isolated environment
    with proper cleanup after the test completes.
    """
    env = IsolatedEnvironment()
    env.enable_isolation(backup_original=True, refresh_vars=True)
    
    try:
        yield env
    finally:
        # Cleanup: reset to original state and disable isolation
        env.reset_to_original()
        env.disable_isolation(restore_original=True)


@pytest.fixture
def multi_env_contexts() -> Generator[Dict[str, IsolatedEnvironment], None, None]:
    """
    Provide multiple isolated environment contexts for multi-service testing.
    
    Returns a dictionary of environment instances representing different services:
    - auth_service: Authentication service environment
    - backend_service: Main backend service environment  
    - analytics_service: Analytics service environment
    - user_context: User-specific environment context
    """
    contexts = {}
    
    # Create service-specific environments
    service_configs = {
        'auth_service': {
            'SERVICE_NAME': 'auth_service',
            'SERVICE_PORT': '8081',
            'JWT_SECRET_KEY': 'auth-jwt-secret-key-32-chars-long',
            'OAUTH_CLIENT_ID': 'auth_oauth_client_123',
            'OAUTH_CLIENT_SECRET': 'auth_oauth_secret_456'
        },
        'backend_service': {
            'SERVICE_NAME': 'backend_service',  
            'SERVICE_PORT': '8000',
            'JWT_SECRET_KEY': 'backend-jwt-secret-key-32-chars-long',
            'ANTHROPIC_API_KEY': 'backend_anthropic_key_789',
            'OPENAI_API_KEY': 'backend_openai_key_abc'
        },
        'analytics_service': {
            'SERVICE_NAME': 'analytics_service',
            'SERVICE_PORT': '8002', 
            'JWT_SECRET_KEY': 'analytics-jwt-secret-key-32-chars',
            'CLICKHOUSE_URL': 'clickhouse://localhost:8123/analytics',
            'ANALYTICS_API_KEY': 'analytics_api_key_def'
        },
        'user_context': {
            'USER_ID': 'user_123',
            'SESSION_TOKEN': 'session_token_abc123',
            'WORKSPACE_ID': 'workspace_user123',
            'API_QUOTA': '1000'
        }
    }
    
    try:
        for context_name, config in service_configs.items():
            env = IsolatedEnvironment()
            env.enable_isolation()
            env.update(config, f"{context_name}_config")
            contexts[context_name] = env
            
        yield contexts
        
    finally:
        # Cleanup all contexts
        for context_name, env in contexts.items():
            try:
                env.reset()
            except Exception:
                pass  # Best effort cleanup


@pytest.fixture
def test_config_files() -> Generator[Dict[str, Path], None, None]:
    """
    Create temporary configuration files for testing file-based loading.
    
    Returns a dictionary of Path objects for different configuration scenarios:
    - default: Basic default configuration
    - environment: Environment-specific overrides  
    - secrets: Sensitive configuration values
    - invalid: Configuration with intentional errors
    - migration: Legacy configuration for migration testing
    """
    test_dir = Path(tempfile.mkdtemp(prefix="netra_env_test_"))
    config_files = {}
    
    try:
        # Default configuration
        default_config = test_dir / "default.env"
        with open(default_config, 'w', encoding='utf-8') as f:
            f.write("""
# Default Configuration
ENVIRONMENT=development
LOG_LEVEL=INFO
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_USER=netra_user
DATABASE_PASSWORD=default_password
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=default-jwt-secret-key-32-characters
FERNET_KEY=default-fernet-key-base64-encoded-32=
""".strip())
        config_files['default'] = default_config
        
        # Environment-specific configuration
        env_config = test_dir / "test.env"
        with open(env_config, 'w', encoding='utf-8') as f:
            f.write("""
# Test Environment Configuration  
ENVIRONMENT=test
LOG_LEVEL=DEBUG
DATABASE_HOST=test-db.example.com
DATABASE_USER=test_user
DATABASE_PASSWORD=test_secure_password_123
TEST_MODE=true
TESTING=1
""".strip())
        config_files['environment'] = env_config
        
        # Secrets configuration
        secrets_config = test_dir / "secrets.env"
        with open(secrets_config, 'w', encoding='utf-8') as f:
            f.write("""
# Sensitive Configuration Values
API_KEY=secret_api_key_abc123def456
ANTHROPIC_API_KEY=secret_anthropic_key_xyz789
OPENAI_API_KEY=secret_openai_key_mno456
GOOGLE_CLIENT_SECRET=secret_google_oauth_secret
DATABASE_PASSWORD=ultra_secure_db_password_789
FERNET_KEY=ultra_secure_fernet_key_base64_encoded=
""".strip())
        config_files['secrets'] = secrets_config
        
        # Invalid configuration (for error testing)
        invalid_config = test_dir / "invalid.env"
        with open(invalid_config, 'w', encoding='utf-8') as f:
            f.write("""
# Valid entry
VALID_KEY=valid_value

# Invalid entries (intentional errors)
MALFORMED LINE WITHOUT EQUALS
=VALUE_WITHOUT_KEY  
KEY_WITH=MULTIPLE=EQUALS=SIGNS

# Empty key
=empty_key_value

# Unicode test
UNICODE_KEY=unicode_value_with_special_chars_[U+00E9][U+00F1]

# Multi-line value (invalid)
MULTILINE_KEY=line1
line2
line3
""".strip())
        config_files['invalid'] = invalid_config
        
        # Legacy configuration (for migration testing)
        legacy_config = test_dir / "legacy.env"
        with open(legacy_config, 'w', encoding='utf-8') as f:
            f.write("""
# Legacy Configuration Format
POSTGRES_HOST=legacy-db.example.com
POSTGRES_PORT=5432
POSTGRES_USER=legacy_user
POSTGRES_PASSWORD=legacy_password
REDIS_HOST=legacy-redis.example.com
REDIS_PORT=6379
SECRET_KEY=legacy_secret_key_value
DEPRECATED_SETTING=legacy_deprecated_value
OLD_API_ENDPOINT=https://legacy-api.example.com/v1
""".strip())
        config_files['migration'] = legacy_config
        
        yield config_files
        
    finally:
        # Cleanup all test files
        for config_path in config_files.values():
            try:
                if config_path.exists():
                    config_path.unlink()
            except Exception:
                pass
                
        try:
            test_dir.rmdir()
        except Exception:
            pass


@pytest.fixture
def thread_safety_helper():
    """
    Provide utilities for testing thread safety scenarios.
    """
    class ThreadSafetyHelper:
        def __init__(self):
            self.results = {}
            self.errors = []
            self.barrier = None
            
        def create_barrier(self, num_threads: int):
            """Create a threading barrier for synchronized starts."""
            self.barrier = threading.Barrier(num_threads)
            
        def worker_function(self, thread_id: int, env: IsolatedEnvironment, 
                          operations: List[Dict[str, Any]]):
            """
            Generic worker function for thread safety testing.
            
            Args:
                thread_id: Unique identifier for this thread
                env: IsolatedEnvironment instance to operate on
                operations: List of operations to perform
            """
            try:
                if self.barrier:
                    self.barrier.wait()  # Wait for all threads to be ready
                
                thread_results = []
                
                for op in operations:
                    op_type = op['type']
                    
                    if op_type == 'set':
                        success = env.set(op['key'], op['value'], f"thread_{thread_id}")
                        thread_results.append(('set', op['key'], success))
                        
                    elif op_type == 'get':
                        value = env.get(op['key'], op.get('default'))
                        thread_results.append(('get', op['key'], value))
                        
                    elif op_type == 'delete':
                        success = env.delete(op['key'])
                        thread_results.append(('delete', op['key'], success))
                        
                    elif op_type == 'exists':
                        exists = env.exists(op['key'])
                        thread_results.append(('exists', op['key'], exists))
                        
                    elif op_type == 'update':
                        results = env.update(op['variables'], f"thread_{thread_id}")
                        thread_results.append(('update', len(op['variables']), results))
                    
                    # Small delay to increase contention
                    if op.get('delay', 0) > 0:
                        time.sleep(op['delay'])
                
                self.results[thread_id] = thread_results
                
            except Exception as e:
                self.errors.append(f"Thread {thread_id}: {str(e)}")
        
        def run_concurrent_test(self, num_threads: int, env: IsolatedEnvironment,
                              operations_per_thread: List[List[Dict[str, Any]]]) -> Dict[str, Any]:
            """
            Run a concurrent test with multiple threads.
            
            Args:
                num_threads: Number of threads to create
                env: IsolatedEnvironment instance  
                operations_per_thread: List of operation lists for each thread
                
            Returns:
                Dictionary containing test results and metrics
            """
            self.results.clear()
            self.errors.clear()
            self.create_barrier(num_threads)
            
            threads = []
            start_time = time.time()
            
            # Create and start threads
            for i in range(num_threads):
                operations = operations_per_thread[i] if i < len(operations_per_thread) else []
                thread = threading.Thread(
                    target=self.worker_function,
                    args=(i, env, operations)
                )
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join(timeout=30)  # 30 second timeout
            
            end_time = time.time()
            
            return {
                'duration': end_time - start_time,
                'thread_results': dict(self.results),
                'errors': list(self.errors),
                'num_threads': num_threads,
                'success': len(self.errors) == 0 and len(self.results) == num_threads
            }
    
    return ThreadSafetyHelper()


@pytest.fixture
def performance_helper():
    """
    Provide utilities for performance testing scenarios.
    """
    class PerformanceHelper:
        def __init__(self):
            self.metrics = {}
            
        def measure_operation(self, operation_name: str, func, *args, **kwargs):
            """
            Measure the performance of a specific operation.
            
            Args:
                operation_name: Name of the operation being measured
                func: Function to execute and measure
                *args, **kwargs: Arguments to pass to the function
                
            Returns:
                Result of the function call
            """
            start_time = time.time()
            start_memory = self._get_memory_usage()
            
            try:
                result = func(*args, **kwargs)
                success = True
                error = None
            except Exception as e:
                result = None
                success = False
                error = str(e)
            
            end_time = time.time()
            end_memory = self._get_memory_usage()
            
            self.metrics[operation_name] = {
                'duration': end_time - start_time,
                'memory_delta': end_memory - start_memory,
                'success': success,
                'error': error
            }
            
            return result
            
        def bulk_operation_benchmark(self, env: IsolatedEnvironment, 
                                   num_operations: int) -> Dict[str, Any]:
            """
            Benchmark bulk operations on environment variables.
            
            Args:
                env: IsolatedEnvironment instance
                num_operations: Number of operations to perform
                
            Returns:
                Performance metrics dictionary
            """
            # Generate test data
            test_data = {}
            for i in range(num_operations):
                key = f"PERF_TEST_{i:06d}"
                value = f"performance_test_value_{i}_{'x' * 50}"  # 50 char padding
                test_data[key] = value
            
            metrics = {}
            
            # Bulk set operations
            start_time = time.time()
            env.update(test_data, "performance_test")
            metrics['bulk_set_duration'] = time.time() - start_time
            
            # Individual get operations
            start_time = time.time()
            for i in range(0, num_operations, 10):  # Sample every 10th
                key = f"PERF_TEST_{i:06d}"
                value = env.get(key)
                assert value is not None
            metrics['sample_get_duration'] = time.time() - start_time
            
            # Bulk get all operation
            start_time = time.time()
            all_vars = env.get_all()
            metrics['get_all_duration'] = time.time() - start_time
            metrics['total_variables'] = len(all_vars)
            
            # Existence checks
            start_time = time.time()
            for i in range(0, num_operations, 20):  # Sample every 20th
                key = f"PERF_TEST_{i:06d}"
                exists = env.exists(key)
                assert exists is True
            metrics['sample_exists_duration'] = time.time() - start_time
            
            # Cleanup operations  
            start_time = time.time()
            for key in list(test_data.keys())[::10]:  # Delete every 10th
                env.delete(key)
            metrics['sample_delete_duration'] = time.time() - start_time
            
            return metrics
        
        def _get_memory_usage(self) -> int:
            """Get current memory usage (simplified)."""
            import sys
            return sys.getsizeof({})  # Placeholder - could use more sophisticated measurement
            
        def get_metrics_summary(self) -> Dict[str, Any]:
            """Get summary of all collected metrics."""
            if not self.metrics:
                return {}
                
            total_duration = sum(m.get('duration', 0) for m in self.metrics.values())
            successful_ops = sum(1 for m in self.metrics.values() if m.get('success', False))
            
            return {
                'total_operations': len(self.metrics),
                'successful_operations': successful_ops,
                'total_duration': total_duration,
                'average_duration': total_duration / len(self.metrics) if self.metrics else 0,
                'operations_per_second': len(self.metrics) / total_duration if total_duration > 0 else 0,
                'individual_metrics': dict(self.metrics)
            }
    
    return PerformanceHelper()


@contextmanager
def temporary_environment_state(env: IsolatedEnvironment, 
                              temp_vars: Dict[str, str],
                              restore_after: bool = True):
    """
    Context manager for temporary environment state modifications.
    
    Args:
        env: IsolatedEnvironment instance
        temp_vars: Temporary variables to set
        restore_after: Whether to restore original state after context
        
    Usage:
        with temporary_environment_state(env, {"TEMP_VAR": "temp_value"}):
            # Use temporary environment state
            assert env.get("TEMP_VAR") == "temp_value"
        # Original state automatically restored
    """
    if restore_after:
        # Backup current state
        original_state = env.get_all().copy()
    
    try:
        # Set temporary variables
        env.update(temp_vars, "temporary_context")
        yield env
        
    finally:
        if restore_after:
            # Restore original state
            current_vars = env.get_all()
            
            # Remove any variables that weren't in original state
            for key in current_vars:
                if key not in original_state:
                    env.delete(key)
            
            # Restore original values
            for key, value in original_state.items():
                if env.get(key) != value:
                    env.set(key, value, "restore_original")


class ConfigurationScenario:
    """
    Helper class for creating realistic configuration testing scenarios.
    """
    
    @staticmethod
    def create_development_config() -> Dict[str, str]:
        """Create a realistic development environment configuration."""
        return {
            'ENVIRONMENT': 'development',
            'LOG_LEVEL': 'DEBUG',
            'DATABASE_URL': 'postgresql://netra:netra@localhost:5432/netra_dev',
            'REDIS_URL': 'redis://localhost:6379/0',
            'JWT_SECRET_KEY': 'dev-jwt-secret-key-for-local-development-only',
            'FERNET_KEY': 'dev-fernet-key-base64-encoded-for-local-only=',
            'ANTHROPIC_API_KEY': 'dev_anthropic_api_key',
            'OPENAI_API_KEY': 'dev_openai_api_key',
            'FRONTEND_URL': 'http://localhost:3000',
            'BACKEND_URL': 'http://localhost:8000',
            'AUTH_URL': 'http://localhost:8081',
            'ENABLE_DEBUG': 'true',
            'HOT_RELOAD': 'true'
        }
    
    @staticmethod
    def create_test_config() -> Dict[str, str]:
        """Create a realistic test environment configuration.""" 
        return {
            'ENVIRONMENT': 'test',
            'TESTING': 'true',
            'LOG_LEVEL': 'WARNING',
            'DATABASE_URL': 'postgresql://test:test@localhost:5434/netra_test',
            'REDIS_URL': 'redis://localhost:6381/0',
            'JWT_SECRET_KEY': 'test-jwt-secret-key-32-chars-long-secure',
            'FERNET_KEY': 'test-fernet-key-base64-encoded-32-chars=',
            'ANTHROPIC_API_KEY': 'test_anthropic_key',
            'OPENAI_API_KEY': 'test_openai_key',
            'DISABLE_EXTERNAL_APIS': 'true',
            'MOCK_LLM_RESPONSES': 'true',
            'TEST_TIMEOUT': '30',
            'PARALLEL_TESTS': 'true'
        }
    
    @staticmethod
    def create_staging_config() -> Dict[str, str]:
        """Create a realistic staging environment configuration."""
        return {
            'ENVIRONMENT': 'staging',
            'LOG_LEVEL': 'INFO',
            'GCP_PROJECT_ID': 'netra-staging',
            'DATABASE_URL': 'postgresql://postgres:staging_secure_password@staging-db:5432/netra_staging',
            'REDIS_URL': 'redis://staging-redis:6379/0',
            'JWT_SECRET_KEY': 'staging-jwt-secret-very-secure-32-chars',
            'FERNET_KEY': 'staging-fernet-key-secure-base64-encoded=',
            'ANTHROPIC_API_KEY': 'staging_anthropic_api_key_real',
            'OPENAI_API_KEY': 'staging_openai_api_key_real', 
            'OAUTH_CLIENT_ID': 'staging_oauth_client_id',
            'OAUTH_CLIENT_SECRET': 'staging_oauth_client_secret',
            'FRONTEND_URL': 'https://staging.netra.ai',
            'BACKEND_URL': 'https://api-staging.netra.ai',
            'ENABLE_MONITORING': 'true',
            'RATE_LIMITING': 'true'
        }
    
    @staticmethod
    def create_production_config() -> Dict[str, str]:
        """Create a realistic production environment configuration."""
        return {
            'ENVIRONMENT': 'production',
            'LOG_LEVEL': 'ERROR',
            'GCP_PROJECT_ID': 'netra-production',
            'DATABASE_URL': 'postgresql://postgres:ultra_secure_prod_password@prod-db:5432/netra_production',
            'REDIS_URL': 'redis://prod-redis:6379/0',
            'JWT_SECRET_KEY': 'production-jwt-secret-ultra-secure-32-chars',
            'FERNET_KEY': 'production-fernet-key-ultra-secure-base64=',
            'ANTHROPIC_API_KEY': 'production_anthropic_api_key_real',
            'OPENAI_API_KEY': 'production_openai_api_key_real',
            'OAUTH_CLIENT_ID': 'production_oauth_client_id',
            'OAUTH_CLIENT_SECRET': 'production_oauth_client_secret',
            'FRONTEND_URL': 'https://netra.ai',
            'BACKEND_URL': 'https://api.netra.ai',
            'ENABLE_MONITORING': 'true',
            'ENABLE_ANALYTICS': 'true',
            'RATE_LIMITING': 'true',
            'SECURITY_HEADERS': 'strict'
        }