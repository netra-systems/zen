"""Comprehensive tests for Quality Gate Service - Full Coverage
This file provides additional tests to achieve 100% coverage of quality_gate_service.py
"""

import pytest
import asyncio
import re
import hashlib
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List, Tuple
from datetime import datetime
from collections import defaultdict

from app.services.quality_gate_service import (
    QualityGateService,
    QualityLevel,
    ContentType,
    QualityMetrics,
    ValidationResult
)
from app.redis_manager import RedisManager
from app.core.exceptions import NetraException


class TestQualityMetricsDataclass:
    """Test QualityMetrics dataclass initialization and defaults"""
    
    def test_quality_metrics_defaults(self):
        """Test QualityMetrics default values"""
        metrics = QualityMetrics()
        
        assert metrics.specificity_score == 0.0
        assert metrics.actionability_score == 0.0
        assert metrics.quantification_score == 0.0
        assert metrics.relevance_score == 0.0
        assert metrics.completeness_score == 0.0
        assert metrics.novelty_score == 0.0
        assert metrics.clarity_score == 0.0
        assert metrics.generic_phrase_count == 0
        assert metrics.circular_reasoning_detected is False
        assert metrics.hallucination_risk == 0.0
        assert metrics.redundancy_ratio == 0.0
        assert metrics.word_count == 0
        assert metrics.sentence_count == 0
        assert metrics.numeric_values_count == 0
        assert metrics.specific_terms_count == 0
        assert metrics.overall_score == 0.0
        assert metrics.quality_level == QualityLevel.UNACCEPTABLE
        assert metrics.issues == []
        assert metrics.suggestions == []
        
    def test_quality_metrics_custom_values(self):
        """Test QualityMetrics with custom values"""
        issues = ["Issue 1", "Issue 2"]
        suggestions = ["Suggestion 1"]
        
        metrics = QualityMetrics(
            specificity_score=0.8,
            actionability_score=0.9,
            generic_phrase_count=3,
            circular_reasoning_detected=True,
            issues=issues,
            suggestions=suggestions
        )
        
        assert metrics.specificity_score == 0.8
        assert metrics.actionability_score == 0.9
        assert metrics.generic_phrase_count == 3
        assert metrics.circular_reasoning_detected is True
        assert metrics.issues == issues
        assert metrics.suggestions == suggestions


class TestValidationResultDataclass:
    """Test ValidationResult dataclass"""
    
    def test_validation_result_initialization(self):
        """Test ValidationResult initialization"""
        metrics = QualityMetrics(overall_score=0.75)
        
        result = ValidationResult(
            passed=True,
            metrics=metrics,
            retry_suggested=False,
            retry_prompt_adjustments={"temperature": 0.5},
            fallback_response="Fallback content"
        )
        
        assert result.passed is True
        assert result.metrics == metrics
        assert result.retry_suggested is False
        assert result.retry_prompt_adjustments == {"temperature": 0.5}
        assert result.fallback_response == "Fallback content"
        
    def test_validation_result_defaults(self):
        """Test ValidationResult default values"""
        metrics = QualityMetrics()
        result = ValidationResult(passed=False, metrics=metrics)
        
        assert result.passed is False
        assert result.metrics == metrics
        assert result.retry_suggested is False
        assert result.retry_prompt_adjustments is None
        assert result.fallback_response is None


class TestCompleteMetricsCalculation:
    """Test the complete metrics calculation workflow"""
    
    @pytest.fixture
    def quality_service(self):
        """Create QualityGateService instance"""
        return QualityGateService(redis_manager=None)
        
    @pytest.mark.asyncio
    async def test_calculate_metrics_complete_workflow(self, quality_service):
        """Test complete metrics calculation with all components"""
        content = """
        Performance Optimization Report:
        
        Current State: The system processes 500 requests per second with 200ms p95 latency.
        GPU utilization sits at 65% with 12GB memory usage.
        
        Proposed Changes:
        1. Enable batch processing with batch_size=32 (currently 8)
        2. Implement KV cache with 2GB allocation
        3. Use INT8 quantization for 50% memory reduction
        
        Implementation:
        ```bash
        pip install optimization-toolkit
        python optimize.py --batch-size 32 --quantize int8
        ```
        
        Expected Results:
        - Throughput: 500 RPS → 1500 RPS (200% increase)
        - Latency: 200ms → 120ms (40% reduction)
        - Memory: 12GB → 6GB (50% reduction)
        - Cost: $1000/month → $600/month
        
        Trade-offs: 0.5% accuracy loss acceptable for 3x performance gain.
        """
        
        context = {
            "user_request": "optimize system performance",
            "data_source": "production metrics"
        }
        
        metrics = await quality_service._calculate_metrics(
            content,
            ContentType.OPTIMIZATION,
            context
        )
        
        # Verify all metrics were calculated
        assert metrics.word_count > 100
        assert metrics.sentence_count > 5
        assert metrics.generic_phrase_count == 0
        assert metrics.circular_reasoning_detected is False
        assert metrics.specificity_score > 0.7
        assert metrics.actionability_score > 0.6
        assert metrics.quantification_score > 0.8
        assert metrics.relevance_score > 0.5
        assert metrics.completeness_score > 0.7
        assert metrics.novelty_score > 0
        assert metrics.clarity_score > 0.6
        assert metrics.redundancy_ratio < 0.3
        assert metrics.hallucination_risk < 0.3
        assert metrics.overall_score > 0.6
        assert metrics.quality_level in [QualityLevel.GOOD, QualityLevel.EXCELLENT]
        assert len(metrics.suggestions) >= 0


