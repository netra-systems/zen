"""
Quality Validation Service for AI Slop Prevention
Implements comprehensive quality checks for all AI-generated outputs
"""

import re
import json
from typing import Dict, Any, Tuple, List, Optional
from dataclasses import dataclass
from enum import Enum
import numpy as np
from pydantic import BaseModel, Field, validator


class QualityLevel(Enum):
    """Quality level classifications"""
    EXCELLENT = "excellent"  # Score >= 0.9
    GOOD = "good"           # Score >= 0.75
    ACCEPTABLE = "acceptable"  # Score >= 0.6
    POOR = "poor"           # Score >= 0.4
    UNACCEPTABLE = "unacceptable"  # Score < 0.4


class QualityMetrics(BaseModel):
    """Detailed quality metrics for an output"""
    overall_score: float = Field(ge=0, le=1)
    specificity_score: float = Field(ge=0, le=1)
    actionability_score: float = Field(ge=0, le=1)
    quantification_score: float = Field(ge=0, le=1)
    novelty_score: float = Field(ge=0, le=1)
    completeness_score: float = Field(ge=0, le=1)
    domain_relevance_score: float = Field(ge=0, le=1)
    quality_level: QualityLevel
    issues_detected: List[str] = Field(default_factory=list)
    improvements_suggested: List[str] = Field(default_factory=list)


@dataclass
class ValidationConfig:
    """Configuration for quality validation"""
    min_length: int = 100
    min_quality_score: float = 0.7
    min_specificity: float = 0.7
    min_actionability: float = 0.6
    require_metrics: bool = True
    require_concrete_steps: bool = True
    max_generic_phrase_ratio: float = 0.1


