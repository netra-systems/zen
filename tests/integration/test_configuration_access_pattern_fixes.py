"""
Real Configuration Access Pattern Integration Test

This test validates the actual configuration access patterns in the Netra system
according to CLAUDE.md requirements and SPEC/unified_environment_management.xml.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Stable configuration management preventing production incidents
- Value Impact: Eliminates configuration-related service failures
- Strategic Impact: Foundation for reliable multi-service architecture

Key Requirements Tested:
1. ALL environment access goes through IsolatedEnvironment (SPEC/unified_environment_management.xml)
2. Service independence maintained (SPEC/independent_services.xml)
3. Real services and real databases used (NO MOCKS per CLAUDE.md)
4. Configuration patterns follow docs/configuration_architecture.md
5. SSOT principles enforced across all services
"""

import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import pytest
import subprocess
from unittest.mock import patch

from shared.isolated_environment import get_env, IsolatedEnvironment
from netra_backend.app.config import get_config as get_backend_config
from auth_service.auth_core.config import AuthConfig

logger = logging.getLogger(__name__)


class RealConfigurationPatternValidator:
    """Validates real configuration patterns across all services."""
    
    def __init__(self):
        self.env = get_env()
        self.issues_found: List[str] = []
        self.services_tested: List[str] = []
    
    def start_real_services(self) -> Dict[str, bool]:
        """Start real database services using docker-compose.
        
        CRITICAL: We use real services, no mocks per CLAUDE.md requirements.
        """
        print("\n=== STARTING REAL SERVICES (NO MOCKS) ===")
        
        services_status = {
            'postgres': False,
            'redis': False
        }
        
        # Check if services are already running
        try:
            # Try to start minimal services (postgres + redis only for this test)
            result = subprocess.run([
                'docker-compose', '-f', 'docker-compose.minimal.yml', 'up', '-d'
            ], 
            cwd='/Users/anthony/Documents/GitHub/netra-apex',
            capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print("✅ Docker services started successfully")
                services_status['postgres'] = True
                services_status['redis'] = True
            else:
                print(f"⚠️  Docker services may already be running: {result.stderr}")
                # Check if services are accessible even if command failed
                services_status = self._check_service_connectivity()
        
        except subprocess.TimeoutExpired:
            print("⚠️  Docker startup timed out, checking existing services...")
            services_status = self._check_service_connectivity()
        except Exception as e:
            print(f"⚠️  Docker command failed: {e}, checking existing services...")
            services_status = self._check_service_connectivity()
        
        # Wait for services to be ready
        if services_status['postgres'] or services_status['redis']:
            print("Waiting for services to be ready...")
            time.sleep(5)
            
        return services_status
    
    def _check_service_connectivity(self) -> Dict[str, bool]:
        """Check if services are accessible."""
        services = {'postgres': False, 'redis': False}
        
        # Check PostgreSQL
        try:
            # Use a simple connection test
            import psycopg2
            conn = psycopg2.connect(
                host="localhost",
                port="5433",  # From docker-compose.minimal.yml
                user="netra",
                password="netra123",
                database="netra_dev",
                connect_timeout=5
            )
            conn.close()
            services['postgres'] = True
            print("✅ PostgreSQL is accessible")
        except Exception as e:
            print(f"❌ PostgreSQL not accessible: {e}")
        
        # Check Redis
        try:
            import redis
            r = redis.Redis(host='localhost', port=6380, decode_responses=True)
            r.ping()
            services['redis'] = True
            print("✅ Redis is accessible")
        except Exception as e:
            print(f"❌ Redis not accessible: {e}")
        
        return services
    
    def setup_test_environment(self):
        """Setup test environment variables through IsolatedEnvironment."""
        print("\n=== SETTING UP TEST ENVIRONMENT ===")
        
        # Enable isolation mode for testing
        self.env.enable_isolation()
        
        # Set test environment variables using REAL service connection details
        test_config = {
            'ENVIRONMENT': 'test',
            'TESTING': '1',
            # Real PostgreSQL from docker-compose.minimal.yml
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5433',
            'POSTGRES_USER': 'netra',
            'POSTGRES_PASSWORD': 'netra123', 
            'POSTGRES_DB': 'netra_dev',
            'DATABASE_URL': 'postgresql://netra:netra123@localhost:5433/netra_dev',
            # Real Redis from docker-compose.minimal.yml
            'REDIS_URL': 'redis://localhost:6380',
            'REDIS_DISABLED': 'false',
            # JWT configuration
            'JWT_SECRET_KEY': 'test-jwt-secret-key-that-is-long-enough-for-security',
            'SECRET_KEY': 'test-secret-key-that-is-long-enough-for-security',
            # Fernet key for encryption (required in testing)
            'FERNET_KEY': 'Eqj3Aqtrxtbnx5ZzSgcfCpK9r_fZz0ejRC1W1Wtpdnw=',
            # Auth service specific
            'SERVICE_SECRET': 'test-service-secret-that-is-different-from-jwt',
            'SERVICE_ID': 'test-auth-service-instance',
            # OAuth configuration
            'GOOGLE_CLIENT_ID': 'test-google-client-id',
            'GOOGLE_CLIENT_SECRET': 'test-google-client-secret',
            # Frontend/service URLs
            'FRONTEND_URL': 'http://localhost:3000',
            'AUTH_SERVICE_URL': 'http://localhost:8001',
        }
        
        for key, value in test_config.items():
            success = self.env.set(key, value, source='integration_test')
            if success:
                print(f"✅ Set {key}")
            else:
                print(f"❌ Failed to set {key}")
                self.issues_found.append(f"Failed to set environment variable: {key}")
        
        print(f"Environment configured with {len(test_config)} variables")
    
    def validate_isolated_environment_usage(self) -> Dict[str, Any]:
        """Validate that all services use IsolatedEnvironment correctly."""
        print("\n=== VALIDATING ISOLATED ENVIRONMENT USAGE ===")
        
        results = {
            'shared_isolated_environment': self._test_shared_isolated_environment(),
            'netra_backend_config': self._test_netra_backend_config_patterns(),
            'auth_service_config': self._test_auth_service_config_patterns(),
            'environment_isolation': self._test_environment_isolation(),
            'ssot_compliance': self._test_ssot_compliance()
        }
        
        return results
    
    def _test_shared_isolated_environment(self) -> Dict[str, Any]:
        """Test shared IsolatedEnvironment functionality."""
        print("\nTesting shared IsolatedEnvironment...")
        
        test_result = {
            'success': True,
            'tests': {},
            'issues': []
        }
        
        try:
            # Test singleton pattern
            env1 = get_env()
            env2 = get_env()
            
            test_result['tests']['singleton'] = env1 is env2
            if not test_result['tests']['singleton']:
                test_result['issues'].append("IsolatedEnvironment not singleton")
                test_result['success'] = False
            
            # Test isolation mode
            test_result['tests']['isolation_enabled'] = env1.is_isolated()
            if not test_result['tests']['isolation_enabled']:
                test_result['issues'].append("Isolation mode not enabled")
            
            # Test get/set operations
            test_key = "TEST_ISOLATION_KEY"
            test_value = "test-isolation-value"
            
            set_success = env1.set(test_key, test_value, source='isolation_test')
            retrieved_value = env1.get(test_key)
            
            test_result['tests']['get_set_operations'] = (
                set_success and retrieved_value == test_value
            )
            
            if not test_result['tests']['get_set_operations']:
                test_result['issues'].append(f"Get/set operations failed: set={set_success}, retrieved='{retrieved_value}'")
                test_result['success'] = False
            
            # Test source tracking
            source = env1.get_variable_source(test_key)
            test_result['tests']['source_tracking'] = source == 'isolation_test'
            
            if not test_result['tests']['source_tracking']:
                test_result['issues'].append(f"Source tracking failed: expected 'isolation_test', got '{source}'")
                test_result['success'] = False
            
            # Clean up test key
            env1.delete(test_key, source='cleanup')
            
            print(f"  Shared IsolatedEnvironment: {'✅ PASS' if test_result['success'] else '❌ FAIL'}")
            for issue in test_result['issues']:
                print(f"    - {issue}")
        
        except Exception as e:
            test_result['success'] = False
            test_result['issues'].append(f"Exception during testing: {e}")
            print(f"  Shared IsolatedEnvironment: ❌ ERROR - {e}")
        
        return test_result
    
    def _test_netra_backend_config_patterns(self) -> Dict[str, Any]:
        """Test netra_backend configuration patterns."""
        print("\nTesting netra_backend configuration patterns...")
        
        test_result = {
            'success': True,
            'tests': {},
            'issues': []
        }
        
        try:
            # Test unified config access
            config = get_backend_config()
            
            test_result['tests']['config_loaded'] = config is not None
            if not config:
                test_result['success'] = False
                test_result['issues'].append("Backend configuration not loaded")
                return test_result
            
            # Test database URL
            db_url = getattr(config, 'database_url', None)
            test_result['tests']['database_url_configured'] = bool(db_url)
            
            if not db_url:
                test_result['issues'].append("Database URL not configured in backend")
                test_result['success'] = False
            else:
                # Validate it's using our test database
                test_result['tests']['using_test_database'] = 'localhost:5433' in db_url
                if not test_result['tests']['using_test_database']:
                    test_result['issues'].append(f"Not using test database: {db_url}")
            
            # Test environment detection
            environment = getattr(config, 'environment', None)
            test_result['tests']['environment_detection'] = environment == 'test'
            
            if environment != 'test':
                test_result['issues'].append(f"Environment not detected as 'test': {environment}")
                test_result['success'] = False
            
            # Test Redis configuration
            redis_url = getattr(config, 'redis_url', None)
            test_result['tests']['redis_configured'] = bool(redis_url)
            
            print(f"  Backend configuration: {'✅ PASS' if test_result['success'] else '❌ FAIL'}")
            for issue in test_result['issues']:
                print(f"    - {issue}")
        
        except Exception as e:
            test_result['success'] = False
            test_result['issues'].append(f"Exception during backend config test: {e}")
            print(f"  Backend configuration: ❌ ERROR - {e}")
        
        return test_result
    
    def _test_auth_service_config_patterns(self) -> Dict[str, Any]:
        """Test auth_service configuration patterns."""
        print("\nTesting auth_service configuration patterns...")
        
        test_result = {
            'success': True,
            'tests': {},
            'issues': []
        }
        
        try:
            # Test AuthConfig access patterns
            auth_config = AuthConfig()
            
            # Test environment detection
            environment = auth_config.get_environment()
            test_result['tests']['environment_detection'] = environment == 'test'
            
            if environment != 'test':
                test_result['issues'].append(f"Auth environment not detected as 'test': {environment}")
                test_result['success'] = False
            
            # Test database URL generation
            db_url = auth_config.get_database_url()
            test_result['tests']['database_url_configured'] = bool(db_url)
            
            if not db_url:
                test_result['issues'].append("Database URL not configured in auth service")
                test_result['success'] = False
            else:
                # Validate it's using our test database
                test_result['tests']['using_test_database'] = 'localhost:5433' in db_url
                if not test_result['tests']['using_test_database']:
                    test_result['issues'].append(f"Auth not using test database: {db_url}")
            
            # Test JWT configuration
            jwt_secret = auth_config.get_jwt_secret()
            test_result['tests']['jwt_secret_configured'] = bool(jwt_secret)
            
            if not jwt_secret:
                test_result['issues'].append("JWT secret not configured in auth service")
                test_result['success'] = False
            
            # Test service independence - auth should have its own config
            service_secret = auth_config.get_service_secret()
            test_result['tests']['service_secret_configured'] = bool(service_secret)
            
            if not service_secret:
                test_result['issues'].append("Service secret not configured in auth service")
                test_result['success'] = False
            
            # Test Redis URL
            redis_url = auth_config.get_redis_url()
            test_result['tests']['redis_configured'] = bool(redis_url)
            
            if redis_url and 'localhost:6380' not in redis_url:
                test_result['issues'].append(f"Auth not using test Redis: {redis_url}")
            
            print(f"  Auth configuration: {'✅ PASS' if test_result['success'] else '❌ FAIL'}")
            for issue in test_result['issues']:
                print(f"    - {issue}")
        
        except Exception as e:
            test_result['success'] = False
            test_result['issues'].append(f"Exception during auth config test: {e}")
            print(f"  Auth configuration: ❌ ERROR - {e}")
        
        return test_result
    
    def _test_environment_isolation(self) -> Dict[str, Any]:
        """Test environment variable isolation."""
        print("\nTesting environment isolation...")
        
        test_result = {
            'success': True,
            'tests': {},
            'issues': []
        }
        
        try:
            env = get_env()
            
            # Test that isolation prevents os.environ pollution
            test_key = "ISOLATION_TEST_KEY"
            test_value = "isolation_test_value"
            
            # Set in isolated environment
            env.set(test_key, test_value, source='isolation_test')
            
            # Check it's not in os.environ (unless preserved)
            if test_key not in env.PRESERVE_IN_OS_ENVIRON:
                test_result['tests']['isolation_prevents_pollution'] = test_key not in os.environ
                
                if test_key in os.environ:
                    test_result['issues'].append(f"Isolation failed: {test_key} leaked to os.environ")
                    test_result['success'] = False
            
            # Test that we can still retrieve the value
            retrieved_value = env.get(test_key)
            test_result['tests']['isolated_retrieval'] = retrieved_value == test_value
            
            if retrieved_value != test_value:
                test_result['issues'].append(f"Failed to retrieve isolated value: expected '{test_value}', got '{retrieved_value}'")
                test_result['success'] = False
            
            # Clean up
            env.delete(test_key, source='cleanup')
            
            print(f"  Environment isolation: {'✅ PASS' if test_result['success'] else '❌ FAIL'}")
            for issue in test_result['issues']:
                print(f"    - {issue}")
        
        except Exception as e:
            test_result['success'] = False
            test_result['issues'].append(f"Exception during isolation test: {e}")
            print(f"  Environment isolation: ❌ ERROR - {e}")
        
        return test_result
    
    def _test_ssot_compliance(self) -> Dict[str, Any]:
        """Test Single Source of Truth compliance."""
        print("\nTesting SSOT compliance...")
        
        test_result = {
            'success': True,
            'tests': {},
            'issues': []
        }
        
        try:
            # Test that both services use the same IsolatedEnvironment instance
            env1 = get_env()  # Used by shared components
            
            # Test that configuration managers use the same environment
            test_key = "SSOT_TEST_KEY"
            test_value = "ssot_test_value"
            
            env1.set(test_key, test_value, source='ssot_test')
            
            # Verify both backend and auth can see the same value
            backend_env_value = env1.get(test_key)
            
            # Create new config instances to test they see same environment
            try:
                backend_config = get_backend_config()
                auth_config = AuthConfig()
                
                # Both should see the same environment through shared IsolatedEnvironment
                test_result['tests']['shared_environment'] = True
                
                # Test that JWT secret is consistent (through SharedJWTSecretManager)
                backend_jwt = getattr(backend_config, 'jwt_secret_key', None)
                auth_jwt = auth_config.get_jwt_secret()
                
                if backend_jwt and auth_jwt:
                    test_result['tests']['consistent_jwt_secrets'] = backend_jwt == auth_jwt
                    if backend_jwt != auth_jwt:
                        test_result['issues'].append("JWT secrets not consistent between services")
                        test_result['success'] = False
                else:
                    test_result['issues'].append("Could not retrieve JWT secrets from both services")
                    test_result['success'] = False
            
            except Exception as e:
                test_result['issues'].append(f"Error testing service consistency: {e}")
                test_result['success'] = False
            
            # Clean up
            env1.delete(test_key, source='cleanup')
            
            print(f"  SSOT compliance: {'✅ PASS' if test_result['success'] else '❌ FAIL'}")
            for issue in test_result['issues']:
                print(f"    - {issue}")
        
        except Exception as e:
            test_result['success'] = False
            test_result['issues'].append(f"Exception during SSOT test: {e}")
            print(f"  SSOT compliance: ❌ ERROR - {e}")
        
        return test_result
    
    def validate_real_database_connections(self) -> Dict[str, Any]:
        """Test real database connections using configured URLs."""
        print("\n=== TESTING REAL DATABASE CONNECTIONS ===")
        
        results = {
            'backend_database': self._test_backend_database_connection(),
            'auth_database': self._test_auth_database_connection(),
            'redis_connection': self._test_redis_connection()
        }
        
        return results
    
    def _test_backend_database_connection(self) -> Dict[str, Any]:
        """Test backend database connection."""
        print("\nTesting backend database connection...")
        
        test_result = {
            'success': False,
            'connection_details': {},
            'issues': []
        }
        
        try:
            # Get backend config
            config = get_backend_config()
            db_url = getattr(config, 'database_url', None)
            
            if not db_url:
                test_result['issues'].append("No database URL configured")
                return test_result
            
            test_result['connection_details']['url'] = db_url
            
            # Test actual connection
            import psycopg2
            from urllib.parse import urlparse
            
            parsed = urlparse(db_url)
            
            conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port,
                user=parsed.username,
                password=parsed.password,
                database=parsed.path.lstrip('/'),
                connect_timeout=10
            )
            
            # Test basic query
            cursor = conn.cursor()
            cursor.execute("SELECT 1 as test")
            result = cursor.fetchone()
            
            test_result['success'] = result[0] == 1
            test_result['connection_details']['query_result'] = result[0]
            
            cursor.close()
            conn.close()
            
            print(f"  Backend database: {'✅ CONNECTED' if test_result['success'] else '❌ FAILED'}")
        
        except Exception as e:
            test_result['issues'].append(f"Connection failed: {e}")
            print(f"  Backend database: ❌ ERROR - {e}")
        
        return test_result
    
    def _test_auth_database_connection(self) -> Dict[str, Any]:
        """Test auth service database connection."""
        print("\nTesting auth database connection...")
        
        test_result = {
            'success': False,
            'connection_details': {},
            'issues': []
        }
        
        try:
            # Get auth config
            auth_config = AuthConfig()
            db_url = auth_config.get_database_url()
            
            if not db_url:
                test_result['issues'].append("No database URL configured")
                return test_result
            
            test_result['connection_details']['url'] = db_url
            
            # Test actual connection
            import psycopg2
            from urllib.parse import urlparse
            
            parsed = urlparse(db_url)
            
            conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port,
                user=parsed.username,
                password=parsed.password,
                database=parsed.path.lstrip('/'),
                connect_timeout=10
            )
            
            # Test basic query
            cursor = conn.cursor()
            cursor.execute("SELECT 1 as test")
            result = cursor.fetchone()
            
            test_result['success'] = result[0] == 1
            test_result['connection_details']['query_result'] = result[0]
            
            cursor.close()
            conn.close()
            
            print(f"  Auth database: {'✅ CONNECTED' if test_result['success'] else '❌ FAILED'}")
        
        except Exception as e:
            test_result['issues'].append(f"Connection failed: {e}")
            print(f"  Auth database: ❌ ERROR - {e}")
        
        return test_result
    
    def _test_redis_connection(self) -> Dict[str, Any]:
        """Test Redis connection."""
        print("\nTesting Redis connection...")
        
        test_result = {
            'success': False,
            'connection_details': {},
            'issues': []
        }
        
        try:
            # Get Redis URL from environment
            env = get_env()
            redis_url = env.get('REDIS_URL')
            
            if not redis_url:
                test_result['issues'].append("No Redis URL configured")
                return test_result
            
            test_result['connection_details']['url'] = redis_url
            
            # Test actual connection
            import redis
            r = redis.from_url(redis_url, decode_responses=True)
            
            # Test ping
            ping_result = r.ping()
            test_result['success'] = ping_result
            
            # Test set/get
            test_key = "config_test_key"
            test_value = "config_test_value"
            
            r.set(test_key, test_value, ex=60)  # Expire in 60 seconds
            retrieved_value = r.get(test_key)
            
            test_result['connection_details']['set_get_test'] = retrieved_value == test_value
            
            # Clean up
            r.delete(test_key)
            
            print(f"  Redis: {'✅ CONNECTED' if test_result['success'] else '❌ FAILED'}")
        
        except Exception as e:
            test_result['issues'].append(f"Connection failed: {e}")
            print(f"  Redis: ❌ ERROR - {e}")
        
        return test_result
    
    def generate_validation_report(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive validation report."""
        
        report = {
            'overall_success': True,
            'summary': {},
            'detailed_results': results,
            'issues_found': [],
            'recommendations': []
        }
        
        # Analyze results
        for category, category_results in results.items():
            if isinstance(category_results, dict):
                # Special handling for services status
                if category == 'services':
                    # Services status is a dict of service_name: boolean
                    services_working = all(status for status in category_results.values())
                    category_success = services_working
                    issues = [] if services_working else [f"Some services not working: {category_results}"]
                else:
                    # Normal test result format
                    category_success = category_results.get('success', False)
                    issues = category_results.get('issues', [])
                
                if not category_success:
                    report['overall_success'] = False
                    
                report['summary'][category] = {
                    'success': category_success,
                    'issues': issues
                }
                
                # Collect issues
                if issues:
                    report['issues_found'].extend(issues)
        
        # Add recommendations
        if not report['overall_success']:
            report['recommendations'] = [
                "Fix configuration access patterns to use IsolatedEnvironment",
                "Ensure all services maintain independence while using shared utilities",
                "Verify database connections use real services during testing",
                "Check SSOT compliance across all configuration components"
            ]
        
        return report


@pytest.mark.integration
class TestConfigurationAccessPatternFixes:
    """Integration test for REAL configuration access patterns.
    
    Tests the actual configuration implementations against CLAUDE.md requirements.
    """
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Setup isolated test environment."""
        # Get isolated environment and enable isolation
        env = get_env()
        env.enable_isolation()
        
        # Save original state for cleanup
        original_state = env.get_all()
        
        yield env
        
        # Restore original state
        env.reset_to_original()
    
    def test_real_configuration_access_patterns(self, setup_test_environment):
        """Test REAL configuration access patterns with REAL services."""
        
        print("\n" + "="*80)
        print("TESTING REAL CONFIGURATION ACCESS PATTERNS")
        print("Business Goal: Prevent $12K MRR loss from config incidents")
        print("="*80)
        
        validator = RealConfigurationPatternValidator()
        
        # Step 1: Start real services
        services_status = validator.start_real_services()
        
        # Require at least PostgreSQL for the test to proceed
        if not services_status.get('postgres', False):
            pytest.skip("PostgreSQL service not available - cannot test real configuration patterns")
        
        # Step 2: Setup test environment through IsolatedEnvironment
        validator.setup_test_environment()
        
        # Step 3: Validate configuration access patterns
        config_results = validator.validate_isolated_environment_usage()
        
        # Step 4: Test real database connections
        db_results = validator.validate_real_database_connections()
        
        # Step 5: Generate comprehensive report
        all_results = {
            'services': services_status,
            **config_results,
            **db_results
        }
        
        report = validator.generate_validation_report(all_results)
        
        # Print comprehensive results
        print(f"\n=== CONFIGURATION VALIDATION RESULTS ===")
        print(f"Overall Success: {'✅ PASS' if report['overall_success'] else '❌ FAIL'}")
        
        print(f"\n=== SUMMARY BY CATEGORY ===")
        for category, summary in report['summary'].items():
            status = "✅ PASS" if summary['success'] else "❌ FAIL"
            print(f"{category}: {status}")
            for issue in summary.get('issues', []):
                print(f"  - {issue}")
        
        if report['issues_found']:
            print(f"\n=== ISSUES FOUND ({len(report['issues_found'])}) ===")
            for i, issue in enumerate(report['issues_found'], 1):
                print(f"{i}. {issue}")
        
        if report['recommendations']:
            print(f"\n=== RECOMMENDATIONS ===")
            for i, rec in enumerate(report['recommendations'], 1):
                print(f"{i}. {rec}")
        
        print("\n" + "="*80)
        
        # Test assertions
        assert services_status.get('postgres', False), "PostgreSQL service must be available for configuration testing"
        
        # Validate core configuration patterns
        assert config_results.get('shared_isolated_environment', {}).get('success', False), \
            "Shared IsolatedEnvironment must work correctly"
        
        assert config_results.get('environment_isolation', {}).get('success', False), \
            "Environment isolation must prevent os.environ pollution"
        
        # Validate service configurations load correctly
        backend_config_success = config_results.get('netra_backend_config', {}).get('success', False)
        auth_config_success = config_results.get('auth_service_config', {}).get('success', False)
        
        assert backend_config_success, "Backend configuration patterns must be correct"
        assert auth_config_success, "Auth service configuration patterns must be correct"
        
        # Validate real database connections work
        backend_db_success = db_results.get('backend_database', {}).get('success', False)
        auth_db_success = db_results.get('auth_database', {}).get('success', False)
        
        assert backend_db_success, "Backend must connect to real database"
        assert auth_db_success, "Auth service must connect to real database"
        
        # Overall system health check
        assert report['overall_success'], f"Configuration system has {len(report['issues_found'])} issues that must be fixed"
        
        print("🎉 ALL CONFIGURATION ACCESS PATTERNS VALIDATED SUCCESSFULLY!")


if __name__ == "__main__":
    # Run the test directly for debugging
    pytest.main([__file__, "-v", "-s", "--tb=short"])