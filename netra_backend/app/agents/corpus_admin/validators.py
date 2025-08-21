"""
Corpus Approval Validator

Validates corpus operations and determines approval requirements.
Maintains single responsibility and 25-line function limit.
"""

from typing import Any, Dict

from netra_backend.app.agents.corpus_admin.models import (
    CorpusOperation,
    CorpusOperationRequest,
)
from netra_backend.app.agents.state import DeepAgentState


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
        header = self._build_message_header()
        operation_details = self._build_operation_details(request)
        action_statement = self._build_action_statement(request, action)
        return f"{header}\n{operation_details}\n{action_statement}"
    
    def _build_message_header(self) -> str:
        """Build message header"""
        return "**📚 Corpus Administration Request**"
    
    def _build_operation_details(self, request: CorpusOperationRequest) -> str:
        """Build operation details section"""
        operation = request.operation.value.title()
        corpus_name = request.corpus_metadata.corpus_name
        corpus_type = request.corpus_metadata.corpus_type.value.replace('_', ' ').title()
        access_level = request.corpus_metadata.access_level
        return f"\n**Operation:** {operation}\n**Corpus:** {corpus_name}\n**Type:** {corpus_type}\n**Access Level:** {access_level}"
    
    def _build_action_statement(self, request: CorpusOperationRequest, action: str) -> str:
        """Build action statement"""
        return f"\nYou are requesting to {action} \"{request.corpus_metadata.corpus_name}\"."
    
    def _add_filters_info(self, message: str, request: CorpusOperationRequest) -> str:
        """Add filter information to message"""
        if request.filters:
            filter_section = self._build_filters_section(request.filters)
            message += filter_section
        return message
    
    def _build_filters_section(self, filters: dict) -> str:
        """Build filters section of message"""
        filter_lines = []
        for key, value in filters.items():
            filter_lines.append(f"  - {key}: {value}")
        return f"\n**Filters Applied:**\n" + "\n".join(filter_lines) + "\n"
    
    def _add_warning_for_delete(self, message: str, request: CorpusOperationRequest) -> str:
        """Add delete warning if applicable"""
        if request.operation == CorpusOperation.DELETE:
            message += "\n⚠️ **Warning:** This operation cannot be undone!\n"
        return message
    
    def _get_approval_prompt(self) -> str:
        """Get approval prompt text"""
        return "\n**Do you approve this operation?**\nReply with 'approve' to proceed or 'cancel' to abort."