class TestSpecificityCalculationEdgeCases:
    """Test edge cases in specificity calculation"""
    
    @pytest.fixture
    def quality_service(self):
        return QualityGateService()
        
    @pytest.mark.asyncio
    async def test_specificity_with_all_indicators(self, quality_service):
        """Test specificity with all positive indicators"""
        content = """
        Configure batch_size=64, learning_rate=0.001, temperature=0.7, top_k=50.
        Using quantization and pruning for optimization.
        Achieve 250ms latency, 95% GPU utilization, 3200 QPS throughput.
        Set context_window=4096, max_tokens=2048, num_beams=4.
        """
        
        score = await quality_service._calculate_specificity(
            content,
            ContentType.OPTIMIZATION
        )
        
        assert score > 0.8  # Should be very high
        
    @pytest.mark.asyncio
    async def test_specificity_with_vague_language_penalty(self, quality_service):
        """Test specificity penalty for vague language"""
        content = "You might want to consider optimizing your model perhaps."
        
        score = await quality_service._calculate_specificity(
            content,
            ContentType.OPTIMIZATION
        )
        
        assert score < 0.2  # Should be penalized for vagueness


class TestActionabilityEdgeCases:
    """Test edge cases in actionability calculation"""
    
    @pytest.fixture
    def quality_service(self):
        return QualityGateService()
        
    @pytest.mark.asyncio
    async def test_actionability_with_file_paths(self, quality_service):
        """Test actionability with file paths and URLs"""
        content = """
        1. Edit /etc/config/model.yaml
        2. Download weights from https://models.example.com/weights.bin
        3. Run the script at C:\\Users\\model\\optimize.py
        """
        
        score = await quality_service._calculate_actionability(
            content,
            ContentType.ACTION_PLAN
        )
        
        assert score > 0.5  # Should recognize paths and URLs
        
    @pytest.mark.asyncio
    async def test_actionability_code_blocks(self, quality_service):
        """Test actionability with code blocks"""
        content = """
        Execute the following:
        ```python
        model.compile(optimizer='adam')
        model.fit(data, epochs=10)
        ```
        Then run: `python train.py --epochs 10`
        """
        
        score = await quality_service._calculate_actionability(
            content,
            ContentType.ACTION_PLAN
        )
        
        assert score > 0.6  # Should recognize code


class TestQuantificationPatterns:
    """Test quantification pattern matching"""
    
    @pytest.fixture
    def quality_service(self):
        return QualityGateService()
        
    @pytest.mark.asyncio
    async def test_quantification_all_patterns(self, quality_service):
        """Test all quantification patterns"""
        content = """
        Results show 85% accuracy improvement.
        Latency reduced by 150ms (from 200ms to 50ms).
        Memory usage: 4.5GB, storage: 250MB.
        Processing 1500 tokens per second.
        Throughput increased to 2000 QPS.
        Performance improved by 3.5x.
        Cost decreased by 40% monthly.
        """
        
        score = await quality_service._calculate_quantification(content)
        assert score > 0.9  # Should match all patterns
        
    @pytest.mark.asyncio
    async def test_quantification_before_after(self, quality_service):
        """Test before/after comparison bonus"""
        content = "Latency improved from 500ms before optimization to 150ms after."
        
        score = await quality_service._calculate_quantification(content)
        assert score > 0.3  # Should get bonus for before/after
        
    @pytest.mark.asyncio
    async def test_quantification_metric_names(self, quality_service):
        """Test metric names with values bonus"""
        content = "Achieved throughput of 5000 QPS with latency under 50ms and precision at 0.95."
        
        score = await quality_service._calculate_quantification(content)
        assert score > 0.4  # Should get bonus for named metrics


