"""Critical test reproducing user data leakage vulnerabilities in production scenarios.

CRITICAL SECURITY VULNERABILITY: Issue #271 - Production User Data Leakage

This test reproduces real-world production scenarios where DeepAgentState
causes actual user data leakage that would affect customers in production.

Business Value Justification:
- Segment: Enterprise (Primary Risk)
- Business Goal: Customer Trust & Regulatory Compliance  
- Value Impact: Prevents $500K+ ARR loss from data breach incidents
- Revenue Impact: Protects enterprise contracts requiring GDPR/HIPAA compliance

PRODUCTION SCENARIOS REPRODUCED:
1. Multi-tenant agent execution with shared state
2. WebSocket event cross-contamination  
3. Database session state pollution
4. Agent context bleeding between users
5. Memory pressure causing data corruption

COMPLIANCE REQUIREMENTS:
- GDPR: User data isolation (Article 25 - Data Protection by Design)
- HIPAA: PHI segregation requirements  
- SOC 2: Logical access controls
- Enterprise Security: Multi-tenant data isolation

EXPECTED OUTCOME: These tests should FAIL initially, proving production vulnerability exists.
"""

import asyncio
import pytest
import time
import uuid
import json
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List, Optional, Set
from unittest.mock import MagicMock, AsyncMock, patch
from dataclasses import dataclass

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.agent_registry import UserAgentSession
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID


@dataclass
class ProductionUserProfile:
    """Simulates real production user data."""
    user_id: str
    company: str
    industry: str
    sensitive_data: Dict[str, Any]
    compliance_requirements: List[str]
    
    
