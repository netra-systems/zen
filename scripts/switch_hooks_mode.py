#!/usr/bin/env python3
"""
Switch between strict and permissive pre-commit hook configurations.
This allows developers to use appropriate enforcement based on context.
"""
import sys
import shutil
from pathlib import Path
import argparse

def switch_mode(mode):
    """Switch pre-commit configuration to specified mode."""
    root = Path(__file__).parent.parent
    current_config = root / '.pre-commit-config.yaml'
    strict_config = root / '.pre-commit-config-strict.yaml'
    permissive_config = root / '.pre-commit-config-permissive.yaml'
    
    # Backup current config if it's not already backed up
    if not strict_config.exists() and current_config.exists():
        print("Backing up current (strict) configuration...")
        shutil.copy2(current_config, strict_config)
    
    if mode == 'strict':
        if not strict_config.exists():
            print("ERROR: Strict configuration not found!")
            return False
        
        print("Switching to STRICT mode...")
        shutil.copy2(strict_config, current_config)
        print("SUCCESS: Strict hooks enabled - Full compliance enforcement")
        print("   Use for: Production releases, major refactors")
        
    elif mode == 'permissive':
        if not permissive_config.exists():
            print("ERROR: Permissive configuration not found!")
            return False
        
        print("Switching to PERMISSIVE mode...")
        shutil.copy2(permissive_config, current_config)
        print("SUCCESS: Permissive hooks enabled - Focus on new code only")
        print("   Use for: Feature development, quick fixes, legacy code work")
        
    elif mode == 'off':
        print("Disabling pre-commit hooks...")
        if current_config.exists():
            current_config.rename(current_config.with_suffix('.yaml.disabled'))
        print("SUCCESS: Pre-commit hooks disabled")
        print("   WARNING: Remember to re-enable before committing!")
        
    elif mode == 'status':
        if not current_config.exists():
            print("ERROR: No active pre-commit configuration")
            return True
        
        # Try to detect which mode is active
        with open(current_config, 'r') as f:
            content = f.read()
            
        if 'Permissive' in content:
            print("Current mode: PERMISSIVE")
            print("   - Checking new files strictly")
            print("   - Checking only modified lines in existing files")
            print("   - Lenient on test files")
        elif 'Elite Enforcement' in content:
            print("Current mode: STRICT")
            print("   - Full compliance enforcement")
            print("   - 300-line file limits")
            print("   - 25-line function limits")
        else:
            print("Current mode: CUSTOM")
        
        return True
    
    else:
        print(f"ERROR: Unknown mode: {mode}")
        return False
    
    return True

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Switch between strict and permissive pre-commit hooks',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/switch_hooks_mode.py permissive  # For development
  python scripts/switch_hooks_mode.py strict      # For releases
  python scripts/switch_hooks_mode.py off         # Disable temporarily
  python scripts/switch_hooks_mode.py status      # Check current mode
  
Modes:
  permissive - Focus on new files and changes only (recommended for development)
  strict     - Full compliance checking (use before releases)
  off        - Disable hooks temporarily
  status     - Show current configuration
        """
    )
    parser.add_argument(
        'mode',
        choices=['strict', 'permissive', 'off', 'status'],
        help='Hook enforcement mode'
    )
    
    args = parser.parse_args()
    
    success = switch_mode(args.mode)
    
    if success and args.mode != 'status':
        print("\nTip: Run 'pre-commit install' to apply changes")
        print("   Or use: git commit --no-verify to bypass hooks once")
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())