class TestRelevanceCalculation:
    """Test relevance calculation with various contexts"""
    
    @pytest.fixture
    def quality_service(self):
        return QualityGateService()
        
    @pytest.mark.asyncio
    async def test_relevance_technical_terms_matching(self, quality_service):
        """Test relevance with technical term matching"""
        content = "Implement distributed training across multiple GPUs for faster convergence."
        context = {
            "user_request": "How to speed up neural network training with multiple graphics cards"
        }
        
        score = await quality_service._calculate_relevance(content, context)
        assert score > 0.5  # Should match technical concepts
        
    @pytest.mark.asyncio
    async def test_relevance_empty_request_words(self, quality_service):
        """Test relevance when request has no words"""
        content = "Optimization strategy"
        context = {"user_request": ""}
        
        score = await quality_service._calculate_relevance(content, context)
        assert score >= 0  # Should handle empty request gracefully


class TestCompletenessCalculation:
    """Test completeness calculation for all content types"""
    
    @pytest.fixture
    def quality_service(self):
        return QualityGateService()
        
    @pytest.mark.asyncio
    async def test_completeness_report_type(self, quality_service):
        """Test completeness for report content type"""
        content = """
        Summary: System performance analyzed.
        Findings: Identified three bottlenecks.
        Recommendations: Implement caching and optimization.
        Conclusion: 40% improvement expected.
        Metrics: Latency 200ms, throughput 1000 QPS.
        """
        
        score = await quality_service._calculate_completeness(
            content,
            ContentType.REPORT
        )
        assert score == 1.0  # Has all required elements
        
    @pytest.mark.asyncio
    async def test_completeness_general_type(self, quality_service):
        """Test completeness for general content type"""
        content = """
        The system needs optimization. However, there are trade-offs to consider.
        This is because performance improvements may affect accuracy.
        We have analyzed the situation thoroughly.
        """
        
        # Need to access metrics for word/sentence count
        metrics = QualityMetrics()
        metrics.word_count = len(content.split())
        metrics.sentence_count = len(re.split(r'[.!?]+', content))
        
        # Mock the metrics temporarily
        with patch.object(quality_service, '_calculate_metrics', return_value=metrics):
            score = await quality_service._calculate_completeness(
                content,
                ContentType.GENERAL
            )
            assert score > 0  # Should calculate based on general criteria


class TestNoveltyCalculation:
    """Test novelty calculation with Redis integration"""
    
    @pytest.fixture
    def mock_redis(self):
        mock = AsyncMock(spec=RedisManager)
        return mock
        
    @pytest.fixture
    def quality_service(self, mock_redis):
        return QualityGateService(redis_manager=mock_redis)
        
    @pytest.mark.asyncio
    async def test_novelty_redis_error_handling(self, quality_service, mock_redis):
        """Test novelty calculation when Redis operations fail"""
        content = "Test content"
        
        # Simulate Redis error
        mock_redis.get_list.side_effect = Exception("Redis connection failed")
        
        score = await quality_service._calculate_novelty(content)
        assert score == 0.5  # Should return default on error
        
    @pytest.mark.asyncio
    async def test_novelty_large_cache(self, quality_service, mock_redis):
        """Test novelty with large cache list"""
        content = "Unique content"
        
        # Simulate large cache
        mock_redis.get_list.return_value = ["hash" + str(i) for i in range(100)]
        
        score = await quality_service._calculate_novelty(content)
        assert score == 0.8  # Should be novel if not in cache


class TestClarityCalculation:
    """Test clarity calculation edge cases"""
    
    @pytest.fixture
    def quality_service(self):
        return QualityGateService()
        
    @pytest.mark.asyncio
    async def test_clarity_very_long_sentences(self, quality_service):
        """Test clarity with very long sentences"""
        # Create a sentence with 50+ words
        long_sentence = " ".join(["word"] * 50) + "."
        
        score = await quality_service._calculate_clarity(long_sentence)
        assert score < 0.6  # Should be penalized for length
        
    @pytest.mark.asyncio
    async def test_clarity_excessive_acronyms(self, quality_service):
        """Test clarity with many unexplained acronyms"""
        content = "Use API, SDK, CLI, GUI, REST, SOAP, XML, JSON, YAML, CSV for integration."
        
        score = await quality_service._calculate_clarity(content)
        assert score < 0.95  # Should be slightly penalized
        
    @pytest.mark.asyncio
    async def test_clarity_nested_parentheses(self, quality_service):
        """Test clarity with nested parentheses"""
        content = "The system (which includes components (like cache (Redis) and database)) is complex."
        
        score = await quality_service._calculate_clarity(content)
        assert score < 0.95  # Should be penalized
        
    @pytest.mark.asyncio
    async def test_clarity_no_sentences(self, quality_service):
        """Test clarity calculation with no proper sentences"""
        content = "optimization performance metrics"
        
        score = await quality_service._calculate_clarity(content)
        assert score >= 0  # Should handle gracefully


