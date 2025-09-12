from shared.isolated_environment import get_env
#!/usr/bin/env python3
"""
Claude Code Commit Hook - Pre-commit integration
Intelligently decides when to use Claude Code for commit messages
"""

import sys
import os
import subprocess
from pathlib import Path
from typing import Optional


class ClaudeCommitHook:
    """Pre-commit hook for Claude commit management"""
    
    def __init__(self):
        self.repo_root = Path(subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            text=True
        ).strip())
        self.manager_script = self.repo_root / "scripts" / "claude_commit_manager.py"
        
    def should_activate(self) -> bool:
        """Determine if Claude commit helper should activate"""
        # Check if feature is enabled
        if os.environ.get("DISABLE_CLAUDE_COMMIT") == "1":
            return False
        
        # Check git config
        try:
            config_value = subprocess.check_output(
                ["git", "config", "--get", "netra.claude-commit"],
                text=True,
                stderr=subprocess.DEVNULL
            ).strip()
            if config_value.lower() in ["false", "0", "no", "disabled"]:
                return False
        except subprocess.CalledProcessError:
            pass  # Config not set, use default behavior
        
        # Check if manager script exists
        if not self.manager_script.exists():
            return False
        
        # Check commit message file
        commit_msg_file = Path(".git/COMMIT_EDITMSG")
        if commit_msg_file.exists():
            with open(commit_msg_file, 'r') as f:
                content = f.read()
                # Skip if message already exists and isn't template
                if content.strip() and not content.startswith("#"):
                    return False
        
        return True
    
    def run(self) -> int:
        """Execute the hook"""
        if not self.should_activate():
            return 0
        
        print("[U+1F916] Claude Commit Helper is checking your changes...")
        
        try:
            # Run the manager
            result = subprocess.run(
                [sys.executable, str(self.manager_script)],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and result.stdout.strip():
                # Save generated message to staging file
                staging_file = self.repo_root / ".git" / "CLAUDE_COMMIT_MSG"
                with open(staging_file, 'w') as f:
                    f.write(result.stdout.strip())
                print(f" PASS:  Commit message prepared. Review it when git opens your editor.")
            else:
                print("[U+2139][U+FE0F] Claude commit helper completed (no message generated)")
            
        except Exception as e:
            print(f" WARNING: [U+FE0F] Claude commit helper error: {e}")
            # Don't block commit on errors
        
        return 0


def main():
    """Entry point"""
    hook = ClaudeCommitHook()
    return hook.run()


if __name__ == "__main__":
    sys.exit(main())
