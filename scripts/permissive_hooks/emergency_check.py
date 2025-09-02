from shared.isolated_environment import get_env
#!/usr/bin/env python3
"""
Emergency bypass check - allows quick fixes when needed.
Use commit message flags: [EMERGENCY], [HOTFIX], or [BYPASS]
"""
import sys
import subprocess
import os

def check_for_emergency_flag():
    """Check if commit message contains emergency bypass flag."""
    try:
        # Get the commit message
        result = subprocess.run(
            ['git', 'log', '--format=%B', '-n', '1', 'HEAD'],
            capture_output=True,
            text=True,
            check=True
        )
        commit_msg = result.stdout.strip()
    except subprocess.CalledProcessError:
        # If we can't get the commit message, check for environment variable
        commit_msg = os.environ.get('GIT_COMMIT_MSG', '')
    
    # Check for bypass flags
    bypass_flags = ['[EMERGENCY]', '[HOTFIX]', '[BYPASS]', 'EMERGENCY_FIX']
    
    for flag in bypass_flags:
        if flag in commit_msg.upper():
            return True, flag
    
    return False, None

def main():
    """Main entry point for pre-commit hook."""
    is_emergency, flag = check_for_emergency_flag()
    
    if is_emergency:
        print(f"\nEMERGENCY MODE DETECTED: {flag}")
        print("WARNING: Bypassing standard checks for emergency fix")
        print("Remember to follow up with proper cleanup commit")
        
        # Log this bypass for tracking
        try:
            with open('.emergency_bypasses.log', 'a') as f:
                import datetime
                f.write(f"{datetime.datetime.now().isoformat()} - Emergency bypass used: {flag}\n")
        except:
            pass
        
        # Allow the commit
        return 0
    
    # Check if we're in CI/CD environment (should not block CI)
    if os.environ.get('CI') or os.environ.get('GITHUB_ACTIONS'):
        print("CI/CD environment detected - using relaxed checks")
        return 0
    
    # Normal mode - continue with other checks
    return 0

if __name__ == '__main__':
    sys.exit(main())