class TestRedundancyCalculation:
    """Test redundancy calculation edge cases"""
    
    @pytest.fixture
    def quality_service(self):
        return QualityGateService()
        
    @pytest.mark.asyncio
    async def test_redundancy_single_sentence(self, quality_service):
        """Test redundancy with single sentence"""
        content = "This is a single sentence."
        
        score = await quality_service._calculate_redundancy(content)
        assert score == 0.0  # No redundancy possible
        
    @pytest.mark.asyncio
    async def test_redundancy_empty_sentences(self, quality_service):
        """Test redundancy with empty sentence splits"""
        content = "First. . . Last."
        
        score = await quality_service._calculate_redundancy(content)
        assert score >= 0  # Should handle empty splits
        
    @pytest.mark.asyncio
    async def test_redundancy_high_overlap(self, quality_service):
        """Test redundancy with high word overlap"""
        content = """
        The optimization improves system performance significantly.
        System performance improves significantly with the optimization.
        Significant performance improvements come from system optimization.
        """
        
        score = await quality_service._calculate_redundancy(content)
        assert score > 0.4  # Should detect high redundancy


class TestHallucinationRisk:
    """Test hallucination risk detection"""
    
    @pytest.fixture
    def quality_service(self):
        return QualityGateService()
        
    @pytest.mark.asyncio
    async def test_hallucination_specific_numbers_with_context(self, quality_service):
        """Test hallucination risk with specific numbers but with data source"""
        content = "The system processes exactly 12345.678 requests per second."
        context = {"data_source": "production_metrics"}
        
        score = await quality_service._calculate_hallucination_risk(content, context)
        assert score < 0.2  # Should be low with data source
        
    @pytest.mark.asyncio
    async def test_hallucination_claims_with_evidence(self, quality_service):
        """Test hallucination risk for claims with evidence"""
        content = "Studies show improvement according to Smith et al. (2023) [1]."
        
        score = await quality_service._calculate_hallucination_risk(content, None)
        assert score < 0.3  # Should be low with citations
        
    @pytest.mark.asyncio
    async def test_hallucination_multiple_impossible_claims(self, quality_service):
        """Test hallucination risk with multiple impossible claims"""
        content = """
        Achieve 100% improvement with zero latency.
        Perfect accuracy guaranteed with infinite throughput.
        No cost solution with unlimited scaling.
        """
        
        score = await quality_service._calculate_hallucination_risk(content, None)
        assert score > 0.8  # Should be very high


class TestWeightedScoring:
    """Test weighted score calculation with penalties"""
    
    @pytest.fixture
    def quality_service(self):
        return QualityGateService()
        
    def test_weighted_score_no_penalties(self, quality_service):
        """Test weighted score without penalties"""
        metrics = QualityMetrics(
            specificity_score=1.0,
            actionability_score=1.0,
            quantification_score=1.0,
            relevance_score=1.0,
            completeness_score=1.0,
            novelty_score=1.0,
            clarity_score=1.0
        )
        
        weights = {
            'specificity': 0.2,
            'actionability': 0.2,
            'quantification': 0.2,
            'relevance': 0.2,
            'completeness': 0.2
        }
        
        score = quality_service._calculate_weighted_score(metrics, weights)
        assert score == 1.0  # Perfect score
        
    def test_weighted_score_all_penalties(self, quality_service):
        """Test weighted score with all penalties applied"""
        metrics = QualityMetrics(
            specificity_score=0.8,
            actionability_score=0.8,
            generic_phrase_count=10,  # High penalty
            circular_reasoning_detected=True,  # -0.2
            hallucination_risk=0.8,  # -0.15
            redundancy_ratio=0.5  # -0.1
        )
        
        weights = {'specificity': 0.5, 'actionability': 0.5}
        
        score = quality_service._calculate_weighted_score(metrics, weights)
        assert score < 0.5  # Should be heavily penalized
        
    def test_weighted_score_zero_weight(self, quality_service):
        """Test weighted score with zero total weight"""
        metrics = QualityMetrics()
        weights = {}  # No weights
        
        score = quality_service._calculate_weighted_score(metrics, weights)
        assert score == 0.0  # Should handle zero weight gracefully


