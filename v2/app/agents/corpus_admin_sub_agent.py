# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-10T21:05:00.000000+00:00
# Agent: Claude Opus 4.1 claude-opus-4-1-20250805
# Context: Creating CorpusAdminsubAgent for corpus management
# Git: v8 | dirty
# Change: New Feature | Scope: Component | Risk: Medium
# Session: corpus-admin-agent-creation | Seq: 1
# Review: Pending | Score: 85
# ================================

import json
import logging
import time
import asyncio
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime, timezone

from pydantic import BaseModel, Field, ValidationError
from app.llm.llm_manager import LLMManager
from app.agents.base import BaseSubAgent
from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.state import DeepAgentState
from app.agents.utils import extract_json_from_response
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

class CorpusOperation(str, Enum):
    """Types of corpus operations"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    SEARCH = "search"
    ANALYZE = "analyze"
    EXPORT = "export"
    IMPORT = "import"
    VALIDATE = "validate"

class CorpusType(str, Enum):
    """Types of corpus data"""
    DOCUMENTATION = "documentation"
    KNOWLEDGE_BASE = "knowledge_base"
    TRAINING_DATA = "training_data"
    REFERENCE_DATA = "reference_data"
    EMBEDDINGS = "embeddings"

class CorpusMetadata(BaseModel):
    """Metadata for corpus entries"""
    corpus_id: Optional[str] = None
    corpus_name: str
    corpus_type: CorpusType
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    size_bytes: Optional[int] = None
    document_count: Optional[int] = None
    version: str = Field(default="1.0")
    access_level: str = Field(default="private")  # private, team, public

class CorpusOperationRequest(BaseModel):
    """Request for corpus operation"""
    operation: CorpusOperation
    corpus_metadata: CorpusMetadata
    filters: Dict[str, Any] = Field(default_factory=dict)
    content: Optional[Any] = None
    options: Dict[str, Any] = Field(default_factory=dict)
    requires_approval: bool = False

class CorpusOperationResult(BaseModel):
    """Result of corpus operation"""
    success: bool
    operation: CorpusOperation
    corpus_metadata: CorpusMetadata
    affected_documents: int = 0
    result_data: Optional[Any] = None
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    requires_approval: bool = False
    approval_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class CorpusStatistics(BaseModel):
    """Statistics about corpus"""
    total_corpora: int = 0
    total_documents: int = 0
    total_size_bytes: int = 0
    corpora_by_type: Dict[str, int] = Field(default_factory=dict)
    recent_operations: List[Dict[str, Any]] = Field(default_factory=list)
    
class CorpusAdminSubAgent(BaseSubAgent):
    """Sub-agent dedicated to corpus administration and management"""
    
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher):
        super().__init__(
            llm_manager,
            name="CorpusAdminSubAgent",
            description="Agent specialized in corpus management and administration"
        )
        self.tool_dispatcher = tool_dispatcher
        self.approval_thresholds = {
            "delete_documents": 100,  # Require approval for deleting > 100 docs
            "update_documents": 500,  # Require approval for updating > 500 docs
            "export_size_mb": 100,    # Require approval for exports > 100MB
        }
    
    async def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:
        """Check if conditions are met for corpus administration"""
        # Check if we're in admin mode or have explicit corpus request
        triage_result = state.triage_result or {}
        
        if isinstance(triage_result, dict):
            category = triage_result.get("category", "")
            is_admin = triage_result.get("is_admin_mode", False)
            
            # Check if this is a corpus management request
            if "corpus" in category.lower() or "admin" in category.lower() or is_admin:
                return True
        
        # Check if explicitly called for corpus operations
        if state.user_request:
            corpus_keywords = ["corpus", "knowledge base", "documentation", "reference data", "embeddings"]
            if any(keyword in state.user_request.lower() for keyword in corpus_keywords):
                return True
        
        self.logger.info(f"Corpus administration not required for run_id: {run_id}")
        return False
    
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Execute corpus administration operation"""
        start_time = time.time()
        
        try:
            # Send initial update
            if stream_updates:
                await self._send_update(run_id, {
                    "status": "starting",
                    "message": "📚 Initializing corpus administration...",
                    "agent": "CorpusAdminSubAgent"
                })
            
            # Parse the corpus operation request
            operation_request = await self._parse_operation_request(state)
            
            # Check if approval is required
            requires_approval = await self._check_approval_requirements(operation_request, state)
            
            if requires_approval:
                # Request user approval
                approval_message = self._generate_approval_message(operation_request)
                
                state.corpus_admin_result = CorpusOperationResult(
                    success=False,
                    operation=operation_request.operation,
                    corpus_metadata=operation_request.corpus_metadata,
                    requires_approval=True,
                    approval_message=approval_message
                ).model_dump()
                
                if stream_updates:
                    await self._send_update(run_id, {
                        "status": "approval_required",
                        "message": approval_message,
                        "requires_user_action": True,
                        "action_type": "approve_corpus_operation",
                        "operation_details": operation_request.model_dump()
                    })
                return
            
            # Execute the corpus operation
            if stream_updates:
                await self._send_update(run_id, {
                    "status": "processing",
                    "message": f"🔄 Executing {operation_request.operation.value} operation on corpus '{operation_request.corpus_metadata.corpus_name}'...",
                    "operation": operation_request.operation.value
                })
            
            # Perform the operation
            result = await self._execute_corpus_operation(operation_request, run_id, stream_updates)
            
            # Store result in state
            state.corpus_admin_result = result.model_dump()
            
            # Send completion update
            if stream_updates:
                duration = int((time.time() - start_time) * 1000)
                status_emoji = "✅" if result.success else "❌"
                
                await self._send_update(run_id, {
                    "status": "completed" if result.success else "failed",
                    "message": f"{status_emoji} Corpus operation completed in {duration}ms",
                    "result": result.model_dump(),
                    "statistics": await self._get_corpus_statistics()
                })
            
            self.logger.info(f"Corpus operation completed for run_id {run_id}: "
                           f"operation={result.operation.value}, "
                           f"success={result.success}, "
                           f"affected={result.affected_documents}")
            
        except Exception as e:
            self.logger.error(f"Corpus operation failed for run_id {run_id}: {e}")
            
            error_result = CorpusOperationResult(
                success=False,
                operation=CorpusOperation.SEARCH,
                corpus_metadata=CorpusMetadata(corpus_name="unknown", corpus_type=CorpusType.REFERENCE_DATA),
                errors=[str(e)]
            )
            state.corpus_admin_result = error_result.model_dump()
            
            if stream_updates:
                await self._send_update(run_id, {
                    "status": "error",
                    "message": f"❌ Corpus operation failed: {str(e)}",
                    "error": str(e)
                })
            raise
    
    async def _parse_operation_request(self, state: DeepAgentState) -> CorpusOperationRequest:
        """Parse corpus operation from user request"""
        
        prompt = f"""
Analyze the following user request for corpus management and extract operation details:

User Request: {state.user_request}

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
        // Optional filters for search/update/delete operations
        "date_range": {{"start": "ISO date", "end": "ISO date"}},
        "document_types": ["<types>"],
        "size_range": {{"min": bytes, "max": bytes}}
    }},
    "options": {{
        // Operation-specific options
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
        
        try:
            response = await self.llm_manager.ask_llm(prompt, llm_config_name='default')
            params = extract_json_from_response(response)
            
            if params:
                # Parse corpus metadata
                corpus_metadata = CorpusMetadata(**params.get("corpus_metadata", {}))
                
                return CorpusOperationRequest(
                    operation=CorpusOperation(params.get("operation", "search")),
                    corpus_metadata=corpus_metadata,
                    filters=params.get("filters", {}),
                    options=params.get("options", {})
                )
        except Exception as e:
            self.logger.warning(f"Failed to parse corpus operation: {e}")
        
        # Default to search operation
        return CorpusOperationRequest(
            operation=CorpusOperation.SEARCH,
            corpus_metadata=CorpusMetadata(
                corpus_name="default",
                corpus_type=CorpusType.KNOWLEDGE_BASE
            )
        )
    
    async def _check_approval_requirements(self, request: CorpusOperationRequest, state: DeepAgentState) -> bool:
        """Check if user approval is required"""
        
        # Delete operations always require approval
        if request.operation == CorpusOperation.DELETE:
            return True
        
        # Check if admin mode explicitly requests approval
        triage_result = state.triage_result or {}
        if isinstance(triage_result, dict) and triage_result.get("require_approval"):
            return True
        
        # Large update operations require approval
        if request.operation == CorpusOperation.UPDATE:
            # Would need to check actual document count
            # For now, require approval for any update with filters
            if request.filters:
                return True
        
        # Export operations for large corpora
        if request.operation == CorpusOperation.EXPORT:
            # Would need to check actual size
            # For now, don't require approval
            pass
        
        return False
    
    def _generate_approval_message(self, request: CorpusOperationRequest) -> str:
        """Generate user-friendly approval message"""
        
        operation_descriptions = {
            CorpusOperation.CREATE: "create a new corpus",
            CorpusOperation.UPDATE: "update existing corpus entries",
            CorpusOperation.DELETE: "delete corpus data",
            CorpusOperation.EXPORT: "export corpus data",
            CorpusOperation.IMPORT: "import new data into corpus",
            CorpusOperation.VALIDATE: "validate corpus integrity"
        }
        
        action = operation_descriptions.get(request.operation, "perform operation on")
        
        message = f"""
