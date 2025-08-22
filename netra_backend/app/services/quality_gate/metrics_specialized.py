"""Specialized Quality Metrics Calculators"""

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


class SpecializedMetricsCalculator:
    """Specialized metrics calculators for domain-specific content"""
    
    def __init__(self, patterns: QualityPatterns, redis_manager=None):
        self.patterns = patterns
        self.redis_manager = redis_manager
    
    def _get_gpu_mappings(self) -> Dict[str, set]:
        """Get GPU-related semantic mappings"""
        return {
            'gpu': {'graphics', 'card', 'cards', 'memory'},
            'gpus': {'graphics', 'card', 'cards', 'memory'},
            'graphics': {'gpu', 'gpus'},
            'cards': {'gpu', 'gpus'},
            'memory': {'gpu', 'consumption', 'usage'},
            'usage': {'consumption', 'memory'},
            'consumption': {'usage', 'memory'}
        }

    def _get_training_mappings(self) -> Dict[str, set]:
        """Get training-related semantic mappings"""
        return {
            'training': {'convergence', 'precision', 'mixed'},
            'distributed': {'multiple', 'parallel'},
            'neural': {'network'},
            'speed': {'faster', 'fast'},
            'faster': {'speed', 'fast'},
            'reduce': {'optimize', 'minimize', 'improve'},
            'help': {'optimize', 'improve', 'reduce'},
            'optimize': {'reduce', 'improve', 'help', 'enabling'},
            'enabling': {'optimize', 'improve'}
        }

    def _get_semantic_mappings(self) -> Dict[str, set]:
        """Get all semantic term equivalence mappings"""
        mappings = {}
        mappings.update(self._get_gpu_mappings())
        mappings.update(self._get_training_mappings())
        return mappings

    def _count_semantic_matches(self, request_words: set, content_words: set, mappings: Dict[str, set]) -> int:
        """Count semantic matches between request and content"""
        semantic_matches = 0
        for req_word in request_words:
            if req_word in mappings:
                if any(sem_word in content_words for sem_word in mappings[req_word]):
                    semantic_matches += 1
        return semantic_matches

    def _calculate_semantic_score(self, request_words: set, content_words: set) -> float:
        """Calculate semantic relevance score"""
        if not request_words:
            return 0.0
        mappings = self._get_semantic_mappings()
        semantic_matches = self._count_semantic_matches(request_words, content_words, mappings)
        return min(semantic_matches * 0.2, 0.6)

    def _calculate_word_overlap_score(self, request_words: set, content_words: set) -> float:
        """Calculate direct word overlap score"""
        if not request_words:
            return 0.0
        overlap = len(request_words & content_words)
        return min(overlap / len(request_words) * 0.8, 0.4)

    def _extract_technical_terms(self, request_words: set) -> list[str]:
        """Extract technical terms from request words"""
        return [word for word in request_words if len(word) > 4]

    def _calculate_technical_terms_score(self, request_words: set, content_lower: str) -> float:
        """Calculate technical terms matching score"""
        technical_terms = self._extract_technical_terms(request_words)
        if not technical_terms:
            return 0.0
        addressed_terms = sum(1 for term in technical_terms if term in content_lower)
        return min(addressed_terms / len(technical_terms), 0.5) * 0.4

    def _prepare_relevance_data(self, content: str, context: Dict[str, Any]) -> tuple[set, set]:
        """Prepare words for relevance calculation"""
        user_request = context['user_request'].lower()
        content_lower = content.lower()
        request_words = set(user_request.split())
        content_words = set(content_lower.split())
        return request_words, content_words

    async def calculate_relevance(self, content: str, context: Optional[Dict[str, Any]]) -> float:
        """Calculate relevance to the context and user request"""
        if not context or 'user_request' not in context:
            return 0.5
        request_words, content_words = self._prepare_relevance_data(content, context)
        overlap_score = self._calculate_word_overlap_score(request_words, content_words)
        semantic_score = self._calculate_semantic_score(request_words, content_words)
        technical_score = self._calculate_technical_terms_score(request_words, content.lower())
        return min(overlap_score + semantic_score + technical_score, 1.0)
    
    def _get_required_elements(self) -> Dict[ContentType, list[str]]:
        """Get required elements by content type"""
        return {
            ContentType.OPTIMIZATION: ["improve", "reduce", "increase", "optimize", "change"],
            ContentType.DATA_ANALYSIS: ["data", "pattern", "insight", "trend", "conclusion"],
            ContentType.ACTION_PLAN: ["step", "requirement", "timeline", "outcome", "verification"],
            ContentType.REPORT: ["summary", "finding", "recommendation", "conclusion", "metric"]
        }

    def _calculate_element_score(self, content_lower: str, elements: list[str]) -> float:
        """Calculate score based on required elements"""
        found = sum(1 for elem in elements if elem in content_lower)
        return found / len(elements)

    def _calculate_basic_completeness(self, content: str, content_lower: str) -> float:
        """Calculate basic completeness for unknown content types"""
        score = 0.0
        sentences = len(re.split(r'[.!?]+', content))
        words = len(content.split())
        if sentences >= 3:
            score += 0.3
        if words >= 50:
            score += 0.3
        if "however" in content_lower or "but" in content_lower:
            score += 0.2
        if "because" in content_lower or "due to" in content_lower:
            score += 0.2
        return score

    async def calculate_completeness(self, content: str, content_type: ContentType) -> float:
        """Calculate if the content is complete for its type"""
        content_lower = content.lower()
        required_elements = self._get_required_elements()
        if content_type in required_elements:
            elements = required_elements[content_type]
            score = self._calculate_element_score(content_lower, elements)
        else:
            score = self._calculate_basic_completeness(content, content_lower)
        return min(1.0, score)
    
    def _generate_content_hash(self, content: str) -> str:
        """Generate hash for content"""
        return hashlib.md5(content.encode()).hexdigest()

    async def _check_redis_novelty(self, content_hash: str) -> float:
        """Check novelty using Redis cache"""
        try:
            recent_hashes = await self.redis_manager.get_list("quality:recent_hashes", limit=100)
            if content_hash in recent_hashes:
                return 0.0
            await self.redis_manager.add_to_list("quality:recent_hashes", content_hash, max_size=1000)
            return 0.8
        except Exception as e:
            logger.warning(f"Could not check novelty: {str(e)}")
            return 0.5

    async def calculate_novelty(self, content: str) -> float:
        """Calculate novelty compared to recent outputs"""
        content_hash = self._generate_content_hash(content)
        if self.redis_manager:
            return await self._check_redis_novelty(content_hash)
        return 0.5
    
    def _check_specific_numbers(self, content: str, context: Optional[Dict[str, Any]]) -> float:
        """Check for overly specific numbers without context"""
        very_specific_pattern = r'\b\d{4,}\.?\d*\b'
        specific_matches = re.findall(very_specific_pattern, content)
        if specific_matches and (not context or 'data_source' not in context):
            return 0.2
        return 0.0

    def _check_unsupported_claims(self, content: str) -> float:
        """Check for claims without evidence markers"""
        claim_patterns = [r'studies show', r'research indicates', r'data proves', r'always', r'never', r'guaranteed', r'definitely']
        risk = 0.0
        for pattern in claim_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                if not re.search(r'\[\d+\]|\(\d{4}\)|according to|based on', content):
                    risk += 0.1
        return risk

    def _check_impossible_claims(self, content: str) -> float:
        """Check for impossible claims in optimization context"""
        impossible_patterns = [r'100% improvement', r'zero latency', r'infinite throughput', r'no cost', r'perfect accuracy']
        for pattern in impossible_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return 0.3
        return 0.0

    async def calculate_hallucination_risk(self, content: str, context: Optional[Dict[str, Any]]) -> float:
        """Estimate risk of hallucination in content"""
        numbers_risk = self._check_specific_numbers(content, context)
        claims_risk = self._check_unsupported_claims(content)
        impossible_risk = self._check_impossible_claims(content)
        return min(1.0, numbers_risk + claims_risk + impossible_risk)
    
    def _get_optimization_indicators(self) -> list[str]:
        """Get optimization domain indicators"""
        return ["profiling", "bottleneck", "benchmark", "scaling", "memory footprint",
                "cpu utilization", "gpu utilization", "throughput optimization",
                "latency reduction", "cost efficiency", "performance tuning"]

    def _get_optimization_techniques(self) -> list[str]:
        """Get optimization techniques list"""
        return ["caching strategy", "load balancing", "database indexing",
                "code optimization", "algorithm optimization", "memory management"]

    def _get_analysis_indicators(self) -> list[str]:
        """Get data analysis indicators"""
        return ["statistical significance", "correlation", "regression", "variance",
                "distribution", "outliers", "trends", "patterns", "anomalies"]

    def _get_planning_indicators(self) -> list[str]:
        """Get planning indicators"""
        return ["milestone", "deliverable", "timeline", "resource allocation",
                "risk mitigation", "success criteria", "kpi", "validation"]

    def _calculate_optimization_score(self, content_lower: str) -> float:
        """Calculate optimization domain score"""
        indicators = self._get_optimization_indicators()
        techniques = self._get_optimization_techniques()
        found_indicators = sum(1 for indicator in indicators if indicator in content_lower)
        found_techniques = sum(1 for technique in techniques if technique in content_lower)
        return min(found_indicators * 0.1, 0.4) + min(found_techniques * 0.15, 0.3)

    def _calculate_analysis_score(self, content_lower: str) -> float:
        """Calculate data analysis domain score"""
        indicators = self._get_analysis_indicators()
        found_indicators = sum(1 for indicator in indicators if indicator in content_lower)
        return min(found_indicators * 0.1, 0.4)

    def _calculate_planning_score(self, content_lower: str) -> float:
        """Calculate planning domain score"""
        indicators = self._get_planning_indicators()
        found_indicators = sum(1 for indicator in indicators if indicator in content_lower)
        return min(found_indicators * 0.1, 0.4)

    async def calculate_domain_expertise(self, content: str, content_type: ContentType) -> float:
        """Calculate domain-specific expertise indicators"""
        content_lower = content.lower()
        if content_type == ContentType.OPTIMIZATION:
            score = self._calculate_optimization_score(content_lower)
        elif content_type == ContentType.DATA_ANALYSIS:
            score = self._calculate_analysis_score(content_lower)
        elif content_type == ContentType.ACTION_PLAN:
            score = self._calculate_planning_score(content_lower)
        else:
            score = 0.0
        return min(1.0, score)
    
    def _get_technical_patterns(self) -> list[str]:
        """Get technical terminology patterns"""
        return [r'\b[A-Z]{2,}\b', r'\b\w+\.\w+\(\)', r'\b\d+\.\d+\.\d+\b',
                r'--\w+', r'[a-zA-Z_]\w*=[a-zA-Z_]\w*']

    def _get_explanation_patterns(self) -> list[str]:
        """Get technical explanation patterns"""
        return [r'because\s+\w+', r'due to\s+\w+', r'as a result of\s+\w+',
                r'this is\s+(caused by|due to|because)']

    def _calculate_pattern_score(self, content: str) -> float:
        """Calculate score from technical patterns"""
        patterns = self._get_technical_patterns()
        score = 0.0
        for pattern in patterns:
            matches = re.findall(pattern, content)
            score += min(len(matches) * 0.05, 0.2)
        return score

    def _check_code_snippets(self, content: str) -> float:
        """Check for code snippets or configuration"""
        if re.search(r'```|^\s*[a-zA-Z_]\w*\s*=', content, re.MULTILINE):
            return 0.3
        return 0.0

    def _check_explanations(self, content: str) -> float:
        """Check for technical explanations"""
        patterns = self._get_explanation_patterns()
        for pattern in patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return 0.1
        return 0.0

    async def calculate_technical_depth(self, content: str) -> float:
        """Calculate the technical depth of the content"""
        pattern_score = self._calculate_pattern_score(content)
        code_score = self._check_code_snippets(content)
        explanation_score = self._check_explanations(content)
        return min(1.0, pattern_score + code_score + explanation_score)