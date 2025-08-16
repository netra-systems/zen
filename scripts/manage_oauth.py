#!/usr/bin/env python3
"""
OAuth client management script for Netra platform.
Handles OAuth configuration across different environments.
"""

import os
import sys
import json
import argparse
from typing import Dict, List, Optional
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.logging_config import central_logger as logger


class OAuthManager:
    """Manages OAuth clients across environments."""
    
    def __init__(self, project_id: str, service_account_path: Optional[str] = None):
        self.project_id = project_id
        self.service = None
        
        if service_account_path and os.path.exists(service_account_path):
            self.credentials = service_account.Credentials.from_service_account_file(
                service_account_path,
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )
            self.service = build('iap', 'v1', credentials=self.credentials)
    
    def add_pr_redirect_uri(self, pr_number: int, client_id: str) -> bool:
        """Add redirect URIs for a new PR environment."""
        if not self.service:
            logger.error("Google API service not initialized")
            return False
        
        redirect_uris = [
            f"https://pr-{pr_number}.staging.netrasystems.ai/api/auth/callback",
            f"https://pr-{pr_number}-api.staging.netrasystems.ai/auth/callback",
        ]
        
        origins = [
            f"https://pr-{pr_number}.staging.netrasystems.ai",
            f"https://pr-{pr_number}-api.staging.netrasystems.ai",
        ]
        
        try:
            # Get current OAuth client configuration
            client_name = f"projects/{self.project_id}/brands/default/identityAwareProxyClients/{client_id}"
            client = self.service.projects().brands().identityAwareProxyClients().get(
                name=client_name
            ).execute()
            
            # Update redirect URIs
            current_redirects = client.get('redirectUris', [])
            current_origins = client.get('authorizedJavaScriptOrigins', [])
            
            client['redirectUris'] = list(set(current_redirects + redirect_uris))
            client['authorizedJavaScriptOrigins'] = list(set(current_origins + origins))
            
            # Update the client
            self.service.projects().brands().identityAwareProxyClients().update(
                name=client_name,
                body=client
            ).execute()
            
            logger.info(f"Successfully added OAuth URIs for PR #{pr_number}")
            return True
            
        except HttpError as e:
            logger.error(f"Failed to add OAuth URIs: {e}")
            return False
    
    def remove_pr_redirect_uri(self, pr_number: int, client_id: str) -> bool:
        """Remove redirect URIs when PR is closed."""
        if not self.service:
            logger.error("Google API service not initialized")
            return False
        
        pr_patterns = [
            f"https://pr-{pr_number}",
            f"https://pr-{pr_number}-api",
        ]
        
        try:
            # Get current OAuth client configuration
            client_name = f"projects/{self.project_id}/brands/default/identityAwareProxyClients/{client_id}"
            client = self.service.projects().brands().identityAwareProxyClients().get(
                name=client_name
            ).execute()
            
            # Filter out PR-specific URIs
            current_redirects = client.get('redirectUris', [])
            current_origins = client.get('authorizedJavaScriptOrigins', [])
            
            client['redirectUris'] = [
                uri for uri in current_redirects
                if not any(pattern in uri for pattern in pr_patterns)
            ]
            client['authorizedJavaScriptOrigins'] = [
                origin for origin in current_origins
                if not any(pattern in origin for pattern in pr_patterns)
            ]
            
            # Update the client
            self.service.projects().brands().identityAwareProxyClients().update(
                name=client_name,
                body=client
            ).execute()
            
            logger.info(f"Successfully removed OAuth URIs for PR #{pr_number}")
            return True
            
        except HttpError as e:
            logger.error(f"Failed to remove OAuth URIs: {e}")
            return False
    
    def list_redirect_uris(self, client_id: str) -> Optional[Dict]:
        """List current redirect URIs for a client."""
        if not self.service:
            logger.error("Google API service not initialized")
            return None
        
        try:
            client_name = f"projects/{self.project_id}/brands/default/identityAwareProxyClients/{client_id}"
            client = self.service.projects().brands().identityAwareProxyClients().get(
                name=client_name
            ).execute()
            
            return {
                'redirect_uris': client.get('redirectUris', []),
                'javascript_origins': client.get('authorizedJavaScriptOrigins', []),
            }
            
        except HttpError as e:
            logger.error(f"Failed to list OAuth URIs: {e}")
            return None


class LocalOAuthConfig:
    """Manages local OAuth configuration without Google API."""
    
    def __init__(self):
        self.config_file = Path(__file__).parent.parent / "oauth_config.json"
        self.config = self.load_config()
    
    def load_config(self) -> Dict:
        """Load OAuth configuration from file."""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {
            'development': {},
            'testing': {},
            'staging': {},
            'production': {},
        }
    
    def save_config(self):
        """Save OAuth configuration to file."""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def set_client_id(self, environment: str, client_id: str):
        """Set OAuth client ID for an environment."""
        if environment not in self.config:
            self.config[environment] = {}
        self.config[environment]['client_id'] = client_id
        self.save_config()
        logger.info(f"Set OAuth client ID for {environment}")
    
    def set_client_secret(self, environment: str, client_secret: str):
        """Set OAuth client secret for an environment."""
        if environment not in self.config:
            self.config[environment] = {}
        self.config[environment]['client_secret'] = client_secret
        self.save_config()
        logger.info(f"Set OAuth client secret for {environment}")
    
    def get_config(self, environment: str) -> Dict:
        """Get OAuth configuration for an environment."""
        return self.config.get(environment, {})
    
    def generate_env_file(self, environment: str, output_path: Optional[str] = None):
        """Generate environment file with OAuth configuration."""
        config = self.get_config(environment)
        if not config:
            logger.error(f"No configuration found for {environment}")
            return
        
        env_content = []
        env_suffix = environment.upper()
        
        if 'client_id' in config:
            env_content.append(f"GOOGLE_OAUTH_CLIENT_ID_{env_suffix}={config['client_id']}")
        if 'client_secret' in config:
            env_content.append(f"GOOGLE_OAUTH_CLIENT_SECRET_{env_suffix}={config['client_secret']}")
        
        if output_path:
            with open(output_path, 'w') as f:
                f.write('\n'.join(env_content))
            logger.info(f"Generated env file at {output_path}")
        else:
            print('\n'.join(env_content))


