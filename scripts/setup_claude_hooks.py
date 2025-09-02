from shared.isolated_environment import get_env
#!/usr/bin/env python3
"""
Setup script for Claude Code session hooks.
This script configures Claude Code to run specific hooks at session events.
"""
import json
import sys
import os
from pathlib import Path
import subprocess

# Set UTF-8 encoding for Windows
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

def setup_claude_hook():
    """Setup the Claude Code session end hook."""
    root_dir = Path(__file__).parent.parent
    hook_script = root_dir / "scripts" / "claude_session_end_hook.py"
    config_file = root_dir / ".claude-hooks.json"
    
    print("[SETUP] Claude Code Session Hook Setup")
    print("=" * 60)
    
    # Check if hook script exists
    if not hook_script.exists():
        print(f"[ERROR] Hook script not found: {hook_script}")
        return False
    
    # Check if config exists
    if not config_file.exists():
        print(f"[ERROR] Configuration file not found: {config_file}")
        return False
    
    print(f"[SUCCESS] Hook script found: {hook_script.name}")
    print(f"[SUCCESS] Configuration found: {config_file.name}")
    
    # Make the hook script executable on Unix-like systems
    if sys.platform != 'win32':
        try:
            hook_script.chmod(0o755)
            print(f"[SUCCESS] Made hook script executable")
        except Exception as e:
            print(f"[WARNING] Could not make script executable: {e}")
    
    # Test the hook
    print("\n[INFO] Testing hook functionality...")
    result = subprocess.run(
        [sys.executable, str(hook_script)],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    
    if result.stdout and "Claude Code Session End Hook" in result.stdout:
        print("[SUCCESS] Hook script is working correctly!")
    else:
        print("[WARNING] Hook script test had unexpected output")
    
    print("\n" + "=" * 60)
    print("[INFO] INSTALLATION INSTRUCTIONS:")
    print("=" * 60)
    print("""
To enable the session end commit hook in Claude Code:

1. The hook configuration has been created at:
   .claude-hooks.json

2. The hook script is located at:
   scripts/claude_session_end_hook.py

3. The hook will automatically:
   - Detect when your Claude session ends
   - Stage all changes (git add -A)
   - Create a timestamped commit on the CURRENT branch
   - Include session metadata in the commit message
   - NOT push to remote (you control when to push)

4. How it works:
   - Stays on your current branch (no switching)
   - Creates descriptive commit messages with timestamps
   - Safe: only commits, never pushes or changes branches
   - Shows you what was committed

5. To test the hook manually:
   python scripts/claude_session_end_hook.py

6. To disable the hook temporarily:
   - Edit .claude-hooks.json
   - Set "enabled": false for the session-end hook

7. The hook respects your current git branch and will:
   - Always commit to the branch you're currently on
   - Never switch branches automatically
   - Include the branch name in commit messages
""")
    
    print("=" * 60)
    print("[SUCCESS] Setup complete! The hook is ready to use.")
    print("=" * 60)
    
    return True

def main():
    """Main entry point."""
    try:
        success = setup_claude_hook()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"[ERROR] Setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
