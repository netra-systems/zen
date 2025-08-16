#!/usr/bin/env python3
"""
Configuration parser for GitHub workflows.
Reads and processes JSON configuration files for use in GitHub Actions.
Implements variable hierarchy precedence as defined in MASTER_GITHUB_WORKFLOW.xml.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigParser:
    """Parses workflow configuration files with variable hierarchy support."""
    
    def __init__(self, config_dir: str = ".github/workflows/config"):
        """Initialize parser with configuration directory."""
        self.config_dir = Path(config_dir)
        self.configs = {}
        
    def load_config(self, filename: str) -> Dict[str, Any]:
        """Load a single configuration file."""
        config_path = self.config_dir / filename
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: Config file {filename} not found")
            return {}
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in {filename}: {e}")
            sys.exit(1)
            
    def load_all_configs(self) -> None:
        """Load all configuration files."""
        config_files = [
            "settings.json",
            "features.json", 
            "environments.json",
            "secrets-mapping.json"
        ]
        
        for filename in config_files:
            config_name = filename.replace('.json', '')
            self.configs[config_name] = self.load_config(filename)
            
    def get_value_with_hierarchy(self, key: str, environment: str = "development") -> Any:
        """
        Get configuration value applying variable hierarchy precedence:
        1. Workflow dispatch inputs (highest)
        2. Repository variables  
        3. Repository secrets
        4. Environment variables
        5. Configuration files
        6. Workflow defaults (lowest)
        """
        # Check environment variables first (since we can't access inputs/vars in script)
        env_value = os.getenv(key.upper())
        if env_value is not None:
            return env_value
            
        # Check configuration files
        # Try environment-specific config first
        if environment in self.configs.get('environments', {}):
            env_config = self.configs['environments'][environment]
            if key in env_config:
                return env_config[key]
                
        # Try settings config
        if key in self.configs.get('settings', {}):
            return self.configs['settings'][key]
            
        # Try features config
        if key in self.configs.get('features', {}):
            return self.configs['features'][key]
            
        return None
        
    def get_feature_flag(self, feature_name: str) -> bool:
        """Get feature flag value."""
        features = self.configs.get('features', {})
        return features.get(feature_name, False)
        
    def get_environment_config(self, environment: str) -> Dict[str, Any]:
        """Get complete environment configuration."""
        environments = self.configs.get('environments', {})
        return environments.get(environment, {})
        
    def get_secret_name(self, logical_name: str, environment: str) -> str:
        """Get actual secret name for environment."""
        secrets_mapping = self.configs.get('secrets-mapping', {})
        
        # Check environment-specific mapping
        env_secrets = secrets_mapping.get('environments', {}).get(environment, {})
        if logical_name in env_secrets:
            return env_secrets[logical_name]
            
        # Check shared secrets
        shared_secrets = secrets_mapping.get('shared', {})
        if logical_name in shared_secrets:
            return shared_secrets[logical_name]
            
        # Check notification channels
        notification_secrets = secrets_mapping.get('notification_channels', {})
        if logical_name in notification_secrets:
            return notification_secrets[logical_name]
            
        # Return as-is if not found
        return logical_name.upper()
        
    def output_github_env(self, key: str, value: Any) -> None:
        """Output variable for GitHub Actions environment."""
        github_env = os.getenv('GITHUB_ENV')
        if github_env:
            with open(github_env, 'a') as f:
                f.write(f"{key}={value}\n")
        else:
            print(f"{key}={value}")
            
    def output_github_output(self, key: str, value: Any) -> None:
        """Output variable for GitHub Actions step outputs.""" 
        github_output = os.getenv('GITHUB_OUTPUT')
        if github_output:
            with open(github_output, 'a') as f:
                f.write(f"{key}={value}\n")
        else:
            print(f"{key}={value}")


def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Parse workflow configuration')
    parser.add_argument('--config-dir', default='.github/workflows/config',
                       help='Configuration directory path')
    parser.add_argument('--environment', default='development', 
                       help='Target environment')
    parser.add_argument('--output-format', choices=['env', 'output', 'json'],
                       default='env', help='Output format')
    parser.add_argument('--key', help='Specific configuration key to retrieve')
    parser.add_argument('--feature', help='Feature flag to check')
    parser.add_argument('--secret', help='Secret name to resolve')
    
    args = parser.parse_args()
    
    config_parser = ConfigParser(args.config_dir)
    config_parser.load_all_configs()
    
    if args.feature:
        # Check feature flag
        enabled = config_parser.get_feature_flag(args.feature)
        if args.output_format == 'env':
            config_parser.output_github_env(f"FEATURE_{args.feature.upper()}", str(enabled).lower())
        elif args.output_format == 'output':
            config_parser.output_github_output(f"feature_{args.feature}", str(enabled).lower())
        else:
            print(json.dumps({f"feature_{args.feature}": enabled}))
            
    elif args.secret:
        # Resolve secret name
        secret_name = config_parser.get_secret_name(args.secret, args.environment)
        if args.output_format == 'env':
            config_parser.output_github_env(f"SECRET_{args.secret.upper()}", secret_name)
        elif args.output_format == 'output':
            config_parser.output_github_output(f"secret_{args.secret}", secret_name)
        else:
            print(json.dumps({f"secret_{args.secret}": secret_name}))
            
    elif args.key:
        # Get specific configuration value
        value = config_parser.get_value_with_hierarchy(args.key, args.environment)
        if value is not None:
            if args.output_format == 'env':
                config_parser.output_github_env(args.key.upper(), str(value))
            elif args.output_format == 'output':
                config_parser.output_github_output(args.key, str(value))
            else:
                print(json.dumps({args.key: value}))
        else:
            print(f"Configuration key '{args.key}' not found", file=sys.stderr)
            sys.exit(1)
            
    else:
        # Output all environment configuration
        env_config = config_parser.get_environment_config(args.environment)
        features = config_parser.configs.get('features', {})
        settings = config_parser.configs.get('settings', {})
        
        if args.output_format == 'json':
            output = {
                'environment': env_config,
                'features': features,
                'settings': settings
            }
            print(json.dumps(output, indent=2))
        else:
            # Output key environment variables for GitHub Actions
            for key, value in env_config.items():
                if isinstance(value, (str, int, bool)):
                    if args.output_format == 'env':
                        config_parser.output_github_env(f"ENV_{key.upper()}", str(value))
                    else:
                        config_parser.output_github_output(f"env_{key}", str(value))


if __name__ == "__main__":
    main()