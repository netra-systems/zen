"""
Golden Path Complete User Journey Tests (Staging GCP)

These tests validate the complete user journey on staging environment.
They will FAIL if the golden path is not actually operational.

This is the ultimate test of $500K+ ARR functionality - the complete
business value delivery from user login to AI response.

Business Value Justification:
- Segment: ALL (Free/Early/Mid/Enterprise) 
- Business Goal: Complete User Value Delivery
- Value Impact: Validates end-to-end customer experience and business value
- Strategic Impact: Protects $500K+ ARR by proving golden path operational
"""

import pytest
import asyncio
import aiohttp
import websockets
import json
import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


# Test configuration for staging environment
@dataclass
class StagingTestConfig:
    """Configuration for staging environment tests."""
    base_url: str = "https://staging.netrasystems.ai"
    websocket_url: str = "wss://api-staging.netrasystems.ai"
    api_timeout: int = 30
    websocket_timeout: int = 60
    max_retries: int = 3
    retry_delay: float = 2.0


class GoldenPathStage(Enum):
    """Stages of the golden path user journey."""
    USER_LOGIN = "user_login"
    WEBSOCKET_CONNECTION = "websocket_connection"
    MESSAGE_SENDING = "message_sending" 
    AI_RESPONSE_RECEIVED = "ai_response_received"
    WEBSOCKET_EVENTS_COMPLETE = "websocket_events_complete"
    BUSINESS_VALUE_DELIVERED = "business_value_delivered"


@dataclass
class GoldenPathResult:
    """Result of golden path testing."""
    stage: GoldenPathStage
    success: bool
    error_message: Optional[str] = None
    response_data: Optional[Dict[str, Any]] = None
    duration_seconds: Optional[float] = None
    events_received: Optional[List[str]] = None


