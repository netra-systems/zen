"""
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
"""

import os
import sys
import pytest
import asyncio
from typing import Dict, Any
from unittest.mock import patch, MagicMock

# Add project root to path for imports
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.database_url_builder import DatabaseURLBuilder


class DatabasePortConfigurationTester:
    """Test class to validate database port configuration consistency."""
    
    def __init__(self):
        self.test_scenarios = []
        self.results = {}
        
    def create_test_environment(self, port: str) -> Dict[str, str]:
        """Create a test environment with specific port configuration."""
        return {
            'ENVIRONMENT': 'development',
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': port,
            'POSTGRES_USER': 'postgres',
            'POSTGRES_PASSWORD': 'DTprdt5KoQXlEG4Gh9lF',
            'POSTGRES_DB': 'netra_dev',
            'DATABASE_URL': f'postgresql+asyncpg://postgres:DTprdt5KoQXlEG4Gh9lF@localhost:{port}/netra_dev'
        }
    
    def extract_port_from_url(self, url: str) -> str:
        """Extract port number from database URL."""
        if not url:
            return "NO_URL"
        
        try:
            # Handle standard URL format
            import re
            # Match pattern like @hostname:port/database
            match = re.search(r'@[^:]+:(\d+)/', url)
            if match:
                return match.group(1)
            
            # Handle cases without explicit port (defaults to 5432)
            if '@' in url and ':' not in url.split('@')[1].split('/')[0]:
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
        
        result = {
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
        }
        
        # Identify issues
        if not result['ports_match']:
            result['issues'].append(f"Port mismatch: async={async_port}, sync={sync_port}")
        
        if not result['async_port_correct']:
            result['issues'].append(f"Async URL port {async_port} != configured {expected_port}")
            
        if not result['sync_port_correct']:
            result['issues'].append(f"Sync URL port {sync_port} != configured {expected_port}")
        
        return result


