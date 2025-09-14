"""
E2E Tests for Multi-Turn Conversation Flow - Golden Path Context Persistence

MISSION CRITICAL: Tests context persistence across multiple conversation exchanges
to validate continuous, coherent chat interactions that build upon previous context.
This represents advanced chat functionality critical for user engagement and satisfaction.

Business Value Justification (BVJ):
- Segment: Mid-tier and Enterprise Users (Premium Chat Features)
- Business Goal: User Retention & Platform Stickiness through Superior Chat Experience
- Value Impact: Validates advanced conversational AI that maintains context and memory
- Strategic Impact: Differentiates platform from basic chat solutions, drives premium adoption

Test Strategy:
- REAL SERVICES: Staging GCP Cloud Run environment only (NO Docker)
- REAL AUTH: JWT tokens with persistent session management
- REAL WEBSOCKETS: Persistent wss:// connections across multiple exchanges
- REAL AGENTS: Context-aware agents with conversation memory
- REAL PERSISTENCE: Chat history and context stored in staging databases
- CONVERSATION DEPTH: Multi-turn exchanges with complex context building

CRITICAL: These tests must demonstrate actual context persistence and conversation coherence.
No mocking conversation state or bypassing context validation allowed.

GitHub Issue: #861 Agent Golden Path Messages Test Creation - STEP 1
Coverage Target: 0.9% → 25% improvement (Priority Scenario #2)
"""

import asyncio
import pytest
import time
import json
import logging
import websockets
import ssl
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import uuid

# SSOT imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from tests.e2e.staging_config import get_staging_config, is_staging_available

# Auth and WebSocket utilities
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.ssot.websocket_test_utility import WebSocketTestHelper


