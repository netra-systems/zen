#!/usr/bin/env python3
"""
Cleanup script for generated docs, reports, and agent communication files.
Removes files older than 1 day from designated directories.
"""

import json
import os
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple

# Configuration
MAX_AGE_DAYS = 1  # Files older than this will be deleted
DRY_RUN = False  # Set to True to see what would be deleted without actually deleting

# Directories to clean
CLEANUP_PATHS = [
    # Reports directory
    ("reports", {
        "patterns": ["*.json", "*.md", "*.html", "*.txt", "*.log", "*.csv", "*.xml"],
        "exclude_files": ["LLM_MASTER_INDEX.md", "CLAUDE.md"],  # Important system files to keep
        "subdirs": ["tests", "coverage", "system-startup", "history", "frontend-coverage"]
    }),
    
    # Generated content corpuses
    ("app/data/generated/content_corpuses", {
        "patterns": ["*/content_corpus.json"],
        "exclude_files": [],
        "subdirs": []
    }),
    
    # Generated jobs
    ("app/data/generated/jobs", {
        "patterns": ["*.json"],
        "exclude_files": [],
        "subdirs": []
    }),
    
    # Test reports in app directory
    ("app/tests/performance/test_reports", {
        "patterns": ["**/*.json", "**/*.html"],
        "exclude_files": [],
        "subdirs": ["performance"]
    }),
    
    # Frontend test results
    ("frontend", {
        "patterns": ["cypress-results.json"],
        "exclude_files": [],
        "subdirs": []
    }),
    
    # Test output logs in root
    (".", {
        "patterns": ["test_*.log", "*_test_output.log", "*_test_run*.log"],
        "exclude_files": [],
        "subdirs": []
    }),
    
    # Test reports directory
    ("test_reports", {
        "patterns": ["*.json", "*.md", "*.html"],
        "exclude_files": [],
        "subdirs": []
    })
]

def get_file_age_days(filepath: Path) -> float:
    """Get the age of a file in days."""
    if not filepath.exists():
        return 0
    
    file_time = filepath.stat().st_mtime
    current_time = time.time()
    age_seconds = current_time - file_time
    age_days = age_seconds / (24 * 3600)
    return age_days

def should_delete_file(filepath: Path, max_age_days: float, exclude_files: List[str]) -> bool:
    """Determine if a file should be deleted based on age and exclusion list."""
    # Check if file is in exclusion list
    if filepath.name in exclude_files:
        return False
    
    # Check file age
    age_days = get_file_age_days(filepath)
    return age_days > max_age_days

def cleanup_directory(base_path: str, config: dict) -> Tuple[int, int, List[str]]:
    """
    Clean up files in a directory based on configuration.
    
    Returns:
        Tuple of (files_deleted, bytes_freed, list_of_deleted_files)
    """
    base_dir = Path(base_path)
    if not base_dir.exists():
        print(f"   WARNING: [U+FE0F]  Directory does not exist: {base_path}")
        return 0, 0, []
    
    files_deleted = 0
    bytes_freed = 0
    deleted_files = []
    
    patterns = config.get("patterns", [])
    exclude_files = config.get("exclude_files", [])
    
    for pattern in patterns:
        for filepath in base_dir.glob(pattern):
            if filepath.is_file():
                if should_delete_file(filepath, MAX_AGE_DAYS, exclude_files):
                    file_size = filepath.stat().st_size
                    file_age = get_file_age_days(filepath)
                    
                    if DRY_RUN:
                        print(f"    [DRY RUN] Would delete: {filepath.relative_to(Path.cwd())} "
                              f"(age: {file_age:.1f} days, size: {file_size:,} bytes)")
                    else:
                        try:
                            filepath.unlink()
                            print(f"    [DELETED] {filepath.relative_to(Path.cwd())} "
                                  f"(age: {file_age:.1f} days, size: {file_size:,} bytes)")
                            files_deleted += 1
                            bytes_freed += file_size
                            deleted_files.append(str(filepath.relative_to(Path.cwd())))
                        except Exception as e:
                            print(f"    [ERROR] Error deleting {filepath}: {e}")
    
    # Clean up empty directories (except the base directory itself)
    if not DRY_RUN and files_deleted > 0:
        for dirpath in sorted(base_dir.rglob("*"), reverse=True):
            if dirpath.is_dir() and dirpath != base_dir:
                try:
                    if not any(dirpath.iterdir()):
                        dirpath.rmdir()
                        print(f"    [REMOVED DIR] {dirpath.relative_to(Path.cwd())}")
                except Exception:
                    pass  # Directory not empty or other error
    
    return files_deleted, bytes_freed, deleted_files

