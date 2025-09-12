#!/usr/bin/env python3
"""ACT wrapper for local GitHub Actions testing."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rich.console import Console
from rich.table import Table

console = Console()


class ACTWrapper:
    """Wrapper for ACT CLI tool."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.workflows_dir = self.project_root / ".github" / "workflows"
        self.secrets_file = self.project_root / ".act.secrets"
        self.env_file = self.project_root / ".act.env"
        self._validate_prerequisites()
    
    def _validate_prerequisites(self) -> None:
        """Validate ACT and Docker are installed."""
        if not self._check_command("act", "--version"):
            console.print("[red]ACT not installed. Install from: https://github.com/nektos/act[/red]")
            sys.exit(1)
        if not self._check_docker():
            console.print("[red]Docker not running. Please start Docker Desktop.[/red]")
            sys.exit(1)
    
    def _check_command(self, cmd: str, arg: str) -> bool:
        """Check if command exists."""
        try:
            subprocess.run([cmd, arg], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _check_docker(self) -> bool:
        """Check if Docker is running."""
        return self._check_command("docker", "info")
    
    def list_workflows(self) -> List[Dict[str, str]]:
        """List all available workflows."""
        workflows = []
        for workflow_file in self.workflows_dir.glob("*.yml"):
            workflows.append(self._parse_workflow(workflow_file))
        for workflow_file in self.workflows_dir.glob("*.yaml"):
            workflows.append(self._parse_workflow(workflow_file))
        return workflows
    
    def _parse_workflow(self, file_path: Path) -> Dict[str, str]:
        """Parse workflow file for metadata."""
        import yaml
        with open(file_path, encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return {
            "file": file_path.name,
            "name": data.get("name", file_path.stem),
            "jobs": list(data.get("jobs", {}).keys())
        }
    
    def run_workflow(self, workflow: str, job: Optional[str] = None) -> int:
        """Run a specific workflow."""
        workflow_path = self._resolve_workflow_path(workflow)
        if not workflow_path:
            console.print(f"[red]Workflow '{workflow}' not found[/red]")
            return 1
        return self._execute_act(workflow_path, job)
    
    def _resolve_workflow_path(self, workflow: str) -> Optional[Path]:
        """Resolve workflow name to file path."""
        if workflow.endswith((".yml", ".yaml")):
            path = self.workflows_dir / workflow
        else:
            yml_path = self.workflows_dir / f"{workflow}.yml"
            yaml_path = self.workflows_dir / f"{workflow}.yaml"
            path = yml_path if yml_path.exists() else yaml_path
        return path if path.exists() else None
    
    def _execute_act(self, workflow_path: Path, job: Optional[str]) -> int:
        """Execute ACT command."""
        cmd = self._build_act_command(workflow_path, job)
        console.print(f"[cyan]Running: {' '.join(cmd)}[/cyan]")
        return subprocess.run(cmd).returncode
    
    def _build_act_command(self, workflow_path: Path, job: Optional[str]) -> List[str]:
        """Build ACT command with options."""
        cmd = ["act", "-W", str(workflow_path)]
        if job:
            cmd.extend(["-j", job])
        if self.secrets_file.exists():
            cmd.extend(["--secret-file", str(self.secrets_file)])
        if self.env_file.exists():
            cmd.extend(["--env-file", str(self.env_file)])
        return cmd
    
    def validate_workflows(self) -> bool:
        """Validate all workflows."""
        console.print("[cyan]Validating workflows...[/cyan]")
        all_valid = True
        for workflow_file in self.workflows_dir.glob("*.y*ml"):
            if not self._validate_single_workflow(workflow_file):
                all_valid = False
        return all_valid
    
    def _validate_single_workflow(self, workflow_file: Path) -> bool:
        """Validate a single workflow file."""
        cmd = ["act", "-W", str(workflow_file), "-l"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            console.print(f"[green][U+2713][/green] {workflow_file.name}")
            return True
        console.print(f"[red][U+2717][/red] {workflow_file.name}: {result.stderr}")
        return False
    
    def display_workflows(self) -> None:
        """Display workflows in a table."""
        workflows = self.list_workflows()
        table = self._create_workflows_table()
        for workflow in workflows:
            self._add_workflow_to_table(table, workflow)
        console.print(table)
    
    def _create_workflows_table(self) -> Table:
        """Create table for workflow display."""
        table = Table(title="Available Workflows")
        table.add_column("File", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Jobs", style="yellow")
        return table
    
    def _add_workflow_to_table(self, table: Table, workflow: Dict[str, str]) -> None:
        """Add workflow row to table."""
        jobs_str = ", ".join(workflow["jobs"])
        table.add_row(workflow["file"], workflow["name"], jobs_str)


class StagingDeployer:
    """Handle staging deployments locally."""
    
    def __init__(self, wrapper: ACTWrapper):
        self.wrapper = wrapper
        self.staging_workflow = "staging-environment.yml"
    
    def deploy(self, environment: str = "staging") -> int:
        """Run staging deployment."""
        console.print(f"[cyan]Starting {environment} deployment...[/cyan]")
        return self._execute_deployment(environment)
    
    def _execute_deployment(self, environment: str) -> int:
        """Execute deployment workflow."""
        env_vars = self._prepare_environment(environment)
        with self._temporary_env_file(env_vars):
            return self.wrapper.run_workflow(self.staging_workflow)
    
    def _prepare_environment(self, environment: str) -> Dict[str, str]:
        """Prepare environment variables."""
        return {
            "ENVIRONMENT": environment,
            "DEPLOY_TARGET": "local",
            "SKIP_TESTS": "false"
        }
    
    def _temporary_env_file(self, env_vars: Dict[str, str]):
        """Context manager for temporary env file."""
        import contextlib
        import tempfile
        
        @contextlib.contextmanager
        def _temp_env():
            with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
                for key, value in env_vars.items():
                    f.write(f"{key}={value}\n")
                temp_path = f.name
            try:
                original = self.wrapper.env_file
                self.wrapper.env_file = Path(temp_path)
                yield
            finally:
                self.wrapper.env_file = original
                os.unlink(temp_path)
        
        return _temp_env()


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    wrapper = ACTWrapper()
    return execute_command(wrapper, args)


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(description="ACT wrapper for local testing")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    add_subcommands(subparsers)
    return parser


def add_subcommands(subparsers) -> None:
    """Add subcommands to parser."""
    subparsers.add_parser("list", help="List workflows")
    subparsers.add_parser("validate", help="Validate workflows")
    add_run_command(subparsers)
    add_staging_command(subparsers)


def add_run_command(subparsers) -> None:
    """Add run subcommand."""
    run_parser = subparsers.add_parser("run", help="Run workflow")
    run_parser.add_argument("workflow", help="Workflow name or file")
    run_parser.add_argument("--job", help="Specific job to run")


def add_staging_command(subparsers) -> None:
    """Add staging deployment subcommand."""
    staging_parser = subparsers.add_parser("staging-deploy", help="Run staging deployment")
    staging_parser.add_argument("--env", default="staging", help="Environment name")


def execute_command(wrapper: ACTWrapper, args) -> int:
    """Execute the selected command."""
    if args.command == "list":
        wrapper.display_workflows()
        return 0
    elif args.command == "validate":
        return 0 if wrapper.validate_workflows() else 1
    elif args.command == "run":
        return wrapper.run_workflow(args.workflow, args.job)
    elif args.command == "staging-deploy":
        deployer = StagingDeployer(wrapper)
        return deployer.deploy(args.env)
    else:
        console.print("[yellow]No command specified. Use --help for usage.[/yellow]")
        return 1


if __name__ == "__main__":
    sys.exit(main())