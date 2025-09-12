#!/usr/bin/env python3
"""
Configure Claude Commit Helper - Enable/disable intelligent commit messages
"""

import sys
import subprocess
import shutil
import io
from pathlib import Path
from typing import Optional

# Fix Windows console encoding for emojis
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


class ClaudeCommitConfigurator:
    """Manages Claude commit helper configuration"""
    
    def __init__(self):
        self.repo_root = Path(subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            text=True
        ).strip())
        self.hook_file = self.repo_root / ".git" / "hooks" / "prepare-commit-msg"
        self.hook_source = self.repo_root / ".git" / "hooks" / "prepare-commit-msg"
        
    def status(self) -> str:
        """Get current status"""
        # Check git config
        try:
            config_value = subprocess.check_output(
                ["git", "config", "--get", "netra.claude-commit"],
                text=True,
                stderr=subprocess.DEVNULL
            ).strip()
            config_status = f"Git config: {config_value}"
        except subprocess.CalledProcessError:
            config_status = "Git config: not set (default: enabled)"
        
        # Check hook installation
        if self.hook_file.exists():
            hook_status = "Hook: installed  PASS: "
        else:
            hook_status = "Hook: not installed  FAIL: "
        
        # Check Claude CLI
        if shutil.which("claude"):
            claude_status = "Claude CLI: available  PASS: "
        else:
            claude_status = "Claude CLI: not found  WARNING: [U+FE0F]"
        
        return f"""
Claude Commit Helper Status:
  {config_status}
  {hook_status}
  {claude_status}
"""
    
    def enable(self, mode: str = "auto") -> None:
        """Enable Claude commit helper"""
        # Set git config
        subprocess.run(["git", "config", "netra.claude-commit", "true"])
        
        # Make hook executable
        if self.hook_file.exists():
            self.hook_file.chmod(0o755)
        
        print(f" PASS:  Claude commit helper enabled (mode: {mode})")
        print("    Use 'BYPASS_CLAUDE' in message to skip")
        print("    Or set DISABLE_CLAUDE_COMMIT=1 environment variable")
    
    def disable(self) -> None:
        """Disable Claude commit helper"""
        subprocess.run(["git", "config", "netra.claude-commit", "false"])
        print(" FAIL:  Claude commit helper disabled")
        print("    The hook remains installed but won't activate")
    
    def install_hook(self) -> None:
        """Ensure the prepare-commit-msg hook is properly installed"""
        if not self.hook_file.exists():
            print(" WARNING: [U+FE0F] Hook file not found. Please ensure .git/hooks/prepare-commit-msg exists")
            return
        
        # Make executable
        self.hook_file.chmod(0o755)
        print(" PASS:  Hook installed and made executable")
    
    def test(self) -> None:
        """Test the Claude commit helper with a dry run"""
        print("[U+1F9EA] Testing Claude commit helper...")
        
        # Create a test change
        test_file = self.repo_root / "test_claude_commit.tmp"
        test_file.write_text("Test content for Claude commit helper")
        
        try:
            # Stage the file
            subprocess.run(["git", "add", str(test_file)])
            
            # Run the manager directly
            manager_script = self.repo_root / "scripts" / "claude_commit_manager.py"
            result = subprocess.run(
                [sys.executable, str(manager_script)],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and result.stdout.strip():
                print(" PASS:  Test successful! Generated message:")
                print("[U+2500]" * 50)
                print(result.stdout.strip())
                print("[U+2500]" * 50)
            else:
                print(" FAIL:  Test failed. Check your Claude CLI installation.")
                if result.stderr:
                    print(f"Error: {result.stderr}")
            
        finally:
            # Clean up
            subprocess.run(["git", "reset", "HEAD", str(test_file)], capture_output=True)
            test_file.unlink(missing_ok=True)
    
    def show_usage_tips(self) -> None:
        """Show usage tips"""
        print("""
[U+1F4DD] Claude Commit Helper Usage Tips:

1. Normal commit (Claude will help):
   git commit

2. Bypass Claude for this commit:
   git commit -m "BYPASS_CLAUDE: Quick fix"

3. Emergency commits (auto-bypass):
   git commit -m "EMERGENCY_FIX: Critical production issue"

4. Temporarily disable:
   export DISABLE_CLAUDE_COMMIT=1
   git commit

5. Configure globally:
   git config netra.claude-commit false  # disable
   git config netra.claude-commit true   # enable

6. The helper is smart about:
   - Avoiding recursion (won't call itself)
   - CI/CD environments (auto-disabled)
   - Large diffs (truncates for context)
   - Timeouts (30 second limit)
   - Failures (never blocks commits)

7. Commit message patterns:
   - feat: New feature
   - fix: Bug fix
   - refactor: Code restructuring
   - test: Test updates
   - docs: Documentation
   - chore: Maintenance tasks
""")


def main():
    """CLI entry point"""
    configurator = ClaudeCommitConfigurator()
    
    if len(sys.argv) < 2:
        print("Usage: python configure_claude_commit.py [status|enable|disable|test|tips|install]")
        print(configurator.status())
        return 1
    
    command = sys.argv[1].lower()
    
    if command == "status":
        print(configurator.status())
    elif command == "enable":
        configurator.enable()
    elif command == "disable":
        configurator.disable()
    elif command == "test":
        configurator.test()
    elif command == "tips":
        configurator.show_usage_tips()
    elif command == "install":
        configurator.install_hook()
    else:
        print(f"Unknown command: {command}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())