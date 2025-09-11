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

All original flags and options are preserved and forwarded to the canonical implementation.
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
    print("This deployment entry point is deprecated.")
    print("Please migrate to the canonical deployment script:")
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
        result = subprocess.run(cmd, cwd=project_root)
        
        # Preserve original exit code behavior
        sys.exit(result.returncode)
        
    except KeyboardInterrupt:
        print("\nDeployment interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to execute canonical deployment script: {e}")
        print(f"Manual intervention required")
        sys.exit(1)


if __name__ == "__main__":
    main()