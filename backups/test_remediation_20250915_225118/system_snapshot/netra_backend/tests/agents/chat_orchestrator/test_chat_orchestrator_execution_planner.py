"""
Comprehensive unit tests for ChatOrchestrator execution planning module.

Business Value: Tests the execution planning logic that generates dynamic agent pipelines
based on user intent and confidence levels, ensuring optimal resource allocation and
workflow orchestration for chat responses.

Coverage Areas:
- Execution plan generation for all intent types
- Confidence-based research step inclusion logic
- Domain expert routing for specialized intents
- Analysis step orchestration for complex queries
- Validation step consistency across all plans
- Edge cases and error handling

SSOT Compliance: Uses SSotAsyncTestCase, real ExecutionContext, no mocks for core logic
"""

import asyncio
import pytest
import unittest
from typing import Dict, List
from unittest.mock import MagicMock
from dataclasses import dataclass

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory
from netra_backend.app.agents.chat_orchestrator.execution_planner import ExecutionPlanner
from netra_backend.app.agents.chat_orchestrator.intent_classifier import IntentType
from netra_backend.app.agents.chat_orchestrator.confidence_manager import ConfidenceLevel
from netra_backend.app.agents.base.interface import ExecutionContext


@dataclass
class AgentState:
    """Simple agent state for testing ExecutionPlanner."""
    user_request: str = ""
    accumulated_data: dict = None

    def __post_init__(self):
        if self.accumulated_data is None:
            self.accumulated_data = {}


