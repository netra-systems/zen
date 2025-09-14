#!/usr/bin/env python3
"""Complete the git gardening process by handling all remaining files."""

import subprocess
import sys

def run_git_command(command):
    """Run a git command and return the result."""
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running: {command}")
        print(f"Error: {e.stderr}")
        return None

def complete_gardening():
    """Complete the git gardening process."""
    print("Completing git gardening cycle 2...")

    # Add all files
    result = run_git_command("git add -A")
    if result is not None:
        print("✓ Added all files")

    # Commit with comprehensive message
    commit_message = """chore: Complete git gardening cycle 2 - SSOT test infrastructure

* Finalize comprehensive SSOT test suite for WebSocket Manager fragmentation
* Complete AgentRegistry factory integration testing infrastructure
* Add Issue #824 and #859 complete test coverage
* Consolidate frontend types for SSOT compliance
* Clean repository state for continued SSOT work

Business Impact:
- Repository ready for SSOT remediation execution
- Complete test protection for $500K+ ARR Golden Path functionality
- All SSOT testing infrastructure properly committed

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"""

    result = run_git_command(f'git commit -m "{commit_message}"')
    if result is not None:
        print("✓ Created final commit")

    # Push to origin
    result = run_git_command("git push origin develop-long-lived")
    if result is not None:
        print("✓ Pushed to origin")

    # Final status check
    status = run_git_command("git status")
    print("\nFinal repository status:")
    print(status)

    if "working tree clean" in status:
        print("\n🎉 Git gardening cycle 2 completed successfully!")
        print("Repository is clean and ready for continued SSOT work.")
        return 0
    else:
        print("\n⚠️  Repository not completely clean, but major work done.")
        return 1

if __name__ == "__main__":
    sys.exit(complete_gardening())