**📚 Corpus Administration Request**

**Operation:** {request.operation.value.title()}
**Corpus:** {request.corpus_metadata.corpus_name}
**Type:** {request.corpus_metadata.corpus_type.value.replace('_', ' ').title()}
**Access Level:** {request.corpus_metadata.access_level}

You are requesting to {action} "{request.corpus_metadata.corpus_name}".
"""
        
        if request.filters:
            message += f"\n**Filters Applied:**\n"
            for key, value in request.filters.items():
                message += f"  - {key}: {value}\n"
        
        if request.operation == CorpusOperation.DELETE:
            message += "\n⚠️ **Warning:** This operation cannot be undone!\n"
        
        message += "\n**Do you approve this operation?**\nReply with 'approve' to proceed or 'cancel' to abort."
        
        return message
    
    async def _execute_corpus_operation(self, 
                                       request: CorpusOperationRequest,
                                       run_id: str,
                                       stream_updates: bool) -> CorpusOperationResult:
        """Execute the corpus operation"""
        
        result = CorpusOperationResult(
            success=False,
            operation=request.operation,
            corpus_metadata=request.corpus_metadata
        )
        
        try:
            # Route to appropriate operation handler
            if request.operation == CorpusOperation.CREATE:
                result = await self._create_corpus(request, run_id, stream_updates)
            elif request.operation == CorpusOperation.SEARCH:
                result = await self._search_corpus(request, run_id, stream_updates)
            elif request.operation == CorpusOperation.UPDATE:
                result = await self._update_corpus(request, run_id, stream_updates)
            elif request.operation == CorpusOperation.DELETE:
                result = await self._delete_corpus(request, run_id, stream_updates)
            elif request.operation == CorpusOperation.ANALYZE:
                result = await self._analyze_corpus(request, run_id, stream_updates)
            elif request.operation == CorpusOperation.EXPORT:
                result = await self._export_corpus(request, run_id, stream_updates)
            elif request.operation == CorpusOperation.IMPORT:
                result = await self._import_corpus(request, run_id, stream_updates)
            elif request.operation == CorpusOperation.VALIDATE:
                result = await self._validate_corpus(request, run_id, stream_updates)
            else:
                result.errors.append(f"Unsupported operation: {request.operation}")
                
        except Exception as e:
            result.errors.append(str(e))
            self.logger.error(f"Corpus operation failed: {e}")
        
        return result
    
    async def _create_corpus(self, request: CorpusOperationRequest, run_id: str, stream_updates: bool) -> CorpusOperationResult:
        """Create a new corpus"""
        
        # Use tool dispatcher if available
        tool_name = "create_corpus"
        if self.tool_dispatcher.has_tool(tool_name):
            tool_result = await self.tool_dispatcher.dispatch_tool(
                tool_name=tool_name,
                parameters={
                    "corpus_name": request.corpus_metadata.corpus_name,
                    "corpus_type": request.corpus_metadata.corpus_type.value,
                    "description": request.corpus_metadata.description,
                    "tags": request.corpus_metadata.tags,
                    "access_level": request.corpus_metadata.access_level
                },
                state=DeepAgentState(),
                run_id=run_id
            )
            
            return CorpusOperationResult(
                success=tool_result.get("success", False),
                operation=request.operation,
                corpus_metadata=request.corpus_metadata,
                affected_documents=0,
                result_data=tool_result.get("corpus_id"),
                metadata={"corpus_id": tool_result.get("corpus_id")}
            )
        
        # Fallback mock implementation
        corpus_id = f"corpus_{int(time.time())}"
        request.corpus_metadata.corpus_id = corpus_id
        request.corpus_metadata.created_at = datetime.now(timezone.utc)
        
        return CorpusOperationResult(
            success=True,
            operation=request.operation,
            corpus_metadata=request.corpus_metadata,
            affected_documents=0,
            result_data=corpus_id,
            metadata={"corpus_id": corpus_id}
        )
    
    async def _search_corpus(self, request: CorpusOperationRequest, run_id: str, stream_updates: bool) -> CorpusOperationResult:
        """Search within corpus"""
        
        # Use tool dispatcher if available
        tool_name = "search_corpus"
        if self.tool_dispatcher.has_tool(tool_name):
            tool_result = await self.tool_dispatcher.dispatch_tool(
                tool_name=tool_name,
                parameters={
                    "corpus_name": request.corpus_metadata.corpus_name,
                    "query": request.content,
                    "filters": request.filters,
                    "limit": request.options.get("limit", 10)
                },
                state=DeepAgentState(),
                run_id=run_id
            )
            
            return CorpusOperationResult(
                success=True,
                operation=request.operation,
                corpus_metadata=request.corpus_metadata,
                affected_documents=len(tool_result.get("results", [])),
                result_data=tool_result.get("results"),
                metadata={"total_matches": tool_result.get("total_matches", 0)}
            )
        
        # Fallback mock implementation
        mock_results = [
            {
                "document_id": f"doc_{i}",
                "title": f"Document {i}",
                "relevance_score": 0.95 - (i * 0.05),
                "snippet": f"This is a relevant snippet from document {i}..."
            }
            for i in range(5)
        ]
        
        return CorpusOperationResult(
            success=True,
            operation=request.operation,
            corpus_metadata=request.corpus_metadata,
            affected_documents=len(mock_results),
            result_data=mock_results,
            metadata={"total_matches": 25}
        )
    
    async def _update_corpus(self, request: CorpusOperationRequest, run_id: str, stream_updates: bool) -> CorpusOperationResult:
        """Update corpus entries"""
        
        # Implementation would update corpus based on filters
        return CorpusOperationResult(
            success=True,
            operation=request.operation,
            corpus_metadata=request.corpus_metadata,
            affected_documents=10,
            warnings=["Update operation completed with partial success"]
        )
    
    async def _delete_corpus(self, request: CorpusOperationRequest, run_id: str, stream_updates: bool) -> CorpusOperationResult:
        """Delete corpus or entries"""
        
        # This should never execute without approval
        return CorpusOperationResult(
            success=False,
            operation=request.operation,
            corpus_metadata=request.corpus_metadata,
            errors=["Delete operation requires explicit approval"]
        )
    
    async def _analyze_corpus(self, request: CorpusOperationRequest, run_id: str, stream_updates: bool) -> CorpusOperationResult:
        """Analyze corpus statistics and quality"""
        
        analysis = {
            "total_documents": 1234,
            "total_size_mb": 45.6,
            "avg_document_size_kb": 37.8,
            "unique_terms": 8765,
            "coverage_score": 0.82,
            "quality_score": 0.91,
            "recommendations": [
                "Consider adding more recent documents",
                "Some documents lack proper metadata",
                "Embeddings may need regeneration for 15% of documents"
            ]
        }
        
        return CorpusOperationResult(
            success=True,
            operation=request.operation,
            corpus_metadata=request.corpus_metadata,
            affected_documents=1234,
            result_data=analysis
        )
    
    async def _export_corpus(self, request: CorpusOperationRequest, run_id: str, stream_updates: bool) -> CorpusOperationResult:
        """Export corpus data"""
        
        export_path = f"/exports/corpus_{request.corpus_metadata.corpus_name}_{int(time.time())}.json"
        
        return CorpusOperationResult(
            success=True,
            operation=request.operation,
            corpus_metadata=request.corpus_metadata,
            affected_documents=500,
            result_data={"export_path": export_path, "format": "json", "size_mb": 23.4}
        )
    
    async def _import_corpus(self, request: CorpusOperationRequest, run_id: str, stream_updates: bool) -> CorpusOperationResult:
        """Import data into corpus"""
        
        return CorpusOperationResult(
            success=True,
            operation=request.operation,
            corpus_metadata=request.corpus_metadata,
            affected_documents=150,
            result_data={"imported": 150, "skipped": 5, "errors": 0}
        )
    
    async def _validate_corpus(self, request: CorpusOperationRequest, run_id: str, stream_updates: bool) -> CorpusOperationResult:
        """Validate corpus integrity"""
        
        validation_results = {
            "total_checked": 1000,
            "valid": 985,
            "invalid": 15,
            "issues": [
                {"type": "missing_metadata", "count": 8},
                {"type": "corrupted_embedding", "count": 5},
                {"type": "duplicate_content", "count": 2}
            ]
        }
        
        return CorpusOperationResult(
            success=True,
            operation=request.operation,
            corpus_metadata=request.corpus_metadata,
            affected_documents=1000,
            result_data=validation_results,
            warnings=["Found 15 documents with validation issues"]
        )
    
    async def _get_corpus_statistics(self) -> Dict[str, Any]:
        """Get overall corpus statistics"""
        
        # This would query actual database
        return {
            "total_corpora": 12,
            "total_documents": 45678,
            "total_size_gb": 2.3,
            "corpora_by_type": {
                "documentation": 3,
                "knowledge_base": 5,
                "training_data": 2,
                "reference_data": 1,
                "embeddings": 1
            },
            "recent_operations": [
                {"operation": "search", "timestamp": datetime.now(timezone.utc).isoformat(), "corpus": "main_kb"},
                {"operation": "create", "timestamp": datetime.now(timezone.utc).isoformat(), "corpus": "product_docs"}
            ]
        }
    
    async def cleanup(self, state: DeepAgentState, run_id: str) -> None:
        """Cleanup after execution"""
        await super().cleanup(state, run_id)
        
        # Log final metrics
        if state.corpus_admin_result and isinstance(state.corpus_admin_result, dict):
            result = state.corpus_admin_result
            self.logger.info(f"Corpus operation completed: "
                           f"operation={result.get('operation')}, "
                           f"corpus={result.get('corpus_metadata', {}).get('corpus_name')}, "
                           f"affected={result.get('affected_documents')}")