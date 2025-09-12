#!/usr/bin/env python3

"""
parse-config.py
Reads JSON configuration files and outputs values for GitHub Actions workflow use
ACT compatible - follows patterns from MASTER_GITHUB_WORKFLOW.xml
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional


def is_act_environment() -> bool:
    """Detect if running in ACT local environment"""
    return os.getenv('ACT') == 'true' or os.getenv('ACT_DETECTION') == 'true'


def print_act_debug() -> None:
    """Print ACT debug information if in ACT environment"""
    if is_act_environment():
        print("[U+1F9EA] ACT LOCAL RUN DETECTED", file=sys.stderr)
        print("Debug: Python config parser starting", file=sys.stderr)
        print("=========================", file=sys.stderr)


def load_json_file(file_path: str) -> Dict[str, Any]:
    """
    Load JSON configuration file with error handling
    
    Args:
        file_path: Path to JSON file
        
    Returns:
        Dictionary containing JSON data
        
    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file contains invalid JSON
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        if is_act_environment():
            print(f"[U+1F9EA] ACT: Config file not found: {file_path}", file=sys.stderr)
            return create_mock_config(file_path)
        raise
    except json.JSONDecodeError as e:
        print(f" FAIL:  Invalid JSON in {file_path}: {e}", file=sys.stderr)
        raise


def create_mock_config(file_path: str) -> Dict[str, Any]:
    """Create mock configuration data for ACT testing"""
    filename = os.path.basename(file_path)
    
    if 'settings' in filename or 'nonexistent' in filename:
        return {
            "test_runner": {
                "default_level": "unit",
                "timeout_minutes": 30,
                "retry_failed": True,
                "max_retries": 2
            },
            "deployment": {
                "auto_deploy_branches": ["main", "develop"],
                "require_approval": ["production"],
                "cleanup_on_pr_close": True
            },
            "notifications": {
                "channels": ["slack", "pr_comment"],
                "on_failure": "always",
                "on_success": "pr_only"
            },
            "_mock": True
        }
    elif 'features' in filename:
        return {
            "enable_staging_deploy": True,
            "enable_production_deploy": False,
            "enable_security_scan": True,
            "enable_performance_tests": False,
            "enable_notifications": {
                "slack": True,
                "email": False,
                "pr_comments": True
            },
            "_mock": True
        }
    elif 'environments' in filename:
        return {
            "staging": {
                "url": "https://staging.example.com",
                "auto_deploy": True,
                "cleanup_hours": 24
            },
            "production": {
                "url": "https://production.example.com", 
                "auto_deploy": False,
                "cleanup_hours": 0
            },
            "_mock": True
        }
    else:
        return {"_mock": True}


def get_nested_value(data: Dict[str, Any], key_path: str) -> Any:
    """
    Get value from nested dictionary using dot notation
    
    Args:
        data: Dictionary to search
        key_path: Dot-separated path (e.g., "notifications.slack")
        
    Returns:
        Value at the specified path, or None if not found
    """
    keys = key_path.split('.')
    current = data
    
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None
    
    return current


def format_output_value(value: Any) -> str:
    """
    Format value for GitHub Actions output
    
    Args:
        value: Value to format
        
    Returns:
        String representation suitable for GitHub Actions
    """
    if isinstance(value, bool):
        return 'true' if value else 'false'
    elif isinstance(value, (list, dict)):
        return json.dumps(value, separators=(',', ':'))
    elif value is None:
        return ''
    else:
        return str(value)


def output_to_github_actions(key: str, value: Any) -> None:
    """
    Output value to GitHub Actions in the correct format
    
    Args:
        key: Output key name
        value: Value to output
    """
    formatted_value = format_output_value(value)
    
    # Output to GITHUB_OUTPUT file if available
    if 'GITHUB_OUTPUT' in os.environ:
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as f:
            f.write(f"{key}={formatted_value}\n")
    
    # Also print to stdout for debugging and ACT compatibility
    print(f"{key}={formatted_value}")


def main():
    """Main function to parse configuration and output values"""
    print_act_debug()
    
    parser = argparse.ArgumentParser(
        description='Parse JSON configuration files for GitHub Actions'
    )
    parser.add_argument(
        'config_file',
        help='Path to JSON configuration file'
    )
    parser.add_argument(
        'key_path',
        help='Dot-separated path to value (e.g., notifications.slack)'
    )
    parser.add_argument(
        '--output-name',
        help='Name for the output variable (defaults to last part of key_path)'
    )
    parser.add_argument(
        '--default',
        help='Default value if key not found'
    )
    parser.add_argument(
        '--list-keys',
        action='store_true',
        help='List all available keys in the configuration file'
    )
    
    args = parser.parse_args()
    
    try:
        # Resolve file path relative to .github/workflows/config/
        if not os.path.isabs(args.config_file):
            base_dir = Path(__file__).parent.parent / 'workflows' / 'config'
            config_path = base_dir / args.config_file
        else:
            config_path = Path(args.config_file)
        
        print(f"[U+1F4D6] Loading config: {config_path}", file=sys.stderr)
        
        # Load configuration
        config_data = load_json_file(str(config_path))
        
        if is_act_environment() and config_data.get('_mock'):
            print("[U+1F9EA] ACT: Using mock configuration data", file=sys.stderr)
        
        # List keys if requested
        if args.list_keys:
            print("[U+1F4CB] Available configuration keys:", file=sys.stderr)
            print_keys(config_data)
            return
        
        # Get the requested value
        value = get_nested_value(config_data, args.key_path)
        
        if value is None and args.default is not None:
            value = args.default
            print(f" WARNING: [U+FE0F]  Key '{args.key_path}' not found, using default: {value}", file=sys.stderr)
        elif value is None:
            print(f" FAIL:  Key '{args.key_path}' not found and no default provided", file=sys.stderr)
            sys.exit(1)
        
        # Determine output name
        output_name = args.output_name or args.key_path.split('.')[-1]
        
        # Output the value
        output_to_github_actions(output_name, value)
        
        print(f" PASS:  Successfully parsed: {args.key_path} = {format_output_value(value)}", file=sys.stderr)
        
    except Exception as e:
        print(f" FAIL:  Error parsing configuration: {e}", file=sys.stderr)
        sys.exit(1)


def print_keys(data: Dict[str, Any], prefix: str = "") -> None:
    """
    Recursively print all available keys in a configuration
    
    Args:
        data: Dictionary to traverse
        prefix: Current key prefix for nested objects
    """
    for key, value in data.items():
        if key.startswith('_'):  # Skip internal keys like _mock
            continue
            
        current_path = f"{prefix}.{key}" if prefix else key
        
        if isinstance(value, dict):
            print(f"  [U+1F4C1] {current_path}/", file=sys.stderr)
            print_keys(value, current_path)
        else:
            value_type = type(value).__name__
            print(f"  [U+1F4C4] {current_path} ({value_type})", file=sys.stderr)


if __name__ == '__main__':
    main()