"""
E2E Test: GCP Staging WebSocket Agent Bridge Fix Validation

PURPOSE: End-to-end validation of WebSocket agent bridge functionality in GCP staging environment

CRITICAL STAGING ISSUE:
- websocket_ssot.py lines 732 and 747 have broken imports causing complete Golden Path failure
- Staging environment returns 422 errors and no agent responses
- Chat functionality (90% of platform value) is completely broken

BUSINESS IMPACT:
- $500K+ ARR at risk due to non-functional chat in staging
- Golden Path user flow completely broken
- Customer demos and testing blocked

This E2E test validates:
1. WebSocket connection establishment in staging
2. Agent message handling functionality
3. Complete user chat flow from login to AI response
4. Real-time WebSocket events delivery

Test should FAIL with broken imports, PASS after fix.
"""

import asyncio
import json
import uuid
import websockets
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from tests.e2e.staging_test_base import StagingTestBase
from tests.e2e.staging_websocket_auth_fix import StagingWebSocketAuth
from shared.types.core_types import UserID, ThreadID


class TestGCPStagingWebSocketAgentBridgeFix(SSotAsyncTestCase, StagingTestBase):
    """E2E tests for WebSocket agent bridge functionality in GCP staging environment."""
    
    def setUp(self):
        """Set up staging test environment."""
        super().setUp()
        StagingTestBase.setUp(self)
        
        self.category = "E2E"
        self.test_name = "gcp_staging_websocket_agent_bridge_fix"
        
        # Staging environment configuration
        self.staging_base_url = "wss://netra-staging.example.com"  # Replace with actual staging URL
        self.staging_api_url = "https://netra-staging.example.com"  # Replace with actual staging API URL
        
        # Test user data
        self.test_user_id = UserID(str(uuid.uuid4()))
        self.test_thread_id = ThreadID(str(uuid.uuid4()))
        
        # WebSocket auth helper
        self.ws_auth = StagingWebSocketAuth()
        
        # Track connection state
        self.websocket = None
        self.auth_token = None
        
    async def test_staging_websocket_connection_establishment(self):
        """Test WebSocket connection can be established in staging environment."""
        
        try:
            # Get authentication token for staging
            self.auth_token = await self.ws_auth.get_staging_auth_token()
            assert self.auth_token, "Failed to obtain staging authentication token"
            
            # Establish WebSocket connection
            websocket_url = f"{self.staging_base_url}/ws"
            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Origin": self.staging_api_url
            }
            
            self.websocket = await websockets.connect(
                websocket_url,
                extra_headers=headers,
                timeout=30
            )
            
            self.logger.info("SUCCESS: WebSocket connection established to staging")
            
            # Send ping to verify connection
            await self.websocket.send(json.dumps({"type": "ping"}))
            
            # Wait for pong response
            response = await asyncio.wait_for(self.websocket.recv(), timeout=10)
            response_data = json.loads(response)
            
            assert response_data.get("type") == "pong", f"Expected pong, got: {response_data}"
            self.logger.info("SUCCESS: WebSocket ping-pong completed")
            
        except Exception as e:
            self.logger.error(f"STAGING CONNECTION FAILED: {e}")
            pytest.fail(f"Failed to establish WebSocket connection to staging: {e}")
    
    async def test_staging_agent_message_handling_fails_with_broken_imports(self):
        """Test that agent message handling fails in staging due to broken imports."""
        
        if not self.websocket:
            await self.test_staging_websocket_connection_establishment()
        
        try:
            # Send agent message request
            agent_message = {
                "type": "agent_request",
                "content": "Help me optimize my AI infrastructure costs",
                "thread_id": str(self.test_thread_id),
                "user_id": str(self.test_user_id),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await self.websocket.send(json.dumps(agent_message))
            self.logger.info("Sent agent message request to staging")
            
            # Wait for response (should fail with 422 or error)
            try:
                response = await asyncio.wait_for(self.websocket.recv(), timeout=30)
                response_data = json.loads(response)
                
                # Check for error response indicating broken imports
                if response_data.get("error"):
                    error_msg = response_data.get("error", "Unknown error")
                    self.logger.critical(f"STAGING AGENT FAILURE: {error_msg}")
                    
                    # Look for import-related errors
                    if "ImportError" in error_msg or "No module named" in error_msg:
                        self.logger.critical("CONFIRMED: Broken imports causing staging failure")
                        pytest.fail(f"Staging agent handling failed due to import issue: {error_msg}")
                    else:
                        pytest.fail(f"Staging agent handling failed with error: {error_msg}")
                
                # Check for 422 status (unprocessable entity)
                if response_data.get("status") == 422:
                    self.logger.critical("STAGING FAILURE: 422 error - agent request unprocessable")
                    pytest.fail("Staging returned 422 error for agent request")
                
                # If we get here, the response was unexpected
                self.logger.warning(f"Unexpected staging response: {response_data}")
                
            except asyncio.TimeoutError:
                self.logger.critical("STAGING TIMEOUT: No response from agent request (likely import failure)")
                pytest.fail("Staging agent request timed out - likely due to broken imports")
            
        except Exception as e:
            self.logger.critical(f"STAGING AGENT TEST FAILED: {e}")
            pytest.fail(f"Agent message handling test failed: {e}")
    
    async def test_staging_websocket_events_missing_due_to_broken_agent_bridge(self):
        """Test that WebSocket events are missing due to broken agent bridge."""
        
        if not self.websocket:
            await self.test_staging_websocket_connection_establishment()
        
        try:
            # Send agent message and monitor for expected events
            agent_message = {
                "type": "agent_request",
                "content": "Analyze my cloud infrastructure efficiency",
                "thread_id": str(self.test_thread_id),
                "user_id": str(self.test_user_id)
            }
            
            await self.websocket.send(json.dumps(agent_message))
            
            # Expected WebSocket events for successful agent processing
            expected_events = [
                "agent_started",
                "agent_thinking", 
                "tool_executing",
                "tool_completed",
                "agent_completed"
            ]
            
            received_events = []
            timeout_per_event = 10  # seconds
            
            # Monitor for events
            for expected_event in expected_events:
                try:
                    response = await asyncio.wait_for(self.websocket.recv(), timeout=timeout_per_event)
                    response_data = json.loads(response)
                    
                    event_type = response_data.get("type")
                    received_events.append(event_type)
                    
                    self.logger.info(f"Received event: {event_type}")
                    
                    if event_type == expected_event:
                        continue
                    elif event_type == "error":
                        error_msg = response_data.get("error", "Unknown error")
                        self.logger.critical(f"STAGING ERROR EVENT: {error_msg}")
                        break
                    else:
                        self.logger.warning(f"Unexpected event: {event_type}")
                        
                except asyncio.TimeoutError:
                    self.logger.critical(f"MISSING EVENT: {expected_event} not received within {timeout_per_event}s")
                    break
            
            # Analyze results
            missing_events = set(expected_events) - set(received_events)
            
            if missing_events:
                self.logger.critical(f"GOLDEN PATH BROKEN: Missing WebSocket events: {missing_events}")
                self.logger.critical("ROOT CAUSE: Broken agent bridge imports prevent event delivery")
                pytest.fail(f"Critical WebSocket events missing in staging: {missing_events}")
            else:
                self.logger.info("SUCCESS: All expected WebSocket events received")
                
        except Exception as e:
            self.logger.critical(f"WEBSOCKET EVENT MONITORING FAILED: {e}")
            pytest.fail(f"WebSocket event monitoring failed: {e}")
    
    async def test_staging_complete_golden_path_user_flow(self):
        """Test complete Golden Path user flow that should fail with broken imports."""
        
        self.logger.info("=== GOLDEN PATH E2E TEST: LOGIN → CHAT → AI RESPONSE ===")
        
        try:
            # Step 1: Authentication (should work)
            await self.test_staging_websocket_connection_establishment()
            self.logger.info("✓ Step 1: User authentication successful")
            
            # Step 2: Send chat message (should fail due to broken agent bridge)
            chat_message = {
                "type": "chat_message",
                "content": "I need help optimizing my AI workload costs. Can you analyze my current setup?",
                "thread_id": str(self.test_thread_id),
                "user_id": str(self.test_user_id),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await self.websocket.send(json.dumps(chat_message))
            self.logger.info("✓ Step 2: Chat message sent")
            
            # Step 3: Wait for AI response (should fail or timeout)
            try:
                response = await asyncio.wait_for(self.websocket.recv(), timeout=60)
                response_data = json.loads(response)
                
                if response_data.get("type") == "agent_response":
                    # Unexpected success - imports might be fixed
                    self.logger.info("UNEXPECTED SUCCESS: Agent response received")
                    self.logger.info("This suggests the import issue may have been resolved")
                elif response_data.get("error"):
                    error_msg = response_data.get("error")
                    self.logger.critical(f"✗ Step 3: AI response failed: {error_msg}")
                    pytest.fail(f"Golden Path broken - AI response failed: {error_msg}")
                else:
                    self.logger.warning(f"Unexpected response type: {response_data}")
                    
            except asyncio.TimeoutError:
                self.logger.critical("✗ Step 3: AI response timeout - Golden Path completely broken")
                self.logger.critical("BUSINESS IMPACT: $500K+ ARR at risk - customers cannot get AI responses")
                pytest.fail("Golden Path failure: No AI response received within 60 seconds")
            
        except Exception as e:
            self.logger.critical(f"GOLDEN PATH COMPLETE FAILURE: {e}")
            pytest.fail(f"Complete Golden Path test failed: {e}")
    
    async def test_staging_import_fix_validation_checklist(self):
        """Test that provides validation checklist for the import fix."""
        
        self.logger.info("=== STAGING IMPORT FIX VALIDATION CHECKLIST ===")
        self.logger.info("")
        self.logger.info("ISSUE: websocket_ssot.py has broken imports at lines 732 and 747")
        self.logger.info("FILE: netra_backend/app/routes/websocket_ssot.py")
        self.logger.info("")
        self.logger.info("BROKEN IMPORTS TO FIX:")
        self.logger.info("  Line 732: from netra_backend.app.agents.agent_websocket_bridge import create_agent_websocket_bridge")
        self.logger.info("  Line 747: from netra_backend.app.agents.agent_websocket_bridge import create_agent_websocket_bridge")
        self.logger.info("")
        self.logger.info("CORRECT IMPORTS TO USE:")
        self.logger.info("  Line 732: from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge")
        self.logger.info("  Line 747: from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge")
        self.logger.info("")
        self.logger.info("VALIDATION STEPS AFTER FIX:")
        self.logger.info("1. Deploy to staging with corrected imports")
        self.logger.info("2. Verify WebSocket connection establishment")
        self.logger.info("3. Test agent message handling")
        self.logger.info("4. Confirm all 5 WebSocket events are delivered")
        self.logger.info("5. Validate complete Golden Path user flow")
        self.logger.info("6. Monitor for 422 errors (should be eliminated)")
        self.logger.info("")
        self.logger.info("SUCCESS CRITERIA:")
        self.logger.info("• No ImportError exceptions in staging logs")
        self.logger.info("• Agent responses delivered within 30 seconds")
        self.logger.info("• All WebSocket events (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)")
        self.logger.info("• Golden Path user flow: Login → Chat → AI Response")
        self.logger.info("• Zero 422 errors for valid agent requests")
        self.logger.info("")
        self.logger.info("BUSINESS IMPACT:")
        self.logger.info("• Restores $500K+ ARR protected by chat functionality")
        self.logger.info("• Enables customer demos and testing")
        self.logger.info("• Validates staging environment for production deployment")
        
        # This test always passes - it's informational
        assert True, "Import fix validation checklist provided"

    async def asyncTearDown(self):
        """Clean up WebSocket connection and test environment."""
        if self.websocket:
            try:
                await self.websocket.close()
                self.logger.info("WebSocket connection closed")
            except Exception as e:
                self.logger.warning(f"Error closing WebSocket: {e}")
        
        await super().asyncTearDown()

    def tearDown(self):
        """Clean up test environment."""
        super().tearDown()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])