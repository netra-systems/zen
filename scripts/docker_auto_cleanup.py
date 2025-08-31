#!/usr/bin/env python3
"""
Docker Auto-Cleanup Script for Development
==========================================
Automatically cleans up Docker resources to prevent crashes.
Run this before starting development or as a scheduled task.
"""

import subprocess
import sys
import json
from datetime import datetime
from pathlib import Path

class DockerCleaner:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.stats = {
            'containers_removed': 0,
            'images_removed': 0,
            'volumes_removed': 0,
            'space_reclaimed': 0,
            'errors': []
        }
    
    def run_command(self, cmd, capture=True):
        """Run command and return output."""
        if self.dry_run and any(word in cmd for word in ['rm', 'prune', 'kill']):
            print(f"[DRY RUN] Would execute: {cmd}")
            return "", "", 0
        
        try:
            result = subprocess.run(
                cmd, 
                shell=True, 
                capture_output=capture, 
                text=True,
                timeout=30
            )
            return result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            return "", "Command timed out", 1
        except Exception as e:
            return "", str(e), 1
    
    def parse_size(self, size_str):
        """Parse Docker size strings (e.g., '1.5GB', '256MB')."""
        try:
            size_str = size_str.strip()
            if 'GB' in size_str:
                return float(size_str.replace('GB', '')) * 1024
            elif 'MB' in size_str:
                return float(size_str.replace('MB', ''))
            elif 'KB' in size_str:
                return float(size_str.replace('KB', '')) / 1024
            else:
                return 0
        except:
            return 0
    
    def clean_stopped_containers(self):
        """Remove all stopped containers."""
        print("\n[CONTAINERS] Cleaning stopped containers...")
        
        # Get list of stopped containers
        stdout, _, _ = self.run_command("docker ps -a --filter status=exited -q")
        container_ids = stdout.strip().split('\n') if stdout.strip() else []
        
        if container_ids and container_ids[0]:
            print(f"  Found {len(container_ids)} stopped containers")
            stdout, stderr, code = self.run_command("docker container prune -f")
            
            if code == 0 and 'Total reclaimed space:' in stdout:
                for line in stdout.split('\n'):
                    if 'Total reclaimed space:' in line:
                        size = line.split(':')[1].strip()
                        self.stats['space_reclaimed'] += self.parse_size(size)
                self.stats['containers_removed'] = len(container_ids)
                print(f"  [OK] Removed {len(container_ids)} containers")
        else:
            print("  [OK] No stopped containers to clean")
    
    def clean_dangling_images(self):
        """Remove dangling images (tagged as <none>)."""
        print("\n[IMAGES] Cleaning dangling images...")
        
        # Get dangling images
        stdout, _, _ = self.run_command("docker images -f dangling=true -q")
        image_ids = stdout.strip().split('\n') if stdout.strip() else []
        
        if image_ids and image_ids[0]:
            print(f"  Found {len(image_ids)} dangling images")
            stdout, stderr, code = self.run_command("docker image prune -f")
            
            if code == 0 and 'Total reclaimed space:' in stdout:
                for line in stdout.split('\n'):
                    if 'Total reclaimed space:' in line:
                        size = line.split(':')[1].strip()
                        self.stats['space_reclaimed'] += self.parse_size(size)
                self.stats['images_removed'] = len(image_ids)
                print(f"  [OK] Removed {len(image_ids)} dangling images")
        else:
            print("  [OK] No dangling images to clean")
    
    def clean_old_images(self, keep_recent=3):
        """Remove old versions of images, keeping only recent ones."""
        print(f"\n[CLEANUP] Cleaning old image versions (keeping {keep_recent} recent)...")
        
        # Get all images grouped by repository
        stdout, _, _ = self.run_command("docker images --format '{{.Repository}}:{{.Tag}}:{{.ID}}:{{.CreatedAt}}'")
        
        if not stdout.strip():
            print("  [OK] No images to analyze")
            return
        
        repos = {}
        for line in stdout.strip().split('\n'):
            parts = line.split(':')
            if len(parts) >= 4:
                repo = parts[0]
                tag = parts[1]
                image_id = parts[2]
                
                if repo != '<none>' and 'netra' in repo.lower():
                    if repo not in repos:
                        repos[repo] = []
                    repos[repo].append((tag, image_id))
        
        # Remove old versions
        removed = 0
        for repo, images in repos.items():
            if len(images) > keep_recent:
                print(f"  Found {len(images)} versions of {repo}")
                # Keep the most recent ones
                for tag, image_id in images[keep_recent:]:
                    if not self.dry_run:
                        _, _, code = self.run_command(f"docker rmi {image_id} 2>/dev/null")
                        if code == 0:
                            removed += 1
        
        if removed > 0:
            self.stats['images_removed'] += removed
            print(f"  [OK] Removed {removed} old image versions")
        else:
            print("  [OK] No old versions to remove")
    
    def clean_unused_volumes(self):
        """Remove unused volumes."""
        print("\n[VOLUMES] Cleaning unused volumes...")
        
        # Get unused volumes
        stdout, _, _ = self.run_command("docker volume ls -qf dangling=true")
        volume_ids = stdout.strip().split('\n') if stdout.strip() else []
        
        if volume_ids and volume_ids[0]:
            print(f"  Found {len(volume_ids)} unused volumes")
            stdout, stderr, code = self.run_command("docker volume prune -f")
            
            if code == 0 and 'Total reclaimed space:' in stdout:
                for line in stdout.split('\n'):
                    if 'Total reclaimed space:' in line:
                        size = line.split(':')[1].strip()
                        self.stats['space_reclaimed'] += self.parse_size(size)
                self.stats['volumes_removed'] = len(volume_ids)
                print(f"  [OK] Removed {len(volume_ids)} volumes")
        else:
            print("  [OK] No unused volumes to clean")
    
    def check_disk_usage(self):
        """Check and report Docker disk usage."""
        print("\n[STATS] Docker Disk Usage:")
        stdout, _, _ = self.run_command("docker system df")
        
        if stdout:
            for line in stdout.split('\n'):
                if line and not line.startswith('TYPE'):
                    print(f"  {line}")
    
    def aggressive_cleanup(self):
        """Perform aggressive cleanup (use with caution)."""
        print("\n[WARNING] AGGRESSIVE CLEANUP MODE")
        print("  This will remove ALL unused resources!")
        
        response = input("  Continue? (yes/no): ")
        if response.lower() != 'yes':
            print("  Cancelled")
            return
        
        print("  Performing system-wide prune...")
        stdout, stderr, code = self.run_command("docker system prune -af --volumes")
        
        if code == 0:
            print("  [OK] Aggressive cleanup complete")
            if 'Total reclaimed space:' in stdout:
                for line in stdout.split('\n'):
                    if 'Total reclaimed space:' in line:
                        size = line.split(':')[1].strip()
                        self.stats['space_reclaimed'] += self.parse_size(size)
    
    def run(self, aggressive=False):
        """Run the cleanup process."""
        print("="*60)
        print("Docker Cleanup Process")
        print("="*60)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if self.dry_run:
            print("DRY RUN MODE - No changes will be made")
        
        try:
            if aggressive:
                self.aggressive_cleanup()
            else:
                self.clean_stopped_containers()
                self.clean_dangling_images()
                self.clean_old_images()
                self.clean_unused_volumes()
            
            self.check_disk_usage()
            
            # Print summary
            print("\n" + "="*60)
            print("Cleanup Summary:")
            print(f"  Containers removed: {self.stats['containers_removed']}")
            print(f"  Images removed: {self.stats['images_removed']}")
            print(f"  Volumes removed: {self.stats['volumes_removed']}")
            print(f"  Space reclaimed: {self.stats['space_reclaimed']:.1f} MB")
            
            if self.stats['errors']:
                print(f"\n[WARNING] Errors encountered:")
                for error in self.stats['errors']:
                    print(f"  - {error}")
            
            print("="*60)
            
        except KeyboardInterrupt:
            print("\n\n[WARNING] Cleanup interrupted by user")
            return 1
        except Exception as e:
            print(f"\n[ERROR] Unexpected error: {e}")
            return 1
        
        return 0


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Docker cleanup utility for development environment"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be cleaned without making changes"
    )
    parser.add_argument(
        "--aggressive",
        action="store_true",
        help="Perform aggressive cleanup (removes ALL unused resources)"
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Run without prompts (for automation)"
    )
    
    args = parser.parse_args()
    
    cleaner = DockerCleaner(dry_run=args.dry_run)
    return cleaner.run(aggressive=args.aggressive)


if __name__ == "__main__":
    sys.exit(main())