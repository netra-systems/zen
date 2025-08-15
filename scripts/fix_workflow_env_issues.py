#!/usr/bin/env python3
"""Fix GitHub Actions workflow environment variable issues."""

import os
import re
from pathlib import Path
from typing import List, Tuple


def fix_env_self_reference(content: str) -> str:
    """Fix env variables that self-reference in env section."""
    patterns = [
        (r'ACT: \$\{\{ env\.ACT \|\| \'false\' \}\}', "ACT: 'false'  # Will be overridden by ACT when running locally"),
        (r'IS_ACT: \$\{\{ env\.ACT \|\| \'false\' \}\}', "IS_ACT: 'false'  # Will be overridden by ACT when running locally"),
        (r'ACT_DETECTED: \$\{\{ env\.ACT \|\| \'false\' \}\}', "ACT_DETECTED: 'false'  # Will be overridden by ACT when running locally"),
        (r'ACT_DRY_RUN: \$\{\{ env\.ACT_DRY_RUN \|\| \'true\' \}\}', "ACT_DRY_RUN: 'true'  # Default value"),
        (r'ACT_MOCK_GCP: \$\{\{ env\.ACT_MOCK_GCP \|\| \'true\' \}\}', "ACT_MOCK_GCP: 'true'  # Default value"),
        (r'ACT_RUNNER_NAME: \$\{\{ env\.ACT && \'act-runner\' \|\| \'github-runner\' \}\}', "ACT_RUNNER_NAME: 'github-runner'  # Will be overridden by ACT when running locally"),
        (r'ACT_TEST_MODE: \$\{\{ env\.ACT \|\| \'false\' \}\}', "ACT_TEST_MODE: 'false'  # Will be overridden by ACT when running locally"),
        (r'LOCAL_DEPLOY: \$\{\{ env\.LOCAL_DEPLOY \|\| \'false\' \}\}', "LOCAL_DEPLOY: 'false'  # Default value"),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    return content


def fix_runs_on_conditionals(content: str) -> str:
    """Fix runs-on fields with invalid conditional syntax."""
    pattern = r'runs-on: \$\{\{ env\.ACT && \'ubuntu-latest\' \|\| \'warp-custom-default\' \}\}.*'
    replacement = "runs-on: warp-custom-default  # ACT will override this to ubuntu-latest when running locally"
    
    content = re.sub(pattern, replacement, content)
    
    return content


def fix_timeout_conditionals(content: str) -> str:
    """Fix timeout-minutes fields with invalid conditional syntax."""
    patterns = [
        (r'timeout-minutes: \$\{\{ env\.ACT && \'3\' \|\| \'5\' \}\}.*', "timeout-minutes: 5  # Adjusted for ACT compatibility"),
        (r'timeout-minutes: \$\{\{ env\.ACT && \'30\' \|\| \'60\' \}\}.*', "timeout-minutes: 60  # Adjusted for ACT compatibility"),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    return content


def process_workflow_file(filepath: Path) -> Tuple[bool, List[str]]:
    """Process a single workflow file."""
    changes = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        original_content = f.read()
    
    content = original_content
    
    # Apply fixes
    content = fix_env_self_reference(content)
    content = fix_runs_on_conditionals(content)
    content = fix_timeout_conditionals(content)
    
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Identify what was changed
        if 'ACT:' in original_content and 'ACT:' in content:
            if original_content.count('${{ env.ACT') != content.count('${{ env.ACT'):
                changes.append("Fixed env variable self-references")
        
        if 'runs-on:' in original_content:
            if original_content.count('runs-on: ${{ env.ACT') != content.count('runs-on: ${{ env.ACT'):
                changes.append("Fixed runs-on conditionals")
        
        if 'timeout-minutes:' in original_content:
            if original_content.count('timeout-minutes: ${{ env.ACT') != content.count('timeout-minutes: ${{ env.ACT'):
                changes.append("Fixed timeout-minutes conditionals")
        
        return True, changes
    
    return False, []


def main():
    """Main function to fix all workflow files."""
    workflows_dir = Path('.github/workflows')
    staging_workflows_dir = workflows_dir / 'staging-workflows'
    
    fixed_files = []
    
    # Process all workflow files
    for workflow_file in workflows_dir.glob('*.yml'):
        changed, changes = process_workflow_file(workflow_file)
        if changed:
            fixed_files.append((workflow_file.name, changes))
    
    # Process staging workflow files
    if staging_workflows_dir.exists():
        for workflow_file in staging_workflows_dir.glob('*.yml'):
            changed, changes = process_workflow_file(workflow_file)
            if changed:
                fixed_files.append((f"staging-workflows/{workflow_file.name}", changes))
    
    # Report results
    if fixed_files:
        print(f"Fixed {len(fixed_files)} workflow files:")
        for filename, changes in fixed_files:
            print(f"  - {filename}:")
            for change in changes:
                print(f"    * {change}")
    else:
        print("No workflow files needed fixing")
    
    return len(fixed_files)


if __name__ == '__main__':
    import sys
    sys.exit(0 if main() >= 0 else 1)