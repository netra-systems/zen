"""Corpus request processing module for CorpusAdminSubAgent."""

from typing import List
from app.agents.state import DeepAgentState
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class CorpusRequestProcessor:
    """Handles corpus request processing and validation."""
    
    def __init__(self):
        self.corpus_keywords = self._initialize_corpus_keywords()
    
    def _initialize_corpus_keywords(self) -> List[str]:
        """Initialize corpus-related keywords."""
        return ["corpus", "knowledge base", "documentation", "reference data", "embeddings"]
    
    async def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:
        """Check if conditions are met for corpus administration."""
        if self._is_admin_mode_request(state) or self._has_corpus_keywords(state):
            return True
        
        logger.info(f"Corpus administration not required for run_id: {run_id}")
        return False
    
    def _is_admin_mode_request(self, state: DeepAgentState) -> bool:
        """Check if request is admin mode or corpus-related."""
        triage_result = state.triage_result or {}
        
        if isinstance(triage_result, dict):
            return self._check_admin_indicators(triage_result)
        return False
    
    def _check_admin_indicators(self, triage_result: dict) -> bool:
        """Check if triage result indicates admin or corpus operation."""
        category = triage_result.get("category", "")
        is_admin = triage_result.get("is_admin_mode", False)
        return self._has_corpus_category(category) or self._has_admin_category(category) or is_admin
    
    def _has_corpus_category(self, category: str) -> bool:
        """Check if category contains corpus keywords."""
        return "corpus" in category.lower()
    
    def _has_admin_category(self, category: str) -> bool:
        """Check if category contains admin keywords."""
        return "admin" in category.lower()
    
    def _has_corpus_keywords(self, state: DeepAgentState) -> bool:
        """Check if user request contains corpus keywords."""
        if not state.user_request:
            return False
        return self._request_contains_keywords(state.user_request)
    
    def _request_contains_keywords(self, user_request: str) -> bool:
        """Check if request contains any corpus keywords."""
        request_lower = user_request.lower()
        return any(keyword in request_lower for keyword in self.corpus_keywords)