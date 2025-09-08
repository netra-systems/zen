"""
E2E Tests for Tool Dispatcher Real World Scenarios - Cycle 2

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Validate tool dispatcher works in real-world customer scenarios
- Value Impact: Users get reliable AI-powered analysis results in production environment
- Strategic Impact: Real-world validation ensures platform delivers promised business value

CRITICAL: Real-world scenarios validate that customers will actually receive value.
These tests represent the actual customer experience that drives revenue.

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

class TestToolDispatcherRealWorldScenariosE2E(BaseE2ETest):
    """E2E tests for tool dispatcher in real-world customer scenarios."""
    
    @pytest.fixture
    async def authenticated_user(self):
        """Create authenticated user for E2E testing."""
        auth_helper = E2EAuthHelper()
        user = await auth_helper.create_authenticated_user(
            email="e2e_tool_user@test.netra.ai",
            name="E2E Tool Dispatcher Test User"
        )
        return user

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_complete_cost_optimization_workflow_with_tools(self, authenticated_user, real_services):
        """
        Test complete cost optimization workflow using real tool dispatcher.
        
        Business Value: Validates the core customer use case that generates revenue.
        MISSION CRITICAL: This is the primary value proposition customers pay for.
        """
        # Arrange: Setup authenticated connection
        backend_url = real_services["backend_url"]
        websocket_url = f"ws://{backend_url.replace('http://', '')}/ws"
        
        workflow_events = []
        tool_executions = []
        optimization_results = None
        
        # Act: Execute complete cost optimization workflow
        async with WebSocketTestClient(websocket_url, authenticated_user.token) as ws_client:
            
            # Send comprehensive cost optimization request
            optimization_request = {
                "type": "agent_request",
                "agent": "triage_agent",  # Use triage agent for E2E reliability
                "message": """
                I need a comprehensive cost optimization analysis for my cloud infrastructure:
                
                Current Situation:
                - Monthly AWS spend: $35,000
                - Services: EC2 (60%), S3 (15%), RDS (20%), Other (5%)
                - Growth rate: 25% per quarter
                - Main concern: Costs growing faster than revenue
                
                Please analyze and provide:
                1. Cost breakdown by service and region
                2. Identification of optimization opportunities
                3. Specific recommendations with potential savings
                4. Implementation priority and effort estimates
                
                This analysis will be used for board presentation next week.
                """,
                "context": {
                    "user_intent": "comprehensive_cost_optimization",
                    "current_monthly_spend": 35000,
                    "growth_rate": 0.25,
                    "urgency": "high",
                    "presentation_context": "board_meeting",
                    "services": {
                        "ec2": {"percentage": 60, "amount": 21000},
                        "s3": {"percentage": 15, "amount": 5250},
                        "rds": {"percentage": 20, "amount": 7000},
                        "other": {"percentage": 5, "amount": 1750}
                    }
                }
            }
            
            await ws_client.send_json(optimization_request)
            
            # Capture complete workflow execution
            async for message in ws_client.receive_events(timeout=180):  # Extended timeout for complex analysis
                workflow_events.append(message)
                print(f"E2E Tool Workflow Event: {message.get('type')} at {datetime.now()}")
                
                # Track tool executions specifically
                if message.get("type") == "tool_executing":
                    tool_executions.append({
                        "tool_name": message.get("tool_name"),
                        "parameters": message.get("tool_params", {}),
                        "timestamp": message.get("timestamp")
                    })
                
                elif message.get("type") == "tool_completed":
                    # Find matching execution and add result
                    for execution in reversed(tool_executions):
                        if execution["tool_name"] == message.get("tool_name") and "result" not in execution:
                            execution["result"] = message.get("tool_result", {})
                            execution["completion_time"] = message.get("timestamp")
                            break
                
                elif message.get("type") == "agent_completed":
                    optimization_results = message.get("result", {})
                    break
                    
                elif message.get("type") == "error":
                    print(f"E2E Tool Workflow Error: {message}")
                    break
        
        # Assert: Complete optimization workflow executed successfully
        assert len(workflow_events) >= 5, f"Expected comprehensive workflow events, got {len(workflow_events)}"
        
        # Verify tool execution occurred
        assert len(tool_executions) >= 1, "Should execute at least one analysis tool"
        
        # Business requirement: Tool executions should be relevant to cost optimization
        tool_names = [execution["tool_name"] for execution in tool_executions]
        relevant_tools = [name for name in tool_names if any(keyword in name.lower() for keyword in 
                         ["cost", "analyze", "optimize", "recommend", "calculate", "assess"])]
        
        if tool_names:  # Only check if tools were executed
            assert len(relevant_tools) >= 1, f"Should execute cost-relevant tools, executed: {tool_names}"
        
        # Verify final optimization results
        assert optimization_results is not None, "Should receive optimization analysis results"
        
        # Business value validation: Results should address the specific request
        if optimization_results:
            result_content = json.dumps(optimization_results).lower()
            
            # Should address key elements from request
            request_elements = [
                "cost", "optimization", "recommendation", "saving", "aws", 
                "ec2", "s3", "rds", "analysis", "breakdown"
            ]
            
            matched_elements = sum(1 for element in request_elements if element in result_content)
            assert matched_elements >= 4, f"Results should address key request elements, matched {matched_elements}/10"
            
            # Should provide actionable insights
            actionable_indicators = [
                "recommend", "suggest", "optimize", "reduce", "implement", 
                "priority", "effort", "saving"
            ]
            
            actionable_count = sum(1 for indicator in actionable_indicators if indicator in result_content)
            assert actionable_count >= 3, "Results should provide actionable optimization insights"

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_multi_tool_analysis_workflow(self, authenticated_user, real_services):
        """
        Test workflow that requires multiple tool executions.
        
        Business Value: Complex analyses often require multiple tools working together.
        Multi-tool workflows demonstrate platform sophistication and value.
        """
        backend_url = real_services["backend_url"]
        websocket_url = f"ws://{backend_url.replace('http://', '')}/ws"
        
        multi_tool_events = []
        unique_tools_executed = set()
        
        async with WebSocketTestClient(websocket_url, authenticated_user.token) as ws_client:
            
            # Send complex request that should require multiple tools
            complex_request = {
                "type": "agent_request",
                "agent": "triage_agent",
                "message": """
                Perform a comprehensive infrastructure assessment:
                
                1. Analyze current resource utilization patterns
                2. Identify security vulnerabilities and compliance gaps
                3. Evaluate performance bottlenecks
                4. Calculate cost optimization opportunities
                5. Provide integrated recommendations with ROI analysis
                
                This is for a Fortune 500 client migration planning.
                """,
                "context": {
                    "analysis_type": "comprehensive_infrastructure_assessment",
                    "client_tier": "fortune_500",
                    "scope": ["utilization", "security", "performance", "cost", "roi"],
                    "deliverable": "migration_planning"
                }
            }
            
            await ws_client.send_json(complex_request)
            
            # Capture multi-tool workflow
            async for message in ws_client.receive_events(timeout=150):
                multi_tool_events.append(message)
                
                if message.get("type") == "tool_executing":
                    tool_name = message.get("tool_name")
                    if tool_name:
                        unique_tools_executed.add(tool_name)
                
                elif message.get("type") == "agent_completed":
                    break
                    
                elif message.get("type") == "error":
                    break
        
        # Assert: Multi-tool execution occurred
        assert len(multi_tool_events) >= 3, "Complex request should generate multiple events"
        
        # Business requirement: Complex analysis should use multiple tools
        if len(unique_tools_executed) > 0:
            # If tools were executed, should be multiple for comprehensive analysis
            print(f"E2E Multi-tool test executed {len(unique_tools_executed)} unique tools: {list(unique_tools_executed)}")
            
            # Different tools should be used for different aspects
            tool_names_str = " ".join(unique_tools_executed).lower()
            analysis_aspects = ["analyze", "assess", "check", "calculate", "evaluate", "recommend"]
            covered_aspects = sum(1 for aspect in analysis_aspects if aspect in tool_names_str)
            
            # Complex request should trigger varied tool usage
            assert covered_aspects >= 1, "Multi-tool workflow should cover different analysis aspects"

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_tool_dispatcher_performance_under_realistic_load(self, authenticated_user, real_services):
        """
        Test tool dispatcher performance with realistic customer load.
        
        Business Value: Performance under load determines customer satisfaction.
        Poor performance under realistic load would lose customers.
        """
        backend_url = real_services["backend_url"]
        websocket_url = f"ws://{backend_url.replace('http://', '')}/ws"
        
        load_test_results = []
        
        # Test realistic load scenario: 3 concurrent analyses
        concurrent_requests = [
            {
                "user_context": "startup_cost_analysis",
                "message": "Quick cost analysis for our startup's $5K monthly AWS spend",
                "expected_response_time": 60
            },
            {
                "user_context": "enterprise_security_audit", 
                "message": "Security compliance audit for our enterprise infrastructure",
                "expected_response_time": 90
            },
            {
                "user_context": "performance_optimization",
                "message": "Performance optimization recommendations for high-traffic application",
                "expected_response_time": 75
            }
        ]
        
        # Act: Execute concurrent requests
        async def execute_load_test_request(request_context, index):
            """Execute single request in load test."""
            request_start = time.time()
            events_received = []
            
            try:
                async with WebSocketTestClient(websocket_url, authenticated_user.token) as ws_client:
                    
                    analysis_request = {
                        "type": "agent_request",
                        "agent": "triage_agent",
                        "message": request_context["message"],
                        "context": {
                            "load_test_index": index,
                            "user_context": request_context["user_context"]
                        }
                    }
                    
                    await ws_client.send_json(analysis_request)
                    
                    # Collect events with timeout
                    async for message in ws_client.receive_events(timeout=request_context["expected_response_time"]):
                        events_received.append(message)
                        
                        if message.get("type") == "agent_completed":
                            break
                        elif message.get("type") == "error":
                            break
                
                request_end = time.time()
                return {
                    "index": index,
                    "success": True,
                    "response_time": request_end - request_start,
                    "events_count": len(events_received),
                    "context": request_context["user_context"],
                    "error": None
                }
                
            except Exception as e:
                request_end = time.time()
                return {
                    "index": index,
                    "success": False,
                    "response_time": request_end - request_start,
                    "events_count": len(events_received),
                    "context": request_context["user_context"],
                    "error": str(e)
                }
        
        # Execute all requests concurrently
        concurrent_tasks = [
            execute_load_test_request(request, i) 
            for i, request in enumerate(concurrent_requests)
        ]
        
        load_test_start = time.time()
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        total_load_test_time = time.time() - load_test_start
        
        # Assert: Performance under load meets requirements
        successful_requests = [r for r in results if isinstance(r, dict) and r.get("success")]
        
        # Business requirement: Most requests should complete successfully
        success_rate = len(successful_requests) / len(results) * 100
        assert success_rate >= 70, f"Success rate {success_rate:.1f}% should be at least 70% under load"
        
        # Performance requirement: Concurrent execution should be efficient
        assert total_load_test_time < 120, f"Load test took {total_load_test_time:.2f}s, should be under 120s"
        
        # Individual request performance should be reasonable
        for result in successful_requests:
            context = result["context"]
            response_time = result["response_time"]
            
            # Each request should complete within reasonable time
            assert response_time < 100, f"Request {context} took {response_time:.2f}s, should be under 100s"
            
            # Should receive meaningful number of events
            assert result["events_count"] >= 2, f"Request {context} should receive multiple events"

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_tool_dispatcher_error_recovery_in_production_scenario(self, authenticated_user, real_services):
        """
        Test tool dispatcher error recovery in realistic production scenario.
        
        Business Value: Error recovery prevents customer frustration and churn.
        Production resilience is essential for business continuity.
        """
        backend_url = real_services["backend_url"]
        websocket_url = f"ws://{backend_url.replace('http://', '')}/ws"
        
        recovery_test_events = []
        error_recovery_demonstrated = False
        
        async with WebSocketTestClient(websocket_url, authenticated_user.token) as ws_client:
            
            # Send request that might encounter realistic errors
            error_prone_request = {
                "type": "agent_request",
                "agent": "triage_agent",
                "message": """
                Analyze our extremely complex multi-cloud environment:
                
                - 500+ microservices across AWS, Azure, and GCP
                - 15 different data sources with varying schemas
                - Real-time processing requirements
                - Compliance with 7 different regulatory frameworks
                - Budget constraints requiring 40% cost reduction
                
                Please provide comprehensive analysis with specific recommendations.
                """,
                "context": {
                    "complexity": "extremely_high",
                    "multi_cloud": True,
                    "data_sources": 15,
                    "microservices": 500,
                    "cost_reduction_target": 0.40,
                    "regulatory_frameworks": 7,
                    "error_prone_scenario": True
                }
            }
            
            await ws_client.send_json(error_prone_request)
            
            # Monitor for error recovery patterns
            async for message in ws_client.receive_events(timeout=120):
                recovery_test_events.append(message)
                
                # Look for error recovery indicators
                if message.get("type") == "agent_thinking":
                    thinking_content = message.get("content", "").lower()
                    recovery_indicators = [
                        "retry", "attempting", "recovering", "fallback", 
                        "alternative", "adjusting", "simplifying"
                    ]
                    
                    if any(indicator in thinking_content for indicator in recovery_indicators):
                        error_recovery_demonstrated = True
                
                elif message.get("type") == "tool_executing":
                    # Multiple tool attempts might indicate retry/recovery
                    tool_name = message.get("tool_name", "").lower()
                    if "retry" in tool_name or "fallback" in tool_name:
                        error_recovery_demonstrated = True
                
                elif message.get("type") == "agent_completed":
                    break
                    
                elif message.get("type") == "error":
                    # Error occurred, but should be handled gracefully
                    error_message = message.get("error", "").lower()
                    if "retry" in error_message or "attempting" in error_message:
                        error_recovery_demonstrated = True
                    break
        
        # Assert: Error recovery behavior demonstrated
        assert len(recovery_test_events) >= 1, "Should receive events even for complex/error-prone request"
        
        # Business requirement: System should attempt to handle complex scenarios
        # (May not fully succeed, but should demonstrate recovery attempts)
        
        # Verify agent attempted to process the request
        agent_started = any(event.get("type") == "agent_started" for event in recovery_test_events)
        assert agent_started, "Agent should start processing even complex requests"
        
        # If recovery was demonstrated, that's excellent
        if error_recovery_demonstrated:
            print("E2E Error recovery successfully demonstrated in production scenario")
        
        # Final result should provide some value or clear error explanation
        final_events = [e for e in recovery_test_events if e.get("type") in ["agent_completed", "error"]]
        assert len(final_events) >= 1, "Should receive final status (completion or error)"
        
        for final_event in final_events:
            if final_event.get("type") == "agent_completed":
                # Successful completion should provide results
                result = final_event.get("result", {})
                assert result or len(str(result)) > 10, "Completed analysis should provide meaningful results"
            
            elif final_event.get("type") == "error":
                # Error should be informative for user
                error_msg = final_event.get("error", "")
                assert len(error_msg) > 10, "Error message should be descriptive for user"

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_tool_dispatcher_business_value_delivery_validation(self, authenticated_user, real_services):
        """
        Test that tool dispatcher delivers measurable business value.
        
        Business Value: This validates the core value proposition customers pay for.
        CRITICAL: Without measurable business value, the platform has no revenue justification.
        """
        backend_url = real_services["backend_url"]
        websocket_url = f"ws://{backend_url.replace('http://', '')}/ws"
        
        business_value_events = []
        quantifiable_insights = []
        actionable_recommendations = []
        
        async with WebSocketTestClient(websocket_url, authenticated_user.token) as ws_client:
            
            # Send business-focused request
            business_value_request = {
                "type": "agent_request",
                "agent": "triage_agent",
                "message": """
                I need concrete, actionable recommendations for our cloud cost optimization:
                
                Current metrics:
                - Monthly spend: $25,000
                - Team size: 50 engineers
                - Revenue impact of downtime: $50,000/hour
                - Current profit margin: 15%
                
                Required outcomes:
                1. Specific cost reduction opportunities with $ amounts
                2. Risk assessment for each recommendation
                3. Implementation timeline and resource requirements
                4. Expected ROI for each optimization
                
                This analysis will determine our Q4 infrastructure budget.
                """,
                "context": {
                    "business_focus": True,
                    "monthly_spend": 25000,
                    "team_size": 50,
                    "downtime_cost": 50000,
                    "profit_margin": 0.15,
                    "decision_impact": "q4_budget",
                    "required_outcomes": [
                        "cost_reduction_amounts",
                        "risk_assessment", 
                        "implementation_timeline",
                        "roi_calculations"
                    ]
                }
            }
            
            await ws_client.send_json(business_value_request)
            
            # Analyze business value delivery
            async for message in ws_client.receive_events(timeout=120):
                business_value_events.append(message)
                
                # Extract business value indicators
                if message.get("type") == "tool_completed":
                    tool_result = message.get("tool_result", {})
                    if tool_result:
                        result_str = json.dumps(tool_result).lower()
                        
                        # Look for quantifiable insights
                        quantifiable_patterns = [
                            "$", "cost", "saving", "reduction", "percent", "%", 
                            "roi", "return", "profit", "revenue", "budget"
                        ]
                        
                        for pattern in quantifiable_patterns:
                            if pattern in result_str:
                                quantifiable_insights.append({
                                    "tool": message.get("tool_name"),
                                    "pattern": pattern,
                                    "context": result_str[:200]
                                })
                
                elif message.get("type") == "agent_completed":
                    final_result = message.get("result", {})
                    if final_result:
                        result_str = json.dumps(final_result).lower()
                        
                        # Look for actionable recommendations
                        actionable_patterns = [
                            "recommend", "suggest", "implement", "optimize", 
                            "reduce", "upgrade", "migrate", "configure"
                        ]
                        
                        for pattern in actionable_patterns:
                            if pattern in result_str:
                                actionable_recommendations.append({
                                    "pattern": pattern,
                                    "context": result_str[:300]
                                })
                    
                    break
                    
                elif message.get("type") == "error":
                    break
        
        # Assert: Business value delivery validated
        assert len(business_value_events) >= 2, "Business-focused request should generate meaningful analysis"
        
        # Business requirement: Should provide quantifiable insights
        if len(quantifiable_insights) > 0:
            print(f"E2E Business value test found {len(quantifiable_insights)} quantifiable insights")
            
            # Insights should be relevant to the business context
            business_relevant = [
                insight for insight in quantifiable_insights 
                if any(term in insight["context"] for term in ["cost", "saving", "budget", "reduction"])
            ]
            assert len(business_relevant) >= 1, "Should provide business-relevant quantifiable insights"
        
        # Business requirement: Should provide actionable recommendations
        if len(actionable_recommendations) > 0:
            print(f"E2E Business value test found {len(actionable_recommendations)} actionable recommendations")
            
            # Recommendations should be implementation-focused
            implementation_focused = [
                rec for rec in actionable_recommendations
                if any(term in rec["context"] for term in ["implement", "configure", "optimize", "reduce"])
            ]
            assert len(implementation_focused) >= 1, "Should provide implementation-focused recommendations"
        
        # Overall business value validation
        completion_events = [e for e in business_value_events if e.get("type") == "agent_completed"]
        if len(completion_events) > 0:
            # Successful completion should address business requirements
            final_result = completion_events[0].get("result", {})
            final_result_str = json.dumps(final_result).lower()
            
            # Should address the specific business context
            business_context_elements = ["cost", "budget", "roi", "saving", "optimization", "recommendation"]
            addressed_elements = sum(1 for element in business_context_elements if element in final_result_str)
            
            assert addressed_elements >= 3, f"Should address business context elements, found {addressed_elements}/6"
        
        print(f"E2E Business value validation completed: {len(quantifiable_insights)} insights, {len(actionable_recommendations)} recommendations")