#!/usr/bin/env python3
"""
DEPRECATION WARNING: This deployment script is deprecated.

CRITICAL: The OFFICIAL deployment script is now scripts/deploy_to_gcp_actual.py

Migration Path:
    OLD: python scripts/deploy_to_gcp.py --project netra-staging --build-local
    NEW: python scripts/deploy_to_gcp_actual.py --project netra-staging --build-local

All original flags and options are preserved in the new script.

WARNING: The UnifiedTestRunner does NOT have deployment functionality.
This script will redirect to the actual deployment script for compatibility.
"""

import sys
import subprocess
from pathlib import Path
import argparse
import os


def show_deprecation_warning():
    """Show deprecation warning to users."""
    print("WARNING: DEPLOYMENT SCRIPT DEPRECATED")
    print("=" * 70)
    print("This GCP deployment script is deprecated.")
    print("Please migrate to the official deployment script:")
    print()
    print("  NEW: python scripts/deploy_to_gcp_actual.py")
    print()
    print("All deployment functionality preserved. Redirecting...")
    print("=" * 70)
    print()


def parse_deployment_args():
    """Parse all deployment arguments for compatibility."""
    parser = argparse.ArgumentParser(
        description="[DEPRECATED] Deploy Netra Apex Platform to Google Cloud Run"
    )
    
    # Core deployment options
    parser.add_argument("--project", required=True, help="GCP project ID")
    parser.add_argument("--build-local", action="store_true", help="Build images locally")
    parser.add_argument("--check-secrets", action="store_true", help="Validate secrets from Google Secret Manager")
    parser.add_argument("--check-apis", action="store_true", help="Check GCP API availability")
    parser.add_argument("--run-checks", action="store_true", help="Run all pre-deployment checks")
    parser.add_argument("--rollback", action="store_true", help="Rollback to previous version")
    parser.add_argument("--service", help="Deploy specific service only")
    parser.add_argument("--env", help="Target environment")
    parser.add_argument("--timeout", type=int, help="Deployment timeout in seconds")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    
    return parser.parse_known_args()


def main():
    """Main entry point with deprecation wrapper."""
    show_deprecation_warning()
    
    # Parse all deployment arguments
    args, unknown_args = parse_deployment_args()
    
    # Get project root
    project_root = Path(__file__).parent.parent
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
        result = subprocess.run(cmd, cwd=project_root)
        
        # Preserve original exit code behavior
        sys.exit(result.returncode)
        
    except Exception as e:
        print(f"ERROR: Failed to execute official deployment script: {e}")
        print("Please run the deployment script directly:")
        print(f"   python scripts/deploy_to_gcp_actual.py {' '.join(sys.argv[1:])}")
        sys.exit(1)




if __name__ == "__main__":
    main()