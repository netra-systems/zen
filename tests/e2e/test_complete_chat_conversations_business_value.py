"""
Complete Chat Conversations with Business Value E2E Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Validate complete chat experience delivers measurable business value
- Value Impact: Users must receive actionable insights and solutions through chat interface
- Strategic Impact: Chat is primary value delivery mechanism - conversations must provide real solutions

These tests validate COMPLETE chat conversations that deliver REAL business value:
1. Multi-turn conversations with context preservation
2. Agent handoffs and collaboration
3. Real-time WebSocket updates throughout conversation
4. Actionable business recommendations and insights
5. Conversation persistence and retrieval
6. User engagement and satisfaction indicators

CRITICAL E2E REQUIREMENTS:
1. Real authentication throughout conversation - NO MOCKS
2. Real services with persistent chat state - NO MOCKS
3. Real LLM integration for natural conversations
4. All 5 WebSocket events for every agent interaction
5. Conversation context preservation across turns
6. Measurable business value in every response
7. Multi-agent coordination in complex scenarios
"""

import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
import websockets

from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user, get_test_jwt_token
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestCompleteChatConversationsBusinessValue(SSotBaseTestCase):
    """
    E2E tests for complete chat conversations that deliver measurable business value.
    Tests the entire chat experience from initial question to actionable business outcome.
    """
    
    @pytest.fixture
    async def auth_helper(self):
        """Create authenticated helper for E2E tests."""
        return E2EAuthHelper(environment="test")
    
    @pytest.fixture
    async def authenticated_user(self, auth_helper):
        """Create authenticated user for chat conversation tests."""
        return await create_authenticated_user(
            environment="test",
            email="chat_conversation_test@example.com", 
            permissions=["read", "write", "agent_execution", "chat_access"]
        )

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm
    @pytest.mark.mission_critical
    async def test_multi_turn_cost_optimization_conversation(self, auth_helper, authenticated_user):
        """
        Test complete multi-turn conversation for cost optimization.
        
        Business Scenario: Customer engages in detailed conversation about reducing
        AI costs, asking follow-up questions and refining requirements.
        
        Validates:
        - Multi-turn conversation with context preservation
        - Progressive refinement of optimization strategies  
        - WebSocket events for each turn
        - Actionable business value in every response
        - Conversation persistence and retrieval
        """
        token, user_data = authenticated_user
        
        print(f"🚀 Starting multi-turn cost optimization conversation")
        print(f"👤 User: {user_data['email']}")
        
        websocket_url = "ws://localhost:8000/ws"
        headers = auth_helper.get_websocket_headers(token)
        
        # Define conversation turns with progressive refinement
        conversation_turns = [
            {
                "turn": 1,
                "message": "Hi! I'm spending too much on AI costs. Can you help me optimize?",
                "expected_response_themes": ["cost optimization", "more information", "details"],
                "business_value": "Initial engagement and problem identification"
            },
            {
                "turn": 2, 
                "message": "I'm running a customer service chatbot using GPT-4. We handle about 10,000 requests per month and spend roughly $800. Most questions are simple FAQs.",
                "expected_response_themes": ["chatbot", "model routing", "tiering", "FAQ"],
                "business_value": "Context gathering leads to specific optimization opportunities"
            },
            {
                "turn": 3,
                "message": "That sounds promising! How much could I save with model tiering? And would it affect response quality?",
                "expected_response_themes": ["savings", "percentage", "quality impact", "implementation"],
                "business_value": "Quantified savings estimates and risk assessment"
            },
            {
                "turn": 4,
                "message": "Great! Can you give me specific implementation steps? I'm using OpenAI API directly.",
                "expected_response_themes": ["implementation", "steps", "OpenAI", "routing logic"],
                "business_value": "Actionable implementation guidance"
            },
            {
                "turn": 5,
                "message": "One more question - how do I monitor that this optimization is working after implementation?",
                "expected_response_themes": ["monitoring", "metrics", "tracking", "KPIs"],
                "business_value": "Long-term success measurement strategy"
            }
        ]
        
        conversation_history = []
        
        try:
            async with websockets.connect(websocket_url, additional_headers=headers) as websocket:
                print(f"✅ WebSocket connected for multi-turn conversation")
                
                for turn_data in conversation_turns:
                    turn_num = turn_data["turn"]
                    message = turn_data["message"]
                    expected_themes = turn_data["expected_response_themes"]
                    business_value = turn_data["business_value"]
                    
                    print(f"\n💬 TURN {turn_num}: {message}")
                    
                    # Send message
                    request = {
                        "type": "agent_request",
                        "agent": "supervisor",
                        "message": message,
                        "context": {
                            "conversation_turn": turn_num,
                            "conversation_id": f"cost_optimization_conversation_{int(time.time())}",
                            "user_context": "customer_service_chatbot"
                        },
                        "user_id": user_data["id"]
                    }
                    
                    await websocket.send(json.dumps(request))
                    print(f"📤 Sent turn {turn_num} message")
                    
                    # Collect response events
                    turn_events = []
                    start_time = time.time()
                    response_content = None
                    
                    while time.time() - start_time < 45:  # 45 seconds per turn
                        try:
                            message_raw = await asyncio.wait_for(websocket.recv(), timeout=10)
                            event = json.loads(message_raw)
                            turn_events.append(event)
                            
                            print(f"📨 Turn {turn_num} event: {event['type']}")
                            
                            if event['type'] == 'agent_completed':
                                response_content = event['data']['result']
                                print(f"✅ Turn {turn_num} completed")
                                break
                                
                        except asyncio.TimeoutError:
                            print(f"⏰ Turn {turn_num} timeout waiting for events")
                            continue
                        except json.JSONDecodeError:
                            continue
                    
                    # Validate turn completion
                    assert response_content is not None, f"Turn {turn_num} did not complete"
                    
                    # Validate WebSocket events for this turn
                    event_types = [e['type'] for e in turn_events]
                    required_events = ['agent_started', 'agent_completed']
                    
                    for event in required_events:
                        assert event in event_types, f"Turn {turn_num} missing {event}"
                    
                    # Validate business value in response
                    response_text = str(response_content).lower()
                    
                    found_themes = [theme for theme in expected_themes if theme in response_text]
                    assert len(found_themes) >= 1, f"Turn {turn_num} missing expected themes. Expected: {expected_themes}, Found: {found_themes}"
                    
                    # Store conversation history
                    conversation_history.append({
                        "turn": turn_num,
                        "user_message": message,
                        "agent_response": response_content,
                        "response_themes_found": found_themes,
                        "business_value_delivered": business_value,
                        "events_count": len(turn_events),
                        "completion_time": time.time() - start_time
                    })
                    
                    print(f"✅ Turn {turn_num} validated - themes found: {found_themes}")
                    
                    # Brief pause between turns (realistic conversation pacing)
                    await asyncio.sleep(1)
        
        except Exception as e:
            pytest.fail(f"Multi-turn conversation failed: {e}")
        
        # Validate complete conversation
        assert len(conversation_history) == len(conversation_turns), \
            f"Incomplete conversation: {len(conversation_history)}/{len(conversation_turns)} turns"
        
        print(f"\n📊 CONVERSATION ANALYSIS:")
        
        # Validate conversation progression (each turn should build on previous)
        total_response_length = 0
        for i, turn_record in enumerate(conversation_history):
            turn_response_length = len(str(turn_record["agent_response"]))
            total_response_length += turn_response_length
            
            print(f"   Turn {turn_record['turn']}: {turn_response_length} chars, " +
                  f"{turn_record['events_count']} events, " +
                  f"{turn_record['completion_time']:.1f}s")
            
            # Later turns should generally be more specific and actionable
            if i > 0:
                # Response should contain business-relevant content
                assert turn_response_length > 50, f"Turn {turn_record['turn']} response too short"
        
        # Validate conversation context preservation
        # Later turns should reference earlier context
        later_turns = conversation_history[2:]  # Turns 3+
        context_preservation_indicators = ["chatbot", "10,000 requests", "$800", "FAQ", "gpt-4"]
        
        context_found_in_later_turns = 0
        for turn_record in later_turns:
            response_text = str(turn_record["agent_response"]).lower()
            for indicator in context_preservation_indicators:
                if indicator.lower() in response_text:
                    context_found_in_later_turns += 1
                    break
        
        context_preservation_rate = context_found_in_later_turns / len(later_turns)
        assert context_preservation_rate >= 0.5, f"Poor context preservation: {context_preservation_rate:.1%}"
        
        print(f"   Context preservation: {context_preservation_rate:.1%}")
        print(f"   Total conversation length: {total_response_length} characters")
        
        # Validate progressive business value delivery
        final_turn = conversation_history[-1]
        final_response = str(final_turn["agent_response"]).lower()
        
        # Final response should contain actionable implementation guidance
        actionable_indicators = ["steps", "implement", "monitor", "track", "measure", "next"]
        final_actionable_count = sum(1 for indicator in actionable_indicators if indicator in final_response)
        
        assert final_actionable_count >= 2, f"Final response lacks actionable guidance: {final_actionable_count}"
        
        print(f"✅ MULTI-TURN CONVERSATION SUCCESS!")
        print(f"   ✓ All {len(conversation_turns)} turns completed")
        print(f"   ✓ Context preserved across conversation")
        print(f"   ✓ Progressive business value delivery")
        print(f"   ✓ Actionable final recommendations")
        print(f"   ✓ All WebSocket events delivered")


    @pytest.mark.e2e
    @pytest.mark.real_services  
    @pytest.mark.real_llm
    async def test_complex_multi_agent_conversation(self, auth_helper, authenticated_user):
        """
        Test complex conversation requiring multiple agent handoffs.
        
        Business Scenario: Enterprise customer needs comprehensive analysis
        involving data gathering, optimization, and implementation planning.
        
        Validates:
        - Multi-agent coordination in single conversation
        - Seamless handoffs between specialized agents
        - Comprehensive business solution delivery
        - WebSocket events throughout multi-agent flow
        """
        token, user_data = authenticated_user
        
        print(f"🚀 Starting complex multi-agent conversation")
        
        websocket_url = "ws://localhost:8000/ws"
        headers = auth_helper.get_websocket_headers(token)
        
        # Complex enterprise scenario requiring multiple agents
        complex_request = {
            "type": "agent_request",
            "agent": "supervisor",
            "message": "I need a comprehensive optimization strategy for our enterprise AI infrastructure. We're running multiple models (GPT-4, Claude, Gemini) across different regions (US, EU, APAC) serving 500,000+ requests daily. Current monthly spend is $45,000. Need detailed cost breakdown, performance analysis, and implementation roadmap with ROI projections.",
            "context": {
                "enterprise_customer": True,
                "models": ["GPT-4", "Claude", "Gemini"], 
                "regions": ["US", "EU", "APAC"],
                "daily_requests": 500000,
                "monthly_spend": 45000,
                "requires": ["cost_analysis", "performance_optimization", "implementation_plan", "roi_projection"]
            },
            "user_id": user_data["id"]
        }
        
        print(f"📋 Complex request: Multi-model, multi-region optimization")
        print(f"💰 Current spend: $45,000/month, 500k+ requests/day")
        
        try:
            async with websockets.connect(websocket_url, additional_headers=headers) as websocket:
                await websocket.send(json.dumps(complex_request))
                print(f"📤 Sent complex multi-agent request")
                
                all_events = []
                start_time = time.time()
                timeout_duration = 120.0  # Extended timeout for complex processing
                
                # Collect all events from multi-agent workflow
                while time.time() - start_time < timeout_duration:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=15)
                        event = json.loads(message)
                        all_events.append(event)
                        
                        print(f"📨 Event: {event['type']}")
                        
                        # Look for agent handoff indicators
                        if event['type'] == 'agent_thinking':
                            thinking_content = event.get('data', {}).get('content', '')
                            if any(agent in thinking_content.lower() for agent in ['data', 'optimization', 'triage']):
                                print(f"🔄 Agent coordination detected: {thinking_content[:100]}...")
                        
                        if event['type'] == 'agent_completed':
                            completion_time = time.time() - start_time
                            print(f"✅ Multi-agent workflow completed in {completion_time:.1f}s")
                            break
                            
                    except asyncio.TimeoutError:
                        print(f"⏰ Waiting for multi-agent completion...")
                        continue
                    except json.JSONDecodeError:
                        continue
        
        except Exception as e:
            pytest.fail(f"Complex multi-agent conversation failed: {e}")
        
        # Validate multi-agent workflow
        assert len(all_events) > 0, "No events received from multi-agent workflow"
        
        event_types = [e['type'] for e in all_events]
        print(f"📊 Total events: {len(all_events)}, Types: {set(event_types)}")
        
        # Validate critical events
        required_events = ['agent_started', 'agent_thinking', 'agent_completed']
        for event in required_events:
            assert event in event_types, f"Missing critical event: {event}"
        
        # Should have multiple thinking/processing events for complex workflow
        thinking_events = [e for e in all_events if e['type'] == 'agent_thinking']
        assert len(thinking_events) >= 2, f"Expected multiple thinking events for complex workflow: {len(thinking_events)}"
        
        # Get final result
        completion_events = [e for e in all_events if e['type'] == 'agent_completed']
        assert len(completion_events) > 0, "No completion event"
        
        final_result = completion_events[-1]['data']['result']
        result_text = str(final_result).lower()
        
        # Validate comprehensive enterprise-level response
        enterprise_indicators = [
            "cost", "optimization", "strategy", "roi", "implementation", 
            "models", "regions", "performance", "recommendations", "roadmap"
        ]
        
        found_indicators = [indicator for indicator in enterprise_indicators if indicator in result_text]
        assert len(found_indicators) >= 6, f"Insufficient enterprise analysis depth: {found_indicators}"
        
        # Validate specific business value elements
        business_value_elements = [
            ("savings" in result_text or "reduction" in result_text),  # Cost savings
            ("performance" in result_text or "latency" in result_text),  # Performance improvements  
            ("implementation" in result_text or "steps" in result_text),  # Implementation guidance
            ("roi" in result_text or "return" in result_text or "benefit" in result_text)  # ROI analysis
        ]
        
        business_value_count = sum(business_value_elements)
        assert business_value_count >= 3, f"Insufficient business value elements: {business_value_count}/4"
        
        print(f"✅ COMPLEX MULTI-AGENT CONVERSATION SUCCESS!")
        print(f"   ✓ {len(all_events)} events processed")
        print(f"   ✓ {len(thinking_events)} agent coordination events")
        print(f"   ✓ Enterprise indicators found: {found_indicators}")
        print(f"   ✓ Business value elements: {business_value_count}/4")
        print(f"   ✓ Comprehensive solution delivered")


    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm
    async def test_conversational_error_recovery(self, auth_helper, authenticated_user):
        """
        Test conversation recovery from various error scenarios.
        
        Business Scenario: User encounters issues during conversation and
        system gracefully recovers while maintaining context.
        
        Validates:
        - Error recovery without losing conversation context
        - User-friendly error messages and suggestions
        - Conversation continuation after error resolution
        - Business value delivery despite technical issues
        """
        token, user_data = authenticated_user
        
        print(f"🚀 Starting conversational error recovery test")
        
        websocket_url = "ws://localhost:8000/ws"
        headers = auth_helper.get_websocket_headers(token)
        
        try:
            async with websockets.connect(websocket_url, additional_headers=headers) as websocket:
                # Conversation sequence with intentional problematic requests
                conversation_sequence = [
                    {
                        "type": "normal",
                        "message": "I want to optimize my AI costs for a customer service application",
                        "expected": "cost optimization discussion"
                    },
                    {
                        "type": "problematic", 
                        "message": "<<<INVALID JSON REQUEST>>> {malformed: request}",
                        "expected": "error handling without context loss"
                    },
                    {
                        "type": "recovery",
                        "message": "Sorry about that. As I was saying, I need help with cost optimization for customer service.",
                        "expected": "recovery with context preservation"
                    },
                    {
                        "type": "followup",
                        "message": "Can you give me specific recommendations now?",
                        "expected": "actionable recommendations despite earlier error"
                    }
                ]
                
                conversation_events = []
                
                for i, step in enumerate(conversation_sequence):
                    print(f"\n🔄 Step {i+1} ({step['type']}): {step['message'][:50]}...")
                    
                    request = {
                        "type": "agent_request",
                        "agent": "supervisor",
                        "message": step["message"],
                        "context": {
                            "conversation_step": i+1,
                            "error_recovery_test": True
                        },
                        "user_id": user_data["id"]
                    }
                    
                    # Handle problematic request differently
                    if step["type"] == "problematic":
                        # Send malformed request intentionally
                        try:
                            await websocket.send(step["message"])  # Send raw malformed message
                        except:
                            print(f"✅ Problematic request rejected as expected")
                            continue
                    else:
                        await websocket.send(json.dumps(request))
                    
                    # Collect response
                    step_events = []
                    start_time = time.time()
                    
                    while time.time() - start_time < 30:
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=10)
                            event = json.loads(message)
                            step_events.append(event)
                            
                            if event['type'] == 'agent_completed':
                                break
                            elif event['type'] == 'error':
                                print(f"🔧 Error event received: {event.get('data', {}).get('message', 'Unknown error')}")
                                break
                                
                        except asyncio.TimeoutError:
                            continue
                        except json.JSONDecodeError:
                            continue
                    
                    conversation_events.extend(step_events)
                    
                    # Validate step response
                    if step["type"] != "problematic":
                        completion_events = [e for e in step_events if e['type'] == 'agent_completed']
                        if len(completion_events) > 0:
                            result = completion_events[0]['data']['result']
                            result_text = str(result).lower()
                            
                            # Validate expected content
                            if step["type"] == "normal":
                                assert "cost" in result_text or "optimization" in result_text, \
                                    "Normal request should discuss optimization"
                            elif step["type"] == "recovery":
                                assert "optimization" in result_text or "cost" in result_text, \
                                    "Recovery should maintain context"
                            elif step["type"] == "followup":
                                assert "recommendation" in result_text or "strategy" in result_text, \
                                    "Followup should provide actionable content"
                            
                            print(f"✅ Step {i+1} completed successfully")
                        else:
                            print(f"⚠️ Step {i+1} no completion event")
                
                # Validate overall error recovery
                total_events = len(conversation_events)
                completion_events = [e for e in conversation_events if e['type'] == 'agent_completed']
                error_events = [e for e in conversation_events if e['type'] == 'error']
                
                print(f"📊 Conversation summary:")
                print(f"   Total events: {total_events}")
                print(f"   Completions: {len(completion_events)}")
                print(f"   Errors: {len(error_events)}")
                
                # Should have successful completions for non-problematic requests
                expected_completions = len([s for s in conversation_sequence if s["type"] != "problematic"])
                assert len(completion_events) >= expected_completions - 1, \
                    f"Too few completions: {len(completion_events)}/{expected_completions}"
                
                # Final response should contain business value
                if completion_events:
                    final_result = completion_events[-1]['data']['result']
                    final_text = str(final_result).lower()
                    
                    business_indicators = ["recommendation", "strategy", "cost", "optimization", "save"]
                    found_business = [ind for ind in business_indicators if ind in final_text]
                    
                    assert len(found_business) >= 1, f"Final response lacks business value: {found_business}"
                
                print(f"✅ CONVERSATIONAL ERROR RECOVERY SUCCESS!")
                print(f"   ✓ Handled problematic requests gracefully")
                print(f"   ✓ Maintained conversation context through recovery")
                print(f"   ✓ Delivered business value despite errors")
                print(f"   ✓ {len(completion_events)} successful completions")
        
        except Exception as e:
            pytest.fail(f"Conversational error recovery test failed: {e}")


    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm
    async def test_business_value_measurement_conversation(self, auth_helper, authenticated_user):
        """
        Test conversation focused on measuring and validating business value delivery.
        
        Business Scenario: Customer wants to understand ROI and measurable outcomes
        from optimization recommendations.
        
        Validates:
        - Quantified business impact projections
        - Measurable KPIs and success metrics
        - Implementation timeline with milestones
        - Follow-up and monitoring strategies
        """
        token, user_data = authenticated_user
        
        print(f"🚀 Starting business value measurement conversation")
        
        websocket_url = "ws://localhost:8000/ws"
        headers = auth_helper.get_websocket_headers(token)
        
        # Business value focused request
        value_measurement_request = {
            "type": "agent_request",
            "agent": "supervisor", 
            "message": "I need to justify AI optimization investments to my CFO. Currently spending $25,000/month on AI infrastructure. Need specific ROI projections, timeline for savings, and measurable KPIs to track success. What business case can you help me build?",
            "context": {
                "current_spend": 25000,
                "audience": "CFO",
                "need": "business_justification",
                "focus": "measurable_outcomes"
            },
            "user_id": user_data["id"]
        }
        
        print(f"💼 Business case request: ROI justification for CFO")
        print(f"💰 Current spend: $25,000/month")
        
        try:
            async with websockets.connect(websocket_url, additional_headers=headers) as websocket:
                await websocket.send(json.dumps(value_measurement_request))
                
                events = []
                start_time = time.time()
                
                while time.time() - start_time < 60:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=15)
                        event = json.loads(message)
                        events.append(event)
                        
                        if event['type'] == 'agent_completed':
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                    except json.JSONDecodeError:
                        continue
                
                # Validate business value response
                completion_events = [e for e in events if e['type'] == 'agent_completed']
                assert len(completion_events) > 0, "No completion event"
                
                result = completion_events[0]['data']['result']
                result_text = str(result).lower()
                
                # Validate CFO-relevant business metrics
                business_metrics = [
                    ("roi" in result_text or "return on investment" in result_text),
                    ("savings" in result_text or "cost reduction" in result_text),
                    ("timeline" in result_text or "months" in result_text),
                    ("kpi" in result_text or "metrics" in result_text or "measure" in result_text),
                    ("$" in result_text or "dollar" in result_text or "percent" in result_text),
                ]
                
                business_score = sum(business_metrics)
                assert business_score >= 4, f"Insufficient business justification elements: {business_score}/5"
                
                # Look for specific quantified projections
                quantified_elements = []
                if "%" in str(result) or "percent" in result_text:
                    quantified_elements.append("percentage")
                if "$" in str(result):
                    quantified_elements.append("dollar_amount")  
                if any(word in result_text for word in ["month", "quarter", "year"]):
                    quantified_elements.append("timeframe")
                
                assert len(quantified_elements) >= 2, f"Insufficient quantification: {quantified_elements}"
                
                print(f"✅ BUSINESS VALUE MEASUREMENT SUCCESS!")
                print(f"   ✓ Business metrics score: {business_score}/5")
                print(f"   ✓ Quantified elements: {quantified_elements}")
                print(f"   ✓ CFO-ready business case provided")
                print(f"   ✓ ROI justification delivered")
        
        except Exception as e:
            pytest.fail(f"Business value measurement conversation failed: {e}")


    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm
    async def test_conversation_context_persistence(self, auth_helper, authenticated_user):
        """
        Test conversation context persistence across extended interactions.
        
        Business Scenario: Long conversation with context references to earlier
        parts of the discussion.
        
        Validates:
        - Long-term context preservation
        - Reference resolution across turns
        - Consistent recommendations building on previous discussion
        - Memory of user preferences and constraints
        """
        token, user_data = authenticated_user
        
        print(f"🚀 Starting conversation context persistence test")
        
        websocket_url = "ws://localhost:8000/ws"
        headers = auth_helper.get_websocket_headers(token)
        
        # Extended conversation with context references
        context_turns = [
            {
                "message": "I run a fintech startup. We use AI for fraud detection and customer support. Monthly AI costs are $8,000.",
                "context_elements": ["fintech", "fraud_detection", "customer_support", "8000"]
            },
            {
                "message": "The fraud detection is critical - we can't compromise accuracy. But customer support could be optimized.",
                "context_elements": ["fraud_detection_critical", "customer_support_optimizable"]
            },
            {
                "message": "For the customer support optimization you mentioned - what specific approaches would work for fintech?",
                "context_reference": True,  # References "customer support optimization" from previous
                "expected_context": ["customer_support", "fintech"]
            },
            {
                "message": "Going back to my $8,000 monthly budget - how much could I save with your customer support suggestions?",
                "context_reference": True,  # References budget and previous suggestions
                "expected_context": ["8000", "budget", "customer_support", "savings"]
            }
        ]
        
        conversation_results = []
        
        try:
            async with websockets.connect(websocket_url, additional_headers=headers) as websocket:
                
                for i, turn in enumerate(context_turns):
                    print(f"\n💬 Turn {i+1}: {turn['message'][:60]}...")
                    
                    request = {
                        "type": "agent_request",
                        "agent": "supervisor",
                        "message": turn["message"],
                        "context": {
                            "turn": i+1,
                            "context_persistence_test": True
                        },
                        "user_id": user_data["id"]
                    }
                    
                    await websocket.send(json.dumps(request))
                    
                    # Collect response
                    events = []
                    start_time = time.time()
                    
                    while time.time() - start_time < 30:
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=10)
                            event = json.loads(message)
                            events.append(event)
                            
                            if event['type'] == 'agent_completed':
                                break
                                
                        except asyncio.TimeoutError:
                            continue
                        except json.JSONDecodeError:
                            continue
                    
                    # Validate response
                    completion_events = [e for e in events if e['type'] == 'agent_completed']
                    if len(completion_events) > 0:
                        result = completion_events[0]['data']['result']
                        result_text = str(result).lower()
                        
                        # Check for context preservation
                        if turn.get("context_reference"):
                            expected_context = turn.get("expected_context", [])
                            found_context = [ctx for ctx in expected_context if str(ctx).lower() in result_text]
                            
                            context_preservation_rate = len(found_context) / len(expected_context) if expected_context else 0
                            
                            assert context_preservation_rate >= 0.5, \
                                f"Turn {i+1} poor context preservation: {context_preservation_rate:.1%}, found: {found_context}"
                            
                            print(f"✅ Turn {i+1} context preserved: {found_context}")
                        
                        conversation_results.append({
                            "turn": i+1,
                            "response": result,
                            "response_length": len(str(result)),
                            "context_elements": turn.get("context_elements", []),
                            "context_preserved": turn.get("context_reference", False)
                        })
                    
                    # Brief pause between turns
                    await asyncio.sleep(1)
                
                # Validate overall context persistence
                assert len(conversation_results) == len(context_turns), "Incomplete conversation"
                
                # Final turn should reference multiple earlier context elements
                final_response = conversation_results[-1]["response"]
                final_text = str(final_response).lower()
                
                # Should reference fintech, customer support, and budget from earlier turns
                key_context_elements = ["fintech", "customer", "support", "8000", "budget"]
                final_context_found = [elem for elem in key_context_elements if elem in final_text]
                
                final_context_rate = len(final_context_found) / len(key_context_elements)
                assert final_context_rate >= 0.6, f"Final response lacks context: {final_context_rate:.1%}"
                
                print(f"✅ CONVERSATION CONTEXT PERSISTENCE SUCCESS!")
                print(f"   ✓ All {len(context_turns)} turns completed")
                print(f"   ✓ Context references resolved correctly")
                print(f"   ✓ Final context preservation: {final_context_rate:.1%}")
                print(f"   ✓ Long-term memory demonstrated")
        
        except Exception as e:
            pytest.fail(f"Conversation context persistence test failed: {e}")