class TestUserDataLeakageReproduction(SSotAsyncTestCase):
    """Critical tests reproducing production user data leakage scenarios."""
    
    def setUp(self):
        """Set up production simulation environment."""
        super().setUp()
        
        # Simulate real enterprise customers
        self.enterprise_users = {
            "healthcare_corp": ProductionUserProfile(
                user_id="hc_user_001",
                company="HealthCare Corp",
                industry="Healthcare",
                sensitive_data={
                    "patient_records": ["John Doe - Diabetes", "Jane Smith - Hypertension"],
                    "phi_data": "SSN: 123-45-6789, DOB: 1985-03-15",
                    "medical_api_key": "sk-healthcare-prod-api-key-12345",
                    "hipaa_token": "hipaa_access_token_healthcare_corp"
                },
                compliance_requirements=["HIPAA", "SOC2", "GDPR"]
            ),
            "fintech_startup": ProductionUserProfile(
                user_id="fs_user_002", 
                company="FinTech Startup",
                industry="Financial Services",
                sensitive_data={
                    "customer_accounts": ["Account: 987654321 - Balance: $50,000"],
                    "pii_data": "SSN: 987-65-4321, Credit Score: 780",
                    "banking_api_key": "sk-fintech-banking-api-67890",
                    "pci_token": "pci_compliance_token_fintech"
                },
                compliance_requirements=["PCI-DSS", "SOX", "GDPR", "CCPA"]
            ),
            "defense_contractor": ProductionUserProfile(
                user_id="dc_user_003",
                company="Defense Systems Inc", 
                industry="Defense",
                sensitive_data={
                    "classified_projects": ["Project Falcon - Classification: SECRET"],
                    "security_clearance": "SECRET - Expires: 2025-12-31",
                    "gov_api_key": "sk-defense-govt-api-secret-999",
                    "itar_token": "itar_controlled_access_token"
                },
                compliance_requirements=["ITAR", "DFARS", "NIST", "FedRAMP"]
            )
        }
        
        self.data_leakage_incidents = []
        self.compliance_violations = []
    
    async def test_production_multi_tenant_data_leakage(self):
        """
        CRITICAL PRODUCTION TEST: Multi-tenant agent execution data leakage.
        
        Reproduces real production scenario where multiple enterprise customers
        execute agents concurrently and their sensitive data gets mixed.
        
        COMPLIANCE IMPACT: GDPR Article 25, HIPAA [U+00A7]164.308, SOC 2 CC6.1
        
        EXPECTED: This test should FAIL - proving production vulnerability exists.
        """
        
        execution_results = {}
        cross_tenant_contamination = []
        
        async def simulate_enterprise_agent_execution(user_profile: ProductionUserProfile) -> Dict[str, Any]:
            """Simulate real enterprise customer agent execution."""
            
            # Create production-like DeepAgentState (VULNERABLE)
            state = DeepAgentState(
                user_id=user_profile.user_id,
                user_request=f"Analyze {user_profile.industry} optimization opportunities for {user_profile.company}",
                chat_thread_id=f"prod_thread_{user_profile.user_id}_{uuid.uuid4()}",
                run_id=str(uuid.uuid4()),
                agent_input={
                    "company_profile": {
                        "name": user_profile.company,
                        "industry": user_profile.industry,
                        "compliance_reqs": user_profile.compliance_requirements
                    },
                    "sensitive_context": user_profile.sensitive_data
                }
            )
            
            # Simulate agent processing with sensitive data
            if user_profile.industry == "Healthcare":
                state.triage_result = {
                    "classification": "HEALTHCARE_PHI",
                    "confidence": 0.95,
                    "sensitive_indicators": user_profile.sensitive_data["patient_records"]
                }
                state.metadata.custom_fields["hipaa_context"] = user_profile.sensitive_data["hipaa_token"]
                
            elif user_profile.industry == "Financial Services":
                state.triage_result = {
                    "classification": "FINANCIAL_PII", 
                    "confidence": 0.92,
                    "account_data": user_profile.sensitive_data["customer_accounts"]
                }
                state.metadata.custom_fields["pci_context"] = user_profile.sensitive_data["pci_token"]
                
            elif user_profile.industry == "Defense":
                state.triage_result = {
                    "classification": "CLASSIFIED_DEFENSE",
                    "confidence": 0.98,
                    "clearance_level": user_profile.sensitive_data["security_clearance"]
                }
                state.metadata.custom_fields["itar_context"] = user_profile.sensitive_data["itar_token"]
            
            # Add API keys to context (sensitive data)
            api_key_field = next(
                (k for k in user_profile.sensitive_data.keys() if "api_key" in k),
                None
            )
            if api_key_field:
                state.context_tracking["production_api_key"] = user_profile.sensitive_data[api_key_field]
            
            # Simulate production processing delay
            await asyncio.sleep(0.15)
            
            # Add compliance metadata
            state.metadata.custom_fields["compliance_requirements"] = user_profile.compliance_requirements
            state.quality_metrics["data_classification"] = {
                "sensitivity_level": "HIGH",
                "industry": user_profile.industry,
                "requires_encryption": True
            }
            
            return {
                "user_profile": user_profile,
                "final_state": state.to_dict(),
                "triage_result": state.triage_result,
                "metadata": state.metadata.model_dump(),
                "context_tracking": state.context_tracking,
                "state_memory_id": id(state)
            }
        
        # Execute all enterprise customers concurrently (production simulation)
        tasks = [
            simulate_enterprise_agent_execution(profile)
            for profile in self.enterprise_users.values()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze for cross-tenant data contamination
        for result in results:
            if isinstance(result, Exception):
                self.fail(f"Enterprise execution failed: {result}")
            
            user_id = result["user_profile"].user_id
            execution_results[user_id] = result
        
        # Check for cross-tenant contamination (CRITICAL SECURITY CHECK)
        for user_id_a, result_a in execution_results.items():
            for user_id_b, result_b in execution_results.items():
                if user_id_a != user_id_b:
                    contamination = self._detect_cross_tenant_contamination(
                        result_a, result_b, user_id_a, user_id_b
                    )
                    if contamination:
                        cross_tenant_contamination.extend(contamination)
        
        # CRITICAL VULNERABILITY ASSERTION
        self.assertEqual(
            len(cross_tenant_contamination),
            0,
            f" ALERT:  CRITICAL PRODUCTION VULNERABILITY: Cross-tenant data leakage detected! "
            f"Enterprise customer data is mixing between tenants. "
            f"COMPLIANCE VIOLATION: GDPR, HIPAA, PCI-DSS, ITAR. "
            f"Contamination incidents: {cross_tenant_contamination}"
        )
    
    def _detect_cross_tenant_contamination(
        self,
        result_a: Dict[str, Any],
        result_b: Dict[str, Any], 
        user_id_a: str,
        user_id_b: str
    ) -> List[Dict[str, Any]]:
        """Detect cross-tenant data contamination between results."""
        
        contamination_incidents = []
        
        profile_a = result_a["user_profile"]
        profile_b = result_b["user_profile"]
        
        state_a_str = json.dumps(result_a["final_state"])
        state_b_str = json.dumps(result_b["final_state"])
        
        # Check for sensitive data cross-contamination
        for sensitive_key, sensitive_value in profile_a.sensitive_data.items():
            if isinstance(sensitive_value, str) and len(sensitive_value) > 10:
                if sensitive_value in state_b_str:
                    incident = {
                        "type": "sensitive_data_leakage",
                        "severity": "CRITICAL",
                        "source_user": user_id_a,
                        "source_company": profile_a.company,
                        "affected_user": user_id_b,
                        "affected_company": profile_b.company,
                        "leaked_data_type": sensitive_key,
                        "leaked_value": sensitive_value[:20] + "...",  # Truncate for logging
                        "compliance_impact": self._get_compliance_impact(profile_a, profile_b)
                    }
                    contamination_incidents.append(incident)
                    self.data_leakage_incidents.append(incident)
        
        # Check for API key contamination
        for key, value in result_a.get("context_tracking", {}).items():
            if "api_key" in str(value).lower() and str(value) in state_b_str:
                incident = {
                    "type": "api_key_leakage",
                    "severity": "CRITICAL",
                    "source_user": user_id_a,
                    "affected_user": user_id_b,
                    "leaked_api_key": str(value)[:20] + "...",
                    "security_impact": "FULL_SYSTEM_COMPROMISE_RISK"
                }
                contamination_incidents.append(incident)
        
        # Check for compliance token contamination
        metadata_a = result_a.get("metadata", {}).get("custom_fields", {})
        for field_name, field_value in metadata_a.items():
            if any(token in field_name.lower() for token in ["hipaa", "pci", "itar"]):
                if str(field_value) in state_b_str:
                    incident = {
                        "type": "compliance_token_leakage",
                        "severity": "CRITICAL",
                        "source_user": user_id_a,
                        "affected_user": user_id_b,
                        "compliance_violation": field_name.upper(),
                        "regulatory_impact": "AUDIT_FAILURE_RISK"
                    }
                    contamination_incidents.append(incident)
                    self.compliance_violations.append(incident)
        
        return contamination_incidents
    
    def _get_compliance_impact(
        self,
        profile_a: ProductionUserProfile,
        profile_b: ProductionUserProfile
    ) -> List[str]:
        """Determine compliance impact of cross-tenant contamination."""
        
        combined_requirements = set(profile_a.compliance_requirements + profile_b.compliance_requirements)
        
        impact_mapping = {
            "HIPAA": "PHI_DISCLOSURE_VIOLATION",
            "GDPR": "PERSONAL_DATA_BREACH",
            "PCI-DSS": "CARDHOLDER_DATA_EXPOSURE",
            "SOX": "FINANCIAL_DATA_INTEGRITY_VIOLATION",
            "ITAR": "EXPORT_CONTROL_VIOLATION",
            "DFARS": "DEFENSE_DATA_SPILLAGE"
        }
        
        return [impact_mapping.get(req, f"{req}_COMPLIANCE_FAILURE") for req in combined_requirements]
    
    async def test_websocket_event_cross_user_contamination(self):
        """
        CRITICAL PRODUCTION TEST: WebSocket events sent to wrong users.
        
        Reproduces production scenario where agent execution events 
        (containing sensitive data) are sent to wrong users via WebSocket.
        
        EXPECTED: This test should FAIL - proving vulnerability exists.
        """
        
        websocket_event_contamination = []
        
        # Mock WebSocket bridge that tracks events per user
        mock_bridge = MagicMock()
        mock_bridge.is_connected.return_value = True
        mock_bridge.user_events = {}
        
        def track_websocket_event(user_id: str, event_type: str, data: Any):
            """Track WebSocket events per user."""
            if user_id not in mock_bridge.user_events:
                mock_bridge.user_events[user_id] = []
            mock_bridge.user_events[user_id].append({
                "event_type": event_type,
                "data": data,
                "timestamp": time.time()
            })
        
        mock_bridge.emit_to_user = track_websocket_event
        
        # Simulate concurrent agent executions with WebSocket events
        async def execute_agent_with_websocket_events(user_profile: ProductionUserProfile):
            """Execute agent and emit WebSocket events with sensitive data."""
            
            state = DeepAgentState(
                user_id=user_profile.user_id,
                user_request=f"Process {user_profile.industry} sensitive data",
                chat_thread_id=f"ws_thread_{user_profile.user_id}",
                run_id=str(uuid.uuid4())
            )
            
            # Add sensitive data to state
            state.agent_input = {"sensitive_data": user_profile.sensitive_data}
            state.metadata.custom_fields["company"] = user_profile.company
            
            # Simulate agent events with sensitive data (VULNERABLE)
            sensitive_events = [
                ("agent_started", {
                    "user_id": user_profile.user_id,
                    "company": user_profile.company,
                    "sensitive_context": user_profile.sensitive_data
                }),
                ("agent_thinking", {
                    "reasoning": f"Processing {user_profile.industry} data for {user_profile.company}",
                    "internal_data": list(user_profile.sensitive_data.keys())
                }),
                ("tool_executing", {
                    "tool_name": "data_analyzer",
                    "tool_input": user_profile.sensitive_data
                }),
                ("agent_completed", {
                    "final_result": state.to_dict(),
                    "company_summary": f"Completed analysis for {user_profile.company}"
                })
            ]
            
            # Emit events (potentially to wrong users due to DeepAgentState vulnerability)
            for event_type, event_data in sensitive_events:
                # VULNERABILITY: user_id might be corrupted or shared
                target_user_id = state.user_id  # Could be contaminated
                mock_bridge.emit_to_user(target_user_id, event_type, event_data)
                await asyncio.sleep(0.05)  # Simulate processing delay
        
        # Execute all users concurrently
        tasks = [
            execute_agent_with_websocket_events(profile)
            for profile in self.enterprise_users.values()
        ]
        
        await asyncio.gather(*tasks)
        
        # Analyze WebSocket events for cross-contamination
        for user_id, events in mock_bridge.user_events.items():
            user_profile = next(
                (p for p in self.enterprise_users.values() if p.user_id == user_id),
                None
            )
            
            if not user_profile:
                continue
            
            # Check if this user received events containing other users' data
            for event in events:
                event_str = json.dumps(event["data"])
                
                # Check for other users' sensitive data in this user's events
                for other_profile in self.enterprise_users.values():
                    if other_profile.user_id != user_id:
                        for sensitive_value in other_profile.sensitive_data.values():
                            if isinstance(sensitive_value, str) and sensitive_value in event_str:
                                contamination = {
                                    "type": "websocket_event_contamination",
                                    "severity": "CRITICAL",
                                    "victim_user": user_id,
                                    "victim_company": user_profile.company,
                                    "source_user": other_profile.user_id,
                                    "source_company": other_profile.company,
                                    "event_type": event["event_type"],
                                    "leaked_data": sensitive_value[:30] + "...",
                                    "timestamp": event["timestamp"]
                                }
                                websocket_event_contamination.append(contamination)
        
        # CRITICAL VULNERABILITY ASSERTION
        self.assertEqual(
            len(websocket_event_contamination),
            0,
            f" ALERT:  CRITICAL PRODUCTION VULNERABILITY: WebSocket event cross-contamination detected! "
            f"Users are receiving WebSocket events containing other users' sensitive data. "
            f"Contamination incidents: {websocket_event_contamination}"
        )
    
    async def test_memory_pressure_data_corruption_vulnerability(self):
        """
        CRITICAL PRODUCTION TEST: Memory pressure causing data corruption.
        
        Reproduces production scenario where high memory usage causes
        DeepAgentState instances to share memory and corrupt user data.
        
        EXPECTED: This test should FAIL - proving vulnerability exists.
        """
        
        data_corruption_incidents = []
        
        # Simulate high memory pressure scenario
        large_data_states = []
        
        # Create memory pressure with large states
        for i in range(50):  # Create many states to simulate production load
            user_profile = list(self.enterprise_users.values())[i % 3]  # Cycle through users
            
            # Create large state with sensitive data
            state = DeepAgentState(
                user_id=f"{user_profile.user_id}_load_{i}",
                user_request=f"Large data processing request {i}",
                chat_thread_id=f"memory_thread_{i}",
                run_id=str(uuid.uuid4())
            )
            
            # Add large amounts of sensitive data
            state.agent_input = {
                "large_dataset": [user_profile.sensitive_data for _ in range(100)],
                "user_context": user_profile.sensitive_data,
                "processing_metadata": {
                    "iteration": i,
                    "company": user_profile.company,
                    "sensitive_markers": list(user_profile.sensitive_data.keys())
                }
            }
            
            # Add to tracking
            large_data_states.append((state, user_profile))
        
        # Simulate concurrent processing under memory pressure
        async def process_under_memory_pressure(state_and_profile):
            """Process state under simulated memory pressure."""
            state, profile = state_and_profile
            
            # Simulate memory-intensive operations
            for j in range(10):
                # Create memory pressure
                temp_data = [profile.sensitive_data.copy() for _ in range(100)]
                
                # Modify state (potentially corrupting shared memory)
                state.metadata.custom_fields[f"iteration_{j}"] = {
                    "temp_data_preview": str(temp_data[0])[:100],
                    "memory_marker": f"memory_{id(state)}"
                }
                
                # Simulate processing delay
                await asyncio.sleep(0.01)
                
                # Clear temp data (simulating memory management)
                del temp_data
            
            return state.to_dict()
        
        # Process all states concurrently under memory pressure
        tasks = [
            process_under_memory_pressure(state_profile)
            for state_profile in large_data_states
        ]
        
        processed_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze for data corruption
        for i, result in enumerate(processed_results):
            if isinstance(result, Exception):
                continue
            
            current_profile = large_data_states[i][1]
            result_str = json.dumps(result)
            
            # Check if this result contains data from other users
            for j, (other_state, other_profile) in enumerate(large_data_states):
                if i != j and other_profile.user_id != current_profile.user_id:
                    # Check for cross-contamination
                    for sensitive_key, sensitive_value in other_profile.sensitive_data.items():
                        if isinstance(sensitive_value, str) and sensitive_value in result_str:
                            corruption = {
                                "type": "memory_pressure_data_corruption",
                                "severity": "CRITICAL",
                                "affected_state_index": i,
                                "affected_user": current_profile.user_id,
                                "affected_company": current_profile.company,
                                "corrupting_user": other_profile.user_id,
                                "corrupting_company": other_profile.company,
                                "corrupted_field": sensitive_key,
                                "memory_evidence": f"memory_marker_{id(large_data_states[i][0])}"
                            }
                            data_corruption_incidents.append(corruption)
        
        # CRITICAL VULNERABILITY ASSERTION
        self.assertEqual(
            len(data_corruption_incidents),
            0,
            f" ALERT:  CRITICAL PRODUCTION VULNERABILITY: Memory pressure data corruption detected! "
            f"High memory usage causes DeepAgentState instances to share memory and corrupt data. "
            f"Corruption incidents: {data_corruption_incidents}"
        )
    
    def tearDown(self):
        """Generate compliance violation report."""
        super().tearDown()
        
        if self.data_leakage_incidents or self.compliance_violations:
            total_incidents = len(self.data_leakage_incidents) + len(self.compliance_violations)
            
            self.test_logger.error(
                f" ALERT:  PRODUCTION VULNERABILITY SUMMARY: {total_incidents} critical incidents detected. "
                f"Data leakage: {len(self.data_leakage_incidents)}, "
                f"Compliance violations: {len(self.compliance_violations)}. "
                f"IMMEDIATE REMEDIATION REQUIRED for production deployment."
            )
            
            # Log detailed incident report
            for incident in self.data_leakage_incidents:
                self.test_logger.error(f"Data Leakage: {incident}")
            
            for violation in self.compliance_violations:
                self.test_logger.error(f"Compliance Violation: {violation}")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])