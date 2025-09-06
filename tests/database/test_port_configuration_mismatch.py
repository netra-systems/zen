# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Database Port Configuration Mismatch Test

# REMOVED_SYNTAX_ERROR: This test exposes and validates the critical port configuration issue where:
    # REMOVED_SYNTAX_ERROR: 1. Async database URLs use port 5433 (from environment variables)
    # REMOVED_SYNTAX_ERROR: 2. Sync database URLs default to port 5432 (hardcoded fallback)
    # REMOVED_SYNTAX_ERROR: 3. This causes connectivity failures during database operations

    # REMOVED_SYNTAX_ERROR: Business Value Justification (BVJ):
        # REMOVED_SYNTAX_ERROR: - Segment: Platform/Internal
        # REMOVED_SYNTAX_ERROR: - Business Goal: Platform Stability and Reliability
        # REMOVED_SYNTAX_ERROR: - Value Impact: Prevents database connectivity failures across services
        # REMOVED_SYNTAX_ERROR: - Strategic Impact: Ensures consistent database configuration and eliminates service startup failures

        # REMOVED_SYNTAX_ERROR: This test is designed to FAIL initially, exposing the port mismatch issue,
        # REMOVED_SYNTAX_ERROR: and PASS once the DatabaseURLBuilder is fixed to use consistent ports.
        # REMOVED_SYNTAX_ERROR: '''

        # REMOVED_SYNTAX_ERROR: import os
        # REMOVED_SYNTAX_ERROR: import sys
        # REMOVED_SYNTAX_ERROR: import pytest
        # REMOVED_SYNTAX_ERROR: import asyncio
        # REMOVED_SYNTAX_ERROR: from typing import Dict, Any
        # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

        # Add project root to path for imports
        # REMOVED_SYNTAX_ERROR: from pathlib import Path
        # REMOVED_SYNTAX_ERROR: project_root = Path(__file__).parent.parent.parent
        # REMOVED_SYNTAX_ERROR: sys.path.insert(0, str(project_root))

        # REMOVED_SYNTAX_ERROR: from shared.database_url_builder import DatabaseURLBuilder
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient


# REMOVED_SYNTAX_ERROR: class DatabasePortConfigurationTester:
    # REMOVED_SYNTAX_ERROR: """Test class to validate database port configuration consistency."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.test_scenarios = []
    # REMOVED_SYNTAX_ERROR: self.results = {}

# REMOVED_SYNTAX_ERROR: def create_test_environment(self, port: str) -> Dict[str, str]:
    # REMOVED_SYNTAX_ERROR: """Create a test environment with specific port configuration."""
    # REMOVED_SYNTAX_ERROR: return { )
    # REMOVED_SYNTAX_ERROR: 'ENVIRONMENT': 'development',
    # REMOVED_SYNTAX_ERROR: 'POSTGRES_HOST': 'localhost',
    # REMOVED_SYNTAX_ERROR: 'POSTGRES_PORT': port,
    # REMOVED_SYNTAX_ERROR: 'POSTGRES_USER': 'postgres',
    # REMOVED_SYNTAX_ERROR: 'POSTGRES_PASSWORD': 'DTprdt5KoQXlEG4Gh9lF',
    # REMOVED_SYNTAX_ERROR: 'POSTGRES_DB': 'netra_dev',
    # REMOVED_SYNTAX_ERROR: 'DATABASE_URL': 'formatted_string'
    

