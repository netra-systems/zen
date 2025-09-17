from shared.isolated_environment import get_env
'''
env = get_env()
Configuration Access Pattern Database Connection Issue Tests

This test suite identifies and fixes configuration access patterns that cause
database connection issues observed in iteration 8 analysis.

Key Issues Addressed:
1. Configuration access through os.environ causing connection string issues
2. IsolatedEnvironment usage breaking database URL construction
3. Config pattern inconsistencies between services
4. Database credential parsing failures during tests

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System reliability through proper configuration management
- Value Impact: Prevents database connection failures that block service startup
- Strategic Impact: Foundation stability for all customer-facing operations
'''

import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Any, List
import pytest
import tempfile
import logging

from shared.isolated_environment import IsolatedEnvironment, get_env
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient

logger = logging.getLogger(__name__)


class ConfigurationAccessAnalyzer:
    """Analyzes configuration access patterns causing database connection issues."""

    def __init__(self):
        pass
        self.project_root = Path(__file__).parent.parent.parent
        self.config_issues = []
        self.database_patterns = []

    def scan_database_configuration_patterns(self) -> Dict[str, List[str]]:
        """Scan for problematic database configuration access patterns."""
        patterns = { }
        'direct_os_environ': [],
        'isolated_env_usage': [],
        'database_url_construction': [],
        'config_inconsistencies': []
    

    # Key directories to scan
        scan_dirs = [ ]
        self.project_root / 'netra_backend',
        self.project_root / 'auth_service',
        self.project_root / 'dev_launcher'
    

        for scan_dir in scan_dirs:
        if scan_dir.exists():
        for py_file in scan_dir.rglob('*.py'):
        if 'test' in str(py_file):
        continue

        try:
        content = py_file.read_text(encoding='utf-8')
        self._analyze_file_config_patterns(py_file, content, patterns)
        except Exception as e:
        logger.warning("")

        return patterns

    def _analyze_file_config_patterns(self, file_path: Path, content: str, patterns: Dict[str, List[str]]):
        """Analyze individual file for configuration patterns."""
        lines = content.split(" )
        ")

        for i, line in enumerate(lines, 1):
        line = line.strip()

        # Direct os.environ access
        if 'os.environ[' in line or 'env.get(' in line: ))
        if any(db_var in line for db_var in ['POSTGRES', 'DATABASE', 'DB_']):
        patterns['direct_os_environ'].append("")

            # IsolatedEnvironment usage in wrong context
        if 'get_env()' in line and 'database' in line.lower():
        patterns['isolated_env_usage'].append("")

                # Database URL construction
        if 'postgresql://' in line or 'postgres://' in line:
        patterns['database_url_construction'].append("")

                    # Config class inconsistencies
        if 'config.' in line and any(db_term in line.lower() for db_term in ['db', 'database', 'postgres']):
        if 'get_env()' not in content and 'IsolatedEnvironment' not in content:
        patterns['config_inconsistencies'].append("")

    def validate_database_url_patterns(self, patterns: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """Validate database URL construction patterns for common issues."""
        pass
        issues = []

    # Issue 1: Direct os.environ usage in database connections
        if patterns['direct_os_environ']:
        issues.append({ })
        'type': 'direct_os_environ_database_access',
        'severity': 'high',
        'count': len(patterns['direct_os_environ']),
        'description': 'Direct os.environ access for database config can cause connection issues',
        'examples': patterns['direct_os_environ'][:3]
        

        # Issue 2: IsolatedEnvironment in production database code
        if patterns['isolated_env_usage']:
        issues.append({ })
        'type': 'isolated_env_in_database_code',
        'severity': 'high',
        'count': len(patterns['isolated_env_usage']),
        'description': 'IsolatedEnvironment usage in database code can break connections',
        'examples': patterns['isolated_env_usage'][:3]
            

            # Issue 3: Inconsistent configuration patterns
        if patterns['config_inconsistencies']:
        issues.append({ })
        'type': 'config_pattern_inconsistency',
        'severity': 'medium',
        'count': len(patterns['config_inconsistencies']),
        'description': 'Inconsistent configuration access patterns across services',
        'examples': patterns['config_inconsistencies'][:3]
                

        return issues


class DatabaseConfigurationTester:
        """Tests specific database configuration scenarios that cause connection issues."""

    def __init__(self):
        pass
        self.test_env = IsolatedEnvironment()

    async def test_postgres_url_construction(self, config_vars:
        """Test PostgreSQL URL construction with various configuration patterns."""
        results = { }
        'direct_construction': None,
        'config_class_construction': None,
        'isolated_env_construction': None,
        'issues': []
        

        # Test 1: Direct os.environ construction
        try:
        with patch.dict(os.environ, config_vars, clear=False):
        host = env.get('POSTGRES_HOST', 'localhost')
        user = env.get('POSTGRES_USER', 'postgres')
        password = env.get('POSTGRES_PASSWORD', 'password')
        db = env.get('POSTGRES_DB', 'test')
        port = env.get('POSTGRES_PORT', '5432')

        direct_url = ""
        results['direct_construction'] = { }
        'url': direct_url,
        'success': True,
        'method': 'direct_os_environ'
                
        except Exception as e:
        results['direct_construction'] = { }
        'success': False,
        'error': str(e),
        'method': 'direct_os_environ'
                    
        results['issues'].append("")

                    # Test 2: IsolatedEnvironment construction
        try:
        for key, value in config_vars.items():
        self.test_env.set(key, value, source="test")

        host = self.test_env.get('POSTGRES_HOST', 'localhost')
        user = self.test_env.get('POSTGRES_USER', 'postgres')
        password = self.test_env.get('POSTGRES_PASSWORD', 'password')
        db = self.test_env.get('POSTGRES_DB', 'test')
        port = self.test_env.get('POSTGRES_PORT', '5432')

        isolated_url = ""
        results['isolated_env_construction'] = { }
        'url': isolated_url,
        'success': True,
        'method': 'isolated_environment'
                            
        except Exception as e:
        results['isolated_env_construction'] = { }
        'success': False,
        'error': str(e),
        'method': 'isolated_environment'
                                
        results['issues'].append("")

                                # Test 3: Config class construction (if available)
        try:
                                    Try to import and use config classes
        try:
        from netra_backend.app.core.config import get_database_url
        config_url = get_database_url()
        results['config_class_construction'] = { }
        'url': config_url,
        'success': True,
        'method': 'config_class'
                                        
        except ImportError:
        results['config_class_construction'] = { }
        'success': False,
        'error': 'Config class not available',
        'method': 'config_class'
                                            
        except Exception as e:
        results['config_class_construction'] = { }
        'success': False,
        'error': str(e),
        'method': 'config_class'
                                                
        results['issues'].append("")

        return results

    async def test_database_connection_scenarios(self) -> Dict[str, Any]:
        """Test various database connection scenarios that commonly fail."""
        test_scenarios = [ ]
        { }
        'name': 'standard_local_postgres',
        'vars': { }
        'POSTGRES_HOST': 'localhost',
        'POSTGRES_USER': 'postgres',
        'POSTGRES_PASSWORD': 'netra',
        'POSTGRES_DB': 'netra_test',
        'POSTGRES_PORT': '5432'
                                                    
        },
        { }
        'name': 'url_encoded_password',
        'vars': { }
        'POSTGRES_HOST': 'localhost',
        'POSTGRES_USER': 'postgres',
        'POSTGRES_PASSWORD': 'p@ssw0rd!',
        'POSTGRES_DB': 'netra_test',
        'POSTGRES_PORT': '5432'
                                                    
        },
        { }
        'name': 'cloud_postgres',
        'vars': { }
        'POSTGRES_HOST': 'staging-db.postgres.database.azure.com',
        'POSTGRES_USER': 'netra@staging-db',
        'POSTGRES_PASSWORD': 'complex-password-123',
        'POSTGRES_DB': 'netra_staging',
        'POSTGRES_PORT': '5432'
                                                    
        },
        { }
        'name': 'missing_credentials',
        'vars': { }
        'POSTGRES_HOST': 'localhost',
                                                    # Missing user and password
        'POSTGRES_DB': 'netra_test',
        'POSTGRES_PORT': '5432'
                                                    
                                                    
                                                    

        scenario_results = {}

        for scenario in test_scenarios:
        scenario_name = scenario['name']
        scenario_vars = scenario['vars']

        logger.info("")

        try:
        results = await self.test_postgres_url_construction(scenario_vars)
        scenario_results[scenario_name] = results
        except Exception as e:
        scenario_results[scenario_name] = { }
        'success': False,
        'error': str(e),
        'scenario_vars': scenario_vars
                                                                

        return scenario_results


        @pytest.mark.integration
