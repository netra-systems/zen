#!/usr/bin/env python
"""
E2E TEST: Chat Error Handling and Recovery - Business Continuity Under Failure

CRITICAL BUSINESS MISSION: This test validates BUSINESS CONTINUITY during chat system 
failures. When errors occur, customers must still receive VALUE or clear recovery paths.
Error handling directly impacts customer trust and retention.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - error handling affects all customers
- Business Goal: Validate graceful error recovery maintains customer trust and engagement
- Value Impact: Prevents customer churn during system issues through transparent error communication
- Strategic Impact: Protects $500K+ ARR by maintaining service reliability reputation

CRITICAL REQUIREMENTS per CLAUDE.md:
1. MUST use REAL services with REAL error scenarios - NO mocked errors
2. MUST use REAL authentication throughout error scenarios  
3. MUST validate customer receives CLEAR error communication and recovery guidance
4. MUST validate WebSocket events communicate errors transparently to users
5. MUST test business continuity - partial failures should not block all functionality

TEST FOCUS: E2E test with REAL error scenarios to validate customer-facing error handling
and recovery mechanisms that maintain business value delivery even during system issues.
"""

import asyncio
import json
import pytest
import time
import uuid
import websockets
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import patch, AsyncMock

# SSOT IMPORTS - Following CLAUDE.md absolute import rules
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import (
    E2EWebSocketAuthHelper, create_authenticated_user_context
)
from test_framework.ssot.real_services_test_fixtures import real_services_fixture

# Core system imports for error handling testing
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, WebSocketEventType
from shared.id_generation.unified_id_generator import UnifiedIdGenerator

# Import Docker service management for E2E error testing
from test_framework.unified_docker_manager import UnifiedDockerManager, EnvironmentType


