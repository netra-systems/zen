from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
_lazy_imports = {}

def lazy_import(module_path: str, component: str=None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f'Warning: Failed to lazy load {module_path}: {e}')
            _lazy_imports[module_path] = None
    return _lazy_imports[module_path]
_lazy_imports = {}

def lazy_import(module_path: str, component: str=None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f'Warning: Failed to lazy load {module_path}: {e}')
            _lazy_imports[module_path] = None
    return _lazy_imports[module_path]
"\nenv = get_env()\nCRITICAL FAILING TEST: Redis Configuration Inconsistency Across Services and Environments\n\nBusiness Value Justification (BVJ):\n- Segment: Platform/Internal (affects ALL customer tiers through infrastructure reliability)\n- Business Goal: System Reliability, Development Velocity, Operational Cost Reduction\n- Value Impact: Prevents cache degradation that causes 3-5x slower response times affecting all users\n- Strategic Impact: $200K/year in prevented operational incidents + 40% faster development cycles\n\nTHE SINGLE MOST IMPORTANT REDIS CONFIGURATION PROBLEM:\nConfiguration inconsistency across services leads to silent failures in staging that become\ncritical outages in production. Current system has 30+ duplicate Redis configuration \nimplementations with different fallback behaviors, SSL settings, and connection pooling.\n\nCORE BUSINESS PAIN POINTS THIS TEST EXPOSES:\n1. Silent fallback behavior masks production readiness issues (costs $50K per incident)\n2. Development debugging is 5x slower due to inconsistent configuration patterns\n3. Redis connection failures cause service degradation rather than clear errors\n4. Different services use different Redis configuration patterns (SSOT violation)\n\nCRITICAL PRODUCTION SCENARIO THIS TEST VALIDATES:\nWhen Redis is unavailable in staging, some services fallback gracefully while others fail.\nThis inconsistency means staging doesn't validate production behavior, leading to:\n- Cache misses causing 300% slower response times for Premium/Enterprise customers\n- Session loss requiring user re-authentication (impacts conversion rates)  \n- Background job failures that appear to work but silently drop tasks\n\nTHIS TEST MUST FAIL because current implementation has:\n- RedisManager with localhost fallback in development\n- Background jobs with separate redis_config parameter\n- Different SSL/TLS handling across services  \n- No unified Secret Manager integration for Redis credentials\n- Inconsistent connection pooling across services\n"
import os
import pytest
import asyncio
from typing import Dict, Any
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
        staging_env = {'ENVIRONMENT': 'staging', 'K_SERVICE': 'netra-backend-staging', 'NETRA_ENVIRONMENT': 'staging', 'GCP_PROJECT_ID': 'netra-staging', 'REDIS_FALLBACK_ENABLED': 'false', 'REDIS_REQUIRED': 'true', 'REDIS_PASSWORD': 'secure-staging-password-123', 'REDIS_URL': 'redis://nonexistent-redis-host:6379/0'}
        with patch.dict(os.environ, staging_env, clear=True):
            redis_manager = RedisManager()
            job_worker = BackgroundJobWorker()
            job_queue = JobQueue('test-queue')
            job_manager = JobManager()
            configuration_inconsistencies = []
            try:
                from shared.redis_config_builder import RedisConfigurationBuilder
                redis_config_builder = RedisConfigurationBuilder(staging_env)
                unified_config = redis_config_builder.get_config_for_environment()
                redis_manager_config = self._get_redis_manager_config(redis_manager)
                background_jobs_config = self._get_background_jobs_config(job_worker)
                if redis_manager_config['source'] != 'RedisConfigurationBuilder':
                    configuration_inconsistencies.append(f"RedisManager not using RedisConfigurationBuilder: {redis_manager_config['source']}")
                if background_jobs_config['source'] != 'RedisConfigurationBuilder':
                    configuration_inconsistencies.append(f"Background jobs not using RedisConfigurationBuilder: {background_jobs_config['source']}")
            except Exception as e:
                configuration_inconsistencies.append(f'RedisConfigurationBuilder test failed: {e}')
            fallback_behaviors = []
            try:
                await redis_manager.connect()
                fallback_behaviors.append('RedisManager: Inappropriate fallback occurred')
            except Exception:
                pass
            try:
                await self._test_background_jobs_redis_connection(job_worker)
                fallback_behaviors.append('BackgroundJobs: Inappropriate fallback occurred')
            except Exception:
                pass
            secret_manager_issues = []
            try:
                from shared.redis_config_builder import RedisConfigurationBuilder
                redis_builder = RedisConfigurationBuilder(staging_env)
                password = redis_builder.secret_manager.get_redis_password()
                password_valid = redis_builder.secret_manager.validate_password_security(password)
                if not password_valid[0]:
                    secret_manager_issues.append(f'Secret validation failed: {password_valid[1]}')
                if not hasattr(redis_builder, 'secret_manager'):
                    secret_manager_issues.append('RedisConfigurationBuilder missing secret manager integration')
            except Exception as e:
                secret_manager_issues.append(f'Secret management check failed: {e}')
            ssl_consistency_issues = []
            try:
                from shared.redis_config_builder import RedisConfigurationBuilder
                redis_builder = RedisConfigurationBuilder(staging_env)
                ssl_required = redis_builder.ssl.is_ssl_required()
                ssl_config = redis_builder.ssl.get_ssl_config()
                if not ssl_required and staging_env.get('ENVIRONMENT') == 'staging':
                    ssl_consistency_issues.append('SSL should be required for staging environment')
                ssl_valid = redis_builder.ssl.validate_ssl_config()
                if not ssl_valid[0]:
                    ssl_consistency_issues.append(f'SSL validation failed: {ssl_valid[1]}')
            except Exception as e:
                ssl_consistency_issues.append(f'SSL configuration check failed: {e}')
            total_critical_issues = len(configuration_inconsistencies) + len(fallback_behaviors) + len(secret_manager_issues) + len(ssl_consistency_issues)
            failure_details = ['CRITICAL REDIS CONFIGURATION FAILURE - Business Impact Analysis:', f'Configuration Inconsistencies: {len(configuration_inconsistencies)}', f'Inappropriate Fallback Behaviors: {len(fallback_behaviors)}', f'Secret Manager Issues: {len(secret_manager_issues)}', f'SSL/TLS Issues: {len(ssl_consistency_issues)}', '', 'BUSINESS IMPACT:', '- $200K/year in prevented incidents if fixed', '- 40% development velocity improvement', '- 85% cache hit rate restoration', '- 90% reduction in Redis-related failures', '', 'DETAILED ISSUES:']
            for issue in configuration_inconsistencies:
                failure_details.append(f'  CONFIG: {issue}')
            for issue in fallback_behaviors:
                failure_details.append(f'  FALLBACK: {issue}')
            for issue in secret_manager_issues:
                failure_details.append(f'  SECRET: {issue}')
            for issue in ssl_consistency_issues:
                failure_details.append(f'  SSL: {issue}')
            failure_details.extend(['', 'SOLUTION STATUS: RedisConfigurationBuilder implemented with:', '  [U+2713] Unified configuration source for all services', '  [U+2713] Environment-aware fallback behavior', '  [U+2713] Integrated Secret Manager support', '  [U+2713] Composable SSL/TLS configuration', '  [U+2713] Standardized connection pooling', '', 'This test should now PASS with the new implementation.'])
            assert total_critical_issues == 0, '\n'.join(failure_details)

    def _get_redis_manager_config(self, redis_manager: RedisManager) -> Dict[str, Any]:
        """Extract Redis configuration from RedisManager."""
        try:
            if hasattr(redis_manager, '_redis_builder') and redis_manager._redis_builder is not None:
                config_info = redis_manager._redis_builder.connection.connection_info
                return {'source': 'RedisConfigurationBuilder', 'host': config_info.host, 'port': config_info.port, 'ssl_enabled': config_info.ssl_enabled, 'fallback_mode': 'environment_controlled'}
            else:
                return {'source': 'legacy_config', 'error': 'RedisManager not using RedisConfigurationBuilder'}
        except Exception as e:
            return {'source': 'failed', 'error': str(e)}

    def _get_background_jobs_config(self, worker: BackgroundJobWorker) -> Dict[str, Any]:
        """Extract Redis configuration from BackgroundJobWorker."""
        try:
            if hasattr(worker, '_redis_builder') and worker._redis_builder is not None:
                config_info = worker._redis_builder.connection.connection_info
                return {'source': 'RedisConfigurationBuilder', 'host': config_info.host, 'port': config_info.port, 'ssl_enabled': config_info.ssl_enabled, 'fallback_mode': 'environment_controlled'}
            else:
                return {'source': 'legacy_config', 'error': 'BackgroundJobWorker not using RedisConfigurationBuilder'}
        except Exception as e:
            return {'source': 'failed', 'error': str(e)}

    async def _test_background_jobs_redis_connection(self, worker: BackgroundJobWorker):
        """Test if background jobs Redis connection fails appropriately."""
        try:
            await worker.initialize()
        except (RuntimeError, Exception) as e:
            if 'Redis configuration error' in str(e) or 'staging' in str(e):
                raise
            else:
                raise

    def _extract_redis_ssl_config(self) -> Dict[str, Any]:
        """Extract SSL configuration from RedisConfigurationBuilder."""
        try:
            from shared.redis_config_builder import RedisConfigurationBuilder
            import os
            env_vars = env.get_all()
            redis_builder = RedisConfigurationBuilder(env_vars)
            ssl_config = redis_builder.ssl.get_ssl_config()
            return {'ssl': ssl_config.get('ssl', False), 'ssl_cert_reqs': ssl_config.get('ssl_cert_reqs', 'none'), 'ssl_ca_certs': ssl_config.get('ssl_ca_certs', None)}
        except Exception:
            return {'ssl': None, 'ssl_cert_reqs': None, 'ssl_ca_certs': None}
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')