def format_bytes(size_bytes: int) -> str:
    """Format bytes into human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def scan_for_cleanup(base_path: str, config: dict) -> Tuple[List[Path], int, List[Path]]:
    """
    Scan directory for files that would be cleaned up.
    
    Returns:
        Tuple of (files_to_delete, total_bytes, sample_files)
    """
    base_dir = Path(base_path)
    if not base_dir.exists():
        return [], 0, []
    
    files_to_delete = []
    total_bytes = 0
    
    patterns = config.get("patterns", [])
    exclude_files = config.get("exclude_files", [])
    
    for pattern in patterns:
        for filepath in base_dir.glob(pattern):
            if filepath.is_file():
                if should_delete_file(filepath, MAX_AGE_DAYS, exclude_files):
                    files_to_delete.append(filepath)
                    total_bytes += filepath.stat().st_size
    
    # Get sample files (up to 5)
    sample_files = files_to_delete[:5] if len(files_to_delete) > 5 else files_to_delete
    
    return files_to_delete, total_bytes, sample_files

def print_scan_summary(scan_results: dict):
    """Print a detailed summary of what will be deleted."""
    print("\n" + "=" * 60)
    print("SCAN SUMMARY - Files to be deleted")
    print("=" * 60)
    
    total_files = 0
    total_bytes = 0
    
    for base_path, result in scan_results.items():
        files, bytes_size, samples = result
        if files:
            print(f"\n[{base_path}]")
            print(f"   Files found: {len(files)}")
            print(f"   Total size: {format_bytes(bytes_size)}")
            
            if samples:
                print("   Sample files:")
                for sample in samples[:3]:  # Show max 3 samples per directory
                    age = get_file_age_days(sample)
                    size = sample.stat().st_size
                    print(f"     - {sample.name} (age: {age:.1f} days, size: {format_bytes(size)})")
            
            total_files += len(files)
            total_bytes += bytes_size
    
    print("\n" + "-" * 60)
    print(f"TOTAL: {total_files} files, {format_bytes(total_bytes)}")
    print("-" * 60)
    
    return total_files, total_bytes

def get_user_confirmation() -> bool:
    """Get user confirmation before proceeding with deletion."""
    print("\nWARNING: This action cannot be undone!")
    response = input("Do you want to proceed with deletion? (yes/no): ").strip().lower()
    return response in ['yes', 'y']

def main():
    """Main cleanup function."""
    print("=" * 60)
    print("NETRA GENERATED FILES CLEANUP")
    print("=" * 60)
    print(f"Configuration:")
    print(f"  - Max file age: {MAX_AGE_DAYS} day(s)")
    print(f"  - Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # First, scan all directories to show what will be deleted
    print("Scanning directories for old files...")
    scan_results = {}
    
    for base_path, config in CLEANUP_PATHS:
        files, bytes_size, samples = scan_for_cleanup(base_path, config)
        if files:
            scan_results[base_path] = (files, bytes_size, samples)
    
    if not scan_results:
        print("\n[OK] No files found older than {} day(s). Nothing to clean up!".format(MAX_AGE_DAYS))
        return
    
    # Show summary
    total_files, total_bytes = print_scan_summary(scan_results)
    
    # Ask for confirmation
    if DRY_RUN:
        print("\n[DRY RUN MODE] No files will be deleted.")
        return
    
    if not get_user_confirmation():
        print("\n[CANCELLED] Cleanup cancelled by user.")
        return
    
    # Proceed with deletion
    print("\n" + "=" * 60)
    print("PERFORMING CLEANUP")
    print("=" * 60)
    
    total_files_deleted = 0
    total_bytes_freed = 0
    all_deleted_files = []
    
    for base_path, config in CLEANUP_PATHS:
        if base_path in scan_results:
            print(f"\nCleaning: {base_path}")
            files_deleted, bytes_freed, deleted_files = cleanup_directory(base_path, config)
            
            total_files_deleted += files_deleted
            total_bytes_freed += bytes_freed
            all_deleted_files.extend(deleted_files)
            
            if files_deleted > 0:
                print(f"  [OK] Deleted {files_deleted} files, freed {format_bytes(bytes_freed)}")
    
    # Final summary
    print("=" * 60)
    print("CLEANUP SUMMARY")
    print("=" * 60)
    
    if DRY_RUN:
        print(f"[DRY RUN MODE] Would have deleted:")
    else:
        print(f"Cleanup complete:")
    
    print(f"  - Files deleted: {total_files_deleted}")
    print(f"  - Space freed: {format_bytes(total_bytes_freed)}")
    
    # Create cleanup log
    if not DRY_RUN and total_files_deleted > 0:
        log_file = Path("reports/cleanup_log.json")
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "files_deleted": total_files_deleted,
            "bytes_freed": total_bytes_freed,
            "max_age_days": MAX_AGE_DAYS,
            "deleted_files": all_deleted_files
        }
        
        # Append to existing log or create new
        if log_file.exists():
            try:
                with open(log_file, 'r') as f:
                    log_data = json.load(f)
                    if not isinstance(log_data, list):
                        log_data = [log_data]
            except:
                log_data = []
        else:
            log_data = []
        
        log_data.append(log_entry)
        
        # Keep only last 30 entries
        log_data = log_data[-30:]
        
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        print(f"\nLog saved to: {log_file}")
    
    print("\n[COMPLETED] Cleanup script completed successfully")

if __name__ == "__main__":
    # Allow command line arguments
    import sys
    
    if len(sys.argv) > 1:
        if "--dry-run" in sys.argv:
            DRY_RUN = True
        if "--days" in sys.argv:
            try:
                days_idx = sys.argv.index("--days")
                if days_idx + 1 < len(sys.argv):
                    MAX_AGE_DAYS = float(sys.argv[days_idx + 1])
            except (ValueError, IndexError):
                print("Invalid --days argument. Using default.")
        if "--help" in sys.argv or "-h" in sys.argv:
            print("Usage: python cleanup_generated_files.py [--dry-run] [--days N]")
            print("  --dry-run  : Show what would be deleted without actually deleting")
            print("  --days N   : Set max age in days (default: 1)")
            print("  --help, -h : Show this help message")
            sys.exit(0)
    
    main()