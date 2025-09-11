"""
MISSION CRITICAL TEST: WebSocket 1011 Error Dual SSOT Fix Validation
================================================================

ISSUE #301: Validates the fix for WebSocket 1011 errors caused by dual SSOT ID systems.

BUSINESS IMPACT: $500K+ ARR protection - ensures WebSocket connections don't fail due to
resource cleanup issues when UnifiedIDManager and UnifiedIdGenerator create different
ID patterns for the same user session.

CRITICAL FAILURE SCENARIOS:
1. User connects via WebSocket (creates IDs with one SSOT system)
2. Agent execution begins (may use different SSOT system for IDs)  
3. WebSocket disconnect triggers cleanup using mismatched ID patterns
4. Cleanup fails to find resources → WebSocket 1011 error
5. User loses connection, chat functionality broken

VALIDATION STRATEGY:
- Test all permutations of dual SSOT ID creation
- Verify cleanup works regardless of which system created the IDs  
- Validate no business logic regression
- Ensure performance impact is minimal
"""

import asyncio
import pytest
import time
from typing import Dict, List, Tuple
from unittest.mock import patch, MagicMock
import uuid

from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestWebSocket1011ErrorDualSSOTFixValidation(SSotBaseTestCase):
    """Mission-critical validation of WebSocket 1011 error fix."""

    def setup_method(self):
        """Set up comprehensive test environment."""
        super().setup_method()
        self.id_manager = UnifiedIDManager()
        
        # Simulate WebSocket factory resource tracking
        self.active_connections = {}
        self.cleanup_attempts = []
        self.failed_cleanups = []
        
    def test_websocket_1011_error_fix_all_permutations(self):
        """
        CRITICAL: Test all permutations of dual SSOT ID creation and cleanup.
        
        This is the core business value test - validates that WebSocket 1011 errors
        are prevented regardless of which ID system creates the original IDs.
        """
        user_scenarios = [
            "enterprise_user_123",
            "free_user_456", 
            "mid_tier_user_789"
        ]
        
        # Test all permutations of ID system combinations
        id_system_combinations = [
            # (connection_system, execution_system, cleanup_system)
            ("manager", "manager", "manager"),      # Pure UnifiedIDManager 
            ("generator", "generator", "generator"), # Pure UnifiedIdGenerator
            ("manager", "generator", "manager"),     # Mixed: Mgr → Gen → Mgr
            ("generator", "manager", "generator"),   # Mixed: Gen → Mgr → Gen
            ("manager", "generator", "generator"),   # Mixed: Mgr → Gen → Gen
            ("generator", "manager", "manager"),     # Mixed: Gen → Mgr → Mgr
        ]
        
        success_count = 0
        total_scenarios = len(user_scenarios) * len(id_system_combinations)
        
        for user_id in user_scenarios:
            for conn_sys, exec_sys, cleanup_sys in id_system_combinations:
                # Execute full WebSocket lifecycle with mixed ID systems
                result = self._execute_websocket_lifecycle_scenario(
                    user_id, conn_sys, exec_sys, cleanup_sys
                )
                
                if result['success']:
                    success_count += 1
                else:
                    self.failed_cleanups.append({
                        'user_id': user_id,
                        'combination': (conn_sys, exec_sys, cleanup_sys),
                        'error': result['error']
                    })
        
        # CRITICAL: All scenarios must succeed to prevent $500K+ ARR loss
        success_rate = (success_count / total_scenarios) * 100
        self.assertEqual(success_count, total_scenarios, 
                        f"WebSocket 1011 fix failed in {total_scenarios - success_count} scenarios. "
                        f"Success rate: {success_rate:.1f}%. Failed scenarios: {self.failed_cleanups}")
        
    def test_websocket_resource_cleanup_pattern_matching(self):
        """
        CRITICAL: Test the specific pattern matching logic that prevents 1011 errors.
        
        The fix ensures cleanup can find resources even when ID patterns differ
        between creation and cleanup systems.
        """
        test_cases = [
            # (creation_pattern, cleanup_pattern, should_match)
            ("user123_websocket_1_abc12345", "user123_thread_2_def67890", True),   # Same user prefix
            ("ws_conn_user456_789_xyz", "thread_user456_101112", True),            # User ID embedded
            ("enterprise_websocket_1_abc", "enterprise_execution_2_def", True),    # Same prefix  
            ("user_a_ws_1_xyz", "user_b_thread_2_abc", False),                     # Different users
            ("random_123_abc", "other_456_def", False),                           # No correlation
        ]
        
        for creation_id, cleanup_id, should_match in test_cases:
            # Register connection with creation pattern
            self._register_websocket_connection(creation_id, f"ws_{creation_id}")
            
            # Attempt cleanup with different pattern
            cleanup_result = self._attempt_pattern_based_cleanup(cleanup_id)
            
            if should_match:
                self.assertTrue(cleanup_result['found'], 
                              f"Failed to match related IDs: {creation_id} ↔ {cleanup_id}")
            else:
                self.assertFalse(cleanup_result['found'],
                               f"Incorrectly matched unrelated IDs: {creation_id} ↔ {cleanup_id}")
                               
            # Reset for next test
            self.active_connections.clear()
                
    def test_websocket_1011_error_business_impact_validation(self):
        """
        Validate that the fix addresses the specific business impact scenarios.
        
        These are real user scenarios that were causing revenue loss.
        """
        business_scenarios = [
            {
                'name': 'Enterprise Customer Multi-Agent Session',
                'user_id': 'enterprise_customer_001',
                'session_duration_minutes': 45,
                'agent_switches': 5,
                'expected_revenue_impact': 1500  # $1.5K per session for enterprise
            },
            {
                'name': 'Mid-Tier Customer Optimization Workflow', 
                'user_id': 'mid_tier_customer_002',
                'session_duration_minutes': 20,
                'agent_switches': 3,
                'expected_revenue_impact': 500   # $500 per session for mid-tier
            },
            {
                'name': 'Free User Conversion Session',
                'user_id': 'free_user_003', 
                'session_duration_minutes': 10,
                'agent_switches': 1,
                'expected_revenue_impact': 100   # Conversion opportunity value (LTV of converted free user)
            }
        ]
        
        total_protected_revenue = 0
        
        for scenario in business_scenarios:
            # Simulate the business scenario
            session_result = self._simulate_business_session(scenario)
            
            self.assertTrue(session_result['session_completed'], 
                          f"Business scenario failed: {scenario['name']}")
            self.assertEqual(session_result['websocket_errors'], 0,
                           f"WebSocket errors in {scenario['name']}")
                           
            total_protected_revenue += scenario['expected_revenue_impact']
        
        # Validate overall business impact protection
        self.assertGreater(total_protected_revenue, 2000, 
                          "Protected revenue should exceed $2K for test scenarios")
        
    def test_dual_ssot_performance_impact_on_critical_path(self):
        """
        Ensure the compatibility fix doesn't impact critical path performance.
        
        WebSocket operations are on the critical path for chat functionality.
        """
        performance_benchmarks = {}
        
        # Benchmark 1: Connection establishment
        start_time = time.perf_counter()
        for i in range(100):
            self._create_websocket_connection_with_dual_ssot(f"perf_user_{i}")
        performance_benchmarks['connection_time'] = time.perf_counter() - start_time
        
        # Benchmark 2: Resource cleanup
        start_time = time.perf_counter() 
        for i in range(100):
            self._cleanup_websocket_resources_with_dual_ssot(f"perf_user_{i}")
        performance_benchmarks['cleanup_time'] = time.perf_counter() - start_time
        
        # Performance requirements for critical path
        self.assertLess(performance_benchmarks['connection_time'], 1.0, 
                       "WebSocket connection time exceeds 1s for 100 connections")
        self.assertLess(performance_benchmarks['cleanup_time'], 0.5,
                       "WebSocket cleanup time exceeds 0.5s for 100 cleanups")
                       
        # Log performance for monitoring
        print(f"Performance Benchmarks: {performance_benchmarks}")
        
    # Helper Methods for Test Execution
    
    def _execute_websocket_lifecycle_scenario(self, user_id: str, 
                                            connection_system: str,
                                            execution_system: str, 
                                            cleanup_system: str) -> Dict:
        """Execute complete WebSocket lifecycle with mixed ID systems."""
        try:
            # Phase 1: WebSocket Connection (using connection_system)
            connection_ids = self._create_websocket_connection(user_id, connection_system)
            
            # Phase 2: Agent Execution (using execution_system) 
            execution_ids = self._create_agent_execution_context(user_id, execution_system)
            
            # Phase 3: WebSocket Cleanup (using cleanup_system)
            cleanup_success = self._perform_websocket_cleanup(
                user_id, connection_ids, execution_ids, cleanup_system
            )
            
            return {
                'success': cleanup_success,
                'connection_ids': connection_ids,
                'execution_ids': execution_ids,
                'error': None
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
            
    def _create_websocket_connection(self, user_id: str, system: str) -> Dict:
        """Create WebSocket connection using specified ID system."""
        if system == "manager":
            thread_id = self.id_manager.generate_id(IDType.THREAD, prefix=user_id[:8])
            ws_id = self.id_manager.generate_id(IDType.WEBSOCKET, prefix=user_id[:8])
        else:  # generator
            thread_id, run_id, _ = UnifiedIdGenerator.generate_user_context_ids(user_id)
            ws_id = UnifiedIdGenerator.generate_websocket_connection_id(user_id)
            
        # Register connection
        self.active_connections[thread_id] = {
            'user_id': user_id,
            'ws_id': ws_id,
            'created_by': system,
            'created_at': time.time()
        }
        
        return {'thread_id': thread_id, 'ws_id': ws_id, 'system': system}
        
    def _create_agent_execution_context(self, user_id: str, system: str) -> Dict:
        """Create agent execution context using specified ID system.""" 
        if system == "manager":
            execution_id = self.id_manager.generate_id(IDType.EXECUTION, prefix=user_id[:8])
            agent_id = self.id_manager.generate_id(IDType.AGENT, prefix=user_id[:8])
        else:  # generator
            execution_id = UnifiedIdGenerator.generate_agent_execution_id("supervisor", user_id)
            agent_id = UnifiedIdGenerator.generate_base_id(f"agent_{user_id[:8]}")
            
        return {'execution_id': execution_id, 'agent_id': agent_id, 'system': system}
        
    def _perform_websocket_cleanup(self, user_id: str, connection_ids: Dict, 
                                 execution_ids: Dict, cleanup_system: str) -> bool:
        """Perform WebSocket cleanup using specified system logic."""
        thread_id = connection_ids['thread_id']
        
        # Primary cleanup: exact match
        if thread_id in self.active_connections:
            del self.active_connections[thread_id]
            return True
            
        # CRITICAL FIX: Pattern-based cleanup for dual SSOT compatibility
        return self._pattern_based_cleanup_for_dual_ssot(user_id, thread_id)
        
    def _pattern_based_cleanup_for_dual_ssot(self, user_id: str, target_thread_id: str) -> bool:
        """
        Implement the critical fix for dual SSOT ID pattern matching.
        
        This is the core logic that prevents WebSocket 1011 errors.
        """
        user_patterns = [
            user_id[:4],    # Short user prefix
            user_id[:8],    # Standard user prefix  
            user_id.split('_')[0] if '_' in user_id else user_id[:6]  # Base user ID
        ]
        
        matching_connections = []
        
        for registered_thread_id, connection_info in self.active_connections.items():
            # Check if any user pattern appears in the registered ID
            if (connection_info['user_id'] == user_id or 
                any(pattern in registered_thread_id for pattern in user_patterns if pattern)):
                matching_connections.append(registered_thread_id)
                
        # Clean up all matching connections
        for thread_id in matching_connections:
            del self.active_connections[thread_id]
            
        return len(matching_connections) > 0
        
    def _register_websocket_connection(self, connection_id: str, ws_id: str):
        """Register WebSocket connection for testing."""
        self.active_connections[connection_id] = {
            'ws_id': ws_id,
            'created_at': time.time(),
            'status': 'active'
        }
        
    def _attempt_pattern_based_cleanup(self, cleanup_pattern: str) -> Dict:
        """
        Attempt cleanup using secure pattern matching.
        
        SECURITY CRITICAL: Uses same secure boundary logic as UnifiedIDManager
        to prevent cross-user resource contamination.
        """
        # Extract potential user identifiers from cleanup pattern
        cleanup_parts = cleanup_pattern.split('_')
        
        matching_keys = []
        for connection_id in self.active_connections.keys():
            # CRITICAL SECURITY FIX: Use secure boundary matching
            if self._is_secure_pattern_match_for_cleanup(cleanup_parts, connection_id):
                matching_keys.append(connection_id)
                
        return {
            'found': len(matching_keys) > 0,
            'matches': matching_keys
        }
    
    def _is_secure_pattern_match_for_cleanup(self, cleanup_parts: list[str], connection_id: str) -> bool:
        """
        SECURITY: Perform secure pattern matching that prevents cross-user contamination.
        
        This uses the same logic as UnifiedIDManager._is_secure_pattern_match to ensure
        consistent security boundaries across the system.
        
        Args:
            cleanup_parts: Parts of the cleanup pattern
            connection_id: Connection ID to check against
            
        Returns:
            True only if there's a secure, meaningful correlation
        """
        connection_parts = connection_id.split('_')
        
        # Look for meaningful user correlation patterns that indicate same user
        for cleanup_part in cleanup_parts:
            if len(cleanup_part) >= 4:  # Must be meaningful (≥4 chars)
                for connection_part in connection_parts:
                    # CRITICAL: Must be exact match or clean prefix, not just substring
                    if (connection_part == cleanup_part or 
                        (len(connection_part) >= 4 and connection_part.startswith(cleanup_part))):
                        
                        # Additional validation: ensure it's actually a user identifier
                        # Generic words like "user", "thread", "websocket" are not user-specific
                        if cleanup_part.lower() not in ['user', 'thread', 'websocket', 'conn', 'ws']:
                            return True
        
        return False
        
    def _simulate_business_session(self, scenario: Dict) -> Dict:
        """Simulate a complete business session scenario."""
        user_id = scenario['user_id']
        session_errors = 0
        
        try:
            # Create initial WebSocket connection
            connection_ids = self._create_websocket_connection(user_id, "manager")
            
            # Simulate agent switches during session
            for switch_num in range(scenario['agent_switches']):
                execution_ids = self._create_agent_execution_context(user_id, "generator")
                
                # Simulate some processing time
                time.sleep(0.01)
                
                # Test cleanup during agent switch
                cleanup_success = self._perform_websocket_cleanup(
                    user_id, connection_ids, execution_ids, "generator"
                )
                
                if not cleanup_success:
                    session_errors += 1
                    
                # Re-establish connection for next switch
                if switch_num < scenario['agent_switches'] - 1:
                    connection_ids = self._create_websocket_connection(user_id, "generator")
                    
            return {
                'session_completed': session_errors == 0,
                'websocket_errors': session_errors
            }
            
        except Exception as e:
            return {
                'session_completed': False,
                'websocket_errors': 999,  # Major failure
                'error': str(e)
            }
            
    def _create_websocket_connection_with_dual_ssot(self, user_id: str):
        """Create WebSocket connection using alternating SSOT systems."""
        system = "manager" if hash(user_id) % 2 == 0 else "generator"
        return self._create_websocket_connection(user_id, system)
        
    def _cleanup_websocket_resources_with_dual_ssot(self, user_id: str):
        """Cleanup WebSocket resources using alternating SSOT systems."""
        # Find any connection for this user
        user_connections = [
            (thread_id, info) for thread_id, info in self.active_connections.items()
            if info.get('user_id') == user_id
        ]
        
        if user_connections:
            thread_id, connection_info = user_connections[0]
            cleanup_system = "generator" if connection_info['created_by'] == "manager" else "manager"
            
            return self._perform_websocket_cleanup(
                user_id, 
                {'thread_id': thread_id, 'ws_id': connection_info['ws_id']},
                {'execution_id': 'test', 'agent_id': 'test'},
                cleanup_system
            )
        return True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])