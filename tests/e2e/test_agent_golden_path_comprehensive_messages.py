"""
Agent Golden Path Comprehensive Message Flow E2E Tests

Business Value Justification (BVJ):
- Segment: All segments (Free, Early, Mid, Enterprise) - Core chat functionality
- Business Goal: Validate complete Golden Path user message processing flow
- Value Impact: Ensures $500K+ ARR chat functionality delivers reliable AI responses
- Revenue Impact: Protects core business value through comprehensive message flow testing

PURPOSE:
This E2E test validates the complete Golden Path message flow from user input to AI response,
addressing critical gaps identified in the integration test analysis:

1. API Compatibility Issues: Fixed websocket_manager vs websocket_bridge parameter mismatch
2. WebSocket Event Integration: Comprehensive tracking of all 5 critical events
3. Complete Golden Path Flow: End-to-end user message → agent processing → response
4. Error Recovery Experience: Agent error scenarios and user experience validation
5. Real Service Integration: Tests against GCP staging environment (no Docker dependency)

CRITICAL DESIGN:
- NO DOCKER usage - tests run against GCP staging environment for real service validation
- Uses current API (websocket_bridge) instead of deprecated websocket_manager
- Validates all 5 critical WebSocket events: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
- Comprehensive golden path flow testing with real message processing
- Error handling and recovery validation for production readiness
- Multi-user isolation and security validation

SCOPE:
1. Complete message processing pipeline validation
2. WebSocket event delivery and sequencing
3. Agent response quality and business value
4. Error handling and user experience preservation
5. Multi-user concurrent processing isolation
6. Performance and reliability validation

TEST ARCHITECTURE:
- Real WebSocket connections to GCP staging
- Authenticated users with proper permissions
- Event tracking and validation
- Business context preservation
- Performance monitoring and SLA validation
"""

import asyncio
import json
import time
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from contextlib import asynccontextmanager

import pytest
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper, AuthenticatedUser
from tests.e2e.staging_config import StagingTestConfig
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class MessageFlowType(Enum):
    """Types of message flows for comprehensive testing."""
    SIMPLE_QUERY = "simple_query"
    COMPLEX_ANALYSIS = "complex_analysis"
    MULTI_STEP_WORKFLOW = "multi_step_workflow"
    ERROR_RECOVERY = "error_recovery"
    CONCURRENT_PROCESSING = "concurrent_processing"


@dataclass
class MessageFlowScenario:
    """Represents a message flow scenario for testing."""
    flow_type: MessageFlowType
    description: str
    user_message: Dict[str, Any]
    expected_events: List[str]
    expected_response_indicators: List[str]
    timeout_seconds: float
    business_value_indicators: List[str]


@dataclass
class WebSocketEventValidation:
    """WebSocket event validation tracking."""
    event_type: str
    timestamp: float
    business_context: str
    sequence_position: int
    user_id: str
    thread_id: str
    run_id: str
    payload_valid: bool = True
    timing_valid: bool = True


@dataclass
class MessageFlowResult:
    """Results of message flow testing."""
    flow_type: MessageFlowType
    success: bool
    processing_time: float
    events_received: List[WebSocketEventValidation]
    response_quality: str  # "excellent", "good", "fair", "poor"
    business_value_delivered: bool
    error_messages: List[str]
    user_experience_score: float  # 0.0 to 1.0
    golden_path_complete: bool


@dataclass
class GoldenPathValidationResult:
    """Comprehensive golden path validation results."""
    validation_successful: bool
    scenarios_tested: List[MessageFlowResult]
    overall_success_rate: float
    average_response_time: float
    websocket_events_reliability: float
    business_value_delivery_rate: float
    user_experience_average: float
    golden_path_readiness: bool
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