# REMOVED_SYNTAX_ERROR: def extract_port_from_url(self, url: str) -> str:
    # REMOVED_SYNTAX_ERROR: """Extract port number from database URL."""
    # REMOVED_SYNTAX_ERROR: if not url:
        # REMOVED_SYNTAX_ERROR: return "NO_URL"

        # REMOVED_SYNTAX_ERROR: try:
            # Handle standard URL format
            # REMOVED_SYNTAX_ERROR: import re
            # Match pattern like @hostname:port/database
            # REMOVED_SYNTAX_ERROR: match = re.search(r'@pytest.fixture/', url)
            # REMOVED_SYNTAX_ERROR: if match:
                # REMOVED_SYNTAX_ERROR: return match.group(1)

                # Handle cases without explicit port (defaults to 5432)
                # REMOVED_SYNTAX_ERROR: if '@pytest.fixture[1].split('/')[0]:
                    # REMOVED_SYNTAX_ERROR: return "5432"  # PostgreSQL default

                    # REMOVED_SYNTAX_ERROR: return "UNKNOWN_FORMAT"
                    # REMOVED_SYNTAX_ERROR: except Exception:
                        # REMOVED_SYNTAX_ERROR: return "PARSE_ERROR"

# REMOVED_SYNTAX_ERROR: def test_port_consistency(self, env_vars: Dict[str, str]) -> Dict[str, Any]:
    # REMOVED_SYNTAX_ERROR: """Test port consistency between async and sync URLs."""
    # REMOVED_SYNTAX_ERROR: builder = DatabaseURLBuilder(env_vars)

    # Get URLs
    # REMOVED_SYNTAX_ERROR: async_url = builder.get_url_for_environment(sync=False)
    # REMOVED_SYNTAX_ERROR: sync_url = builder.get_url_for_environment(sync=True)

    # Extract ports
    # REMOVED_SYNTAX_ERROR: async_port = self.extract_port_from_url(async_url)
    # REMOVED_SYNTAX_ERROR: sync_port = self.extract_port_from_url(sync_url)
    # REMOVED_SYNTAX_ERROR: expected_port = env_vars.get('POSTGRES_PORT', '5432')

    # REMOVED_SYNTAX_ERROR: result = { )
    # REMOVED_SYNTAX_ERROR: 'environment': env_vars.get('ENVIRONMENT', 'unknown'),
    # REMOVED_SYNTAX_ERROR: 'configured_port': expected_port,
    # REMOVED_SYNTAX_ERROR: 'async_url': DatabaseURLBuilder.mask_url_for_logging(async_url),
    # REMOVED_SYNTAX_ERROR: 'sync_url': DatabaseURLBuilder.mask_url_for_logging(sync_url),
    # REMOVED_SYNTAX_ERROR: 'async_port': async_port,
    # REMOVED_SYNTAX_ERROR: 'sync_port': sync_port,
    # REMOVED_SYNTAX_ERROR: 'ports_match': async_port == sync_port,
    # REMOVED_SYNTAX_ERROR: 'async_port_correct': async_port == expected_port,
    # REMOVED_SYNTAX_ERROR: 'sync_port_correct': sync_port == expected_port,
    # REMOVED_SYNTAX_ERROR: 'overall_consistent': async_port == sync_port == expected_port,
    # REMOVED_SYNTAX_ERROR: 'issues': []
    

    # Identify issues
    # REMOVED_SYNTAX_ERROR: if not result['ports_match']:
        # REMOVED_SYNTAX_ERROR: result['issues'].append("formatted_string")

        # REMOVED_SYNTAX_ERROR: if not result['async_port_correct']:
            # REMOVED_SYNTAX_ERROR: result['issues'].append("formatted_string")

            # REMOVED_SYNTAX_ERROR: if not result['sync_port_correct']:
                # REMOVED_SYNTAX_ERROR: result['issues'].append("formatted_string")

                # REMOVED_SYNTAX_ERROR: return result


# REMOVED_SYNTAX_ERROR: class TestDatabasePortConfigurationMismatch:
    # REMOVED_SYNTAX_ERROR: """Test suite to expose and validate database port configuration issues."""

