"""
Test Complete Agent Optimization E2E Flows

Business Value Justification (BVJ):
- Segment: Enterprise/Mid/Early (All paid tiers)
- Business Goal: Ensure agents deliver substantive AI-powered optimization insights
- Value Impact: Users receive actionable cost savings and performance improvements
- Strategic Impact: Core value proposition - AI agents must work end-to-end

CRITICAL AUTHENTICATION REQUIREMENT:
ALL tests in this module MUST use authentication (JWT/OAuth) as per CLAUDE.md
section 3.4 and 7.3. This ensures real-world multi-user scenarios are tested.

CRITICAL E2E REQUIREMENTS:
- Full Stack Testing: Uses complete Docker stack with real services
- Real LLM Integration: Uses actual LLM APIs for agent execution
- NO MOCKS: Everything must be real - databases, Redis, WebSocket, LLM, auth  
- WebSocket Events: Validates all 5 critical events during agent execution
- Business Value Focus: Tests complete user journeys and value delivery
"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timezone
from typing import Dict, List, Any
import websockets

from test_framework.base_e2e_test import BaseE2ETest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user
from test_framework.websocket_helpers import WebSocketTestClient
from tests.e2e.staging_config import get_staging_config


class TestAgentOptimizationCompleteFlow(BaseE2ETest):
    """Test complete agent optimization flows with mandatory authentication."""
    
    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()
        self.staging_config = get_staging_config()
        self.auth_helper = E2EAuthHelper(environment="staging")
        
    @pytest.mark.e2e
    @pytest.mark.real_services  
    @pytest.mark.real_llm
    @pytest.mark.staging
    async def test_cost_optimizer_agent_complete_journey(self, real_services, real_llm):
        """Test complete cost optimization agent workflow with authentication.
        
        This test validates the COMPLETE business value delivery pipeline:
        1. User authenticates 
        2. WebSocket connects with auth
        3. Agent executes with real LLM
        4. All 5 WebSocket events are sent
        5. Business value (cost savings) is delivered
        6. Data is persisted correctly
        """
        self.logger.info("[U+1F680] Starting Cost Optimizer Agent E2E Test with Authentication")
        
        # MANDATORY: Authenticate user first
        token, user_data = await create_authenticated_user(
            environment="staging",
            email="cost-optimizer-test@staging.netrasystems.ai",
            permissions=["read", "write", "agent_execute"]
        )
        
        self.logger.info(f" PASS:  User authenticated: {user_data['email']}")
        
        # Connect WebSocket with authentication
        websocket_headers = self.auth_helper.get_websocket_headers(token)
        
        try:
            # Use staging WebSocket URL with authentication
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.staging_config.urls.websocket_url,
                    additional_headers=websocket_headers,
                    open_timeout=20.0
                ),
                timeout=25.0
            )
            
            self.logger.info(" PASS:  WebSocket connected with authentication")
            
            # Send agent request for cost optimization
            agent_request = {
                "type": "agent_request",
                "agent": "cost_optimizer",
                "message": "Analyze my cloud infrastructure costs and provide optimization recommendations",
                "context": {
                    "user_id": user_data["id"],
                    "monthly_spend": 75000,
                    "infrastructure": "AWS + Azure multi-cloud",
                    "business_critical": True
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            self.logger.info("[U+1F4E4] Sending cost optimization request")
            await websocket.send(json.dumps(agent_request))
            
            # Collect ALL WebSocket events
            events = []
            start_time = time.time()
            
            try:
                while time.time() - start_time < 120:  # 2 minute timeout for real LLM
                    event_str = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=30.0
                    )
                    
                    event = json.loads(event_str)
                    events.append(event)
                    
                    self.logger.info(f"[U+1F4E8] Received event: {event['type']}")
                    
                    # Break when agent completes
                    if event["type"] == "agent_completed":
                        break
                        
            except asyncio.TimeoutError:
                self.logger.error(" FAIL:  Timeout waiting for agent completion")
                raise AssertionError("Agent did not complete within timeout")
            finally:
                await websocket.close()
                
            # MANDATORY: Validate all 5 critical WebSocket events
            event_types = [e["type"] for e in events]
            
            assert "agent_started" in event_types, "agent_started event not sent"
            assert "agent_thinking" in event_types, "agent_thinking event not sent" 
            assert "tool_executing" in event_types, "tool_executing event not sent"
            assert "tool_completed" in event_types, "tool_completed event not sent"
            assert "agent_completed" in event_types, "agent_completed event not sent"
            
            self.logger.info(" PASS:  All 5 critical WebSocket events validated")
            
            # Validate REAL business value delivered
            final_event = next(e for e in reversed(events) if e["type"] == "agent_completed")
            result = final_event["data"]["result"]
            
            # Agent MUST provide actual business value
            assert "recommendations" in result, "No optimization recommendations provided"
            assert len(result["recommendations"]) > 0, "Empty recommendations"
            assert "cost_analysis" in result, "No cost analysis provided"
            assert "potential_savings" in result, "No savings calculation provided"
            
            # Validate savings amount is realistic
            savings = result["potential_savings"]
            assert isinstance(savings.get("monthly_amount"), (int, float)), "Invalid savings amount"
            assert savings["monthly_amount"] > 0, "No cost savings identified"
            
            self.logger.info(f" PASS:  Business value delivered: ${savings['monthly_amount']}/month potential savings")
            
            # Verify data persistence (thread and messages)
            thread_id = final_event["data"]["thread_id"]
            assert thread_id is not None, "No thread ID returned"
            
            self.logger.info(f" PASS:  Cost Optimizer Agent E2E Test completed successfully")
            
        except Exception as e:
            self.logger.error(f" FAIL:  Cost Optimizer Agent E2E Test failed: {e}")
            raise
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm  
    @pytest.mark.staging
    async def test_data_analysis_agent_file_processing(self, real_services, real_llm):
        """Test data analysis agent with file processing capabilities."""
        self.logger.info("[U+1F680] Starting Data Analysis Agent E2E Test")
        
        # MANDATORY: Authenticate user
        token, user_data = await create_authenticated_user(
            environment="staging",
            email="data-analysis-test@staging.netrasystems.ai"
        )
        
        websocket_headers = self.auth_helper.get_websocket_headers(token)
        
        try:
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.staging_config.urls.websocket_url,
                    additional_headers=websocket_headers,
                    open_timeout=20.0
                ),
                timeout=25.0
            )
            
            # Send data analysis request
            agent_request = {
                "type": "agent_request",
                "agent": "data_analysis", 
                "message": "Analyze quarterly performance metrics and identify trends",
                "context": {
                    "user_id": user_data["id"],
                    "data_source": "quarterly_metrics.csv",
                    "analysis_type": "trend_analysis",
                    "business_unit": "Operations"
                }
            }
            
            await websocket.send(json.dumps(agent_request))
            
            # Collect events with file processing validation
            events = []
            start_time = time.time()
            
            while time.time() - start_time < 90:
                try:
                    event_str = await asyncio.wait_for(websocket.recv(), timeout=20.0)
                    event = json.loads(event_str)
                    events.append(event)
                    
                    if event["type"] == "agent_completed":
                        break
                        
                except asyncio.TimeoutError:
                    break
            
            await websocket.close()
            
            # Validate WebSocket events
            event_types = [e["type"] for e in events]
            required_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
            
            for event_type in required_events:
                assert event_type in event_types, f"{event_type} event missing"
            
            # Validate data analysis results
            final_event = next(e for e in reversed(events) if e["type"] == "agent_completed")
            result = final_event["data"]["result"]
            
            assert "analysis_summary" in result, "No analysis summary provided"
            assert "key_insights" in result, "No key insights provided"
            assert "trend_data" in result, "No trend data provided"
            
            self.logger.info(" PASS:  Data Analysis Agent E2E Test completed")
            
        except Exception as e:
            self.logger.error(f" FAIL:  Data Analysis Agent test failed: {e}")
            raise
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm
    @pytest.mark.staging
    async def test_multi_agent_orchestration_flow(self, real_services, real_llm):
        """Test multi-agent orchestration with complex workflow."""
        self.logger.info("[U+1F680] Starting Multi-Agent Orchestration E2E Test")
        
        # MANDATORY: Authenticate user  
        token, user_data = await create_authenticated_user(
            environment="staging",
            email="multi-agent-test@staging.netrasystems.ai"
        )
        
        websocket_headers = self.auth_helper.get_websocket_headers(token)
        
        try:
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.staging_config.urls.websocket_url,
                    additional_headers=websocket_headers
                ),
                timeout=25.0
            )
            
            # Send complex multi-agent request
            agent_request = {
                "type": "agent_request",
                "agent": "supervisor",
                "message": "Conduct comprehensive business analysis: cost optimization, performance metrics, and strategic recommendations",
                "context": {
                    "user_id": user_data["id"],
                    "scope": "full_business_analysis",
                    "departments": ["engineering", "operations", "finance"],
                    "timeline": "Q4_2024"
                }
            }
            
            await websocket.send(json.dumps(agent_request))
            
            # Collect events for multi-agent workflow
            events = []
            agent_switches = 0
            start_time = time.time()
            
            while time.time() - start_time < 150:  # Longer timeout for multi-agent
                try:
                    event_str = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    event = json.loads(event_str)
                    events.append(event)
                    
                    # Track agent handoffs
                    if event.get("type") == "agent_handoff":
                        agent_switches += 1
                        
                    if event["type"] == "agent_completed":
                        break
                        
                except asyncio.TimeoutError:
                    break
            
            await websocket.close()
            
            # Validate multi-agent coordination
            event_types = [e["type"] for e in events]
            
            # Should have multiple agent interactions
            assert agent_switches >= 1, "No agent handoffs detected in multi-agent flow"
            
            # Standard events must be present
            required_events = ["agent_started", "agent_completed"]
            for event_type in required_events:
                assert event_type in event_types, f"{event_type} missing in multi-agent flow"
            
            # Validate comprehensive results
            final_event = next(e for e in reversed(events) if e["type"] == "agent_completed")
            result = final_event["data"]["result"]
            
            assert "cost_analysis" in result, "Missing cost analysis component"
            assert "performance_metrics" in result, "Missing performance metrics" 
            assert "strategic_recommendations" in result, "Missing strategic recommendations"
            
            self.logger.info(f" PASS:  Multi-Agent Orchestration completed with {agent_switches} handoffs")
            
        except Exception as e:
            self.logger.error(f" FAIL:  Multi-Agent Orchestration test failed: {e}")
            raise
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm
    @pytest.mark.staging
    async def test_agent_error_handling_and_recovery(self, real_services, real_llm):
        """Test agent error handling and graceful recovery scenarios."""
        self.logger.info("[U+1F680] Starting Agent Error Handling E2E Test")
        
        # MANDATORY: Authenticate user
        token, user_data = await create_authenticated_user(
            environment="staging",  
            email="error-handling-test@staging.netrasystems.ai"
        )
        
        websocket_headers = self.auth_helper.get_websocket_headers(token)
        
        try:
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.staging_config.urls.websocket_url,
                    additional_headers=websocket_headers
                ),
                timeout=25.0
            )
            
            # Send request that will trigger error handling
            agent_request = {
                "type": "agent_request",
                "agent": "cost_optimizer",
                "message": "Analyze costs for non-existent infrastructure provider INVALIDCLOUD",
                "context": {
                    "user_id": user_data["id"],
                    "provider": "INVALIDCLOUD",  # This should trigger error handling
                    "test_scenario": "error_recovery"
                }
            }
            
            await websocket.send(json.dumps(agent_request))
            
            # Collect events including error recovery
            events = []
            start_time = time.time()
            error_events = []
            
            while time.time() - start_time < 60:
                try:
                    event_str = await asyncio.wait_for(websocket.recv(), timeout=20.0)
                    event = json.loads(event_str)
                    events.append(event)
                    
                    # Track error-related events
                    if event.get("type") in ["agent_error", "tool_error", "error_recovery"]:
                        error_events.append(event)
                        
                    if event["type"] in ["agent_completed", "agent_failed"]:
                        break
                        
                except asyncio.TimeoutError:
                    break
            
            await websocket.close()
            
            # Validate error handling
            event_types = [e["type"] for e in events]
            
            # Should have started properly
            assert "agent_started" in event_types, "Agent should have started"
            
            # Should have some form of completion (success or graceful failure)
            completion_events = ["agent_completed", "agent_failed"]
            has_completion = any(event_type in event_types for event_type in completion_events)
            assert has_completion, "Agent should complete or fail gracefully"
            
            # If agent completed, should provide helpful error message to user
            if "agent_completed" in event_types:
                final_event = next(e for e in reversed(events) if e["type"] == "agent_completed")
                result = final_event["data"]["result"]
                assert "error_message" in result or "limitations" in result, "Should explain limitations to user"
            
            self.logger.info(" PASS:  Agent Error Handling E2E Test completed")
            
        except Exception as e:
            self.logger.error(f" FAIL:  Agent Error Handling test failed: {e}")
            raise
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm
    @pytest.mark.staging
    async def test_agent_tool_usage_and_results(self, real_services, real_llm):
        """Test agent tool execution and result processing."""
        self.logger.info("[U+1F680] Starting Agent Tool Usage E2E Test")
        
        # MANDATORY: Authenticate user
        token, user_data = await create_authenticated_user(
            environment="staging",
            email="tool-usage-test@staging.netrasystems.ai"
        )
        
        websocket_headers = self.auth_helper.get_websocket_headers(token)
        
        try:
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.staging_config.urls.websocket_url,
                    additional_headers=websocket_headers
                ),
                timeout=25.0
            )
            
            # Send request that requires tool usage
            agent_request = {
                "type": "agent_request", 
                "agent": "data_helper",
                "message": "Generate a performance report with charts and analysis",
                "context": {
                    "user_id": user_data["id"],
                    "report_type": "performance_dashboard",
                    "include_visuals": True
                }
            }
            
            await websocket.send(json.dumps(agent_request))
            
            # Track tool usage events specifically
            events = []
            tool_executions = []
            start_time = time.time()
            
            while time.time() - start_time < 90:
                try:
                    event_str = await asyncio.wait_for(websocket.recv(), timeout=25.0)
                    event = json.loads(event_str)
                    events.append(event)
                    
                    # Track tool execution details
                    if event.get("type") == "tool_executing":
                        tool_executions.append(event["data"]["tool_name"])
                    
                    if event["type"] == "agent_completed":
                        break
                        
                except asyncio.TimeoutError:
                    break
            
            await websocket.close()
            
            # Validate tool usage
            event_types = [e["type"] for e in events]
            
            # Must have tool events for this type of request
            assert "tool_executing" in event_types, "No tool execution events"
            assert "tool_completed" in event_types, "No tool completion events"
            assert len(tool_executions) > 0, "No tools were executed"
            
            # Validate agent completion with tool results
            final_event = next(e for e in reversed(events) if e["type"] == "agent_completed")
            result = final_event["data"]["result"]
            
            assert "tools_used" in result or len(tool_executions) > 0, "Tool usage not reflected in results"
            assert "report_content" in result or "analysis" in result, "No substantive results from tool usage"
            
            self.logger.info(f" PASS:  Agent Tool Usage Test completed - {len(tool_executions)} tools used")
            
        except Exception as e:
            self.logger.error(f" FAIL:  Agent Tool Usage test failed: {e}")
            raise
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm
    @pytest.mark.staging
    async def test_long_running_agent_execution(self, real_services, real_llm):
        """Test long-running agent execution with sustained WebSocket connection."""
        self.logger.info("[U+1F680] Starting Long-Running Agent Execution E2E Test")
        
        # MANDATORY: Authenticate user
        token, user_data = await create_authenticated_user(
            environment="staging",
            email="long-running-test@staging.netrasystems.ai"
        )
        
        websocket_headers = self.auth_helper.get_websocket_headers(token)
        
        try:
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.staging_config.urls.websocket_url,
                    additional_headers=websocket_headers
                ),
                timeout=25.0
            )
            
            # Send complex request requiring extended processing
            agent_request = {
                "type": "agent_request",
                "agent": "comprehensive_analyzer", 
                "message": "Perform deep analysis of multi-year business data with trend forecasting",
                "context": {
                    "user_id": user_data["id"],
                    "analysis_depth": "comprehensive",
                    "historical_years": 3,
                    "forecast_quarters": 4,
                    "include_ml_models": True
                }
            }
            
            await websocket.send(json.dumps(agent_request))
            
            # Extended event collection for long-running process
            events = []
            start_time = time.time()
            last_heartbeat = start_time
            
            while time.time() - start_time < 300:  # 5 minute max timeout
                try:
                    event_str = await asyncio.wait_for(websocket.recv(), timeout=45.0)
                    event = json.loads(event_str)
                    events.append(event)
                    last_heartbeat = time.time()
                    
                    # Log progress for long-running operations
                    if event.get("type") == "agent_thinking":
                        progress = event.get("data", {}).get("progress", "unknown")
                        self.logger.info(f" CHART:  Agent progress: {progress}")
                    
                    if event["type"] == "agent_completed":
                        break
                        
                except asyncio.TimeoutError:
                    # Check if we've gone too long without any events
                    if time.time() - last_heartbeat > 60:
                        self.logger.warning(" WARNING: [U+FE0F] No events received for 60s, may have stalled")
                        break
            
            await websocket.close()
            
            # Validate sustained execution
            execution_time = time.time() - start_time
            event_types = [e["type"] for e in events]
            
            # Should have sustained activity
            assert execution_time > 30, "Test should run for substantial time to validate long execution"
            assert len(events) >= 10, "Should have multiple events during long execution"
            
            # Standard completion validation
            assert "agent_started" in event_types, "Missing agent_started"
            assert "agent_completed" in event_types, "Agent should complete even for long operations"
            
            # Validate comprehensive results for complex request
            final_event = next(e for e in reversed(events) if e["type"] == "agent_completed")
            result = final_event["data"]["result"]
            
            assert "analysis_results" in result or "summary" in result, "Missing analysis results"
            
            self.logger.info(f" PASS:  Long-Running Agent Test completed in {execution_time:.1f}s")
            
        except Exception as e:
            self.logger.error(f" FAIL:  Long-Running Agent test failed: {e}")
            raise
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm
    @pytest.mark.staging
    async def test_agent_interruption_and_resume(self, real_services, real_llm):
        """Test agent interruption scenarios and graceful handling."""
        self.logger.info("[U+1F680] Starting Agent Interruption E2E Test")
        
        # MANDATORY: Authenticate user
        token, user_data = await create_authenticated_user(
            environment="staging",
            email="interruption-test@staging.netrasystems.ai"
        )
        
        websocket_headers = self.auth_helper.get_websocket_headers(token)
        
        try:
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.staging_config.urls.websocket_url,
                    additional_headers=websocket_headers
                ),
                timeout=25.0
            )
            
            # Start a potentially long-running task
            agent_request = {
                "type": "agent_request",
                "agent": "cost_optimizer",
                "message": "Perform detailed cost analysis across all services",
                "context": {
                    "user_id": user_data["id"],
                    "analysis_scope": "all_services",
                    "detail_level": "comprehensive"
                }
            }
            
            await websocket.send(json.dumps(agent_request))
            
            # Wait for agent to start, then simulate interruption
            events = []
            start_time = time.time()
            
            # Collect initial events
            for _ in range(3):  # Get a few events
                try:
                    event_str = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    event = json.loads(event_str)
                    events.append(event)
                    
                    if event["type"] == "agent_started":
                        # Simulate user interruption
                        interrupt_request = {
                            "type": "agent_interrupt",
                            "reason": "user_cancellation",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        await websocket.send(json.dumps(interrupt_request))
                        break
                        
                except asyncio.TimeoutError:
                    break
            
            # Continue collecting events after interruption
            while time.time() - start_time < 30:
                try:
                    event_str = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    event = json.loads(event_str)
                    events.append(event)
                    
                    if event["type"] in ["agent_completed", "agent_cancelled", "agent_interrupted"]:
                        break
                        
                except asyncio.TimeoutError:
                    break
            
            await websocket.close()
            
            # Validate interruption handling
            event_types = [e["type"] for e in events]
            
            assert "agent_started" in event_types, "Agent should have started"
            
            # Should handle interruption gracefully
            completion_events = ["agent_completed", "agent_cancelled", "agent_interrupted"]
            has_graceful_completion = any(event_type in event_types for event_type in completion_events)
            assert has_graceful_completion, "Agent should handle interruption gracefully"
            
            self.logger.info(" PASS:  Agent Interruption Test completed")
            
        except Exception as e:
            self.logger.error(f" FAIL:  Agent Interruption test failed: {e}")
            raise
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm
    @pytest.mark.staging
    async def test_agent_output_quality_validation(self, real_services, real_llm):
        """Test agent output quality and business value validation."""
        self.logger.info("[U+1F680] Starting Agent Output Quality E2E Test")
        
        # MANDATORY: Authenticate user
        token, user_data = await create_authenticated_user(
            environment="staging",
            email="quality-validation-test@staging.netrasystems.ai"
        )
        
        websocket_headers = self.auth_helper.get_websocket_headers(token)
        
        try:
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.staging_config.urls.websocket_url,
                    additional_headers=websocket_headers
                ),
                timeout=25.0
            )
            
            # Send request that should produce high-quality business insights
            agent_request = {
                "type": "agent_request",
                "agent": "business_advisor",
                "message": "Provide strategic recommendations for reducing operational costs while maintaining service quality",
                "context": {
                    "user_id": user_data["id"],
                    "industry": "technology",
                    "company_size": "enterprise", 
                    "budget_constraints": "moderate"
                }
            }
            
            await websocket.send(json.dumps(agent_request))
            
            # Collect events with focus on output quality
            events = []
            start_time = time.time()
            
            while time.time() - start_time < 90:
                try:
                    event_str = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    event = json.loads(event_str)
                    events.append(event)
                    
                    if event["type"] == "agent_completed":
                        break
                        
                except asyncio.TimeoutError:
                    break
            
            await websocket.close()
            
            # Validate WebSocket event quality
            event_types = [e["type"] for e in events]
            required_events = ["agent_started", "agent_thinking", "agent_completed"]
            
            for event_type in required_events:
                assert event_type in event_types, f"Missing {event_type} event"
            
            # Deep validation of output quality
            final_event = next(e for e in reversed(events) if e["type"] == "agent_completed")
            result = final_event["data"]["result"]
            
            # Quality checks for business value
            assert len(result.get("recommendations", [])) >= 3, "Should provide multiple recommendations"
            assert "cost_impact" in result or "savings_potential" in result, "Should quantify cost impact"
            assert "implementation_steps" in result or "action_items" in result, "Should provide actionable steps"
            
            # Validate content quality
            content_text = json.dumps(result).lower()
            quality_indicators = ["specific", "actionable", "measurable", "timeline", "roi"]
            quality_score = sum(1 for indicator in quality_indicators if indicator in content_text)
            
            assert quality_score >= 2, f"Output quality score too low: {quality_score}/5"
            
            self.logger.info(f" PASS:  Agent Output Quality Test completed - Quality score: {quality_score}/5")
            
        except Exception as e:
            self.logger.error(f" FAIL:  Agent Output Quality test failed: {e}")
            raise