#!/usr/bin/env python3
"""
Validate workflow configuration and ensure all workflows can use it properly.
"""

import yaml
import json
import sys
from pathlib import Path
from typing import Dict, Any, List


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
            # Some workflows might use ubuntu-latest legitimately
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


def main():
    """Main validation function."""
    repo_root = Path(__file__).parent.parent
    config_path = repo_root / '.github' / 'workflow-config.yml'
    workflows_dir = repo_root / '.github' / 'workflows'
    
    print("=" * 60)
    print("WORKFLOW CONFIGURATION VALIDATION")
    print("=" * 60)
    
    # Check if config file exists
    if not config_path.exists():
        print(f"[FAIL] Configuration file not found: {config_path}")
        sys.exit(1)
    
    print(f"[OK] Configuration file found: {config_path}")
    
    # Load configuration
    try:
        config = load_config(config_path)
        print("[OK] Configuration loaded successfully")
    except Exception as e:
        print(f"[FAIL] Failed to load configuration: {e}")
        sys.exit(1)
    
    # Validate structure
    structure_errors = validate_config_structure(config)
    if structure_errors:
        print("\n[FAIL] Configuration structure errors:")
        for error in structure_errors:
            print(f"  - {error}")
    else:
        print("[OK] Configuration structure is valid")
    
    # Check workflow references
    workflow_issues = check_workflow_references(workflows_dir, config)
    if workflow_issues:
        print("\n[WARN] Workflow reference issues:")
        for issue in workflow_issues:
            print(f"  - {issue}")
    else:
        print("[OK] All workflows properly configured")
    
    # Validate runner consistency
    runner_issues = validate_runner_consistency(config)
    if runner_issues:
        print("\n[FAIL] Runner configuration issues:")
        for issue in runner_issues:
            print(f"  - {issue}")
    else:
        print("[OK] Runner configuration is consistent")
    
    # Print summary
    print("\n" + "=" * 60)
    print("CONFIGURATION SUMMARY")
    print("=" * 60)
    print(f"Runner Type: {config['global']['runners']['custom']}")
    print(f"Python Version: {config['global']['versions']['python']}")
    print(f"Node Version: {config['global']['versions']['node']}")
    print(f"Test Timeouts: Smoke={config['timeouts']['smoke']}m, "
          f"Unit={config['timeouts']['unit']}m, "
          f"Integration={config['timeouts']['integration']}m")
    print(f"Unit Test Shards: {', '.join(config['testing']['shards']['unit'])}")
    print(f"Cost Budget: ${config['monitoring']['health']['cost_budget_daily']}/day, "
          f"${config['monitoring']['health']['cost_budget_monthly']}/month")
    
    # Exit with appropriate code
    total_issues = len(structure_errors) + len(workflow_issues) + len(runner_issues)
    if total_issues == 0:
        print("\n[SUCCESS] All validations passed!")
        sys.exit(0)
    else:
        print(f"\n[WARN] Found {total_issues} total issues")
        sys.exit(1 if structure_errors else 0)


if __name__ == "__main__":
    main()