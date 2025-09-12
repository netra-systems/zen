#!/usr/bin/env python3
"""GitHub Actions workflow validation for pre-deployment checks."""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import yaml
from rich.console import Console
from rich.table import Table

console = Console()


class WorkflowValidator:
    """Validate GitHub Actions workflow files."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.workflows_dir = self.project_root / ".github" / "workflows"
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.known_actions = self._load_known_actions()
    
    def _load_known_actions(self) -> Set[str]:
        """Load list of known valid actions."""
        return {
            "actions/checkout",
            "actions/setup-python",
            "actions/setup-node",
            "actions/cache",
            "actions/upload-artifact",
            "actions/download-artifact"
        }
    
    def validate_all(self) -> bool:
        """Validate all workflow files."""
        console.print("[cyan]Validating GitHub Actions workflows...[/cyan]")
        all_valid = True
        for workflow_file in self._get_workflow_files():
            if not self.validate_file(workflow_file):
                all_valid = False
        self._display_summary()
        return all_valid
    
    def _get_workflow_files(self) -> List[Path]:
        """Get all workflow files."""
        files = list(self.workflows_dir.glob("*.yml"))
        files.extend(self.workflows_dir.glob("*.yaml"))
        return sorted(files)
    
    def validate_file(self, file_path: Path) -> bool:
        """Validate a single workflow file."""
        self.errors.clear()
        self.warnings.clear()
        
        if not self._validate_yaml_syntax(file_path):
            return False
        
        workflow = self._load_workflow(file_path)
        if not workflow:
            return False
        
        self._validate_structure(workflow)
        self._validate_jobs(workflow)
        self._validate_actions(workflow)
        self._check_act_compatibility(workflow)
        
        return self._report_file_status(file_path)
    
    def _validate_yaml_syntax(self, file_path: Path) -> bool:
        """Check YAML syntax is valid."""
        try:
            with open(file_path) as f:
                yaml.safe_load(f)
            return True
        except yaml.YAMLError as e:
            self.errors.append(f"YAML syntax error: {e}")
            return False
    
    def _load_workflow(self, file_path: Path) -> Optional[Dict]:
        """Load workflow content."""
        try:
            with open(file_path) as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.errors.append(f"Failed to load: {e}")
            return None
    
    def _validate_structure(self, workflow: Dict) -> None:
        """Validate workflow structure."""
        if "name" not in workflow:
            self.warnings.append("Missing 'name' field")
        if "on" not in workflow:
            self.errors.append("Missing 'on' trigger")
        if "jobs" not in workflow:
            self.errors.append("Missing 'jobs' section")
    
    def _validate_jobs(self, workflow: Dict) -> None:
        """Validate job definitions."""
        jobs = workflow.get("jobs", {})
        for job_name, job_def in jobs.items():
            self._validate_single_job(job_name, job_def)
    
    def _validate_single_job(self, name: str, job: Dict) -> None:
        """Validate a single job."""
        if "runs-on" not in job:
            self.errors.append(f"Job '{name}' missing 'runs-on'")
        if "steps" not in job:
            self.errors.append(f"Job '{name}' missing 'steps'")
        else:
            self._validate_steps(name, job["steps"])
    
    def _validate_steps(self, job_name: str, steps: List[Dict]) -> None:
        """Validate job steps."""
        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                self.errors.append(f"Job '{job_name}' step {i+1} invalid")
                continue
            if "uses" not in step and "run" not in step:
                self.errors.append(f"Job '{job_name}' step {i+1} missing action")
    
    def _validate_actions(self, workflow: Dict) -> None:
        """Validate action references."""
        jobs = workflow.get("jobs", {})
        for job_def in jobs.values():
            for step in job_def.get("steps", []):
                self._validate_action_reference(step)
    
    def _validate_action_reference(self, step: Dict) -> None:
        """Validate action reference format."""
        if "uses" not in step:
            return
        action = step["uses"]
        if not self._is_valid_action_format(action):
            self.errors.append(f"Invalid action format: {action}")
    
    def _is_valid_action_format(self, action: str) -> bool:
        """Check if action reference is valid."""
        pattern = r'^[a-zA-Z0-9-_]+/[a-zA-Z0-9-_]+@.+$'
        return bool(re.match(pattern, action))
    
    def _check_act_compatibility(self, workflow: Dict) -> None:
        """Check for ACT compatibility issues."""
        self._check_unsupported_features(workflow)
        self._check_runner_compatibility(workflow)
    
    def _check_unsupported_features(self, workflow: Dict) -> None:
        """Check for features not supported by ACT."""
        if "concurrency" in workflow:
            self.warnings.append("Concurrency control not fully supported in ACT")
        
        triggers = workflow.get("on", {})
        if isinstance(triggers, dict) and "schedule" in triggers:
            self.warnings.append("Scheduled workflows cannot be tested locally")
    
    def _check_runner_compatibility(self, workflow: Dict) -> None:
        """Check runner compatibility."""
        jobs = workflow.get("jobs", {})
        for job_name, job_def in jobs.items():
            runner = job_def.get("runs-on", "")
            if "self-hosted" in str(runner):
                self.warnings.append(f"Job '{job_name}' uses self-hosted runner")
    
    def _report_file_status(self, file_path: Path) -> bool:
        """Report validation status for file."""
        name = file_path.name
        if self.errors:
            console.print(f"[red][U+2717][/red] {name}")
            for error in self.errors:
                console.print(f"  [red]ERROR:[/red] {error}")
        elif self.warnings:
            console.print(f"[yellow] WARNING: [/yellow] {name}")
            for warning in self.warnings:
                console.print(f"  [yellow]WARN:[/yellow] {warning}")
        else:
            console.print(f"[green][U+2713][/green] {name}")
        
        return len(self.errors) == 0
    
    def _display_summary(self) -> None:
        """Display validation summary."""
        table = Table(title="Validation Summary")
        table.add_column("Status", style="cyan")
        table.add_column("Count", style="white")
        
        total = len(list(self._get_workflow_files()))
        valid = sum(1 for f in self._get_workflow_files() if self.validate_file(f))
        
        table.add_row("Total Workflows", str(total))
        table.add_row("[green]Valid[/green]", str(valid))
        table.add_row("[red]Invalid[/red]", str(total - valid))
        
        console.print(table)


class SecretValidator:
    """Validate secrets configuration."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.secrets_file = self.project_root / ".act.secrets"
        self.required_secrets = self._load_required_secrets()
    
    def _load_required_secrets(self) -> Set[str]:
        """Load list of required secrets."""
        return {
            "GITHUB_TOKEN",
            "NPM_TOKEN",
            "DOCKER_PASSWORD"
        }
    
    def validate(self) -> bool:
        """Validate secrets configuration."""
        if not self.secrets_file.exists():
            console.print("[yellow]No .act.secrets file found[/yellow]")
            return False
        
        existing = self._parse_secrets_file()
        missing = self.required_secrets - existing
        
        if missing:
            self._report_missing_secrets(missing)
            return False
        
        console.print("[green]All required secrets configured[/green]")
        return True
    
    def _parse_secrets_file(self) -> Set[str]:
        """Parse secrets file for defined secrets."""
        secrets = set()
        with open(self.secrets_file) as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key = line.split("=")[0].strip()
                    secrets.add(key)
        return secrets
    
    def _report_missing_secrets(self, missing: Set[str]) -> None:
        """Report missing secrets."""
        console.print("[red]Missing required secrets:[/red]")
        for secret in sorted(missing):
            console.print(f"  - {secret}")


def main():
    """Main entry point."""
    validator = WorkflowValidator()
    secret_validator = SecretValidator()
    
    workflows_valid = validator.validate_all()
    secrets_valid = secret_validator.validate()
    
    if workflows_valid and secrets_valid:
        console.print("\n[green][U+2713] All validations passed[/green]")
        return 0
    else:
        console.print("\n[red][U+2717] Validation failed[/red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())