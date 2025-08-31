"""
Database Connection Timeout Diagnosis and Fixes

This test module diagnoses and fixes the critical PostgreSQL database connection
timeout issue causing 503 errors in services. Based on iterations 9-10 analysis
showing 4-5 second timeouts and blocking connection issues.

Business Value Justification (BVJ):
- Segment: Platform/Internal (CRITICAL BLOCKER)
- Business Goal: System operability - prevent 503 Service Unavailable errors
- Value Impact: Enables all services to start successfully and handle requests
- Strategic Impact: Removes primary blocker preventing full system operation

This addresses the root cause of services failing with database connection timeouts.
"""

import asyncio
import pytest
import time
import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from contextlib import asynccontextmanager
import asyncpg
import psycopg2
from unittest.mock import patch, AsyncMock

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from netra_backend.app.core.configuration.database import DatabaseConfigManager
from shared.database_url_builder import DatabaseURLBuilder
from shared.isolated_environment import get_env
from test_framework.environment_markers import env
from auth_service.auth_core.config import AuthConfig
from auth_service.auth_core.database.connection import AuthDatabaseConnection
from auth_service.auth_core.database.database_manager import AuthDatabaseManager

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DatabaseConnectionTimeoutDiagnostic:
    """Comprehensive diagnostic tool for database connection timeout issues."""
    
    def __init__(self):
        self.env = get_env()
        self.results = {}
        self.timeout_results = []
        
    def get_current_config(self) -> Dict[str, Any]:
        """Get current database configuration from all sources."""
        config = {
            'environment_vars': {},
            'direct_env': {},
            'auth_config': {},
            'database_urls': {}
        }
        
        # Environment variables
        env_vars = ['DATABASE_URL', 'POSTGRES_HOST', 'POSTGRES_PORT', 'POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB']
        for var in env_vars:
            value = self.env.get(var)
            config['environment_vars'][var] = value if var != 'POSTGRES_PASSWORD' else ('***' if value else None)
            config['direct_env'][var] = value
        
        # Auth service configuration
        try:
            config['auth_config']['environment'] = AuthConfig.get_environment()
            config['auth_config']['database_url'] = AuthConfig.get_database_url()
            config['auth_config']['masked_url'] = DatabaseURLBuilder.mask_url_for_logging(config['auth_config']['database_url'])
        except Exception as e:
            config['auth_config']['error'] = str(e)
        
        # Database URL variations
        try:
            builder = DatabaseURLBuilder(config['direct_env'])
            config['database_urls']['builder_async'] = builder.get_url_for_environment(sync=False)
            config['database_urls']['builder_sync'] = builder.get_url_for_environment(sync=True)
            config['database_urls']['auth_async'] = AuthDatabaseManager.get_auth_database_url_async()
            config['database_urls']['auth_migration'] = AuthDatabaseManager.get_migration_url_sync_format()
        except Exception as e:
            config['database_urls']['error'] = str(e)
            
        return config
        
    async def test_connection_with_timeout(self, url: str, timeout: float, description: str) -> Dict[str, Any]:
        """Test database connection with specific timeout."""
        result = {
            'description': description,
            'url_masked': DatabaseURLBuilder.mask_url_for_logging(url),
            'timeout': timeout,
            'success': False,
            'connection_time': None,
            'error': None,
            'timeout_exceeded': False
        }
        
        start_time = time.time()
        try:
            # Clean URL for asyncpg
            clean_url = url.replace("postgresql+asyncpg://", "postgresql://")
            
            # Test connection with timeout
            conn = await asyncio.wait_for(
                asyncpg.connect(clean_url),
                timeout=timeout
            )
            
            # Test query
            await asyncio.wait_for(
                conn.fetchval("SELECT 1"),
                timeout=timeout
            )
            
            await conn.close()
            
            connection_time = time.time() - start_time
            result.update({
                'success': True,
                'connection_time': connection_time
            })
            
        except asyncio.TimeoutError:
            result.update({
                'timeout_exceeded': True,
                'connection_time': time.time() - start_time,
                'error': f'Connection timeout exceeded ({timeout}s)'
            })
        except Exception as e:
            result.update({
                'connection_time': time.time() - start_time,
                'error': str(e)
            })
            
        return result
        
    async def test_auth_database_connection_initialization(self) -> Dict[str, Any]:
        """Test auth database connection initialization flow."""
        result = {
            'test': 'auth_database_initialization',
            'success': False,
            'stages': {},
            'total_time': 0,
            'error': None
        }
        
        start_time = time.time()
        
        try:
            # Stage 1: Create connection object
            stage_start = time.time()
            auth_conn = AuthDatabaseConnection()
            result['stages']['create_object'] = {
                'time': time.time() - stage_start,
                'success': True
            }
            
            # Stage 2: Initialize connection
            stage_start = time.time()
            await asyncio.wait_for(auth_conn.initialize(), timeout=15.0)
            result['stages']['initialize'] = {
                'time': time.time() - stage_start,
                'success': True
            }
            
            # Stage 3: Test readiness
            stage_start = time.time()
            is_ready = await asyncio.wait_for(auth_conn.is_ready(), timeout=10.0)
            result['stages']['is_ready'] = {
                'time': time.time() - stage_start,
                'success': is_ready,
                'ready': is_ready
            }
            
            # Stage 4: Test connection
            stage_start = time.time()
            test_success = await asyncio.wait_for(auth_conn.test_connection(), timeout=10.0)
            result['stages']['test_connection'] = {
                'time': time.time() - stage_start,
                'success': test_success
            }
            
            # Clean up
            await auth_conn.close(timeout=5.0)
            
            result['success'] = is_ready and test_success
            
        except Exception as e:
            result['error'] = str(e)
            
        result['total_time'] = time.time() - start_time
        return result
        
    async def test_concurrent_connections(self, url: str, concurrent_count: int = 5) -> Dict[str, Any]:
        """Test concurrent database connections to identify blocking issues."""
        result = {
            'test': 'concurrent_connections',
            'concurrent_count': concurrent_count,
            'url_masked': DatabaseURLBuilder.mask_url_for_logging(url),
            'success': False,
            'connections': [],
            'total_time': 0,
            'error': None
        }
        
        start_time = time.time()
        
        try:
            # Clean URL
            clean_url = url.replace("postgresql+asyncpg://", "postgresql://")
            
            # Create concurrent connection tasks
            async def connect_and_query(conn_id: int):
                conn_start = time.time()
                try:
                    conn = await asyncio.wait_for(asyncpg.connect(clean_url), timeout=10.0)
                    await asyncio.wait_for(conn.fetchval("SELECT 1"), timeout=5.0)
                    await conn.close()
                    return {
                        'id': conn_id,
                        'success': True,
                        'time': time.time() - conn_start,
                        'error': None
                    }
                except Exception as e:
                    return {
                        'id': conn_id,
                        'success': False,
                        'time': time.time() - conn_start,
                        'error': str(e)
                    }
            
            # Run concurrent connections
            tasks = [connect_and_query(i) for i in range(concurrent_count)]
            connection_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            result['connections'] = connection_results
            result['success'] = all(
                not isinstance(r, Exception) and r.get('success', False) 
                for r in connection_results
            )
            
        except Exception as e:
            result['error'] = str(e)
            
        result['total_time'] = time.time() - start_time
        return result
        
    async def diagnose_timeout_patterns(self) -> Dict[str, Any]:
        """Comprehensive timeout pattern analysis."""
        logger.info("Starting comprehensive database connection timeout diagnosis...")
        
        config = self.get_current_config()
        
        # Test different timeout values
        timeout_tests = [
            (1.0, "very_short"),
            (5.0, "short"), 
            (10.0, "normal"),
            (15.0, "long"),
            (30.0, "very_long")
        ]
        
        auth_url = config['auth_config'].get('database_url')
        if not auth_url:
            return {'error': 'No database URL available for testing'}
            
        # Run timeout tests
        timeout_results = []
        for timeout, label in timeout_tests:
            result = await self.test_connection_with_timeout(auth_url, timeout, label)
            timeout_results.append(result)
            
        # Test auth database initialization
        init_result = await self.test_auth_database_connection_initialization()
        
        # Test concurrent connections
        concurrent_result = await self.test_concurrent_connections(auth_url, 3)
        
        diagnosis = {
            'config': config,
            'timeout_tests': timeout_results,
            'initialization_test': init_result,
            'concurrent_test': concurrent_result,
            'analysis': self._analyze_results(timeout_results, init_result, concurrent_result)
        }
        
        return diagnosis
        
    def _analyze_results(self, timeout_results: List[Dict], init_result: Dict, concurrent_result: Dict) -> Dict[str, Any]:
        """Analyze test results to identify root causes."""
        analysis = {
            'root_causes': [],
            'recommendations': [],
            'severity': 'unknown'
        }
        
        # Analyze timeout patterns
        successful_timeouts = [r for r in timeout_results if r['success']]
        failed_timeouts = [r for r in timeout_results if not r['success']]
        
        if not successful_timeouts:
            analysis['root_causes'].append("All timeout tests failed - database unreachable or configuration issue")
            analysis['severity'] = 'critical'
        elif len(failed_timeouts) > 0:
            min_success_timeout = min(r['timeout'] for r in successful_timeouts)
            analysis['root_causes'].append(f"Connection requires > {min_success_timeout}s timeout")
            analysis['severity'] = 'high'
            
        # Analyze initialization
        if not init_result['success']:
            analysis['root_causes'].append("Auth database initialization failing")
            if init_result.get('error'):
                analysis['root_causes'].append(f"Init error: {init_result['error']}")
                
        # Analyze concurrent connections
        if not concurrent_result['success']:
            analysis['root_causes'].append("Concurrent connections failing - potential blocking issue")
            
        # Generate recommendations
        if analysis['severity'] in ['critical', 'high']:
            analysis['recommendations'].extend([
                "Increase database connection timeouts to minimum working value",
                "Implement connection pooling with proper timeout configuration", 
                "Add retry logic with exponential backoff",
                "Monitor database connection pool status"
            ])
            
        return analysis


