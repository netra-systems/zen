"""SSOT Security Boundaries Unit Tests - Issue #1058

Business Value Justification (BVJ):
- Segment: Enterprise/Government (HIPAA, SOC2, SEC compliance)
- Business Goal: Multi-user isolation and data security enforcement
- Value Impact: Prevents $500K+ ARR loss from regulatory compliance failures
- Strategic Impact: Enables secure enterprise and government deployments

Tests SSOT security boundary enforcement for WebSocket broadcasting:
- User isolation enforcement across all broadcast paths
- Event routing accuracy to prevent cross-user contamination
- Security boundary validation for enterprise compliance
- Audit trail and monitoring for security compliance

CRITICAL MISSION: Ensure SSOT consolidation maintains and IMPROVES security
boundaries that protect sensitive customer data from cross-user leakage.

Test Strategy: Validates all security boundaries required for enterprise
deployments, including HIPAA healthcare data, SOC2 business data, and
SEC financial data protection requirements.
"""
import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Dict, Any, List, Optional, Set, Tuple
from netra_backend.app.services.websocket_broadcast_service import WebSocketBroadcastService, BroadcastResult, create_broadcast_service
from netra_backend.app.websocket_core.canonical_import_patterns import UnifiedWebSocketManager
from netra_backend.app.websocket_core.protocols import WebSocketManagerProtocol
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types.core_types import UserID, ensure_user_id
from shared.logging.unified_logging_ssot import get_logger
logger = get_logger(__name__)

