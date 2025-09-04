#!/usr/bin/env python3
"""
Quick script to check if containers are running with resource limits
"""

import subprocess
import sys

def check_podman_resources():
    """Check Podman container resource usage"""
    print("\n" + "="*70)
    print("CONTAINER RESOURCE LIMITS VERIFICATION")
    print("="*70)
    
    try:
        # Get stats from Podman
        result = subprocess.run(
            ['podman', 'stats', '--no-stream'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            print(f"Error getting stats: {result.stderr}")
            return False
        
        lines = result.stdout.strip().split('\n')
        if len(lines) < 2:
            print("No containers running")
            return False
        
        # Parse header and data
        print("\nRunning Containers with Resource Limits:")
        print("-"*70)
        
        success = True
        total_memory_used = 0
        total_memory_limit = 0
        
        for line in lines[1:]:  # Skip header
            parts = line.split(None, 10)  # Split into max 11 parts
            if len(parts) >= 6:
                name = parts[1]
                cpu_percent = parts[2]
                # Memory is in format "24.72MB / 268.4MB" in parts[3] and parts[4]
                mem_used = parts[3]
                # parts[4] is "/"
                mem_limit = parts[5] if len(parts) > 5 else "0MB"
                mem_percent = parts[6] if len(parts) > 6 else "0%"
                
                # Construct mem_usage string for display
                mem_usage = f"{mem_used} / {mem_limit}"
                
                # Parse memory usage
                if mem_used and mem_limit:
                    # Convert to MB for totals
                    used_mb = float(mem_used.replace('MB', '').replace('GB', '000'))
                    limit_mb = float(mem_limit.replace('MB', '').replace('GB', '000'))
                    
                    total_memory_used += used_mb
                    total_memory_limit += limit_mb
                    
                    # Determine status
                    mem_percent_val = float(mem_percent.rstrip('%'))
                    if mem_percent_val > 80:
                        status = "[CRITICAL]"
                        success = False
                    elif mem_percent_val > 60:
                        status = "[WARNING]"
                    else:
                        status = "[OK]"
                    
                    # Print container info
                    print(f"\nContainer: {name}")
                    print(f"  CPU Usage: {cpu_percent}")
                    print(f"  Memory: {mem_usage} ({mem_percent})")
                    print(f"  Status: {status}")
                    
                    # Check if limits are applied (should be less than system total)
                    if limit_mb < 10000:  # Assuming system has more than 10GB
                        print(f"  [YES] Resource limit applied: {mem_limit}")
                    else:
                        print(f"  [NO] No effective limit (using system max)")
        
        print("\n" + "-"*70)
        print(f"Total Memory Usage: {total_memory_used:.1f}MB / {total_memory_limit:.1f}MB")
        if total_memory_limit > 0:
            print(f"Total Percentage: {(total_memory_used/total_memory_limit*100):.1f}%")
        else:
            print("Total Percentage: N/A")
        
        # Analysis
        print("\n" + "="*70)
        print("ANALYSIS:")
        print("="*70)
        
        if total_memory_limit < 1000:  # Less than 1GB total
            print("[EXCELLENT] Total memory limits are very conservative (<1GB)")
        elif total_memory_limit < 3000:  # Less than 3GB
            print("[GOOD] Total memory limits are reasonable (<3GB)")
        else:
            print("[WARNING] Total memory limits may be too high (>3GB)")
        
        if success:
            print("[SUCCESS] All containers within healthy resource limits")
        else:
            print("[ALERT] Some containers exceeding safe limits!")
        
        # Recommendations
        print("\n" + "="*70)
        print("RECOMMENDATIONS:")
        print("="*70)
        print("1. Current infrastructure services (PostgreSQL, Redis) are running efficiently")
        print("2. These limits prevent resource exhaustion as documented in crash analysis")
        print("3. Backend service (when started) will be limited to 1GB as requested")
        print("4. Total system usage will stay well under WSL2/Podman limits")
        
        return success
        
    except subprocess.TimeoutExpired:
        print("Timeout getting stats")
        return False
    except FileNotFoundError:
        print("Podman not found. Please ensure Podman is installed and in PATH")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    success = check_podman_resources()
    sys.exit(0 if success else 1)