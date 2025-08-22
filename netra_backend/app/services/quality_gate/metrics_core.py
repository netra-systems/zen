"""Core Quality Metrics Calculator"""

import hashlib
import re
from typing import Any, Dict, Optional

from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.quality_gate.quality_gate_models import (
    ContentType,
    QualityMetrics,
)
from netra_backend.app.services.quality_gate.quality_gate_patterns import (
    QualityPatterns,
)

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
        self._calculate_text_stats(metrics, content)
        self._calculate_numeric_values(metrics, content)
        self._check_generic_phrases(metrics, content)
        self._check_vague_terms(metrics, content)
        self._check_circular_reasoning(metrics, content)
        return metrics
    
    def _calculate_text_stats(self, metrics: QualityMetrics, content: str) -> None:
        """Calculate word and sentence counts"""
        metrics.word_count = len(content.split())
        metrics.sentence_count = len(re.split(r'[.!?]+', content))
    
    def _calculate_numeric_values(self, metrics: QualityMetrics, content: str) -> None:
        """Count numeric values in content"""
        numeric_pattern = r'\b\d+(?:\.\d+)?(?:%|ms|GB|MB|KB|s|x|M|K)?\b'
        numeric_matches = re.findall(numeric_pattern, content)
        metrics.numeric_values_count = len(numeric_matches)
    
    def _check_generic_phrases(self, metrics: QualityMetrics, content: str) -> None:
        """Check for generic phrases and update metrics"""
        generic_matches = self.generic_pattern.findall(content)
        metrics.generic_phrase_count = len(generic_matches)
        if metrics.generic_phrase_count > 0:
            metrics.issues.append(f"Contains {metrics.generic_phrase_count} generic phrases")
    
    def _check_vague_terms(self, metrics: QualityMetrics, content: str) -> None:
        """Check for vague terms and update issues"""
        vague_matches = self.vague_pattern.findall(content)
        if vague_matches:
            metrics.issues.append(f"Contains {len(vague_matches)} vague optimization terms without specifics")
    
    def _check_circular_reasoning(self, metrics: QualityMetrics, content: str) -> None:
        """Check for circular reasoning and update metrics"""
        circular_matches = self.circular_pattern.findall(content)
        metrics.circular_reasoning_detected = len(circular_matches) > 0
        if metrics.circular_reasoning_detected:
            metrics.issues.append("Circular reasoning detected")
    
    async def calculate_specificity(self, content: str, content_type: ContentType) -> float:
        """Calculate how specific and detailed the content is"""
        score = 0.0
        content_lower = content.lower()
        score += self._calculate_domain_terms_score(content_lower)
        score += self._calculate_numeric_metrics_score(content)
        score += self._calculate_parameters_score(content)
        score -= self._apply_vague_penalty(content)
        score += self._calculate_content_type_specificity_bonus(content_type, content, content_lower)
        return max(0.0, min(1.0, score))
    
    def _calculate_domain_terms_score(self, content_lower: str) -> float:
        """Calculate score for domain-specific terms"""
        domain_term_count = sum(1 for term in self.patterns.DOMAIN_TERMS if term in content_lower)
        return min(domain_term_count * 0.05, 0.3)
    
    def _calculate_numeric_metrics_score(self, content: str) -> float:
        """Calculate score for numeric metrics"""
        numeric_pattern = r'\b\d+\.?\d*\s*(ms|%|x|GB|MB|KB|tokens?|requests?|QPS|RPS|FLOPS)\b'
        numeric_matches = re.findall(numeric_pattern, content, re.IGNORECASE)
        return min(len(numeric_matches) * 0.1, 0.3)
    
    def _calculate_parameters_score(self, content: str) -> float:
        """Calculate score for parameter configurations"""
        param_pattern = r'(batch_size|learning_rate|temperature|top_[pk]|max_tokens|num_beams|context_window)\s*[=:]\s*\d+'
        param_matches = re.findall(param_pattern, content, re.IGNORECASE)
        return min(len(param_matches) * 0.15, 0.3)
    
    def _apply_vague_penalty(self, content: str) -> float:
        """Apply penalty for vague language"""
        return 0.2 if self.vague_pattern.search(content) else 0.0
    
    def _calculate_content_type_specificity_bonus(self, content_type: ContentType, content: str, content_lower: str) -> float:
        """Calculate content type specific specificity bonuses"""
        if content_type == ContentType.OPTIMIZATION:
            return self._calculate_optimization_specificity_bonus(content_lower)
        elif content_type == ContentType.ERROR_MESSAGE:
            return self._calculate_error_specificity(content, content_lower)
        return 0.0
    
    def _calculate_optimization_specificity_bonus(self, content_lower: str) -> float:
        """Calculate optimization specific bonus"""
        optimization_terms = ["quantization", "pruning", "distillation", "caching", "batching", "parallelization"]
        opt_count = sum(1 for term in optimization_terms if term in content_lower)
        return min(opt_count * 0.1, 0.2)
    
    async def calculate_actionability(self, content: str, content_type: ContentType) -> float:
        """Calculate how actionable the content is"""
        content_lower = content.lower()
        score = 0.0
        
        score += self._calculate_action_verb_score(content_lower)
        score += self._calculate_instruction_patterns_score(content_lower)
        score += self._calculate_code_patterns_score(content)
        score += self._calculate_path_patterns_score(content)
        score -= self._calculate_uncertainty_penalty(content_lower)
        score += self._calculate_content_type_bonus(content_type, content_lower)
        
        return max(0.0, min(1.0, score))
    
    def _calculate_action_verb_score(self, content_lower: str) -> float:
        """Calculate score based on action verbs"""
        action_verbs = self._get_action_verbs_list()
        action_count = sum(1 for verb in action_verbs if verb in content_lower)
        return min(action_count * 0.08, 0.4)
    
    def _get_action_verbs_list(self) -> list:
        """Get comprehensive list of action verbs"""
        return [
            "set", "configure", "install", "run", "execute", "implement",
            "add", "remove", "update", "modify", "change", "apply",
            "enable", "disable", "increase", "decrease", "adjust",
            "edit", "download", "upload", "create", "delete", "copy", "move",
            "implementing", "enabling", "increasing", "adjusting", "reducing",
            "editing", "downloading", "uploading", "creating", "deleting", "copying"
        ]
    
    def _calculate_instruction_patterns_score(self, content_lower: str) -> float:
        """Calculate score for step-by-step instruction patterns"""
        step_pattern = r'(step \d+|first|second|third|then|next|finally)'
        return 0.2 if re.search(step_pattern, content_lower) else 0.0
    
    def _calculate_code_patterns_score(self, content: str) -> float:
        """Calculate score for code patterns"""
        code_pattern = r'```|`[^`]+`|\$\s*\w+|pip install|npm install|docker run'
        return 0.3 if re.search(code_pattern, content) else 0.0
    
    def _calculate_path_patterns_score(self, content: str) -> float:
        """Calculate score for file path and URL patterns"""
        path_patterns = [
            r'/[\w\-./]+\.\w+',
            r'[A-Z]:\\[\w\\\-.]+\.\w+',
            r'https?://[\w\-./]+',
            r'[\w\-./]+\.(?:yaml|yml|py|json|xml|conf|cfg|ini)\b'
        ]
        path_matches = sum(1 for pattern in path_patterns if re.search(pattern, content))
        return min(path_matches * 0.15, 0.3)
    
    def _calculate_uncertainty_penalty(self, content_lower: str) -> float:
        """Calculate penalty for uncertain language"""
        uncertain_terms = ["might", "could", "perhaps", "maybe", "possibly", "consider", "think about"]
        uncertain_count = sum(1 for term in uncertain_terms if term in content_lower)
        return uncertain_count * 0.05
    
    def _calculate_content_type_bonus(self, content_type: ContentType, content_lower: str) -> float:
        """Calculate content type specific bonus"""
        if content_type == ContentType.ERROR_MESSAGE:
            return self._calculate_error_actionability(content_lower)
        return 0.0
    
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
        sentences = [s for s in re.split(r'[.!?]+', content) if s.strip()]
        score -= self._calculate_sentence_length_penalty(words, sentences)
        score -= self._calculate_jargon_penalty(content)
        score -= self._calculate_punctuation_penalty(content, sentences)
        score += self._calculate_structure_bonus(content)
        return max(0.0, min(1.0, score))
    
    def _calculate_sentence_length_penalty(self, words: list, sentences: list) -> float:
        """Calculate penalty for long sentences"""
        if not sentences:
            return 0.0
        avg_sentence_length = len(words) / len(sentences)
        return self._get_length_penalty(avg_sentence_length)
    
    def _get_length_penalty(self, avg_length: float) -> float:
        """Get penalty based on average sentence length"""
        if avg_length > 40:
            return 0.5
        elif avg_length > 30:
            return 0.2
        return 0.0
    
    def _calculate_jargon_penalty(self, content: str) -> float:
        """Calculate penalty for excessive jargon"""
        jargon_pattern = r'\b[A-Z]{3,}\b'
        jargon_matches = re.findall(jargon_pattern, content)
        return 0.1 if len(jargon_matches) > 5 else 0.0
    
    def _calculate_punctuation_penalty(self, content: str, sentences: list) -> float:
        """Calculate penalty for excessive punctuation"""
        penalty = 0.0
        penalty += self._calculate_parentheses_penalty(content, sentences)
        penalty += self._calculate_comma_penalty(content, sentences)
        return penalty
    
    def _calculate_parentheses_penalty(self, content: str, sentences: list) -> float:
        """Calculate penalty for excessive parentheses"""
        paren_count = content.count('(')
        return min(paren_count * 0.02, 0.1) if paren_count > 2 and sentences else 0.0
    
    def _calculate_comma_penalty(self, content: str, sentences: list) -> float:
        """Calculate penalty for excessive commas"""
        return 0.1 if content.count(',') > len(sentences) * 3 else 0.0
    
    def _calculate_structure_bonus(self, content: str) -> float:
        """Calculate bonus for clear structure markers"""
        structure_markers = ['first', 'second', 'finally', 'in summary']
        return 0.1 if any(marker in content.lower() for marker in structure_markers) else 0.0
    
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