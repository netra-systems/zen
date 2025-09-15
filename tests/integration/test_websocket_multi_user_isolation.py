"""WebSocket Multi-User Isolation Test Suite

PURPOSE: Validate proper user context separation for Issue #1182 WebSocket Manager SSOT Migration
BUSINESS VALUE: Protects $500K+ ARR by ensuring enterprise-grade user isolation for HIPAA, SOC2, SEC compliance

This test suite MUST FAIL with current cross-user state contamination and PASS after SSOT consolidation.

CRITICAL: These tests follow claude.md requirements:
- NO Docker dependencies (integration without docker)
- Real services focus
- Multi-user isolation validation
- Enterprise security requirements
"""

import asyncio
import unittest
import uuid
import time
import json
from typing import Dict, List, Set, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
import threading

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.logging.unified_logging_ssot import get_logger
from shared.types.core_types import UserID, ThreadID, ensure_user_id

logger = get_logger(__name__)


@dataclass
class UserSession:
    """Represents a user session for isolation testing."""
    user_id: str
    session_id: str
    websocket_manager: Any = None
    secret_data: Dict[str, Any] = field(default_factory=dict)
    contamination_detected: List[str] = field(default_factory=list)
    operation_results: List[Dict[str, Any]] = field(default_factory=list)


class TestWebSocketMultiUserIsolation(SSotAsyncTestCase):
    """Test WebSocket manager multi-user isolation and security.
    
    These tests MUST FAIL with current cross-user state contamination.
    After SSOT consolidation, they MUST PASS with complete user isolation.
    """

    def setUp(self):
        """Set up test environment for multi-user isolation testing."""
        super().setUp()
        self.user_sessions = {}
        self.contamination_violations = []
        self.security_violations = []
        self.performance_violations = []
        
    async def asyncSetUp(self):
        """Async setup for multi-user testing."""
        await super().asyncSetUp()
        await self._create_isolated_user_sessions()
        
    async def _create_isolated_user_sessions(self) -> None:
        """Create isolated user sessions for testing."""
        # Create different types of users for comprehensive testing
        user_profiles = [
            {"type": "healthcare_user", "compliance": "HIPAA", "sensitivity": "high"},
            {"type": "financial_user", "compliance": "SOC2", "sensitivity": "high"},
            {"type": "government_user", "compliance": "SEC", "sensitivity": "critical"},
            {"type": "enterprise_user", "compliance": "general", "sensitivity": "medium"},
            {"type": "free_tier_user", "compliance": "basic", "sensitivity": "low"}
        ]
        
        for i, profile in enumerate(user_profiles):
            try:
                # Create proper user execution context
                from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType
                
                id_manager = UnifiedIDManager()
                user_id = ensure_user_id(id_manager.generate_id(IDType.USER, prefix=f"isolation_test_{profile['type']}"))
                session_id = id_manager.generate_id(IDType.THREAD, prefix=f"session_{profile['type']}")
                
                # Create user context with compliance requirements
                user_context = type('TestUserContext', (), {
                    'user_id': user_id,
                    'session_id': session_id,
                    'request_id': id_manager.generate_id(IDType.REQUEST, prefix=f"req_{profile['type']}"),
                    'is_test': True,
                    'compliance_level': profile['compliance'],
                    'sensitivity_level': profile['sensitivity'],
                    'user_type': profile['type']
                })()
                
                # Create user session
                user_session = UserSession(
                    user_id=user_id,
                    session_id=session_id
                )
                
                # Add sensitive test data that must NOT leak between users
                user_session.secret_data = {
                    'ssn': f"000-00-{1000 + i}",  # Mock SSN for testing
                    'financial_data': f"account_{user_id}_{i}",
                    'health_record': f"patient_record_{user_id}",
                    'classified_info': f"top_secret_{profile['type']}_{uuid.uuid4()}",
                    'api_key': f"sk-{uuid.uuid4().hex}",
                    'session_token': f"token_{uuid.uuid4().hex}"
                }
                
                self.user_sessions[user_id] = user_session
                logger.info(f"Created isolated user session for {profile['type']}: {user_id}")
                
            except Exception as e:
                logger.error(f"Failed to create user session {i}: {e}")
                self.fail(f"Unable to create test user sessions: {e}")

    async def test_websocket_manager_user_data_isolation(self):
        """
        CRITICAL TEST: Verify complete isolation of user data between WebSocket managers
        
        EXPECTED BEHAVIOR:
        - MUST FAIL (current): User data leaks between manager instances
        - MUST PASS (after SSOT): Complete user data isolation
        """
        logger.info("Testing WebSocket manager user data isolation...")
        
        try:
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
            
            # Create managers for each user and set sensitive data
            for user_id, session in self.user_sessions.items():
                try:
                    # Create user context for manager
                    user_context = type('UserContext', (), {
                        'user_id': user_id,
                        'session_id': session.session_id,
                        'is_test': True
                    })()
                    
                    # Get WebSocket manager
                    manager = await get_websocket_manager(user_context=user_context)
                    session.websocket_manager = manager
                    
                    # Set sensitive data in manager that must NOT leak
                    if hasattr(manager, '_user_data'):
                        manager._user_data = session.secret_data.copy()
                    elif hasattr(manager, '__dict__'):
                        for key, value in session.secret_data.items():
                            setattr(manager, f"user_{key}", value)
                    
                    logger.info(f"Set sensitive data for user {user_id}: {list(session.secret_data.keys())}")
                    
                except Exception as e:
                    logger.error(f"Failed to create manager for user {user_id}: {e}")
                    self.contamination_violations.append(f"Manager creation failed for {user_id}: {e}")
            
            # Test for data leakage between users
            data_leakage_violations = []
            
            for user_id1, session1 in self.user_sessions.items():
                if session1.websocket_manager is None:
                    continue
                    
                for user_id2, session2 in self.user_sessions.items():
                    if user_id1 == user_id2 or session2.websocket_manager is None:
                        continue
                    
                    # Check if manager1 has access to manager2's sensitive data
                    manager1 = session1.websocket_manager
                    
                    # Test different ways data might leak
                    for secret_key, secret_value in session2.secret_data.items():
                        # Check direct attribute access
                        if hasattr(manager1, f"user_{secret_key}"):
                            leaked_value = getattr(manager1, f"user_{secret_key}")
                            if leaked_value == secret_value:
                                data_leakage_violations.append(
                                    f"CRITICAL: User {user_id1} manager has access to {user_id2}'s {secret_key}: {leaked_value}"
                                )
                        
                        # Check user data dictionary
                        if hasattr(manager1, '_user_data') and isinstance(manager1._user_data, dict):
                            if secret_key in manager1._user_data and manager1._user_data[secret_key] == secret_value:
                                data_leakage_violations.append(
                                    f"CRITICAL: User {user_id1} manager._user_data contains {user_id2}'s {secret_key}"
                                )
                        
                        # Check for shared object references
                        if hasattr(manager1, '_user_data') and hasattr(session2.websocket_manager, '_user_data'):
                            if id(manager1._user_data) == id(session2.websocket_manager._user_data):
                                data_leakage_violations.append(
                                    f"CRITICAL: Shared _user_data object between {user_id1} and {user_id2}"
                                )
            
            # ASSERTION: This MUST FAIL currently (proving data leakage exists)
            # After SSOT consolidation, this MUST PASS (complete data isolation)
            self.assertEqual(len(data_leakage_violations), 0,
                           f"USER DATA ISOLATION VIOLATIONS: Found {len(data_leakage_violations)} data leakage issues. "
                           f"Violations: {data_leakage_violations}")
                           
        except Exception as e:
            self.fail(f"Failed to test user data isolation: {e}")

    async def test_websocket_manager_concurrent_operation_isolation(self):
        """
        CRITICAL TEST: Verify concurrent operations don't contaminate user contexts
        
        EXPECTED BEHAVIOR:
        - MUST FAIL (current): Concurrent operations share state
        - MUST PASS (after SSOT): Complete operation isolation
        """
        logger.info("Testing WebSocket manager concurrent operation isolation...")
        
        concurrent_violations = []
        
        async def simulate_user_operation(user_id: str, operation_id: str, secret_payload: str) -> Dict[str, Any]:
            """Simulate a user-specific operation with sensitive data."""
            try:
                session = self.user_sessions[user_id]
                manager = session.websocket_manager
                
                if manager is None:
                    return {'error': f'No manager for user {user_id}'}
                
                # Simulate setting sensitive operation state
                operation_state = {
                    'user_id': user_id,
                    'operation_id': operation_id,
                    'secret_payload': secret_payload,
                    'timestamp': time.time(),
                    'processing_flag': f"processing_{user_id}_{operation_id}"
                }
                
                # Set state in manager
                if hasattr(manager, '_current_operation'):
                    manager._current_operation = operation_state
                elif hasattr(manager, '__dict__'):
                    manager.__dict__.update({f'op_{operation_id}': operation_state})
                
                # Simulate some async work
                await asyncio.sleep(0.02)  # Allow time for race conditions
                
                # Verify state is still correct after async operation
                if hasattr(manager, '_current_operation'):
                    current_state = manager._current_operation
                    if current_state.get('user_id') != user_id:
                        return {
                            'contamination': f"Operation state contaminated: expected {user_id}, got {current_state.get('user_id')}",
                            'user_id': user_id,
                            'operation_id': operation_id
                        }
                
                return {
                    'success': True,
                    'user_id': user_id,
                    'operation_id': operation_id,
                    'secret_payload': secret_payload
                }
                
            except Exception as e:
                return {
                    'error': str(e),
                    'user_id': user_id,
                    'operation_id': operation_id
                }
        
        # Run concurrent operations for all users
        tasks = []
        for user_id in self.user_sessions.keys():
            for op_num in range(5):  # Multiple operations per user
                secret_payload = f"secret_operation_{user_id}_{op_num}_{uuid.uuid4().hex[:8]}"
                operation_id = f"op_{op_num}"
                task = simulate_user_operation(user_id, operation_id, secret_payload)
                tasks.append(task)
        
        # Execute all operations concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results for contamination
        for result in results:
            if isinstance(result, dict):
                if 'contamination' in result:
                    concurrent_violations.append(result['contamination'])
                elif 'error' in result:
                    concurrent_violations.append(f"Operation failed for {result.get('user_id', 'unknown')}: {result['error']}")
        
        # ASSERTION: This MUST FAIL currently (proving concurrent contamination)
        # After SSOT consolidation, this MUST PASS (isolated concurrent operations)
        self.assertEqual(len(concurrent_violations), 0,
                        f"CONCURRENT OPERATION VIOLATIONS: Found {len(concurrent_violations)} contamination issues. "
                        f"Violations: {concurrent_violations}")

    async def test_websocket_manager_memory_boundary_enforcement(self):
        """
        CRITICAL TEST: Verify memory boundaries prevent cross-user access
        
        EXPECTED BEHAVIOR:
        - MUST FAIL (current): Shared memory allows cross-user access
        - MUST PASS (after SSOT): Strict memory boundaries between users
        """
        logger.info("Testing WebSocket manager memory boundary enforcement...")
        
        memory_violations = []
        
        try:
            # Test memory isolation between managers
            manager_memory_info = {}
            
            for user_id, session in self.user_sessions.items():
                if session.websocket_manager is None:
                    continue
                
                manager = session.websocket_manager
                
                # Get memory information
                manager_id = id(manager)
                manager_dict_id = id(manager.__dict__) if hasattr(manager, '__dict__') else None
                
                # Store memory info
                manager_memory_info[user_id] = {
                    'manager_id': manager_id,
                    'dict_id': manager_dict_id,
                    'class_id': id(type(manager))
                }
                
                # Set unique memory markers
                memory_marker = f"memory_marker_{user_id}_{uuid.uuid4().hex}"
                if hasattr(manager, '__dict__'):
                    manager.__dict__[f'memory_marker_{user_id}'] = memory_marker
            
            # Check for shared memory violations
            for user_id1, info1 in manager_memory_info.items():
                for user_id2, info2 in manager_memory_info.items():
                    if user_id1 == user_id2:
                        continue
                    
                    # Check for shared manager instances
                    if info1['manager_id'] == info2['manager_id']:
                        memory_violations.append(f"CRITICAL: Shared manager instance between {user_id1} and {user_id2}")
                    
                    # Check for shared __dict__ objects
                    if info1['dict_id'] and info2['dict_id'] and info1['dict_id'] == info2['dict_id']:
                        memory_violations.append(f"CRITICAL: Shared __dict__ object between {user_id1} and {user_id2}")
                    
                    # Check for memory marker leakage
                    manager1 = self.user_sessions[user_id1].websocket_manager
                    manager2 = self.user_sessions[user_id2].websocket_manager
                    
                    if hasattr(manager1, f'memory_marker_{user_id2}'):
                        memory_violations.append(f"CRITICAL: {user_id1} manager has memory marker from {user_id2}")
                    
                    if hasattr(manager2, f'memory_marker_{user_id1}'):
                        memory_violations.append(f"CRITICAL: {user_id2} manager has memory marker from {user_id1}")
            
            # ASSERTION: This MUST FAIL currently (proving memory boundary violations)
            # After SSOT consolidation, this MUST PASS (strict memory boundaries)
            self.assertEqual(len(memory_violations), 0,
                           f"MEMORY BOUNDARY VIOLATIONS: Found {len(memory_violations)} memory sharing issues. "
                           f"Violations: {memory_violations}")
                           
        except Exception as e:
            self.fail(f"Failed to test memory boundary enforcement: {e}")

    async def test_websocket_manager_thread_local_isolation(self):
        """
        CRITICAL TEST: Verify thread-local storage isolates user contexts
        
        EXPECTED BEHAVIOR:
        - MUST FAIL (current): Thread-local data leaks between users
        - MUST PASS (after SSOT): Proper thread-local isolation
        """
        logger.info("Testing WebSocket manager thread-local isolation...")
        
        thread_violations = []
        
        def test_thread_isolation(user_id: str, thread_id: int) -> Dict[str, Any]:
            """Test thread isolation for a specific user."""
            try:
                # Create new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def thread_operation():
                    try:
                        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
                        
                        # Create user context
                        user_context = type('ThreadUserContext', (), {
                            'user_id': user_id,
                            'thread_id': thread_id,
                            'is_test': True
                        })()
                        
                        # Get manager in this thread
                        manager = await get_websocket_manager(user_context=user_context)
                        
                        # Set thread-specific data
                        thread_data = f"thread_data_{user_id}_{thread_id}_{uuid.uuid4().hex}"
                        if hasattr(manager, '__dict__'):
                            manager.__dict__[f'thread_data_{thread_id}'] = thread_data
                        
                        # Simulate work
                        await asyncio.sleep(0.01)
                        
                        # Verify data is still correct
                        if hasattr(manager, f'thread_data_{thread_id}'):
                            stored_data = getattr(manager, f'thread_data_{thread_id}')
                            if stored_data != thread_data:
                                return {
                                    'contamination': f"Thread data contaminated for {user_id} in thread {thread_id}",
                                    'expected': thread_data,
                                    'actual': stored_data
                                }
                        
                        return {
                            'success': True,
                            'user_id': user_id,
                            'thread_id': thread_id,
                            'manager_id': id(manager)
                        }
                        
                    except Exception as e:
                        return {
                            'error': str(e),
                            'user_id': user_id,
                            'thread_id': thread_id
                        }
                
                result = loop.run_until_complete(thread_operation())
                loop.close()
                return result
                
            except Exception as e:
                return {
                    'error': str(e),
                    'user_id': user_id,
                    'thread_id': thread_id
                }
        
        # Test multiple threads for multiple users
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            
            # Create multiple threads for each user
            for user_id in self.user_sessions.keys():
                for thread_num in range(3):
                    future = executor.submit(test_thread_isolation, user_id, thread_num)
                    futures.append(future)
            
            # Collect results
            for future in as_completed(futures):
                result = future.result()
                if 'contamination' in result:
                    thread_violations.append(result['contamination'])
                elif 'error' in result:
                    thread_violations.append(f"Thread test failed: {result['error']}")
        
        # ASSERTION: This MUST FAIL currently (proving thread isolation violations)
        # After SSOT consolidation, this MUST PASS (proper thread isolation)
        self.assertEqual(len(thread_violations), 0,
                        f"THREAD ISOLATION VIOLATIONS: Found {len(thread_violations)} thread contamination issues. "
                        f"Violations: {thread_violations}")

    async def test_websocket_manager_compliance_boundary_validation(self):
        """
        CRITICAL TEST: Verify compliance boundaries prevent cross-user data access
        
        EXPECTED BEHAVIOR:
        - MUST FAIL (current): Compliance data leaks between different compliance levels
        - MUST PASS (after SSOT): Strict compliance boundary enforcement
        """
        logger.info("Testing WebSocket manager compliance boundary validation...")
        
        compliance_violations = []
        
        # Group users by compliance level
        compliance_groups = {}
        for user_id, session in self.user_sessions.items():
            if session.websocket_manager is None:
                continue
            
            # Get compliance level from user context
            manager = session.websocket_manager
            if hasattr(manager, 'user_context'):
                compliance_level = getattr(manager.user_context, 'compliance_level', 'unknown')
            else:
                compliance_level = 'unknown'
            
            if compliance_level not in compliance_groups:
                compliance_groups[compliance_level] = []
            compliance_groups[compliance_level].append((user_id, session))
        
        logger.info(f"Compliance groups: {list(compliance_groups.keys())}")
        
        # Test cross-compliance data isolation
        for compliance1, users1 in compliance_groups.items():
            for compliance2, users2 in compliance_groups.items():
                if compliance1 == compliance2:
                    continue
                
                # Test that users from different compliance levels cannot access each other's data
                for user_id1, session1 in users1:
                    for user_id2, session2 in users2:
                        manager1 = session1.websocket_manager
                        
                        # Check if high-compliance user can access low-compliance data (should be prevented)
                        if compliance1 in ['HIPAA', 'SOC2', 'SEC'] and compliance2 == 'basic':
                            # High compliance user should not be able to access basic compliance data
                            if hasattr(manager1, '_user_data'):
                                user_data = getattr(manager1, '_user_data', {})
                                for key, value in session2.secret_data.items():
                                    if key in user_data and user_data[key] == value:
                                        compliance_violations.append(
                                            f"COMPLIANCE VIOLATION: {compliance1} user {user_id1} has access to {compliance2} user {user_id2}'s {key}"
                                        )
                        
                        # Check for shared compliance data structures
                        if (hasattr(manager1, '_compliance_data') and 
                            hasattr(session2.websocket_manager, '_compliance_data')):
                            if id(manager1._compliance_data) == id(session2.websocket_manager._compliance_data):
                                compliance_violations.append(
                                    f"COMPLIANCE VIOLATION: Shared _compliance_data between {compliance1} and {compliance2} users"
                                )
        
        # ASSERTION: This MUST FAIL currently (proving compliance violations)
        # After SSOT consolidation, this MUST PASS (strict compliance boundaries)
        self.assertEqual(len(compliance_violations), 0,
                        f"COMPLIANCE BOUNDARY VIOLATIONS: Found {len(compliance_violations)} compliance issues. "
                        f"Violations: {compliance_violations}")

    async def asyncTearDown(self):
        """Clean up user sessions and managers."""
        for user_id, session in self.user_sessions.items():
            if session.websocket_manager:
                try:
                    if hasattr(session.websocket_manager, 'cleanup'):
                        await session.websocket_manager.cleanup()
                    elif hasattr(session.websocket_manager, 'close'):
                        await session.websocket_manager.close()
                except Exception as e:
                    logger.warning(f"Failed to cleanup manager for user {user_id}: {e}")
        
        await super().asyncTearDown()
        
    def tearDown(self):
        """Clean up after multi-user isolation tests."""
        super().tearDown()
        logger.info(f"Multi-user isolation test completed.")
        logger.info(f"Contamination violations: {len(self.contamination_violations)}")
        logger.info(f"Security violations: {len(self.security_violations)}")
        logger.info(f"Performance violations: {len(self.performance_violations)}")


if __name__ == '__main__':
    unittest.main()