#!/usr/bin/env python3
"""Force cancel stuck GitHub workflow."""

import os
import sys
from typing import List, Optional, Tuple

import requests


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
        print(f"[U+2713] Successfully force-cancelled workflow run #{run_id}")
        return True
    elif response.status_code == 409:
        print(f"Workflow run #{run_id} is not in a state that can be cancelled")
        return False
    else:
        print(f"Error force-cancelling workflow: {response.status_code}")
        print(response.text)
        return False

def _get_github_token() -> str:
    """Get GitHub token from user input with validation."""
    token = input("Enter your GitHub Personal Access Token (with 'actions:write' scope): ").strip()
    if not token:
        print("Error: GitHub token is required")
        sys.exit(1)
    return token

def _display_and_find_stuck_runs(runs: list) -> List[Tuple[int, int, int, str]]:
    """Display workflow runs and identify stuck ones."""
    print("\nRecent workflow runs:")
    print("-" * 80)
    stuck_runs = []
    for i, run in enumerate(runs[:10]):
        status, conclusion, run_id, run_number, name, created = _extract_run_info(run)
        _print_run_info(i, status, conclusion, run_id, run_number, name, created)
        if status in ["in_progress", "queued", "waiting"]:
            stuck_runs.append((i+1, run_id, run_number, name))
    return stuck_runs

def _extract_run_info(run: dict) -> Tuple[str, str, int, int, str, str]:
    """Extract run information from workflow run data."""
    status = run["status"]
    conclusion = run["conclusion"] or "in_progress"
    run_id = run["id"]
    run_number = run["run_number"]
    name = run["name"]
    created = run["created_at"]
    return status, conclusion, run_id, run_number, name, created

def _print_run_info(i: int, status: str, conclusion: str, run_id: int, run_number: int, name: str, created: str) -> None:
    """Print formatted run information."""
    status_emoji = " CYCLE: " if status == "in_progress" else "[U+2713]" if status == "completed" else "[U+23F8]"
    print(f"{i+1}. {status_emoji} Run #{run_number} (ID: {run_id})")
    print(f"   Name: {name}")
    print(f"   Status: {status} / {conclusion}")
    print(f"   Created: {created}\n")

def _display_stuck_runs_summary(stuck_runs: List[Tuple[int, int, int, str]]) -> None:
    """Display summary of stuck workflow runs."""
    print("-" * 80)
    print(f"\nFound {len(stuck_runs)} potentially stuck workflow(s):")
    for idx, run_id, run_number, name in stuck_runs:
        print(f"  {idx}. Run #{run_number} - {name} (ID: {run_id})")

def _handle_cancellation_choice(stuck_runs: List[Tuple[int, int, int, str]], token: str, owner: str, repo: str) -> None:
    """Handle user choice for workflow cancellation."""
    if len(stuck_runs) == 1:
        _handle_single_workflow_choice(stuck_runs[0], token, owner, repo)
    else:
        _handle_multiple_workflow_choice(stuck_runs, token, owner, repo)

def _handle_single_workflow_choice(workflow: Tuple[int, int, int, str], token: str, owner: str, repo: str) -> None:
    """Handle cancellation choice for single workflow."""
    choice = input(f"\nForce cancel Run #{workflow[2]}? (y/n): ").strip().lower()
    if choice == 'y':
        force_cancel_workflow(token, owner, repo, workflow[1])

def _handle_multiple_workflow_choice(stuck_runs: List[Tuple[int, int, int, str]], token: str, owner: str, repo: str) -> None:
    """Handle cancellation choice for multiple workflows."""
    choice = input("\nEnter the number of the workflow to force cancel (or 'all' for all): ").strip()
    if choice.lower() == 'all':
        for _, run_id, run_number, _ in stuck_runs:
            force_cancel_workflow(token, owner, repo, run_id)
    elif choice.isdigit():
        _cancel_workflow_by_index(int(choice), stuck_runs, token, owner, repo)
    else:
        print(f"Invalid choice: {choice}")

def _cancel_workflow_by_index(idx: int, stuck_runs: List[Tuple[int, int, int, str]], token: str, owner: str, repo: str) -> None:
    """Cancel workflow by index selection."""
    for list_idx, run_id, run_number, _ in stuck_runs:
        if list_idx == idx:
            force_cancel_workflow(token, owner, repo, run_id)
            return
    print(f"Invalid choice: {idx}")

def main() -> None:
    """Main workflow cancellation orchestration function."""
    token = _get_github_token()
    owner, repo = "netra-systems", "netra-apex"
    print(f"\nFetching workflow runs for {owner}/{repo}...")
    runs = get_workflow_runs(token, owner, repo)
    if not runs:
        print("No workflow runs found")
        return
    stuck_runs = _display_and_find_stuck_runs(runs)
    if not stuck_runs:
        print("No stuck workflows found!")
        return
    _display_stuck_runs_summary(stuck_runs)
    _handle_cancellation_choice(stuck_runs, token, owner, repo)

if __name__ == "__main__":
    main()