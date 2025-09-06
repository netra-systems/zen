#!/usr/bin/env python3
"""
Simplified GitHub CI Monitor - Just monitors the existing runs
"""

import json
import subprocess
import time
import sys
from datetime import datetime

def run_gh_command(args):
    """Execute GitHub CLI command."""
    cmd = ["gh"] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr}")
        return ""

def monitor_workflow(repo="netra-systems/netra-apex", branch="critical-remediation-20250823"):
    """Monitor the latest workflow run."""
    print(f"[MONITOR] Monitoring workflows for {repo} on branch {branch}")
    print("="*60)
    
    workflow_id = 185743170  # Unified Test Pipeline
    last_status = {}
    
    while True:
        # Get latest runs
        output = run_gh_command([
            "run", "list", 
            "--workflow", str(workflow_id),
            "--repo", repo,
            "--branch", branch,
            "--limit", "5",
            "--json", "databaseId,status,conclusion,url,createdAt,displayTitle"
        ])
        
        if output:
            runs = json.loads(output)
            
            # Clear screen for clean display
            print("\033[2J\033[H")  # Clear screen and move cursor to top
            print(f"[MONITOR] GitHub Actions Status - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("="*80)
            
            for run in runs:
                run_id = run['databaseId']
                status = run['status']
                conclusion = run['conclusion'] or "pending"
                created = run['createdAt']
                title = run['displayTitle'][:50] + "..." if len(run['displayTitle']) > 50 else run['displayTitle']
                
                # Track status changes
                prev_status = last_status.get(run_id, {})
                status_changed = prev_status.get('status') != status or prev_status.get('conclusion') != conclusion
                
                # Format status with colors (using simple ASCII)
                if status == "completed":
                    if conclusion == "success":
                        status_str = "[SUCCESS]"
                    elif conclusion == "failure":
                        status_str = "[FAILED]"
                    else:
                        status_str = f"[{conclusion.upper()}]"
                elif status == "in_progress":
                    status_str = "[RUNNING]"
                elif status == "queued":
                    status_str = "[QUEUED]"
                else:
                    status_str = f"[{status.upper()}]"
                
                # Print run info
                change_marker = " *" if status_changed else ""
                print(f"{status_str:12} Run #{run_id}: {title}{change_marker}")
                print(f"            Created: {created}")
                print(f"            URL: {run['url']}")
                
                # If failed, fetch logs
                if status == "completed" and conclusion == "failure" and status_changed:
                    print(f"\n[LOGS] Fetching failure details for run #{run_id}...")
                    
                    # Get job details
                    job_output = run_gh_command([
                        "run", "view", str(run_id),
                        "--repo", repo,
                        "--json", "jobs"
                    ])
                    
                    if job_output:
                        jobs = json.loads(job_output).get('jobs', [])
                        failed_jobs = [j for j in jobs if j.get('conclusion') == 'failure']
                        
                        if failed_jobs:
                            print(f"[FAILED JOBS] Found {len(failed_jobs)} failed job(s):")
                            for job in failed_jobs[:3]:  # Show first 3 failed jobs
                                print(f"  - {job['name']}")
                                
                                # Get failure step
                                for step in job.get('steps', []):
                                    if step.get('conclusion') == 'failure':
                                        print(f"    Failed at step: {step.get('name', 'Unknown')}")
                                        break
                
                # Update last status
                last_status[run_id] = {'status': status, 'conclusion': conclusion}
                print()
            
            # Check if any run succeeded
            for run in runs:
                if run['status'] == 'completed' and run['conclusion'] == 'success':
                    print("\n" + "="*80)
                    print("[SUCCESS] Tests passed successfully!")
                    print(f"URL: {run['url']}")
                    return True
            
            # Check if we should trigger a new run
            latest_run = runs[0] if runs else None
            if latest_run:
                if latest_run['status'] == 'completed' and latest_run['conclusion'] == 'failure':
                    print("\n[ACTION NEEDED] Latest run failed. Review logs and apply fixes.")
                    print("To trigger a new run after fixes:")
                    print(f"  gh workflow run {workflow_id} --repo {repo} --ref {branch}")
        
        print(f"\nRefreshing in 30 seconds... (Press Ctrl+C to stop)")
        time.sleep(30)

def main():
    """Main entry point."""
    try:
        monitor_workflow()
    except KeyboardInterrupt:
        print("\n[STOPPED] Monitoring stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()