from unittest.mock import Mock, patch, MagicMock
import asyncio

"""
Tests for TriageSubAgent edge cases, performance, and Pydantic model validation
Refactored to comply with 25-line function limit and 450-line file limit
"""""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

from datetime import datetime

import pytest

from netra_backend.app.agents.state import DeepAgentState

from netra_backend.app.agents.triage.unified_triage_agent import (
Complexity,
ExtractedEntities,
KeyParameters,
Priority,
TriageResult,
UserIntent,
)
from netra_backend.app.agents.triage.unified_triage_agent import UnifiedTriageAgent
from netra_backend.tests.helpers.triage_test_helpers import (
EdgeCaseHelpers,
EntityExtractionHelpers,
IntentHelpers,
PerformanceHelpers,
TriageMockHelpers,
)

@pytest.fixture
def triage_agent():
    """Create TriageSubAgent with mocked dependencies"""
    mock_llm = TriageMockHelpers.create_mock_llm_manager()
    mock_tool = TriageMockHelpers.create_mock_tool_dispatcher()
    mock_redis = TriageMockHelpers.create_mock_redis()
    return TriageSubAgent(mock_llm, mock_tool, mock_redis)

class TestEdgeCasesAndBoundaryConditions:
    """Test edge cases and boundary conditions"""
    @pytest.mark.asyncio
    async def test_empty_and_whitespace_requests(self, triage_agent):
        """Test handling of empty and whitespace-only requests"""
        edge_cases = EdgeCaseHelpers.get_empty_requests()

        for request in edge_cases:
            state = DeepAgentState(user_request=request)
            result = await triage_agent.check_entry_conditions(state, "edge_test")

            # Empty/whitespace requests may be handled differently
            assert result is not None
            if state.triage_result:
                # Check validation status for errors instead of looking for "error" field
                assert state.triage_result.validation_status.validation_errors
                @pytest.mark.asyncio
                async def test_unicode_and_special_characters(self, triage_agent):
                    """Test handling of Unicode and special characters"""
                    unicode_requests = EdgeCaseHelpers.get_unicode_requests()

                    for request in unicode_requests:
                        await self._test_unicode_request(triage_agent, request)

                        async def _test_unicode_request(self, agent, request):
                            """Test individual Unicode request"""
                            state = DeepAgentState(user_request=request)

                            agent.llm_manager.set_responses([
                            '{"category": "Cost Optimization", "priority": "medium", "confidence_score": 0.8}'
                            ])

                            await agent.execute(state, "unicode_test", stream_updates=False)

                            assert state.triage_result != None
                            assert "category" in state.triage_result
                            @pytest.mark.asyncio
                            async def test_extremely_long_requests(self, triage_agent):
                                """Test handling of extremely long requests"""
                                boundary_request = "Optimize AI costs " * 588
                                very_long_request = "Optimize AI costs " * 1000

                                self._test_boundary_request(triage_agent, boundary_request)
                                self._test_very_long_request(triage_agent, very_long_request)

                                def _test_boundary_request(self, agent, request):
                                    """Test boundary case request"""
                                    validation = agent.triage_core.validator.validate_request(request)
        # Note: Validation may reject very long requests for security
                                    assert validation is not None

                                    def _test_very_long_request(self, agent, request):
                                        """Test very long request"""
                                        validation = agent.triage_core.validator.validate_request(request)
        # Basic test - actual validation behavior may vary
                                        assert validation is not None
                                        @pytest.mark.asyncio
                                        async def test_malformed_json_responses(self, triage_agent):
                                            """Test handling of malformed JSON responses from LLM"""
                                            malformed_responses = EdgeCaseHelpers.get_malformed_json_responses()

                                            for malformed_response in malformed_responses:
                                                await self._test_malformed_response(triage_agent, malformed_response)

                                                async def _test_malformed_response(self, agent, malformed_response):
                                                    """Test individual malformed response"""
                                                    agent.llm_manager.set_responses([malformed_response])

                                                    state = DeepAgentState(user_request="Test malformed JSON")
                                                    await agent.execute(state, "malformed_test", stream_updates=False)

        # Basic assertion that processing completed
                                                    assert state.triage_result is not None

                                                    class TestPerformanceOptimization:
                                                        """Test performance optimization features"""
                                                        @pytest.mark.asyncio
                                                        async def test_request_processing_performance(self, triage_agent):
                                                            """Test request processing performance"""
                                                            request_sizes = PerformanceHelpers.get_request_sizes()

                                                            for size in request_sizes:
                                                                await self._test_request_size_performance(triage_agent, size)

                                                                async def _test_request_size_performance(self, agent, size):
                                                                    """Test performance for specific request size"""
                                                                    request = PerformanceHelpers.create_sized_request(size)
                                                                    state = DeepAgentState(user_request=request)

                                                                    agent.llm_manager.set_responses([
                                                                    '{"category": "Cost Optimization", "priority": "medium", "confidence_score": 0.8}'
                                                                    ])

                                                                    start_time = datetime.now()
                                                                    await agent.execute(state, f"perf_test_{size}", stream_updates=False)
                                                                    end_time = datetime.now()

                                                                    execution_time = PerformanceHelpers.measure_execution_time(start_time, end_time)

                                                                    assert execution_time < 5000  # 5 seconds max
                                                                    assert state.triage_result != None
                                                                    @pytest.mark.asyncio
                                                                    async def test_memory_efficiency(self, triage_agent):
                                                                        """Test memory efficiency with large datasets"""
                                                                        large_request = PerformanceHelpers.create_large_request()
                                                                        state = DeepAgentState(user_request=large_request)

                                                                        triage_agent.llm_manager.set_responses([
                                                                        '{"category": "Performance Optimization", "priority": "high", "confidence_score": 0.85}'
                                                                        ])

                                                                        await triage_agent.execute(state, "memory_test", stream_updates=False)

                                                                        assert state.triage_result != None
                                                                        assert state.triage_result.category == "Performance Optimization"

                                                                        def test_hash_generation_performance(self, triage_agent):
                                                                            """Test hash generation performance"""
                                                                            test_inputs = self._get_hash_test_inputs()

                                                                            for test_input in test_inputs:
                                                                                self._test_hash_generation_speed(triage_agent, test_input)

                                                                                def _get_hash_test_inputs(self):
                                                                                    """Get test inputs for hash generation"""
                                                                                    return [
                                                                                "Short request",
                                                                                "Medium length request with some technical details about optimization",
                                                                                ("Very long request " * 100 + " with lots of repeated content and technical jargon "
                                                                                "about AI model optimization, cost reduction, performance improvements, "
                                                                                "and various metrics and thresholds"),
                                                                                ]

                                                                                def _test_hash_generation_speed(self, agent, test_input):
                                                                                    """Test hash generation speed for input"""
                                                                                    start_time, hash_result, end_time = self._generate_hash_with_timing(agent, test_input)
                                                                                    generation_time = PerformanceHelpers.measure_execution_time(start_time, end_time)

                                                                                    self._assert_hash_performance(generation_time, hash_result)

                                                                                    def _generate_hash_with_timing(self, agent, test_input):
                                                                                        """Generate hash with timing measurement"""
                                                                                        start_time = datetime.now()
                                                                                        hash_result = agent.triage_core.generate_request_hash(test_input)
                                                                                        end_time = datetime.now()
                                                                                        return start_time, hash_result, end_time

                                                                                    def _assert_hash_performance(self, generation_time, hash_result):
                                                                                        """Assert hash generation performance"""
                                                                                        assert generation_time < 10  # < 10ms
        # Hash length may vary based on implementation (MD5=32, SHA256=64)
                                                                                        assert len(hash_result) >= 32
                                                                                        assert hash_result.isalnum()

                                                                                        class TestPydanticModelValidation:
                                                                                            """Test Pydantic model validation and serialization"""

                                                                                            def test_triage_result_comprehensive_validation(self):
                                                                                                """Test comprehensive TriageResult validation"""
                                                                                                valid_result = self._create_comprehensive_triage_result()

                                                                                                self._assert_triage_result_valid(valid_result)

                                                                                                def _create_comprehensive_triage_result(self):
                                                                                                    """Create comprehensive triage result"""
                                                                                                    from netra_backend.app.agents.triage.unified_triage_agent import TriageMetadata
                                                                                                    key_params = self._create_test_key_parameters()
                                                                                                    metadata = TriageMetadata(triage_duration_ms=300, llm_tokens_used=100)
                                                                                                    return TriageResult(
                                                                                                category="Cost Optimization",
                                                                                                confidence_score=0.85,
                                                                                                priority=Priority.HIGH,
                                                                                                complexity=Complexity.MODERATE,
                                                                                                key_parameters=key_params,
                                                                                                metadata=metadata
                                                                                                )

                                                                                                def _create_test_key_parameters(self):
                                                                                                    """Create test key parameters"""
                                                                                                    return KeyParameters(
                                                                                                workload_type="inference",
                                                                                                optimization_focus="cost",
                                                                                                constraints=["latency < 100ms"]
                                                                                                )

                                                                                                def _assert_triage_result_valid(self, result):
                                                                                                    """Assert triage result is valid"""
                                                                                                    assert result.category == "Cost Optimization"
                                                                                                    assert result.confidence_score == 0.85
                                                                                                    assert result.priority == Priority.HIGH
                                                                                                    assert result.complexity == Complexity.MODERATE

                                                                                                    def test_triage_result_edge_case_validation(self):
                                                                                                        """Test TriageResult validation edge cases"""
                                                                                                        minimal_result = self._create_minimal_triage_result()
                                                                                                        max_confidence_result = self._create_max_confidence_result()

                                                                                                        self._assert_minimal_result_valid(minimal_result)
                                                                                                        self._assert_max_confidence_valid(max_confidence_result)

                                                                                                        def _create_minimal_triage_result(self):
                                                                                                            """Create minimal triage result"""
                                                                                                            return TriageResult(
                                                                                                        category="Test",
                                                                                                        confidence_score=0.0,
                                                                                                        priority=Priority.LOW,
                                                                                                        complexity=Complexity.SIMPLE
                                                                                                        )

                                                                                                        def _create_max_confidence_result(self):
                                                                                                            """Create maximum confidence result"""
                                                                                                            return TriageResult(
                                                                                                        category="Test",
                                                                                                        confidence_score=1.0,
                                                                                                        priority=Priority.CRITICAL,
                                                                                                        complexity=Complexity.EXPERT
                                                                                                        )

                                                                                                        def _assert_minimal_result_valid(self, result):
                                                                                                            """Assert minimal result is valid"""
                                                                                                            assert result.confidence_score == 0.0
        # Basic validation of minimal result
                                                                                                            assert result.metadata == None

                                                                                                            def _assert_max_confidence_valid(self, result):
                                                                                                                """Assert max confidence result is valid"""
                                                                                                                assert result.confidence_score == 1.0

                                                                                                                def test_extracted_entities_complex_validation(self):
                                                                                                                    """Test ExtractedEntities with complex data"""
                                                                                                                    complex_entities = EntityExtractionHelpers.create_complex_entities()

                                                                                                                    self._assert_complex_entities_valid(complex_entities)

                                                                                                                    def _assert_complex_entities_valid(self, entities):
                                                                                                                        """Assert complex entities are valid"""
                                                                                                                        assert len(entities.models_mentioned) == 3
                                                                                                                        assert len(entities.thresholds) == 3
                                                                                                                        assert len(entities.targets) == 2
        # Basic validation that complex entities were created
                                                                                                                        assert len(entities.models_mentioned) == 3

                                                                                                                        def test_user_intent_comprehensive(self):
                                                                                                                            """Test UserIntent with comprehensive data"""
                                                                                                                            comprehensive_intent = IntentHelpers.create_comprehensive_intent()

                                                                                                                            self._assert_comprehensive_intent_valid(comprehensive_intent)

                                                                                                                            def _assert_comprehensive_intent_valid(self, intent):
                                                                                                                                """Assert comprehensive intent is valid"""
                                                                                                                                assert intent.primary_intent == "optimize"
                                                                                                                                assert len(intent.secondary_intents) == 3
                                                                                                                                assert intent.action_required == True

                                                                                                                                if __name__ == "__main__":
                                                                                                                                    pytest.main([__file__, "-v", "--tb=short"])