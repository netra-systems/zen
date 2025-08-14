#!/usr/bin/env python3
"""
Health monitoring utilities for dev launcher.
Provides service readiness checks and browser integration.
"""

import time
import webbrowser
import urllib.request
import urllib.error
from typing import Optional


def wait_for_service(url: str, timeout: int = 30) -> bool:
    """Wait for a service to become available."""
    start_time = time.time()
    attempt = 0
    
    while time.time() - start_time < timeout:
        attempt += 1
        try:
            if _check_service_health(url):
                print(f"   Service ready after {attempt} attempts")
                return True
        except (urllib.error.URLError, ConnectionError, TimeoutError, OSError):
            _handle_service_check_failure(url, attempt)
            time.sleep(2)
    
    return False


def _check_service_health(url: str) -> bool:
    """Check if service is healthy."""
    with urllib.request.urlopen(url, timeout=3) as response:
        return response.status == 200


def _handle_service_check_failure(url: str, attempt: int) -> None:
    """Handle service check failure with appropriate logging."""
    if attempt == 1:
        print(f"   Waiting for service at {url}...")
    elif attempt % 10 == 0:
        print(f"   Still waiting... ({attempt} attempts)")


def open_browser(url: str, no_browser: bool = False) -> bool:
    """Open the browser with the given URL."""
    if no_browser:
        return False
    
    try:
        # Add a small delay to ensure the page is ready
        time.sleep(1)
        
        # Open the default browser
        webbrowser.open(url)
        print(f"[WEB] Opening browser at {url}")
        return True
    except Exception as e:
        print(f"[WARNING] Could not open browser automatically: {e}")
        return False


def check_process_health(process, name: str) -> bool:
    """Check if a process is still running."""
    if process and process.poll() is not None:
        print(f"[WARNING] {name} process has stopped")
        return False
    return True


def check_monitor_health(monitor, name: str) -> bool:
    """Check if a process monitor is still running."""
    if monitor and not monitor.monitoring:
        print(f"[WARNING] {name} monitoring stopped (exceeded max restarts)")
        return False
    return True


def validate_backend_health(backend_info: dict, timeout: int = 30) -> bool:
    """Validate backend service health."""
    if not backend_info:
        print("[WARNING] Backend service discovery not found")
        return False
    
    print("[WAIT] Waiting for backend to be ready...")
    backend_url = f"{backend_info['api_url']}/health/live"
    
    if wait_for_service(backend_url, timeout):
        print("[OK] Backend is ready")
        return True
    else:
        print("[WARNING] Backend health check timed out, continuing anyway...")
        return False


def validate_frontend_health(frontend_port: int, timeout: int = 90) -> bool:
    """Validate frontend service health."""
    print("[WAIT] Waiting for frontend to be ready...")
    frontend_url = f"http://localhost:{frontend_port}"
    
    # Give Next.js a bit more time to compile initially
    print("   Allowing Next.js to compile...")
    time.sleep(3)
    
    if wait_for_service(frontend_url, timeout):
        print("[OK] Frontend is ready")
        return True
    else:
        print("[WARNING] Frontend readiness check timed out")
        return False


def print_service_summary(backend_info: Optional[dict], frontend_port: int, 
                         auto_restart: bool) -> None:
    """Print summary of running services."""
    print("\n" + "=" * 60)
    print("✨ Development environment is running!")
    print("=" * 60)
    
    if backend_info:
        print("\n[BACKEND]")
        print(f"   API: {backend_info['api_url']}")
        print(f"   WebSocket: {backend_info['ws_url']}")
        print(f"   Logs: Real-time streaming (cyan)")
    
    print("\n[FRONTEND]")
    print(f"   URL: http://localhost:{frontend_port}")
    print(f"   Logs: Real-time streaming (magenta)")
    
    if auto_restart:
        print("\n[AUTO] Auto-Restart: Enabled")
        print("   Services will automatically restart if they crash")
    
    print("\n[COMMANDS]:")
    print("   Press Ctrl+C to stop all services")
    print("   Logs are streamed in real-time with color coding")
    print("-" * 60 + "\n")


def print_configuration_summary(dynamic_ports: bool, backend_reload: bool,
                               frontend_reload: bool, auto_restart: bool,
                               use_turbopack: bool, load_secrets: bool) -> None:
    """Print configuration summary."""
    print("\n[CONFIG] Configuration:")
    print(f"   * Dynamic ports: {'YES' if dynamic_ports else 'NO'}")
    print(f"   * Backend hot reload: {'YES' if backend_reload else 'NO'}")
    print(f"   * Frontend hot reload: {'YES' if frontend_reload else 'NO'}")
    print(f"   * Auto-restart on crash: {'YES' if auto_restart else 'NO'}")
    print(f"   * Real-time log streaming: YES")
    print(f"   * Turbopack: {'YES (experimental)' if use_turbopack else 'NO (webpack)'}")
    print(f"   * Secret loading: {'YES (Google + env)' if load_secrets else 'NO'}")
    print("")


def monitor_processes_loop(backend_process, frontend_process, 
                          backend_monitor, frontend_monitor, 
                          auto_restart: bool) -> bool:
    """Monitor running processes and return True if all healthy."""
    if not auto_restart:
        # Check if processes are still running
        if not check_process_health(backend_process, "Backend"):
            return False
        if not check_process_health(frontend_process, "Frontend"):
            return False
    else:
        # Check if monitors are still running
        if not check_monitor_health(backend_monitor, "Backend"):
            return False
        if not check_monitor_health(frontend_monitor, "Frontend"):
            return False
    
    return True