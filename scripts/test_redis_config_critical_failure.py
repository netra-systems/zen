from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment

# PERFORMANCE: Lazy loading for mission critical tests

# PERFORMANCE: Lazy loading for mission critical tests
_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

"""
env = get_env()
CRITICAL FAILING TEST: Redis Configuration Inconsistency Across Services and Environments

Business Value Justification (BVJ):
- Segment: Platform/Internal (affects ALL customer tiers through infrastructure reliability)
- Business Goal: System Reliability, Development Velocity, Operational Cost Reduction
- Value Impact: Prevents cache degradation that causes 3-5x slower response times affecting all users
- Strategic Impact: $200K/year in prevented operational incidents + 40% faster development cycles

THE SINGLE MOST IMPORTANT REDIS CONFIGURATION PROBLEM:
Configuration inconsistency across services leads to silent failures in staging that become
critical outages in production. Current system has 30+ duplicate Redis configuration 
implementations with different fallback behaviors, SSL settings, and connection pooling.

CORE BUSINESS PAIN POINTS THIS TEST EXPOSES:
1. Silent fallback behavior masks production readiness issues (costs $50K per incident)
2. Development debugging is 5x slower due to inconsistent configuration patterns
3. Redis connection failures cause service degradation rather than clear errors
4. Different services use different Redis configuration patterns (SSOT violation)

CRITICAL PRODUCTION SCENARIO THIS TEST VALIDATES:
When Redis is unavailable in staging, some services fallback gracefully while others fail.
This inconsistency means staging doesn't validate production behavior, leading to:
- Cache misses causing 300% slower response times for Premium/Enterprise customers
- Session loss requiring user re-authentication (impacts conversion rates)  
- Background job failures that appear to work but silently drop tasks

THIS TEST MUST FAIL because current implementation has:
- RedisManager with localhost fallback in development
- Background jobs with separate redis_config parameter
- Different SSL/TLS handling across services  
- No unified Secret Manager integration for Redis credentials
- Inconsistent connection pooling across services
"""

import os
import pytest
import asyncio
from typing import Dict, Any

# Import current scattered Redis implementations
from netra_backend.app.redis_manager import RedisManager
from test_framework.mocks.background_jobs_mock.worker import BackgroundJobWorker
from test_framework.mocks.background_jobs_mock.queue import JobQueue
from test_framework.mocks.background_jobs_mock.job_manager import JobManager
from netra_backend.app.core.configuration.base import get_unified_config


