#!/usr/bin/env python3
"""
GitHub Label Cleanup Script - Remove "actively-being-worked-on" from Stale Issues

This script identifies GitHub issues with the "actively-being-worked-on" label that haven't
been updated in the last 20 minutes and removes the label from them.

SAFETY FIRST: Only makes minimal changes needed - removes stale labels without damaging repo health.

Business Value: Platform/Internal - Keeps GitHub organization clean and prevents label pollution.

Usage:
    python scripts/cleanup_stale_actively_being_worked_on_labels.py [--dry-run] [--verbose]
"""

import asyncio
import logging
import sys
from datetime import datetime, timezone, timedelta
from typing import List, Tuple, Optional
import argparse

# Add project root to path for imports
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test_framework.ssot.github_client import (
    GitHubClient,
    GitHubIssue,
    GitHubAPIError,
    create_github_client
)
from shared.isolated_environment import IsolatedEnvironment

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
STALE_LABEL = "actively-being-worked-on"
STALE_THRESHOLD_MINUTES = 20


class LabelCleanupResult:
    """Results of label cleanup operation."""

    def __init__(self):
        self.issues_checked = 0
        self.stale_issues_found = 0
        self.labels_removed = 0
        self.errors = []
        self.processed_issues = []

    def add_processed_issue(self, issue: GitHubIssue, was_stale: bool, action_taken: str):
        """Add a processed issue to results."""
        self.processed_issues.append({
            'issue_number': issue.number,
            'title': issue.title,
            'updated_at': issue.updated_at,
            'was_stale': was_stale,
            'action_taken': action_taken
        })

    def add_error(self, error_message: str):
        """Add an error to results."""
        self.errors.append(error_message)

    def summary(self) -> str:
        """Get summary of cleanup results."""
        return (
            f"Cleanup Summary:\n"
            f"  Issues checked: {self.issues_checked}\n"
            f"  Stale issues found: {self.stale_issues_found}\n"
            f"  Labels removed: {self.labels_removed}\n"
            f"  Errors: {len(self.errors)}"
        )


async def get_repo_info() -> Tuple[str, str]:
    """
    Get repository owner and name from environment or git remote.

    Returns:
        Tuple of (repo_owner, repo_name)
    """
    env = IsolatedEnvironment()

    # Try environment variables first
    repo_owner = env.get("GITHUB_TEST_REPO_OWNER", "")
    repo_name = env.get("GITHUB_TEST_REPO_NAME", "")

    if repo_owner and repo_name:
        return repo_owner, repo_name

    # Fall back to parsing git remote
    try:
        import subprocess
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )

        if result.returncode == 0:
            remote_url = result.stdout.strip()
            # Parse GitHub URL: https://github.com/owner/repo.git
            if "github.com" in remote_url:
                if remote_url.startswith("https://github.com/"):
                    parts = remote_url.replace("https://github.com/", "").replace(".git", "").split("/")
                elif remote_url.startswith("git@github.com:"):
                    parts = remote_url.replace("git@github.com:", "").replace(".git", "").split("/")
                else:
                    raise ValueError(f"Unrecognized GitHub URL format: {remote_url}")

                if len(parts) >= 2:
                    return parts[0], parts[1]

    except Exception as e:
        logger.warning(f"Could not parse git remote: {e}")

    # Default fallback
    return "netra-systems", "netra-apex"