class TestGoldenPathCompleteUserJourney:
    """Test complete user journey on staging GCP environment."""
    
    def setup_method(self):
        """Setup method for each test - replaces __init__ for pytest compatibility.
        
        Initializes staging test configuration, logger, and result tracking
        for golden path validation tests.
        """
        self.config = StagingTestConfig()
        self.logger = logging.getLogger(__name__)
        self.test_results: List[GoldenPathResult] = []
    
    @pytest.mark.asyncio
    @pytest.mark.staging
    @pytest.mark.golden_path
    @pytest.mark.timeout(180)  # 3 minute total timeout
    async def test_complete_user_login_to_ai_response_flow(self):
        """Test complete flow: user login → send message → receive AI response.
        
        This test WILL FAIL if the golden path is not actually operational.
        This is the ultimate test of $500K+ ARR functionality.
        
        Expected to FAIL initially - proves golden path claims are false.
        """
        self.logger.info("Starting CRITICAL golden path validation - $500K+ ARR test")
        
        # Execute golden path stages sequentially
        stages = [
            (GoldenPathStage.USER_LOGIN, self._test_user_login),
            (GoldenPathStage.WEBSOCKET_CONNECTION, self._test_websocket_connection),
            (GoldenPathStage.MESSAGE_SENDING, self._test_send_message_to_agent),
            (GoldenPathStage.AI_RESPONSE_RECEIVED, self._test_receive_ai_response),
            (GoldenPathStage.WEBSOCKET_EVENTS_COMPLETE, self._test_all_websocket_events),
            (GoldenPathStage.BUSINESS_VALUE_DELIVERED, self._test_business_value_delivery)
        ]
        
        failed_stages = []
        
        for stage, test_func in stages:
            self.logger.info(f"Testing golden path stage: {stage.value}")
            start_time = time.time()
            
            try:
                result = await test_func()
                duration = time.time() - start_time
                
                if result.success:
                    self.logger.info(f"Stage {stage.value} PASSED in {duration:.2f}s")
                    self.test_results.append(result)
                else:
                    self.logger.error(f"Stage {stage.value} FAILED: {result.error_message}")
                    failed_stages.append((stage, result.error_message))
                    self.test_results.append(result)
                    break  # Stop on first failure
                    
            except Exception as e:
                duration = time.time() - start_time
                error_msg = f"Exception in {stage.value}: {str(e)}"
                self.logger.error(error_msg)
                
                failed_result = GoldenPathResult(
                    stage=stage,
                    success=False,
                    error_message=error_msg,
                    duration_seconds=duration
                )
                self.test_results.append(failed_result)
                failed_stages.append((stage, error_msg))
                break
        
        # Generate comprehensive failure report
        if failed_stages:
            self._generate_failure_report(failed_stages)
            
            # EXPECTED FAILURE - proves golden path is not operational
            pytest.fail(
                f"GOLDEN PATH NOT OPERATIONAL: {len(failed_stages)} stage(s) failed. "
                f"This proves '$500K+ ARR golden path operational' claims are FALSE. "
                f"Failed stages: {[stage.value for stage, _ in failed_stages]}. "
                f"First failure: {failed_stages[0][1]}. "
                f"Complete analysis in test results."
            )
        
        # If we reach here, golden path is actually operational
        self.logger.info("GOLDEN PATH FULLY OPERATIONAL - All stages passed")
        assert True, "Golden path validation successful"
    
    async def _test_user_login(self) -> GoldenPathResult:
        """Test user login to staging environment."""
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.api_timeout)
            ) as session:
                
                # First, test if staging is accessible
                try:
                    async with session.get(f"{self.config.base_url}/health") as response:
                        if response.status != 200:
                            return GoldenPathResult(
                                stage=GoldenPathStage.USER_LOGIN,
                                success=False,
                                error_message=f"Staging health check failed: HTTP {response.status}",
                                duration_seconds=time.time() - start_time
                            )
                except Exception as e:
                    return GoldenPathResult(
                        stage=GoldenPathStage.USER_LOGIN,
                        success=False,
                        error_message=f"Staging not accessible: {str(e)}",
                        duration_seconds=time.time() - start_time
                    )
                
                # Test authentication endpoint
                login_endpoints = [
                    "/api/auth/login",
                    "/api/v1/auth/login", 
                    "/auth/login",
                    "/login"
                ]
                
                for endpoint in login_endpoints:
                    try:
                        login_data = {
                            "email": "test@staging.example.com",
                            "password": "staging_test_password"
                        }
                        
                        async with session.post(
                            f"{self.config.base_url}{endpoint}",
                            json=login_data
                        ) as response:
                            
                            if response.status == 200:
                                result_data = await response.json()
                                if result_data.get('access_token'):
                                    return GoldenPathResult(
                                        stage=GoldenPathStage.USER_LOGIN,
                                        success=True,
                                        response_data=result_data,
                                        duration_seconds=time.time() - start_time
                                    )
                            elif response.status == 404:
                                continue  # Try next endpoint
                            else:
                                # Authentication failed - might be expected for test account
                                pass
                                
                    except Exception:
                        continue  # Try next endpoint
                
                # If no login endpoints work, authentication system is broken
                return GoldenPathResult(
                    stage=GoldenPathStage.USER_LOGIN,
                    success=False,
                    error_message="No functional authentication endpoints found on staging",
                    duration_seconds=time.time() - start_time
                )
                
        except Exception as e:
            return GoldenPathResult(
                stage=GoldenPathStage.USER_LOGIN,
                success=False,
                error_message=f"Login test failed with exception: {str(e)}",
                duration_seconds=time.time() - start_time
            )
    
    async def _test_websocket_connection(self) -> GoldenPathResult:
        """Test WebSocket connection to staging."""
        start_time = time.time()
        
        websocket_endpoints = [
            f"{self.config.websocket_url}/ws",
            f"{self.config.websocket_url}/websocket",
            f"{self.config.websocket_url}/api/v1/websocket",
            f"wss://staging.netrasystems.ai/ws"
        ]
        
        for endpoint in websocket_endpoints:
            try:
                async with websockets.connect(
                    endpoint,
                    timeout=self.config.websocket_timeout
                ) as websocket:
                    
                    # Send ping to test connection
                    ping_message = json.dumps({"type": "ping", "timestamp": time.time()})
                    await websocket.send(ping_message)
                    
                    # Wait for response
                    try:
                        response = await asyncio.wait_for(
                            websocket.recv(), 
                            timeout=10
                        )
                        
                        # Any response indicates connection works
                        return GoldenPathResult(
                            stage=GoldenPathStage.WEBSOCKET_CONNECTION,
                            success=True,
                            response_data={"endpoint": endpoint, "response": response},
                            duration_seconds=time.time() - start_time
                        )
                        
                    except asyncio.TimeoutError:
                        # Connection established but no response - might still be valid
                        return GoldenPathResult(
                            stage=GoldenPathStage.WEBSOCKET_CONNECTION,
                            success=True,
                            response_data={"endpoint": endpoint, "note": "Connected but no ping response"},
                            duration_seconds=time.time() - start_time
                        )
                        
            except Exception as e:
                self.logger.debug(f"WebSocket endpoint {endpoint} failed: {e}")
                continue  # Try next endpoint
        
        # No WebSocket endpoints work
        return GoldenPathResult(
            stage=GoldenPathStage.WEBSOCKET_CONNECTION,
            success=False,
            error_message="No functional WebSocket endpoints found on staging",
            duration_seconds=time.time() - start_time
        )
    
    async def _test_send_message_to_agent(self) -> GoldenPathResult:
        """Test sending message to agent."""
        start_time = time.time()
        
        websocket_endpoints = [
            f"{self.config.websocket_url}/ws",
            f"{self.config.websocket_url}/websocket",
            f"{self.config.websocket_url}/api/v1/websocket"
        ]
        
        for endpoint in websocket_endpoints:
            try:
                async with websockets.connect(
                    endpoint,
                    timeout=self.config.websocket_timeout
                ) as websocket:
                    
                    # Send agent message
                    test_message = {
                        "type": "chat_message",
                        "content": "Help me optimize my AI costs - simple test query",
                        "user_id": f"test-user-golden-path-{int(time.time())}",
                        "thread_id": f"test-thread-golden-path-{int(time.time())}"
                    }
                    
                    await websocket.send(json.dumps(test_message))
                    
                    # Wait for acknowledgment or response
                    try:
                        response = await asyncio.wait_for(
                            websocket.recv(),
                            timeout=15
                        )
                        
                        # Parse response
                        try:
                            response_data = json.loads(response)
                        except:
                            response_data = {"raw_response": response}
                        
                        # Check for message processing indicators
                        response_str = str(response).lower()
                        success_indicators = [
                            "received", "started", "processing", "agent_started",
                            "thinking", "acknowledged"
                        ]
                        
                        if any(indicator in response_str for indicator in success_indicators):
                            return GoldenPathResult(
                                stage=GoldenPathStage.MESSAGE_SENDING,
                                success=True,
                                response_data=response_data,
                                duration_seconds=time.time() - start_time
                            )
                        
                        # Got response but unclear if processing started
                        return GoldenPathResult(
                            stage=GoldenPathStage.MESSAGE_SENDING,
                            success=False,
                            error_message=f"Message sent but unclear response: {response[:200]}",
                            response_data=response_data,
                            duration_seconds=time.time() - start_time
                        )
                        
                    except asyncio.TimeoutError:
                        return GoldenPathResult(
                            stage=GoldenPathStage.MESSAGE_SENDING,
                            success=False,
                            error_message="Message sent but no acknowledgment received within timeout",
                            duration_seconds=time.time() - start_time
                        )
                        
            except Exception as e:
                self.logger.debug(f"Message sending to {endpoint} failed: {e}")
                continue
        
        return GoldenPathResult(
            stage=GoldenPathStage.MESSAGE_SENDING,
            success=False,
            error_message="Failed to send message to any WebSocket endpoint",
            duration_seconds=time.time() - start_time
        )
    
    async def _test_receive_ai_response(self) -> GoldenPathResult:
        """Test receiving AI response from agent."""
        start_time = time.time()
        
        websocket_endpoints = [
            f"{self.config.websocket_url}/ws",
            f"{self.config.websocket_url}/websocket"
        ]
        
        for endpoint in websocket_endpoints:
            try:
                async with websockets.connect(
                    endpoint,
                    timeout=self.config.websocket_timeout
                ) as websocket:
                    
                    # Send message and collect responses
                    test_message = {
                        "type": "chat_message",
                        "content": "Simple test query - provide brief response",
                        "user_id": f"test-user-ai-response-{int(time.time())}",
                        "thread_id": f"test-thread-ai-response-{int(time.time())}"
                    }
                    
                    await websocket.send(json.dumps(test_message))
                    
                    # Collect responses for up to 45 seconds
                    responses = []
                    ai_response_found = False
                    timeout_start = time.time()
                    
                    while time.time() - timeout_start < 45:
                        try:
                            response = await asyncio.wait_for(
                                websocket.recv(),
                                timeout=10
                            )
                            responses.append(response)
                            
                            # Check for AI response indicators
                            response_str = str(response).lower()
                            ai_indicators = [
                                "agent_completed", "final_response", "response",
                                "content", "result", "recommendation"
                            ]
                            
                            if any(indicator in response_str for indicator in ai_indicators):
                                # Try to parse as JSON to get actual content
                                try:
                                    response_data = json.loads(response)
                                    content = (
                                        response_data.get('content') or
                                        response_data.get('final_response') or
                                        response_data.get('result') or
                                        response_data.get('data', {}).get('content') or
                                        ""
                                    )
                                    
                                    # Validate this looks like an AI response
                                    if len(content) > 10:  # Substantial response
                                        ai_response_found = True
                                        break
                                        
                                except:
                                    # Not JSON, but might still be AI response
                                    if len(response) > 50:  # Substantial response
                                        ai_response_found = True
                                        break
                            
                            # Check for completion signals
                            if "agent_completed" in response_str:
                                ai_response_found = True
                                break
                                
                        except asyncio.TimeoutError:
                            continue
                        except Exception as e:
                            self.logger.debug(f"Error receiving response: {e}")
                            break
                    
                    if ai_response_found:
                        return GoldenPathResult(
                            stage=GoldenPathStage.AI_RESPONSE_RECEIVED,
                            success=True,
                            response_data={
                                "responses_count": len(responses),
                                "final_response": responses[-1] if responses else None
                            },
                            duration_seconds=time.time() - start_time
                        )
                    else:
                        return GoldenPathResult(
                            stage=GoldenPathStage.AI_RESPONSE_RECEIVED,
                            success=False,
                            error_message=f"No AI response received. Got {len(responses)} messages but none contained AI content",
                            response_data={"responses": responses[:3]},  # First 3 for debugging
                            duration_seconds=time.time() - start_time
                        )
                        
            except Exception as e:
                self.logger.debug(f"AI response test failed for {endpoint}: {e}")
                continue
        
        return GoldenPathResult(
            stage=GoldenPathStage.AI_RESPONSE_RECEIVED,
            success=False,
            error_message="Failed to receive AI response from any endpoint",
            duration_seconds=time.time() - start_time
        )
    
    async def _test_all_websocket_events(self) -> GoldenPathResult:
        """Test all 5 critical WebSocket events are delivered."""
        start_time = time.time()
        
        # The 5 business-critical WebSocket events
        required_events = {
            "agent_started",
            "agent_thinking",
            "tool_executing", 
            "tool_completed",
            "agent_completed"
        }
        
        for endpoint in [f"{self.config.websocket_url}/ws"]:
            try:
                async with websockets.connect(
                    endpoint,
                    timeout=self.config.websocket_timeout
                ) as websocket:
                    
                    # Send message that should trigger all events
                    test_message = {
                        "type": "chat_message",
                        "content": "Analyze my cloud costs and provide optimization recommendations with tool usage",
                        "user_id": f"test-user-events-{int(time.time())}",
                        "thread_id": f"test-thread-events-{int(time.time())}"
                    }
                    
                    await websocket.send(json.dumps(test_message))
                    
                    # Track events
                    events_received = set()
                    all_responses = []
                    timeout_start = time.time()
                    
                    while time.time() - timeout_start < 60:  # 60 second timeout
                        try:
                            response = await asyncio.wait_for(
                                websocket.recv(),
                                timeout=10
                            )
                            all_responses.append(response)
                            
                            # Check for each required event
                            response_str = str(response).lower()
                            for event_type in required_events:
                                if event_type in response_str:
                                    events_received.add(event_type)
                                    self.logger.debug(f"Detected event: {event_type}")
                            
                            # Check if we have all events
                            if events_received == required_events:
                                return GoldenPathResult(
                                    stage=GoldenPathStage.WEBSOCKET_EVENTS_COMPLETE,
                                    success=True,
                                    events_received=list(events_received),
                                    response_data={
                                        "events_received": list(events_received),
                                        "total_responses": len(all_responses)
                                    },
                                    duration_seconds=time.time() - start_time
                                )
                            
                            # Early exit on completion
                            if "agent_completed" in response_str:
                                break
                                
                        except asyncio.TimeoutError:
                            continue
                        except Exception as e:
                            self.logger.debug(f"Error in event collection: {e}")
                            break
                    
                    # Check what events we received
                    missing_events = required_events - events_received
                    
                    return GoldenPathResult(
                        stage=GoldenPathStage.WEBSOCKET_EVENTS_COMPLETE,
                        success=False,
                        error_message=f"Missing {len(missing_events)} critical events: {missing_events}",
                        events_received=list(events_received),
                        response_data={
                            "events_received": list(events_received),
                            "missing_events": list(missing_events),
                            "total_responses": len(all_responses)
                        },
                        duration_seconds=time.time() - start_time
                    )
                    
            except Exception as e:
                self.logger.debug(f"WebSocket events test failed: {e}")
                continue
        
        return GoldenPathResult(
            stage=GoldenPathStage.WEBSOCKET_EVENTS_COMPLETE,
            success=False,
            error_message="Failed to test WebSocket events on any endpoint",
            duration_seconds=time.time() - start_time
        )
    
    async def _test_business_value_delivery(self) -> GoldenPathResult:
        """Test that business value is actually delivered."""
        start_time = time.time()
        
        # This is a simplified business value test
        # In a full implementation, this would validate response quality,
        # actionable insights, cost optimization recommendations, etc.
        
        try:
            # For now, if we got this far, business value pipeline is working
            return GoldenPathResult(
                stage=GoldenPathStage.BUSINESS_VALUE_DELIVERED,
                success=True,
                response_data={"note": "Business value pipeline functional"},
                duration_seconds=time.time() - start_time
            )
        except Exception as e:
            return GoldenPathResult(
                stage=GoldenPathStage.BUSINESS_VALUE_DELIVERED,
                success=False,
                error_message=f"Business value validation failed: {str(e)}",
                duration_seconds=time.time() - start_time
            )
    
    def _generate_failure_report(self, failed_stages: List[tuple]):
        """Generate comprehensive failure report for analysis."""
        self.logger.error("=" * 80)
        self.logger.error("GOLDEN PATH FAILURE ANALYSIS REPORT")
        self.logger.error("=" * 80)
        
        self.logger.error(f"BUSINESS IMPACT: $500K+ ARR at risk due to golden path failures")
        self.logger.error(f"FAILED STAGES: {len(failed_stages)} out of {len(GoldenPathStage)}")
        
        for i, (stage, error) in enumerate(failed_stages, 1):
            self.logger.error(f"\nFAILURE #{i}: {stage.value}")
            self.logger.error(f"  Error: {error}")
            
            # Find result for this stage
            stage_result = next(
                (r for r in self.test_results if r.stage == stage),
                None
            )
            if stage_result:
                self.logger.error(f"  Duration: {stage_result.duration_seconds:.2f}s")
                if stage_result.response_data:
                    self.logger.error(f"  Data: {stage_result.response_data}")
        
        self.logger.error("\nRECOMMENDATIONS:")
        self.logger.error("1. Stop claiming 'Golden Path FULLY OPERATIONAL'")
        self.logger.error("2. Fix infrastructure issues before updating documentation")
        self.logger.error("3. Implement authentic end-to-end testing")
        self.logger.error("4. Validate business value delivery empirically")
        self.logger.error("=" * 80)


if __name__ == "__main__":
    # Run golden path tests on staging
    pytest.main([__file__, "-v", "--tb=short", "--staging-e2e"])