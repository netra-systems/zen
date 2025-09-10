#!/usr/bin/env python3
"""
DEPRECATION WARNING: This script is deprecated in favor of UnifiedTestRunner SSOT.

This CI/CD failure analysis script now redirects to the unified test runner
to maintain SSOT compliance while preserving existing functionality.

CRITICAL: Please migrate to using the unified test runner directly:
    python tests/unified_test_runner.py --execution-mode nightly --failure-analysis

Migration Path:
    OLD: python .github/scripts/failure_analysis.py --workflow-context "{...}" --job-results "{...}"
    NEW: python tests/unified_test_runner.py --execution-mode failure_analysis --context "{...}" --results "{...}"
"""

import sys
import subprocess
from pathlib import Path
import json
import argparse
import os


def show_deprecation_warning():
    """Show deprecation warning to users."""
    print("WARNING: DEPRECATION WARNING")
    print("=" * 50)
    print("This CI/CD failure analysis script is deprecated.")
    print("Please migrate to UnifiedTestRunner SSOT:")
    print()
    print("  NEW: python tests/unified_test_runner.py --execution-mode failure_analysis")
    print()
    print("Redirecting to UnifiedTestRunner with compatibility wrapper...")
    print("=" * 50)
    print()


def main():
    """Main entry point with deprecation wrapper."""
    show_deprecation_warning()
    
    # Parse original arguments for compatibility
    parser = argparse.ArgumentParser(
        description="[DEPRECATED] Analyze CI/CD failures and generate debug reports"
    )
    parser.add_argument("--workflow-context", required=True, help="JSON string with workflow context")
    parser.add_argument("--job-results", required=True, help="JSON string with job results")
    parser.add_argument("--workspace", default=".", help="Workspace directory path")
    parser.add_argument("--output", help="Output file for failure report")
    parser.add_argument("--create-archive", action="store_true", help="Create debug archive")
    
    args = parser.parse_args()
    
    # Get project root
    project_root = Path(__file__).parent.parent.parent
    unified_runner = project_root / "tests" / "unified_test_runner.py"
    
    if not unified_runner.exists():
        print(f"❌ ERROR: UnifiedTestRunner not found at {unified_runner}")
        print("Please check your installation and try again.")
        sys.exit(1)
    
    try:
        # Build unified test runner command with equivalent parameters
        cmd = [
            sys.executable, str(unified_runner),
            "--execution-mode", "failure_analysis",
            "--workspace", args.workspace
        ]
        
        # Pass context and results through environment variables for safety
        env = {
            **dict(os.environ),
            "FAILURE_ANALYSIS_CONTEXT": args.workflow_context,
            "FAILURE_ANALYSIS_RESULTS": args.job_results
        }
        
        if args.output:
            cmd.extend(["--output", args.output])
        
        if args.create_archive:
            cmd.append("--create-archive")
        
        print(f"Executing: {' '.join(cmd)}")
        
        # Execute unified test runner with same arguments
        result = subprocess.run(cmd, env=env, cwd=project_root)
        
        # Preserve original exit code behavior
        sys.exit(result.returncode)
        
    except Exception as e:
        print(f"ERROR: Failed to execute UnifiedTestRunner: {e}")
        print("Falling back to direct execution...")
        
        # Import and execute original functionality as fallback
        # This maintains compatibility during transition period
        import os
        os.environ['PATH'] = str(project_root) + os.pathsep + os.environ.get('PATH', '')
        sys.path.insert(0, str(project_root))
        
        try:
            # Import the backed up original implementation
            backup_file = Path(__file__).parent / "failure_analysis.py.backup"
            if backup_file.exists():
                import importlib.util
                spec = importlib.util.spec_from_file_location("failure_analysis_backup", backup_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Execute main from backup
                module.main()
            else:
                print("CRITICAL: No backup available and UnifiedTestRunner failed")
                sys.exit(1)
                
        except Exception as fallback_error:
            print(f"CRITICAL: Both UnifiedTestRunner and fallback failed: {fallback_error}")
            sys.exit(1)


if __name__ == "__main__":
    main()