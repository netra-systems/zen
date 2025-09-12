#!/usr/bin/env python3
"""
Pre-commit hook for duplicate and legacy code auditing
Integrates with the audit orchestrator
"""

import sys
import os
import asyncio
import subprocess
from pathlib import Path

# Add parent directory to path

from code_audit_orchestrator import CodeAuditOrchestrator
from audit_config import get_default_config, AuditLevel


def get_commit_message() -> str:
    """Try to get commit message if available"""
    try:
        # Check if COMMIT_EDITMSG exists
        commit_msg_file = Path(".git/COMMIT_EDITMSG")
        if commit_msg_file.exists():
            with open(commit_msg_file, 'r') as f:
                return f.read()
    except Exception:
        pass
    return ""


async def run_audit_hook():
    """Main hook logic"""
    # Load configuration
    config = get_default_config()
    
    # Check if audit is enabled
    if not config.flags.duplicate_detection and not config.flags.legacy_code_detection:
        print("[U+2139][U+FE0F] Code audit is disabled")
        return 0
    
    # Get commit message for bypass checking
    commit_message = get_commit_message()
    
    # Create orchestrator
    orchestrator = CodeAuditOrchestrator(config)
    
    # Check for bypass
    if orchestrator.check_bypass(commit_message):
        print(f" WARNING: [U+FE0F] Audit bypassed: {orchestrator.bypass_reason}")
        return 0
    
    print("\n" + "=" * 60)
    print(" SEARCH:  NETRA CODE AUDIT - Pre-commit Check")
    print("=" * 60)
    
    # Run audit on staged files only
    results = await orchestrator.run_audit()
    
    # Check results
    stats = results["stats"]
    
    if stats["should_block"]:
        print("\n" + "=" * 60)
        print("[U+26D4] COMMIT BLOCKED - Critical issues detected")
        print("=" * 60)
        
        print("\n CHART:  Issues Found:")
        print(f"  - Critical Duplicates: {stats['critical_duplicates']}")
        print(f"  - Critical Legacy: {stats['critical_legacy']}")
        
        # Show how to bypass if allowed
        if config.flags.allow_emergency_bypass:
            print("\n IDEA:  To bypass (use with caution):")
            print("  1. Add 'BYPASS_AUDIT' to commit message")
            print("  2. Use: BYPASS_AUDIT=1 git commit")
            print("  3. Add 'EMERGENCY_FIX' to commit message")
        
        # Show how to get details
        print("\n[U+1F4C4] For detailed report:")
        print("  python scripts/code_audit_orchestrator.py")
        
        return 1
    
    elif stats["total_duplicates"] > 0 or stats["total_legacy"] > 0:
        print("\n" + "=" * 60)
        print(" WARNING: [U+FE0F] WARNINGS - Non-critical issues found")
        print("=" * 60)
        
        print(f"\n CHART:  Issues Found:")
        print(f"  - Total Duplicates: {stats['total_duplicates']}")
        print(f"  - Total Legacy Patterns: {stats['total_legacy']}")
        
        # Check level
        level = config.flags.duplicate_level
        if level == AuditLevel.NOTIFY:
            print("\n PASS:  Commit allowed (notify mode)")
        elif level == AuditLevel.WARN:
            print("\n PASS:  Commit allowed (warning mode)")
        
        return 0
    
    else:
        print("\n PASS:  No issues found - code looks good!")
        return 0


def main():
    """Entry point"""
    try:
        # Run async audit
        exit_code = asyncio.run(run_audit_hook())
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\n\n WARNING: [U+FE0F] Audit cancelled by user")
        sys.exit(0)
        
    except Exception as e:
        print(f"\n FAIL:  Audit hook error: {e}")
        # Don't block on errors
        sys.exit(0)


if __name__ == "__main__":
    main()