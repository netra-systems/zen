"""
Workflow Status Verification Module

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Provide workflow status verification functionality for tests
- Value Impact: Enables workflow verification tests to execute without import errors
- Strategic Impact: Enables workflow status verification functionality validation
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from scripts.manage_workflows import WorkflowManager, WorkflowStatus

# Import from workflow_introspection for compatibility
try:
    from workflow_introspection import WorkflowRun
except ImportError:
    # Fallback definition
    @dataclass
    class WorkflowRun:
        """Workflow run data."""
        id: str
        name: str
        status: str = "pending"
        started_at: Optional[Any] = None
        completed_at: Optional[Any] = None


@dataclass
class VerificationConfig:
    """Configuration for workflow verification."""
    timeout: int = 30
    retry_count: int = 3
    retry_interval: float = 1.0
    strict_mode: bool = False


class GitHubAPIError(Exception):
    """Custom exception for GitHub API errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None):
        """Initialize GitHub API error."""
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class OutputFormatter:
    """Formats output for workflow verification."""
    
    def format_verification_result(self, result: Dict[str, Any]) -> str:
        """Format verification result."""
        import json
        return json.dumps(result, indent=2, default=str)
    
    def format_table(self, data: List[Dict[str, Any]], columns: List[str]) -> str:
        """Format data as a table."""
        if not data:
            return "No data to display"
        
        # Simple table formatting
        header = " | ".join(columns)
        separator = "-" * len(header)
        rows = []
        
        for item in data:
            row = " | ".join(str(item.get(col, "")) for col in columns)
            rows.append(row)
        
        return "\n".join([header, separator] + rows)
    
    def format_json(self, data: Any) -> str:
        """Format data as JSON."""
        import json
        return json.dumps(data, indent=2, default=str)


class CLIHandler:
    """Command line interface handler for workflow verification."""
    
    def __init__(self, config: Optional[VerificationConfig] = None):
        """Initialize CLI handler."""
        self.config = config or VerificationConfig()
        self.verifier = WorkflowStatusVerifier()
    
    def handle_verify_command(self, workflow_id: str, expected_status: str) -> Dict[str, Any]:
        """Handle verify command from CLI."""
        result = self.verifier.verify_workflow_status(workflow_id, expected_status)
        return {
            'workflow_id': workflow_id,
            'expected_status': expected_status,
            'verified': result,
            'actual_status': self.verifier.workflow_manager.get_workflow_status(workflow_id)
        }
    
    def handle_list_command(self) -> Dict[str, Any]:
        """Handle list command from CLI."""
        workflows = self.verifier.workflow_manager.list_workflows()
        return {'workflows': workflows, 'count': len(workflows)}
    
    def handle_health_command(self, workflow_id: str) -> Dict[str, Any]:
        """Handle health command from CLI."""
        return self.verifier.verify_workflow_health(workflow_id)


class WorkflowStatusVerifier:
    """Verifies workflow status and health."""
    
    def __init__(self, workflow_manager: Optional[WorkflowManager] = None):
        """Initialize workflow status verifier."""
        self.workflow_manager = workflow_manager or WorkflowManager()
    
    def verify_workflow_status(self, workflow_id: str, expected_status: str) -> bool:
        """Verify workflow has expected status."""
        actual_status = self.workflow_manager.get_workflow_status(workflow_id)
        return actual_status == expected_status
    
    def verify_workflow_exists(self, workflow_id: str) -> bool:
        """Verify workflow exists."""
        return workflow_id in self.workflow_manager.workflows
    
    def verify_workflow_health(self, workflow_id: str) -> Dict[str, Any]:
        """Verify workflow health."""
        if not self.verify_workflow_exists(workflow_id):
            return {'healthy': False, 'reason': 'workflow_not_found'}
        
        workflow = self.workflow_manager.workflows[workflow_id]
        status = workflow['status']
        
        if status == WorkflowStatus.FAILED.value:
            return {'healthy': False, 'reason': 'workflow_failed'}
        
        if status in [WorkflowStatus.PENDING.value, WorkflowStatus.RUNNING.value, 
                      WorkflowStatus.COMPLETED.value]:
            return {'healthy': True, 'status': status}
        
        return {'healthy': False, 'reason': 'unknown_status', 'status': status}
    
    def get_verification_report(self, workflow_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get verification report for multiple workflows."""
        report = {}
        for workflow_id in workflow_ids:
            report[workflow_id] = {
                'exists': self.verify_workflow_exists(workflow_id),
                'status': self.workflow_manager.get_workflow_status(workflow_id),
                'health': self.verify_workflow_health(workflow_id)
            }
        return report


# Module-level instance
verifier = WorkflowStatusVerifier()


# Module-level functions for compatibility
def verify_workflow_status(workflow_id: str, expected_status: str) -> bool:
    """Verify workflow status."""
    return verifier.verify_workflow_status(workflow_id, expected_status)


def verify_workflow_exists(workflow_id: str) -> bool:
    """Verify workflow exists."""
    return verifier.verify_workflow_exists(workflow_id)


def get_workflow_health(workflow_id: str) -> Dict[str, Any]:
    """Get workflow health."""
    return verifier.verify_workflow_health(workflow_id)


def create_config_from_args(args: Any) -> VerificationConfig:
    """Create configuration from command line arguments."""
    config = VerificationConfig()
    
    # Set config values from args if they exist
    if hasattr(args, 'timeout'):
        config.timeout = getattr(args, 'timeout', 30)
    if hasattr(args, 'retry_count'):
        config.retry_count = getattr(args, 'retry_count', 3)
    if hasattr(args, 'retry_interval'):
        config.retry_interval = getattr(args, 'retry_interval', 1.0)
    if hasattr(args, 'strict_mode'):
        config.strict_mode = getattr(args, 'strict_mode', False)
    
    return config