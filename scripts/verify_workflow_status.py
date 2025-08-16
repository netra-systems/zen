#!/usr/bin/env python3
"""
GitHub Workflow Status Verification Script

Verifies GitHub workflow run status via the GitHub API.
Supports authentication, retry logic, and detailed status reporting.

Usage:
    python verify_workflow_status.py --repo owner/repo --workflow-name "CI" --run-id 123456
    python verify_workflow_status.py --repo owner/repo --workflow-name "CI" --wait-for-completion
"""

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union
from urllib.parse import urljoin

import httpx
from rich.console import Console
from rich.table import Table
from tenacity import retry, stop_after_attempt, wait_exponential


@dataclass
class WorkflowRun:
    """GitHub workflow run data."""
    id: int
    status: str
    conclusion: Optional[str]
    name: str
    head_branch: str
    head_sha: str
    created_at: str
    updated_at: str
    html_url: str


@dataclass
class VerificationConfig:
    """Configuration for workflow verification."""
    repo: str
    workflow_name: Optional[str]
    run_id: Optional[int]
    token: str
    timeout: int
    poll_interval: int
    max_retries: int


class GitHubAPIError(Exception):
    """GitHub API error."""
    
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class WorkflowStatusVerifier:
    """GitHub workflow status verification service."""
    
    def __init__(self, config: VerificationConfig):
        self.config = config
        self.console = Console()
        self.client = self._create_client()
    
    def _create_client(self) -> httpx.Client:
        """Create authenticated HTTP client."""
        headers = {
            "Authorization": f"token {self.config.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "netra-workflow-verifier/1.0"
        }
        return httpx.Client(
            base_url="https://api.github.com",
            headers=headers,
            timeout=30.0
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def _api_request(self, endpoint: str) -> Dict:
        """Make authenticated API request with retry logic."""
        try:
            response = self.client.get(endpoint)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise GitHubAPIError(
                f"API request failed: {e.response.status_code} {e.response.text}",
                e.response.status_code
            )
        except httpx.RequestError as e:
            raise GitHubAPIError(f"Request error: {str(e)}")
    
    def get_workflow_runs(self, workflow_name: str) -> List[WorkflowRun]:
        """Get recent workflow runs by name."""
        endpoint = f"/repos/{self.config.repo}/actions/workflows/{workflow_name}.yml/runs"
        data = self._api_request(endpoint)
        
        runs = []
        for run_data in data.get("workflow_runs", []):
            runs.append(self._parse_workflow_run(run_data))
        return runs
    
    def get_workflow_run_by_id(self, run_id: int) -> WorkflowRun:
        """Get specific workflow run by ID."""
        endpoint = f"/repos/{self.config.repo}/actions/runs/{run_id}"
        data = self._api_request(endpoint)
        return self._parse_workflow_run(data)
    
    def _parse_workflow_run(self, data: Dict) -> WorkflowRun:
        """Parse workflow run data from API response."""
        return WorkflowRun(
            id=data["id"],
            status=data["status"],
            conclusion=data.get("conclusion"),
            name=data["name"],
            head_branch=data["head_branch"],
            head_sha=data["head_sha"][:8],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            html_url=data["html_url"]
        )
    
    def wait_for_completion(self, run: WorkflowRun) -> WorkflowRun:
        """Wait for workflow run to complete."""
        start_time = time.time()
        
        while time.time() - start_time < self.config.timeout:
            current_run = self.get_workflow_run_by_id(run.id)
            
            if current_run.status == "completed":
                return current_run
            
            self.console.print(
                f"[yellow]Waiting for workflow {current_run.name} "
                f"(ID: {current_run.id}) - Status: {current_run.status}[/yellow]"
            )
            time.sleep(self.config.poll_interval)
        
        raise GitHubAPIError(f"Workflow timeout after {self.config.timeout} seconds")
    
    def verify_workflow_success(self, run: WorkflowRun) -> bool:
        """Verify workflow completed successfully."""
        return run.status == "completed" and run.conclusion == "success"


class CLIHandler:
    """Command-line interface handler."""
    
    def __init__(self):
        self.console = Console()
    
    def parse_args(self) -> argparse.Namespace:
        """Parse command-line arguments."""
        parser = argparse.ArgumentParser(
            description="Verify GitHub workflow status",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=self._get_usage_examples()
        )
        
        parser.add_argument(
            "--repo", required=True,
            help="Repository in format 'owner/repo'"
        )
        parser.add_argument(
            "--workflow-name",
            help="Workflow name (file name without .yml extension)"
        )
        parser.add_argument(
            "--run-id", type=int,
            help="Specific workflow run ID to check"
        )
        parser.add_argument(
            "--token",
            help="GitHub token (defaults to GITHUB_TOKEN env var)"
        )
        parser.add_argument(
            "--wait-for-completion", action="store_true",
            help="Wait for workflow to complete"
        )
        parser.add_argument(
            "--timeout", type=int, default=1800,
            help="Timeout in seconds for waiting (default: 1800)"
        )
        parser.add_argument(
            "--poll-interval", type=int, default=30,
            help="Polling interval in seconds (default: 30)"
        )
        parser.add_argument(
            "--output", choices=["table", "json"], default="table",
            help="Output format (default: table)"
        )
        
        return parser.parse_args()
    
    def _get_usage_examples(self) -> str:
        """Get usage examples for help text."""
        return """
Examples:
  # Check specific workflow run
  python verify_workflow_status.py --repo owner/repo --run-id 123456
  
  # Check latest workflow run by name
  python verify_workflow_status.py --repo owner/repo --workflow-name "test-suite"
  
  # Wait for workflow completion
  python verify_workflow_status.py --repo owner/repo --workflow-name "deploy" --wait-for-completion
  
  # JSON output
  python verify_workflow_status.py --repo owner/repo --run-id 123456 --output json
"""
    
    def validate_args(self, args: argparse.Namespace) -> None:
        """Validate command-line arguments."""
        if not args.run_id and not args.workflow_name:
            raise ValueError("Either --run-id or --workflow-name must be specified")
        
        if args.wait_for_completion and not args.workflow_name:
            raise ValueError("--wait-for-completion requires --workflow-name")
    
    def get_github_token(self, token_arg: Optional[str]) -> str:
        """Get GitHub token from args or environment."""
        token = token_arg or os.getenv("GITHUB_TOKEN")
        if not token:
            raise ValueError("GitHub token required: use --token or set GITHUB_TOKEN")
        return token


class OutputFormatter:
    """Formats and displays verification results."""
    
    def __init__(self, console: Console):
        self.console = console
    
    def display_table(self, runs: List[WorkflowRun], title: str = "Workflow Status") -> None:
        """Display workflow runs in table format."""
        table = Table(title=title)
        
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="blue")
        table.add_column("Status", style="yellow")
        table.add_column("Conclusion", style="green")
        table.add_column("Branch", style="magenta")
        table.add_column("SHA", style="dim")
        table.add_column("Updated", style="dim")
        
        for run in runs:
            status_style = self._get_status_style(run.status, run.conclusion)
            conclusion_text = run.conclusion or "—"
            
            table.add_row(
                str(run.id),
                run.name,
                f"[{status_style}]{run.status}[/{status_style}]",
                f"[{status_style}]{conclusion_text}[/{status_style}]",
                run.head_branch,
                run.head_sha,
                run.updated_at.split("T")[1][:8]  # Show time only
            )
        
        self.console.print(table)
    
    def display_json(self, runs: List[WorkflowRun]) -> None:
        """Display workflow runs in JSON format."""
        data = [
            {
                "id": run.id,
                "name": run.name,
                "status": run.status,
                "conclusion": run.conclusion,
                "head_branch": run.head_branch,
                "head_sha": run.head_sha,
                "created_at": run.created_at,
                "updated_at": run.updated_at,
                "html_url": run.html_url
            }
            for run in runs
        ]
        
        print(json.dumps(data, indent=2))
    
    def _get_status_style(self, status: str, conclusion: Optional[str]) -> str:
        """Get rich style for status display."""
        if status == "completed":
            return "green" if conclusion == "success" else "red"
        return "yellow"
    
    def display_success_summary(self, run: WorkflowRun) -> None:
        """Display success summary."""
        self.console.print(f"[green]SUCCESS: Workflow {run.name} completed successfully[/green]")
        self.console.print(f"   Run ID: {run.id}")
        self.console.print(f"   URL: {run.html_url}")
    
    def display_failure_summary(self, run: WorkflowRun) -> None:
        """Display failure summary."""
        self.console.print(f"[red]FAILED: Workflow {run.name} failed[/red]")
        self.console.print(f"   Status: {run.status}")
        self.console.print(f"   Conclusion: {run.conclusion}")
        self.console.print(f"   URL: {run.html_url}")


