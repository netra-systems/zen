"""
Corpus Request Parser

Parses natural language requests into structured corpus operations.
Maintains 8-line function limit and single responsibility.
"""

from typing import Dict, Any
from app.llm.llm_manager import LLMManager
from app.agents.utils import extract_json_from_response
from app.logging_config import central_logger
from app.llm.observability import (
    start_llm_heartbeat, stop_llm_heartbeat, generate_llm_correlation_id,
    log_agent_input, log_agent_output
)
from .models import CorpusOperation, CorpusType, CorpusMetadata, CorpusOperationRequest

logger = central_logger.get_logger(__name__)


class CorpusRequestParser:
    """Parses corpus operation requests from natural language"""
    
    def __init__(self, llm_manager: LLMManager):
        self.llm_manager = llm_manager
    
    async def parse_operation_request(self, user_request: str) -> CorpusOperationRequest:
        """Parse corpus operation from user request"""
        correlation_id = generate_llm_correlation_id()
        
        # Start heartbeat for LLM operation
        start_llm_heartbeat(correlation_id, "CorpusAdminSubAgent-Parser")
        
        try:
            prompt = self._build_parsing_prompt(user_request)
            
            # Log input to LLM
            log_agent_input("CorpusAdminSubAgent", "LLM", len(prompt), correlation_id)
            
            response = await self.llm_manager.ask_llm(prompt, llm_config_name='default')
            
            # Log output from LLM
            log_agent_output("LLM", "CorpusAdminSubAgent", 
                           len(response), "success", correlation_id)
            
            params = extract_json_from_response(response)
            
            if params:
                return self._create_operation_request(params)
            return self._create_default_request()
        finally:
            # Stop heartbeat
            stop_llm_heartbeat(correlation_id)
    
    def _build_parsing_prompt(self, user_request: str) -> str:
        """Build LLM prompt for parsing corpus requests"""
        return f"""
Analyze the following user request for corpus management and extract operation details:

User Request: {user_request}

Return a JSON object with these fields:
{{
    "operation": "create|update|delete|search|analyze|export|import|validate",
    "corpus_metadata": {{
        "corpus_name": "<name of corpus>",
        "corpus_type": "documentation|knowledge_base|training_data|reference_data|embeddings",
        "description": "<optional description>",
        "tags": ["<optional tags>"],
        "access_level": "private|team|public"
    }},
    "filters": {{
        "date_range": {{"start": "ISO date", "end": "ISO date"}},
        "document_types": ["<types>"],
        "size_range": {{"min": bytes, "max": bytes}}
    }},
    "options": {{
        "include_embeddings": true/false,
        "format": "json|csv|parquet",
        "compression": true/false
    }}
}}

Examples:
- "Create a new corpus for product documentation" -> operation: "create"
- "Search the knowledge base for optimization strategies" -> operation: "search"
- "Delete old training data from last year" -> operation: "delete"
- "Export the reference corpus as JSON" -> operation: "export"
"""
    
    def _create_operation_request(self, params: Dict[str, Any]) -> CorpusOperationRequest:
        """Create operation request from parsed parameters"""
        corpus_metadata = CorpusMetadata(**params.get("corpus_metadata", {}))
        
        return CorpusOperationRequest(
            operation=CorpusOperation(params.get("operation", "search")),
            corpus_metadata=corpus_metadata,
            filters=params.get("filters", {}),
            options=params.get("options", {})
        )
    
    def _create_default_request(self) -> CorpusOperationRequest:
        """Create default search request when parsing fails"""
        return CorpusOperationRequest(
            operation=CorpusOperation.SEARCH,
            corpus_metadata=CorpusMetadata(
                corpus_name="default",
                corpus_type=CorpusType.KNOWLEDGE_BASE
            )
        )