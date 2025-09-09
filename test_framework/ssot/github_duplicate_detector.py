"""
GitHub Duplicate Detector - Single Source of Truth for Intelligent Duplicate Issue Detection

This module provides advanced duplicate detection for GitHub issues using semantic
similarity, error fingerprinting, and intelligent pattern matching to prevent
issue spam and consolidate related error reports.

CRITICAL: This is the SINGLE SOURCE OF TRUTH for GitHub duplicate detection.
All duplicate detection logic across the entire codebase MUST use this detector.

Business Value: Platform/Internal - System Stability & Development Velocity
Prevents GitHub issue spam, consolidates related errors, and improves issue
tracking efficiency by intelligently identifying duplicate error patterns.

REQUIREMENTS per CLAUDE.md:
- Semantic similarity detection using multiple algorithms
- Error pattern fingerprinting and normalization  
- Configurable similarity thresholds
- Integration with SSOT GitHub components
- Performance optimization for large issue datasets
"""

import difflib
import hashlib
import logging
import re
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set, Union
from dataclasses import dataclass, asdict
from enum import Enum

from test_framework.ssot.github_client import GitHubClient, GitHubIssue
from test_framework.ssot.github_issue_manager import ErrorContext, ErrorCategory


logger = logging.getLogger(__name__)


class SimilarityAlgorithm(Enum):
    """Similarity detection algorithms."""
    EXACT_MATCH = "exact_match"
    FINGERPRINT = "fingerprint"  
    SEQUENCE_MATCHER = "sequence_matcher"
    TOKEN_SIMILARITY = "token_similarity"
    SEMANTIC_PATTERNS = "semantic_patterns"
    STACK_TRACE_SIMILARITY = "stack_trace_similarity"


@dataclass
class SimilarityScore:
    """Similarity score breakdown for transparency."""
    overall_score: float  # 0.0 to 1.0
    algorithm_scores: Dict[str, float]  # Individual algorithm scores
    confidence: float  # Confidence in the similarity assessment
    similarity_reasons: List[str]  # Human-readable reasons for similarity
    
    def is_duplicate(self, threshold: float = 0.8) -> bool:
        """Check if similarity score indicates a duplicate."""
        return self.overall_score >= threshold
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class DuplicateDetectionResult:
    """Result of duplicate detection analysis."""
    is_duplicate: bool
    similar_issues: List[GitHubIssue]
    similarity_scores: List[SimilarityScore]
    recommended_action: str  # "create_new", "add_comment", "merge_with"
    confidence_level: str  # "high", "medium", "low"
    
    def get_best_match(self) -> Optional[Tuple[GitHubIssue, SimilarityScore]]:
        """Get the best matching issue and its score."""
        if not self.similar_issues or not self.similarity_scores:
            return None
        
        # Find the highest scoring match
        best_index = 0
        best_score = 0.0
        
        for i, score in enumerate(self.similarity_scores):
            if score.overall_score > best_score:
                best_score = score.overall_score
                best_index = i
        
        return self.similar_issues[best_index], self.similarity_scores[best_index]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_duplicate": self.is_duplicate,
            "similar_issues_count": len(self.similar_issues),
            "similarity_scores": [score.to_dict() for score in self.similarity_scores],
            "recommended_action": self.recommended_action,
            "confidence_level": self.confidence_level,
            "best_match": {
                "issue_number": self.get_best_match()[0].number if self.get_best_match() else None,
                "score": self.get_best_match()[1].overall_score if self.get_best_match() else 0.0
            } if self.get_best_match() else None
        }


