#!/usr/bin/env python3
"""
Windows Port 8000 Permission Error Fix

This script resolves the Windows socket permission error [WinError 10013] that prevents
the backend service from binding to port 8000.

Common causes addressed:
1. Process already using port 8000
2. Windows firewall blocking port access
3. Orphaned processes from previous dev launcher runs
4. System-reserved ports (Windows dynamic port range)

Usage:
    python scripts/fix_port_8000_windows.py [--kill-processes] [--check-firewall] [--force]
"""

import argparse
import subprocess
import sys
import time
import logging
from pathlib import Path
from typing import List, Tuple, Optional

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def run_command(cmd: str, shell: bool = True, timeout: int = 10) -> Tuple[bool, str, str]:
    """
    Run a command safely and return success status, stdout, and stderr.
    
    Args:
        cmd: Command to run
        shell: Whether to use shell
        timeout: Command timeout in seconds
        
    Returns:
        Tuple of (success, stdout, stderr)
    """
    try:
        result = subprocess.run(
            cmd, 
            shell=shell, 
            capture_output=True, 
            text=True, 
            timeout=timeout,
            encoding='utf-8',
            errors='replace'
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", f"Command timed out after {timeout} seconds"
    except Exception as e:
        return False, "", str(e)

def check_port_usage(port: int = 8000) -> List[Tuple[str, str, str]]:
    """
    Check what processes are using the specified port.
    
    Args:
        port: Port number to check
        
    Returns:
        List of tuples (process_name, pid, connection_info)
    """
    logger.info(f" SEARCH:  Checking what processes are using port {port}...")
    
    success, stdout, stderr = run_command(f"netstat -ano | findstr :{port}")
    
    if not success or not stdout.strip():
        logger.info(f" PASS:  Port {port} appears to be free")
        return []
    
    processes = []
    lines = stdout.strip().split('\n')
    
    for line in lines:
        parts = line.split()
        if len(parts) >= 5:
            protocol = parts[0]
            local_addr = parts[1]
            remote_addr = parts[2] if len(parts) > 2 else ""
            state = parts[3] if len(parts) > 3 else ""
            pid = parts[-1]
            
            if pid.isdigit() and pid != "0":
                # Get process name
                proc_success, proc_stdout, _ = run_command(f'tasklist /FI "PID eq {pid}" /FO CSV /NH')
                process_name = "Unknown"
                if proc_success and proc_stdout.strip():
                    try:
                        # Parse CSV output: "process_name","pid","session_name","session_id","mem_usage"
                        csv_line = proc_stdout.strip().split('\n')[0]
                        process_name = csv_line.split(',')[0].strip('"')
                    except:
                        process_name = "Unknown"
                
                processes.append((process_name, pid, f"{protocol} {local_addr} {state}"))
    
    if processes:
        logger.warning(f" WARNING: [U+FE0F]  Port {port} is being used by {len(processes)} process(es):")
        for i, (name, pid, conn_info) in enumerate(processes, 1):
            logger.warning(f"   {i}. {name} (PID: {pid}) - {conn_info}")
    
    return processes

def kill_processes_using_port(port: int = 8000, force: bool = False) -> bool:
    """
    Kill processes using the specified port.
    
    Args:
        port: Port number
        force: Whether to force kill (use /F flag)
        
    Returns:
        True if successful, False otherwise
    """
    processes = check_port_usage(port)
    
    if not processes:
        logger.info(f" PASS:  No processes found using port {port}")
        return True
    
    logger.info(f"[U+1F52A] Attempting to terminate {len(processes)} process(es) using port {port}...")
    
    killed_count = 0
    for process_name, pid, _ in processes:
        # Skip system processes
        if process_name.lower() in ['system', 'csrss.exe', 'winlogon.exe', 'services.exe']:
            logger.warning(f" WARNING: [U+FE0F]  Skipping system process: {process_name} (PID: {pid})")
            continue
            
        logger.info(f"   Terminating {process_name} (PID: {pid})...")
        
        # Try graceful termination first
        success, stdout, stderr = run_command(f"taskkill /PID {pid}")
        
        if not success and force:
            logger.info(f"   Graceful termination failed, forcing kill...")
            success, stdout, stderr = run_command(f"taskkill /F /T /PID {pid}")
        
        if success:
            logger.info(f"    PASS:  Successfully terminated {process_name} (PID: {pid})")
            killed_count += 1
        else:
            logger.error(f"    FAIL:  Failed to terminate {process_name} (PID: {pid}): {stderr}")
    
    # Wait a moment for processes to clean up
    if killed_count > 0:
        logger.info("[U+23F3] Waiting 3 seconds for processes to clean up...")
        time.sleep(3)
        
        # Verify the port is now free
        remaining = check_port_usage(port)
        if not remaining:
            logger.info(f" PASS:  Port {port} is now free!")
            return True
        else:
            logger.warning(f" WARNING: [U+FE0F]  Port {port} still has {len(remaining)} process(es) using it")
            return False
    
    return killed_count > 0

def check_windows_firewall(port: int = 8000) -> bool:
    """
    Check Windows firewall rules for the specified port.
    
    Args:
        port: Port number to check
        
    Returns:
        True if port is allowed, False otherwise
    """
    logger.info(f" FIRE:  Checking Windows firewall rules for port {port}...")
    
    # Check existing firewall rules
    success, stdout, stderr = run_command(
        f'netsh advfirewall firewall show rule name=all | findstr /C:"{port}"'
    )
    
    if success and stdout.strip():
        logger.info(f" PASS:  Found firewall rules mentioning port {port}:")
        lines = stdout.strip().split('\n')
        for line in lines[:5]:  # Show first 5 matches
            logger.info(f"   {line.strip()}")
        return True
    else:
        logger.warning(f" WARNING: [U+FE0F]  No specific firewall rules found for port {port}")
        return False

def create_firewall_rule(port: int = 8000) -> bool:
    """
    Create Windows firewall rule to allow traffic on the specified port.
    
    Args:
        port: Port number
        
    Returns:
        True if successful, False otherwise
    """
    logger.info(f" FIRE:  Creating Windows firewall rule for port {port}...")
    
    rule_name = f"Netra Backend Port {port}"
    
    # Remove existing rule if it exists
    run_command(f'netsh advfirewall firewall delete rule name="{rule_name}"')
    
    # Create new inbound rule
    success, stdout, stderr = run_command(
        f'netsh advfirewall firewall add rule '
        f'name="{rule_name}" '
        f'dir=in '
        f'action=allow '
        f'protocol=TCP '
        f'localport={port}'
    )
    
    if success:
        logger.info(f" PASS:  Successfully created firewall rule for port {port}")
        return True
    else:
        logger.error(f" FAIL:  Failed to create firewall rule: {stderr}")
        return False

def check_reserved_ports(port: int = 8000) -> bool:
    """
    Check if the port is in Windows' dynamic/reserved port range.
    
    Args:
        port: Port number to check
        
    Returns:
        True if port is available, False if reserved
    """
    logger.info(f" SEARCH:  Checking if port {port} is in Windows reserved range...")
    
    # Get dynamic port range
    success, stdout, stderr = run_command("netsh int ipv4 show dynamicport tcp")
    
    if success:
        logger.info("Windows TCP dynamic port range:")
        logger.info(stdout.strip())
        
        # Parse the output to check if our port is in the range
        lines = stdout.strip().split('\n')
        for line in lines:
            if "Start Port" in line:
                try:
                    start_port = int(line.split(':')[-1].strip())
                except:
                    continue
            elif "Number of Ports" in line:
                try:
                    num_ports = int(line.split(':')[-1].strip())
                    end_port = start_port + num_ports - 1
                    
                    if start_port <= port <= end_port:
                        logger.warning(f" WARNING: [U+FE0F]  Port {port} is in Windows dynamic range ({start_port}-{end_port})")
                        logger.warning(f"   Consider using a different port outside this range")
                        return False
                    else:
                        logger.info(f" PASS:  Port {port} is not in Windows dynamic range ({start_port}-{end_port})")
                        return True
                except:
                    continue
    
    logger.info(f" PASS:  Port {port} should be available for use")
    return True

def test_port_binding(port: int = 8000) -> bool:
    """
    Test if we can bind to the specified port.
    
    Args:
        port: Port number to test
        
    Returns:
        True if binding successful, False otherwise
    """
    logger.info(f"[U+1F9EA] Testing if we can bind to port {port}...")
    
    try:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(5)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('127.0.0.1', port))
            sock.listen(1)
            
            actual_port = sock.getsockname()[1]
            logger.info(f" PASS:  Successfully bound to port {actual_port}")
            return True
            
    except OSError as e:
        if e.errno == 10013:  # Permission denied
            logger.error(f" FAIL:  Permission denied when trying to bind to port {port}")
            logger.error(f"   This usually means another process is using the port or firewall is blocking it")
        elif e.errno == 10048:  # Address already in use
            logger.error(f" FAIL:  Port {port} is already in use by another process")
        else:
            logger.error(f" FAIL:  Failed to bind to port {port}: {e}")
        return False
    except Exception as e:
        logger.error(f" FAIL:  Unexpected error when testing port {port}: {e}")
        return False

