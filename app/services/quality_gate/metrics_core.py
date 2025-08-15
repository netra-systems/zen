"""Core Quality Metrics Calculator"""

import re
import hashlib
from typing import Dict, Optional, Any

from app.logging_config import central_logger
from .quality_gate_models import ContentType, QualityMetrics
from .quality_gate_patterns import QualityPatterns

logger = central_logger.get_logger(__name__)


class CoreMetricsCalculator:
    """Core metrics calculation functionality"""
    
    def __init__(self, patterns: QualityPatterns, redis_manager=None):
        self.patterns = patterns
        self.redis_manager = redis_manager
        
        # Compile regex patterns for efficiency
        self.generic_pattern = re.compile(
            "|".join(patterns.GENERIC_PHRASES), 
            re.IGNORECASE
        )
        self.vague_pattern = re.compile(
            "|".join(patterns.VAGUE_TERMS), 
            re.IGNORECASE
        )
        self.circular_pattern = re.compile(
            "|".join(patterns.CIRCULAR_PATTERNS), 
            re.IGNORECASE
        )
    
    async def calculate_basic_metrics(self, content: str) -> QualityMetrics:
        """Calculate basic text analysis metrics"""
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
        
        return metrics
    
    async def calculate_specificity(self, content: str, content_type: ContentType) -> float:
        """Calculate how specific and detailed the content is"""
        score = 0.0
        content_lower = content.lower()
        
        # Check for domain-specific terms
        domain_term_count = sum(1 for term in self.patterns.DOMAIN_TERMS if term in content_lower)
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
        elif content_type == ContentType.ERROR_MESSAGE:
            # ERROR_MESSAGE content should contain specific error indicators
            score += self._calculate_error_specificity(content, content_lower)
        
        return max(0.0, min(1.0, score))
    
    async def calculate_actionability(self, content: str, content_type: ContentType) -> float:
        """Calculate how actionable the content is"""
        score = 0.0
        content_lower = content.lower()
        
        # Check for action verbs (including gerund forms)
        action_verbs = [
            "set", "configure", "install", "run", "execute", "implement",
            "add", "remove", "update", "modify", "change", "apply",
            "enable", "disable", "increase", "decrease", "adjust",
            "edit", "download", "upload", "create", "delete", "copy", "move",
            "implementing", "enabling", "increasing", "adjusting", "reducing",
            "editing", "downloading", "uploading", "creating", "deleting", "copying"
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
        path_patterns = [
            r'/[\w\-./]+\.\w+',
            r'[A-Z]:\\[\w\\\-.]+\.\w+',
            r'https?://[\w\-./]+',
            r'[\w\-./]+\.(?:yaml|yml|py|json|xml|conf|cfg|ini)\b'
        ]
        path_matches = sum(1 for pattern in path_patterns if re.search(pattern, content))
        score += min(path_matches * 0.15, 0.3)
        
        # Penalty for conditional or uncertain language
        uncertain_terms = ["might", "could", "perhaps", "maybe", "possibly", "consider", "think about"]
        uncertain_count = sum(1 for term in uncertain_terms if term in content_lower)
        score -= uncertain_count * 0.05
        
        # ERROR_MESSAGE specific actionability bonuses
        if content_type == ContentType.ERROR_MESSAGE:
            score += self._calculate_error_actionability(content_lower)
        
        return max(0.0, min(1.0, score))
    
    async def calculate_quantification(self, content: str) -> float:
        """Calculate the level of quantification in the content"""
        score = 0.0
        score += self._calculate_pattern_scores(content)
        score += self._calculate_comparison_bonus(content)
        score += self._calculate_metric_names_bonus(content)
        score += self._calculate_error_quantification_bonus(content)
        return min(1.0, score)
    
    def _calculate_pattern_scores(self, content: str) -> float:
        """Calculate scores from numeric pattern matches"""
        patterns = self._get_quantification_patterns()
        score = 0.0
        for pattern in patterns.values():
            matches = re.findall(pattern, content, re.IGNORECASE)
            score += min(len(matches) * 0.15, 0.3)
        return score
    
    def _get_quantification_patterns(self) -> Dict[str, str]:
        """Get quantification regex patterns"""
        patterns = {}
        patterns.update(self._get_basic_numeric_patterns())
        patterns.update(self._get_advanced_numeric_patterns())
        return patterns
    
    def _get_basic_numeric_patterns(self) -> Dict[str, str]:
        """Get basic numeric patterns"""
        return {
            'percentage': r'\b\d+\.?\d*\s*%',
            'time': r'\b\d+\.?\d*\s*(ms|microseconds|seconds?|minutes?|hours?)\b',
            'size': r'\b\d+\.?\d*\s*(GB|MB|KB|bytes?)\b',
            'count': r'\b\d+\.?\d*\s*(tokens?|requests?|queries|items?|elements?)\b'
        }
    
    def _get_advanced_numeric_patterns(self) -> Dict[str, str]:
        """Get advanced numeric patterns"""
        return {
            'rate': r'\b\d+\.?\d*\s*(QPS|RPS|/s|per second)\b',
            'multiplier': r'\b\d+\.?\d*x\b',
            'comparison': r'(increase|decrease|improve|reduce) by \d+\.?\d*'
        }
    
    def _calculate_comparison_bonus(self, content: str) -> float:
        """Calculate bonus for before/after comparisons"""
        if re.search(r'(from|before).*\d+.*to.*\d+', content, re.IGNORECASE):
            return 0.2
        return 0.0
    
    def _calculate_metric_names_bonus(self, content: str) -> float:
        """Calculate bonus for specific metric names with values"""
        pattern = r'(latency|throughput|accuracy|precision|recall|f1).{0,20}\d+'
        metric_names = re.findall(pattern, content, re.IGNORECASE)
        unique_metrics = len(set(metric_names))
        return min(unique_metrics * 0.1, 0.3)
    
    async def calculate_clarity(self, content: str) -> float:
        """Calculate clarity and readability of content"""
        score = 1.0
        
        words = content.split()
        sentences = re.split(r'[.!?]+', content)
        sentences = [s for s in sentences if s.strip()]
        
        if sentences:
            avg_sentence_length = len(words) / len(sentences)
            if avg_sentence_length > 40:
                score -= 0.5  # Heavy penalty for very long sentences
            elif avg_sentence_length > 30:
                score -= 0.2  # Moderate penalty for long sentences
        
        # Check for excessive jargon without explanation
        jargon_pattern = r'\b[A-Z]{3,}\b'
        jargon_matches = re.findall(jargon_pattern, content)
        if len(jargon_matches) > 5:
            score -= 0.1
        
        # Check for nested parentheses or excessive punctuation
        paren_count = content.count('(')
        if paren_count > 2 and sentences:  # 3+ parentheses in a sentence is confusing
            score -= min(paren_count * 0.02, 0.1)  # Progressive penalty
        if content.count(',') > len(sentences) * 3:
            score -= 0.1
        
        # Check for clear structure markers
        if any(marker in content.lower() for marker in ['first', 'second', 'finally', 'in summary']):
            score += 0.1
        
        return max(0.0, min(1.0, score))
    
    async def calculate_redundancy(self, content: str) -> float:
        """Calculate redundancy ratio in content"""
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip().lower() for s in sentences if s.strip()]
        
        if len(sentences) < 2:
            return 0.0
        
        repeated_count = 0
        for i in range(len(sentences)):
            for j in range(i + 1, len(sentences)):
                words1 = set(sentences[i].split())
                words2 = set(sentences[j].split())
                if words1 and words2:
                    overlap = len(words1 & words2) / min(len(words1), len(words2))
                    if overlap > 0.7:
                        repeated_count += 1
        
        redundancy_ratio = repeated_count / (len(sentences) * (len(sentences) - 1) / 2)
        return min(1.0, redundancy_ratio)
    
    def _calculate_error_specificity(self, content: str, content_lower: str) -> float:
        """Calculate ERROR_MESSAGE specific indicators (max 8 lines)"""
        score = 0.0
        error_patterns = self.patterns.ERROR_SPECIFIC_PATTERNS
        for pattern_name, pattern in error_patterns.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            score += min(len(matches) * 0.2, 0.3)
        error_terms = sum(1 for term in self.patterns.ERROR_DOMAIN_TERMS if term in content_lower)
        return min(score + min(error_terms * 0.08, 0.25), 0.8)
    
    def _calculate_error_actionability(self, content_lower: str) -> float:
        """Calculate ERROR_MESSAGE specific actionability (max 8 lines)"""
        score = 0.0
        resolution_terms = ["killed", "increased", "reduced", "enabled", "monitor", "implement", "optimize", "schedule"]
        resolution_count = sum(1 for term in resolution_terms if term in content_lower)
        score += min(resolution_count * 0.1, 0.3)
        if re.search(r'(immediate actions|prevention|resolution|rollback|monitoring)', content_lower):
            score += 0.2
        return min(score, 0.4)
    
    def _calculate_error_quantification_bonus(self, content: str) -> float:
        """Calculate ERROR_MESSAGE specific quantification bonus (max 8 lines)"""
        score = 0.0
        error_metrics = re.findall(r'(connections?|timeout|pool_size|threshold)\s*[=:]\s*\d+', content, re.IGNORECASE)
        score += min(len(error_metrics) * 0.1, 0.2)
        time_patterns = re.findall(r'\b\d+[:-]\d+(?:[:-]\d+)?\s*(AM|PM|minutes?|seconds?)', content, re.IGNORECASE)
        score += min(len(time_patterns) * 0.05, 0.1)
        return min(score, 0.15)