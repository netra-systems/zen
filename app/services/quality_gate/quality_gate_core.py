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
            cache_key = self._generate_cache_key(content, content_type, strict_mode)
            cached_result = self._check_validation_cache(cache_key)
            if cached_result:
                return cached_result
            
            metrics = await self._calculate_content_metrics(content, content_type, context)
            result = await self._build_validation_result(metrics, content_type, strict_mode)
            await self._cache_and_store_result(cache_key, result, content_type)
            self._log_validation_result(content_type, metrics, result.passed)
            return result
        except Exception as e:
            logger.error(f"Error validating content: {str(e)}")
            return self._create_error_result(e)
    
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
                import json
                await self.redis_manager.set(
                    f"quality_metrics:{content_type.value}:{datetime.now(UTC).isoformat()}",
                    json.dumps(metrics.__dict__),
                    ex=86400  # 24 hours
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