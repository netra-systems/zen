from shared.isolated_environment import get_env
#!/usr/bin/env python3
"""
Claude Code session end hook - automatically commits changes to the current branch.
This hook is triggered when a Claude Code session ends.
"""
import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path
import json

# Set UTF-8 encoding for Windows
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

def run_command(cmd, capture_output=True):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=capture_output,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def get_current_branch():
    """Get the current git branch."""
    success, branch, _ = run_command("git branch --show-current")
    if success:
        return branch.strip()
    return None

def get_git_status():
    """Get the current git status."""
    success, status, _ = run_command("git status --porcelain")
    if success:
        return status.strip()
    return None

def create_commit_message():
    """Create an automated commit message with timestamp and branch info."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    branch = get_current_branch() or "unknown"
    
    # Avoid emojis in commit message for Windows compatibility
    message = f"""Session checkpoint: {timestamp}

Automated commit at session end on branch: {branch}
Created by Claude Code session end hook

Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"""
    
    return message

def main():
    """Main function to handle the session end commit."""
    print("=" * 60)
    print("Claude Code Session End Hook - Auto Commit")
    print("=" * 60)
    
    # Check if we're in a git repository
    success, _, _ = run_command("git rev-parse --git-dir")
    if not success:
        print("[ERROR] Not in a git repository. Skipping commit.")
        return 0
    
    # Get current branch
    branch = get_current_branch()
    if not branch:
        print("[ERROR] Could not determine current branch. Skipping commit.")
        return 1
    
    print(f"[INFO] Current branch: {branch}")
    
    # Check for changes
    status = get_git_status()
    if not status:
        print("[SUCCESS] No changes to commit. Repository is clean.")
        return 0
    
    print(f"\n[INFO] Changes detected:")
    print("-" * 40)
    for line in status.split('\n')[:10]:  # Show first 10 changes
        if line.strip():
            print(f"  {line}")
    
    if len(status.split('\n')) > 10:
        print(f"  ... and {len(status.split('\n')) - 10} more files")
    print("-" * 40)
    
    # Stage all changes
    print("\n[INFO] Staging all changes...")
    success, _, error = run_command("git add -A")
    if not success:
        print(f"[ERROR] Failed to stage changes: {error}")
        return 1
    
    # Create commit
    commit_message = create_commit_message()
    print(f"\n[INFO] Creating commit on branch '{branch}'...")
    
    # Use a temporary file for the commit message to handle multi-line properly
    commit_file = Path(__file__).parent / ".claude_commit_msg.tmp"
    try:
        commit_file.write_text(commit_message, encoding='utf-8')
        success, output, error = run_command(f"git commit -F \"{commit_file}\"")
        
        if success:
            print("[SUCCESS] Successfully created commit!")
            # Get the commit hash
            success, commit_hash, _ = run_command("git rev-parse HEAD")
            if success:
                print(f"[INFO] Commit hash: {commit_hash.strip()[:8]}")
        else:
            if "nothing to commit" in error or "nothing to commit" in output:
                print("[INFO] No changes to commit (all changes already committed)")
            else:
                print(f"[ERROR] Failed to create commit: {error}")
                return 1
    finally:
        # Clean up temp file
        if commit_file.exists():
            commit_file.unlink()
    
    print("\n" + "=" * 60)
    print("[SUCCESS] Session end hook completed successfully!")
    print(f"[INFO] Branch '{branch}' has been updated with your session changes.")
    print("[TIP] Use 'git push' to sync with remote when ready.")
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[WARNING] Hook interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error in hook: {e}")
        sys.exit(1)
