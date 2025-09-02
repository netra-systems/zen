from shared.isolated_environment import get_env
#!/usr/bin/env python3
"""Secure local secrets management for ACT testing."""

import base64
import getpass
import json
import os
from pathlib import Path
from typing import Dict, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

console = Console()


class LocalSecretsManager:
    """Manage secrets for local ACT testing."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.secrets_store = self.project_root / ".local_secrets"
        self.act_secrets = self.project_root / ".act.secrets"
        self.key_file = self.project_root / ".secrets.key"
        self._ensure_gitignore()
    
    def _ensure_gitignore(self) -> None:
        """Ensure secret files are in gitignore."""
        gitignore = self.project_root / ".gitignore"
        patterns = [".act.secrets", ".local_secrets", ".secrets.key", ".act.env"]
        self._add_to_gitignore(gitignore, patterns)
    
    def _add_to_gitignore(self, gitignore: Path, patterns: list) -> None:
        """Add patterns to gitignore if not present."""
        existing = set()
        if gitignore.exists():
            existing = set(gitignore.read_text().splitlines())
        
        to_add = [p for p in patterns if p not in existing]
        if to_add:
            with open(gitignore, "a") as f:
                f.write("\n# Local ACT secrets\n")
                for pattern in to_add:
                    f.write(f"{pattern}\n")
    
    def initialize(self) -> None:
        """Initialize secrets storage."""
        if not self.key_file.exists():
            self._generate_key()
            console.print("[green]Secrets storage initialized[/green]")
        else:
            console.print("[cyan]Secrets storage already initialized[/cyan]")
    
    def _generate_key(self) -> None:
        """Generate encryption key."""
        password = getpass.getpass("Enter master password: ")
        confirm = getpass.getpass("Confirm password: ")
        
        if password != confirm:
            console.print("[red]Passwords do not match[/red]")
            return
        
        key = self._derive_key(password)
        self.key_file.write_bytes(key)
        self.key_file.chmod(0o600)
    
    def _derive_key(self, password: str) -> bytes:
        """Derive encryption key from password."""
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'netra-act-secrets',
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def add_secret(self, name: str, value: Optional[str] = None) -> None:
        """Add or update a secret."""
        if value is None:
            value = Prompt.ask(f"Enter value for {name}", password=True)
        
        secrets = self._load_secrets()
        secrets[name] = value
        self._save_secrets(secrets)
        console.print(f"[green]Secret '{name}' saved[/green]")
    
    def _load_secrets(self) -> Dict[str, str]:
        """Load and decrypt secrets."""
        if not self.secrets_store.exists():
            return {}
        
        key = self._get_key()
        if not key:
            return {}
        
        fernet = Fernet(key)
        encrypted = self.secrets_store.read_bytes()
        decrypted = fernet.decrypt(encrypted)
        return json.loads(decrypted)
    
    def _save_secrets(self, secrets: Dict[str, str]) -> None:
        """Encrypt and save secrets."""
        key = self._get_key()
        if not key:
            console.print("[red]No encryption key found[/red]")
            return
        
        fernet = Fernet(key)
        data = json.dumps(secrets).encode()
        encrypted = fernet.encrypt(data)
        self.secrets_store.write_bytes(encrypted)
        self.secrets_store.chmod(0o600)
    
    def _get_key(self) -> Optional[bytes]:
        """Get encryption key."""
        if not self.key_file.exists():
            console.print("[red]Not initialized. Run 'init' first[/red]")
            return None
        return self.key_file.read_bytes()
    
    def list_secrets(self) -> None:
        """List all stored secrets."""
        secrets = self._load_secrets()
        if not secrets:
            console.print("[yellow]No secrets stored[/yellow]")
            return
        
        table = Table(title="Stored Secrets")
        table.add_column("Name", style="cyan")
        table.add_column("Status", style="green")
        
        for name in sorted(secrets.keys()):
            table.add_row(name, "✓ Configured")
        
        console.print(table)
    
    def export_for_act(self) -> None:
        """Export secrets to ACT format."""
        secrets = self._load_secrets()
        if not secrets:
            console.print("[yellow]No secrets to export[/yellow]")
            return
        
        self._write_act_secrets(secrets)
        console.print(f"[green]Exported {len(secrets)} secrets to .act.secrets[/green]")
    
    def _write_act_secrets(self, secrets: Dict[str, str]) -> None:
        """Write secrets in ACT format."""
        with open(self.act_secrets, "w") as f:
            for name, value in secrets.items():
                f.write(f"{name}={value}\n")
        self.act_secrets.chmod(0o600)
    
    def remove_secret(self, name: str) -> None:
        """Remove a secret."""
        secrets = self._load_secrets()
        if name not in secrets:
            console.print(f"[yellow]Secret '{name}' not found[/yellow]")
            return
        
        del secrets[name]
        self._save_secrets(secrets)
        console.print(f"[green]Secret '{name}' removed[/green]")
    
    def import_from_env(self) -> None:
        """Import secrets from environment variables."""
        env_vars = self._get_github_env_vars()
        if not env_vars:
            console.print("[yellow]No GitHub secrets found in environment[/yellow]")
            return
        
        self._import_env_vars(env_vars)
    
    def _get_github_env_vars(self) -> Dict[str, str]:
        """Get GitHub-related environment variables."""
        prefixes = ["GITHUB_", "NPM_", "DOCKER_", "AWS_", "GCP_"]
        env_vars = {}
        
        for key, value in os.environ.items():
            if any(key.startswith(p) for p in prefixes):
                env_vars[key] = value
        
        return env_vars
    
    def _import_env_vars(self, env_vars: Dict[str, str]) -> None:
        """Import environment variables as secrets."""
        secrets = self._load_secrets()
        count = 0
        
        for key, value in env_vars.items():
            if key not in secrets:
                secrets[key] = value
                count += 1
        
        self._save_secrets(secrets)
        console.print(f"[green]Imported {count} secrets from environment[/green]")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Local secrets manager")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    subparsers.add_parser("init", help="Initialize secrets storage")
    subparsers.add_parser("list", help="List stored secrets")
    subparsers.add_parser("export", help="Export to .act.secrets")
    subparsers.add_parser("import", help="Import from environment")
    
    add_parser = subparsers.add_parser("add", help="Add secret")
    add_parser.add_argument("name", help="Secret name")
    add_parser.add_argument("--value", help="Secret value")
    
    remove_parser = subparsers.add_parser("remove", help="Remove secret")
    remove_parser.add_argument("name", help="Secret name")
    
    args = parser.parse_args()
    manager = LocalSecretsManager()
    
    if args.command == "init":
        manager.initialize()
    elif args.command == "list":
        manager.list_secrets()
    elif args.command == "add":
        manager.add_secret(args.name, args.value)
    elif args.command == "remove":
        manager.remove_secret(args.name)
    elif args.command == "export":
        manager.export_for_act()
    elif args.command == "import":
        manager.import_from_env()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
