"""
Workflow Introspection Module

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Provide workflow introspection functionality for tests
- Value Impact: Enables workflow introspection tests to execute without import errors
- Strategic Impact: Enables workflow analysis functionality validation
"""

import json
import subprocess
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
    id: int  # Can be int or str
    name: str
    workflow_name: str = ""
    status: str = "pending"
    head_branch: str = ""
    head_sha: str = ""
    event: str = ""
    started_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None
    html_url: str = ""
    jobs: List[WorkflowJob] = None
    conclusion: Optional[str] = None
    
    def __post_init__(self):
        if self.jobs is None:
            self.jobs = []


class OutputFormatter:
    """Formats workflow introspection output."""
    
    def __init__(self, console=None):
        """Initialize formatter with optional console."""
        self.console = console
    
    def _get_status_style(self, status: str, conclusion: Optional[str] = None) -> str:
        """Get style for status display."""
        if status == "completed":
            if conclusion == "success":
                return "green"
            elif conclusion == "failure":
                return "red"
            elif conclusion == "cancelled":
                return "yellow"
            else:
                return "dim"
        elif status == "in_progress":
            return "yellow"
        elif status == "queued":
            return "blue"
        else:
            return "dim"
    
    def display_workflows_table(self, workflows: List[Dict[str, str]]) -> None:
        """Display workflows in table format."""
        if self.console:
            from rich.table import Table
            table = Table(title="Workflows")
            table.add_column("Name")
            table.add_column("State") 
            table.add_column("ID")
            
            for workflow in workflows:
                table.add_row(workflow["name"], workflow["state"], workflow["id"])
            
            self.console.print(table)
        else:
            for workflow in workflows:
                print(f"{workflow['name']}\t{workflow['state']}\t{workflow['id']}")
    
    def display_runs_table(self, runs: List[WorkflowRun]) -> None:
        """Display runs in table format."""
        if self.console:
            from rich.table import Table
            table = Table(title="Workflow Runs")
            table.add_column("ID")
            table.add_column("Name")
            table.add_column("Status")
            table.add_column("Branch")
            table.add_column("Event")
            
            for run in runs:
                style = self._get_status_style(run.status, getattr(run, 'conclusion', None))
                table.add_row(
                    str(run.id),
                    run.name,
                    run.status,
                    run.head_branch,
                    run.event,
                    style=style
                )
            
            self.console.print(table)
        else:
            for run in runs:
                print(f"{run.id}\t{run.name}\t{run.status}\t{run.head_branch}\t{run.event}")
    
    def display_run_details(self, run: WorkflowRun) -> None:
        """Display detailed run information."""
        if self.console:
            from rich.tree import Tree
            from rich.text import Text
            
            tree = Tree(f"[bold]{run.name} ({run.id})[/bold]")
            tree.add(f"Status: {run.status}")
            tree.add(f"Branch: {run.head_branch}")
            tree.add(f"Event: {run.event}")
            
            for job in run.jobs:
                job_node = tree.add(f"Job: {job.name} ({job.status})")
                for step in job.steps:
                    job_node.add(f"Step: {step.name} ({step.status})")
            
            self.console.print(tree)
        else:
            print(f"Run: {run.name} ({run.id})")
            print(f"  Status: {run.status}")
            print(f"  Branch: {run.head_branch}")
            for job in run.jobs:
                print(f"  Job: {job.name} ({job.status})")
                for step in job.steps:
                    print(f"    Step: {step.name} ({step.status})")
    
    def display_outputs(self, outputs: Dict[str, Any]) -> None:
        """Display workflow outputs."""
        if outputs:
            if self.console:
                from rich.json import JSON
                self.console.print("Workflow Outputs:", style="bold")
                self.console.print(JSON(json.dumps(outputs, indent=2)))
            else:
                print("Workflow Outputs:")
                print(json.dumps(outputs, indent=2))
        else:
            if self.console:
                self.console.print("No workflow outputs available", style="dim")
            else:
                print("No workflow outputs available")
    
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
        return json.dumps(data, indent=2, default=str)


