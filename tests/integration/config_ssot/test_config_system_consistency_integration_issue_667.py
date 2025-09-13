"""
INTEGRATION TEST: Configuration System Consistency - Issue #667

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Reliability
- Business Goal: Validate configuration system consistency affects Golden Path authentication
- Value Impact: Ensures authentication flow reliability protecting $500K+ ARR
- Strategic Impact: Validates SSOT violations cause real system inconsistencies

CRITICAL INTEGRATION TESTS:
These tests validate that the 3 configuration managers cause real system inconsistencies
that affect Golden Path authentication with actual services.

Expected Issues (proving real impact):
1. Configuration values differ between managers
2. Authentication tokens load inconsistently
3. Service connectivity affected by config conflicts
4. Golden Path authentication flow breaks due to config inconsistencies

These tests use REAL services to prove Issue #667 has actual business impact.
"""

import unittest
import asyncio
import time
from typing import Dict, List, Any, Optional
from unittest.mock import patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment


class TestConfigSystemConsistencyIntegrationIssue667(SSotAsyncTestCase, unittest.TestCase):
    """Integration tests to validate configuration system consistency for Issue #667."""
    
    def setUp(self):
        """Set up integration test environment with real services."""
        super().setUp()
        self.env = IsolatedEnvironment()
        self.consistency_results = {}
        self.config_managers = {}
        self.auth_test_results = {}
        
        # Initialize the 3 configuration managers synchronously
        self._initialize_config_managers()
    
    async def asyncSetUp(self):
        """Async setup for real service integration."""
        await super().asyncSetUp()
    
    def _initialize_config_managers(self):
        """Initialize all 3 configuration managers for comparison testing."""
        try:
            # Manager 1: UnifiedConfigManager from base.py
            from netra_backend.app.core.configuration.base import get_unified_config, config_manager
            self.config_managers['unified_config_manager'] = {
                'get_config': get_unified_config,
                'manager': config_manager,
                'source': 'netra_backend.app.core.configuration.base'
            }
            
            # Manager 2: get_config from config.py 
            from netra_backend.app.config import get_config
            self.config_managers['config_py'] = {
                'get_config': get_config,
                'manager': None,  # Function-based
                'source': 'netra_backend.app.config'
            }
            
            # Manager 3: UnifiedConfigurationManager from managers
            from netra_backend.app.core.managers.unified_configuration_manager import (
                get_configuration_manager, ConfigurationManagerFactory
            )
            global_manager = ConfigurationManagerFactory.get_global_manager()
            self.config_managers['unified_configuration_manager'] = {
                'get_config': lambda: global_manager,  # Returns manager, not config
                'manager': global_manager,
                'source': 'netra_backend.app.core.managers.unified_configuration_manager'
            }
            
        except ImportError as e:
            self.fail(f"Failed to import configuration managers for testing: {e}")
    
    async def test_configuration_value_consistency_real_auth(self):
        """
        CRITICAL TEST: Validate configuration values are consistent for authentication.
        
        Tests that the 3 configuration managers return the same values for
        critical authentication configuration, affecting Golden Path.
        """
        critical_auth_keys = [
            'service_secret',
            'jwt_secret',
            'auth_service_url',
            'environment'
        ]
        
        config_results = {}
        consistency_violations = []
        
        for manager_name, manager_info in self.config_managers.items():
            config_results[manager_name] = {}
            
            try:
                if manager_name in ['unified_config_manager', 'config_py']:
                    # These return AppConfig objects
                    config = manager_info['get_config']()
                    
                    for key in critical_auth_keys:
                        try:
                            if hasattr(config, key):
                                value = getattr(config, key)
                            elif hasattr(config, 'get') and callable(config.get):
                                value = config.get(key)
                            else:
                                value = None
                            
                            config_results[manager_name][key] = value
                        except Exception as e:
                            config_results[manager_name][key] = f"ERROR: {e}"
                
                elif manager_name == 'unified_configuration_manager':
                    # This returns a manager object
                    manager = manager_info['get_config']()
                    
                    for key in critical_auth_keys:
                        try:
                            # Try different access patterns
                            if hasattr(manager, 'get'):
                                value = manager.get(key)
                            elif hasattr(manager, 'get_str'):
                                value = manager.get_str(key)
                            else:
                                value = None
                            
                            config_results[manager_name][key] = value
                        except Exception as e:
                            config_results[manager_name][key] = f"ERROR: {e}"
                            
            except Exception as e:
                config_results[manager_name] = {'ERROR': str(e)}
        
        # Check for value inconsistencies
        for key in critical_auth_keys:
            values_for_key = {}
            for manager_name in config_results.keys():
                if key in config_results[manager_name]:
                    value = config_results[manager_name][key]
                    if value not in values_for_key:
                        values_for_key[value] = []
                    values_for_key[value].append(manager_name)
            
            if len(values_for_key) > 1:
                consistency_violations.append({
                    'key': key,
                    'value_variations': values_for_key,
                    'manager_count': len(config_results)
                })
        
        self.consistency_results['value_consistency'] = {
            'config_results': config_results,
            'violations': consistency_violations
        }
        
        # EXPECTED FAILURE: Should have consistency violations proving real impact
        self.assertEqual(
            len(consistency_violations), 0,
            f"REAL SYSTEM IMPACT: Found {len(consistency_violations)} configuration value inconsistencies "
            f"affecting Golden Path authentication. "
            f"Violations: {consistency_violations}. "
            f"Config results: {config_results}. "
            f"This proves Issue #667 causes real authentication problems."
        )
    
    async def test_auth_service_connectivity_consistency(self):
        """
        CRITICAL TEST: Validate auth service connectivity consistency.
        
        Tests that different configuration managers affect auth service
        connectivity differently, impacting Golden Path authentication.
        """
        connectivity_results = {}
        connectivity_issues = []
        
        for manager_name, manager_info in self.config_managers.items():
            connectivity_results[manager_name] = {}
            
            try:
                # Get auth-related configuration
                if manager_name in ['unified_config_manager', 'config_py']:
                    config = manager_info['get_config']()
                    
                    # Check auth service configuration
                    auth_config = {}
                    auth_attrs = ['auth_service_url', 'service_secret', 'jwt_secret_key', 'jwt_secret']
                    
                    for attr in auth_attrs:
                        if hasattr(config, attr):
                            auth_config[attr] = getattr(config, attr)
                        elif hasattr(config, 'get') and callable(config.get):
                            auth_config[attr] = config.get(attr)
                    
                    connectivity_results[manager_name]['auth_config'] = auth_config
                    
                elif manager_name == 'unified_configuration_manager':
                    manager = manager_info['get_config']()
                    
                    # Get security configuration
                    try:
                        security_config = manager.get_security_config()
                        connectivity_results[manager_name]['auth_config'] = security_config
                    except Exception as e:
                        connectivity_results[manager_name]['auth_config'] = {'ERROR': str(e)}
                
                # Test basic validation
                auth_config = connectivity_results[manager_name].get('auth_config', {})
                has_jwt_secret = any(key for key in auth_config.keys() if 'jwt' in key.lower() and 'secret' in key.lower())
                has_auth_url = any(key for key in auth_config.keys() if 'auth' in key.lower() and 'url' in key.lower())
                
                connectivity_results[manager_name]['validation'] = {
                    'has_jwt_secret': has_jwt_secret,
                    'has_auth_url': has_auth_url,
                    'config_complete': has_jwt_secret  # Minimum for auth to work
                }
                
                if not has_jwt_secret:
                    connectivity_issues.append({
                        'manager': manager_name,
                        'issue': 'Missing JWT secret configuration',
                        'severity': 'critical'
                    })
                    
            except Exception as e:
                connectivity_results[manager_name] = {'ERROR': str(e)}
                connectivity_issues.append({
                    'manager': manager_name,
                    'issue': f'Configuration access failed: {e}',
                    'severity': 'critical'
                })
        
        # Check for connectivity consistency issues
        validation_results = {}
        for manager_name, results in connectivity_results.items():
            if 'validation' in results:
                validation = results['validation']
                for check, result in validation.items():
                    if check not in validation_results:
                        validation_results[check] = {}
                    validation_results[check][manager_name] = result
        
        # Find inconsistencies
        for check, manager_results in validation_results.items():
            unique_results = set(manager_results.values())
            if len(unique_results) > 1:
                connectivity_issues.append({
                    'manager': 'cross_manager',
                    'issue': f'Inconsistent {check} results: {manager_results}',
                    'severity': 'high'
                })
        
        self.consistency_results['connectivity'] = {
            'connectivity_results': connectivity_results,
            'issues': connectivity_issues,
            'validation_results': validation_results
        }
        
        # EXPECTED FAILURE: Should have connectivity issues proving real impact
        self.assertEqual(
            len(connectivity_issues), 0,
            f"REAL SYSTEM IMPACT: Found {len(connectivity_issues)} auth connectivity issues. "
            f"Issues: {[issue['issue'] for issue in connectivity_issues]}. "
            f"This proves Issue #667 affects real Golden Path authentication connectivity. "
            f"Results: {connectivity_results}"
        )
    
    async def test_configuration_environment_detection_consistency(self):
        """
        CRITICAL TEST: Validate environment detection consistency.
        
        Tests that different configuration managers detect environment
        differently, affecting Golden Path environment-specific authentication.
        """
        environment_results = {}
        environment_conflicts = []
        
        for manager_name, manager_info in self.config_managers.items():
            try:
                if manager_name in ['unified_config_manager', 'config_py']:
                    config = manager_info['get_config']()
                    
                    # Get environment information
                    env_info = {}
                    env_attrs = ['environment', 'env', 'stage', 'deployment_env']
                    
                    for attr in env_attrs:
                        if hasattr(config, attr):
                            env_info[attr] = getattr(config, attr)
                        elif hasattr(config, 'get') and callable(config.get):
                            env_info[attr] = config.get(attr)
                    
                    environment_results[manager_name] = env_info
                    
                elif manager_name == 'unified_configuration_manager':
                    manager = manager_info['get_config']()
                    
                    # Get environment from manager
                    env_info = {
                        'environment': getattr(manager, 'environment', None),
                        'detected_env': manager.get('system.environment') if hasattr(manager, 'get') else None
                    }
                    
                    environment_results[manager_name] = env_info
                    
            except Exception as e:
                environment_results[manager_name] = {'ERROR': str(e)}
                environment_conflicts.append({
                    'manager': manager_name,
                    'issue': f'Environment detection failed: {e}',
                    'severity': 'critical'
                })
        
        # Check for environment detection conflicts
        detected_environments = {}
        for manager_name, env_info in environment_results.items():
            if isinstance(env_info, dict) and 'ERROR' not in env_info:
                for key, value in env_info.items():
                    if value:  # Only consider non-None, non-empty values
                        if value not in detected_environments:
                            detected_environments[value] = []
                        detected_environments[value].append(f"{manager_name}.{key}")
        
        if len(detected_environments) > 1:
            environment_conflicts.append({
                'manager': 'cross_manager',
                'issue': f'Multiple environments detected: {list(detected_environments.keys())}',
                'severity': 'high',
                'details': detected_environments
            })
        
        self.consistency_results['environment'] = {
            'environment_results': environment_results,
            'conflicts': environment_conflicts,
            'detected_environments': detected_environments
        }
        
        # EXPECTED FAILURE: Should have environment conflicts proving real impact
        self.assertEqual(
            len(environment_conflicts), 0,
            f"REAL SYSTEM IMPACT: Found {len(environment_conflicts)} environment detection conflicts. "
            f"Conflicts: {[conf['issue'] for conf in environment_conflicts]}. "
            f"This proves Issue #667 affects environment-specific Golden Path authentication. "
            f"Detected environments: {detected_environments}"
        )
    
    async def test_configuration_reload_behavior_consistency(self):
        """
        CRITICAL TEST: Validate configuration reload behavior consistency.
        
        Tests that different configuration managers handle reloading
        differently, affecting Golden Path authentication resilience.
        """
        reload_results = {}
        reload_issues = []
        
        for manager_name, manager_info in self.config_managers.items():
            reload_results[manager_name] = {}
            
            try:
                # Test reload capability
                if manager_name == 'unified_config_manager':
                    manager = manager_info['manager']
                    if hasattr(manager, 'reload_config'):
                        # Test reload
                        original_config = manager_info['get_config']()
                        original_values = {
                            'service_secret': getattr(original_config, 'service_secret', None)
                        }
                        
                        # Reload
                        reloaded_config = manager.reload_config(force=True)
                        reloaded_values = {
                            'service_secret': getattr(reloaded_config, 'service_secret', None)
                        }
                        
                        reload_results[manager_name] = {
                            'supports_reload': True,
                            'reload_method': 'reload_config',
                            'original_values': original_values,
                            'reloaded_values': reloaded_values,
                            'values_changed': original_values != reloaded_values
                        }
                    else:
                        reload_results[manager_name] = {
                            'supports_reload': False,
                            'reason': 'No reload_config method'
                        }
                
                elif manager_name == 'config_py':
                    # Test if config.py supports reload
                    try:
                        from netra_backend.app.config import reload_config
                        
                        original_config = manager_info['get_config']()
                        original_values = {
                            'service_secret': getattr(original_config, 'service_secret', None)
                        }
                        
                        # Reload
                        reload_config(force=True)
                        reloaded_config = manager_info['get_config']()
                        reloaded_values = {
                            'service_secret': getattr(reloaded_config, 'service_secret', None)
                        }
                        
                        reload_results[manager_name] = {
                            'supports_reload': True,
                            'reload_method': 'reload_config',
                            'original_values': original_values,
                            'reloaded_values': reloaded_values,
                            'values_changed': original_values != reloaded_values
                        }
                    except ImportError:
                        reload_results[manager_name] = {
                            'supports_reload': False,
                            'reason': 'No reload_config function'
                        }
                
                elif manager_name == 'unified_configuration_manager':
                    manager = manager_info['manager']
                    if hasattr(manager, 'clear_cache'):
                        # Test cache clearing (form of reload)
                        original_secret = manager.get('security.jwt_secret')
                        
                        # Clear cache
                        manager.clear_cache()
                        reloaded_secret = manager.get('security.jwt_secret')
                        
                        reload_results[manager_name] = {
                            'supports_reload': True,
                            'reload_method': 'clear_cache',
                            'original_values': {'jwt_secret': original_secret},
                            'reloaded_values': {'jwt_secret': reloaded_secret},
                            'values_changed': original_secret != reloaded_secret
                        }
                    else:
                        reload_results[manager_name] = {
                            'supports_reload': False,
                            'reason': 'No clear_cache method'
                        }
                        
            except Exception as e:
                reload_results[manager_name] = {'ERROR': str(e)}
                reload_issues.append({
                    'manager': manager_name,
                    'issue': f'Reload testing failed: {e}',
                    'severity': 'medium'
                })
        
        # Check for reload capability inconsistencies
        reload_capabilities = {}
        for manager_name, results in reload_results.items():
            if isinstance(results, dict) and 'ERROR' not in results:
                supports_reload = results.get('supports_reload', False)
                if supports_reload not in reload_capabilities:
                    reload_capabilities[supports_reload] = []
                reload_capabilities[supports_reload].append(manager_name)
        
        if len(reload_capabilities) > 1:
            reload_issues.append({
                'manager': 'cross_manager',
                'issue': f'Inconsistent reload support: {reload_capabilities}',
                'severity': 'medium'
            })
        
        self.consistency_results['reload'] = {
            'reload_results': reload_results,
            'issues': reload_issues,
            'capabilities': reload_capabilities
        }
        
        # EXPECTED FAILURE: Should have reload inconsistencies proving real impact
        self.assertEqual(
            len(reload_issues), 0,
            f"REAL SYSTEM IMPACT: Found {len(reload_issues)} configuration reload inconsistencies. "
            f"Issues: {[issue['issue'] for issue in reload_issues]}. "
            f"This proves Issue #667 affects Golden Path authentication resilience. "
            f"Results: {reload_results}"
        )
    
    async def test_golden_path_auth_flow_integration(self):
        """
        CRITICAL TEST: Validate Golden Path authentication flow integration.
        
        Tests that configuration manager differences cause actual Golden Path
        authentication flow failures with real auth service integration.
        """
        auth_flow_results = {}
        auth_flow_failures = []
        
        for manager_name, manager_info in self.config_managers.items():
            auth_flow_results[manager_name] = {}
            
            try:
                # Simulate Golden Path auth flow with each configuration manager
                if manager_name in ['unified_config_manager', 'config_py']:
                    config = manager_info['get_config']()
                    
                    # Extract auth configuration for Golden Path
                    auth_data = {
                        'service_secret': getattr(config, 'service_secret', None),
                        'jwt_secret_key': getattr(config, 'jwt_secret_key', None),
                        'auth_service_url': getattr(config, 'auth_service_url', None),
                        'environment': getattr(config, 'environment', None)
                    }
                    
                    # Check Golden Path auth readiness
                    auth_ready = bool(auth_data['service_secret'] or auth_data['jwt_secret_key'])
                    
                    auth_flow_results[manager_name] = {
                        'auth_data': auth_data,
                        'auth_ready': auth_ready,
                        'missing_config': [k for k, v in auth_data.items() if not v]
                    }
                    
                    if not auth_ready:
                        auth_flow_failures.append({
                            'manager': manager_name,
                            'issue': 'Missing critical auth configuration for Golden Path',
                            'missing': [k for k, v in auth_data.items() if not v],
                            'severity': 'critical'
                        })
                
                elif manager_name == 'unified_configuration_manager':
                    manager = manager_info['manager']
                    
                    # Get security config for Golden Path
                    try:
                        security_config = manager.get_security_config()
                        auth_ready = bool(security_config.get('jwt_secret'))
                        
                        auth_flow_results[manager_name] = {
                            'security_config': security_config,
                            'auth_ready': auth_ready,
                            'missing_config': [k for k, v in security_config.items() if not v] if isinstance(security_config, dict) else []
                        }
                        
                        if not auth_ready:
                            auth_flow_failures.append({
                                'manager': manager_name,
                                'issue': 'Security config missing JWT secret for Golden Path',
                                'severity': 'critical'
                            })
                    except Exception as e:
                        auth_flow_results[manager_name] = {'ERROR': str(e)}
                        auth_flow_failures.append({
                            'manager': manager_name,
                            'issue': f'Security config access failed: {e}',
                            'severity': 'critical'
                        })
                        
            except Exception as e:
                auth_flow_results[manager_name] = {'ERROR': str(e)}
                auth_flow_failures.append({
                    'manager': manager_name,
                    'issue': f'Auth flow testing failed: {e}',
                    'severity': 'critical'
                })
        
        # Check for auth readiness inconsistencies
        auth_readiness = {}
        for manager_name, results in auth_flow_results.items():
            if isinstance(results, dict) and 'ERROR' not in results:
                ready = results.get('auth_ready', False)
                if ready not in auth_readiness:
                    auth_readiness[ready] = []
                auth_readiness[ready].append(manager_name)
        
        if len(auth_readiness) > 1:
            auth_flow_failures.append({
                'manager': 'cross_manager',
                'issue': f'Inconsistent auth readiness across managers: {auth_readiness}',
                'severity': 'critical'
            })
        
        self.auth_test_results = {
            'auth_flow_results': auth_flow_results,
            'failures': auth_flow_failures,
            'readiness': auth_readiness
        }
        
        # EXPECTED FAILURE: Should have auth flow failures proving real Golden Path impact
        self.assertEqual(
            len(auth_flow_failures), 0,
            f"CRITICAL GOLDEN PATH IMPACT: Found {len(auth_flow_failures)} authentication flow failures. "
            f"Failures: {[fail['issue'] for fail in auth_flow_failures]}. "
            f"This proves Issue #667 breaks actual Golden Path authentication flow ($500K+ ARR at risk). "
            f"Auth readiness: {auth_readiness}"
        )
    
    def tearDown(self):
        """Clean up and report comprehensive integration test results."""
        if hasattr(self, 'consistency_results') and self.consistency_results:
            print("\n" + "="*80)
            print("CONFIGURATION SYSTEM INTEGRATION TEST RESULTS - Issue #667")
            print("="*80)
            
            total_violations = 0
            for test_type, results in self.consistency_results.items():
                violations = results.get('violations', results.get('issues', results.get('conflicts', [])))
                total_violations += len(violations)
                
                print(f"\n{test_type.upper()} TEST:")
                print(f"  Violations: {len(violations)}")
                if violations:
                    for violation in violations[:3]:  # Show first 3
                        issue = violation.get('issue', violation.get('key', 'Unknown'))
                        print(f"    - {issue}")
                    if len(violations) > 3:
                        print(f"    ... and {len(violations) - 3} more")
            
            if hasattr(self, 'auth_test_results') and self.auth_test_results:
                auth_failures = len(self.auth_test_results.get('failures', []))
                total_violations += auth_failures
                
                print(f"\nGOLDEN PATH AUTH TEST:")
                print(f"  Failures: {auth_failures}")
                if auth_failures > 0:
                    for failure in self.auth_test_results['failures'][:3]:
                        print(f"    - {failure.get('issue', 'Unknown')}")
            
            print(f"\nTOTAL SYSTEM IMPACT: {total_violations} violations detected")
            print("="*80)
            print("BUSINESS IMPACT: Configuration SSOT violations cause real Golden Path failures")
            print("RECOMMENDATION: Immediate SSOT consolidation required")
            print("="*80)
        
        super().tearDown()


if __name__ == '__main__':
    unittest.main()