def create_main_parser() -> argparse.ArgumentParser:
    """Create main argument parser with all subcommands."""
    parser = argparse.ArgumentParser(description='Manage OAuth configuration for Netra platform')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    _add_pr_subcommands(subparsers)
    _add_config_subcommands(subparsers)
    return parser


def _add_pr_subcommands(subparsers) -> None:
    """Add PR-related subcommands."""
    _add_pr_add_command(subparsers)
    _add_pr_remove_command(subparsers)
    _add_pr_list_command(subparsers)


def _add_pr_add_command(subparsers) -> None:
    """Add 'add-pr' subcommand."""
    add_pr_parser = subparsers.add_parser('add-pr', help='Add redirect URIs for PR environment')
    add_pr_parser.add_argument('pr_number', type=int, help='PR number')
    add_pr_parser.add_argument('--client-id', required=True, help='OAuth client ID')
    add_pr_parser.add_argument('--project-id', help='Google Cloud project ID')
    add_pr_parser.add_argument('--service-account', help='Path to service account JSON')


def _add_pr_remove_command(subparsers) -> None:
    """Add 'remove-pr' subcommand."""
    remove_pr_parser = subparsers.add_parser('remove-pr', help='Remove redirect URIs for PR environment')
    remove_pr_parser.add_argument('pr_number', type=int, help='PR number')
    remove_pr_parser.add_argument('--client-id', required=True, help='OAuth client ID')
    remove_pr_parser.add_argument('--project-id', help='Google Cloud project ID')
    remove_pr_parser.add_argument('--service-account', help='Path to service account JSON')


def _add_pr_list_command(subparsers) -> None:
    """Add 'list' subcommand."""
    list_parser = subparsers.add_parser('list', help='List current redirect URIs')
    list_parser.add_argument('--client-id', required=True, help='OAuth client ID')
    list_parser.add_argument('--project-id', help='Google Cloud project ID')
    list_parser.add_argument('--service-account', help='Path to service account JSON')


def _add_config_subcommands(subparsers) -> None:
    """Add configuration-related subcommands."""
    _add_set_client_id_command(subparsers)
    _add_set_client_secret_command(subparsers)
    _add_generate_env_command(subparsers)


def _add_set_client_id_command(subparsers) -> None:
    """Add 'set-client-id' subcommand."""
    set_id_parser = subparsers.add_parser('set-client-id', help='Set OAuth client ID for environment')
    set_id_parser.add_argument('environment', choices=['development', 'testing', 'staging', 'production'])
    set_id_parser.add_argument('client_id', help='OAuth client ID')


def _add_set_client_secret_command(subparsers) -> None:
    """Add 'set-client-secret' subcommand."""
    set_secret_parser = subparsers.add_parser('set-client-secret', help='Set OAuth client secret for environment')
    set_secret_parser.add_argument('environment', choices=['development', 'testing', 'staging', 'production'])
    set_secret_parser.add_argument('client_secret', help='OAuth client secret')


def _add_generate_env_command(subparsers) -> None:
    """Add 'generate-env' subcommand."""
    gen_env_parser = subparsers.add_parser('generate-env', help='Generate environment file')
    gen_env_parser.add_argument('environment', choices=['development', 'testing', 'staging', 'production'])
    gen_env_parser.add_argument('--output', help='Output file path')


def handle_google_api_commands(args: argparse.Namespace) -> None:
    """Handle commands that use Google API."""
    if not args.project_id:
        logger.error("Project ID is required for Google API operations")
        return
    manager = OAuthManager(args.project_id, args.service_account)
    _execute_google_api_command(manager, args)


def _execute_google_api_command(manager: OAuthManager, args: argparse.Namespace) -> None:
    """Execute specific Google API command."""
    if args.command == 'add-pr':
        success = manager.add_pr_redirect_uri(args.pr_number, args.client_id)
        sys.exit(0 if success else 1)
    elif args.command == 'remove-pr':
        success = manager.remove_pr_redirect_uri(args.pr_number, args.client_id)
        sys.exit(0 if success else 1)
    elif args.command == 'list':
        _handle_list_command(manager, args)


def _handle_list_command(manager: OAuthManager, args: argparse.Namespace) -> None:
    """Handle list redirect URIs command."""
    uris = manager.list_redirect_uris(args.client_id)
    if uris:
        print(json.dumps(uris, indent=2))
    sys.exit(0 if uris else 1)


def handle_local_config_commands(args: argparse.Namespace) -> None:
    """Handle commands that use local configuration."""
    config = LocalOAuthConfig()
    if args.command == 'set-client-id':
        config.set_client_id(args.environment, args.client_id)
    elif args.command == 'set-client-secret':
        config.set_client_secret(args.environment, args.client_secret)
    elif args.command == 'generate-env':
        config.generate_env_file(args.environment, args.output)


def main():
    """Main entry point for OAuth management script."""
    parser = create_main_parser()
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return
    if args.command in ['add-pr', 'remove-pr', 'list']:
        handle_google_api_commands(args)
    else:
        handle_local_config_commands(args)


if __name__ == '__main__':
    main()