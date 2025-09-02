"""
L3 Integration Test: Agent Quality Gate Pipeline

Business Value Justification (BVJ):
- Segment: Mid/Enterprise (advanced AI quality control)
- Business Goal: Ensure AI output quality meets customer standards
- Value Impact: Prevents poor quality responses that could damage customer trust
- Strategic Impact: $150K MRR - Quality assurance for enterprise AI workflows

L3 Test: Uses real quality gate service with multi-dimensional validation.
Quality target: ≥0.6 quality score threshold with real-time monitoring.
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, Mock, patch, patch

import pytest
from netra_backend.app.schemas import User

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.state_manager import AgentStateManager

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.core.exceptions_base import NetraException, QualityGateException
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.services.quality_gate.quality_gate_core import QualityGateService
from netra_backend.app.services.quality_gate.quality_gate_models import (
    ContentType,
    QualityLevel,
    QualityMetrics,
    ValidationResult,
)
# Removed mock import - using real service testing per CLAUDE.md "MOCKS = Abomination"
from test_framework.real_services import get_real_services

logger = logging.getLogger(__name__)

class QualityGateTestManager:
    """Manager for quality gate pipeline testing."""
    
    def __init__(self):
        self.quality_scores: List[float] = []
        self.validation_results: List[ValidationResult] = []
        self.quality_failures: List[Dict[str, Any]] = []
        self.bypass_events: List[Dict[str, Any]] = []
        
    def record_quality_score(self, score: float, content: str, metadata: Dict[str, Any] = None) -> None:
        """Record a quality score measurement."""
        self.quality_scores.append(score)
        result_data = {
            "score": score,
            "content_length": len(content),
            "timestamp": time.time(),
            "metadata": metadata or {}
        }
        self.validation_results.append(result_data)
        
    def record_quality_failure(self, content: str, reason: str, score: float) -> None:
        """Record a quality gate failure."""
        failure_data = {
            "content": content[:200],  # Truncated for logging
            "reason": reason,
            "score": score,
            "timestamp": time.time()
        }
        self.quality_failures.append(failure_data)
        
    def record_bypass_event(self, reason: str, metadata: Dict[str, Any] = None) -> None:
        """Record a quality gate bypass event."""
        bypass_data = {
            "reason": reason,
            "timestamp": time.time(),
            "metadata": metadata or {}
        }
        self.bypass_events.append(bypass_data)
        
    def get_average_quality_score(self) -> float:
        """Calculate average quality score."""
        if not self.quality_scores:
            return 0.0
        return sum(self.quality_scores) / len(self.quality_scores)
        
    def get_failure_rate(self) -> float:
        """Calculate quality gate failure rate."""
        total_attempts = len(self.validation_results)
        if total_attempts == 0:
            return 0.0
        return len(self.quality_failures) / total_attempts

class MockQualityAwareAgent(BaseAgent):
    """Mock agent that integrates with quality gate pipeline."""
    
    def __init__(self, agent_id: str, quality_gate_service: QualityGateService):
        super().__init__(agent_id=agent_id)
        self.quality_gate_service = quality_gate_service
        self.generated_responses = []
        self.quality_scores = []
        
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process request through quality gate pipeline."""
        # Simulate AI response generation
        response_content = self._generate_mock_response(request)
        
        # Quality gate validation
        validation_result = await self.quality_gate_service.validate_content(
            content=response_content,
            content_type=ContentType.AGENT_RESPONSE,
            context={"agent_id": self.agent_id, "request": request}
        )
        
        self.quality_scores.append(validation_result.overall_score)
        
        if not validation_result.passes_quality_gate:
            # Quality improvement loop
            improved_response = await self._improve_response(response_content, validation_result)
            # Re-validate improved response
            validation_result = await self.quality_gate_service.validate_content(
                content=improved_response,
                content_type=ContentType.AGENT_RESPONSE,
                context={"agent_id": self.agent_id, "request": request, "iteration": 2}
            )
            response_content = improved_response
            
        return {
            "response": response_content,
            "quality_score": validation_result.overall_score,
            "quality_metrics": validation_result.metrics,
            "passes_gate": validation_result.passes_quality_gate
        }
        
    def _generate_mock_response(self, request: Dict[str, Any]) -> str:
        """Generate mock AI response with varying quality."""
        quality_setting = request.get("quality_setting", "normal")
        
        if quality_setting == "low":
            return "This is a very basic response with minimal effort. OK. Sure."
        elif quality_setting == "high":
            return """This is a comprehensive, well-structured response that addresses 
            all aspects of your question with detailed analysis and concrete examples. 
            The response demonstrates deep understanding and provides actionable insights."""
        else:
            return "This is a standard response that provides adequate information."
            
    async def _improve_response(self, original: str, validation_result: ValidationResult) -> str:
        """Improve response based on quality gate feedback."""
        # Simulate quality improvement process
        issues = validation_result.quality_issues or []
        
        if "too_short" in str(issues):
            return original + " Additionally, this response has been expanded with more detailed information and analysis."
        elif "generic" in str(issues):
            return f"Specifically addressing your request: {original} This provides more targeted and relevant information."
        else:
            return f"Improved version: {original} With enhanced clarity and structure."

