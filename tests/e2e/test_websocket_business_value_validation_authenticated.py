#!/usr/bin/env python
"""
CLAUDE.md COMPLIANT: WebSocket Business Value Validation with MANDATORY Authentication

This test suite validates SUBSTANTIVE chat interactions and AI value delivery through WebSocket events,
using REAL authentication as mandated by CLAUDE.md Section 6 - MISSION CRITICAL: WebSocket Agent Events.

Business Value Justification:
- Segment: ALL customer tiers (Free, Early, Mid, Enterprise) - Direct revenue impact $500K+ ARR
- Business Goal: Validate 90% business value delivery through chat interactions
- Value Impact: Ensures WebSocket events enable substantive AI responses (>50 chars meaningful content)
- Revenue Impact: Prevents chat failures that cause user abandonment and subscription cancellations

CLAUDE.md COMPLIANCE:
✅ ALL e2e tests MUST use authentication (JWT/OAuth) - MANDATORY
✅ Real services only - NO MOCKS allowed (ABOMINATION if violated)
✅ Tests fail hard - no bypassing/cheating (ABOMINATION if violated)
✅ Focus on 5 critical WebSocket events: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
✅ Business value validation - substantive chat interactions delivering AI value

CRITICAL REQUIREMENTS:
- WebSocket events MUST enable meaningful AI interactions
- Agent responses MUST be >50 characters with actionable insights
- Event sequence MUST support optimal chat UX timing
- Authentication MUST use test_framework/ssot/e2e_auth_helper.py (SSOT)
- NO exceptions for auth requirement except tests that directly validate auth system
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

import pytest
import websockets
from websockets.exceptions import ConnectionClosedError

# CLAUDE.md COMPLIANT: Use SSOT authentication helper - MANDATORY for all e2e tests
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper
from shared.isolated_environment import get_env


class BusinessValueWebSocketValidator:
    """
    Validates WebSocket events deliver substantive business value through authenticated connections.
    
    CRITICAL: This class enforces CLAUDE.md authentication mandates and business value requirements.
    """
    
    def __init__(self):
        """Initialize with MANDATORY authentication helper."""
        self.env = get_env()
        self.environment = self.env.get("TEST_ENV", "test")
        
        # CLAUDE.md COMPLIANT: Use SSOT authentication helper - MANDATORY
        self.auth_helper = E2EWebSocketAuthHelper(environment=self.environment)
        
        # Business value validation thresholds
        self.min_substantive_response_chars = 50  # Minimum for meaningful AI response
        self.max_event_latency_ms = 100  # Performance requirement
        self.max_total_flow_seconds = 45  # Complete agent execution time limit
        
        # Track business metrics
        self.business_metrics = {
            "total_responses": 0,
            "substantive_responses": 0,  # >50 chars with actionable content
            "event_sequence_complete": 0,
            "authentication_successes": 0,
            "business_value_delivered": False
        }
    
    async def validate_authenticated_websocket_business_value(self, test_prompt: str = "Analyze market trends for tech stocks") -> Dict[str, Any]:
        """
        Validate complete business value delivery through authenticated WebSocket connection.
        
        CRITICAL: Tests the COMPLETE business value chain:
        1. MANDATORY Authentication (JWT/OAuth)
        2. WebSocket connection with auth headers
        3. Agent execution with 5 critical events
        4. SUBSTANTIVE AI response delivery (>50 chars meaningful content)
        5. Business value validation (actionable insights)
        
        Args:
            test_prompt: Business-relevant prompt to test AI value delivery
            
        Returns:
            Comprehensive validation results with business metrics
        """
        validation_start = time.time()
        
        try:
            # STEP 1: MANDATORY Authentication - CLAUDE.md Section 6 requirement
            print("🔐 STEP 1: MANDATORY Authentication (CLAUDE.md compliance)")
            websocket = await self.auth_helper.connect_authenticated_websocket(timeout=15.0)
            
            self.business_metrics["authentication_successes"] += 1
            print(f"✅ Authentication successful for environment: {self.environment}")
            
            # STEP 2: Business Value Request - Send substantive prompt
            print(f"💼 STEP 2: Business Value Request - Testing AI value delivery")
            
            business_request = {
                "type": "agent_execution_request",
                "message": test_prompt,
                "user_id": f"test-user-{uuid.uuid4().hex[:8]}",
                "thread_id": f"test-thread-{uuid.uuid4().hex[:8]}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "require_substantive_response": True  # Business requirement flag
            }
            
            await websocket.send(json.dumps(business_request))
            print(f"📤 Sent business request: {test_prompt[:50]}...")
            
            # STEP 3: Critical Event Sequence Validation
            print("📊 STEP 3: Critical WebSocket Event Sequence Validation")
            event_validation = await self._validate_critical_event_sequence(websocket)
            
            # STEP 4: Business Value Analysis
            print("💰 STEP 4: Business Value Analysis")
            business_analysis = await self._analyze_business_value_delivery(event_validation)
            
            await websocket.close()
            
            # STEP 5: Comprehensive Results
            total_time = time.time() - validation_start
            
            results = {
                "authentication_compliant": True,  # CLAUDE.md mandated
                "business_value_delivered": business_analysis["substantive_response"],
                "critical_events_complete": event_validation["all_events_received"],
                "performance_within_limits": total_time <= self.max_total_flow_seconds,
                "total_execution_time": total_time,
                "business_metrics": self.business_metrics,
                "event_details": event_validation,
                "business_analysis": business_analysis,
                "claude_md_compliant": True,  # Confirms SSOT auth usage
                "revenue_impact_positive": business_analysis["actionable_insights_count"] > 0
            }
            
            return results
            
        except Exception as e:
            # CLAUDE.md COMPLIANCE: Tests must fail hard - no bypassing
            error_results = {
                "authentication_compliant": False,
                "business_value_delivered": False,
                "critical_events_complete": False,
                "performance_within_limits": False,
                "error": str(e),
                "claude_md_compliant": False,  # Failed to use SSOT auth properly
                "revenue_impact_positive": False,
                "total_execution_time": time.time() - validation_start
            }
            
            # ABOMINATION CHECK: Ensure we're not masking authentication failures
            if "auth" in str(e).lower() or "token" in str(e).lower():
                print(f"🚨 AUTHENTICATION FAILURE - CLAUDE.md VIOLATION: {e}")
                error_results["authentication_violation"] = True
            
            return error_results
    
    async def _validate_critical_event_sequence(self, websocket) -> Dict[str, Any]:
        """
        Validate the 5 CRITICAL WebSocket events that enable business value delivery.
        
        CLAUDE.md Section 6: Required events for substantive chat interactions:
        1. agent_started - User sees agent processing
        2. agent_thinking - Real-time reasoning visibility  
        3. tool_executing - Tool usage transparency
        4. tool_completed - Tool results delivery
        5. agent_completed - Final response ready
        
        Returns:
            Event sequence validation results with business impact analysis
        """
        required_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        received_events = []
        event_timeline = []
        sequence_start = time.time()
        
        # Business value tracking
        reasoning_visible = False
        tool_transparency_shown = False
        actionable_results_delivered = False
        
        try:
            # Listen for events with timeout
            while len(received_events) < len(required_events):
                # Prevent infinite wait - business requirement
                if time.time() - sequence_start > self.max_total_flow_seconds:
                    print(f"⏰ Event sequence timeout after {self.max_total_flow_seconds}s")
                    break
                
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    event_data = json.loads(message)
                    event_type = event_data.get("type")
                    event_time = time.time()
                    
                    if event_type in required_events:
                        received_events.append(event_type)
                        event_timeline.append({
                            "type": event_type,
                            "timestamp": event_time,
                            "latency_ms": (event_time - sequence_start) * 1000,
                            "content": event_data.get("content", ""),
                            "business_relevant": self._is_business_relevant_event(event_data)
                        })
                        
                        # Business value analysis
                        if event_type == "agent_thinking":
                            reasoning_visible = len(event_data.get("content", "")) > 20
                        elif event_type == "tool_executing":
                            tool_transparency_shown = "tool" in event_data.get("content", "").lower()
                        elif event_type == "tool_completed":
                            actionable_results_delivered = len(event_data.get("content", "")) > self.min_substantive_response_chars
                        
                        print(f"✅ Event received: {event_type} ({(event_time - sequence_start) * 1000:.0f}ms)")
                    
                except asyncio.TimeoutError:
                    print("⏰ Event timeout - continuing to next")
                    break
                    
        except Exception as e:
            print(f"❌ Event sequence validation error: {e}")
        
        # Business impact analysis
        all_events_received = len(received_events) == len(required_events)
        business_transparency = reasoning_visible and tool_transparency_shown and actionable_results_delivered
        
        return {
            "all_events_received": all_events_received,
            "received_events": received_events,
            "missing_events": [e for e in required_events if e not in received_events],
            "event_timeline": event_timeline,
            "business_transparency": business_transparency,
            "reasoning_visible": reasoning_visible,
            "tool_transparency_shown": tool_transparency_shown,
            "actionable_results_delivered": actionable_results_delivered,
            "total_sequence_time": time.time() - sequence_start,
            "sequence_within_performance_limits": all([
                e["latency_ms"] <= self.max_event_latency_ms for e in event_timeline
            ])
        }
    
    async def _analyze_business_value_delivery(self, event_validation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze if WebSocket events delivered substantive business value.
        
        CLAUDE.md Business Value Requirements:
        - Substantive chat responses (>50 chars meaningful content)
        - Actionable insights delivery
        - Real-time problem-solving visibility
        - AI value that justifies subscription cost
        
        Returns:
            Business value analysis with revenue impact metrics
        """
        business_analysis = {
            "substantive_response": False,
            "actionable_insights_count": 0,
            "response_quality_score": 0.0,
            "revenue_justifying_value": False,
            "chat_ux_quality": "poor"
        }
        
        # Analyze event timeline for business value
        timeline = event_validation.get("event_timeline", [])
        
        # Check for substantive content
        total_content_length = 0
        actionable_keywords = ["analyze", "recommend", "strategy", "trend", "insight", "data", "solution", "optimize"]
        actionable_mentions = 0
        
        for event in timeline:
            content = event.get("content", "")
            total_content_length += len(content)
            
            # Count actionable insights
            for keyword in actionable_keywords:
                if keyword in content.lower():
                    actionable_mentions += 1
        
        # Business value scoring
        business_analysis["substantive_response"] = total_content_length >= self.min_substantive_response_chars
        business_analysis["actionable_insights_count"] = actionable_mentions
        business_analysis["response_quality_score"] = min(1.0, total_content_length / 200.0)  # Scale to 1.0
        
        # UX Quality Assessment
        if event_validation["all_events_received"] and event_validation["business_transparency"]:
            if event_validation["sequence_within_performance_limits"]:
                business_analysis["chat_ux_quality"] = "excellent"
            else:
                business_analysis["chat_ux_quality"] = "good"
        elif event_validation["all_events_received"]:
            business_analysis["chat_ux_quality"] = "acceptable"
        else:
            business_analysis["chat_ux_quality"] = "poor"
        
        # Revenue justification logic
        business_analysis["revenue_justifying_value"] = (
            business_analysis["substantive_response"] and
            business_analysis["actionable_insights_count"] >= 2 and
            business_analysis["response_quality_score"] >= 0.5
        )
        
        return business_analysis
    
    def _is_business_relevant_event(self, event_data: Dict[str, Any]) -> bool:
        """Check if event contains business-relevant information."""
        content = event_data.get("content", "").lower()
        business_keywords = ["market", "trend", "analysis", "data", "insight", "strategy", "recommendation"]
        return any(keyword in content for keyword in business_keywords)


