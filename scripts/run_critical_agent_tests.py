#!/usr/bin/env python
"""
🚨 CRITICAL: Run Top 5 Agent Tests with Optimized Memory Management
LIFE OR DEATH: These tests MUST pass for the product to work
"""

import os
import sys
import subprocess
import time
import psutil
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Docker and environment imports handled via subprocess

# Top 5 Critical Agent Tests (in priority order)
CRITICAL_TESTS = [
    {
        "name": "WebSocket Agent Events Suite",
        "path": "tests/mission_critical/test_websocket_agent_events_suite.py",
        "business_value": "$500K+ ARR",
        "description": "Core chat functionality - all 5 WebSocket events",
        "timeout": 300,
    },
    {
        "name": "Agent Orchestration with Real LLM",
        "path": "tests/e2e/test_agent_orchestration_real_llm.py",
        "business_value": "Core agent execution",
        "description": "ExecutionEngine with real LLM integration",
        "timeout": 600,
    },
    {
        "name": "Comprehensive WebSocket Events",
        "path": "tests/e2e/test_agent_websocket_events_comprehensive.py",
        "business_value": "Complete event flow",
        "description": "Full agent lifecycle and event sequences",
        "timeout": 400,
    },
    {
        "name": "Agent Message Flow",
        "path": "tests/e2e/test_agent_message_flow_implementation.py",
        "business_value": "User chat flow",
        "description": "End-to-end message processing and streaming",
        "timeout": 400,
    },
    {
        "name": "Write-Review-Refine Integration",
        "path": "tests/e2e/test_agent_write_review_refine_integration_core.py",
        "business_value": "Multi-agent collaboration",
        "description": "Agent workflow and state management",
        "timeout": 500,
    },
]

def get_memory_usage() -> Dict[str, float]:
    """Get current memory usage statistics."""
    mem = psutil.virtual_memory()
    return {
        "total_gb": mem.total / (1024**3),
        "available_gb": mem.available / (1024**3),
        "used_gb": mem.used / (1024**3),
        "percent": mem.percent,
    }

def print_memory_status(label: str = ""):
    """Print current memory status."""
    mem = get_memory_usage()
    status = f"[{label}] " if label else ""
    status += f"Memory: {mem['used_gb']:.1f}/{mem['total_gb']:.1f}GB ({mem['percent']:.1f}%) - Available: {mem['available_gb']:.1f}GB"
    print(f"💾 {status}")

def cleanup_docker():
    """Clean up all Docker resources to free memory."""
    print("\n🧹 Cleaning up Docker resources...")
    
    # Stop all containers
    subprocess.run(["docker", "stop", "$(docker ps -q)"], shell=True, capture_output=True)
    
    # Remove all containers
    subprocess.run(["docker", "rm", "-f", "$(docker ps -aq)"], shell=True, capture_output=True)
    
    # Remove all networks except default
    subprocess.run(
        ["docker", "network", "prune", "-f"],
        capture_output=True
    )
    
    # Clean up volumes (but keep named volumes)
    subprocess.run(["docker", "volume", "prune", "-f"], capture_output=True)
    
    print("✅ Docker cleanup complete")
    print_memory_status("After cleanup")

