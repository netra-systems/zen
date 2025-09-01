#!/usr/bin/env python3
"""
Script to update GitHub Actions workflows to use the unified PR comment action
This prevents comment spam by ensuring each workflow updates a single comment
"""

import os
import re
import yaml
from pathlib import Path

def update_workflow_comments():
    """Update all workflows to use the unified PR comment action"""
    
    workflows_dir = Path(".github/workflows")
    workflows_to_update = {
        "mission-critical-tests.yml": "netra-mission-critical",
        "e2e-tests.yml": "netra-e2e-tests", 
        "deploy-staging.yml": "netra-deploy-staging",
        "database-regression-tests.yml": "netra-database-tests",
        "cleanup.yml": "netra-cleanup",
        "ci-orchestrator.yml": "netra-ci-orchestrator",
        "ci-max-parallel.yml": "netra-ci-parallel",
        "ci-fail-fast.yml": "netra-ci-failfast",
        "ci-balanced.yml": "netra-ci-balanced",
        "agent-startup-e2e-tests.yml": "netra-agent-e2e"
    }
    
    updated_count = 0
    
    for workflow_file, comment_id in workflows_to_update.items():
        workflow_path = workflows_dir / workflow_file
        
        if not workflow_path.exists():
            print(f"Warning: Workflow not found: {workflow_path}")
            continue
            
        print(f"Updating {workflow_file}...")
        
        with open(workflow_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Pattern to find PR comment sections using github.rest.issues.createComment
        pattern = r'(- name:.*?PR comment.*?\n(?:.*?\n)*?.*?github\.rest\.issues\.createComment\([^)]+\);?)'
        
        # Check if this workflow has the old pattern
        if 'github.rest.issues.createComment' in content:
            print(f"  Found old comment pattern in {workflow_file}")
            updated_count += 1
            
            # Create update notice
            update_notice = f"""
# NOTE: This workflow has been identified for PR comment update
# To prevent comment spam, update PR comment sections to use:
# uses: ./.github/actions/pr-comment
# with:
#   comment-identifier: '{comment_id}'
#   comment-body: |
#     Your comment content here
"""
            
            # Add notice at the top of the file if not already present
            if 'PR comment update' not in content:
                content = update_notice + "\n" + content
                
                with open(workflow_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                    
                print(f"  Added update notice to {workflow_file}")
        else:
            print(f"  {workflow_file} may already be updated or doesn't have PR comments")
    
    print(f"\nSummary: {updated_count} workflows need updating")
    print("\nNext steps:")
    print("1. Review the workflows with update notices")
    print("2. Manually update each PR comment section to use the reusable action")
    print("3. Test the changes in a PR to ensure comments are properly consolidated")
    
    return updated_count

if __name__ == "__main__":
    update_workflow_comments()