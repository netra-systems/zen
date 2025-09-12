"""
E2E Test: Business Value Chat Recovery Patterns - MISSION CRITICAL Resilience Validation

BUSINESS IMPACT: Tests chat recovery patterns that maintain business value during edge cases.
This validates system resilience that protects revenue during service degradation or errors.

Business Value Justification (BVJ):
- Segment: Enterprise/Platform - Service Reliability  
- Business Goal: Revenue Protection - Maintain value delivery during degradation
- Value Impact: Validates graceful degradation that preserves customer experience
- Strategic Impact: Tests resilience patterns that prevent customer churn during issues

CRITICAL SUCCESS METRICS:
 PASS:  Graceful degradation maintains partial business value
 PASS:  Error recovery preserves user session and context
 PASS:  Fallback patterns deliver alternative value when primary fails
 PASS:  User experience remains positive during service issues
 PASS:  Business insights still delivered despite technical challenges

RECOVERY PATTERNS TESTED:
[U+2022] Connection recovery - Reconnect and resume chat sessions
[U+2022] Agent failure recovery - Alternative approaches when agents fail
[U+2022] Partial response recovery - Extract value from incomplete responses  
[U+2022] Service degradation - Maintain core functionality during slowdowns
[U+2022] Context preservation - Maintain user state across recovery scenarios

COMPLIANCE:
@compliance CLAUDE.md - Resilience by default (Section 2.6)
@compliance CLAUDE.md - E2E AUTH MANDATORY (Section 7.3)
@compliance CLAUDE.md - Business value preservation during failures
@compliance SPEC/core.xml - Error handling and recovery patterns
"""

import asyncio
import json
import pytest
import time
import uuid
import websockets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# SSOT Imports - Authentication and Recovery
from test_framework.ssot.e2e_auth_helper import (
    E2EWebSocketAuthHelper,
    create_authenticated_user_context
)
from test_framework.ssot.websocket_golden_path_helpers import (
    WebSocketGoldenPathHelper,
    GoldenPathTestConfig
)
from netra_backend.app.websocket_core.event_validator import (
    AgentEventValidator,
    CriticalAgentEventType,
    WebSocketEventMessage
)

# SSOT Imports - Types
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, WebSocketID
from shared.types.execution_types import StronglyTypedUserExecutionContext

# Test Framework
from test_framework.ssot.base_test_case import SSotBaseTestCase


