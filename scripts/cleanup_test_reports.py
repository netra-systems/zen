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
    reports_dir = _validate_reports_directory()
    if not reports_dir:
        return
    directories = _create_organized_directories(reports_dir)
    cutoff_date = datetime.now() - timedelta(days=keep_days)
    files_to_delete, files_to_move = _collect_files_for_cleanup(reports_dir, directories, cutoff_date)
    _execute_cleanup_actions(files_to_delete, files_to_move, dry_run)
    _cleanup_misc_files(reports_dir, dry_run)
    _report_final_structure(directories)

def _validate_reports_directory():
    """Validate and return reports directory"""
    reports_dir = PROJECT_ROOT / "test_reports"
    if not reports_dir.exists():
        print("[ERROR] Test reports directory not found")
        return None
    return reports_dir

def _create_organized_directories(reports_dir):
    """Create organized directory structure"""
    directories = {
        "latest": reports_dir / "latest",
        "history": reports_dir / "history",
        "metrics": reports_dir / "metrics",
        "analysis": reports_dir / "analysis"
    }
    for name, dir_path in directories.items():
        _ensure_directory_exists(dir_path)
    return directories

def _ensure_directory_exists(dir_path):
    """Ensure directory exists and log creation"""
    if not dir_path.exists():
        dir_path.mkdir(exist_ok=True)
        print(f"[OK] Created directory: {dir_path.name}/")

def _collect_files_for_cleanup(reports_dir, directories, cutoff_date):
    """Collect files that need deletion or moving"""
    files_to_delete = []
    files_to_move = []
    _collect_test_report_files(reports_dir, cutoff_date, files_to_delete, files_to_move, directories)
    _collect_latest_files(reports_dir, directories, files_to_move)
    _collect_old_history_files(directories["history"], cutoff_date, files_to_delete)
    return files_to_delete, files_to_move

def _collect_test_report_files(reports_dir, cutoff_date, files_to_delete, files_to_move, directories):
    """Collect test report files for processing"""
    for pattern in ["test_report_*.md", "test_report_*.json"]:
        for file in reports_dir.glob(pattern):
            _process_test_report_file(file, cutoff_date, files_to_delete, files_to_move, directories)

def _process_test_report_file(file, cutoff_date, files_to_delete, files_to_move, directories):
    """Process individual test report file"""
    try:
        parts = file.stem.split('_')
        if len(parts) >= 4:
            timestamp_str = f"{parts[-2]}_{parts[-1]}"
            file_date = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
            _categorize_file_action(file, file_date, cutoff_date, files_to_delete, files_to_move, directories)
    except Exception as e:
        print(f"[WARNING] Could not parse file: {file.name} - {e}")

def _categorize_file_action(file, file_date, cutoff_date, files_to_delete, files_to_move, directories):
    """Categorize file for deletion or moving"""
    if file.suffix == '.json':
        files_to_delete.append(file)
    elif file_date < cutoff_date:
        files_to_delete.append(file)
    else:
        files_to_move.append((file, directories["history"] / file.name))

def _collect_latest_files(reports_dir, directories, files_to_move):
    """Collect latest report files for moving"""
    for pattern in ["latest_*.md"]:
        for file in reports_dir.glob(pattern):
            files_to_move.append((file, directories["latest"] / file.name))

def _collect_old_history_files(history_dir, cutoff_date, files_to_delete):
    """Collect old history files for deletion"""
    if not history_dir.exists():
        return
    for file in history_dir.glob("*.md"):
        _check_history_file_age(file, cutoff_date, files_to_delete)

def _check_history_file_age(file, cutoff_date, files_to_delete):
    """Check if history file is old enough for deletion"""
    try:
        parts = file.stem.split('_')
        if len(parts) >= 4:
            timestamp_str = f"{parts[-2]}_{parts[-1]}"
            file_date = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
            if file_date < cutoff_date:
                files_to_delete.append(file)
    except:
        pass

