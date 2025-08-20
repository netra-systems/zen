"""
Corpus Admin Tools

Corpus-specific admin tools for generation, optimization, and export.
All functions maintain 25-line limit with single responsibility.
"""

from typing import Dict, Any, List, Optional, Callable
from app.logging_config import central_logger
from app.services.corpus_service import CorpusService
from app.services.synthetic_data_service import SyntheticDataService

# Import modular components
from .corpus_models import CorpusToolType, CorpusToolRequest, CorpusToolResponse
from .corpus_validators import CorpusValidators
from .corpus_tool_handlers import CorpusToolHandlers

# Backward compatibility exports
__all__ = ["CorpusToolType", "CorpusToolRequest", "CorpusToolResponse", "CorpusAdminTools"]

logger = central_logger.get_logger(__name__)


class CorpusAdminTools:
    """Corpus-specific admin tools orchestrator"""
    
    def __init__(self, corpus_service: CorpusService, synthetic_manager: SyntheticDataService):
        """Initialize corpus admin tools with services"""
        self.corpus_service = corpus_service
        self.synthetic_manager = synthetic_manager
        self.handlers = CorpusToolHandlers(corpus_service, synthetic_manager)
        self.validators = CorpusValidators.get_validator_registry()
        self.tool_registry = self._initialize_tool_registry()
    
    def _initialize_tool_registry(self) -> Dict[CorpusToolType, Callable]:
        """Initialize registry of corpus tools"""
        return self._build_tool_mapping()
    
    def _build_tool_mapping(self) -> Dict[CorpusToolType, Callable]:
        """Build the tool type to handler mapping"""
        return {
            CorpusToolType.CREATE: self.handlers.create_corpus_tool,
            CorpusToolType.GENERATE: self.handlers.generate_synthetic_data_tool,
            CorpusToolType.OPTIMIZE: self.handlers.optimize_corpus_tool,
            CorpusToolType.EXPORT: self.handlers.export_corpus_tool,
            CorpusToolType.VALIDATE: self.handlers.validate_corpus_tool,
            CorpusToolType.DELETE: self.handlers.delete_corpus_tool,
            CorpusToolType.UPDATE: self.handlers.update_corpus_tool,
            CorpusToolType.ANALYZE: self.handlers.analyze_corpus_tool
        }
    
    async def execute_tool(self, request: CorpusToolRequest) -> CorpusToolResponse:
        """Execute a corpus admin tool"""
        try:
            if request.tool_type not in self.tool_registry:
                return self._create_error_response(request.tool_type, "Unknown tool type")
            return await self._execute_validated_tool(request)
        except Exception as e:
            logger.error(f"Tool execution error: {str(e)}")
            return self._create_error_response(request.tool_type, str(e))
    
    async def _execute_validated_tool(self, request: CorpusToolRequest) -> CorpusToolResponse:
        """Execute tool after validation"""
        validation_result = await self._validate_request(request)
        if not validation_result[0]:
            return self._create_error_response(request.tool_type, validation_result[1])
        return await self.tool_registry[request.tool_type](request)
    
    async def _validate_request(self, request: CorpusToolRequest) -> tuple[bool, Optional[str]]:
        """Validate tool request parameters"""
        if request.tool_type in self.validators:
            return await self.validators[request.tool_type](request.parameters)
        return True, None
    
    def _create_error_response(self, tool_type: CorpusToolType, error: str) -> CorpusToolResponse:
        """Create error response for failed tool execution"""
        return CorpusToolResponse(
            success=False,
            tool_type=tool_type,
            error=error,
            metadata={"error_type": "validation_error"}
        )
    
    def get_available_tools(self) -> List[Dict[str, str]]:
        """Get list of available corpus tools"""
        tools = []
        for tool_type in CorpusToolType:
            tools.append(self._create_tool_info(tool_type))
        return tools
    
    def _create_tool_info(self, tool_type: CorpusToolType) -> Dict[str, str]:
        """Create tool information dictionary"""
        return {
            "type": tool_type.value,
            "description": self._get_tool_description(tool_type)
        }
    
    def _get_tool_description(self, tool_type: CorpusToolType) -> str:
        """Get description for a tool type"""
        descriptions = self._build_tool_descriptions()
        return descriptions.get(tool_type, "Unknown tool")
    
    def _build_tool_descriptions(self) -> Dict[CorpusToolType, str]:
        """Build tool descriptions mapping"""
        return {
            CorpusToolType.CREATE: "Create a new corpus",
            CorpusToolType.GENERATE: "Generate synthetic data",
            CorpusToolType.OPTIMIZE: "Optimize corpus performance",
            CorpusToolType.EXPORT: "Export corpus data",
            CorpusToolType.VALIDATE: "Validate corpus integrity",
            CorpusToolType.DELETE: "Delete a corpus",
            CorpusToolType.UPDATE: "Update corpus metadata",
            CorpusToolType.ANALYZE: "Analyze corpus statistics"
        }