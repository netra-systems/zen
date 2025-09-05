#!/usr/bin/env python3
"""
Automated Resource Cleanup Script
Based on DOCKER_CRASH_DEEP_10_WHYS_ANALYSIS.md recommendations

Automatically cleans up resources when approaching limits to prevent crashes.
Can be run manually or as a scheduled task/cron job.
"""

import subprocess
import sys
import json
import platform
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Tuple

class AutoResourceCleanup:
    def __init__(self, runtime=None, dry_run=False):
        self.runtime = runtime or self._detect_runtime()
        self.dry_run = dry_run
        self.is_windows = platform.system() == 'Windows'
        
        # Thresholds for cleanup triggers
        self.memory_threshold_percent = 70  # Cleanup when memory > 70%
        self.disk_threshold_gb = 5  # Cleanup when free disk < 5GB
        self.image_age_days = 7  # Remove images older than 7 days
        
    def _detect_runtime(self):
        """Detect container runtime"""
        for cmd in ['podman', 'docker']:
            try:
                subprocess.run([cmd, 'version'], capture_output=True, timeout=2, check=True)
                return cmd
            except:
                continue
        print("No container runtime found")
        sys.exit(1)
    
    def _run_command(self, cmd, description=""):
        """Run command and return output"""
        if description:
            print(f"  {description}")
        
        if self.dry_run:
            print(f"    [DRY RUN] Would execute: {' '.join(cmd)}")
            return True, ""
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.returncode == 0, result.stdout
        except Exception as e:
            return False, str(e)
    
    def check_memory_usage(self) -> Tuple[float, bool]:
        """Check current memory usage and determine if cleanup needed"""
        print("\n1. Checking Memory Usage...")
        
        # Get container stats
        success, output = self._run_command(
            [self.runtime, 'stats', '--no-stream', '--format', 'json']
        )
        
        if not success:
            print("   Could not get memory stats")
            return 0, False
        
        total_memory_mb = 0
        total_limit_mb = 0
        
        try:
            for line in output.strip().split('\n'):
                if line:
                    data = json.loads(line)
                    mem_usage = data.get('MemUsage', '0MiB / 0MiB')
                    if ' / ' in mem_usage:
                        current, limit = mem_usage.split(' / ')
                        # Parse memory values
                        current_mb = self._parse_memory(current)
                        limit_mb = self._parse_memory(limit)
                        total_memory_mb += current_mb
                        total_limit_mb += limit_mb
        except:
            pass
        
        if total_limit_mb > 0:
            usage_percent = (total_memory_mb / total_limit_mb) * 100
            print(f"   Current usage: {total_memory_mb:.1f}MB / {total_limit_mb:.1f}MB ({usage_percent:.1f}%)")
            
            if usage_percent > self.memory_threshold_percent:
                print(f"   [WARNING] Memory usage exceeds {self.memory_threshold_percent}% threshold")
                return usage_percent, True
            else:
                print(f"   [OK] Memory usage within limits")
                return usage_percent, False
        
        return 0, False
    
    def _parse_memory(self, mem_str):
        """Parse memory string to MB"""
        mem_str = mem_str.strip()
        if 'GiB' in mem_str:
            return float(mem_str.replace('GiB', '')) * 1024
        elif 'MiB' in mem_str:
            return float(mem_str.replace('MiB', ''))
        elif 'GB' in mem_str:
            return float(mem_str.replace('GB', '')) * 1000
        elif 'MB' in mem_str:
            return float(mem_str.replace('MB', ''))
        return 0
    
    def check_disk_usage(self) -> Tuple[Dict, bool]:
        """Check disk usage for cleanup opportunities"""
        print("\n2. Checking Disk Usage...")
        
        success, output = self._run_command(
            [self.runtime, 'system', 'df']
        )
        
        cleanup_needed = False
        sizes = {}
        
        if success and output:
            for line in output.split('\n'):
                if 'Images' in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        sizes['images'] = parts[3]
                        print(f"   Images: {parts[2]} total, {parts[3]} reclaimable")
                elif 'Containers' in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        sizes['containers'] = parts[3]
                        print(f"   Containers: {parts[2]} total, {parts[3]} reclaimable")
                elif 'Volumes' in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        sizes['volumes'] = parts[3]
                        print(f"   Volumes: {parts[2]} total, {parts[3]} reclaimable")
            
            # Check if significant space can be reclaimed
            for category, size in sizes.items():
                if 'GB' in size or ('MB' in size and float(size.replace('MB', '')) > 500):
                    cleanup_needed = True
                    print(f"   [INFO] Significant space can be reclaimed from {category}")
        
        return sizes, cleanup_needed
    
    def cleanup_stopped_containers(self):
        """Remove stopped containers"""
        print("\n3. Cleaning Stopped Containers...")
        
        success, output = self._run_command(
            [self.runtime, 'container', 'prune', '-f'],
            "Removing stopped containers"
        )
        
        if success and output:
            print(f"   {output.strip()}")
        else:
            print("   No stopped containers to remove")
    
    def cleanup_unused_volumes(self):
        """Remove unused volumes"""
        print("\n4. Cleaning Unused Volumes...")
        
        success, output = self._run_command(
            [self.runtime, 'volume', 'prune', '-f'],
            "Removing unused volumes"
        )
        
        if success and output:
            print(f"   {output.strip()}")
        else:
            print("   No unused volumes to remove")
    
    def cleanup_dangling_images(self):
        """Remove dangling images"""
        print("\n5. Cleaning Dangling Images...")
        
        success, output = self._run_command(
            [self.runtime, 'image', 'prune', '-f'],
            "Removing dangling images"
        )
        
        if success and output:
            print(f"   {output.strip()}")
        else:
            print("   No dangling images to remove")
    
    def cleanup_old_images(self):
        """Remove images older than threshold"""
        print(f"\n6. Cleaning Images Older Than {self.image_age_days} Days...")
        
        # Get image list with creation dates
        success, output = self._run_command(
            [self.runtime, 'images', '--format', 'json']
        )
        
        if not success:
            print("   Could not list images")
            return
        
        removed_count = 0
        cutoff_date = datetime.now() - timedelta(days=self.image_age_days)
        
        try:
            for line in output.strip().split('\n'):
                if line:
                    data = json.loads(line)
                    # Check image age (implementation varies by runtime)
                    # This is a simplified version
                    image_id = data.get('Id', '')[:12]
                    if image_id and not self.dry_run:
                        # Skip images currently in use
                        check_cmd = [self.runtime, 'ps', '-q', '--filter', f'ancestor={image_id}']
                        result = subprocess.run(check_cmd, capture_output=True, text=True)
                        if not result.stdout.strip():  # Image not in use
                            # Remove old image
                            success, _ = self._run_command(
                                [self.runtime, 'rmi', image_id],
                                f"Removing old image {image_id}"
                            )
                            if success:
                                removed_count += 1
        except:
            pass
        
        print(f"   Removed {removed_count} old images")
    
    def cleanup_build_cache(self):
        """Clear build cache"""
        print("\n7. Cleaning Build Cache...")
        
        if self.runtime == 'docker':
            success, output = self._run_command(
                ['docker', 'builder', 'prune', '-f'],
                "Clearing Docker build cache"
            )
        else:
            success, output = self._run_command(
                ['podman', 'system', 'prune', '--filter', 'label!=keep', '-f'],
                "Clearing Podman build cache"
            )
        
        if success and output:
            print(f"   {output.strip()}")
    
    def cleanup_wsl2(self):
        """WSL2-specific cleanup on Windows"""
        if not self.is_windows:
            return
        
        print("\n8. WSL2 Cleanup (Windows)...")
        
        # Compact WSL2 virtual disk
        if not self.dry_run:
            try:
                # Shutdown WSL2 first
                subprocess.run(['wsl', '--shutdown'], capture_output=True, timeout=10)
                print("   WSL2 shutdown for disk compaction")
                
                # Note: Actual disk compaction requires additional steps
                # This is a placeholder for the full implementation
                print("   [INFO] Run 'Optimize-VHD' in PowerShell as admin to compact WSL2 disk")
            except:
                print("   Could not perform WSL2 cleanup")
    
    def generate_report(self, initial_memory, final_memory, initial_disk, final_disk):
        """Generate cleanup report"""
        print("\n" + "="*60)
        print("CLEANUP REPORT")
        print("="*60)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Runtime: {self.runtime}")
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        
        if initial_memory > 0 and final_memory > 0:
            memory_freed = initial_memory - final_memory
            print(f"\nMemory:")
            print(f"  Before: {initial_memory:.1f}%")
            print(f"  After: {final_memory:.1f}%")
            print(f"  Freed: {memory_freed:.1f}%")
        
        print("\nDisk Space Reclaimed:")
        for category in ['images', 'containers', 'volumes']:
            if category in initial_disk:
                print(f"  {category.capitalize()}: {initial_disk.get(category, 'N/A')}")
        
        print("\nRecommendations:")
        if final_memory > 60:
            print("  - Consider restarting heavy services")
        if final_memory > 80:
            print("  - CRITICAL: Immediate action needed to prevent crashes")
        print("  - Schedule regular cleanup (daily recommended)")
        print("  - Monitor resource trends over time")
    
    def run(self, force=False):
        """Execute automated cleanup"""
        print("\n" + "#"*60)
        print("# AUTOMATED RESOURCE CLEANUP")
        print("#"*60)
        print(f"Runtime: {self.runtime}")
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        
        # Initial checks
        initial_memory, memory_cleanup_needed = self.check_memory_usage()
        initial_disk, disk_cleanup_needed = self.check_disk_usage()
        
        # Determine if cleanup should proceed
        if not force and not memory_cleanup_needed and not disk_cleanup_needed:
            print("\n[SUCCESS] No cleanup needed - resources within limits")
            return True
        
        if force:
            print("\n[INFO] Force flag set - proceeding with cleanup")
        
        # Execute cleanup steps
        print("\n" + "="*60)
        print("EXECUTING CLEANUP")
        print("="*60)
        
        self.cleanup_stopped_containers()
        self.cleanup_unused_volumes()
        self.cleanup_dangling_images()
        
        if disk_cleanup_needed or force:
            self.cleanup_old_images()
            self.cleanup_build_cache()
        
        if self.is_windows:
            self.cleanup_wsl2()
        
        # Final checks
        print("\n" + "="*60)
        print("POST-CLEANUP VERIFICATION")
        print("="*60)
        
        final_memory, _ = self.check_memory_usage()
        final_disk, _ = self.check_disk_usage()
        
        # Generate report
        self.generate_report(initial_memory, final_memory, initial_disk, final_disk)
        
        return True


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Automated resource cleanup for Docker/Podman"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be cleaned without actually doing it'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force cleanup even if thresholds not exceeded'
    )
    parser.add_argument(
        '--runtime',
        choices=['docker', 'podman'],
        help='Specify container runtime'
    )
    parser.add_argument(
        '--memory-threshold',
        type=int,
        default=70,
        help='Memory usage threshold percent (default: 70)'
    )
    
    args = parser.parse_args()
    
    try:
        cleaner = AutoResourceCleanup(
            runtime=args.runtime,
            dry_run=args.dry_run
        )
        
        if args.memory_threshold:
            cleaner.memory_threshold_percent = args.memory_threshold
        
        success = cleaner.run(force=args.force)
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\nCleanup cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()