#!/usr/bin/env python3

"""
Fast Test Collection Script
===========================
Quick test collection for development and debugging

Usage:
    python3 scripts/fast_test_collection.py --pattern "*agent*"
    python3 scripts/fast_test_collection.py --category agent --count-only
"""

import sys
import time
import argparse
from pathlib import Path
import glob

PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

def fast_collect_tests(pattern: str = "*", category: str = "all") -> dict:
    """Fast test collection without heavy imports"""
    start_time = time.time()
    
    # Test directories to search
    test_dirs = [
        PROJECT_ROOT / "netra_backend" / "tests",
        PROJECT_ROOT / "tests",
        PROJECT_ROOT / "auth_service" / "tests",
        PROJECT_ROOT / "frontend" / "src" / "__tests__"
    ]
    
    results = {
        "total_files": 0,
        "by_directory": {},
        "files": []
    }
    
    for test_dir in test_dirs:
        if test_dir.exists():
            # Use glob for fast file discovery
            search_pattern = f"*{pattern.replace('*', '')}*.py"
            files = list(test_dir.rglob(search_pattern))
            
            valid_files = [f for f in files if f.is_file() and f.name.startswith("test_")]
            
            results["by_directory"][str(test_dir)] = len(valid_files)
            results["total_files"] += len(valid_files)
            results["files"].extend([str(f) for f in valid_files])
    
    results["collection_time"] = time.time() - start_time
    return results

def main():
    parser = argparse.ArgumentParser(description="Fast test collection")
    parser.add_argument('--pattern', default="*", help='Test pattern to search for')
    parser.add_argument('--category', default="all", help='Test category')
    parser.add_argument('--count-only', action='store_true', help='Only show counts')
    parser.add_argument('--time-limit', type=float, default=5.0, 
                       help='Maximum collection time in seconds')
    
    args = parser.parse_args()
    
    print(f"🔍 Fast collecting tests: pattern='{args.pattern}', category='{args.category}'")
    
    # Set timeout
    start_time = time.time()
    try:
        results = fast_collect_tests(args.pattern, args.category)
        
        collection_time = results["collection_time"]
        
        if collection_time > args.time_limit:
            print(f"⚠️  Collection time {collection_time:.2f}s exceeded limit {args.time_limit}s")
        else:
            print(f"✅ Collection completed in {collection_time:.2f}s")
        
        print(f"📊 Found {results['total_files']} test files")
        
        if not args.count_only:
            for directory, count in results["by_directory"].items():
                if count > 0:
                    print(f"   {Path(directory).name}: {count} files")
        
        # Performance rating
        if collection_time < 1.0:
            rating = "🚀 EXCELLENT"
        elif collection_time < 5.0:
            rating = "✅ GOOD"
        elif collection_time < 15.0:
            rating = "⚠️  FAIR"
        else:
            rating = "❌ POOR"
        
        print(f"Performance: {rating} ({collection_time:.2f}s)")
        
        return 0
        
    except Exception as e:
        print(f"❌ Collection failed: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
