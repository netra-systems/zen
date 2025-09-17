'''
'''
Database Port Configuration Mismatch Test

This test exposes and validates the critical port configuration issue where:
1. Async database URLs use port 5433 (from environment variables)
2. Sync database URLs default to port 5432 (hardcoded fallback)
3. This causes connectivity failures during database operations

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Platform Stability and Reliability
- Value Impact: Prevents database connectivity failures across services
- Strategic Impact: Ensures consistent database configuration and eliminates service startup failures

This test is designed to FAIL initially, exposing the port mismatch issue,
and PASS once the DatabaseURLBuilder is fixed to use consistent ports.
'''
'''

import os
import sys
import pytest
import asyncio
from typing import Dict, Any
from shared.isolated_environment import IsolatedEnvironment

        # Add project root to path for imports
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.database_url_builder import DatabaseURLBuilder
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient


class DatabasePortConfigurationTester:
    """Test class to validate database port configuration consistency."""

    def __init__(self):
        pass
        self.test_scenarios = []
        self.results = {}

    def create_test_environment(self, port: str) -> Dict[str, str]:
        """Create a test environment with specific port configuration."""
        return { }
        'ENVIRONMENT': 'development',
        'POSTGRES_HOST': 'localhost',
        'POSTGRES_PORT': port,
        'POSTGRES_USER': 'postgres',
        'POSTGRES_PASSWORD': 'DTprdt5KoQXlEG4Gh9lF',
        'POSTGRES_DB': 'netra_dev',
        'DATABASE_URL': 'formatted_string'
    

    def extract_port_from_url(self, url: str) -> str:
        """Extract port number from database URL."""
        if not url:
        return "NO_URL"

        try:
            # Handle standard URL format
        import re
            # Match pattern like @hostname:port/database
        match = re.search(r'@pytest.fixture/', url)
        if match:
        return match.group(1)

                # Handle cases without explicit port (defaults to 5432)
        if '@pytest.fixture[1].split('/')[0]:'
        return "5432"  # PostgreSQL default

        return "UNKNOWN_FORMAT"
        except Exception:
        return "PARSE_ERROR"

    def test_port_consistency(self, env_vars: Dict[str, str]) -> Dict[str, Any]:
        """Test port consistency between async and sync URLs."""
        builder = DatabaseURLBuilder(env_vars)

    # Get URLs
        async_url = builder.get_url_for_environment(sync=False)
        sync_url = builder.get_url_for_environment(sync=True)

    # Extract ports
        async_port = self.extract_port_from_url(async_url)
        sync_port = self.extract_port_from_url(sync_url)
        expected_port = env_vars.get('POSTGRES_PORT', '5432')

        result = { }
        'environment': env_vars.get('ENVIRONMENT', 'unknown'),
        'configured_port': expected_port,
        'async_url': DatabaseURLBuilder.mask_url_for_logging(async_url),
        'sync_url': DatabaseURLBuilder.mask_url_for_logging(sync_url),
        'async_port': async_port,
        'sync_port': sync_port,
        'ports_match': async_port == sync_port,
        'async_port_correct': async_port == expected_port,
        'sync_port_correct': sync_port == expected_port,
        'overall_consistent': async_port == sync_port == expected_port,
        'issues': []
    

    # Identify issues
        if not result['ports_match']:
        result['issues'].append("")

        if not result['async_port_correct']:
        result['issues'].append("")

        if not result['sync_port_correct']:
        result['issues'].append("")

        return result