def main():
    """Main function to fix port 8000 issues."""
    parser = argparse.ArgumentParser(
        description="Fix Windows socket permission error for port 8000",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/fix_port_8000_windows.py                    # Check only
  python scripts/fix_port_8000_windows.py --kill-processes   # Kill processes using port
  python scripts/fix_port_8000_windows.py --check-firewall   # Check firewall rules  
  python scripts/fix_port_8000_windows.py --force            # Force kill processes and fix firewall
        """
    )
    
    parser.add_argument(
        "--port", 
        type=int, 
        default=8000, 
        help="Port number to check/fix (default: 8000)"
    )
    parser.add_argument(
        "--kill-processes", 
        action="store_true", 
        help="Kill processes using the port"
    )
    parser.add_argument(
        "--check-firewall", 
        action="store_true", 
        help="Check and create firewall rules"
    )
    parser.add_argument(
        "--force", 
        action="store_true", 
        help="Force kill processes and create firewall rules"
    )
    parser.add_argument(
        "--create-firewall-rule", 
        action="store_true", 
        help="Create Windows firewall rule for the port"
    )
    
    args = parser.parse_args()
    
    if sys.platform != "win32":
        logger.error(" FAIL:  This script is only for Windows systems")
        return 1
    
    logger.info("[U+1F680] Starting Windows Port 8000 Permission Error Fix")
    logger.info("=" * 60)
    
    # Step 1: Check current port usage
    processes_found = len(check_port_usage(args.port)) > 0
    
    # Step 2: Kill processes if requested or if force is enabled
    if args.kill_processes or args.force:
        if processes_found:
            success = kill_processes_using_port(args.port, force=args.force)
            if not success:
                logger.error(f" FAIL:  Failed to free port {args.port}")
                return 1
    
    # Step 3: Check Windows firewall
    if args.check_firewall or args.force:
        check_windows_firewall(args.port)
    
    # Step 4: Create firewall rule if requested
    if args.create_firewall_rule or args.force:
        create_firewall_rule(args.port)
    
    # Step 5: Check reserved ports
    check_reserved_ports(args.port)
    
    # Step 6: Test port binding
    if test_port_binding(args.port):
        logger.info("=" * 60)
        logger.info(f" PASS:  SUCCESS: Port {args.port} is now available for the backend service!")
        logger.info(f"   You can now run the dev launcher:")
        logger.info(f"   python scripts/dev_launcher.py")
        return 0
    else:
        logger.error("=" * 60)
        logger.error(f" FAIL:  FAILED: Port {args.port} is still not available")
        logger.error("   Additional troubleshooting may be needed:")
        logger.error("   1. Try running as Administrator")
        logger.error("   2. Check if Windows Defender is blocking the port")
        logger.error("   3. Restart your computer to clear any stuck processes")
        logger.error(f"   4. Use a different port: python scripts/dev_launcher.py --backend-port 8001")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)