class ChatOrchestratorExecutionPlannerTests(SSotAsyncTestCase, unittest.TestCase):
    """Comprehensive tests for ChatOrchestrator execution planning business logic."""

    def setUp(self):
        """Set up test environment with real services."""
        super().setUp()
        self.planner = ExecutionPlanner()
        self.mock_factory = SSotMockFactory()

    def create_execution_context(self, user_request: str = "test request") -> ExecutionContext:
        """Create ExecutionContext for testing."""
        state = AgentState(user_request=user_request)
        context = ExecutionContext(
            session_id="test_session",
            run_id="test_run",
            state=state,
            user_id="test_user"
        )
        return context

    def test_init_domain_mappings(self):
        """Test initialization of intent to domain mappings."""
        expected_mappings = {
            IntentType.TCO_ANALYSIS: "finance",
            IntentType.OPTIMIZATION_ADVICE: "engineering", 
            IntentType.MARKET_RESEARCH: "business",
            IntentType.PRICING_INQUIRY: "pricing",
            IntentType.BENCHMARKING: "performance",
        }
        
        self.assertEqual(self.planner.domain_mapping, expected_mappings)

    def test_init_intent_requirements(self):
        """Test initialization of intent-specific requirements."""
        self.assertEqual(
            self.planner.volatile_intents, 
            [IntentType.PRICING_INQUIRY, IntentType.BENCHMARKING]
        )
        self.assertEqual(
            self.planner.complex_intents, 
            [IntentType.TCO_ANALYSIS, IntentType.BENCHMARKING]
        )
        self.assertEqual(
            self.planner.domain_intents, 
            [IntentType.TCO_ANALYSIS, IntentType.OPTIMIZATION_ADVICE]
        )

    async def test_generate_plan_high_confidence_simple_intent(self):
        """Test plan generation for high confidence, simple intent."""
        context = self.create_execution_context("What is market research?")
        intent = IntentType.MARKET_RESEARCH
        confidence = ConfidenceLevel.HIGH.value

        plan = await self.planner.generate_plan(context, intent, confidence)
        
        # Should have validation step only (no research needed for high confidence)
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["agent"], "validator")
        self.assertEqual(plan[0]["action"], "validate_response")

    async def test_generate_plan_low_confidence_requires_research(self):
        """Test plan generation for low confidence requiring research."""
        context = self.create_execution_context("Complex market analysis needed")
        intent = IntentType.MARKET_RESEARCH
        confidence = ConfidenceLevel.LOW.value

        plan = await self.planner.generate_plan(context, intent, confidence)
        
        # Should have research step + validation
        self.assertGreaterEqual(len(plan), 2)
        research_step = next(step for step in plan if step["agent"] == "researcher")
        self.assertEqual(research_step["action"], "deep_research")
        self.assertEqual(research_step["params"]["intent"], intent.value)
        self.assertTrue(research_step["params"]["require_citations"])

    async def test_generate_plan_volatile_intent_always_research(self):
        """Test that volatile intents always require research regardless of confidence."""
        context = self.create_execution_context("Current pricing information")
        intent = IntentType.PRICING_INQUIRY
        confidence = ConfidenceLevel.VERY_HIGH.value  # Even very high confidence

        plan = await self.planner.generate_plan(context, intent, confidence)
        
        # Should have research step for volatile intent
        research_step = next((step for step in plan if step["agent"] == "researcher"), None)
        self.assertIsNotNone(research_step, "Volatile intents should always include research")

    async def test_generate_plan_domain_intent_includes_domain_expert(self):
        """Test that domain intents include domain expert step."""
        context = self.create_execution_context("TCO analysis needed")
        intent = IntentType.TCO_ANALYSIS
        confidence = ConfidenceLevel.HIGH.value

        plan = await self.planner.generate_plan(context, intent, confidence)
        
        # Should have domain expert step
        domain_step = next((step for step in plan if step["agent"] == "domain_expert"), None)
        self.assertIsNotNone(domain_step, "Domain intents should include domain expert")
        self.assertEqual(domain_step["action"], "validate_requirements")
        self.assertEqual(domain_step["params"]["domain"], "finance")

    async def test_generate_plan_complex_intent_includes_analysis(self):
        """Test that complex intents include analysis step."""
        context = self.create_execution_context("Comprehensive benchmarking analysis")
        intent = IntentType.BENCHMARKING
        confidence = ConfidenceLevel.HIGH.value

        plan = await self.planner.generate_plan(context, intent, confidence)
        
        # Should have analysis step
        analysis_step = next((step for step in plan if step["agent"] == "analyst"), None)
        self.assertIsNotNone(analysis_step, "Complex intents should include analysis")
        self.assertEqual(analysis_step["action"], "perform_analysis")
        self.assertEqual(analysis_step["params"]["analysis_type"], intent.value)

    async def test_generate_plan_comprehensive_tco_analysis(self):
        """Test comprehensive plan for TCO analysis (domain + complex intent)."""
        context = self.create_execution_context("Full TCO analysis for cloud migration")
        intent = IntentType.TCO_ANALYSIS
        confidence = ConfidenceLevel.LOW.value

        plan = await self.planner.generate_plan(context, intent, confidence)
        
        # Should have all steps: research + domain + analysis + validation
        agent_types = [step["agent"] for step in plan]
        
        self.assertIn("researcher", agent_types, "Should include research for low confidence")
        self.assertIn("domain_expert", agent_types, "Should include domain expert for TCO")
        self.assertIn("analyst", agent_types, "Should include analyst for complex intent")
        self.assertIn("validator", agent_types, "Should always include validation")

    def test_needs_research_low_confidence(self):
        """Test research requirement based on confidence levels."""
        # Low confidence should need research
        self.assertTrue(
            self.planner._needs_research(IntentType.GENERAL_INQUIRY, ConfidenceLevel.LOW.value)
        )
        
        # Medium confidence should need research
        self.assertTrue(
            self.planner._needs_research(IntentType.GENERAL_INQUIRY, ConfidenceLevel.MEDIUM.value)
        )
        
        # High confidence should not need research for non-volatile intent
        self.assertFalse(
            self.planner._needs_research(IntentType.GENERAL_INQUIRY, ConfidenceLevel.HIGH.value)
        )

    def test_needs_research_volatile_intents(self):
        """Test that volatile intents always need research."""
        for volatile_intent in self.planner.volatile_intents:
            # Even very high confidence volatile intents need research
            self.assertTrue(
                self.planner._needs_research(volatile_intent, ConfidenceLevel.VERY_HIGH.value),
                f"{volatile_intent} should always need research"
            )

    def test_create_research_step_format(self):
        """Test research step creation format."""
        step = self.planner._create_research_step(IntentType.MARKET_RESEARCH)
        
        expected_step = {
            "agent": "researcher",
            "action": "deep_research",
            "params": {
                "intent": IntentType.MARKET_RESEARCH.value,
                "require_citations": True
            }
        }
        
        self.assertEqual(step, expected_step)

    def test_create_domain_step_format(self):
        """Test domain expert step creation format."""
        step = self.planner._create_domain_step("finance")
        
        expected_step = {
            "agent": "domain_expert",
            "action": "validate_requirements",
            "params": {"domain": "finance"}
        }
        
        self.assertEqual(step, expected_step)

    def test_create_analysis_step_format(self):
        """Test analysis step creation format."""
        step = self.planner._create_analysis_step(IntentType.BENCHMARKING)
        
        expected_step = {
            "agent": "analyst", 
            "action": "perform_analysis",
            "params": {"analysis_type": IntentType.BENCHMARKING.value}
        }
        
        self.assertEqual(step, expected_step)

    def test_domain_mapping_coverage(self):
        """Test that all domain intents have domain mappings."""
        for domain_intent in self.planner.domain_intents:
            self.assertIn(
                domain_intent, 
                self.planner.domain_mapping,
                f"Domain intent {domain_intent} should have domain mapping"
            )

    def test_domain_mapping_fallback(self):
        """Test domain mapping fallback for unmapped intents."""
        # Test with intent not in domain_intents but somehow processed as domain
        step = self.planner._create_domain_step(
            self.planner.domain_mapping.get(IntentType.GENERAL_INQUIRY, "general")
        )
        
        self.assertEqual(step["params"]["domain"], "general")

    async def test_validation_step_always_included(self):
        """Test that validation step is always included in every plan."""
        test_cases = [
            (IntentType.GENERAL_INQUIRY, ConfidenceLevel.HIGH.value),
            (IntentType.TCO_ANALYSIS, ConfidenceLevel.LOW.value),
            (IntentType.PRICING_INQUIRY, ConfidenceLevel.VERY_HIGH.value),
            (IntentType.BENCHMARKING, ConfidenceLevel.MEDIUM.value),
        ]
        
        for intent, confidence in test_cases:
            with self.subTest(intent=intent, confidence=confidence):
                context = self.create_execution_context("test request")
                plan = await self.planner.generate_plan(context, intent, confidence)
                
                # Every plan should have validation step
                validation_step = next(
                    (step for step in plan if step["agent"] == "validator"), 
                    None
                )
                self.assertIsNotNone(
                    validation_step, 
                    f"Plan for {intent} should include validation step"
                )
                self.assertEqual(validation_step["action"], "validate_response")
                self.assertTrue(validation_step["params"]["check_citations"])
                self.assertTrue(validation_step["params"]["check_accuracy"])

    async def test_plan_order_consistency(self):
        """Test that execution plan steps are in correct order."""
        context = self.create_execution_context("Complex TCO analysis")
        intent = IntentType.TCO_ANALYSIS
        confidence = ConfidenceLevel.LOW.value

        plan = await self.planner.generate_plan(context, intent, confidence)
        
        # Extract agent types in order
        agent_sequence = [step["agent"] for step in plan]
        
        # Research should come before domain/analysis if present
        if "researcher" in agent_sequence and "domain_expert" in agent_sequence:
            research_idx = agent_sequence.index("researcher")
            domain_idx = agent_sequence.index("domain_expert")
            self.assertLess(research_idx, domain_idx, "Research should come before domain expert")
        
        # Validation should always be last
        self.assertEqual(agent_sequence[-1], "validator", "Validation should always be last")

    async def test_plan_generation_performance(self):
        """Test that plan generation is performant for multiple intents."""
        context = self.create_execution_context("Performance test")
        
        # Test all intent types
        for intent in IntentType:
            for confidence in [ConfidenceLevel.LOW.value, ConfidenceLevel.HIGH.value]:
                with self.subTest(intent=intent, confidence=confidence):
                    plan = await self.planner.generate_plan(context, intent, confidence)
                    
                    # Basic validation - plan should not be empty and have validation
                    self.assertGreater(len(plan), 0, f"Plan for {intent} should not be empty")
                    self.assertTrue(
                        any(step["agent"] == "validator" for step in plan),
                        f"Plan for {intent} should have validation"
                    )

    def tearDown(self):
        """Clean up test environment."""
        super().tearDown()


if __name__ == "__main__":
    # Run tests directly if executed as script
    unittest.main()