"""
Phase 3: End-to-End Business Logic Integration Tests - Issue #861

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - $500K+ ARR Protection
- Business Goal: Validate complete business workflows deliver substantive value
- Value Impact: End-to-end validation = Business critical chat platform reliability
- Revenue Impact: Complete user journey validation for customer retention

CRITICAL COVERAGE GAPS ADDRESSED:
- Complete golden path user flow validation (Login → Chat → AI Response)
- Business logic integration across all system components
- Real-world user scenario testing with actual data flows
- Multi-service integration validation (Auth + Backend + WebSocket + LLM)
- Enterprise customer workflow validation

PHASE 3 TARGET: Complete business workflow validation
COVERAGE IMPROVEMENT: Final contribution to 10.92% → 25%+ coverage increase

TEST INFRASTRUCTURE:
- Full staging environment integration
- Real service dependencies (Auth, Database, LLM, WebSocket)
- Complete user journey validation from login to response
- Business value measurement and validation
- Enterprise customer scenario testing

BUSINESS-CRITICAL END-TO-END FLOWS:
1. User Authentication → WebSocket Connection → Agent Execution → AI Response
2. Multi-user concurrent chat with proper isolation
3. Complex business queries requiring multiple agents and tools
4. Error recovery and user experience continuity
5. Enterprise customer workflow validation
6. Performance and scalability under realistic load
"""

import pytest
import asyncio
import json
import uuid
from typing import Dict, Any, List, Optional, Union
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta
import time

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.websocket_test_utility import WebSocketTestUtility
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper

# Complete System Integration
try:
    from netra_backend.app.main import create_app
    from netra_backend.app.core.app_state_contracts import validate_app_state_contracts
    APP_AVAILABLE = True
except ImportError:
    APP_AVAILABLE = False

# Authentication Integration
try:
    from auth_service.auth_core.core.jwt_handler import JWTHandler
    from auth_service.auth_core.core.session_manager import SessionManager
    AUTH_SERVICE_AVAILABLE = True
except ImportError:
    AUTH_SERVICE_AVAILABLE = False

# Complete Agent System
try:
    from netra_backend.app.agents.supervisor_agent_modern import SupervisorAgentModern
    from netra_backend.app.agents.data_helper.data_helper_agent import DataHelperAgent
    from netra_backend.app.agents.triage.triage_agent import TriageAgent
    COMPLETE_AGENT_SYSTEM_AVAILABLE = True
except ImportError:
    COMPLETE_AGENT_SYSTEM_AVAILABLE = False

# Database and Persistence
try:
    from netra_backend.app.db.database_manager import DatabaseManager
    from netra_backend.app.services.state_persistence_optimized import OptimizedStatePersistence
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False

# WebSocket and Real-time Communication
try:
    from netra_backend.app.websocket_core.manager import WebSocketManager
    from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
    REALTIME_AVAILABLE = True
except ImportError:
    REALTIME_AVAILABLE = False

# LLM Integration
try:
    from netra_backend.app.llm_providers.openai_provider import OpenAIProvider
    from netra_backend.app.llm_providers.claude_provider import ClaudeProvider
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False