class ErrorPatternNormalizer:
    """Normalizes error patterns for consistent comparison."""
    
    # Common patterns to normalize
    NORMALIZATION_PATTERNS = [
        # Timestamps
        (r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?', '[TIMESTAMP]'),
        # UUIDs
        (r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', '[UUID]'),
        # Hash values
        (r'\b[0-9a-f]{32,64}\b', '[HASH]'),
        # IP addresses
        (r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP]'),
        # URLs
        (r'https?://[^\s/$.?#].[^\s]*', '[URL]'),
        # File paths (Unix/Windows)
        (r'(?:/[^/\s]+)+/?|(?:[A-Z]:\\[^\\]+\\?)+', '[PATH]'),
        # Numbers (but preserve structure)
        (r'\b\d+\b', '[NUM]'),
        # Memory addresses
        (r'\b0x[0-9a-f]+\b', '[ADDR]'),
        # Email addresses
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]'),
        # Database connection strings
        (r'(postgresql|mysql|mongodb)://[^\s]+', '[DB_URL]'),
        # API keys (partial masking)
        (r'\b[A-Za-z0-9]{20,}\b', '[API_KEY]'),
    ]
    
    def normalize_error_message(self, message: str) -> str:
        """
        Normalize error message for pattern matching.
        
        Args:
            message: Original error message
            
        Returns:
            Normalized error message
        """
        normalized = message.lower().strip()
        
        # Apply normalization patterns
        for pattern, replacement in self.NORMALIZATION_PATTERNS:
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        return normalized
    
    def normalize_stack_trace(self, stack_trace: str) -> str:
        """
        Normalize stack trace for pattern matching.
        
        Args:
            stack_trace: Original stack trace
            
        Returns:
            Normalized stack trace focusing on structure
        """
        lines = stack_trace.split('\n')
        normalized_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Normalize file paths and line numbers
            normalized_line = re.sub(r'File "([^"]+)"', 'File "[PATH]"', line)
            normalized_line = re.sub(r', line \d+', ', line [LINE]', normalized_line)
            normalized_line = re.sub(r'at \S+:\d+', 'at [LOCATION]', normalized_line)
            
            # Normalize memory addresses and object references
            normalized_line = re.sub(r'0x[0-9a-f]+', '[ADDR]', normalized_line)
            normalized_line = re.sub(r'object at 0x[0-9a-f]+', 'object at [ADDR]', normalized_line)
            
            normalized_lines.append(normalized_line.lower())
        
        return '\n'.join(normalized_lines)
    
    def extract_error_signature(self, error_context: ErrorContext) -> str:
        """
        Extract a signature that captures the essence of the error.
        
        Args:
            error_context: Error context to analyze
            
        Returns:
            Error signature string
        """
        signature_parts = []
        
        # Error type (unchanged)
        signature_parts.append(f"type:{error_context.error_type}")
        
        # Normalized error message
        normalized_message = self.normalize_error_message(error_context.error_message)
        signature_parts.append(f"message:{normalized_message}")
        
        # Service context
        if error_context.service:
            signature_parts.append(f"service:{error_context.service}")
        
        # Extract key stack trace patterns
        if error_context.stack_trace:
            stack_signature = self._extract_stack_signature(error_context.stack_trace)
            if stack_signature:
                signature_parts.append(f"stack:{stack_signature}")
        
        return "|".join(signature_parts)
    
    def _extract_stack_signature(self, stack_trace: str) -> str:
        """Extract key patterns from stack trace."""
        lines = stack_trace.split('\n')
        function_calls = []
        
        for line in lines:
            # Look for function calls and method invocations
            if 'in ' in line and '(' in line:
                # Extract function name
                match = re.search(r'in (\w+)', line)
                if match:
                    function_calls.append(match.group(1))
        
        # Return the call chain signature (last 3 functions)
        return '->'.join(function_calls[-3:]) if function_calls else ''


class SemanticSimilarityDetector:
    """Detects semantic similarity between errors using multiple algorithms."""
    
    def __init__(self):
        self.normalizer = ErrorPatternNormalizer()
    
    def calculate_similarity(
        self,
        error_context: ErrorContext,
        existing_issue: GitHubIssue
    ) -> SimilarityScore:
        """
        Calculate similarity between error and existing issue.
        
        Args:
            error_context: New error context
            existing_issue: Existing GitHub issue
            
        Returns:
            SimilarityScore with detailed breakdown
        """
        algorithm_scores = {}
        similarity_reasons = []
        
        # Algorithm 1: Exact fingerprint match
        fingerprint_score = self._calculate_fingerprint_similarity(error_context, existing_issue)
        algorithm_scores[SimilarityAlgorithm.FINGERPRINT.value] = fingerprint_score
        
        if fingerprint_score > 0.9:
            similarity_reasons.append("Exact error fingerprint match")
        
        # Algorithm 2: Error message similarity
        message_score = self._calculate_message_similarity(error_context, existing_issue)
        algorithm_scores[SimilarityAlgorithm.SEQUENCE_MATCHER.value] = message_score
        
        if message_score > 0.8:
            similarity_reasons.append("High error message similarity")
        
        # Algorithm 3: Token-based similarity
        token_score = self._calculate_token_similarity(error_context, existing_issue)
        algorithm_scores[SimilarityAlgorithm.TOKEN_SIMILARITY.value] = token_score
        
        if token_score > 0.7:
            similarity_reasons.append("Similar error tokens and keywords")
        
        # Algorithm 4: Stack trace similarity
        stack_score = self._calculate_stack_trace_similarity(error_context, existing_issue)
        algorithm_scores[SimilarityAlgorithm.STACK_TRACE_SIMILARITY.value] = stack_score
        
        if stack_score > 0.6:
            similarity_reasons.append("Similar stack trace patterns")
        
        # Algorithm 5: Semantic pattern matching
        pattern_score = self._calculate_pattern_similarity(error_context, existing_issue)
        algorithm_scores[SimilarityAlgorithm.SEMANTIC_PATTERNS.value] = pattern_score
        
        if pattern_score > 0.7:
            similarity_reasons.append("Matching error patterns and context")
        
        # Calculate weighted overall score
        weights = {
            SimilarityAlgorithm.FINGERPRINT.value: 0.3,
            SimilarityAlgorithm.SEQUENCE_MATCHER.value: 0.25,
            SimilarityAlgorithm.TOKEN_SIMILARITY.value: 0.2,
            SimilarityAlgorithm.STACK_TRACE_SIMILARITY.value: 0.15,
            SimilarityAlgorithm.SEMANTIC_PATTERNS.value: 0.1
        }
        
        overall_score = sum(
            algorithm_scores[alg] * weight 
            for alg, weight in weights.items()
        )
        
        # Calculate confidence based on score consistency
        score_values = list(algorithm_scores.values())
        score_variance = sum((score - overall_score) ** 2 for score in score_values) / len(score_values)
        confidence = max(0.0, 1.0 - score_variance)
        
        return SimilarityScore(
            overall_score=overall_score,
            algorithm_scores=algorithm_scores,
            confidence=confidence,
            similarity_reasons=similarity_reasons
        )
    
    def _calculate_fingerprint_similarity(
        self,
        error_context: ErrorContext,
        existing_issue: GitHubIssue
    ) -> float:
        """Calculate similarity based on error fingerprints."""
        current_fingerprint = error_context.generate_fingerprint()
        
        # Look for fingerprint in existing issue body
        if current_fingerprint in existing_issue.body:
            return 1.0
        
        # Extract fingerprints from issue body using regex
        fingerprint_pattern = r'Fingerprint.*?`([a-f0-9]{16})`'
        matches = re.findall(fingerprint_pattern, existing_issue.body, re.IGNORECASE)
        
        if matches:
            existing_fingerprint = matches[0]
            if current_fingerprint == existing_fingerprint:
                return 1.0
            
            # Calculate character-level similarity for near-matches
            return difflib.SequenceMatcher(None, current_fingerprint, existing_fingerprint).ratio()
        
        return 0.0
    
    def _calculate_message_similarity(
        self,
        error_context: ErrorContext,
        existing_issue: GitHubIssue
    ) -> float:
        """Calculate similarity based on error messages."""
        # Normalize both messages
        current_normalized = self.normalizer.normalize_error_message(error_context.error_message)
        
        # Extract error message from issue title or body
        title_normalized = self.normalizer.normalize_error_message(existing_issue.title)
        
        # Check title similarity first (higher weight)
        title_similarity = difflib.SequenceMatcher(None, current_normalized, title_normalized).ratio()
        
        # Also check body content
        body_normalized = self.normalizer.normalize_error_message(existing_issue.body)
        body_similarity = difflib.SequenceMatcher(None, current_normalized, body_normalized).ratio()
        
        # Return weighted average (title is more important)
        return (title_similarity * 0.7) + (body_similarity * 0.3)
    
    def _calculate_token_similarity(
        self,
        error_context: ErrorContext,
        existing_issue: GitHubIssue
    ) -> float:
        """Calculate similarity based on token overlap."""
        # Extract meaningful tokens from current error
        current_tokens = self._extract_meaningful_tokens(
            f"{error_context.error_type} {error_context.error_message}"
        )
        
        # Extract tokens from existing issue
        existing_tokens = self._extract_meaningful_tokens(
            f"{existing_issue.title} {existing_issue.body}"
        )
        
        if not current_tokens or not existing_tokens:
            return 0.0
        
        # Calculate Jaccard similarity
        intersection = current_tokens.intersection(existing_tokens)
        union = current_tokens.union(existing_tokens)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _calculate_stack_trace_similarity(
        self,
        error_context: ErrorContext,
        existing_issue: GitHubIssue
    ) -> float:
        """Calculate similarity based on stack traces."""
        if not error_context.stack_trace:
            return 0.0
        
        # Normalize current stack trace
        current_normalized = self.normalizer.normalize_stack_trace(error_context.stack_trace)
        
        # Extract stack trace from existing issue body
        stack_pattern = r'```\n(.*?)\n```'
        stack_matches = re.findall(stack_pattern, existing_issue.body, re.DOTALL)
        
        if not stack_matches:
            return 0.0
        
        # Compare with first stack trace found
        existing_stack = stack_matches[0]
        existing_normalized = self.normalizer.normalize_stack_trace(existing_stack)
        
        # Calculate line-by-line similarity
        current_lines = current_normalized.split('\n')
        existing_lines = existing_normalized.split('\n')
        
        # Use sequence matcher on normalized stack traces
        similarity = difflib.SequenceMatcher(None, current_lines, existing_lines).ratio()
        
        return similarity
    
    def _calculate_pattern_similarity(
        self,
        error_context: ErrorContext,
        existing_issue: GitHubIssue
    ) -> float:
        """Calculate similarity based on semantic patterns."""
        score = 0.0
        total_checks = 0
        
        # Check error type similarity
        if error_context.error_type.lower() in existing_issue.title.lower():
            score += 0.3
        total_checks += 1
        
        # Check service similarity
        if error_context.service and error_context.service in existing_issue.body:
            score += 0.2
        total_checks += 1
        
        # Check environment similarity
        if error_context.environment and error_context.environment in existing_issue.body:
            score += 0.1
        total_checks += 1
        
        # Check label similarity
        current_error_signature = self.normalizer.extract_error_signature(error_context)
        
        # Look for similar patterns in existing issue labels
        label_similarity = 0.0
        for label in existing_issue.labels:
            if any(part in label for part in current_error_signature.split('|')):
                label_similarity += 0.1
        
        score += min(label_similarity, 0.4)  # Cap at 0.4
        total_checks += 1
        
        return score / total_checks if total_checks > 0 else 0.0
    
    def _extract_meaningful_tokens(self, text: str) -> Set[str]:
        """Extract meaningful tokens from text."""
        # Normalize text
        normalized = self.normalizer.normalize_error_message(text)
        
        # Split into tokens
        tokens = re.findall(r'\b\w+\b', normalized)
        
        # Filter out common words and very short tokens
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'this', 'that', 'these', 'those', 'not', 'no', 'yes'
        }
        
        meaningful_tokens = {
            token for token in tokens 
            if len(token) > 2 and token not in stop_words
        }
        
        return meaningful_tokens