@pytest.mark.e2e
@pytest.mark.gcp_staging
@pytest.mark.agent_goldenpath
@pytest.mark.mission_critical
class TestMultiTurnConversationE2E(SSotAsyncTestCase):
    """
    E2E tests for validating multi-turn conversation flow and context persistence.

    Tests advanced chat functionality: conversation memory, context building,
    and coherent multi-exchange interactions that build upon previous dialogue.
    """

    @classmethod
    def setup_class(cls):
        """Setup staging environment configuration and dependencies."""

        # Initialize staging configuration
        cls.staging_config = get_staging_config()
        cls.logger = logging.getLogger(__name__)

        # Skip if staging not available
        if not is_staging_available():
            pytest.skip("Staging environment not available")

        # Initialize auth helper for JWT management
        cls.auth_helper = E2EAuthHelper(environment="staging")

        # Initialize WebSocket test utilities
        cls.websocket_helper = WebSocketTestHelper(
            base_url=cls.staging_config.urls.websocket_url,
            environment="staging"
        )

        # Test user configuration for conversation persistence
        cls.test_user_id = f"conversation_user_{int(time.time())}"
        cls.test_user_email = f"conversation_test_{int(time.time())}@netra-testing.ai"

        cls.logger.info(f"Multi-turn conversation E2E tests initialized for staging")

    def setup_method(self, method):
        """Setup for each test method."""
        super().setup_method(method)

        # Generate persistent conversation context
        self.conversation_id = str(uuid.uuid4())
        self.thread_id = f"conversation_{self.conversation_id}"
        self.run_id = f"run_{self.thread_id}"

        # Create JWT token with extended expiry for multi-turn testing
        self.access_token = self.__class__.auth_helper.create_test_jwt_token(
            user_id=self.__class__.test_user_id,
            email=self.__class__.test_user_email,
            exp_minutes=120  # Longer for multi-turn tests
        )

        self.logger.info(f"Conversation test setup - conversation_id: {self.conversation_id}")

    async def _establish_persistent_websocket_connection(self) -> websockets.WebSocketServerProtocol:
        """Establish persistent WebSocket connection for multi-turn conversation."""
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False  # Staging environment
        ssl_context.verify_mode = ssl.CERT_NONE

        websocket = await asyncio.wait_for(
            websockets.connect(
                self.__class__.staging_config.urls.websocket_url,
                additional_headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "X-Environment": "staging",
                    "X-Test-Suite": "multi-turn-conversation-e2e",
                    "X-Conversation-Id": self.conversation_id,
                    "X-Persistent-Context": "true"
                },
                ssl=ssl_context,
                ping_interval=45,  # Longer for persistent connections
                ping_timeout=15
            ),
            timeout=20.0
        )

        return websocket

    async def _send_conversation_turn(self, websocket, agent_type: str, message: str,
                                    turn_number: int, context: Dict = None) -> List[Dict]:
        """Send a conversation turn and collect response with context tracking."""
        turn_message = {
            "type": "agent_request",
            "agent": agent_type,
            "message": message,
            "thread_id": self.thread_id,
            "run_id": f"{self.run_id}_turn_{turn_number}",
            "user_id": self.__class__.test_user_id,
            "conversation_id": self.conversation_id,
            "turn_number": turn_number,
            "context": {
                "conversation_turn": turn_number,
                "persist_context": True,
                **(context or {})
            }
        }

        # Send the conversation turn
        await websocket.send(json.dumps(turn_message))

        # Collect all events for this turn
        events = []
        response_timeout = 90.0
        collection_start = time.time()

        while time.time() - collection_start < response_timeout:
            try:
                event_data = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                event = json.loads(event_data)
                events.append(event)

                event_type = event.get("type", "unknown")

                # Check for completion or error
                if event_type == "agent_completed":
                    break
                elif event_type in ["error", "agent_error"]:
                    raise AssertionError(f"Agent processing error on turn {turn_number}: {event}")

            except asyncio.TimeoutError:
                continue
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse WebSocket message on turn {turn_number}: {e}")
                continue

        return events

    def _extract_response_content(self, events: List[Dict]) -> str:
        """Extract response content from agent events."""
        final_response = None
        for event in reversed(events):
            if event.get("type") == "agent_completed":
                final_response = event
                break

        if not final_response:
            return ""

        response_data = final_response.get("data", {})
        result = response_data.get("result", {})

        if isinstance(result, dict):
            return result.get("response", str(result))
        else:
            return str(result)

    def _analyze_context_continuity(self, responses: List[str], conversation_elements: List[str]) -> Dict[str, Any]:
        """Analyze context continuity across conversation turns."""
        analysis = {
            "total_turns": len(responses),
            "context_references": 0,
            "conversation_elements_maintained": [],
            "context_coherence_score": 0,
            "response_lengths": [len(r) for r in responses],
            "avg_response_length": sum(len(r) for r in responses) / len(responses) if responses else 0
        }

        # Check for context references in later responses
        for i, response in enumerate(responses[1:], 1):  # Skip first response
            response_lower = response.lower()

            # Count references to conversation elements
            for element in conversation_elements:
                if element.lower() in response_lower:
                    analysis["context_references"] += 1
                    if element not in analysis["conversation_elements_maintained"]:
                        analysis["conversation_elements_maintained"].append(element)

            # Look for continuity indicators
            continuity_indicators = [
                "as mentioned", "as discussed", "previously", "earlier", "following up",
                "building on", "continuing", "based on", "given that", "since you"
            ]

            for indicator in continuity_indicators:
                if indicator in response_lower:
                    analysis["context_references"] += 1

        # Calculate coherence score
        expected_references = len(conversation_elements) * (len(responses) - 1)  # Each element in each subsequent response
        if expected_references > 0:
            analysis["context_coherence_score"] = min(1.0, analysis["context_references"] / expected_references)

        return analysis

    async def test_basic_two_turn_context_persistence(self):
        """
        Test basic two-turn conversation with context persistence.

        CONTEXT VALIDATION: Second response should reference and build upon first exchange.

        Conversation Flow:
        1. User asks about AI cost optimization
        2. Agent provides initial recommendations
        3. User asks follow-up about specific recommendation
        4. Agent references previous context and provides detailed guidance

        DIFFICULTY: Medium (25 minutes)
        REAL SERVICES: Yes - Persistent conversation context in staging
        STATUS: Should PASS - Basic context persistence is fundamental
        """
        self.logger.info("🔗 Testing basic two-turn context persistence")

        websocket = await self._establish_persistent_websocket_connection()

        try:
            conversation_responses = []
            conversation_elements = ["prompt optimization", "model selection", "caching"]

            # Turn 1: Initial optimization question
            turn1_message = (
                "I'm spending $10,000/month on OpenAI API calls for my customer support system. "
                "I need practical ways to reduce costs without hurting response quality. "
                "What are the top 3 optimization strategies I should focus on?"
            )

            turn1_events = await self._send_conversation_turn(
                websocket, "apex_optimizer_agent", turn1_message, 1,
                {"optimization_context": "customer_support", "budget": "$10k_monthly"}
            )

            turn1_response = self._extract_response_content(turn1_events)
            conversation_responses.append(turn1_response)

            self.logger.info(f"Turn 1 response: {len(turn1_response)} chars")

            # Validate first response quality
            assert len(turn1_response) >= 100, f"Turn 1 response too short: {len(turn1_response)} chars"

            # Wait brief moment to ensure context persistence
            await asyncio.sleep(2)

            # Turn 2: Follow-up question referencing first response
            turn2_message = (
                "You mentioned prompt optimization as one of the strategies. "
                "Can you give me specific examples of how to optimize prompts for customer support "
                "to reduce token usage while maintaining helpful responses?"
            )

            turn2_events = await self._send_conversation_turn(
                websocket, "apex_optimizer_agent", turn2_message, 2,
                {"follow_up": True, "references_previous": "prompt optimization"}
            )

            turn2_response = self._extract_response_content(turn2_events)
            conversation_responses.append(turn2_response)

            self.logger.info(f"Turn 2 response: {len(turn2_response)} chars")

            # Analyze context continuity
            context_analysis = self._analyze_context_continuity(
                conversation_responses, conversation_elements
            )

            self.logger.info(f"📊 Context Continuity Analysis:")
            self.logger.info(f"   Context References: {context_analysis['context_references']}")
            self.logger.info(f"   Elements Maintained: {context_analysis['conversation_elements_maintained']}")
            self.logger.info(f"   Coherence Score: {context_analysis['context_coherence_score']:.2f}")
            self.logger.info(f"   Avg Response Length: {context_analysis['avg_response_length']:.0f} chars")

            # Validate context persistence
            assert context_analysis["context_references"] >= 1, (
                f"Turn 2 should reference previous context. "
                f"Found {context_analysis['context_references']} references"
            )

            turn2_lower = turn2_response.lower()
            assert any(elem in turn2_lower for elem in ["prompt", "optimization", "customer support"]), (
                f"Turn 2 should specifically address prompt optimization for customer support. "
                f"Response: {turn2_response[:200]}..."
            )

            # Second response should be substantive and contextual
            assert len(turn2_response) >= 150, (
                f"Turn 2 response should be detailed follow-up: {len(turn2_response)} chars"
            )

            assert context_analysis["coherence_score"] >= 0.3, (
                f"Context coherence too low: {context_analysis['context_coherence_score']:.2f} "
                f"(conversation should build upon previous context)"
            )

            self.logger.info("✅ Basic two-turn context persistence validated")

        finally:
            await websocket.close()

    async def test_multi_turn_conversation_building(self):
        """
        Test complex multi-turn conversation with progressive context building.

        CONTEXT VALIDATION: Each turn should build upon all previous context,
        creating a coherent, evolving conversation thread.

        Conversation Flow:
        1. Initial business problem presentation
        2. Clarifying questions and detailed analysis
        3. Specific implementation guidance
        4. Follow-up refinements and edge cases
        5. Final summary with action plan

        DIFFICULTY: Very High (50 minutes)
        REAL SERVICES: Yes - Complex conversation state management in staging
        STATUS: Should PASS - Advanced conversation flow is premium feature
        """
        self.logger.info("🔗 Testing complex multi-turn conversation building")

        websocket = await self._establish_persistent_websocket_connection()

        try:
            conversation_responses = []
            conversation_elements = []

            # Turn 1: Present complex business scenario
            turn1_message = (
                "I'm the CTO of a B2B SaaS company with 200 employees. We've built an AI-powered "
                "analytics platform that helps customers optimize their marketing campaigns. "
                "Our AI infrastructure costs have grown from $5K to $40K monthly in 6 months "
                "due to increased customer usage. We're profitable but margins are shrinking. "
                "I need a comprehensive strategy to manage these costs while supporting growth."
            )

            conversation_elements.extend(["B2B SaaS", "analytics platform", "marketing campaigns",
                                        "$40K monthly", "margins shrinking"])

            turn1_events = await self._send_conversation_turn(
                websocket, "supervisor_agent", turn1_message, 1,
                {"scenario": "cto_cost_management", "company_size": "200_employees"}
            )

            turn1_response = self._extract_response_content(turn1_events)
            conversation_responses.append(turn1_response)
            self.logger.info(f"Turn 1 (Scenario): {len(turn1_response)} chars")

            # Turn 2: Dive deeper into specific area
            turn2_message = (
                "The marketing campaign optimization feature is our most popular but also most expensive. "
                "It analyzes customer data patterns and generates recommendations using GPT-4. "
                "Each analysis costs us about $2.50 in API calls but we only charge customers $15/month. "
                "With 500 active customers running 3-5 analyses per week, the math is getting challenging."
            )

            conversation_elements.extend(["marketing campaign optimization", "$2.50 API cost",
                                        "500 customers", "3-5 analyses per week"])

            turn2_events = await self._send_conversation_turn(
                websocket, "apex_optimizer_agent", turn2_message, 2,
                {"cost_analysis": True, "unit_economics": "$2.50_cost_$15_revenue"}
            )

            turn2_response = self._extract_response_content(turn2_events)
            conversation_responses.append(turn2_response)
            self.logger.info(f"Turn 2 (Details): {len(turn2_response)} chars")

            # Turn 3: Ask about specific recommendation from Turn 2
            turn3_message = (
                "Based on your recommendation about tiered pricing and usage limits, "
                "how would you suggest I communicate these changes to existing customers "
                "without damaging relationships? Some have been with us since our early days "
                "when we offered unlimited analyses."
            )

            turn3_events = await self._send_conversation_turn(
                websocket, "data_helper_agent", turn3_message, 3,
                {"implementation_focus": "customer_communication",
                 "references_previous": "tiered_pricing"}
            )

            turn3_response = self._extract_response_content(turn3_events)
            conversation_responses.append(turn3_response)
            self.logger.info(f"Turn 3 (Implementation): {len(turn3_response)} chars")

            # Turn 4: Technical implementation details
            turn4_message = (
                "The grandfathering approach makes sense for customer relations. "
                "On the technical side, what specific changes should I make to our API architecture "
                "to implement usage tracking and limits without impacting performance? "
                "We're currently using microservices on AWS with Redis for caching."
            )

            conversation_elements.extend(["grandfathering approach", "API architecture",
                                        "microservices", "AWS", "Redis"])

            turn4_events = await self._send_conversation_turn(
                websocket, "apex_optimizer_agent", turn4_message, 4,
                {"technical_implementation": True, "architecture": "aws_microservices"}
            )

            turn4_response = self._extract_response_content(turn4_events)
            conversation_responses.append(turn4_response)
            self.logger.info(f"Turn 4 (Technical): {len(turn4_response)} chars")

            # Turn 5: Timeline and prioritization
            turn5_message = (
                "This is a comprehensive plan. Given that we need to implement these changes "
                "within the next quarter to manage cash flow, how would you prioritize these initiatives? "
                "What should we tackle first to get the biggest impact on our $40K monthly costs?"
            )

            turn5_events = await self._send_conversation_turn(
                websocket, "supervisor_agent", turn5_message, 5,
                {"prioritization": True, "timeline": "quarterly", "cost_impact": "$40K_monthly"}
            )

            turn5_response = self._extract_response_content(turn5_events)
            conversation_responses.append(turn5_response)
            self.logger.info(f"Turn 5 (Prioritization): {len(turn5_response)} chars")

            # Analyze complex conversation context continuity
            context_analysis = self._analyze_context_continuity(
                conversation_responses, conversation_elements
            )

            self.logger.info(f"📊 Multi-Turn Context Analysis:")
            self.logger.info(f"   Total Turns: {context_analysis['total_turns']}")
            self.logger.info(f"   Context References: {context_analysis['context_references']}")
            self.logger.info(f"   Elements Maintained: {len(context_analysis['conversation_elements_maintained'])}")
            self.logger.info(f"   Coherence Score: {context_analysis['context_coherence_score']:.2f}")
            self.logger.info(f"   Response Quality: {[len(r) for r in conversation_responses]}")

            # Validate multi-turn conversation quality
            assert all(len(response) >= 80 for response in conversation_responses), (
                f"All responses should be substantive. Lengths: {[len(r) for r in conversation_responses]}"
            )

            assert context_analysis["context_references"] >= 3, (
                f"Multi-turn conversation should have multiple context references. "
                f"Found: {context_analysis['context_references']}"
            )

            assert len(context_analysis["conversation_elements_maintained"]) >= 5, (
                f"Should maintain key conversation elements across turns. "
                f"Maintained: {context_analysis['conversation_elements_maintained']}"
            )

            # Later responses should reference earlier context
            turn5_lower = turn5_response.lower()
            should_reference = ["$40k", "quarter", "prioritize", "cost", "impact"]
            referenced = [term for term in should_reference if term in turn5_lower]

            assert len(referenced) >= 3, (
                f"Final turn should synthesize conversation context. "
                f"Referenced: {referenced} of {should_reference}"
            )

            assert context_analysis["context_coherence_score"] >= 0.4, (
                f"Complex conversation coherence insufficient: {context_analysis['context_coherence_score']:.2f}. "
                f"Multi-turn conversations require strong context continuity."
            )

            self.logger.info("✅ Complex multi-turn conversation building validated")

        finally:
            await websocket.close()

    async def test_conversation_memory_across_agent_types(self):
        """
        Test conversation memory persistence across different agent types.

        CONTEXT VALIDATION: Different agents should access and build upon the same
        conversation context, maintaining coherent dialogue regardless of agent type.

        Agent Flow:
        1. Supervisor agent initial analysis
        2. Triage agent specialization assessment
        3. APEX optimizer detailed recommendations
        4. Data helper impact analysis
        5. Supervisor agent final synthesis

        DIFFICULTY: Very High (45 minutes)
        REAL SERVICES: Yes - Cross-agent context sharing in staging
        STATUS: Should PASS - Agent collaboration with context is premium feature
        """
        self.logger.info("🔗 Testing conversation memory across agent types")

        websocket = await self._establish_persistent_websocket_connection()

        try:
            conversation_responses = []
            agent_sequence = []

            # Shared conversation elements to track
            conversation_elements = ["e-commerce platform", "Black Friday", "traffic surge",
                                   "API rate limits", "performance optimization"]

            # Turn 1: Supervisor Agent - Initial Problem Assessment
            turn1_message = (
                "Our e-commerce platform experienced major issues during last Black Friday. "
                "Traffic surged 10x but our AI recommendation engine hit API rate limits, "
                "causing slow page loads and lost sales. We estimate $2M in lost revenue. "
                "This year's Black Friday is 8 weeks away and we need a solution."
            )

            turn1_events = await self._send_conversation_turn(
                websocket, "supervisor_agent", turn1_message, 1,
                {"crisis_scenario": "black_friday_preparation", "lost_revenue": "$2M"}
            )

            turn1_response = self._extract_response_content(turn1_events)
            conversation_responses.append(turn1_response)
            agent_sequence.append("supervisor_agent")
            self.logger.info(f"Turn 1 (Supervisor): {len(turn1_response)} chars")

            # Turn 2: Triage Agent - Specialization Assessment
            turn2_message = (
                "Given the Black Friday timeline pressure and the $2M revenue impact you mentioned, "
                "which technical areas should I prioritize: API optimization, caching strategy, "
                "or infrastructure scaling? Our current setup uses microservices with Redis."
            )

            turn2_events = await self._send_conversation_turn(
                websocket, "triage_agent", turn2_message, 2,
                {"timeline_pressure": "8_weeks", "prioritization_needed": True}
            )

            turn2_response = self._extract_response_content(turn2_events)
            conversation_responses.append(turn2_response)
            agent_sequence.append("triage_agent")
            self.logger.info(f"Turn 2 (Triage): {len(turn2_response)} chars")

            # Turn 3: APEX Optimizer - Technical Deep Dive
            turn3_message = (
                "Following your triage recommendation to focus on API optimization first, "
                "our recommendation engine currently makes 15-20 API calls per user session. "
                "During Black Friday's 10x traffic, this becomes 150-200 calls per user. "
                "What specific optimization techniques can handle this load?"
            )

            turn3_events = await self._send_conversation_turn(
                websocket, "apex_optimizer_agent", turn3_message, 3,
                {"technical_focus": "api_optimization", "load_multiplier": "10x_traffic"}
            )

            turn3_response = self._extract_response_content(turn3_events)
            conversation_responses.append(turn3_response)
            agent_sequence.append("apex_optimizer_agent")
            self.logger.info(f"Turn 3 (APEX): {len(turn3_response)} chars")

            # Turn 4: Data Helper - Impact Analysis
            turn4_message = (
                "Based on the API optimization strategies you outlined, "
                "can you help me calculate the potential cost and performance improvements? "
                "Last Black Friday we had 500K unique users, 2M page views, average 18 API calls per user. "
                "What would be the before/after metrics with your recommended optimizations?"
            )

            turn4_events = await self._send_conversation_turn(
                websocket, "data_helper_agent", turn4_message, 4,
                {"metrics_analysis": True, "historical_data": "500K_users_2M_pageviews"}
            )

            turn4_response = self._extract_response_content(turn4_events)
            conversation_responses.append(turn4_response)
            agent_sequence.append("data_helper_agent")
            self.logger.info(f"Turn 4 (Data Helper): {len(turn4_response)} chars")

            # Turn 5: Supervisor Agent - Final Synthesis
            turn5_message = (
                "Excellent analysis on the cost/performance projections. "
                "Now I need to present this to the executive team for Black Friday prep approval. "
                "Can you synthesize everything we've discussed into a clear action plan with "
                "timeline, resource requirements, and expected ROI for the $2M revenue protection?"
            )

            turn5_events = await self._send_conversation_turn(
                websocket, "supervisor_agent", turn5_message, 5,
                {"executive_summary": True, "synthesis_required": True}
            )

            turn5_response = self._extract_response_content(turn5_events)
            conversation_responses.append(turn5_response)
            agent_sequence.append("supervisor_agent")
            self.logger.info(f"Turn 5 (Supervisor Synthesis): {len(turn5_response)} chars")

            # Analyze cross-agent context continuity
            context_analysis = self._analyze_context_continuity(
                conversation_responses, conversation_elements
            )

            self.logger.info(f"📊 Cross-Agent Context Analysis:")
            self.logger.info(f"   Agent Sequence: {agent_sequence}")
            self.logger.info(f"   Context References: {context_analysis['context_references']}")
            self.logger.info(f"   Elements Maintained: {len(context_analysis['conversation_elements_maintained'])}")
            self.logger.info(f"   Coherence Score: {context_analysis['context_coherence_score']:.2f}")

            # Validate cross-agent context sharing
            assert context_analysis["context_references"] >= 4, (
                f"Cross-agent conversation should maintain context. "
                f"Found {context_analysis['context_references']} references"
            )

            # Check that different agents reference shared context
            for i, response in enumerate(conversation_responses[1:], 1):
                response_lower = response.lower()

                # Should reference Black Friday scenario
                assert "black friday" in response_lower, (
                    f"Turn {i+1} ({agent_sequence[i]}) should reference Black Friday context"
                )

                # Should reference either revenue impact or timeline
                context_refs = ["$2m", "2m", "revenue", "8 weeks", "timeline"]
                has_context = any(ref in response_lower for ref in context_refs)

                assert has_context, (
                    f"Turn {i+1} ({agent_sequence[i]}) should reference shared context elements. "
                    f"Sample: {response[:200]}..."
                )

            # Final synthesis should comprehensively reference conversation
            final_response = conversation_responses[-1].lower()
            synthesis_elements = ["black friday", "api", "optimization", "revenue", "timeline"]
            final_references = [elem for elem in synthesis_elements if elem in final_response]

            assert len(final_references) >= 4, (
                f"Final synthesis should reference comprehensive conversation context. "
                f"Found: {final_references} of {synthesis_elements}"
            )

            assert context_analysis["context_coherence_score"] >= 0.5, (
                f"Cross-agent context coherence insufficient: {context_analysis['context_coherence_score']:.2f}. "
                f"Different agents must share conversation memory effectively."
            )

            self.logger.info("✅ Cross-agent conversation memory validated")

        finally:
            await websocket.close()

    async def test_conversation_branching_and_context_recovery(self):
        """
        Test conversation branching and context recovery capabilities.

        CONTEXT VALIDATION: System should handle conversation branches and
        return to previous context threads without losing coherence.

        Branching Flow:
        1. Main conversation thread establishment
        2. Branch into specialized sub-topic
        3. Deep dive into branch topic
        4. Return to main thread with context recovery
        5. Continue main conversation with integrated insights

        DIFFICULTY: Very High (40 minutes)
        REAL SERVICES: Yes - Complex conversation state management
        STATUS: Should PASS - Advanced conversation handling for premium UX
        """
        self.logger.info("🔗 Testing conversation branching and context recovery")

        websocket = await self._establish_persistent_websocket_connection()

        try:
            conversation_responses = []
            main_context = ["startup scaling", "AI infrastructure", "cost management", "$50K budget"]
            branch_context = ["security compliance", "SOC2", "data encryption"]

            # Turn 1: Establish main conversation thread
            turn1_message = (
                "I'm scaling my AI startup from 20 to 100 employees over the next 6 months. "
                "Our current AI infrastructure costs $15K/month but we expect it to hit $50K "
                "with the growth. I need a comprehensive scaling strategy that balances "
                "performance, costs, and our upcoming SOC2 compliance requirements."
            )

            turn1_events = await self._send_conversation_turn(
                websocket, "supervisor_agent", turn1_message, 1,
                {"main_thread": True, "scaling_scenario": "20_to_100_employees"}
            )

            turn1_response = self._extract_response_content(turn1_events)
            conversation_responses.append(turn1_response)
            self.logger.info(f"Turn 1 (Main Thread): {len(turn1_response)} chars")

            # Turn 2: Branch into security/compliance topic
            turn2_message = (
                "Let me dive deeper into the SOC2 compliance aspect you mentioned. "
                "We're currently processing customer data through various AI models including "
                "OpenAI and Claude. What specific security measures and data handling "
                "procedures do we need for SOC2 Type II certification?"
            )

            turn2_events = await self._send_conversation_turn(
                websocket, "triage_agent", turn2_message, 2,
                {"branch_topic": "security_compliance", "certification": "SOC2_Type_II"}
            )

            turn2_response = self._extract_response_content(turn2_events)
            conversation_responses.append(turn2_response)
            self.logger.info(f"Turn 2 (Security Branch): {len(turn2_response)} chars")

            # Turn 3: Deep dive into branch topic
            turn3_message = (
                "The data encryption and audit logging requirements you outlined are extensive. "
                "Given that we're using cloud-based AI APIs, how do we maintain data encryption "
                "in transit and at rest while still getting the performance we need? "
                "Will this impact our API response times significantly?"
            )

            turn3_events = await self._send_conversation_turn(
                websocket, "apex_optimizer_agent", turn3_message, 3,
                {"deep_branch": True, "technical_focus": "encryption_performance"}
            )

            turn3_response = self._extract_response_content(turn3_events)
            conversation_responses.append(turn3_response)
            self.logger.info(f"Turn 3 (Deep Branch): {len(turn3_response)} chars")

            # Turn 4: Return to main thread with context recovery
            turn4_message = (
                "Great insights on the security implementation. Now, returning to our main "
                "scaling discussion, how do these SOC2 security requirements affect our "
                "$15K to $50K infrastructure scaling timeline? Will the additional security "
                "measures significantly impact our cost projections for the 100-employee target?"
            )

            turn4_events = await self._send_conversation_turn(
                websocket, "data_helper_agent", turn4_message, 4,
                {"return_to_main": True, "context_recovery": "scaling_with_security"}
            )

            turn4_response = self._extract_response_content(turn4_events)
            conversation_responses.append(turn4_response)
            self.logger.info(f"Turn 4 (Context Recovery): {len(turn4_response)} chars")

            # Turn 5: Continue main thread with integrated insights
            turn5_message = (
                "Perfect analysis of how security impacts our scaling costs. "
                "Now I can see the full picture: scaling from 20 to 100 employees, "
                "$15K to $50K infrastructure costs, plus SOC2 compliance overhead. "
                "What's the recommended implementation sequence to minimize business disruption "
                "while meeting our 6-month timeline?"
            )

            turn5_events = await self._send_conversation_turn(
                websocket, "supervisor_agent", turn5_message, 5,
                {"integrated_planning": True, "synthesis_with_branch": True}
            )

            turn5_response = self._extract_response_content(turn5_events)
            conversation_responses.append(turn5_response)
            self.logger.info(f"Turn 5 (Integrated Main): {len(turn5_response)} chars")

            # Analyze conversation branching and recovery
            context_analysis = self._analyze_context_continuity(
                conversation_responses, main_context + branch_context
            )

            # Specific analysis for branching behavior
            main_thread_recovery = 0
            branch_integration = 0

            for response in conversation_responses[3:]:  # Turns 4-5 should show recovery
                response_lower = response.lower()

                # Count main thread context recovery
                main_refs = sum(1 for elem in main_context if elem.lower() in response_lower)
                main_thread_recovery += main_refs

                # Count branch context integration
                branch_refs = sum(1 for elem in branch_context if elem.lower() in response_lower)
                branch_integration += branch_refs

            self.logger.info(f"📊 Conversation Branching Analysis:")
            self.logger.info(f"   Total Context References: {context_analysis['context_references']}")
            self.logger.info(f"   Main Thread Recovery: {main_thread_recovery}")
            self.logger.info(f"   Branch Integration: {branch_integration}")
            self.logger.info(f"   Coherence Score: {context_analysis['context_coherence_score']:.2f}")

            # Validate successful branching and recovery
            assert main_thread_recovery >= 3, (
                f"Should successfully recover main thread context. "
                f"Found {main_thread_recovery} main context references"
            )

            assert branch_integration >= 2, (
                f"Should integrate branch topic insights into main thread. "
                f"Found {branch_integration} branch context integrations"
            )

            # Turn 4 should demonstrate context recovery
            turn4_lower = conversation_responses[3].lower()
            recovery_indicators = ["scaling", "$15k", "$50k", "100 employees", "timeline"]
            recovered = [ind for ind in recovery_indicators if ind in turn4_lower]

            assert len(recovered) >= 3, (
                f"Turn 4 should recover main thread context effectively. "
                f"Recovered: {recovered} of {recovery_indicators}"
            )

            # Turn 5 should show integrated understanding
            turn5_lower = conversation_responses[4].lower()
            integration_elements = main_context + branch_context
            integrated = [elem.lower() for elem in integration_elements if elem.lower() in turn5_lower]

            assert len(integrated) >= 4, (
                f"Turn 5 should integrate both main and branch contexts. "
                f"Integrated: {integrated}"
            )

            assert context_analysis["context_coherence_score"] >= 0.45, (
                f"Branching conversation coherence insufficient: {context_analysis['context_coherence_score']:.2f}. "
                f"Complex conversation flows require strong context management."
            )

            self.logger.info("✅ Conversation branching and context recovery validated")

        finally:
            await websocket.close()


if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--tb=long",
        "-s",
        "--gcp-staging",
        "--agent-goldenpath"
    ])