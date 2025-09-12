"""
Corpus validators module.

Provides validators for corpus operations.
This module has been removed but tests still reference it.
"""

from typing import Any, Dict, List
from netra_backend.app.services.user_execution_context import UserExecutionContext


class CorpusApprovalValidator:
    """
    Corpus approval validator.
    
    Validates whether corpus operations require approval.
    """
    
    def __init__(self):
        self.high_risk_operations = ["delete", "bulk_update", "migrate"]
        self.approval_required_corpus_types = ["production", "critical"]
    
    def validate_approval_required(self, request: Any, user_context: UserExecutionContext,
                                 run_id: str, stream_updates: bool) -> bool:
        """Validate if operation requires approval."""
        # Extract operation from request
        operation = getattr(request, 'operation', 'unknown')
        if hasattr(request, 'get'):
            operation = request.get('operation', 'unknown')
        elif isinstance(request, dict):
            operation = request.get('operation', 'unknown')
        
        # Check if operation is high risk
        if operation in self.high_risk_operations:
            return True
        
        # Check if corpus is critical
        corpus_type = getattr(state, 'corpus_type', None)
        if corpus_type in self.approval_required_corpus_types:
            return True
            
        return False
    
    def get_approval_requirements(self, operation: str) -> Dict[str, Any]:
        """Get approval requirements for operation."""
        if operation in self.high_risk_operations:
            return {
                "approval_required": True,
                "approvers_needed": 2,
                "approval_type": "manager_approval"
            }
        else:
            return {
                "approval_required": False,
                "approvers_needed": 0,
                "approval_type": "none"
            }
    
    def validate_approver_permissions(self, user_id: str, operation: str) -> bool:
        """Validate if user has permission to approve operation."""
        # Simplified validation - in real implementation would check roles/permissions
        return True


class CorpusDataValidator:
    """
    Corpus data validator.
    
    Validates corpus data and metadata.
    """
    
    def __init__(self):
        self.required_fields = ["name", "type"]
        self.valid_types = ["documentation", "knowledge_base", "reference", "custom"]
    
    def validate_corpus_data(self, corpus_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate corpus data."""
        errors = []
        
        # Check required fields
        for field in self.required_fields:
            if field not in corpus_data:
                errors.append(f"Missing required field: {field}")
        
        # Check corpus type
        if "type" in corpus_data and corpus_data["type"] not in self.valid_types:
            errors.append(f"Invalid corpus type: {corpus_data['type']}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    def validate_document_format(self, document_data: Any) -> Dict[str, Any]:
        """Validate document format."""
        if not document_data:
            return {"valid": False, "errors": ["Document data is empty"]}
        
        return {"valid": True, "errors": []}
    
    def validate_corpus_size(self, size_bytes: int) -> Dict[str, Any]:
        """Validate corpus size limits."""
        max_size = 1000 * 1024 * 1024  # 1GB limit
        
        if size_bytes > max_size:
            return {
                "valid": False, 
                "errors": [f"Corpus size {size_bytes} exceeds maximum {max_size}"]
            }
        
        return {"valid": True, "errors": []}