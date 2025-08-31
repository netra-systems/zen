#!/usr/bin/env python3
"""
Test remediation on a small sample of high-priority files
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.remediate_os_environ_violations import OSEnvironRemediator

def main():
    """Test remediation on specific high-priority files"""
    project_root = Path(__file__).parent.parent
    
    # Test files to remediate (high priority, small scope)
    test_files = [
        project_root / "tests" / "unit" / "test_environment_isolation_simple.py",
        project_root / "netra_backend" / "tests" / "unit" / "test_environment_validator.py"
    ]
    
    # Filter to files that actually exist
    existing_files = [f for f in test_files if f.exists()]
    
    print(f"Testing remediation on {len(existing_files)} files...")
    
    remediator = OSEnvironRemediator(project_root)
    remediator.dry_run = True  # Safe dry-run mode
    
    # Remediate the specific files
    remediator.remediate_all_files(existing_files)
    
    # Print results
    remediator.print_summary()

if __name__ == '__main__':
    main()