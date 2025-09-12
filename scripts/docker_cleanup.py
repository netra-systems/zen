#!/usr/bin/env python3
"""
Docker cleanup script to remove legacy artifacts and free up space.
Comprehensive cleanup for containers, images, volumes, networks, and build cache.
"""

import subprocess
import sys
import time
from typing import List, Dict, Any, Optional
import json
import argparse
from datetime import datetime, timedelta
import re
import os


class SecurityError(Exception):
    """Critical security exception for Docker force flag violations."""
    pass
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import centralized Docker manager if available
try:
    from test_framework.unified_docker_manager import (
        UnifiedDockerManager, EnvironmentType
    )
    CENTRALIZED_MANAGER_AVAILABLE = True
except ImportError:
    CENTRALIZED_MANAGER_AVAILABLE = False
    UnifiedDockerManager = None

# CRITICAL SECURITY: Import Docker Force Flag Guardian
try:
    from test_framework.docker_force_flag_guardian import (
        DockerForceFlagGuardian,
        DockerForceFlagViolation,
        validate_docker_command
    )
    FORCE_FLAG_GUARDIAN_AVAILABLE = True
except ImportError:
    print("WARNING: Docker Force Flag Guardian not available - force flags will not be validated")
    FORCE_FLAG_GUARDIAN_AVAILABLE = False
    validate_docker_command = lambda x: None