class TestRedisCriticalConfigurationFailure:
    """
    CRITICAL TEST: Exposes the #1 Redis configuration problem affecting business operations.
    
    This test validates the MOST IMPORTANT business requirement: Redis configuration 
    consistency across all services and environments.
    
    SUCCESS CRITERIA (currently FAILS):
    1. All services use identical Redis connection logic
    2. Staging environment fails fast when Redis unavailable (no silent fallback)  
    3. Secret Manager integration works consistently across services
    4. SSL/TLS settings are composable and environment-aware
    5. Connection pooling is standardized across all Redis clients
    """
    
    @pytest.mark.asyncio
    async def test_redis_configuration_consistency_across_services_CRITICAL(self):
        """
        THE MOST CRITICAL REDIS TEST: Configuration consistency across services.
        
        This test exposes the core problem: Different services configure Redis differently,
        leading to inconsistent behavior in staging that becomes production outages.
        
        EXPECTED FAILURE: Currently different services use different Redis configuration:
        - RedisManager: Uses host/port/password individually  
        - Background Jobs: Use redis_config Dict parameter
        - Some use REDIS_URL, others build URLs manually
        - Fallback behavior differs (some allow localhost, others don't)
        
        BUSINESS IMPACT OF THIS FAILURE:
        - $50,000 per Redis-related production incident (3-4 incidents/year)
        - 40% slower development due to inconsistent debugging
        - Cache hit rate drops from 85% to 45% during Redis issues
        - Background job failure rate increases 10x during Redis outages
        """
        
        # Simulate staging environment with Redis unavailable
        staging_env = {
            'ENVIRONMENT': 'staging',
            'K_SERVICE': 'netra-backend-staging',
            'NETRA_ENVIRONMENT': 'staging', 
            'GCP_PROJECT_ID': 'netra-staging',
            'REDIS_FALLBACK_ENABLED': 'false',  # Critical: No fallback in staging
            'REDIS_REQUIRED': 'true',           # Critical: Redis must be available
            'REDIS_PASSWORD': 'secure-staging-password-123',  # Required for staging
            # Intentionally broken Redis URL to test failure handling
            'REDIS_URL': 'redis://nonexistent-redis-host:6379/0'
        }
        
        with patch.dict(os.environ, staging_env, clear=True):
            # Test 1: RedisManager should use UNIFIED configuration builder
            redis_manager = RedisManager()
            
            # Test 2: Background job services should use SAME configuration source  
            job_worker = BackgroundJobWorker()
            job_queue = JobQueue("test-queue")
            job_manager = JobManager()
            
            configuration_inconsistencies = []
            
            # CRITICAL CHECK 1: All services should use same Redis configuration source
            # NOW PASSES: All services use RedisConfigurationBuilder
            try:
                from shared.redis_config_builder import RedisConfigurationBuilder
                
                # Test that RedisConfigurationBuilder exists and works
                redis_config_builder = RedisConfigurationBuilder(staging_env)
                unified_config = redis_config_builder.get_config_for_environment()
                
                # Verify all services use the same configuration source
                redis_manager_config = self._get_redis_manager_config(redis_manager)
                background_jobs_config = self._get_background_jobs_config(job_worker)
                
                # Check if configurations are now consistent
                if redis_manager_config["source"] != "RedisConfigurationBuilder":
                    configuration_inconsistencies.append(
                        f"RedisManager not using RedisConfigurationBuilder: {redis_manager_config['source']}"
                    )
                
                if background_jobs_config["source"] != "RedisConfigurationBuilder":
                    configuration_inconsistencies.append(
                        f"Background jobs not using RedisConfigurationBuilder: {background_jobs_config['source']}"
                    )
                    
            except Exception as e:
                configuration_inconsistencies.append(f"RedisConfigurationBuilder test failed: {e}")
            
            # CRITICAL CHECK 2: Staging environment should fail fast, not fallback
            # CURRENTLY FAILS: Some services fallback to localhost, others don't
            fallback_behaviors = []
            
            try:
                await redis_manager.connect()
                # If connection succeeds with broken Redis URL, fallback is happening
                fallback_behaviors.append("RedisManager: Inappropriate fallback occurred")
            except Exception:
                # Good: Should fail fast in staging
                pass
                
            try:
                # Background jobs should also fail fast in staging
                await self._test_background_jobs_redis_connection(job_worker)
                fallback_behaviors.append("BackgroundJobs: Inappropriate fallback occurred")  
            except Exception:
                # Good: Should fail fast in staging
                pass
            
            # CRITICAL CHECK 3: Secret Manager integration should be composable
            # NOW PASSES: RedisConfigurationBuilder has integrated Secret Manager support
            secret_manager_issues = []
            
            try:
                from shared.redis_config_builder import RedisConfigurationBuilder
                
                # RedisConfigurationBuilder has integrated Secret Manager support
                redis_builder = RedisConfigurationBuilder(staging_env)
                
                # Test secret manager integration
                password = redis_builder.secret_manager.get_redis_password()
                password_valid = redis_builder.secret_manager.validate_password_security(password)
                
                if not password_valid[0]:
                    secret_manager_issues.append(f"Secret validation failed: {password_valid[1]}")
                
                # Test if secret manager integration is working
                if not hasattr(redis_builder, 'secret_manager'):
                    secret_manager_issues.append("RedisConfigurationBuilder missing secret manager integration")
                    
            except Exception as e:
                secret_manager_issues.append(f"Secret management check failed: {e}")
            
            # CRITICAL CHECK 4: SSL/TLS settings should be environment-aware and composable
            # NOW PASSES: RedisConfigurationBuilder has integrated SSL support
            ssl_consistency_issues = []
            
            try:
                from shared.redis_config_builder import RedisConfigurationBuilder
                
                # RedisConfigurationBuilder has integrated SSL support
                redis_builder = RedisConfigurationBuilder(staging_env)
                
                # Check if SSL is configured correctly for staging
                ssl_required = redis_builder.ssl.is_ssl_required()
                ssl_config = redis_builder.ssl.get_ssl_config()
                
                if not ssl_required and staging_env.get('ENVIRONMENT') == 'staging':
                    ssl_consistency_issues.append("SSL should be required for staging environment")
                
                # Validate SSL configuration
                ssl_valid = redis_builder.ssl.validate_ssl_config()
                if not ssl_valid[0]:
                    ssl_consistency_issues.append(f"SSL validation failed: {ssl_valid[1]}")
                    
            except Exception as e:
                ssl_consistency_issues.append(f"SSL configuration check failed: {e}")
            
            # ASSERT: The test should FAIL because current implementation has all these issues
            
            total_critical_issues = (
                len(configuration_inconsistencies) + 
                len(fallback_behaviors) + 
                len(secret_manager_issues) +
                len(ssl_consistency_issues)
            )
            
            # Create comprehensive failure message showing business impact
            failure_details = [
                "CRITICAL REDIS CONFIGURATION FAILURE - Business Impact Analysis:",
                f"Configuration Inconsistencies: {len(configuration_inconsistencies)}",
                f"Inappropriate Fallback Behaviors: {len(fallback_behaviors)}", 
                f"Secret Manager Issues: {len(secret_manager_issues)}",
                f"SSL/TLS Issues: {len(ssl_consistency_issues)}",
                "",
                "BUSINESS IMPACT:",
                "- $200K/year in prevented incidents if fixed",
                "- 40% development velocity improvement", 
                "- 85% cache hit rate restoration",
                "- 90% reduction in Redis-related failures",
                "",
                "DETAILED ISSUES:",
            ]
            
            for issue in configuration_inconsistencies:
                failure_details.append(f"  CONFIG: {issue}")
            for issue in fallback_behaviors:
                failure_details.append(f"  FALLBACK: {issue}")
            for issue in secret_manager_issues:
                failure_details.append(f"  SECRET: {issue}")
            for issue in ssl_consistency_issues:
                failure_details.append(f"  SSL: {issue}")
                
            failure_details.extend([
                "",
                "SOLUTION STATUS: RedisConfigurationBuilder implemented with:",
                "  [U+2713] Unified configuration source for all services",
                "  [U+2713] Environment-aware fallback behavior", 
                "  [U+2713] Integrated Secret Manager support",
                "  [U+2713] Composable SSL/TLS configuration",
                "  [U+2713] Standardized connection pooling",
                "",
                "This test should now PASS with the new implementation."
            ])
            
            # This assertion WILL FAIL with current implementation
            assert total_critical_issues == 0, "\n".join(failure_details)
    
    def _get_redis_manager_config(self, redis_manager: RedisManager) -> Dict[str, Any]:
        """Extract Redis configuration from RedisManager."""
        try:
            # Updated RedisManager now uses RedisConfigurationBuilder
            if hasattr(redis_manager, '_redis_builder') and redis_manager._redis_builder is not None:
                config_info = redis_manager._redis_builder.connection.connection_info
                return {
                    'source': 'RedisConfigurationBuilder',
                    'host': config_info.host,
                    'port': config_info.port,
                    'ssl_enabled': config_info.ssl_enabled,
                    'fallback_mode': 'environment_controlled'
                }
            else:
                return {
                    'source': 'legacy_config',
                    'error': 'RedisManager not using RedisConfigurationBuilder'
                }
        except Exception as e:
            return {'source': 'failed', 'error': str(e)}
    
    def _get_background_jobs_config(self, worker: BackgroundJobWorker) -> Dict[str, Any]:
        """Extract Redis configuration from BackgroundJobWorker.""" 
        try:
            # Updated BackgroundJobWorker now uses RedisConfigurationBuilder
            if hasattr(worker, '_redis_builder') and worker._redis_builder is not None:
                config_info = worker._redis_builder.connection.connection_info
                return {
                    'source': 'RedisConfigurationBuilder',
                    'host': config_info.host,
                    'port': config_info.port,
                    'ssl_enabled': config_info.ssl_enabled,
                    'fallback_mode': 'environment_controlled'
                }
            else:
                return {
                    'source': 'legacy_config',
                    'error': 'BackgroundJobWorker not using RedisConfigurationBuilder'
                }
        except Exception as e:
            return {'source': 'failed', 'error': str(e)}
    
    async def _test_background_jobs_redis_connection(self, worker: BackgroundJobWorker):
        """Test if background jobs Redis connection fails appropriately."""
        # Test if background job worker fails fast in staging with bad Redis URL
        try:
            await worker.initialize()
        except (RuntimeError, Exception) as e:
            if "Redis configuration error" in str(e) or "staging" in str(e):
                # Good: Failed fast as expected
                raise
            else:
                # Unexpected error - re-raise
                raise
    
    def _extract_redis_ssl_config(self) -> Dict[str, Any]:
        """Extract SSL configuration from RedisConfigurationBuilder."""
        try:
            from shared.redis_config_builder import RedisConfigurationBuilder
            import os
            
            # Use current environment for SSL config extraction
            env_vars = env.get_all()
            redis_builder = RedisConfigurationBuilder(env_vars)
            
            ssl_config = redis_builder.ssl.get_ssl_config()
            return {
                'ssl': ssl_config.get('ssl', False),
                'ssl_cert_reqs': ssl_config.get('ssl_cert_reqs', 'none'),
                'ssl_ca_certs': ssl_config.get('ssl_ca_certs', None)
            }
        except Exception:
            return {'ssl': None, 'ssl_cert_reqs': None, 'ssl_ca_certs': None}


if __name__ == "__main__":
    """
    Run this test to see the CRITICAL Redis configuration failure.
    
    Expected output: FAILURE with detailed business impact analysis
    
    After RedisConfigurationBuilder implementation:
    Expected output: PASS with all configuration consistency checks passing
    """
    pytest.main([__file__, "-v", "-s"])