#!/usr/bin/env python3
"""
Clear Old Issue Locks

Removes "actively-being-worked-on" tags from GitHub issues if:
1) The last comment (or comment update time) was more than 20 minutes ago
AND
2) There is no recently added agent session tag

This prevents issues from being stuck in a "locked" state when work has stopped.
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
import re

class GitHubIssueLockCleaner:
    def __init__(self, repo: str = "netra-systems/netra-apex"):
        self.repo = repo
        self.lock_tag = "actively-being-worked-on"
        self.agent_session_pattern = r"agent-session-\d{4}-\d{2}-\d{2}-\d{6}"
        self.stale_threshold_minutes = 20

    def run_gh_command(self, args: List[str]) -> str:
        """Execute GitHub CLI command."""
        cmd = ["gh"] + args
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8')
            return result.stdout
        except subprocess.CalledProcessError as e:
            print(f"Error running gh command: {e}")
            print(f"STDERR: {e.stderr}")
            return ""

    def get_issues_with_lock_tag(self) -> List[Dict]:
        """Get all issues with the actively-being-worked-on tag."""
        print(f"[SEARCH] Finding issues with '{self.lock_tag}' tag...")

        output = self.run_gh_command([
            "issue", "list",
            "--repo", self.repo,
            "--label", self.lock_tag,
            "--state", "open",
            "--json", "number,title,labels,updatedAt,comments",
            "--limit", "100"
        ])

        if not output:
            print("No issues found or error occurred")
            return []

        issues = json.loads(output)
        print(f"[FOUND] {len(issues)} issues with '{self.lock_tag}' tag")
        return issues

    def get_issue_comments(self, issue_number: int) -> List[Dict]:
        """Get all comments for a specific issue."""
        output = self.run_gh_command([
            "issue", "view", str(issue_number),
            "--repo", self.repo,
            "--json", "comments"
        ])

        if not output:
            return []

        data = json.loads(output)
        return data.get("comments", [])

    def get_issue_labels(self, issue_number: int) -> List[str]:
        """Get current labels for an issue."""
        output = self.run_gh_command([
            "issue", "view", str(issue_number),
            "--repo", self.repo,
            "--json", "labels"
        ])

        if not output:
            return []

        data = json.loads(output)
        return [label["name"] for label in data.get("labels", [])]

    def has_recent_agent_session_tag(self, labels: List[str]) -> bool:
        """Check if issue has a recently added agent session tag."""
        for label in labels:
            if re.match(self.agent_session_pattern, label):
                # Extract timestamp from agent session tag
                match = re.search(r"(\d{4}-\d{2}-\d{2}-\d{6})", label)
                if match:
                    timestamp_str = match.group(1)
                    try:
                        # Parse timestamp: YYYY-MM-DD-HHMMSS
                        dt = datetime.strptime(timestamp_str, "%Y-%m-%d-%H%M%S")
                        time_diff = datetime.now() - dt

                        # Consider agent session recent if within 20 minutes
                        if time_diff <= timedelta(minutes=self.stale_threshold_minutes):
                            return True
                    except ValueError:
                        # If we can't parse the timestamp, assume it's recent to be safe
                        return True
        return False

    def get_last_activity_time(self, issue: Dict, comments: List[Dict]) -> datetime:
        """Get the time of the last activity (comment or issue update)."""
        times = []

        # Add issue update time
        if issue.get("updatedAt"):
            times.append(datetime.fromisoformat(issue["updatedAt"].replace("Z", "+00:00")))

        # Add comment times
        for comment in comments:
            if comment.get("updatedAt"):
                times.append(datetime.fromisoformat(comment["updatedAt"].replace("Z", "+00:00")))

        # Return the most recent time
        return max(times) if times else datetime.min.replace(tzinfo=None)

    def is_stale(self, last_activity: datetime) -> bool:
        """Check if the last activity is older than the threshold."""
        # Convert to UTC for comparison
        now = datetime.now()

        # Handle timezone-aware datetime
        if last_activity.tzinfo is not None:
            import pytz
            if now.tzinfo is None:
                now = pytz.UTC.localize(now)
        else:
            # Remove timezone info from last_activity if present
            last_activity = last_activity.replace(tzinfo=None)

        time_diff = now - last_activity
        return time_diff > timedelta(minutes=self.stale_threshold_minutes)

    def remove_lock_tag(self, issue_number: int) -> bool:
        """Remove the actively-being-worked-on tag from an issue."""
        print(f"[REMOVE] Removing '{self.lock_tag}' tag from issue #{issue_number}")

        result = self.run_gh_command([
            "issue", "edit", str(issue_number),
            "--repo", self.repo,
            "--remove-label", self.lock_tag
        ])

        return bool(result)

    def add_comment_about_lock_removal(self, issue_number: int, reason: str):
        """Add a comment explaining why the lock was removed."""
        comment_body = f"""**Automated Lock Removal**