def _execute_cleanup_actions(files_to_delete, files_to_move, dry_run):
    """Execute cleanup or show what would be done"""
    _print_cleanup_summary(files_to_delete, files_to_move, dry_run)
    if not dry_run:
        _perform_actual_cleanup(files_to_delete, files_to_move)
    else:
        _show_dry_run_preview(files_to_delete, files_to_move)

def _print_cleanup_summary(files_to_delete, files_to_move, dry_run):
    """Print summary of cleanup actions"""
    print(f"\n{'[DRY RUN]' if dry_run else '[CLEANUP]'} Summary:")
    print(f"  Files to delete: {len(files_to_delete)}")
    print(f"  Files to move: {len(files_to_move)}")

def _perform_actual_cleanup(files_to_delete, files_to_move):
    """Perform actual file operations"""
    _delete_files(files_to_delete)
    _move_files(files_to_move)
    print("\n[SUCCESS] Cleanup complete!")

def _delete_files(files_to_delete):
    """Delete specified files"""
    for file in files_to_delete:
        try:
            file.unlink()
            print(f"  [DELETE] {file.name}")
        except Exception as e:
            print(f"  [ERROR] Error deleting {file.name}: {e}")

def _move_files(files_to_move):
    """Move specified files"""
    for src, dst in files_to_move:
        try:
            shutil.move(str(src), str(dst))
            print(f"  [MOVE] {src.name} -> {dst.parent.name}/{dst.name}")
        except Exception as e:
            print(f"  [ERROR] Error moving {src.name}: {e}")

def _show_dry_run_preview(files_to_delete, files_to_move):
    """Show preview of what would be done in dry run"""
    _preview_deletions(files_to_delete)
    _preview_moves(files_to_move)

def _preview_deletions(files_to_delete):
    """Preview files that would be deleted"""
    print("\n[INFO] Files that would be deleted:")
    for file in files_to_delete[:10]:
        print(f"    - {file.name}")
    if len(files_to_delete) > 10:
        print(f"    ... and {len(files_to_delete) - 10} more")

def _preview_moves(files_to_move):
    """Preview files that would be moved"""
    print("\n[INFO] Files that would be moved:")
    for src, dst in files_to_move[:10]:
        print(f"    - {src.name} -> {dst.parent.name}/")
    if len(files_to_move) > 10:
        print(f"    ... and {len(files_to_move) - 10} more")

def _cleanup_misc_files(reports_dir, dry_run):
    """Clean up miscellaneous files"""
    patterns = ["*.pyc", "__pycache__", ".pytest_cache", "test_output.txt", "full_test_results.txt", "initial_test_output.txt"]
    print("\n[INFO] Checking for misc files to clean...")
    misc_cleaned = 0
    for pattern in patterns:
        misc_cleaned += _clean_misc_pattern(reports_dir, pattern, dry_run)
    _report_misc_cleanup(misc_cleaned)

def _clean_misc_pattern(reports_dir, pattern, dry_run):
    """Clean files matching a specific pattern"""
    cleaned_count = 0
    for file in reports_dir.glob(pattern):
        if _process_misc_file(file, dry_run):
            cleaned_count += 1
    return cleaned_count

def _process_misc_file(file, dry_run):
    """Process a single miscellaneous file"""
    if not dry_run:
        return _delete_misc_file(file)
    else:
        print(f"  Would remove: {file.name}")
        return True

def _delete_misc_file(file):
    """Delete a miscellaneous file or directory"""
    try:
        if file.is_dir():
            shutil.rmtree(file)
        else:
            file.unlink()
        print(f"  [DELETE] {file.name}")
        return True
    except Exception as e:
        print(f"  [WARNING] Could not remove {file.name}: {e}")
        return False

def _report_misc_cleanup(misc_cleaned):
    """Report on miscellaneous file cleanup"""
    if misc_cleaned == 0:
        print("  [OK] No misc files to clean")

def _report_final_structure(directories):
    """Report final directory structure"""
    print("\n[INFO] Final Directory Structure:")
    for name, dir_path in directories.items():
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