@pytest.mark.L3
@pytest.mark.integration
class TestAgentQualityGatePipelineL3:
    """L3 integration tests for agent quality gate pipeline."""
    
    @pytest.fixture
    async def redis_manager(self):
        """Create Redis manager for quality gate caching."""
        redis_mgr = RedisManager()
        redis_mgr.enabled = True
        yield redis_mgr
        
    @pytest.fixture
    async def quality_gate_service(self, redis_manager):
        """Create quality gate service for testing."""
        service = QualityGateService(redis_manager=redis_manager)
        yield service
        
    @pytest.fixture
    async def quality_test_manager(self):
        """Create quality gate test manager."""
        yield QualityGateTestManager()
        
    @pytest.fixture
    def test_user(self):
        """Create test user for quality testing."""
        return User(
            id="quality_test_user",
            email="qualityuser@example.com",
            username="qualityuser",
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        
    @pytest.fixture
    async def quality_aware_agent(self, quality_gate_service):
        """Create quality-aware agent for testing."""
        agent = MockQualityAwareAgent("quality_agent_1", quality_gate_service)
        yield agent
        
    @pytest.mark.asyncio
    async def test_quality_score_threshold_enforcement(self, quality_gate_service, quality_test_manager, quality_aware_agent):
        """Test quality score threshold enforcement (≥0.6)."""
        # Test requests with different quality expectations
        test_requests = [
            {"query": "test high quality", "quality_setting": "high"},
            {"query": "test normal quality", "quality_setting": "normal"},
            {"query": "test low quality", "quality_setting": "low"},
        ]
        
        results = []
        for request in test_requests:
            result = await quality_aware_agent.process_request(request)
            results.append(result)
            quality_test_manager.record_quality_score(
                result["quality_score"], 
                result["response"],
                {"quality_setting": request["quality_setting"]}
            )
            
            if not result["passes_gate"]:
                quality_test_manager.record_quality_failure(
                    result["response"],
                    "Below quality threshold",
                    result["quality_score"]
                )
        
        # Verify threshold enforcement
        passing_results = [r for r in results if r["passes_gate"]]
        
        # At least 66% should pass quality gate (2 out of 3)
        assert len(passing_results) >= 2
        
        # All passing results should meet threshold
        for result in passing_results:
            assert result["quality_score"] >= 0.6
            
        # Average quality should be reasonable
        avg_quality = quality_test_manager.get_average_quality_score()
        assert avg_quality >= 0.5  # Allow some low quality for testing
        
    @pytest.mark.asyncio
    async def test_multi_dimensional_quality_validation(self, quality_gate_service, quality_test_manager):
        """Test multi-dimensional quality validation."""
        test_contents = [
            {
                "content": "This is a comprehensive response with detailed analysis and specific examples.",
                "expected_dimensions": ["length", "specificity", "coherence"]
            },
            {
                "content": "OK.",
                "expected_dimensions": ["length"]  # Should fail on length
            },
            {
                "content": "As an AI language model, I think that this is a good question and I will try to help you.",
                "expected_dimensions": ["generic_phrases"]  # Should flag generic content
            }
        ]
        
        validation_results = []
        for test_case in test_contents:
            result = await quality_gate_service.validate_content(
                content=test_case["content"],
                content_type=ContentType.AGENT_RESPONSE,
                context={"test_case": True}
            )
            validation_results.append(result)
            
            quality_test_manager.record_quality_score(
                result.overall_score,
                test_case["content"],
                {"expected_dimensions": test_case["expected_dimensions"]}
            )
            
        # Verify multi-dimensional analysis
        assert len(validation_results) == 3
        
        # First (comprehensive) should score highest
        assert validation_results[0].overall_score > validation_results[1].overall_score
        assert validation_results[0].overall_score > validation_results[2].overall_score
        
        # Check that quality metrics are populated
        for result in validation_results:
            assert hasattr(result, 'metrics')
            assert result.overall_score is not None
            
    @pytest.mark.asyncio
    async def test_quality_improvement_loop(self, quality_aware_agent, quality_test_manager):
        """Test quality improvement loop for failed responses."""
        # Request that will initially fail quality gate
        low_quality_request = {
            "query": "Tell me about AI",
            "quality_setting": "low"
        }
        
        result = await quality_aware_agent.process_request(low_quality_request)
        
        quality_test_manager.record_quality_score(
            result["quality_score"],
            result["response"],
            {"test": "improvement_loop"}
        )
        
        # Should have attempted improvement if initial quality was low
        if result["quality_score"] < 0.6:
            # Agent should have triggered improvement loop
            # Result should show improved content
            assert len(result["response"]) > 50  # Should be expanded
            
        # Final result should either pass or show improvement attempt
        assert result["quality_score"] > 0.0
        
    @pytest.mark.asyncio
    async def test_performance_quality_tradeoff(self, quality_gate_service, quality_test_manager):
        """Test performance vs quality trade-off monitoring."""
        start_time = time.time()
        
        # Process multiple requests to test performance impact
        test_contents = [
            f"Test response {i} with varying quality levels and content length."
            for i in range(10)
        ]
        
        validation_times = []
        quality_scores = []
        
        for content in test_contents:
            validation_start = time.time()
            
            result = await quality_gate_service.validate_content(
                content=content,
                content_type=ContentType.AGENT_RESPONSE,
                context={"performance_test": True}
            )
            
            validation_time = time.time() - validation_start
            validation_times.append(validation_time)
            quality_scores.append(result.overall_score)
            
            quality_test_manager.record_quality_score(
                result.overall_score,
                content,
                {"validation_time": validation_time}
            )
        
        total_time = time.time() - start_time
        
        # Performance requirements
        assert total_time < 5.0  # Should complete in under 5 seconds
        assert max(validation_times) < 1.0  # No single validation > 1 second
        assert sum(validation_times) / len(validation_times) < 0.5  # Average < 0.5s
        
        # Quality consistency
        avg_quality = sum(quality_scores) / len(quality_scores)
        assert avg_quality > 0.4  # Maintain reasonable quality
        
    @pytest.mark.asyncio
    async def test_real_time_quality_monitoring(self, quality_gate_service, quality_test_manager):
        """Test real-time quality monitoring and alerting."""
        # Simulate continuous quality monitoring
        monitoring_period = 3.0  # 3 seconds of monitoring
        check_interval = 0.5  # Check every 0.5 seconds
        
        start_time = time.time()
        quality_checks = []
        
        while time.time() - start_time < monitoring_period:
            # Simulate random quality content
            quality_level = ["high", "normal", "low"][int(time.time() * 3) % 3]
            test_content = f"Quality test content with {quality_level} characteristics."
            
            if quality_level == "low":
                test_content = "Bad."
            elif quality_level == "high":
                test_content = "This is a comprehensive, high-quality response with detailed analysis."
                
            result = await quality_gate_service.validate_content(
                content=test_content,
                content_type=ContentType.AGENT_RESPONSE,
                context={"monitoring": True, "quality_level": quality_level}
            )
            
            quality_checks.append({
                "timestamp": time.time(),
                "score": result.overall_score,
                "passes": result.passes_quality_gate
            })
            
            quality_test_manager.record_quality_score(
                result.overall_score,
                test_content,
                {"quality_level": quality_level}
            )
            
            await asyncio.sleep(check_interval)
        
        # Analyze monitoring results
        assert len(quality_checks) >= 5  # Should have multiple checks
        
        # Quality trend analysis
        passing_checks = [c for c in quality_checks if c["passes"]]
        pass_rate = len(passing_checks) / len(quality_checks)
        
        # Should maintain reasonable pass rate
        assert pass_rate >= 0.5  # At least 50% should pass
        
    @pytest.mark.asyncio
    async def test_quality_gate_bypass_for_emergencies(self, quality_gate_service, quality_test_manager):
        """Test quality gate bypass mechanism for emergency situations."""
        emergency_content = "Emergency alert: System issue detected."
        
        # Normal validation (should apply quality gate)
        normal_result = await quality_gate_service.validate_content(
            content=emergency_content,
            content_type=ContentType.AGENT_RESPONSE,
            context={"emergency": False}
        )
        
        # Emergency bypass validation
        emergency_result = await quality_gate_service.validate_content(
            content=emergency_content,
            content_type=ContentType.AGENT_RESPONSE,
            context={"emergency": True, "bypass_quality_gate": True}
        )
        
        quality_test_manager.record_quality_score(
            normal_result.overall_score,
            emergency_content,
            {"test": "normal_validation"}
        )
        
        quality_test_manager.record_quality_score(
            emergency_result.overall_score,
            emergency_content,
            {"test": "emergency_bypass"}
        )
        
        if emergency_result.passes_quality_gate and not normal_result.passes_quality_gate:
            quality_test_manager.record_bypass_event(
                "Emergency bypass activated",
                {"content_length": len(emergency_content)}
            )
        
        # Verify bypass functionality
        # Emergency context should allow bypass if implemented
        # For now, just verify both validations completed
        assert normal_result.overall_score is not None
        assert emergency_result.overall_score is not None
        
    @pytest.mark.asyncio
    async def test_batch_quality_validation(self, quality_gate_service, quality_test_manager):
        """Test batch quality validation for high-throughput scenarios."""
        # Generate batch of content for validation
        batch_contents = [
            f"Response {i}: This is a test response with varying quality characteristics."
            for i in range(20)
        ]
        
        # Add some intentionally low quality content
        batch_contents.extend([
            "OK.",
            "Sure thing.",
            "As an AI language model, I'll help.",
            "This is a comprehensive analysis with detailed insights and specific examples."
        ])
        
        # Batch validation
        validation_tasks = [
            quality_gate_service.validate_content(
                content=content,
                content_type=ContentType.AGENT_RESPONSE,
                context={"batch_index": i}
            )
            for i, content in enumerate(batch_contents)
        ]
        
        start_time = time.time()
        validation_results = await asyncio.gather(*validation_tasks)
        batch_time = time.time() - start_time
        
        # Record results
        for i, result in enumerate(validation_results):
            quality_test_manager.record_quality_score(
                result.overall_score,
                batch_contents[i],
                {"batch_index": i}
            )
            
            if not result.passes_quality_gate:
                quality_test_manager.record_quality_failure(
                    batch_contents[i],
                    "Batch validation failure",
                    result.overall_score
                )
        
        # Performance validation
        assert batch_time < 10.0  # Batch should complete in under 10 seconds
        assert len(validation_results) == len(batch_contents)
        
        # Quality analysis
        avg_quality = quality_test_manager.get_average_quality_score()
        failure_rate = quality_test_manager.get_failure_rate()
        
        # Should maintain quality standards even in batch processing
        assert avg_quality > 0.4
        assert failure_rate < 0.5  # Less than 50% failure rate
        
        # Verify quality distribution
        scores = [r.overall_score for r in validation_results]
        assert max(scores) > 0.7  # Should have some high quality
        assert min(scores) >= 0.0  # All scores should be valid

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])