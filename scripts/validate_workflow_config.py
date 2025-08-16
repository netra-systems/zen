#!/usr/bin/env python3
"""
Validate workflow configuration and ensure all workflows can use it properly.
"""

import yaml
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple


def load_config(config_path: Path) -> Dict[str, Any]:
    """Load and parse the workflow configuration file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def validate_config_structure(config: Dict[str, Any]) -> List[str]:
    """Validate the configuration structure."""
    errors = []
    required_sections = [
        'global', 'timeouts', 'testing', 'deployment', 
        'monitoring', 'ai', 'caching', 'security',
        'workflow_control', 'notifications', 'performance'
    ]
    
    for section in required_sections:
        if section not in config:
            errors.append(f"Missing required section: {section}")
    
    # Validate specific critical values
    if 'global' in config:
        if 'runners' not in config['global']:
            errors.append("Missing 'runners' in global section")
        elif 'custom' not in config['global']['runners']:
            errors.append("Missing 'custom' runner in global.runners")
        
        if 'versions' not in config['global']:
            errors.append("Missing 'versions' in global section")
    
    if 'timeouts' in config:
        required_timeouts = ['smoke', 'unit', 'integration', 'comprehensive']
        for timeout in required_timeouts:
            if timeout not in config['timeouts']:
                errors.append(f"Missing timeout for: {timeout}")
    
    if 'testing' in config:
        if 'shards' not in config['testing']:
            errors.append("Missing 'shards' in testing section")
        elif 'unit' not in config['testing']['shards']:
            errors.append("Missing 'unit' shards in testing.shards")
    
    return errors


def check_workflow_references(workflows_dir: Path, config: Dict[str, Any]) -> List[str]:
    """Check if workflows properly reference the configuration."""
    issues = []
    workflows = list(workflows_dir.glob('*.yml')) + list(workflows_dir.glob('*.yaml'))
    
    config_file_reference = 'CONFIG_FILE: .github/workflow-config.yml'
    runner_reference = 'warp-custom-default'
    
    for workflow_path in workflows:
        if workflow_path.name == 'workflow-config.yml':
            continue
            
        with open(workflow_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check if workflow uses the custom runner
        if runner_reference not in content and 'runs-on:' in content:
            # Some workflows might use warp-custom-default legitimately
            if workflow_path.name not in ['terraform-lock-cleanup.yml', 'gemini-pr-review.yml']:
                issues.append(f"{workflow_path.name}: Not using custom runner")
        
        # Check if orchestrator references config file
        if workflow_path.name == 'orchestrator.yml':
            if config_file_reference not in content:
                issues.append(f"{workflow_path.name}: Missing CONFIG_FILE reference")
    
    return issues


def validate_runner_consistency(config: Dict[str, Any]) -> List[str]:
    """Validate runner configurations are consistent."""
    issues = []
    
    custom_runner = config.get('global', {}).get('runners', {}).get('custom')
    if custom_runner != 'warp-custom-default':
        issues.append(f"Custom runner should be 'warp-custom-default', found: {custom_runner}")
    
    return issues


def main() -> None:
    """Main validation function."""
    repo_root = Path(__file__).parent.parent
    config_path = repo_root / '.github' / 'workflow-config.yml'
    workflows_dir = repo_root / '.github' / 'workflows'
    _print_header()
    config = _load_and_validate_config(config_path)
    issues = _run_validations(config, workflows_dir)
    _print_summary(config)
    _exit_with_status(issues)


def _print_header() -> None:
    """Print validation header."""
    print("=" * 60)
    print("WORKFLOW CONFIGURATION VALIDATION")
    print("=" * 60)


def _load_and_validate_config(config_path: Path) -> Dict[str, Any]:
    """Load and validate config file exists."""
    if not config_path.exists():
        print(f"[FAIL] Configuration file not found: {config_path}")
        sys.exit(1)
    print(f"[OK] Configuration file found: {config_path}")
    return _load_config_safely(config_path)


def _load_config_safely(config_path: Path) -> Dict[str, Any]:
    """Load configuration with error handling."""
    try:
        config = load_config(config_path)
        print("[OK] Configuration loaded successfully")
        return config
    except Exception as e:
        print(f"[FAIL] Failed to load configuration: {e}")
        sys.exit(1)


def _run_validations(config: Dict[str, Any], workflows_dir: Path) -> Tuple[List[str], List[str], List[str]]:
    """Run all validation checks."""
    structure_errors = _validate_structure_with_output(config)
    workflow_issues = _validate_workflows_with_output(config, workflows_dir)
    runner_issues = _validate_runners_with_output(config)
    return structure_errors, workflow_issues, runner_issues


def _validate_structure_with_output(config: Dict[str, Any]) -> List[str]:
    """Validate structure and print results."""
    structure_errors = validate_config_structure(config)
    if structure_errors:
        print("\n[FAIL] Configuration structure errors:")
        for error in structure_errors:
            print(f"  - {error}")
    else:
        print("[OK] Configuration structure is valid")
    return structure_errors


def _validate_workflows_with_output(config: Dict[str, Any], workflows_dir: Path) -> List[str]:
    """Validate workflows and print results."""
    workflow_issues = check_workflow_references(workflows_dir, config)
    if workflow_issues:
        print("\n[WARN] Workflow reference issues:")
        for issue in workflow_issues:
            print(f"  - {issue}")
    else:
        print("[OK] All workflows properly configured")
    return workflow_issues


def _validate_runners_with_output(config: Dict[str, Any]) -> List[str]:
    """Validate runner consistency and print results."""
    runner_issues = validate_runner_consistency(config)
    if runner_issues:
        print("\n[FAIL] Runner configuration issues:")
        for issue in runner_issues:
            print(f"  - {issue}")
    else:
        print("[OK] Runner configuration is consistent")
    return runner_issues


def _print_summary(config: Dict[str, Any]) -> None:
    """Print configuration summary."""
    print("\n" + "=" * 60)
    print("CONFIGURATION SUMMARY")
    print("=" * 60)
    _print_config_details(config)


def _print_config_details(config: Dict[str, Any]) -> None:
    """Print detailed configuration information."""
    print(f"Runner Type: {config.get('global', {}).get('runners', {}).get('custom', 'unknown')}")
    print(f"Python Version: {config.get('global', {}).get('versions', {}).get('python', 'unknown')}")
    print(f"Node Version: {config.get('global', {}).get('versions', {}).get('node', 'unknown')}")
    if 'timeouts' in config:
        print(f"Test Timeouts: Smoke={config['timeouts'].get('smoke', 'unknown')}m, "
              f"Unit={config['timeouts'].get('unit', 'unknown')}m, "
              f"Integration={config['timeouts'].get('integration', 'unknown')}m")
    if 'testing' in config and 'shards' in config['testing']:
        print(f"Unit Test Shards: {', '.join(config['testing']['shards'].get('unit', []))}")
    if 'monitoring' in config and 'health' in config['monitoring']:
        print(f"Cost Budget: ${config['monitoring']['health'].get('cost_budget_daily', 'unknown')}/day, "
              f"${config['monitoring']['health'].get('cost_budget_monthly', 'unknown')}/month")


def _exit_with_status(issues: Tuple[List[str], List[str], List[str]]) -> None:
    """Exit with appropriate status code."""
    structure_errors, workflow_issues, runner_issues = issues
    total_issues = len(structure_errors) + len(workflow_issues) + len(runner_issues)
    if total_issues == 0:
        print("\n[SUCCESS] All validations passed!")
        sys.exit(0)
    else:
        print(f"\n[WARN] Found {total_issues} total issues")
        sys.exit(1 if structure_errors else 0)


if __name__ == "__main__":
    main()