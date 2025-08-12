"""Quality Gate Service for AI Slop Prevention

This service provides comprehensive quality validation for all AI-generated outputs
to prevent generic, low-value, or meaningless responses (AI slop).
"""

import re
import hashlib
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, UTC
import asyncio
from collections import defaultdict

from app.logging_config import central_logger
from app.core.exceptions import NetraException
from app.redis_manager import RedisManager

logger = central_logger.get_logger(__name__)


class QualityLevel(Enum):
    """Quality level classifications"""
    EXCELLENT = "excellent"  # Score >= 0.9
    GOOD = "good"           # Score >= 0.7
    ACCEPTABLE = "acceptable"  # Score >= 0.5
    POOR = "poor"           # Score >= 0.3
    UNACCEPTABLE = "unacceptable"  # Score < 0.3


class ContentType(Enum):
    """Types of content to validate"""
    OPTIMIZATION = "optimization"
    DATA_ANALYSIS = "data_analysis"
    ACTION_PLAN = "action_plan"
    REPORT = "report"
    TRIAGE = "triage"
    ERROR_MESSAGE = "error_message"
    GENERAL = "general"


@dataclass
class QualityMetrics:
    """Quality metrics for a piece of content"""
    specificity_score: float = 0.0
    actionability_score: float = 0.0
    quantification_score: float = 0.0
    relevance_score: float = 0.0
    completeness_score: float = 0.0
    novelty_score: float = 0.0
    clarity_score: float = 0.0
    
    # Negative indicators
    generic_phrase_count: int = 0
    circular_reasoning_detected: bool = False
    hallucination_risk: float = 0.0
    redundancy_ratio: float = 0.0
    
    # Meta information
    word_count: int = 0
    sentence_count: int = 0
    numeric_values_count: int = 0
    specific_terms_count: int = 0
    
    # Overall score
    overall_score: float = 0.0
    quality_level: QualityLevel = QualityLevel.UNACCEPTABLE
    
    # Detailed feedback
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Result of quality validation"""
    passed: bool
    metrics: QualityMetrics
    retry_suggested: bool = False
    retry_prompt_adjustments: Optional[Dict[str, Any]] = None
    fallback_response: Optional[str] = None


class QualityGateService:
    """Service for validating content quality and preventing AI slop"""
    
    # Generic phrases that indicate low-quality content
    GENERIC_PHRASES = [
        r"it is important to note that",
        r"generally speaking",
        r"in general",
        r"as we know",
        r"it should be noted",
        r"one could argue",
        r"it goes without saying",
        r"needless to say",
        r"at the end of the day",
        r"when all is said and done",
        r"for all intents and purposes",
        r"in today's world",
        r"in this day and age",
        r"since the dawn of time",
        r"throughout history",
        r"in conclusion",
        r"to summarize",
        r"all things considered",
        r"it is worth mentioning"
    ]
    
    # Vague optimization terms without specifics
    # These patterns detect vague language that lacks specificity
    # We want to catch phrases like "optimize things" but NOT "optimize GPU utilization"
    VAGUE_TERMS = [
        r"just\s+optimize",
        r"optimize\s+(things|stuff|it|everything|something)",
        r"improve\s+(things|stuff|it|everything|something)",
        r"enhance\s+(things|stuff|it|everything|something)",
        r"make\s+(?:it\s+)?better",
        r"more\s+efficient(?!\s+(by|than))",
        r"consider\s+optimizing",
        r"think about\s+improving",
        r"look into\s+enhancing",
        r"you might want to",
        r"you could try",
        r"perhaps you should"
    ]
    
    # Circular reasoning patterns
    CIRCULAR_PATTERNS = [
        r"to improve (.+) you should improve",
        r"optimize (.+) by optimizing",
        r"better (.+) through better",
        r"enhance (.+) by enhancing",
        r"for better (.+), use better"
    ]
    
    # Domain-specific terms for Netra (indicates good content)
    DOMAIN_TERMS = [
        "latency", "throughput", "batch size", "token", "inference",
        "quantization", "pruning", "distillation", "cache", "memory",
        "GPU", "CPU", "TPU", "FLOPS", "bandwidth", "utilization",
        "p50", "p95", "p99", "QPS", "RPS", "ms", "microseconds",
        "cost per token", "cost per request", "TCO", "ROI",
        "model size", "parameter count", "attention heads", "layers",
        "beam search", "temperature", "top-p", "top-k", "context window",
        "KV cache", "flash attention", "tensor parallel", "pipeline parallel"
    ]
    
    def __init__(self, redis_manager: Optional[RedisManager] = None):
        """Initialize the quality gate service"""
        self.redis_manager = redis_manager
        self.validation_cache = {}
        self.metrics_history = defaultdict(list)
        
        # Compile regex patterns for efficiency
        self.generic_pattern = re.compile(
            "|".join(self.GENERIC_PHRASES), 
            re.IGNORECASE
        )
        self.vague_pattern = re.compile(
            "|".join(self.VAGUE_TERMS), 
            re.IGNORECASE
        )
        self.circular_pattern = re.compile(
            "|".join(self.CIRCULAR_PATTERNS), 
            re.IGNORECASE
        )
        
        # Quality thresholds by content type
        self.thresholds = {
            ContentType.OPTIMIZATION: {
                "min_score": 0.7,
                "min_specificity": 0.6,
                "min_actionability": 0.7,
                "min_quantification": 0.7
            },
            ContentType.DATA_ANALYSIS: {
                "min_score": 0.6,
                "min_specificity": 0.6,
                "min_quantification": 0.8,
                "min_relevance": 0.5
            },
            ContentType.ACTION_PLAN: {
                "min_score": 0.7,
                "min_actionability": 0.9,
                "min_specificity": 0.7,
                "min_completeness": 0.8
            },
            ContentType.REPORT: {
                "min_score": 0.6,
                "min_completeness": 0.8,
                "min_clarity": 0.7,
                "max_redundancy": 0.2
            },
            ContentType.TRIAGE: {
                "min_score": 0.5,
                "min_specificity": 0.6,
                "min_relevance": 0.8
            },
            ContentType.ERROR_MESSAGE: {
                "min_score": 0.5,
                "min_clarity": 0.8,
                "min_actionability": 0.6
            },
            ContentType.GENERAL: {
                "min_score": 0.5,
                "min_clarity": 0.6,
                "max_generic_phrases": 3
            }
        }
        
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
            cache_key = f"quality:{content_type.value}:{content_hash}"
            
            # Check cache
            if cache_key in self.validation_cache:
                logger.debug(f"Using cached validation for {cache_key}")
                return self.validation_cache[cache_key]
            
            # Perform comprehensive validation
            metrics = await self._calculate_metrics(content, content_type, context)
            
            # Apply thresholds
            passed = self._check_thresholds(metrics, content_type, strict_mode)
            
            # Generate result
            result = ValidationResult(
                passed=passed,
                metrics=metrics,
                retry_suggested=not passed and metrics.overall_score > 0.3,
                retry_prompt_adjustments=self._generate_prompt_adjustments(metrics) if not passed else None,
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
    
    async def _calculate_metrics(
        self,
        content: str,
        content_type: ContentType,
        context: Optional[Dict[str, Any]]
    ) -> QualityMetrics:
        """Calculate comprehensive quality metrics for content"""
        metrics = QualityMetrics()
        
        # Basic text analysis
        metrics.word_count = len(content.split())
        metrics.sentence_count = len(re.split(r'[.!?]+', content))
        
        # Count numeric values (including percentages, decimals, etc.)
        numeric_pattern = r'\b\d+(?:\.\d+)?(?:%|ms|GB|MB|KB|s|x|M|K)?\b'
        numeric_matches = re.findall(numeric_pattern, content)
        metrics.numeric_values_count = len(numeric_matches)
        
        # Check for generic phrases
        generic_matches = self.generic_pattern.findall(content)
        metrics.generic_phrase_count = len(generic_matches)
        if metrics.generic_phrase_count > 0:
            metrics.issues.append(f"Contains {metrics.generic_phrase_count} generic phrases")
        
        # Check for vague terms
        vague_matches = self.vague_pattern.findall(content)
        if vague_matches:
            metrics.issues.append(f"Contains {len(vague_matches)} vague optimization terms without specifics")
        
        # Check for circular reasoning
        circular_matches = self.circular_pattern.findall(content)
        metrics.circular_reasoning_detected = len(circular_matches) > 0
        if metrics.circular_reasoning_detected:
            metrics.issues.append("Circular reasoning detected")
        
        # Calculate specificity score
        metrics.specificity_score = await self._calculate_specificity(content, content_type)
        
        # Calculate actionability score
        metrics.actionability_score = await self._calculate_actionability(content, content_type)
        
        # Calculate quantification score
        metrics.quantification_score = await self._calculate_quantification(content)
        
        # Calculate relevance score
        metrics.relevance_score = await self._calculate_relevance(content, context)
        
        # Calculate completeness score
        metrics.completeness_score = await self._calculate_completeness(content, content_type)
        
        # Calculate novelty score (check against recent outputs)
        metrics.novelty_score = await self._calculate_novelty(content)
        
        # Calculate clarity score
        metrics.clarity_score = await self._calculate_clarity(content)
        
        # Calculate redundancy ratio
        metrics.redundancy_ratio = await self._calculate_redundancy(content)
        
        # Calculate hallucination risk
        metrics.hallucination_risk = await self._calculate_hallucination_risk(content, context)
        
        # Calculate overall score with weighted average
        weights = self._get_weights_for_type(content_type)
        metrics.overall_score = self._calculate_weighted_score(metrics, weights)
        
        # Determine quality level
        metrics.quality_level = self._determine_quality_level(metrics.overall_score)
        
        # Generate suggestions for improvement
        metrics.suggestions = self._generate_suggestions(metrics, content_type)
        
        return metrics
    
    async def _calculate_specificity(self, content: str, content_type: ContentType) -> float:
        """Calculate how specific and detailed the content is"""
        score = 0.0
        content_lower = content.lower()
        
        # Check for domain-specific terms
        domain_term_count = sum(1 for term in self.DOMAIN_TERMS if term in content_lower)
        score += min(domain_term_count * 0.05, 0.3)  # Up to 0.3 for domain terms
        
        # Check for numeric values (specific metrics)
        numeric_pattern = r'\b\d+\.?\d*\s*(ms|%|x|GB|MB|KB|tokens?|requests?|QPS|RPS|FLOPS)\b'
        numeric_matches = re.findall(numeric_pattern, content, re.IGNORECASE)
        score += min(len(numeric_matches) * 0.1, 0.3)  # Up to 0.3 for metrics
        
        # Check for specific parameter names or configurations
        param_pattern = r'(batch_size|learning_rate|temperature|top_[pk]|max_tokens|num_beams|context_window)\s*[=:]\s*\d+'
        param_matches = re.findall(param_pattern, content, re.IGNORECASE)
        score += min(len(param_matches) * 0.15, 0.3)  # Up to 0.3 for parameters
        
        # Penalty for vague language
        if self.vague_pattern.search(content):
            score -= 0.2
        
        # Content type specific bonuses
        if content_type == ContentType.OPTIMIZATION:
            # Optimization content should mention specific techniques
            optimization_terms = ["quantization", "pruning", "distillation", "caching", "batching", "parallelization"]
            opt_count = sum(1 for term in optimization_terms if term in content_lower)
            score += min(opt_count * 0.1, 0.2)
        
        return max(0.0, min(1.0, score))
    
    async def _calculate_actionability(self, content: str, content_type: ContentType) -> float:
        """Calculate how actionable the content is"""
        score = 0.0
        content_lower = content.lower()
        
        # Check for action verbs (including gerund forms)
        action_verbs = [
            "set", "configure", "install", "run", "execute", "implement",
            "add", "remove", "update", "modify", "change", "apply",
            "enable", "disable", "increase", "decrease", "adjust",
            "implementing", "enabling", "increasing", "adjusting", "reducing"
        ]
        action_count = sum(1 for verb in action_verbs if verb in content_lower)
        score += min(action_count * 0.08, 0.4)
        
        # Check for step-by-step instructions
        step_pattern = r'(step \d+|first|second|third|then|next|finally)'
        if re.search(step_pattern, content_lower):
            score += 0.2
        
        # Check for specific commands or code
        code_pattern = r'```|`[^`]+`|\$\s*\w+|pip install|npm install|docker run'
        if re.search(code_pattern, content):
            score += 0.3
        
        # Check for specific file paths or URLs
        path_pattern = r'[/\\][\w\-./\\]+\.\w+|https?://[\w\-./]+'
        if re.search(path_pattern, content):
            score += 0.1
        
        # Penalty for conditional or uncertain language
        uncertain_terms = ["might", "could", "perhaps", "maybe", "possibly", "consider", "think about"]
        uncertain_count = sum(1 for term in uncertain_terms if term in content_lower)
        score -= uncertain_count * 0.05
        
        return max(0.0, min(1.0, score))
    
    async def _calculate_quantification(self, content: str) -> float:
        """Calculate the level of quantification in the content"""
        score = 0.0
        
        # Count different types of numeric values
        patterns = {
            'percentage': r'\b\d+\.?\d*\s*%',
            'time': r'\b\d+\.?\d*\s*(ms|microseconds|seconds?|minutes?|hours?)\b',
            'size': r'\b\d+\.?\d*\s*(GB|MB|KB|bytes?)\b',
            'count': r'\b\d+\.?\d*\s*(tokens?|requests?|queries|items?|elements?)\b',
            'rate': r'\b\d+\.?\d*\s*(QPS|RPS|/s|per second)\b',
            'multiplier': r'\b\d+\.?\d*x\b',
            'comparison': r'(increase|decrease|improve|reduce) by \d+\.?\d*'
        }
        
        total_matches = 0
        for pattern_type, pattern in patterns.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            total_matches += len(matches)
            score += min(len(matches) * 0.15, 0.3)
        
        # Bonus for before/after comparisons
        if re.search(r'(from|before).*\d+.*to.*\d+', content, re.IGNORECASE):
            score += 0.2
        
        # Bonus for specific metric names with values
        if re.search(r'(latency|throughput|accuracy|precision|recall|f1).{0,20}\d+', content, re.IGNORECASE):
            score += 0.1
        
        return min(1.0, score)
    
    async def _calculate_relevance(self, content: str, context: Optional[Dict[str, Any]]) -> float:
        """Calculate relevance to the context and user request"""
        if not context or 'user_request' not in context:
            # Can't calculate relevance without context
            return 0.5
        
        score = 0.0
        user_request = context['user_request'].lower()
        content_lower = content.lower()
        
        # Extract key terms from user request
        request_words = set(user_request.split())
        content_words = set(content_lower.split())
        
        # Calculate word overlap
        overlap = len(request_words & content_words)
        if request_words:
            score += min(overlap / len(request_words), 0.5)
        
        # Check if content addresses the main topic
        # Extract nouns and technical terms from request
        technical_terms = [word for word in request_words if len(word) > 4]
        addressed_terms = sum(1 for term in technical_terms if term in content_lower)
        if technical_terms:
            score += min(addressed_terms / len(technical_terms), 0.5) * 0.5
        
        return score
    
    async def _calculate_completeness(self, content: str, content_type: ContentType) -> float:
        """Calculate if the content is complete for its type"""
        score = 0.0
        content_lower = content.lower()
        
        # Define required elements by content type
        required_elements = {
            ContentType.OPTIMIZATION: [
                "improve", "reduce", "increase", "optimize", "change"
            ],
            ContentType.DATA_ANALYSIS: [
                "data", "pattern", "insight", "trend", "conclusion"
            ],
            ContentType.ACTION_PLAN: [
                "step", "requirement", "timeline", "outcome", "verification"
            ],
            ContentType.REPORT: [
                "summary", "finding", "recommendation", "conclusion", "metric"
            ]
        }
        
        if content_type in required_elements:
            elements = required_elements[content_type]
            found = sum(1 for elem in elements if elem in content_lower)
            score = found / len(elements)
        else:
            # For other types, check basic completeness
            if metrics.sentence_count >= 3:
                score += 0.3
            if metrics.word_count >= 50:
                score += 0.3
            if "however" in content_lower or "but" in content_lower:
                score += 0.2  # Shows consideration of alternatives
            if "because" in content_lower or "due to" in content_lower:
                score += 0.2  # Shows reasoning
        
        return min(1.0, score)
    
    async def _calculate_novelty(self, content: str) -> float:
        """Calculate novelty compared to recent outputs"""
        # Generate content hash
        content_hash = hashlib.md5(content.encode()).hexdigest()
        
        # Check recent outputs for similarity
        if self.redis_manager:
            try:
                # Get recent output hashes
                recent_hashes = await self.redis_manager.get_list("quality:recent_hashes", limit=100)
                
                # Simple novelty check - is this exact content new?
                if content_hash in recent_hashes:
                    return 0.0  # Exact duplicate
                
                # Store this hash
                await self.redis_manager.add_to_list("quality:recent_hashes", content_hash, max_size=1000)
                
                # For more sophisticated similarity, we'd need embeddings
                # For now, return high novelty if not duplicate
                return 0.8
                
            except Exception as e:
                logger.warning(f"Could not check novelty: {str(e)}")
        
        # Default to moderate novelty if can't check
        return 0.5
    
    async def _calculate_clarity(self, content: str) -> float:
        """Calculate clarity and readability of content"""
        score = 1.0  # Start with perfect score and deduct
        
        # Check average sentence length (very long sentences reduce clarity)
        words = content.split()
        sentences = re.split(r'[.!?]+', content)
        sentences = [s for s in sentences if s.strip()]
        
        if sentences:
            avg_sentence_length = len(words) / len(sentences)
            if avg_sentence_length > 30:
                score -= 0.2
            elif avg_sentence_length > 40:
                score -= 0.4
        
        # Check for excessive jargon without explanation
        jargon_pattern = r'\b[A-Z]{3,}\b'  # Unexplained acronyms
        jargon_matches = re.findall(jargon_pattern, content)
        if len(jargon_matches) > 5:
            score -= 0.1
        
        # Check for nested parentheses or excessive punctuation
        if content.count('(') > 5 or content.count(',') > len(sentences) * 3:
            score -= 0.1
        
        # Check for clear structure markers
        if any(marker in content.lower() for marker in ['first', 'second', 'finally', 'in summary']):
            score += 0.1
        
        return max(0.0, min(1.0, score))
    
    async def _calculate_redundancy(self, content: str) -> float:
        """Calculate redundancy ratio in content"""
        # Split into sentences
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip().lower() for s in sentences if s.strip()]
        
        if len(sentences) < 2:
            return 0.0
        
        # Check for repeated phrases
        repeated_count = 0
        for i in range(len(sentences)):
            for j in range(i + 1, len(sentences)):
                # Simple word overlap check
                words1 = set(sentences[i].split())
                words2 = set(sentences[j].split())
                if words1 and words2:
                    overlap = len(words1 & words2) / min(len(words1), len(words2))
                    if overlap > 0.7:  # High overlap indicates redundancy
                        repeated_count += 1
        
        redundancy_ratio = repeated_count / (len(sentences) * (len(sentences) - 1) / 2)
        return min(1.0, redundancy_ratio)
    
    async def _calculate_hallucination_risk(self, content: str, context: Optional[Dict[str, Any]]) -> float:
        """Estimate risk of hallucination in content"""
        risk = 0.0
        
        # Check for overly specific numbers without context
        very_specific_pattern = r'\b\d{4,}\.?\d*\b'  # 4+ digit numbers
        specific_matches = re.findall(very_specific_pattern, content)
        if specific_matches and (not context or 'data_source' not in context):
            risk += 0.2
        
        # Check for claims without evidence markers
        claim_patterns = [
            r'studies show', r'research indicates', r'data proves',
            r'always', r'never', r'guaranteed', r'definitely'
        ]
        for pattern in claim_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                # Check if followed by citation or specific reference
                if not re.search(r'\[\d+\]|\(\d{4}\)|according to|based on', content):
                    risk += 0.1
        
        # Check for impossible claims in optimization context
        impossible_patterns = [
            r'100% improvement', r'zero latency', r'infinite throughput',
            r'no cost', r'perfect accuracy'
        ]
        for pattern in impossible_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                risk += 0.3
        
        return min(1.0, risk)
    
    def _get_weights_for_type(self, content_type: ContentType) -> Dict[str, float]:
        """Get scoring weights based on content type"""
        weights = {
            ContentType.OPTIMIZATION: {
                'specificity': 0.25,
                'actionability': 0.25,
                'quantification': 0.20,
                'relevance': 0.15,
                'completeness': 0.10,
                'clarity': 0.05
            },
            ContentType.DATA_ANALYSIS: {
                'quantification': 0.30,
                'specificity': 0.20,
                'relevance': 0.20,
                'completeness': 0.15,
                'clarity': 0.10,
                'novelty': 0.05
            },
            ContentType.ACTION_PLAN: {
                'actionability': 0.35,
                'completeness': 0.25,
                'specificity': 0.20,
                'clarity': 0.15,
                'relevance': 0.05
            },
            ContentType.REPORT: {
                'completeness': 0.25,
                'clarity': 0.20,
                'specificity': 0.20,
                'quantification': 0.15,
                'relevance': 0.10,
                'novelty': 0.10
            }
        }
        
        return weights.get(content_type, {
            'specificity': 0.20,
            'actionability': 0.15,
            'quantification': 0.15,
            'relevance': 0.15,
            'completeness': 0.15,
            'clarity': 0.10,
            'novelty': 0.10
        })
    
    def _calculate_weighted_score(self, metrics: QualityMetrics, weights: Dict[str, float]) -> float:
        """Calculate weighted overall score"""
        score = 0.0
        total_weight = 0.0
        
        metric_values = {
            'specificity': metrics.specificity_score,
            'actionability': metrics.actionability_score,
            'quantification': metrics.quantification_score,
            'relevance': metrics.relevance_score,
            'completeness': metrics.completeness_score,
            'novelty': metrics.novelty_score,
            'clarity': metrics.clarity_score
        }
        
        for metric, weight in weights.items():
            if metric in metric_values:
                score += metric_values[metric] * weight
                total_weight += weight
        
        # Apply penalties
        if metrics.generic_phrase_count > 2:
            score -= 0.1
        if metrics.circular_reasoning_detected:
            score -= 0.2
        if metrics.hallucination_risk > 0.5:
            score -= 0.15
        if metrics.redundancy_ratio > 0.3:
            score -= 0.1
        
        # Normalize
        if total_weight > 0:
            score = score / total_weight
        
        return max(0.0, min(1.0, score))
    
    def _determine_quality_level(self, score: float) -> QualityLevel:
        """Determine quality level from score"""
        if score >= 0.9:
            return QualityLevel.EXCELLENT
        elif score >= 0.7:
            return QualityLevel.GOOD
        elif score >= 0.5:
            return QualityLevel.ACCEPTABLE
        elif score >= 0.3:
            return QualityLevel.POOR
        else:
            return QualityLevel.UNACCEPTABLE
    
    def _check_thresholds(
        self,
        metrics: QualityMetrics,
        content_type: ContentType,
        strict_mode: bool
    ) -> bool:
        """Check if metrics meet thresholds for the content type"""
        thresholds = self.thresholds.get(content_type, self.thresholds[ContentType.GENERAL])
        
        # Apply strict mode multiplier
        if strict_mode:
            thresholds = {k: v * 1.2 if k.startswith('min_') else v * 0.8 
                         for k, v in thresholds.items()}
        
        # Check overall score
        if metrics.overall_score < thresholds.get('min_score', 0.5):
            return False
        
        # Check specific metrics
        if 'min_specificity' in thresholds and metrics.specificity_score < thresholds['min_specificity']:
            return False
        
        if 'min_actionability' in thresholds and metrics.actionability_score < thresholds['min_actionability']:
            return False
        
        if 'min_quantification' in thresholds and metrics.quantification_score < thresholds['min_quantification']:
            return False
        
        if 'min_relevance' in thresholds and metrics.relevance_score < thresholds['min_relevance']:
            return False
        
        if 'min_completeness' in thresholds and metrics.completeness_score < thresholds['min_completeness']:
            return False
        
        if 'min_clarity' in thresholds and metrics.clarity_score < thresholds['min_clarity']:
            return False
        
        if 'max_redundancy' in thresholds and metrics.redundancy_ratio > thresholds['max_redundancy']:
            return False
        
        if 'max_generic_phrases' in thresholds and metrics.generic_phrase_count > thresholds['max_generic_phrases']:
            return False
        
        # Check for critical failures
        if metrics.circular_reasoning_detected:
            return False
        
        if metrics.hallucination_risk > 0.7:
            return False
        
        return True
    
    def _generate_suggestions(self, metrics: QualityMetrics, content_type: ContentType) -> List[str]:
        """Generate improvement suggestions based on metrics"""
        suggestions = []
        
        if metrics.specificity_score < 0.5:
            suggestions.append("Add specific metrics, parameters, or configuration values")
        
        if metrics.actionability_score < 0.5:
            suggestions.append("Include clear action steps or commands")
        
        if metrics.quantification_score < 0.5:
            suggestions.append("Add numerical values and measurable outcomes")
        
        if metrics.generic_phrase_count > 2:
            suggestions.append("Remove generic phrases and filler language")
        
        if metrics.circular_reasoning_detected:
            suggestions.append("Avoid circular reasoning - provide concrete solutions")
        
        if metrics.redundancy_ratio > 0.2:
            suggestions.append("Reduce redundant information")
        
        if content_type == ContentType.OPTIMIZATION and metrics.quantification_score < 0.7:
            suggestions.append("Include before/after performance metrics")
        
        if content_type == ContentType.ACTION_PLAN and metrics.completeness_score < 0.7:
            suggestions.append("Add verification steps and success criteria")
        
        return suggestions
    
    def _generate_prompt_adjustments(self, metrics: QualityMetrics) -> Dict[str, Any]:
        """Generate prompt adjustments for retry based on quality issues"""
        adjustments = {
            'temperature': 0.3,  # Lower temperature for more focused output
            'additional_instructions': []
        }
        
        if metrics.specificity_score < 0.5:
            adjustments['additional_instructions'].append(
                "Be extremely specific. Include exact parameter values, configuration settings, and metrics."
            )
        
        if metrics.actionability_score < 0.5:
            adjustments['additional_instructions'].append(
                "Provide step-by-step actionable instructions with specific commands or code."
            )
        
        if metrics.quantification_score < 0.5:
            adjustments['additional_instructions'].append(
                "Include numerical values for all claims. Show before/after metrics with percentages."
            )
        
        if metrics.generic_phrase_count > 2:
            adjustments['additional_instructions'].append(
                "Avoid generic phrases. Be direct and specific without filler language."
            )
        
        if metrics.circular_reasoning_detected:
            adjustments['additional_instructions'].append(
                "Provide concrete solutions, not circular logic. Explain HOW, not just WHAT."
            )
        
        return adjustments
    
    async def _store_metrics(self, metrics: QualityMetrics, content_type: ContentType):
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