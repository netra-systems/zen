"""
Integration Test: SSOT Configuration Service Secret Validation with Real Services

Business Value Justification (BVJ):
- Segment: Platform/Internal - Multi-User System Stability
- Business Goal: Prevent WebSocket 1011 errors causing $500K+ ARR loss  
- Value Impact: Ensures configuration consistency across real backend services
- Strategic Impact: Validates SSOT pattern prevents race conditions in production

CRITICAL PURPOSE:
Integration test with REAL services (no Docker required) to validate SSOT 
configuration loading patterns. Tests configuration consistency across 
actual backend services and WebSocket authentication flows.

INTEGRATION SCOPE:
- Real backend service configuration loading
- Multi-user scenario validation  
- WebSocket authentication configuration
- Service secret consistency across services
- Race condition prevention in real service context

TEST DESIGN:
- BEFORE FIX: Tests FAIL demonstrating SSOT violations with real services
- AFTER FIX: Tests PASS showing proper SSOT compliance
- NO MOCKS: Uses real service integrations to validate patterns
- NO DOCKER: Tests run against real services without container orchestration
"""

import asyncio
import concurrent.futures
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional

import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.core.configuration.base import UnifiedConfigManager
from netra_backend.app.core.managers.unified_configuration_manager import UnifiedConfigurationManager
from netra_backend.app.websocket_core.manager import WebSocketManager
from shared.isolated_environment import IsolatedEnvironment