The "actively-being-worked-on" tag has been automatically removed from this issue.

**Reason:** {reason}

**Policy:** Issues are automatically unlocked when:
- Last activity was more than {self.stale_threshold_minutes} minutes ago
- No recent agent session tags are present

The issue remains open and available for work. Feel free to add the tag back when actively working on it.

---
*Automated by `clear-old-issue-locks` script*"""

        self.run_gh_command([
            "issue", "comment", str(issue_number),
            "--repo", self.repo,
            "--body", comment_body
        ])

    def clear_old_locks(self, dry_run: bool = False) -> Dict[str, List[int]]:
        """Main function to clear old locks."""
        print(f"[START] Clearing old issue locks (threshold: {self.stale_threshold_minutes} minutes)")
        print(f"[MODE] {'DRY RUN' if dry_run else 'LIVE MODE'}")
        print("="*60)

        issues = self.get_issues_with_lock_tag()

        if not issues:
            print("[DONE] No issues with lock tags found")
            return {"removed": [], "kept": [], "errors": []}

        removed = []
        kept = []
        errors = []

        for issue in issues:
            issue_number = issue["number"]
            title = issue["title"][:50] + "..." if len(issue["title"]) > 50 else issue["title"]

            print(f"\n[CHECK] Issue #{issue_number}: {title}")

            try:
                # Get current labels (in case they changed)
                current_labels = self.get_issue_labels(issue_number)

                # Check if it still has the lock tag
                if self.lock_tag not in current_labels:
                    print(f"  [OK] Lock tag already removed")
                    continue

                # Check for recent agent session tags
                if self.has_recent_agent_session_tag(current_labels):
                    print(f"  [OK] Has recent agent session tag - keeping lock")
                    kept.append(issue_number)
                    continue

                # Get comments to check last activity
                comments = self.get_issue_comments(issue_number)
                last_activity = self.get_last_activity_time(issue, comments)

                if self.is_stale(last_activity):
                    time_diff = datetime.now() - last_activity.replace(tzinfo=None)
                    minutes_ago = int(time_diff.total_seconds() / 60)

                    print(f"  [WARN] Stale activity ({minutes_ago} minutes ago) - removing lock")

                    if not dry_run:
                        if self.remove_lock_tag(issue_number):
                            reason = f"Last activity was {minutes_ago} minutes ago (threshold: {self.stale_threshold_minutes} minutes)"
                            self.add_comment_about_lock_removal(issue_number, reason)
                            removed.append(issue_number)
                            print(f"  [SUCCESS] Lock removed successfully")
                        else:
                            print(f"  [ERROR] Failed to remove lock")
                            errors.append(issue_number)
                    else:
                        print(f"  [DRY-RUN] Would remove lock (dry run)")
                        removed.append(issue_number)
                else:
                    print(f"  [OK] Recent activity - keeping lock")
                    kept.append(issue_number)

            except Exception as e:
                print(f"  [ERROR] Error processing issue: {e}")
                errors.append(issue_number)

        # Summary
        print("\n" + "="*60)
        print("[SUMMARY]")
        print(f"  Locks removed: {len(removed)} issues")
        if removed:
            print(f"    Issues: {', '.join(f'#{n}' for n in removed)}")

        print(f"  Locks kept: {len(kept)} issues")
        if kept:
            print(f"    Issues: {', '.join(f'#{n}' for n in kept)}")

        if errors:
            print(f"  Errors: {len(errors)} issues")
            print(f"    Issues: {', '.join(f'#{n}' for n in errors)}")

        print(f"\n[DONE] Lock cleanup complete")

        return {
            "removed": removed,
            "kept": kept,
            "errors": errors
        }

def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Clear old GitHub issue locks")
    parser.add_argument("--repo", default="netra-systems/netra-apex",
                       help="GitHub repository (default: netra-systems/netra-apex)")
    parser.add_argument("--threshold", type=int, default=20,
                       help="Minutes threshold for stale activity (default: 20)")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be done without making changes")
    parser.add_argument("--verbose", action="store_true",
                       help="Show detailed output")

    args = parser.parse_args()

    cleaner = GitHubIssueLockCleaner(repo=args.repo)
    cleaner.stale_threshold_minutes = args.threshold

    try:
        results = cleaner.clear_old_locks(dry_run=args.dry_run)

        # Exit with appropriate code
        if results["errors"]:
            print(f"\n[WARNING] Some errors occurred during processing")
            sys.exit(1)
        else:
            print(f"\n[SUCCESS] All operations completed successfully")
            sys.exit(0)

    except KeyboardInterrupt:
        print("\n[STOPPED] Operation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()