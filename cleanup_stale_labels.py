#!/usr/bin/env python3
"""
Script to remove 'actively-being-worked-on' labels from GitHub issues
that haven't been updated in more than 20 minutes.
"""

import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta

def run_gh_command(cmd):
    """Run a gh command and return the output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command '{cmd}': {e}")
        print(f"stderr: {e.stderr}")
        return None

def parse_datetime(dt_string):
    """Parse ISO datetime string to datetime object"""
    return datetime.fromisoformat(dt_string.replace('Z', '+00:00'))

def should_remove_label(updated_at_str, current_time, threshold_minutes=20):
    """Check if an issue should have its label removed"""
    updated_at = parse_datetime(updated_at_str)
    time_diff = current_time - updated_at
    return time_diff > timedelta(minutes=threshold_minutes)

def main():
    # Get current time
    current_time = datetime.now(timezone.utc)
    print(f"Current time: {current_time.isoformat()}")
    print(f"Checking for issues updated more than 20 minutes ago...")
    print()
    
    # Get all issues with the label
    cmd = 'gh issue list --label "actively-being-worked-on" --json number,title,updatedAt,url --limit 100'
    output = run_gh_command(cmd)
    
    if not output:
        print("Failed to get issues list")
        return 1
    
    try:
        issues = json.loads(output)
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON: {e}")
        return 1
    
    print(f"Found {len(issues)} issues with 'actively-being-worked-on' label")
    print()
    
    issues_to_clean = []
    
    for issue in issues:
        issue_num = issue['number']
        title = issue['title']
        updated_at = issue['updatedAt']
        url = issue['url']
        
        if should_remove_label(updated_at, current_time):
            updated_datetime = parse_datetime(updated_at)
            time_since_update = current_time - updated_datetime
            hours = int(time_since_update.total_seconds() // 3600)
            minutes = int((time_since_update.total_seconds() % 3600) // 60)
            
            issues_to_clean.append({
                'number': issue_num,
                'title': title,
                'updated_at': updated_at,
                'url': url,
                'time_since_update': f"{hours}h {minutes}m"
            })
            
            print(f"STALE: Issue #{issue_num} - Last updated {hours}h {minutes}m ago")
            print(f"  Title: {title}")
            print(f"  Updated: {updated_at}")
            print()
    
    if not issues_to_clean:
        print("No stale issues found - all issues have been updated within the last 20 minutes")
        return 0
    
    print(f"Found {len(issues_to_clean)} stale issues to clean up")
    print()
    
    # Remove labels from stale issues
    successful_removals = []
    failed_removals = []
    
    for issue in issues_to_clean:
        issue_num = issue['number']
        print(f"Removing label from issue #{issue_num}...")
        
        cmd = f'gh issue edit {issue_num} --remove-label "actively-being-worked-on"'
        result = run_gh_command(cmd)
        
        if result is not None:
            successful_removals.append(issue)
            print(f"  ✓ Successfully removed label from issue #{issue_num}")
        else:
            failed_removals.append(issue)
            print(f"  ✗ Failed to remove label from issue #{issue_num}")
        print()
    
    # Summary
    print("=" * 50)
    print("CLEANUP SUMMARY")
    print("=" * 50)
    print(f"Total issues checked: {len(issues)}")
    print(f"Issues needing cleanup: {len(issues_to_clean)}")
    print(f"Labels successfully removed: {len(successful_removals)}")
    print(f"Failed removals: {len(failed_removals)}")
    print()
    
    if successful_removals:
        print("Successfully cleaned up issues:")
        for issue in successful_removals:
            print(f"  - Issue #{issue['number']}: {issue['title']}")
            print(f"    Last updated: {issue['time_since_update']} ago")
            print(f"    URL: {issue['url']}")
            print()
    
    if failed_removals:
        print("Failed to clean up issues:")
        for issue in failed_removals:
            print(f"  - Issue #{issue['number']}: {issue['title']}")
            print(f"    URL: {issue['url']}")
            print()
    
    return 0 if not failed_removals else 1

if __name__ == "__main__":
    sys.exit(main())