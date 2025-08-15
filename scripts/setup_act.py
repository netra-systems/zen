#!/usr/bin/env python3
"""Setup script for ACT local testing environment."""

import os
import platform
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def check_docker() -> bool:
    """Check if Docker is installed and running."""
    try:
        subprocess.run(["docker", "info"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def check_act() -> bool:
    """Check if ACT is installed."""
    try:
        subprocess.run(["act", "--version"], capture_output=True, check=True)
        return True
    except FileNotFoundError:
        return False


def install_act() -> bool:
    """Install ACT based on platform."""
    system = platform.system().lower()
    
    console.print("[cyan]Installing ACT...[/cyan]")
    
    if system == "darwin":
        # macOS
        cmd = ["brew", "install", "act"]
    elif system == "linux":
        # Linux
        cmd = ["sh", "-c", "curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash"]
    elif system == "windows":
        # Windows
        cmd = ["choco", "install", "act-cli"]
    else:
        console.print(f"[red]Unsupported platform: {system}[/red]")
        return False
    
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def create_config_files() -> None:
    """Create default configuration files."""
    project_root = Path(__file__).parent.parent
    
    # Create .act.secrets template
    secrets_file = project_root / ".act.secrets"
    if not secrets_file.exists():
        secrets_content = """# ACT Secrets Configuration
# Add your secrets here (this file is gitignored)
GITHUB_TOKEN=
NPM_TOKEN=
DOCKER_PASSWORD=
TEST_DATABASE_URL=sqlite:///test.db
TEST_REDIS_URL=redis://localhost:6379
"""
        secrets_file.write_text(secrets_content)
        secrets_file.chmod(0o600)
        console.print("[green]Created .act.secrets template[/green]")
    
    # Create .act.env template
    env_file = project_root / ".act.env"
    if not env_file.exists():
        env_content = """# ACT Environment Configuration
# Local testing settings
LOCAL_DEPLOY=true
ACT_VERBOSE=false
ACT_DRY_RUN=false
ACT_MOCK_SERVICES=true
ACT_SKIP_EXTERNAL=true
"""
        env_file.write_text(env_content)
        console.print("[green]Created .act.env template[/green]")
    
    # Update .gitignore
    gitignore = project_root / ".gitignore"
    patterns = [
        ".act.secrets",
        ".act.env",
        ".local_secrets",
        ".secrets.key",
        "act-results/",
        "/tmp/act-artifacts/"
    ]
    
    existing = set()
    if gitignore.exists():
        existing = set(gitignore.read_text().splitlines())
    
    to_add = [p for p in patterns if p not in existing]
    if to_add:
        with open(gitignore, "a") as f:
            f.write("\n# ACT Local Testing\n")
            for pattern in to_add:
                f.write(f"{pattern}\n")
        console.print("[green]Updated .gitignore[/green]")


def install_dependencies() -> None:
    """Install Python dependencies."""
    requirements = ["rich", "pyyaml", "cryptography"]
    
    console.print("[cyan]Installing Python dependencies...[/cyan]")
    
    for package in requirements:
        try:
            __import__(package)
        except ImportError:
            subprocess.run([sys.executable, "-m", "pip", "install", package], check=True)


def run_validation() -> bool:
    """Run workflow validation."""
    console.print("[cyan]Validating workflows...[/cyan]")
    
    try:
        result = subprocess.run(
            [sys.executable, "scripts/workflow_validator.py"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            console.print("[green]Workflow validation passed[/green]")
            return True
        else:
            console.print("[yellow]Some workflows have issues[/yellow]")
            console.print(result.stdout)
            return False
    except Exception as e:
        console.print(f"[red]Validation failed: {e}[/red]")
        return False


def main():
    """Main setup process."""
    console.print(Panel.fit(
        "[bold cyan]ACT Local Testing Setup[/bold cyan]\n"
        "Setting up your environment for local GitHub Actions testing",
        border_style="cyan"
    ))
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        # Check Docker
        task = progress.add_task("Checking Docker...", total=1)
        if not check_docker():
            console.print("[red]Docker is not running. Please start Docker Desktop.[/red]")
            console.print("Visit: https://www.docker.com/products/docker-desktop")
            return 1
        progress.update(task, completed=1)
        
        # Check/Install ACT
        task = progress.add_task("Checking ACT...", total=1)
        if not check_act():
            console.print("[yellow]ACT not found. Installing...[/yellow]")
            if not install_act():
                console.print("[red]Failed to install ACT[/red]")
                console.print("Manual installation: https://github.com/nektos/act")
                return 1
        progress.update(task, completed=1)
        
        # Install dependencies
        task = progress.add_task("Installing dependencies...", total=1)
        install_dependencies()
        progress.update(task, completed=1)
        
        # Create config files
        task = progress.add_task("Creating configuration files...", total=1)
        create_config_files()
        progress.update(task, completed=1)
        
        # Run validation
        task = progress.add_task("Validating workflows...", total=1)
        run_validation()
        progress.update(task, completed=1)
    
    console.print("\n" + Panel.fit(
        "[bold green]Setup Complete![/bold green]\n\n"
        "Next steps:\n"
        "1. Edit .act.secrets with your secrets\n"
        "2. Run: python scripts/act_wrapper.py list\n"
        "3. Test: python scripts/act_wrapper.py run test-smoke\n\n"
        "Documentation: docs/ACT_LOCAL_TESTING_GUIDE.md",
        border_style="green"
    ))
    
    return 0


if __name__ == "__main__":
    sys.exit(main())