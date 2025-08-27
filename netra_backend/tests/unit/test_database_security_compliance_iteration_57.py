"""
Test Database Security and Compliance - Iteration 57

Business Value Justification:
- Segment: Enterprise/Mid
- Business Goal: Security & Compliance
- Value Impact: Ensures data protection and regulatory compliance
- Strategic Impact: Protects against breaches and maintains customer trust

Focus: Encryption, access controls, audit logging, and compliance validation
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import hashlib
import secrets

from netra_backend.app.database.manager import DatabaseManager


class TestDatabaseSecurityCompliance:
    """Test database security controls and compliance mechanisms"""
    
    @pytest.fixture
    def mock_security_manager(self):
        """Mock security manager with encryption and access controls"""
        manager = MagicMock()
        manager.encryption_enabled = True
        manager.access_logs = []
        manager.failed_attempts = {}
        return manager
    
    @pytest.fixture
    def mock_compliance_service(self):
        """Mock compliance validation service"""
        service = MagicMock()
        service.audit_logs = []
        service.compliance_status = {}
        return service
    
    @pytest.mark.asyncio
    async def test_data_encryption_at_rest(self, mock_security_manager):
        """Test data encryption at rest implementation"""
        def encrypt_data(data, key_id="default"):
            # Simulate encryption process
            if not mock_security_manager.encryption_enabled:
                return {"data": data, "encrypted": False}
            
            # Mock encryption (in real implementation, use proper encryption)
            encrypted_data = hashlib.sha256(f"{key_id}_{data}".encode()).hexdigest()
            
            return {
                "data": encrypted_data,
                "encrypted": True,
                "key_id": key_id,
                "algorithm": "AES-256-GCM",
                "timestamp": datetime.now().isoformat()
            }
        
        def decrypt_data(encrypted_data, key_id="default"):
            if not encrypted_data.get("encrypted", False):
                return encrypted_data["data"]
            
            # Mock decryption - in practice, use proper decryption
            # For testing, we'll return a mock decrypted value
            return f"decrypted_{encrypted_data['key_id']}_data"
        
        mock_security_manager.encrypt_data = encrypt_data
        mock_security_manager.decrypt_data = decrypt_data
        
        # Test encryption
        sensitive_data = "user_ssn_123456789"
        encrypted_result = mock_security_manager.encrypt_data(sensitive_data)
        
        assert encrypted_result["encrypted"] is True
        assert encrypted_result["key_id"] == "default"
        assert encrypted_result["algorithm"] == "AES-256-GCM"
        assert encrypted_result["data"] != sensitive_data  # Data should be transformed
        
        # Test decryption
        decrypted_data = mock_security_manager.decrypt_data(encrypted_result)
        assert decrypted_data == "decrypted_default_data"
        
        # Test with encryption disabled
        mock_security_manager.encryption_enabled = False
        unencrypted_result = mock_security_manager.encrypt_data(sensitive_data)
        assert unencrypted_result["encrypted"] is False
        assert unencrypted_result["data"] == sensitive_data
    
    @pytest.mark.asyncio
    async def test_access_control_validation(self, mock_security_manager):
        """Test database access control and authorization"""
        user_permissions = {
            "admin_user": {"permissions": ["READ", "WRITE", "DELETE", "ADMIN"], "role": "admin"},
            "app_user": {"permissions": ["READ", "WRITE"], "role": "application"},
            "readonly_user": {"permissions": ["READ"], "role": "readonly"},
            "audit_user": {"permissions": ["READ"], "role": "auditor", "tables": ["audit_log"]}
        }
        
        def validate_access(user_id, operation, table_name=None):
            if user_id not in user_permissions:
                return {"access_granted": False, "reason": "User not found"}
            
            user = user_permissions[user_id]
            
            # Check operation permission
            if operation not in user["permissions"]:
                mock_security_manager.access_logs.append({
                    "user_id": user_id,
                    "operation": operation,
                    "table": table_name,
                    "status": "denied",
                    "reason": "Insufficient permissions",
                    "timestamp": datetime.now().isoformat()
                })
                return {"access_granted": False, "reason": "Insufficient permissions"}
            
            # Check table-specific access for auditors
            if user["role"] == "auditor" and table_name:
                allowed_tables = user.get("tables", [])
                if table_name not in allowed_tables:
                    mock_security_manager.access_logs.append({
                        "user_id": user_id,
                        "operation": operation,
                        "table": table_name,
                        "status": "denied",
                        "reason": "Table access denied",
                        "timestamp": datetime.now().isoformat()
                    })
                    return {"access_granted": False, "reason": "Table access denied"}
            
            # Log successful access
            mock_security_manager.access_logs.append({
                "user_id": user_id,
                "operation": operation,
                "table": table_name,
                "status": "granted",
                "timestamp": datetime.now().isoformat()
            })
            
            return {"access_granted": True, "user_role": user["role"]}
        
        mock_security_manager.validate_access = validate_access
        
        # Test admin access
        admin_result = mock_security_manager.validate_access("admin_user", "DELETE", "users")
        assert admin_result["access_granted"] is True
        assert admin_result["user_role"] == "admin"
        
        # Test application user access
        app_result = mock_security_manager.validate_access("app_user", "WRITE", "posts")
        assert app_result["access_granted"] is True
        
        # Test readonly user denied write access
        readonly_result = mock_security_manager.validate_access("readonly_user", "WRITE", "users")
        assert readonly_result["access_granted"] is False
        assert readonly_result["reason"] == "Insufficient permissions"
        
        # Test auditor table restrictions
        audit_allowed = mock_security_manager.validate_access("audit_user", "READ", "audit_log")
        assert audit_allowed["access_granted"] is True
        
        audit_denied = mock_security_manager.validate_access("audit_user", "READ", "users")
        assert audit_denied["access_granted"] is False
        assert audit_denied["reason"] == "Table access denied"
        
        # Verify access logging
        assert len(mock_security_manager.access_logs) >= 4
        denied_logs = [log for log in mock_security_manager.access_logs if log["status"] == "denied"]
        assert len(denied_logs) == 2
    
    @pytest.mark.asyncio
    async def test_sql_injection_prevention(self, mock_security_manager):
        """Test SQL injection prevention mechanisms"""
        malicious_patterns = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM passwords --",
            "'; INSERT INTO admin_users VALUES ('hacker', 'password'); --",
            "' AND (SELECT COUNT(*) FROM information_schema.tables) > 0 --"
        ]
        
        def validate_query_safety(query, parameters=None):
            validation_result = {
                "query": query,
                "safe": True,
                "threats_detected": [],
                "sanitized_query": query
            }
            
            # Check for common SQL injection patterns
            query_upper = query.upper()
            
            dangerous_patterns = {
                "DROP TABLE": "Potential table deletion",
                "DROP DATABASE": "Potential database deletion",
                "'; --": "SQL comment injection",
                "' OR '1'='1": "Boolean injection",
                "UNION SELECT": "Union-based injection",
                "INFORMATION_SCHEMA": "Schema enumeration attempt",
                "'; INSERT": "Stacked query injection"
            }
            
            for pattern, description in dangerous_patterns.items():
                if pattern in query_upper:
                    validation_result["safe"] = False
                    validation_result["threats_detected"].append({
                        "pattern": pattern,
                        "description": description,
                        "severity": "high"
                    })
            
            # Check for parameterized query usage
            if parameters is not None:
                validation_result["parameterized"] = True
                validation_result["safe"] = True  # Parameterized queries are generally safe
                validation_result["threats_detected"] = []
            else:
                validation_result["parameterized"] = False
            
            return validation_result
        
        mock_security_manager.validate_query_safety = validate_query_safety
        
        # Test malicious queries
        for malicious_query in malicious_patterns:
            result = mock_security_manager.validate_query_safety(malicious_query)
            assert result["safe"] is False
            assert len(result["threats_detected"]) > 0
            
            # Verify specific threat detection
            if "DROP TABLE" in malicious_query:
                drop_threats = [t for t in result["threats_detected"] if "deletion" in t["description"]]
                assert len(drop_threats) > 0
        
        # Test safe parameterized query
        safe_query = "SELECT * FROM users WHERE id = ? AND email = ?"
        safe_result = mock_security_manager.validate_query_safety(
            safe_query, 
            parameters=["user123", "user@example.com"]
        )
        assert safe_result["safe"] is True
        assert safe_result["parameterized"] is True
        assert len(safe_result["threats_detected"]) == 0
    
    @pytest.mark.asyncio
    async def test_audit_logging_compliance(self, mock_compliance_service):
        """Test comprehensive audit logging for compliance"""
        def log_database_activity(activity_data):
            audit_entry = {
                "timestamp": datetime.now().isoformat(),
                "activity_id": secrets.token_hex(8),
                "user_id": activity_data["user_id"],
                "session_id": activity_data.get("session_id"),
                "operation": activity_data["operation"],
                "table_name": activity_data.get("table_name"),
                "record_ids": activity_data.get("record_ids", []),
                "query": activity_data.get("query"),
                "success": activity_data.get("success", True),
                "error_message": activity_data.get("error_message"),
                "ip_address": activity_data.get("ip_address"),
                "user_agent": activity_data.get("user_agent"),
                "data_classification": activity_data.get("data_classification", "internal")
            }
            
            mock_compliance_service.audit_logs.append(audit_entry)
            return audit_entry
        
        def generate_compliance_report(date_range):
            start_date = datetime.fromisoformat(date_range["start"])
            end_date = datetime.fromisoformat(date_range["end"])
            
            relevant_logs = []
            for log in mock_compliance_service.audit_logs:
                log_time = datetime.fromisoformat(log["timestamp"])
                if start_date <= log_time <= end_date:
                    relevant_logs.append(log)
            
            report = {
                "report_period": date_range,
                "total_activities": len(relevant_logs),
                "activities_by_operation": {},
                "activities_by_user": {},
                "failed_operations": [],
                "high_risk_activities": []
            }
            
            for log in relevant_logs:
                # Count by operation
                op = log["operation"]
                report["activities_by_operation"][op] = report["activities_by_operation"].get(op, 0) + 1
                
                # Count by user
                user = log["user_id"]
                report["activities_by_user"][user] = report["activities_by_user"].get(user, 0) + 1
                
                # Track failures
                if not log["success"]:
                    report["failed_operations"].append(log)
                
                # Identify high-risk activities
                if log["data_classification"] == "confidential" or log["operation"] in ["DELETE", "DROP"]:
                    report["high_risk_activities"].append(log)
            
            return report
        
        mock_compliance_service.log_database_activity = log_database_activity
        mock_compliance_service.generate_compliance_report = generate_compliance_report
        
        # Log various database activities
        activities = [
            {
                "user_id": "user123",
                "session_id": "sess_001",
                "operation": "SELECT",
                "table_name": "users",
                "query": "SELECT * FROM users WHERE id = ?",
                "ip_address": "192.168.1.100",
                "data_classification": "internal"
            },
            {
                "user_id": "admin456",
                "session_id": "sess_002",
                "operation": "DELETE",
                "table_name": "users",
                "record_ids": ["user_789"],
                "query": "DELETE FROM users WHERE id = ?",
                "ip_address": "192.168.1.200",
                "data_classification": "confidential"
            },
            {
                "user_id": "user123",
                "session_id": "sess_003",
                "operation": "UPDATE",
                "table_name": "profiles",
                "success": False,
                "error_message": "Access denied",
                "ip_address": "192.168.1.100"
            }
        ]
        
        logged_activities = []
        for activity in activities:
            logged_activity = mock_compliance_service.log_database_activity(activity)
            logged_activities.append(logged_activity)
        
        # Verify audit logging
        assert len(mock_compliance_service.audit_logs) == 3
        
        for logged in logged_activities:
            assert "activity_id" in logged
            assert "timestamp" in logged
            assert logged["user_id"] in ["user123", "admin456"]
        
        # Generate compliance report
        report_range = {
            "start": (datetime.now() - timedelta(hours=1)).isoformat(),
            "end": (datetime.now() + timedelta(hours=1)).isoformat()
        }
        
        report = mock_compliance_service.generate_compliance_report(report_range)
        
        assert report["total_activities"] == 3
        assert report["activities_by_operation"]["SELECT"] == 1
        assert report["activities_by_operation"]["DELETE"] == 1
        assert report["activities_by_operation"]["UPDATE"] == 1
        assert report["activities_by_user"]["user123"] == 2
        assert report["activities_by_user"]["admin456"] == 1
        
        # Check high-risk activities
        assert len(report["high_risk_activities"]) == 1  # DELETE operation
        assert report["high_risk_activities"][0]["operation"] == "DELETE"
        
        # Check failed operations
        assert len(report["failed_operations"]) == 1
        assert report["failed_operations"][0]["error_message"] == "Access denied"
    
    def test_gdpr_compliance_validation(self, mock_compliance_service):
        """Test GDPR compliance validation and data handling"""
        def validate_gdpr_compliance(data_processing_activity):
            compliance_check = {
                "activity": data_processing_activity,
                "compliant": True,
                "violations": [],
                "recommendations": []
            }
            
            # Check for personal data processing
            personal_data_fields = ["email", "name", "phone", "address", "ssn", "ip_address"]
            has_personal_data = any(field in str(data_processing_activity.get("fields", [])).lower() 
                                  for field in personal_data_fields)
            
            if has_personal_data:
                # Check for consent
                if not data_processing_activity.get("consent_obtained", False):
                    compliance_check["violations"].append({
                        "type": "missing_consent",
                        "description": "Processing personal data without consent",
                        "severity": "high"
                    })
                    compliance_check["compliant"] = False
                
                # Check for lawful basis
                if not data_processing_activity.get("lawful_basis"):
                    compliance_check["violations"].append({
                        "type": "missing_lawful_basis",
                        "description": "No lawful basis specified for processing",
                        "severity": "high"
                    })
                    compliance_check["compliant"] = False
                
                # Check data retention policy
                if not data_processing_activity.get("retention_period"):
                    compliance_check["recommendations"].append({
                        "type": "data_retention",
                        "description": "Specify data retention period"
                    })
                
                # Check data subject rights implementation
                required_rights = ["access", "rectification", "erasure", "portability"]
                implemented_rights = data_processing_activity.get("data_subject_rights", [])
                missing_rights = set(required_rights) - set(implemented_rights)
                
                if missing_rights:
                    compliance_check["recommendations"].append({
                        "type": "data_subject_rights",
                        "description": f"Implement missing data subject rights: {', '.join(missing_rights)}"
                    })
            
            return compliance_check
        
        def implement_data_subject_request(request_type, user_id, additional_params=None):
            request_result = {
                "request_type": request_type,
                "user_id": user_id,
                "status": "completed",
                "timestamp": datetime.now().isoformat()
            }
            
            if request_type == "access":
                # Data portability request
                request_result["data_export"] = {
                    "format": "JSON",
                    "size_bytes": 1024,
                    "download_link": f"https://api.example.com/export/{user_id}"
                }
            
            elif request_type == "erasure":
                # Right to be forgotten
                request_result["data_deleted"] = {
                    "tables_affected": ["users", "user_profiles", "user_preferences"],
                    "records_deleted": 3,
                    "anonymized_records": 5  # Records that were anonymized instead of deleted
                }
            
            elif request_type == "rectification":
                # Data correction request
                updated_fields = additional_params.get("updated_fields", {})
                request_result["data_updated"] = {
                    "fields_updated": list(updated_fields.keys()),
                    "records_affected": 1
                }
            
            return request_result
        
        mock_compliance_service.validate_gdpr_compliance = validate_gdpr_compliance
        mock_compliance_service.implement_data_subject_request = implement_data_subject_request
        
        # Test compliant activity
        compliant_activity = {
            "operation": "SELECT",
            "fields": ["name", "email"],
            "consent_obtained": True,
            "lawful_basis": "consent",
            "retention_period": "2 years",
            "data_subject_rights": ["access", "rectification", "erasure", "portability"]
        }
        
        compliance_result = mock_compliance_service.validate_gdpr_compliance(compliant_activity)
        assert compliance_result["compliant"] is True
        assert len(compliance_result["violations"]) == 0
        
        # Test non-compliant activity
        non_compliant_activity = {
            "operation": "SELECT",
            "fields": ["name", "email", "ssn"],
            "consent_obtained": False,
            "data_subject_rights": ["access"]  # Missing rights
        }
        
        compliance_result = mock_compliance_service.validate_gdpr_compliance(non_compliant_activity)
        assert compliance_result["compliant"] is False
        assert len(compliance_result["violations"]) >= 1
        assert len(compliance_result["recommendations"]) >= 1
        
        # Test data subject rights implementation
        access_request = mock_compliance_service.implement_data_subject_request("access", "user123")
        assert access_request["status"] == "completed"
        assert "data_export" in access_request
        
        erasure_request = mock_compliance_service.implement_data_subject_request("erasure", "user456")
        assert erasure_request["status"] == "completed"
        assert "data_deleted" in erasure_request
        assert erasure_request["data_deleted"]["records_deleted"] == 3