class TestThresholdChecking:
    """Test threshold checking for all scenarios"""
    
    @pytest.fixture
    def quality_service(self):
        return QualityGateService()
        
    def test_threshold_all_specific_checks(self, quality_service):
        """Test all specific threshold checks"""
        metrics = QualityMetrics(
            overall_score=0.4,  # Below min_score
            specificity_score=0.4,  # Below min_specificity
            actionability_score=0.4,  # Below min_actionability
            quantification_score=0.4,  # Below min_quantification
            relevance_score=0.4,  # Below min_relevance
            completeness_score=0.4,  # Below min_completeness
            clarity_score=0.4,  # Below min_clarity
            redundancy_ratio=0.5,  # Above max_redundancy
            generic_phrase_count=10  # Above max_generic_phrases
        )
        
        # Should fail for optimization type
        passed = quality_service._check_thresholds(
            metrics,
            ContentType.OPTIMIZATION,
            strict_mode=False
        )
        assert passed is False
        
    def test_threshold_hallucination_critical_failure(self, quality_service):
        """Test critical failure due to high hallucination risk"""
        metrics = QualityMetrics(
            overall_score=0.9,
            hallucination_risk=0.8  # Above 0.7 threshold
        )
        
        passed = quality_service._check_thresholds(
            metrics,
            ContentType.GENERAL,
            strict_mode=False
        )
        assert passed is False


class TestSuggestionGeneration:
    """Test suggestion generation for all issue types"""
    
    @pytest.fixture
    def quality_service(self):
        return QualityGateService()
        
    def test_suggestions_all_issues(self, quality_service):
        """Test suggestions for all possible issues"""
        metrics = QualityMetrics(
            specificity_score=0.3,
            actionability_score=0.3,
            quantification_score=0.3,
            generic_phrase_count=5,
            circular_reasoning_detected=True,
            redundancy_ratio=0.4,
            completeness_score=0.3
        )
        
        suggestions = quality_service._generate_suggestions(
            metrics,
            ContentType.OPTIMIZATION
        )
        
        # Should have suggestions for all issues
        assert len(suggestions) >= 6
        assert any("specific" in s for s in suggestions)
        assert any("action" in s for s in suggestions)
        assert any("numerical" in s for s in suggestions)
        assert any("generic" in s for s in suggestions)
        assert any("circular" in s for s in suggestions)
        assert any("redundant" in s for s in suggestions)
        
    def test_suggestions_optimization_specific(self, quality_service):
        """Test optimization-specific suggestions"""
        metrics = QualityMetrics(
            quantification_score=0.3,
            completeness_score=0.8
        )
        
        suggestions = quality_service._generate_suggestions(
            metrics,
            ContentType.OPTIMIZATION
        )
        
        assert any("before/after" in s for s in suggestions)
        
    def test_suggestions_action_plan_specific(self, quality_service):
        """Test action plan-specific suggestions"""
        metrics = QualityMetrics(
            completeness_score=0.3,
            actionability_score=0.8
        )
        
        suggestions = quality_service._generate_suggestions(
            metrics,
            ContentType.ACTION_PLAN
        )
        
        assert any("verification" in s or "success criteria" in s for s in suggestions)


class TestPromptAdjustments:
    """Test prompt adjustment generation"""
    
    @pytest.fixture
    def quality_service(self):
        return QualityGateService()
        
    def test_prompt_adjustments_all_issues(self, quality_service):
        """Test prompt adjustments for all issue types"""
        metrics = QualityMetrics(
            specificity_score=0.2,
            actionability_score=0.2,
            quantification_score=0.2,
            generic_phrase_count=8,
            circular_reasoning_detected=True
        )
        
        adjustments = quality_service._generate_prompt_adjustments(metrics)
        
        assert adjustments['temperature'] == 0.3
        assert len(adjustments['additional_instructions']) == 5
        
        instructions_text = ' '.join(adjustments['additional_instructions'])
        assert "specific" in instructions_text
        assert "step-by-step" in instructions_text or "actionable" in instructions_text
        assert "numerical" in instructions_text
        assert "generic" in instructions_text
        assert "HOW" in instructions_text  # From circular reasoning


