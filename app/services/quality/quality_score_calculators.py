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
    def _count_generic_phrases(output_lower: str) -> int:
        """Count generic AI slop phrases in text"""
        return sum(1 for phrase in QualityScoreCalculators.GENERIC_PHRASES 
                  if phrase in output_lower)
    
    @staticmethod
    def _count_circular_patterns(output_lower: str) -> int:
        """Count circular reasoning patterns in text"""
        return sum(1 for pattern in QualityScoreCalculators.CIRCULAR_PATTERNS
                  if re.search(pattern, output_lower))
    
    @staticmethod
    def _count_vague_patterns(output_lower: str) -> int:
        """Count vague recommendation patterns in text"""
        return sum(1 for pattern in QualityScoreCalculators.VAGUE_PATTERNS
                  if re.search(pattern, output_lower))
    
    @staticmethod
    def _calculate_issue_ratio(total_issues: int, word_count: int) -> float:
        """Calculate normalized ratio of issues to content"""
        if word_count == 0:
            return 1.0
        return total_issues / max(word_count / 20, 1)
    
    @staticmethod
    def _count_technical_terms(output: str) -> int:
        """Count technical terms using CamelCase pattern"""
        return len(re.findall(r'\b[A-Z][a-zA-Z]+(?:[A-Z][a-z]+)*\b', output))
    
    @staticmethod
    def calculate_specificity_score(output: str) -> float:
        """Calculate how specific vs generic the output is"""
        output_lower = output.lower()
        word_count = len(output.split())
        if word_count == 0:
            return 0.0
        
        total_issues = (QualityScoreCalculators._count_generic_phrases(output_lower) +
                       QualityScoreCalculators._count_circular_patterns(output_lower) +
                       QualityScoreCalculators._count_vague_patterns(output_lower))
        issue_ratio = QualityScoreCalculators._calculate_issue_ratio(total_issues, word_count)
        score = max(0.0, 1.0 - (issue_ratio * 0.2))
        technical_bonus = QualityScoreCalculators._count_technical_terms(output) * 0.02
        return min(1.0, score + technical_bonus)
    
    @staticmethod
    def _count_action_keywords(output_lower: str) -> int:
        """Count action-oriented keywords in text"""
        return sum(1 for keyword in QualityScoreCalculators.ACTION_KEYWORDS
                  if keyword in output_lower)
    
    @staticmethod
    def _has_step_instructions(output_lower: str) -> bool:
        """Check for step-by-step instruction patterns"""
        return bool(re.search(r'(step \d+|first|second|third|finally)', output_lower))
    
    @staticmethod
    def _has_code_examples(output: str) -> bool:
        """Check for code example patterns"""
        return bool(re.search(r'```|`[^`]+`', output))
    
    @staticmethod
    def _has_specific_parameters(output: str) -> bool:
        """Check for specific parameter patterns"""
        return bool(re.search(r'(=\s*\d+|:\s*\d+|set to \d+)', output))
    
    @staticmethod
    def _calculate_actionability_base_score(action_count: int) -> float:
        """Calculate base score from action keyword count"""
        return min(0.5, action_count * 0.1) if action_count > 0 else 0.0
    
    @staticmethod
    def _calculate_actionability_bonuses(has_steps: bool, has_code: bool, has_parameters: bool) -> float:
        """Calculate bonus points for actionable structure elements"""
        bonus = 0.0
        if has_steps:
            bonus += 0.2
        if has_code:
            bonus += 0.2
        if has_parameters:
            bonus += 0.1
        return bonus
    
    @staticmethod
    def calculate_actionability_score(output: str) -> float:
        """Calculate how actionable the recommendations are"""
        output_lower = output.lower()
        action_count = QualityScoreCalculators._count_action_keywords(output_lower)
        base_score = QualityScoreCalculators._calculate_actionability_base_score(action_count)
        
        has_steps = QualityScoreCalculators._has_step_instructions(output_lower)
        has_code = QualityScoreCalculators._has_code_examples(output)
        has_parameters = QualityScoreCalculators._has_specific_parameters(output)
        bonuses = QualityScoreCalculators._calculate_actionability_bonuses(has_steps, has_code, has_parameters)
        
        return min(1.0, base_score + bonuses)
    
    @staticmethod
    def _count_quantification_matches(output: str) -> int:
        """Count quantification indicators in text"""
        return sum(len(re.findall(pattern, output)) 
                  for pattern in QualityScoreCalculators.QUANTIFICATION_INDICATORS)
    
    @staticmethod
    def _calculate_expected_metrics(word_count: int) -> float:
        """Calculate expected number of metrics based on word count"""
        return word_count / 50
    
    @staticmethod
    def calculate_quantification_score(output: str) -> float:
        """Calculate presence of quantifiable metrics"""
        word_count = len(output.split())
        if word_count == 0:
            return 0.0
        
        quant_matches = QualityScoreCalculators._count_quantification_matches(output)
        expected_metrics = QualityScoreCalculators._calculate_expected_metrics(word_count)
        
        return min(1.0, quant_matches / max(expected_metrics, 1))
    
    @staticmethod
    def _get_boilerplate_patterns() -> List[str]:
        """Get list of common boilerplate patterns"""
        return [
            r"thank you for",
            r"i hope this helps",
            r"please let me know",
            r"feel free to",
            r"don't hesitate to"
        ]
    
    @staticmethod
    def _calculate_uniqueness_ratio(words: List[str]) -> float:
        """Calculate ratio of unique words to total words"""
        if not words:
            return 0.0
        unique_words = len(set(words))
        total_words = len(words)
        return unique_words / total_words
    
    @staticmethod
    def _count_boilerplate_patterns(output_lower: str) -> int:
        """Count boilerplate patterns in text"""
        patterns = QualityScoreCalculators._get_boilerplate_patterns()
        return sum(1 for pattern in patterns
                  if re.search(pattern, output_lower))
    
    @staticmethod
    def calculate_novelty_score(output: str) -> float:
        """Calculate how novel/unique vs boilerplate the content is"""
        words = output.lower().split()
        if not words:
            return 0.0
        
        uniqueness_ratio = QualityScoreCalculators._calculate_uniqueness_ratio(words)
        boilerplate_count = QualityScoreCalculators._count_boilerplate_patterns(output.lower())
        score = uniqueness_ratio - (boilerplate_count * 0.1)
        
        return max(0.0, min(1.0, score))
    
    @staticmethod
    def _get_min_length_requirements() -> dict:
        """Get minimum length requirements by output type"""
        return {
            "report": 200,
            "recommendation": 100,
            "analysis": 150,
            "general": 50
        }
    
    @staticmethod
    def _calculate_completeness_ratio_score(word_count: int, expected_length: int) -> float:
        """Calculate score based on word count to expected length ratio"""
        if word_count < expected_length * 0.5:
            return 0.3
        elif word_count < expected_length:
            return 0.6
        else:
            return min(1.0, 0.8 + (word_count / expected_length) * 0.1)
    
    @staticmethod
    def calculate_completeness_score(output: str, output_type: str) -> float:
        """Calculate if the output is complete for its type"""
        word_count = len(output.split())
        min_lengths = QualityScoreCalculators._get_min_length_requirements()
        expected_length = min_lengths.get(output_type, 100)
        
        return QualityScoreCalculators._calculate_completeness_ratio_score(word_count, expected_length)
    
    @staticmethod
    def _count_domain_keywords(output_lower: str) -> int:
        """Count domain-specific keywords in text"""
        return sum(1 for keyword in QualityScoreCalculators.DOMAIN_KEYWORDS
                  if keyword in output_lower)
    
    @staticmethod
    def _calculate_expected_domain_terms(word_count: int) -> float:
        """Calculate expected number of domain terms based on word count"""
        return word_count / 35
    
    @staticmethod
    def calculate_domain_relevance_score(output: str) -> float:
        """Calculate relevance to optimization domain"""
        output_lower = output.lower()
        word_count = len(output.split())
        if word_count == 0:
            return 0.0
        
        domain_count = QualityScoreCalculators._count_domain_keywords(output_lower)
        expected_terms = QualityScoreCalculators._calculate_expected_domain_terms(word_count)
        
        return min(1.0, domain_count / max(expected_terms, 1))