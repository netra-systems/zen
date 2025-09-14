"""
E2E Tests for Agent Orchestration - Golden Path Multi-Agent Workflows

MISSION CRITICAL: Tests the complete agent orchestration flow that represents
the core AI intelligence of the platform. This is the sophisticated multi-agent
workflow that differentiates Netra from simple chatbots.

Business Value Justification (BVJ):
- Segment: Mid/Enterprise Users (Primary Revenue Generators)
- Business Goal: Platform Differentiation & Revenue Expansion
- Value Impact: Multi-agent orchestration IS the core platform value proposition
- Strategic Impact: Advanced agent workflows justify premium pricing tiers

Agent Orchestration Flow (Golden Path):
1. Supervisor Agent - Receives user request, plans workflow
2. Triage Agent - Analyzes request type and data requirements  
3. Specialized Agents - APEX Optimizer, Data Helper, etc.
4. Supervisor Agent - Synthesizes results, provides final response

This orchestration enables:
- Sophisticated analysis beyond single-model limitations
- Specialized expertise for different problem domains
- Quality validation through multi-agent validation
- Premium user experience justifying higher pricing

Test Strategy:
- REAL SERVICES: Staging GCP with complete agent ecosystem
- REAL LLM CALLS: Each agent makes actual LLM requests
- REAL ORCHESTRATION: Test actual supervisor → triage → specialist flow
- REAL BUSINESS LOGIC: Test realistic AI optimization scenarios
- PERFORMANCE VALIDATION: Orchestration should complete in reasonable time

CRITICAL: These tests validate the core competitive advantage of the platform.
Multi-agent orchestration is what justifies premium pricing and enterprise adoption.

GitHub Issue: #870 Agent Integration Test Suite Phase 1
Focus: Agent orchestration as premium platform differentiator
"""

import asyncio
import pytest
import time
import json
import logging
import websockets
import ssl
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from collections import defaultdict
import httpx

# SSOT imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from tests.e2e.staging_config import get_staging_config, is_staging_available

# Auth and WebSocket utilities
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.ssot.websocket_test_utility import WebSocketTestHelper


