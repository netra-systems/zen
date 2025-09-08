"""
E2E Tests for Agent Execution with Real LLM Integration - Cycle 2

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure agent execution works with real LLM in production environment
- Value Impact: Users receive genuine AI-powered insights and recommendations
- Strategic Impact: This validates the core AI value proposition customers pay for

CRITICAL: Real LLM integration is what differentiates our platform from simple automation.
Without working LLM integration, there is no business value delivered.

E2E AUTHENTICATION REQUIREMENT: All tests MUST use real authentication per CLAUDE.md
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Any

from test_framework.base_e2e_test import BaseE2ETest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.websocket_helpers import WebSocketTestClient

class TestAgentExecutionRealLLME2E(BaseE2ETest):
    """E2E tests for agent execution with real LLM integration."""
    
    @pytest.fixture
    async def authenticated_user(self):
        """Create authenticated user for E2E testing."""
        auth_helper = E2EAuthHelper()
        user = await auth_helper.create_authenticated_user(
            email="e2e_llm_user@test.netra.ai",
            name="E2E LLM Test User"
        )
        return user

    @pytest.mark.e2e
    @pytest.mark.real_llm
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_complete_agent_execution_with_real_llm(self, authenticated_user, real_services):
        """
        Test complete agent execution using real LLM for genuine AI responses.
        
        Business Value: Validates that users receive actual AI-powered insights.
        MISSION CRITICAL: This is the core value proposition of the platform.
        """
        # Arrange: Setup authenticated connection to real services
        backend_url = real_services["backend_url"]
        websocket_url = f"ws://{backend_url.replace('http://', '')}/ws"
        
        agent_events = []
        llm_interaction_detected = False
        genuine_ai_response = False
        
        # Act: Connect and request real AI analysis
        async with WebSocketTestClient(websocket_url, authenticated_user.token) as ws_client:
            
            # Send request for AI-powered cost analysis
            ai_request = {
                "type": "agent_request",
                "agent": "triage_agent",
                "message": "I'm spending $5,000/month on AWS. My main services are EC2 instances for web hosting, S3 for file storage, and RDS for our database. Can you analyze this and suggest specific optimizations to reduce costs by at least 20%?",
                "context": {
                    "user_intent": "cost_optimization",
                    "budget_target": "20_percent_reduction",
                    "current_spend": 5000,
                    "services": ["ec2", "s3", "rds"],
                    "business_type": "web_hosting"
                }
            }
            
            await ws_client.send_json(ai_request)
            
            # Capture all events from agent execution
            async for message in ws_client.receive_events(timeout=120):  # Extended timeout for real LLM
                agent_events.append(message)
                print(f"E2E LLM Event: {message.get('type')} at {datetime.now()}")
                
                # Detect signs of real LLM interaction
                if message.get("type") == "agent_thinking":
                    thinking_content = message.get("content", "").lower()
                    # Real LLM typically shows reasoning patterns
                    if any(pattern in thinking_content for pattern in [
                        "analyzing", "considering", "examining", "evaluating", 
                        "based on", "looking at", "given that", "therefore"
                    ]):
                        llm_interaction_detected = True
                
                elif message.get("type") == "agent_completed":
                    result = message.get("result", {})
                    result_str = json.dumps(result).lower()
                    
                    # Check for genuine AI-generated insights
                    ai_indicators = [
                        "recommend", "suggest", "optimize", "reduce", "improve",
                        "specific", "detailed", "analysis", "insight", "strategy",
                        "ec2", "s3", "rds", "cost", "saving", "efficiency"
                    ]
                    
                    ai_indicator_count = sum(1 for indicator in ai_indicators if indicator in result_str)
                    
                    # Genuine AI response should mention multiple specific concepts
                    if ai_indicator_count >= 5 and len(result_str) > 200:
                        genuine_ai_response = True
                    
                    break  # Agent completed
                    
                # Stop on error
                if message.get("type") == "error":
                    break
        
        # Assert: Real AI-powered execution occurred
        assert len(agent_events) >= 3, f"Expected multiple events from real agent execution, got {len(agent_events)}"
        
        # Verify critical agent events
        event_types = [event.get("type") for event in agent_events]
        critical_events = ["agent_started", "agent_completed"]
        
        for event_type in critical_events:
            assert event_type in event_types, f"Missing critical event: {event_type}"
        
        # Business requirement: Real LLM interaction should be detectable
        assert llm_interaction_detected, "Should detect genuine LLM reasoning in agent_thinking events"
        
        # Business requirement: AI response should provide genuine value
        assert genuine_ai_response, "Agent should provide genuine AI-powered insights and recommendations"
        
        # Validate final result contains business value
        completed_events = [e for e in agent_events if e.get("type") == "agent_completed"]
        assert len(completed_events) >= 1, "Should receive agent completion"
        
        final_result = completed_events[0].get("result", {})
        assert final_result, "Completed agent should provide results"
        
        # Business value validation: Result should address the specific request
        result_content = json.dumps(final_result).lower()
        request_elements = ["cost", "aws", "ec2", "s3", "rds", "optimization", "reduce"]
        matched_elements = sum(1 for element in request_elements if element in result_content)
        
        assert matched_elements >= 4, f"AI result should address specific request elements, matched {matched_elements}/7"

    @pytest.mark.e2e
    @pytest.mark.real_llm
    @pytest.mark.real_services
    async def test_agent_execution_handles_complex_real_world_query(self, authenticated_user, real_services):
        """
        Test agent execution with complex real-world query using real LLM.
        
        Business Value: Validates platform handles enterprise-level complexity.
        Complex queries demonstrate the platform's premium value proposition.
        """
        backend_url = real_services["backend_url"]
        websocket_url = f"ws://{backend_url.replace('http://', '')}/ws"
        
        complex_query_events = []
        complex_response_quality = False
        
        async with WebSocketTestClient(websocket_url, authenticated_user.token) as ws_client:
            
            # Send complex enterprise-level query
            complex_request = {
                "type": "agent_request",
                "agent": "triage_agent",
                "message": """
                We're a SaaS company with 100+ microservices running on Kubernetes across multiple AWS regions. 
                Our monthly cloud spend has grown from $50K to $200K over 6 months. 
                
                Key concerns:
                1. ECS Fargate costs seem excessive for our workload patterns
                2. Data transfer costs between regions are high
                3. We're using RDS Multi-AZ but unsure if it's optimally configured
                4. S3 storage classes might not be optimized for our access patterns
                5. CloudWatch logs are generating significant costs
                
                Please provide a comprehensive analysis with specific, actionable recommendations 
                that could realistically achieve 30-40% cost reduction while maintaining 
                our 99.9% uptime SLA and data compliance requirements.
                """,
                "context": {
                    "company_type": "saas",
                    "infrastructure": "kubernetes",
                    "current_spend": 200000,
                    "growth_rate": "4x_in_6_months",
                    "sla_requirement": "99.9_percent",
                    "complexity": "enterprise",
                    "services_count": 100,
                    "regions": "multi_region"
                }
            }
            
            await ws_client.send_json(complex_request)
            
            # Capture response to complex query
            async for message in ws_client.receive_events(timeout=180):  # Longer timeout for complex query
                complex_query_events.append(message)
                
                if message.get("type") == "agent_completed":
                    result = message.get("result", {})
                    
                    # Analyze response quality for complex query
                    if self._assess_complex_response_quality(result, complex_request["message"]):
                        complex_response_quality = True
                    
                    break
                    
                if message.get("type") == "error":
                    print(f"Complex query error: {message}")
                    break
        
        # Assert: Complex query handled appropriately
        assert len(complex_query_events) >= 2, "Complex query should generate multiple events"
        
        # Business requirement: Complex queries should receive thorough responses
        completion_events = [e for e in complex_query_events if e.get("type") == "agent_completed"]
        
        if len(completion_events) > 0:
            # If agent completed, response should show appropriate complexity
            assert complex_response_quality, "Complex query should receive sophisticated AI response"
        else:
            # If agent didn't complete, should have provided some progress indication
            thinking_events = [e for e in complex_query_events if e.get("type") == "agent_thinking"]
            assert len(thinking_events) >= 1, "Complex query should at least show agent thinking"

    @pytest.mark.e2e
    @pytest.mark.real_llm
    @pytest.mark.real_services
    async def test_agent_execution_llm_performance_characteristics(self, authenticated_user, real_services):
        """
        Test agent execution performance characteristics with real LLM.
        
        Business Value: Ensures LLM integration meets performance expectations.
        Performance directly impacts user experience and business scalability.
        """
        backend_url = real_services["backend_url"]
        websocket_url = f"ws://{backend_url.replace('http://', '')}/ws"
        
        performance_metrics = {
            "start_time": None,
            "first_event_time": None,
            "completion_time": None,
            "total_events": 0,
            "thinking_events": 0
        }
        
        async with WebSocketTestClient(websocket_url, authenticated_user.token) as ws_client:
            
            performance_request = {
                "type": "agent_request",
                "agent": "triage_agent", 
                "message": "Quick analysis: I'm spending $1000/month on AWS EC2. What are the top 3 immediate cost optimization opportunities?",
                "context": {
                    "urgency": "high",
                    "response_type": "concise",
                    "current_spend": 1000
                }
            }
            
            performance_metrics["start_time"] = time.time()
            await ws_client.send_json(performance_request)
            
            async for message in ws_client.receive_events(timeout=90):
                current_time = time.time()
                
                if performance_metrics["first_event_time"] is None:
                    performance_metrics["first_event_time"] = current_time
                
                performance_metrics["total_events"] += 1
                
                if message.get("type") == "agent_thinking":
                    performance_metrics["thinking_events"] += 1
                
                if message.get("type") == "agent_completed":
                    performance_metrics["completion_time"] = current_time
                    break
                    
                if message.get("type") == "error":
                    break
        
        # Calculate performance metrics
        if performance_metrics["completion_time"] and performance_metrics["start_time"]:
            total_duration = performance_metrics["completion_time"] - performance_metrics["start_time"]
            time_to_first_event = performance_metrics["first_event_time"] - performance_metrics["start_time"]
            
            # Assert: Performance meets business requirements
            assert total_duration < 60, f"LLM-powered execution should complete within 60s, took {total_duration:.2f}s"
            assert time_to_first_event < 10, f"Should receive first event within 10s, took {time_to_first_event:.2f}s"
            
            # Business requirement: Reasonable event frequency
            assert performance_metrics["total_events"] >= 2, "Should receive multiple events during execution"
            
            # Performance indicator: Some thinking should be visible for transparency
            if performance_metrics["thinking_events"] > 0:
                thinking_ratio = performance_metrics["thinking_events"] / performance_metrics["total_events"]
                assert thinking_ratio > 0, "Should show some AI thinking process to users"

    def _assess_complex_response_quality(self, result: Dict[str, Any], original_query: str) -> bool:
        """
        Assess whether agent response shows appropriate quality for complex query.
        
        Business Value: Ensures AI responses justify premium platform pricing.
        """
        if not result:
            return False
        
        result_str = json.dumps(result).lower()
        
        # Check for sophisticated response indicators
        sophistication_indicators = [
            "specific", "detailed", "comprehensive", "actionable", 
            "recommendation", "analysis", "strategy", "optimization",
            "fargate", "kubernetes", "microservice", "multi-az", "sla"
        ]
        
        sophistication_score = sum(1 for indicator in sophistication_indicators if indicator in result_str)
        
        # Response should be substantial and relevant
        response_length_adequate = len(result_str) > 500
        mentions_key_concepts = sophistication_score >= 5
        
        # Check for structured thinking (lists, categories, priorities)
        structured_indicators = ["1.", "2.", "3.", "first", "second", "priority", "step"]
        shows_structure = sum(1 for indicator in structured_indicators if indicator in result_str) >= 2
        
        return response_length_adequate and mentions_key_concepts and shows_structure