# REMOVED_SYNTAX_ERROR: def test_port_5433_configuration_consistency(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: CRITICAL TEST: Expose port mismatch between async and sync URLs.

    # REMOVED_SYNTAX_ERROR: This test demonstrates the specific issue where:
        # REMOVED_SYNTAX_ERROR: - Dev environment is configured to use port 5433
        # REMOVED_SYNTAX_ERROR: - Async URLs correctly use port 5433
        # REMOVED_SYNTAX_ERROR: - Sync URLs incorrectly default to port 5432

        # REMOVED_SYNTAX_ERROR: This test should FAIL initially, proving the configuration mismatch.
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: pass
        # REMOVED_SYNTAX_ERROR: tester = DatabasePortConfigurationTester()

        # Test with port 5433 (current dev configuration)
        # REMOVED_SYNTAX_ERROR: env_5433 = tester.create_test_environment('5433')

        # REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, env_5433, clear=False):
            # REMOVED_SYNTAX_ERROR: result = tester.test_port_consistency(env_5433)

            # Print detailed results for debugging
            # REMOVED_SYNTAX_ERROR: print(f" )
            # REMOVED_SYNTAX_ERROR: === PORT 5433 CONFIGURATION TEST ===")
            # REMOVED_SYNTAX_ERROR: print("formatted_string")
            # REMOVED_SYNTAX_ERROR: print("formatted_string")
            # REMOVED_SYNTAX_ERROR: print("formatted_string")
            # REMOVED_SYNTAX_ERROR: print("formatted_string")
            # REMOVED_SYNTAX_ERROR: print("formatted_string")
            # REMOVED_SYNTAX_ERROR: print("formatted_string")
            # REMOVED_SYNTAX_ERROR: print("formatted_string")
            # REMOVED_SYNTAX_ERROR: print("formatted_string")

            # REMOVED_SYNTAX_ERROR: if result['issues']:
                # REMOVED_SYNTAX_ERROR: print(f"Issues Found:")
                # REMOVED_SYNTAX_ERROR: for issue in result['issues']:
                    # REMOVED_SYNTAX_ERROR: print("formatted_string")

                    # This assertion should FAIL initially, exposing the mismatch
                    # REMOVED_SYNTAX_ERROR: assert result['overall_consistent'], ( )
                    # REMOVED_SYNTAX_ERROR: f"DATABASE PORT CONFIGURATION MISMATCH DETECTED:
                        # REMOVED_SYNTAX_ERROR: "
                        # REMOVED_SYNTAX_ERROR: "formatted_string"
                            # REMOVED_SYNTAX_ERROR: "formatted_string"
                            # REMOVED_SYNTAX_ERROR: "formatted_string"
                            # REMOVED_SYNTAX_ERROR: "formatted_string"
                            # REMOVED_SYNTAX_ERROR: f"This demonstrates the critical port configuration issue where sync URLs
                            # REMOVED_SYNTAX_ERROR: "
                            # REMOVED_SYNTAX_ERROR: f"ignore environment configuration and default to port 5432."
                            

# REMOVED_SYNTAX_ERROR: def test_port_5432_configuration_consistency(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: BASELINE TEST: Verify standard port 5432 works correctly.

    # REMOVED_SYNTAX_ERROR: This test should PASS, showing that the issue is specific to
    # REMOVED_SYNTAX_ERROR: non-standard ports like 5433 used in development.
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: tester = DatabasePortConfigurationTester()

    # Test with standard port 5432
    # REMOVED_SYNTAX_ERROR: env_5432 = tester.create_test_environment('5432')

    # REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, env_5432, clear=False):
        # REMOVED_SYNTAX_ERROR: result = tester.test_port_consistency(env_5432)

        # REMOVED_SYNTAX_ERROR: print(f" )
        # REMOVED_SYNTAX_ERROR: === PORT 5432 BASELINE TEST ===")
        # REMOVED_SYNTAX_ERROR: print("formatted_string")
        # REMOVED_SYNTAX_ERROR: print("formatted_string")
        # REMOVED_SYNTAX_ERROR: print("formatted_string")
        # REMOVED_SYNTAX_ERROR: print("formatted_string")

        # This should pass since 5432 is the default
        # REMOVED_SYNTAX_ERROR: assert result['overall_consistent'], ( )
        # REMOVED_SYNTAX_ERROR: "formatted_string"
        