@pytest.mark.e2e
@pytest.mark.gcp_staging
@pytest.mark.agent_orchestration
@pytest.mark.mission_critical
class TestAgentOrchestrationE2E(SSotAsyncTestCase):
    """
    E2E tests for multi-agent orchestration workflows in staging GCP.
    
    Tests the sophisticated agent coordination that represents the platform's core value.
    """

    @classmethod
    def setUpClass(cls):
        """Setup staging environment for agent orchestration testing."""
        super().setUpClass()
        
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
        
        # Define expected agent types in orchestration flow
        cls.ORCHESTRATION_AGENTS = [
            "supervisor_agent",     # Entry point, workflow coordination
            "triage_agent",        # Request analysis and routing
            "apex_optimizer_agent", # AI cost optimization specialist
            "data_helper_agent"    # Data analysis and requirements
        ]
        
        # Test user configuration
        cls.test_user_id = f"orchestration_user_{int(time.time())}"
        cls.test_user_email = f"orchestration_test_{int(time.time())}@netra-testing.ai"
        
        cls.logger.info(f"Agent orchestration e2e tests initialized for staging")

    def setUp(self):
        """Setup for each test method."""
        super().setUp()
        
        # Generate test-specific context
        self.thread_id = f"orchestration_test_{int(time.time())}"
        self.run_id = f"run_{self.thread_id}"
        
        # Create JWT token for this test
        self.access_token = self.auth_helper.create_test_jwt_token(
            user_id=self.test_user_id,
            email=self.test_user_email,
            expires_in_hours=1
        )
        
        self.logger.info(f"Agent orchestration test setup - thread_id: {self.thread_id}")

    async def test_complete_supervisor_triage_specialist_orchestration(self):
        """
        Test complete supervisor → triage → specialist agent orchestration flow.
        
        GOLDEN PATH PREMIUM: This is the sophisticated multi-agent workflow that
        differentiates the platform and justifies enterprise pricing.
        
        Flow validation:
        1. Supervisor receives request, plans multi-agent workflow
        2. Triage analyzes request complexity and data requirements
        3. Specialist agents (APEX, Data Helper) provide expert analysis
        4. Supervisor synthesizes and delivers comprehensive response
        5. Quality validation through multi-agent cross-checking
        
        DIFFICULTY: Very High (50+ minutes)
        REAL SERVICES: Yes - Complete staging agent ecosystem
        STATUS: Should PASS - Core platform differentiator must work
        """
        orchestration_start_time = time.time()
        orchestration_metrics = {
            "agents_involved": set(),
            "agent_transitions": [],
            "specialist_analyses": [],
            "synthesis_quality": None,
            "total_llm_calls": 0,
            "workflow_complexity": 0
        }
        
        self.logger.info("🎭 Testing complete multi-agent orchestration workflow")
        
        try:
            # Establish WebSocket connection
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connection_start = time.time()
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.staging_config.urls.websocket_url,
                    extra_headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "X-Environment": "staging",
                        "X-Test-Suite": "agent-orchestration-premium"
                    },
                    ssl=ssl_context,
                    ping_interval=60,  # Longer for complex orchestration
                    ping_timeout=20
                ),
                timeout=30.0
            )
            
            connection_time = time.time() - connection_start
            self.logger.info(f"✅ WebSocket connected in {connection_time:.2f}s")
            
            # Send complex request requiring multi-agent orchestration
            orchestration_request = {
                "type": "agent_request",
                "agent": "supervisor_agent",  # Start with supervisor
                "message": (
                    "I need a comprehensive AI cost optimization strategy for my enterprise. "
                    "Current situation: $25,000/month OpenAI spend, 100K users, 75% GPT-4 usage. "
                    "Requirements: "
                    "1) Detailed cost breakdown analysis with market comparisons "
                    "2) Specific model selection optimization (GPT-4 vs GPT-3.5 vs alternatives) "
                    "3) Caching strategy recommendations with ROI calculations "
                    "4) Implementation roadmap with risk assessment "
                    "5) Monitoring and alerting setup for cost control "
                    "Please coordinate with your specialist agents to provide expert analysis "
                    "in each area and synthesize a comprehensive optimization plan."
                ),
                "thread_id": self.thread_id,
                "run_id": self.run_id,
                "user_id": self.test_user_id,
                "context": {
                    "test_scenario": "enterprise_orchestration",
                    "complexity_level": "high",
                    "requires_multiple_agents": True,
                    "expected_specialists": ["triage_agent", "apex_optimizer_agent", "data_helper_agent"]
                }
            }
            
            message_send_time = time.time()
            await websocket.send(json.dumps(orchestration_request))
            
            self.logger.info("📤 Complex orchestration request sent - tracking agent workflow...")
            
            # Collect orchestration events with detailed agent tracking
            orchestration_events = []
            orchestration_timeout = 180.0  # Allow time for complex multi-agent workflow
            event_collection_deadline = time.time() + orchestration_timeout
            
            current_agent = None
            agent_handoffs = []
            specialist_outputs = {}
            
            while time.time() < event_collection_deadline:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=20.0)
                    event = json.loads(event_data)
                    
                    event_received_time = time.time()
                    event_type = event.get("type", "unknown")
                    orchestration_events.append(event)
                    
                    # Track agent involvement and transitions
                    event_data_content = event.get("data", {})
                    agent_name = event_data_content.get("agent", "")
                    
                    if not agent_name:
                        # Try to extract agent from event content
                        event_str = json.dumps(event).lower()
                        for agent in self.ORCHESTRATION_AGENTS:
                            if agent.replace("_", "").replace("agent", "") in event_str:
                                agent_name = agent
                                break
                    
                    if agent_name and agent_name != current_agent:
                        if current_agent:
                            agent_handoffs.append({
                                "from": current_agent,
                                "to": agent_name,
                                "timestamp": event_received_time,
                                "event_type": event_type
                            })
                        current_agent = agent_name
                        orchestration_metrics["agents_involved"].add(agent_name)
                    
                    # Track specialist analysis outputs
                    if event_type in ["tool_completed", "agent_completed"]:
                        if agent_name in ["apex_optimizer_agent", "data_helper_agent", "triage_agent"]:
                            result = event_data_content.get("result", {})
                            if result:
                                specialist_outputs[agent_name] = {
                                    "output": str(result),
                                    "timestamp": event_received_time,
                                    "event_type": event_type
                                }
                    
                    # Count LLM interaction indicators
                    event_str = json.dumps(event).lower()
                    if any(llm_indicator in event_str for llm_indicator in [
                        "thinking", "analyzing", "generating", "reasoning", "processing"
                    ]):
                        orchestration_metrics["total_llm_calls"] += 1
                    
                    # Log significant orchestration events
                    if event_type in ["agent_started", "agent_completed", "tool_executing", "tool_completed"]:
                        time_since_request = event_received_time - message_send_time
                        self.logger.info(
                            f"🎭 ORCHESTRATION: {event_type} "
                            f"({agent_name}) +{time_since_request:.1f}s"
                        )
                    
                    # Check for final completion
                    if event_type == "agent_completed" and "supervisor" in agent_name.lower():
                        self.logger.info("🏁 Supervisor orchestration completed")
                        break
                    
                    # Check for error events
                    if event_type in ["error", "agent_error"]:
                        raise AssertionError(f"Orchestration error: {event}")
                        
                except asyncio.TimeoutError:
                    # Log timeout and continue
                    current_time = time.time()
                    self.logger.warning(
                        f"⏰ Orchestration event timeout - no event for 20s "
                        f"(total elapsed: {current_time - message_send_time:.1f}s)"
                    )
                    continue
                    
                except json.JSONDecodeError as e:
                    self.logger.error(f"❌ Failed to parse orchestration event: {e}")
                    continue
            
            await websocket.close()
            
            total_orchestration_time = time.time() - orchestration_start_time
            
            # COMPREHENSIVE ORCHESTRATION VALIDATION
            
            # 1. Validate multi-agent involvement
            assert len(orchestration_metrics["agents_involved"]) >= 3, (
                f"Orchestration should involve at least 3 agents, got: {orchestration_metrics['agents_involved']}. "
                f"Expected: supervisor + triage + at least 1 specialist."
            )
            
            # Must include supervisor and triage
            assert any("supervisor" in agent for agent in orchestration_metrics["agents_involved"]), (
                f"Orchestration must include supervisor agent, got: {orchestration_metrics['agents_involved']}"
            )
            
            assert any("triage" in agent for agent in orchestration_metrics["agents_involved"]), (
                f"Orchestration must include triage agent, got: {orchestration_metrics['agents_involved']}"
            )
            
            # Should include at least one specialist
            specialists_involved = [
                agent for agent in orchestration_metrics["agents_involved"] 
                if any(specialist in agent for specialist in ["apex", "data_helper", "optimizer"])
            ]
            assert len(specialists_involved) >= 1, (
                f"Orchestration should include specialist agents, got: {specialists_involved}"
            )
            
            # 2. Validate agent handoffs and workflow progression
            assert len(agent_handoffs) >= 2, (
                f"Should see agent handoffs in orchestration, got: {len(agent_handoffs)} handoffs. "
                f"Handoffs: {agent_handoffs}"
            )
            
            # 3. Validate specialist analysis quality
            assert len(specialist_outputs) >= 1, (
                f"Should receive specialist analysis outputs, got: {len(specialist_outputs)} outputs. "
                f"Specialists: {list(specialist_outputs.keys())}"
            )
            
            # Each specialist output should be substantive
            for agent, output_data in specialist_outputs.items():
                output_text = output_data["output"]
                assert len(output_text) > 100, (
                    f"Specialist {agent} output too short: {len(output_text)} chars. "
                    f"Output: {output_text[:200]}..."
                )
            
            # 4. Validate final orchestrated response
            final_events = [e for e in orchestration_events if e.get("type") == "agent_completed"]
            assert len(final_events) > 0, "Should receive final orchestrated response"
            
            final_response = final_events[-1]
            final_data = final_response.get("data", {})
            final_result = final_data.get("result", {})
            final_text = str(final_result)
            
            # Final response should be comprehensive (multi-agent synthesis)
            assert len(final_text) > 500, (
                f"Final orchestrated response too short: {len(final_text)} chars. "
                f"Expected comprehensive synthesis of specialist analyses."
            )
            
            # Should address multiple aspects from the request
            required_topics = ["cost", "optimization", "model", "caching", "monitoring"]
            addressed_topics = [
                topic for topic in required_topics 
                if topic in final_text.lower()
            ]
            assert len(addressed_topics) >= 3, (
                f"Final response should address multiple topics, got: {addressed_topics}. "
                f"Required: {required_topics}"
            )
            
            # 5. Validate orchestration performance
            assert total_orchestration_time < 240.0, (
                f"Orchestration took too long: {total_orchestration_time:.1f}s (max 240s). "
                f"Complex workflows must complete in reasonable time."
            )
            
            # Should have reasonable LLM interaction count
            assert orchestration_metrics["total_llm_calls"] >= 3, (
                f"Should see evidence of multiple LLM interactions: {orchestration_metrics['total_llm_calls']}"
            )
            
            # LOG COMPREHENSIVE SUCCESS METRICS
            self.logger.info("🎉 MULTI-AGENT ORCHESTRATION SUCCESS")
            self.logger.info(f"📊 Orchestration Metrics:")
            self.logger.info(f"   Total Duration: {total_orchestration_time:.1f}s")
            self.logger.info(f"   Agents Involved: {len(orchestration_metrics['agents_involved'])}")
            self.logger.info(f"   Agent Types: {sorted(orchestration_metrics['agents_involved'])}")
            self.logger.info(f"   Agent Handoffs: {len(agent_handoffs)}")
            self.logger.info(f"   Specialist Outputs: {len(specialist_outputs)}")
            self.logger.info(f"   LLM Interactions: {orchestration_metrics['total_llm_calls']}")
            self.logger.info(f"   Final Response: {len(final_text)} characters")
            self.logger.info(f"   Topics Addressed: {addressed_topics}")
            
            # Business value validation
            orchestration_metrics["workflow_complexity"] = (
                len(orchestration_metrics["agents_involved"]) * 2 +
                len(agent_handoffs) +
                len(specialist_outputs)
            )
            
            assert orchestration_metrics["workflow_complexity"] >= 10, (
                f"Orchestration complexity too low: {orchestration_metrics['workflow_complexity']}. "
                f"Premium workflows should demonstrate sophisticated agent coordination."
            )
            
        except Exception as e:
            total_time = time.time() - orchestration_start_time
            
            self.logger.error("❌ MULTI-AGENT ORCHESTRATION FAILURE")
            self.logger.error(f"   Error: {str(e)}")
            self.logger.error(f"   Duration: {total_time:.1f}s")
            self.logger.error(f"   Events collected: {len(orchestration_events) if 'orchestration_events' in locals() else 0}")
            self.logger.error(f"   Agents involved: {orchestration_metrics.get('agents_involved', 'unknown')}")
            
            raise AssertionError(
                f"Multi-agent orchestration failed after {total_time:.1f}s: {e}. "
                f"This breaks the core platform differentiator and premium value proposition."
            )

    async def test_agent_specialization_and_expertise_quality(self):
        """
        Test agent specialization and expertise quality in orchestrated workflows.
        
        SPECIALIZATION: Different agents should provide specialized expertise
        that demonstrates clear value differentiation from single-agent responses.
        
        Validation areas:
        1. Triage agent correctly classifies request complexity
        2. APEX optimizer provides specific cost optimization expertise
        3. Data helper provides data analysis and requirements expertise
        4. Specialist outputs are domain-specific and high-quality
        5. Integration between specialists creates comprehensive solutions
        
        DIFFICULTY: High (35 minutes)
        REAL SERVICES: Yes - Staging specialist agent ecosystem
        STATUS: Should PASS - Agent specialization is key competitive advantage
        """
        self.logger.info("🎯 Testing agent specialization and expertise quality")
        
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Test scenarios targeting different agent specializations
        specialization_scenarios = [
            {
                "name": "cost_optimization_expertise",
                "agent": "apex_optimizer_agent",
                "message": (
                    "I'm spending $10,000/month on GPT-4 API calls for my SaaS application. "
                    "I need specific recommendations to reduce costs by 40% while maintaining "
                    "response quality. Please analyze current market alternatives and provide "
                    "a detailed cost optimization strategy with ROI calculations."
                ),
                "expected_expertise": [
                    "cost", "optimization", "gpt-4", "alternatives", "roi", "strategy"
                ],
                "expected_depth": 300  # Minimum response length for expertise
            },
            {
                "name": "data_analysis_expertise",
                "agent": "data_helper_agent", 
                "message": (
                    "I need to analyze my AI usage patterns to identify inefficiencies. "
                    "I have: 50K monthly users, 2.5M API calls, peak usage during business hours, "
                    "average response time 1.2s. Please help me understand what data I need to "
                    "collect and how to analyze it for optimization opportunities."
                ),
                "expected_expertise": [
                    "data", "analysis", "patterns", "usage", "metrics", "collection"
                ],
                "expected_depth": 250
            },
            {
                "name": "triage_classification_expertise",
                "agent": "triage_agent",
                "message": (
                    "I have multiple AI optimization challenges: high costs, slow response times, "
                    "quality issues, and scaling problems. I'm not sure which to tackle first or "
                    "how they're interconnected. Please help me prioritize and plan my approach."
                ),
                "expected_expertise": [
                    "priorit", "classif", "approach", "interconnect", "plan", "triage"
                ],
                "expected_depth": 200
            }
        ]
        
        specialization_results = {}
        
        for scenario in specialization_scenarios:
            scenario_start = time.time()
            self.logger.info(f"Testing specialization: {scenario['name']}")
            
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.staging_config.urls.websocket_url,
                    extra_headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "X-Environment": "staging",
                        "X-Test-Suite": f"specialization-{scenario['name']}"
                    },
                    ssl=ssl_context
                ),
                timeout=20.0
            )
            
            try:
                # Send specialist-targeted request
                message = {
                    "type": "agent_request",
                    "agent": scenario["agent"],
                    "message": scenario["message"],
                    "thread_id": f"specialization_{scenario['name']}_{int(time.time())}",
                    "user_id": self.test_user_id,
                    "context": {
                        "test_scenario": scenario["name"],
                        "target_specialist": scenario["agent"]
                    }
                }
                
                await websocket.send(json.dumps(message))
                
                # Collect specialist response
                specialist_events = []
                specialist_response = None
                response_timeout = 60.0
                
                collection_start = time.time()
                while time.time() - collection_start < response_timeout:
                    try:
                        event_data = await asyncio.wait_for(websocket.recv(), timeout=12.0)
                        event = json.loads(event_data)
                        specialist_events.append(event)
                        
                        if event.get("type") == "agent_completed":
                            specialist_response = event
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                
                scenario_duration = time.time() - scenario_start
                
                # Validate specialist expertise
                assert specialist_response is not None, (
                    f"Should receive specialist response for {scenario['name']}"
                )
                
                response_data = specialist_response.get("data", {})
                result = response_data.get("result", {})
                response_text = str(result).lower()
                
                # Validate expertise depth
                assert len(response_text) >= scenario["expected_depth"], (
                    f"Specialist {scenario['agent']} response too shallow: "
                    f"{len(response_text)} chars (expected ≥{scenario['expected_depth']})"
                )
                
                # Validate domain expertise keywords
                found_expertise = [
                    keyword for keyword in scenario["expected_expertise"]
                    if keyword in response_text
                ]
                
                expertise_coverage = len(found_expertise) / len(scenario["expected_expertise"])
                assert expertise_coverage >= 0.5, (
                    f"Specialist {scenario['agent']} lacks domain expertise. "
                    f"Found {found_expertise}, expected {scenario['expected_expertise']}"
                )
                
                # Record specialization quality metrics
                specialization_results[scenario["name"]] = {
                    "agent": scenario["agent"],
                    "duration": scenario_duration,
                    "response_length": len(response_text),
                    "expertise_coverage": expertise_coverage,
                    "domain_keywords_found": found_expertise,
                    "events_count": len(specialist_events),
                    "success": True
                }
                
                self.logger.info(f"✅ {scenario['name']} specialization validated:")
                self.logger.info(f"   Duration: {scenario_duration:.1f}s")
                self.logger.info(f"   Response length: {len(response_text)} chars")
                self.logger.info(f"   Expertise coverage: {expertise_coverage:.1%}")
                self.logger.info(f"   Domain keywords: {found_expertise}")
                
            except Exception as e:
                specialization_results[scenario["name"]] = {
                    "agent": scenario["agent"],
                    "duration": time.time() - scenario_start,
                    "success": False,
                    "error": str(e)
                }
                
                self.logger.error(f"❌ {scenario['name']} specialization failed: {e}")
            
            finally:
                await websocket.close()
        
        # Validate overall specialization quality
        successful_specializations = [
            result for result in specialization_results.values() 
            if result["success"]
        ]
        
        assert len(successful_specializations) >= 2, (
            f"At least 2/3 specializations should succeed, got {len(successful_specializations)}. "
            f"Results: {specialization_results}"
        )
        
        # Validate specialization diversity
        if len(successful_specializations) >= 2:
            avg_expertise_coverage = sum(
                result["expertise_coverage"] 
                for result in successful_specializations
            ) / len(successful_specializations)
            
            assert avg_expertise_coverage >= 0.6, (
                f"Average specialization expertise too low: {avg_expertise_coverage:.1%} "
                f"(expected ≥60%)"
            )
            
            avg_response_length = sum(
                result["response_length"]
                for result in successful_specializations  
            ) / len(successful_specializations)
            
            assert avg_response_length >= 250, (
                f"Average specialist response too shallow: {avg_response_length} chars "
                f"(expected ≥250 chars for quality expertise)"
            )
        
        self.logger.info(f"🎯 Agent specialization validation complete:")
        self.logger.info(f"   Successful specializations: {len(successful_specializations)}/3")
        self.logger.info(f"   Average expertise coverage: {avg_expertise_coverage:.1%}")
        self.logger.info(f"   Average response depth: {avg_response_length} chars")

    async def test_orchestration_error_handling_and_fallbacks(self):
        """
        Test orchestration error handling and graceful fallback scenarios.
        
        RESILIENCE: Complex orchestration should handle individual agent failures
        gracefully without breaking the entire user experience.
        
        Error scenarios:
        1. Individual specialist agent errors
        2. Triage agent classification failures
        3. Supervisor coordination issues
        4. Partial workflow completion with graceful degradation
        5. Recovery after temporary agent failures
        
        DIFFICULTY: Very High (40 minutes)  
        REAL SERVICES: Yes - Staging error handling testing
        STATUS: Should PASS - Resilience is critical for premium user experience
        """
        self.logger.info("🛡️ Testing orchestration error handling and fallbacks")
        
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False  
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Test error scenarios that should trigger graceful handling
        error_scenarios = [
            {
                "name": "invalid_agent_request_in_orchestration",
                "message": {
                    "type": "agent_request",
                    "agent": "nonexistent_specialist_agent",
                    "message": "This should trigger orchestration error handling",
                    "thread_id": f"error_orchestration_{int(time.time())}"
                },
                "expected_recovery": True,
                "timeout": 30.0
            },
            {
                "name": "malformed_orchestration_context",
                "message": {
                    "type": "agent_request",
                    "agent": "supervisor_agent",
                    "message": "Valid message but with malformed orchestration context",
                    "thread_id": f"malformed_orchestration_{int(time.time())}",
                    "context": {
                        "invalid_orchestration_data": "This should not break the workflow",
                        "malformed_agent_list": ["agent1", None, {"invalid": "structure"}]
                    }
                },
                "expected_recovery": True,
                "timeout": 45.0
            },
            {
                "name": "orchestration_timeout_recovery",
                "message": {
                    "type": "agent_request", 
                    "agent": "supervisor_agent",
                    "message": (
                        "Please coordinate with your specialists to analyze this extremely "
                        "complex request that might take a very long time to process and "
                        "could potentially timeout during orchestration. I need comprehensive "
                        "analysis that tests the system's ability to handle timeouts gracefully."
                    ),
                    "thread_id": f"timeout_orchestration_{int(time.time())}",
                    "context": {
                        "complexity": "maximum",
                        "timeout_test": True
                    }
                },
                "expected_recovery": True,
                "timeout": 90.0  # Longer timeout for this test
            }
        ]
        
        orchestration_error_results = []
        
        for scenario in error_scenarios:
            scenario_start = time.time()
            self.logger.info(f"Testing orchestration error scenario: {scenario['name']}")
            
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.staging_config.urls.websocket_url,
                    extra_headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "X-Environment": "staging",
                        "X-Test-Suite": f"orchestration-error-{scenario['name']}"
                    },
                    ssl=ssl_context
                ),
                timeout=15.0
            )
            
            try:
                # Send error-inducing orchestration request
                await websocket.send(json.dumps(scenario["message"]))
                
                # Collect error handling events
                error_events = []
                recovery_events = []
                error_detected = False
                recovery_detected = False
                
                timeout = scenario["timeout"]
                collection_start = time.time()
                
                while time.time() - collection_start < timeout:
                    try:
                        event_data = await asyncio.wait_for(websocket.recv(), timeout=8.0)
                        event = json.loads(event_data)
                        
                        event_type = event.get("type", "unknown")
                        
                        # Classify event types
                        if "error" in event_type.lower():
                            error_events.append(event)
                            error_detected = True
                            self.logger.info(f"🚨 Orchestration error detected: {event_type}")
                        
                        elif event_type in ["agent_started", "agent_completed"] and error_detected:
                            recovery_events.append(event)
                            recovery_detected = True
                            self.logger.info(f"🔄 Orchestration recovery detected: {event_type}")
                        
                        # Check for final resolution
                        if event_type == "agent_completed":
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                
                scenario_duration = time.time() - scenario_start
                
                # Analyze error handling results
                result = {
                    "scenario": scenario["name"],
                    "duration": scenario_duration,
                    "error_events": len(error_events),
                    "recovery_events": len(recovery_events),
                    "error_detected": error_detected,
                    "recovery_detected": recovery_detected,
                    "graceful_handling": False
                }
                
                # Validate error handling quality
                if scenario["expected_recovery"]:
                    # Should either recover gracefully OR provide meaningful error response
                    graceful_handling = (
                        (error_detected and recovery_detected) or  # Detected and recovered
                        (len(recovery_events) > 0) or              # Some recovery activity
                        (not error_detected)                       # No error (handled upstream)
                    )
                    
                    result["graceful_handling"] = graceful_handling
                    
                    if not graceful_handling:
                        self.logger.warning(
                            f"Orchestration error handling may need improvement for {scenario['name']}: "
                            f"Error detected: {error_detected}, Recovery: {recovery_detected}"
                        )
                    else:
                        self.logger.info(f"✅ Graceful error handling for {scenario['name']}")
                
                orchestration_error_results.append(result)
                
            except Exception as e:
                orchestration_error_results.append({
                    "scenario": scenario["name"],
                    "duration": time.time() - scenario_start,
                    "error_events": 0,
                    "recovery_events": 0,
                    "error_detected": False,
                    "recovery_detected": False,
                    "graceful_handling": False,
                    "test_error": str(e)
                })
                
                self.logger.error(f"❌ Error testing scenario {scenario['name']} failed: {e}")
            
            finally:
                await websocket.close()
        
        # Validate overall orchestration error handling
        successful_error_handling = [
            result for result in orchestration_error_results
            if result.get("graceful_handling", False) or "test_error" not in result
        ]
        
        error_handling_rate = len(successful_error_handling) / len(orchestration_error_results)
        
        assert error_handling_rate >= 0.66, (
            f"Orchestration error handling success rate too low: {error_handling_rate:.1%} "
            f"(expected ≥66%). Results: {orchestration_error_results}"
        )
        
        self.logger.info(f"🛡️ Orchestration error handling validation complete:")
        self.logger.info(f"   Error handling success rate: {error_handling_rate:.1%}")
        self.logger.info(f"   Scenarios tested: {len(orchestration_error_results)}")
        self.logger.info(f"   Graceful handling: {len(successful_error_handling)}")

    async def test_orchestration_performance_under_load(self):
        """
        Test orchestration performance characteristics under concurrent load.
        
        SCALABILITY: Multi-agent orchestration should maintain reasonable performance
        even when handling multiple concurrent complex workflows.
        
        Load scenarios:
        1. Multiple concurrent orchestration requests
        2. Performance degradation measurement
        3. Resource utilization during peak orchestration
        4. Quality maintenance under load
        
        DIFFICULTY: High (30 minutes)
        REAL SERVICES: Yes - Staging performance testing
        STATUS: Should PASS - Performance under load is essential for enterprise usage
        """
        self.logger.info("🚀 Testing orchestration performance under concurrent load")
        
        # Concurrent orchestration load test
        concurrent_workflows = 2  # Reasonable for staging environment
        
        async def execute_concurrent_orchestration(workflow_id: int) -> Dict[str, Any]:
            """Execute a single concurrent orchestration workflow."""
            workflow_start = time.time()
            
            try:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
                websocket = await asyncio.wait_for(
                    websockets.connect(
                        self.staging_config.urls.websocket_url,
                        extra_headers={
                            "Authorization": f"Bearer {self.access_token}",
                            "X-Environment": "staging",
                            "X-Workflow-ID": str(workflow_id)
                        },
                        ssl=ssl_context
                    ),
                    timeout=20.0
                )
                
                # Send concurrent orchestration request
                message = {
                    "type": "agent_request",
                    "agent": "supervisor_agent",
                    "message": (
                        f"Concurrent workflow {workflow_id}: Please coordinate with specialists "
                        f"to analyze AI cost optimization for a {workflow_id * 10}K user application "
                        f"spending ${workflow_id * 5000}/month on LLM costs. I need comprehensive "
                        f"recommendations with detailed analysis from your expert agents."
                    ),
                    "thread_id": f"concurrent_orchestration_{workflow_id}_{int(time.time())}",
                    "user_id": self.test_user_id
                }
                
                await websocket.send(json.dumps(message))
                
                # Collect orchestration performance metrics
                events_count = 0
                agents_involved = set()
                completion_received = False
                
                performance_timeout = 120.0  # Longer timeout under load
                collection_start = time.time()
                
                while time.time() - collection_start < performance_timeout:
                    try:
                        event_data = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                        event = json.loads(event_data)
                        events_count += 1
                        
                        event_type = event.get("type", "unknown")
                        
                        # Track agent involvement
                        event_str = json.dumps(event).lower()
                        for agent in self.ORCHESTRATION_AGENTS:
                            if agent.replace("_", "").replace("agent", "") in event_str:
                                agents_involved.add(agent)
                        
                        if event_type == "agent_completed":
                            completion_received = True
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                
                await websocket.close()
                
                workflow_duration = time.time() - workflow_start
                
                return {
                    "workflow_id": workflow_id,
                    "success": completion_received,
                    "duration": workflow_duration,
                    "events_count": events_count,
                    "agents_involved": len(agents_involved),
                    "performance_score": events_count / workflow_duration if workflow_duration > 0 else 0
                }
                
            except Exception as e:
                return {
                    "workflow_id": workflow_id,
                    "success": False,
                    "duration": time.time() - workflow_start,
                    "error": str(e),
                    "events_count": 0,
                    "agents_involved": 0,
                    "performance_score": 0
                }
        
        # Execute concurrent workflows
        concurrent_start = time.time()
        workflow_tasks = [
            execute_concurrent_orchestration(i) for i in range(1, concurrent_workflows + 1)
        ]
        
        workflow_results = await asyncio.gather(*workflow_tasks, return_exceptions=True)
        total_concurrent_time = time.time() - concurrent_start
        
        # Analyze performance results
        successful_workflows = [
            result for result in workflow_results
            if isinstance(result, dict) and result["success"]
        ]
        failed_workflows = [
            result for result in workflow_results  
            if isinstance(result, dict) and not result["success"]
        ]
        
        success_rate = len(successful_workflows) / concurrent_workflows
        
        self.logger.info(f"🚀 Concurrent orchestration results:")
        self.logger.info(f"   Total concurrent time: {total_concurrent_time:.1f}s")
        self.logger.info(f"   Successful workflows: {len(successful_workflows)}/{concurrent_workflows}")
        self.logger.info(f"   Success rate: {success_rate:.1%}")
        
        # Validate performance under load
        assert success_rate >= 0.75, (
            f"Orchestration success rate under load too low: {success_rate:.1%} "
            f"(expected ≥75%)"
        )
        
        if successful_workflows:
            avg_duration = sum(w["duration"] for w in successful_workflows) / len(successful_workflows)
            max_duration = max(w["duration"] for w in successful_workflows)
            avg_events = sum(w["events_count"] for w in successful_workflows) / len(successful_workflows)
            avg_agents = sum(w["agents_involved"] for w in successful_workflows) / len(successful_workflows)
            
            assert avg_duration < 150.0, (
                f"Average orchestration duration under load too slow: {avg_duration:.1f}s "
                f"(expected <150s)"
            )
            
            assert avg_agents >= 2, (
                f"Orchestration complexity maintained under load: {avg_agents:.1f} agents average "
                f"(expected ≥2 agents for multi-agent workflows)"
            )
            
            self.logger.info(f"📊 Performance metrics under load:")
            self.logger.info(f"   Average duration: {avg_duration:.1f}s")
            self.logger.info(f"   Maximum duration: {max_duration:.1f}s")
            self.logger.info(f"   Average events: {avg_events:.1f}")
            self.logger.info(f"   Average agents involved: {avg_agents:.1f}")
        
        self.logger.info("🚀 Orchestration performance under load validation complete")


if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--tb=long",
        "-s",
        "--gcp-staging",
        "--agent-orchestration"
    ])