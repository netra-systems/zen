"""Error recovery strategies for Triage Sub Agent operations."""

import re
from typing import Any, Dict, List, Optional

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TriageErrorRecovery:
    """Handles error recovery strategies for triage operations."""
    
    def __init__(self):
        self.intent_keywords = self._initialize_intent_keywords()
    
    def _initialize_intent_keywords(self) -> Dict[str, List[str]]:
        """Initialize intent keyword mappings."""
        return {
            'data_analysis': ['analyze', 'analysis', 'data', 'metrics', 'performance'],
            'corpus_management': ['corpus', 'documents', 'upload', 'manage'],
            'optimization': ['optimize', 'improve', 'performance', 'cost'],
            'general_inquiry': ['help', 'what', 'how', 'explain', 'info'],
        }
    
    async def fallback_intent_detection(self, user_input: str) -> Dict[str, Any]:
        """Fallback strategy for intent detection."""
        user_input_lower = user_input.lower()
        best_intent, max_matches = self._find_best_matching_intent(user_input_lower)
        return self._build_intent_fallback_result(best_intent, max_matches)
    
    def _find_best_matching_intent(self, user_input_lower: str) -> tuple:
        """Find best matching intent based on keyword count."""
        best_intent = 'general_inquiry'
        max_matches = 0
        for intent, keywords in self.intent_keywords.items():
            matches = self._count_keyword_matches(keywords, user_input_lower)
            best_intent, max_matches = self._update_best_match(intent, matches, best_intent, max_matches)
        return best_intent, max_matches
    
    def _count_keyword_matches(self, keywords: List[str], user_input_lower: str) -> int:
        """Count keyword matches in user input."""
        return sum(1 for keyword in keywords if keyword in user_input_lower)
    
    def _update_best_match(self, intent: str, matches: int, best_intent: str, max_matches: int) -> tuple:
        """Update best matching intent if current is better."""
        if matches > max_matches:
            return intent, matches
        return best_intent, max_matches
    
    def _build_intent_fallback_result(self, best_intent: str, max_matches: int) -> Dict[str, Any]:
        """Build intent fallback result dictionary."""
        return {
            'intent': best_intent,
            'confidence': min(0.8, max_matches * 0.2),
            'method': 'keyword_fallback',
            'matched_keywords': max_matches
        }
    
    async def fallback_entity_extraction(self, user_input: str, failed_entities: List[str]) -> Dict[str, Any]:
        """Fallback strategy for entity extraction."""
        extracted_entities = {}
        
        # Apply simple regex-based extraction for common entities
        for entity_type in failed_entities:
            value = self._extract_entity_by_type(entity_type, user_input)
            if value:
                extracted_entities[entity_type] = value
        
        return {
            'entities': extracted_entities,
            'method': 'regex_fallback',
            'failed_entities': [e for e in failed_entities if e not in extracted_entities]
        }
    
    def _extract_entity_by_type(self, entity_type: str, user_input: str) -> Optional[str]:
        """Extract entity using simple regex patterns."""
        patterns = self._get_entity_patterns()
        pattern = patterns.get(entity_type)
        
        if not pattern:
            return None
        
        match = re.search(pattern, user_input, re.IGNORECASE)
        return match.group(1) if match else None
    
    def _get_entity_patterns(self) -> Dict[str, str]:
        """Get regex patterns for common entity types."""
        return {
            'time_range': r'(last\s+\d+\s+\w+|yesterday|today|this\s+week)',
            'metric_name': r'(latency|throughput|cpu|memory|disk|network)',
            'user_id': r'user[_\s]*(\d+)',
            'workload_id': r'workload[_\s]*(\d+)',
            'dataset': r'dataset[_\s]*(\w+)',
        }
    
    async def fallback_tool_recommendation(self, intent: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback strategy for tool recommendation."""
        default_tools = self._get_default_tools_for_intent(intent)
        
        return {
            'tools': default_tools,
            'confidence': 0.6,
            'method': 'intent_mapping_fallback',
            'recommended_count': len(default_tools)
        }
    
    def _get_default_tools_for_intent(self, intent: str) -> List[str]:
        """Get default tools based on intent."""
        tool_mapping = {
            'data_analysis': ['data_analyzer', 'metrics_collector', 'performance_monitor'],
            'corpus_management': ['corpus_uploader', 'document_processor', 'corpus_analyzer'],
            'optimization': ['optimizer', 'cost_analyzer', 'performance_tuner'],
            'general_inquiry': ['help_system', 'documentation_search', 'status_checker']
        }
        return tool_mapping.get(intent, ['help_system', 'status_checker'])
    
    def create_recovery_metadata(self, run_id: str, operation: str, **kwargs) -> Dict[str, Any]:
        """Create metadata for recovery operations."""
        return {
            'run_id': run_id,
            'operation': operation,
            'recovery_timestamp': self._get_current_timestamp(),
            'additional_context': kwargs
        }
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp for recovery metadata."""
        from datetime import datetime, UTC
        return datetime.now(UTC).isoformat()
    
    def should_attempt_recovery(self, error: Exception, operation: str) -> bool:
        """Determine if recovery should be attempted for the error."""
        # Define non-recoverable error patterns
        non_recoverable = [
            'authentication',
            'authorization',
            'permission_denied',
            'system_shutdown'
        ]
        
        error_message = str(error).lower()
        return not any(pattern in error_message for pattern in non_recoverable)
    
    def get_recovery_strategy(self, operation: str) -> str:
        """Get the appropriate recovery strategy for an operation."""
        strategy_mapping = {
            'intent_detection': 'keyword_fallback',
            'entity_extraction': 'regex_fallback',
            'tool_recommendation': 'intent_mapping_fallback',
            'cache_operation': 'cache_invalidation',
            'state_operation': 'state_rollback'
        }
        return strategy_mapping.get(operation, 'generic_retry')