# REMOVED_SYNTAX_ERROR: def test_multiple_port_configurations(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: COMPREHENSIVE TEST: Test various port configurations.

    # REMOVED_SYNTAX_ERROR: This test validates port consistency across different port values
    # REMOVED_SYNTAX_ERROR: to ensure the fix works for any port configuration.
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: tester = DatabasePortConfigurationTester()

    # REMOVED_SYNTAX_ERROR: test_ports = ['5432', '5433', '5434', '15432']
    # REMOVED_SYNTAX_ERROR: results = {}

    # REMOVED_SYNTAX_ERROR: for port in test_ports:
        # REMOVED_SYNTAX_ERROR: env_config = tester.create_test_environment(port)

        # REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, env_config, clear=False):
            # REMOVED_SYNTAX_ERROR: results[port] = tester.test_port_consistency(env_config)

            # REMOVED_SYNTAX_ERROR: print(f" )
            # REMOVED_SYNTAX_ERROR: === MULTIPLE PORT CONFIGURATION TEST ===")

            # REMOVED_SYNTAX_ERROR: all_consistent = True
            # REMOVED_SYNTAX_ERROR: for port, result in results.items():
                # REMOVED_SYNTAX_ERROR: status = "[OK] CONSISTENT" if result['overall_consistent'] else "[FAIL] INCONSISTENT"
                # REMOVED_SYNTAX_ERROR: print("formatted_string")
                # REMOVED_SYNTAX_ERROR: if result['issues']:
                    # REMOVED_SYNTAX_ERROR: for issue in result['issues']:
                        # REMOVED_SYNTAX_ERROR: print("formatted_string")

                        # REMOVED_SYNTAX_ERROR: if not result['overall_consistent']:
                            # REMOVED_SYNTAX_ERROR: all_consistent = False

                            # REMOVED_SYNTAX_ERROR: assert all_consistent, ( )
                            # REMOVED_SYNTAX_ERROR: f"Port configuration inconsistencies found across multiple ports. "
                            # REMOVED_SYNTAX_ERROR: f"This indicates the DatabaseURLBuilder has systematic issues with "
                            # REMOVED_SYNTAX_ERROR: f"non-standard port configurations."
                            

                            # Removed problematic line: @pytest.mark.asyncio
                            # Removed problematic line: async def test_actual_database_connectivity_with_port_mismatch(self):
                                # REMOVED_SYNTAX_ERROR: '''
                                # REMOVED_SYNTAX_ERROR: INTEGRATION TEST: Demonstrate how port mismatch causes real connectivity failures.

                                # REMOVED_SYNTAX_ERROR: This test shows the real-world impact of the port configuration issue.
                                # REMOVED_SYNTAX_ERROR: '''
                                # REMOVED_SYNTAX_ERROR: pass
                                # Test environment with port 5433 (where database is running)
                                # REMOVED_SYNTAX_ERROR: env_vars = { )
                                # REMOVED_SYNTAX_ERROR: 'ENVIRONMENT': 'development',
                                # REMOVED_SYNTAX_ERROR: 'POSTGRES_HOST': 'localhost',
                                # REMOVED_SYNTAX_ERROR: 'POSTGRES_PORT': '5433',  # Database runs on 5433
                                # REMOVED_SYNTAX_ERROR: 'POSTGRES_USER': 'postgres',
                                # REMOVED_SYNTAX_ERROR: 'POSTGRES_PASSWORD': 'DTprdt5KoQXlEG4Gh9lF',
                                # REMOVED_SYNTAX_ERROR: 'POSTGRES_DB': 'netra_dev'
                                

                                # REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, env_vars, clear=False):
                                    # REMOVED_SYNTAX_ERROR: builder = DatabaseURLBuilder(env_vars)

                                    # REMOVED_SYNTAX_ERROR: async_url = builder.get_url_for_environment(sync=False)
                                    # REMOVED_SYNTAX_ERROR: sync_url = builder.get_url_for_environment(sync=True)

                                    # REMOVED_SYNTAX_ERROR: print(f" )
                                    # REMOVED_SYNTAX_ERROR: === CONNECTIVITY TEST ===")
                                    # REMOVED_SYNTAX_ERROR: print("formatted_string")
                                    # REMOVED_SYNTAX_ERROR: print("formatted_string")

                                    # Try to connect using both URLs
                                    # REMOVED_SYNTAX_ERROR: try:
                                        # REMOVED_SYNTAX_ERROR: import asyncpg

                                        # Test async URL (should work - connects to 5433)
                                        # REMOVED_SYNTAX_ERROR: async_connection_url = DatabaseURLBuilder.format_for_asyncpg_driver(async_url)
                                        # REMOVED_SYNTAX_ERROR: print("formatted_string")

                                        # REMOVED_SYNTAX_ERROR: try:
                                            # REMOVED_SYNTAX_ERROR: conn = await asyncpg.connect(async_connection_url, timeout=2)
                                            # REMOVED_SYNTAX_ERROR: await conn.close()
                                            # REMOVED_SYNTAX_ERROR: async_works = True
                                            # REMOVED_SYNTAX_ERROR: print("[OK] Async connection successful")
                                            # REMOVED_SYNTAX_ERROR: except Exception as e:
                                                # REMOVED_SYNTAX_ERROR: async_works = False
                                                # REMOVED_SYNTAX_ERROR: print("formatted_string")

                                                # Test sync URL (might fail - tries to connect to 5432)
                                                # REMOVED_SYNTAX_ERROR: sync_connection_url = DatabaseURLBuilder.format_for_asyncpg_driver(sync_url)
                                                # REMOVED_SYNTAX_ERROR: print("formatted_string")

                                                # REMOVED_SYNTAX_ERROR: try:
                                                    # REMOVED_SYNTAX_ERROR: conn = await asyncpg.connect(sync_connection_url, timeout=2)
                                                    # REMOVED_SYNTAX_ERROR: await conn.close()
                                                    # REMOVED_SYNTAX_ERROR: sync_works = True
                                                    # REMOVED_SYNTAX_ERROR: print("[OK] Sync URL connection successful")
                                                    # REMOVED_SYNTAX_ERROR: except Exception as e:
                                                        # REMOVED_SYNTAX_ERROR: sync_works = False
                                                        # REMOVED_SYNTAX_ERROR: print("formatted_string")

                                                        # If async works but sync doesn't, we've proven the port mismatch issue
                                                        # REMOVED_SYNTAX_ERROR: if async_works and not sync_works:
                                                            # REMOVED_SYNTAX_ERROR: pytest.fail( )
                                                            # REMOVED_SYNTAX_ERROR: "CONNECTIVITY FAILURE DUE TO PORT MISMATCH:
                                                                # REMOVED_SYNTAX_ERROR: "
                                                                # REMOVED_SYNTAX_ERROR: f"- Async URL (port 5433) connects successfully
                                                                # REMOVED_SYNTAX_ERROR: "
                                                                # REMOVED_SYNTAX_ERROR: f"- Sync URL (wrong port) fails to connect
                                                                # REMOVED_SYNTAX_ERROR: "
                                                                # REMOVED_SYNTAX_ERROR: "This proves that the port configuration mismatch causes real connectivity issues."
                                                                
                                                                # REMOVED_SYNTAX_ERROR: elif not async_works and not sync_works:
                                                                    # REMOVED_SYNTAX_ERROR: pytest.skip("Database not available for connectivity test")
                                                                    # REMOVED_SYNTAX_ERROR: else:
                                                                        # REMOVED_SYNTAX_ERROR: print("Both connections work - database may be running on both ports")

                                                                        # REMOVED_SYNTAX_ERROR: except ImportError:
                                                                            # REMOVED_SYNTAX_ERROR: pytest.skip("asyncpg not available for connectivity test")