class TestDatabasePortConfigurationMismatch:
    """Test suite to expose and validate database port configuration issues."""
    
    def test_port_5433_configuration_consistency(self):
        """
        CRITICAL TEST: Expose port mismatch between async and sync URLs.
        
        This test demonstrates the specific issue where:
        - Dev environment is configured to use port 5433
        - Async URLs correctly use port 5433
        - Sync URLs incorrectly default to port 5432
        
        This test should FAIL initially, proving the configuration mismatch.
        """
        tester = DatabasePortConfigurationTester()
        
        # Test with port 5433 (current dev configuration)
        env_5433 = tester.create_test_environment('5433')
        
        with patch.dict(os.environ, env_5433, clear=False):
            result = tester.test_port_consistency(env_5433)
            
            # Print detailed results for debugging
            print(f"\n=== PORT 5433 CONFIGURATION TEST ===")
            print(f"Environment: {result['environment']}")
            print(f"Configured Port: {result['configured_port']}")
            print(f"Async URL: {result['async_url']}")
            print(f"Sync URL: {result['sync_url']}")
            print(f"Async Port: {result['async_port']}")
            print(f"Sync Port: {result['sync_port']}")
            print(f"Ports Match: {result['ports_match']}")
            print(f"Overall Consistent: {result['overall_consistent']}")
            
            if result['issues']:
                print(f"Issues Found:")
                for issue in result['issues']:
                    print(f"  - {issue}")
            
            # This assertion should FAIL initially, exposing the mismatch
            assert result['overall_consistent'], (
                f"DATABASE PORT CONFIGURATION MISMATCH DETECTED:\n"
                f"Environment configured for port {result['configured_port']}, but:\n"
                f"- Async URL uses port {result['async_port']}\n"
                f"- Sync URL uses port {result['sync_port']}\n"
                f"Issues: {', '.join(result['issues'])}\n\n"
                f"This demonstrates the critical port configuration issue where sync URLs\n"
                f"ignore environment configuration and default to port 5432."
            )
    
    def test_port_5432_configuration_consistency(self):
        """
        BASELINE TEST: Verify standard port 5432 works correctly.
        
        This test should PASS, showing that the issue is specific to
        non-standard ports like 5433 used in development.
        """
        tester = DatabasePortConfigurationTester()
        
        # Test with standard port 5432
        env_5432 = tester.create_test_environment('5432')
        
        with patch.dict(os.environ, env_5432, clear=False):
            result = tester.test_port_consistency(env_5432)
            
            print(f"\n=== PORT 5432 BASELINE TEST ===")
            print(f"Configured Port: {result['configured_port']}")
            print(f"Async Port: {result['async_port']}")
            print(f"Sync Port: {result['sync_port']}")
            print(f"Overall Consistent: {result['overall_consistent']}")
            
            # This should pass since 5432 is the default
            assert result['overall_consistent'], (
                f"Even standard port 5432 configuration is inconsistent: {result['issues']}"
            )
    
    def test_multiple_port_configurations(self):
        """
        COMPREHENSIVE TEST: Test various port configurations.
        
        This test validates port consistency across different port values
        to ensure the fix works for any port configuration.
        """
        tester = DatabasePortConfigurationTester()
        
        test_ports = ['5432', '5433', '5434', '15432']
        results = {}
        
        for port in test_ports:
            env_config = tester.create_test_environment(port)
            
            with patch.dict(os.environ, env_config, clear=False):
                results[port] = tester.test_port_consistency(env_config)
        
        print(f"\n=== MULTIPLE PORT CONFIGURATION TEST ===")
        
        all_consistent = True
        for port, result in results.items():
            status = "[OK] CONSISTENT" if result['overall_consistent'] else "[FAIL] INCONSISTENT"
            print(f"Port {port}: {status}")
            if result['issues']:
                for issue in result['issues']:
                    print(f"  - {issue}")
            
            if not result['overall_consistent']:
                all_consistent = False
        
        assert all_consistent, (
            f"Port configuration inconsistencies found across multiple ports. "
            f"This indicates the DatabaseURLBuilder has systematic issues with "
            f"non-standard port configurations."
        )
    
    @pytest.mark.asyncio
    async def test_actual_database_connectivity_with_port_mismatch(self):
        """
        INTEGRATION TEST: Demonstrate how port mismatch causes real connectivity failures.
        
        This test shows the real-world impact of the port configuration issue.
        """
        # Test environment with port 5433 (where database is running)
        env_vars = {
            'ENVIRONMENT': 'development',
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5433',  # Database runs on 5433
            'POSTGRES_USER': 'postgres',
            'POSTGRES_PASSWORD': 'DTprdt5KoQXlEG4Gh9lF',
            'POSTGRES_DB': 'netra_dev'
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            builder = DatabaseURLBuilder(env_vars)
            
            async_url = builder.get_url_for_environment(sync=False)
            sync_url = builder.get_url_for_environment(sync=True)
            
            print(f"\n=== CONNECTIVITY TEST ===")
            print(f"Async URL: {DatabaseURLBuilder.mask_url_for_logging(async_url)}")
            print(f"Sync URL: {DatabaseURLBuilder.mask_url_for_logging(sync_url)}")
            
            # Try to connect using both URLs
            try:
                import asyncpg
                
                # Test async URL (should work - connects to 5433)
                async_connection_url = DatabaseURLBuilder.format_for_asyncpg_driver(async_url)
                print(f"Testing async connection to: {DatabaseURLBuilder.mask_url_for_logging(async_connection_url)}")
                
                try:
                    conn = await asyncpg.connect(async_connection_url, timeout=2)
                    await conn.close()
                    async_works = True
                    print("[OK] Async connection successful")
                except Exception as e:
                    async_works = False
                    print(f"[FAIL] Async connection failed: {e}")
                
                # Test sync URL (might fail - tries to connect to 5432)
                sync_connection_url = DatabaseURLBuilder.format_for_asyncpg_driver(sync_url)
                print(f"Testing sync URL with asyncpg: {DatabaseURLBuilder.mask_url_for_logging(sync_connection_url)}")
                
                try:
                    conn = await asyncpg.connect(sync_connection_url, timeout=2)
                    await conn.close()
                    sync_works = True
                    print("[OK] Sync URL connection successful")
                except Exception as e:
                    sync_works = False
                    print(f"[FAIL] Sync URL connection failed: {e}")
                
                # If async works but sync doesn't, we've proven the port mismatch issue
                if async_works and not sync_works:
                    pytest.fail(
                        "CONNECTIVITY FAILURE DUE TO PORT MISMATCH:\n"
                        f"- Async URL (port 5433) connects successfully\n"
                        f"- Sync URL (wrong port) fails to connect\n"
                        "This proves that the port configuration mismatch causes real connectivity issues."
                    )
                elif not async_works and not sync_works:
                    pytest.skip("Database not available for connectivity test")
                else:
                    print("Both connections work - database may be running on both ports")
                    
            except ImportError:
                pytest.skip("asyncpg not available for connectivity test")


class TestDatabaseURLBuilderPortLogic:
    """Test the specific logic in DatabaseURLBuilder that causes port mismatches."""
    
    def test_development_builder_port_consistency(self):
        """
        UNIT TEST: Test DevelopmentBuilder port consistency logic.
        
        This test directly examines the DevelopmentBuilder class to identify
        where the port configuration is being ignored for sync URLs.
        """
        # Environment with non-standard port
        env_vars = {
            'ENVIRONMENT': 'development',
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5433',
            'POSTGRES_USER': 'postgres',
            'POSTGRES_PASSWORD': 'test_pass',
            'POSTGRES_DB': 'netra_dev'
        }
        
        builder = DatabaseURLBuilder(env_vars)
        
        print(f"\n=== DEVELOPMENT BUILDER ANALYSIS ===")
        print(f"Environment variables:")
        print(f"  POSTGRES_PORT: {env_vars['POSTGRES_PORT']}")
        print(f"  POSTGRES_HOST: {env_vars['POSTGRES_HOST']}")
        
        # Test TCP builder (should use environment variables)
        print(f"\nTCP Builder:")
        print(f"  Has config: {builder.tcp.has_config}")
        print(f"  Async URL: {DatabaseURLBuilder.mask_url_for_logging(builder.tcp.async_url)}")
        print(f"  Sync URL: {DatabaseURLBuilder.mask_url_for_logging(builder.tcp.sync_url)}")
        
        # Test development builder
        print(f"\nDevelopment Builder:")
        print(f"  Default URL: {DatabaseURLBuilder.mask_url_for_logging(builder.development.default_url)}")
        print(f"  Default Sync URL: {DatabaseURLBuilder.mask_url_for_logging(builder.development.default_sync_url)}")
        print(f"  Auto URL: {DatabaseURLBuilder.mask_url_for_logging(builder.development.auto_url)}")
        
        # Test environment-based URL selection
        async_url = builder.get_url_for_environment(sync=False)
        sync_url = builder.get_url_for_environment(sync=True)
        
        print(f"\nEnvironment URL Selection:")
        print(f"  Async (sync=False): {DatabaseURLBuilder.mask_url_for_logging(async_url)}")
        print(f"  Sync (sync=True): {DatabaseURLBuilder.mask_url_for_logging(sync_url)}")
        
        # Extract ports to verify the issue
        tester = DatabasePortConfigurationTester()
        async_port = tester.extract_port_from_url(async_url)
        sync_port = tester.extract_port_from_url(sync_url)
        
        print(f"\nPort Analysis:")
        print(f"  Expected port: {env_vars['POSTGRES_PORT']}")
        print(f"  Async URL port: {async_port}")
        print(f"  Sync URL port: {sync_port}")
        
        # The bug: sync URL should use the same port as async URL
        assert async_port == env_vars['POSTGRES_PORT'], (
            f"Async URL should use configured port {env_vars['POSTGRES_PORT']}, got {async_port}"
        )
        
        # This assertion should FAIL, exposing the bug
        assert sync_port == env_vars['POSTGRES_PORT'], (
            f"SYNC URL PORT MISMATCH BUG:\n"
            f"Expected port: {env_vars['POSTGRES_PORT']}\n"
            f"Async URL port: {async_port} (correct)\n"
            f"Sync URL port: {sync_port} (WRONG - ignores environment configuration)\n\n"
            f"The sync URL is using hardcoded default port instead of environment configuration.\n"
            f"This happens in the DevelopmentBuilder.default_sync_url property."
        )


# Additional diagnostic function for debugging
def diagnose_port_configuration():
    """
    Diagnostic function to understand the current database configuration.
    Can be run independently for debugging purposes.
    """
    from dev_launcher.isolated_environment import get_env
    
    print("=== DATABASE PORT CONFIGURATION DIAGNOSIS ===")
    
    env = get_env()
    env_vars = env.get_all()
    
    print(f"\nEnvironment Variables:")
    for key in ['ENVIRONMENT', 'POSTGRES_HOST', 'POSTGRES_PORT', 'POSTGRES_USER', 'POSTGRES_DB']:
        value = env_vars.get(key, 'NOT SET')
        print(f"  {key}: {value}")
    
    builder = DatabaseURLBuilder(env_vars)
    
    print(f"\nGenerated URLs:")
    print(f"  Async: {DatabaseURLBuilder.mask_url_for_logging(builder.get_url_for_environment(sync=False))}")
    print(f"  Sync: {DatabaseURLBuilder.mask_url_for_logging(builder.get_url_for_environment(sync=True))}")
    
    tester = DatabasePortConfigurationTester()
    result = tester.test_port_consistency(env_vars)
    
    print(f"\nPort Consistency Analysis:")
    print(f"  Configured: {result['configured_port']}")
    print(f"  Async Port: {result['async_port']}")
    print(f"  Sync Port: {result['sync_port']}")
    print(f"  Consistent: {result['overall_consistent']}")
    
    if result['issues']:
        print(f"\nIssues Found:")
        for issue in result['issues']:
            print(f"  - {issue}")


if __name__ == "__main__":
    # Run diagnostic when executed directly
    diagnose_port_configuration()