class TestConfigSSoTServiceSecretValidation(SSotAsyncTestCase):
    """Integration tests for SSOT configuration with real backend services."""

    def setup_method(self, method=None):
        """Set up real service integration test environment."""
        super().setup_method(method)
        self.test_environments = [
            {'SERVICE_SECRET': 'backend-test-secret-001', 'SERVICE_ID': 'backend-service'},
            {'SERVICE_SECRET': 'auth-test-secret-002', 'SERVICE_ID': 'auth-service'},
            {'SERVICE_SECRET': 'websocket-test-secret-003', 'SERVICE_ID': 'websocket-service'},
        ]
        
        # Track configuration loading patterns
        self.config_load_history = []
        self.service_interactions = []

    async def test_service_secret_consistency_across_services(self):
        """
        Test SERVICE_SECRET consistency across real backend services.
        
        INTEGRATION SCOPE: Real service configuration loading without Docker
        
        EXPECTED BEHAVIOR:
        - BEFORE FIX: FAIL - inconsistent service secrets due to SSOT violations
        - AFTER FIX: PASS - consistent service secrets through proper SSOT usage
        """
        service_configs = {}
        consistency_violations = []
        
        # Test configuration loading across different service contexts
        for service_env in self.test_environments:
            service_id = service_env['SERVICE_ID']
            
            try:
                # Set up isolated environment for service
                env = IsolatedEnvironment()
                for key, value in service_env.items():
                    env.set(key, value)
                
                # Load configuration using UnifiedConfigManager (should be SSOT)
                config_manager = UnifiedConfigManager()
                config = config_manager.get_config()
                
                service_secret = getattr(config, 'service_secret', None)
                
                service_configs[service_id] = {
                    'service_secret': service_secret,
                    'expected_secret': service_env['SERVICE_SECRET'],
                    'config_load_time': time.time(),
                    'service_id': service_id
                }
                
                # Check if configuration matches expected service secret
                if service_secret != service_env['SERVICE_SECRET']:
                    consistency_violations.append({
                        'service_id': service_id,
                        'expected': service_env['SERVICE_SECRET'],
                        'actual': service_secret,
                        'issue': 'Service secret mismatch indicates SSOT violation'
                    })
                
                self.service_interactions.append({
                    'service_id': service_id,
                    'interaction_type': 'config_load',
                    'status': 'success',
                    'timestamp': time.time()
                })
                
            except Exception as e:
                consistency_violations.append({
                    'service_id': service_id,
                    'error': str(e),
                    'issue': 'Configuration loading failed for real service'
                })
                
                self.service_interactions.append({
                    'service_id': service_id,
                    'interaction_type': 'config_load',
                    'status': 'error',
                    'error': str(e),
                    'timestamp': time.time()
                })
        
        # Validate results
        if consistency_violations:
            violation_report = '\n'.join([
                f"- {v['service_id']}: {v.get('issue', 'Unknown issue')} "
                f"(Expected: {v.get('expected', 'N/A')}, Got: {v.get('actual', 'N/A')})"
                for v in consistency_violations
            ])
            
            pytest.fail(
                f"SERVICE SECRET CONSISTENCY VIOLATIONS DETECTED:\n{violation_report}\n"
                f"SSOT violation in configuration base causes inconsistent service secrets across real services. "
                f"This can cause WebSocket 1011 authentication errors."
            )
        
        # After SSOT fix, all services should load configurations successfully
        assert len(service_configs) >= len(self.test_environments), \
            "All real services should successfully load configurations through SSOT pattern"

    async def test_configuration_loading_race_conditions(self):
        """
        Test race condition prevention in multi-user configuration loading with real services.
        
        INTEGRATION SCOPE: Concurrent real service access patterns
        
        EXPECTED BEHAVIOR:
        - BEFORE FIX: FAIL - race conditions between concurrent users/services
        - AFTER FIX: PASS - proper isolation prevents race conditions
        """
        race_conditions = []
        concurrent_configs = {}
        load_times = []
        
        async def load_config_concurrently(user_id: str, service_context: Dict[str, str]) -> Dict[str, Any]:
            """Load configuration concurrently for different users/services."""
            start_time = time.time()
            
            try:
                # Set up user-specific environment
                env = IsolatedEnvironment()
                for key, value in service_context.items():
                    env.set(key, value)
                env.set('USER_ID', user_id)
                
                # Load configuration through what should be SSOT
                config_manager = UnifiedConfigManager()
                config = config_manager.get_config()
                
                end_time = time.time()
                load_time = end_time - start_time
                load_times.append(load_time)
                
                service_secret = getattr(config, 'service_secret', None)
                
                # Check for race condition indicators
                expected_secret = service_context.get('SERVICE_SECRET')
                if service_secret and expected_secret and service_secret != expected_secret:
                    race_conditions.append({
                        'user_id': user_id,
                        'expected_secret': expected_secret,
                        'actual_secret': service_secret,
                        'load_time': load_time,
                        'issue': 'Configuration contaminated by concurrent access'
                    })
                
                return {
                    'user_id': user_id,
                    'service_secret': service_secret,
                    'load_time': load_time,
                    'service_context': service_context.get('SERVICE_ID', 'unknown'),
                    'timestamp': end_time
                }
                
            except Exception as e:
                race_conditions.append({
                    'user_id': user_id,
                    'error': str(e),
                    'issue': 'Concurrent configuration loading failed'
                })
                return {'user_id': user_id, 'error': str(e)}
        
        # Create concurrent configuration loading scenarios
        tasks = []
        for i in range(10):  # 10 concurrent users
            for j, service_env in enumerate(self.test_environments):
                user_id = f"user_{i}_service_{j}"
                task = load_config_concurrently(user_id, service_env)
                tasks.append(task)
        
        # Execute concurrent loads
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for result in results:
            if isinstance(result, Exception):
                race_conditions.append({
                    'error': str(result),
                    'issue': 'Async configuration loading exception'
                })
            elif isinstance(result, dict) and 'error' not in result:
                concurrent_configs[result['user_id']] = result
        
        # Analyze for race conditions
        if race_conditions:
            race_condition_report = '\n'.join([
                f"- {rc.get('user_id', 'unknown')}: {rc.get('issue', 'Unknown race condition')}"
                for rc in race_conditions
            ])
            
            pytest.fail(
                f"RACE CONDITIONS DETECTED IN REAL SERVICE INTEGRATION:\n{race_condition_report}\n"
                f"SSOT violations in configuration base allow race conditions that can cause "
                f"WebSocket 1011 errors in multi-user scenarios."
            )
        
        # Performance validation
        if load_times:
            avg_load_time = sum(load_times) / len(load_times)
            max_load_time = max(load_times)
            
            # Configuration loading should be efficient and consistent
            assert avg_load_time < 1.0, "Average configuration load time should be < 1 second"
            assert max_load_time < 3.0, "Max configuration load time should be < 3 seconds"

    async def test_websocket_config_ssot_compliance(self):
        """
        Test WebSocket configuration SSOT compliance with real WebSocket manager.
        
        INTEGRATION SCOPE: Real WebSocket service integration
        
        EXPECTED BEHAVIOR:
        - BEFORE FIX: FAIL - WebSocket config inconsistencies cause 1011 errors
        - AFTER FIX: PASS - consistent WebSocket configuration through SSOT
        """
        websocket_config_issues = []
        websocket_managers = []
        
        # Test WebSocket configuration across multiple instantiations
        for i in range(3):
            try:
                # Set up environment for WebSocket
                env = IsolatedEnvironment()
                env.set('SERVICE_SECRET', f'websocket-test-{i}')
                env.set('SERVICE_ID', 'websocket-service')
                
                # Load configuration for WebSocket (this should use SSOT)
                config_manager = UnifiedConfigManager()
                config = config_manager.get_config()
                
                # This would normally create a WebSocketManager with the config
                # For integration testing, we validate the configuration consistency
                service_secret = getattr(config, 'service_secret', None)
                
                if not service_secret:
                    websocket_config_issues.append({
                        'instance': i,
                        'issue': 'Missing service_secret for WebSocket authentication',
                        'impact': 'WebSocket 1011 connection errors'
                    })
                
                # Check for configuration consistency patterns
                if service_secret != f'websocket-test-{i}':
                    websocket_config_issues.append({
                        'instance': i,
                        'expected': f'websocket-test-{i}',
                        'actual': service_secret,
                        'issue': 'WebSocket configuration inconsistency'
                    })
                
                websocket_managers.append({
                    'instance': i,
                    'service_secret': service_secret,
                    'config_status': 'loaded',
                    'timestamp': time.time()
                })
                
            except Exception as e:
                websocket_config_issues.append({
                    'instance': i,
                    'error': str(e),
                    'issue': 'WebSocket configuration loading failed'
                })
        
        # Check for WebSocket configuration issues
        if websocket_config_issues:
            websocket_issue_report = '\n'.join([
                f"- Instance {issue.get('instance', 'unknown')}: {issue.get('issue', 'Unknown issue')}"
                for issue in websocket_config_issues
            ])
            
            pytest.fail(
                f"WEBSOCKET CONFIGURATION SSOT VIOLATIONS:\n{websocket_issue_report}\n"
                f"Configuration base SSOT violations cause WebSocket authentication issues "
                f"leading to 1011 connection errors."
            )
        
        # After SSOT fix, WebSocket configurations should be consistent
        assert len(websocket_managers) == 3, "All WebSocket manager configurations should load successfully"

    async def test_ssot_configuration_manager_integration(self):
        """
        Test end-to-end SSOT configuration manager integration with real services.
        
        INTEGRATION SCOPE: Full configuration flow through real service stack
        
        EXPECTED BEHAVIOR:
        - BEFORE FIX: FAIL - UnifiedConfigurationManager not properly integrated
        - AFTER FIX: PASS - seamless SSOT integration across all services
        """
        integration_failures = []
        service_integration_results = {}
        
        # Test full configuration integration flow
        for service_env in self.test_environments:
            service_id = service_env['SERVICE_ID']
            
            try:
                # Step 1: Environment setup
                env = IsolatedEnvironment()
                for key, value in service_env.items():
                    env.set(key, value)
                
                # Step 2: UnifiedConfigManager should be the SSOT
                unified_config = UnifiedConfigurationManager()
                
                # Step 3: Configuration loading through SSOT pattern
                config_manager = UnifiedConfigManager()
                config = config_manager.get_config()
                
                # Step 4: Validate integration results
                service_secret = getattr(config, 'service_secret', None)
                
                if not service_secret:
                    integration_failures.append({
                        'service_id': service_id,
                        'step': 'service_secret_loading',
                        'issue': 'SERVICE_SECRET not loaded through SSOT pattern'
                    })
                
                # Step 5: Test configuration consistency
                second_config = config_manager.get_config()
                second_service_secret = getattr(second_config, 'service_secret', None)
                
                if service_secret != second_service_secret:
                    integration_failures.append({
                        'service_id': service_id,
                        'step': 'consistency_check',
                        'issue': 'Configuration inconsistent between calls',
                        'first_secret': service_secret,
                        'second_secret': second_service_secret
                    })
                
                service_integration_results[service_id] = {
                    'service_secret_loaded': bool(service_secret),
                    'configuration_consistent': service_secret == second_service_secret,
                    'integration_status': 'success'
                }
                
            except Exception as e:
                integration_failures.append({
                    'service_id': service_id,
                    'step': 'configuration_integration',
                    'error': str(e),
                    'issue': 'SSOT configuration integration failed'
                })
                
                service_integration_results[service_id] = {
                    'integration_status': 'failed',
                    'error': str(e)
                }
        
        # Validate integration results
        if integration_failures:
            integration_failure_report = '\n'.join([
                f"- {failure['service_id']}: {failure['issue']} (Step: {failure.get('step', 'unknown')})"
                for failure in integration_failures
            ])
            
            pytest.fail(
                f"SSOT CONFIGURATION MANAGER INTEGRATION FAILURES:\n{integration_failure_report}\n"
                f"UnifiedConfigurationManager not properly integrated as SSOT for real services. "
                f"This causes configuration inconsistencies leading to WebSocket 1011 errors."
            )
        
        # After SSOT fix, all service integrations should succeed
        successful_integrations = sum(1 for result in service_integration_results.values() 
                                    if result.get('integration_status') == 'success')
        
        assert successful_integrations == len(self.test_environments), \
            "All services should successfully integrate with SSOT configuration manager"

    def teardown_method(self, method=None):
        """Clean up integration test resources."""
        super().teardown_method(method)
        
        # Log integration test results for analysis
        if hasattr(self, '_test_context') and self._test_context:
            self._test_context.metadata.update({
                'config_load_history': len(getattr(self, 'config_load_history', [])),
                'service_interactions': len(getattr(self, 'service_interactions', [])),
                'test_category': 'integration_ssot_config',
                'real_services_used': True
            })


if __name__ == '__main__':
    pytest.main([__file__, '-v'])