#!/usr/bin/env python3
"""
Enhanced GitHub Workflow Introspection Tool

Provides comprehensive visibility into GitHub Actions workflow status and outputs.
Uses gh CLI for direct API access to workflow runs, jobs, steps, and logs.
"""

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.tree import Tree


@dataclass
class WorkflowStep:
    """Represents a workflow step with its status."""
    name: str
    conclusion: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]


@dataclass
class WorkflowJob:
    """Represents a workflow job with its steps."""
    name: str
    status: str
    conclusion: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    steps: List[WorkflowStep]


@dataclass
class WorkflowRun:
    """Represents a complete workflow run."""
    id: int
    name: str
    workflow_name: str
    status: str
    conclusion: Optional[str]
    head_branch: str
    head_sha: str
    event: str
    started_at: Optional[str]
    updated_at: Optional[str]
    html_url: str
    jobs: List[WorkflowJob] = None


class WorkflowIntrospector:
    """GitHub workflow introspection service using gh CLI."""
    
    def __init__(self, repo: Optional[str] = None):
        self.console = Console()
        self.repo = repo
        
    def _run_gh_command(self, args: List[str]) -> Dict:
        """Execute gh CLI command and return JSON output."""
        cmd = ["gh"] + args
        if self.repo:
            cmd.extend(["--repo", self.repo])
            
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            return json.loads(result.stdout) if result.stdout else {}
        except subprocess.CalledProcessError as e:
            self.console.print(f"[red]Error executing gh command: {e.stderr}[/red]")
            return {}
        except json.JSONDecodeError:
            return {}
    
    def list_workflows(self, limit: int = 20) -> List[Dict]:
        """List available workflows in the repository."""
        result = subprocess.run(
            ["gh", "workflow", "list", "--limit", str(limit)],
            capture_output=True,
            text=True
        )
        
        workflows = []
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split('\t')
                if len(parts) >= 3:
                    workflows.append({
                        'name': parts[0],
                        'state': parts[1],
                        'id': parts[2]
                    })
        return workflows
    
    def get_recent_runs(self, limit: int = 10, workflow: Optional[str] = None) -> List[WorkflowRun]:
        """Get recent workflow runs."""
        args = ["run", "list", "--limit", str(limit), "--json",
                "databaseId,name,status,conclusion,workflowName,headBranch,headSha,event,startedAt,updatedAt,url"]
        
        if workflow:
            args.extend(["--workflow", workflow])
            
        data = self._run_gh_command(args)
        
        runs = []
        for run_data in data:
            runs.append(WorkflowRun(
                id=run_data['databaseId'],
                name=run_data['name'],
                workflow_name=run_data['workflowName'],
                status=run_data['status'],
                conclusion=run_data.get('conclusion'),
                head_branch=run_data['headBranch'],
                head_sha=run_data['headSha'][:8],
                event=run_data['event'],
                started_at=run_data.get('startedAt'),
                updated_at=run_data.get('updatedAt'),
                html_url=run_data['url']
            ))
        return runs
    
    def get_run_details(self, run_id: int) -> Optional[WorkflowRun]:
        """Get detailed information about a specific run including jobs and steps."""
        # Get run info
        run_data = self._run_gh_command(["run", "view", str(run_id), "--json",
                                         "databaseId,name,status,conclusion,workflowName,headBranch,headSha,event,startedAt,updatedAt,url,jobs"])
        
        if not run_data:
            return None
            
        # Parse jobs and steps
        jobs = []
        for job_data in run_data.get('jobs', []):
            steps = []
            for step_data in job_data.get('steps', []):
                steps.append(WorkflowStep(
                    name=step_data['name'],
                    conclusion=step_data.get('conclusion'),
                    started_at=step_data.get('startedAt'),
                    completed_at=step_data.get('completedAt')
                ))
            
            jobs.append(WorkflowJob(
                name=job_data['name'],
                status=job_data['status'],
                conclusion=job_data.get('conclusion'),
                started_at=job_data.get('startedAt'),
                completed_at=job_data.get('completedAt'),
                steps=steps
            ))
        
        return WorkflowRun(
            id=run_data['databaseId'],
            name=run_data['name'],
            workflow_name=run_data['workflowName'],
            status=run_data['status'],
            conclusion=run_data.get('conclusion'),
            head_branch=run_data['headBranch'],
            head_sha=run_data['headSha'][:8],
            event=run_data['event'],
            started_at=run_data.get('startedAt'),
            updated_at=run_data.get('updatedAt'),
            html_url=run_data['url'],
            jobs=jobs
        )
    
    def get_run_logs(self, run_id: int, job_name: Optional[str] = None) -> str:
        """Get logs for a workflow run or specific job."""
        args = ["run", "view", str(run_id), "--log"]
        
        if job_name:
            args.extend(["--job", job_name])
            
        result = subprocess.run(
            ["gh"] + args,
            capture_output=True,
            text=True
        )
        return result.stdout
    
    def get_workflow_outputs(self, run_id: int) -> Dict:
        """Get workflow outputs via GitHub API."""
        # Use gh api to access outputs
        api_path = f"repos/{self.repo or '{owner}/{repo}'}/actions/runs/{run_id}"
        data = self._run_gh_command(["api", api_path])
        
        return {
            'outputs': data.get('outputs'),
            'artifacts_url': data.get('artifacts_url'),
            'logs_url': data.get('logs_url'),
            'check_suite_url': data.get('check_suite_url')
        }
    
    def watch_run(self, run_id: int) -> None:
        """Watch a workflow run in real-time."""
        subprocess.run(["gh", "run", "watch", str(run_id)])