class DockerCleaner:
    """Manages Docker cleanup operations."""
    
    def __init__(self, dry_run: bool = False, force: bool = False, use_centralized: bool = True):
        """
        Initialize Docker cleaner.
        
        Args:
            dry_run: If True, only show what would be removed
            force: If True, skip confirmation prompts
            use_centralized: If True, use centralized Docker manager for test environments
        """
        self.dry_run = dry_run
        self.force = force
        self.use_centralized = use_centralized and CENTRALIZED_MANAGER_AVAILABLE
        self.stats = {
            'containers_removed': 0,
            'images_removed': 0,
            'volumes_removed': 0,
            'networks_removed': 0,
            'space_reclaimed': 0,
            'test_environments_cleaned': 0
        }
        
        # Initialize centralized manager if available
        self.centralized_manager = None
        if self.use_centralized:
            try:
                self.centralized_manager = UnifiedDockerManager()
                print("[INFO] Using centralized Docker manager for test environment cleanup")
            except Exception as e:
                print(f"[WARNING] Could not initialize centralized manager: {e}")
                self.use_centralized = False
    
    def run_command(self, cmd: List[str], capture_output: bool = True, input_data: str = None) -> Optional[str]:
        """
        Execute a Docker command with CRITICAL force flag protection.
        
        Args:
            cmd: Command to execute
            capture_output: Whether to capture output
            input_data: Input to send to command (for interactive confirmations)
            
        Returns:
            Command output if captured, None otherwise
            
        Raises:
            SecurityError: If force flags detected (CRITICAL PROTECTION)
        """
        try:
            #  ALERT:  CRITICAL SECURITY: Validate command for force flags using centralized guardian
            cmd_str = ' '.join(cmd)
            if FORCE_FLAG_GUARDIAN_AVAILABLE:
                try:
                    validate_docker_command(cmd_str)
                except DockerForceFlagViolation as e:
                    raise SecurityError(f"CRITICAL DOCKER SECURITY VIOLATION: {e}")
            else:
                # Fallback protection if guardian unavailable
                if any(flag in cmd_str for flag in ['-f', '--force']):
                    raise SecurityError(f"FORBIDDEN: Force flag detected in command: {cmd_str}")
                
            if self.dry_run and any(action in cmd for action in ['rm', 'rmi', 'prune', 'remove']):
                print(f"[DRY RUN] Would execute: {' '.join(cmd)}")
                return None
                
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                input=input_data,
                check=True
            )
            return result.stdout if capture_output else None
        except subprocess.CalledProcessError as e:
            print(f"Error executing command: {e}")
            if capture_output:
                print(f"Error output: {e.stderr}")
            return None
    
    def get_docker_info(self) -> Dict[str, Any]:
        """Get Docker system information."""
        info = {}
        
        # Get Docker version
        version_output = self.run_command(['docker', 'version', '--format', 'json'])
        if version_output:
            try:
                info['version'] = json.loads(version_output)
            except json.JSONDecodeError:
                pass
        
        # Get system df info
        df_output = self.run_command(['docker', 'system', 'df'])
        if df_output:
            info['disk_usage'] = df_output
            
        return info
    
    def clean_test_environments(self) -> None:
        """Clean up old test environments using centralized manager."""
        if not self.centralized_manager:
            return
        
        print("\n=== Cleaning Test Environments ===")
        
        try:
            # Get current statistics
            stats = self.centralized_manager.get_statistics()
            print(f"Active environments: {stats['active_environments']}")
            print(f"Total environments: {stats['environments']}")
            
            # Clean up old environments (older than 4 hours by default)
            if not self.dry_run:
                self.centralized_manager.cleanup_old_environments(max_age_hours=4)
                self.stats['test_environments_cleaned'] += 1
                print(" PASS:  Cleaned up old test environments")
            else:
                print("[DRY RUN] Would clean up old test environments")
        except Exception as e:
            print(f"Error cleaning test environments: {e}")
    
    def clean_stopped_containers(self) -> None:
        """Remove all stopped containers."""
        print("\n=== Cleaning Stopped Containers ===")
        
        # Get stopped containers
        containers = self.run_command([
            'docker', 'ps', '-a', '-q', '-f', 'status=exited'
        ])
        
        if not containers:
            print("No stopped containers found")
            return
            
        container_ids = containers.strip().split('\n')
        container_ids = [c for c in container_ids if c]
        
        print(f"Found {len(container_ids)} stopped containers")
        
        for container_id in container_ids:
            # Get container details
            details = self.run_command([
                'docker', 'inspect', container_id, '--format',
                '{{.Name}} ({{.State.FinishedAt}})'
            ])
            if details:
                print(f"  Removing: {details.strip()}")
            
            self.run_command(['docker', 'rm', container_id])
            self.stats['containers_removed'] += 1
    
    def clean_dangling_images(self) -> None:
        """Remove dangling images (untagged)."""
        print("\n=== Cleaning Dangling Images ===")
        
        # Get dangling images
        images = self.run_command([
            'docker', 'images', '-q', '-f', 'dangling=true'
        ])
        
        if not images:
            print("No dangling images found")
            return
            
        image_ids = images.strip().split('\n')
        image_ids = [i for i in image_ids if i]
        
        print(f"Found {len(image_ids)} dangling images")
        
        for image_id in image_ids:
            print(f"  Removing image: {image_id[:12]}")
            self.run_command(['docker', 'rmi', image_id])
            self.stats['images_removed'] += 1
    
    def clean_unused_images(self, days_old: int = 30) -> None:
        """
        Remove unused images older than specified days.
        
        Args:
            days_old: Remove images not used in this many days
        """
        print(f"\n=== Cleaning Unused Images (older than {days_old} days) ===")
        
        # Get all images with creation time
        images_json = self.run_command([
            'docker', 'images', '--format', 'json'
        ])
        
        if not images_json:
            print("No images found")
            return
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        images_to_remove = []
        
        for line in images_json.strip().split('\n'):
            if not line:
                continue
            try:
                image = json.loads(line)
                # Parse created time (format: "2024-01-15 10:30:45 -0800 PST")
                created_str = image.get('CreatedAt', '')
                # Extract date part
                date_match = re.match(r'(\d{4}-\d{2}-\d{2})', created_str)
                if date_match:
                    created_date = datetime.strptime(date_match.group(1), '%Y-%m-%d')
                    if created_date < cutoff_date:
                        images_to_remove.append({
                            'id': image.get('ID', ''),
                            'repo': image.get('Repository', '<none>'),
                            'tag': image.get('Tag', '<none>'),
                            'created': created_str
                        })
            except (json.JSONDecodeError, ValueError):
                continue
        
        if not images_to_remove:
            print(f"No unused images older than {days_old} days found")
            return
        
        print(f"Found {len(images_to_remove)} old unused images")
        for image in images_to_remove:
            print(f"  Removing: {image['repo']}:{image['tag']} ({image['id'][:12]})")
            # CRITICAL: Use safe removal without force flags to prevent daemon crashes
            try:
                result = self.run_command(['docker', 'rmi', image['id']], capture_output=True)
                self.stats['images_removed'] += 1
                print(f"    Successfully removed image {image['id'][:12]}")
            except (subprocess.CalledProcessError, SecurityError) as e:
                # SAFE: Skip image removal if it fails rather than forcing
                print(f"    Warning: Could not remove image {image['id'][:12]} - possibly still in use")
                print(f"    Reason: {e}")
                print(f"    SAFE: Skipping to prevent Docker daemon crash")
                continue
    
    def clean_unused_volumes(self) -> None:
        """Remove unused volumes."""
        print("\n=== Cleaning Unused Volumes ===")
        
        # Get unused volumes
        volumes = self.run_command([
            'docker', 'volume', 'ls', '-q', '-f', 'dangling=true'
        ])
        
        if not volumes:
            print("No unused volumes found")
            return
        
        volume_names = volumes.strip().split('\n')
        volume_names = [v for v in volume_names if v]
        
        print(f"Found {len(volume_names)} unused volumes")
        
        for volume in volume_names:
            print(f"  Removing volume: {volume}")
            self.run_command(['docker', 'volume', 'rm', volume])
            self.stats['volumes_removed'] += 1
    
    def clean_unused_networks(self) -> None:
        """Remove unused custom networks."""
        print("\n=== Cleaning Unused Networks ===")
        
        # Get all custom networks (excluding default ones)
        networks_json = self.run_command([
            'docker', 'network', 'ls', '--format', 'json'
        ])
        
        if not networks_json:
            print("No networks found")
            return
        
        default_networks = ['bridge', 'host', 'none']
        networks_to_remove = []
        
        for line in networks_json.strip().split('\n'):
            if not line:
                continue
            try:
                network = json.loads(line)
                name = network.get('Name', '')
                if name not in default_networks:
                    # Check if network is in use
                    inspect = self.run_command([
                        'docker', 'network', 'inspect', name,
                        '--format', '{{len .Containers}}'
                    ])
                    if inspect and inspect.strip() == '0':
                        networks_to_remove.append(name)
            except json.JSONDecodeError:
                continue
        
        if not networks_to_remove:
            print("No unused custom networks found")
            return
        
        print(f"Found {len(networks_to_remove)} unused networks")
        for network in networks_to_remove:
            print(f"  Removing network: {network}")
            self.run_command(['docker', 'network', 'rm', network])
            self.stats['networks_removed'] += 1
    
    def clean_build_cache(self) -> None:
        """Clean Docker build cache."""
        print("\n=== Cleaning Build Cache ===")
        
        # Get cache size before cleaning
        before_df = self.run_command(['docker', 'system', 'df'])
        
        # Prune build cache
        if self.dry_run:
            print("[DRY RUN] Would clean build cache")
        else:
            print("Cleaning build cache...")
            # SAFE: Interactive confirmation (NO --force flag)
            output = self.run_command([
                'docker', 'builder', 'prune', '--all'
            ], input_data='y\n')
            if output:
                # Extract reclaimed space from output
                match = re.search(r'reclaimed:\s*([\d.]+\s*[KMGT]?B)', output, re.IGNORECASE)
                if match:
                    print(f"Build cache cleaned. Space reclaimed: {match.group(1)}")
    
    def system_prune(self, all_images: bool = False) -> None:
        """
        Perform Docker system prune.
        
        Args:
            all_images: If True, remove all unused images, not just dangling ones
        """
        print("\n=== System Prune ===")
        
        # SAFE: Interactive confirmation (NO --force flag)
        cmd = ['docker', 'system', 'prune']
        if all_images:
            cmd.append('--all')
        cmd.append('--volumes')
        
        if self.dry_run:
            print(f"[DRY RUN] Would execute: {' '.join(cmd)}")
        else:
            print("Running system prune...")
            # SAFE: Provide interactive confirmation automatically
            output = self.run_command(cmd, input_data='y\n')
            if output:
                print(output)
    
    def aggressive_cleanup(self) -> None:
        """Perform aggressive cleanup - removes everything not currently running."""
        print("\n" + "="*50)
        print("AGGRESSIVE CLEANUP MODE")
        print("WARNING: This will remove ALL stopped containers, unused images,")
        print("volumes, networks, and build cache!")
        print("="*50)
        
        if not self.force and not self.dry_run:
            response = input("\nAre you sure you want to continue? (yes/no): ")
            if response.lower() != 'yes':
                print("Cleanup cancelled")
                return
        
        # Stop all running containers first
        print("\n=== Stopping All Containers ===")
        running = self.run_command(['docker', 'ps', '-q'])
        if running:
            container_ids = running.strip().split('\n')
            container_ids = [c for c in container_ids if c]
            for container_id in container_ids:
                print(f"  Stopping container: {container_id[:12]}")
                self.run_command(['docker', 'stop', container_id])
        
        # Clean everything
        self.clean_stopped_containers()
        self.clean_dangling_images()
        self.clean_unused_images(days_old=0)  # Remove all unused images
        self.clean_unused_volumes()
        self.clean_unused_networks()
        self.clean_build_cache()
        self.system_prune(all_images=True)
    
    def safe_cleanup(self) -> None:
        """Perform safe cleanup - only removes obviously unused items."""
        print("\n=== Safe Cleanup Mode ===")
        print("Removing only dangling and obviously unused resources...")
        
        self.clean_stopped_containers()
        self.clean_dangling_images()
        self.clean_unused_volumes()
        self.clean_unused_networks()
        self.clean_build_cache()
    
    def print_summary(self) -> None:
        """Print cleanup summary."""
        print("\n" + "="*50)
        print("CLEANUP SUMMARY")
        print("="*50)
        print(f"Containers removed: {self.stats['containers_removed']}")
        print(f"Images removed: {self.stats['images_removed']}")
        print(f"Volumes removed: {self.stats['volumes_removed']}")
        print(f"Networks removed: {self.stats['networks_removed']}")
        
        # Get final disk usage
        df_after = self.run_command(['docker', 'system', 'df'])
        if df_after:
            print("\nCurrent Docker disk usage:")
            print(df_after)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Docker cleanup script to remove legacy artifacts'
    )
    parser.add_argument(
        '--mode',
        choices=['safe', 'normal', 'aggressive'],
        default='normal',
        help='Cleanup mode: safe (minimal), normal (default), or aggressive (remove all)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be removed without actually removing'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Skip confirmation prompts'
    )
    parser.add_argument(
        '--days-old',
        type=int,
        default=30,
        help='Remove images older than this many days (default: 30)'
    )
    
    args = parser.parse_args()
    
    # Check if Docker is available
    try:
        subprocess.run(['docker', 'version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: Docker is not installed or not running")
        sys.exit(1)
    
    cleaner = DockerCleaner(dry_run=args.dry_run, force=args.force)
    
    print("Docker Cleanup Utility")
    print(f"Mode: {args.mode.upper()}")
    if args.dry_run:
        print("DRY RUN MODE - No changes will be made")
    print("")
    
    # Show current Docker info
    info = cleaner.get_docker_info()
    if 'disk_usage' in info:
        print("Current Docker disk usage:")
        print(info['disk_usage'])
        print("")
    
    try:
        if args.mode == 'safe':
            cleaner.safe_cleanup()
        elif args.mode == 'aggressive':
            cleaner.aggressive_cleanup()
        else:  # normal mode
            # Clean test environments first (if centralized manager available)
            cleaner.clean_test_environments()
            
            # Then clean regular Docker resources
            cleaner.clean_stopped_containers()
            cleaner.clean_dangling_images()
            cleaner.clean_unused_images(days_old=args.days_old)
            cleaner.clean_unused_volumes()
            cleaner.clean_unused_networks()
            cleaner.clean_build_cache()
    except KeyboardInterrupt:
        print("\n\nCleanup interrupted by user")
    except Exception as e:
        print(f"\nError during cleanup: {e}")
        sys.exit(1)
    
    cleaner.print_summary()


if __name__ == '__main__':
    main()