#!/usr/bin/env python3
"""GitHub workflow runs and artifacts cleanup script."""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def run_gh_command(args: List[str]) -> Dict[str, Any]:
    """Execute GitHub CLI command and return JSON output."""
    # Try to find gh in PATH first, then try common Windows locations
    gh_path = shutil.which("gh")
    if not gh_path and os.name == 'nt':
        # Check common Windows install locations
        possible_paths = [
            r"C:\Program Files\GitHub CLI\gh.exe",
            r"C:\Program Files (x86)\GitHub CLI\gh.exe"
        ]
        for path in possible_paths:
            if os.path.exists(path):
                gh_path = path
                break
    
    if not gh_path:
        print("GitHub CLI (gh) not found. Please install it first.")
        print("Install with: winget install --id GitHub.cli")
        sys.exit(1)
    
    cmd = [gh_path, "api"] + args
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True, encoding='utf-8'
        )
        return json.loads(result.stdout) if result.stdout else {}
    except subprocess.CalledProcessError as e:
        print(f"Error running gh command: {e.stderr}")
        return {}


def get_workflow_runs(
    repo: str, days_old: int, workflow_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Get workflow runs older than specified days."""
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
    
    endpoint = f"repos/{repo}/actions/runs"
    if workflow_id:
        endpoint = f"repos/{repo}/actions/workflows/{workflow_id}/runs"
    
    # Use per_page and iterate through pages manually
    old_runs = []
    page = 1
    while True:
        params = ["-X", "GET", f"{endpoint}?per_page=100&page={page}"]
        data = run_gh_command(params)
        
        if not data or "workflow_runs" not in data or not data["workflow_runs"]:
            break
        
        for run in data["workflow_runs"]:
            run_date = datetime.fromisoformat(
                run["created_at"].replace("Z", "+00:00")
            )
            if run_date < cutoff_date:
                old_runs.append(run)
        
        # If we got less than 100 results, we're on the last page
        if len(data["workflow_runs"]) < 100:
            break
        
        page += 1
    
    return old_runs


def delete_workflow_run(repo: str, run_id: int) -> bool:
    """Delete a specific workflow run."""
    endpoint = f"repos/{repo}/actions/runs/{run_id}"
    result = run_gh_command(["-X", "DELETE", endpoint])
    return result is not None


def get_artifacts(repo: str, days_old: int) -> List[Dict[str, Any]]:
    """Get artifacts older than specified days."""
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
    
    endpoint = f"repos/{repo}/actions/artifacts"
    
    # Use per_page and iterate through pages manually
    old_artifacts = []
    page = 1
    while True:
        params = ["-X", "GET", f"{endpoint}?per_page=100&page={page}"]
        data = run_gh_command(params)
        
        if not data or "artifacts" not in data or not data["artifacts"]:
            break
        
        for artifact in data["artifacts"]:
            created_date = datetime.fromisoformat(
                artifact["created_at"].replace("Z", "+00:00")
            )
            if created_date < cutoff_date:
                old_artifacts.append(artifact)
        
        # If we got less than 100 results, we're on the last page
        if len(data["artifacts"]) < 100:
            break
        
        page += 1
    
    return old_artifacts


def delete_artifact(repo: str, artifact_id: int) -> bool:
    """Delete a specific artifact."""
    endpoint = f"repos/{repo}/actions/artifacts/{artifact_id}"
    result = run_gh_command(["-X", "DELETE", endpoint])
    return result is not None


def clean_local_directories(
    root_path: Path, days_old: int, dry_run: bool = False
) -> int:
    """Clean local workflow-related directories."""
    directories_to_clean = [
        ".github/workflows/local-ACT-workflows",
        ".github/workflows/pending",
        "logs",
        "artifacts",
        ".act"
    ]
    
    cutoff_date = datetime.now() - timedelta(days=days_old)
    deleted_count = 0
    
    for dir_path in directories_to_clean:
        full_path = root_path / dir_path
        if not full_path.exists():
            continue
        
        for item in full_path.iterdir():
            try:
                stat = item.stat()
                mod_time = datetime.fromtimestamp(stat.st_mtime)
                
                if mod_time < cutoff_date:
                    if dry_run:
                        print(f"Would delete: {item}")
                    else:
                        if item.is_dir():
                            shutil.rmtree(item)
                        else:
                            item.unlink()
                        print(f"Deleted: {item}")
                    deleted_count += 1
            except Exception as e:
                print(f"Error processing {item}: {e}")
    
    return deleted_count


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Clean up old GitHub workflow runs and artifacts"
    )
    
    parser.add_argument(
        "--repo",
        help="Repository in format owner/repo (auto-detected if not provided)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Delete items older than this many days (default: 30)"
    )
    parser.add_argument(
        "--workflow-id",
        help="Specific workflow ID to clean (optional)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting"
    )
    parser.add_argument(
        "--local-only",
        action="store_true",
        help="Only clean local directories, skip GitHub API operations"
    )
    parser.add_argument(
        "--remote-only",
        action="store_true",
        help="Only clean remote GitHub runs, skip local directories"
    )
    parser.add_argument(
        "--keep-failed",
        action="store_true",
        help="Keep failed workflow runs for debugging"
    )
    
    return parser.parse_args()


def get_repo_from_git() -> Optional[str]:
    """Auto-detect repository from git remote."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True
        )
        url = result.stdout.strip()
        
        # Parse GitHub URL formats
        if "github.com" in url:
            if url.startswith("git@"):
                parts = url.split(":")[-1].replace(".git", "")
            else:
                parts = url.split("github.com/")[-1].replace(".git", "")
            return parts
    except subprocess.CalledProcessError:
        pass
    
    return None