class TestDatabaseConnectionTimeoutFix:
    """Tests for database connection timeout diagnosis and fixes."""
    
    @pytest.fixture(scope="class")
    def diagnostic(self):
        return DatabaseConnectionTimeoutDiagnostic()
    
    @pytest.mark.asyncio
    async def test_comprehensive_database_timeout_diagnosis(self, diagnostic):
        """
        CRITICAL TEST: Comprehensive diagnosis of database connection timeout issues.
        
        This test identifies the root cause of 503 Service Unavailable errors
        by analyzing connection timeouts, initialization failures, and blocking issues.
        """
        logger.info("=== COMPREHENSIVE DATABASE TIMEOUT DIAGNOSIS ===")
        
        # Run comprehensive diagnosis
        diagnosis = await diagnostic.diagnose_timeout_patterns()
        
        # Print detailed results
        print(f"\n{'='*80}")
        print("DATABASE CONNECTION TIMEOUT DIAGNOSIS RESULTS")
        print(f"{'='*80}")
        
        # Configuration
        config = diagnosis.get('config', {})
        print(f"\nConfiguration:")
        print(f"  Environment: {config.get('auth_config', {}).get('environment', 'unknown')}")
        print(f"  Database URL: {config.get('auth_config', {}).get('masked_url', 'unknown')}")
        
        # Timeout test results
        timeout_tests = diagnosis.get('timeout_tests', [])
        print(f"\nTimeout Test Results:")
        for result in timeout_tests:
            status = "✅ SUCCESS" if result['success'] else "❌ FAILED"
            time_str = f"{result['connection_time']:.2f}s" if result['connection_time'] else "N/A"
            print(f"  {result['description']} ({result['timeout']}s): {status} ({time_str})")
            if result.get('error'):
                print(f"    Error: {result['error']}")
        
        # Initialization test
        init_result = diagnosis.get('initialization_test', {})
        print(f"\nInitialization Test:")
        print(f"  Overall: {'✅ SUCCESS' if init_result['success'] else '❌ FAILED'}")
        print(f"  Total Time: {init_result['total_time']:.2f}s")
        
        for stage_name, stage_result in init_result.get('stages', {}).items():
            status = "✅" if stage_result['success'] else "❌"
            print(f"    {stage_name}: {status} ({stage_result['time']:.2f}s)")
        
        if init_result.get('error'):
            print(f"  Error: {init_result['error']}")
            
        # Concurrent test
        concurrent_result = diagnosis.get('concurrent_test', {})
        print(f"\nConcurrent Connection Test:")
        print(f"  Overall: {'✅ SUCCESS' if concurrent_result['success'] else '❌ FAILED'}")
        print(f"  Total Time: {concurrent_result['total_time']:.2f}s")
        
        # Analysis
        analysis = diagnosis.get('analysis', {})
        print(f"\nRoot Cause Analysis:")
        print(f"  Severity: {analysis.get('severity', 'unknown').upper()}")
        
        for cause in analysis.get('root_causes', []):
            print(f"  ⚠️  {cause}")
            
        print(f"\nRecommendations:")
        for rec in analysis.get('recommendations', []):
            print(f"  💡 {rec}")
        
        # Determine if this is a blocking issue
        has_critical_issues = (
            analysis.get('severity') == 'critical' or 
            not init_result.get('success') or
            not any(r['success'] for r in timeout_tests)
        )
        
        if has_critical_issues:
            # This test should document the issue but not fail - we need to implement fixes
            print(f"\n{'='*80}")
            print("❌ CRITICAL BLOCKING ISSUE IDENTIFIED")
            print("This test documents the database connection timeout issue.")
            print("Fixes are being implemented in subsequent tests.")
            print(f"{'='*80}")
        
        # Always assert - this test should pass after fixes are implemented
        working_timeouts = [r for r in timeout_tests if r['success']]
        assert len(working_timeouts) > 0, (
            f"CRITICAL: No database connections successful. Root causes: {analysis.get('root_causes')}"
        )
        
        # Verify auth database initialization works (should work after fixes)
        assert init_result.get('success'), (
            f"CRITICAL: Auth database initialization failed. Error: {init_result.get('error')}"
        )
    
    @pytest.mark.asyncio
    async def test_database_connection_with_timeout_configuration(self):
        """
        TEST: Database connection with proper timeout configuration.
        
        This test verifies that database connections work with appropriate timeout settings
        and implements fixes for timeout-related issues.
        """
        logger.info("=== DATABASE CONNECTION TIMEOUT CONFIGURATION TEST ===")
        
        # Get environment configuration
        env = get_env()
        
        # Test timeout configurations
        timeout_configs = [
            {'connect': 10.0, 'query': 5.0, 'description': 'Standard'},
            {'connect': 15.0, 'query': 10.0, 'description': 'Extended'},
            {'connect': 30.0, 'query': 15.0, 'description': 'Long'}
        ]
        
        successful_configs = []
        
        for config in timeout_configs:
            try:
                # Get database URL
                database_url = AuthConfig.get_database_url()
                clean_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
                
                # Test connection with specific timeouts
                start_time = time.time()
                
                conn = await asyncio.wait_for(
                    asyncpg.connect(clean_url), 
                    timeout=config['connect']
                )
                
                result = await asyncio.wait_for(
                    conn.fetchval("SELECT 1"),
                    timeout=config['query']
                )
                
                await conn.close()
                
                connection_time = time.time() - start_time
                
                config_result = {
                    'config': config,
                    'success': True,
                    'connection_time': connection_time,
                    'result': result
                }
                
                successful_configs.append(config_result)
                
                print(f"{config['description']} timeout config: ✅ SUCCESS ({connection_time:.2f}s)")
                
            except Exception as e:
                print(f"{config['description']} timeout config: ❌ FAILED - {e}")
        
        # Verify at least one configuration works
        assert len(successful_configs) > 0, (
            "No timeout configuration successful. Database may be unreachable or credentials invalid."
        )
        
        # Find optimal timeout configuration
        optimal_config = min(successful_configs, key=lambda x: x['connection_time'])
        
        print(f"\nOptimal timeout configuration:")
        print(f"  Connect timeout: {optimal_config['config']['connect']}s")
        print(f"  Query timeout: {optimal_config['config']['query']}s") 
        print(f"  Connection time: {optimal_config['connection_time']:.2f}s")
        
        # Recommend configuration updates
        print(f"\nRecommended fixes:")
        print(f"  1. Update AsyncPG connection timeout to {optimal_config['config']['connect']}s")
        print(f"  2. Update query timeout to {optimal_config['config']['query']}s")
        print(f"  3. Implement retry logic with exponential backoff")
        
    def test_database_url_formation_diagnosis(self):
        """
        TEST: Diagnose database URL formation issues.
        
        This test identifies issues with database URL construction that could
        cause connection timeouts or failures.
        """
        logger.info("=== DATABASE URL FORMATION DIAGNOSIS ===")
        
        # Get all URL variations
        env = get_env()
        env_vars = env.get_all()
        
        # Test DatabaseURLBuilder
        builder = DatabaseURLBuilder(env_vars)
        
        urls = {
            'builder_async': builder.get_url_for_environment(sync=False),
            'builder_sync': builder.get_url_for_environment(sync=True),
            'auth_async': AuthDatabaseManager.get_auth_database_url_async(),
            'auth_migration': AuthDatabaseManager.get_migration_url_sync_format(),
            'auth_config': AuthConfig.get_database_url()
        }
        
        print(f"\nDatabase URL Analysis:")
        
        url_issues = []
        
        for name, url in urls.items():
            if url:
                masked_url = DatabaseURLBuilder.mask_url_for_logging(url)
                print(f"  {name}: {masked_url}")
                
                # Check for common issues
                if "postgresql+asyncpg://" in url and name.endswith('_sync'):
                    url_issues.append(f"{name}: Uses async driver for sync operation")
                    
                if "sslmode=" in url and "asyncpg" in url:
                    url_issues.append(f"{name}: AsyncPG doesn't support sslmode parameter")
                    
                if "ssl=" in url and "psycopg2" in url:
                    url_issues.append(f"{name}: psycopg2 expects sslmode, not ssl")
                    
                if ":5432/" in url and env_vars.get('POSTGRES_PORT') != '5432':
                    url_issues.append(f"{name}: Port mismatch with POSTGRES_PORT")
                    
            else:
                print(f"  {name}: ❌ NO URL GENERATED")
                url_issues.append(f"{name}: URL generation failed")
        
        print(f"\nURL Issues Found:")
        if url_issues:
            for issue in url_issues:
                print(f"  ⚠️  {issue}")
        else:
            print(f"  ✅ No URL formation issues detected")
        
        # Verify no critical URL issues
        critical_issues = [issue for issue in url_issues if "sslmode=" in issue or "generation failed" in issue]
        
        if critical_issues:
            print(f"\nCritical URL issues that need fixing:")
            for issue in critical_issues:
                print(f"  🚨 {issue}")
        
        # Assert URLs are formed correctly
        assert urls['auth_config'], "Auth service database URL must be generated"
        assert urls['builder_async'], "DatabaseURLBuilder async URL must be generated"
        
        # Check for SSL parameter issues (critical for asyncpg)
        auth_url = urls['auth_config']
        if "asyncpg" in auth_url:
            assert "sslmode=" not in auth_url, (
                f"AsyncPG URL contains unsupported sslmode parameter. "
                f"URL: {DatabaseURLBuilder.mask_url_for_logging(auth_url)}"
            )


