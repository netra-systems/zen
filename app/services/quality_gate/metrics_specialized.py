"""Specialized Quality Metrics Calculators"""

import re
import hashlib
from typing import Dict, Optional, Any

from app.logging_config import central_logger
from .quality_gate_models import ContentType, QualityMetrics
from .quality_gate_patterns import QualityPatterns

logger = central_logger.get_logger(__name__)


class SpecializedMetricsCalculator:
    """Specialized metrics calculators for domain-specific content"""
    
    def __init__(self, patterns: QualityPatterns, redis_manager=None):
        self.patterns = patterns
        self.redis_manager = redis_manager
    
    def _get_gpu_mappings(self) -> Dict[str, set]:
        """Get GPU-related semantic mappings"""
        return {
            'gpu': {'graphics', 'card', 'cards'},
            'gpus': {'graphics', 'card', 'cards'},
            'graphics': {'gpu', 'gpus'},
            'cards': {'gpu', 'gpus'}
        }

    def _get_training_mappings(self) -> Dict[str, set]:
        """Get training-related semantic mappings"""
        return {
            'training': {'convergence'},
            'distributed': {'multiple', 'parallel'},
            'neural': {'network'},
            'speed': {'faster', 'fast'},
            'faster': {'speed', 'fast'}
        }

    def _get_semantic_mappings(self) -> Dict[str, set]:
        """Get all semantic term equivalence mappings"""
        mappings = {}
        mappings.update(self._get_gpu_mappings())
        mappings.update(self._get_training_mappings())
        return mappings

    def _calculate_semantic_score(self, request_words: set, content_words: set) -> float:
        """Calculate semantic relevance score"""
        mappings = self._get_semantic_mappings()
        semantic_matches = 0
        for req_word in request_words:
            if req_word in mappings:
                if any(sem_word in content_words for sem_word in mappings[req_word]):
                    semantic_matches += 1
        return min(semantic_matches * 0.2, 0.6) if request_words else 0.0

    def _calculate_word_overlap_score(self, request_words: set, content_words: set) -> float:
        """Calculate direct word overlap score"""
        if not request_words:
            return 0.0
        overlap = len(request_words & content_words)
        return min(overlap / len(request_words) * 0.8, 0.4)

    def _calculate_technical_terms_score(self, request_words: set, content_lower: str) -> float:
        """Calculate technical terms matching score"""
        technical_terms = [word for word in request_words if len(word) > 4]
        if not technical_terms:
            return 0.0
        addressed_terms = sum(1 for term in technical_terms if term in content_lower)
        return min(addressed_terms / len(technical_terms), 0.5) * 0.4

    async def calculate_relevance(self, content: str, context: Optional[Dict[str, Any]]) -> float:
        """Calculate relevance to the context and user request"""
        if not context or 'user_request' not in context:
            return 0.5
        user_request, content_lower = context['user_request'].lower(), content.lower()
        request_words, content_words = set(user_request.split()), set(content_lower.split())
        
        overlap_score = self._calculate_word_overlap_score(request_words, content_words)
        semantic_score = self._calculate_semantic_score(request_words, content_words)
        technical_score = self._calculate_technical_terms_score(request_words, content_lower)
        return min(overlap_score + semantic_score + technical_score, 1.0)
    
    async def calculate_completeness(self, content: str, content_type: ContentType) -> float:
        """Calculate if the content is complete for its type"""
        score = 0.0
        content_lower = content.lower()
        
        # Define required elements by content type
        required_elements = {
            ContentType.OPTIMIZATION: ["improve", "reduce", "increase", "optimize", "change"],
            ContentType.DATA_ANALYSIS: ["data", "pattern", "insight", "trend", "conclusion"],
            ContentType.ACTION_PLAN: ["step", "requirement", "timeline", "outcome", "verification"],
            ContentType.REPORT: ["summary", "finding", "recommendation", "conclusion", "metric"]
        }
        
        if content_type in required_elements:
            elements = required_elements[content_type]
            found = sum(1 for elem in elements if elem in content_lower)
            score = found / len(elements)
        else:
            # For other types, check basic completeness
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
        
        return min(1.0, score)
    
    async def calculate_novelty(self, content: str) -> float:
        """Calculate novelty compared to recent outputs"""
        content_hash = hashlib.md5(content.encode()).hexdigest()
        
        if self.redis_manager:
            try:
                recent_hashes = await self.redis_manager.get_list("quality:recent_hashes", limit=100)
                if content_hash in recent_hashes:
                    return 0.0
                await self.redis_manager.add_to_list("quality:recent_hashes", content_hash, max_size=1000)
                return 0.8
            except Exception as e:
                logger.warning(f"Could not check novelty: {str(e)}")
        
        return 0.5
    
    async def calculate_hallucination_risk(self, content: str, context: Optional[Dict[str, Any]]) -> float:
        """Estimate risk of hallucination in content"""
        risk = 0.0
        
        # Check for overly specific numbers without context
        very_specific_pattern = r'\b\d{4,}\.?\d*\b'
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
    
    async def calculate_domain_expertise(self, content: str, content_type: ContentType) -> float:
        """Calculate domain-specific expertise indicators"""
        score = 0.0
        content_lower = content.lower()
        
        # Domain-specific scoring based on content type
        if content_type == ContentType.OPTIMIZATION:
            # Look for optimization-specific terminology and concepts
            optimization_indicators = [
                "profiling", "bottleneck", "benchmark", "scaling", "memory footprint",
                "cpu utilization", "gpu utilization", "throughput optimization",
                "latency reduction", "cost efficiency", "performance tuning"
            ]
            found_indicators = sum(1 for indicator in optimization_indicators if indicator in content_lower)
            score += min(found_indicators * 0.1, 0.4)
            
            # Check for specific optimization techniques
            techniques = [
                "caching strategy", "load balancing", "database indexing",
                "code optimization", "algorithm optimization", "memory management"
            ]
            found_techniques = sum(1 for technique in techniques if technique in content_lower)
            score += min(found_techniques * 0.15, 0.3)
        
        elif content_type == ContentType.DATA_ANALYSIS:
            # Look for data analysis terminology
            analysis_indicators = [
                "statistical significance", "correlation", "regression", "variance",
                "distribution", "outliers", "trends", "patterns", "anomalies"
            ]
            found_indicators = sum(1 for indicator in analysis_indicators if indicator in content_lower)
            score += min(found_indicators * 0.1, 0.4)
            
        elif content_type == ContentType.ACTION_PLAN:
            # Look for project management and planning terminology
            planning_indicators = [
                "milestone", "deliverable", "timeline", "resource allocation",
                "risk mitigation", "success criteria", "kpi", "validation"
            ]
            found_indicators = sum(1 for indicator in planning_indicators if indicator in content_lower)
            score += min(found_indicators * 0.1, 0.4)
        
        return min(1.0, score)
    
    async def calculate_technical_depth(self, content: str) -> float:
        """Calculate the technical depth of the content"""
        score = 0.0
        
        # Check for technical terminology depth
        technical_patterns = [
            r'\b[A-Z]{2,}\b',  # Acronyms
            r'\b\w+\.\w+\(\)',  # Method calls
            r'\b\d+\.\d+\.\d+\b',  # Version numbers
            r'--\w+',  # Command line flags
            r'[a-zA-Z_]\w*=[a-zA-Z_]\w*',  # Parameter assignments
        ]
        
        for pattern in technical_patterns:
            matches = re.findall(pattern, content)
            score += min(len(matches) * 0.05, 0.2)
        
        # Check for code snippets or configuration examples
        if re.search(r'```|^\s*[a-zA-Z_]\w*\s*=', content, re.MULTILINE):
            score += 0.3
        
        # Check for technical explanations
        explanation_patterns = [
            r'because\s+\w+',
            r'due to\s+\w+',
            r'as a result of\s+\w+',
            r'this is\s+(caused by|due to|because)',
        ]
        
        for pattern in explanation_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                score += 0.1
        
        return min(1.0, score)