#!/usr/bin/env python3
"""
Check and display Docker memory allocation and usage.
Provides recommendations for optimal memory settings.
"""

import subprocess
import json
import sys
import io
from pathlib import Path

# Fix Windows Unicode output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def get_docker_info():
    """Get Docker system information."""
    try:
        result = subprocess.run(
            ["docker", "system", "info", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            print(f"Error getting Docker info: {result.stderr}")
            return None
    except Exception as e:
        print(f"Failed to get Docker info: {e}")
        return None

def get_container_stats():
    """Get memory usage of running containers."""
    try:
        result = subprocess.run(
            ["docker", "stats", "--no-stream", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            stats = []
            for line in result.stdout.strip().split('\n'):
                stats.append(json.loads(line))
            return stats
        return []
    except Exception as e:
        print(f"Failed to get container stats: {e}")
        return []

def bytes_to_gb(bytes_val):
    """Convert bytes to gigabytes."""
    return bytes_val / (1024 ** 3)

def parse_memory_string(mem_str):
    """Parse Docker memory string (e.g., '500MiB / 2GiB')."""
    if '/' in mem_str:
        used, total = mem_str.split('/')
        return used.strip(), total.strip()
    return mem_str, None

def check_wsl_config():
    """Check WSL configuration file for memory settings."""
    wsl_config = Path.home() / ".wslconfig"
    if wsl_config.exists():
        print(f"\n📄 WSL Config File: {wsl_config}")
        with open(wsl_config, 'r') as f:
            content = f.read()
            print("Current .wslconfig content:")
            print("-" * 40)
            print(content)
            print("-" * 40)
    else:
        print(f"\n📄 No .wslconfig file found at: {wsl_config}")
        print("   You can create one to customize WSL2 memory allocation")

def print_recommendations(current_memory_gb):
    """Print memory recommendations based on current allocation."""
    print("\n🎯 Memory Recommendations for Netra Project:")
    print("-" * 50)
    
    if current_memory_gb < 8:
        print("⚠️  WARNING: Current allocation is below minimum!")
        print("   Minimum required: 8GB")
        print("   You may experience performance issues")
    elif current_memory_gb < 12:
        print("⚡ Current allocation meets minimum requirements")
        print("   Consider upgrading to 12-16GB for better performance")
    elif current_memory_gb < 16:
        print("✅ Good allocation for development")
        print("   This should handle all services comfortably")
    else:
        print("🚀 Excellent allocation!")
        print("   You have plenty of memory for all services")
    
    print("\nRecommended per-service allocation:")
    print("  - Backend: 2-4GB")
    print("  - Auth: 1-2GB")
    print("  - PostgreSQL: 1-2GB")
    print("  - Redis: 512MB-1GB")
    print("  - ClickHouse: 1-2GB")
    print("  - Frontend: 1-2GB")
    print("  - Total: 8-16GB recommended")

def create_wslconfig_template():
    """Create a template .wslconfig file."""
    template = """[wsl2]
# Memory allocation for WSL2 (and Docker)
memory=12GB

# CPU cores
processors=4

# Swap configuration
swap=8GB
swapfile=%USERPROFILE%\\AppData\\Local\\Temp\\swap.vhdx

# Localhost forwarding
localhostForwarding=true

# Nested virtualization for better performance
nestedVirtualization=true

# Disable page reporting to reduce memory overhead
pageReporting=false

# Disable idle memory trimming
idleCommitLimit=max
"""
    
    template_path = Path.cwd() / "wslconfig_template.txt"
    with open(template_path, 'w') as f:
        f.write(template)
    
    print(f"\n📝 WSL config template created: {template_path}")
    print(f"   Copy to: {Path.home() / '.wslconfig'}")
    print("   Then run: wsl --shutdown")
    print("   And restart Docker Desktop")

def main():
    """Main function to check Docker memory allocation."""
    print("=" * 60)
    print("Docker Memory Allocation Checker")
    print("=" * 60)
    
    # Get Docker info
    docker_info = get_docker_info()
    
    if docker_info:
        # Extract memory information
        total_memory = docker_info.get('MemTotal', 0)
        total_memory_gb = bytes_to_gb(total_memory)
        
        print(f"\n🐳 Docker System Information:")
        print(f"  Platform: {docker_info.get('OperatingSystem', 'Unknown')}")
        print(f"  Kernel: {docker_info.get('KernelVersion', 'Unknown')}")
        print(f"  Total Memory: {total_memory_gb:.2f} GB ({total_memory:,} bytes)")
        print(f"  CPUs: {docker_info.get('NCPU', 'Unknown')}")
        print(f"  Docker Root: {docker_info.get('DockerRootDir', 'Unknown')}")
        
        # Container information
        containers = docker_info.get('Containers', 0)
        running = docker_info.get('ContainersRunning', 0)
        print(f"\n📦 Containers:")
        print(f"  Total: {containers}")
        print(f"  Running: {running}")
        print(f"  Stopped: {docker_info.get('ContainersStopped', 0)}")
        print(f"  Images: {docker_info.get('Images', 0)}")
        
        # Get container stats if any are running
        if running > 0:
            stats = get_container_stats()
            if stats:
                print(f"\n💾 Running Container Memory Usage:")
                for stat in stats:
                    name = stat.get('Name', 'Unknown')
                    mem_usage = stat.get('MemUsage', 'Unknown')
                    mem_percent = stat.get('MemPerc', 'Unknown')
                    print(f"  - {name}: {mem_usage} ({mem_percent})")
        
        # Check WSL config
        check_wsl_config()
        
        # Print recommendations
        print_recommendations(total_memory_gb)
        
        # Ask if user wants to create template
        print("\n" + "=" * 60)
        response = input("Create WSL config template? (y/n): ").lower()
        if response == 'y':
            create_wslconfig_template()
    else:
        print("\n❌ Could not retrieve Docker information")
        print("   Make sure Docker Desktop is running")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("Memory check complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()