class GitHubDuplicateDetector:
    """
    Single Source of Truth GitHub Duplicate Detector
    
    This is the CANONICAL duplicate detection system that intelligently identifies
    duplicate GitHub issues using multiple similarity algorithms and semantic analysis.
    """
    
    def __init__(
        self,
        github_client: GitHubClient,
        similarity_threshold: float = 0.8,
        max_search_results: int = 50
    ):
        """
        Initialize GitHub duplicate detector.
        
        Args:
            github_client: GitHub client instance
            similarity_threshold: Minimum similarity score for duplicate detection
            max_search_results: Maximum number of issues to search for comparison
        """
        self._github_client = github_client
        self._similarity_threshold = similarity_threshold
        self._max_search_results = max_search_results
        self._similarity_detector = SemanticSimilarityDetector()
        
        logger.info(f"Initialized GitHub duplicate detector with threshold {similarity_threshold}")
    
    async def detect_duplicates(
        self,
        error_context: ErrorContext,
        repo_owner: str,
        repo_name: str,
        search_timeframe_days: int = 30
    ) -> DuplicateDetectionResult:
        """
        Detect duplicate issues for the given error context.
        
        Args:
            error_context: Error context to check for duplicates
            repo_owner: Repository owner
            repo_name: Repository name
            search_timeframe_days: How many days back to search
            
        Returns:
            DuplicateDetectionResult with analysis and recommendations
        """
        # Step 1: Search for potentially similar issues
        candidate_issues = await self._find_candidate_issues(
            error_context, repo_owner, repo_name, search_timeframe_days
        )
        
        if not candidate_issues:
            return DuplicateDetectionResult(
                is_duplicate=False,
                similar_issues=[],
                similarity_scores=[],
                recommended_action="create_new",
                confidence_level="high"
            )
        
        # Step 2: Calculate similarity scores for each candidate
        similar_issues = []
        similarity_scores = []
        
        for issue in candidate_issues:
            score = self._similarity_detector.calculate_similarity(error_context, issue)
            
            if score.overall_score >= 0.3:  # Only keep reasonably similar issues
                similar_issues.append(issue)
                similarity_scores.append(score)
        
        # Step 3: Sort by similarity score
        if similar_issues:
            sorted_pairs = sorted(
                zip(similar_issues, similarity_scores),
                key=lambda x: x[1].overall_score,
                reverse=True
            )
            similar_issues, similarity_scores = zip(*sorted_pairs)
            similar_issues = list(similar_issues)
            similarity_scores = list(similarity_scores)
        
        # Step 4: Determine if it's a duplicate and recommend action
        is_duplicate = False
        recommended_action = "create_new"
        confidence_level = "low"
        
        if similarity_scores:
            best_score = similarity_scores[0]
            
            if best_score.overall_score >= self._similarity_threshold:
                is_duplicate = True
                
                if best_score.overall_score >= 0.95:
                    recommended_action = "add_comment"
                    confidence_level = "high"
                elif best_score.overall_score >= 0.85:
                    recommended_action = "add_comment"
                    confidence_level = "medium"
                else:
                    recommended_action = "merge_with"
                    confidence_level = "medium"
            
            elif best_score.overall_score >= 0.6:
                # High similarity but below threshold - recommend review
                recommended_action = "review_similarity"
                confidence_level = "low"
        
        result = DuplicateDetectionResult(
            is_duplicate=is_duplicate,
            similar_issues=similar_issues[:5],  # Limit to top 5 matches
            similarity_scores=similarity_scores[:5],
            recommended_action=recommended_action,
            confidence_level=confidence_level
        )
        
        logger.info(
            f"Duplicate detection complete: is_duplicate={is_duplicate}, "
            f"similar_count={len(similar_issues)}, "
            f"best_score={similarity_scores[0].overall_score if similarity_scores else 0.0:.3f}"
        )
        
        return result
    
    async def _find_candidate_issues(
        self,
        error_context: ErrorContext,
        repo_owner: str,
        repo_name: str,
        search_timeframe_days: int
    ) -> List[GitHubIssue]:
        """Find candidate issues that might be duplicates."""
        candidate_issues = []
        
        # Strategy 1: Search by error type
        try:
            type_query = f'"{error_context.error_type}" is:issue'
            type_issues = await self._github_client.search_issues(
                query=type_query,
                repo_owner=repo_owner,
                repo_name=repo_name,
                state="open",
                per_page=min(self._max_search_results // 2, 25)
            )
            candidate_issues.extend(type_issues)
        except Exception as e:
            logger.warning(f"Error searching by error type: {e}")
        
        # Strategy 2: Search by key error message terms
        try:
            # Extract key terms from error message
            key_terms = self._extract_search_terms(error_context.error_message)
            if key_terms:
                terms_query = f'{" ".join(key_terms[:3])} is:issue'  # Use top 3 terms
                terms_issues = await self._github_client.search_issues(
                    query=terms_query,
                    repo_owner=repo_owner,
                    repo_name=repo_name,
                    state="open",
                    per_page=min(self._max_search_results // 2, 25)
                )
                candidate_issues.extend(terms_issues)
        except Exception as e:
            logger.warning(f"Error searching by error terms: {e}")
        
        # Strategy 3: Search by service/component if available
        if error_context.service:
            try:
                service_query = f'"{error_context.service}" is:issue'
                service_issues = await self._github_client.search_issues(
                    query=service_query,
                    repo_owner=repo_owner,
                    repo_name=repo_name,
                    state="open",
                    per_page=10
                )
                candidate_issues.extend(service_issues)
            except Exception as e:
                logger.warning(f"Error searching by service: {e}")
        
        # Remove duplicates based on issue number
        seen_numbers = set()
        unique_candidates = []
        
        for issue in candidate_issues:
            if issue.number not in seen_numbers:
                seen_numbers.add(issue.number)
                unique_candidates.append(issue)
        
        # Filter by timeframe
        if search_timeframe_days > 0:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=search_timeframe_days)
            
            filtered_candidates = []
            for issue in unique_candidates:
                try:
                    issue_date = datetime.fromisoformat(issue.created_at.replace('Z', '+00:00'))
                    if issue_date >= cutoff_date:
                        filtered_candidates.append(issue)
                except ValueError:
                    # Include issue if date parsing fails
                    filtered_candidates.append(issue)
            
            unique_candidates = filtered_candidates
        
        logger.debug(f"Found {len(unique_candidates)} candidate issues for duplicate detection")
        return unique_candidates[:self._max_search_results]
    
    def _extract_search_terms(self, error_message: str) -> List[str]:
        """Extract meaningful search terms from error message."""
        # Normalize and tokenize
        normalized = self._similarity_detector.normalizer.normalize_error_message(error_message)
        tokens = re.findall(r'\b\w+\b', normalized)
        
        # Score tokens by importance
        token_scores = defaultdict(int)
        
        # Higher score for longer tokens
        for token in tokens:
            if len(token) > 3:
                token_scores[token] += len(token)
        
        # Higher score for technical terms
        technical_indicators = [
            'error', 'exception', 'failed', 'timeout', 'connection', 'database',
            'authentication', 'authorization', 'validation', 'import', 'module',
            'service', 'api', 'http', 'sql', 'json', 'xml'
        ]
        
        for token in tokens:
            if token in technical_indicators:
                token_scores[token] += 10
        
        # Sort by score and return top terms
        sorted_tokens = sorted(token_scores.items(), key=lambda x: x[1], reverse=True)
        return [token for token, score in sorted_tokens[:5]]
    
    def get_similarity_threshold(self) -> float:
        """Get current similarity threshold."""
        return self._similarity_threshold
    
    def set_similarity_threshold(self, threshold: float) -> None:
        """Set similarity threshold (0.0 to 1.0)."""
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("Similarity threshold must be between 0.0 and 1.0")
        
        self._similarity_threshold = threshold
        logger.info(f"Updated similarity threshold to {threshold}")


# === SSOT FACTORY FUNCTIONS ===

def create_github_duplicate_detector(
    github_client: GitHubClient,
    similarity_threshold: float = 0.8,
    max_search_results: int = 50
) -> GitHubDuplicateDetector:
    """
    Create GitHub duplicate detector using SSOT patterns.
    
    This is the CANONICAL way to create GitHub duplicate detectors.
    
    Args:
        github_client: GitHub client instance
        similarity_threshold: Minimum similarity score for duplicate detection
        max_search_results: Maximum number of issues to search
        
    Returns:
        Configured GitHubDuplicateDetector
    """
    return GitHubDuplicateDetector(
        github_client=github_client,
        similarity_threshold=similarity_threshold,
        max_search_results=max_search_results
    )