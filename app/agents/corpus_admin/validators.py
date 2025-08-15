"""
Corpus Approval Validator

Validates corpus operations and determines approval requirements.
Maintains single responsibility and 8-line function limit.
"""

from typing import Dict, Any
from app.agents.state import DeepAgentState
from .models import CorpusOperation, CorpusOperationRequest


class CorpusApprovalValidator:
    """Validates and determines approval requirements for corpus operations"""
    
    def __init__(self) -> None:
        self.approval_thresholds = {
            "delete_documents": 100,
            "update_documents": 500,
            "export_size_mb": 100,
        }
    
    async def check_approval_requirements(
        self, 
        request: CorpusOperationRequest, 
        state: DeepAgentState
    ) -> bool:
        """Check if user approval is required"""
        if self._is_delete_operation(request):
            return True
        if self._has_explicit_approval_request(state):
            return True
        if self._is_large_update_operation(request):
            return True
        return False
    
    def generate_approval_message(self, request: CorpusOperationRequest) -> str:
        """Generate user-friendly approval message"""
        operation_descriptions = self._get_operation_descriptions()
        action = operation_descriptions.get(request.operation, "perform operation on")
        
        message = self._build_base_message(request, action)
        message = self._add_filters_info(message, request)
        message = self._add_warning_for_delete(message, request)
        message += self._get_approval_prompt()
        
        return message
    
    def _is_delete_operation(self, request: CorpusOperationRequest) -> bool:
        """Check if operation is delete"""
        return request.operation == CorpusOperation.DELETE
    
    def _has_explicit_approval_request(self, state: DeepAgentState) -> bool:
        """Check if triage result requires approval"""
        triage_result = state.triage_result or {}
        return isinstance(triage_result, dict) and triage_result.get("require_approval")
    
    def _is_large_update_operation(self, request: CorpusOperationRequest) -> bool:
        """Check if update operation is large enough to require approval"""
        return (request.operation == CorpusOperation.UPDATE and 
                request.filters)
    
    def _get_operation_descriptions(self) -> Dict[CorpusOperation, str]:
        """Get human-readable operation descriptions"""
        return {
            CorpusOperation.CREATE: "create a new corpus",
            CorpusOperation.UPDATE: "update existing corpus entries",
            CorpusOperation.DELETE: "delete corpus data",
            CorpusOperation.EXPORT: "export corpus data",
            CorpusOperation.IMPORT: "import new data into corpus",
            CorpusOperation.VALIDATE: "validate corpus integrity"
        }
    
    def _build_base_message(self, request: CorpusOperationRequest, action: str) -> str:
        """Build base approval message"""
        return f"""
**📚 Corpus Administration Request**

**Operation:** {request.operation.value.title()}
**Corpus:** {request.corpus_metadata.corpus_name}
**Type:** {request.corpus_metadata.corpus_type.value.replace('_', ' ').title()}
**Access Level:** {request.corpus_metadata.access_level}

You are requesting to {action} "{request.corpus_metadata.corpus_name}".
"""
    
    def _add_filters_info(self, message: str, request: CorpusOperationRequest) -> str:
        """Add filter information to message"""
        if request.filters:
            message += f"\n**Filters Applied:**\n"
            for key, value in request.filters.items():
                message += f"  - {key}: {value}\n"
        return message
    
    def _add_warning_for_delete(self, message: str, request: CorpusOperationRequest) -> str:
        """Add delete warning if applicable"""
        if request.operation == CorpusOperation.DELETE:
            message += "\n⚠️ **Warning:** This operation cannot be undone!\n"
        return message
    
    def _get_approval_prompt(self) -> str:
        """Get approval prompt text"""
        return "\n**Do you approve this operation?**\nReply with 'approve' to proceed or 'cancel' to abort."