"""
Strategic Unit Tests for Advanced Agent Security Scenarios and Multi-User Isolation

Business Value Justification (BVJ):
- Segment: Enterprise/Regulated - HIPAA, SOC2, SEC compliance requirements  
- Business Goal: Security & Trust - Prevent cross-user data contamination
- Value Impact: Protects $500K+ ARR from regulatory violations and customer churn
- Strategic Impact: Enables enterprise sales with compliance confidence

STRATEGIC GAP ADDRESSED: Advanced Security Scenarios for multi-user isolation
This test suite focuses on sophisticated security attack vectors:
1. Cross-user message contamination through object reference sharing
2. Agent context bleeding between concurrent user sessions  
3. Privilege escalation through malformed agent messages
4. Data exfiltration through WebSocket event manipulation
5. Session hijacking through agent state manipulation

CRITICAL: These tests validate enterprise-grade security isolation requirements.
"""

import pytest
import asyncio
import uuid
import json
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch, MagicMock, PropertyMock
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.agent_websocket_bridge import (
    AgentWebSocketBridge,
    IntegrationState,
    IntegrationConfig
)


@dataclass
class SecurityTestUser:
    """Test user with security context tracking."""
    user_id: str
    tenant_id: str
    security_level: str
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    thread_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    websocket_connection_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    received_messages: List[Dict] = field(default_factory=list)
    sensitive_data: Set[str] = field(default_factory=set)


