"""SSOT WebSocket Data Integrity Preservation Unit Tests - Issue #1058 Validation

Business Value Justification (BVJ):
- Segment: Enterprise/Platform (HIPAA, SOC2, SEC compliance)
- Business Goal: Data integrity and audit trail preservation
- Value Impact: Ensures event data provenance preserved while preventing security violations
- Strategic Impact: Enables regulatory compliance through proper data handling

Tests validate the critical distinction between:
1. EVENT DATA (provenance/context) - MUST be preserved for audit trails
2. ROUTING DATA (targeting/delivery) - MUST be sanitized for security

CRITICAL MISSION: These tests validate that the completed Issue #1058 SSOT implementation
correctly handles data integrity while preventing cross-user contamination.

Test Strategy: Validates data integrity preservation principles in the working SSOT
WebSocketBroadcastService._prevent_cross_user_contamination method.
"""

import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any, List

from netra_backend.app.services.websocket_broadcast_service import (
    WebSocketBroadcastService,
    BroadcastResult,
    create_broadcast_service
)
from netra_backend.app.websocket_core.protocols import WebSocketManagerProtocol
from shared.types.core_types import UserID, ensure_user_id
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


@pytest.mark.unit
@pytest.mark.websocket_ssot
@pytest.mark.issue_1058_data_integrity
class TestSSOTDataIntegrityPreservation:
    """Unit tests validating data integrity preservation in SSOT consolidation.

    CRITICAL: These tests validate that Issue #1058 SSOT implementation correctly
    distinguishes between event data (preserve) and routing data (sanitize).

    Tests validate the working implementation maintains regulatory compliance
    through proper data handling principles.
    """

    @pytest.fixture
    def mock_websocket_manager(self):
        """Create mock WebSocket manager for data integrity testing."""
        manager = Mock(spec=WebSocketManagerProtocol)
        manager.send_to_user = AsyncMock()
        manager.get_user_connections = Mock(return_value=[
            {'connection_id': 'conn_1', 'user_id': 'target_user_123'}
        ])
        return manager

    @pytest.fixture
    def ssot_broadcast_service(self, mock_websocket_manager):
        """Create SSOT broadcast service instance for testing."""
        return WebSocketBroadcastService(mock_websocket_manager)

    @pytest.fixture
    def event_with_provenance_data(self):
        """Create event with provenance fields that should be preserved."""
        return {
            'type': 'agent_completed',
            'data': {
                'message': 'Analysis complete',
                'agent_id': 'cost_optimizer_456',
                'timestamp': datetime.now(timezone.utc).isoformat()
            },
            # PROVENANCE DATA - MUST be preserved for audit trails
            'user_id': 'original_user_789',      # Event creator - preserve
            'sender_id': 'agent_sender_999',     # Message sender - preserve
            'creator_id': 'content_creator_111', # Content creator - preserve
            'owner_id': 'resource_owner_222',    # Resource owner - preserve
            # ROUTING DATA - SHOULD be sanitized for security
            'recipient_id': 'wrong_recipient_333',  # Message recipient - sanitize
            'target_user_id': 'wrong_target_444',   # Explicit target - sanitize
            'userId': 'legacy_user_555',            # Legacy recipient - sanitize
            'thread_id': 'thread_666'
        }

    @pytest.mark.asyncio
    async def test_event_data_preservation_vs_routing_data(
        self,
        ssot_broadcast_service,
        event_with_provenance_data
    ):
        """Test SSOT preserves event data while sanitizing routing data.

        ISSUE #1058 VALIDATION: This test validates the working implementation
        correctly distinguishes between data types for regulatory compliance.

        Event data (provenance) MUST be preserved for audit trails.
        Routing data (targeting) MUST be sanitized for security.
        """
        target_user_id = 'compliance_user_123'

        # Execute SSOT broadcast
        result = await ssot_broadcast_service.broadcast_to_user(
            target_user_id,
            event_with_provenance_data
        )

        # Validate broadcast succeeded
        assert isinstance(result, BroadcastResult)
        assert result.is_successful
        assert result.user_id == target_user_id

        # Validate the event sent to WebSocket manager
        ssot_broadcast_service.websocket_manager.send_to_user.assert_called_once()
        call_args = ssot_broadcast_service.websocket_manager.send_to_user.call_args
        sent_user_id = call_args[0][0]
        sent_event = call_args[0][1]

        assert sent_user_id == ensure_user_id(target_user_id)

        # CRITICAL: Validate PROVENANCE DATA preserved (audit trail compliance)
        assert sent_event['user_id'] == 'original_user_789'        # Event creator preserved
        assert sent_event['sender_id'] == 'agent_sender_999'       # Sender preserved
        assert sent_event['creator_id'] == 'content_creator_111'   # Creator preserved
        assert sent_event['owner_id'] == 'resource_owner_222'      # Owner preserved

        # CRITICAL: Validate ROUTING DATA sanitized (security compliance)
        assert sent_event['target_user_id'] == target_user_id      # Target sanitized
        assert sent_event['userId'] == target_user_id              # Legacy field sanitized

        # Validate contamination detection recorded the routing violations
        assert len(result.errors) >= 2  # At least recipient_id and target_user_id violations
        contamination_errors = [err for err in result.errors if 'contamination' in err.lower()]
        assert len(contamination_errors) >= 2

        logger.info('✅ Event data preservation vs routing data sanitization validated')
        logger.info(f'📊 Provenance fields preserved: user_id, sender_id, creator_id, owner_id')
        logger.info(f'🔒 Routing fields sanitized: target_user_id, userId')

    @pytest.mark.asyncio
    async def test_provenance_fields_preservation(self, ssot_broadcast_service):
        """Test SSOT preserves all provenance fields for regulatory compliance.

        ISSUE #1058 VALIDATION: Validates working implementation preserves
        all fields required for HIPAA, SOC2, SEC audit trails.
        """
        target_user_id = 'audit_user_456'

        # Event with comprehensive provenance data
        provenance_event = {
            'type': 'financial_analysis',
            'data': {'analysis': 'Cost optimization complete', 'savings': 15000},
            'user_id': 'financial_analyst_789',     # WHO created the analysis
            'sender_id': 'trading_system_999',      # WHAT system sent it
            'creator_id': 'ai_agent_111',           # WHICH agent created content
            'owner_id': 'enterprise_account_222',   # WHO owns the resource
            'source_system': 'apex_optimizer',      # WHERE it came from
            'audit_trail': 'compliance_required',   # WHY preservation needed
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        result = await ssot_broadcast_service.broadcast_to_user(target_user_id, provenance_event)

        # Validate successful broadcast
        assert result.is_successful

        # Get the sent event
        call_args = ssot_broadcast_service.websocket_manager.send_to_user.call_args
        sent_event = call_args[0][1]

        # CRITICAL: All provenance fields must be preserved exactly
        provenance_fields = ['user_id', 'sender_id', 'creator_id', 'owner_id']
        for field in provenance_fields:
            original_value = provenance_event[field]
            preserved_value = sent_event[field]
            assert preserved_value == original_value, (
                f"Provenance field '{field}' not preserved: "
                f"expected '{original_value}', got '{preserved_value}'"
            )

        # Additional audit fields should also be preserved
        assert sent_event['source_system'] == 'apex_optimizer'
        assert sent_event['audit_trail'] == 'compliance_required'

        logger.info('✅ All provenance fields preserved for regulatory compliance')
        logger.info(f'📋 Preserved fields: {provenance_fields + ["source_system", "audit_trail"]}')

    @pytest.mark.asyncio
    async def test_routing_fields_sanitization(self, ssot_broadcast_service):
        """Test SSOT sanitizes routing fields for security compliance.

        ISSUE #1058 VALIDATION: Validates working implementation properly
        sanitizes all routing/targeting fields to prevent security violations.
        """
        target_user_id = 'secure_user_789'

        # Event with potentially dangerous routing data
        routing_event = {
            'type': 'security_alert',
            'data': {'alert': 'Unauthorized access attempt'},
            'user_id': 'security_analyst_123',      # Provenance - preserve
            'recipient_id': 'attacker_user_999',    # Routing - sanitize
            'target_user_id': 'victim_user_888',    # Routing - sanitize
            'userId': 'legacy_target_777',          # Routing - sanitize
            'delivery_target': 'wrong_user_666',    # Custom routing - should be handled
            'thread_id': 'security_thread_555'
        }

        result = await ssot_broadcast_service.broadcast_to_user(target_user_id, routing_event)

        # Validate successful broadcast with contamination detection
        assert result.is_successful
        assert len(result.errors) >= 3  # Multiple routing field violations expected

        # Get the sent event
        call_args = ssot_broadcast_service.websocket_manager.send_to_user.call_args
        sent_event = call_args[0][1]

        # CRITICAL: User provenance preserved (security context)
        assert sent_event['user_id'] == 'security_analyst_123'  # Analyst identity preserved

        # CRITICAL: All routing fields sanitized to target user
        routing_fields = ['target_user_id', 'userId']
        for field in routing_fields:
            if field in sent_event:
                sanitized_value = sent_event[field]
                assert sanitized_value == target_user_id, (
                    f"Routing field '{field}' not sanitized: "
                    f"expected '{target_user_id}', got '{sanitized_value}'"
                )

        # Validate contamination detection logged the security violations
        contamination_errors = [err for err in result.errors if 'contamination' in err.lower()]
        routing_violations = [err for err in contamination_errors if any(
            field in err for field in ['recipient_id', 'target_user_id', 'userId']
        )]
        assert len(routing_violations) >= 3

        logger.info('✅ Routing fields properly sanitized for security compliance')
        logger.info(f'🔒 Sanitized fields: {routing_fields}')
        logger.info(f'🚨 Contamination violations detected: {len(routing_violations)}')

    @pytest.mark.asyncio
    async def test_contamination_detection_accuracy(self, ssot_broadcast_service):
        """Test SSOT contamination detection accurately identifies violations.

        ISSUE #1058 VALIDATION: Validates working implementation accurately
        detects contamination without false positives or missed violations.
        """
        target_user_id = 'detection_user_123'

        # Clean event - no contamination expected
        clean_event = {
            'type': 'clean_message',
            'data': {'message': 'This is a clean event'},
            'user_id': target_user_id,        # Same as target - no violation
            'thread_id': 'clean_thread_456'
        }

        clean_result = await ssot_broadcast_service.broadcast_to_user(target_user_id, clean_event)

        # Clean event should have no contamination errors
        assert clean_result.is_successful
        contamination_clean = [err for err in clean_result.errors if 'contamination' in err.lower()]
        assert len(contamination_clean) == 0, f"False positive contamination detected: {contamination_clean}"

        # Contaminated event - violations expected
        contaminated_event = {
            'type': 'contaminated_message',
            'data': {'message': 'This event has routing violations'},
            'user_id': 'event_creator_789',           # Different from target - OK (provenance)
            'recipient_id': 'wrong_recipient_999',    # Different from target - VIOLATION
            'target_user_id': 'wrong_target_888',     # Different from target - VIOLATION
            'userId': 'legacy_wrong_777',             # Different from target - VIOLATION
            'thread_id': 'contaminated_thread_666'
        }

        contaminated_result = await ssot_broadcast_service.broadcast_to_user(
            target_user_id,
            contaminated_event
        )

        # Contaminated event should detect exactly 3 routing violations
        assert contaminated_result.is_successful  # Still broadcasts, but with warnings
        contamination_violations = [
            err for err in contaminated_result.errors
            if 'contamination' in err.lower()
        ]
        assert len(contamination_violations) >= 3, (
            f"Expected at least 3 contamination violations, got {len(contamination_violations)}: "
            f"{contamination_violations}"
        )

        # Validate specific violations detected
        violation_text = ' '.join(contamination_violations).lower()
        assert 'recipient_id' in violation_text
        assert 'target_user_id' in violation_text
        assert 'userid' in violation_text

        logger.info('✅ Contamination detection accuracy validated')
        logger.info(f'🧹 Clean events: 0 false positives')
        logger.info(f'🚨 Contaminated events: {len(contamination_violations)} violations detected')

    @pytest.mark.asyncio
    async def test_enterprise_compliance_data_handling(self, ssot_broadcast_service):
        """Test SSOT data handling meets enterprise compliance requirements.

        ISSUE #1058 VALIDATION: Validates working implementation provides
        enterprise-grade data handling for HIPAA, SOC2, SEC compliance.
        """
        target_user_id = 'enterprise_user_456'

        # Enterprise compliance scenario: healthcare data analysis
        healthcare_event = {
            'type': 'healthcare_analysis_complete',
            'data': {
                'analysis_id': 'HIPAA_PROTECTED_789',
                'patient_insights': 'Cost optimization for patient care',
                'compliance_level': 'HIPAA_PHI'
            },
            'user_id': 'healthcare_analyst_123',        # Doctor who created - MUST preserve
            'sender_id': 'medical_ai_system_999',       # AI system - MUST preserve
            'creator_id': 'healthcare_ai_agent_111',    # AI agent - MUST preserve
            'owner_id': 'hospital_system_222',          # Hospital - MUST preserve
            'recipient_id': 'wrong_doctor_888',         # Wrong recipient - MUST sanitize
            'target_user_id': 'wrong_patient_777',      # Wrong patient - MUST sanitize
            'hipaa_tracking_id': 'AUDIT_TRAIL_333',    # Audit trail - MUST preserve
            'compliance_officer': 'officer_444',        # Compliance - MUST preserve
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        result = await ssot_broadcast_service.broadcast_to_user(target_user_id, healthcare_event)

        # Validate enterprise-grade handling
        assert result.is_successful

        # Get the processed event
        call_args = ssot_broadcast_service.websocket_manager.send_to_user.call_args
        sent_event = call_args[0][1]

        # HIPAA COMPLIANCE: All provenance preserved for audit trails
        assert sent_event['user_id'] == 'healthcare_analyst_123'     # Doctor preserved
        assert sent_event['sender_id'] == 'medical_ai_system_999'    # System preserved
        assert sent_event['creator_id'] == 'healthcare_ai_agent_111' # Agent preserved
        assert sent_event['owner_id'] == 'hospital_system_222'       # Hospital preserved
        assert sent_event['hipaa_tracking_id'] == 'AUDIT_TRAIL_333'  # Audit preserved
        assert sent_event['compliance_officer'] == 'officer_444'     # Officer preserved

        # SECURITY COMPLIANCE: Routing fields sanitized
        assert sent_event['target_user_id'] == target_user_id  # Target sanitized

        # Validate contamination detection for enterprise security
        contamination_errors = [err for err in result.errors if 'contamination' in err.lower()]
        assert len(contamination_errors) >= 2  # recipient_id and target_user_id violations

        # Validate statistics tracking for compliance reporting
        stats = ssot_broadcast_service.get_stats()
        assert stats['broadcast_stats']['cross_user_contamination_prevented'] >= 1
        assert stats['security_metrics']['contamination_prevention_enabled'] is True

        logger.info('✅ Enterprise compliance data handling validated')
        logger.info('🏥 HIPAA: All provenance data preserved for audit trails')
        logger.info('🔒 Security: Routing data sanitized to prevent violations')
        logger.info('📊 Compliance: Statistics tracked for regulatory reporting')

    def test_ssot_data_integrity_principles_documentation(self, ssot_broadcast_service):
        """Test SSOT service properly documents data integrity principles.

        ISSUE #1058 VALIDATION: Validates working implementation correctly
        identifies and documents data handling principles for compliance.
        """
        stats = ssot_broadcast_service.get_stats()
        service_info = stats['service_info']

        # Validate service properly identifies its purpose
        assert service_info['name'] == 'WebSocketBroadcastService'
        assert 'SSOT consolidation' in service_info['purpose']

        # Validate security features documented
        security_metrics = stats['security_metrics']
        assert 'contamination_prevention_enabled' in security_metrics
        assert security_metrics['contamination_prevention_enabled'] is True

        # Validate the service identifies what it replaces
        replaced_implementations = service_info['replaces']
        expected_replacements = [
            'WebSocketEventRouter.broadcast_to_user',
            'UserScopedWebSocketEventRouter.broadcast_to_user',
            'broadcast_user_event'
        ]

        for expected in expected_replacements:
            assert expected in replaced_implementations, (
                f"Missing expected replacement: {expected}"
            )

        logger.info('✅ SSOT service properly documents data integrity principles')
        logger.info(f'📋 Service: {service_info["name"]}')
        logger.info(f'🎯 Purpose: {service_info["purpose"]}')
        logger.info(f'🔄 Replaces: {len(replaced_implementations)} legacy implementations')


if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --test-file netra_backend/tests/unit/websocket_core/test_ssot_data_integrity_preservation.py')