class OutputFormatter:
    """Formats and displays workflow information."""
    
    def __init__(self, console: Console):
        self.console = console
    
    def display_workflows_table(self, workflows: List[Dict]) -> None:
        """Display available workflows in a table."""
        table = Table(title="Available Workflows")
        
        table.add_column("Workflow Name", style="cyan")
        table.add_column("State", style="green")
        table.add_column("ID", style="dim")
        
        for workflow in workflows:
            state_style = "green" if workflow['state'] == "active" else "yellow"
            table.add_row(
                workflow['name'],
                f"[{state_style}]{workflow['state']}[/{state_style}]",
                workflow['id']
            )
        
        self.console.print(table)
    
    def display_runs_table(self, runs: List[WorkflowRun]) -> None:
        """Display workflow runs in a table."""
        table = Table(title="Recent Workflow Runs")
        
        table.add_column("ID", style="cyan")
        table.add_column("Workflow", style="blue")
        table.add_column("Status", style="yellow")
        table.add_column("Conclusion", style="green")
        table.add_column("Branch", style="magenta")
        table.add_column("Event", style="dim")
        table.add_column("Started", style="dim")
        
        for run in runs:
            status_style = self._get_status_style(run.status, run.conclusion)
            conclusion_text = run.conclusion or "—"
            started = run.started_at.split('T')[0] if run.started_at else "—"
            
            table.add_row(
                str(run.id),
                run.workflow_name[:30],
                f"[{status_style}]{run.status}[/{status_style}]",
                f"[{status_style}]{conclusion_text}[/{status_style}]",
                run.head_branch,
                run.event,
                started
            )
        
        self.console.print(table)
    
    def display_run_details(self, run: WorkflowRun) -> None:
        """Display detailed run information with jobs and steps."""
        # Summary panel
        summary = f"""
[bold]Workflow Run Details[/bold]
=============================
ID: {run.id}
Name: {run.name}
Workflow: {run.workflow_name}
Status: [{self._get_status_style(run.status, run.conclusion)}]{run.status}[/{self._get_status_style(run.status, run.conclusion)}]
Conclusion: {run.conclusion or 'N/A'}
Branch: {run.head_branch}
SHA: {run.head_sha}
Event: {run.event}
URL: {run.html_url}
        """
        
        self.console.print(Panel(summary.strip(), expand=False))
        
        # Jobs tree
        if run.jobs:
            tree = Tree("[bold]Jobs and Steps[/bold]")
            
            for job in run.jobs:
                job_style = self._get_status_style(job.status, job.conclusion)
                job_branch = tree.add(f"[{job_style}]{job.name}[/{job_style}] ({job.status})")
                
                for step in job.steps:
                    step_style = self._get_status_style("completed", step.conclusion)
                    step_icon = "[OK]" if step.conclusion == "success" else "[X]" if step.conclusion == "failure" else "[o]"
                    job_branch.add(f"[{step_style}]{step_icon} {step.name}[/{step_style}]")
            
            self.console.print(tree)
    
    def display_outputs(self, outputs: Dict) -> None:
        """Display workflow outputs and artifacts."""
        if outputs.get('outputs'):
            self.console.print("\n[bold]Workflow Outputs:[/bold]")
            self.console.print(json.dumps(outputs['outputs'], indent=2))
        else:
            self.console.print("\n[dim]No workflow outputs available[/dim]")
        
        if outputs.get('artifacts_url'):
            self.console.print(f"\n[bold]Artifacts URL:[/bold] {outputs['artifacts_url']}")
        
        if outputs.get('logs_url'):
            self.console.print(f"[bold]Logs URL:[/bold] {outputs['logs_url']}")
    
    def _get_status_style(self, status: str, conclusion: Optional[str]) -> str:
        """Get rich style for status display."""
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


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="GitHub Workflow Introspection Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("--repo", help="Repository in format 'owner/repo'")
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # List workflows command
    list_wf = subparsers.add_parser("workflows", help="List available workflows")
    list_wf.add_argument("--limit", type=int, default=20, help="Number of workflows to show")
    
    # List runs command
    list_runs = subparsers.add_parser("runs", help="List recent workflow runs")
    list_runs.add_argument("--limit", type=int, default=10, help="Number of runs to show")
    list_runs.add_argument("--workflow", help="Filter by workflow name")
    
    # View run command
    view_run = subparsers.add_parser("view", help="View detailed run information")
    view_run.add_argument("run_id", type=int, help="Workflow run ID")
    view_run.add_argument("--logs", action="store_true", help="Show logs")
    view_run.add_argument("--outputs", action="store_true", help="Show outputs")
    
    # Watch run command
    watch_run = subparsers.add_parser("watch", help="Watch a run in real-time")
    watch_run.add_argument("run_id", type=int, help="Workflow run ID")
    
    args = parser.parse_args()
    
    console = Console()
    introspector = WorkflowIntrospector(args.repo)
    formatter = OutputFormatter(console)
    
    try:
        if args.command == "workflows":
            workflows = introspector.list_workflows(args.limit)
            formatter.display_workflows_table(workflows)
            
        elif args.command == "runs":
            runs = introspector.get_recent_runs(args.limit, args.workflow)
            formatter.display_runs_table(runs)
            
        elif args.command == "view":
            run = introspector.get_run_details(args.run_id)
            if run:
                formatter.display_run_details(run)
                
                if args.outputs:
                    outputs = introspector.get_workflow_outputs(args.run_id)
                    formatter.display_outputs(outputs)
                
                if args.logs:
                    console.print("\n[bold]Logs:[/bold]")
                    logs = introspector.get_run_logs(args.run_id)
                    console.print(Syntax(logs[:5000], "log", theme="monokai"))
            else:
                console.print(f"[red]Run {args.run_id} not found[/red]")
                
        elif args.command == "watch":
            introspector.watch_run(args.run_id)
            
        else:
            parser.print_help()
            
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())