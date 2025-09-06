#!/usr/bin/env python3
"""
Test script for Docker crash analysis with Windows Event Viewer integration.

This script demonstrates how to use the new Windows Event Viewer integration
in the UnifiedDockerManager for analyzing Docker crashes.
"""

import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from test_framework.unified_docker_manager import UnifiedDockerManager
from test_framework.windows_event_viewer import WindowsDockerEventViewer, DockerCrashAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_windows_event_viewer():
    """Test Windows Event Viewer functionality."""
    print("\n" + "="*60)
    print("Testing Windows Event Viewer Integration")
    print("="*60)
    
    # Create event viewer instance
    viewer = WindowsDockerEventViewer(hours_back=24)
    
    # Get Docker service status
    print("\n📊 Docker Service Status:")
    service_status = viewer.get_docker_service_status()
    for service_name, status in service_status.items():
        if isinstance(status, dict):
            print(f"  - {service_name}: {status.get('Status', 'Unknown')}")
    
    # Get recent Docker crashes
    print("\n🔥 Recent Docker Crashes (last hour):")
    crashes = viewer.get_recent_docker_crashes(hours=1)
    if crashes:
        for crash in crashes[:5]:  # Show first 5
            print(f"  - [{crash.timestamp}] {crash.source}: {crash.message[:100]}...")
    else:
        print("  No recent crashes found")
    
    # Get Docker event logs
    print("\n📝 Docker Event Logs (last 24 hours):")
    events = viewer.get_docker_crash_logs(limit=10)
    if events:
        for event in events[:5]:  # Show first 5
            print(f"  - [{event.level.value}] {event.source}: {event.message[:100]}...")
    else:
        print("  No Docker events found")


def test_docker_manager_crash_analysis():
    """Test Docker crash analysis through UnifiedDockerManager."""
    print("\n" + "="*60)
    print("Testing UnifiedDockerManager Crash Analysis")
    print("="*60)
    
    # Create Docker manager instance
    manager = UnifiedDockerManager()
    
    # Analyze Docker crashes
    print("\n🔍 Analyzing Docker environment...")
    analysis = manager.analyze_docker_crash(
        save_report=True,
        include_event_viewer=True
    )
    
    # Display analysis results
    print("\n📊 Analysis Results:")
    print(f"  - Platform: {analysis.get('platform')}")
    print(f"  - Timestamp: {analysis.get('timestamp')}")
    
    if "docker_status" in analysis:
        docker_status = analysis["docker_status"]
        print(f"  - Docker Running: {docker_status.get('running', False)}")
    
    if "windows_event_viewer" in analysis:
        event_data = analysis["windows_event_viewer"]
        if "recent_crashes" in event_data:
            print(f"  - Recent Crashes: {len(event_data['recent_crashes'])}")
        if "service_status" in event_data:
            print(f"  - Services Checked: {len(event_data['service_status'])}")
    
    if "report_path" in analysis:
        print(f"\n📄 Full report saved to: {analysis['report_path']}")
    
    # Get Windows Event Logs directly
    print("\n📋 Direct Windows Event Log Access:")
    events = manager.get_windows_event_logs(hours_back=1, limit=5)
    if events:
        for event in events:
            print(f"  - [{event['level']}] {event['source']}: {event['message'][:80]}...")
    else:
        print("  No events found or not on Windows")
    
    # Get Windows Docker service status
    print("\n🔧 Windows Docker Service Status:")
    service_status = manager.get_docker_service_status_windows()
    if "error" not in service_status:
        for service, status in service_status.items():
            if isinstance(status, dict):
                print(f"  - {service}: {status.get('Status', 'Unknown')}")
    else:
        print(f"  {service_status['error']}")


def test_crash_analyzer():
    """Test the standalone crash analyzer."""
    print("\n" + "="*60)
    print("Testing Standalone Docker Crash Analyzer")
    print("="*60)
    
    analyzer = DockerCrashAnalyzer()
    
    print("\n🔍 Running comprehensive crash analysis...")
    analysis = analyzer.analyze_docker_crash(save_report=True)
    
    print("\n📊 Analysis Summary:")
    print(f"  - Platform: {analysis.get('platform')}")
    
    if "docker_info" in analysis:
        docker_info = analysis["docker_info"]
        if "version" in docker_info:
            print("  - Docker Version: Available")
        if "system" in docker_info:
            print("  - Docker System Info: Available")
    
    if "windows_events" in analysis:
        windows_events = analysis["windows_events"]
        if "recent_crashes" in windows_events:
            crashes = windows_events["recent_crashes"]
            print(f"  - Windows Event Crashes: {len(crashes)}")
        if "service_status" in windows_events:
            services = windows_events["service_status"]
            print(f"  - Windows Services: {len(services)}")
    
    if "report_path" in analysis:
        print(f"\n📄 Analysis report saved to: {analysis['report_path']}")


def main():
    """Main test function."""
    import platform
    
    print("\n" + "#"*60)
    print("# Docker Crash Analysis Test Suite")
    print("#"*60)
    print(f"\nPlatform: {platform.system()} {platform.release()}")
    
    if platform.system() == "Windows":
        print("✅ Running on Windows - Full Event Viewer support available")
    else:
        print("⚠️ Not running on Windows - Event Viewer features will be skipped")
    
    try:
        # Test Windows Event Viewer directly
        if platform.system() == "Windows":
            test_windows_event_viewer()
        
        # Test UnifiedDockerManager integration
        test_docker_manager_crash_analysis()
        
        # Test standalone crash analyzer
        test_crash_analyzer()
        
        print("\n" + "#"*60)
        print("# All tests completed successfully!")
        print("#"*60)
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print("\n❌ Test suite failed. Check logs for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()