#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DEPRECATION WARNING: This deployment entry point is deprecated.

WEEK 1 SSOT REMEDIATION (GitHub Issue #245): 
This script now redirects to the canonical deployment source while preserving 
100% backward compatibility during the transition period.

CANONICAL SOURCE: scripts/deploy_to_gcp_actual.py

Migration Path:
    OLD: python scripts/deploy_to_gcp.py --project netra-staging --build-local
    NEW: python scripts/deploy_to_gcp_actual.py --project netra-staging --build-local

<<<<<<< HEAD
All original flags and options are preserved and forwarded to the canonical implementation.
This wrapper will be removed in Week 2 after validation of the transition.
=======
All original flags and options are preserved in the new script.

WARNING: The UnifiedTestRunner does NOT have deployment functionality.
This script will redirect to the actual deployment script for compatibility.
>>>>>>> aff87269fab4baa3d9e1197f91be90d4c7c0367d
"""

import sys
import subprocess
from pathlib import Path
import argparse

# Handle Windows encoding issues
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def show_deprecation_warning():
    """Show deprecation warning to users."""
<<<<<<< HEAD
    print("=" * 80)
    print("WARNING: DEPRECATION WARNING - WEEK 1 SSOT REMEDIATION")
    print("=" * 80)
    print("GitHub Issue #245: Deployment canonical source conflicts")
    print()
    print("This deployment entry point is deprecated.")
    print("Please migrate to the canonical deployment script:")
=======
    print("WARNING: DEPLOYMENT SCRIPT DEPRECATED")
    print("=" * 70)
    print("This GCP deployment script is deprecated.")
    print("Please migrate to the official deployment script:")
    print()
    print("  NEW: python scripts/deploy_to_gcp_actual.py")
>>>>>>> aff87269fab4baa3d9e1197f91be90d4c7c0367d
    print()
    print("  CANONICAL: python scripts/deploy_to_gcp_actual.py")
    print()
    print("All functionality preserved. Auto-redirecting to canonical source...")
    print("=" * 80)
    print()


def main():
    """Main entry point with deprecation wrapper and redirect."""
    show_deprecation_warning()
    
    # Get project root and canonical deployment script
    project_root = Path(__file__).parent.parent
<<<<<<< HEAD
    canonical_script = Path(__file__).parent / "deploy_to_gcp_actual.py"
    
    if not canonical_script.exists():
        print(f"ERROR: Canonical deployment script not found at {canonical_script}")
        print(f"CRITICAL: Deployment cannot proceed")
        print(f"   Please restore scripts/deploy_to_gcp_actual.py")
        sys.exit(1)
    
    try:
        # Build command to execute canonical deployment script
        cmd = [sys.executable, str(canonical_script)] + sys.argv[1:]
        
        print(f"Redirecting to canonical deployment script:")
        print(f"   {' '.join(cmd)}")
        print()
        
        # Execute canonical deployment script with all original arguments
=======
    actual_deploy_script = project_root / "scripts" / "deploy_to_gcp_actual.py"
    
    if not actual_deploy_script.exists():
        print(f"ERROR: Official deployment script not found at {actual_deploy_script}")
        print("Please check that scripts/deploy_to_gcp_actual.py exists")
        sys.exit(1)
    
    try:
        # Build command for actual deployment script
        cmd = [sys.executable, str(actual_deploy_script)]
        
        # Forward all deployment arguments
        if args.project:
            cmd.extend(["--project", args.project])
        if args.build_local:
            cmd.append("--build-local")
        if args.check_secrets:
            cmd.append("--check-secrets")
        if args.check_apis:
            cmd.append("--check-apis")
        if args.run_checks:
            cmd.append("--run-checks")
        if args.rollback:
            cmd.append("--rollback")
        if args.service:
            cmd.extend(["--service", args.service])
        if args.env:
            cmd.extend(["--env", args.env])
        if args.timeout:
            cmd.extend(["--timeout", str(args.timeout)])
        if args.verbose:
            cmd.append("--verbose")
        if args.dry_run:
            cmd.append("--dry-run")
            
        # Add any unknown arguments
        cmd.extend(unknown_args)
        
        print(f"Redirecting to official deployment script:")
        print(f"   {' '.join(cmd)}")
        print()
        
        # Execute actual deployment script
>>>>>>> aff87269fab4baa3d9e1197f91be90d4c7c0367d
        result = subprocess.run(cmd, cwd=project_root)
        
        # Preserve original exit code behavior
        sys.exit(result.returncode)
        
    except KeyboardInterrupt:
        print("\nDeployment interrupted by user")
        sys.exit(1)
    except Exception as e:
<<<<<<< HEAD
        print(f"ERROR: Failed to execute canonical deployment script: {e}")
        print(f"Manual intervention required")
=======
        print(f"ERROR: Failed to execute official deployment script: {e}")
        print("Please run the deployment script directly:")
        print(f"   python scripts/deploy_to_gcp_actual.py {' '.join(sys.argv[1:])}")
>>>>>>> aff87269fab4baa3d9e1197f91be90d4c7c0367d
        sys.exit(1)




if __name__ == "__main__":
    main()