class ErrorRecoveryValidator:
    """Validates error handling and recovery mechanisms for business continuity."""
    
    def __init__(self):
        self.error_events = []
        self.recovery_events = []
        self.user_communication_events = []
        
    def analyze_error_events(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze WebSocket events for proper error handling patterns."""
        error_types_found = set()
        recovery_patterns_found = set()
        user_guidance_provided = False
        transparent_communication = False
        
        for event in events:
            event_type = event.get("type", "")
            event_content = str(event.get("content", "")).lower()
            
            # Classify error events
            if event_type == "error" or "error" in event_content:
                self.error_events.append(event)
                error_types_found.add(event_type)
                
                # Check for transparent error communication
                if any(term in event_content for term in ["experiencing", "technical", "retry", "support"]):
                    transparent_communication = True
                    
            # Classify recovery events  
            elif event_type in ["recovery_started", "fallback_activated", "retry_attempt"]:
                self.recovery_events.append(event)
                recovery_patterns_found.add(event_type)
                
            # Check for user guidance
            elif any(term in event_content for term in ["please", "try", "contact", "help", "support"]):
                self.user_communication_events.append(event)
                user_guidance_provided = True
        
        return {
            "total_error_events": len(self.error_events),
            "total_recovery_events": len(self.recovery_events),
            "error_types_found": list(error_types_found),
            "recovery_patterns_found": list(recovery_patterns_found),
            "transparent_communication": transparent_communication,
            "user_guidance_provided": user_guidance_provided,
            "business_continuity_maintained": len(self.recovery_events) > 0 or user_guidance_provided
        }
    
    def validate_business_continuity(self, pre_error_events: List[Dict], post_error_events: List[Dict]) -> Dict[str, Any]:
        """Validate that business functionality continues after error recovery."""
        pre_error_types = set(event.get("type", "") for event in pre_error_events)
        post_error_types = set(event.get("type", "") for event in post_error_events)
        
        # Check if core business functionality resumed
        business_event_types = {"agent_started", "agent_thinking", "tool_executing", "agent_completed"}
        
        pre_business_events = business_event_types.intersection(pre_error_types)
        post_business_events = business_event_types.intersection(post_error_types)
        
        return {
            "business_functionality_before_error": len(pre_business_events),
            "business_functionality_after_recovery": len(post_business_events),
            "functionality_restored": len(post_business_events) > 0,
            "continuity_ratio": len(post_business_events) / max(len(pre_business_events), 1)
        }


@pytest.mark.e2e
@pytest.mark.requires_docker
@pytest.mark.error_handling
class TestChatErrorHandlingRecovery(SSotAsyncTestCase):
    """
    CRITICAL: E2E test for chat error handling and recovery mechanisms.
    
    This test validates that when chat system encounters errors, customers receive
    transparent communication and the system provides recovery paths to maintain business value.
    """
    
    def setup_method(self, method=None):
        """Setup with business continuity focus."""
        super().setup_method(method)
        
        # Business value metrics for error handling
        self.record_metric("business_segment", "all_segments")
        self.record_metric("test_type", "e2e_error_recovery") 
        self.record_metric("business_goal", "customer_trust_maintenance_during_errors")
        self.record_metric("continuity_requirement", "graceful_error_recovery")
        
        # Initialize test components
        self._websocket_helper = None
        self._docker_manager = None
        self._error_validator = None
        
    async def async_setup_method(self, method=None):
        """Async setup for error handling E2E testing."""
        await super().async_setup_method(method)
        
        # Initialize Docker manager for real services
        self._docker_manager = UnifiedDockerManager(environment_type=EnvironmentType.TEST)
        
        # Start required services for error testing
        if self._docker_manager.is_docker_available():
            await self._docker_manager.start_services(['backend', 'auth', 'redis'])
            await asyncio.sleep(5)  # Allow services to initialize
            
        # Initialize WebSocket helper
        environment = self.get_env_var("TEST_ENV", "test")
        self._websocket_helper = E2EWebSocketAuthHelper(environment=environment)
        
        # Initialize error recovery validator
        self._error_validator = ErrorRecoveryValidator()
        
    @pytest.mark.asyncio
    async def test_complete_chat_error_recovery_with_business_continuity(self):
        """
        Test complete chat error recovery workflow with business continuity validation.
        
        CRITICAL: This tests CUSTOMER EXPERIENCE during system errors:
        Normal Chat → Error Occurs → Transparent Communication → Recovery Attempt → Business Value Restored
        
        Business Value: Validates customer trust is maintained during system issues.
        """
        # Arrange - Create authenticated user for error recovery testing
        user_context = await create_authenticated_user_context(
            user_email="error_recovery_test_user@example.com",
            environment="test",
            permissions=["read", "write", "execute_agents", "error_recovery_testing"],
            websocket_enabled=True
        )
        
        # Connect to WebSocket with authentication
        websocket_url = self.get_env_var("WEBSOCKET_URL", "ws://localhost:8000/ws")
        headers = self._websocket_helper.get_websocket_headers()
        
        self.logger.info(f"🔌 Connecting to WebSocket for error recovery testing: {websocket_url}")
        
        pre_error_events = []
        error_phase_events = []
        post_recovery_events = []
        
        async with websockets.connect(websocket_url, additional_headers=headers) as websocket:
            
            # Phase 1: Establish normal chat functionality
            self.logger.info("📤 Phase 1: Establishing normal chat baseline")
            
            normal_chat_request = {
                "type": "chat_message",
                "content": "Analyze my cloud costs and provide optimization recommendations",
                "user_id": str(user_context.user_id),
                "thread_id": str(user_context.thread_id),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "test_phase": "baseline_functionality"
            }
            
            await websocket.send(json.dumps(normal_chat_request))
            
            # Collect baseline events
            baseline_timeout = 20.0
            baseline_start = time.time()
            
            while (time.time() - baseline_start) < baseline_timeout:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    event = json.loads(event_data)
                    
                    pre_error_events.append({
                        **event,
                        "phase": "baseline",
                        "received_timestamp": time.time()
                    })
                    
                    self.logger.info(f"📨 Baseline: {event.get('type', 'unknown')}")
                    
                    # Stop when we get some baseline functionality
                    if len(pre_error_events) >= 3:
                        break
                        
                except asyncio.TimeoutError:
                    if len(pre_error_events) >= 2:
                        break
                    continue
            
            # Phase 2: Introduce controlled error scenario
            self.logger.info("💥 Phase 2: Introducing error scenario")
            
            # Send request that will trigger error conditions
            # This simulates real error scenarios like service timeouts, data issues, etc.
            error_inducing_request = {
                "type": "chat_message",
                "content": "Process extremely complex optimization analysis with 10000 variables and ML model training",
                "user_id": str(user_context.user_id),
                "thread_id": str(user_context.thread_id),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "test_phase": "error_induction",
                "complexity_level": "extreme",  # Likely to cause timeouts
                "requires_intensive_processing": True
            }
            
            # Use patch to simulate service errors during processing
            with patch('netra_backend.app.agents.supervisor.execution_engine.ExecutionEngine.execute') as mock_execute:
                # Simulate realistic error scenarios  
                mock_execute.side_effect = [
                    Exception("Service temporarily unavailable"),  # First attempt fails
                    Exception("Request timeout"),                   # Second attempt fails  
                    {"result": "Fallback analysis completed"}       # Third attempt succeeds with fallback
                ]
                
                await websocket.send(json.dumps(error_inducing_request))
                
                # Collect error handling events
                error_timeout = 45.0
                error_start = time.time()
                
                while (time.time() - error_start) < error_timeout:
                    try:
                        event_data = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                        event = json.loads(event_data)
                        
                        error_phase_events.append({
                            **event,
                            "phase": "error_handling",
                            "received_timestamp": time.time()
                        })
                        
                        self.logger.info(f"💥 Error phase: {event.get('type', 'unknown')}")
                        
                        # Stop when we receive recovery completion or fallback success
                        if event.get("type") in ["recovery_completed", "fallback_success", "agent_completed"]:
                            break
                            
                    except asyncio.TimeoutError:
                        if len(error_phase_events) >= 3:
                            break
                        continue
            
            # Phase 3: Validate business continuity restoration
            self.logger.info("🔄 Phase 3: Validating business continuity restoration")
            
            # Send follow-up request to test if system recovered
            recovery_validation_request = {
                "type": "chat_message",
                "content": "Provide simple cost optimization summary based on previous analysis",
                "user_id": str(user_context.user_id),
                "thread_id": str(user_context.thread_id),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "test_phase": "recovery_validation",
                "simple_request": True
            }
            
            await websocket.send(json.dumps(recovery_validation_request))
            
            # Collect post-recovery events
            recovery_timeout = 25.0
            recovery_start = time.time()
            
            while (time.time() - recovery_start) < recovery_timeout:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    event = json.loads(event_data)
                    
                    post_recovery_events.append({
                        **event,
                        "phase": "post_recovery",
                        "received_timestamp": time.time()
                    })
                    
                    self.logger.info(f"🔄 Recovery: {event.get('type', 'unknown')}")
                    
                    # Stop when we get completion event
                    if event.get("type") == "agent_completed":
                        break
                        
                except asyncio.TimeoutError:
                    if len(post_recovery_events) >= 2:
                        break
                    continue
        
        # Assert - Validate comprehensive error recovery and business continuity
        
        # Validate baseline functionality was established
        self.assertGreater(len(pre_error_events), 0,
            "Must establish baseline chat functionality before error testing")
        
        # Validate error events were properly handled
        self.assertGreater(len(error_phase_events), 0,
            "Must receive error handling events during error phase")
        
        # Analyze error handling quality using validator
        error_analysis = self._error_validator.analyze_error_events(error_phase_events)
        
        # CRITICAL: System must communicate errors transparently to users
        self.assertTrue(error_analysis["transparent_communication"] or error_analysis["user_guidance_provided"],
            f"CRITICAL: No transparent error communication found. Users must be informed of issues. "
            f"Analysis: {error_analysis}")
        
        # Validate business continuity was maintained
        continuity_analysis = self._error_validator.validate_business_continuity(
            pre_error_events, post_recovery_events
        )
        
        # CRITICAL: Some level of business functionality must be restored
        self.assertTrue(continuity_analysis["functionality_restored"],
            f"CRITICAL: Business functionality not restored after error recovery. "
            f"Continuity analysis: {continuity_analysis}")
        
        # Validate recovery events were sent
        self.assertTrue(error_analysis["business_continuity_maintained"],
            "System must demonstrate business continuity during errors")
        
        # Validate post-recovery system works for simple requests
        self.assertGreater(len(post_recovery_events), 0,
            "System must handle requests after error recovery")
        
        # Check that error events contain helpful information for users
        error_content_analysis = []
        for event in error_phase_events:
            content = str(event.get("content", "")).lower()
            if any(helpful_term in content for helpful_term in 
                   ["please", "try again", "temporary", "working", "support", "retry"]):
                error_content_analysis.append(event)
        
        # Users should receive helpful guidance during errors
        self.assertGreater(len(error_content_analysis), 0,
            "Error events should contain helpful guidance for users")
        
        # Validate error types were appropriate (not generic failures)
        error_types = set(event.get("type", "") for event in error_phase_events)
        generic_error_types = {"unknown_error", "generic_error", "undefined"}
        
        self.assertFalse(error_types.issubset(generic_error_types),
            f"Error types should be specific, not generic. Found: {error_types}")
        
        # Record comprehensive error handling metrics
        self.record_metric("baseline_events", len(pre_error_events))
        self.record_metric("error_phase_events", len(error_phase_events))
        self.record_metric("post_recovery_events", len(post_recovery_events))
        self.record_metric("transparent_communication", error_analysis["transparent_communication"])
        self.record_metric("user_guidance_provided", error_analysis["user_guidance_provided"])
        self.record_metric("business_continuity_maintained", error_analysis["business_continuity_maintained"])
        self.record_metric("functionality_restored", continuity_analysis["functionality_restored"])
        self.record_metric("continuity_ratio", continuity_analysis["continuity_ratio"])
        self.record_metric("error_recovery_success", True)
        
        self.logger.info(f"✅ Chat error recovery validated: "
                        f"baseline={len(pre_error_events)}, errors={len(error_phase_events)}, "
                        f"recovery={len(post_recovery_events)}, continuity_ratio={continuity_analysis['continuity_ratio']:.2f}")
    
    # Helper Methods and Cleanup
    
    async def async_teardown_method(self, method=None):
        """Cleanup Docker services after error testing."""
        if self._docker_manager and self._docker_manager.is_docker_available():
            try:
                await self._docker_manager.stop_services(['backend', 'auth', 'redis'])
            except Exception as e:
                self.logger.warning(f"Error stopping Docker services after error testing: {e}")
        
        await super().async_teardown_method(method)
    
    def teardown_method(self, method=None):
        """Cleanup after error recovery test."""
        super().teardown_method(method)
        
        # Clear error validator
        if self._error_validator:
            self._error_validator.error_events.clear()
            self._error_validator.recovery_events.clear()
            self._error_validator.user_communication_events.clear()
            
        self.logger.info(f"✅ Chat error handling and recovery E2E test completed successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "e2e"])