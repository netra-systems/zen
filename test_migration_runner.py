#!/usr/bin/env python3
"""Test script for migration runner."""

import os
import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dev_launcher.migration_runner import MigrationRunner

def test_migration_runner():
    """Test the migration runner functionality."""
    print("=" * 60)
    print("Testing Migration Runner")
    print("=" * 60)
    
    # Create migration runner
    runner = MigrationRunner(project_root, use_emoji=True)
    
    # Set test environment
    env = os.environ.copy()
    
    # Check and run migrations
    print("\nChecking migrations...")
    success = runner.check_and_run_migrations(env)
    
    if success:
        print("\n✅ Migration check completed successfully")
    else:
        print("\n⚠️ Migration check encountered issues")
    
    return success

if __name__ == "__main__":
    success = test_migration_runner()
    sys.exit(0 if success else 1)