class QualityValidationService:
    """Service for validating AI output quality and detecting slop"""
    
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
    
    def __init__(self, config: Optional[ValidationConfig] = None):
        """Initialize the quality validation service"""
        self.config = config or ValidationConfig()
        
    def validate_output(self, 
                       output: str, 
                       output_type: str = "general",
                       context: Optional[Dict[str, Any]] = None) -> Tuple[bool, QualityMetrics]:
        """
        Validate the quality of an AI-generated output
        
        Args:
            output: The text output to validate
            output_type: Type of output (e.g., "report", "recommendation", "analysis")
            context: Additional context for validation
            
        Returns:
            Tuple of (is_valid, quality_metrics)
        """
        metrics = self._calculate_metrics(output, output_type)
        is_valid = self._determine_validity(metrics)
        
        return is_valid, metrics
    
    def _calculate_metrics(self, output: str, output_type: str) -> QualityMetrics:
        """Calculate all quality metrics for the output"""
        # Calculate individual scores
        specificity = self._calculate_specificity_score(output)
        actionability = self._calculate_actionability_score(output)
        quantification = self._calculate_quantification_score(output)
        novelty = self._calculate_novelty_score(output)
        completeness = self._calculate_completeness_score(output, output_type)
        domain_relevance = self._calculate_domain_relevance_score(output)
        
        # Calculate weighted overall score
        weights = {
            'specificity': 0.25,
            'actionability': 0.20,
            'quantification': 0.20,
            'novelty': 0.10,
            'completeness': 0.15,
            'domain_relevance': 0.10
        }
        
        overall_score = (
            specificity * weights['specificity'] +
            actionability * weights['actionability'] +
            quantification * weights['quantification'] +
            novelty * weights['novelty'] +
            completeness * weights['completeness'] +
            domain_relevance * weights['domain_relevance']
        )
        
        # Determine quality level
        if overall_score >= 0.9:
            quality_level = QualityLevel.EXCELLENT
        elif overall_score >= 0.75:
            quality_level = QualityLevel.GOOD
        elif overall_score >= 0.6:
            quality_level = QualityLevel.ACCEPTABLE
        elif overall_score >= 0.4:
            quality_level = QualityLevel.POOR
        else:
            quality_level = QualityLevel.UNACCEPTABLE
        
        # Detect issues
        issues = self._detect_issues(output, {
            'specificity': specificity,
            'actionability': actionability,
            'quantification': quantification
        })
        
        # Suggest improvements
        improvements = self._suggest_improvements({
            'specificity': specificity,
            'actionability': actionability,
            'quantification': quantification
        })
        
        return QualityMetrics(
            overall_score=overall_score,
            specificity_score=specificity,
            actionability_score=actionability,
            quantification_score=quantification,
            novelty_score=novelty,
            completeness_score=completeness,
            domain_relevance_score=domain_relevance,
            quality_level=quality_level,
            issues_detected=issues,
            improvements_suggested=improvements
        )
    
    def _calculate_specificity_score(self, output: str) -> float:
        """Calculate how specific vs generic the output is"""
        output_lower = output.lower()
        
        # Count generic phrases
        generic_count = sum(1 for phrase in self.GENERIC_PHRASES 
                          if phrase in output_lower)
        
        # Check for circular reasoning
        circular_count = sum(1 for pattern in self.CIRCULAR_PATTERNS
                           if re.search(pattern, output_lower))
        
        # Check for vague patterns
        vague_count = sum(1 for pattern in self.VAGUE_PATTERNS
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
    
    def _calculate_actionability_score(self, output: str) -> float:
        """Calculate how actionable the recommendations are"""
        output_lower = output.lower()
        
        # Count action keywords
        action_count = sum(1 for keyword in self.ACTION_KEYWORDS
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
    
    def _calculate_quantification_score(self, output: str) -> float:
        """Calculate presence of quantifiable metrics"""
        # Count quantification indicators
        quant_matches = sum(len(re.findall(pattern, output)) 
                          for pattern in self.QUANTIFICATION_INDICATORS)
        
        # Normalize by output length
        word_count = len(output.split())
        if word_count == 0:
            return 0.0
        
        # Expect roughly 1 metric per 50 words for good quantification
        expected_metrics = word_count / 50
        score = min(1.0, quant_matches / max(expected_metrics, 1))
        
        return score
    
    def _calculate_novelty_score(self, output: str) -> float:
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
    
    def _calculate_completeness_score(self, output: str, output_type: str) -> float:
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
    
    def _calculate_domain_relevance_score(self, output: str) -> float:
        """Calculate relevance to optimization domain"""
        output_lower = output.lower()
        
        # Count domain keywords
        domain_count = sum(1 for keyword in self.DOMAIN_KEYWORDS
                         if keyword in output_lower)
        
        # Normalize by output length
        word_count = len(output.split())
        if word_count == 0:
            return 0.0
        
        # Expect domain terms every 30-40 words
        expected_terms = word_count / 35
        score = min(1.0, domain_count / max(expected_terms, 1))
        
        return score
    
    def _determine_validity(self, metrics: QualityMetrics) -> bool:
        """Determine if output meets quality thresholds"""
        return (
            metrics.overall_score >= self.config.min_quality_score and
            metrics.specificity_score >= self.config.min_specificity and
            metrics.actionability_score >= self.config.min_actionability and
            metrics.quality_level not in [QualityLevel.POOR, QualityLevel.UNACCEPTABLE]
        )
    
    def _detect_issues(self, output: str, scores: Dict[str, float]) -> List[str]:
        """Detect specific quality issues"""
        issues = []
        
        if len(output) < self.config.min_length:
            issues.append(f"Output too short ({len(output)} chars, minimum {self.config.min_length})")
        
        if scores['specificity'] < 0.5:
            issues.append("High presence of generic language and vague statements")
        
        if scores['actionability'] < 0.3:
            issues.append("Lacks actionable recommendations or concrete steps")
        
        if scores['quantification'] < 0.2:
            issues.append("Missing quantifiable metrics and measurements")
        
        # Check for specific slop patterns
        if any(phrase in output.lower() for phrase in self.GENERIC_PHRASES[:5]):
            issues.append("Contains generic AI phrases")
        
        return issues
    
    def _suggest_improvements(self, scores: Dict[str, float]) -> List[str]:
        """Suggest improvements based on scores"""
        improvements = []
        
        if scores['specificity'] < 0.7:
            improvements.append("Add specific technical details and avoid generic language")
        
        if scores['actionability'] < 0.6:
            improvements.append("Include concrete implementation steps with parameters")
        
        if scores['quantification'] < 0.5:
            improvements.append("Add measurable metrics (percentages, times, sizes)")
        
        return improvements
    
    def validate_agent_output(self, 
                             agent_name: str,
                             output: Dict[str, Any]) -> Tuple[bool, QualityMetrics]:
        """
        Validate output from a specific agent
        
        Args:
            agent_name: Name of the agent
            output: Agent's output dictionary
            
        Returns:
            Tuple of (is_valid, quality_metrics)
        """
        # Extract text content from agent output
        if isinstance(output, dict):
            # Try common keys
            text_content = (
                output.get('report', '') or
                output.get('analysis', '') or 
                output.get('recommendations', '') or
                output.get('data', '') or
                json.dumps(output)
            )
        else:
            text_content = str(output)
        
        # Determine output type based on agent
        output_type_map = {
            'TriageSubAgent': 'analysis',
            'DataSubAgent': 'analysis',
            'OptimizationsCoreSubAgent': 'recommendation',
            'ActionsToMeetGoalsSubAgent': 'recommendation',
            'ReportingSubAgent': 'report'
        }
        
        output_type = output_type_map.get(agent_name, 'general')
        
        return self.validate_output(text_content, output_type)
    
    def get_quality_report(self, metrics: QualityMetrics) -> str:
        """Generate a human-readable quality report"""
        report = f"""
Quality Assessment Report
========================
Overall Score: {metrics.overall_score:.2f} ({metrics.quality_level.value.upper()})

Detailed Scores:
- Specificity: {metrics.specificity_score:.2f}
- Actionability: {metrics.actionability_score:.2f}
- Quantification: {metrics.quantification_score:.2f}
- Novelty: {metrics.novelty_score:.2f}
- Completeness: {metrics.completeness_score:.2f}
- Domain Relevance: {metrics.domain_relevance_score:.2f}

Issues Detected: {len(metrics.issues_detected)}
{chr(10).join(f'  - {issue}' for issue in metrics.issues_detected) if metrics.issues_detected else '  None'}

Suggested Improvements: {len(metrics.improvements_suggested)}
{chr(10).join(f'  - {improvement}' for improvement in metrics.improvements_suggested) if metrics.improvements_suggested else '  None'}
"""
        return report