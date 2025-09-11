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
    print("WARNING: DEPLOYMENT SCRIPT DEPRECATED")
    print("=" * 70)
    print("This GCP deployment script is deprecated.")
    print("Please migrate to the official deployment script:")
    print()
    print("  NEW: python scripts/deploy_to_gcp_actual.py")
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
    actual_deploy_script = project_root / "scripts" / "deploy_to_gcp_actual.py"
    
    if not actual_deploy_script.exists():
        print(f"ERROR: Official deployment script not found at {actual_deploy_script}")
        print("Please check that scripts/deploy_to_gcp_actual.py exists")
        sys.exit(1)
    
    try:
        # Build command for actual deployment script
        cmd = [sys.executable, str(actual_deploy_script)] + sys.argv[1:]
        
        print(f"Redirecting to official deployment script:")
        print(f"   {' '.join(cmd)}")
        print()
        
        # Execute actual deployment script
        result = subprocess.run(cmd, cwd=project_root)
        
        # Preserve original exit code behavior
        sys.exit(result.returncode)
        
    except KeyboardInterrupt:
        print("\nDeployment interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to execute official deployment script: {e}")
        print("Please run the deployment script directly:")
        print(f"   python scripts/deploy_to_gcp_actual.py {' '.join(sys.argv[1:])}")
        sys.exit(1)




if __name__ == "__main__":
    main()