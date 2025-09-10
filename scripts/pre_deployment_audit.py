#!/usr/bin/env python3
"""
DEPRECATION WARNING: This pre-deployment audit script is deprecated in favor of UnifiedTestRunner SSOT.

This pre-deployment audit script now redirects to the unified test runner's audit mode
to maintain SSOT compliance while preserving all existing audit functionality.

CRITICAL: Please migrate to using the unified test runner directly:
    python tests/unified_test_runner.py --execution-mode audit --commit-count 10

Migration Path:
    OLD: python scripts/pre_deployment_audit.py --commit-count 10 --since "1 hour ago"
    NEW: python tests/unified_test_runner.py --execution-mode audit --commit-count 10 --since "1 hour ago"

All original audit flags and options are preserved and forwarded to the SSOT implementation.
"""

import sys
import subprocess
from pathlib import Path
import argparse
import os


def show_deprecation_warning():
    """Show deprecation warning to users."""
    print("⚠️  DEPRECATION WARNING")
    print("=" * 70)
    print("This pre-deployment audit script is deprecated.")
    print("Please migrate to UnifiedTestRunner SSOT:")
    print()
    print("  NEW: python tests/unified_test_runner.py --execution-mode audit")
    print()
    print("All audit functionality preserved. Redirecting...")
    print("=" * 70)
    print()


def parse_audit_args():
    """Parse all audit arguments for compatibility."""
    parser = argparse.ArgumentParser(
        description="[DEPRECATED] Pre-deployment audit for catching LLM coding errors"
    )
    
    # Core audit options
    parser.add_argument("--commit-count", type=int, default=10, help="Number of recent commits to audit")
    parser.add_argument("--since", help="Audit commits since this time (e.g., '1 hour ago')")
    parser.add_argument("--branch", default="main", help="Base branch for comparison")
    parser.add_argument("--output", help="Output file for audit report")
    parser.add_argument("--format", choices=["json", "markdown", "text"], default="text", help="Report format")
    parser.add_argument("--severity", choices=["CRITICAL", "HIGH", "MEDIUM", "LOW"], help="Filter by minimum severity")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--no-git-analysis", action="store_true", help="Skip git analysis")
    parser.add_argument("--no-test-coverage", action="store_true", help="Skip test coverage analysis")
    parser.add_argument("--focus", help="Focus on specific component or module")
    
    return parser.parse_known_args()


def main():
    """Main entry point with deprecation wrapper."""
    show_deprecation_warning()
    
    # Parse all audit arguments
    args, unknown_args = parse_audit_args()
    
    # Get project root
    project_root = Path(__file__).parent.parent
    unified_runner = project_root / "tests" / "unified_test_runner.py"
    
    if not unified_runner.exists():
        print(f"❌ ERROR: UnifiedTestRunner not found at {unified_runner}")
        print("Falling back to original audit script...")
        return execute_fallback_audit()
    
    try:
        # Build unified test runner command with audit mode
        cmd = [
            sys.executable, str(unified_runner),
            "--execution-mode", "audit"
        ]
        
        # Forward all audit arguments
        if args.commit_count != 10:  # Only add if not default
            cmd.extend(["--commit-count", str(args.commit_count)])
        if args.since:
            cmd.extend(["--since", args.since])
        if args.branch != "main":  # Only add if not default
            cmd.extend(["--branch", args.branch])
        if args.output:
            cmd.extend(["--output", args.output])
        if args.format != "text":  # Only add if not default
            cmd.extend(["--format", args.format])
        if args.severity:
            cmd.extend(["--severity", args.severity])
        if args.verbose:
            cmd.append("--verbose")
        if args.no_git_analysis:
            cmd.append("--no-git-analysis")
        if args.no_test_coverage:
            cmd.append("--no-test-coverage")
        if args.focus:
            cmd.extend(["--focus", args.focus])
            
        # Add any unknown arguments
        cmd.extend(unknown_args)
        
        print(f"🔄 Executing audit via UnifiedTestRunner:")
        print(f"   {' '.join(cmd)}")
        print()
        
        # Execute unified test runner in audit mode
        result = subprocess.run(cmd, cwd=project_root)
        
        # Preserve original exit code behavior
        sys.exit(result.returncode)
        
    except Exception as e:
        print(f"❌ ERROR: Failed to execute UnifiedTestRunner audit: {e}")
        print("Falling back to original audit script...")
        return execute_fallback_audit()


def execute_fallback_audit():
    """Execute original audit script as fallback."""
    try:
        # Import and execute original functionality as fallback
        project_root = Path(__file__).parent.parent
        
        # Import the backed up original implementation
        backup_file = Path(__file__).parent / "pre_deployment_audit.py.backup"
        if backup_file.exists():
            print("🔄 Using backup audit implementation...")
            
            # Add project root to path
            sys.path.insert(0, str(project_root))
            
            import importlib.util
            spec = importlib.util.spec_from_file_location("audit_backup", backup_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Execute main from backup with original arguments
            # Reset sys.argv to original arguments for the backup script
            original_argv = sys.argv[:]
            original_argv[0] = str(backup_file)  # Update script name
            sys.argv = original_argv
            
            module.main()
        else:
            print("❌ CRITICAL: No backup available for audit script")
            print("Please restore original pre_deployment_audit.py")
            sys.exit(1)
            
    except Exception as fallback_error:
        print(f"❌ CRITICAL: Fallback audit failed: {fallback_error}")
        print("Manual code review required before deployment.")
        sys.exit(1)


if __name__ == "__main__":
    main()