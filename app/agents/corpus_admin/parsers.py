"""
Corpus Request Parser

Parses natural language requests into structured corpus operations.
Maintains 25-line function limit and single responsibility.
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
        start_llm_heartbeat(correlation_id, "CorpusAdminSubAgent-Parser")
        
        try:
            return await self._execute_llm_parsing(user_request, correlation_id)
        finally:
            stop_llm_heartbeat(correlation_id)
    
    async def _execute_llm_parsing(self, user_request: str, correlation_id: str) -> CorpusOperationRequest:
        """Execute LLM parsing operation"""
        prompt = self._build_parsing_prompt(user_request)
        log_agent_input("CorpusAdminSubAgent", "LLM", len(prompt), correlation_id)
        
        response = await self.llm_manager.ask_llm(prompt, llm_config_name='default')
        log_agent_output("LLM", "CorpusAdminSubAgent", len(response), "success", correlation_id)
        
        return self._process_llm_response(response)
    
    def _process_llm_response(self, response: str) -> CorpusOperationRequest:
        """Process LLM response and create operation request"""
        params = extract_json_from_response(response)
        
        if params:
            return self._create_operation_request(params)
        return self._create_default_request()
    
    def _build_parsing_prompt(self, user_request: str) -> str:
        """Build LLM prompt for parsing corpus requests"""
        base_prompt = self._get_base_prompt_template()
        schema_section = self._get_schema_section()
        examples_section = self._get_examples_section()
        
        return f"{base_prompt}{user_request}{schema_section}{examples_section}"
    
    def _get_base_prompt_template(self) -> str:
        """Get base prompt template"""
        return "\nAnalyze the following user request for corpus management and extract operation details:\n\nUser Request: "
    
    def _get_schema_section(self) -> str:
        """Get JSON schema section of prompt"""
        schema_header = self._get_schema_header()
        operation_fields = self._get_operation_fields()
        metadata_fields = self._get_metadata_fields()
        filter_fields = self._get_filter_fields()
        option_fields = self._get_option_fields()
        return f"{schema_header}{operation_fields}{metadata_fields}{filter_fields}{option_fields}}}"
    
    def _get_schema_header(self) -> str:
        """Get schema header section."""
        return "\n\nReturn a JSON object with these fields:\n{"
    
    def _get_operation_fields(self) -> str:
        """Get operation field definition."""
        return '\n    "operation": "create|update|delete|search|analyze|export|import|validate",'
    
    def _get_metadata_fields(self) -> str:
        """Get corpus metadata field definitions."""
        return '''\n    "corpus_metadata": {
        "corpus_name": "<name of corpus>",
        "corpus_type": "documentation|knowledge_base|training_data|reference_data|embeddings",
        "description": "<optional description>",
        "tags": ["<optional tags>"],
        "access_level": "private|team|public"
    },'''
    
    def _get_filter_fields(self) -> str:
        """Get filter field definitions."""
        return '''\n    "filters": {
        "date_range": {"start": "ISO date", "end": "ISO date"},
        "document_types": ["<types>"],
        "size_range": {"min": bytes, "max": bytes}
    },'''
    
    def _get_option_fields(self) -> str:
        """Get option field definitions."""
        return '''\n    "options": {
        "include_embeddings": true/false,
        "format": "json|csv|parquet",
        "compression": true/false
    }
}'''
    
    def _get_examples_section(self) -> str:
        """Get examples section of prompt"""
        return '''\n\nExamples:
- "Create a new corpus for product documentation" -> operation: "create"
- "Search the knowledge base for optimization strategies" -> operation: "search"
- "Delete old training data from last year" -> operation: "delete"
- "Export the reference corpus as JSON" -> operation: "export"
'''
    
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