def is_issue_stale(issue: GitHubIssue, threshold_minutes: int = STALE_THRESHOLD_MINUTES) -> bool:
    """
    Check if an issue is stale based on its last update time.

    Args:
        issue: GitHub issue to check
        threshold_minutes: Minutes after which an issue is considered stale

    Returns:
        True if issue is stale, False otherwise
    """
    try:
        # Parse GitHub timestamp: "2024-01-15T10:30:00Z"
        updated_at = datetime.fromisoformat(issue.updated_at.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        time_diff = now - updated_at

        return time_diff > timedelta(minutes=threshold_minutes)

    except (ValueError, AttributeError) as e:
        logger.warning(f"Could not parse update time for issue #{issue.number}: {e}")
        return False


async def find_issues_with_label(
    client: GitHubClient,
    repo_owner: str,
    repo_name: str,
    label: str
) -> List[GitHubIssue]:
    """
    Find all open issues with the specified label.

    Args:
        client: GitHub API client
        repo_owner: Repository owner
        repo_name: Repository name
        label: Label to search for

    Returns:
        List of issues with the label
    """
    try:
        issues = await client.search_issues(
            query="",
            repo_owner=repo_owner,
            repo_name=repo_name,
            state="open",
            labels=label,
            sort="updated",
            order="desc",
            per_page=100
        )

        logger.info(f"Found {len(issues)} issues with label '{label}'")
        return issues

    except GitHubAPIError as e:
        logger.error(f"Error searching for issues with label '{label}': {e}")
        return []


async def remove_label_from_issue(
    client: GitHubClient,
    repo_owner: str,
    repo_name: str,
    issue: GitHubIssue,
    label_to_remove: str,
    dry_run: bool = False
) -> bool:
    """
    Remove a specific label from an issue.

    Args:
        client: GitHub API client
        repo_owner: Repository owner
        repo_name: Repository name
        issue: Issue to remove label from
        label_to_remove: Label name to remove
        dry_run: If True, don't actually remove the label

    Returns:
        True if label was removed (or would be removed in dry run), False otherwise
    """
    try:
        # Get current labels and filter out the one to remove
        current_labels = [label for label in issue.labels if label != label_to_remove]

        if label_to_remove not in issue.labels:
            logger.debug(f"Issue #{issue.number} doesn't have label '{label_to_remove}'")
            return False

        if dry_run:
            logger.info(f"DRY RUN: Would remove label '{label_to_remove}' from issue #{issue.number}")
            return True

        # Update issue with new labels
        await client.update_issue(
            repo_owner=repo_owner,
            repo_name=repo_name,
            issue_number=issue.number,
            labels=current_labels
        )

        logger.info(f"Removed label '{label_to_remove}' from issue #{issue.number}: {issue.title}")
        return True

    except GitHubAPIError as e:
        logger.error(f"Error removing label from issue #{issue.number}: {e}")
        return False


async def cleanup_stale_labels(dry_run: bool = False, verbose: bool = False) -> LabelCleanupResult:
    """
    Main function to cleanup stale "actively-being-worked-on" labels.

    Args:
        dry_run: If True, don't actually remove labels
        verbose: If True, log detailed information

    Returns:
        LabelCleanupResult with operation results
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    result = LabelCleanupResult()

    try:
        # Get repository information
        repo_owner, repo_name = await get_repo_info()
        logger.info(f"Checking repository: {repo_owner}/{repo_name}")

        # Create GitHub client
        client = create_github_client(user_context="label_cleanup")

        async with client:
            # Validate credentials
            is_valid = await client.validate_credentials()
            if not is_valid:
                error_msg = "GitHub credentials validation failed"
                logger.error(error_msg)
                result.add_error(error_msg)
                return result

            logger.info("GitHub credentials validated successfully")

            # Find issues with the target label
            issues = await find_issues_with_label(
                client, repo_owner, repo_name, STALE_LABEL
            )

            result.issues_checked = len(issues)

            if not issues:
                logger.info(f"No issues found with label '{STALE_LABEL}'")
                return result

            # Check each issue for staleness
            for issue in issues:
                logger.debug(f"Checking issue #{issue.number}: {issue.title}")
                logger.debug(f"  Last updated: {issue.updated_at}")

                if is_issue_stale(issue, STALE_THRESHOLD_MINUTES):
                    result.stale_issues_found += 1
                    logger.info(f"Issue #{issue.number} is stale (updated: {issue.updated_at})")

                    # Remove the label
                    if await remove_label_from_issue(
                        client, repo_owner, repo_name, issue, STALE_LABEL, dry_run
                    ):
                        result.labels_removed += 1
                        result.add_processed_issue(
                            issue, True, "removed" if not dry_run else "would_remove"
                        )
                    else:
                        result.add_processed_issue(issue, True, "failed_to_remove")

                else:
                    logger.debug(f"Issue #{issue.number} is still active")
                    result.add_processed_issue(issue, False, "no_action")

    except Exception as e:
        error_msg = f"Unexpected error during cleanup: {str(e)}"
        logger.error(error_msg)
        result.add_error(error_msg)

    return result


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Remove 'actively-being-worked-on' labels from stale GitHub issues"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    logger.info("Starting GitHub label cleanup")
    logger.info(f"Target label: '{STALE_LABEL}'")
    logger.info(f"Stale threshold: {STALE_THRESHOLD_MINUTES} minutes")

    if args.dry_run:
        logger.info("DRY RUN MODE: No actual changes will be made")

    result = await cleanup_stale_labels(dry_run=args.dry_run, verbose=args.verbose)

    # Print results
    print("\n" + "="*60)
    print(result.summary())

    if result.processed_issues:
        print("\nProcessed Issues:")
        for issue_info in result.processed_issues:
            status_icon = "🔄" if issue_info['was_stale'] else "✅"
            action = issue_info['action_taken']
            print(f"  {status_icon} #{issue_info['issue_number']}: {issue_info['title']}")
            print(f"     Updated: {issue_info['updated_at']} | Action: {action}")

    if result.errors:
        print("\nErrors:")
        for error in result.errors:
            print(f"  ❌ {error}")

    # Exit code based on results
    if result.errors:
        sys.exit(1)
    elif result.stale_issues_found > 0:
        print(f"\n✅ Successfully processed {result.stale_issues_found} stale issues")
        sys.exit(0)
    else:
        print("\n✅ No stale issues found - repository is clean!")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())