class TestDatabasePortConfigurationMismatch:
        """Test suite to expose and validate database port configuration issues."""

    def test_port_5433_configuration_consistency(self):
        '''
        '''
        CRITICAL TEST: Expose port mismatch between async and sync URLs.

        This test demonstrates the specific issue where:
        - Dev environment is configured to use port 5433
        - Async URLs correctly use port 5433
        - Sync URLs incorrectly default to port 5432

        This test should FAIL initially, proving the configuration mismatch.
        '''
        '''
        pass
        tester = DatabasePortConfigurationTester()

        # Test with port 5433 (current dev configuration)
        env_5433 = tester.create_test_environment('5433')

        with patch.dict(os.environ, env_5433, clear=False):
        result = tester.test_port_consistency(env_5433)

            # Print detailed results for debugging
        print(f" )"
        === PORT 5433 CONFIGURATION TEST ===")"
        print("")
        print("")
        print("")
        print("")
        print("")
        print("")
        print("")
        print("")

        if result['issues']:
        print(f"Issues Found:")
        for issue in result['issues']:
        print("")

                    # This assertion should FAIL initially, exposing the mismatch
        assert result['overall_consistent'], ( )
        f"DATABASE PORT CONFIGURATION MISMATCH DETECTED:"
        "
        "
        ""
        ""
        ""
        ""
        f"This demonstrates the critical port configuration issue where sync URLs"
        "
        "
        f"ignore environment configuration and default to port 5432."
                            

    def test_port_5432_configuration_consistency(self):
        '''
        '''
        BASELINE TEST: Verify standard port 5432 works correctly.

        This test should PASS, showing that the issue is specific to
        non-standard ports like 5433 used in development.
        '''
        '''
        pass
        tester = DatabasePortConfigurationTester()

    # Test with standard port 5432
        env_5432 = tester.create_test_environment('5432')

        with patch.dict(os.environ, env_5432, clear=False):
        result = tester.test_port_consistency(env_5432)

        print(f" )"
        === PORT 5432 BASELINE TEST ===")"
        print("")
        print("")
        print("")
        print("")

        # This should pass since 5432 is the default
        assert result['overall_consistent'], ( )
        ""
        

    def test_multiple_port_configurations(self):
        '''
        '''
        COMPREHENSIVE TEST: Test various port configurations.

        This test validates port consistency across different port values
        to ensure the fix works for any port configuration.
        '''
        '''
        pass
        tester = DatabasePortConfigurationTester()

        test_ports = ['5432', '5433', '5434', '15432']
        results = {}

        for port in test_ports:
        env_config = tester.create_test_environment(port)

        with patch.dict(os.environ, env_config, clear=False):
        results[port] = tester.test_port_consistency(env_config)

        print(f" )"
        === MULTIPLE PORT CONFIGURATION TEST ===")"

        all_consistent = True
        for port, result in results.items():
        status = "[OK] CONSISTENT" if result['overall_consistent'] else "[FAIL] INCONSISTENT"
        print("")
        if result['issues']:
        for issue in result['issues']:
        print("")

        if not result['overall_consistent']:
        all_consistent = False

        assert all_consistent, ( )
        f"Port configuration inconsistencies found across multiple ports. "
        f"This indicates the DatabaseURLBuilder has systematic issues with "
        f"non-standard port configurations."
                            

@pytest.mark.asyncio
    async def test_actual_database_connectivity_with_port_mismatch(self):
'''
'''
INTEGRATION TEST: Demonstrate how port mismatch causes real connectivity failures.

This test shows the real-world impact of the port configuration issue.
'''
'''
pass
                                # Test environment with port 5433 (where database is running)
env_vars = { }
'ENVIRONMENT': 'development',
'POSTGRES_HOST': 'localhost',
'POSTGRES_PORT': '5433',  # Database runs on 5433
'POSTGRES_USER': 'postgres',
'POSTGRES_PASSWORD': 'DTprdt5KoQXlEG4Gh9lF',
'POSTGRES_DB': 'netra_dev'
                                

with patch.dict(os.environ, env_vars, clear=False):
builder = DatabaseURLBuilder(env_vars)

async_url = builder.get_url_for_environment(sync=False)
sync_url = builder.get_url_for_environment(sync=True)

print(f" )"
=== CONNECTIVITY TEST ===")"
print("")
print("")

                                    # Try to connect using both URLs
try:
    pass
import asyncpg

                                        # Test async URL (should work - connects to 5433)
async_connection_url = DatabaseURLBuilder.format_for_asyncpg_driver(async_url)
print("")

try:
    pass
conn = await asyncpg.connect(async_connection_url, timeout=2)
await conn.close()
async_works = True
print("[OK] Async connection successful")
except Exception as e:
    pass
async_works = False
print("")

                                                # Test sync URL (might fail - tries to connect to 5432)
sync_connection_url = DatabaseURLBuilder.format_for_asyncpg_driver(sync_url)
print("")

try:
    pass
conn = await asyncpg.connect(sync_connection_url, timeout=2)
await conn.close()
sync_works = True
print("[OK] Sync URL connection successful")
except Exception as e:
    pass
sync_works = False
print("")

                                                        # If async works but sync doesn't, we've proven the port mismatch issue
if async_works and not sync_works:
    pass
pytest.fail( )
"CONNECTIVITY FAILURE DUE TO PORT MISMATCH:"
"
"
f"- Async URL (port 5433) connects successfully"
"
"
f"- Sync URL (wrong port) fails to connect"
"
"
"This proves that the port configuration mismatch causes real connectivity issues."
                                                                
elif not async_works and not sync_works:
    pass
pytest.skip("Database not available for connectivity test")
else:
    print("Both connections work - database may be running on both ports")

except ImportError:
    pass
pytest.skip("asyncpg not available for connectivity test")


class TestDatabaseURLBuilderPortLogic:
    """Test the specific logic in DatabaseURLBuilder that causes port mismatches."""

    def test_development_builder_port_consistency(self):
        '''
        '''
        UNIT TEST: Test DevelopmentBuilder port consistency logic.

        This test directly examines the DevelopmentBuilder class to identify
        where the port configuration is being ignored for sync URLs.
        '''
        '''
        pass
    # Environment with non-standard port
        env_vars = { }
        'ENVIRONMENT': 'development',
        'POSTGRES_HOST': 'localhost',
        'POSTGRES_PORT': '5433',
        'POSTGRES_USER': 'postgres',
        'POSTGRES_PASSWORD': 'test_pass',
        'POSTGRES_DB': 'netra_dev'
    

        builder = DatabaseURLBuilder(env_vars)

        print(f" )"
        === DEVELOPMENT BUILDER ANALYSIS ===")"
        print(f"Environment variables:")
        print("")
        print("")

    # Test TCP builder (should use environment variables)
        print(f" )"
        TCP Builder:")"
        print("")
        print("")
        print("")

    # Test development builder
        print(f" )"
        Development Builder:")"
        print("")
        print("")
        print("")

    # Test environment-based URL selection
        async_url = builder.get_url_for_environment(sync=False)
        sync_url = builder.get_url_for_environment(sync=True)

        print(f" )"
        Environment URL Selection:")"
        print("")
        print("")

    # Extract ports to verify the issue
        tester = DatabasePortConfigurationTester()
        async_port = tester.extract_port_from_url(async_url)
        sync_port = tester.extract_port_from_url(sync_url)

        print(f" )"
        Port Analysis:")"
        print("")
        print("")
        print("")

    # The bug: sync URL should use the same port as async URL
        assert async_port == env_vars['POSTGRES_PORT'], ( )
        ""
    

    # This assertion should FAIL, exposing the bug
        assert sync_port == env_vars['POSTGRES_PORT'], ( )
        f"SYNC URL PORT MISMATCH BUG:"
        "
        "
        ""
        ""
        ""
        f"The sync URL is using hardcoded default port instead of environment configuration."
        "
        "
        f"This happens in the DevelopmentBuilder.default_sync_url property."
        


        # Additional diagnostic function for debugging
    def diagnose_port_configuration():
        '''
        '''
        Diagnostic function to understand the current database configuration.
        Can be run independently for debugging purposes.
        '''
        '''
        pass
        from shared.isolated_environment import get_env

        print("=== DATABASE PORT CONFIGURATION DIAGNOSIS ===")

        env = get_env()
        env_vars = env.get_all()

        print(f" )"
        Environment Variables:")"
        for key in ['ENVIRONMENT', 'POSTGRES_HOST', 'POSTGRES_PORT', 'POSTGRES_USER', 'POSTGRES_DB']:
        value = env_vars.get(key, 'NOT SET')
        print("")

        builder = DatabaseURLBuilder(env_vars)

        print(f" )"
        Generated URLs:")"
        print("")
        print("")

        tester = DatabasePortConfigurationTester()
        result = tester.test_port_consistency(env_vars)

        print(f" )"
        Port Consistency Analysis:")"
        print("")
        print("")
        print("")
        print("")

        if result['issues']:
        print(f" )"
        Issues Found:")"
        for issue in result['issues']:
        print("")


        if __name__ == "__main__":
                    # Run diagnostic when executed directly
        diagnose_port_configuration()
