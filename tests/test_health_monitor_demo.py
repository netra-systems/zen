#!/usr/bin/env python3
"""
Demo script to test the enhanced health monitoring system.

This script demonstrates the new modular health monitoring architecture
with comprehensive checks for databases, Redis, WebSocket, and system resources.
"""

import asyncio
import time
from app.core.system_health_monitor import SystemHealthMonitor
from app.core.health_types import HealthStatus, HealthCheckResult


async def demo_health_checker() -> HealthCheckResult:
    """Demo health checker that simulates varying health."""
    health_score = 0.8 + 0.2 * (time.time() % 10) / 10  # Varies between 0.8-1.0
    return HealthCheckResult(
        component_name="demo_service",
        success=True,
        health_score=health_score,
        response_time_ms=50.0 + (time.time() % 5) * 10,  # 50-100ms
        metadata={"demo": True, "connections": int(time.time() % 20)}
    )


async def failing_health_checker() -> HealthCheckResult:
    """Demo health checker that occasionally fails."""
    if time.time() % 15 < 5:  # Fail for 1/3 of the time
        return HealthCheckResult(
            component_name="unstable_service",
            success=False,
            health_score=0.0,
            response_time_ms=5000.0,
            error_message="Service temporarily unavailable"
        )
    else:
        return HealthCheckResult(
            component_name="unstable_service",
            success=True,
            health_score=0.9,
            response_time_ms=25.0,
            metadata={"stable_period": True}
        )


def print_system_overview(monitor: SystemHealthMonitor):
    """Print comprehensive system health overview."""
    print("\n" + "="*60)
    print("SYSTEM HEALTH OVERVIEW")
    print("="*60)
    
    overview = monitor.get_system_overview()
    print(f"Overall Status: {overview['overall_status'].upper()}")
    print(f"System Health: {overview['system_health_percentage']:.1f}%")
    print(f"Uptime: {overview['uptime_seconds']:.1f} seconds")
    print(f"Active Alerts: {overview['active_alerts']}")
    print()
    
    print("Component Breakdown:")
    print(f"  • Healthy: {overview['healthy_components']}")
    print(f"  • Degraded: {overview['degraded_components']}")
    print(f"  • Unhealthy: {overview['unhealthy_components']}")
    print(f"  • Critical: {overview['critical_components']}")
    print(f"  • Total: {overview['total_components']}")
    print()
    
    print("Individual Component Health:")
    for name, health in monitor.component_health.items():
        status_color = {
            HealthStatus.HEALTHY: "✅",
            HealthStatus.DEGRADED: "⚠️",
            HealthStatus.UNHEALTHY: "❌",
            HealthStatus.CRITICAL: "🔥"
        }.get(health.status, "❓")
        
        response_time = health.metadata.get("response_time_ms", 0)
        print(f"  {status_color} {name}: {health.health_score:.2f} "
              f"({health.status.value}, {response_time:.1f}ms)")
    
    # Show recent alerts
    active_alerts = monitor.alert_manager.get_active_alerts()
    if active_alerts:
        print(f"\nActive Alerts ({len(active_alerts)}):")
        for alert in active_alerts[-5:]:  # Show last 5 alerts
            severity_icon = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "critical": "🔥"}
            icon = severity_icon.get(alert.severity, "❓")
            print(f"  {icon} [{alert.severity.upper()}] {alert.component}: {alert.message}")


async def alert_callback(alert):
    """Demo alert callback that prints alerts."""
    severity_icon = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "critical": "🔥"}
    icon = severity_icon.get(alert.severity, "❓")
    print(f"\n🔔 ALERT {icon} [{alert.severity.upper()}] {alert.component}: {alert.message}")


async def main():
    """Main demo function."""
    print("🏥 Health Monitoring System Demo")
    print("="*60)
    print("This demo shows the enhanced health monitoring system with:")
    print("• Modular architecture (≤300 lines per file)")
    print("• Functions ≤8 lines each")
    print("• Comprehensive health checks")
    print("• Real-time alerting")
    print("• Recovery mechanisms")
    print("• Production-ready monitoring")
    print()
    
    # Create monitor with short interval for demo
    monitor = SystemHealthMonitor(check_interval=3)
    
    # Register demo health checkers
    monitor.register_component_checker("demo_service", demo_health_checker)
    monitor.register_component_checker("unstable_service", failing_health_checker)
    
    # Register alert callback
    monitor.register_alert_callback(alert_callback)
    
    print("🚀 Starting health monitoring...")
    await monitor.start_monitoring()
    
    try:
        # Run for 30 seconds to show various states
        for i in range(10):
            await asyncio.sleep(3)
            print_system_overview(monitor)
            
            if i == 3:
                print("\n📊 Health monitoring active for 12 seconds...")
                print("   Observing component health changes and threshold alerts...")
            elif i == 6:
                print("\n🔍 Continuing monitoring...")
                print("   Watch for recovery patterns and system-wide health evaluation...")
    
    finally:
        print("\n🛑 Stopping health monitoring...")
        await monitor.stop_monitoring()
        
        # Final summary
        print("\n" + "="*60)
        print("FINAL SUMMARY")
        print("="*60)
        total_alerts = len(monitor.alert_manager.alerts)
        active_alerts = len(monitor.alert_manager.get_active_alerts())
        print(f"Total alerts generated: {total_alerts}")
        print(f"Active alerts: {active_alerts}")
        print(f"Monitoring uptime: {time.time() - monitor.start_time:.1f} seconds")
        
        if monitor.alert_manager.alerts:
            print("\nLast few alerts:")
            for alert in monitor.alert_manager.alerts[-3:]:
                print(f"  • [{alert.severity}] {alert.component}: {alert.message}")
        
        print("\n✅ Health monitoring demo completed successfully!")
        print("The modular architecture ensures maintainable, testable code.")


if __name__ == "__main__":
    asyncio.run(main())