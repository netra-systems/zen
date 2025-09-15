"""
Integration Test Suite: Issue #89 UnifiedIDManager Migration - Cross-Service Validation
==================================================================================

BUSINESS JUSTIFICATION (Issue #89):
- Cross-service ID consistency critical for $500K+ ARR
- WebSocket routing, auth sessions, and data persistence depend on ID format alignment
- Current 7/12 compliance test failures indicate integration issues
- Multi-user isolation requires consistent ID relationships across services

PURPOSE: Integration tests that validate ID consistency across service boundaries
STRATEGY: Real service integration without Docker (staging GCP validation)
VALIDATION: These tests FAIL until cross-service migration coordination is complete

CRITICAL INTEGRATION PATTERNS:
1. Auth Service ↔ Backend ID format alignment
2. WebSocket ↔ User Context ID consistency
3. Thread/Run ID relationships across services
4. Database persistence ID format validation
5. Real-time communication ID routing

Expected Outcome: Integration failures expose cross-service migration gaps
"""
import pytest
import asyncio
import time
from typing import Dict, List, Set, Optional, Any
from pathlib import Path
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.core.unified_id_manager import UnifiedIDManager
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from netra_backend.app.services.user_execution_context import UserExecutionContext
try:
    from auth_service.auth_core.services.auth_service import AuthService
    from auth_service.auth_core.core.jwt_handler import JWTHandler
    AUTH_SERVICE_AVAILABLE = True
except ImportError:
    AUTH_SERVICE_AVAILABLE = False