def start_docker_services() -> Tuple[bool, str]:
    """Start Docker services with optimized Alpine configuration."""
    print("\n🚀 Starting Docker services with optimized memory settings...")
    
    try:
        # Use the updated Alpine test configuration
        compose_file = project_root / "docker-compose.alpine-test.yml"
        
        # Start services with explicit project name
        project_name = f"netra-critical-test-{int(time.time())}"
        
        cmd = [
            "docker-compose",
            "-f", str(compose_file),
            "-p", project_name,
            "up", "-d",
            "--build",
            "--force-recreate",
            "--remove-orphans"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            print(f"❌ Failed to start Docker services: {result.stderr}")
            return False, project_name
        
        # Wait for services to be healthy
        print("⏳ Waiting for services to be healthy (up to 3 minutes)...")
        max_wait = 180
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            # Check health status
            health_cmd = [
                "docker-compose",
                "-f", str(compose_file),
                "-p", project_name,
                "ps"
            ]
            
            result = subprocess.run(health_cmd, capture_output=True, text=True)
            output = result.stdout
            
            # Check if all required services are healthy
            if all(service in output for service in ["healthy", "running"]):
                unhealthy_count = output.count("unhealthy")
                if unhealthy_count == 0:
                    print("✅ All services are healthy!")
                    print_memory_status("After Docker startup")
                    return True, project_name
            
            time.sleep(5)
        
        print("⚠️ Services did not become healthy in time")
        return False, project_name
        
    except subprocess.TimeoutExpired:
        print("❌ Docker startup timed out")
        return False, ""
    except Exception as e:
        print(f"❌ Error starting Docker: {e}")
        return False, ""

def stop_docker_services(project_name: str):
    """Stop Docker services for a specific project."""
    if not project_name:
        return
    
    print(f"\n🛑 Stopping Docker services for {project_name}...")
    
    compose_file = project_root / "docker-compose.alpine-test.yml"
    
    cmd = [
        "docker-compose",
        "-f", str(compose_file),
        "-p", project_name,
        "down",
        "--volumes",
        "--remove-orphans"
    ]
    
    subprocess.run(cmd, capture_output=True, timeout=30)

def run_single_test(test_info: Dict) -> bool:
    """Run a single critical test with monitoring."""
    print(f"\n{'='*80}")
    print(f"🎯 Running: {test_info['name']}")
    print(f"📊 Business Value: {test_info['business_value']}")
    print(f"📝 Description: {test_info['description']}")
    print(f"⏱️  Timeout: {test_info['timeout']}s")
    print(f"{'='*80}")
    
    print_memory_status("Before test")
    
    test_path = project_root / test_info["path"]
    
    if not test_path.exists():
        print(f"❌ Test file not found: {test_path}")
        return False
    
    # Run the test with real services
    cmd = [
        sys.executable,
        str(test_path),
        "--real-services",
        "-v"
    ]
    
    # Set environment variables for testing
    env = os.environ.copy()
    env["USE_REAL_SERVICES"] = "true"
    env["REAL_LLM"] = "true"
    env["ENVIRONMENT"] = "test"
    env["PYTHONUNBUFFERED"] = "1"
    
    try:
        start_time = time.time()
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=test_info["timeout"],
            env=env
        )
        
        elapsed = time.time() - start_time
        
        # Check if test passed
        if result.returncode == 0:
            print(f"✅ PASSED in {elapsed:.1f}s")
            print_memory_status("After test (PASSED)")
            return True
        else:
            print(f"❌ FAILED after {elapsed:.1f}s")
            print("\n--- Test Output (last 50 lines) ---")
            lines = result.stdout.split('\n')
            for line in lines[-50:]:
                if line.strip():
                    print(line)
            
            if result.stderr:
                print("\n--- Error Output ---")
                print(result.stderr[-2000:])  # Last 2000 chars of stderr
            
            print_memory_status("After test (FAILED)")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏱️ TIMEOUT after {test_info['timeout']}s")
        print_memory_status("After test (TIMEOUT)")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        print_memory_status("After test (ERROR)")
        return False

def main():
    """Run all critical tests with proper isolation and memory management."""
    print("\n" + "="*80)
    print("🚨 CRITICAL AGENT TESTS - LIFE OR DEATH SITUATION")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Initial memory check
    mem = get_memory_usage()
    if mem["available_gb"] < 8:
        print(f"⚠️ WARNING: Only {mem['available_gb']:.1f}GB available. Recommended: 8GB+")
        print("Consider closing other applications to free memory.")
    
    print_memory_status("Initial")
    
    # Results tracking
    results = []
    
    # Run each test in isolation
    for i, test_info in enumerate(CRITICAL_TESTS, 1):
        print(f"\n{'#'*80}")
        print(f"TEST {i}/{len(CRITICAL_TESTS)}")
        print(f"{'#'*80}")
        
        # Clean up before each test
        cleanup_docker()
        time.sleep(5)  # Let system stabilize
        
        # Start fresh Docker services
        docker_started, project_name = start_docker_services()
        
        if not docker_started:
            print(f"⚠️ Skipping test due to Docker startup failure")
            results.append((test_info["name"], False, "Docker startup failed"))
            continue
        
        # Run the test
        try:
            passed = run_single_test(test_info)
            results.append((test_info["name"], passed, "Completed"))
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            results.append((test_info["name"], False, str(e)))
        finally:
            # Always stop Docker services after test
            stop_docker_services(project_name)
        
        # Brief pause between tests
        if i < len(CRITICAL_TESTS):
            print("\n⏸️  Pausing 10 seconds before next test...")
            time.sleep(10)
    
    # Final cleanup
    cleanup_docker()
    
    # Print summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    
    passed_count = sum(1 for _, passed, _ in results if passed)
    failed_count = len(results) - passed_count
    
    for test_name, passed, status in results:
        icon = "✅" if passed else "❌"
        print(f"{icon} {test_name}: {status}")
    
    print(f"\n📈 Results: {passed_count}/{len(results)} passed")
    
    if passed_count == len(CRITICAL_TESTS):
        print("\n🎉 SUCCESS! All critical tests passed!")
        print("✅ The product is ready for deployment!")
        return 0
    else:
        print(f"\n🚨 FAILURE! {failed_count} critical tests failed!")
        print("❌ The product is NOT ready - IMMEDIATE ACTION REQUIRED!")
        return 1

if __name__ == "__main__":
    sys.exit(main())