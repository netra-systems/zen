"""
Quality Score Calculation Functions
Contains all score calculation methods for different quality dimensions
"""

import re
from typing import List


class QualityScoreCalculators:
    """Collection of score calculation methods for quality validation"""
    
    # Generic phrases that indicate AI slop
    GENERIC_PHRASES = [
        "it is important to note that",
        "generally speaking",
        "in general",
        "as you may know",
        "it's worth mentioning",
        "consider the following",
        "various factors",
        "multiple aspects",
        "different approaches",
        "several options",
        "optimize performance",
        "improve efficiency",
        "enhance capabilities",
        "increase effectiveness",
        "better results"
    ]
    
    # Circular reasoning patterns
    CIRCULAR_PATTERNS = [
        r"to improve (.*?) you should improve",
        r"optimize (.*?) by optimizing",
        r"better (.*?) through better",
        r"enhance (.*?) by enhancing",
        r"increase (.*?) by increasing"
    ]
    
    # Vague recommendation patterns
    VAGUE_PATTERNS = [
        r"consider using",
        r"think about",
        r"look into",
        r"explore options",
        r"evaluate possibilities",
        r"assess alternatives"
    ]
    
    # Quantification indicators
    QUANTIFICATION_INDICATORS = [
        r"\d+%",  # Percentages
        r"\d+ms",  # Milliseconds
        r"\d+x",   # Multipliers
        r"\d+\.\d+",  # Decimals
        r"by \d+",  # Specific amounts
        r"from \d+ to \d+",  # Ranges
        r"\d+ (seconds|minutes|hours)",  # Time measurements
        r"\d+ (MB|GB|TB)",  # Memory measurements
    ]
    
    # Action-oriented keywords
    ACTION_KEYWORDS = [
        "implement", "configure", "set", "adjust", "modify",
        "update", "change", "deploy", "execute", "run",
        "install", "enable", "disable", "create", "delete",
        "add", "remove", "replace", "migrate", "upgrade"
    ]
    
    # Optimization domain keywords
    DOMAIN_KEYWORDS = [
        "latency", "throughput", "bandwidth", "cache", "memory",
        "cpu", "gpu", "batch", "quantization", "pruning",
        "distillation", "compression", "parallelization", "sharding",
        "replication", "load balancing", "rate limiting", "qps",
        "token", "embedding", "inference", "training", "fine-tuning"
    ]
    
    @staticmethod
    def calculate_specificity_score(output: str) -> float:
        """Calculate how specific vs generic the output is"""
        output_lower = output.lower()
        
        # Count generic phrases
        generic_count = sum(1 for phrase in QualityScoreCalculators.GENERIC_PHRASES 
                          if phrase in output_lower)
        
        # Check for circular reasoning
        circular_count = sum(1 for pattern in QualityScoreCalculators.CIRCULAR_PATTERNS
                           if re.search(pattern, output_lower))
        
        # Check for vague patterns
        vague_count = sum(1 for pattern in QualityScoreCalculators.VAGUE_PATTERNS
                        if re.search(pattern, output_lower))
        
        # Calculate word count for ratio
        word_count = len(output.split())
        if word_count == 0:
            return 0.0
        
        # Calculate negative indicators ratio
        total_issues = generic_count + circular_count + vague_count
        issue_ratio = total_issues / max(word_count / 20, 1)  # Normalize by chunks of 20 words
        
        # Score decreases with more generic content
        score = max(0.0, 1.0 - (issue_ratio * 0.2))
        
        # Bonus for specific technical terms
        technical_terms = len(re.findall(r'\b[A-Z][a-zA-Z]+(?:[A-Z][a-z]+)*\b', output))
        score = min(1.0, score + (technical_terms * 0.02))
        
        return score
    
    @staticmethod
    def calculate_actionability_score(output: str) -> float:
        """Calculate how actionable the recommendations are"""
        output_lower = output.lower()
        
        # Count action keywords
        action_count = sum(1 for keyword in QualityScoreCalculators.ACTION_KEYWORDS
                         if keyword in output_lower)
        
        # Check for step-by-step instructions
        has_steps = bool(re.search(r'(step \d+|first|second|third|finally)', output_lower))
        
        # Check for code examples
        has_code = bool(re.search(r'```|`[^`]+`', output))
        
        # Check for specific parameters
        has_parameters = bool(re.search(r'(=\s*\d+|:\s*\d+|set to \d+)', output))
        
        # Calculate score
        score = 0.0
        
        # Base score from action keywords
        if action_count > 0:
            score += min(0.5, action_count * 0.1)
        
        # Bonus for structure
        if has_steps:
            score += 0.2
        if has_code:
            score += 0.2
        if has_parameters:
            score += 0.1
        
        return min(1.0, score)
    
    @staticmethod
    def calculate_quantification_score(output: str) -> float:
        """Calculate presence of quantifiable metrics"""
        # Count quantification indicators
        quant_matches = sum(len(re.findall(pattern, output)) 
                          for pattern in QualityScoreCalculators.QUANTIFICATION_INDICATORS)
        
        # Normalize by output length
        word_count = len(output.split())
        if word_count == 0:
            return 0.0
        
        # Expect roughly 1 metric per 50 words for good quantification
        expected_metrics = word_count / 50
        score = min(1.0, quant_matches / max(expected_metrics, 1))
        
        return score
    
    @staticmethod
    def calculate_novelty_score(output: str) -> float:
        """Calculate how novel/unique vs boilerplate the content is"""
        # Simple heuristic: Check for unique word ratio
        words = output.lower().split()
        if not words:
            return 0.0
        
        unique_words = len(set(words))
        total_words = len(words)
        
        # Higher ratio of unique words indicates less repetition
        uniqueness_ratio = unique_words / total_words
        
        # Check for boilerplate patterns
        boilerplate_patterns = [
            r"thank you for",
            r"i hope this helps",
            r"please let me know",
            r"feel free to",
            r"don't hesitate to"
        ]
        
        boilerplate_count = sum(1 for pattern in boilerplate_patterns
                               if re.search(pattern, output.lower()))
        
        # Calculate score
        score = uniqueness_ratio
        score -= (boilerplate_count * 0.1)
        
        return max(0.0, min(1.0, score))
    
    @staticmethod
    def calculate_completeness_score(output: str, output_type: str) -> float:
        """Calculate if the output is complete for its type"""
        word_count = len(output.split())
        
        # Different expectations for different output types
        min_lengths = {
            "report": 200,
            "recommendation": 100,
            "analysis": 150,
            "general": 50
        }
        
        expected_length = min_lengths.get(output_type, 100)
        
        if word_count < expected_length * 0.5:
            return 0.3
        elif word_count < expected_length:
            return 0.6
        else:
            return min(1.0, 0.8 + (word_count / expected_length) * 0.1)
    
    @staticmethod
    def calculate_domain_relevance_score(output: str) -> float:
        """Calculate relevance to optimization domain"""
        output_lower = output.lower()
        
        # Count domain keywords
        domain_count = sum(1 for keyword in QualityScoreCalculators.DOMAIN_KEYWORDS
                         if keyword in output_lower)
        
        # Normalize by output length
        word_count = len(output.split())
        if word_count == 0:
            return 0.0
        
        # Expect domain terms every 30-40 words
        expected_terms = word_count / 35
        score = min(1.0, domain_count / max(expected_terms, 1))
        
        return score