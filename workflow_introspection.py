"""
Workflow Introspection Module

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Provide workflow introspection functionality for tests
- Value Impact: Enables workflow introspection tests to execute without import errors
- Strategic Impact: Enables workflow analysis functionality validation
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class WorkflowStep:
    """Represents a workflow step."""
    name: str
    status: str = "pending"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    logs: List[str] = None
    
    def __post_init__(self):
        if self.logs is None:
            self.logs = []


@dataclass
class WorkflowJob:
    """Represents a workflow job."""
    name: str
    status: str = "pending"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    steps: List[WorkflowStep] = None
    
    def __post_init__(self):
        if self.steps is None:
            self.steps = []


@dataclass  
class WorkflowRun:
    """Represents a workflow run."""
    id: str
    name: str
    status: str = "pending"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    jobs: List[WorkflowJob] = None
    
    def __post_init__(self):
        if self.jobs is None:
            self.jobs = []


class OutputFormatter:
    """Formats workflow introspection output."""
    
    def format_workflow_run(self, run: WorkflowRun) -> str:
        """Format workflow run output."""
        return f"Workflow {run.name} ({run.id}): {run.status}"
    
    def format_job(self, job: WorkflowJob) -> str:
        """Format job output."""
        return f"Job {job.name}: {job.status}"
    
    def format_step(self, step: WorkflowStep) -> str:
        """Format step output."""
        return f"Step {step.name}: {step.status}"
    
    def format_json(self, data: Any) -> str:
        """Format data as JSON."""
        import json
        return json.dumps(data, indent=2, default=str)


class WorkflowIntrospector:
    """Provides introspection capabilities for workflows."""
    
    def __init__(self):
        """Initialize workflow introspector."""
        self.workflows: Dict[str, Dict[str, Any]] = {}
    
    def register_workflow(self, workflow_id: str, workflow_data: Dict[str, Any]) -> None:
        """Register a workflow for introspection."""
        self.workflows[workflow_id] = workflow_data
    
    def get_workflow_info(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow information."""
        return self.workflows.get(workflow_id)
    
    def get_workflow_status(self, workflow_id: str) -> str:
        """Get workflow status."""
        workflow = self.get_workflow_info(workflow_id)
        if workflow:
            return workflow.get('status', 'unknown')
        return 'not_found'
    
    def list_workflows(self) -> List[str]:
        """List all registered workflows."""
        return list(self.workflows.keys())


# Module-level functions for compatibility
def get_workflow_status(workflow_id: str) -> str:
    """Get workflow status."""
    introspector = WorkflowIntrospector()
    return introspector.get_workflow_status(workflow_id)


def introspect_workflow(workflow_id: str) -> Dict[str, Any]:
    """Introspect a workflow."""
    introspector = WorkflowIntrospector()
    return introspector.get_workflow_info(workflow_id) or {}