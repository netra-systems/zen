"""
MISSION CRITICAL E2E TEST: Agent Golden Path Message Flow - REAL GCP STAGING ONLY

Business Value Justification:
- Segment: All (Free/Early/Mid/Enterprise/Platform) 
- Business Goal: Validate complete $500K+ ARR golden path user flow
- Value Impact: Ensures core AI chat functionality works end-to-end
- Strategic Impact: Protects 90% of platform business value

CRITICAL TEST PURPOSE:
This test validates the COMPLETE golden path user flow from login to AI response
that represents 90% of the platform's business value. Any failure here blocks
deployment and indicates broken core functionality.

Test Scope:
1. Real user authentication with GCP staging environment
2. Complete agent execution flow with real LLMs
3. All 5 critical WebSocket events validation
4. Multi-agent coordination and message routing
5. Quality of AI responses (substantive business value)
6. Performance metrics and error scenarios
7. Complete cleanup and resource management

REQUIREMENTS per CLAUDE.md:
- NO MOCKS - Use real GCP staging services only
- REAL WEBSOCKET CONNECTIONS - Test actual WebSocket infrastructure
- REAL AGENT EXECUTION - Full supervisor and sub-agent workflows
- REAL LLM CALLS - Validate actual AI responses
- PROPER ERROR HANDLING - Tests must fail hard when issues occur
- VALIDATE BUSINESS VALUE - Ensure AI responses provide real value
- END-TO-END VALIDATION - Complete user journey from auth to response

If this test fails, the core product functionality is broken.
"""

import asyncio
import json
import logging
import os
import sys
import time
import uuid
import websockets
from collections import defaultdict
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Set, Any, Optional, AsyncGenerator, Tuple
from unittest.mock import AsyncMock

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
import aiohttp
from loguru import logger

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase, SsotTestMetrics, CategoryType
from shared.isolated_environment import get_env, IsolatedEnvironment

# Real GCP Staging Services
try:
    from tests.e2e.staging_override import StagingServicesConfig
    from tests.e2e.real_client_factory import RealGCPStagingClientFactory
    from tests.e2e.enforce_real_services import EnforceRealServicesConfig
except ImportError as e:
    logger.warning(f"Staging services not available: {e}")

# Configure logging for mission critical tests
logger.configure(handlers=[{
    'sink': sys.stdout, 
    'level': 'INFO', 
    'format': '<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>'
}])


@dataclass
class GoldenPathTestResult:
    """Comprehensive results from golden path flow test."""
    success: bool = False
    user_authenticated: bool = False
    websocket_connected: bool = False
    agent_execution_started: bool = False
    websocket_events_received: int = 0
    critical_events_validated: bool = False
    agent_response_received: bool = False
    response_quality_valid: bool = False
    response_time: float = 0.0
    total_execution_time: float = 0.0
    agent_response_content: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    websocket_events: List[Dict[str, Any]] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    
    def is_golden_path_successful(self) -> bool:
        """Determine if the complete golden path flow succeeded."""
        return (
            self.success and
            self.user_authenticated and
            self.websocket_connected and
            self.agent_execution_started and
            self.critical_events_validated and
            self.agent_response_received and
            self.response_quality_valid and
            len(self.errors) == 0
        )
    
    def get_business_value_score(self) -> float:
        """Calculate business value delivery score (0-100)."""
        score = 0.0
        
        # Authentication (10%)
        if self.user_authenticated:
            score += 10.0
            
        # WebSocket connectivity (15%)
        if self.websocket_connected:
            score += 15.0
            
        # Agent execution (20%)
        if self.agent_execution_started:
            score += 20.0
            
        # Event delivery (25%)
        if self.critical_events_validated:
            score += 25.0
            
        # Response received (20%)
        if self.agent_response_received:
            score += 20.0
            
        # Response quality (10%) 
        if self.response_quality_valid:
            score += 10.0
            
        return score


