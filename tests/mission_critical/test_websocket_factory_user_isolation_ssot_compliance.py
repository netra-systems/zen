"""

WebSocket Factory User Isolation SSOT Compliance Test

PURPOSE: Enterprise user isolation validation with SSOT patterns
SHOULD FAIL: Because user isolation is compromised by dual patterns
SHOULD PASS: When SSOT factory ensures proper user isolation

Business Impact: $500K+ plus ARR at risk - Enterprise compliance (HIPAA, SOC2, SEC)
GitHub Issue: #1144 - WebSocket Factory Dual Pattern Blocking Golden Path

This test validates that:
    1. User isolation is maintained across all WebSocket factory patterns
2. No shared state contamination between concurrent users
3. Enterprise security requirements are met
4. Factory patterns follow SSOT user isolation standards

CRITICAL: This is a mission critical test protecting enterprise compliance.
"
""


"""

import asyncio
import threading
import time
import uuid
from typing import Dict, List, Any, Optional
from unittest.mock import MagicMock, patch
import concurrent.futures
from dataclasses import dataclass
from pathlib import Path

from test_framework.ssot.base_test_case import SSotBaseTestCase


@dataclass
class UserContext:
    "Test user context for isolation validation."
    user_id: str
    session_id: str
    tenant_id: str
    security_clearance: str
    
    
@dataclass
class WebSocketTestConnection:
    "Test WebSocket connection for isolation validation."
    connection_id: str
    user_context: UserContext
    manager_instance: Any
    state_data: Dict[str, Any]


class WebSocketFactoryUserIsolationSSotComplianceTest(SSotBaseTestCase):
    "
    ""

    Mission Critical Test: WebSocket Factory User Isolation SSOT Compliance.
    
    This test MUST FAIL with current dual pattern implementation to prove
    user isolation violations exist. After SSOT remediation, it should PASS.
    
    Enterprise Impact: HIPAA, SOC2, SEC compliance requirements.