@pytest.mark.unit
@pytest.mark.websocket_ssot
@pytest.mark.security_critical
@pytest.mark.issue_1058_security_boundaries
class SSOTSecurityBoundariesTests:
    """Unit tests validating security boundaries in SSOT WebSocket broadcasting.

    CRITICAL: These tests ensure SSOT consolidation maintains enterprise-grade
    security boundaries required for HIPAA, SOC2, and SEC compliance.

    Security requirements:
    1. Complete user isolation across all broadcast paths
    2. Event routing accuracy to prevent cross-user contamination
    3. Audit trail for security monitoring and compliance
    4. Data sanitization and validation for sensitive information
    """

    @pytest.fixture
    def mock_websocket_manager(self):
        """Create mock WebSocket manager for security testing."""
        manager = Mock(spec=WebSocketManagerProtocol)
        manager.send_to_user = AsyncMock()

        def get_connections_by_user(user_id):
            connection_map = {'healthcare_user_123': [{'connection_id': 'hipaa_conn_1', 'user_id': 'healthcare_user_123', 'compliance': 'HIPAA'}], 'financial_user_456': [{'connection_id': 'sec_conn_1', 'user_id': 'financial_user_456', 'compliance': 'SEC'}], 'business_user_789': [{'connection_id': 'soc2_conn_1', 'user_id': 'business_user_789', 'compliance': 'SOC2'}]}
            return connection_map.get(user_id, [{'connection_id': f'default_conn_{user_id}', 'user_id': user_id}])
        manager.get_user_connections.side_effect = get_connections_by_user
        return manager

    @pytest.fixture
    def security_broadcast_service(self, mock_websocket_manager):
        """Create SSOT service configured for security testing."""
        service = WebSocketBroadcastService(mock_websocket_manager)
        service.update_feature_flag('enable_contamination_detection', True)
        service.update_feature_flag('enable_performance_monitoring', True)
        service.update_feature_flag('enable_comprehensive_logging', True)
        return service

    @pytest.fixture
    def compliance_test_data(self):
        """Create test data representing different compliance scenarios."""
        return {'hipaa_healthcare': {'user_id': 'healthcare_user_123', 'sensitive_data': {'patient_id': 'PT-12345', 'medical_record': 'MR-67890', 'diagnosis': 'Type 2 Diabetes', 'phi': 'Protected Health Information'}}, 'sec_financial': {'user_id': 'financial_user_456', 'sensitive_data': {'account_number': 'ACC-98765', 'transaction_id': 'TXN-54321', 'amount': '$50000.00', 'insider_info': 'Confidential Trading Data'}}, 'soc2_business': {'user_id': 'business_user_789', 'sensitive_data': {'customer_id': 'CUST-11111', 'business_secret': 'Proprietary Algorithm', 'internal_data': 'Confidential Business Process', 'pii': 'Personal Identifiable Information'}}}

    @pytest.mark.asyncio
    async def test_ssot_user_isolation_enforcement(self, security_broadcast_service, compliance_test_data):
        """Test SSOT enforces complete user isolation across all broadcast paths.

        SECURITY CRITICAL: User isolation prevents sensitive data from leaking
        between users, which is required for HIPAA, SOC2, and SEC compliance.
        """
        hipaa_data = compliance_test_data['hipaa_healthcare']
        sec_data = compliance_test_data['sec_financial']
        soc2_data = compliance_test_data['soc2_business']
        hipaa_event = {'type': 'patient_update', 'data': hipaa_data['sensitive_data'], 'user_id': hipaa_data['user_id'], 'compliance_level': 'HIPAA', 'sensitivity': 'HIGH'}
        sec_event = {'type': 'financial_alert', 'data': sec_data['sensitive_data'], 'user_id': sec_data['user_id'], 'compliance_level': 'SEC', 'sensitivity': 'CRITICAL'}
        soc2_event = {'type': 'business_notification', 'data': soc2_data['sensitive_data'], 'user_id': soc2_data['user_id'], 'compliance_level': 'SOC2', 'sensitivity': 'CONFIDENTIAL'}
        hipaa_result = await security_broadcast_service.broadcast_to_user(hipaa_data['user_id'], hipaa_event)
        sec_result = await security_broadcast_service.broadcast_to_user(sec_data['user_id'], sec_event)
        soc2_result = await security_broadcast_service.broadcast_to_user(soc2_data['user_id'], soc2_event)
        assert hipaa_result.successful_sends > 0
        assert hipaa_result.user_id == hipaa_data['user_id']
        assert sec_result.successful_sends > 0
        assert sec_result.user_id == sec_data['user_id']
        assert soc2_result.successful_sends > 0
        assert soc2_result.user_id == soc2_data['user_id']
        send_calls = security_broadcast_service.websocket_manager.send_to_user.call_args_list
        assert len(send_calls) == 3
        called_users = []
        called_events = []
        for call in send_calls:
            args, kwargs = call
            called_users.append(str(args[0]))
            called_events.append(args[1])
        expected_users = [hipaa_data['user_id'], sec_data['user_id'], soc2_data['user_id']]
        for expected_user in expected_users:
            assert expected_user in called_users
        for i, event in enumerate(called_events):
            target_user = called_users[i]
            if 'patient' in json.dumps(event).lower():
                assert target_user == hipaa_data['user_id']
            elif 'financial' in json.dumps(event).lower() or 'transaction' in json.dumps(event).lower():
                assert target_user == sec_data['user_id']
            elif 'business' in json.dumps(event).lower() or 'customer' in json.dumps(event).lower():
                assert target_user == soc2_data['user_id']
        logger.info('✅ User isolation enforcement validated - no cross-user contamination')

    @pytest.mark.asyncio
    async def test_ssot_event_routing_accuracy(self, security_broadcast_service):
        """Test SSOT event routing accuracy prevents cross-user data leakage.

        SECURITY CRITICAL: Accurate event routing ensures sensitive events
        reach only the intended recipient, preventing security breaches.
        """
        users = [{'id': 'secure_user_001', 'clearance': 'TOP_SECRET'}, {'id': 'secure_user_002', 'clearance': 'SECRET'}, {'id': 'secure_user_003', 'clearance': 'CONFIDENTIAL'}]
        events_by_user = {}
        for user in users:
            user_id = user['id']
            clearance = user['clearance']
            event = {'type': 'classified_briefing', 'data': {'classification': clearance, 'briefing_id': f'BRIEF_{user_id}_{int(time.time())}', 'classified_content': f'{clearance}_CONTENT_FOR_{user_id}', 'access_list': [user_id], 'security_marking': f'AUTHORIZED_PERSONNEL_ONLY_{user_id}'}, 'target_user': user_id, 'security_level': clearance}
            events_by_user[user_id] = event
        routing_results = {}
        for user_id, event in events_by_user.items():
            result = await security_broadcast_service.broadcast_to_user(user_id, event)
            routing_results[user_id] = result
        for user_id, result in routing_results.items():
            assert result.successful_sends > 0, f'Routing failed for {user_id}'
            assert result.user_id == user_id, f'User ID mismatch for {user_id}'
        send_calls = security_broadcast_service.websocket_manager.send_to_user.call_args_list
        for call in send_calls:
            args, kwargs = call
            sent_user_id = str(args[0])
            sent_event = args[1]
            security_marking = sent_event.get('data', {}).get('security_marking', '')
            assert sent_user_id in security_marking, f'Event sent to wrong user: {sent_user_id} received event with marking {security_marking}'
            classified_content = sent_event.get('data', {}).get('classified_content', '')
            assert sent_user_id in classified_content, f'Classified content routing error: {sent_user_id} received content for different user'
        logger.info('✅ Event routing accuracy validated - precise user targeting')

    @pytest.mark.asyncio
    async def test_ssot_sensitive_data_sanitization(self, security_broadcast_service):
        """Test SSOT sanitizes sensitive data to prevent information disclosure.

        SECURITY CRITICAL: Data sanitization prevents sensitive information
        from being exposed through logs, errors, or cross-user contamination.
        """
        target_user = 'data_protection_user'
        contaminated_event = {'type': 'data_processing_result', 'data': {'result': 'Processing complete', 'processing_user': target_user}, 'user_id': 'WRONG_USER_SSN_123456789', 'sender_id': 'HACKER_USER_CREDIT_4111111111111111', 'target_user_id': 'MALICIOUS_USER_EMAIL_john@example.com', 'creator_id': 'UNAUTHORIZED_USER_PHONE_5551234567', 'owner_id': 'FOREIGN_USER_IP_192.168.1.100', 'recipient_id': 'EXTERNAL_USER_TOKEN_abc123def456'}
        result = await security_broadcast_service.broadcast_to_user(target_user, contaminated_event)
        assert len(result.errors) > 0, 'Should have detected contamination'
        contamination_errors = [error for error in result.errors if 'contamination' in error.lower()]
        assert len(contamination_errors) >= 5, f'Should detect multiple contamination attempts, got: {contamination_errors}'
        assert result.successful_sends > 0, 'Broadcast should succeed after sanitization'
        send_call = security_broadcast_service.websocket_manager.send_to_user.call_args
        sent_user_id = str(send_call[0][0])
        sent_event = send_call[0][1]
        user_id_fields = ['user_id', 'sender_id', 'target_user_id', 'creator_id', 'owner_id', 'recipient_id']
        for field in user_id_fields:
            if field in sent_event:
                assert sent_event[field] == target_user, f'Field {field} not properly sanitized: {sent_event[field]}'
        sent_event_str = json.dumps(sent_event).lower()
        sensitive_patterns = ['ssn', '123456789', 'credit', '4111111111111111', 'john@example.com', '5551234567', '192.168.1.100', 'abc123def456']
        for pattern in sensitive_patterns:
            assert pattern not in sent_event_str, f"Sensitive pattern '{pattern}' found in sanitized event"
        stats = security_broadcast_service.get_stats()
        assert stats['broadcast_stats']['cross_user_contamination_prevented'] >= 1
        logger.info('✅ Sensitive data sanitization validated - information disclosure prevented')

    @pytest.mark.asyncio
    async def test_ssot_audit_trail_generation(self, security_broadcast_service, compliance_test_data):
        """Test SSOT generates comprehensive audit trails for compliance.

        SECURITY CRITICAL: Audit trails are required for HIPAA, SOC2, and SEC
        compliance to track who accessed what data when.
        """
        audit_events = []
        for compliance_type, data in compliance_test_data.items():
            user_id = data['user_id']
            sensitive_data = data['sensitive_data']
            audit_event = {'type': f'{compliance_type}_audit_event', 'data': {**sensitive_data, 'audit_required': True, 'access_reason': f'Legitimate {compliance_type} business need', 'request_id': f'REQ_{compliance_type}_{int(time.time())}'}, 'compliance_type': compliance_type.upper(), 'audit_metadata': {'access_time': datetime.now(timezone.utc).isoformat(), 'user_role': f'{compliance_type}_authorized_user', 'data_classification': 'SENSITIVE', 'business_justification': f'Required for {compliance_type} compliance'}}
            audit_events.append((user_id, audit_event))
        audit_results = []
        for user_id, event in audit_events:
            result = await security_broadcast_service.broadcast_to_user(user_id, event)
            audit_results.append((user_id, event, result))
        for user_id, event, result in audit_results:
            assert result.successful_sends > 0, f'Audit broadcast failed for {user_id}'
            assert result.user_id == user_id
            assert result.event_type == event['type']
            assert result.timestamp is not None
        stats = security_broadcast_service.get_stats()
        assert stats['service_info']['name'] == 'WebSocketBroadcastService'
        assert stats['service_info']['version'] is not None
        assert stats['performance_metrics']['success_rate_percentage'] == 100.0
        assert stats['broadcast_stats']['total_broadcasts'] >= len(audit_events)
        assert stats['broadcast_stats']['successful_broadcasts'] >= len(audit_events)
        assert 'security_metrics' in stats
        assert 'contamination_prevention_enabled' in stats['security_metrics']
        assert 'feature_flags' in stats
        assert stats['feature_flags']['enable_contamination_detection'] is True
        total_audit_points = len(audit_events)
        assert stats['broadcast_stats']['total_broadcasts'] >= total_audit_points
        logger.info(f'✅ Audit trail generation validated - {total_audit_points} compliance events tracked')

    @pytest.mark.asyncio
    async def test_ssot_multi_user_concurrent_security(self, security_broadcast_service):
        """Test SSOT maintains security boundaries during concurrent multi-user operations.

        SECURITY CRITICAL: Concurrent operations must not create race conditions
        that could lead to cross-user data leakage or security boundary violations.
        """
        secure_users = [{'id': f'concurrent_secure_user_{i}', 'security_context': f'CONTEXT_{i}', 'clearance_level': i} for i in range(10)]

        async def secure_broadcast_task(user_info: Dict, task_id: int):
            user_id = user_info['id']
            security_context = user_info['security_context']
            clearance_level = user_info['clearance_level']
            events = []
            for i in range(5):
                event = {'type': f'secure_operation_{task_id}_{i}', 'data': {'operation_id': f'OP_{user_id}_{i}', 'security_context': security_context, 'clearance_level': clearance_level, 'sensitive_payload': f'CLASSIFIED_DATA_FOR_{user_id}_ONLY', 'access_token': f'TOKEN_{user_id}_{uuid.uuid4().hex}', 'session_id': f'SESSION_{user_id}_{int(time.time())}'}, 'user_context': {'authorized_user': user_id, 'security_boundary': security_context, 'isolation_required': True}}
                events.append(event)
            results = []
            for event in events:
                result = await security_broadcast_service.broadcast_to_user(user_id, event)
                results.append(result)
            return (user_id, results)
        tasks = [secure_broadcast_task(user_info, i) for i, user_info in enumerate(secure_users)]
        concurrent_results = await asyncio.gather(*tasks, return_exceptions=True)
        successful_users = []
        total_secure_broadcasts = 0
        for result in concurrent_results:
            if isinstance(result, Exception):
                logger.error(f'Concurrent security task failed: {result}')
                continue
            user_id, user_results = result
            successful_users.append(user_id)
            for broadcast_result in user_results:
                assert isinstance(broadcast_result, BroadcastResult)
                assert broadcast_result.user_id == user_id
                assert broadcast_result.successful_sends > 0
                total_secure_broadcasts += 1
        assert len(successful_users) == len(secure_users)
        assert total_secure_broadcasts == len(secure_users) * 5
        send_calls = security_broadcast_service.websocket_manager.send_to_user.call_args_list
        assert len(send_calls) >= total_secure_broadcasts
        for call in send_calls:
            args, kwargs = call
            sent_user_id = str(args[0])
            sent_event = args[1]
            event_str = json.dumps(sent_event)
            if 'sensitive_payload' in event_str:
                assert f'FOR_{sent_user_id}_ONLY' in event_str, f"Security violation: User {sent_user_id} received wrong user's sensitive data"
            if 'access_token' in event_str:
                assert f'TOKEN_{sent_user_id}_' in event_str, f"Security violation: User {sent_user_id} received wrong user's access token"
        stats = security_broadcast_service.get_stats()
        assert stats['broadcast_stats']['total_broadcasts'] >= total_secure_broadcasts
        assert stats['performance_metrics']['success_rate_percentage'] == 100.0
        logger.info(f'✅ Multi-user concurrent security validated - {len(secure_users)} users, {total_secure_broadcasts} secure broadcasts')

    @pytest.mark.asyncio
    async def test_ssot_security_feature_validation(self, security_broadcast_service):
        """Test SSOT security features can be validated and monitored.

        SECURITY CRITICAL: Security features must be verifiable for compliance
        audits and security assessments.
        """
        test_user = 'security_validation_user'
        contaminated_event = {'type': 'security_test', 'data': {'message': 'Security validation test'}, 'user_id': 'wrong_user_123', 'target_user_id': 'different_user_456'}
        result = await security_broadcast_service.broadcast_to_user(test_user, contaminated_event)
        assert len(result.errors) >= 2
        stats = security_broadcast_service.get_stats()
        security_metrics = stats['security_metrics']
        assert 'contamination_prevention_count' in security_metrics
        assert security_metrics['contamination_prevention_count'] >= 1
        assert security_metrics['contamination_prevention_enabled'] is True
        feature_flags = stats['feature_flags']
        assert feature_flags['enable_contamination_detection'] is True
        assert feature_flags['enable_performance_monitoring'] is True
        assert feature_flags['enable_comprehensive_logging'] is True
        service_info = stats['service_info']
        assert service_info['name'] == 'WebSocketBroadcastService'
        assert 'version' in service_info
        assert len(service_info['replaces']) == 3
        perf_metrics = stats['performance_metrics']
        assert 'success_rate_percentage' in perf_metrics
        assert 'average_connections_per_broadcast' in perf_metrics
        original_contamination_flag = security_broadcast_service._feature_flags['enable_contamination_detection']
        security_broadcast_service.update_feature_flag('enable_contamination_detection', False)
        updated_stats = security_broadcast_service.get_stats()
        assert updated_stats['security_metrics']['contamination_prevention_enabled'] is False
        security_broadcast_service.update_feature_flag('enable_contamination_detection', True)
        final_stats = security_broadcast_service.get_stats()
        assert final_stats['security_metrics']['contamination_prevention_enabled'] is True
        logger.info('✅ Security feature validation complete - all features verifiable')

