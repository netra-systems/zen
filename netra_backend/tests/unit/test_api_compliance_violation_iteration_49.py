import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from netra_backend.app.core.compliance_manager import ComplianceManager
from netra_backend.app.core.audit_logger import AuditLogger
from netra_backend.app.core.privacy_controller import PrivacyController


class TestAPIComplianceViolation:
    """Test API compliance violation prevention - Iteration 49
    
    Business Value: Prevents $200K/month losses from compliance violations
    Ensures GDPR, HIPAA, SOX, and other regulatory compliance
    """

    @pytest.fixture
    def compliance_manager(self):
        return ComplianceManager()

    @pytest.fixture
    def audit_logger(self):
        return AuditLogger()

    @pytest.fixture
    def privacy_controller(self):
        return PrivacyController()

    @pytest.mark.asyncio
    async def test_gdpr_data_processing_consent_validation(self, compliance_manager):
        """Test GDPR consent validation for data processing"""
        user_id = 123
        processing_purpose = "marketing_analytics"
        
        # No consent should block processing
        consent_status = await compliance_manager.check_gdpr_consent(
            user_id, processing_purpose
        )
        assert not consent_status["has_consent"]
        
        with pytest.raises(ValueError, match="GDPR consent required"):
            await compliance_manager.process_personal_data(
                user_id, {"email": "user@example.com"}, processing_purpose
            )
        
        # Valid consent should allow processing
        await compliance_manager.record_gdpr_consent(
            user_id, processing_purpose, consent_timestamp=datetime.now()
        )
        
        consent_status = await compliance_manager.check_gdpr_consent(
            user_id, processing_purpose
        )
        assert consent_status["has_consent"]
        
        # Processing should succeed with consent
        processing_result = await compliance_manager.process_personal_data(
            user_id, {"email": "user@example.com"}, processing_purpose
        )
        assert processing_result["processed"] is True

    @pytest.mark.asyncio
    async def test_data_retention_policy_enforcement(self, compliance_manager):
        """Test enforcement of data retention policies"""
        # Data older than retention period should be flagged
        old_data = {
            "user_id": 456,
            "data_type": "user_activity_logs",
            "created_at": datetime.now() - timedelta(days=2555),  # 7+ years old
            "retention_period_days": 2555  # 7 years
        }
        
        retention_status = await compliance_manager.check_data_retention(old_data)
        assert retention_status["should_delete"] is True
        assert retention_status["days_overdue"] > 0
        
        # Recent data should be retained
        recent_data = old_data.copy()
        recent_data["created_at"] = datetime.now() - timedelta(days=30)
        
        retention_status = await compliance_manager.check_data_retention(recent_data)
        assert retention_status["should_delete"] is False

    @pytest.mark.asyncio
    async def test_hipaa_phi_access_controls(self, compliance_manager):
        """Test HIPAA PHI access controls"""
        phi_data = {
            "patient_id": "P123456",
            "medical_record_number": "MR789012",
            "diagnosis": "Type 2 Diabetes",
            "treatment_plan": "Insulin therapy"
        }
        
        # Unauthorized user should not access PHI
        unauthorized_user = {"user_id": 999, "role": "marketing", "clearance": "none"}
        
        with pytest.raises(ValueError, match="HIPAA violation: Unauthorized PHI access"):
            await compliance_manager.access_phi_data(
                phi_data, accessing_user=unauthorized_user
            )
        
        # Authorized healthcare provider should access PHI
        authorized_user = {"user_id": 123, "role": "physician", "clearance": "phi_access"}
        
        access_result = await compliance_manager.access_phi_data(
            phi_data, accessing_user=authorized_user
        )
        assert access_result["access_granted"] is True
        
        # Access should be logged for audit
        audit_entry = access_result["audit_entry"]
        assert audit_entry["user_id"] == 123
        assert audit_entry["data_accessed"] == "phi"
        assert "patient_id" in audit_entry["metadata"]

    @pytest.mark.asyncio
    async def test_sox_financial_data_controls(self, compliance_manager, audit_logger):
        """Test SOX controls for financial data"""
        financial_transaction = {
            "transaction_id": "TXN123456",
            "amount": 50000.00,
            "account_number": "ACC789012",
            "transaction_type": "wire_transfer"
        }
        
        # Financial transaction should require dual authorization
        single_approval = [{"approver_id": 123, "role": "manager"}]
        
        with pytest.raises(ValueError, match="SOX compliance: Dual authorization required"):
            await compliance_manager.process_financial_transaction(
                financial_transaction, approvals=single_approval
            )
        
        # Dual authorization should allow processing
        dual_approvals = [
            {"approver_id": 123, "role": "manager"},
            {"approver_id": 456, "role": "director"}
        ]
        
        processing_result = await compliance_manager.process_financial_transaction(
            financial_transaction, approvals=dual_approvals
        )
        assert processing_result["processed"] is True
        
        # Should create immutable audit trail
        audit_records = await audit_logger.get_transaction_audit_trail(
            financial_transaction["transaction_id"]
        )
        assert len(audit_records) >= 2  # At least dual approval records
        assert any(record["action"] == "dual_authorization_verified" for record in audit_records)

    @pytest.mark.asyncio
    async def test_pci_dss_payment_data_handling(self, compliance_manager):
        """Test PCI DSS compliance for payment data handling"""
        payment_data = {
            "card_number": "4111111111111111",
            "cvv": "123",
            "expiry_date": "12/25",
            "cardholder_name": "John Doe"
        }
        
        # Raw payment data should not be stored
        with pytest.raises(ValueError, match="PCI DSS violation: Raw payment data storage prohibited"):
            await compliance_manager.store_payment_data(payment_data, encrypt=False)
        
        # Tokenized/encrypted data should be allowed
        tokenization_result = await compliance_manager.tokenize_payment_data(payment_data)
        assert "token" in tokenization_result
        assert payment_data["card_number"] not in str(tokenization_result["token"])
        
        # Storing tokenized data should be compliant
        storage_result = await compliance_manager.store_payment_data(
            tokenization_result, encrypt=True
        )
        assert storage_result["stored"] is True
        assert storage_result["pci_compliant"] is True

    @pytest.mark.asyncio
    async def test_right_to_be_forgotten_gdpr(self, privacy_controller):
        """Test GDPR right to be forgotten implementation"""
        user_id = 789
        
        # User requests data deletion
        deletion_request = {
            "user_id": user_id,
            "request_type": "right_to_be_forgotten",
            "requested_at": datetime.now()
        }
        
        # Should identify all user data across systems
        data_inventory = await privacy_controller.inventory_user_data(user_id)
        assert "personal_info" in data_inventory
        assert "activity_logs" in data_inventory
        assert "preferences" in data_inventory
        
        # Should execute secure deletion
        deletion_result = await privacy_controller.execute_data_deletion(
            deletion_request, data_inventory
        )
        
        assert deletion_result["deleted"] is True
        assert "deletion_certificate" in deletion_result
        assert deletion_result["verified_deletion"] is True
        
        # Data should no longer be accessible
        remaining_data = await privacy_controller.inventory_user_data(user_id)
        assert len(remaining_data) == 0

    @pytest.mark.asyncio
    async def test_cross_border_data_transfer_validation(self, compliance_manager):
        """Test validation of cross-border data transfers"""
        transfer_request = {
            "source_country": "EU",
            "destination_country": "US",
            "data_type": "personal_data",
            "user_consent": True,
            "transfer_mechanism": "standard_contractual_clauses"
        }
        
        # Validate transfer is legally compliant
        validation_result = await compliance_manager.validate_cross_border_transfer(
            transfer_request
        )
        
        assert validation_result["compliant"] is True
        assert "adequate_protection" in validation_result
        assert validation_result["legal_basis"] == "standard_contractual_clauses"
        
        # Invalid transfer should be blocked
        invalid_request = transfer_request.copy()
        invalid_request["destination_country"] = "non_adequate_country"
        invalid_request["transfer_mechanism"] = "none"
        
        validation_result = await compliance_manager.validate_cross_border_transfer(
            invalid_request
        )
        assert validation_result["compliant"] is False
        assert "inadequate_protection" in validation_result["issues"]

    @pytest.mark.asyncio
    async def test_automated_compliance_monitoring(self, compliance_manager, audit_logger):
        """Test automated compliance monitoring and alerting"""
        # Simulate suspicious activity that violates compliance
        suspicious_activities = [
            {"action": "bulk_data_export", "user_id": 123, "record_count": 100000},
            {"action": "after_hours_access", "user_id": 123, "timestamp": "02:00:00"},
            {"action": "privilege_escalation", "user_id": 123, "old_role": "user", "new_role": "admin"}
        ]
        
        for activity in suspicious_activities:
            await audit_logger.log_activity(activity)
        
        # Automated monitoring should detect violations
        compliance_alerts = await compliance_manager.run_compliance_monitoring(
            time_window_hours=1
        )
        
        assert len(compliance_alerts) > 0
        assert any(alert["type"] == "potential_data_breach" for alert in compliance_alerts)
        assert any(alert["severity"] == "high" for alert in compliance_alerts)
        
        # Should trigger automated response
        response_actions = await compliance_manager.execute_automated_response(
            compliance_alerts
        )
        
        assert "user_account_lock" in response_actions
        assert "security_team_notification" in response_actions
        assert "regulatory_report_preparation" in response_actions

    @pytest.mark.asyncio
    async def test_data_classification_enforcement(self, compliance_manager):
        """Test enforcement of data classification policies"""
        classified_data = {
            "content": "Confidential financial projections Q4 2024",
            "classification": "confidential",
            "access_level": "executive_only"
        }
        
        unauthorized_user = {"user_id": 999, "clearance_level": "public"}
        
        # Unauthorized access should be blocked
        with pytest.raises(ValueError, match="Insufficient clearance level"):
            await compliance_manager.access_classified_data(
                classified_data, accessing_user=unauthorized_user
            )
        
        # Authorized user should access data
        authorized_user = {"user_id": 123, "clearance_level": "confidential"}
        
        access_result = await compliance_manager.access_classified_data(
            classified_data, accessing_user=authorized_user
        )
        
        assert access_result["access_granted"] is True
        assert "data_handling_restrictions" in access_result
        assert "no_forwarding" in access_result["data_handling_restrictions"]
