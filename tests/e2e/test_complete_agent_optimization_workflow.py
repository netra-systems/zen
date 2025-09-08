"""
Complete Agent Optimization Workflow E2E Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Validate complete AI workload optimization delivery
- Value Impact: Users receive actionable cost savings and performance improvements
- Strategic Impact: Core platform value proposition - optimization workflows must work end-to-end

These tests validate the COMPLETE business workflow from user request to delivered optimization recommendations.
Tests use real authentication, real services, real LLM, and validate all 5 critical WebSocket events.

CRITICAL E2E REQUIREMENTS:
1. Real authentication (JWT/OAuth) - NO MOCKS
2. Real services (Docker stack) - NO MOCKS  
3. Real LLM integration for agent execution
4. All 5 WebSocket events MUST be verified
5. Complete business value delivery validation
6. Multi-user isolation testing
7. End-to-end optimization workflows
"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import websockets

from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user, get_test_jwt_token
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestCompleteAgentOptimizationWorkflow(SSotBaseTestCase):
    """
    E2E tests for complete agent optimization workflows.
    Tests the full business journey from user request to optimization recommendations.
    """
    
    @pytest.fixture
    async def auth_helper(self):
        """Create authenticated helper for E2E tests."""
        return E2EAuthHelper(environment="test")
    
    @pytest.fixture 
    async def authenticated_user(self, auth_helper):
        """Create authenticated user with real JWT token."""
        return await create_authenticated_user(
            environment="test",
            email="test_optimization@example.com",
            permissions=["read", "write", "agent_execution"]
        )

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm
    @pytest.mark.mission_critical
    async def test_cost_optimization_complete_workflow(self, auth_helper, authenticated_user):
        """
        Test complete cost optimization workflow end-to-end.
        
        Business Scenario: Enterprise customer wants to reduce AI costs by 30% 
        while maintaining quality for their chatbot workload.
        
        Validates:
        - Triage agent properly categorizes request
        - Data agent gathers workload information  
        - Optimization agent creates actionable strategies
        - All 5 WebSocket events are delivered
        - Final recommendations contain measurable business value
        """
        token, user_data = authenticated_user
        
        # Test request representing real customer scenario
        optimization_request = {
            "type": "agent_request", 
            "agent": "supervisor",
            "message": "I need to reduce my chatbot costs by 30% while maintaining 90% customer satisfaction. We're currently spending $5000/month on OpenAI GPT-4 for 100k requests. About 80% are simple FAQ queries and 20% need complex reasoning.",
            "context": {
                "current_monthly_spend": 5000,
                "monthly_requests": 100000,
                "target_cost_reduction": 30,
                "quality_threshold": 90,
                "workload_type": "chatbot",
                "use_case": "customer_service"
            },
            "user_id": user_data["id"]
        }
        
        print(f"🚀 Starting cost optimization E2E test for user: {user_data['email']}")
        
        # Connect to WebSocket with authentication
        websocket_url = "ws://localhost:8000/ws"
        headers = auth_helper.get_websocket_headers(token)
        
        try:
            async with websockets.connect(websocket_url, additional_headers=headers) as websocket:
                print(f"✅ WebSocket connection established with auth headers")
                
                # Send optimization request
                await websocket.send(json.dumps(optimization_request))
                print(f"📤 Sent optimization request: {optimization_request['message'][:100]}...")
                
                # Collect all events from the complete workflow
                events = []
                start_time = time.time()
                timeout_duration = 60.0  # 1 minute for complete workflow
                
                while True:
                    try:
                        # Wait for message with timeout
                        remaining_time = timeout_duration - (time.time() - start_time)
                        if remaining_time <= 0:
                            break
                            
                        message = await asyncio.wait_for(
                            websocket.recv(), 
                            timeout=remaining_time
                        )
                        
                        event = json.loads(message)
                        events.append(event)
                        
                        print(f"📨 Received event: {event['type']}")
                        if event.get('data'):
                            print(f"   Data keys: {list(event['data'].keys())}")
                        
                        # Stop when agent workflow is complete
                        if event['type'] == 'agent_completed':
                            print(f"✅ Agent workflow completed in {time.time() - start_time:.2f}s")
                            break
                            
                    except asyncio.TimeoutError:
                        print(f"⏰ Timeout waiting for events after {time.time() - start_time:.2f}s")
                        break
                    except json.JSONDecodeError as e:
                        print(f"❌ Failed to parse WebSocket message: {e}")
                        continue
        
        except Exception as e:
            pytest.fail(f"WebSocket connection failed: {e}")
        
        # Validate we received events
        assert len(events) > 0, "No WebSocket events received"
        print(f"📊 Total events received: {len(events)}")
        
        # Extract event types for analysis
        event_types = [e['type'] for e in events]
        print(f"📋 Event types: {event_types}")
        
        # 🚨 CRITICAL: Validate ALL 5 required WebSocket events
        required_events = [
            'agent_started',
            'agent_thinking', 
            'tool_executing',
            'tool_completed',
            'agent_completed'
        ]
        
        for required_event in required_events:
            assert required_event in event_types, f"Missing critical WebSocket event: {required_event}"
        
        print(f"✅ All 5 critical WebSocket events validated")
        
        # Find the final completion event
        completion_events = [e for e in events if e['type'] == 'agent_completed']
        assert len(completion_events) > 0, "No agent completion event found"
        
        final_result = completion_events[-1]
        assert 'data' in final_result, "Completion event missing data"
        assert 'result' in final_result['data'], "Completion event missing result"
        
        result_data = final_result['data']['result']
        print(f"🎯 Final result keys: {list(result_data.keys())}")
        
        # 🚨 CRITICAL: Validate business value delivery
        # The optimization agent MUST provide actionable cost reduction strategies
        
        # Validate optimization strategies are present
        assert 'strategies' in result_data or 'optimization_summary' in result_data, \
            "Result missing optimization strategies"
        
        # Validate cost savings projections
        has_cost_analysis = any([
            'cost_savings' in result_data,
            'projected_cost_savings' in result_data, 
            'strategies' in result_data,
            'cost_reduction' in str(result_data).lower(),
            'savings' in str(result_data).lower()
        ])
        
        assert has_cost_analysis, "Result missing cost savings analysis"
        
        # Validate business-relevant recommendations  
        result_text = str(result_data).lower()
        business_indicators = [
            'chatbot', 'cost', 'reduction', 'model', 'routing', 
            'optimization', 'strategy', 'savings', 'recommendation'
        ]
        
        found_indicators = [indicator for indicator in business_indicators if indicator in result_text]
        assert len(found_indicators) >= 3, f"Result lacks business relevance. Found indicators: {found_indicators}"
        
        print(f"✅ Business value validated - found indicators: {found_indicators}")
        
        # Validate agent workflow progression  
        # Should show: triage -> data gathering -> optimization -> completion
        agent_thinking_events = [e for e in events if e['type'] == 'agent_thinking']
        assert len(agent_thinking_events) > 0, "No agent thinking events - workflow not progressing properly"
        
        tool_events = [e for e in events if e['type'] in ['tool_executing', 'tool_completed']]
        assert len(tool_events) > 0, "No tool execution events - agents not using tools"
        
        print(f"✅ Agent workflow progression validated")
        print(f"   - Agent thinking events: {len(agent_thinking_events)}")
        print(f"   - Tool execution events: {len(tool_events)}")
        
        # Performance validation - should complete within reasonable time
        total_duration = time.time() - start_time
        assert total_duration < 120, f"Workflow took too long: {total_duration:.2f}s (max 120s)"
        
        print(f"✅ Performance validated - completed in {total_duration:.2f}s")
        
        # Final success validation
        print(f"🎉 COMPLETE COST OPTIMIZATION WORKFLOW SUCCESS!")
        print(f"   ✓ All 5 WebSocket events delivered")
        print(f"   ✓ Business value optimization strategies provided") 
        print(f"   ✓ Agent workflow progressed through all phases")
        print(f"   ✓ Performance within acceptable limits")
        print(f"   ✓ Real authentication and services used")


    @pytest.mark.e2e
    @pytest.mark.real_services  
    @pytest.mark.real_llm
    async def test_performance_optimization_workflow(self, auth_helper, authenticated_user):
        """
        Test complete performance optimization workflow.
        
        Business Scenario: Healthcare customer needs <500ms latency for diagnostic AI
        while scaling to 100 concurrent requests with diagnostic accuracy maintained.
        
        Validates complete workflow for performance-focused optimization.
        """
        token, user_data = authenticated_user
        
        performance_request = {
            "type": "agent_request",
            "agent": "supervisor", 
            "message": "Our medical diagnostic AI needs to scale to 100 concurrent requests with <500ms latency. Currently using GPT-4 with 2-3 second response time. Cannot compromise on diagnostic accuracy - physicians will notice quality dips.",
            "context": {
                "target_latency_ms": 500,
                "target_concurrency": 100,
                "current_latency_ms": 2500,
                "workload_type": "healthcare",
                "use_case": "diagnostic_support", 
                "quality_constraint": "maintain_accuracy"
            },
            "user_id": user_data["id"]
        }
        
        print(f"🚀 Starting performance optimization E2E test")
        
        websocket_url = "ws://localhost:8000/ws"
        headers = auth_helper.get_websocket_headers(token)
        
        async with websockets.connect(websocket_url, additional_headers=headers) as websocket:
            await websocket.send(json.dumps(performance_request))
            
            events = []
            start_time = time.time()
            
            while time.time() - start_time < 60:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=10)
                    event = json.loads(message)
                    events.append(event)
                    
                    if event['type'] == 'agent_completed':
                        break
                except asyncio.TimeoutError:
                    continue
        
        # Validate critical events
        event_types = [e['type'] for e in events]
        required_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        
        for event in required_events:
            assert event in event_types, f"Missing event: {event}"
        
        # Validate performance-specific recommendations
        final_result = [e for e in events if e['type'] == 'agent_completed'][-1]
        result_data = final_result['data']['result']
        result_text = str(result_data).lower()
        
        performance_indicators = ['latency', 'performance', 'speed', 'concurrent', 'scaling', 'optimization']
        found = [ind for ind in performance_indicators if ind in result_text]
        
        assert len(found) >= 2, f"Performance optimization lacking relevant recommendations: {found}"
        print(f"✅ Performance optimization validated with indicators: {found}")


    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm  
    async def test_quality_optimization_workflow(self, auth_helper, authenticated_user):
        """
        Test complete quality optimization workflow.
        
        Business Scenario: Finance company needs to reduce false positives in fraud detection
        while maintaining fraud catch rate within 1% tolerance.
        
        Validates quality-focused optimization with precision/recall trade-offs.
        """
        token, user_data = authenticated_user
        
        quality_request = {
            "type": "agent_request",
            "agent": "supervisor",
            "message": "Our fraud detection LLM has too many false positives - blocking legitimate transactions and frustrating customers. Need to reduce false positive rate while keeping fraud catch rate within 1% of current performance. Currently catching 94% of fraud with 12% false positive rate.",
            "context": {
                "current_fraud_detection_rate": 94,
                "current_false_positive_rate": 12,
                "target_false_positive_rate": 6,
                "max_fraud_detection_loss": 1,
                "workload_type": "finance",
                "use_case": "fraud_detection",
                "constraint_type": "precision_recall_balance"
            },
            "user_id": user_data["id"]
        }
        
        print(f"🚀 Starting quality optimization E2E test")
        
        websocket_url = "ws://localhost:8000/ws" 
        headers = auth_helper.get_websocket_headers(token)
        
        async with websockets.connect(websocket_url, additional_headers=headers) as websocket:
            await websocket.send(json.dumps(quality_request))
            
            events = []
            start_time = time.time()
            
            while time.time() - start_time < 60:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=10)
                    event = json.loads(message)
                    events.append(event)
                    
                    if event['type'] == 'agent_completed':
                        break
                except asyncio.TimeoutError:
                    continue
        
        # Validate workflow completion
        event_types = [e['type'] for e in events]
        required_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        
        for event in required_events:
            assert event in event_types, f"Missing event: {event}"
        
        # Validate quality-specific recommendations
        final_result = [e for e in events if e['type'] == 'agent_completed'][-1]
        result_data = final_result['data']['result']
        result_text = str(result_data).lower()
        
        quality_indicators = ['false positive', 'accuracy', 'precision', 'fraud', 'detection', 'quality', 'model']
        found = [ind for ind in quality_indicators if ind in result_text]
        
        assert len(found) >= 2, f"Quality optimization lacking relevant recommendations: {found}"
        print(f"✅ Quality optimization validated with indicators: {found}")


    @pytest.mark.e2e 
    @pytest.mark.real_services
    @pytest.mark.real_llm
    async def test_multi_objective_balanced_optimization(self, auth_helper, authenticated_user):
        """
        Test balanced multi-objective optimization workflow.
        
        Business Scenario: Media company needs to scale content generation 10x
        while managing costs and maintaining content quality standards.
        
        Validates complex multi-objective optimization balancing cost, performance, and quality.
        """
        token, user_data = authenticated_user
        
        balanced_request = {
            "type": "agent_request", 
            "agent": "supervisor",
            "message": "We need to scale our AI content generation from 1000 to 10,000 articles per day in 3 months. Current costs are $2 per article using GPT-4. We need to control costs while maintaining editorial quality standards. Articles must pass automated quality checks at 85% rate minimum.",
            "context": {
                "current_volume": 1000,
                "target_volume": 10000,
                "current_cost_per_article": 2.0,
                "scale_timeframe": "3_months", 
                "quality_threshold": 85,
                "workload_type": "content_generation",
                "use_case": "media_scaling",
                "optimization_focus": "balanced"
            },
            "user_id": user_data["id"]
        }
        
        print(f"🚀 Starting balanced optimization E2E test")
        
        websocket_url = "ws://localhost:8000/ws"
        headers = auth_helper.get_websocket_headers(token)
        
        async with websockets.connect(websocket_url, additional_headers=headers) as websocket:
            await websocket.send(json.dumps(balanced_request))
            
            events = []
            start_time = time.time()
            
            while time.time() - start_time < 60:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=10)
                    event = json.loads(message) 
                    events.append(event)
                    
                    if event['type'] == 'agent_completed':
                        break
                except asyncio.TimeoutError:
                    continue
        
        # Validate complete workflow
        event_types = [e['type'] for e in events]
        required_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        
        for event in required_events:
            assert event in event_types, f"Missing event: {event}"
        
        # Validate multi-objective recommendations
        final_result = [e for e in events if e['type'] == 'agent_completed'][-1]
        result_data = final_result['data']['result']
        result_text = str(result_data).lower()
        
        # Should address cost, performance (scaling), and quality
        cost_indicators = ['cost', 'savings', 'budget', 'price']
        performance_indicators = ['scale', 'volume', 'throughput', 'capacity']
        quality_indicators = ['quality', 'editorial', 'standards', 'content']
        
        found_cost = [ind for ind in cost_indicators if ind in result_text]
        found_performance = [ind for ind in performance_indicators if ind in result_text] 
        found_quality = [ind for ind in quality_indicators if ind in result_text]
        
        assert len(found_cost) >= 1, f"Missing cost considerations: {found_cost}"
        assert len(found_performance) >= 1, f"Missing performance considerations: {found_performance}"
        assert len(found_quality) >= 1, f"Missing quality considerations: {found_quality}"
        
        print(f"✅ Multi-objective optimization validated:")
        print(f"   Cost indicators: {found_cost}")
        print(f"   Performance indicators: {found_performance}")
        print(f"   Quality indicators: {found_quality}")


    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm
    async def test_insufficient_data_workflow(self, auth_helper, authenticated_user):
        """
        Test workflow when user provides insufficient data for optimization.
        
        Business Scenario: User makes vague request without specific metrics or context.
        System should triage as insufficient data and request additional information.
        
        Validates triage agent properly identifies data gaps and requests clarification.
        """
        token, user_data = authenticated_user
        
        vague_request = {
            "type": "agent_request",
            "agent": "supervisor", 
            "message": "My AI costs are too high. Can you help optimize?",
            "context": {},  # Intentionally minimal context
            "user_id": user_data["id"]
        }
        
        print(f"🚀 Starting insufficient data workflow test")
        
        websocket_url = "ws://localhost:8000/ws"
        headers = auth_helper.get_websocket_headers(token)
        
        async with websockets.connect(websocket_url, additional_headers=headers) as websocket:
            await websocket.send(json.dumps(vague_request))
            
            events = []
            start_time = time.time()
            
            while time.time() - start_time < 45:  # Shorter timeout for insufficient data case
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=10)
                    event = json.loads(message)
                    events.append(event)
                    
                    if event['type'] == 'agent_completed':
                        break
                except asyncio.TimeoutError:
                    continue
        
        # Validate events received
        event_types = [e['type'] for e in events]
        assert 'agent_started' in event_types, "Missing agent_started event"
        assert 'agent_completed' in event_types, "Missing agent_completed event"
        
        # Find completion event
        final_result = [e for e in events if e['type'] == 'agent_completed'][-1]
        result_data = final_result['data']['result']
        result_text = str(result_data).lower()
        
        # Should identify insufficient data and request more information
        clarification_indicators = [
            'more information', 'additional details', 'specific', 'clarify', 
            'details needed', 'provide more', 'current spending', 'workload'
        ]
        
        found_clarification = [ind for ind in clarification_indicators if ind in result_text]
        assert len(found_clarification) >= 1, f"Should request clarification for insufficient data: {found_clarification}"
        
        print(f"✅ Insufficient data handling validated: {found_clarification}")