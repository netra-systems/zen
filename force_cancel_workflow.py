#!/usr/bin/env python3
"""Force cancel stuck GitHub workflow."""

import os
import sys
import requests
from typing import Optional

def get_workflow_runs(token: str, owner: str, repo: str) -> list:
    """Get list of workflow runs."""
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Error fetching workflow runs: {response.status_code}")
        print(response.text)
        return []
    
    return response.json().get("workflow_runs", [])

def force_cancel_workflow(token: str, owner: str, repo: str, run_id: int) -> bool:
    """Force cancel a workflow run."""
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/force-cancel"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    print(f"Attempting to force cancel workflow run #{run_id}...")
    response = requests.post(url, headers=headers)
    
    if response.status_code == 202:
        print(f"✓ Successfully force-cancelled workflow run #{run_id}")
        return True
    elif response.status_code == 409:
        print(f"Workflow run #{run_id} is not in a state that can be cancelled")
        return False
    else:
        print(f"Error force-cancelling workflow: {response.status_code}")
        print(response.text)
        return False

def main():
    """Main function."""
    # Get GitHub token
    token = input("Enter your GitHub Personal Access Token (with 'actions:write' scope): ").strip()
    if not token:
        print("Error: GitHub token is required")
        sys.exit(1)
    
    owner = "netra-systems"
    repo = "netra-apex"
    
    # Get workflow runs
    print(f"\nFetching workflow runs for {owner}/{repo}...")
    runs = get_workflow_runs(token, owner, repo)
    
    if not runs:
        print("No workflow runs found")
        return
    
    # Find stuck workflows
    print("\nRecent workflow runs:")
    print("-" * 80)
    stuck_runs = []
    
    for i, run in enumerate(runs[:10]):
        status = run["status"]
        conclusion = run["conclusion"] or "in_progress"
        run_id = run["id"]
        run_number = run["run_number"]
        name = run["name"]
        created = run["created_at"]
        
        status_emoji = "🔄" if status == "in_progress" else "✓" if status == "completed" else "⏸"
        print(f"{i+1}. {status_emoji} Run #{run_number} (ID: {run_id})")
        print(f"   Name: {name}")
        print(f"   Status: {status} / {conclusion}")
        print(f"   Created: {created}")
        print()
        
        if status in ["in_progress", "queued", "waiting"]:
            stuck_runs.append((i+1, run_id, run_number, name))
    
    if not stuck_runs:
        print("No stuck workflows found!")
        return
    
    print("-" * 80)
    print(f"\nFound {len(stuck_runs)} potentially stuck workflow(s):")
    for idx, run_id, run_number, name in stuck_runs:
        print(f"  {idx}. Run #{run_number} - {name} (ID: {run_id})")
    
    # Ask which to cancel
    if len(stuck_runs) == 1:
        choice = input(f"\nForce cancel Run #{stuck_runs[0][2]}? (y/n): ").strip().lower()
        if choice == 'y':
            force_cancel_workflow(token, owner, repo, stuck_runs[0][1])
    else:
        choice = input("\nEnter the number of the workflow to force cancel (or 'all' for all): ").strip()
        if choice.lower() == 'all':
            for _, run_id, run_number, _ in stuck_runs:
                force_cancel_workflow(token, owner, repo, run_id)
        elif choice.isdigit():
            idx = int(choice)
            for list_idx, run_id, run_number, _ in stuck_runs:
                if list_idx == idx:
                    force_cancel_workflow(token, owner, repo, run_id)
                    break
            else:
                print(f"Invalid choice: {choice}")

if __name__ == "__main__":
    main()