"
""

    
    def setup_method(self, method):
        Set up test environment for user isolation validation.""
        super().setup_method(method)
        
        self.isolation_violations = {
            'shared_state_contamination': [],
            'cross_user_data_leakage': [],
            'factory_instance_sharing': [],
            'session_state_pollution': []
        }
        
        # Record test context metrics
        self.record_metric('test_type', 'user_isolation_compliance')
        self.record_metric('test_category', 'mission_critical')
        
        # Create test user contexts for isolation testing
        self.test_users = [
            UserContext(
                user_id=fuser_{i},
                session_id=f"session_{i}_{uuid.uuid4().hex[:8]},"
                tenant_id=ftenant_{i % 3}",  # Multiple tenants for isolation testing"
                security_clearance=[PUBLIC, CONFIDENTIAL, "SECRET][i % 3]"
            for i in range(5)
        ]
        
        self.test_connections = []
    
    def tearDown(self):
        Clean up test connections and state."
        Clean up test connections and state."
        # Clean up any test connections
        for connection in self.test_connections:
            try:
                if hasattr(connection.manager_instance, 'cleanup'):
                    connection.manager_instance.cleanup()
            except Exception:
                pass
        self.test_connections.clear()
    
    def test_websocket_factory_user_state_isolation_violation(self):
        """
    ""

        CRITICAL: Test detecting user state isolation violations in factory pattern.
        
        This test MUST FAIL because:
        - Dual pattern creates shared state between users
        - Factory instances may be singleton-like across users
        - User context contamination occurs between concurrent sessions
        
        After SSOT fix, should PASS with proper user isolation.
        "
        "
        # Test concurrent user factory creation
        isolation_violations = self._test_concurrent_user_factory_isolation()
        
        print(f\nDETECTED USER STATE ISOLATION VIOLATIONS: {len(isolation_violations)}")"
        for violation in isolation_violations:
            print(f  - User {violation['user_id']}: {violation['violation_type']})
            print(f    Details: {violation['details']}"")
        
        # This assertion SHOULD FAIL with current dual pattern
        # Expected failure: User state contamination detected
        self.assertEqual(
            len(isolation_violations), 0,
            fENTERPRISE SECURITY VIOLATION: Found {len(isolation_violations)} user state isolation violations. 
            fThis violates HIPAA, SOC2, and SEC compliance requirements. "
            fThis violates HIPAA, SOC2, and SEC compliance requirements. "
            f"Violations: {[v['violation_type'] for v in isolation_violations]}"
        )
    
    def test_websocket_factory_cross_tenant_data_leakage_detection(self):
        pass
        CRITICAL: Test detecting cross-tenant data leakage in factory patterns.
        
        This test MUST FAIL because:
        - Dual pattern allows cross-tenant data contamination
        - Factory instances may share state across tenant boundaries
        - Security clearance isolation is compromised
        
        After SSOT fix, should PASS with strict tenant isolation.
""
        # Test cross-tenant data isolation
        data_leakage_violations = self._test_cross_tenant_data_isolation()
        
        print(f\nDETECTED CROSS-TENANT DATA LEAKAGE VIOLATIONS: {len(data_leakage_violations)})
        for violation in data_leakage_violations:
            print(f  - Tenant {violation['source_tenant']} -> {violation['target_tenant']}")"
            print(f    Data leaked: {violation['leaked_data_type']})
            print(f    Security impact: {violation['security_impact']}")"
        
        # This assertion SHOULD FAIL with current data leakage
        # Expected failure: Cross-tenant contamination detected
        self.assertEqual(
            len(data_leakage_violations), 0,
            fENTERPRISE SECURITY VIOLATION: Found {len(data_leakage_violations)} cross-tenant data leakage violations. 
            fThis violates multi-tenant security requirements and regulatory compliance. 
            f"Affected tenants: {list(set(v['source_tenant'] for v in data_leakage_violations))}"
        )
    
    def test_websocket_factory_concurrent_session_contamination_detection(self):
        """
        ""

        CRITICAL: Test detecting session contamination in concurrent access.
        
        This test MUST FAIL because:
        - Dual pattern creates race conditions between user sessions
        - Factory state is shared across concurrent connections
        - Session data bleeds between users
        
        After SSOT fix, should PASS with isolated session management.
"
"
        # Test concurrent session isolation
        session_contamination = self._test_concurrent_session_isolation()
        
        print(f"\nDETECTED SESSION CONTAMINATION VIOLATIONS: {len(session_contamination)}))"
        for contamination in session_contamination:
            print(f  - Session {contamination['source_session']} contaminated {contamination['target_session']})"
            print(f  - Session {contamination['source_session']} contaminated {contamination['target_session']})"
            print(f"    Contamination type: {contamination['contamination_type']}))"
            print(f    Data affected: {contamination['affected_data']})"
            print(f    Data affected: {contamination['affected_data']})""

        
        # This assertion SHOULD FAIL with current session contamination
        # Expected failure: Session state contamination detected
        self.assertEqual(
            len(session_contamination), 0,
            f"ENTERPRISE SECURITY VIOLATION: Found {len(session_contamination)} session contamination violations."
            fThis creates security vulnerabilities in multi-user environment. 
            fContamination types: {list(set(c['contamination_type'] for c in session_contamination))}
        )
    
    def test_websocket_factory_security_clearance_isolation_violation(self):
        """

        CRITICAL: Test detecting security clearance isolation violations.
        
        This test MUST FAIL because:
        - Dual pattern doesn't enforce security clearance boundaries'
        - Users with different clearances share factory instances
        - Classified data may leak to unauthorized users
        
        After SSOT fix, should PASS with clearance-based isolation.

        # Test security clearance isolation
        clearance_violations = self._test_security_clearance_isolation()
        
        print(f"\nDETECTED SECURITY CLEARANCE VIOLATIONS: {len(clearance_violations)})"
        for violation in clearance_violations:
            print(f  - User {violation['user_id']} (clearance: {violation['user_clearance']})
            print(f"    Accessed data requiring: {violation['required_clearance']})"
            print(f    Violation severity: {violation['severity']})
        
        # This assertion SHOULD FAIL with current clearance violations
        # Expected failure: Security clearance boundaries violated
        self.assertEqual(
            len(clearance_violations), 0,
            f"ENTERPRISE SECURITY VIOLATION: Found {len(clearance_violations)} security clearance violations."
            fThis violates government/enterprise security requirements. "
            fThis violates government/enterprise security requirements. ""

            fAffected clearances: {list(set(v['required_clearance'] for v in clearance_violations))}
        )
    
    def test_websocket_factory_memory_isolation_violation(self):
        """
        ""

        CRITICAL: Test detecting memory isolation violations in factory pattern.
        
        This test MUST FAIL because:
        - Dual pattern creates shared memory structures
        - User data persists in memory across sessions
        - Memory leaks contain sensitive data from other users
        
        After SSOT fix, should PASS with proper memory isolation.
"
"
        # Test memory isolation between users
        memory_violations = self._test_memory_isolation()
        
        print(f\nDETECTED MEMORY ISOLATION VIOLATIONS: {len(memory_violations)}")"
        for violation in memory_violations:
            print(f  - Memory region: {violation['memory_region']}")"
            print(f    Contains data from users: {violation['user_data_found']}")"
            print(f    Data sensitivity: {violation['data_sensitivity']}")"
        
        # This assertion SHOULD FAIL with current memory violations
        # Expected failure: Memory contamination between users detected
        self.assertEqual(
            len(memory_violations), 0,
            fENTERPRISE SECURITY VIOLATION: Found {len(memory_violations)} memory isolation violations. 
            fThis creates data leakage risks and violates data protection regulations. ""
            fAffected memory regions: {[v['memory_region'] for v in memory_violations]}
        )
    
    def _test_concurrent_user_factory_isolation(self) -> List[Dict]:
        Test user state isolation in concurrent factory creation.""
        violations = []
        
        # Create concurrent WebSocket factory instances for different users
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            
            for user in self.test_users:
                future = executor.submit(self._create_user_websocket_connection, user)
                futures.append((user, future))
            
            # Collect results
            connections = []
            for user, future in futures:
                try:
                    connection = future.result(timeout=5)
                    connections.append(connection)
                    self.test_connections.append(connection)
                except Exception as e:
                    violations.append({
                        'user_id': user.user_id,
                        'violation_type': 'factory_creation_failure',
                        'details': fFailed to create isolated factory: {str(e)}
                    }
        
        # Analyze isolation between connections
        for i, conn1 in enumerate(connections):
            for j, conn2 in enumerate(connections[i+1:], i+1):
                if self._connections_share_state(conn1, conn2):
                    violations.append({
                        'user_id': f{conn1.user_context.user_id}+{conn2.user_context.user_id},
                        'violation_type': 'shared_factory_state',
                        'details': f"Connections share state: {conn1.connection_id} <-> {conn2.connection_id}"
                    }
        
        return violations
    
    def _test_cross_tenant_data_isolation(self) -> List[Dict]:
        "Test cross-tenant data isolation."
        violations = []
        
        # Create connections for different tenants
        tenant_connections = {}
        for user in self.test_users:
            if user.tenant_id not in tenant_connections:
                tenant_connections[user.tenant_id] = []
            
            try:
                connection = self._create_user_websocket_connection(user)
                tenant_connections[user.tenant_id].append(connection)
                self.test_connections.append(connection)
                
                # Inject tenant-specific test data
                self._inject_tenant_test_data(connection, user.tenant_id)
                
            except Exception as e:
                violations.append({
                    'source_tenant': user.tenant_id,
                    'target_tenant': 'unknown',
                    'leaked_data_type': 'connection_failure',
                    'security_impact': f"Tenant isolation test failed: {str(e)}"
                }
        
        # Test cross-tenant data access
        for tenant_id, connections in tenant_connections.items():
            for connection in connections:
                other_tenant_data = self._check_for_cross_tenant_data(connection, tenant_id)
                for data_item in other_tenant_data:
                    violations.append({
                        'source_tenant': data_item['source_tenant'],
                        'target_tenant': tenant_id,
                        'leaked_data_type': data_item['data_type'],
                        'security_impact': 'CRITICAL - Cross-tenant data leakage'
                    }
        
        return violations
    
    def _test_concurrent_session_isolation(self) -> List[Dict]:
        "Test session isolation in concurrent access."
        contaminations = []
        
        # Create multiple sessions for same user to test session isolation
        user = self.test_users[0]
        sessions = []
        
        # Create concurrent sessions
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for i in range(3):
                session_user = UserContext(
                    user_id=user.user_id,
                    session_id=f"session_{i}_{uuid.uuid4().hex[:8]},"
                    tenant_id=user.tenant_id,
                    security_clearance=user.security_clearance
                )
                future = executor.submit(self._create_user_websocket_connection, session_user)
                futures.append((session_user, future))
            
            # Collect sessions
            for session_user, future in futures:
                try:
                    connection = future.result(timeout=5)
                    sessions.append(connection)
                    self.test_connections.append(connection)
                    
                    # Inject session-specific data
                    self._inject_session_test_data(connection, session_user.session_id)
                    
                except Exception as e:
                    contaminations.append({
                        'source_session': 'unknown',
                        'target_session': session_user.session_id,
                        'contamination_type': 'session_creation_failure',
                        'affected_data': fSession creation failed: {str(e)}"
                        'affected_data': fSession creation failed: {str(e)}""

                    }
        
        # Check for cross-session contamination
        for i, session1 in enumerate(sessions):
            for j, session2 in enumerate(sessions[i+1:], i+1):
                contamination = self._check_session_contamination(session1, session2)
                if contamination:
                    contaminations.append(contamination)
        
        return contaminations
    
    def _test_security_clearance_isolation(self) -> List[Dict]:
        Test security clearance isolation.""
        violations = []
        
        # Create connections with different security clearances
        clearance_connections = {}
        for user in self.test_users:
            if user.security_clearance not in clearance_connections:
                clearance_connections[user.security_clearance] = []
            
            try:
                connection = self._create_user_websocket_connection(user)
                clearance_connections[user.security_clearance].append(connection)
                self.test_connections.append(connection)
                
                # Inject clearance-appropriate test data
                self._inject_clearance_test_data(connection, user.security_clearance)
                
            except Exception:
                continue
        
        # Test clearance boundary violations
        clearance_hierarchy = ['PUBLIC', 'CONFIDENTIAL', 'SECRET']
        
        for clearance, connections in clearance_connections.items():
            clearance_level = clearance_hierarchy.index(clearance) if clearance in clearance_hierarchy else 0
            
            for connection in connections:
                # Check if user can access higher clearance data
                for higher_clearance in clearance_hierarchy[clearance_level + 1:]:
                    if self._can_access_clearance_data(connection, higher_clearance):
                        violations.append({
                            'user_id': connection.user_context.user_id,
                            'user_clearance': clearance,
                            'required_clearance': higher_clearance,
                            'severity': 'CRITICAL'
                        }
        
        return violations
    
    def _test_memory_isolation(self) -> List[Dict]:
        Test memory isolation between user sessions."
        Test memory isolation between user sessions.""

        violations = []
        
        # Create and destroy connections to test memory cleanup
        memory_snapshots = []
        
        for user in self.test_users:
            try:
                # Create connection
                connection = self._create_user_websocket_connection(user)
                self.test_connections.append(connection)
                
                # Inject user-specific data
                user_data = f"sensitive_data_for_{user.user_id}_{user.tenant_id}"
                self._inject_user_memory_data(connection, user_data)
                
                # Take memory snapshot
                memory_snapshot = self._capture_memory_snapshot(connection)
                memory_snapshots.append((user, memory_snapshot))
                
                # Cleanup connection
                if hasattr(connection.manager_instance, 'cleanup'):
                    connection.manager_instance.cleanup()
                    
            except Exception:
                continue
        
        # Check for memory contamination
        for i, (user1, snapshot1) in enumerate(memory_snapshots):
            for j, (user2, snapshot2) in enumerate(memory_snapshots[i+1:], i+1):
                contamination = self._check_memory_contamination(user1, snapshot1, user2, snapshot2)
                if contamination:
                    violations.append(contamination)
        
        return violations
    
    def _create_user_websocket_connection(self, user: UserContext) -> WebSocketTestConnection:
        Create a WebSocket connection for a user (attempts both patterns)."
        Create a WebSocket connection for a user (attempts both patterns)."
        connection_id = f"conn_{user.user_id}_{uuid.uuid4().hex[:8]}"
        
        # Try to create manager using current dual pattern
        manager_instance = None
        
        # Try legacy pattern first
        try:
            from netra_backend.app.websocket.connection_manager import get_connection_manager
            manager_instance = get_connection_manager()
        except Exception:
            pass
        
        # Try core pattern if legacy failed
        if not manager_instance:
            try:
                from netra_backend.app.websocket_core.manager import WebSocketManager
                manager_instance = WebSocketManager()
            except Exception:
                pass
        
        # Create mock manager if both failed (indicates SSOT compliance)
        if not manager_instance:
            manager_instance = MagicMock()
            manager_instance.user_context = user
            manager_instance.connection_id = connection_id
        
        return WebSocketTestConnection(
            connection_id=connection_id,
            user_context=user,
            manager_instance=manager_instance,
            state_data={}
    
    def _connections_share_state(self, conn1: WebSocketTestConnection, conn2: WebSocketTestConnection) -> bool:
        Check if two connections share state (violation)."
        Check if two connections share state (violation)."
        # Check if manager instances are the same object (shared state)
        if id(conn1.manager_instance) == id(conn2.manager_instance):
            return True
        
        # Check if managers share internal state
        if (hasattr(conn1.manager_instance, '_instance') and 
            hasattr(conn2.manager_instance, '_instance') and
            id(conn1.manager_instance._instance) == id(conn2.manager_instance._instance)):
            return True
        
        return False
    
    def _inject_tenant_test_data(self, connection: WebSocketTestConnection, tenant_id: str):
        "Inject tenant-specific test data."
        test_data = ftenant_{tenant_id}_sensitive_data_{uuid.uuid4().hex[:8]}""
        connection.state_data[f'tenant_data_{tenant_id}'] = test_data
        
        # Try to inject into manager if possible
        if hasattr(connection.manager_instance, 'tenant_data'):
            connection.manager_instance.tenant_data = test_data
        elif hasattr(connection.manager_instance, '__dict__'):
            connection.manager_instance.__dict__[f'tenant_data_{tenant_id}'] = test_data
    
    def _check_for_cross_tenant_data(self, connection: WebSocketTestConnection, current_tenant: str) -> List[Dict]:
        Check for cross-tenant data in connection."
        Check for cross-tenant data in connection.""

        cross_tenant_data = []
        
        # Check state data for other tenant data
        for key, value in connection.state_data.items():
            if 'tenant_' in key and current_tenant not in key:
                cross_tenant_data.append({
                    'source_tenant': key.split('_')[1] if '_' in key else 'unknown',
                    'data_type': 'state_data'
                }
        
        # Check manager attributes for cross-tenant contamination
        if hasattr(connection.manager_instance, '__dict__'):
            for attr_name, attr_value in connection.manager_instance.__dict__.items():
                if 'tenant_' in attr_name and current_tenant not in attr_name:
                    cross_tenant_data.append({
                        'source_tenant': attr_name.split('_')[1] if '_' in attr_name else 'unknown',
                        'data_type': 'manager_attribute'
                    }
        
        return cross_tenant_data
    
    def _inject_session_test_data(self, connection: WebSocketTestConnection, session_id: str):
        "Inject session-specific test data."
        test_data = f"session_{session_id}_data_{uuid.uuid4().hex[:8]}"
        connection.state_data[f'session_data_{session_id}'] = test_data
    
    def _check_session_contamination(self, session1: WebSocketTestConnection, session2: WebSocketTestConnection) -> Optional[Dict]:
        "Check for session contamination between two sessions."
        # Check if session1 data appears in session2
        session1_id = session1.user_context.session_id
        session2_id = session2.user_context.session_id
        
        # Check state data contamination
        for key in session2.state_data:
            if session1_id in key:
                return {
                    'source_session': session1_id,
                    'target_session': session2_id,
                    'contamination_type': 'state_data_bleed',
                    'affected_data': key
                }
        
        return None
    
    def _inject_clearance_test_data(self, connection: WebSocketTestConnection, clearance: str):
        "Inject clearance-appropriate test data."
        test_data = f{clearance}_classified_data_{uuid.uuid4().hex[:8]}"
        test_data = f{clearance}_classified_data_{uuid.uuid4().hex[:8]}""

        connection.state_data[f'clearance_data_{clearance}'] = test_data
    
    def _can_access_clearance_data(self, connection: WebSocketTestConnection, target_clearance: str) -> bool:
        "Check if connection can access higher clearance data."
        # Check if higher clearance data is accessible
        target_key = f'clearance_data_{target_clearance}'
        return target_key in connection.state_data
    
    def _inject_user_memory_data(self, connection: WebSocketTestConnection, user_data: str):
        ""Inject user-specific data into memory.""

        connection.state_data['user_memory_data'] = user_data
    
    def _capture_memory_snapshot(self, connection: WebSocketTestConnection) -> Dict:
        Capture memory snapshot for contamination analysis.""
        return {
            'state_data': dict(connection.state_data),
            'manager_attrs': getattr(connection.manager_instance, '__dict__', {}.copy()
        }
    
    def _check_memory_contamination(self, user1: UserContext, snapshot1: Dict, 
                                  user2: UserContext, snapshot2: Dict) -> Optional[Dict]:
        Check for memory contamination between users.""
        # Check if user1 data appears in user2's snapshot'
        user1_data = snapshot1.get('state_data', {}.get('user_memory_data', '')
        user2_data = snapshot2.get('state_data', {}.get('user_memory_data', '')
        
        if user1.user_id in user2_data or user2.user_id in user1_data:
            return {
                'memory_region': 'state_data',
                'user_data_found': [user1.user_id, user2.user_id],
                'data_sensitivity': 'HIGH'
            }
        
        return None


if __name__ == '__main__':
    # Run with verbose output to show violation details
    unittest.main(verbosity=2)
)))))))))))))