class TestIDMigrationCrossServiceIntegration(SSotAsyncTestCase):
    """Integration tests for cross-service ID consistency and migration compliance."""

    def setup_method(self, method=None):
        """Setup for cross-service integration tests."""
        super().setup_method(method)
        self.env = IsolatedEnvironment()
        self.service_integration_failures = []
        self.id_format_mismatches = []
        self.routing_consistency_issues = []
        self.test_user_contexts = []

    async def test_auth_backend_id_format_integration_EXPECT_FAILURE(self):
        """
        EXPECTED FAILURE: Auth service and backend use incompatible ID formats.
        
        BUSINESS IMPACT: $500K+ ARR - User authentication must integrate with backend routing.
        """
        if not AUTH_SERVICE_AVAILABLE:
            pytest.skip('Auth service not available for integration testing')
        auth_backend_mismatches = []
        try:
            auth_service = AuthService()
            test_email = f'integration_test_{int(time.time())}@example.com'
            auth_user_data = await auth_service.create_user({'email': test_email, 'password': 'test_password123'})
            auth_user_id = auth_user_data.get('id') or auth_user_data.get('user_id')
            if not self._is_unified_id_format(auth_user_id):
                auth_backend_mismatches.append({'service': 'auth_service', 'id_type': 'user_id', 'id_value': auth_user_id, 'issue': 'Does not follow UnifiedIdGenerator structured format', 'expected': 'user_timestamp_counter_random'})
            try:
                backend_context = UserExecutionContext.from_request(user_id=auth_user_id, thread_id=UnifiedIDManager.generate_thread_id(), run_id=UnifiedIDManager.generate_run_id(UnifiedIDManager.generate_thread_id()), request_id=UnifiedIdGenerator.generate_base_id('req'))
                context_ids = {'user_id': backend_context.user_id, 'thread_id': backend_context.thread_id, 'run_id': backend_context.run_id, 'request_id': backend_context.request_id}
                for id_type, id_value in context_ids.items():
                    if not self._is_unified_id_format(id_value):
                        auth_backend_mismatches.append({'service': 'backend', 'id_type': id_type, 'id_value': id_value, 'issue': f'Backend {id_type} not in unified format', 'expected': f"{id_type.split('_')[0]}_timestamp_counter_random"})
                extracted_thread_id = UnifiedIDManager.extract_thread_id(backend_context.run_id)
                if extracted_thread_id != backend_context.thread_id:
                    auth_backend_mismatches.append({'service': 'integration', 'id_type': 'thread_run_relationship', 'id_value': f'{backend_context.thread_id} -> {backend_context.run_id}', 'issue': f'Thread extraction mismatch: expected {backend_context.thread_id}, got {extracted_thread_id}', 'expected': 'Run ID should properly embed thread ID'})
            except Exception as e:
                auth_backend_mismatches.append({'service': 'backend', 'id_type': 'context_creation', 'id_value': 'N/A', 'issue': f'Backend context creation failed with auth user ID: {e}', 'expected': 'Backend should handle auth service user IDs gracefully'})
        except Exception as e:
            auth_backend_mismatches.append({'service': 'auth_service', 'id_type': 'user_creation', 'id_value': 'N/A', 'issue': f'Auth service user creation failed: {e}', 'expected': 'Auth service should use UnifiedIdGenerator for user IDs'})
        self.assertGreater(len(auth_backend_mismatches), 0, 'Expected auth service and backend ID format mismatches. If this passes, services are already integrated!')
        self.service_integration_failures.extend(auth_backend_mismatches)
        report_lines = [f'AUTH-BACKEND INTEGRATION FAILURES: {len(auth_backend_mismatches)} mismatches', '🚨 BUSINESS IMPACT: $500K+ ARR depends on auth/backend ID integration', '']
        for mismatch in auth_backend_mismatches:
            report_lines.extend([f"   🔧 {mismatch['service']}.{mismatch['id_type']}", f"      Value: {mismatch['id_value'][:60]}...", f"      Issue: {mismatch['issue']}", f"      Expected: {mismatch['expected']}", ''])
        report_lines.extend(['🎯 INTEGRATION MIGRATION REQUIRED:', '   - Migrate auth service to UnifiedIdGenerator', '   - Update backend to handle legacy auth IDs during transition', '   - Implement ID format conversion layer if needed'])
        pytest.fail('\n'.join(report_lines))

    async def test_websocket_user_context_id_consistency_EXPECT_FAILURE(self):
        """
        EXPECTED FAILURE: WebSocket routing and user context use inconsistent ID formats.
        
        BUSINESS IMPACT: Chat functionality (90% of platform value) depends on consistent routing.
        """
        websocket_context_issues = []
        test_users = [f'test_user_{int(time.time())}_001', f'test_user_{int(time.time())}_002']
        for user_id in test_users:
            try:
                websocket_id = UnifiedIDManager().generate_websocket_id_with_user_context(user_id)
                user_context = UserExecutionContext.from_request(user_id=user_id, thread_id=UnifiedIDManager.generate_thread_id(), run_id=UnifiedIDManager.generate_run_id(UnifiedIDManager.generate_thread_id()), request_id=UnifiedIdGenerator.generate_base_id('req'))
                if not self._is_unified_id_format(websocket_id):
                    websocket_context_issues.append({'component': 'websocket', 'id_type': 'connection_id', 'id_value': websocket_id, 'user_id': user_id, 'issue': 'WebSocket connection ID not in unified format', 'business_impact': 'Chat routing failures'})
                context_ids = {'thread_id': user_context.thread_id, 'run_id': user_context.run_id, 'request_id': user_context.request_id}
                for id_type, id_value in context_ids.items():
                    if not self._is_unified_id_format(id_value):
                        websocket_context_issues.append({'component': 'user_context', 'id_type': id_type, 'id_value': id_value, 'user_id': user_id, 'issue': f'User context {id_type} not in unified format', 'business_impact': 'Multi-user isolation failures'})
                if user_id not in websocket_id and (not self._has_user_context_embedding(websocket_id, user_id)):
                    websocket_context_issues.append({'component': 'integration', 'id_type': 'websocket_user_binding', 'id_value': f'{websocket_id} for user {user_id}', 'user_id': user_id, 'issue': 'WebSocket ID does not contain user context for routing', 'business_impact': 'Cross-user message delivery failures'})
                extracted_thread = UnifiedIDManager.extract_thread_id(user_context.run_id)
                if extracted_thread != user_context.thread_id:
                    websocket_context_issues.append({'component': 'user_context', 'id_type': 'thread_run_consistency', 'id_value': f'{user_context.thread_id} -> {user_context.run_id}', 'user_id': user_id, 'issue': f'Thread extraction failed: expected {user_context.thread_id}, got {extracted_thread}', 'business_impact': 'Agent execution routing failures'})
            except Exception as e:
                websocket_context_issues.append({'component': 'system', 'id_type': 'creation_failure', 'id_value': 'N/A', 'user_id': user_id, 'issue': f'WebSocket/context creation failed: {e}', 'business_impact': 'System unavailable for users'})
        self.assertGreater(len(websocket_context_issues), 1, f'Expected >1 WebSocket/context consistency issue, found {len(websocket_context_issues)}. If this passes, WebSocket routing is already consistent!')
        self.routing_consistency_issues.extend(websocket_context_issues)
        report_lines = [f'WEBSOCKET-CONTEXT INTEGRATION FAILURES: {len(websocket_context_issues)} issues', '🚨 BUSINESS IMPACT: 90% of platform value depends on consistent chat routing', '']
        for issue in websocket_context_issues[:8]:
            report_lines.extend([f"   💬 {issue['component']}.{issue['id_type']}", f"      User: {issue['user_id']}", f"      Value: {issue['id_value'][:50]}...", f"      Issue: {issue['issue']}", f"      Impact: {issue['business_impact']}", ''])
        report_lines.extend(['🎯 WEBSOCKET INTEGRATION MIGRATION REQUIRED:', '   - Standardize WebSocket ID generation with UnifiedIdGenerator', '   - Ensure user context embedding in WebSocket IDs', '   - Validate thread/run relationship consistency', '   - Test multi-user isolation in real scenarios'])
        pytest.fail('\n'.join(report_lines))

    async def test_database_persistence_id_format_consistency_EXPECT_FAILURE(self):
        """
        EXPECTED FAILURE: Database persistence layers use inconsistent ID formats.
        
        BUSINESS IMPACT: Data integrity and query performance depend on consistent ID indexing.
        """
        database_consistency_issues = []
        test_scenarios = [{'operation': 'user_session_storage', 'description': 'Store user session with generated IDs'}, {'operation': 'agent_execution_logging', 'description': 'Log agent execution with thread/run IDs'}, {'operation': 'websocket_connection_tracking', 'description': 'Track WebSocket connections with user mapping'}]
        for scenario in test_scenarios:
            try:
                user_id = UnifiedIdGenerator.generate_base_id('user')
                thread_id = UnifiedIDManager.generate_thread_id()
                run_id = UnifiedIDManager.generate_run_id(thread_id)
                request_id = UnifiedIdGenerator.generate_base_id('req')
                websocket_id = UnifiedIDManager().generate_websocket_id_with_user_context(user_id)
                db_ids = {'user_id': user_id, 'thread_id': thread_id, 'run_id': run_id, 'request_id': request_id, 'websocket_id': websocket_id}
                for id_type, id_value in db_ids.items():
                    if not self._is_unified_id_format(id_value):
                        database_consistency_issues.append({'scenario': scenario['operation'], 'id_type': id_type, 'id_value': id_value, 'issue': f'Database {id_type} not in unified format', 'impact': 'Query performance and indexing issues'})
                    if len(id_value) > 255:
                        database_consistency_issues.append({'scenario': scenario['operation'], 'id_type': id_type, 'id_value': id_value[:50] + '...', 'issue': f'ID too long for database storage: {len(id_value)} chars', 'impact': 'Database schema compatibility issues'})
                if not self._validate_id_relationships_for_db(user_id, thread_id, run_id, websocket_id):
                    database_consistency_issues.append({'scenario': scenario['operation'], 'id_type': 'id_relationships', 'id_value': f'user:{user_id[:20]}... -> thread:{thread_id[:20]}... -> run:{run_id[:20]}...', 'issue': 'ID relationships not queryable/parseable for database operations', 'impact': 'Complex queries and data consistency issues'})
            except Exception as e:
                database_consistency_issues.append({'scenario': scenario['operation'], 'id_type': 'generation_failure', 'id_value': 'N/A', 'issue': f'Database ID generation scenario failed: {e}', 'impact': 'Database operations unavailable'})
        try:
            parent_user_id = UnifiedIdGenerator.generate_base_id('user')
            child_thread_id = UnifiedIDManager.generate_thread_id()
            grandchild_run_id = UnifiedIDManager.generate_run_id(child_thread_id)
            if not self._would_foreign_key_work(parent_user_id, child_thread_id):
                database_consistency_issues.append({'scenario': 'foreign_key_validation', 'id_type': 'user_thread_fk', 'id_value': f'{parent_user_id} -> {child_thread_id}', 'issue': 'User to thread foreign key relationship format mismatch', 'impact': 'Database referential integrity issues'})
            if not self._would_foreign_key_work(child_thread_id, grandchild_run_id):
                database_consistency_issues.append({'scenario': 'foreign_key_validation', 'id_type': 'thread_run_fk', 'id_value': f'{child_thread_id} -> {grandchild_run_id}', 'issue': 'Thread to run foreign key relationship format mismatch', 'impact': 'Database referential integrity issues'})
        except Exception as e:
            database_consistency_issues.append({'scenario': 'foreign_key_validation', 'id_type': 'fk_test_failure', 'id_value': 'N/A', 'issue': f'Foreign key consistency test failed: {e}', 'impact': 'Database schema validation unavailable'})
        self.assertGreater(len(database_consistency_issues), 2, f'Expected >2 database consistency issues, found {len(database_consistency_issues)}. If this passes, database ID handling is already consistent!')
        report_lines = [f'DATABASE ID CONSISTENCY FAILURES: {len(database_consistency_issues)} issues', '🚨 BUSINESS IMPACT: Data integrity and query performance depend on consistent ID formats', '']
        for issue in database_consistency_issues[:10]:
            report_lines.extend([f"   🗄️ {issue['scenario']}.{issue['id_type']}", f"      Value: {issue['id_value'][:60]}...", f"      Issue: {issue['issue']}", f"      Impact: {issue['impact']}", ''])
        report_lines.extend(['🎯 DATABASE INTEGRATION MIGRATION REQUIRED:', '   - Standardize all database ID operations on UnifiedIdGenerator', '   - Update database schemas to handle unified ID formats', '   - Implement ID relationship validation for foreign keys', '   - Add database indexing optimized for structured ID patterns'])
        pytest.fail('\n'.join(report_lines))

    async def test_real_time_communication_id_routing_EXPECT_FAILURE(self):
        """
        EXPECTED FAILURE: Real-time communication routing uses inconsistent ID patterns.
        
        BUSINESS IMPACT: Agent-to-user communication (core platform value) depends on consistent routing.
        """
        rtc_routing_issues = []
        test_user_count = 3
        user_communication_contexts = []
        for user_num in range(test_user_count):
            try:
                user_id = UnifiedIdGenerator.generate_base_id(f'user_{user_num}')
                websocket_id = UnifiedIDManager().generate_websocket_id_with_user_context(user_id)
                thread_id = UnifiedIDManager.generate_thread_id()
                run_id = UnifiedIDManager.generate_run_id(thread_id)
                user_context = {'user_id': user_id, 'websocket_id': websocket_id, 'thread_id': thread_id, 'run_id': run_id, 'user_num': user_num}
                user_communication_contexts.append(user_context)
                routing_ids = [user_id, websocket_id, thread_id, run_id]
                for routing_id in routing_ids:
                    if not self._is_routable_id_format(routing_id):
                        rtc_routing_issues.append({'user_num': user_num, 'id_type': self._identify_id_type(routing_id), 'id_value': routing_id, 'issue': 'ID format not suitable for real-time routing', 'routing_impact': 'Message delivery failures'})
                for other_context in user_communication_contexts[:-1]:
                    if self._ids_could_cross_contaminate(user_context, other_context):
                        rtc_routing_issues.append({'user_num': user_num, 'id_type': 'isolation_violation', 'id_value': f"User {user_num} vs User {other_context['user_num']}", 'issue': 'ID patterns could cause cross-user message contamination', 'routing_impact': 'Security breach - messages sent to wrong users'})
            except Exception as e:
                rtc_routing_issues.append({'user_num': user_num, 'id_type': 'context_creation', 'id_value': 'N/A', 'issue': f'User communication context creation failed: {e}', 'routing_impact': 'User communication unavailable'})
        try:
            routing_table = {}
            for context in user_communication_contexts:
                routing_key = self._generate_routing_key(context['websocket_id'], context['thread_id'])
                if routing_key in routing_table:
                    rtc_routing_issues.append({'user_num': context['user_num'], 'id_type': 'routing_key_collision', 'id_value': routing_key, 'issue': 'Routing key collision between different users', 'routing_impact': 'Message delivery to wrong user'})
                else:
                    routing_table[routing_key] = context
                if not self._is_valid_routing_key_format(routing_key):
                    rtc_routing_issues.append({'user_num': context['user_num'], 'id_type': 'routing_key_format', 'id_value': routing_key, 'issue': 'Routing key format not optimized for lookup performance', 'routing_impact': 'Slow message routing, increased latency'})
        except Exception as e:
            rtc_routing_issues.append({'user_num': -1, 'id_type': 'routing_table_creation', 'id_value': 'N/A', 'issue': f'Routing table consistency test failed: {e}', 'routing_impact': 'Real-time communication system unavailable'})
        self.assertGreater(len(rtc_routing_issues), 1, f'Expected >1 real-time communication routing issue, found {len(rtc_routing_issues)}. If this passes, real-time routing is already consistent!')
        report_lines = [f'REAL-TIME COMMUNICATION ROUTING FAILURES: {len(rtc_routing_issues)} issues', '🚨 BUSINESS IMPACT: Agent-to-user communication is core platform value', '']
        for issue in rtc_routing_issues[:8]:
            report_lines.extend([f"   📡 User {issue['user_num']}: {issue['id_type']}", f"      Value: {issue['id_value'][:50]}...", f"      Issue: {issue['issue']}", f"      Routing Impact: {issue['routing_impact']}", ''])
        report_lines.extend(['🎯 REAL-TIME COMMUNICATION MIGRATION REQUIRED:', '   - Standardize routing ID formats for consistent lookup', '   - Implement cross-user isolation validation', '   - Optimize routing key generation for performance', '   - Test multi-user scenarios thoroughly'])
        pytest.fail('\n'.join(report_lines))

    def _is_unified_id_format(self, id_value: str) -> bool:
        """Check if ID follows UnifiedIdGenerator structured format."""
        import re
        pattern = re.compile('^[a-z_]+_\\d+_\\d+_[a-f0-9]{8}$')
        return pattern.match(id_value) is not None

    def _has_user_context_embedding(self, websocket_id: str, user_id: str) -> bool:
        """Check if WebSocket ID contains user context for routing."""
        user_parts = user_id.split('_')
        if len(user_parts) > 1:
            user_identifier = user_parts[1]
            return user_identifier in websocket_id
        return user_id[:8] in websocket_id

    def _validate_id_relationships_for_db(self, user_id: str, thread_id: str, run_id: str, websocket_id: str) -> bool:
        """Validate that ID relationships work for database queries."""
        try:
            extracted_thread = UnifiedIDManager.extract_thread_id(run_id)
            if extracted_thread != thread_id:
                return False
            id_formats = [self._get_id_format_structure(id_val) for id_val in [user_id, thread_id, run_id, websocket_id]]
            unique_formats = set(id_formats)
            return len(unique_formats) <= 2
        except:
            return False

    def _get_id_format_structure(self, id_value: str) -> str:
        """Get structural pattern of an ID for consistency checking."""
        parts = id_value.split('_')
        structure = []
        for part in parts:
            if part.isdigit():
                structure.append('NUM')
            elif len(part) == 8 and all((c in '0123456789abcdef' for c in part.lower())):
                structure.append('HEX8')
            else:
                structure.append('TEXT')
        return '_'.join(structure)

    def _would_foreign_key_work(self, parent_id: str, child_id: str) -> bool:
        """Check if parent-child ID relationship would work as foreign key."""
        parent_format = self._get_id_format_structure(parent_id)
        child_format = self._get_id_format_structure(child_id)
        return parent_format == child_format or abs(len(parent_format) - len(child_format)) <= 4

    def _is_routable_id_format(self, id_value: str) -> bool:
        """Check if ID format is suitable for real-time routing."""
        if len(id_value) > 100:
            return False
        if '_' not in id_value:
            return False
        parts = id_value.split('_')
        if len(parts) < 3:
            return False
        return True

    def _identify_id_type(self, id_value: str) -> str:
        """Identify the type of ID based on its content."""
        if id_value.startswith('user_'):
            return 'user_id'
        elif id_value.startswith('websocket_'):
            return 'websocket_id'
        elif id_value.startswith('thread_') or id_value.startswith('session_'):
            return 'thread_id'
        elif id_value.startswith('run_'):
            return 'run_id'
        elif id_value.startswith('req_'):
            return 'request_id'
        else:
            return 'unknown_id'

    def _ids_could_cross_contaminate(self, context1: dict, context2: dict) -> bool:
        """Check if two user contexts could cause cross-user contamination."""
        ids1 = set([context1['user_id'], context1['websocket_id'], context1['thread_id']])
        ids2 = set([context2['user_id'], context2['websocket_id'], context2['thread_id']])
        for id1 in ids1:
            for id2 in ids2:
                if self._ids_too_similar(id1, id2):
                    return True
        return False

    def _ids_too_similar(self, id1: str, id2: str) -> bool:
        """Check if two IDs are dangerously similar for routing."""
        parts1 = id1.split('_')
        parts2 = id2.split('_')
        if len(parts1) >= 2 and len(parts2) >= 2:
            if parts1[0] == parts2[0]:
                try:
                    if parts1[1].isdigit() and parts2[1].isdigit():
                        diff = abs(int(parts1[1]) - int(parts2[1]))
                        if diff < 1000:
                            return True
                except:
                    pass
        return False

    def _generate_routing_key(self, websocket_id: str, thread_id: str) -> str:
        """Generate routing key from WebSocket and thread IDs."""
        ws_parts = websocket_id.split('_')
        thread_parts = thread_id.split('_')
        ws_key = ws_parts[1] if len(ws_parts) > 1 else ws_parts[0]
        thread_key = thread_parts[1] if len(thread_parts) > 1 else thread_parts[0]
        return f'{ws_key}:{thread_key}'

    def _is_valid_routing_key_format(self, routing_key: str) -> bool:
        """Check if routing key format is optimized for lookup."""
        if len(routing_key) > 50:
            return False
        if ':' not in routing_key and '_' not in routing_key:
            return False
        unique_chars = len(set(routing_key))
        if unique_chars < 5:
            return False
        return True

    def tearDown(self):
        """Cleanup and summary after integration tests."""
        total_issues = len(self.service_integration_failures) + len(self.id_format_mismatches) + len(self.routing_consistency_issues)
        if total_issues > 0:
            print(f'\n🔗 INTEGRATION ISSUES: {total_issues} cross-service problems detected')
            print('🎯 Priority: Focus on service boundary ID format consistency')
        super().tearDown()
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')