class TestMetricsStorage:
    """Test metrics storage and retrieval"""
    
    @pytest.fixture
    def mock_redis(self):
        return AsyncMock(spec=RedisManager)
        
    @pytest.fixture
    def quality_service(self, mock_redis):
        return QualityGateService(redis_manager=mock_redis)
        
    @pytest.mark.asyncio
    async def test_store_metrics_memory_limit(self, quality_service):
        """Test that metrics history is limited properly"""
        # Pre-fill with 1000 entries
        for i in range(1000):
            quality_service.metrics_history[ContentType.OPTIMIZATION].append({
                'timestamp': f'2024-01-01T{i:04d}',
                'overall_score': 0.5
            })
        
        # Add one more
        new_metrics = QualityMetrics(overall_score=0.9)
        await quality_service._store_metrics(new_metrics, ContentType.OPTIMIZATION)
        
        # Should still be 1000
        assert len(quality_service.metrics_history[ContentType.OPTIMIZATION]) == 1000
        # Last one should be the new one
        assert quality_service.metrics_history[ContentType.OPTIMIZATION][-1]['overall_score'] == 0.9
        
    @pytest.mark.asyncio
    async def test_store_metrics_redis_with_ttl(self, quality_service, mock_redis):
        """Test Redis storage with TTL"""
        metrics = QualityMetrics(overall_score=0.75)
        
        await quality_service._store_metrics(metrics, ContentType.DATA_ANALYSIS)
        
        mock_redis.store_metrics.assert_called_once()
        call_args = mock_redis.store_metrics.call_args
        
        assert "quality_metrics:data_analysis" in call_args[0]
        assert call_args[1][1] == metrics.__dict__
        assert call_args[1][2] == 86400  # 24 hour TTL


class TestQualityStats:
    """Test quality statistics calculation"""
    
    @pytest.fixture
    def quality_service(self):
        return QualityGateService()
        
    @pytest.mark.asyncio
    async def test_get_quality_stats_empty(self, quality_service):
        """Test stats when no metrics exist"""
        stats = await quality_service.get_quality_stats()
        assert stats == {}
        
    @pytest.mark.asyncio
    async def test_get_quality_stats_distribution(self, quality_service):
        """Test quality distribution in stats"""
        # Add metrics with different quality levels
        for level, score in [
            (QualityLevel.EXCELLENT, 0.95),
            (QualityLevel.GOOD, 0.75),
            (QualityLevel.ACCEPTABLE, 0.55),
            (QualityLevel.POOR, 0.35),
            (QualityLevel.UNACCEPTABLE, 0.25)
        ]:
            quality_service.metrics_history[ContentType.REPORT].append({
                'timestamp': '2024-01-01',
                'overall_score': score,
                'quality_level': level.value
            })
        
        stats = await quality_service.get_quality_stats(ContentType.REPORT)
        
        report_stats = stats[ContentType.REPORT.value]
        assert report_stats['count'] == 5
        assert report_stats['min_score'] == 0.25
        assert report_stats['max_score'] == 0.95
        
        # Check distribution
        dist = report_stats['quality_distribution']
        assert dist[QualityLevel.EXCELLENT.value] == 1
        assert dist[QualityLevel.GOOD.value] == 1
        assert dist[QualityLevel.ACCEPTABLE.value] == 1
        assert dist[QualityLevel.POOR.value] == 1
        assert dist[QualityLevel.UNACCEPTABLE.value] == 1
        
    @pytest.mark.asyncio
    async def test_get_quality_stats_recent_only(self, quality_service):
        """Test that stats use only recent entries"""
        # Add 150 metrics
        for i in range(150):
            quality_service.metrics_history[ContentType.TRIAGE].append({
                'timestamp': f'2024-01-{i+1:03d}',
                'overall_score': 0.5 + (i * 0.001),
                'quality_level': 'acceptable'
            })
        
        stats = await quality_service.get_quality_stats(ContentType.TRIAGE)
        
        # Should only use last 100
        triage_stats = stats[ContentType.TRIAGE.value]
        assert triage_stats['count'] == 100


