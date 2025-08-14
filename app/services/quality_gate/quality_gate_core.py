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
from .quality_gate_metrics import MetricsCalculator
from .quality_gate_validators import QualityValidator

logger = central_logger.get_logger(__name__)


class QualityGateService:
    """Service for validating content quality and preventing AI slop"""
    
    def __init__(self, redis_manager: Optional[RedisManager] = None):
        """Initialize the quality gate service"""
        self.redis_manager = redis_manager
        self.validation_cache = {}
        self.metrics_history = defaultdict(list)
        
        # Initialize components
        self.patterns = QualityPatterns()
        self.metrics_calculator = MetricsCalculator(self.patterns, redis_manager)
        self.validator = QualityValidator()
        
        logger.info("Quality Gate Service initialized")
    
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
            # Calculate content hash for caching
            content_hash = hashlib.md5(content.encode()).hexdigest()
            cache_key = f"quality:{content_type.value}:{content_hash}:strict={strict_mode}"
            
            # Check cache
            if cache_key in self.validation_cache:
                logger.debug(f"Using cached validation for {cache_key}")
                return self.validation_cache[cache_key]
            
            # Calculate metrics
            metrics = await self.metrics_calculator.calculate_metrics(content, content_type, context)
            
            # Calculate overall score with weighted average
            weights = self.validator.get_weights_for_type(content_type)
            metrics.overall_score = self.validator.calculate_weighted_score(metrics, weights)
            
            # Determine quality level
            metrics.quality_level = self.validator.determine_quality_level(metrics.overall_score)
            
            # Generate suggestions for improvement
            metrics.suggestions = self.validator.generate_suggestions(metrics, content_type)
            
            # Apply thresholds
            passed = self.validator.check_thresholds(metrics, content_type, strict_mode)
            
            # Generate result
            result = ValidationResult(
                passed=passed,
                metrics=metrics,
                retry_suggested=not passed and metrics.overall_score > 0.3,
                retry_prompt_adjustments=self.validator.generate_prompt_adjustments(metrics) if not passed else None,
                fallback_response=None  # Will be set by fallback system
            )
            
            # Cache result
            self.validation_cache[cache_key] = result
            
            # Store metrics for monitoring
            await self._store_metrics(metrics, content_type)
            
            # Log validation result
            logger.info(
                f"Content validation: {content_type.value} - "
                f"Score: {metrics.overall_score:.2f} - "
                f"Level: {metrics.quality_level.value} - "
                f"Passed: {passed}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error validating content: {str(e)}")
            # Return a failed validation on error
            return ValidationResult(
                passed=False,
                metrics=QualityMetrics(
                    overall_score=0.0,
                    quality_level=QualityLevel.UNACCEPTABLE,
                    issues=[f"Validation error: {str(e)}"]
                )
            )
    
    async def _store_metrics(self, metrics: QualityMetrics, content_type: ContentType) -> None:
        """Store metrics for monitoring and analysis"""
        try:
            # Store in memory for immediate access
            self.metrics_history[content_type].append({
                'timestamp': datetime.now(UTC).isoformat(),
                'overall_score': metrics.overall_score,
                'quality_level': metrics.quality_level.value,
                'specificity': metrics.specificity_score,
                'actionability': metrics.actionability_score,
                'quantification': metrics.quantification_score
            })
            
            # Keep only last 1000 entries per type
            if len(self.metrics_history[content_type]) > 1000:
                self.metrics_history[content_type] = self.metrics_history[content_type][-1000:]
            
            # Store in Redis for persistence
            if self.redis_manager:
                await self.redis_manager.store_metrics(
                    f"quality_metrics:{content_type.value}",
                    metrics.__dict__,
                    ttl=86400  # 24 hours
                )
                
        except Exception as e:
            logger.warning(f"Could not store metrics: {str(e)}")
    
    async def get_quality_stats(self, content_type: Optional[ContentType] = None) -> Dict[str, Any]:
        """Get quality statistics for monitoring"""
        stats = {}
        
        if content_type:
            types = [content_type]
        else:
            types = list(ContentType)
        
        for ct in types:
            if ct in self.metrics_history and self.metrics_history[ct]:
                recent = self.metrics_history[ct][-100:]  # Last 100 entries
                
                scores = [m['overall_score'] for m in recent]
                stats[ct.value] = {
                    'count': len(recent),
                    'avg_score': sum(scores) / len(scores),
                    'min_score': min(scores),
                    'max_score': max(scores),
                    'failure_rate': len([s for s in scores if s < 0.5]) / len(scores),
                    'quality_distribution': {
                        level.value: len([m for m in recent if m['quality_level'] == level.value])
                        for level in QualityLevel
                    }
                }
        
        return stats
    
    async def validate_batch(
        self,
        contents: List[Tuple[str, ContentType]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[ValidationResult]:
        """Validate multiple contents in parallel"""
        tasks = [
            self.validate_content(content, content_type, context)
            for content, content_type in contents
        ]
        return await asyncio.gather(*tasks)
    
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