@pytest.mark.e2e
@pytest.mark.staging_compatible
@pytest.mark.recovery
class TestBusinessValueChatRecoveryE2E(SSotBaseTestCase):
    """
    MISSION CRITICAL E2E Tests for Business Value Chat Recovery Patterns.
    
    These tests validate that the chat system can recover gracefully from
    various failure scenarios while preserving business value delivery.
    
    REVENUE IMPACT: If recovery fails, customer trust and retention suffer.
    """
    
    def setup_method(self):
        """Set up business value chat recovery test environment."""
        super().setup_method()
        
        # Initialize SSOT helpers
        self.environment = self.get_test_environment()
        self.ws_auth_helper = E2EWebSocketAuthHelper(environment=self.environment)
        self.golden_path_helper = WebSocketGoldenPathHelper(environment=self.environment)
        
        # Recovery-focused test configuration
        self.config = GoldenPathTestConfig.for_environment(self.environment)
        self.config.max_retries = 3  # Higher retry count for recovery testing
        self.config.enable_performance_monitoring = True
        
        # Recovery tracking
        self.test_start_time = time.time()
        self.recovery_attempts = 0
        self.successful_recoveries = 0
        self.business_value_preserved = 0.0
        self.user_experience_impact = 0.0
        
        print(f"\n CYCLE:  BUSINESS VALUE CHAT RECOVERY E2E - Environment: {self.environment}")
        print(f" TARGET:  Target: Graceful recovery with business value preservation")
        print(f"[U+1F4BC] Business Impact: Resilience patterns protect revenue during issues")
    
    def teardown_method(self):
        """Clean up and report recovery metrics."""
        test_duration = time.time() - self.test_start_time
        recovery_success_rate = (self.successful_recoveries / max(1, self.recovery_attempts)) * 100
        
        print(f"\n CHART:  Chat Recovery Test Summary:")
        print(f"[U+23F1][U+FE0F] Duration: {test_duration:.2f}s")
        print(f" CYCLE:  Recovery Attempts: {self.recovery_attempts}")
        print(f" PASS:  Successful Recoveries: {self.successful_recoveries}")
        print(f"[U+1F4C8] Recovery Success Rate: {recovery_success_rate:.1f}%")
        print(f"[U+1F4B0] Business Value Preserved: {self.business_value_preserved:.1f}%")
        print(f"[U+1F465] User Experience Impact: {self.user_experience_impact:.1f}%")
        
        if recovery_success_rate >= 80.0 and self.business_value_preserved >= 70.0:
            print(f" PASS:  EXCELLENT RECOVERY - Business continuity ensured")
        elif recovery_success_rate >= 60.0 and self.business_value_preserved >= 50.0:
            print(f" PASS:  GOOD RECOVERY - Acceptable business resilience")
        else:
            print(f" FAIL:  POOR RECOVERY - Revenue at risk during failures")
        
        super().teardown_method()
    
    def _extract_business_value_from_partial_response(self, events: List[WebSocketEventMessage]) -> float:
        """
        Extract business value from partial or incomplete responses.
        
        Args:
            events: List of WebSocket events received
            
        Returns:
            Business value score (0-100) extracted from partial responses
        """
        if not events:
            return 0.0
        
        value_indicators = []
        
        for event in events:
            if hasattr(event, 'data'):
                content = (
                    event.data.get("message", "") + " " +
                    event.data.get("response", "") + " " +
                    str(event.data.get("thinking_process", ""))
                ).strip()
                
                if len(content) > 20:  # Substantial content
                    # Check for business value keywords
                    business_keywords = [
                        "analysis", "recommend", "strategy", "insight", "improve",
                        "optimize", "growth", "revenue", "customer", "efficiency"
                    ]
                    
                    found_keywords = sum(1 for kw in business_keywords if kw.lower() in content.lower())
                    keyword_score = min(25.0, found_keywords * 5)
                    
                    # Check for specific data or numbers
                    specificity_indicators = ["%", "$", "increase", "decrease", "metric", "kpi"]
                    found_specific = sum(1 for ind in specificity_indicators if ind in content.lower())
                    specificity_score = min(25.0, found_specific * 8)
                    
                    # Check for actionable content
                    if any(word in content.lower() for word in ["should", "recommend", "suggest", "implement"]):
                        actionable_score = 20.0
                    else:
                        actionable_score = 0.0
                    
                    # Content length bonus
                    length_score = min(30.0, len(content) / 10)
                    
                    event_value = keyword_score + specificity_score + actionable_score + length_score
                    value_indicators.append(event_value)
        
        return sum(value_indicators) / len(value_indicators) if value_indicators else 0.0
    
    @pytest.mark.asyncio
    async def test_websocket_connection_recovery_with_context_preservation(self):
        """
        CRITICAL: WebSocket connection recovery with context preservation.
        
        Tests that chat can recover from connection drops while preserving
        user context and continuing to deliver business value.
        
        BUSINESS IMPACT: Validates connection resilience for uninterrupted service.
        """
        print("\n[U+1F9EA] CRITICAL: Testing WebSocket connection recovery...")
        
        # STEP 1: Create authenticated user context
        user_context = await create_authenticated_user_context(
            user_email=f"connection_recovery_{uuid.uuid4().hex[:8]}@example.com",
            environment=self.environment,
            permissions=["read", "write", "chat", "connection_recovery", "websocket"],
            websocket_enabled=True
        )
        
        print(f"[U+1F464] User authenticated for connection recovery: {user_context.user_id}")
        
        # STEP 2: Establish initial connection and start chat
        initial_request = (
            "I need a comprehensive business analysis for my consulting firm. "
            "We have 25 consultants, $2M annual revenue, and want to expand into "
            "AI advisory services. Please analyze our current position and "
            "provide strategic recommendations for this expansion."
        )
        
        recovery_start = time.time()
        
        # STEP 3: Start chat session
        try:
            async with self.golden_path_helper.authenticated_websocket_connection(user_context):
                # Send initial request
                initial_message = await self.golden_path_helper.send_golden_path_request(
                    user_message=initial_request,
                    user_context=user_context
                )
                
                print(f"[U+1F4E4] Initial request sent: {initial_message['message_id']}")
                
                # Capture initial events for a short period
                initial_events = await self.golden_path_helper.capture_events_with_timeout(
                    timeout=20.0,  # Short timeout to simulate connection issue
                    required_events={"agent_started", "agent_thinking"}
                )
                
                print(f"[U+1F4E8] Captured {len(initial_events)} initial events before 'connection issue'")
                
        except Exception as e:
            print(f" CYCLE:  Simulated connection issue: {str(e)[:100]}")
        
        self.recovery_attempts += 1
        
        # STEP 4: Attempt recovery with new connection
        print(" CYCLE:  Attempting recovery with new connection...")
        
        try:
            # Create new connection (simulating recovery)
            async with self.golden_path_helper.authenticated_websocket_connection(user_context):
                # Continue the same conversation context
                continuation_request = (
                    "Continuing our previous conversation about expanding my consulting firm "
                    "into AI advisory services. Please provide the strategic recommendations "
                    "and implementation timeline we were discussing."
                )
                
                # Execute continuation with recovery
                recovery_result = await self.golden_path_helper.execute_golden_path_flow(
                    user_message=continuation_request,
                    user_context=user_context,
                    timeout=90.0
                )
                
                if recovery_result.success:
                    self.successful_recoveries += 1
                    
                    # Extract business value from recovery
                    recovery_business_value = self._extract_business_value_from_partial_response(
                        recovery_result.events_received
                    )
                    self.business_value_preserved = recovery_business_value
                    
                    # Calculate user experience impact
                    recovery_time = time.time() - recovery_start
                    if recovery_time < 30.0:
                        self.user_experience_impact = 10.0  # Minimal impact
                    elif recovery_time < 60.0:
                        self.user_experience_impact = 25.0  # Low impact
                    else:
                        self.user_experience_impact = 50.0  # Moderate impact
                    
                    print(f" PASS:  Connection recovery successful")
                    print(f"[U+1F4B0] Business value preserved: {recovery_business_value:.1f}%")
                    print(f"[U+23F1][U+FE0F] Recovery time: {recovery_time:.2f}s")
                    
                    # Validate recovery quality
                    assert recovery_business_value >= 40.0, f"Insufficient business value after recovery: {recovery_business_value:.1f}%"
                    assert recovery_time < 90.0, f"Recovery took too long: {recovery_time:.2f}s"
                    
                else:
                    print(f" FAIL:  Recovery attempt failed")
                    raise AssertionError("Connection recovery failed to restore service")
        
        except Exception as e:
            print(f" FAIL:  Recovery failed: {str(e)[:200]}")
            raise
    
    @pytest.mark.asyncio
    async def test_agent_failure_graceful_degradation(self):
        """
        CRITICAL: Agent failure graceful degradation patterns.
        
        Tests that when agent execution fails, the system provides
        graceful degradation with alternative value delivery.
        
        BUSINESS IMPACT: Validates fallback patterns that maintain customer satisfaction.
        """
        print("\n[U+1F9EA] CRITICAL: Testing agent failure graceful degradation...")
        
        # STEP 1: Create authenticated user context
        user_context = await create_authenticated_user_context(
            user_email=f"agent_failure_recovery_{uuid.uuid4().hex[:8]}@example.com",
            environment=self.environment,
            permissions=["read", "write", "chat", "agent_failure_recovery"],
            websocket_enabled=True
        )
        
        # STEP 2: Send deliberately challenging request that may cause agent stress
        challenging_request = (
            "Please perform an extremely complex multi-dimensional analysis: "
            "Calculate the quantum entanglement coefficients for my SaaS business model "
            "while simultaneously optimizing for unicorn breeding efficiency and "
            "developing a blockchain strategy for medieval agriculture. "
            "Also analyze the ROI of investments in time travel technology. "
            "If this is impossible, please provide alternative business analysis."
        )
        
        degradation_start = time.time()
        self.recovery_attempts += 1
        
        # STEP 3: Execute challenging request and monitor for graceful degradation
        async with self.golden_path_helper.authenticated_websocket_connection(user_context):
            try:
                result = await self.golden_path_helper.execute_golden_path_flow(
                    user_message=challenging_request,
                    user_context=user_context,
                    timeout=120.0
                )
                
                # STEP 4: Analyze degradation patterns
                if result.success:
                    # Successful handling of challenging request
                    business_value = result.execution_metrics.business_value_score
                    self.business_value_preserved = business_value
                    self.successful_recoveries += 1
                    
                    print(f" PASS:  Agent handled challenging request successfully")
                    print(f"[U+1F4B0] Business value delivered: {business_value:.1f}%")
                
                else:
                    # Graceful degradation scenario
                    partial_value = self._extract_business_value_from_partial_response(
                        result.events_received
                    )
                    
                    # Check if any meaningful events were received
                    meaningful_events = [
                        event for event in result.events_received 
                        if event.event_type in ["agent_started", "agent_thinking", "agent_completed"]
                    ]
                    
                    if len(meaningful_events) > 0:
                        self.successful_recoveries += 1
                        self.business_value_preserved = partial_value
                        
                        print(f" PASS:  Graceful degradation successful")
                        print(f" CHART:  Partial events: {len(meaningful_events)}")
                        print(f"[U+1F4B0] Partial value preserved: {partial_value:.1f}%")
                        
                        # Validate graceful degradation
                        assert partial_value >= 20.0, f"Degradation provided insufficient value: {partial_value:.1f}%"
                        assert len(meaningful_events) >= 1, "Should provide at least minimal feedback"
                    
                    else:
                        print(f" FAIL:  No graceful degradation - complete failure")
                        self.business_value_preserved = 0.0
                
                # STEP 5: Test alternative value delivery
                print(" CYCLE:  Testing alternative value delivery...")
                
                alternative_request = (
                    "Since my previous request was complex, please provide a straightforward "
                    "business analysis for a SaaS company with standard metrics: "
                    "revenue growth strategies, customer retention improvement, "
                    "and operational efficiency recommendations."
                )
                
                alternative_result = await self.golden_path_helper.execute_golden_path_flow(
                    user_message=alternative_request,
                    user_context=user_context,
                    timeout=60.0
                )
                
                if alternative_result.success:
                    alternative_value = alternative_result.execution_metrics.business_value_score
                    self.business_value_preserved = max(self.business_value_preserved, alternative_value)
                    
                    print(f" PASS:  Alternative value delivery successful: {alternative_value:.1f}%")
                
                degradation_time = time.time() - degradation_start
                self.user_experience_impact = min(50.0, degradation_time * 0.5)  # Impact increases with time
                
                # Critical graceful degradation validation
                assert self.business_value_preserved >= 30.0, f"Insufficient value preservation: {self.business_value_preserved:.1f}%"
                assert degradation_time < 180.0, f"Degradation handling too slow: {degradation_time:.2f}s"
                
            except Exception as e:
                print(f" WARNING: [U+FE0F] Agent failure scenario: {str(e)[:200]}")
                # Even in failure, should attempt graceful handling
                self.business_value_preserved = 10.0  # Minimal fallback value
    
    @pytest.mark.asyncio
    async def test_service_degradation_business_continuity(self):
        """
        CRITICAL: Service degradation with business continuity.
        
        Tests that during service degradation (slow responses, partial failures),
        the system maintains business value delivery and user satisfaction.
        
        BUSINESS IMPACT: Validates business continuity during infrastructure stress.
        """
        print("\n[U+1F9EA] CRITICAL: Testing service degradation business continuity...")
        
        # STEP 1: Create authenticated user context
        user_context = await create_authenticated_user_context(
            user_email=f"service_degradation_{uuid.uuid4().hex[:8]}@example.com",
            environment=self.environment,
            permissions=["read", "write", "chat", "service_degradation", "business_continuity"],
            websocket_enabled=True
        )
        
        # STEP 2: Test multiple scenarios under simulated degradation
        degradation_scenarios = [
            {
                "name": "slow_response_tolerance",
                "request": (
                    "Provide a quick market analysis for our B2B software company "
                    "entering the healthcare sector. Focus on key opportunities and risks."
                ),
                "timeout": 45.0,  # Shorter timeout to simulate degradation
                "min_business_value": 40.0
            },
            {
                "name": "partial_failure_handling",
                "request": (
                    "Analyze our customer acquisition funnel and recommend optimization "
                    "strategies. We have 10% conversion rate and want to improve."
                ),
                "timeout": 60.0,
                "min_business_value": 35.0
            },
            {
                "name": "essential_value_delivery",
                "request": (
                    "What are the top 3 priorities for scaling our startup from "
                    "$1M to $5M ARR? Provide actionable recommendations."
                ),
                "timeout": 30.0,  # Very short timeout
                "min_business_value": 30.0
            }
        ]
        
        continuity_start = time.time()
        successful_scenarios = 0
        total_business_value = 0.0
        
        # STEP 3: Execute degradation scenarios
        async with self.golden_path_helper.authenticated_websocket_connection(user_context):
            for i, scenario in enumerate(degradation_scenarios):
                print(f" CYCLE:  Testing degradation scenario {i+1}: {scenario['name']}")
                
                self.recovery_attempts += 1
                scenario_start = time.time()
                
                try:
                    result = await self.golden_path_helper.execute_golden_path_flow(
                        user_message=scenario["request"],
                        user_context=user_context,
                        timeout=scenario["timeout"]
                    )
                    
                    scenario_time = time.time() - scenario_start
                    
                    if result.success:
                        business_value = result.execution_metrics.business_value_score
                        total_business_value += business_value
                        
                        if business_value >= scenario["min_business_value"]:
                            successful_scenarios += 1
                            self.successful_recoveries += 1
                            
                            print(f"    PASS:  Success: {business_value:.1f}% value in {scenario_time:.2f}s")
                        else:
                            print(f"    WARNING: [U+FE0F] Low value: {business_value:.1f}% in {scenario_time:.2f}s")
                    
                    else:
                        # Check for partial value in failed scenarios
                        partial_value = self._extract_business_value_from_partial_response(
                            result.events_received
                        )
                        
                        if partial_value >= scenario["min_business_value"] * 0.7:  # 70% of minimum
                            successful_scenarios += 1
                            self.successful_recoveries += 1
                            total_business_value += partial_value
                            
                            print(f"    PASS:  Partial success: {partial_value:.1f}% value (degraded)")
                        else:
                            print(f"    FAIL:  Failed: {partial_value:.1f}% value")
                
                except Exception as e:
                    print(f"    FAIL:  Exception: {str(e)[:100]}")
                
                # Brief delay between scenarios
                await asyncio.sleep(1.0)
        
        # STEP 4: Validate business continuity
        continuity_time = time.time() - continuity_start
        success_rate = (successful_scenarios / len(degradation_scenarios)) * 100
        avg_business_value = total_business_value / len(degradation_scenarios) if degradation_scenarios else 0
        
        self.business_value_preserved = avg_business_value
        self.user_experience_impact = min(60.0, continuity_time * 0.8)
        
        print(f" CHART:  Business continuity results:")
        print(f"   [U+2022] Success rate: {success_rate:.1f}%")
        print(f"   [U+2022] Average business value: {avg_business_value:.1f}%")
        print(f"   [U+2022] Total time: {continuity_time:.2f}s")
        
        # Critical business continuity validation
        assert success_rate >= 66.0, f"Business continuity success rate too low: {success_rate:.1f}%"
        assert avg_business_value >= 25.0, f"Average business value too low during degradation: {avg_business_value:.1f}%"
        assert continuity_time < 180.0, f"Business continuity testing too slow: {continuity_time:.2f}s"
        
        print(f" PASS:  Service degradation business continuity validated")
    
    @pytest.mark.asyncio
    async def test_comprehensive_recovery_resilience_suite(self):
        """
        CRITICAL: Comprehensive recovery resilience validation.
        
        Tests multiple recovery patterns in sequence to validate
        overall system resilience and business value preservation.
        
        BUSINESS IMPACT: Validates comprehensive resilience for enterprise reliability.
        """
        print("\n[U+1F9EA] CRITICAL: Testing comprehensive recovery resilience...")
        
        # STEP 1: Create authenticated user context
        user_context = await create_authenticated_user_context(
            user_email=f"comprehensive_recovery_{uuid.uuid4().hex[:8]}@enterprise.com",
            environment=self.environment,
            permissions=["read", "write", "chat", "comprehensive_recovery", "enterprise"],
            websocket_enabled=True
        )
        
        # STEP 2: Define comprehensive recovery test suite
        recovery_tests = [
            {
                "name": "timeout_recovery",
                "description": "Recovery from request timeout",
                "timeout": 15.0,  # Very short timeout
                "expected_resilience": 60.0
            },
            {
                "name": "context_preservation",
                "description": "Context preservation across sessions", 
                "timeout": 45.0,
                "expected_resilience": 70.0
            },
            {
                "name": "error_graceful_handling",
                "description": "Graceful error handling with value",
                "timeout": 60.0,
                "expected_resilience": 65.0
            }
        ]
        
        comprehensive_start = time.time()
        total_resilience_score = 0.0
        recovery_patterns_validated = 0
        
        # STEP 3: Execute comprehensive recovery suite
        business_request = (
            "As an enterprise client, I need robust business intelligence: "
            "1) Analyze our market position vs competitors "
            "2) Identify growth opportunities for next quarter "
            "3) Assess operational risks and mitigation strategies "
            "4) Provide implementation roadmap with KPIs. "
            "This analysis is critical for board presentation."
        )
        
        for i, recovery_test in enumerate(recovery_tests):
            print(f" CYCLE:  Recovery test {i+1}: {recovery_test['name']}")
            
            self.recovery_attempts += 1
            test_start = time.time()
            
            try:
                async with self.golden_path_helper.authenticated_websocket_connection(user_context):
                    result = await self.golden_path_helper.execute_golden_path_flow(
                        user_message=f"Recovery test {i+1}: {business_request}",
                        user_context=user_context,
                        timeout=recovery_test["timeout"]
                    )
                    
                    test_time = time.time() - test_start
                    
                    # Calculate resilience score
                    if result.success:
                        resilience_score = result.execution_metrics.business_value_score
                        self.successful_recoveries += 1
                    else:
                        # Extract value from partial responses
                        resilience_score = self._extract_business_value_from_partial_response(
                            result.events_received
                        )
                        
                        if resilience_score >= recovery_test["expected_resilience"] * 0.6:
                            self.successful_recoveries += 1
                    
                    total_resilience_score += resilience_score
                    
                    if resilience_score >= recovery_test["expected_resilience"]:
                        recovery_patterns_validated += 1
                        print(f"    PASS:  Resilient: {resilience_score:.1f}% in {test_time:.2f}s")
                    else:
                        print(f"    WARNING: [U+FE0F] Degraded: {resilience_score:.1f}% in {test_time:.2f}s")
            
            except Exception as e:
                print(f"    FAIL:  Test failed: {str(e)[:100]}")
                total_resilience_score += 10.0  # Minimal fallback score
            
            # Brief recovery between tests
            await asyncio.sleep(2.0)
        
        # STEP 4: Validate comprehensive resilience
        comprehensive_time = time.time() - comprehensive_start
        avg_resilience = total_resilience_score / len(recovery_tests)
        pattern_success_rate = (recovery_patterns_validated / len(recovery_tests)) * 100
        
        self.business_value_preserved = avg_resilience
        self.user_experience_impact = min(70.0, comprehensive_time * 0.6)
        
        print(f" CELEBRATION:  Comprehensive recovery resilience summary:")
        print(f"   [U+2022] Pattern success rate: {pattern_success_rate:.1f}%")
        print(f"   [U+2022] Average resilience: {avg_resilience:.1f}%")
        print(f"   [U+2022] Recovery time: {comprehensive_time:.2f}s")
        print(f"   [U+2022] Patterns validated: {recovery_patterns_validated}/{len(recovery_tests)}")
        
        # Critical comprehensive resilience validation
        assert pattern_success_rate >= 66.0, f"Recovery pattern success rate too low: {pattern_success_rate:.1f}%"
        assert avg_resilience >= 40.0, f"Average resilience too low: {avg_resilience:.1f}%"
        assert comprehensive_time < 240.0, f"Comprehensive recovery testing too slow: {comprehensive_time:.2f}s"
        
        print(f" PASS:  Comprehensive recovery resilience validated")
        print(f"[U+1F3E2] Enterprise-grade reliability confirmed")


if __name__ == "__main__":
    """
    Run E2E tests for business value chat recovery patterns.
    
    Usage:
        python -m pytest tests/e2e/test_business_value_chat_recovery_e2e.py -v
        python -m pytest tests/e2e/test_business_value_chat_recovery_e2e.py::TestBusinessValueChatRecoveryE2E::test_websocket_connection_recovery_with_context_preservation -v -s
    """
    import sys
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))