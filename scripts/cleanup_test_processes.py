#!/usr/bin/env python
"""
Test Process Cleanup Utility
Cleans up hanging Node.js and Python test processes on Windows
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import psutil

PROJECT_ROOT = Path(__file__).parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"

def kill_process_tree(pid: int) -> None:
    """Kill a process and all its children."""
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        
        # Kill children first
        for child in children:
            try:
                child.terminate()
            except psutil.NoSuchProcess:
                pass
        
        # Give them time to terminate
        psutil.wait_procs(children, timeout=3)
        
        # Force kill any remaining
        for child in children:
            try:
                if child.is_running():
                    child.kill()
            except psutil.NoSuchProcess:
                pass
        
        # Kill parent
        try:
            parent.terminate()
            parent.wait(timeout=3)
        except psutil.TimeoutExpired:
            parent.kill()
        except psutil.NoSuchProcess:
            pass
            
    except psutil.NoSuchProcess:
        pass
    except Exception as e:
        print(f"Error killing process {pid}: {e}")


def find_test_processes() -> list:
    """Find Node and Python processes related to testing."""
    test_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            name = proc.info['name']
            cmdline = proc.info.get('cmdline', []) or []
            cmdline_str = ' '.join(cmdline).lower()
            
            # Check for Node processes
            if 'node' in name.lower():
                # Jest, Cypress, or dev server
                if any(x in cmdline_str for x in ['jest', 'cypress', 'next', 'webpack', 'test']):
                    test_processes.append({
                        'pid': proc.info['pid'],
                        'name': name,
                        'type': 'node',
                        'cmdline': ' '.join(cmdline[:3]) if cmdline else ''
                    })
            
            # Check for Python test processes
            elif 'python' in name.lower():
                if any(x in cmdline_str for x in ['pytest', 'test_runner', 'test_frontend', 'test_backend']):
                    test_processes.append({
                        'pid': proc.info['pid'],
                        'name': name,
                        'type': 'python',
                        'cmdline': ' '.join(cmdline[:3]) if cmdline else ''
                    })
                    
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    return test_processes


def cleanup_test_processes(force: bool = False) -> int:
    """Clean up hanging test processes."""
    print("=" * 60)
    print("TEST PROCESS CLEANUP")
    print("=" * 60)
    
    processes = find_test_processes()
    
    if not processes:
        print("No test processes found running.")
        return 0
    
    print(f"\nFound {len(processes)} test-related process(es):")
    for proc in processes:
        print(f"  [{proc['type']:6}] PID {proc['pid']:6} - {proc['cmdline']}")
    
    if not force:
        response = input("\nKill these processes? (y/n): ")
        if response.lower() != 'y':
            print("Cleanup cancelled.")
            return 0
    
    print("\nKilling processes...")
    killed = 0
    for proc in processes:
        try:
            kill_process_tree(proc['pid'])
            print(f"  Killed PID {proc['pid']}")
            killed += 1
        except Exception as e:
            print(f"  Failed to kill PID {proc['pid']}: {e}")
    
    print(f"\nKilled {killed} process(es).")
    
    # Clean up Jest cache if it exists
    jest_cache = FRONTEND_DIR / "node_modules" / ".cache" / "jest"
    if jest_cache.exists():
        try:
            import shutil
            shutil.rmtree(jest_cache, ignore_errors=True)
            print("Cleared Jest cache.")
        except:
            pass
    
    return 0


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Clean up hanging test processes"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force kill without confirmation"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List processes only, don't kill"
    )
    
    args = parser.parse_args()
    
    if args.list:
        processes = find_test_processes()
        if processes:
            print("Test processes running:")
            for proc in processes:
                print(f"  [{proc['type']:6}] PID {proc['pid']:6} - {proc['cmdline']}")
        else:
            print("No test processes found.")
        return 0
    
    return cleanup_test_processes(args.force)


if __name__ == "__main__":
    sys.exit(main())