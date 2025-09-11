#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DEPRECATION WARNING: This build script is deprecated.

WEEK 1 SSOT REMEDIATION (GitHub Issue #245): 
This script incorrectly refers to Docker Compose builds as "staging" deployment.

CANONICAL SOURCES:
  - Actual staging deployment: scripts/deploy_to_gcp_actual.py --project netra-staging
  - Local Docker development: docker-compose --profile dev up
  - Local Docker testing: docker-compose --profile test up

Migration Paths:
    OLD: python scripts/build_staging.py --action build
    NEW: docker-compose --profile dev build

    OLD: python scripts/build_staging.py --action start  
    NEW: docker-compose --profile dev up

    OLD: python scripts/build_staging.py --action full
    NEW: For staging: python scripts/deploy_to_gcp_actual.py --project netra-staging --build-local
         For local: docker-compose --profile dev up --build

This wrapper will be removed in Week 2 after validation of the transition.
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
    print("=" * 80)
    print("WARNING: DEPRECATION WARNING - WEEK 1 SSOT REMEDIATION")
    print("=" * 80)
    print("GitHub Issue #245: Deployment canonical source conflicts")
    print()
    print("This build script incorrectly refers to Docker Compose as 'staging'.")
    print()
    print("For ACTUAL staging deployment:")
    print("  CANONICAL: python scripts/deploy_to_gcp_actual.py --project netra-staging")
    print()
    print("For local Docker development:")
    print("  CANONICAL: docker-compose --profile dev up")
    print()
    print("For local Docker testing:")
    print("  CANONICAL: docker-compose --profile test up")
    print("=" * 80)
    print()


def parse_args():
    """Parse command line arguments for compatibility."""
    parser = argparse.ArgumentParser(
        description="[DEPRECATED] Build script - redirects to canonical sources"
    )
    parser.add_argument("--action", choices=["build", "start", "stop", "test", "health", "logs", "full"],
                       default="full", help="Action to perform")
    parser.add_argument("--service", help="Service name for logs")
    parser.add_argument("--skip-build", action="store_true", help="Skip building Docker images")
    parser.add_argument("--tag", default="latest", help="Docker image tag")
    parser.add_argument("--api-url", default="http://localhost:8080", help="API URL for frontend build")
    
    return parser.parse_args()


def redirect_to_docker_compose(action: str, args):
    """Redirect to appropriate docker-compose command."""
    project_root = Path(__file__).parent.parent
    
    if action in ["build", "start", "full"]:
        profile = "dev"  # Default to development profile
        
        if action == "build":
            cmd = ["docker-compose", "--profile", profile, "build"]
        elif action == "start":
            cmd = ["docker-compose", "--profile", profile, "up", "-d"]
        elif action == "full":
            cmd = ["docker-compose", "--profile", profile, "up", "--build", "-d"]
            
        print(f"Redirecting to Docker Compose:")
        print(f"   {' '.join(cmd)}")
        print()
        
        try:
            result = subprocess.run(cmd, cwd=project_root)
            
            if result.returncode == 0 and action in ["start", "full"]:
                print("\nServices started successfully!")
                print("   Frontend: http://localhost:3000")
                print("   Backend API: http://localhost:8080")
                print("   API Docs: http://localhost:8080/docs")
            
            return result.returncode
            
        except Exception as e:
            print(f"ERROR: Failed to execute docker-compose: {e}")
            return 1
            
    elif action == "stop":
        cmd = ["docker-compose", "down", "-v"]
        
        print(f"Redirecting to Docker Compose:")
        print(f"   {' '.join(cmd)}")
        print()
        
        try:
            result = subprocess.run(cmd, cwd=project_root)
            return result.returncode
        except Exception as e:
            print(f"ERROR: Failed to stop services: {e}")
            return 1
            
    elif action == "logs":
        cmd = ["docker-compose", "logs"]
        if args.service:
            cmd.append(args.service)
        else:
            cmd.extend(["--tail", "50"])
            
        print(f"Redirecting to Docker Compose:")
        print(f"   {' '.join(cmd)}")
        print()
        
        try:
            subprocess.run(cmd, cwd=project_root)
            return 0
        except Exception as e:
            print(f"ERROR: Failed to show logs: {e}")
            return 1
            
    elif action in ["test", "health"]:
        print("For testing, please use the UnifiedTestRunner:")
        print("   python tests/unified_test_runner.py --categories smoke")
        print()
        print("For health checks, use:")
        print("   curl http://localhost:8080/health")
        print("   curl http://localhost:3000")
        return 0
        
    else:
        print(f"Unknown action: {action}")
        return 1


def suggest_gcp_deployment():
    """Suggest GCP deployment for actual staging."""
    print("HINT: If you need ACTUAL staging deployment to GCP:")
    print("   python scripts/deploy_to_gcp_actual.py --project netra-staging --build-local")
    print()


def main():
    """Main entry point with deprecation wrapper."""
    show_deprecation_warning()
    
    args = parse_args()
    
    # Show GCP deployment suggestion
    suggest_gcp_deployment()
    
    # Redirect to appropriate canonical source
    exit_code = redirect_to_docker_compose(args.action, args)
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()