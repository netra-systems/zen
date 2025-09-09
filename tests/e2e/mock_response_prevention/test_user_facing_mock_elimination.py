"""
User-Facing Mock Response Elimination E2E Tests

Business Value Justification (BVJ):
- Segment: All user interfaces (Web, Mobile, API) - Complete UX authenticity
- Business Goal: Zero mock responses visible to users through ANY interface
- Value Impact: Protect user experience quality and platform credibility
- Strategic Impact: User trust and competitive differentiation through interface integrity

CRITICAL: These E2E tests validate the complete user journey from request
to response across all interfaces to ensure users never encounter mock,
fallback, or inauthentic responses regardless of entry point.

Test Status: FAILING (Expected) - Proves user interfaces show mock responses
Fix Required: All user-facing interfaces must show authentic responses only
"""

import asyncio
import pytest
import json
import logging
import time
import uuid
from typing import Dict, List, Any, Optional
import aiohttp
import websockets
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

from test_framework.base_e2e_test import BaseE2ETest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, AuthenticatedUser
from test_framework.websocket_helpers import WebSocketTestClient, assert_websocket_events
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env
from shared.types.core_types import UserID, ThreadID, RequestID

logger = logging.getLogger(__name__)


class TestUserFacingMockElimination(BaseE2ETest):
    """
    FAILING E2E TESTS: Prove users can see mock responses through any interface
    
    These tests validate the complete user experience across all interfaces
    to ensure no mock/fallback responses are visible to users through web UI,
    mobile interfaces, direct API calls, or WebSocket connections.
    """

    @pytest.fixture
    async def test_user(self, real_services_fixture):
        """Create test user for interface testing"""
        auth_helper = E2EAuthHelper()
        user = await auth_helper.create_authenticated_user(
            email=f"ui.test.user.{uuid.uuid4()}@example.com"
        )
        yield user
        await auth_helper.cleanup_user(user)

    @pytest.fixture
    def web_driver(self):
        """Setup Chrome WebDriver for UI testing"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(10)
        yield driver
        driver.quit()

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_web_ui_mock_response_elimination(self, real_services_fixture, test_user, web_driver):
        """
        FAILING TEST: Prove web UI can display mock responses to users
        
        Business Impact: Users seeing "I apologize" or "Service unavailable" in 
        web interface immediately recognize platform as unreliable and consider alternatives.
        
        Expected Failure: Mock responses visible in web UI
        Required Fix: Web UI must show authentic responses or premium error handling
        """
        logger.info("Testing web UI mock response elimination...")
        
        frontend_url = get_env('FRONTEND_URL', 'http://localhost:3000')
        
        try:
            # Navigate to the application
            web_driver.get(frontend_url)
            
            # Login with test user credentials
            login_button = WebDriverWait(web_driver, 10).until(
                EC.element_to_be_clickable((By.ID, "login-button"))
            )
            login_button.click()
            
            # Fill in login credentials
            email_input = web_driver.find_element(By.ID, "email-input")
            email_input.send_keys(test_user.email)
            
            password_input = web_driver.find_element(By.ID, "password-input") 
            password_input.send_keys("test-password-123")  # Standard test password
            
            submit_button = web_driver.find_element(By.ID, "login-submit")
            submit_button.click()
            
            # Wait for login success and navigate to chat
            WebDriverWait(web_driver, 10).until(
                EC.presence_of_element_located((By.ID, "chat-container"))
            )
            
            # Test scenarios that might trigger UI fallbacks
            ui_test_scenarios = [
                {
                    "name": "LLM Service Failure",
                    "message": "Analyze market trends for strategic planning",
                    "force_failure": True,
                    "expected_ui_elements": ["chat-input", "send-button", "message-container"]
                },
                {
                    "name": "Database Connection Lost",
                    "message": "Retrieve my historical data and generate insights",
                    "simulate_db_failure": True,
                    "expected_ui_elements": ["chat-input", "send-button", "message-container"]
                },
                {
                    "name": "System Overload",
                    "message": "Generate comprehensive analysis report immediately",
                    "simulate_overload": True,
                    "expected_ui_elements": ["chat-input", "send-button", "message-container"]
                }
            ]
            
            ui_mock_evidence = []
            
            for scenario in ui_test_scenarios:
                logger.info(f"Testing UI scenario: {scenario['name']}")
                
                # Find chat input and send message
                chat_input = web_driver.find_element(By.ID, "chat-input")
                chat_input.clear()
                chat_input.send_keys(scenario["message"])
                
                # Add test parameters to trigger failures
                if scenario.get("force_failure"):
                    # Use JavaScript to set test parameters
                    web_driver.execute_script(f"""
                        window.testParameters = {{
                            forceLLMFailure: true,
                            testScenario: '{scenario["name"]}'
                        }};
                    """)
                
                # Send message
                send_button = web_driver.find_element(By.ID, "send-button")
                send_button.click()
                
                # Wait for response to appear
                try:
                    WebDriverWait(web_driver, 30).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "ai-response"))
                    )
                    
                    # Get the response text from UI
                    response_elements = web_driver.find_elements(By.CLASS_NAME, "ai-response")
                    latest_response = response_elements[-1] if response_elements else None
                    
                    if latest_response:
                        response_text = latest_response.text.lower()
                        
                        # UI MOCK RESPONSE DETECTION PATTERNS
                        ui_mock_patterns = [
                            "i apologize",
                            "i'm sorry", 
                            "something went wrong",
                            "please try again",
                            "service temporarily unavailable",
                            "unable to process your request",
                            "encountered an error",
                            "system is experiencing issues",
                            "please refresh the page",
                            "connection error",
                            "failed to load",
                            "error occurred",
                            "try again later",
                            "service unavailable",
                            "processing failed"
                        ]
                        
                        detected_ui_patterns = []
                        for pattern in ui_mock_patterns:
                            if pattern in response_text:
                                detected_ui_patterns.append(pattern)
                        
                        if detected_ui_patterns:
                            # Capture screenshot as evidence
                            screenshot_path = f"/tmp/ui_mock_evidence_{scenario['name'].lower().replace(' ', '_')}.png"
                            web_driver.save_screenshot(screenshot_path)
                            
                            evidence = {
                                "scenario": scenario["name"],
                                "detected_patterns": detected_ui_patterns,
                                "response_text": response_text[:300],
                                "screenshot_path": screenshot_path,
                                "ui_elements_present": [elem for elem in scenario["expected_ui_elements"] 
                                                      if web_driver.find_elements(By.ID, elem)],
                                "user_visible_error": True
                            }
                            ui_mock_evidence.append(evidence)
                            
                            logger.error(f"UI MOCK RESPONSE DETECTED: {json.dumps(evidence, indent=2)}")
                    
                    # Also check for error notifications/toasts
                    error_notifications = web_driver.find_elements(By.CLASS_NAME, "error-notification")
                    for notification in error_notifications:
                        notification_text = notification.text.lower()
                        if any(pattern in notification_text for pattern in ui_mock_patterns):
                            ui_mock_evidence.append({
                                "scenario": f"{scenario['name']} - Error Notification",
                                "detected_patterns": ["error_notification_mock"],
                                "notification_text": notification_text,
                                "element_type": "error_notification"
                            })
                            
                except Exception as e:
                    logger.error(f"UI test scenario {scenario['name']} failed: {str(e)}")
                    # Even UI failures should not show generic error messages
                    if any(pattern in str(e).lower() for pattern in ["timeout", "element not found", "failed"]):
                        ui_mock_evidence.append({
                            "scenario": f"{scenario['name']} - UI Exception",
                            "detected_patterns": ["ui_exception_generic"],
                            "exception_content": str(e)[:200]
                        })
                
                # Brief pause between scenarios
                time.sleep(2)
            
            if ui_mock_evidence:
                failure_evidence = {
                    "test_name": "Web UI Mock Response Elimination",
                    "interface": "Web Browser UI",
                    "failures_count": len(ui_mock_evidence),
                    "ui_mock_evidence": ui_mock_evidence,
                    "customer_impact": {
                        "user_experience": "Degraded - users see platform as unreliable",
                        "competitive_position": "Weakened - appears less sophisticated than competitors",
                        "trust_damage": "High - users question platform capabilities"
                    }
                }
                
                logger.error(f"WEB UI MOCK RESPONSES DETECTED: {json.dumps(failure_evidence, indent=2)}")
                
                pytest.fail(
                    f"WEB UI MOCK RESPONSES DETECTED: "
                    f"Found {len(ui_mock_evidence)} instances of mock/fallback responses "
                    f"visible to users in the web interface. "
                    f"Users seeing generic error messages like 'I apologize' or 'Service unavailable' "
                    f"immediately recognize the platform as unreliable. "
                    f"Web UI must show authentic responses or premium error handling only. "
                    f"Detected scenarios: {[e['scenario'] for e in ui_mock_evidence]}"
                )
                
        except Exception as e:
            logger.error(f"Web UI test setup failed: {str(e)}")
            pytest.fail(f"Web UI test could not complete due to setup issues: {str(e)}")

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical  
    async def test_api_response_mock_elimination(self, real_services_fixture, test_user):
        """
        FAILING TEST: Prove direct API calls can return mock responses
        
        Business Impact: API integrations showing fallback responses to partner
        systems makes our platform appear unreliable in B2B integrations.
        
        Expected Failure: Mock responses in API responses
        Required Fix: API endpoints must return authentic data or proper error codes
        """
        logger.info("Testing API response mock elimination...")
        
        # Test all major API endpoints for mock response elimination
        api_endpoints_to_test = [
            {
                "name": "Agent Execution API",
                "endpoint": "/api/v1/agent/execute", 
                "method": "POST",
                "payload": {
                    "user_id": test_user.user_id,
                    "prompt": "Generate business intelligence report",
                    "context": {"integration": "api_test"}
                }
            },
            {
                "name": "Data Analysis API",
                "endpoint": "/api/v1/data/analyze",
                "method": "POST", 
                "payload": {
                    "user_id": test_user.user_id,
                    "query": "Provide cost optimization analysis",
                    "context": {"api_integration": True}
                }
            },
            {
                "name": "Chat Message API",
                "endpoint": "/api/v1/chat/message",
                "method": "POST",
                "payload": {
                    "user_id": test_user.user_id,
                    "message": "Help me analyze market trends",
                    "thread_id": f"api-test-{uuid.uuid4()}"
                }
            },
            {
                "name": "User Context API", 
                "endpoint": "/api/v1/user/context",
                "method": "GET",
                "payload": None
            },
            {
                "name": "Health Check API",
                "endpoint": "/api/health",
                "method": "GET", 
                "payload": None
            }
        ]
        
        api_mock_evidence = []
        
        async with aiohttp.ClientSession() as session:
            backend_url = get_env('BACKEND_URL', 'http://localhost:8000')
            
            for api_test in api_endpoints_to_test:
                try:
                    # Add failure simulation parameters
                    if api_test["payload"]:
                        api_test["payload"]["test_failure_simulation"] = True
                        api_test["payload"]["force_potential_errors"] = True
                    
                    # Make API request
                    request_kwargs = {
                        "headers": {"Authorization": f"Bearer {test_user.jwt_token}"},
                        "timeout": 45
                    }
                    
                    if api_test["method"] == "POST":
                        request_kwargs["json"] = api_test["payload"]
                        
                    async with getattr(session, api_test["method"].lower())(
                        f"{backend_url}{api_test['endpoint']}",
                        **request_kwargs
                    ) as response:
                        
                        response_text = await response.text()
                        response_content = response_text.lower()
                        
                        try:
                            response_json = await response.json()
                        except:
                            response_json = {}
                        
                        # API MOCK RESPONSE DETECTION PATTERNS
                        api_mock_patterns = [
                            # Direct mock responses in API
                            "i apologize",
                            "unable to process", 
                            "encountered an error",
                            "please try again",
                            "service temporarily unavailable",
                            "internal server error",
                            "processing failed",
                            "system error",
                            
                            # API-specific fallback patterns
                            "fallback response",
                            "default api response",
                            "generic error message", 
                            "api error occurred",
                            "service not available",
                            "endpoint unavailable",
                            
                            # Mock data indicators in API responses
                            "sample_data",
                            "mock_response", 
                            "placeholder_content",
                            "test_data_returned",
                            "fallback_data",
                            
                            # HTTP error fallbacks
                            "500 internal server error",
                            "503 service unavailable", 
                            "502 bad gateway",
                            "504 gateway timeout"
                        ]
                        
                        detected_api_patterns = []
                        for pattern in api_mock_patterns:
                            if pattern in response_content:
                                detected_api_patterns.append(pattern)
                        
                        # Check HTTP status codes that might indicate fallback responses
                        if response.status >= 500:
                            detected_api_patterns.append(f"http_status_{response.status}")
                        
                        if detected_api_patterns:
                            evidence = {
                                "api_endpoint": api_test["name"], 
                                "endpoint_path": api_test["endpoint"],
                                "http_method": api_test["method"],
                                "http_status": response.status,
                                "detected_patterns": detected_api_patterns,
                                "response_content": response_content[:400],
                                "response_json": response_json if response_json else "No JSON data",
                                "integration_impact": "Partner systems receive unreliable data"
                            }
                            api_mock_evidence.append(evidence)
                            
                            logger.error(f"API MOCK RESPONSE DETECTED: {json.dumps(evidence, indent=2)}")
                            
                except Exception as e:
                    # API exceptions should also not contain mock language
                    error_content = str(e).lower()
                    if any(pattern in error_content for pattern in ["apologize", "unavailable", "try again"]):
                        api_mock_evidence.append({
                            "api_endpoint": f"{api_test['name']} - Exception",
                            "endpoint_path": api_test["endpoint"],
                            "detected_patterns": ["exception_contains_mock_language"],
                            "exception_content": error_content[:300],
                            "integration_impact": "API integration failures with generic messaging"
                        })
        
        if api_mock_evidence:
            failure_evidence = {
                "test_name": "API Response Mock Elimination",
                "interface": "Direct API Calls", 
                "failures_count": len(api_mock_evidence),
                "api_mock_evidence": api_mock_evidence,
                "business_impact": {
                    "b2b_integrations": "Partner systems receive unreliable responses",
                    "platform_credibility": "API appears unstable to technical integrators",
                    "competitive_disadvantage": "Technical evaluators prefer more reliable APIs"
                }
            }
            
            logger.error(f"API MOCK RESPONSES DETECTED: {json.dumps(failure_evidence, indent=2)}")
            
            pytest.fail(
                f"API MOCK RESPONSES DETECTED: "
                f"Found {len(api_mock_evidence)} API endpoints returning mock/fallback responses. "
                f"B2B integrations and partner systems receiving generic error messages or "
                f"fallback data makes our platform appear unreliable in technical evaluations. "
                f"APIs must return authentic data or proper HTTP error codes with structured "
                f"error responses, never generic 'I apologize' style messages. "
                f"Affected endpoints: {[e['api_endpoint'] for e in api_mock_evidence]}"
            )

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_websocket_user_experience_mock_elimination(self, real_services_fixture, test_user):
        """
        FAILING TEST: Prove WebSocket user experience can show mock responses
        
        Business Impact: Real-time chat showing "Connection error" or fallback
        messages creates poor user experience and platform perception.
        
        Expected Failure: Mock responses visible through WebSocket interface
        Required Fix: WebSocket interface must provide authentic real-time experience
        """
        logger.info("Testing WebSocket user experience mock elimination...")
        
        backend_url = get_env('BACKEND_URL', 'http://localhost:8000')
        ws_url = backend_url.replace('http', 'ws') + '/ws'
        
        ws_mock_evidence = []
        
        try:
            async with websockets.connect(
                ws_url + f"?token={test_user.jwt_token}",
                timeout=15
            ) as websocket:
                
                # Test WebSocket scenarios that might show mock responses to users
                ws_scenarios = [
                    {
                        "name": "Chat Message with AI Failure",
                        "message": {
                            "user_id": test_user.user_id,
                            "thread_id": f"ws-test-{uuid.uuid4()}",
                            "message": "I need immediate analysis for my business meeting",
                            "force_ai_failure": True
                        }
                    },
                    {
                        "name": "Agent Execution with Tool Failure", 
                        "message": {
                            "user_id": test_user.user_id,
                            "thread_id": f"ws-tool-test-{uuid.uuid4()}", 
                            "action": "execute_agent",
                            "prompt": "Run comprehensive data analysis",
                            "force_tool_failure": True
                        }
                    },
                    {
                        "name": "Connection Stress Test",
                        "message": {
                            "user_id": test_user.user_id,
                            "thread_id": f"ws-stress-test-{uuid.uuid4()}",
                            "action": "stress_test_connection",
                            "simulate_connection_issues": True
                        }
                    }
                ]
                
                for scenario in ws_scenarios:
                    logger.info(f"Testing WebSocket scenario: {scenario['name']}")
                    
                    # Send WebSocket message
                    await websocket.send(json.dumps(scenario["message"]))
                    
                    # Collect WebSocket responses
                    ws_responses = []
                    timeout_count = 0
                    
                    while timeout_count < 8:
                        try:
                            response = await asyncio.wait_for(websocket.recv(), timeout=5)
                            ws_responses.append(response)
                            
                            # Parse response
                            try:
                                response_data = json.loads(response)
                                response_content = str(response_data).lower()
                                
                                # WEBSOCKET USER EXPERIENCE MOCK PATTERNS
                                ws_mock_patterns = [
                                    # Real-time chat fallbacks
                                    "connection error",
                                    "websocket error",
                                    "failed to send message",
                                    "chat service unavailable",
                                    "message delivery failed",
                                    
                                    # AI response fallbacks through WebSocket
                                    "i apologize",
                                    "unable to process",
                                    "something went wrong",
                                    "please try again",
                                    "service temporarily down",
                                    
                                    # Real-time system status fallbacks  
                                    "system overloaded",
                                    "processing queue full",
                                    "server not responding",
                                    "connection timeout",
                                    "network error",
                                    
                                    # WebSocket-specific generic responses
                                    "websocket disconnected",
                                    "connection lost", 
                                    "failed to reconnect",
                                    "session expired",
                                    "authentication failed"
                                ]
                                
                                detected_ws_patterns = []
                                for pattern in ws_mock_patterns:
                                    if pattern in response_content:
                                        detected_ws_patterns.append(pattern)
                                
                                if detected_ws_patterns:
                                    evidence = {
                                        "scenario": scenario["name"],
                                        "detected_patterns": detected_ws_patterns,
                                        "response_content": response_content[:300],
                                        "response_data": response_data,
                                        "user_visible": True,
                                        "real_time_impact": "User sees unreliable real-time experience"
                                    }
                                    ws_mock_evidence.append(evidence)
                                    
                                    logger.error(f"WEBSOCKET MOCK RESPONSE DETECTED: {json.dumps(evidence, indent=2)}")
                                
                                # Check if this looks like a completion message
                                if response_data.get('event_type') == 'agent_completed' or 'completed' in response_content:
                                    break
                                    
                            except json.JSONDecodeError:
                                # Non-JSON responses might also contain mock patterns
                                if any(pattern in response.lower() for pattern in ws_mock_patterns):
                                    ws_mock_evidence.append({
                                        "scenario": f"{scenario['name']} - Non-JSON Response",
                                        "detected_patterns": ["non_json_mock_response"],
                                        "response_content": response[:200],
                                        "user_visible": True
                                    })
                            
                        except asyncio.TimeoutError:
                            timeout_count += 1
                            continue
                        except websockets.exceptions.ConnectionClosed:
                            # Connection closing with generic message is also a mock pattern
                            ws_mock_evidence.append({
                                "scenario": f"{scenario['name']} - Connection Closed",
                                "detected_patterns": ["generic_connection_closure"],
                                "error_type": "connection_closed_without_context"
                            })
                            break
                    
                    # Brief pause between scenarios
                    await asyncio.sleep(2)
        
        except Exception as e:
            logger.error(f"WebSocket test failed: {str(e)}")
            # WebSocket connection failures should also not show generic language
            error_content = str(e).lower()
            if any(pattern in error_content for pattern in ["connection failed", "unable to connect", "websocket error"]):
                ws_mock_evidence.append({
                    "scenario": "WebSocket Connection Exception",
                    "detected_patterns": ["connection_exception_generic"],
                    "exception_content": error_content[:300],
                    "user_impact": "User sees generic connection error"
                })
        
        if ws_mock_evidence:
            failure_evidence = {
                "test_name": "WebSocket User Experience Mock Elimination",
                "interface": "Real-time WebSocket Connection",
                "failures_count": len(ws_mock_evidence),
                "ws_mock_evidence": ws_mock_evidence,
                "user_experience_impact": {
                    "real_time_chat": "Poor - users see unreliable messaging",
                    "live_interactions": "Degraded - generic error handling", 
                    "platform_perception": "Unreliable - users question real-time capabilities"
                }
            }
            
            logger.error(f"WEBSOCKET MOCK RESPONSES DETECTED: {json.dumps(failure_evidence, indent=2)}")
            
            pytest.fail(
                f"WEBSOCKET USER EXPERIENCE MOCK RESPONSES DETECTED: "
                f"Found {len(ws_mock_evidence)} instances of mock/fallback responses "
                f"visible to users through real-time WebSocket interface. "
                f"Users experiencing 'Connection error', 'Chat service unavailable', or "
                f"generic AI fallbacks in real-time interactions immediately perceive "
                f"the platform as unreliable for live use cases. "
                f"WebSocket interface must provide authentic real-time experience only. "
                f"Detected scenarios: {[e['scenario'] for e in ws_mock_evidence]}"
            )

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_error_handling_mock_elimination_across_interfaces(self, real_services_fixture, test_user):
        """
        FAILING TEST: Prove error handling shows mock responses across interfaces
        
        Business Impact: Consistent generic error handling across all interfaces
        makes platform appear unprofessional and reduces user confidence.
        
        Expected Failure: Generic error handling patterns across all interfaces
        Required Fix: Context-aware, authentic error handling for all interfaces
        """
        logger.info("Testing error handling mock elimination across all interfaces...")
        
        # Test error handling across multiple interfaces simultaneously
        interface_tests = {
            "API": [],
            "WebSocket": [],
            "System": []
        }
        
        # Generate various error conditions
        error_scenarios = [
            {
                "name": "Database Connection Lost",
                "trigger": "force_db_connection_failure",
                "context": "critical_data_operation"
            },
            {
                "name": "LLM API Rate Limited", 
                "trigger": "force_llm_rate_limit",
                "context": "ai_processing_request"
            },
            {
                "name": "Authentication Token Expired",
                "trigger": "force_token_expiration", 
                "context": "authenticated_operation"
            },
            {
                "name": "System Resource Exhausted",
                "trigger": "force_resource_exhaustion",
                "context": "high_load_operation"
            }
        ]
        
        # Test API error handling
        async with aiohttp.ClientSession() as session:
            backend_url = get_env('BACKEND_URL', 'http://localhost:8000')
            
            for scenario in error_scenarios:
                try:
                    payload = {
                        "user_id": test_user.user_id,
                        "thread_id": f"error-test-{uuid.uuid4()}",
                        "prompt": f"Test error handling for {scenario['name']}",
                        scenario["trigger"]: True,
                        "context": {
                            "error_test": True,
                            "scenario": scenario["name"],
                            "interface": "API"
                        }
                    }
                    
                    async with session.post(
                        f"{backend_url}/api/v1/agent/execute",
                        json=payload,
                        headers={"Authorization": f"Bearer {test_user.jwt_token}"},
                        timeout=30
                    ) as response:
                        
                        response_data = await response.json()
                        response_content = str(response_data).lower()
                        
                        # ERROR HANDLING MOCK PATTERNS
                        error_mock_patterns = [
                            "internal error occurred",
                            "please contact support",
                            "unexpected error",
                            "system temporarily unavailable", 
                            "please try again later",
                            "error processing request",
                            "service not available",
                            "operation failed"
                        ]
                        
                        detected_error_patterns = []
                        for pattern in error_mock_patterns:
                            if pattern in response_content:
                                detected_error_patterns.append(pattern)
                        
                        if detected_error_patterns:
                            interface_tests["API"].append({
                                "scenario": scenario["name"],
                                "detected_patterns": detected_error_patterns,
                                "response_content": response_content[:250],
                                "interface": "API"
                            })
                            
                except Exception as e:
                    if any(pattern in str(e).lower() for pattern in error_mock_patterns):
                        interface_tests["API"].append({
                            "scenario": f"{scenario['name']} - Exception",
                            "detected_patterns": ["api_exception_generic"],
                            "exception_content": str(e)[:200]
                        })
        
        # Test WebSocket error handling
        try:
            backend_url = get_env('BACKEND_URL', 'http://localhost:8000')
            ws_url = backend_url.replace('http', 'ws') + '/ws'
            
            async with websockets.connect(
                ws_url + f"?token={test_user.jwt_token}",
                timeout=10
            ) as websocket:
                
                for scenario in error_scenarios:
                    await websocket.send(json.dumps({
                        "user_id": test_user.user_id,
                        "action": "test_error_handling",
                        scenario["trigger"]: True,
                        "scenario_name": scenario["name"]
                    }))
                    
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=10)
                        response_data = json.loads(response)
                        response_content = str(response_data).lower()
                        
                        detected_ws_error_patterns = []
                        for pattern in error_mock_patterns:
                            if pattern in response_content:
                                detected_ws_error_patterns.append(pattern)
                        
                        if detected_ws_error_patterns:
                            interface_tests["WebSocket"].append({
                                "scenario": scenario["name"],
                                "detected_patterns": detected_ws_error_patterns,
                                "response_content": response_content[:250],
                                "interface": "WebSocket"
                            })
                            
                    except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed) as e:
                        interface_tests["WebSocket"].append({
                            "scenario": f"{scenario['name']} - WebSocket Error",
                            "detected_patterns": ["websocket_generic_error"],
                            "error_type": type(e).__name__
                        })
                        
        except Exception as e:
            interface_tests["System"].append({
                "scenario": "WebSocket Connection Setup",
                "detected_patterns": ["websocket_setup_error"],
                "exception_content": str(e)[:200]
            })
        
        # Analyze cross-interface consistency
        total_errors_detected = sum(len(errors) for errors in interface_tests.values())
        
        if total_errors_detected > 0:
            failure_evidence = {
                "test_name": "Cross-Interface Error Handling Mock Elimination",
                "total_errors_detected": total_errors_detected,
                "errors_by_interface": interface_tests,
                "consistency_analysis": {
                    "api_errors": len(interface_tests["API"]),
                    "websocket_errors": len(interface_tests["WebSocket"]), 
                    "system_errors": len(interface_tests["System"])
                },
                "business_impact": {
                    "user_experience": "Inconsistent - users see generic errors across all interfaces",
                    "platform_credibility": "Damaged - appears unprofessional and unreliable",
                    "competitive_disadvantage": "Significant - competitors provide better error UX"
                }
            }
            
            logger.error(f"CROSS-INTERFACE ERROR HANDLING FAILURES: {json.dumps(failure_evidence, indent=2)}")
            
            pytest.fail(
                f"CROSS-INTERFACE ERROR HANDLING MOCK RESPONSES DETECTED: "
                f"Found {total_errors_detected} total instances of generic error handling "
                f"across API ({len(interface_tests['API'])}), WebSocket ({len(interface_tests['WebSocket'])}), "
                f"and System ({len(interface_tests['System'])}) interfaces. "
                f"Consistent generic error messages like 'Please try again later' and "
                f"'Service temporarily unavailable' across all interfaces makes the platform "
                f"appear unprofessional and reduces user confidence in system reliability. "
                f"Each interface must provide context-aware, authentic error handling "
                f"appropriate for the user's context and tier."
            )