class TestBatchValidation:
    """Test batch validation functionality"""
    
    @pytest.fixture
    def quality_service(self):
        return QualityGateService()
        
    @pytest.mark.asyncio
    async def test_validate_batch_empty(self, quality_service):
        """Test batch validation with empty list"""
        results = await quality_service.validate_batch([])
        assert results == []
        
    @pytest.mark.asyncio
    async def test_validate_batch_mixed_types(self, quality_service):
        """Test batch validation with mixed content types"""
        contents = [
            ("Error: Out of memory", ContentType.ERROR_MESSAGE),
            ("SELECT * FROM users", ContentType.DATA_ANALYSIS),
            ("Step 1: Install package", ContentType.ACTION_PLAN),
            ("Report summary here", ContentType.REPORT),
            ("Route to optimization team", ContentType.TRIAGE),
            ("General content", ContentType.GENERAL),
            ("Reduce latency by 50ms", ContentType.OPTIMIZATION)
        ]
        
        results = await quality_service.validate_batch(contents)
        
        assert len(results) == 7
        assert all(isinstance(r, ValidationResult) for r in results)
        
    @pytest.mark.asyncio
    async def test_validate_batch_parallel_execution(self, quality_service):
        """Test that batch validation runs in parallel"""
        import time
        
        # Mock validation to take time
        async def slow_validate(*args, **kwargs):
            await asyncio.sleep(0.1)
            return ValidationResult(
                passed=True,
                metrics=QualityMetrics()
            )
        
        with patch.object(quality_service, 'validate_content', side_effect=slow_validate):
            contents = [("Content", ContentType.GENERAL)] * 5
            
            start = time.time()
            results = await quality_service.validate_batch(contents)
            elapsed = time.time() - start
            
            assert len(results) == 5
            # Should be much less than 0.5s (sequential would take 0.5s)
            assert elapsed < 0.3


class TestCachingMechanism:
    """Test content caching functionality"""
    
    @pytest.fixture
    def quality_service(self):
        return QualityGateService()
        
    @pytest.mark.asyncio
    async def test_cache_key_generation(self, quality_service):
        """Test cache key generation for different content"""
        content1 = "Test content 1"
        content2 = "Test content 2"
        
        result1 = await quality_service.validate_content(
            content1,
            ContentType.OPTIMIZATION
        )
        
        result2 = await quality_service.validate_content(
            content2,
            ContentType.OPTIMIZATION
        )
        
        # Different content should have different cache keys
        assert len(quality_service.validation_cache) == 2
        
    @pytest.mark.asyncio
    async def test_cache_hit_performance(self, quality_service):
        """Test that cache hits are faster than calculations"""
        import time
        
        content = "Performance test content with some complexity"
        
        # First call - should calculate
        start1 = time.time()
        result1 = await quality_service.validate_content(content)
        time1 = time.time() - start1
        
        # Second call - should use cache
        start2 = time.time()
        result2 = await quality_service.validate_content(content)
        time2 = time.time() - start2
        
        # Cache hit should be much faster
        assert time2 < time1 / 2
        assert result1.metrics.overall_score == result2.metrics.overall_score


class TestErrorHandling:
    """Test error handling in various methods"""
    
    @pytest.fixture
    def quality_service(self):
        return QualityGateService()
        
    @pytest.mark.asyncio
    async def test_validate_content_calculation_error(self, quality_service):
        """Test error during metrics calculation"""
        with patch.object(
            quality_service,
            '_calculate_metrics',
            side_effect=ValueError("Calculation error")
        ):
            result = await quality_service.validate_content("Test")
            
            assert result.passed is False
            assert "Validation error" in result.metrics.issues[0]
            
    @pytest.mark.asyncio
    async def test_validate_content_threshold_error(self, quality_service):
        """Test error during threshold checking"""
        with patch.object(
            quality_service,
            '_check_thresholds',
            side_effect=KeyError("Missing threshold")
        ):
            result = await quality_service.validate_content("Test")
            
            assert result.passed is False
            
    @pytest.mark.asyncio
    async def test_store_metrics_error_handling(self, quality_service):
        """Test error handling in metrics storage"""
        metrics = QualityMetrics()
        
        # Create a metrics history that causes error
        quality_service.metrics_history = None
        
        # Should not raise, just log warning
        with patch('app.services.quality_gate_service.logger') as mock_logger:
            await quality_service._store_metrics(metrics, ContentType.GENERAL)
            mock_logger.warning.assert_called()