def _setup_repository_detection(args):
    """Setup and detect repository if needed"""
    repo = args.repo
    if not repo and not args.local_only:
        repo = get_repo_from_git()
        if not repo:
            print("Could not auto-detect repository. Use --repo flag.")
            sys.exit(1)
        print(f"Auto-detected repository: {repo}")
    return repo

def _clean_workflow_runs(repo, args):
    """Clean old workflow runs and return deletion count"""
    old_runs = get_workflow_runs(repo, args.days, args.workflow_id)
    print(f"Found {len(old_runs)} old workflow runs")
    deleted_count = 0
    for run in old_runs:
        if args.keep_failed and run["conclusion"] == "failure":
            print(f"Keeping failed run: {run['id']}")
            continue
        if args.dry_run:
            print(f"Would delete run {run['id']} from {run['created_at']}")
        elif delete_workflow_run(repo, run["id"]):
            print(f"Deleted run {run['id']}")
            deleted_count += 1
    return deleted_count

def _clean_artifacts(repo, args):
    """Clean old artifacts and return deletion count"""
    print(f"\nCleaning artifacts older than {args.days} days...")
    old_artifacts = get_artifacts(repo, args.days)
    print(f"Found {len(old_artifacts)} old artifacts")
    deleted_count = 0
    for artifact in old_artifacts:
        if args.dry_run:
            print(f"Would delete artifact: {artifact['name']}")
        elif delete_artifact(repo, artifact["id"]):
            print(f"Deleted artifact: {artifact['name']}")
            deleted_count += 1
    return deleted_count

def _clean_remote_items(args, repo):
    """Clean remote GitHub runs and artifacts"""
    total_deleted = 0
    if not args.local_only and repo:
        print(f"\nCleaning GitHub runs older than {args.days} days...")
        total_deleted += _clean_workflow_runs(repo, args)
        total_deleted += _clean_artifacts(repo, args)
    return total_deleted

def _clean_local_items(args):
    """Clean local directories and return deletion count"""
    if args.remote_only: return 0
    print(f"\nCleaning local directories older than {args.days} days...")
    root_path = Path.cwd()
    local_deleted = clean_local_directories(root_path, args.days, args.dry_run)
    print(f"Cleaned {local_deleted} local items")
    return local_deleted

def _display_cleanup_summary(total_deleted, dry_run):
    """Display cleanup completion summary"""
    if dry_run:
        print(f"\nDry run complete. Would delete {total_deleted} items.")
    else:
        print(f"\nCleanup complete. Deleted {total_deleted} items.")

def main():
    """Main cleanup function."""
    args = parse_args()
    repo = _setup_repository_detection(args)
    total_deleted = 0
    total_deleted += _clean_remote_items(args, repo)
    total_deleted += _clean_local_items(args)
    _display_cleanup_summary(total_deleted, args.dry_run)


if __name__ == "__main__":
    main()