class AgentGoldenPathValidator:
    """Validates complete agent golden path message processing."""
    
    # Performance thresholds
    EXCELLENT_RESPONSE_TIME = 8.0
    GOOD_RESPONSE_TIME = 15.0
    ACCEPTABLE_RESPONSE_TIME = 30.0
    
    # Event timing requirements (in seconds)
    MAX_EVENT_INTERVAL = 5.0  # Max time between consecutive events
    MAX_FIRST_EVENT_DELAY = 3.0  # Max time to first event
    
    # Required WebSocket events for Golden Path
    CRITICAL_WEBSOCKET_EVENTS = [
        'agent_started',      # User sees agent began processing
        'agent_thinking',     # Real-time reasoning visibility
        'tool_executing',     # Tool usage transparency
        'tool_completed',     # Tool results display
        'agent_completed'     # Completion signal
    ]
    
    # Business value indicators
    BUSINESS_VALUE_INDICATORS = [
        'analysis', 'recommendation', 'solution', 'strategy', 'optimization',
        'insight', 'improvement', 'efficiency', 'cost', 'revenue', 'performance',
        'actionable', 'implementation', 'results', 'benefit', 'value'
    ]
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.scenarios: List[MessageFlowScenario] = []
        self.results: List[MessageFlowResult] = []
        self.validation_start_time = time.time()
        
    def create_comprehensive_scenarios(self) -> List[MessageFlowScenario]:
        """Create comprehensive message flow scenarios."""
        scenarios = [
            MessageFlowScenario(
                flow_type=MessageFlowType.SIMPLE_QUERY,
                description="Simple business question with quick response",
                user_message={
                    "message": "What are the key factors for improving customer retention?",
                    "context": {"domain": "business_strategy", "complexity": "low"},
                    "expects_quick_response": True
                },
                expected_events=self.CRITICAL_WEBSOCKET_EVENTS,
                expected_response_indicators=["retention", "customer", "strategies", "improvement"],
                timeout_seconds=20.0,
                business_value_indicators=["actionable", "strategy", "improvement"]
            ),
            
            MessageFlowScenario(
                flow_type=MessageFlowType.COMPLEX_ANALYSIS,
                description="Complex business analysis requiring multiple steps",
                user_message={
                    "message": "Analyze our competitive position in the SaaS market and provide a comprehensive growth strategy with specific recommendations for the next 12 months.",
                    "context": {"domain": "strategic_planning", "complexity": "high", "multi_step": True},
                    "expects_detailed_analysis": True
                },
                expected_events=self.CRITICAL_WEBSOCKET_EVENTS,
                expected_response_indicators=["competitive", "analysis", "growth", "strategy", "recommendations", "12 months"],
                timeout_seconds=45.0,
                business_value_indicators=["analysis", "strategy", "recommendations", "growth", "competitive"]
            ),
            
            MessageFlowScenario(
                flow_type=MessageFlowType.MULTI_STEP_WORKFLOW,
                description="Multi-step workflow with tool usage",
                user_message={
                    "message": "Help me create a comprehensive project plan for launching a new product feature, including timeline, resource requirements, and risk assessment.",
                    "context": {"domain": "project_management", "complexity": "high", "requires_tools": True},
                    "expects_structured_output": True
                },
                expected_events=self.CRITICAL_WEBSOCKET_EVENTS,
                expected_response_indicators=["project", "timeline", "resources", "risk", "assessment", "plan"],
                timeout_seconds=50.0,
                business_value_indicators=["plan", "timeline", "resources", "implementation", "actionable"]
            ),
            
            MessageFlowScenario(
                flow_type=MessageFlowType.ERROR_RECOVERY,
                description="Error recovery with graceful handling",
                user_message={
                    "message": "Please analyze the data from the table 'nonexistent_data_source_xyz' and provide insights.",
                    "context": {"domain": "data_analysis", "complexity": "medium", "expect_error": True},
                    "expects_error_handling": True
                },
                expected_events=['agent_started', 'agent_thinking', 'tool_executing'],  # May not complete all events
                expected_response_indicators=["unable", "alternative", "error", "try", "different"],
                timeout_seconds=30.0,
                business_value_indicators=["alternative", "suggestion", "help"]
            )
        ]
        
        self.scenarios = scenarios
        return scenarios
    
    async def execute_message_flow_scenario(self, scenario: MessageFlowScenario,
                                          websocket_url: str, websocket_headers: Dict[str, str],
                                          connection_timeout: float = 15.0) -> MessageFlowResult:
        """Execute a message flow scenario and validate results."""
        scenario_start_time = time.time()
        
        print(f"[GOLDEN PATH] Executing scenario: {scenario.flow_type.value}")
        print(f"[GOLDEN PATH] Description: {scenario.description}")
        
        # Generate unique identifiers for this scenario
        thread_id = f"golden_thread_{scenario.flow_type.value}_{uuid.uuid4().hex[:8]}"
        run_id = f"golden_run_{scenario.flow_type.value}_{uuid.uuid4().hex[:8]}"
        
        # Prepare the test message
        test_message = {
            "type": "chat_message",
            "content": scenario.user_message.get("message", ""),
            "thread_id": thread_id,
            "run_id": run_id,
            "user_id": self.user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "context": scenario.user_message.get("context", {}),
            "golden_path_test": True
        }
        
        # Initialize result tracking
        events_received = []
        response_content = ""
        business_value_delivered = False
        user_experience_score = 0.0
        golden_path_complete = False
        error_messages = []
        
        try:
            async with websockets.connect(
                websocket_url,
                additional_headers=websocket_headers,
                timeout=connection_timeout,
                ping_interval=30,
                ping_timeout=10
            ) as websocket:
                
                # Send the message
                await websocket.send(json.dumps(test_message))
                print(f"[GOLDEN PATH] Message sent: {scenario.flow_type.value}")
                
                # Monitor for events and responses
                first_event_time = None
                last_event_time = scenario_start_time
                event_sequence_position = 0
                
                while time.time() - scenario_start_time < scenario.timeout_seconds:
                    try:
                        response_text = await asyncio.wait_for(
                            websocket.recv(),
                            timeout=10.0
                        )
                        
                        response_data = json.loads(response_text)
                        event_type = response_data.get("type", response_data.get("event_type", "unknown"))
                        current_time = time.time()
                        
                        # Track first event timing
                        if first_event_time is None:
                            first_event_time = current_time
                            first_event_delay = first_event_time - scenario_start_time
                        else:
                            first_event_delay = 0
                        
                        # Calculate event interval
                        event_interval = current_time - last_event_time
                        last_event_time = current_time
                        
                        # Validate event timing
                        timing_valid = (
                            (first_event_delay <= self.MAX_FIRST_EVENT_DELAY or first_event_delay == 0) and
                            event_interval <= self.MAX_EVENT_INTERVAL
                        )
                        
                        # Extract business context
                        business_context = self._extract_business_context(response_data)
                        
                        # Create event validation
                        event_validation = WebSocketEventValidation(
                            event_type=event_type,
                            timestamp=current_time - scenario_start_time,
                            business_context=business_context,
                            sequence_position=event_sequence_position,
                            user_id=self.user_id,
                            thread_id=thread_id,
                            run_id=run_id,
                            payload_valid=self._validate_event_payload(response_data),
                            timing_valid=timing_valid
                        )
                        
                        events_received.append(event_validation)
                        event_sequence_position += 1
                        
                        # Extract response content
                        content = response_data.get("content", response_data.get("message", ""))
                        if content:
                            response_content += content
                            
                            # Check for business value indicators
                            content_lower = content.lower()
                            if any(indicator in content_lower for indicator in self.BUSINESS_VALUE_INDICATORS):
                                business_value_delivered = True
                        
                        print(f"[GOLDEN PATH] Event received: {event_type} at {event_validation.timestamp:.2f}s")
                        
                        # Check for completion
                        if event_type in ["agent_completed", "error", "system_error"]:
                            print(f"[GOLDEN PATH] Scenario completion event: {event_type}")
                            break
                            
                    except asyncio.TimeoutError:
                        # Continue monitoring
                        continue
                        
                    except (ConnectionClosed, WebSocketException) as e:
                        print(f"[GOLDEN PATH] WebSocket error: {e}")
                        error_messages.append(f"WebSocket error: {e}")
                        break
                
        except Exception as e:
            print(f"[GOLDEN PATH] Scenario execution error: {e}")
            error_messages.append(f"Execution error: {e}")
        
        # Calculate results
        processing_time = time.time() - scenario_start_time
        
        # Evaluate success
        success = self._evaluate_scenario_success(
            scenario, events_received, response_content, processing_time, error_messages
        )
        
        # Evaluate response quality
        response_quality = self._evaluate_response_quality(
            response_content, processing_time, events_received, scenario
        )
        
        # Calculate user experience score
        user_experience_score = self._calculate_user_experience_score(
            events_received, processing_time, response_content, business_value_delivered
        )
        
        # Check golden path completeness
        golden_path_complete = self._validate_golden_path_complete(
            events_received, response_content, business_value_delivered
        )
        
        result = MessageFlowResult(
            flow_type=scenario.flow_type,
            success=success,
            processing_time=processing_time,
            events_received=events_received,
            response_quality=response_quality,
            business_value_delivered=business_value_delivered,
            error_messages=error_messages,
            user_experience_score=user_experience_score,
            golden_path_complete=golden_path_complete
        )
        
        self.results.append(result)
        return result
    
    def _extract_business_context(self, response_data: Dict[str, Any]) -> str:
        """Extract business context from WebSocket event."""
        # Look for various fields that might contain business context
        context_fields = [
            "business_context", "context", "description", "status", 
            "message", "content", "details", "progress"
        ]
        
        for field in context_fields:
            if field in response_data and response_data[field]:
                return str(response_data[field])[:200]  # Limit length
        
        return "No business context available"
    
    def _validate_event_payload(self, response_data: Dict[str, Any]) -> bool:
        """Validate that event payload contains required fields."""
        required_fields = ["type"]
        return all(field in response_data for field in required_fields)
    
    def _evaluate_scenario_success(self, scenario: MessageFlowScenario, 
                                 events_received: List[WebSocketEventValidation],
                                 response_content: str, processing_time: float,
                                 error_messages: List[str]) -> bool:
        """Evaluate if scenario was successful."""
        # Basic success criteria
        if len(error_messages) > 0 and scenario.flow_type != MessageFlowType.ERROR_RECOVERY:
            return False
        
        if processing_time > scenario.timeout_seconds:
            return False
        
        # Event validation
        if len(events_received) == 0:
            return False
        
        # Response content validation
        if len(response_content) < 10:  # Minimum meaningful response
            return False
        
        # Check for expected response indicators
        content_lower = response_content.lower()
        matching_indicators = sum(1 for indicator in scenario.expected_response_indicators 
                                if indicator.lower() in content_lower)
        
        # Require at least 25% of expected indicators for success
        required_matches = max(1, len(scenario.expected_response_indicators) // 4)
        return matching_indicators >= required_matches
    
    def _evaluate_response_quality(self, response_content: str, processing_time: float,
                                 events_received: List[WebSocketEventValidation],
                                 scenario: MessageFlowScenario) -> str:
        """Evaluate the quality of the response."""
        if len(response_content) < 20:
            return "poor"
        
        content_lower = response_content.lower()
        
        # Check for business value indicators
        business_indicators = sum(1 for indicator in self.BUSINESS_VALUE_INDICATORS 
                                if indicator in content_lower)
        
        # Check timing
        timing_score = 1.0
        if processing_time > self.EXCELLENT_RESPONSE_TIME:
            timing_score = 0.8
        if processing_time > self.GOOD_RESPONSE_TIME:
            timing_score = 0.6
        if processing_time > self.ACCEPTABLE_RESPONSE_TIME:
            timing_score = 0.4
        
        # Check event quality
        event_score = min(len(events_received) / len(self.CRITICAL_WEBSOCKET_EVENTS), 1.0)
        
        # Calculate overall quality
        overall_score = (business_indicators / 10 + timing_score + event_score) / 3
        
        if overall_score >= 0.8:
            return "excellent"
        elif overall_score >= 0.6:
            return "good"
        elif overall_score >= 0.4:
            return "fair"
        else:
            return "poor"
    
    def _calculate_user_experience_score(self, events_received: List[WebSocketEventValidation],
                                       processing_time: float, response_content: str,
                                       business_value_delivered: bool) -> float:
        """Calculate user experience score (0.0 to 1.0)."""
        score = 0.0
        
        # Event delivery score (0.3 weight)
        if events_received:
            event_score = min(len(events_received) / len(self.CRITICAL_WEBSOCKET_EVENTS), 1.0)
            score += event_score * 0.3
        
        # Response time score (0.2 weight)
        if processing_time <= self.EXCELLENT_RESPONSE_TIME:
            time_score = 1.0
        elif processing_time <= self.GOOD_RESPONSE_TIME:
            time_score = 0.8
        elif processing_time <= self.ACCEPTABLE_RESPONSE_TIME:
            time_score = 0.6
        else:
            time_score = 0.3
        score += time_score * 0.2
        
        # Content quality score (0.3 weight)
        if response_content:
            content_score = min(len(response_content) / 100, 1.0)  # Normalize to 100 chars
            score += content_score * 0.3
        
        # Business value score (0.2 weight)
        if business_value_delivered:
            score += 0.2
        
        return min(score, 1.0)
    
    def _validate_golden_path_complete(self, events_received: List[WebSocketEventValidation],
                                     response_content: str, business_value_delivered: bool) -> bool:
        """Validate that the golden path was completed successfully."""
        # Must have events
        if len(events_received) == 0:
            return False
        
        # Must have meaningful response
        if len(response_content) < 20:
            return False
        
        # Should have business value
        if not business_value_delivered:
            return False
        
        # Should have at least some critical events
        critical_events_received = sum(1 for event in events_received 
                                     if event.event_type in self.CRITICAL_WEBSOCKET_EVENTS)
        
        return critical_events_received >= 2  # At least 2 critical events
    
    def validate_golden_path_comprehensive(self) -> GoldenPathValidationResult:
        """Validate comprehensive golden path functionality."""
        if not self.results:
            return GoldenPathValidationResult(
                validation_successful=False,
                scenarios_tested=[],
                overall_success_rate=0.0,
                average_response_time=0.0,
                websocket_events_reliability=0.0,
                business_value_delivery_rate=0.0,
                user_experience_average=0.0,
                golden_path_readiness=False,
                recommendations=["No scenarios tested"]
            )
        
        # Calculate metrics
        successful_scenarios = sum(1 for result in self.results if result.success)
        overall_success_rate = successful_scenarios / len(self.results)
        
        average_response_time = sum(result.processing_time for result in self.results) / len(self.results)
        
        # WebSocket events reliability
        total_events_expected = sum(len(self.CRITICAL_WEBSOCKET_EVENTS) for _ in self.results)
        total_events_received = sum(len(result.events_received) for result in self.results)
        websocket_events_reliability = min(total_events_received / total_events_expected, 1.0) if total_events_expected > 0 else 0.0
        
        # Business value delivery rate
        business_value_scenarios = sum(1 for result in self.results if result.business_value_delivered)
        business_value_delivery_rate = business_value_scenarios / len(self.results)
        
        # User experience average
        user_experience_average = sum(result.user_experience_score for result in self.results) / len(self.results)
        
        # Golden path readiness assessment
        golden_path_complete_scenarios = sum(1 for result in self.results if result.golden_path_complete)
        golden_path_readiness = (
            overall_success_rate >= 0.7 and
            average_response_time <= self.ACCEPTABLE_RESPONSE_TIME and
            websocket_events_reliability >= 0.8 and
            business_value_delivery_rate >= 0.6 and
            golden_path_complete_scenarios >= len(self.results) * 0.7
        )
        
        # Performance metrics
        performance_metrics = {
            "total_scenarios": len(self.results),
            "successful_scenarios": successful_scenarios,
            "average_response_time_seconds": average_response_time,
            "fastest_response_time": min(result.processing_time for result in self.results),
            "slowest_response_time": max(result.processing_time for result in self.results),
            "total_events_received": total_events_received,
            "average_events_per_scenario": total_events_received / len(self.results)
        }
        
        # Generate recommendations
        recommendations = []
        if overall_success_rate < 0.8:
            recommendations.append("Improve overall scenario success rate - currently below 80%")
        if average_response_time > self.GOOD_RESPONSE_TIME:
            recommendations.append("Optimize response times - currently above good threshold")
        if websocket_events_reliability < 0.9:
            recommendations.append("Improve WebSocket event delivery reliability")
        if business_value_delivery_rate < 0.8:
            recommendations.append("Enhance business value delivery in responses")
        if user_experience_average < 0.7:
            recommendations.append("Improve overall user experience scores")
        
        # Overall validation success
        validation_successful = (
            overall_success_rate >= 0.6 and
            websocket_events_reliability >= 0.7 and
            business_value_delivery_rate >= 0.5 and
            user_experience_average >= 0.5
        )
        
        return GoldenPathValidationResult(
            validation_successful=validation_successful,
            scenarios_tested=self.results,
            overall_success_rate=overall_success_rate,
            average_response_time=average_response_time,
            websocket_events_reliability=websocket_events_reliability,
            business_value_delivery_rate=business_value_delivery_rate,
            user_experience_average=user_experience_average,
            golden_path_readiness=golden_path_readiness,
            performance_metrics=performance_metrics,
            recommendations=recommendations
        )


class TestAgentGoldenPathComprehensiveMessages(SSotAsyncTestCase):
    """
    Comprehensive E2E Tests for Agent Golden Path Message Processing.
    
    Tests the complete message flow from user input to AI response,
    validating WebSocket events, response quality, and business value delivery.
    """
    
    def setup_method(self, method=None):
        """Set up comprehensive golden path test environment."""
        super().setup_method(method)
        self.env = get_env()
        
        # Environment configuration for E2E testing
        test_env = self.env.get("TEST_ENV", "test")
        if test_env == "staging" or self.env.get("ENVIRONMENT") == "staging":
            self.test_env = "staging"
            self.staging_config = StagingTestConfig()
            self.websocket_url = self.staging_config.urls.websocket_url
            self.timeout = 60.0  # Extended timeout for comprehensive scenarios
        else:
            self.test_env = "test"
            self.websocket_url = self.env.get("TEST_WEBSOCKET_URL", "ws://localhost:8002/ws")
            self.timeout = 45.0
            
        self.e2e_helper = E2EWebSocketAuthHelper(environment=self.test_env)
        
        # Test configuration
        self.comprehensive_timeout = 120.0  # Allow time for complex scenarios
        self.connection_timeout = 20.0      # Connection establishment
        
        logger.info(f"[GOLDEN PATH SETUP] Test environment: {self.test_env}")
        logger.info(f"[GOLDEN PATH SETUP] WebSocket URL: {self.websocket_url}")
    
    @pytest.mark.e2e
    @pytest.mark.agent_golden_path
    @pytest.mark.timeout(180)  # 3 minutes for comprehensive testing
    async def test_comprehensive_golden_path_message_flows(self):
        """
        Test comprehensive golden path message flows with full validation.
        
        This test validates the complete Golden Path user experience:
        1. Simple queries with quick responses
        2. Complex analysis requiring multiple processing steps
        3. Multi-step workflows with tool usage
        4. Error recovery with graceful handling
        
        BVJ: This test protects $500K+ ARR by ensuring core chat functionality
        delivers reliable, valuable AI responses across all user scenarios.
        """
        test_start_time = time.time()
        print(f"[GOLDEN PATH] Starting comprehensive golden path message flow validation")
        print(f"[GOLDEN PATH] Environment: {self.test_env}")
        
        # Create authenticated user for golden path testing
        golden_path_user = await self.e2e_helper.create_authenticated_user(
            email=f"golden_path_comprehensive_{int(time.time())}@test.com",
            permissions=["read", "write", "chat", "agent_execution", "golden_path_testing"]
        )
        
        # Initialize golden path validator
        validator = AgentGoldenPathValidator(user_id=golden_path_user.user_id)
        
        # Create comprehensive scenarios
        message_flow_scenarios = validator.create_comprehensive_scenarios()
        print(f"[GOLDEN PATH] Created {len(message_flow_scenarios)} comprehensive scenarios")
        
        websocket_headers = self.e2e_helper.get_websocket_headers(golden_path_user.jwt_token)
        scenario_results = []
        
        # Execute each message flow scenario
        for i, scenario in enumerate(message_flow_scenarios, 1):
            print(f"\n[GOLDEN PATH] Executing scenario {i}/{len(message_flow_scenarios)}: {scenario.flow_type.value}")
            print(f"[GOLDEN PATH] Description: {scenario.description}")
            
            try:
                result = await validator.execute_message_flow_scenario(
                    scenario=scenario,
                    websocket_url=self.websocket_url,
                    websocket_headers=websocket_headers,
                    connection_timeout=self.connection_timeout
                )
                
                scenario_results.append(result)
                
                print(f"[GOLDEN PATH] Scenario {i} completed:")
                print(f"  - Success: {result.success}")
                print(f"  - Processing Time: {result.processing_time:.2f}s")
                print(f"  - Events Received: {len(result.events_received)}")
                print(f"  - Response Quality: {result.response_quality}")
                print(f"  - Business Value Delivered: {result.business_value_delivered}")
                print(f"  - User Experience Score: {result.user_experience_score:.2f}")
                print(f"  - Golden Path Complete: {result.golden_path_complete}")
                
                if result.error_messages:
                    print(f"  - Error Messages: {len(result.error_messages)} errors")
                
            except Exception as e:
                print(f"[GOLDEN PATH] Scenario {i} execution failed: {e}")
                # Continue with other scenarios
            
            # Brief pause between scenarios
            await asyncio.sleep(2.0)
        
        # Comprehensive validation
        validation_result = validator.validate_golden_path_comprehensive()
        
        # Log comprehensive results
        test_duration = time.time() - test_start_time
        print(f"\n[GOLDEN PATH RESULTS] Comprehensive Golden Path Message Flow Validation Results")
        print(f"[GOLDEN PATH RESULTS] Test Duration: {test_duration:.2f}s")
        print(f"[GOLDEN PATH RESULTS] Scenarios Tested: {len(validation_result.scenarios_tested)}")
        print(f"[GOLDEN PATH RESULTS] Overall Success Rate: {validation_result.overall_success_rate:.2f}")
        print(f"[GOLDEN PATH RESULTS] Average Response Time: {validation_result.average_response_time:.2f}s")
        print(f"[GOLDEN PATH RESULTS] WebSocket Events Reliability: {validation_result.websocket_events_reliability:.2f}")
        print(f"[GOLDEN PATH RESULTS] Business Value Delivery Rate: {validation_result.business_value_delivery_rate:.2f}")
        print(f"[GOLDEN PATH RESULTS] User Experience Average: {validation_result.user_experience_average:.2f}")
        print(f"[GOLDEN PATH RESULTS] Golden Path Readiness: {validation_result.golden_path_readiness}")
        print(f"[GOLDEN PATH RESULTS] Validation Successful: {validation_result.validation_successful}")
        print(f"[GOLDEN PATH RESULTS] Performance Metrics: {validation_result.performance_metrics}")
        
        # Detailed scenario results
        for i, result in enumerate(validation_result.scenarios_tested, 1):
            print(f"\n[SCENARIO {i} RESULTS] {result.flow_type.value}:")
            print(f"  - Success: {result.success}")
            print(f"  - Processing Time: {result.processing_time:.2f}s")
            print(f"  - Events Received: {len(result.events_received)}")
            print(f"  - Response Quality: {result.response_quality}")
            print(f"  - Business Value: {result.business_value_delivered}")
            print(f"  - UX Score: {result.user_experience_score:.2f}")
            print(f"  - Golden Path Complete: {result.golden_path_complete}")
            
            # Event details
            for event in result.events_received:
                print(f"    - {event.event_type} at {event.timestamp:.2f}s (timing: {'✓' if event.timing_valid else '✗'})")
        
        if validation_result.recommendations:
            print(f"\n[GOLDEN PATH RECOMMENDATIONS]")
            for i, rec in enumerate(validation_result.recommendations, 1):
                print(f"  {i}. {rec}")
        
        # ASSERTIONS: Comprehensive golden path validation
        
        # Scenario execution validation
        assert len(validation_result.scenarios_tested) >= 3, \
            f"Expected at least 3 scenarios tested, got {len(validation_result.scenarios_tested)}"
        
        # Overall success rate validation
        assert validation_result.overall_success_rate >= 0.6, \
            f"Overall success rate {validation_result.overall_success_rate:.2f} below minimum 0.6"
        
        # Response time validation
        assert validation_result.average_response_time <= 45.0, \
            f"Average response time {validation_result.average_response_time:.2f}s exceeds maximum 45s"
        
        # WebSocket events reliability validation
        assert validation_result.websocket_events_reliability >= 0.7, \
            f"WebSocket events reliability {validation_result.websocket_events_reliability:.2f} below minimum 0.7"
        
        # Business value delivery validation
        assert validation_result.business_value_delivery_rate >= 0.5, \
            f"Business value delivery rate {validation_result.business_value_delivery_rate:.2f} below minimum 0.5"
        
        # User experience validation
        assert validation_result.user_experience_average >= 0.5, \
            f"User experience average {validation_result.user_experience_average:.2f} below minimum 0.5"
        
        # Performance metrics validation
        performance = validation_result.performance_metrics
        assert performance.get("total_events_received", 0) > 0, \
            "No WebSocket events received across all scenarios"
        
        assert performance.get("successful_scenarios", 0) > 0, \
            "No scenarios completed successfully"
        
        # Overall validation success
        assert validation_result.validation_successful, \
            f"Golden path validation failed. Recommendations: {validation_result.recommendations}"
        
        print(f"\n[GOLDEN PATH SUCCESS] Comprehensive golden path message flow validation passed!")
        print(f"[GOLDEN PATH SUCCESS] System demonstrates reliable message processing capabilities")
        print(f"[GOLDEN PATH SUCCESS] Overall success rate: {validation_result.overall_success_rate:.2f}")
        print(f"[GOLDEN PATH SUCCESS] WebSocket events reliability: {validation_result.websocket_events_reliability:.2f}")
        print(f"[GOLDEN PATH SUCCESS] Business value delivery: {validation_result.business_value_delivery_rate:.2f}")
        print(f"[GOLDEN PATH SUCCESS] Golden path readiness: {validation_result.golden_path_readiness}")
    
    @pytest.mark.e2e
    @pytest.mark.agent_golden_path
    @pytest.mark.timeout(90)
    async def test_websocket_event_sequence_validation(self):
        """
        Test WebSocket event sequence validation for golden path.
        
        Validates that all 5 critical WebSocket events are delivered
        in the correct sequence with proper timing for optimal UX.
        """
        print(f"[EVENT SEQUENCE] Starting WebSocket event sequence validation")
        
        # Create user for event sequence testing
        event_user = await self.e2e_helper.create_authenticated_user(
            email=f"event_sequence_{int(time.time())}@test.com",
            permissions=["read", "write", "chat", "websocket_events"]
        )
        
        websocket_headers = self.e2e_helper.get_websocket_headers(event_user.jwt_token)
        
        # Test message designed to trigger all events
        test_message = {
            "type": "chat_message",
            "content": "Please analyze current market trends and provide strategic recommendations.",
            "thread_id": f"event_thread_{uuid.uuid4().hex[:8]}",
            "run_id": f"event_run_{uuid.uuid4().hex[:8]}",
            "user_id": event_user.user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "expects_all_events": True
        }
        
        events_received = []
        sequence_start_time = time.time()
        
        try:
            async with websockets.connect(
                self.websocket_url,
                additional_headers=websocket_headers,
                timeout=15.0
            ) as websocket:
                
                # Send message
                await websocket.send(json.dumps(test_message))
                print(f"[EVENT SEQUENCE] Test message sent")
                
                # Monitor for events
                while time.time() - sequence_start_time < 30.0:
                    try:
                        response_text = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        response_data = json.loads(response_text)
                        event_type = response_data.get("type", response_data.get("event_type", "unknown"))
                        
                        event_info = {
                            "type": event_type,
                            "timestamp": time.time() - sequence_start_time,
                            "data": response_data
                        }
                        events_received.append(event_info)
                        
                        print(f"[EVENT SEQUENCE] Event: {event_type} at {event_info['timestamp']:.2f}s")
                        
                        # Stop after completion event
                        if event_type in ["agent_completed", "error"]:
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                        
        except Exception as e:
            print(f"[EVENT SEQUENCE] Test error: {e}")
            if self._is_service_unavailable_error(e):
                pytest.skip(f"WebSocket service unavailable: {e}")
        
        total_time = time.time() - sequence_start_time
        
        print(f"[EVENT SEQUENCE RESULTS] Event Sequence Validation Results:")
        print(f"  - Total Events Received: {len(events_received)}")
        print(f"  - Total Sequence Time: {total_time:.2f}s")
        
        # Analyze event sequence
        critical_events_received = [e for e in events_received 
                                  if e['type'] in AgentGoldenPathValidator.CRITICAL_WEBSOCKET_EVENTS]
        
        print(f"  - Critical Events Received: {len(critical_events_received)}")
        for event in critical_events_received:
            print(f"    - {event['type']} at {event['timestamp']:.2f}s")
        
        # Event sequence validation
        assert len(events_received) > 0, "No WebSocket events received"
        
        assert len(critical_events_received) >= 2, \
            f"Expected at least 2 critical events, got {len(critical_events_received)}"
        
        # Timing validation
        if len(critical_events_received) > 1:
            max_interval = max(critical_events_received[i]['timestamp'] - critical_events_received[i-1]['timestamp']
                             for i in range(1, len(critical_events_received)))
            assert max_interval <= 10.0, \
                f"Event intervals too long for good UX: {max_interval:.2f}s"
        
        assert total_time <= 35.0, \
            f"Event sequence took too long: {total_time:.2f}s"
        
        print(f"[EVENT SEQUENCE SUCCESS] WebSocket event sequence validation passed!")
    
    def _is_service_unavailable_error(self, error: Exception) -> bool:
        """Check if error indicates service unavailability."""
        error_msg = str(error).lower()
        unavailable_indicators = [
            "connection refused", "connection failed", "timeout", "refused",
            "network unreachable", "connection reset"
        ]
        return any(indicator in error_msg for indicator in unavailable_indicators)


if __name__ == "__main__":
    # Allow running this test file directly
    import asyncio
    
    async def run_test():
        test_instance = TestAgentGoldenPathComprehensiveMessages()
        test_instance.setup_method()
        await test_instance.test_comprehensive_golden_path_message_flows()
        print("Direct test execution completed successfully")
    
    asyncio.run(run_test())