class TestIntegrationScenarios:
    """Test complete integration scenarios"""
    
    @pytest.fixture
    def quality_service(self):
        mock_redis = AsyncMock(spec=RedisManager)
        mock_redis.get_list = AsyncMock(return_value=[])
        mock_redis.add_to_list = AsyncMock()
        mock_redis.store_metrics = AsyncMock()
        return QualityGateService(redis_manager=mock_redis)
        
    @pytest.mark.asyncio
    async def test_complete_optimization_workflow(self, quality_service):
        """Test complete workflow for optimization content"""
        content = """
        System Optimization Plan
        
        Current Performance Baseline:
        - Request latency: 450ms p95, 200ms p50
        - Throughput: 1,200 requests per second
        - GPU utilization: 45% average, 78% peak
        - Memory usage: 14GB / 16GB available
        - Monthly cost: $3,500 for compute resources
        
        Identified Bottlenecks:
        1. Inefficient batch processing (batch_size=4)
        2. No caching for repeated queries
        3. Synchronous I/O operations blocking GPU
        
        Optimization Strategy:
        
        Phase 1 - Quick Wins (Week 1):
        - Increase batch_size to 32
        - Enable KV cache with 2GB allocation
        - Implement async I/O handlers
        
        Implementation Steps:
        ```bash
        # Update configuration
        sed -i 's/batch_size=4/batch_size=32/' config.yaml
        
        # Install caching layer
        pip install redis-cache==2.1.0
        python setup_cache.py --size 2GB --ttl 3600
        
        # Deploy async handlers
        git checkout feature/async-io
        python deploy.py --service inference --async
        ```
        
        Phase 2 - Advanced Optimizations (Week 2):
        - Implement INT8 quantization
        - Enable tensor parallelism across 4 GPUs
        - Use Flash Attention 2 for transformer layers
        
        Expected Outcomes:
        - Latency: 450ms → 180ms p95 (60% reduction)
        - Throughput: 1,200 → 3,600 RPS (3x increase)
        - GPU utilization: 45% → 85% (better resource usage)
        - Memory: 14GB → 8GB (43% reduction)
        - Cost: $3,500 → $2,100/month (40% savings)
        
        Success Metrics:
        - All API endpoints respond < 200ms p95
        - Zero downtime during migration
        - Accuracy degradation < 0.5%
        
        Rollback Plan:
        - Keep previous deployment in blue-green setup
        - Monitor error rates, rollback if > 1%
        - Maintain config backups in git
        
        Trade-offs:
        - 0.3% accuracy loss from quantization
        - Increased complexity in deployment
        - Initial 2-day migration effort required
        """
        
        context = {
            "user_request": "Create a detailed plan to optimize our inference system",
            "data_source": "production_metrics",
            "constraints": "Must maintain 99.9% uptime"
        }
        
        result = await quality_service.validate_content(
            content,
            ContentType.OPTIMIZATION,
            context,
            strict_mode=False
        )
        
        # Should pass with high scores
        assert result.passed is True
        assert result.metrics.overall_score > 0.8
        assert result.metrics.quality_level in [QualityLevel.EXCELLENT, QualityLevel.GOOD]
        
        # Check individual metrics
        assert result.metrics.specificity_score > 0.8
        assert result.metrics.actionability_score > 0.8
        assert result.metrics.quantification_score > 0.8
        assert result.metrics.completeness_score > 0.8
        assert result.metrics.clarity_score > 0.7
        
        # Should have no major issues
        assert result.metrics.generic_phrase_count < 2
        assert result.metrics.circular_reasoning_detected is False
        assert result.metrics.hallucination_risk < 0.3
        assert result.metrics.redundancy_ratio < 0.2
        
        # No retry needed
        assert result.retry_suggested is False
        assert result.retry_prompt_adjustments is None
        
    @pytest.mark.asyncio
    async def test_poor_content_improvement_cycle(self, quality_service):
        """Test improvement cycle for poor content"""
        # Start with poor content
        poor_content = """
        You should probably consider maybe optimizing things.
        It's important to note that optimization is important.
        To improve performance, improve the performance.
        Generally speaking, things could be better.
        """
        
        result1 = await quality_service.validate_content(
            poor_content,
            ContentType.OPTIMIZATION
        )
        
        # Should fail and suggest retry
        assert result1.passed is False
        assert result1.retry_suggested is True
        assert result1.retry_prompt_adjustments is not None
        
        # Simulate improved content based on adjustments
        improved_content = """
        Optimization Plan:
        1. Set batch_size=32 for 40% throughput increase
        2. Enable GPU caching to reduce memory transfers by 2GB
        3. Implement quantization for 50% model size reduction
        
        Expected results: 200ms latency reduction, $500/month cost savings
        """
        
        result2 = await quality_service.validate_content(
            improved_content,
            ContentType.OPTIMIZATION
        )
        
        # Should now pass
        assert result2.passed is True
        assert result2.metrics.overall_score > result1.metrics.overall_score
        assert result2.metrics.generic_phrase_count < result1.metrics.generic_phrase_count


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=app.services.quality_gate_service", "--cov-report=term-missing"])