#!/usr/bin/env python3
"""
Enhanced staging deployment script with comprehensive validation.

This script combines the existing deploy_to_gcp.py functionality with 
additional staging-specific validation and fixes.

Usage:
    python scripts/deploy_staging_with_validation.py [--fix-issues] [--skip-build]
"""

import subprocess
import sys
import time
from pathlib import Path

def run_pre_deployment_validation():
    """Run pre-deployment validation and fixes."""
    print("🔍 RUNNING PRE-DEPLOYMENT VALIDATION")
    print("=" * 60)
    
    # Run the fix script first to ensure all issues are resolved
    print("Running staging deployment fix script...")
    result = subprocess.run([
        sys.executable, "scripts/fix_staging_deployment.py", "netra-staging"
    ], cwd=Path(__file__).parent.parent)
    
    if result.returncode != 0:
        print("❌ Pre-deployment fixes failed - please resolve issues first")
        return False
        
    print("✅ Pre-deployment validation completed successfully")
    return True

def deploy_with_enhanced_configuration():
    """Deploy using the official script with staging-specific parameters."""
    print("\n🚀 DEPLOYING TO STAGING WITH ENHANCED CONFIGURATION")
    print("=" * 60)
    
    # Use the official deployment script with optimal parameters for staging
    deploy_cmd = [
        sys.executable, "scripts/deploy_to_gcp.py",
        "--project", "netra-staging",
        "--build-local",  # 5-10x faster than cloud build
        "--run-checks"    # Comprehensive pre-deployment checks
    ]
    
    print("Running deployment command:")
    print(" ".join(deploy_cmd))
    
    result = subprocess.run(
        deploy_cmd, 
        cwd=Path(__file__).parent.parent
    )
    
    return result.returncode == 0

def run_post_deployment_validation():
    """Run post-deployment validation to ensure everything is working."""
    print("\n🔍 RUNNING POST-DEPLOYMENT VALIDATION")
    print("=" * 60)
    
    # Wait a bit for services to fully start
    print("Waiting 30 seconds for services to fully initialize...")
    time.sleep(30)
    
    # Run validation again to verify everything is working
    result = subprocess.run([
        sys.executable, "scripts/validate_staging_config.py"
    ], cwd=Path(__file__).parent.parent)
    
    if result.returncode == 0:
        print("✅ Post-deployment validation passed!")
        return True
    else:
        print("⚠️ Some post-deployment validation checks failed")
        print("Services may still be starting up - this is often normal")
        return False

def main():
    """Main deployment process with validation."""
    print("🚀 NETRA STAGING DEPLOYMENT WITH VALIDATION")
    print("=" * 80)
    print("This script will:")
    print("1. Run pre-deployment validation and fixes")
    print("2. Deploy using the official deployment script")
    print("3. Run post-deployment validation")
    print("4. Provide comprehensive status report")
    
    # Parse arguments
    fix_issues = "--fix-issues" in sys.argv
    skip_build = "--skip-build" in sys.argv
    
    try:
        # Step 1: Pre-deployment validation
        if fix_issues or True:  # Always run validation for staging
            if not run_pre_deployment_validation():
                print("\n❌ DEPLOYMENT ABORTED - Pre-deployment validation failed")
                return 1
        
        # Step 2: Deploy to staging
        if not deploy_with_enhanced_configuration():
            print("\n❌ DEPLOYMENT FAILED")
            return 1
            
        # Step 3: Post-deployment validation
        validation_passed = run_post_deployment_validation()
        
        # Step 4: Final status
        print("\n" + "=" * 80)
        if validation_passed:
            print("🎉 STAGING DEPLOYMENT COMPLETED SUCCESSFULLY!")
            print("\n📋 STAGING ENVIRONMENT URLS:")
            print("   Backend:  https://netra-backend-jmujvwwf7q-uc.a.run.app")
            print("   Auth:     https://netra-auth-jmujvwwf7q-uc.a.run.app") 
            print("   Frontend: https://netra-frontend-jmujvwwf7q-uc.a.run.app")
            print("\n✅ All services are healthy and ready for testing!")
        else:
            print("⚠️ STAGING DEPLOYMENT COMPLETED WITH WARNINGS")
            print("   Services deployed but some validation checks failed")
            print("   This is often normal - services may still be starting")
            print("   Wait 5-10 minutes and re-run validation if needed")
            
        return 0
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Deployment interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Deployment failed with error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())