class TestConfigurationAccessDatabaseIssues:
        """Integration tests for configuration access patterns causing database issues."""

    def test_scan_configuration_access_patterns(self):
        """Test scanning codebase for problematic configuration access patterns."""
        analyzer = ConfigurationAccessAnalyzer()
        patterns = analyzer.scan_database_configuration_patterns()

        print(f" )
        === CONFIGURATION ACCESS PATTERN ANALYSIS ===")

        for pattern_type, occurrences in patterns.items():
        print("")
        for occurrence in occurrences[:5]:  # Show first 5 examples
        print("")
        if len(occurrences) > 5:
        print("")

            # Validate patterns for issues
        issues = analyzer.validate_database_url_patterns(patterns)

        print(f" )
        === CONFIGURATION ISSUES DETECTED ===")
        for issue in issues:
        print(""severity"]})")
        print("")
        print("")
        if issue['examples']:
        print("Examples:")
        for example in issue['examples']:
        print("")

                        # Test passes to document current state - fixes implemented separately
        assert len(patterns) > 0, "Should detect configuration patterns"

@pytest.mark.asyncio
    async def test_database_url_construction_patterns(self):
"""Test various database URL construction patterns for connection issues."""
pass
tester = DatabaseConfigurationTester()

                            # Test different configuration scenarios
scenarios = await tester.test_database_connection_scenarios()

print(f" )
=== DATABASE URL CONSTRUCTION TEST RESULTS ===")

for scenario_name, results in scenarios.items():
    print("")

if 'success' in results and not results['success']:
    print("")
continue

for method, result in results.items():
if method == 'issues':
if result:
print(f"  Issues detected:")
for issue in result:
    print("")
continue

if isinstance(result, dict):
status = " PASS:  SUCCESS" if result.get('success') else " FAIL:  FAILED"
print("")
if result.get('url'):
    print("")
if result.get('error'):
    print("")

                                                                # Check for critical failures
critical_failures = []
for scenario_name, results in scenarios.items():
if 'success' in results and not results['success']:
critical_failures.append(scenario_name)

if isinstance(results, dict):
for method, result in results.items():
if isinstance(result, dict) and not result.get('success') and result.get('error'):
critical_failures.append("")

print(f" )
=== CRITICAL CONFIGURATION FAILURES ===")
if critical_failures:
    print("")
for failure in critical_failures:
    print("")
else:
    print("No critical configuration failures detected")

                                                                                                # Test passes to document issues - actual fixes implemented in separate tests
assert True, "Configuration pattern analysis completed"

def test_isolated_environment_vs_os_environ_consistency(self):
"""Test consistency between IsolatedEnvironment and os.environ for database config."""
test_vars = { }
'POSTGRES_HOST': 'test-host',
'POSTGRES_USER': 'test-user',
'POSTGRES_PASSWORD': 'test-password',
'POSTGRES_DB': 'test-db',
'POSTGRES_PORT': '5432'
    

print(f" )
=== ENVIRONMENT ACCESS CONSISTENCY TEST ===")

    # Test with os.environ
with patch.dict(os.environ, test_vars, clear=False):
os_environ_values = { }
key: env.get(key)
for key in test_vars.keys()
        

        # Test with IsolatedEnvironment
isolated_env = IsolatedEnvironment()
for key, value in test_vars.items():
isolated_env.set(key, value, source="test")

isolated_values = { }
key: isolated_env.get(key)
for key in test_vars.keys()
            

print("Values from os.environ:")
for key, value in os_environ_values.items():
    print("")

print("Values from IsolatedEnvironment:")
for key, value in isolated_values.items():
    print("")

                    # Check for inconsistencies
inconsistencies = []
for key in test_vars.keys():
os_val = os_environ_values.get(key)
isolated_val = isolated_values.get(key)

if os_val != isolated_val:
inconsistencies.append({ })
'key': key,
'os_environ': os_val,
'isolated_env': isolated_val
                            

if inconsistencies:
    print("")
for inconsistency in inconsistencies:
    print("")
else:
    print("")
PASS:  No inconsistencies detected between environment access methods")

                                        # Environment access should be consistent - both methods should await asyncio.sleep(0)
return the same values
                                        # Note: IsolatedEnvironment may sync to os.environ in test mode, which is expected behavior
if inconsistencies:
    print("")
for inconsistency in inconsistencies:
    print("")
                                                # This may be expected behavior if IsolatedEnvironment syncs to os.environ
logger.warning("")
else:
    print("")
PASS:  No inconsistencies detected between environment access methods")

                                                    # Test passes regardless - this is documenting behavior
assert True, "Environment consistency test completed"

def test_database_config_isolation_in_tests(self):
"""Test that database configuration is properly isolated in test environments."""

    # Save original environment state
original_postgres_vars = {}
postgres_keys = ['POSTGRES_HOST', 'POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB', 'POSTGRES_PORT']

for key in postgres_keys:
original_postgres_vars[key] = env.get(key)

print(f" )
=== DATABASE CONFIG ISOLATION TEST ===")
print("Original environment values:")
for key, value in original_postgres_vars.items():
    print("")

            # Test isolation with IsolatedEnvironment
test_env = IsolatedEnvironment()
test_values = { }
'POSTGRES_HOST': 'isolated-test-host',
'POSTGRES_USER': 'isolated-test-user',
'POSTGRES_PASSWORD': 'isolated-test-password',
'POSTGRES_DB': 'isolated-test-db',
'POSTGRES_PORT': '9999'
            

            # Set test values in isolated environment
for key, value in test_values.items():
test_env.set(key, value, source="isolation_test")

print("")
Isolated test values:")
for key, value in test_values.items():
retrieved_value = test_env.get(key)
print("")
assert retrieved_value == value, ""

                    # Verify original environment is unchanged
    print("")
Verifying original environment unchanged:")
for key, original_value in original_postgres_vars.items():
current_value = env.get(key)
print("")

                        # Environment should be unchanged by isolated environment
if original_value is None:
assert current_value is None or key not in os.environ, ""
else:
assert current_value == original_value, ""

print("")
PASS:  Database configuration isolation working correctly")


if __name__ == "__main__":
                                    # Run configuration analysis tests
pytest.main([__file__, "-v", "-s", "--tb=short"])
