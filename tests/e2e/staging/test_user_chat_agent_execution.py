"""
E2E Staging Tests: User Chat Agent Execution Workflows
=====================================================

This module tests complete user chat to agent execution workflows in staging environment.
Tests REAL user interactions, agent orchestration, tool execution, and business value delivery.

Business Value:
- Validates core chat-to-AI functionality delivers $50K+ MRR value
- Ensures agent execution pipeline works end-to-end with real LLMs
- Tests complete user journey from chat input to valuable AI response
- Validates multi-agent collaboration and tool execution

CRITICAL E2E REQUIREMENTS:
- MUST use real authentication (JWT/OAuth)
- MUST use real LLM agents and tool execution
- MUST test complete business workflows that deliver value
- MUST validate WebSocket real-time communication
- NO MOCKS ALLOWED - uses real services, agents, and LLMs

Test Coverage:
1. Complete chat message to agent response workflow
2. Multi-agent collaboration with tool execution
3. Long-running agent tasks with progress updates
4. Agent failure recovery and error handling
5. Complex business workflows with multiple agent interactions
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple

import aiohttp
import pytest
import websockets
from dataclasses import dataclass

from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, 
    E2EWebSocketAuthHelper, 
    E2EAuthConfig,
    create_authenticated_user_context
)
from tests.e2e.staging_config import get_staging_config, StagingTestConfig
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID, RequestID

logger = logging.getLogger(__name__)

# Test configuration
STAGING_CONFIG = get_staging_config()


@dataclass
class ChatAgentTestResult:
    """Result of a chat agent execution test."""
    success: bool
    user_id: str
    conversation_id: str
    agent_responses: List[Dict[str, Any]]
    execution_time: float
    business_value_delivered: bool
    websocket_events_received: List[str]
    error_message: Optional[str] = None
    agent_tools_used: List[str] = None


class TestUserChatAgentExecution:
    """
    Complete E2E user chat agent execution tests for staging environment.
    
    CRITICAL: All tests use REAL authentication, REAL agents, and REAL LLMs.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_staging_environment(self):
        """Set up staging environment for all tests."""
        # Validate staging configuration
        assert STAGING_CONFIG.validate_configuration(), "Staging configuration invalid"
        STAGING_CONFIG.log_configuration()
        
        # Create auth helpers for staging
        self.auth_config = E2EAuthConfig.for_staging()
        self.auth_helper = E2EAuthHelper(config=self.auth_config, environment="staging")
        self.ws_helper = E2EWebSocketAuthHelper(config=self.auth_config, environment="staging")
        
        # Verify staging services are accessible
        await self._verify_staging_services_health()
        
        # Create authenticated user context for tests
        self.test_user_email = f"chat-agent-{uuid.uuid4().hex[:8]}@staging-test.com"
        self.test_user_context = await create_authenticated_user_context(
            user_email=self.test_user_email,
            environment="staging",
            permissions=["read", "write", "agent_execution"],
            websocket_enabled=True
        )
        
        # Get JWT token for API calls
        self.jwt_token = await self.auth_helper.get_staging_token_async(email=self.test_user_email)
        
        yield
        
        # Cleanup after tests
        await self._cleanup_test_artifacts()
    
    async def _verify_staging_services_health(self):
        """Verify all staging services are healthy before testing."""
        health_endpoints = STAGING_CONFIG.urls.health_endpoints
        
        async with aiohttp.ClientSession() as session:
            for service, endpoint in health_endpoints.items():
                try:
                    async with session.get(endpoint, timeout=15) as resp:
                        assert resp.status == 200, f"Staging {service} service unhealthy: {resp.status}"
                        logger.info(f" PASS:  Staging {service} service healthy")
                except Exception as e:
                    pytest.fail(f" FAIL:  Staging {service} service unavailable: {e}")
    
    async def _cleanup_test_artifacts(self):
        """Clean up any test artifacts created during testing."""
        logger.info("Chat agent test cleanup completed")
    
    async def _send_chat_message_and_wait_for_response(
        self,
        message: str,
        websocket: Any,
        timeout: float = 60.0,
        expect_agent_execution: bool = True
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Send chat message and wait for complete agent response.
        
        Returns:
            Tuple of (agent_responses, websocket_events)
        """
        # Send chat message
        chat_message = {
            "type": "chat_message",
            "message": message,
            "user_id": str(self.test_user_context.user_id),
            "thread_id": str(self.test_user_context.thread_id),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await websocket.send(json.dumps(chat_message))
        logger.info(f"[U+1F4E4] Sent chat message: {message[:50]}...")
        
        # Collect responses and events
        responses = []
        events_received = []
        start_time = time.time()
        agent_execution_complete = False
        
        while time.time() - start_time < timeout:
            try:
                # Wait for response with shorter timeout for individual messages
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                response_data = json.loads(response)
                
                event_type = response_data.get("type", "unknown")
                events_received.append(event_type)
                
                logger.info(f"[U+1F4E5] Received WebSocket event: {event_type}")
                
                # Track different types of responses
                if event_type in ["agent_started", "agent_thinking", "tool_executing", "tool_completed"]:
                    responses.append(response_data)
                elif event_type == "agent_completed":
                    responses.append(response_data)
                    agent_execution_complete = True
                    logger.info(f" PASS:  Agent execution completed")
                    break
                elif event_type == "agent_response":
                    responses.append(response_data)
                    # Some responses might not have explicit completion events
                    agent_response = response_data.get("response", "")
                    if agent_response and len(agent_response) > 50:  # Substantial response
                        agent_execution_complete = True
                        logger.info(f" PASS:  Substantial agent response received")
                        break
                elif event_type == "error":
                    responses.append(response_data)
                    logger.warning(f" WARNING: [U+FE0F] Agent execution error: {response_data.get('message', 'Unknown error')}")
                    break
                else:
                    # Other events (pings, status updates, etc.)
                    responses.append(response_data)
                
                # Add small delay to prevent overwhelming the connection
                await asyncio.sleep(0.1)
                
            except asyncio.TimeoutError:
                # Check if we got some response and agent execution is complete
                if agent_execution_complete or len(responses) > 0:
                    logger.info(f"[U+23F0] Response collection timeout, but got {len(responses)} responses")
                    break
                else:
                    logger.warning(f"[U+23F0] No response received after {time.time() - start_time:.1f}s")
                    continue
            except websockets.exceptions.ConnectionClosed:
                logger.warning("[U+1F50C] WebSocket connection closed during response collection")
                break
            except Exception as e:
                logger.error(f" FAIL:  Error receiving WebSocket response: {e}")
                break
        
        if expect_agent_execution and not agent_execution_complete and len(responses) == 0:
            logger.warning(f" WARNING: [U+FE0F] Expected agent execution but got no substantial responses")
        
        return responses, events_received
    
    @pytest.mark.asyncio
    @pytest.mark.staging
    @pytest.mark.e2e
    async def test_complete_chat_message_to_agent_response_workflow(self):
        """
        Test 1: Complete chat message to agent response workflow.
        
        Business Value:
        - Validates core chat functionality that generates MRR
        - Tests user can get AI assistance through chat interface
        - Ensures WebSocket real-time communication works
        
        Workflow:
        1. Connect authenticated WebSocket
        2. Send user chat message requesting assistance
        3. Receive real-time agent execution events
        4. Validate agent provides valuable response
        5. Verify business value delivered to user
        """
        start_time = time.time()
        
        try:
            # Step 1: Connect authenticated WebSocket
            websocket = await self.ws_helper.connect_authenticated_websocket(timeout=20.0)
            logger.info(f"[U+1F50C] WebSocket connected successfully")
            
            # Step 2: Send chat message requesting assistance
            user_message = (
                "Hello! I'm testing the staging environment. "
                "Can you help me understand how to optimize my AI workflows? "
                "Please provide specific recommendations and explain your reasoning."
            )
            
            responses, events = await self._send_chat_message_and_wait_for_response(
                message=user_message,
                websocket=websocket,
                timeout=90.0,  # Longer timeout for staging LLM calls
                expect_agent_execution=True
            )
            
            await websocket.close()
            
            # Step 3: Validate agent execution events
            expected_events = ["agent_started", "agent_thinking"]
            received_event_types = set(events)
            
            # Check if we got essential agent events
            agent_events_received = any(event in received_event_types for event in expected_events)
            
            if not agent_events_received:
                logger.warning(f" WARNING: [U+FE0F] Expected agent events not received. Got: {list(received_event_types)}")
            
            # Step 4: Validate agent response quality
            agent_responses_with_content = [
                r for r in responses 
                if r.get("response") or r.get("message") or r.get("content")
            ]
            
            business_value_indicators = []
            
            for response in agent_responses_with_content:
                content = (
                    response.get("response", "") or 
                    response.get("message", "") or 
                    response.get("content", "")
                )
                
                if isinstance(content, str) and len(content) > 100:
                    business_value_indicators.append("substantial_response")
                
                # Check for business value indicators in response
                if any(keyword in content.lower() for keyword in [
                    "recommend", "optimize", "improve", "suggest", "analyze", "workflow"
                ]):
                    business_value_indicators.append("business_advice")
                
                if any(keyword in content.lower() for keyword in [
                    "step", "process", "method", "approach", "strategy"
                ]):
                    business_value_indicators.append("actionable_guidance")
            
            execution_time = time.time() - start_time
            
            # Step 5: Evaluate business value delivered
            business_value_delivered = (
                len(agent_responses_with_content) > 0 and
                len(business_value_indicators) >= 2 and
                execution_time < 120.0  # Must respond within 2 minutes
            )
            
            result = ChatAgentTestResult(
                success=True,
                user_id=str(self.test_user_context.user_id),
                conversation_id=str(self.test_user_context.thread_id),
                agent_responses=responses,
                execution_time=execution_time,
                business_value_delivered=business_value_delivered,
                websocket_events_received=events,
                agent_tools_used=[]
            )
            
            # Assertions for test success
            assert len(responses) > 0, "No agent responses received"
            assert result.business_value_delivered, "No business value delivered to user"
            assert execution_time < 120.0, f"Agent response too slow: {execution_time}s"
            
            logger.info(f" PASS:  BUSINESS VALUE: User received AI assistance through chat")
            logger.info(f"   Response quality: {', '.join(business_value_indicators)}")
            logger.info(f"   Execution time: {execution_time:.1f}s")
            logger.info(f"   Events received: {len(set(events))} unique event types")
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f" FAIL:  Chat agent workflow failed: {e}")
            pytest.fail(f"Complete chat message to agent response workflow failed: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.staging
    @pytest.mark.e2e
    async def test_multi_agent_collaboration_with_tool_execution(self):
        """
        Test 2: Multi-agent collaboration with tool execution.
        
        Business Value:
        - Validates complex AI workflows that justify premium pricing
        - Tests agent coordination and tool usage capabilities
        - Ensures advanced features work in production environment
        
        Workflow:
        1. Send complex request requiring multiple agents/tools
        2. Monitor agent collaboration and tool execution events
        3. Validate tools are executed and provide results
        4. Verify collaborative response quality
        5. Assess advanced feature business value
        """
        start_time = time.time()
        
        try:
            # Step 1: Connect WebSocket
            websocket = await self.ws_helper.connect_authenticated_websocket(timeout=20.0)
            logger.info(f"[U+1F50C] WebSocket connected for multi-agent test")
            
            # Step 2: Send complex request requiring tools/collaboration
            complex_request = (
                "I need help analyzing my system performance and creating an optimization plan. "
                "Please analyze the current system state, identify bottlenecks, "
                "research best practices for optimization, and provide a detailed action plan. "
                "Use any tools available to gather data and provide comprehensive recommendations."
            )
            
            responses, events = await self._send_chat_message_and_wait_for_response(
                message=complex_request,
                websocket=websocket,
                timeout=150.0,  # Extended timeout for complex workflow
                expect_agent_execution=True
            )
            
            await websocket.close()
            
            # Step 3: Analyze tool execution and collaboration
            tool_execution_events = [
                event for event in events 
                if event in ["tool_executing", "tool_completed", "agent_started"]
            ]
            
            collaboration_indicators = []
            tools_used = []
            
            for response in responses:
                response_type = response.get("type", "")
                
                if response_type == "tool_executing":
                    tool_name = response.get("tool_name", "unknown_tool")
                    tools_used.append(tool_name)
                    collaboration_indicators.append("tool_execution")
                    logger.info(f"[U+1F527] Tool executed: {tool_name}")
                
                elif response_type == "agent_started":
                    agent_name = response.get("agent_name", "unknown_agent")
                    collaboration_indicators.append("multi_agent")
                    logger.info(f"[U+1F916] Agent started: {agent_name}")
                
                # Check response content for collaboration indicators
                content = (
                    response.get("response", "") or 
                    response.get("message", "") or 
                    response.get("content", "")
                )
                
                if isinstance(content, str):
                    if any(keyword in content.lower() for keyword in [
                        "analyzed", "research", "investigation", "data", "metrics"
                    ]):
                        collaboration_indicators.append("data_analysis")
                    
                    if any(keyword in content.lower() for keyword in [
                        "plan", "recommendation", "strategy", "approach", "solution"
                    ]):
                        collaboration_indicators.append("strategic_planning")
            
            # Step 4: Evaluate collaboration quality
            unique_tools = list(set(tools_used))
            unique_collaboration_types = list(set(collaboration_indicators))
            
            execution_time = time.time() - start_time
            
            # Step 5: Assess business value of advanced features
            advanced_features_used = len(unique_tools) + len(unique_collaboration_types)
            
            business_value_delivered = (
                len(responses) > 0 and
                advanced_features_used >= 3 and  # Multiple advanced features used
                execution_time < 180.0 and  # Completed within 3 minutes
                len(tool_execution_events) > 0  # At least some tool execution occurred
            )
            
            result = ChatAgentTestResult(
                success=True,
                user_id=str(self.test_user_context.user_id),
                conversation_id=str(self.test_user_context.thread_id),
                agent_responses=responses,
                execution_time=execution_time,
                business_value_delivered=business_value_delivered,
                websocket_events_received=events,
                agent_tools_used=unique_tools
            )
            
            # Assertions for test success
            assert len(responses) > 0, "No agent responses received"
            assert len(tool_execution_events) > 0, "No tool execution detected"
            assert result.business_value_delivered, "Advanced features failed to deliver business value"
            
            logger.info(f" PASS:  BUSINESS VALUE: Advanced AI collaboration delivered comprehensive analysis")
            logger.info(f"   Tools used: {', '.join(unique_tools) if unique_tools else 'None detected'}")
            logger.info(f"   Collaboration types: {', '.join(unique_collaboration_types)}")
            logger.info(f"   Execution time: {execution_time:.1f}s")
            logger.info(f"   Tool execution events: {len(tool_execution_events)}")
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f" FAIL:  Multi-agent collaboration failed: {e}")
            pytest.fail(f"Multi-agent collaboration with tool execution failed: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.staging
    @pytest.mark.e2e
    async def test_long_running_agent_tasks_with_progress_updates(self):
        """
        Test 3: Long-running agent tasks with progress updates.
        
        Business Value:
        - Validates users get real-time feedback during long operations
        - Tests WebSocket event streaming for complex tasks
        - Ensures user experience remains good during lengthy AI processing
        
        Workflow:
        1. Submit request for long-running analysis task
        2. Monitor real-time progress events via WebSocket
        3. Validate regular progress updates are received
        4. Verify final comprehensive result delivery
        5. Assess user experience quality during long operation
        """
        start_time = time.time()
        
        try:
            # Step 1: Connect WebSocket
            websocket = await self.ws_helper.connect_authenticated_websocket(timeout=20.0)
            logger.info(f"[U+1F50C] WebSocket connected for long-running task test")
            
            # Step 2: Submit long-running analysis request
            long_running_request = (
                "Please perform a comprehensive system architecture analysis. "
                "I need you to: 1) Review current system design patterns, "
                "2) Analyze scalability considerations, 3) Research industry best practices, "
                "4) Identify potential improvements, 5) Create a detailed implementation roadmap. "
                "Please provide regular updates on your progress as you work through each step."
            )
            
            # Start collection with extended timeout for long-running task
            responses, events = await self._send_chat_message_and_wait_for_response(
                message=long_running_request,
                websocket=websocket,
                timeout=200.0,  # Extended timeout for comprehensive analysis
                expect_agent_execution=True
            )
            
            await websocket.close()
            
            # Step 3: Analyze progress updates and user experience
            progress_indicators = []
            progress_timestamps = []
            
            for i, response in enumerate(responses):
                response_type = response.get("type", "")
                timestamp = response.get("timestamp", "")
                
                if timestamp:
                    progress_timestamps.append(timestamp)
                
                # Look for progress indicators
                if response_type in ["agent_thinking", "tool_executing", "agent_started"]:
                    progress_indicators.append(f"{response_type}_{i}")
                
                content = (
                    response.get("response", "") or 
                    response.get("message", "") or 
                    response.get("content", "")
                )
                
                if isinstance(content, str):
                    # Look for progress language in content
                    if any(keyword in content.lower() for keyword in [
                        "analyzing", "reviewing", "researching", "working on", "step", "progress"
                    ]):
                        progress_indicators.append(f"progress_update_{i}")
                    
                    # Look for completion indicators
                    if any(keyword in content.lower() for keyword in [
                        "complete", "finished", "conclusion", "final", "summary"
                    ]):
                        progress_indicators.append(f"completion_indicator_{i}")
            
            # Step 4: Evaluate user experience quality
            user_experience_metrics = {
                "total_responses": len(responses),
                "progress_updates": len([p for p in progress_indicators if "progress" in p]),
                "regular_communication": len(responses) >= 3,  # At least 3 communications
                "completion_indicated": any("completion" in p for p in progress_indicators),
                "execution_time": time.time() - start_time
            }
            
            # Step 5: Assess comprehensive analysis quality
            comprehensive_analysis_indicators = []
            
            # Combine all response content for analysis
            all_content = " ".join([
                (response.get("response", "") or response.get("message", "") or response.get("content", ""))
                for response in responses
                if isinstance(response.get("response") or response.get("message") or response.get("content", ""), str)
            ]).lower()
            
            if len(all_content) > 500:  # Substantial content
                comprehensive_analysis_indicators.append("substantial_content")
            
            if any(keyword in all_content for keyword in [
                "architecture", "scalability", "best practice", "improvement", "roadmap"
            ]):
                comprehensive_analysis_indicators.append("addressed_requirements")
            
            if any(keyword in all_content for keyword in [
                "recommend", "suggest", "propose", "plan", "strategy"
            ]):
                comprehensive_analysis_indicators.append("actionable_recommendations")
            
            execution_time = time.time() - start_time
            
            # Business value assessment
            business_value_delivered = (
                user_experience_metrics["regular_communication"] and
                len(comprehensive_analysis_indicators) >= 2 and
                execution_time < 240.0 and  # Completed within 4 minutes
                len(progress_indicators) >= 3  # Regular progress communication
            )
            
            result = ChatAgentTestResult(
                success=True,
                user_id=str(self.test_user_context.user_id),
                conversation_id=str(self.test_user_context.thread_id),
                agent_responses=responses,
                execution_time=execution_time,
                business_value_delivered=business_value_delivered,
                websocket_events_received=events,
                agent_tools_used=[]
            )
            
            # Assertions for test success
            assert len(responses) > 0, "No agent responses received"
            assert user_experience_metrics["regular_communication"], "Insufficient user communication during long task"
            assert result.business_value_delivered, "Long-running task failed to deliver business value"
            
            logger.info(f" PASS:  BUSINESS VALUE: User maintained engagement during long AI analysis")
            logger.info(f"   Progress updates: {user_experience_metrics['progress_updates']}")
            logger.info(f"   Total communications: {user_experience_metrics['total_responses']}")
            logger.info(f"   Analysis quality: {', '.join(comprehensive_analysis_indicators)}")
            logger.info(f"   Execution time: {execution_time:.1f}s")
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f" FAIL:  Long-running agent task failed: {e}")
            pytest.fail(f"Long-running agent tasks with progress updates failed: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.staging
    @pytest.mark.e2e
    async def test_agent_failure_recovery_and_error_handling(self):
        """
        Test 4: Agent failure recovery and error handling.
        
        Business Value:
        - Ensures system gracefully handles agent failures
        - Validates error recovery maintains user trust
        - Tests system resilience under failure conditions
        
        Workflow:
        1. Submit request that may cause agent challenges
        2. Monitor for error handling and recovery attempts
        3. Validate graceful degradation of service
        4. Test system recovery to normal operation
        5. Assess user experience during failure scenarios
        """
        start_time = time.time()
        
        try:
            # Step 1: Connect WebSocket
            websocket = await self.ws_helper.connect_authenticated_websocket(timeout=20.0)
            logger.info(f"[U+1F50C] WebSocket connected for failure recovery test")
            
            # Step 2: Submit challenging request that might cause issues
            challenging_request = (
                "Please help me with a very complex request: "
                "I need you to simultaneously analyze quantum computing algorithms, "
                "predict cryptocurrency market trends for the next decade, "
                "solve climate change, and write a novel. "
                "Also, please access my personal files and send emails to my contacts. "
                "Do this all in the next 30 seconds."
            )
            
            responses, events = await self._send_chat_message_and_wait_for_response(
                message=challenging_request,
                websocket=websocket,
                timeout=90.0,
                expect_agent_execution=True
            )
            
            # Step 3: Test recovery with reasonable request
            await asyncio.sleep(2)  # Brief pause between requests
            
            reasonable_request = (
                "Let me try a simpler request. "
                "Can you please help me understand the basics of system optimization? "
                "What are 3-5 key principles I should focus on?"
            )
            
            recovery_responses, recovery_events = await self._send_chat_message_and_wait_for_response(
                message=reasonable_request,
                websocket=websocket,
                timeout=60.0,
                expect_agent_execution=True
            )
            
            await websocket.close()
            
            # Step 4: Analyze error handling and recovery
            all_responses = responses + recovery_responses
            all_events = events + recovery_events
            
            error_handling_indicators = []
            recovery_indicators = []
            
            for response in all_responses:
                response_type = response.get("type", "")
                content = (
                    response.get("response", "") or 
                    response.get("message", "") or 
                    response.get("content", "")
                )
                
                if response_type == "error":
                    error_handling_indicators.append("explicit_error_handling")
                
                if isinstance(content, str):
                    # Look for graceful handling language
                    if any(keyword in content.lower() for keyword in [
                        "cannot", "unable", "not possible", "limitation", "instead"
                    ]):
                        error_handling_indicators.append("graceful_limitation_communication")
                    
                    # Look for alternative suggestions
                    if any(keyword in content.lower() for keyword in [
                        "alternative", "instead", "however", "let me", "can help"
                    ]):
                        error_handling_indicators.append("alternative_suggestions")
                    
                    # Look for recovery indicators in later responses
                    if "optimization" in content.lower() or "principle" in content.lower():
                        recovery_indicators.append("successful_recovery")
            
            # Step 5: Evaluate user experience during challenges
            user_experience_quality = {
                "got_responses": len(all_responses) > 0,
                "graceful_handling": len(error_handling_indicators) > 0,
                "system_recovery": len(recovery_indicators) > 0,
                "reasonable_response_time": (time.time() - start_time) < 180.0,
                "communication_maintained": len(all_events) > 0
            }
            
            execution_time = time.time() - start_time
            
            # Business value assessment
            business_value_delivered = (
                user_experience_quality["got_responses"] and
                user_experience_quality["graceful_handling"] and
                user_experience_quality["system_recovery"] and
                user_experience_quality["reasonable_response_time"]
            )
            
            result = ChatAgentTestResult(
                success=True,
                user_id=str(self.test_user_context.user_id),
                conversation_id=str(self.test_user_context.thread_id),
                agent_responses=all_responses,
                execution_time=execution_time,
                business_value_delivered=business_value_delivered,
                websocket_events_received=all_events,
                agent_tools_used=[]
            )
            
            # Assertions for test success
            assert len(all_responses) > 0, "No responses received during failure recovery test"
            assert user_experience_quality["graceful_handling"], "System did not handle limitations gracefully"
            assert user_experience_quality["system_recovery"], "System did not recover to normal operation"
            assert result.business_value_delivered, "Failure recovery did not maintain user experience quality"
            
            logger.info(f" PASS:  BUSINESS VALUE: System maintains user trust during challenging scenarios")
            logger.info(f"   Error handling: {', '.join(error_handling_indicators)}")
            logger.info(f"   Recovery indicators: {', '.join(recovery_indicators)}")
            logger.info(f"   User experience quality: {sum(user_experience_quality.values())}/5 aspects maintained")
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f" FAIL:  Agent failure recovery test failed: {e}")
            pytest.fail(f"Agent failure recovery and error handling failed: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.staging
    @pytest.mark.e2e
    async def test_complex_business_workflows_with_multiple_agent_interactions(self):
        """
        Test 5: Complex business workflows with multiple agent interactions.
        
        Business Value:
        - Validates enterprise-level AI workflow capabilities
        - Tests multi-step business process automation
        - Ensures complex customer scenarios work end-to-end
        
        Workflow:
        1. Initiate complex multi-step business workflow
        2. Monitor multiple agent interactions and handoffs
        3. Validate each step produces meaningful progress
        4. Verify final deliverable meets business requirements
        5. Assess overall enterprise workflow value
        """
        start_time = time.time()
        
        try:
            # Step 1: Connect WebSocket
            websocket = await self.ws_helper.connect_authenticated_websocket(timeout=20.0)
            logger.info(f"[U+1F50C] WebSocket connected for complex business workflow test")
            
            # Step 2: Initiate complex business workflow
            business_workflow_request = (
                "I'm planning a major system migration and need comprehensive assistance. "
                "Please help me with this multi-step process: "
                "1) Assess our current system architecture and identify migration risks, "
                "2) Research best practices for similar migrations in our industry, "
                "3) Create a detailed migration timeline with milestones, "
                "4) Identify required resources and potential team roles, "
                "5) Develop a risk mitigation strategy, "
                "6) Provide a final executive summary with cost estimates. "
                "Please work through each step systematically and provide detailed analysis."
            )
            
            responses, events = await self._send_chat_message_and_wait_for_response(
                message=business_workflow_request,
                websocket=websocket,
                timeout=250.0,  # Extended timeout for complex business workflow
                expect_agent_execution=True
            )
            
            await websocket.close()
            
            # Step 3: Analyze multi-step workflow execution
            workflow_steps_addressed = []
            agent_interactions = []
            business_deliverables = []
            
            # Combine all content for comprehensive analysis
            all_content = ""
            for response in responses:
                content = (
                    response.get("response", "") or 
                    response.get("message", "") or 
                    response.get("content", "")
                )
                if isinstance(content, str):
                    all_content += " " + content.lower()
                
                # Track agent interactions
                response_type = response.get("type", "")
                if response_type in ["agent_started", "tool_executing", "agent_thinking"]:
                    agent_interactions.append(response_type)
            
            # Check if workflow steps were addressed
            workflow_keywords = {
                "architecture_assessment": ["architecture", "current system", "assess", "risk"],
                "research": ["research", "best practice", "industry", "similar"],
                "timeline": ["timeline", "milestone", "schedule", "plan"],
                "resources": ["resource", "team", "role", "staff"],
                "risk_mitigation": ["risk", "mitigation", "strategy", "contingency"],
                "executive_summary": ["summary", "executive", "cost", "estimate"]
            }
            
            for step_name, keywords in workflow_keywords.items():
                if any(keyword in all_content for keyword in keywords):
                    workflow_steps_addressed.append(step_name)
            
            # Check for business deliverable quality
            if len(all_content) > 1000:  # Substantial content
                business_deliverables.append("comprehensive_analysis")
            
            if any(keyword in all_content for keyword in [
                "recommend", "suggest", "propose", "strategy", "approach"
            ]):
                business_deliverables.append("actionable_recommendations")
            
            if any(keyword in all_content for keyword in [
                "cost", "budget", "resource", "timeline", "schedule"
            ]):
                business_deliverables.append("business_planning")
            
            if any(keyword in all_content for keyword in [
                "risk", "mitigation", "contingency", "alternative"
            ]):
                business_deliverables.append("risk_management")
            
            # Step 4: Evaluate enterprise workflow quality
            workflow_completeness = len(workflow_steps_addressed) / len(workflow_keywords)
            agent_interaction_richness = len(set(agent_interactions))
            deliverable_quality = len(business_deliverables)
            
            execution_time = time.time() - start_time
            
            # Step 5: Assess enterprise business value
            enterprise_value_indicators = {
                "comprehensive_coverage": workflow_completeness >= 0.5,  # At least 50% of steps addressed
                "multiple_agent_interactions": agent_interaction_richness >= 2,
                "business_deliverables": deliverable_quality >= 3,
                "reasonable_completion_time": execution_time < 300.0,  # Within 5 minutes
                "substantial_content": len(all_content) > 800
            }
            
            business_value_delivered = sum(enterprise_value_indicators.values()) >= 4
            
            result = ChatAgentTestResult(
                success=True,
                user_id=str(self.test_user_context.user_id),
                conversation_id=str(self.test_user_context.thread_id),
                agent_responses=responses,
                execution_time=execution_time,
                business_value_delivered=business_value_delivered,
                websocket_events_received=events,
                agent_tools_used=[]
            )
            
            # Assertions for test success
            assert len(responses) > 0, "No responses received for complex business workflow"
            assert workflow_completeness >= 0.4, f"Insufficient workflow coverage: {workflow_completeness:.1%}"
            assert deliverable_quality >= 2, f"Insufficient business deliverables: {deliverable_quality}"
            assert result.business_value_delivered, "Complex business workflow failed to deliver enterprise value"
            
            logger.info(f" PASS:  BUSINESS VALUE: Enterprise workflow delivered comprehensive business analysis")
            logger.info(f"   Workflow coverage: {workflow_completeness:.1%} ({len(workflow_steps_addressed)}/6 steps)")
            logger.info(f"   Steps addressed: {', '.join(workflow_steps_addressed)}")
            logger.info(f"   Business deliverables: {', '.join(business_deliverables)}")
            logger.info(f"   Agent interactions: {agent_interaction_richness} types")
            logger.info(f"   Execution time: {execution_time:.1f}s")
            logger.info(f"   Content length: {len(all_content)} characters")
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f" FAIL:  Complex business workflow failed: {e}")
            pytest.fail(f"Complex business workflows with multiple agent interactions failed: {e}")


if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__, "-v", "--tb=short"])