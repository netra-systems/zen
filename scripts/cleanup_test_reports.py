#!/usr/bin/env python
"""
Clean up and organize test reports directory
Removes old artifacts and organizes reports properly
"""

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import json

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def cleanup_test_reports(keep_days: int = 7, dry_run: bool = False):
    """Clean up test reports directory"""
    
    reports_dir = PROJECT_ROOT / "test_reports"
    if not reports_dir.exists():
        print("[ERROR] Test reports directory not found")
        return
    
    # Create organized structure
    latest_dir = reports_dir / "latest"
    history_dir = reports_dir / "history"
    metrics_dir = reports_dir / "metrics"
    analysis_dir = reports_dir / "analysis"
    
    for dir_path in [latest_dir, history_dir, metrics_dir, analysis_dir]:
        if not dir_path.exists():
            dir_path.mkdir(exist_ok=True)
            print(f"[OK] Created directory: {dir_path.name}/")
    
    cutoff_date = datetime.now() - timedelta(days=keep_days)
    
    files_to_delete = []
    files_to_move = []
    
    # Find all test report files in root directory
    for pattern in ["test_report_*.md", "test_report_*.json"]:
        for file in reports_dir.glob(pattern):
            # Parse timestamp from filename
            try:
                parts = file.stem.split('_')
                if len(parts) >= 4:
                    timestamp_str = f"{parts[-2]}_{parts[-1]}"
                    file_date = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                    
                    # Decide action based on age and type
                    if file.suffix == '.json':
                        # Delete all JSON files (we have better metrics now)
                        files_to_delete.append(file)
                    elif file_date < cutoff_date:
                        # Delete old MD files
                        files_to_delete.append(file)
                    else:
                        # Move recent MD files to history
                        files_to_move.append((file, history_dir / file.name))
            except Exception as e:
                print(f"[WARNING] Could not parse file: {file.name} - {e}")
    
    # Find latest reports that should be in latest/ directory
    for pattern in ["latest_*.md"]:
        for file in reports_dir.glob(pattern):
            files_to_move.append((file, latest_dir / file.name))
    
    # Clean up old history files
    if history_dir.exists():
        for file in history_dir.glob("*.md"):
            try:
                parts = file.stem.split('_')
                if len(parts) >= 4:
                    timestamp_str = f"{parts[-2]}_{parts[-1]}"
                    file_date = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                    if file_date < cutoff_date:
                        files_to_delete.append(file)
            except:
                pass
    
    # Execute cleanup
    print(f"\n{'[DRY RUN]' if dry_run else '[CLEANUP]'} Summary:")
    print(f"  Files to delete: {len(files_to_delete)}")
    print(f"  Files to move: {len(files_to_move)}")
    
    if not dry_run:
        # Delete files
        for file in files_to_delete:
            try:
                file.unlink()
                print(f"  [DELETE] {file.name}")
            except Exception as e:
                print(f"  [ERROR] Error deleting {file.name}: {e}")
        
        # Move files
        for src, dst in files_to_move:
            try:
                shutil.move(str(src), str(dst))
                print(f"  [MOVE] {src.name} -> {dst.parent.name}/{dst.name}")
            except Exception as e:
                print(f"  [ERROR] Error moving {src.name}: {e}")
        
        print("\n[SUCCESS] Cleanup complete!")
    else:
        print("\n[INFO] Files that would be deleted:")
        for file in files_to_delete[:10]:
            print(f"    - {file.name}")
        if len(files_to_delete) > 10:
            print(f"    ... and {len(files_to_delete) - 10} more")
        
        print("\n[INFO] Files that would be moved:")
        for src, dst in files_to_move[:10]:
            print(f"    - {src.name} -> {dst.parent.name}/")
        if len(files_to_move) > 10:
            print(f"    ... and {len(files_to_move) - 10} more")
    
    # Additional cleanup for misc files
    misc_patterns = [
        "*.pyc",
        "__pycache__",
        ".pytest_cache",
        "test_output.txt",
        "full_test_results.txt",
        "initial_test_output.txt"
    ]
    
    print("\n[INFO] Checking for misc files to clean...")
    misc_cleaned = 0
    
    for pattern in misc_patterns:
        for file in reports_dir.glob(pattern):
            if not dry_run:
                try:
                    if file.is_dir():
                        shutil.rmtree(file)
                    else:
                        file.unlink()
                    misc_cleaned += 1
                    print(f"  [DELETE] {file.name}")
                except Exception as e:
                    print(f"  [WARNING] Could not remove {file.name}: {e}")
            else:
                print(f"  Would remove: {file.name}")
                misc_cleaned += 1
    
    if misc_cleaned == 0:
        print("  [OK] No misc files to clean")
    
    # Report on directory structure
    print("\n[INFO] Final Directory Structure:")
    for dir_path in [latest_dir, history_dir, metrics_dir, analysis_dir]:
        if dir_path.exists():
            file_count = len(list(dir_path.glob("*")))
            print(f"  {dir_path.name}/: {file_count} files")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean up test reports directory")
    parser.add_argument(
        "--keep-days",
        type=int,
        default=7,
        help="Number of days to keep historical reports (default: 7)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be cleaned without actually doing it"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("TEST REPORTS CLEANUP UTILITY")
    print("=" * 60)
    
    cleanup_test_reports(keep_days=args.keep_days, dry_run=args.dry_run)


if __name__ == "__main__":
    main()