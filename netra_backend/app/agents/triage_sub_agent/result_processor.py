"""Triage Result Processing Module

Handles result processing, enrichment, and finalization.
Keeps functions under 8 lines and module under 300 lines.
"""

from typing import Any, Dict

from netra_backend.app.agents.triage_sub_agent.models import (
    ExtractedEntities,
    TriageResult,
)
from netra_backend.app.core.serialization.unified_json_handler import (
    comprehensive_json_fix,
    ensure_agent_response_is_json,
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TriageResultProcessor:
    """Handles triage result processing and enrichment."""
    
    def __init__(self, agent):
        """Initialize with reference to main agent."""
        self.agent = agent
        self.logger = logger
    
    def process_result(self, result: Any, user_request: str) -> TriageResult:
        """Process and ensure result is proper TriageResult."""
        triage_result = self._ensure_triage_result(result)
        return self.enrich_triage_result(triage_result, user_request)
    
    def _ensure_triage_result(self, result: Any) -> TriageResult:
        """Ensure result is a proper TriageResult object."""
        if isinstance(result, TriageResult):
            return result
        elif isinstance(result, dict):
            return self._convert_dict_to_triage_result(result)
        else:
            # Fix non-JSON responses before processing
            fixed_result = llm_parser.ensure_agent_response_is_json(result)
            return self._convert_dict_to_triage_result(fixed_result)
    
    def _convert_dict_to_triage_result(self, result_dict: dict) -> TriageResult:
        """Convert dictionary to TriageResult with error handling."""
        try:
            # Check if this is a wrapped text/command/malformed response BEFORE fixing
            if self._is_wrapped_response(result_dict):
                logger.warning(f"Received wrapped response type: {result_dict.get('type', 'unknown')}")
                return self._create_fallback_triage_result()
            
            # Apply comprehensive JSON fixes only for non-wrapped responses
            # But skip string-to-JSON conversion for valid dict structures
            fixed_dict = self._apply_selective_json_fixes(result_dict)
            return TriageResult(**fixed_dict)
        except Exception as e:
            logger.warning(f"Failed to convert dict to TriageResult: {e}")
            return self._create_fallback_triage_result()
    
    def _apply_selective_json_fixes(self, result_dict: dict) -> dict:
        """Apply JSON fixes selectively without wrapping valid strings."""
        # Apply specific fixes for tool parameters and list recommendations
        from netra_backend.app.core.json_parsing_utils import (
            fix_tool_parameters, fix_list_recommendations
        )
        fixed_dict = fix_tool_parameters(result_dict.copy())
        fixed_dict = fix_list_recommendations(fixed_dict)
        return fixed_dict
    
    def _is_wrapped_response(self, result_dict: dict) -> bool:
        """Check if the response is wrapped by ensure_agent_response_is_json."""
        if not isinstance(result_dict, dict):
            return False
        response_type = result_dict.get('type')
        wrapped_types = {'text_response', 'command_result', 'malformed_json', 'unknown_response', 'list_response'}
        return response_type in wrapped_types
    
    def _create_fallback_triage_result(self) -> TriageResult:
        """Create fallback TriageResult with default values."""
        from netra_backend.app.agents.triage_sub_agent.models import TriageMetadata
        return TriageResult(
            category="unknown",
            confidence_score=0.5,
            metadata=TriageMetadata(triage_duration_ms=0, fallback_used=True)
        )
    
    def enrich_triage_result(self, triage_result: Any, user_request: str) -> TriageResult:
        """Enrich triage result with additional analysis."""
        result_dict = self._convert_to_dict(triage_result)
        self._apply_enrichments(result_dict, user_request)
        return self._convert_dict_to_triage_result(result_dict)
    
    def _convert_to_dict(self, triage_result: Any) -> dict:
        """Convert triage result to dictionary for processing."""
        if isinstance(triage_result, TriageResult):
            return triage_result.model_dump()
        else:
            return triage_result if isinstance(triage_result, dict) else {}
    
    def _apply_enrichments(self, result_dict: dict, user_request: str) -> None:
        """Apply all enrichments to result dictionary."""
        self._ensure_entities_extracted(result_dict, user_request)
        self._ensure_intent_detected(result_dict, user_request)
        self._handle_admin_mode_detection(result_dict, user_request)
        self._ensure_tool_recommendations(result_dict)
    
    def _ensure_entities_extracted(self, triage_result: dict, user_request: str) -> None:
        """Ensure entities are extracted from request."""
        if not triage_result.get("extracted_entities"):
            entities = self.agent.triage_core.entity_extractor.extract_entities(user_request)
            triage_result["extracted_entities"] = entities.model_dump()
    
    def _ensure_intent_detected(self, triage_result: dict, user_request: str) -> None:
        """Ensure user intent is detected."""
        if not triage_result.get("user_intent"):
            intent = self.agent.triage_core.intent_detector.detect_intent(user_request)
            triage_result["user_intent"] = intent.model_dump()
    
    def _handle_admin_mode_detection(self, triage_result: dict, user_request: str) -> None:
        """Handle admin mode detection and category adjustment."""
        is_admin = self.agent.triage_core.intent_detector.detect_admin_mode(user_request)
        triage_result["is_admin_mode"] = is_admin
        
        if is_admin:
            self._adjust_admin_category(triage_result, user_request)
    
    def _ensure_tool_recommendations(self, triage_result: dict) -> None:
        """Ensure tool recommendations are present."""
        if not triage_result.get("tool_recommendations"):
            tools = self.agent.triage_core.tool_recommender.recommend_tools(
                triage_result.get("category", "General Inquiry"),
                ExtractedEntities(**triage_result.get("extracted_entities", {}))
            )
            triage_result["tool_recommendations"] = [t.model_dump() for t in tools]
    
    def _adjust_admin_category(self, triage_result: dict, user_request: str) -> None:
        """Adjust category for admin mode requests."""
        current_category = triage_result.get("category")
        admin_categories = ["Synthetic Data Generation", "Corpus Management"]
        
        if current_category not in admin_categories:
            new_category = self._determine_admin_category(user_request)
            if new_category:
                triage_result["category"] = new_category
    
    def _determine_admin_category(self, user_request: str) -> str:
        """Determine appropriate admin category based on request."""
        request_lower = user_request.lower()
        
        if "synthetic" in request_lower or "generate data" in request_lower:
            return "Synthetic Data Generation"
        elif "corpus" in request_lower:
            return "Corpus Management"
        
        return None
    
    def validate_result_completeness(self, result: TriageResult) -> bool:
        """Validate that result has all required fields."""
        required_fields = ['category', 'confidence_score']
        return all(hasattr(result, field) and getattr(result, field) is not None 
                  for field in required_fields)
    
    def format_result_for_response(self, result: TriageResult) -> Dict[str, Any]:
        """Format result for API response."""
        formatted = result.model_dump()
        
        # Ensure proper formatting of key fields
        formatted = self._format_confidence_score(formatted)
        formatted = self._format_category(formatted)
        formatted = self._format_metadata(formatted)
        
        return formatted
    
    def _format_confidence_score(self, result_dict: dict) -> dict:
        """Format confidence score to reasonable precision."""
        if 'confidence_score' in result_dict:
            score = result_dict['confidence_score']
            result_dict['confidence_score'] = round(float(score), 3) if score is not None else 0.0
        return result_dict
    
    def _format_category(self, result_dict: dict) -> dict:
        """Format category string."""
        if 'category' in result_dict:
            category = result_dict['category']
            result_dict['category'] = str(category).strip() if category else "General Inquiry"
        return result_dict
    
    def _format_metadata(self, result_dict: dict) -> dict:
        """Format metadata section."""
        self._ensure_metadata_exists(result_dict)
        metadata = result_dict['metadata']
        if isinstance(metadata, dict):
            self._format_numeric_metadata_fields(metadata)
        return result_dict
    
    def _ensure_metadata_exists(self, result_dict: dict) -> None:
        """Ensure metadata section exists."""
        if 'metadata' not in result_dict:
            result_dict['metadata'] = {}
    
    def _format_numeric_metadata_fields(self, metadata: dict) -> None:
        """Format numeric fields in metadata."""
        for key in ['triage_duration_ms', 'retry_count']:
            if key in metadata and metadata[key] is not None:
                metadata[key] = int(metadata[key])
    
    def create_error_result(self, error_message: str, error_type: str = "processing_error") -> TriageResult:
        """Create standardized error result."""
        from netra_backend.app.agents.triage_sub_agent.models import TriageMetadata
        return TriageResult(
            category="Error",
            confidence_score=0.0,
            error_message=error_message,
            metadata=TriageMetadata(
                triage_duration_ms=0,
                fallback_used=True,
                error_details=error_type
            )
        )
    
    def merge_results(self, primary: TriageResult, fallback: TriageResult) -> TriageResult:
        """Merge primary result with fallback when needed."""
        merged_dict = primary.model_dump()
        fallback_dict = fallback.model_dump()
        self._fill_missing_fields(merged_dict, fallback_dict)
        return TriageResult(**merged_dict)
    
    def _fill_missing_fields(self, merged_dict: dict, fallback_dict: dict) -> None:
        """Fill missing fields from fallback."""
        for key, value in fallback_dict.items():
            if key not in merged_dict or merged_dict[key] is None:
                merged_dict[key] = value
    
    def add_enrichment_metadata(self, result: TriageResult, enrichment_info: Dict[str, Any]) -> TriageResult:
        """Add enrichment metadata to result."""
        result_dict = result.model_dump()
        self._ensure_metadata_exists(result_dict)
        enrichment_data = self._build_enrichment_metadata(enrichment_info)
        result_dict['metadata'].update(enrichment_data)
        return TriageResult(**result_dict)
    
    def _build_enrichment_metadata(self, enrichment_info: Dict[str, Any]) -> dict:
        """Build enrichment metadata dictionary."""
        return {
            'enrichment_applied': True,
            'enrichment_timestamp': enrichment_info.get('timestamp'),
            'enrichment_version': enrichment_info.get('version', '1.0')
        }
    
    def validate_and_sanitize(self, result: Any) -> TriageResult:
        """Validate and sanitize result data."""
        triage_result = self._ensure_triage_result(result)
        
        # Sanitize fields
        sanitized_dict = triage_result.model_dump()
        sanitized_dict = self._sanitize_text_fields(sanitized_dict)
        sanitized_dict = self._sanitize_numeric_fields(sanitized_dict)
        
        return TriageResult(**sanitized_dict)
    
    def _sanitize_text_fields(self, result_dict: dict) -> dict:
        """Sanitize text fields in result."""
        text_fields = ['category', 'error_message']
        
        for field in text_fields:
            if field in result_dict and result_dict[field]:
                # Basic sanitization - remove excessive whitespace
                result_dict[field] = str(result_dict[field]).strip()
        
        return result_dict
    
    def _sanitize_numeric_fields(self, result_dict: dict) -> dict:
        """Sanitize numeric fields in result."""
        # Ensure confidence score is in valid range
        if 'confidence_score' in result_dict:
            score = result_dict['confidence_score']
            if score is not None:
                result_dict['confidence_score'] = max(0.0, min(1.0, float(score)))
        
        return result_dict