# REMOVED_SYNTAX_ERROR: class TestDatabaseURLBuilderPortLogic:
    # REMOVED_SYNTAX_ERROR: """Test the specific logic in DatabaseURLBuilder that causes port mismatches."""

# REMOVED_SYNTAX_ERROR: def test_development_builder_port_consistency(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: UNIT TEST: Test DevelopmentBuilder port consistency logic.

    # REMOVED_SYNTAX_ERROR: This test directly examines the DevelopmentBuilder class to identify
    # REMOVED_SYNTAX_ERROR: where the port configuration is being ignored for sync URLs.
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # Environment with non-standard port
    # REMOVED_SYNTAX_ERROR: env_vars = { )
    # REMOVED_SYNTAX_ERROR: 'ENVIRONMENT': 'development',
    # REMOVED_SYNTAX_ERROR: 'POSTGRES_HOST': 'localhost',
    # REMOVED_SYNTAX_ERROR: 'POSTGRES_PORT': '5433',
    # REMOVED_SYNTAX_ERROR: 'POSTGRES_USER': 'postgres',
    # REMOVED_SYNTAX_ERROR: 'POSTGRES_PASSWORD': 'test_pass',
    # REMOVED_SYNTAX_ERROR: 'POSTGRES_DB': 'netra_dev'
    

    # REMOVED_SYNTAX_ERROR: builder = DatabaseURLBuilder(env_vars)

    # REMOVED_SYNTAX_ERROR: print(f" )
    # REMOVED_SYNTAX_ERROR: === DEVELOPMENT BUILDER ANALYSIS ===")
    # REMOVED_SYNTAX_ERROR: print(f"Environment variables:")
    # REMOVED_SYNTAX_ERROR: print("formatted_string")
    # REMOVED_SYNTAX_ERROR: print("formatted_string")

    # Test TCP builder (should use environment variables)
    # REMOVED_SYNTAX_ERROR: print(f" )
    # REMOVED_SYNTAX_ERROR: TCP Builder:")
    # REMOVED_SYNTAX_ERROR: print("formatted_string")
    # REMOVED_SYNTAX_ERROR: print("formatted_string")
    # REMOVED_SYNTAX_ERROR: print("formatted_string")

    # Test development builder
    # REMOVED_SYNTAX_ERROR: print(f" )
    # REMOVED_SYNTAX_ERROR: Development Builder:")
    # REMOVED_SYNTAX_ERROR: print("formatted_string")
    # REMOVED_SYNTAX_ERROR: print("formatted_string")
    # REMOVED_SYNTAX_ERROR: print("formatted_string")

    # Test environment-based URL selection
    # REMOVED_SYNTAX_ERROR: async_url = builder.get_url_for_environment(sync=False)
    # REMOVED_SYNTAX_ERROR: sync_url = builder.get_url_for_environment(sync=True)

    # REMOVED_SYNTAX_ERROR: print(f" )
    # REMOVED_SYNTAX_ERROR: Environment URL Selection:")
    # REMOVED_SYNTAX_ERROR: print("formatted_string")
    # REMOVED_SYNTAX_ERROR: print("formatted_string")

    # Extract ports to verify the issue
    # REMOVED_SYNTAX_ERROR: tester = DatabasePortConfigurationTester()
    # REMOVED_SYNTAX_ERROR: async_port = tester.extract_port_from_url(async_url)
    # REMOVED_SYNTAX_ERROR: sync_port = tester.extract_port_from_url(sync_url)

    # REMOVED_SYNTAX_ERROR: print(f" )
    # REMOVED_SYNTAX_ERROR: Port Analysis:")
    # REMOVED_SYNTAX_ERROR: print("formatted_string")
    # REMOVED_SYNTAX_ERROR: print("formatted_string")
    # REMOVED_SYNTAX_ERROR: print("formatted_string")

    # The bug: sync URL should use the same port as async URL
    # REMOVED_SYNTAX_ERROR: assert async_port == env_vars['POSTGRES_PORT'], ( )
    # REMOVED_SYNTAX_ERROR: "formatted_string"
    

    # This assertion should FAIL, exposing the bug
    # REMOVED_SYNTAX_ERROR: assert sync_port == env_vars['POSTGRES_PORT'], ( )
    # REMOVED_SYNTAX_ERROR: f"SYNC URL PORT MISMATCH BUG:
        # REMOVED_SYNTAX_ERROR: "
        # REMOVED_SYNTAX_ERROR: "formatted_string"
        # REMOVED_SYNTAX_ERROR: "formatted_string"
        # REMOVED_SYNTAX_ERROR: "formatted_string"
        # REMOVED_SYNTAX_ERROR: f"The sync URL is using hardcoded default port instead of environment configuration.
        # REMOVED_SYNTAX_ERROR: "
        # REMOVED_SYNTAX_ERROR: f"This happens in the DevelopmentBuilder.default_sync_url property."
        


        # Additional diagnostic function for debugging