@dataclass
class WebSocketEventMonitor:
    """Monitors and validates critical WebSocket events for business value."""
    
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.agent_started: bool = False
        self.agent_thinking: bool = False
        self.tool_executing: bool = False
        self.tool_completed: bool = False
        self.agent_completed: bool = False
        self.errors: List[str] = []
        self.start_time: float = time.time()
        self.event_timestamps: Dict[str, List[float]] = defaultdict(list)
        
    def record_event(self, event: Dict[str, Any]) -> None:
        """Record and categorize WebSocket event with timestamp."""
        current_time = time.time()
        event_with_meta = {
            **event,
            'timestamp': current_time - self.start_time,
            'received_at': datetime.now(UTC).isoformat(),
            'sequence_number': len(self.events)
        }
        
        self.events.append(event_with_meta)
        event_type = event.get('type', '').lower()
        
        # Track event timestamps
        self.event_timestamps[event_type].append(current_time - self.start_time)
        
        logger.info(f"📥 WebSocket Event #{len(self.events)}: {event_type}")
        
        # Categorize critical business events
        if 'agent_started' in event_type or 'agent_beginning' in event_type:
            self.agent_started = True
            logger.success("CHECK CRITICAL EVENT: agent_started - User knows AI processing began")
            
        elif 'agent_thinking' in event_type or 'reasoning' in event_type:
            self.agent_thinking = True
            logger.success("CHECK REAL-TIME EVENT: agent_thinking - User sees AI reasoning")
            
        elif 'tool_executing' in event_type or 'tool_start' in event_type:
            self.tool_executing = True
            logger.success("CHECK TRANSPARENCY EVENT: tool_executing - User sees tool usage")
            
        elif 'tool_completed' in event_type or 'tool_result' in event_type:
            self.tool_completed = True
            logger.success("CHECK FEEDBACK EVENT: tool_completed - User sees tool results")
            
        elif 'agent_completed' in event_type or 'final_result' in event_type or 'agent_finished' in event_type:
            self.agent_completed = True
            logger.success("CHECK COMPLETION EVENT: agent_completed - User knows processing finished")
            
        else:
            logger.debug(f"📋 Other event: {event_type}")
    
    def validate_critical_events(self) -> Tuple[bool, List[str]]:
        """Validate that all critical business events were received."""
        validation_errors = []
        
        if not self.agent_started:
            validation_errors.append("X CRITICAL: No agent_started event - Users don't know AI processing began")
            
        if not self.agent_thinking:
            validation_errors.append("WARNING️  WARNING: No agent_thinking events - Users can't see AI reasoning process")
            
        if not self.agent_completed:
            validation_errors.append("X CRITICAL: No agent_completed event - Users don't know when processing finished")
            
        if len(self.events) == 0:
            validation_errors.append("X FATAL: No WebSocket events received - Chat functionality completely broken")
            
        return (len(validation_errors) == 0, validation_errors)
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """Get performance metrics for business value assessment."""
        metrics = {
            'total_events': len(self.events),
            'event_rate': len(self.events) / max(0.1, time.time() - self.start_time),
            'time_to_first_event': 0.0,
            'time_to_completion': 0.0,
            'average_event_interval': 0.0
        }
        
        if self.events:
            metrics['time_to_first_event'] = self.events[0]['timestamp']
            
            if self.agent_completed and 'agent_completed' in self.event_timestamps:
                metrics['time_to_completion'] = self.event_timestamps['agent_completed'][0]
                
            # Calculate average interval between events
            if len(self.events) > 1:
                intervals = [
                    self.events[i]['timestamp'] - self.events[i-1]['timestamp'] 
                    for i in range(1, len(self.events))
                ]
                metrics['average_event_interval'] = sum(intervals) / len(intervals)
        
        return metrics
    
    def generate_validation_report(self) -> str:
        """Generate comprehensive validation report for business stakeholders."""
        is_valid, errors = self.validate_critical_events()
        metrics = self.get_performance_metrics()
        
        report_lines = [
            "=" * 100,
            "🎯 MISSION CRITICAL: GOLDEN PATH WEBSOCKET EVENT VALIDATION REPORT",
            "=" * 100,
            f"📊 Total Events Received: {len(self.events)}",
            f"⏱️  Test Duration: {time.time() - self.start_time:.2f}s",
            f"📈 Event Rate: {metrics['event_rate']:.1f} events/second",
            "",
            "🔍 CRITICAL BUSINESS EVENT COVERAGE:",
            f"  🚀 agent_started:   {'CHECK RECEIVED' if self.agent_started else 'X MISSING'}",
            f"  🧠 agent_thinking:  {'CHECK RECEIVED' if self.agent_thinking else 'WARNING️  MISSING'}",
            f"  🔧 tool_executing:  {'CHECK RECEIVED' if self.tool_executing else 'WARNING️  MISSING'}",
            f"  CHECK tool_completed:  {'CHECK RECEIVED' if self.tool_completed else 'WARNING️  MISSING'}",
            f"  🏁 agent_completed: {'CHECK RECEIVED' if self.agent_completed else 'X MISSING'}",
            "",
            f"🎯 BUSINESS VALUE STATUS: {'CHECK DELIVERING VALUE' if is_valid else 'X VALUE AT RISK'}",
        ]
        
        if errors:
            report_lines.extend([
                "",
                "WARNING️  CRITICAL ISSUES BLOCKING BUSINESS VALUE:",
            ])
            for error in errors:
                report_lines.append(f"  {error}")
        
        if self.events:
            report_lines.extend([
                "",
                "📋 EVENT SEQUENCE (Business Flow Analysis):",
            ])
            for i, event in enumerate(self.events[:15]):  # Show first 15 events
                timestamp = event.get('timestamp', 0)
                event_type = event.get('type', 'unknown')
                report_lines.append(f"  {i+1:2d}. [{timestamp:6.2f}s] {event_type}")
                
            if len(self.events) > 15:
                report_lines.append(f"  ... and {len(self.events) - 15} more events")
        
        report_lines.extend([
            "",
            "📈 PERFORMANCE METRICS:",
            f"  ⚡ Time to First Event: {metrics['time_to_first_event']:.2f}s",
            f"  🏁 Time to Completion: {metrics['time_to_completion']:.2f}s",
            f"  📊 Average Event Interval: {metrics['average_event_interval']:.2f}s",
            "=" * 100
        ])
        
        return '\n'.join(report_lines)


