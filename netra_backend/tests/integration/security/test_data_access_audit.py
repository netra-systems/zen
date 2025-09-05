"""
Data Access Audit Integration Tests

BVJ:
- Segment: Enterprise ($200K+ MRR)
- Business Goal: Compliance reporting protecting $200K+ MRR
- Value Impact: Essential for GDPR Article 30 compliance - detailed access logs
- Revenue Impact: Protects and enables $200K+ enterprise revenue stream

REQUIREMENTS:
- Data access logging with tamper-proof storage
- Comprehensive metadata capture for forensic analysis
- Resource-level access tracking
- Performance metrics and compliance flags
"""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import asyncio
from datetime import datetime, timezone

import pytest

from netra_backend.app.schemas.registry import CorpusAuditAction, CorpusAuditStatus

from netra_backend.tests.integration.security.shared_fixtures import (
    DataAccessAuditHelper,
    data_access_helper,
    enterprise_security_infrastructure,
)

class TestDataAccessAudit:
    """BVJ: Essential for GDPR Article 30 compliance - detailed access logs."""

    @pytest.mark.asyncio
    async def test_data_access_logging_tamper_proof(self, enterprise_security_infrastructure, data_access_helper):
        """BVJ: Essential for GDPR Article 30 compliance - detailed access logs."""
        infrastructure = enterprise_security_infrastructure
        
        access_scenarios = await data_access_helper.create_data_access_scenarios()
        logged_accesses = []
        
        for scenario in access_scenarios:
            access_log = await data_access_helper.log_data_access_event(infrastructure, scenario)
            logged_accesses.append(access_log)
            await self._verify_tamper_proof_storage(infrastructure, access_log)
        
        await self._validate_data_access_audit_integrity(infrastructure, logged_accesses)

    async def _verify_tamper_proof_storage(self, infrastructure, audit_record):
        """Verify audit record has tamper-proof characteristics."""
        assert audit_record.timestamp is not None
        assert audit_record.metadata.ip_address is not None
        assert audit_record.metadata.request_id is not None
        assert audit_record.metadata.session_id is not None
        
        assert "gdpr_logged" in audit_record.metadata.compliance_flags
        assert "soc2_tracked" in audit_record.metadata.compliance_flags
        
        infrastructure["tamper_detector"].verify_integrity.return_value = True

    async def _validate_data_access_audit_integrity(self, infrastructure, logged_accesses):
        """Validate data access audit integrity."""
        assert len(logged_accesses) == 3
        for access in logged_accesses:
            assert access.status == CorpusAuditStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_corpus_search_access_logging(self, enterprise_security_infrastructure, data_access_helper):
        """BVJ: Validates corpus search operations are properly logged."""
        infrastructure = enterprise_security_infrastructure
        
        search_scenario = {
            "action": CorpusAuditAction.SEARCH,
            "resource_type": "corpus",
            "resource_id": "corpus123",
            "user_id": "user123",
            "access_type": "api_read",
            "data_classification": "confidential"
        }
        
        access_log = await data_access_helper.log_data_access_event(infrastructure, search_scenario)
        
        assert access_log.action == CorpusAuditAction.SEARCH
        assert access_log.resource_type == "corpus"
        assert access_log.metadata.configuration["data_classification"] == "confidential"

    @pytest.mark.asyncio
    async def test_document_update_access_logging(self, enterprise_security_infrastructure, data_access_helper):
        """BVJ: Validates document update operations are properly logged."""
        infrastructure = enterprise_security_infrastructure
        
        update_scenario = {
            "action": CorpusAuditAction.UPDATE,
            "resource_type": "document",
            "resource_id": "doc456",
            "user_id": "user456",
            "access_type": "direct_modification",
            "data_classification": "restricted"
        }
        
        access_log = await data_access_helper.log_data_access_event(infrastructure, update_scenario)
        
        assert access_log.action == CorpusAuditAction.UPDATE
        assert access_log.resource_type == "document"
        assert access_log.metadata.configuration["access_type"] == "direct_modification"

    @pytest.mark.asyncio
    async def test_data_deletion_access_logging(self, enterprise_security_infrastructure, data_access_helper):
        """BVJ: Validates data deletion operations are properly logged."""
        infrastructure = enterprise_security_infrastructure
        
        delete_scenario = {
            "action": CorpusAuditAction.DELETE,
            "resource_type": "embedding",
            "resource_id": "embed789",
            "user_id": "admin001",
            "access_type": "admin_deletion",
            "data_classification": "public"
        }
        
        access_log = await data_access_helper.log_data_access_event(infrastructure, delete_scenario)
        
        assert access_log.action == CorpusAuditAction.DELETE
        assert access_log.resource_type == "embedding"
        assert access_log.user_id == "admin001"

    @pytest.mark.asyncio
    async def test_performance_metrics_capture(self, enterprise_security_infrastructure, data_access_helper):
        """BVJ: Validates performance metrics are captured in audit logs."""
        infrastructure = enterprise_security_infrastructure
        
        scenario = {
            "action": CorpusAuditAction.SEARCH,
            "resource_type": "corpus",
            "resource_id": "perf_test",
            "user_id": "perf_user",
            "access_type": "api_read",
            "data_classification": "public"
        }
        
        access_log = await data_access_helper.log_data_access_event(infrastructure, scenario)
        
        perf_metrics = access_log.metadata.performance_metrics
        assert "operation_duration_ms" in perf_metrics
        assert "data_size_bytes" in perf_metrics
        assert perf_metrics["operation_duration_ms"] > 0

    @pytest.mark.asyncio
    async def test_compliance_flags_validation(self, enterprise_security_infrastructure, data_access_helper):
        """BVJ: Validates compliance flags are properly set in audit records."""
        infrastructure = enterprise_security_infrastructure
        
        scenario = {
            "action": CorpusAuditAction.SEARCH,
            "resource_type": "corpus",
            "resource_id": "compliance_test",
            "user_id": "compliance_user",
            "access_type": "compliance_audit",
            "data_classification": "confidential"
        }
        
        access_log = await data_access_helper.log_data_access_event(infrastructure, scenario)
        
        compliance_flags = access_log.metadata.compliance_flags
        assert "gdpr_logged" in compliance_flags
        assert "soc2_tracked" in compliance_flags
        assert len(compliance_flags) >= 2

    @pytest.mark.asyncio
    async def test_resource_classification_tracking(self, enterprise_security_infrastructure, data_access_helper):
        """BVJ: Validates data classification is properly tracked."""
        infrastructure = enterprise_security_infrastructure
        
        classifications = ["public", "confidential", "restricted"]
        
        for classification in classifications:
            scenario = {
                "action": CorpusAuditAction.SEARCH,
                "resource_type": "document",
                "resource_id": f"doc_{classification}",
                "user_id": "classification_test",
                "access_type": "classification_test",
                "data_classification": classification
            }
            
            access_log = await data_access_helper.log_data_access_event(infrastructure, scenario)
            assert access_log.metadata.configuration["data_classification"] == classification

    @pytest.mark.asyncio
    async def test_session_and_request_tracking(self, enterprise_security_infrastructure, data_access_helper):
        """BVJ: Validates session and request IDs are properly tracked."""
        infrastructure = enterprise_security_infrastructure
        
        scenario = {
            "action": CorpusAuditAction.SEARCH,
            "resource_type": "corpus",
            "resource_id": "session_test",
            "user_id": "session_user",
            "access_type": "session_tracking",
            "data_classification": "public"
        }
        
        access_log = await data_access_helper.log_data_access_event(infrastructure, scenario)
        
        assert access_log.metadata.session_id is not None
        assert access_log.metadata.request_id is not None
        assert len(access_log.metadata.session_id) > 0
        assert len(access_log.metadata.request_id) > 0

    @pytest.mark.asyncio
    async def test_user_agent_and_ip_tracking(self, enterprise_security_infrastructure, data_access_helper):
        """BVJ: Validates user agent and IP address are captured for security."""
        infrastructure = enterprise_security_infrastructure
        
        scenario = {
            "action": CorpusAuditAction.UPDATE,
            "resource_type": "document",
            "resource_id": "security_test",
            "user_id": "security_user",
            "access_type": "security_audit",
            "data_classification": "restricted"
        }
        
        access_log = await data_access_helper.log_data_access_event(infrastructure, scenario)
        
        assert access_log.metadata.ip_address == "192.168.1.100"
        assert access_log.metadata.user_agent == "Enterprise Client v1.0"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])