def create_config_from_args(args: argparse.Namespace) -> VerificationConfig:
    """Create verification config from CLI arguments."""
    cli_handler = CLIHandler()
    
    return VerificationConfig(
        repo=args.repo,
        workflow_name=args.workflow_name,
        run_id=args.run_id,
        token=cli_handler.get_github_token(args.token),
        timeout=args.timeout,
        poll_interval=args.poll_interval,
        max_retries=3
    )


def main() -> int:
    """Main entry point."""
    console = Console()
    cli_handler = CLIHandler()
    formatter = OutputFormatter(console)
    
    try:
        args = cli_handler.parse_args()
        cli_handler.validate_args(args)
        
        config = create_config_from_args(args)
        verifier = WorkflowStatusVerifier(config)
        
        # Get workflow run(s)
        if config.run_id:
            runs = [verifier.get_workflow_run_by_id(config.run_id)]
        else:
            all_runs = verifier.get_workflow_runs(config.workflow_name)
            runs = all_runs[:1] if all_runs else []
        
        if not runs:
            console.print("[red]ERROR: No workflow runs found[/red]")
            return 1
        
        run = runs[0]
        
        # Wait for completion if requested
        if args.wait_for_completion and run.status != "completed":
            run = verifier.wait_for_completion(run)
            runs = [run]
        
        # Display results
        if args.output == "json":
            formatter.display_json(runs)
        else:
            formatter.display_table(runs)
        
        # Check success and return appropriate exit code
        if verifier.verify_workflow_success(run):
            formatter.display_success_summary(run)
            return 0
        else:
            formatter.display_failure_summary(run)
            return 1
    
    except Exception as e:
        console.print(f"[red]ERROR: {str(e)}[/red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())