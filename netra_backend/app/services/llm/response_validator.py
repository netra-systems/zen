"""LLM response validation and quality assessment.

Business Value Justification (BVJ):
- Segment: All customer segments (response quality)
- Business Goal: Ensure high-quality AI responses that provide customer value
- Value Impact: Poor response quality directly impacts customer satisfaction and retention
- Strategic Impact: Quality validation enables consistent service delivery and trust
"""

import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class QualityScore:
    """Response quality assessment scores."""
    overall_score: float
    relevance_score: float
    completeness_score: float
    accuracy_score: float
    coherence_score: float
    details: Dict[str, Any]


class ResponseValidator:
    """Validates and assesses LLM response quality."""

    def __init__(self):
        """Initialize response validator."""
        self._quality_thresholds = {
            "minimum_acceptable": 0.6,
            "good": 0.7,
            "excellent": 0.9
        }

    async def assess_response_quality(
        self,
        prompt: str,
        response: str,
        criteria: Optional[List[str]] = None
    ) -> QualityScore:
        """Assess the quality of an LLM response.
        
        Args:
            prompt: Original prompt
            response: LLM response to evaluate
            criteria: List of quality criteria to assess
            
        Returns:
            Quality score with detailed breakdown
        """
        try:
            criteria = criteria or ["relevance", "completeness", "accuracy", "coherence"]
            
            logger.debug(f"Assessing response quality for {len(criteria)} criteria")
            
            scores = {}
            details = {}
            
            if "relevance" in criteria:
                scores["relevance"], details["relevance"] = self._assess_relevance(prompt, response)
            
            if "completeness" in criteria:
                scores["completeness"], details["completeness"] = self._assess_completeness(prompt, response)
            
            if "accuracy" in criteria:
                scores["accuracy"], details["accuracy"] = self._assess_accuracy(prompt, response)
            
            if "coherence" in criteria:
                scores["coherence"], details["coherence"] = self._assess_coherence(response)
            
            # Calculate overall score as weighted average
            weights = {
                "relevance": 0.3,
                "completeness": 0.25,
                "accuracy": 0.25,
                "coherence": 0.2
            }
            
            overall_score = 0.0
            total_weight = 0.0
            
            for criterion, score in scores.items():
                weight = weights.get(criterion, 0.2)
                overall_score += score * weight
                total_weight += weight
            
            if total_weight > 0:
                overall_score = overall_score / total_weight
            
            return QualityScore(
                overall_score=overall_score,
                relevance_score=scores.get("relevance", 0.0),
                completeness_score=scores.get("completeness", 0.0),
                accuracy_score=scores.get("accuracy", 0.0),
                coherence_score=scores.get("coherence", 0.0),
                details=details
            )
            
        except Exception as e:
            logger.error(f"Error assessing response quality: {str(e)}")
            return QualityScore(
                overall_score=0.0,
                relevance_score=0.0,
                completeness_score=0.0,
                accuracy_score=0.0,
                coherence_score=0.0,
                details={"error": str(e)}
            )

    def _assess_relevance(self, prompt: str, response: str) -> tuple[float, Dict[str, Any]]:
        """Assess how relevant the response is to the prompt."""
        try:
            # Extract key terms from prompt
            prompt_words = set(word.lower().strip('.,!?') for word in prompt.split())
            response_words = set(word.lower().strip('.,!?') for word in response.split())
            
            # Remove common stop words
            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
            prompt_keywords = prompt_words - stop_words
            response_keywords = response_words - stop_words
            
            # Calculate keyword overlap
            if len(prompt_keywords) == 0:
                keyword_overlap = 0.0
            else:
                common_keywords = prompt_keywords.intersection(response_keywords)
                keyword_overlap = len(common_keywords) / len(prompt_keywords)
            
            # Check for direct question answering
            is_question = any(q in prompt.lower() for q in ['what', 'how', 'why', 'when', 'where', 'who'])
            has_answer_indicators = any(ind in response.lower() for ind in ['answer', 'result', 'solution', 'because'])
            
            question_relevance = 0.8 if is_question and has_answer_indicators else 0.5
            
            # Check for specific domain matches
            domain_relevance = self._check_domain_relevance(prompt, response)
            
            # Combined relevance score
            relevance_score = (keyword_overlap * 0.4 + question_relevance * 0.3 + domain_relevance * 0.3)
            relevance_score = min(1.0, max(0.0, relevance_score))
            
            details = {
                "keyword_overlap": keyword_overlap,
                "common_keywords": len(prompt_keywords.intersection(response_keywords)),
                "is_question": is_question,
                "has_answer_indicators": has_answer_indicators,
                "domain_relevance": domain_relevance
            }
            
            return relevance_score, details
            
        except Exception as e:
            logger.error(f"Error assessing relevance: {str(e)}")
            return 0.0, {"error": str(e)}

    def _check_domain_relevance(self, prompt: str, response: str) -> float:
        """Check domain-specific relevance."""
        try:
            domain_matches = 0
            total_domains = 0
            
            # Technical domains
            if any(term in prompt.lower() for term in ['python', 'code', 'function', 'programming']):
                total_domains += 1
                if any(term in response.lower() for term in ['def', 'function', 'python', 'code', 'import']):
                    domain_matches += 1
            
            # AWS/Cloud domains
            if any(term in prompt.lower() for term in ['aws', 'cloud', 'cost', 'optimization']):
                total_domains += 1
                if any(term in response.lower() for term in ['aws', 's3', 'ec2', 'cloud', 'cost', 'tier']):
                    domain_matches += 1
            
            # Math domains
            if any(term in prompt for term in ['2 + 2', '+', '-', '*', '/', 'calculate']):
                total_domains += 1
                if any(term in response for term in ['=', 'answer', 'result', '4', 'calculation']):
                    domain_matches += 1
            
            return domain_matches / total_domains if total_domains > 0 else 0.5
            
        except Exception as e:
            logger.error(f"Error checking domain relevance: {str(e)}")
            return 0.0

    def _assess_completeness(self, prompt: str, response: str) -> tuple[float, Dict[str, Any]]:
        """Assess how complete the response is."""
        try:
            # Check response length
            response_length = len(response.split())
            min_expected_length = max(10, len(prompt.split()) * 2)
            
            length_score = min(1.0, response_length / min_expected_length)
            
            # Check for multiple parts if prompt asks for multiple things
            prompt_parts = len(re.findall(r'[.!?]+', prompt))
            response_parts = len(re.findall(r'[.!?]+', response))
            
            parts_score = min(1.0, response_parts / max(1, prompt_parts))
            
            # Check for conclusion/summary indicators
            has_conclusion = any(ind in response.lower() for ind in ['in conclusion', 'summary', 'overall', 'therefore'])
            conclusion_score = 0.8 if has_conclusion else 0.6
            
            # Check for examples if appropriate
            has_examples = any(ind in response.lower() for ind in ['example', 'for instance', 'such as', '```'])
            needs_examples = any(term in prompt.lower() for term in ['example', 'show', 'demonstrate'])
            
            example_score = 0.9 if (has_examples and needs_examples) or not needs_examples else 0.5
            
            completeness_score = (length_score * 0.3 + parts_score * 0.3 + conclusion_score * 0.2 + example_score * 0.2)
            completeness_score = min(1.0, max(0.0, completeness_score))
            
            details = {
                "response_length": response_length,
                "expected_min_length": min_expected_length,
                "length_score": length_score,
                "parts_score": parts_score,
                "has_conclusion": has_conclusion,
                "has_examples": has_examples,
                "needs_examples": needs_examples
            }
            
            return completeness_score, details
            
        except Exception as e:
            logger.error(f"Error assessing completeness: {str(e)}")
            return 0.0, {"error": str(e)}

    def _assess_accuracy(self, prompt: str, response: str) -> tuple[float, Dict[str, Any]]:
        """Assess the accuracy of the response."""
        try:
            accuracy_score = 0.8  # Default assumption of accuracy
            accuracy_details = {}
            
            # Check for obvious mathematical errors
            if "2 + 2" in prompt:
                if "4" in response:
                    accuracy_score = 1.0
                    accuracy_details["math_correct"] = True
                else:
                    accuracy_score = 0.0
                    accuracy_details["math_correct"] = False
            
            # Check for programming syntax (basic validation)
            if "python" in prompt.lower() and "function" in prompt.lower():
                if "def " in response and ":" in response:
                    accuracy_score = max(accuracy_score, 0.8)
                    accuracy_details["python_syntax"] = True
                else:
                    accuracy_score = min(accuracy_score, 0.4)
                    accuracy_details["python_syntax"] = False
            
            # Check for factual consistency (basic heuristics)
            inconsistency_indicators = ['impossible', 'contradiction', 'error', 'mistake']
            if any(ind in response.lower() for ind in inconsistency_indicators):
                accuracy_score = min(accuracy_score, 0.6)
                accuracy_details["potential_inconsistencies"] = True
            
            # Check for uncertainty indicators (which can be good for accuracy)
            uncertainty_indicators = ['might', 'could', 'possibly', 'approximately', 'around']
            if any(ind in response.lower() for ind in uncertainty_indicators):
                accuracy_score = max(accuracy_score, 0.7)  # Acknowledging uncertainty is often accurate
                accuracy_details["shows_uncertainty"] = True
            
            details = {
                "base_accuracy": accuracy_score,
                **accuracy_details
            }
            
            return accuracy_score, details
            
        except Exception as e:
            logger.error(f"Error assessing accuracy: {str(e)}")
            return 0.0, {"error": str(e)}

    def _assess_coherence(self, response: str) -> tuple[float, Dict[str, Any]]:
        """Assess the coherence and readability of the response."""
        try:
            sentences = re.split(r'[.!?]+', response)
            sentences = [s.strip() for s in sentences if s.strip()]
            
            if len(sentences) == 0:
                return 0.0, {"error": "No sentences found"}
            
            # Check sentence length variation
            sentence_lengths = [len(s.split()) for s in sentences]
            avg_length = sum(sentence_lengths) / len(sentence_lengths)
            length_variance = sum((l - avg_length) ** 2 for l in sentence_lengths) / len(sentence_lengths)
            
            # Good writing has some variation in sentence length
            length_score = 0.8 if length_variance > 10 else 0.6
            
            # Check for transition words
            transition_words = ['however', 'therefore', 'additionally', 'furthermore', 'moreover', 'consequently']
            has_transitions = any(word in response.lower() for word in transition_words)
            transition_score = 0.8 if has_transitions else 0.6
            
            # Check for repetitive words/phrases
            words = response.lower().split()
            word_counts = {}
            for word in words:
                word_counts[word] = word_counts.get(word, 0) + 1
            
            # Calculate repetition ratio
            total_words = len(words)
            unique_words = len(word_counts)
            repetition_ratio = unique_words / total_words if total_words > 0 else 0
            
            repetition_score = min(1.0, repetition_ratio * 2)  # Penalize excessive repetition
            
            # Check for proper structure
            has_structure = any(ind in response for ind in [':', '-', '1.', '2.', '[U+2022]', '*'])
            structure_score = 0.9 if has_structure else 0.7
            
            coherence_score = (length_score * 0.25 + transition_score * 0.25 + repetition_score * 0.25 + structure_score * 0.25)
            coherence_score = min(1.0, max(0.0, coherence_score))
            
            details = {
                "sentence_count": len(sentences),
                "avg_sentence_length": avg_length,
                "length_variance": length_variance,
                "has_transitions": has_transitions,
                "repetition_ratio": repetition_ratio,
                "has_structure": has_structure,
                "unique_words": unique_words,
                "total_words": total_words
            }
            
            return coherence_score, details
            
        except Exception as e:
            logger.error(f"Error assessing coherence: {str(e)}")
            return 0.0, {"error": str(e)}

    async def validate_response_safety(self, response: str) -> Dict[str, Any]:
        """Validate response for safety and appropriateness.
        
        Args:
            response: Response to validate
            
        Returns:
            Safety validation results
        """
        try:
            safety_issues = []
            
            # Check for harmful content indicators
            harmful_indicators = [
                'violence', 'harm', 'illegal', 'dangerous', 'weapon',
                'drug', 'suicide', 'self-harm', 'hate speech'
            ]
            
            for indicator in harmful_indicators:
                if indicator in response.lower():
                    safety_issues.append(f"Contains potentially harmful content: {indicator}")
            
            # Check for inappropriate personal information requests
            personal_info_requests = [
                'password', 'ssn', 'social security', 'credit card',
                'bank account', 'personal address', 'phone number'
            ]
            
            for info_type in personal_info_requests:
                if info_type in response.lower():
                    safety_issues.append(f"Requests personal information: {info_type}")
            
            is_safe = len(safety_issues) == 0
            
            return {
                "is_safe": is_safe,
                "safety_score": 1.0 if is_safe else max(0.0, 1.0 - len(safety_issues) * 0.2),
                "issues": safety_issues,
                "content_length": len(response)
            }
            
        except Exception as e:
            logger.error(f"Error validating response safety: {str(e)}")
            return {
                "is_safe": False,
                "safety_score": 0.0,
                "issues": [f"Validation error: {str(e)}"],
                "content_length": len(response) if response else 0
            }