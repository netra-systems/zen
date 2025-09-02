#!/usr/bin/env python3
"""
Docker Stability Monitor - Keeps Docker Desktop running and healthy
"""
import subprocess
import time
import sys
import os
import signal
from datetime import datetime

class DockerStabilityMonitor:
    def __init__(self):
        self.running = True
        self.restart_count = 0
        self.last_restart_time = None
        
    def check_docker_status(self):
        """Check if Docker daemon is responsive"""
        try:
            result = subprocess.run(
                ["docker", "version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def restart_docker(self):
        """Restart Docker Desktop"""
        print(f"[{datetime.now()}] Restarting Docker Desktop (attempt #{self.restart_count + 1})")
        
        # Kill existing Docker processes
        subprocess.run(["pkill", "-9", "Docker"], capture_output=True)
        time.sleep(3)
        
        # Start Docker Desktop
        subprocess.run(["open", "-a", "Docker"], capture_output=True)
        
        # Wait for Docker to be ready
        for i in range(30):
            time.sleep(2)
            if self.check_docker_status():
                print(f"[{datetime.now()}] Docker Desktop restarted successfully")
                self.restart_count += 1
                self.last_restart_time = datetime.now()
                return True
        
        print(f"[{datetime.now()}] Failed to restart Docker Desktop")
        return False
    
    def apply_resource_limits(self):
        """Apply conservative resource limits to prevent crashes"""
        try:
            # Update Docker Desktop settings (if settings file exists)
            settings_path = os.path.expanduser("~/Library/Group Containers/group.com.docker/settings.json")
            if os.path.exists(settings_path):
                import json
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
                
                # Conservative settings
                settings['memoryMiB'] = 8192  # 8GB
                settings['cpus'] = 4
                settings['diskSizeMiB'] = 61440  # 60GB
                
                with open(settings_path, 'w') as f:
                    json.dump(settings, f, indent=2)
                
                print(f"[{datetime.now()}] Applied conservative resource limits")
        except Exception as e:
            print(f"[{datetime.now()}] Could not update settings: {e}")
    
    def monitor_loop(self):
        """Main monitoring loop"""
        print(f"[{datetime.now()}] Starting Docker Stability Monitor")
        print("Press Ctrl+C to stop monitoring")
        
        signal.signal(signal.SIGINT, self.signal_handler)
        
        while self.running:
            if not self.check_docker_status():
                print(f"[{datetime.now()}] Docker is not responding")
                
                # Check if we're restarting too frequently
                if self.last_restart_time:
                    time_since_restart = (datetime.now() - self.last_restart_time).seconds
                    if time_since_restart < 60:
                        print(f"[{datetime.now()}] Docker crashed too quickly after restart. Waiting 30 seconds...")
                        time.sleep(30)
                
                if not self.restart_docker():
                    print(f"[{datetime.now()}] Unable to restart Docker. Waiting 60 seconds before retry...")
                    time.sleep(60)
            else:
                # Docker is healthy
                sys.stdout.write(f"\r[{datetime.now()}] Docker is healthy (restarts: {self.restart_count})")
                sys.stdout.flush()
            
            time.sleep(10)  # Check every 10 seconds
    
    def signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        print(f"\n[{datetime.now()}] Stopping Docker Stability Monitor")
        self.running = False
        sys.exit(0)

if __name__ == "__main__":
    monitor = DockerStabilityMonitor()
    
    # Apply conservative settings on start
    monitor.apply_resource_limits()
    
    # Start monitoring
    monitor.monitor_loop()