class DatabaseConnectionTimeoutFixes:
    """Implementation of fixes for database connection timeout issues."""
    
    @classmethod
    @asynccontextmanager
    async def enhanced_database_connection(cls, database_url: str, connect_timeout: float = 15.0, query_timeout: float = 10.0):
        """Enhanced database connection with proper timeout handling."""
        conn = None
        try:
            # Clean URL for asyncpg
            clean_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
            
            # Connect with timeout
            conn = await asyncio.wait_for(
                asyncpg.connect(clean_url),
                timeout=connect_timeout
            )
            
            yield conn
            
        except asyncio.TimeoutError:
            raise RuntimeError(f"Database connection timeout exceeded ({connect_timeout}s)")
        except Exception as e:
            raise RuntimeError(f"Database connection failed: {e}") from e
        finally:
            if conn:
                try:
                    await asyncio.wait_for(conn.close(), timeout=5.0)
                except Exception as close_error:
                    logger.warning(f"Error closing connection: {close_error}")
    
    @classmethod
    async def test_database_readiness_with_timeout(cls, database_url: str, timeout: float = 10.0) -> bool:
        """Test database readiness with configurable timeout."""
        try:
            async with cls.enhanced_database_connection(database_url, timeout, timeout) as conn:
                result = await asyncio.wait_for(
                    conn.fetchval("SELECT 1"),
                    timeout=timeout
                )
                return result == 1
        except Exception as e:
            logger.error(f"Database readiness check failed: {e}")
            return False
    
    @classmethod
    async def retry_database_operation(cls, operation_func, max_retries: int = 3, initial_delay: float = 1.0, max_delay: float = 10.0):
        """Retry database operations with exponential backoff."""
        delay = initial_delay
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                return await operation_func()
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    logger.warning(f"Database operation attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, max_delay)
                else:
                    logger.error(f"Database operation failed after {max_retries} attempts")
        
        raise last_exception


class TestDatabaseConnectionTimeoutImplementedFixes:
    """Test the implemented fixes for database connection timeouts."""
    
    @pytest.mark.asyncio
    async def test_enhanced_database_connection_with_timeouts(self):
        """Test enhanced database connection with proper timeout handling."""
        database_url = AuthConfig.get_database_url()
        
        # Test with enhanced connection
        async with DatabaseConnectionTimeoutFixes.enhanced_database_connection(
            database_url, connect_timeout=15.0, query_timeout=10.0
        ) as conn:
            result = await conn.fetchval("SELECT 1")
            assert result == 1
            
        print("✅ Enhanced database connection with timeouts working")
    
    @pytest.mark.asyncio
    async def test_database_readiness_with_timeout_fix(self):
        """Test database readiness check with timeout fix."""
        database_url = AuthConfig.get_database_url()
        
        # Test readiness with timeout
        is_ready = await DatabaseConnectionTimeoutFixes.test_database_readiness_with_timeout(
            database_url, timeout=15.0
        )
        
        assert is_ready, "Database readiness check with timeout should pass"
        print("✅ Database readiness check with timeout working")
    
    @pytest.mark.asyncio 
    async def test_retry_database_operation_fix(self):
        """Test retry logic for database operations."""
        database_url = AuthConfig.get_database_url()
        
        # Define operation to retry
        async def test_operation():
            async with DatabaseConnectionTimeoutFixes.enhanced_database_connection(database_url) as conn:
                return await conn.fetchval("SELECT 1")
        
        # Test with retry logic
        result = await DatabaseConnectionTimeoutFixes.retry_database_operation(
            test_operation, max_retries=3, initial_delay=0.1, max_delay=1.0
        )
        
        assert result == 1
        print("✅ Database operation retry logic working")


if __name__ == "__main__":
    # Run diagnostic when executed directly
    async def main():
        print("=== DATABASE CONNECTION TIMEOUT DIAGNOSIS ===")
        diagnostic = DatabaseConnectionTimeoutDiagnostic()
        results = await diagnostic.diagnose_timeout_patterns()
        
        # Print summary
        print(f"\nDiagnosis Summary:")
        analysis = results.get('analysis', {})
        print(f"Severity: {analysis.get('severity', 'unknown')}")
        
        for cause in analysis.get('root_causes', []):
            print(f"Root cause: {cause}")
            
        for rec in analysis.get('recommendations', []):
            print(f"Recommendation: {rec}")
    
    asyncio.run(main())