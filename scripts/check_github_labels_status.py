#!/usr/bin/env python3
"""
GitHub Label Status Checker - Check "actively-being-worked-on" labels

This script checks the current status of GitHub issues with the "actively-being-worked-on" label
and reports which ones might be stale (not updated in last 20 minutes).

This is a READ-ONLY script that makes no changes to the repository.
"""

import asyncio
import sys
import os
from datetime import datetime, timezone, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from test_framework.ssot.github_client import create_github_client, GitHubAPIError
    from shared.isolated_environment import IsolatedEnvironment

    async def check_label_status():
        """Check status of actively-being-worked-on labels."""
        print("GitHub Label Status Checker")
        print("=" * 50)

        # Get repository info from git remote
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
                if "netra-systems/netra-apex" in remote_url:
                    repo_owner = "netra-systems"
                    repo_name = "netra-apex"
                else:
                    print(f"Detected repository: {remote_url}")
                    # Parse the URL to extract owner/repo
                    if "github.com" in remote_url:
                        if "https://github.com/" in remote_url:
                            parts = remote_url.replace("https://github.com/", "").replace(".git", "").split("/")
                        elif "git@github.com:" in remote_url:
                            parts = remote_url.replace("git@github.com:", "").replace(".git", "").split("/")
                        else:
                            raise ValueError("Unknown URL format")

                        if len(parts) >= 2:
                            repo_owner, repo_name = parts[0], parts[1]
                        else:
                            raise ValueError("Could not parse owner/repo")
                    else:
                        raise ValueError("Not a GitHub repository")
            else:
                raise subprocess.CalledProcessError(result.returncode, "git remote get-url origin")

        except Exception as e:
            print(f"Could not determine repository from git remote: {e}")
            print("Using default: netra-systems/netra-apex")
            repo_owner = "netra-systems"
            repo_name = "netra-apex"

        print(f"Repository: {repo_owner}/{repo_name}")
        print(f"Target label: 'actively-being-worked-on'")
        print(f"Stale threshold: 20 minutes")
        print()

        # Check environment for GitHub configuration
        env = IsolatedEnvironment()
        token = env.get("GITHUB_TEST_TOKEN", "")

        if not token:
            print("❌ GITHUB_TEST_TOKEN not found in environment")
            print("   Set this environment variable to access GitHub API")
            return

        print(f"✅ GitHub token configured (length: {len(token)})")

        try:
            # Create GitHub client
            client = create_github_client(user_context="status_check")

            async with client:
                # Validate credentials
                is_valid = await client.validate_credentials()
                if not is_valid:
                    print("❌ GitHub credentials validation failed")
                    return

                print("✅ GitHub credentials validated")
                print()

                # Search for issues with the label
                issues = await client.search_issues(
                    query="",
                    repo_owner=repo_owner,
                    repo_name=repo_name,
                    state="open",
                    labels="actively-being-worked-on",
                    sort="updated",
                    order="desc",
                    per_page=100
                )

                print(f"Found {len(issues)} issues with 'actively-being-worked-on' label:")
                print()

                if not issues:
                    print("🎉 No issues found with the 'actively-being-worked-on' label!")
                    print("   Repository is clean.")
                    return

                now = datetime.now(timezone.utc)
                stale_count = 0

                for issue in issues:
                    try:
                        # Parse update time
                        updated_at = datetime.fromisoformat(issue.updated_at.replace('Z', '+00:00'))
                        time_diff = now - updated_at
                        minutes_ago = int(time_diff.total_seconds() / 60)

                        # Check if stale
                        is_stale = time_diff > timedelta(minutes=20)
                        status_icon = "🔄" if is_stale else "✅"

                        if is_stale:
                            stale_count += 1

                        print(f"{status_icon} Issue #{issue.number}: {issue.title}")
                        print(f"   Last updated: {minutes_ago} minutes ago ({issue.updated_at})")
                        print(f"   URL: {issue.html_url}")

                        if is_stale:
                            print(f"   ⚠️  STALE: This issue should have label removed")

                        print()

                    except (ValueError, AttributeError) as e:
                        print(f"❌ Could not parse update time for issue #{issue.number}: {e}")
                        print()

                # Summary
                print("=" * 50)
                print(f"Summary:")
                print(f"  Total issues with label: {len(issues)}")
                print(f"  Stale issues (>20 min): {stale_count}")
                print(f"  Active issues (≤20 min): {len(issues) - stale_count}")

                if stale_count > 0:
                    print(f"\n⚠️  {stale_count} issues need label cleanup")
                    print("   Run the cleanup script to remove stale labels")
                else:
                    print(f"\n🎉 All issues with label are actively being worked on!")

        except GitHubAPIError as e:
            print(f"❌ GitHub API Error: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")

    # Run the check
    asyncio.run(check_label_status())

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("   Make sure you're running from the project root directory")
except Exception as e:
    print(f"❌ Error: {e}")