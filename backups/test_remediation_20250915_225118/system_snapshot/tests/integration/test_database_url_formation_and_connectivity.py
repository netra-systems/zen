'''
Database URL Formation and Connectivity Issues Test

This test specifically addresses URL formation issues that can cause database
connection failures and timeouts. Based on analysis of the codebase showing
potential SSL parameter mismatches and driver specification issues.

Business Value Justification (BVJ):
- Segment: Platform/Internal (CONNECTIVITY CRITICAL)
- Business Goal: Eliminate database connection failures from configuration issues
- Value Impact: Ensures all services can connect to databases with proper URLs
- Strategic Impact: Prevents deployment failures and service outages

This addresses URL formation issues that cause connection timeouts.
'''

import asyncio
import pytest
import time
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple
import asyncpg
import psycopg2
from shared.isolated_environment import IsolatedEnvironment

    # Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.database_url_builder import DatabaseURLBuilder
from shared.isolated_environment import get_env
from auth_service.auth_core.database.database_manager import AuthDatabaseManager
from auth_service.auth_core.config import AuthConfig
from test_framework.environment_markers import env

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseURLFormationDiagnostic:
    """Diagnostic tool for database URL formation and connectivity issues."""

    def __init__(self):
        pass
        self.env = get_env()

    def get_all_database_urls(self) -> Dict[str, Any]:
        """Get all database URLs from different sources for comparison."""
        urls = {}
        errors = {}

        try:
        # Environment variables
        env_vars = self.env.get_all()
        urls['environment_vars'] = { )
        'DATABASE_URL': env_vars.get('DATABASE_URL'),
        'POSTGRES_HOST': env_vars.get('POSTGRES_HOST'),
        'POSTGRES_PORT': env_vars.get('POSTGRES_PORT'),
        'POSTGRES_USER': env_vars.get('POSTGRES_USER'),
        'POSTGRES_PASSWORD': '***' if env_vars.get('POSTGRES_PASSWORD') else None,
        'POSTGRES_DB': env_vars.get('POSTGRES_DB')
        

        # DatabaseURLBuilder URLs
        try:
        builder = DatabaseURLBuilder(env_vars)
        urls['builder'] = { )
        'async_url': builder.get_url_for_environment(sync=False),
        'sync_url': builder.get_url_for_environment(sync=True)
            

            # Validate builder
        is_valid, error_msg = builder.validate()
        urls['builder']['validation'] = {'valid': is_valid, 'error': error_msg}

        except Exception as e:
        errors['builder'] = str(e)

                # AuthDatabaseManager URLs
        try:
        urls['auth_manager'] = { )
        'async_url': AuthDatabaseManager.get_auth_database_url_async(),
        'migration_url': AuthDatabaseManager.get_migration_url_sync_format(),
        'base_url': AuthDatabaseManager.get_base_database_url()
                    
        except Exception as e:
        errors['auth_manager'] = str(e)

                        # AuthConfig URL
        try:
        urls['auth_config'] = { )
        'database_url': AuthConfig.get_database_url()
                            
        except Exception as e:
        errors['auth_config'] = str(e)

        except Exception as e:
        errors['general'] = str(e)

        return {'urls': urls, 'errors': errors}

    def analyze_url_issues(self, url_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Analyze URLs for potential issues."""
        issues = []

        urls = url_data.get('urls', {})

    # Check all URLs for common issues
        for source, source_urls in urls.items():
        if isinstance(source_urls, dict):
        for url_type, url in source_urls.items():
        if isinstance(url, str) and url:
        issues.extend(self._check_single_url(url, "formatted_string"))

        return issues

    def _check_single_url(self, url: str, source: str) -> List[Dict[str, str]]:
        """Check a single URL for issues."""
        issues = []

    # SSL parameter issues
        if "postgresql+asyncpg://" in url or "+asyncpg" in url:
        if "sslmode=" in url:
        issues.append({ ))
        'source': source,
        'severity': 'critical',
        'issue': 'AsyncPG URL contains sslmode parameter',
        'description': 'AsyncPG driver does not support sslmode, use ssl instead',
        'url_masked': DatabaseURLBuilder.mask_url_for_logging(url)
            

        if "postgresql+psycopg2://" in url or "+psycopg2" in url:
        if "ssl=" in url and "sslmode=" not in url:
        issues.append({ ))
        'source': source,
        'severity': 'warning',
        'issue': 'psycopg2 URL contains ssl parameter without sslmode',
        'description': 'psycopg2 driver prefers sslmode over ssl',
        'url_masked': DatabaseURLBuilder.mask_url_for_logging(url)
                    

                    # Driver specification issues
        if url.startswith("postgres://"):
        issues.append({ ))
        'source': source,
        'severity': 'medium',
        'issue': 'URL uses postgres:// scheme',
        'description': 'Should use postgresql:// for better compatibility',
        'url_masked': DatabaseURLBuilder.mask_url_for_logging(url)
                        

                        # Port issues
        env_port = self.env.get('POSTGRES_PORT')
        if env_port and env_port != '5432':
        if "formatted_string" not in url and not url.startswith('sqlite'):
        issues.append({ ))
        'source': source,
        'severity': 'high',
        'issue': 'formatted_string',
        'description': 'formatted_string',
        'url_masked': DatabaseURLBuilder.mask_url_for_logging(url)
                                

        return issues

    async def test_url_connectivity(self, url:
        """Test connectivity for a specific URL."""
        result = { )
        'description': description,
        'url_masked': DatabaseURLBuilder.mask_url_for_logging(url),
        'success': False,
        'connection_time': None,
        'error': None,
        'driver_compatibility': 'unknown'
                                    

        if not url or url.startswith('sqlite'):
        result['error'] = 'Skipping SQLite or empty URL'
        return result

        start_time = time.time()

        try:
                                            # Clean URL for asyncpg test
        clean_url = url.replace("postgresql+asyncpg://", "postgresql://").replace("postgresql+psycopg2://", "postgresql://")

                                            # Test with asyncpg
        conn = await asyncio.wait_for( )
        asyncpg.connect(clean_url),
        timeout=10.0
                                            

        await asyncio.wait_for( )
        conn.fetchval("SELECT 1"),
        timeout=5.0
                                            

        await conn.close()

        result.update({ ))
        'success': True,
        'connection_time': time.time() - start_time,
        'driver_compatibility': 'asyncpg_compatible'
                                            

        except Exception as e:
        result.update({ ))
        'connection_time': time.time() - start_time,
        'error': str(e)
                                                

                                                # Check if error is related to SSL parameters
        error_str = str(e).lower()
        if 'sslmode' in error_str:
        result['driver_compatibility'] = 'asyncpg_ssl_incompatible'
        elif 'authentication' in error_str or 'password' in error_str:
        result['driver_compatibility'] = 'auth_issue'
        elif 'timeout' in error_str:
        result['driver_compatibility'] = 'timeout_issue'
        else:
        result['driver_compatibility'] = 'connection_failed'

        return result


class TestDatabaseURLFormationAndConnectivity:
        """Test suite for database URL formation and connectivity issues."""

        @pytest.fixture
    def diagnostic(self):
        pass
        return DatabaseURLFormationDiagnostic()

    def test_database_url_formation_analysis(self, diagnostic):
        '''
        CRITICAL TEST: Analyze database URL formation for issues.

        This test identifies URL formation issues that can cause connection
        failures, timeouts, or driver compatibility problems.
        '''
        pass
        logger.info("=== DATABASE URL FORMATION ANALYSIS ===")

    # Get all URLs
        url_data = diagnostic.get_all_database_urls()

        print(f" )
        Database URL Sources:")
        urls = url_data.get('urls', {})
        errors = url_data.get('errors', {})

    # Display URLs
        for source, source_data in urls.items():
        print("formatted_string")
        if isinstance(source_data, dict):
        for key, value in source_data.items():
        if key == 'validation':
        print("formatted_string")
        elif isinstance(value, str) and value:
        masked_value = DatabaseURLBuilder.mask_url_for_logging(value)
        print("formatted_string")
        else:
        print("formatted_string")
        else:
        print("formatted_string")

                                # Display errors
        if errors:
        print(f" )
        URL Formation Errors:")
        for source, error in errors.items():
        print("formatted_string")

                                        # Analyze issues
        issues = diagnostic.analyze_url_issues(url_data)

        print(f" )
        URL Issues Analysis:")
        print("formatted_string")

        critical_issues = []
        high_issues = []
        other_issues = []

        for issue in issues:
        severity = issue.get('severity', 'unknown')
        print("formatted_string")
        print("formatted_string")
        print("formatted_string")
        print("formatted_string")

        if severity == 'critical':
        critical_issues.append(issue)
        elif severity == 'high':
        high_issues.append(issue)
        else:
        other_issues.append(issue)

        if not issues:
        print("   PASS:  No URL formation issues detected")

                                                            # Assert no critical issues that would cause connection failures
        assert len(critical_issues) == 0, ( )
        f"Critical URL formation issues found that will cause connection failures:
        " +
        "
        ".join("formatted_string"issue"]}" for issue in critical_issues) +
        f"

        These issues must be fixed before database connections will work properly."
                                                                

                                                                # Warn about high-priority issues
        if high_issues:
        print(f" )
        WARNING: [U+FE0F]  High-priority issues that should be addressed:")
        for issue in high_issues:
        print("formatted_string")

        print(f" )
        PASS:  Database URL formation analysis completed")

@pytest.mark.asyncio
    async def test_database_url_connectivity_verification(self, diagnostic):
'''
TEST: Test connectivity for all generated database URLs.

This test verifies that database URLs can actually establish connections
and identifies which URLs work vs. which fail.
'''
pass
logger.info("=== DATABASE URL CONNECTIVITY VERIFICATION ===")

                                                                            # Get all URLs
url_data = diagnostic.get_all_database_urls()
urls = url_data.get('urls', {})

                                                                            # Collect all URLs to test
urls_to_test = []

for source, source_data in urls.items():
if isinstance(source_data, dict):
for key, url in source_data.items():
if isinstance(url, str) and url and not url.startswith('sqlite'):
urls_to_test.append(("formatted_string", url))

print("formatted_string")

                                                                                            # Test connectivity for each URL
connectivity_results = []
for description, url in urls_to_test:
result = await diagnostic.test_url_connectivity(url, description)
connectivity_results.append(result)

                                                                                                # Analyze results
successful_connections = [item for item in []]]
failed_connections = [item for item in []]]

print(f" )
Connectivity Test Results:")
print("formatted_string")
print("formatted_string")

                                                                                                # Display detailed results
for result in connectivity_results:
status = " PASS:  SUCCESS" if result['success'] else " FAIL:  FAILED"
time_str = "formatted_string" if result['connection_time'] else "N/A"

print("formatted_string")
print("formatted_string")
print("formatted_string")

if result.get('error'):
print("formatted_string")

                                                                                                        # Group failures by type
ssl_failures = [item for item in []]
auth_failures = [item for item in []]
timeout_failures = [item for item in []]
other_failures = [item for item in []]

print(f" )
Failure Analysis:")
print("formatted_string")
print("formatted_string")
print("formatted_string")
print("formatted_string")

                                                                                                        # Assert that at least one URL works for basic connectivity
assert len(successful_connections) > 0, ( )
f"No database URLs successfully connected. This indicates a fundamental "
f"connectivity or configuration issue. Failure details:
" +
"
".join("formatted_string"error"]}" for r in failed_connections[:3])
                                                                                                            

                                                                                                            # Warn if primary URLs fail but others work
auth_config_results = [item for item in []]]
if auth_config_results and not auth_config_results[0]['success']:
print(f" )
WARNING: [U+FE0F]  WARNING: Primary auth_config URL failed but other URLs work.")
print(f"This indicates the auth service may not be using the optimal URL.")

print(f" )
PASS:  Database URL connectivity verification completed")

def test_ssl_parameter_compatibility_check(self):
'''
TEST: Verify SSL parameter compatibility across different drivers.

This test checks that SSL parameters are correctly handled for
asyncpg vs. psycopg2 drivers to prevent connection failures.
'''
pass
logger.info("=== SSL PARAMETER COMPATIBILITY CHECK ===")

    # Test URL transformations for SSL parameters
test_cases = [ )
{ )
'name': 'sslmode_to_ssl_for_asyncpg',
'input_url': 'postgresql://user:pass@host:5432/db?sslmode=require',
'expected_asyncpg': 'ssl=require',
'expected_psycopg2': 'sslmode=require'
},
{ )
'name': 'ssl_to_sslmode_for_psycopg2',
'input_url': 'postgresql://user:pass@host:5432/db?ssl=require',
'expected_asyncpg': 'ssl=require',
'expected_psycopg2': 'sslmode=require'
},
{ )
'name': 'cloud_sql_no_ssl_params',
'input_url': 'postgresql://user:pass@/db?host=/cloudsql/project:region:instance&sslmode=require',
'expected_asyncpg': 'no_ssl_params',
'expected_psycopg2': 'no_ssl_params'
    
    

print(f" )
SSL Parameter Compatibility Tests:")

compatibility_issues = []

for test_case in test_cases:
print("formatted_string")
print("formatted_string")

        # Test AuthDatabaseManager URL transformations
try:
            # Set test URL temporarily
from shared.isolated_environment import get_env
env = get_env()
original_url = env.get('DATABASE_URL')

env.set('DATABASE_URL', test_case['input_url'])

            # Get async URL (for asyncpg)
async_url = AuthDatabaseManager.get_auth_database_url_async()
print("formatted_string")

            # Get migration URL (for psycopg2)
migration_url = AuthDatabaseManager.get_migration_url_sync_format()
print("formatted_string")

            # Check async URL for asyncpg compatibility
if test_case['expected_asyncpg'] == 'ssl=require':
if 'ssl=require' not in async_url:
compatibility_issues.append("formatted_string")
if 'sslmode=' in async_url:
compatibility_issues.append("formatted_string")
elif test_case['expected_asyncpg'] == 'no_ssl_params':
if 'ssl=' in async_url or 'sslmode=' in async_url:
compatibility_issues.append("formatted_string")

                                # Check migration URL for psycopg2 compatibility
if test_case['expected_psycopg2'] == 'sslmode=require':
if 'sslmode=require' not in migration_url:
compatibility_issues.append("formatted_string")
elif test_case['expected_psycopg2'] == 'no_ssl_params':
if 'ssl=' in migration_url or 'sslmode=' in migration_url:
compatibility_issues.append("formatted_string")

                                                # Restore original URL
if original_url:
env.set('DATABASE_URL', original_url)
else:
env.set('DATABASE_URL', 'sqlite+aiosqlite:///test.db')

print(f"   PASS:  SSL parameter transformation working")

except Exception as e:
compatibility_issues.append("formatted_string")
print("formatted_string")

print(f" )
SSL Parameter Compatibility Summary:")
print("formatted_string")

for issue in compatibility_issues:
print("formatted_string")

if not compatibility_issues:
print("   PASS:  All SSL parameter transformations working correctly")

                                                                    # Assert no critical SSL compatibility issues
critical_ssl_issues = [item for item in []]

assert len(critical_ssl_issues) == 0, ( )
f"Critical SSL parameter compatibility issues found:
" +
"
".join("formatted_string" for issue in critical_ssl_issues) +
f"

These will cause "unexpected keyword argument sslmode" errors with asyncpg."
                                                                        

print(f" )
PASS:  SSL parameter compatibility check completed")


if __name__ == "__main__":
                                                                            # Run diagnostic when executed directly
async def main():
pass
print("=== DATABASE URL FORMATION AND CONNECTIVITY DIAGNOSIS ===")

diagnostic = DatabaseURLFormationDiagnostic()

    # Analyze URL formation
print("1. Analyzing URL formation...")
url_data = diagnostic.get_all_database_urls()
issues = diagnostic.analyze_url_issues(url_data)

print("formatted_string")

for issue in issues:
print("formatted_string")

        # Test connectivity
print(" )
2. Testing URL connectivity...")
urls = url_data.get('urls', {})

test_urls = []
for source, source_data in urls.items():
if isinstance(source_data, dict):
for key, url in source_data.items():
if isinstance(url, str) and url and not url.startswith('sqlite'):
test_urls.append(("formatted_string", url))

connectivity_results = []
for description, url in test_urls[:3]:  # Test first 3 URLs
result = await diagnostic.test_url_connectivity(url, description)
connectivity_results.append(result)

successful = [item for item in []]]
print("formatted_string")

if successful:
print(" PASS:  Database URL formation and connectivity working")
else:
print(" FAIL:  Database URL formation or connectivity issues found")

asyncio.run(main())