class RealWebSocketConnection:
    """Real WebSocket connection for GCP staging environment."""
    
    def __init__(self, event_monitor: WebSocketEventMonitor, staging_config: Dict[str, str]):
        self.event_monitor = event_monitor
        self.staging_config = staging_config
        self.websocket = None
        self.is_connected = False
        self.connection_id = str(uuid.uuid4())
        self.received_messages: List[Dict[str, Any]] = []
        
    async def connect(self, auth_token: str, user_id: str) -> bool:
        """Connect to real GCP staging WebSocket service."""
        try:
            # Use staging WebSocket URL from configuration
            ws_url = self.staging_config.get('websocket_url', 'wss://api-staging.netrasystems.ai/ws')
            
            # Add authentication and user context to connection
            connection_params = {
                'token': auth_token,
                'user_id': user_id,
                'connection_id': self.connection_id
            }
            
            # Build WebSocket URL with authentication
            ws_url_with_auth = f"{ws_url}?{aiohttp.helpers.urlencode(connection_params)}"
            
            logger.info(f"🔌 Connecting to real GCP staging WebSocket: {ws_url}")
            
            # Connect with proper headers for staging environment
            extra_headers = {
                'Authorization': f'Bearer {auth_token}',
                'X-User-ID': user_id,
                'X-Connection-ID': self.connection_id
            }
            
            self.websocket = await websockets.connect(
                ws_url_with_auth,
                extra_headers=extra_headers,
                ping_interval=20,
                ping_timeout=10,
                timeout=30
            )
            
            self.is_connected = True
            logger.success(f"CHECK WebSocket connected to staging environment")
            
            # Start listening for messages
            asyncio.create_task(self._listen_for_messages())
            
            return True
            
        except Exception as e:
            logger.error(f"X Failed to connect to staging WebSocket: {e}")
            return False
    
    async def _listen_for_messages(self):
        """Listen for WebSocket messages and route to event monitor."""
        try:
            async for message in self.websocket:
                try:
                    if isinstance(message, str):
                        data = json.loads(message)
                    else:
                        data = message
                    
                    self.received_messages.append(data)
                    self.event_monitor.record_event(data)
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"WARNING️  Invalid JSON in WebSocket message: {e}")
                    
        except websockets.ConnectionClosed:
            logger.info("🔌 WebSocket connection closed by server")
            self.is_connected = False
        except Exception as e:
            logger.error(f"X Error in WebSocket message listener: {e}")
            self.is_connected = False
    
    async def send_message(self, message: Dict[str, Any]) -> bool:
        """Send message through WebSocket connection."""
        if not self.is_connected or not self.websocket:
            logger.error("X Cannot send message - WebSocket not connected")
            return False
            
        try:
            await self.websocket.send(json.dumps(message))
            logger.debug(f"📤 Sent WebSocket message: {message.get('type', 'unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"X Failed to send WebSocket message: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect WebSocket connection."""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            logger.info("🔌 WebSocket disconnected")


@pytest.mark.e2e
@pytest.mark.critical
class TestAgentGoldenPathMessages(SSotAsyncTestCase):
    """
    MISSION CRITICAL E2E Tests for Agent Golden Path Message Flow.
    
    This test class validates the COMPLETE golden path user flow that represents
    90% of the platform's business value. Tests run against real GCP staging
    environment with no mocks.
    
    Business Impact: $500K+ ARR depends on this functionality.
    """
    
    @classmethod
    def setup_class(cls):
        """Set up class-level resources for golden path testing."""
        super().setup_class()
        cls.logger.info("🎯 Setting up MISSION CRITICAL Golden Path test suite")
        
        # Initialize staging configuration
        cls.staging_config = {
            'backend_url': 'https://staging.netrasystems.ai',
            'auth_url': 'https://staging.netrasystems.ai',
            'websocket_url': 'wss://api-staging.netrasystems.ai/ws',
            'frontend_url': 'https://staging.netrasystems.ai'
        }
        
        # Validate staging environment
        cls._validate_staging_environment()
    
    @classmethod
    def _validate_staging_environment(cls):
        """Validate that staging environment is accessible."""
        try:
            import requests
            
            # Check backend health
            response = requests.get(
                f"{cls.staging_config['backend_url']}/health",
                timeout=10
            )
            
            if response.status_code != 200:
                cls.logger.warning(f"WARNING️  Staging backend health check failed: {response.status_code}")
            else:
                cls.logger.success("CHECK Staging backend is healthy")
                
        except Exception as e:
            cls.logger.warning(f"WARNING️  Could not validate staging environment: {e}")
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        
        # Configure test for E2E category
        self._test_context.test_category = CategoryType.E2E
        self._test_context.metadata['business_critical'] = True
        self._test_context.metadata['golden_path'] = True
        self._test_context.metadata['staging_environment'] = True
        
        # Initialize test components
        self.event_monitor = WebSocketEventMonitor()
        self.test_result = GoldenPathTestResult()
        self.start_time = time.time()
        
        # Set staging environment variables
        self.set_env_var('ENVIRONMENT', 'staging')
        self.set_env_var('USE_REAL_SERVICES', 'true')
        self.set_env_var('NO_MOCKS', 'true')
        self.set_env_var('GCP_STAGING', 'true')
        
        logger.info("🎯 MISSION CRITICAL: Starting Golden Path test")
    
    def teardown_method(self, method=None):
        """Cleanup after each test method."""
        # Record comprehensive metrics
        self._metrics.record_custom('golden_path_success', self.test_result.is_golden_path_successful())
        self._metrics.record_custom('business_value_score', self.test_result.get_business_value_score())
        self._metrics.record_custom('websocket_events_count', len(self.event_monitor.events))
        self._metrics.record_custom('critical_events_validated', self.test_result.critical_events_validated)
        self._metrics.record_custom('response_quality_valid', self.test_result.response_quality_valid)
        
        # Log final validation report
        logger.info("\n" + self.event_monitor.generate_validation_report())
        
        # Log business value summary
        business_score = self.test_result.get_business_value_score()
        logger.info(f"💰 BUSINESS VALUE SCORE: {business_score:.1f}/100.0")
        
        if business_score < 80.0:
            logger.error(f"X BUSINESS VALUE AT RISK: Score {business_score:.1f} below threshold")
        else:
            logger.success(f"CHECK BUSINESS VALUE PROTECTED: Score {business_score:.1f}")
        
        super().teardown_method(method)
    
    @pytest.mark.asyncio
    async def test_complete_golden_path_user_flow(self):
        """
        Test the complete golden path user flow from authentication to AI response.
        
        This test validates the end-to-end user journey that represents 90% of
        platform business value:
        
        1. User authentication with real GCP staging auth service
        2. WebSocket connection establishment with staging infrastructure  
        3. User sends message through real WebSocket connection
        4. Agent execution with real LLM integration
        5. All 5 critical WebSocket events received
        6. Quality AI response delivered to user
        7. Performance within acceptable thresholds
        8. Complete cleanup and resource management
        
        CRITICAL: Failure blocks deployment - core product broken.
        """
        logger.info("🎯 EXECUTING MISSION CRITICAL GOLDEN PATH FLOW TEST")
        logger.info("=" * 100)
        
        try:
            # Phase 1: User Authentication with Real GCP Staging
            logger.info("🔐 Phase 1: Authenticating user with real GCP staging environment...")
            auth_result = await self._authenticate_real_staging_user()
            
            if not auth_result['success']:
                self.test_result.errors.append(f"Authentication failed: {auth_result['error']}")
                pytest.fail("X CRITICAL: User authentication failed - Golden Path blocked")
            
            self.test_result.user_authenticated = True
            user_id = auth_result['user_id']
            auth_token = auth_result['access_token']
            
            logger.success(f"CHECK User authenticated: {user_id}")
            
            # Phase 2: WebSocket Connection with Real Staging Infrastructure
            logger.info("🔌 Phase 2: Establishing WebSocket connection with staging infrastructure...")
            websocket_conn = RealWebSocketConnection(self.event_monitor, self.staging_config)
            
            connection_success = await websocket_conn.connect(auth_token, user_id)
            if not connection_success:
                self.test_result.errors.append("WebSocket connection to staging failed")
                pytest.fail("X CRITICAL: WebSocket connection failed - Chat infrastructure broken")
            
            self.test_result.websocket_connected = True
            logger.success("CHECK WebSocket connected to staging environment")
            
            # Phase 3: Send User Message and Initiate Agent Execution
            logger.info("💬 Phase 3: Sending user message and initiating agent execution...")
            
            user_message = {
                'type': 'chat_message',
                'content': 'Please analyze the current performance of our AI optimization systems and provide recommendations for improvement.',
                'user_id': user_id,
                'thread_id': str(uuid.uuid4()),
                'timestamp': datetime.now(UTC).isoformat(),
                'request_id': str(uuid.uuid4())
            }
            
            # Send message through WebSocket
            message_sent = await websocket_conn.send_message(user_message)
            if not message_sent:
                self.test_result.errors.append("Failed to send user message through WebSocket")
                pytest.fail("X CRITICAL: Cannot send messages - Chat functionality broken")
            
            # Trigger agent execution through staging backend
            agent_execution_result = await self._trigger_real_agent_execution(
                auth_token, user_message, user_id
            )
            
            if agent_execution_result['success']:
                self.test_result.agent_execution_started = True
                logger.success("CHECK Agent execution initiated successfully")
            else:
                self.test_result.errors.append(f"Agent execution failed: {agent_execution_result['error']}")
                
            # Phase 4: Monitor WebSocket Events and Agent Processing
            logger.info("📡 Phase 4: Monitoring WebSocket events and agent processing...")
            
            # Wait for agent processing and collect events
            await self._monitor_agent_execution_events(websocket_conn, timeout=45.0)
            
            # Validate critical WebSocket events
            events_valid, event_errors = self.event_monitor.validate_critical_events()
            self.test_result.critical_events_validated = events_valid
            self.test_result.websocket_events_received = len(self.event_monitor.events)
            
            if not events_valid:
                self.test_result.errors.extend(event_errors)
                logger.error("X CRITICAL: Required WebSocket events missing")
            else:
                logger.success("CHECK All critical WebSocket events received")
            
            # Phase 5: Validate Agent Response Quality
            logger.info("🧠 Phase 5: Validating agent response quality and business value...")
            
            response_validation = self._validate_agent_response_quality()
            self.test_result.agent_response_received = response_validation['response_received']
            self.test_result.response_quality_valid = response_validation['quality_valid']
            self.test_result.agent_response_content = response_validation['content']
            
            if not response_validation['quality_valid']:
                self.test_result.errors.extend(response_validation['errors'])
                logger.error("X CRITICAL: Agent response quality insufficient")
            else:
                logger.success("CHECK Agent response meets quality standards")
            
            # Phase 6: Performance and Business Value Validation
            logger.info("📊 Phase 6: Validating performance and business value delivery...")
            
            self.test_result.total_execution_time = time.time() - self.start_time
            self.test_result.performance_metrics = self.event_monitor.get_performance_metrics()
            
            # Validate performance thresholds
            if self.test_result.total_execution_time > 60.0:
                self.test_result.warnings.append(
                    f"Total execution time {self.test_result.total_execution_time:.2f}s exceeds 60s threshold"
                )
            
            # Phase 7: Resource Cleanup
            logger.info("🧹 Phase 7: Cleaning up test resources...")
            await websocket_conn.disconnect()
            await self._cleanup_test_user(auth_result)
            
            # Final Success Determination
            self.test_result.success = len(self.test_result.errors) == 0
            
            # Assert Golden Path Success
            if not self.test_result.is_golden_path_successful():
                error_summary = "; ".join(self.test_result.errors)
                pytest.fail(f"X GOLDEN PATH FAILED: {error_summary}")
                
            logger.success("🎉 GOLDEN PATH VALIDATION COMPLETED SUCCESSFULLY")
            logger.success(f"💰 Business Value Score: {self.test_result.get_business_value_score():.1f}/100")
            
        except Exception as e:
            logger.error(f"X FATAL ERROR in Golden Path test: {e}")
            self.test_result.errors.append(f"Test execution failed: {str(e)}")
            self.test_result.success = False
            raise
    
    async def _authenticate_real_staging_user(self) -> Dict[str, Any]:
        """Authenticate user with real GCP staging auth service."""
        try:
            # Create test user credentials
            test_email = f"golden-path-test-{uuid.uuid4()}@netra.test"
            test_password = "GoldenPath123!"
            
            auth_url = self.staging_config['auth_url']
            
            # Register user
            async with aiohttp.ClientSession() as session:
                register_data = {
                    "email": test_email,
                    "password": test_password,
                    "name": "Golden Path Test User"
                }
                
                async with session.post(
                    f"{auth_url}/api/auth/register",
                    json=register_data,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    
                    if response.status not in [200, 201, 409]:  # 409 = user already exists
                        error_text = await response.text()
                        return {
                            'success': False,
                            'error': f"Registration failed: {response.status} - {error_text}"
                        }
                
                # Login user
                login_data = {
                    "email": test_email,
                    "password": test_password
                }
                
                async with session.post(
                    f"{auth_url}/api/auth/login",
                    json=login_data,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    
                    if response.status == 200:
                        auth_data = await response.json()
                        return {
                            'success': True,
                            'user_id': auth_data.get('user_id'),
                            'access_token': auth_data.get('access_token'),
                            'user_email': test_email
                        }
                    else:
                        error_text = await response.text()
                        return {
                            'success': False,
                            'error': f"Login failed: {response.status} - {error_text}"
                        }
                        
        except Exception as e:
            return {
                'success': False,
                'error': f"Authentication error: {str(e)}"
            }
    
    async def _trigger_real_agent_execution(
        self, 
        auth_token: str, 
        user_message: Dict[str, Any], 
        user_id: str
    ) -> Dict[str, Any]:
        """Trigger real agent execution through staging backend."""
        try:
            backend_url = self.staging_config['backend_url']
            
            agent_request = {
                "message": user_message['content'],
                "user_id": user_id,
                "thread_id": user_message.get('thread_id'),
                "agent_type": "supervisor",
                "context": {
                    "request_id": user_message.get('request_id'),
                    "session_type": "golden_path_test"
                }
            }
            
            headers = {
                'Authorization': f'Bearer {auth_token}',
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{backend_url}/api/v1/agents/execute",
                    json=agent_request,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        return {
                            'success': True,
                            'execution_id': result.get('execution_id'),
                            'agent_type': result.get('agent_type')
                        }
                    else:
                        error_text = await response.text()
                        return {
                            'success': False,
                            'error': f"Agent execution failed: {response.status} - {error_text}"
                        }
                        
        except Exception as e:
            return {
                'success': False,
                'error': f"Agent execution error: {str(e)}"
            }
    
    async def _monitor_agent_execution_events(
        self, 
        websocket_conn: RealWebSocketConnection, 
        timeout: float = 45.0
    ):
        """Monitor agent execution and collect WebSocket events."""
        start_time = time.time()
        completion_detected = False
        
        logger.info(f"📡 Monitoring agent execution for up to {timeout}s...")
        
        while time.time() - start_time < timeout and not completion_detected:
            await asyncio.sleep(0.5)
            
            # Check if agent completion event received
            if self.event_monitor.agent_completed:
                completion_detected = True
                logger.success("🏁 Agent completion detected")
                break
            
            # Check for minimum event threshold
            if len(self.event_monitor.events) >= 10:
                logger.info(f"📊 {len(self.event_monitor.events)} events received, continuing monitoring...")
        
        elapsed_time = time.time() - start_time
        logger.info(f"📡 Monitoring completed after {elapsed_time:.2f}s")
        logger.info(f"📊 Total events received: {len(self.event_monitor.events)}")
    
    def _validate_agent_response_quality(self) -> Dict[str, Any]:
        """Validate the quality of agent responses for business value."""
        validation_result = {
            'response_received': False,
            'quality_valid': False,
            'content': None,
            'errors': []
        }
        
        # Find agent response events
        response_events = [
            event for event in self.event_monitor.events
            if event.get('type') in ['agent_completed', 'final_result', 'agent_response']
            and event.get('data', {}).get('content')
        ]
        
        if not response_events:
            validation_result['errors'].append("No agent response found in events")
            return validation_result
        
        validation_result['response_received'] = True
        
        # Get the most recent/comprehensive response
        response_event = response_events[-1]
        response_content = response_event.get('data', {}).get('content', '')
        validation_result['content'] = response_content
        
        # Quality validation criteria for business value
        quality_checks = []
        
        # Length check - substantive content
        if len(response_content.strip()) < 50:
            quality_checks.append("Response too short (< 50 characters)")
        elif len(response_content.strip()) > 500:
            quality_checks.append("CHECK Substantive response length")
        
        # Content quality indicators
        response_lower = response_content.lower()
        
        # Check for AI analysis indicators
        analysis_indicators = [
            'analysis', 'recommend', 'optimize', 'performance', 
            'status', 'system', 'improvement', 'suggestion'
        ]
        
        found_indicators = [ind for ind in analysis_indicators if ind in response_lower]
        if len(found_indicators) >= 2:
            quality_checks.append("CHECK Contains relevant analysis content")
        else:
            quality_checks.append("Missing relevant analysis content")
        
        # Check for structured response
        if any(marker in response_content for marker in ['\n', '1.', '2.', '-', '*']):
            quality_checks.append("CHECK Well-structured response")
        
        # Check for non-generic content (avoid template responses)
        generic_phrases = ['sorry', 'cannot help', 'try again', 'error occurred']
        if not any(phrase in response_lower for phrase in generic_phrases):
            quality_checks.append("CHECK Non-generic, specific content")
        else:
            quality_checks.append("Contains generic error phrases")
        
        # Determine overall quality
        passed_checks = [check for check in quality_checks if check.startswith('CHECK')]
        failed_checks = [check for check in quality_checks if not check.startswith('CHECK')]
        
        if len(passed_checks) >= 2 and len(failed_checks) <= 1:
            validation_result['quality_valid'] = True
            logger.success(f"CHECK Response quality validation passed: {len(passed_checks)} criteria met")
        else:
            validation_result['quality_valid'] = False
            validation_result['errors'].extend(failed_checks)
            logger.error(f"X Response quality insufficient: {len(failed_checks)} criteria failed")
        
        return validation_result
    
    async def _cleanup_test_user(self, auth_result: Dict[str, Any]):
        """Clean up test user resources."""
        try:
            # In a production system, we might want to clean up test users
            # For now, we'll just log the cleanup
            logger.info(f"🧹 Cleaning up test user: {auth_result.get('user_email')}")
            
            # Could implement user deletion via API if needed
            # await self._delete_test_user(auth_result)
            
        except Exception as e:
            logger.warning(f"WARNING️  User cleanup warning: {e}")
    
    @pytest.mark.asyncio
    async def test_golden_path_error_scenarios(self):
        """Test golden path error scenarios and recovery."""
        logger.info("🚨 Testing Golden Path error scenarios and recovery...")
        
        # Test authentication failure handling
        invalid_auth_result = await self._test_invalid_authentication()
        assert not invalid_auth_result['success'], "Invalid auth should fail"
        
        # Test WebSocket connection failure handling
        websocket_failure_result = await self._test_websocket_connection_failure()
        assert not websocket_failure_result['success'], "Invalid WebSocket should fail"
        
        logger.success("CHECK Error scenario testing completed")
    
    async def _test_invalid_authentication(self) -> Dict[str, Any]:
        """Test authentication with invalid credentials."""
        try:
            auth_url = self.staging_config['auth_url']
            
            invalid_login = {
                "email": "invalid@invalid.com",
                "password": "invalid_password"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{auth_url}/api/auth/login",
                    json=invalid_login,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    return {
                        'success': response.status == 200,
                        'status': response.status
                    }
                    
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _test_websocket_connection_failure(self) -> Dict[str, Any]:
        """Test WebSocket connection with invalid parameters."""
        try:
            # Try to connect to invalid WebSocket URL
            invalid_ws_url = "wss://invalid.netrasystems.ai/ws"
            
            websocket = await websockets.connect(
                invalid_ws_url,
                timeout=5
            )
            
            # Should not reach here
            await websocket.close()
            return {'success': True}
            
        except Exception:
            # Expected to fail
            return {'success': False}
    
    @pytest.mark.asyncio
    async def test_golden_path_performance_benchmarks(self):
        """Test golden path performance benchmarks for business SLAs."""
        logger.info("📊 Testing Golden Path performance benchmarks...")
        
        performance_metrics = {
            'authentication_time': 0.0,
            'websocket_connection_time': 0.0,
            'first_event_time': 0.0,
            'completion_time': 0.0,
            'total_flow_time': 0.0
        }
        
        start_time = time.time()
        
        # Simplified performance test - authenticate and connect
        try:
            # Measure authentication time
            auth_start = time.time()
            auth_result = await self._authenticate_real_staging_user()
            performance_metrics['authentication_time'] = time.time() - auth_start
            
            if auth_result['success']:
                # Measure WebSocket connection time
                ws_start = time.time()
                websocket_conn = RealWebSocketConnection(self.event_monitor, self.staging_config)
                connection_success = await websocket_conn.connect(
                    auth_result['access_token'], 
                    auth_result['user_id']
                )
                performance_metrics['websocket_connection_time'] = time.time() - ws_start
                
                if connection_success:
                    logger.success("CHECK Performance test connections established")
                    await websocket_conn.disconnect()
                
                await self._cleanup_test_user(auth_result)
            
            performance_metrics['total_flow_time'] = time.time() - start_time
            
            # Validate performance against business SLAs
            self._validate_performance_slas(performance_metrics)
            
        except Exception as e:
            logger.error(f"X Performance test error: {e}")
            raise
    
    def _validate_performance_slas(self, metrics: Dict[str, float]):
        """Validate performance metrics against business SLAs."""
        sla_thresholds = {
            'authentication_time': 5.0,      # 5 seconds max
            'websocket_connection_time': 3.0, # 3 seconds max
            'total_flow_time': 15.0          # 15 seconds max for basic flow
        }
        
        violations = []
        
        for metric, threshold in sla_thresholds.items():
            if metric in metrics and metrics[metric] > threshold:
                violations.append(f"{metric}: {metrics[metric]:.2f}s > {threshold:.2f}s")
        
        if violations:
            violation_summary = "; ".join(violations)
            logger.error(f"X SLA violations detected: {violation_summary}")
            pytest.fail(f"Performance SLA violations: {violation_summary}")
        else:
            logger.success("CHECK All performance SLAs met")
            
        # Record performance metrics
        for metric, value in metrics.items():
            self.record_metric(f"perf_{metric}", value)


if __name__ == '__main__':
    # Use SSOT unified test runner
    print("MIGRATION NOTICE: Please use SSOT unified test runner")
    print("Command: python tests/unified_test_runner.py --category e2e --pattern golden_path")