# REMOVED_SYNTAX_ERROR: def diagnose_port_configuration():
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Diagnostic function to understand the current database configuration.
    # REMOVED_SYNTAX_ERROR: Can be run independently for debugging purposes.
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env

    # REMOVED_SYNTAX_ERROR: print("=== DATABASE PORT CONFIGURATION DIAGNOSIS ===")

    # REMOVED_SYNTAX_ERROR: env = get_env()
    # REMOVED_SYNTAX_ERROR: env_vars = env.get_all()

    # REMOVED_SYNTAX_ERROR: print(f" )
    # REMOVED_SYNTAX_ERROR: Environment Variables:")
    # REMOVED_SYNTAX_ERROR: for key in ['ENVIRONMENT', 'POSTGRES_HOST', 'POSTGRES_PORT', 'POSTGRES_USER', 'POSTGRES_DB']:
        # REMOVED_SYNTAX_ERROR: value = env_vars.get(key, 'NOT SET')
        # REMOVED_SYNTAX_ERROR: print("formatted_string")

        # REMOVED_SYNTAX_ERROR: builder = DatabaseURLBuilder(env_vars)

        # REMOVED_SYNTAX_ERROR: print(f" )
        # REMOVED_SYNTAX_ERROR: Generated URLs:")
        # REMOVED_SYNTAX_ERROR: print("formatted_string")
        # REMOVED_SYNTAX_ERROR: print("formatted_string")

        # REMOVED_SYNTAX_ERROR: tester = DatabasePortConfigurationTester()
        # REMOVED_SYNTAX_ERROR: result = tester.test_port_consistency(env_vars)

        # REMOVED_SYNTAX_ERROR: print(f" )
        # REMOVED_SYNTAX_ERROR: Port Consistency Analysis:")
        # REMOVED_SYNTAX_ERROR: print("formatted_string")
        # REMOVED_SYNTAX_ERROR: print("formatted_string")
        # REMOVED_SYNTAX_ERROR: print("formatted_string")
        # REMOVED_SYNTAX_ERROR: print("formatted_string")

        # REMOVED_SYNTAX_ERROR: if result['issues']:
            # REMOVED_SYNTAX_ERROR: print(f" )
            # REMOVED_SYNTAX_ERROR: Issues Found:")
            # REMOVED_SYNTAX_ERROR: for issue in result['issues']:
                # REMOVED_SYNTAX_ERROR: print("formatted_string")


                # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                    # Run diagnostic when executed directly
                    # REMOVED_SYNTAX_ERROR: diagnose_port_configuration()