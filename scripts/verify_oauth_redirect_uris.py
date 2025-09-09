#!/usr/bin/env python3
"""
Verify OAuth Redirect URIs Configuration
Lists all required OAuth redirect URIs for Google Cloud Console configuration
"""

import json
import sys

# Fix Windows Unicode issues
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console(force_terminal=True if sys.platform == 'win32' else None)

def main():
    """Display required OAuth redirect URIs for different environments."""
    
    console.print("\n[bold cyan]OAuth Redirect URIs Configuration Guide[/bold cyan]\n")
    
    # Define URIs for different environments
    environments = {
        "Local Development": {
            "base_url": "http://localhost",
            "auth_port": "8081",
            "backend_port": "8000",
            "frontend_port": "3000",
            "uris": [
                "http://localhost:8081/auth/google/callback",
                "http://localhost:8000/auth/google/callback",
                "http://localhost:3000/auth/callback",
                "http://127.0.0.1:8081/auth/google/callback",
                "http://127.0.0.1:8000/auth/google/callback",
                "http://127.0.0.1:3000/auth/callback",
            ]
        },
        "GCP Staging": {
            "base_url": "https://",
            "services": {
                "auth": "auth.staging.netrasystems.ai",
                "backend": "api.staging.netrasystems.ai",
                "frontend": "app.staging.netrasystems.ai"
            },
            "uris": [
                "https://auth.staging.netrasystems.ai/auth/google/callback",
                "https://api.staging.netrasystems.ai/auth/google/callback",
                "https://app.staging.netrasystems.ai/auth/callback",
                # Legacy Cloud Run URLs (can be removed after migration)
                "https://netra-auth-service-cpbplcdz7q-uc.a.run.app/auth/google/callback",
                "https://api.staging.netrasystems.ai/auth/google/callback",
                "https://app.staging.netrasystems.ai/auth/callback",
            ]
        },
        "Production (Future)": {
            "domains": [
                "netrasystems.ai",
                "app.netrasystems.ai", 
                "api.netrasystems.ai",
                "auth.netrasystems.ai"
            ],
            "uris": [
                "https://auth.netrasystems.ai/auth/google/callback",
                "https://api.netrasystems.ai/auth/google/callback",
                "https://app.netrasystems.ai/auth/callback",
                "https://netrasystems.ai/auth/callback"
            ]
        }
    }
    
    # Display each environment
    for env_name, env_config in environments.items():
        table = Table(title=f"[bold]{env_name}[/bold]", show_header=True, header_style="bold magenta")
        table.add_column("Redirect URI", style="cyan", no_wrap=False)
        table.add_column("Purpose", style="green")
        
        for uri in env_config.get("uris", []):
            purpose = ""
            if "/auth/google/callback" in uri:
                purpose = "Auth Service OAuth Callback"
            elif "/auth/google/callback" in uri:
                purpose = "Backend API OAuth Proxy"
            elif "/auth/callback" in uri:
                purpose = "Frontend OAuth Callback"
            
            table.add_row(uri, purpose)
        
        console.print(table)
        console.print()
    
    # Instructions
    instructions = """
[bold yellow]How to Configure in Google Cloud Console:[/bold yellow]

1. Go to: https://console.cloud.google.com/apis/credentials
2. Select your OAuth 2.0 Client ID
3. Under "Authorized redirect URIs", add ALL URIs for your environment
4. Click "Save"

[bold red]Important Notes:[/bold red]
- ALL redirect URIs must be added exactly as shown
- Include both http://localhost and http://127.0.0.1 for local development
- The auth service handles the actual OAuth flow
- The backend proxies requests to the auth service
- The frontend receives the final token after redirect

[bold green]OAuth Configuration:[/bold green]
Configure your OAuth 2.0 Client ID with the redirect URIs above
    """
    
    console.print(Panel(instructions, title="Configuration Instructions", border_style="blue"))
    
    # Check current configuration
    console.print("\n[bold cyan]Current Service URLs (GCP Staging):[/bold cyan]")
    service_table = Table(show_header=True, header_style="bold")
    service_table.add_column("Service", style="cyan")
    service_table.add_column("URL", style="green")
    
    service_table.add_row("Auth Service", "https://netra-auth-service-cpbplcdz7q-uc.a.run.app")
    service_table.add_row("Backend API", "https://api.staging.netrasystems.ai")
    service_table.add_row("Frontend", "https://app.staging.netrasystems.ai")
    
    console.print(service_table)
    
    # Export to JSON
    export_data = {
        "oauth_client_id": "Configure in Google Cloud Console",
        "environments": environments,
        "staging_urls": {
            "auth_service": "https://netra-auth-service-cpbplcdz7q-uc.a.run.app",
            "backend": "https://api.staging.netrasystems.ai",
            "frontend": "https://app.staging.netrasystems.ai"
        }
    }
    
    with open("oauth_redirect_uris.json", "w") as f:
        json.dump(export_data, f, indent=2)
    
    console.print("\n[green]✓[/green] Configuration exported to oauth_redirect_uris.json")

if __name__ == "__main__":
    main()