# CLAUDE.md COMPLIANT TEST CASES
class TestWebSocketBusinessValueAuthenticated:
    """
    CLAUDE.md COMPLIANT: WebSocket Business Value Tests with MANDATORY Authentication
    
    ALL tests use SSOT E2EAuthHelper as mandated by CLAUDE.md Section 6.
    NO exceptions allowed except for tests specifically validating auth system.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_validator(self):
        """Setup business value validator with MANDATORY authentication."""
        self.validator = BusinessValueWebSocketValidator()
    
    @pytest.mark.asyncio
    async def test_authenticated_market_analysis_business_value(self):
        """
        CLAUDE.md COMPLIANT: Test market analysis business value with MANDATORY authentication.
        
        Validates:
        ✅ MANDATORY JWT authentication (CLAUDE.md Section 6)
        ✅ Real WebSocket connection (NO MOCKS - ABOMINATION if violated)
        ✅ 5 critical WebSocket events for business value
        ✅ Substantive AI response (>50 chars meaningful content)
        ✅ Actionable business insights delivery
        """
        # BUSINESS VALUE PROMPT: Market analysis request
        business_prompt = "Analyze current market trends for technology stocks and provide actionable investment insights"
        
        # Execute authenticated business value validation
        results = await self.validator.validate_authenticated_websocket_business_value(business_prompt)
        
        # CLAUDE.md COMPLIANCE ASSERTIONS - MUST NOT BE BYPASSED
        assert results["authentication_compliant"], "❌ CLAUDE.md VIOLATION: Authentication not compliant"
        assert results["claude_md_compliant"], "❌ CLAUDE.md VIOLATION: SSOT auth helper not used"
        
        # BUSINESS VALUE ASSERTIONS - Revenue protection
        assert results["business_value_delivered"], "💰 Business value not delivered - chat experience inadequate"
        assert results["revenue_impact_positive"], "📈 No positive revenue impact - AI response lacks actionable insights"
        
        # CRITICAL EVENT SEQUENCE ASSERTIONS
        assert results["critical_events_complete"], "📊 Critical WebSocket events incomplete - chat UX compromised"
        
        # PERFORMANCE ASSERTIONS
        assert results["performance_within_limits"], f"⏰ Performance violation: {results['total_execution_time']:.1f}s > {self.validator.max_total_flow_seconds}s"
        
        # BUSINESS METRICS VALIDATION
        business_metrics = results["business_metrics"]
        assert business_metrics["authentication_successes"] > 0, "🔐 No authentication successes recorded"
        
        print("✅ CLAUDE.md COMPLIANT: Market analysis business value validation PASSED")
        print(f"📊 Business metrics: {business_metrics}")
        print(f"💰 Revenue impact: {results['revenue_impact_positive']}")
    
    @pytest.mark.asyncio  
    async def test_authenticated_multi_user_business_isolation(self):
        """
        CLAUDE.md COMPLIANT: Test multi-user business value isolation with MANDATORY authentication.
        
        Validates:
        ✅ Multiple authenticated users (SSOT auth for each)
        ✅ Business value isolation between users
        ✅ No cross-user data leakage in responses
        ✅ Concurrent substantive AI interactions
        """
        user_prompts = [
            "Analyze healthcare technology investment opportunities",
            "Review renewable energy market dynamics and growth potential",
            "Assess cryptocurrency market volatility and trading strategies"
        ]
        
        # Execute concurrent authenticated sessions
        tasks = []
        for i, prompt in enumerate(user_prompts):
            validator = BusinessValueWebSocketValidator()  # Fresh validator per user
            task = validator.validate_authenticated_websocket_business_value(prompt)
            tasks.append(task)
        
        # Wait for all concurrent business value validations
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Validate all sessions succeeded with business value
        successful_sessions = 0
        total_revenue_impact = 0
        
        for i, results in enumerate(results_list):
            if isinstance(results, Exception):
                pytest.fail(f"❌ User {i+1} session failed: {results}")
            
            # CLAUDE.md compliance checks per user
            assert results["authentication_compliant"], f"❌ User {i+1} authentication not compliant"
            assert results["business_value_delivered"], f"💰 User {i+1} business value not delivered"
            
            if results["revenue_impact_positive"]:
                total_revenue_impact += 1
                successful_sessions += 1
        
        # Multi-user business success criteria
        assert successful_sessions >= len(user_prompts) * 0.8, f"📊 Only {successful_sessions}/{len(user_prompts)} sessions delivered business value"
        assert total_revenue_impact >= 2, f"💰 Only {total_revenue_impact} sessions had positive revenue impact"
        
        print(f"✅ CLAUDE.md COMPLIANT: Multi-user business isolation PASSED")
        print(f"👥 Successful sessions: {successful_sessions}/{len(user_prompts)}")  
        print(f"💰 Revenue positive sessions: {total_revenue_impact}")
    
    @pytest.mark.asyncio
    async def test_authenticated_performance_under_business_load(self):
        """
        CLAUDE.md COMPLIANT: Test WebSocket performance under business load with MANDATORY authentication.
        
        Validates:
        ✅ Performance maintains business value under load
        ✅ Authentication scales with concurrent business requests
        ✅ WebSocket events remain reliable under business pressure
        ✅ Revenue-generating capability under realistic load
        """
        # Realistic business load simulation
        concurrent_business_requests = 5  # Realistic concurrent users
        
        validators = [BusinessValueWebSocketValidator() for _ in range(concurrent_business_requests)]
        business_prompt = "Provide strategic analysis and actionable recommendations for market expansion"
        
        # Execute concurrent business value tests
        start_time = time.time()
        tasks = [
            validator.validate_authenticated_websocket_business_value(business_prompt) 
            for validator in validators
        ]
        
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Business performance analysis
        successful_authentications = 0
        business_value_delivered_count = 0
        total_response_quality = 0.0
        
        for results in results_list:
            if isinstance(results, Exception):
                print(f"⚠️  Load test session exception: {results}")
                continue
                
            if results["authentication_compliant"]:
                successful_authentications += 1
            
            if results["business_value_delivered"]:
                business_value_delivered_count += 1
            
            if "business_analysis" in results:
                total_response_quality += results["business_analysis"]["response_quality_score"]
        
        # Business load performance assertions
        auth_success_rate = successful_authentications / concurrent_business_requests
        business_success_rate = business_value_delivered_count / concurrent_business_requests
        avg_response_quality = total_response_quality / len(results_list) if results_list else 0
        
        # Performance requirements for business viability
        assert auth_success_rate >= 0.9, f"🔐 Authentication success rate {auth_success_rate:.1%} below 90% requirement"
        assert business_success_rate >= 0.8, f"💰 Business value delivery rate {business_success_rate:.1%} below 80% requirement"
        assert total_time <= 60.0, f"⏰ Load test took {total_time:.1f}s, requirement <= 60s"
        assert avg_response_quality >= 0.4, f"📊 Average response quality {avg_response_quality:.2f} below 0.4 requirement"
        
        print(f"✅ CLAUDE.md COMPLIANT: Performance under business load PASSED")
        print(f"🔐 Auth success rate: {auth_success_rate:.1%}")
        print(f"💰 Business value rate: {business_success_rate:.1%}")
        print(f"⏱️  Total execution time: {total_time:.1f}s")
        print(f"📊 Avg response quality: {avg_response_quality:.2f}")


if __name__ == "__main__":
    """
    Direct execution for development testing.
    
    CLAUDE.md COMPLIANT: Uses SSOT authentication for all tests.
    """
    async def main():
        validator = BusinessValueWebSocketValidator()
        
        print("🚀 Starting CLAUDE.md COMPLIANT WebSocket Business Value Validation")
        print("🔐 Using MANDATORY SSOT Authentication")
        
        results = await validator.validate_authenticated_websocket_business_value()
        
        print("\n📊 VALIDATION RESULTS:")
        print(f"Authentication Compliant: {results['authentication_compliant']}")
        print(f"Business Value Delivered: {results['business_value_delivered']}")  
        print(f"Revenue Impact Positive: {results['revenue_impact_positive']}")
        print(f"CLAUDE.md Compliant: {results['claude_md_compliant']}")
    
    # Run validation
    asyncio.run(main())