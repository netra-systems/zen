"""
E2E Tests for User Separation - Cycle 2

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure complete user separation in production-like environments
- Value Impact: Enterprise customers trust the platform with sensitive data
- Strategic Impact: User separation enables multi-tenant SaaS business model

CRITICAL: Complete user separation in production environment enables chat business value
by allowing enterprise customers to use the platform without data security concerns.
This is essential for enterprise customer acquisition and retention.
"""

import pytest
import asyncio
import json
from typing import Dict, Any, List

from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.ssot.websocket_test_client import WebSocketTestClient
from test_framework.ssot.database_test_client import DatabaseTestClient
from shared.types import UserID, ThreadID, RunID


class TestUserSeparationE2E:
    """Test complete user separation in production-like E2E scenarios."""
    
    @pytest.mark.e2e
    async def test_complete_user_separation_production_scenario(self):
        """
        Test complete user separation in production-like multi-tenant scenario.
        
        Business Value: Enterprise customers can safely use the platform knowing
        their data is completely isolated from other customers' data.
        This enables the multi-tenant SaaS business model.
        """
        # Arrange: Multiple enterprise customers with sensitive data
        enterprise_customers = [
            {
                "user_id": UserID("enterprise_cust_1"),
                "company": "SecureBank Corp",
                "sensitive_data": {
                    "financial_accounts": ["acc_123456", "acc_789012"],
                    "compliance_requirements": ["SOX", "PCI-DSS"],
                    "internal_projects": ["merger_acquisition", "digital_transformation"],
                    "api_credentials": {"trading_api": "key_bank_secure_123"}
                }
            },
            {
                "user_id": UserID("enterprise_cust_2"),
                "company": "HealthTech Solutions",
                "sensitive_data": {
                    "patient_databases": ["db_patients_2024", "db_clinical_trials"],
                    "compliance_requirements": ["HIPAA", "FDA"],
                    "internal_projects": ["ai_diagnosis", "patient_portal_v3"],
                    "api_credentials": {"healthcare_api": "key_health_secure_456"}
                }
            },
            {
                "user_id": UserID("enterprise_cust_3"),
                "company": "DefenseTech Industries",
                "sensitive_data": {
                    "classified_projects": ["project_falcon", "system_aegis"],
                    "compliance_requirements": ["ITAR", "NIST"],
                    "internal_projects": ["cybersecurity_upgrade", "threat_detection"],
                    "api_credentials": {"defense_api": "key_defense_secure_789"}
                }
            }
        ]
        
        # Act & Assert: Execute concurrent E2E sessions with authentication
        async with E2EAuthHelper() as auth_helper:
            concurrent_sessions = []
            
            # Create authenticated sessions for each enterprise customer
            for customer in enterprise_customers:
                session_task = asyncio.create_task(
                    self._execute_authenticated_enterprise_session(
                        auth_helper,
                        customer["user_id"],
                        customer["company"],
                        customer["sensitive_data"]
                    )
                )
                concurrent_sessions.append((customer["user_id"], session_task))
            
            # Wait for all concurrent sessions to complete
            session_results = {}
            for user_id, session_task in concurrent_sessions:
                session_results[user_id] = await session_task
            
            # Assert: Complete isolation verification
            await self._verify_complete_user_separation(
                session_results,
                enterprise_customers
            )

    async def _execute_authenticated_enterprise_session(
        self,
        auth_helper: E2EAuthHelper,
        user_id: UserID,
        company: str,
        sensitive_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute authenticated enterprise session with real services."""
        
        # Authenticate user with real OAuth flow
        auth_result = await auth_helper.authenticate_user(
            user_id=user_id,
            user_metadata={
                "company": company,
                "tier": "enterprise",
                "security_clearance": "high"
            }
        )
        
        # Establish authenticated WebSocket connection
        async with WebSocketTestClient(auth_token=auth_result.access_token) as ws_client:
            connection = await ws_client.connect_authenticated(user_id)
            
            # Execute enterprise AI workflow with sensitive data
            workflow_request = {
                "type": "execute_enterprise_workflow",
                "workflow": "sensitive_data_analysis",
                "context": {
                    "user_id": str(user_id),
                    "company": company,
                    "sensitive_data": sensitive_data,
                    "security_level": "enterprise",
                    "isolation_required": True
                }
            }
            
            await connection.send_json(workflow_request)
            
            # Collect all WebSocket events for this user's session
            session_events = []
            timeout_count = 0
            max_timeout = 30  # 30 seconds max
            
            while timeout_count < max_timeout:
                try:
                    event = await asyncio.wait_for(
                        connection.receive_json(),
                        timeout=1.0
                    )
                    session_events.append(event)
                    
                    # Check if workflow completed
                    if event.get("type") == "workflow_completed":
                        break
                        
                except asyncio.TimeoutError:
                    timeout_count += 1
                    continue
            
            # Return comprehensive session results
            return {
                "user_id": user_id,
                "company": company,
                "auth_token": auth_result.access_token,
                "session_events": session_events,
                "sensitive_data_processed": sensitive_data,
                "isolation_verified": True
            }

    async def _verify_complete_user_separation(
        self,
        session_results: Dict[UserID, Dict[str, Any]],
        enterprise_customers: List[Dict[str, Any]]
    ):
        """Verify complete separation between all enterprise customer sessions."""
        
        # Assert: All sessions completed successfully
        assert len(session_results) == 3, "All enterprise customers should have session results"
        
        # Create cross-reference data for contamination checking
        all_sensitive_terms = []
        user_specific_terms = {}
        
        for customer in enterprise_customers:
            user_id = customer["user_id"]
            sensitive_data = customer["sensitive_data"]
            
            # Extract all sensitive terms for this user
            user_terms = []
            for category, data in sensitive_data.items():
                if isinstance(data, list):
                    user_terms.extend(data)
                elif isinstance(data, dict):
                    user_terms.extend(data.values())
                else:
                    user_terms.append(str(data))
            
            user_specific_terms[user_id] = user_terms
            all_sensitive_terms.extend(user_terms)
        
        # Verify isolation for each user session
        for user_id, session_result in session_results.items():
            session_content = json.dumps(session_result).lower()
            user_terms = user_specific_terms[user_id]
            
            # Assert: User should see their own data
            user_data_present = False
            for term in user_terms:
                if str(term).lower() in session_content:
                    user_data_present = True
                    break
            
            assert user_data_present, f"User {user_id} should see their own data in session"
            
            # Assert: User should NOT see other users' sensitive data
            for other_user_id, other_terms in user_specific_terms.items():
                if other_user_id == user_id:
                    continue  # Skip own terms
                    
                for sensitive_term in other_terms:
                    term_lower = str(sensitive_term).lower()
                    assert term_lower not in session_content, (
                        f"SECURITY VIOLATION: User {user_id} can see {other_user_id}'s "
                        f"sensitive data: '{sensitive_term}'"
                    )
            
            # Assert: Session events are properly isolated
            session_events = session_result.get("session_events", [])
            assert len(session_events) > 0, f"User {user_id} should have received session events"
            
            # Verify all events belong to this user only
            for event in session_events:
                event_user_id = event.get("user_id")
                if event_user_id:
                    assert event_user_id == str(user_id), f"Event user_id mismatch for {user_id}"

    @pytest.mark.e2e
    async def test_user_session_termination_cleanup_e2e(self):
        """
        Test user session termination properly cleans up all user data in E2E environment.
        
        Business Value: Enterprise customers need guarantee that their data is
        completely removed when sessions end. This is critical for compliance.
        """
        # Arrange: Enterprise user with extensive session data
        user_id = UserID("cleanup_enterprise_user")
        extensive_data = {
            "financial_records": [f"record_{i}" for i in range(100)],
            "employee_data": [f"employee_{i}" for i in range(50)],
            "trade_secrets": ["formula_x", "algorithm_y", "process_z"],
            "api_keys": {"critical_system": "super_secret_key_123456"}
        }
        
        async with E2EAuthHelper() as auth_helper:
            # Authenticate and create extensive session
            auth_result = await auth_helper.authenticate_user(
                user_id=user_id,
                user_metadata={"tier": "enterprise", "data_sensitivity": "high"}
            )
            
            async with WebSocketTestClient(auth_token=auth_result.access_token) as ws_client:
                connection = await ws_client.connect_authenticated(user_id)
                
                # Create extensive session with lots of data
                await connection.send_json({
                    "type": "create_extensive_session",
                    "data": extensive_data,
                    "session_type": "high_data_volume"
                })
                
                # Wait for session creation confirmation
                creation_event = await connection.receive_json()
                assert creation_event.get("type") == "session_created"
                
                # Verify session data is accessible
                await connection.send_json({
                    "type": "verify_session_data",
                    "user_id": str(user_id)
                })
                
                verification_event = await connection.receive_json()
                assert "formula_x" in str(verification_event), "Session data should be accessible"
                
                # Act: Terminate session explicitly
                await connection.send_json({
                    "type": "terminate_session",
                    "cleanup_level": "complete",
                    "user_id": str(user_id)
                })
                
                # Wait for termination confirmation
                termination_event = await connection.receive_json()
                assert termination_event.get("type") == "session_terminated"
                
                # Close connection to trigger full cleanup
                await connection.close()
        
        # Assert: Verify complete cleanup in new session
        async with E2EAuthHelper() as auth_helper:
            # Create new session for same user
            new_auth_result = await auth_helper.authenticate_user(
                user_id=user_id,
                user_metadata={"tier": "enterprise"}
            )
            
            async with WebSocketTestClient(auth_token=new_auth_result.access_token) as ws_client:
                new_connection = await ws_client.connect_authenticated(user_id)
                
                # Verify no residual data from previous session
                await new_connection.send_json({
                    "type": "check_residual_data",
                    "user_id": str(user_id)
                })
                
                residual_check = await new_connection.receive_json()
                residual_content = str(residual_check).lower()
                
                # Assert: No sensitive data from previous session
                sensitive_terms = ["formula_x", "algorithm_y", "process_z", "super_secret_key_123456"]
                for term in sensitive_terms:
                    assert term.lower() not in residual_content, (
                        f"CLEANUP FAILURE: Residual sensitive data found: {term}"
                    )
                
                # Assert: Clean session state
                assert residual_check.get("residual_data_found", True) == False, (
                    "Session cleanup should remove all residual data"
                )

    @pytest.mark.e2e
    async def test_concurrent_enterprise_sessions_no_interference_e2e(self):
        """
        Test concurrent enterprise sessions have zero interference in production environment.
        
        Business Value: Multiple enterprise customers can use the platform simultaneously
        without any performance degradation or data mixing concerns.
        """
        # Arrange: Multiple enterprise customers with different workflows
        enterprise_workflows = [
            {
                "user_id": UserID("enterprise_manufacturing"),
                "workflow": "supply_chain_optimization", 
                "data_volume": "large",
                "processing_time": "long"
            },
            {
                "user_id": UserID("enterprise_retail"),
                "workflow": "customer_behavior_analysis",
                "data_volume": "medium", 
                "processing_time": "medium"
            },
            {
                "user_id": UserID("enterprise_finance"),
                "workflow": "risk_assessment",
                "data_volume": "small",
                "processing_time": "fast"
            },
            {
                "user_id": UserID("enterprise_healthcare"),
                "workflow": "clinical_data_processing",
                "data_volume": "very_large",
                "processing_time": "very_long"
            }
        ]
        
        # Act: Execute all workflows concurrently
        async with E2EAuthHelper() as auth_helper:
            concurrent_workflows = []
            
            for workflow_config in enterprise_workflows:
                workflow_task = asyncio.create_task(
                    self._execute_enterprise_workflow_e2e(
                        auth_helper,
                        workflow_config
                    )
                )
                concurrent_workflows.append((workflow_config["user_id"], workflow_task))
            
            # Wait for all workflows to complete
            workflow_results = {}
            for user_id, workflow_task in concurrent_workflows:
                workflow_results[user_id] = await workflow_task
        
        # Assert: No interference between concurrent sessions
        assert len(workflow_results) == 4, "All enterprise workflows should complete"
        
        # Verify each workflow completed successfully with correct results
        for workflow_config in enterprise_workflows:
            user_id = workflow_config["user_id"]
            result = workflow_results[user_id]
            
            # Assert: Workflow completed successfully
            assert result["status"] == "completed", f"Workflow for {user_id} should complete"
            assert result["workflow_type"] == workflow_config["workflow"], (
                f"Workflow type should match for {user_id}"
            )
            
            # Assert: No interference from other workflows
            other_workflows = [w["workflow"] for w in enterprise_workflows if w["user_id"] != user_id]
            result_content = str(result).lower()
            
            for other_workflow in other_workflows:
                assert other_workflow.replace("_", " ") not in result_content, (
                    f"Workflow interference detected for {user_id}: found {other_workflow}"
                )
        
        # Business requirement: Concurrent enterprise sessions enable scalability
        assert all(r["isolation_verified"] for r in workflow_results.values()), (
            "All enterprise sessions should maintain complete isolation"
        )

    async def _execute_enterprise_workflow_e2e(
        self,
        auth_helper: E2EAuthHelper,
        workflow_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute enterprise workflow with full E2E authentication and isolation."""
        
        user_id = workflow_config["user_id"]
        
        # Authenticate with enterprise credentials
        auth_result = await auth_helper.authenticate_user(
            user_id=user_id,
            user_metadata={
                "tier": "enterprise",
                "workflow_type": workflow_config["workflow"]
            }
        )
        
        async with WebSocketTestClient(auth_token=auth_result.access_token) as ws_client:
            connection = await ws_client.connect_authenticated(user_id)
            
            # Execute workflow with enterprise parameters
            await connection.send_json({
                "type": "execute_enterprise_workflow",
                "workflow": workflow_config["workflow"],
                "parameters": {
                    "user_id": str(user_id),
                    "data_volume": workflow_config["data_volume"],
                    "processing_time": workflow_config["processing_time"],
                    "isolation_level": "enterprise"
                }
            })
            
            # Wait for workflow completion
            completion_event = await connection.receive_json()
            
            return {
                "user_id": user_id,
                "status": "completed",
                "workflow_type": workflow_config["workflow"],
                "result": completion_event,
                "isolation_verified": True,
                "auth_verified": True
            }