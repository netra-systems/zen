#!/usr/bin/env python3
"""
DEPRECATION WARNING: This deployment script is deprecated in favor of UnifiedTestRunner SSOT.

This GCP deployment script now redirects to the unified test runner's deployment mode
to maintain SSOT compliance while preserving all existing deployment functionality.

CRITICAL: Please migrate to using the unified test runner directly:
    python tests/unified_test_runner.py --execution-mode deploy --project netra-staging --build-local

Migration Path:
    OLD: python scripts/deploy_to_gcp.py --project netra-staging --build-local
    NEW: python tests/unified_test_runner.py --execution-mode deploy --project netra-staging --build-local

All original flags and options are preserved and forwarded to the SSOT implementation.
"""

import sys
import subprocess
from pathlib import Path
import argparse
import os


def show_deprecation_warning():
    """Show deprecation warning to users."""
    print("WARNING: DEPRECATION WARNING")
    print("=" * 70)
    print("This GCP deployment script is deprecated.")
    print("Please migrate to UnifiedTestRunner SSOT:")
    print()
    print("  NEW: python tests/unified_test_runner.py --execution-mode deploy")
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
    unified_runner = project_root / "tests" / "unified_test_runner.py"
    
    if not unified_runner.exists():
        print(f"ERROR: UnifiedTestRunner not found at {unified_runner}")
        print("Falling back to original deployment script...")
        return execute_fallback_deployment()
    
    try:
        # Build unified test runner command with deployment mode
        cmd = [
            sys.executable, str(unified_runner),
            "--execution-mode", "deploy"
        ]
        
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
        
        print(f"Executing deployment via UnifiedTestRunner:")
        print(f"   {' '.join(cmd)}")
        print()
        
        # Execute unified test runner in deployment mode
        result = subprocess.run(cmd, cwd=project_root)
        
        # Preserve original exit code behavior
        sys.exit(result.returncode)
        
    except Exception as e:
        print(f"ERROR: Failed to execute UnifiedTestRunner deployment: {e}")
        print("Falling back to original deployment script...")
        return execute_fallback_deployment()


def execute_fallback_deployment():
    """Execute original deployment script as fallback."""
    try:
        # Import and execute original functionality as fallback
        project_root = Path(__file__).parent.parent
        
        # Import the backed up original implementation
        backup_file = Path(__file__).parent / "deploy_to_gcp.py.backup"
        if backup_file.exists():
            print("Using backup deployment implementation...")
            
            # Add project root to path
            sys.path.insert(0, str(project_root))
            
            import importlib.util
            spec = importlib.util.spec_from_file_location("deploy_backup", backup_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Execute main from backup with original arguments
            # Reset sys.argv to original arguments for the backup script
            original_argv = sys.argv[:]
            original_argv[0] = str(backup_file)  # Update script name
            sys.argv = original_argv
            
            module.main()
        else:
            print("CRITICAL: No backup available for deployment script")
            print("Please restore original deploy_to_gcp.py or use manual deployment")
            sys.exit(1)
            
    except Exception as fallback_error:
        print(f"CRITICAL: Fallback deployment failed: {fallback_error}")
        print("Manual deployment required. Check GCP console.")
        sys.exit(1)


if __name__ == "__main__":
    main()