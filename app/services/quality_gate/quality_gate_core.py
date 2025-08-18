"""Quality Gate Service Core Implementation"""

import hashlib
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, UTC
from collections import defaultdict

from app.logging_config import central_logger
from app.redis_manager import RedisManager

from .quality_gate_models import ContentType, QualityLevel, QualityMetrics, ValidationResult
from .quality_gate_patterns import QualityPatterns
from .quality_gate_metrics import QualityGateMetricsCalculator
from .quality_gate_validators import QualityValidator

logger = central_logger.get_logger(__name__)


class QualityGateService:
    """Service for validating content quality and preventing AI slop"""
    
    def __init__(self, redis_manager: Optional[RedisManager] = None):
        """Initialize the quality gate service"""
        self.redis_manager = redis_manager
        self._init_storage()
        self._init_components(redis_manager)
        logger.info("Quality Gate Service initialized")

    def _init_storage(self) -> None:
        """Initialize storage components."""
        self.validation_cache = {}
        self.metrics_history = defaultdict(list)

    def _init_components(self, redis_manager: Optional[RedisManager]) -> None:
        """Initialize quality gate components."""
        self.patterns = QualityPatterns()
        self.metrics_calculator = QualityGateMetricsCalculator(self.patterns, redis_manager)
        self.validator = QualityValidator()
    
    async def validate_content(
        self,
        content: str,
        content_type: ContentType = ContentType.GENERAL,
        context: Optional[Dict[str, Any]] = None,
        strict_mode: bool = False
    ) -> ValidationResult:
        """
        Validate content quality and check for AI slop
        
        Args:
            content: The content to validate
            content_type: Type of content for specific validation rules
            context: Additional context for validation
            strict_mode: If True, apply stricter validation rules
            
        Returns:
            ValidationResult with metrics and pass/fail status
        """
        try:
            return await self._perform_validation(content, content_type, context, strict_mode)
        except Exception as e:
            return self._handle_validation_error(e)

    def _handle_validation_error(self, error: Exception) -> ValidationResult:
        """Handle validation error and create error result"""
        logger.error(f"Error validating content: {str(error)}")
        return self._create_error_result(error)

    async def _perform_validation(self, content: str, content_type: ContentType, 
                                context: Optional[Dict[str, Any]], strict_mode: bool) -> ValidationResult:
        """Perform the validation workflow."""
        cache_key = self._generate_cache_key(content, content_type, strict_mode)
        cached_result = self._check_validation_cache(cache_key)
        if cached_result:
            return cached_result
        return await self._validate_and_cache(content, content_type, context, strict_mode, cache_key)

    async def _validate_and_cache(self, content: str, content_type: ContentType,
                                context: Optional[Dict[str, Any]], strict_mode: bool, cache_key: str) -> ValidationResult:
        """Validate content and cache result."""
        metrics = await self._calculate_content_metrics(content, content_type, context)
        result = await self._build_validation_result(metrics, content_type, strict_mode)
        await self._cache_and_store_result(cache_key, result, content_type)
        self._log_validation_result(content_type, metrics, result.passed)
        return result

    def _generate_cache_key(self, content: str, content_type: ContentType, strict_mode: bool) -> str:
        """Generate cache key for content validation."""
        content_hash = hashlib.md5(content.encode()).hexdigest()
        return f"quality:{content_type.value}:{content_hash}:strict={strict_mode}"
    
    def _check_validation_cache(self, cache_key: str) -> Optional[ValidationResult]:
        """Check if validation result exists in cache."""
        if cache_key in self.validation_cache:
            logger.debug(f"Using cached validation for {cache_key}")
            return self.validation_cache[cache_key]
        return None
    
    async def _calculate_content_metrics(self, content: str, content_type: ContentType, context: Optional[Dict[str, Any]]) -> QualityMetrics:
        """Calculate comprehensive content quality metrics."""
        metrics = await self.metrics_calculator.calculate_metrics(content, content_type, context)
        weights = self.validator.get_weights_for_type(content_type)
        metrics.overall_score = self.validator.calculate_weighted_score(metrics, weights)
        metrics.quality_level = self.validator.determine_quality_level(metrics.overall_score)
        metrics.suggestions = self.validator.generate_suggestions(metrics, content_type)
        return metrics
    
    async def _build_validation_result(self, metrics: QualityMetrics, content_type: ContentType, strict_mode: bool) -> ValidationResult:
        """Build validation result with pass/fail status and retry suggestions."""
        passed = self.validator.check_thresholds(metrics, content_type, strict_mode)
        retry_adjustments = self._get_retry_adjustments(metrics, passed)
        return self._create_validation_result(passed, metrics, retry_adjustments)

    def _get_retry_adjustments(self, metrics: QualityMetrics, passed: bool) -> Optional[dict]:
        """Get retry adjustments if validation failed."""
        if passed:
            return None
        return self.validator.generate_prompt_adjustments(metrics)

    def _create_validation_result(self, passed: bool, metrics: QualityMetrics, 
                                retry_adjustments: Optional[dict]) -> ValidationResult:
        """Create validation result object."""
        retry_suggested = not passed and retry_adjustments is not None
        return ValidationResult(
            passed=passed,
            metrics=metrics,
            retry_suggested=retry_suggested,
            retry_prompt_adjustments=retry_adjustments,
            fallback_response=None
        )
    
    async def _cache_and_store_result(self, cache_key: str, result: ValidationResult, content_type: ContentType) -> None:
        """Cache validation result and store metrics for monitoring."""
        self.validation_cache[cache_key] = result
        await self._store_metrics(result.metrics, content_type)
    
    def _log_validation_result(self, content_type: ContentType, metrics: QualityMetrics, passed: bool) -> None:
        """Log validation result for monitoring and debugging."""
        logger.info(
            f"Content validation: {content_type.value} - "
            f"Score: {metrics.overall_score:.2f} - "
            f"Level: {metrics.quality_level.value} - "
            f"Passed: {passed}"
        )
    
    def _create_error_result(self, error: Exception) -> ValidationResult:
        """Create a failed validation result for error cases."""
        error_metrics = self._create_error_metrics(error)
        return ValidationResult(
            passed=False,
            metrics=error_metrics
        )

    def _create_error_metrics(self, error: Exception) -> QualityMetrics:
        """Create error metrics for failed validation."""
        return QualityMetrics(
            overall_score=0.0,
            quality_level=QualityLevel.UNACCEPTABLE,
            issues=[f"Validation error: {str(error)}"]
        )
    
    async def _store_metrics(self, metrics: QualityMetrics, content_type: ContentType) -> None:
        """Store metrics for monitoring and analysis"""
        try:
            self._store_metrics_in_memory(metrics, content_type)
            await self._store_metrics_in_redis(metrics, content_type)
        except Exception as e:
            logger.warning(f"Could not store metrics: {str(e)}")
    
    def _store_metrics_in_memory(self, metrics: QualityMetrics, content_type: ContentType) -> None:
        """Store metrics in memory for immediate access."""
        metric_entry = self._create_metric_entry(metrics)
        self.metrics_history[content_type].append(metric_entry)
        self._trim_metrics_history(content_type)
    
    def _create_metric_entry(self, metrics: QualityMetrics) -> Dict[str, Any]:
        """Create standardized metric entry for storage."""
        base_entry = self._get_base_metric_entry(metrics)
        score_entry = self._get_score_metric_entry(metrics)
        return {**base_entry, **score_entry}

    def _get_base_metric_entry(self, metrics: QualityMetrics) -> Dict[str, Any]:
        """Get base metric entry fields."""
        return {
            'timestamp': datetime.now(UTC).isoformat(),
            'overall_score': metrics.overall_score,
            'quality_level': metrics.quality_level.value
        }

    def _get_score_metric_entry(self, metrics: QualityMetrics) -> Dict[str, Any]:
        """Get score metric entry fields."""
        return {
            'specificity': metrics.specificity_score,
            'actionability': metrics.actionability_score,
            'quantification': metrics.quantification_score
        }
    
    def _trim_metrics_history(self, content_type: ContentType) -> None:
        """Trim metrics history to maintain maximum size."""
        if len(self.metrics_history[content_type]) > 1000:
            self.metrics_history[content_type] = self.metrics_history[content_type][-1000:]
    
    async def _store_metrics_in_redis(self, metrics: QualityMetrics, content_type: ContentType) -> None:
        """Store metrics in Redis for persistence."""
        if self.redis_manager:
            import json
            metrics_dict = self._prepare_redis_metrics_dict(metrics)
            redis_key = self._generate_redis_metrics_key(content_type)
            await self.redis_manager.set(redis_key, json.dumps(metrics_dict), ex=86400)
    
    def _prepare_redis_metrics_dict(self, metrics: QualityMetrics) -> Dict[str, Any]:
        """Prepare metrics dictionary for Redis storage."""
        metrics_dict = metrics.__dict__.copy()
        if 'quality_level' in metrics_dict and hasattr(metrics_dict['quality_level'], 'value'):
            metrics_dict['quality_level'] = metrics_dict['quality_level'].value
        return metrics_dict
    
    def _generate_redis_metrics_key(self, content_type: ContentType) -> str:
        """Generate Redis key for metrics storage."""
        timestamp = datetime.now(UTC).isoformat()
        return f"quality_metrics:{content_type.value}:{timestamp}"
    
    async def get_quality_stats(self, content_type: Optional[ContentType] = None) -> Dict[str, Any]:
        """Get quality statistics for monitoring"""
        types = self._get_content_types_for_stats(content_type)
        return self._build_stats_for_types(types)

    def _build_stats_for_types(self, types: List[ContentType]) -> Dict[str, Any]:
        """Build statistics for given content types."""
        stats = {}
        for ct in types:
            if self._has_metrics_data(ct):
                recent = self.metrics_history[ct][-100:]
                stats[ct.value] = self._calculate_content_type_stats(recent)
        return stats
    
    def _get_content_types_for_stats(self, content_type: Optional[ContentType]) -> List[ContentType]:
        """Get content types to include in statistics."""
        if content_type:
            return [content_type]
        return list(ContentType)
    
    def _has_metrics_data(self, content_type: ContentType) -> bool:
        """Check if metrics data exists for content type."""
        return content_type in self.metrics_history and self.metrics_history[content_type]
    
    def _calculate_content_type_stats(self, recent_metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate comprehensive statistics for a content type."""
        scores = [m['overall_score'] for m in recent_metrics]
        basic_stats = self._calculate_basic_stats(recent_metrics, scores)
        quality_stats = self._calculate_quality_distribution(recent_metrics)
        return {**basic_stats, 'quality_distribution': quality_stats}

    def _calculate_basic_stats(self, recent_metrics: List[Dict[str, Any]], scores: List[float]) -> Dict[str, Any]:
        """Calculate basic statistical metrics."""
        return {
            'count': len(recent_metrics),
            'avg_score': sum(scores) / len(scores),
            'min_score': min(scores),
            'max_score': max(scores),
            'failure_rate': len([s for s in scores if s < 0.5]) / len(scores)
        }
    
    def _calculate_quality_distribution(self, recent_metrics: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate quality level distribution."""
        return {
            level.value: len([m for m in recent_metrics if m['quality_level'] == level.value])
            for level in QualityLevel
        }
    
    async def validate_batch(
        self,
        contents: List[Tuple[str, ContentType]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[ValidationResult]:
        """Validate multiple contents in parallel"""
        tasks = self._create_validation_tasks(contents, context)
        return await asyncio.gather(*tasks)

    def _create_validation_tasks(self, contents: List[Tuple[str, ContentType]], 
                               context: Optional[Dict[str, Any]]) -> List:
        """Create validation tasks for batch processing."""
        return [
            self.validate_content(content, content_type, context)
            for content, content_type in contents
        ]
    
    def clear_cache(self) -> None:
        """Clear the validation cache"""
        self.validation_cache.clear()
        logger.info("Validation cache cleared")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        return {
            'cache_size': len(self.validation_cache),
            'metrics_history_size': sum(len(v) for v in self.metrics_history.values())
        }