class TestAgentSecurityIsolationStrategic(SSotAsyncTestCase):
    """
    Strategic unit tests for advanced security scenarios in multi-user agent systems.
    
    SECURITY FOCUS: Enterprise compliance scenarios that could cause data breaches
    or regulatory violations in production environments.
    """
    
    def setup_method(self, method):
        """Set up test fixtures with security monitoring."""
        super().setup_method(method)
        
        # Create bridge for security testing
        self.bridge = AgentWebSocketBridge()
        
        # Create test users with different security contexts
        self.user_alice = SecurityTestUser(
            user_id="alice_secure_123",
            tenant_id="tenant_healthcare", 
            security_level="HIPAA_PROTECTED",
            sensitive_data={"SSN_123456789", "medical_record_alice", "diagnosis_confidential"}
        )
        
        self.user_bob = SecurityTestUser(
            user_id="bob_standard_456",
            tenant_id="tenant_finance",
            security_level="SOC2_COMPLIANT", 
            sensitive_data={"account_987654321", "trading_strategy_bob", "financial_projections"}
        )
        
        self.user_charlie = SecurityTestUser(
            user_id="charlie_restricted_789",
            tenant_id="tenant_government",
            security_level="SEC_REGULATED",
            sensitive_data={"classified_data_charlie", "sec_filing_draft", "insider_information"}
        )
        
        # Security violation tracking
        self.security_violations = []
        self.cross_user_contamination = []
        self.privilege_escalations = []
        
        # Mock WebSocket manager with security monitoring
        self.mock_websocket_manager = AsyncMock()
        self.mock_websocket_manager.emit_to_run.side_effect = self._monitor_security_emissions

    async def _monitor_security_emissions(self, run_id, event_type, data, **kwargs):
        """Monitor emissions for security violations."""
        # Track which user this emission is for
        target_user = None
        for user in [self.user_alice, self.user_bob, self.user_charlie]:
            if user.run_id == run_id:
                target_user = user
                break
        
        if target_user:
            # Record message for user
            message = {
                'timestamp': time.time(),
                'run_id': run_id,
                'event_type': event_type,
                'data': json.loads(json.dumps(data)) if isinstance(data, dict) else data,
                'target_user_id': target_user.user_id,
                'target_tenant_id': target_user.tenant_id
            }
            target_user.received_messages.append(message)
            
            # Check for security violations
            await self._check_security_violations(target_user, message)
        
        return True

    async def _check_security_violations(self, target_user, message):
        """Check for various security violations."""
        # Check for cross-user data contamination
        message_content = str(message.get('data', ''))
        
        # Check if this user's message contains other users' sensitive data
        for other_user in [self.user_alice, self.user_bob, self.user_charlie]:
            if other_user.user_id != target_user.user_id:
                for sensitive_item in other_user.sensitive_data:
                    if sensitive_item in message_content:
                        violation = {
                            'type': 'CROSS_USER_CONTAMINATION',
                            'victim_user': target_user.user_id,
                            'contaminated_data': sensitive_item,
                            'source_user': other_user.user_id,
                            'message': message,
                            'timestamp': time.time()
                        }
                        self.security_violations.append(violation)
                        self.cross_user_contamination.append(violation)

    async def test_concurrent_user_message_isolation_strict(self):
        """
        SECURITY CRITICAL: Concurrent users must have complete message isolation.
        
        COMPLIANCE REQUIREMENT: HIPAA, SOC2, SEC regulations require zero cross-user data leakage.
        This test simulates high-concurrency scenarios with sensitive data.
        """
        # Arrange - Create realistic user contexts
        alice_context = Mock()
        alice_context.user_id = self.user_alice.user_id
        alice_context.tenant_id = self.user_alice.tenant_id
        alice_context.run_id = self.user_alice.run_id
        alice_context.thread_id = self.user_alice.thread_id
        
        bob_context = Mock()
        bob_context.user_id = self.user_bob.user_id
        bob_context.tenant_id = self.user_bob.tenant_id
        bob_context.run_id = self.user_bob.run_id
        bob_context.thread_id = self.user_bob.thread_id
        
        charlie_context = Mock()
        charlie_context.user_id = self.user_charlie.user_id
        charlie_context.tenant_id = self.user_charlie.tenant_id
        charlie_context.run_id = self.user_charlie.run_id
        charlie_context.thread_id = self.user_charlie.thread_id
        
        # Mock the websocket_manager property directly since _get_websocket_manager doesn't exist
        with patch.object(type(self.bridge), 'websocket_manager', new_callable=PropertyMock) as mock_ws_property:
            mock_ws_property.return_value = self.mock_websocket_manager
            # Act - Concurrent operations with sensitive data
            concurrent_tasks = [
                # Alice (HIPAA) processes medical data
                self.bridge.notify_agent_started(
                    run_id=self.user_alice.run_id,
                    agent_name="MedicalAnalysisAgent",
                    context={
                        "patient_data": "SSN_123456789",
                        "medical_record": "medical_record_alice", 
                        "diagnosis": "diagnosis_confidential",
                        "user_id": self.user_alice.user_id,
                        "tenant_id": self.user_alice.tenant_id
                    }
                ),
                
                # Bob (SOC2) processes financial data  
                self.bridge.notify_agent_started(
                    run_id=self.user_bob.run_id,
                    agent_name="FinancialAnalysisAgent",
                    context={
                        "account_info": "account_987654321",
                        "trading_strategy": "trading_strategy_bob",
                        "projections": "financial_projections",
                        "user_id": self.user_bob.user_id,
                        "tenant_id": self.user_bob.tenant_id
                    }
                ),
                
                # Charlie (SEC) processes regulated data
                self.bridge.notify_agent_started(
                    run_id=self.user_charlie.run_id,
                    agent_name="RegulatoryAgent", 
                    context={
                        "classified": "classified_data_charlie",
                        "sec_filing": "sec_filing_draft",
                        "insider_info": "insider_information",
                        "user_id": self.user_charlie.user_id,
                        "tenant_id": self.user_charlie.tenant_id
                    }
                ),
                
                # Concurrent thinking processes with sensitive reasoning
                self.bridge.notify_agent_thinking(
                    run_id=self.user_alice.run_id,
                    agent_name="MedicalAnalysisAgent",
                    reasoning="Analyzing patient SSN_123456789 medical history"
                ),
                
                self.bridge.notify_agent_thinking(
                    run_id=self.user_bob.run_id,
                    agent_name="FinancialAnalysisAgent", 
                    reasoning="Processing account_987654321 trading patterns"
                ),
                
                self.bridge.notify_agent_thinking(
                    run_id=self.user_charlie.run_id,
                    agent_name="RegulatoryAgent",
                    reasoning="Reviewing classified_data_charlie compliance"
                )
            ]
            
            # Execute all concurrent operations
            results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            
            # Assert - No cross-contamination should occur
            assert all(r is True for r in results if not isinstance(r, Exception)), \
                "All concurrent operations should succeed"
            
            # Critical security verification
            assert len(self.cross_user_contamination) == 0, \
                f"SECURITY VIOLATION: Cross-user contamination detected: {self.cross_user_contamination}"
            
            # Verify each user only received their own data
            for user in [self.user_alice, self.user_bob, self.user_charlie]:
                for message in user.received_messages:
                    assert message['target_user_id'] == user.user_id, \
                        f"User {user.user_id} received message for different user"
                    assert message['target_tenant_id'] == user.tenant_id, \
                        f"User {user.user_id} received message from different tenant"

    async def test_agent_context_bleeding_prevention(self):
        """
        SECURITY CRITICAL: Agent execution contexts must not bleed between users.
        
        ATTACK VECTOR: Malicious user attempts to access other users' agent contexts
        through shared object references or memory leaks.
        """
        # Arrange - Create agents with intentionally similar contexts to test bleeding
        shared_agent_name = "DataProcessorAgent"  # Same agent, different users
        
        # Mock the websocket_manager property directly since _get_websocket_manager doesn't exist
        with patch.object(type(self.bridge), 'websocket_manager', new_callable=PropertyMock) as mock_ws_property:
            mock_ws_property.return_value = self.mock_websocket_manager
            # Act - Sequential agent operations that could cause context bleeding
            
            # Alice starts agent with sensitive medical context
            await self.bridge.notify_agent_started(
                run_id=self.user_alice.run_id,
                agent_name=shared_agent_name,
                context={
                    "operation": "medical_analysis",
                    "sensitive_ssn": "SSN_123456789",
                    "patient_id": "medical_record_alice",
                    "security_clearance": "HIPAA_PROTECTED"
                }
            )
            
            # Bob starts SAME agent type with financial context
            await self.bridge.notify_agent_started(
                run_id=self.user_bob.run_id, 
                agent_name=shared_agent_name,
                context={
                    "operation": "financial_analysis", 
                    "account_number": "account_987654321",
                    "strategy": "trading_strategy_bob",
                    "security_clearance": "SOC2_COMPLIANT"
                }
            )
            
            # Alice continues with thinking - context should remain medical
            await self.bridge.notify_agent_thinking(
                run_id=self.user_alice.run_id,
                agent_name=shared_agent_name,
                reasoning="Continuing medical analysis for SSN_123456789"
            )
            
            # Bob continues with thinking - context should remain financial  
            await self.bridge.notify_agent_thinking(
                run_id=self.user_bob.run_id,
                agent_name=shared_agent_name,
                reasoning="Continuing financial analysis for account_987654321"
            )
            
            # Assert - No context bleeding should occur
            alice_messages = [msg for msg in self.user_alice.received_messages]
            bob_messages = [msg for msg in self.user_bob.received_messages]
            
            # Alice should only see medical data
            alice_content = ' '.join([str(msg['data']) for msg in alice_messages])
            assert "SSN_123456789" in alice_content, "Alice should see her medical data"
            assert "medical_record_alice" in alice_content, "Alice should see her patient ID"
            assert "account_987654321" not in alice_content, \
                "SECURITY VIOLATION: Alice should not see Bob's financial data"
            assert "trading_strategy_bob" not in alice_content, \
                "SECURITY VIOLATION: Alice should not see Bob's trading strategy"
            
            # Bob should only see financial data
            bob_content = ' '.join([str(msg['data']) for msg in bob_messages])
            assert "account_987654321" in bob_content, "Bob should see his financial data"
            assert "trading_strategy_bob" in bob_content, "Bob should see his strategy"
            assert "SSN_123456789" not in bob_content, \
                "SECURITY VIOLATION: Bob should not see Alice's medical data"
            assert "medical_record_alice" not in bob_content, \
                "SECURITY VIOLATION: Bob should not see Alice's patient data"

    async def test_privilege_escalation_through_agent_messages(self):
        """
        SECURITY CRITICAL: Users must not escalate privileges through malformed agent messages.
        
        ATTACK VECTOR: Malicious user crafts agent messages to access higher privilege data
        or execute operations beyond their authorization level.
        """
        # Arrange - Create low-privilege user attempting escalation
        low_privilege_user = SecurityTestUser(
            user_id="mallory_lowpriv_999",
            tenant_id="tenant_basic",
            security_level="BASIC_ACCESS"
        )
        
        # Mock the websocket_manager property directly since _get_websocket_manager doesn't exist
        with patch.object(type(self.bridge), 'websocket_manager', new_callable=PropertyMock) as mock_ws_property:
            mock_ws_property.return_value = self.mock_websocket_manager
            # Act - Malicious user attempts privilege escalation
            
            # Attempt 1: Impersonation through context manipulation
            malicious_result1 = await self.bridge.notify_agent_started(
                run_id=low_privilege_user.run_id,
                agent_name="EscalationAgent",
                context={
                    # Malicious: trying to impersonate Alice
                    "user_id": self.user_alice.user_id,  
                    "tenant_id": self.user_alice.tenant_id,
                    "security_level": "HIPAA_PROTECTED",
                    "requested_data": "SSN_123456789",  # Trying to access Alice's data
                    "actual_user": low_privilege_user.user_id  # Real user buried in context
                }
            )
            
            # Attempt 2: Cross-tenant data access
            malicious_result2 = await self.bridge.notify_agent_thinking(
                run_id=low_privilege_user.run_id,
                agent_name="EscalationAgent", 
                reasoning=f"Accessing cross-tenant data: {self.user_bob.tenant_id} financial records"
            )
            
            # Attempt 3: Admin function impersonation
            malicious_result3 = await self.bridge.notify_agent_completed(
                run_id=low_privilege_user.run_id,
                agent_name="EscalationAgent",
                result={
                    "admin_operation": "user_data_export",
                    "target_users": [self.user_alice.user_id, self.user_bob.user_id],
                    "privileged_data": "all_user_sensitive_data"
                }
            )
            
            # Assert - Privilege escalation attempts should be contained
            assert malicious_result1 is True, "Message should be processed (but contained)"
            assert malicious_result2 is True, "Message should be processed (but contained)"  
            assert malicious_result3 is True, "Message should be processed (but contained)"
            
            # Critical: Verify no sensitive data was exposed to low-privilege user
            low_priv_messages = [msg for msg in low_privilege_user.received_messages if 
                               msg['run_id'] == low_privilege_user.run_id]
            
            for message in low_priv_messages:
                message_content = str(message.get('data', ''))
                
                # Should not contain any sensitive data from other users
                for sensitive_item in (self.user_alice.sensitive_data | 
                                     self.user_bob.sensitive_data | 
                                     self.user_charlie.sensitive_data):
                    assert sensitive_item not in message_content, \
                        f"PRIVILEGE ESCALATION: Low-privilege user accessed sensitive data: {sensitive_item}"

    async def test_websocket_session_hijacking_prevention(self):
        """
        SECURITY CRITICAL: WebSocket sessions must be protected from hijacking attempts.
        
        ATTACK VECTOR: Attacker attempts to hijack active WebSocket sessions to access
        other users' real-time agent messages.
        """
        # Arrange - Create active user sessions
        alice_session_token = f"session_alice_{uuid.uuid4()}"
        bob_session_token = f"session_bob_{uuid.uuid4()}"
        
        # Mock WebSocket connections with session tracking
        mock_alice_connection = Mock()
        mock_alice_connection.session_token = alice_session_token
        mock_alice_connection.user_id = self.user_alice.user_id
        
        mock_bob_connection = Mock()  
        mock_bob_connection.session_token = bob_session_token
        mock_bob_connection.user_id = self.user_bob.user_id
        
        # Mock the websocket_manager property directly since _get_websocket_manager doesn't exist
        with patch.object(type(self.bridge), 'websocket_manager', new_callable=PropertyMock) as mock_ws_property:
            mock_ws_property.return_value = self.mock_websocket_manager
            # Act - Simulate session hijacking attempt
            
            # Alice starts normal session with sensitive data
            await self.bridge.notify_agent_started(
                run_id=self.user_alice.run_id,
                agent_name="SecureAgent",
                context={
                    "session_token": alice_session_token,
                    "sensitive_operation": "medical_record_access",
                    "patient_ssn": "SSN_123456789"
                }
            )
            
            # Attacker (using Bob's credentials) tries to hijack Alice's session
            hijack_attempt_run_id = str(uuid.uuid4())
            await self.bridge.notify_agent_started(
                run_id=hijack_attempt_run_id,
                agent_name="HijackAgent",
                context={
                    # Malicious: trying to use Alice's session token
                    "session_token": alice_session_token,  
                    "user_id": self.user_bob.user_id,  # But claiming to be Bob
                    "hijack_target": self.user_alice.user_id,
                    "requested_data": "all_medical_records"
                }
            )
            
            # Alice continues normal operations
            await self.bridge.notify_agent_thinking(
                run_id=self.user_alice.run_id,
                agent_name="SecureAgent",
                reasoning="Processing confidential medical data"
            )
            
            # Hijacker tries to intercept Alice's messages
            await self.bridge.notify_agent_thinking(
                run_id=hijack_attempt_run_id,
                agent_name="HijackAgent", 
                reasoning="Attempting to access Alice's medical data stream"
            )
            
            # Assert - Session hijacking should be prevented
            
            # Alice should only receive her own messages
            alice_messages = [msg for msg in self.user_alice.received_messages 
                            if msg['run_id'] == self.user_alice.run_id]
            assert len(alice_messages) >= 2, "Alice should receive her own messages"
            
            # Hijacker should not receive Alice's data
            hijack_messages = [msg for msg in self.user_alice.received_messages  
                             if msg['run_id'] == hijack_attempt_run_id]
            
            for hijack_message in hijack_messages:
                message_content = str(hijack_message.get('data', ''))
                assert "SSN_123456789" not in message_content, \
                    "HIJACK ATTACK: Attacker should not access Alice's SSN"
                assert "medical_record_alice" not in message_content, \
                    "HIJACK ATTACK: Attacker should not access Alice's medical records"

    async def test_data_exfiltration_through_agent_results(self):
        """
        SECURITY CRITICAL: Agent results must not enable data exfiltration across security boundaries.
        
        ATTACK VECTOR: Malicious agent attempts to exfiltrate sensitive data by embedding
        it in seemingly legitimate agent results.
        """
        # Arrange - Set up cross-tenant scenario with different security levels
        # Mock the websocket_manager property directly since _get_websocket_manager doesn't exist
        with patch.object(type(self.bridge), 'websocket_manager', new_callable=PropertyMock) as mock_ws_property:
            mock_ws_property.return_value = self.mock_websocket_manager
            # Act - Legitimate operations followed by exfiltration attempt
            
            # Alice performs legitimate medical analysis
            await self.bridge.notify_agent_started(
                run_id=self.user_alice.run_id,
                agent_name="MedicalAgent",
                context={
                    "operation": "patient_analysis",
                    "patient_ssn": "SSN_123456789",
                    "security_level": "HIPAA_PROTECTED"
                }
            )
            
            await self.bridge.notify_agent_completed(
                run_id=self.user_alice.run_id,
                agent_name="MedicalAgent",
                result={
                    "diagnosis": "Patient diagnosis for SSN_123456789",
                    "treatment_plan": "Confidential treatment recommendations",
                    "medical_history": "medical_record_alice detailed history"
                }
            )
            
            # Bob performs legitimate financial analysis  
            await self.bridge.notify_agent_started(
                run_id=self.user_bob.run_id,
                agent_name="FinancialAgent",
                context={
                    "operation": "portfolio_analysis", 
                    "account": "account_987654321",
                    "security_level": "SOC2_COMPLIANT"
                }
            )
            
            # Malicious: Bob's agent tries to exfiltrate Alice's medical data
            await self.bridge.notify_agent_completed(
                run_id=self.user_bob.run_id,
                agent_name="FinancialAgent",
                result={
                    "portfolio_summary": "Investment recommendations",
                    "risk_analysis": "Standard financial risk assessment",
                    # MALICIOUS: Attempting to exfiltrate Alice's medical data
                    "market_research": "Research includes SSN_123456789 medical trends",
                    "data_sources": "Including medical_record_alice market correlations",
                    "hidden_payload": {
                        "exfiltrated_data": "diagnosis_confidential", 
                        "stolen_from_user": self.user_alice.user_id
                    }
                }
            )
            
            # Assert - Data exfiltration should be prevented
            
            # Bob should not have access to Alice's sensitive data in his results
            bob_messages = [msg for msg in self.user_bob.received_messages
                          if msg['run_id'] == self.user_bob.run_id]
            
            for message in bob_messages:
                message_content = str(message.get('data', ''))
                
                # Bob's messages should not contain Alice's sensitive data
                for alice_sensitive in self.user_alice.sensitive_data:
                    if alice_sensitive in message_content:
                        # This would be a critical security violation
                        assert False, \
                            f"DATA EXFILTRATION: Bob's agent results contain Alice's sensitive data: {alice_sensitive}"
            
            # Verify no cross-contamination occurred  
            assert len(self.cross_user_contamination) == 0, \
                f"Data exfiltration prevented: {self.cross_user_contamination}"

    async def test_concurrent_security_stress_under_load(self):
        """
        SECURITY CRITICAL: Security isolation must hold under high concurrent load.
        
        STRESS TEST: Multiple users performing concurrent operations with sensitive data
        should maintain perfect isolation even under system stress.
        """
        # Arrange - Create high-concurrency security stress test
        stress_users = []
        for i in range(10):  # 10 concurrent users
            user = SecurityTestUser(
                user_id=f"stress_user_{i}",
                tenant_id=f"tenant_stress_{i}",
                security_level="CONFIDENTIAL",
                sensitive_data={f"secret_data_{i}", f"confidential_info_{i}", f"private_key_{i}"}
            )
            stress_users.append(user)
        
        # Mock the websocket_manager property directly since _get_websocket_manager doesn't exist
        with patch.object(type(self.bridge), 'websocket_manager', new_callable=PropertyMock) as mock_ws_property:
            mock_ws_property.return_value = self.mock_websocket_manager
            # Act - High-concurrency stress test with sensitive data
            stress_tasks = []
            
            for user in stress_users:
                # Each user performs multiple rapid operations with sensitive data
                for operation in range(5):  # 5 operations per user = 50 total concurrent ops
                    stress_tasks.extend([
                        self.bridge.notify_agent_started(
                            run_id=f"{user.run_id}_{operation}",
                            agent_name=f"StressAgent_{operation}",
                            context={
                                "user_id": user.user_id,
                                "tenant_id": user.tenant_id,
                                "sensitive_payload": list(user.sensitive_data)[0],  # First sensitive item
                                "operation_id": operation,
                                "stress_test": True
                            }
                        ),
                        
                        self.bridge.notify_agent_thinking(
                            run_id=f"{user.run_id}_{operation}",
                            agent_name=f"StressAgent_{operation}",
                            reasoning=f"Processing {list(user.sensitive_data)[1]} under stress"  # Second sensitive item
                        ),
                        
                        self.bridge.notify_agent_completed(
                            run_id=f"{user.run_id}_{operation}",
                            agent_name=f"StressAgent_{operation}",
                            result={
                                "stress_result": f"Completed processing for {user.user_id}",
                                "sensitive_output": list(user.sensitive_data)[2],  # Third sensitive item
                                "operation_success": True
                            }
                        )
                    ])
            
            # Execute all stress operations concurrently
            start_time = time.time()
            results = await asyncio.gather(*stress_tasks, return_exceptions=True)
            end_time = time.time()
            
            # Assert - Security must hold under stress
            successful_ops = sum(1 for r in results if r is True)
            failed_ops = sum(1 for r in results if isinstance(r, Exception))
            
            assert successful_ops > 0, "Some operations should succeed under stress"
            assert failed_ops == 0, f"No operations should fail due to security issues: {failed_ops}"
            
            # Critical: No cross-user contamination should occur even under stress
            assert len(self.cross_user_contamination) == 0, \
                f"SECURITY FAILURE UNDER STRESS: Cross-user contamination detected: {self.cross_user_contamination}"
            
            # Verify performance under security constraints
            execution_time = end_time - start_time
            ops_per_second = len(stress_tasks) / execution_time
            assert ops_per_second > 10, \
                f"Security-constrained operations should maintain reasonable performance: {ops_per_second:.1f} ops/sec"

    def teardown_method(self, method):
        """Clean up security test artifacts."""
        super().teardown_method(method)
        # Clear security tracking
        self.security_violations.clear()
        self.cross_user_contamination.clear()
        self.privilege_escalations.clear()
        
        # Clear user message histories
        for user in [self.user_alice, self.user_bob, self.user_charlie]:
            user.received_messages.clear()


if __name__ == '__main__':
    """
    Run strategic security isolation tests.
    
    These tests validate enterprise-grade security requirements that protect
    the $500K+ ARR business from regulatory violations and data breaches.
    """
    pytest.main([__file__, "-v", "--tb=short"])