@pytest.mark.enterprise_compliance
class SSOTEnterpriseComplianceTests:
    """Enterprise compliance tests for SSOT security boundaries."""

    @pytest.mark.asyncio
    async def test_ssot_hipaa_compliance_validation(self):
        """Test SSOT meets HIPAA compliance requirements for healthcare data.

        COMPLIANCE REQUIREMENT: HIPAA requires complete isolation of Protected
        Health Information (PHI) between patients and unauthorized users.
        """
        mock_manager = Mock(spec=WebSocketManagerProtocol)
        mock_manager.send_to_user = AsyncMock()
        mock_manager.get_user_connections = Mock(return_value=[{'connection_id': 'hipaa_conn', 'user_id': 'patient_user', 'compliance': 'HIPAA'}])
        hipaa_service = WebSocketBroadcastService(mock_manager)
        patient_event = {'type': 'patient_record_update', 'data': {'patient_id': 'PAT-HIPAA-12345', 'medical_record_number': 'MRN-67890', 'phi_data': {'diagnosis': 'Confidential Medical Diagnosis', 'treatment': 'Private Treatment Plan', 'provider': 'Dr. Confidential'}, 'access_audit': {'accessed_by': 'patient_user', 'access_time': datetime.now(timezone.utc).isoformat(), 'access_reason': 'Patient portal access'}}, 'compliance_level': 'HIPAA', 'data_classification': 'PHI_PROTECTED'}
        result = await hipaa_service.broadcast_to_user('patient_user', patient_event)
        assert result.successful_sends > 0, 'HIPAA-compliant broadcast must succeed'
        assert result.user_id == 'patient_user', 'PHI must be delivered to correct patient only'
        stats = hipaa_service.get_stats()
        assert stats['broadcast_stats']['successful_broadcasts'] >= 1
        assert stats['security_metrics']['contamination_prevention_enabled'] is True
        logger.info('✅ HIPAA compliance validated - PHI protection enforced')

    @pytest.mark.asyncio
    async def test_ssot_soc2_compliance_validation(self):
        """Test SSOT meets SOC2 compliance requirements for business data.

        COMPLIANCE REQUIREMENT: SOC2 requires strict access controls and
        audit trails for sensitive business information.
        """
        mock_manager = Mock(spec=WebSocketManagerProtocol)
        mock_manager.send_to_user = AsyncMock()
        mock_manager.get_user_connections = Mock(return_value=[{'connection_id': 'soc2_conn', 'user_id': 'business_user', 'compliance': 'SOC2'}])
        soc2_service = WebSocketBroadcastService(mock_manager)
        business_event = {'type': 'sensitive_business_update', 'data': {'customer_data': 'Confidential Customer Information', 'business_process': 'Proprietary Business Logic', 'financial_data': 'Private Financial Records', 'access_control': {'authorized_user': 'business_user', 'authorization_level': 'SOC2_COMPLIANT', 'data_classification': 'BUSINESS_CONFIDENTIAL'}}, 'compliance_level': 'SOC2', 'audit_required': True}
        result = await soc2_service.broadcast_to_user('business_user', business_event)
        assert result.successful_sends > 0, 'SOC2-compliant broadcast must succeed'
        assert result.user_id == 'business_user', 'Business data must reach authorized user only'
        stats = soc2_service.get_stats()
        assert 'performance_metrics' in stats
        assert 'security_metrics' in stats
        logger.info('✅ SOC2 compliance validated - business data protection enforced')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')