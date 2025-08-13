#!/usr/bin/env python
"""
Cleanup Test Reports - Organize and clean test reports directory.
Removes timestamped reports and maintains only the unified reporting structure.
"""

import shutil
from pathlib import Path
from datetime import datetime
import json


def cleanup_test_reports():
    """Clean up and reorganize test reports directory."""
    reports_dir = Path("test_reports")
    
    if not reports_dir.exists():
        print("No test_reports directory found")
        return
    
    print("Cleaning up test reports directory...")
    
    # Remove modular directory with timestamped reports
    modular_dir = reports_dir / "modular"
    if modular_dir.exists():
        shutil.rmtree(modular_dir)
        print("[OK] Removed modular directory with timestamped reports")
    
    # Clean up history directory (remove old timestamped files)
    history_dir = reports_dir / "history"
    if history_dir.exists():
        for file in history_dir.glob("test_report_*_*.md"):
            file.unlink()
            print(f"  Removed: {file.name}")
        for file in history_dir.glob("test_report_*_*.json"):
            file.unlink()
            print(f"  Removed: {file.name}")
    
    # Clean up duplicate latest reports
    for file in reports_dir.glob("latest_*.md"):
        file.unlink()
        print(f"  Removed duplicate: {file.name}")
    
    # Ensure proper directory structure
    ensure_directory_structure(reports_dir)
    
    # Initialize unified reporting files if needed
    initialize_unified_reports(reports_dir)
    
    print("\n[OK] Test reports cleanup complete!")
    print("\nNew Structure:")
    print("  test_reports/")
    print("    - unified_report.md     # Main report with all info")
    print("    - dashboard.md          # Last 3 runs overview")
    print("    - latest/")
    print("        - delta_summary.md  # What changed")
    print("        - critical_changes.md # Critical issues only")
    print("        - {level}_report.md # Legacy format")
    print("    - metrics/")
    print("        - test_history.json # Historical data")


def ensure_directory_structure(reports_dir: Path):
    """Ensure proper directory structure exists."""
    # Create required directories
    (reports_dir / "latest").mkdir(exist_ok=True)
    (reports_dir / "metrics").mkdir(exist_ok=True)
    
    # Remove unnecessary directories
    unnecessary_dirs = ["batch_results", "categories", "fixes", 
                       "analysis", "logs", "temp", "uploads"]
    
    for dir_name in unnecessary_dirs:
        dir_path = reports_dir / dir_name
        if dir_path.exists() and dir_path.is_dir():
            # Keep if contains important data, otherwise remove
            if not any(dir_path.glob("*")):
                shutil.rmtree(dir_path)
                print(f"  Removed empty directory: {dir_name}")


def initialize_unified_reports(reports_dir: Path):
    """Initialize unified reporting files if they don't exist."""
    # Create initial dashboard
    dashboard_file = reports_dir / "dashboard.md"
    if not dashboard_file.exists():
        dashboard_content = """# Test Dashboard

No test runs recorded yet.

Run tests with:
```bash
python test_runner.py --level smoke
```
"""
        dashboard_file.write_text(dashboard_content)
        print("  Created: dashboard.md")
    
    # Create initial unified report
    unified_file = reports_dir / "unified_report.md"
    if not unified_file.exists():
        unified_content = """# Unified Test Report

No test runs recorded yet.

This report will show:
- Current test results
- Changes from previous run
- Critical issues
- Test trends

Run tests to populate this report.
"""
        unified_file.write_text(unified_content)
        print("  Created: unified_report.md")
    
    # Initialize test history if needed
    history_file = reports_dir / "metrics" / "test_history.json"
    if not history_file.exists():
        initial_history = {
            "runs": [],
            "tests": {},
            "metadata": {
                "created": datetime.now().isoformat(),
                "version": "2.0"
            }
        }
        with open(history_file, 'w') as f:
            json.dump(initial_history, f, indent=2)
        print("  Initialized: test_history.json")


def migrate_existing_data(reports_dir: Path):
    """Migrate existing test data to new format if possible."""
    # Check for existing metrics files
    metrics_dir = reports_dir / "metrics"
    
    for metric_file in metrics_dir.glob("*_metrics.json"):
        # Keep these for now, they contain useful data
        print(f"  Preserved: {metric_file.name}")


if __name__ == "__main__":
    cleanup_test_reports()
    print("\nNext steps:")
    print("1. Run tests: python test_runner.py --level smoke")
    print("2. View dashboard: cat test_reports/dashboard.md")
    print("3. Check critical issues: cat test_reports/latest/critical_changes.md")