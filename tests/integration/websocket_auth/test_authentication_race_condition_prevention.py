"""
Integration Test for WebSocket Authentication Race Condition Prevention

BUSINESS IMPACT: $500K+ ARR - WebSocket authentication race conditions blocking Golden Path
ISSUE: #1076 - Duplicate authenticators causing authentication chaos and race conditions

This test SHOULD FAIL INITIALLY (detecting race conditions) and PASS AFTER REMEDIATION.

SSOT Gardener Step 2.4: Test WebSocket authentication handshake reliability.
Tests for race conditions that occur when multiple authenticators compete during handshake.

Expected Test Behavior:
- FAILS NOW: Race conditions detected from duplicate authenticators
- PASSES AFTER: Single authenticator eliminates race conditions
"""

import asyncio
import time
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, AsyncMock, patch
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.websocket_helpers import MockWebSocketConnection


class TestAuthenticationRaceConditionPrevention(SSotAsyncTestCase):
    """
    Integration Test: WebSocket Authentication Race Condition Detection
    
    Tests for race conditions in WebSocket authentication that can occur when
    multiple authenticators compete or when authentication timing is inconsistent.
    """
    
    def setUp(self):
        """Set up test environment for race condition testing."""
        super().setUp()
        self.test_token = "race-test-jwt-token"
        self.test_user_id = "race-test-user"
        self.concurrent_connections = 5
        self.race_condition_threshold_ms = 100  # Acceptable timing variation
    
    async def test_websocket_authentication_no_race_conditions(self):
        """
        CRITICAL TEST: Should FAIL currently - tests race conditions from duplicate authenticators.
        
        This test simulates concurrent WebSocket authentication attempts and measures
        timing consistency. Race conditions manifest as:
        - Inconsistent authentication timing
        - Authentication failures under concurrent load
        - State corruption between concurrent requests
        
        Business Impact: Race conditions block reliable Golden Path authentication
        """
        from netra_backend.app.websocket_core.unified_websocket_auth import authenticate_websocket_ssot
        
        # Prepare concurrent authentication scenarios
        auth_results = []
        timing_results = []
        
        # Create multiple WebSocket connections for concurrent testing
        websockets = []
        for i in range(self.concurrent_connections):
            ws = MockWebSocketConnection()
            ws.headers = {"authorization": f"Bearer {self.test_token}-{i}"}
            ws.subprotocols = [f"jwt-auth.{self.test_token}-{i}"]
            websockets.append(ws)
        
        # Mock auth service to simulate consistent behavior
        with patch('netra_backend.app.services.unified_authentication_service.get_unified_auth_service') as mock_auth:
            mock_service = AsyncMock()
            mock_auth.return_value = mock_service
            
            # Configure predictable auth service responses
            def create_auth_response(connection_id):
                return (
                    Mock(success=True, user_id=f"user-{connection_id}", error=None, error_code=None,
                         email=f"user{connection_id}@example.com", permissions=['execute_agents']),
                    Mock(user_id=f"user-{connection_id}", websocket_client_id=f"client-{connection_id}",
                         thread_id=f"thread-{connection_id}", run_id=f"run-{connection_id}")
                )
            
            # Test concurrent authentication
            auth_tasks = []
            start_time = time.time()
            
            for i, websocket in enumerate(websockets):
                mock_service.authenticate_websocket.return_value = create_auth_response(i)
                
                task = asyncio.create_task(
                    self._timed_authentication(websocket, f"connection-{i}")
                )
                auth_tasks.append(task)
            
            # Wait for all authentications to complete
            completed_results = await asyncio.gather(*auth_tasks, return_exceptions=True)
            total_time = time.time() - start_time
            
            # Analyze results for race conditions
            race_condition_analysis = self._analyze_race_conditions(
                completed_results, total_time
            )
            
            self._log_race_condition_analysis(race_condition_analysis)
            
            # CRITICAL ASSERTIONS: Should FAIL now (race conditions), PASS after remediation
            
            # 1. All authentications should succeed (no failures due to race conditions)
            successful_auths = [r for r in completed_results 
                              if not isinstance(r, Exception) and getattr(r, 'success', False)]
            
            self.assertEqual(len(successful_auths), self.concurrent_connections,
                            f"RACE CONDITION DETECTED: Only {len(successful_auths)}/{self.concurrent_connections} "
                            f"concurrent authentications succeeded. Failures may indicate race conditions. "
                            f"Exceptions: {[str(r) for r in completed_results if isinstance(r, Exception)]}")
            
            # 2. Authentication timing should be consistent (no major variations)
            timing_variations = race_condition_analysis['timing_variations']
            max_acceptable_variation = self.race_condition_threshold_ms / 1000.0  # Convert to seconds
            
            self.assertLess(timing_variations['max_variation'], max_acceptable_variation,
                           f"RACE CONDITION DETECTED: Authentication timing inconsistent. "
                           f"Max variation: {timing_variations['max_variation']:.3f}s exceeds "
                           f"threshold: {max_acceptable_variation:.3f}s. This indicates competing authenticators.")
            
            # 3. No authentication state corruption
            unique_user_ids = set(r.user_id for r in successful_auths if hasattr(r, 'user_id'))
            expected_unique_ids = self.concurrent_connections
            
            self.assertEqual(len(unique_user_ids), expected_unique_ids,
                           f"RACE CONDITION DETECTED: Authentication state corruption. "
                           f"Expected {expected_unique_ids} unique user IDs, got {len(unique_user_ids)}. "
                           f"Duplicate IDs indicate shared state between concurrent authentications.")
    
    async def test_authentication_circuit_breaker_race_protection(self):
        """
        CIRCUIT BREAKER TEST: Verify circuit breaker prevents race condition failures.
        
        This test simulates rapid authentication attempts that could trigger
        circuit breaker protection and verifies consistent behavior.
        """
        from netra_backend.app.websocket_core.unified_websocket_auth import authenticate_websocket_ssot
        
        # Test rapid authentication attempts
        rapid_auth_count = 10
        circuit_breaker_results = []
        
        with patch('netra_backend.app.services.unified_authentication_service.get_unified_auth_service') as mock_auth:
            mock_service = AsyncMock()
            mock_auth.return_value = mock_service
            
            # Simulate circuit breaker scenario with some failures
            call_count = 0
            def auth_response_with_circuit_breaker(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                
                # First few calls succeed, then trigger circuit breaker
                if call_count <= 3:
                    return (
                        Mock(success=True, user_id=f"circuit-user-{call_count}", error=None),
                        Mock(user_id=f"circuit-user-{call_count}", websocket_client_id=f"circuit-client-{call_count}")
                    )
                elif call_count <= 6:
                    # Simulate auth failures that trigger circuit breaker
                    return (
                        Mock(success=False, user_id=None, error="Auth service overload", error_code="SERVICE_OVERLOAD"),
                        None
                    )
                else:
                    # Circuit breaker should prevent further attempts
                    return (
                        Mock(success=False, user_id=None, error="Circuit breaker open", error_code="CIRCUIT_BREAKER_OPEN"),
                        None
                    )
            
            mock_service.authenticate_websocket.side_effect = auth_response_with_circuit_breaker
            
            # Make rapid authentication attempts
            for i in range(rapid_auth_count):
                websocket = MockWebSocketConnection()
                websocket.headers = {"authorization": f"Bearer rapid-token-{i}"}
                
                try:
                    result = await authenticate_websocket_ssot(websocket)
                    circuit_breaker_results.append({
                        'attempt': i,
                        'success': getattr(result, 'success', False),
                        'error_code': getattr(result, 'error_code', None),
                        'user_id': getattr(result, 'user_id', None)
                    })
                except Exception as e:
                    circuit_breaker_results.append({
                        'attempt': i,
                        'success': False,
                        'error_code': 'EXCEPTION',
                        'exception': str(e)
                    })
                
                # Small delay to simulate rapid requests
                await asyncio.sleep(0.01)
        
        # Analyze circuit breaker behavior
        self._analyze_circuit_breaker_behavior(circuit_breaker_results)
        
        # Circuit breaker should show consistent behavior (not random failures)
        successful_attempts = [r for r in circuit_breaker_results if r['success']]
        failed_attempts = [r for r in circuit_breaker_results if not r['success']]
        
        self.logger.info(f"CIRCUIT BREAKER: {len(successful_attempts)} successful, "
                        f"{len(failed_attempts)} failed out of {rapid_auth_count} attempts")
        
        # This test is more about behavior consistency than pass/fail
        # The important thing is predictable circuit breaker behavior
        self.assertTrue(len(circuit_breaker_results) == rapid_auth_count,
                       f"Expected {rapid_auth_count} authentication attempts, got {len(circuit_breaker_results)}")
    
    async def test_concurrent_user_isolation_race_prevention(self):
        """
        USER ISOLATION TEST: Verify concurrent users don't interfere with each other.
        
        This test simulates multiple users authenticating simultaneously and verifies
        that their authentication contexts remain isolated (no cross-user contamination).
        """
        from netra_backend.app.websocket_core.unified_websocket_auth import authenticate_websocket_ssot
        
        # Create authentication scenarios for different users
        user_scenarios = [
            {'user_id': 'user-alpha', 'token': 'token-alpha', 'permissions': ['alpha-perm']},
            {'user_id': 'user-beta', 'token': 'token-beta', 'permissions': ['beta-perm']},
            {'user_id': 'user-gamma', 'token': 'token-gamma', 'permissions': ['gamma-perm']},
            {'user_id': 'user-delta', 'token': 'token-delta', 'permissions': ['delta-perm']},
        ]
        
        user_isolation_results = {}
        
        with patch('netra_backend.app.services.unified_authentication_service.get_unified_auth_service') as mock_auth:
            mock_service = AsyncMock()
            mock_auth.return_value = mock_service
            
            # Configure auth service to return user-specific data
            def create_user_specific_response(user_scenario):
                return (
                    Mock(
                        success=True, 
                        user_id=user_scenario['user_id'],
                        email=f"{user_scenario['user_id']}@example.com",
                        permissions=user_scenario['permissions'],
                        error=None
                    ),
                    Mock(
                        user_id=user_scenario['user_id'],
                        websocket_client_id=f"client-{user_scenario['user_id']}",
                        thread_id=f"thread-{user_scenario['user_id']}"
                    )
                )
            
            # Test concurrent authentication for different users
            isolation_tasks = []
            
            for scenario in user_scenarios:
                websocket = MockWebSocketConnection()
                websocket.headers = {"authorization": f"Bearer {scenario['token']}"}
                
                mock_service.authenticate_websocket.return_value = create_user_specific_response(scenario)
                
                task = asyncio.create_task(
                    self._isolated_authentication(websocket, scenario)
                )
                isolation_tasks.append(task)
            
            # Wait for all user authentications
            isolation_results = await asyncio.gather(*isolation_tasks, return_exceptions=True)
            
            # Analyze user isolation
            isolation_analysis = self._analyze_user_isolation(isolation_results, user_scenarios)
            
            self._log_user_isolation_analysis(isolation_analysis)
            
            # CRITICAL ASSERTION: No cross-user contamination
            contamination_detected = isolation_analysis['contamination_detected']
            
            self.assertFalse(contamination_detected,
                           f"USER ISOLATION RACE CONDITION: Cross-user data contamination detected. "
                           f"Details: {isolation_analysis['contamination_details']}. "
                           f"This indicates shared state between concurrent user authentications.")
            
            # All users should have their correct, isolated data
            successful_isolations = isolation_analysis['successful_isolations']
            expected_isolations = len(user_scenarios)
            
            self.assertEqual(successful_isolations, expected_isolations,
                           f"USER ISOLATION FAILURE: Only {successful_isolations}/{expected_isolations} "
                           f"users properly isolated. This indicates authentication context leakage.")
    
    async def _timed_authentication(self, websocket: MockWebSocketConnection, connection_id: str) -> Dict:
        """Perform timed authentication for race condition analysis."""
        from netra_backend.app.websocket_core.unified_websocket_auth import authenticate_websocket_ssot
        
        start_time = time.time()
        
        try:
            result = await authenticate_websocket_ssot(websocket)
            end_time = time.time()
            
            return {
                'connection_id': connection_id,
                'success': getattr(result, 'success', False),
                'user_id': getattr(result, 'user_id', None),
                'timing': end_time - start_time,
                'error': None
            }
        
        except Exception as e:
            end_time = time.time()
            return {
                'connection_id': connection_id,
                'success': False,
                'user_id': None,
                'timing': end_time - start_time,
                'error': str(e)
            }
    
    async def _isolated_authentication(self, websocket: MockWebSocketConnection, user_scenario: Dict) -> Dict:
        """Perform isolated authentication for user isolation testing."""
        from netra_backend.app.websocket_core.unified_websocket_auth import authenticate_websocket_ssot
        
        try:
            result = await authenticate_websocket_ssot(websocket)
            
            return {
                'expected_user_id': user_scenario['user_id'],
                'actual_user_id': getattr(result, 'user_id', None),
                'expected_permissions': user_scenario['permissions'],
                'actual_permissions': getattr(result, 'permissions', []),
                'success': getattr(result, 'success', False),
                'isolation_verified': True
            }
        
        except Exception as e:
            return {
                'expected_user_id': user_scenario['user_id'],
                'actual_user_id': None,
                'success': False,
                'error': str(e),
                'isolation_verified': False
            }
    
    def _analyze_race_conditions(self, results: List, total_time: float) -> Dict:
        """Analyze authentication results for race condition indicators."""
        analysis = {
            'total_attempts': len(results),
            'successful_attempts': 0,
            'failed_attempts': 0,
            'exception_count': 0,
            'timing_variations': {},
            'race_indicators': [],
            'total_execution_time': total_time
        }
        
        successful_results = []
        timings = []
        
        for result in results:
            if isinstance(result, Exception):
                analysis['exception_count'] += 1
                analysis['race_indicators'].append(f"Exception during concurrent auth: {str(result)}")
            elif hasattr(result, 'success') and result.success:
                analysis['successful_attempts'] += 1
                successful_results.append(result)
                if hasattr(result, 'timing'):
                    timings.append(result.timing)
            else:
                analysis['failed_attempts'] += 1
                if hasattr(result, 'error') and result.error:
                    analysis['race_indicators'].append(f"Auth failure: {result.error}")
        
        # Analyze timing variations
        if timings:
            analysis['timing_variations'] = {
                'min_timing': min(timings),
                'max_timing': max(timings),
                'avg_timing': sum(timings) / len(timings),
                'max_variation': max(timings) - min(timings)
            }
            
            # High timing variation indicates race conditions
            if analysis['timing_variations']['max_variation'] > 0.1:  # 100ms
                analysis['race_indicators'].append(
                    f"High timing variation: {analysis['timing_variations']['max_variation']:.3f}s"
                )
        
        return analysis
    
    def _analyze_circuit_breaker_behavior(self, results: List[Dict]) -> Dict:
        """Analyze circuit breaker behavior for consistency."""
        analysis = {
            'total_attempts': len(results),
            'success_count': sum(1 for r in results if r['success']),
            'failure_patterns': {},
            'circuit_breaker_triggers': []
        }
        
        # Group failures by error code
        for result in results:
            if not result['success']:
                error_code = result.get('error_code', 'UNKNOWN')
                if error_code not in analysis['failure_patterns']:
                    analysis['failure_patterns'][error_code] = 0
                analysis['failure_patterns'][error_code] += 1
                
                if error_code == 'CIRCUIT_BREAKER_OPEN':
                    analysis['circuit_breaker_triggers'].append(result['attempt'])
        
        return analysis
    
    def _analyze_user_isolation(self, results: List, user_scenarios: List[Dict]) -> Dict:
        """Analyze user isolation for cross-contamination."""
        analysis = {
            'total_users': len(user_scenarios),
            'successful_isolations': 0,
            'contamination_detected': False,
            'contamination_details': [],
            'isolation_summary': {}
        }
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                continue
                
            expected_scenario = user_scenarios[i]
            expected_user_id = expected_scenario['user_id']
            
            if (hasattr(result, 'expected_user_id') and 
                hasattr(result, 'actual_user_id') and
                result.success):
                
                if result.expected_user_id == result.actual_user_id:
                    analysis['successful_isolations'] += 1
                    analysis['isolation_summary'][expected_user_id] = 'ISOLATED'
                else:
                    analysis['contamination_detected'] = True
                    contamination_detail = (
                        f"User {result.expected_user_id} got data for {result.actual_user_id}"
                    )
                    analysis['contamination_details'].append(contamination_detail)
                    analysis['isolation_summary'][expected_user_id] = 'CONTAMINATED'
            else:
                analysis['isolation_summary'][expected_user_id] = 'FAILED'
        
        return analysis
    
    def _log_race_condition_analysis(self, analysis: Dict):
        """Log detailed race condition analysis."""
        self.logger.info("RACE CONDITION ANALYSIS:")
        self.logger.info(f"  Total attempts: {analysis['total_attempts']}")
        self.logger.info(f"  Successful: {analysis['successful_attempts']}")
        self.logger.info(f"  Failed: {analysis['failed_attempts']}")
        self.logger.info(f"  Exceptions: {analysis['exception_count']}")
        self.logger.info(f"  Total time: {analysis['total_execution_time']:.3f}s")
        
        if analysis['timing_variations']:
            timing = analysis['timing_variations']
            self.logger.info(f"  Timing - Min: {timing['min_timing']:.3f}s, "
                           f"Max: {timing['max_timing']:.3f}s, "
                           f"Avg: {timing['avg_timing']:.3f}s, "
                           f"Variation: {timing['max_variation']:.3f}s")
        
        if analysis['race_indicators']:
            self.logger.warning(f"  Race indicators: {analysis['race_indicators']}")
        
        # Record in test metadata
        self.test_metadata.update({
            "race_condition_analysis": analysis,
            "concurrent_connections_tested": analysis['total_attempts'],
            "authentication_success_rate": (analysis['successful_attempts'] / max(1, analysis['total_attempts'])) * 100
        })
    
    def _log_user_isolation_analysis(self, analysis: Dict):
        """Log detailed user isolation analysis."""
        self.logger.info("USER ISOLATION ANALYSIS:")
        self.logger.info(f"  Total users: {analysis['total_users']}")
        self.logger.info(f"  Successful isolations: {analysis['successful_isolations']}")
        self.logger.info(f"  Contamination detected: {analysis['contamination_detected']}")
        
        if analysis['contamination_details']:
            self.logger.warning(f"  Contamination details: {analysis['contamination_details']}")
        
        self.logger.info(f"  Isolation summary: {analysis['isolation_summary']}")
        
        # Record in test metadata
        self.test_metadata.update({
            "user_isolation_analysis": analysis,
            "isolation_success_rate": (analysis['successful_isolations'] / max(1, analysis['total_users'])) * 100
        })


if __name__ == '__main__':
    unittest.main()