class WorkflowIntrospector:
    """Provides introspection capabilities for workflows."""
    
    def __init__(self, repo: Optional[str] = None):
        """Initialize workflow introspector."""
        self.repo = repo
        self.workflows: Dict[str, Dict[str, Any]] = {}
    
    def _run_gh_command(self, command: List[str]) -> Dict[str, Any]:
        """Run GitHub CLI command and return parsed JSON."""
        try:
            if self.repo:
                cmd = ["gh"] + command + ["--repo", self.repo]
            else:
                cmd = ["gh"] + command
                
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return json.loads(result.stdout) if result.stdout.strip() else {}
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            return {}
    
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
    
    def list_workflows(self, limit: int = 20) -> List[Dict[str, str]]:
        """List available workflows."""
        try:
            cmd = ["gh", "workflow", "list", "--limit", str(limit)]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            workflows = []
            
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = line.split('\t')
                    if len(parts) >= 3:
                        workflows.append({
                            "name": parts[0],
                            "state": parts[1],
                            "id": parts[2]
                        })
            
            return workflows
        except subprocess.CalledProcessError:
            return []
    
    def get_recent_runs(self, limit: int = 10, workflow: Optional[str] = None) -> List[WorkflowRun]:
        """Get recent workflow runs."""
        cmd = ["run", "list", "--limit", str(limit)]
        if workflow:
            cmd.extend(["--workflow", workflow])
        
        data = self._run_gh_command(cmd)
        runs = []
        
        # Handle both API response format and direct list format (for testing)
        if isinstance(data, list):
            runs_data = data
        else:
            runs_data = data.get("workflow_runs", [])
        
        for run_data in runs_data:
            # Handle head_sha truncation safely
            head_sha = run_data.get("headSha", "")
            if len(head_sha) > 8:
                head_sha = head_sha[:8]
                
            run = WorkflowRun(
                id=run_data.get("databaseId", run_data.get("id", 0)),
                name=run_data.get("name", ""),
                workflow_name=run_data.get("workflowName", ""),
                status=run_data.get("status", "unknown"),
                head_branch=run_data.get("headBranch", ""),
                head_sha=head_sha,
                event=run_data.get("event", ""),
                started_at=run_data.get("startedAt", ""),
                updated_at=run_data.get("updatedAt", ""),
                html_url=run_data.get("url", "")
            )
            # Set additional properties for test compatibility
            run.conclusion = run_data.get("conclusion")
            runs.append(run)
        
        return runs
    
    def get_run_details(self, run_id: int) -> Optional[WorkflowRun]:
        """Get detailed information about a workflow run."""
        data = self._run_gh_command(["api", f"repos/{{owner}}/{{repo}}/actions/runs/{run_id}"])
        
        if not data:
            return None
        
        jobs_data = []
        if "jobs" in data:
            for job_data in data["jobs"]:
                steps = []
                for step_data in job_data.get("steps", []):
                    step = WorkflowStep(
                        name=step_data.get("name", ""),
                        status=step_data.get("conclusion", "pending"),
                        started_at=step_data.get("startedAt"),
                        completed_at=step_data.get("completedAt")
                    )
                    steps.append(step)
                
                job = WorkflowJob(
                    name=job_data.get("name", ""),
                    status=job_data.get("conclusion", job_data.get("status", "pending")),
                    started_at=job_data.get("startedAt"),
                    completed_at=job_data.get("completedAt"),
                    steps=steps
                )
                jobs_data.append(job)
        
        run = WorkflowRun(
            id=data.get("databaseId", data.get("id", 0)),
            name=data.get("name", ""),
            workflow_name=data.get("workflowName", ""),
            status=data.get("conclusion") or data.get("status", "unknown"),
            head_branch=data.get("headBranch", ""),
            head_sha=data.get("headSha", ""),
            event=data.get("event", ""),
            started_at=data.get("startedAt", ""),
            updated_at=data.get("updatedAt", ""),
            html_url=data.get("url", ""),
            jobs=jobs_data
        )
        
        return run
    
    def get_run_logs(self, run_id: int, job_name: Optional[str] = None) -> str:
        """Get logs for a workflow run."""
        try:
            cmd = ["run", "view", str(run_id), "--log"]
            if job_name:
                cmd.extend(["--job", job_name])
            
            result = subprocess.run(["gh"] + cmd, capture_output=True, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError:
            return ""
    
    def get_workflow_outputs(self, run_id: int) -> Dict[str, Any]:
        """Get workflow outputs."""
        return self._run_gh_command(["api", f"repos/{{owner}}/{{repo}}/actions/runs/{run_id}"])
    
    def watch_run(self, run_id: int) -> None:
        """Watch a workflow run."""
        try:
            subprocess.run(["gh", "run", "watch", str(run_id)], check=True)
        except subprocess.CalledProcessError:
            pass


# Module-level functions for compatibility
def get_workflow_status(workflow_id: str) -> str:
    """Get workflow status."""
    introspector = WorkflowIntrospector()
    return introspector.get_workflow_status(workflow_id)


def introspect_workflow(workflow_id: str) -> Dict[str, Any]:
    """Introspect a workflow."""
    introspector = WorkflowIntrospector()
    return introspector.get_workflow_info(workflow_id) or {}