@pytest.mark.integration
@pytest.mark.e2e_business_logic
@pytest.mark.business_critical
@pytest.mark.golden_path
class TestEndToEndBusinessLogicIntegration(SSotAsyncTestCase):
    """
    Phase 3: End-to-End Business Logic Integration Test Suite

    BUSINESS IMPACT: Validates complete $500K+ ARR customer journey
    COVERAGE TARGET: Complete business workflow validation and golden path
    """

    def setup_method(self, method):
        """Setup for complete end-to-end business logic testing"""
        super().setup_method(method)
        self.test_user_ids = []
        self.websocket_connections = []
        self.test_sessions = []
        self.auth_helper = E2EAuthHelper()
        self.websocket_utility = WebSocketTestUtility()

        # Business test tracking
        self.test_start_time = datetime.now()
        self.business_flows_tested = []
        self.customer_scenarios_validated = []

    async def teardown_method(self, method):
        """Cleanup complete test environment"""
        # Clean up test sessions
        for session in self.test_sessions:
            try:
                await session.cleanup()
            except Exception:
                pass

        # Close WebSocket connections
        for connection in self.websocket_connections:
            try:
                await connection.close()
            except Exception:
                pass

        # Clean up test users
        for user_id in self.test_user_ids:
            try:
                await self.auth_helper.cleanup_test_user(user_id)
            except Exception:
                pass

        await super().teardown_method(method)

    @pytest.mark.timeout(60)
    async def test_complete_golden_path_user_journey(self):
        """
        Test complete golden path: User Registration → Login → WebSocket → Chat → AI Response
        COVERS: Complete $500K+ ARR customer journey validation
        """
        if not all([APP_AVAILABLE, AUTH_SERVICE_AVAILABLE, REALTIME_AVAILABLE, COMPLETE_AGENT_SYSTEM_AVAILABLE]):
            pytest.skip("Complete system not available")

        # PHASE 1: User Registration and Authentication
        user_id = str(uuid.uuid4())
        self.test_user_ids.append(user_id)

        # Create user account
        user_email = f"test_user_{user_id}@netra.ai"
        user_password = "SecureTestPassword123!"

        auth_token = await self.auth_helper.create_test_user_with_token(
            user_id, email=user_email, password=user_password
        )

        # Verify authentication token
        assert auth_token is not None
        assert len(auth_token) > 20  # Valid JWT token length

        # PHASE 2: WebSocket Connection Establishment
        websocket_url = await self.websocket_utility.get_staging_websocket_url()
        connection = await self.websocket_utility.connect_with_auth(websocket_url, auth_token)
        self.websocket_connections.append(connection)

        # Verify WebSocket connection established
        assert connection is not None
        assert connection.open

        # PHASE 3: Business Chat Request
        business_query = {
            'message': 'I need to analyze our Q3 sales data and identify key growth opportunities. Please provide detailed insights with actionable recommendations.',
            'type': 'business_analysis',
            'session_id': str(uuid.uuid4()),
            'user_id': user_id,
            'timestamp': datetime.now().isoformat()
        }

        # Send business query through WebSocket
        await connection.send(json.dumps(business_query))

        # PHASE 4: Complete Agent Processing Chain
        received_events = []
        expected_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']

        # Collect all events from complete processing
        start_time = datetime.now()
        timeout_seconds = 50  # Generous timeout for complete processing

        try:
            while len(received_events) < 5 and (datetime.now() - start_time).total_seconds() < timeout_seconds:
                message = await asyncio.wait_for(connection.recv(), timeout=10.0)
                event_data = json.loads(message)
                received_events.append(event_data)

                # Break if we receive agent_completed
                if event_data.get('type') == 'agent_completed':
                    break

        except asyncio.TimeoutError:
            pass  # Continue with validation

        processing_time = (datetime.now() - start_time).total_seconds()

        # PHASE 5: Business Value Validation
        # Verify complete agent processing chain
        assert len(received_events) >= 3, f"Expected at least 3 events, got {len(received_events)}"

        # Verify event sequence includes business-critical events
        event_types = [event.get('type') for event in received_events]
        assert any(event_type in expected_events for event_type in event_types)

        # Verify final response contains business value
        final_event = received_events[-1] if received_events else None
        if final_event and final_event.get('type') == 'agent_completed':
            response = final_event.get('response') or final_event.get('final_result') or final_event.get('content')

            if response:
                # Business value indicators
                business_indicators = ['analysis', 'insights', 'recommendations', 'data', 'growth', 'opportunities']
                contains_business_value = any(indicator in str(response).lower() for indicator in business_indicators)
                assert contains_business_value, f"Response lacks business value: {response[:200]}"

                # Response should be substantial (not just acknowledgment)
                assert len(str(response)) > 50, "Response too brief to provide business value"

        # Verify performance meets business requirements
        assert processing_time < 55.0, f"Processing time {processing_time}s exceeds business requirements"

        self.business_flows_tested.append('complete_golden_path')

    @pytest.mark.timeout(50)
    async def test_enterprise_multi_user_concurrent_business_workflows(self):
        """
        Test enterprise scenario with multiple concurrent users and complex business workflows
        COVERS: Enterprise customer concurrent usage patterns
        """
        if not all([REALTIME_AVAILABLE, COMPLETE_AGENT_SYSTEM_AVAILABLE, DATABASE_AVAILABLE]):
            pytest.skip("Enterprise system components not available")

        # Create 3 concurrent enterprise users
        user_count = 3
        user_ids = [str(uuid.uuid4()) for _ in range(user_count)]
        self.test_user_ids.extend(user_ids)

        # Setup concurrent authentication
        auth_tasks = [
            self.auth_helper.create_test_user_with_token(
                user_id,
                email=f"enterprise_user_{i}@enterprise.com",
                role="enterprise"
            )
            for i, user_id in enumerate(user_ids)
        ]
        auth_tokens = await asyncio.gather(*auth_tasks)

        # Setup concurrent WebSocket connections
        websocket_url = await self.websocket_utility.get_staging_websocket_url()
        connection_tasks = [
            self.websocket_utility.connect_with_auth(websocket_url, token)
            for token in auth_tokens
        ]
        connections = await asyncio.gather(*connection_tasks)
        self.websocket_connections.extend(connections)

        # Define enterprise business scenarios
        enterprise_queries = [
            {
                'message': 'Analyze customer churn patterns and develop retention strategy for high-value accounts',
                'type': 'customer_analytics',
                'complexity': 'high',
                'user_id': user_ids[0],
                'department': 'customer_success'
            },
            {
                'message': 'Evaluate market expansion opportunities in European markets with competitive analysis',
                'type': 'market_analysis',
                'complexity': 'high',
                'user_id': user_ids[1],
                'department': 'strategy'
            },
            {
                'message': 'Optimize operational efficiency across our supply chain with cost reduction recommendations',
                'type': 'operational_optimization',
                'complexity': 'high',
                'user_id': user_ids[2],
                'department': 'operations'
            }
        ]

        # Execute concurrent enterprise workflows
        start_time = datetime.now()

        # Send concurrent queries
        send_tasks = [
            connections[i].send(json.dumps(enterprise_queries[i]))
            for i in range(user_count)
        ]
        await asyncio.gather(*send_tasks)

        # Collect responses from all users
        user_responses = [[] for _ in range(user_count)]

        # Monitor responses for up to 45 seconds
        monitoring_duration = 45
        end_time = start_time + timedelta(seconds=monitoring_duration)

        while datetime.now() < end_time:
            # Check each connection for new messages
            for i, connection in enumerate(connections):
                try:
                    message = await asyncio.wait_for(connection.recv(), timeout=1.0)
                    event_data = json.loads(message)
                    user_responses[i].append(event_data)
                except asyncio.TimeoutError:
                    continue
                except Exception:
                    continue

            # Break if all users have received agent_completed
            completed_users = sum(
                1 for responses in user_responses
                if any(event.get('type') == 'agent_completed' for event in responses)
            )
            if completed_users >= 2:  # At least 2 users completed
                break

            await asyncio.sleep(0.5)

        total_processing_time = (datetime.now() - start_time).total_seconds()

        # Enterprise validation requirements
        successful_users = 0

        for i, responses in enumerate(user_responses):
            if len(responses) >= 2:  # At least some processing occurred
                successful_users += 1

                # Verify user isolation
                user_events = [event for event in responses if event.get('user_id') == user_ids[i]]
                other_user_events = [event for event in responses if event.get('user_id') not in [user_ids[i], None]]

                # Should have own events, no other user events
                assert len(user_events) >= 1, f"User {i} should have received own events"
                assert len(other_user_events) == 0, f"User {i} received other user events: {other_user_events}"

        # Enterprise performance requirements
        assert successful_users >= 2, f"Only {successful_users} of {user_count} enterprise users succeeded"
        assert total_processing_time < 50.0, f"Enterprise processing time {total_processing_time}s too slow"

        self.customer_scenarios_validated.append('enterprise_concurrent_workflows')

    @pytest.mark.timeout(45)
    async def test_complex_business_intelligence_workflow(self):
        """
        Test complex business intelligence workflow with multiple agents and tools
        COVERS: Advanced business intelligence scenarios requiring agent coordination
        """
        if not all([COMPLETE_AGENT_SYSTEM_AVAILABLE, DATABASE_AVAILABLE, LLM_AVAILABLE]):
            pytest.skip("Complex BI system components not available")

        # Create business analyst user
        user_id = str(uuid.uuid4())
        self.test_user_ids.append(user_id)
        auth_token = await self.auth_helper.create_test_user_with_token(
            user_id,
            email="business_analyst@company.com",
            role="analyst"
        )

        # Setup WebSocket for real-time BI updates
        websocket_url = await self.websocket_utility.get_staging_websocket_url()
        connection = await self.websocket_utility.connect_with_auth(websocket_url, auth_token)
        self.websocket_connections.append(connection)

        # Complex BI request requiring multiple agents
        bi_request = {
            'message': '''Conduct comprehensive business intelligence analysis:
            1. Analyze revenue trends across all product lines for the past 12 months
            2. Identify top-performing customer segments and their characteristics
            3. Evaluate competitive positioning and market share changes
            4. Provide strategic recommendations for the next quarter
            5. Create executive summary with key metrics and actionable insights

            This requires data analysis, market research, and strategic planning capabilities.''',
            'type': 'comprehensive_bi_analysis',
            'session_id': str(uuid.uuid4()),
            'user_id': user_id,
            'requires_multiple_agents': True,
            'complexity': 'enterprise',
            'timestamp': datetime.now().isoformat()
        }

        # Send complex BI request
        await connection.send(json.dumps(bi_request))

        # Track comprehensive processing
        received_events = []
        agent_coordination_events = []
        tool_execution_events = []

        start_time = datetime.now()
        processing_timeout = 40  # Extended timeout for complex analysis

        try:
            while (datetime.now() - start_time).total_seconds() < processing_timeout:
                message = await asyncio.wait_for(connection.recv(), timeout=8.0)
                event_data = json.loads(message)
                received_events.append(event_data)

                # Track specific event types
                event_type = event_data.get('type')
                if event_type in ['agent_coordination', 'agent_handoff', 'multi_agent']:
                    agent_coordination_events.append(event_data)
                elif event_type in ['tool_executing', 'tool_completed']:
                    tool_execution_events.append(event_data)

                # Stop when comprehensive analysis completed
                if event_type == 'agent_completed':
                    final_response = event_data.get('response') or event_data.get('final_result')
                    if final_response and len(str(final_response)) > 200:
                        break

        except asyncio.TimeoutError:
            pass

        processing_time = (datetime.now() - start_time).total_seconds()

        # Business Intelligence validation
        assert len(received_events) >= 4, f"Complex BI should generate multiple events, got {len(received_events)}"

        # Verify comprehensive response
        final_event = received_events[-1] if received_events else None
        if final_event:
            response = final_event.get('response') or final_event.get('final_result') or final_event.get('content')

            if response:
                response_text = str(response).lower()

                # Should contain BI analysis components
                bi_components = ['revenue', 'trends', 'customer', 'segments', 'competitive', 'recommendations', 'metrics']
                found_components = sum(1 for component in bi_components if component in response_text)
                assert found_components >= 4, f"BI response missing key components. Found {found_components}/7"

                # Should be comprehensive (substantial content)
                assert len(response_text) > 300, f"BI analysis too brief: {len(response_text)} chars"

                # Should contain strategic insights
                strategic_indicators = ['strategy', 'recommend', 'insight', 'opportunity', 'action', 'plan']
                has_strategy = any(indicator in response_text for indicator in strategic_indicators)
                assert has_strategy, "BI analysis lacks strategic recommendations"

        # Performance validation for complex analysis
        assert processing_time < 42.0, f"Complex BI processing time {processing_time}s exceeds limits"

        self.business_flows_tested.append('complex_business_intelligence')

    @pytest.mark.timeout(35)
    async def test_customer_support_escalation_workflow(self):
        """
        Test customer support escalation workflow with agent handoffs
        COVERS: Customer support business workflow with multi-agent coordination
        """
        if not all([COMPLETE_AGENT_SYSTEM_AVAILABLE, REALTIME_AVAILABLE]):
            pytest.skip("Customer support system components not available")

        # Create customer support scenario
        user_id = str(uuid.uuid4())
        self.test_user_ids.append(user_id)
        auth_token = await self.auth_helper.create_test_user_with_token(
            user_id,
            email="support_agent@company.com",
            role="support"
        )

        # Setup WebSocket connection
        websocket_url = await self.websocket_utility.get_staging_websocket_url()
        connection = await self.websocket_utility.connect_with_auth(websocket_url, auth_token)
        self.websocket_connections.append(connection)

        # Customer support escalation scenario
        support_request = {
            'message': '''Customer escalation: Enterprise client reporting critical system performance issues.

            Initial Issue: Dashboard loading times exceed 30 seconds, affecting daily operations
            Customer: TechCorp Enterprise (Tier 1 client, $50K/year contract)
            Impact: High - affecting 200+ end users
            Previous attempts: Basic troubleshooting completed, issue persists

            Required: Technical analysis, performance investigation, solution recommendation,
            and executive communication for high-value client retention.''',
            'type': 'customer_support_escalation',
            'priority': 'critical',
            'customer_tier': 'enterprise',
            'session_id': str(uuid.uuid4()),
            'user_id': user_id,
            'timestamp': datetime.now().isoformat()
        }

        # Send support escalation
        await connection.send(json.dumps(support_request))

        # Track escalation workflow
        received_events = []
        escalation_events = []

        start_time = datetime.now()

        try:
            while (datetime.now() - start_time).total_seconds() < 30:
                message = await asyncio.wait_for(connection.recv(), timeout=6.0)
                event_data = json.loads(message)
                received_events.append(event_data)

                # Track escalation-specific events
                event_type = event_data.get('type')
                if 'escalation' in event_type or 'priority' in str(event_data).lower():
                    escalation_events.append(event_data)

                # Complete when solution provided
                if event_type == 'agent_completed':
                    response = event_data.get('response') or event_data.get('final_result')
                    if response and 'solution' in str(response).lower():
                        break

        except asyncio.TimeoutError:
            pass

        processing_time = (datetime.now() - start_time).total_seconds()

        # Customer support validation
        assert len(received_events) >= 2, "Support escalation should generate multiple events"

        # Verify escalation handling
        final_event = received_events[-1] if received_events else None
        if final_event:
            response = final_event.get('response') or final_event.get('final_result') or final_event.get('content')

            if response:
                response_text = str(response).lower()

                # Should address customer support elements
                support_elements = ['performance', 'solution', 'client', 'enterprise', 'recommendation']
                found_elements = sum(1 for element in support_elements if element in response_text)
                assert found_elements >= 3, f"Support response missing key elements. Found {found_elements}/5"

                # Should be actionable for support team
                actionable_terms = ['action', 'step', 'resolve', 'implement', 'contact', 'follow']
                is_actionable = any(term in response_text for term in actionable_terms)
                assert is_actionable, "Support response lacks actionable recommendations"

        # Performance critical for customer support
        assert processing_time < 32.0, f"Support escalation time {processing_time}s too slow for customer experience"

        self.customer_scenarios_validated.append('customer_support_escalation')

    @pytest.mark.timeout(40)
    async def test_financial_analysis_compliance_workflow(self):
        """
        Test financial analysis workflow with compliance and regulatory requirements
        COVERS: Financial services business logic with compliance validation
        """
        if not all([COMPLETE_AGENT_SYSTEM_AVAILABLE, DATABASE_AVAILABLE]):
            pytest.skip("Financial analysis system components not available")

        # Create financial analyst user
        user_id = str(uuid.uuid4())
        self.test_user_ids.append(user_id)
        auth_token = await self.auth_helper.create_test_user_with_token(
            user_id,
            email="financial_analyst@fintech.com",
            role="financial_analyst"
        )

        # Setup WebSocket connection
        websocket_url = await self.websocket_utility.get_staging_websocket_url()
        connection = await self.websocket_utility.connect_with_auth(websocket_url, auth_token)
        self.websocket_connections.append(connection)

        # Financial compliance analysis request
        financial_request = {
            'message': '''Conduct comprehensive financial analysis with regulatory compliance:

            Scope: Q3 financial performance analysis including:
            - Revenue recognition validation per GAAP standards
            - Risk assessment for portfolio diversification
            - Liquidity analysis and cash flow projections
            - Regulatory compliance check for SOX requirements
            - Audit trail documentation for financial controls

            Compliance requirements: Ensure all analysis meets SEC reporting standards
            and internal risk management policies. Generate executive summary suitable
            for board presentation and regulatory filing.''',
            'type': 'financial_compliance_analysis',
            'compliance_level': 'SEC_SOX',
            'session_id': str(uuid.uuid4()),
            'user_id': user_id,
            'requires_audit_trail': True,
            'timestamp': datetime.now().isoformat()
        }

        # Send financial analysis request
        await connection.send(json.dumps(financial_request))

        # Track financial analysis processing
        received_events = []
        compliance_events = []

        start_time = datetime.now()

        try:
            while (datetime.now() - start_time).total_seconds() < 35:
                message = await asyncio.wait_for(connection.recv(), timeout=7.0)
                event_data = json.loads(message)
                received_events.append(event_data)

                # Track compliance-related events
                if 'compliance' in str(event_data).lower() or 'regulatory' in str(event_data).lower():
                    compliance_events.append(event_data)

                # Complete when financial analysis finished
                if event_data.get('type') == 'agent_completed':
                    response = event_data.get('response') or event_data.get('final_result')
                    if response and len(str(response)) > 250:
                        break

        except asyncio.TimeoutError:
            pass

        processing_time = (datetime.now() - start_time).total_seconds()

        # Financial analysis validation
        assert len(received_events) >= 3, "Financial analysis should be comprehensive"

        # Verify financial compliance response
        final_event = received_events[-1] if received_events else None
        if final_event:
            response = final_event.get('response') or final_event.get('final_result') or final_event.get('content')

            if response:
                response_text = str(response).lower()

                # Should contain financial analysis components
                financial_components = ['financial', 'revenue', 'risk', 'compliance', 'analysis', 'regulatory']
                found_components = sum(1 for component in financial_components if component in response_text)
                assert found_components >= 4, f"Financial response missing components. Found {found_components}/6"

                # Should address compliance requirements
                compliance_terms = ['gaap', 'sec', 'sox', 'audit', 'controls', 'compliance']
                compliance_addressed = sum(1 for term in compliance_terms if term in response_text)
                assert compliance_addressed >= 2, f"Compliance requirements not adequately addressed"

                # Should be substantial financial analysis
                assert len(response_text) > 200, f"Financial analysis too brief: {len(response_text)} chars"

        # Performance requirements for financial analysis
        assert processing_time < 37.0, f"Financial analysis time {processing_time}s exceeds business requirements"

        self.business_flows_tested.append('financial_compliance_analysis')

    @pytest.mark.timeout(30)
    async def test_system_error_recovery_business_continuity(self):
        """
        Test system error recovery and business continuity workflows
        COVERS: Business continuity and error recovery scenarios
        """
        if not REALTIME_AVAILABLE:
            pytest.skip("Real-time system not available")

        # Create business user
        user_id = str(uuid.uuid4())
        self.test_user_ids.append(user_id)
        auth_token = await self.auth_helper.create_test_user_with_token(user_id)

        # Setup WebSocket connection
        websocket_url = await self.websocket_utility.get_staging_websocket_url()
        connection = await self.websocket_utility.connect_with_auth(websocket_url, auth_token)
        self.websocket_connections.append(connection)

        # Send normal business request first
        normal_request = {
            'message': 'Generate quarterly business report with key metrics',
            'type': 'business_report',
            'user_id': user_id,
            'session_id': str(uuid.uuid4())
        }

        await connection.send(json.dumps(normal_request))

        # Collect initial response
        initial_events = []
        try:
            while len(initial_events) < 2:
                message = await asyncio.wait_for(connection.recv(), timeout=8.0)
                event_data = json.loads(message)
                initial_events.append(event_data)
        except asyncio.TimeoutError:
            pass

        # Simulate error scenario - send malformed request
        error_request = {
            'malformed': True,
            'invalid_data': None,
            'user_id': user_id,
            'type': 'invalid_request_type'
        }

        await connection.send(json.dumps(error_request))

        # Brief wait for error processing
        await asyncio.sleep(2.0)

        # Send recovery request to test business continuity
        recovery_request = {
            'message': 'After the system issue, please provide a simple business summary',
            'type': 'business_summary',
            'user_id': user_id,
            'session_id': str(uuid.uuid4()),
            'recovery_test': True
        }

        await connection.send(json.dumps(recovery_request))

        # Collect recovery response
        recovery_events = []
        start_time = datetime.now()

        try:
            while (datetime.now() - start_time).total_seconds() < 20:
                message = await asyncio.wait_for(connection.recv(), timeout=5.0)
                event_data = json.loads(message)
                recovery_events.append(event_data)

                # Break when we get completed response
                if event_data.get('type') == 'agent_completed':
                    break

        except asyncio.TimeoutError:
            pass

        # Business continuity validation
        assert len(initial_events) >= 1, "System should handle normal requests"
        assert len(recovery_events) >= 1, "System should recover after errors"

        # Verify business continuity maintained
        if recovery_events:
            final_recovery = recovery_events[-1]
            recovery_response = final_recovery.get('response') or final_recovery.get('final_result')

            if recovery_response:
                # Should provide business value despite error
                business_terms = ['business', 'summary', 'report', 'analysis']
                contains_business_content = any(term in str(recovery_response).lower() for term in business_terms)
                assert contains_business_content, "Recovery should maintain business functionality"

        self.customer_scenarios_validated.append('error_recovery_business_continuity')

    @pytest.mark.timeout(35)
    async def test_performance_scalability_business_requirements(self):
        """
        Test system performance and scalability under business load requirements
        COVERS: Performance validation for business requirements
        """
        if not REALTIME_AVAILABLE:
            pytest.skip("Real-time system not available")

        # Create business performance test user
        user_id = str(uuid.uuid4())
        self.test_user_ids.append(user_id)
        auth_token = await self.auth_helper.create_test_user_with_token(user_id)

        # Setup WebSocket connection
        websocket_url = await self.websocket_utility.get_staging_websocket_url()
        connection = await self.websocket_utility.connect_with_auth(websocket_url, auth_token)
        self.websocket_connections.append(connection)

        # Test sequential business requests for performance
        business_requests = [
            {
                'message': f'Generate business insight #{i}: Market analysis for product line {i}',
                'type': 'market_analysis',
                'user_id': user_id,
                'session_id': str(uuid.uuid4()),
                'request_number': i
            }
            for i in range(1, 4)  # 3 sequential requests
        ]

        # Execute business requests and measure performance
        request_times = []
        all_responses = []

        for i, request in enumerate(business_requests):
            start_time = datetime.now()

            # Send request
            await connection.send(json.dumps(request))

            # Collect response
            request_events = []
            try:
                while (datetime.now() - start_time).total_seconds() < 25:
                    message = await asyncio.wait_for(connection.recv(), timeout=8.0)
                    event_data = json.loads(message)
                    request_events.append(event_data)

                    # Stop when we get completion
                    if event_data.get('type') == 'agent_completed':
                        break

            except asyncio.TimeoutError:
                pass

            request_time = (datetime.now() - start_time).total_seconds()
            request_times.append(request_time)
            all_responses.extend(request_events)

            # Brief pause between requests
            await asyncio.sleep(1.0)

        # Performance validation for business requirements
        successful_requests = sum(1 for events in all_responses if events)
        assert successful_requests >= 6, f"Should handle business requests successfully, got {successful_requests}"

        # Individual request performance
        for i, request_time in enumerate(request_times):
            assert request_time < 27.0, f"Request {i+1} took {request_time}s, exceeds business requirements"

        # Average performance
        average_time = sum(request_times) / len(request_times) if request_times else 0
        assert average_time < 20.0, f"Average response time {average_time}s too slow for business use"

        # Verify business content quality maintained under load
        completed_events = [event for event in all_responses if event.get('type') == 'agent_completed']

        for event in completed_events:
            response = event.get('response') or event.get('final_result')
            if response:
                # Should maintain business quality under performance pressure
                business_quality_indicators = ['analysis', 'market', 'insight', 'business']
                has_quality = any(indicator in str(response).lower() for indicator in business_quality_indicators)
                assert has_quality, "Business quality degraded under performance load"

        self.business_flows_tested.append('performance_scalability_validation')