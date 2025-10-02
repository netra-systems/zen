#!/usr/bin/env python3
"""
🌍 Zen Community Analytics - Interactive Demo

This script demonstrates how community analytics work in real-time.
Run this to see exactly what data gets collected and how privacy is protected.
"""

import os
import json
import time
import uuid
from datetime import datetime


def print_banner():
    """Print demo banner"""
    print("=" * 70)
    print("🌍 ZEN COMMUNITY ANALYTICS - LIVE DEMO")
    print("=" * 70)
    print("Demonstrating Path 1: Anonymous Public Telemetry")
    print("✅ No authentication required")
    print("🔒 Complete privacy protection")
    print("📊 Contributing to community insights")
    print("=" * 70)
    print()


def demo_basic_import():
    """Demo 1: Basic zen import"""
    print("📍 DEMO 1: Basic Zen Import with Community Analytics")
    print("-" * 50)

    print("Code: import zen")
    print()

    try:
        # Simulate zen import
        print("⏳ Importing zen...")
        time.sleep(1)

        # Show community analytics activation
        print("✅ Community analytics activated!")
        print("📡 Target project: netra-telemetry-public")

        # Show generated session ID
        session_id = f"zen_community_{uuid.uuid4().hex[:8]}"
        print(f"🔑 Anonymous session: {session_id}")

        # Show resource attributes
        resource_attrs = {
            "service.name": "zen-orchestrator",
            "service.version": "1.0.3",
            "zen.analytics.type": "community",
            "zen.analytics.session": session_id,
            "zen.platform.os": os.name,
            "zen.differentiator": "community_analytics"
        }

        print("📋 Resource attributes:")
        print(json.dumps(resource_attrs, indent=2))

    except ImportError:
        print("ℹ️  zen not installed - showing simulated output")

    print("\n" + "=" * 70 + "\n")


def demo_trace_generation():
    """Demo 2: Trace generation simulation"""
    print("📍 DEMO 2: Community Trace Generation")
    print("-" * 50)

    print("Code: orchestrator.run_instance('demo')")
    print()

    # Simulate trace generation
    trace_id = uuid.uuid4().hex
    span_id = uuid.uuid4().hex[:16]
    start_time = datetime.utcnow()

    print("⏳ Executing zen orchestrator...")
    time.sleep(2)  # Simulate execution

    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds() * 1000

    # Generate community trace
    community_trace = {
        "trace_id": trace_id,
        "span_id": span_id,
        "span_name": "orchestrator.run_instance",
        "start_time": start_time.isoformat() + "Z",
        "end_time": end_time.isoformat() + "Z",
        "duration_ms": int(duration),
        "status": "OK",
        "attributes": {
            "function.name": "run_instance",
            "function.module": "zen_orchestrator",
            "function.type": "async",
            "zen.analytics.type": "community",
            "zen.analytics.anonymous": True,
            "zen.differentiator": "open_source_analytics",
            "zen.contribution": "public_insights",
            "instance.name": "[INSTANCE_REDACTED]",
            "workspace.path": "[PATH_REDACTED]",
            "performance.duration_ms": int(duration)
        }
    }

    print("📊 Generated community trace:")
    print(json.dumps(community_trace, indent=2))

    print("\n🚀 Trace sent to: netra-telemetry-public")
    print("📈 Contributing to community performance metrics")

    print("\n" + "=" * 70 + "\n")


def demo_privacy_protection():
    """Demo 3: Privacy protection simulation"""
    print("📍 DEMO 3: Privacy Protection in Action")
    print("-" * 50)

    # Simulate user code with sensitive data
    sensitive_input = {
        "workspace": "/Users/john.doe@company.com/secret-project",
        "api_key": "sk_live_abc123def456ghi789",
        "email": "john.doe@company.com",
        "phone": "555-123-4567",
        "database": "postgresql://user:secret@db.company.com/private"
    }

    print("🔴 Original user data (SENSITIVE):")
    print(json.dumps(sensitive_input, indent=2))
    print()

    print("⏳ Applying community-mode PII filtering...")
    time.sleep(1)

    # Simulate sanitization
    sanitized_output = {
        "workspace": "[PATH_REDACTED]",
        "api_key": "[API_KEY_REDACTED]",
        "email": "[EMAIL_REDACTED]",
        "phone": "[PHONE_REDACTED]",
        "database": "[URL_REDACTED]"
    }

    print("🟢 Sanitized data (SAFE FOR COMMUNITY):")
    print(json.dumps(sanitized_output, indent=2))
    print()

    print("🛡️ Privacy protections applied:")
    print("  ✅ Email addresses redacted")
    print("  ✅ API keys redacted")
    print("  ✅ Phone numbers redacted")
    print("  ✅ File paths redacted")
    print("  ✅ Database URLs redacted")

    print("\n✨ Only anonymous performance data sent to community")

    print("\n" + "=" * 70 + "\n")


def demo_community_insights():
    """Demo 4: Community insights simulation"""
    print("📍 DEMO 4: Community Insights Dashboard Preview")
    print("-" * 50)

    # Simulate aggregated community data
    community_metrics = {
        "total_executions_today": 8934,
        "active_community_users": 1247,
        "average_performance": {
            "initialization_ms": 18,
            "execution_ms": 4200,
            "success_rate": 94.8
        },
        "platform_distribution": {
            "macOS": 45.2,
            "Linux": 41.8,
            "Windows": 13.0
        },
        "trending_features": [
            {"name": "parallel_instances", "growth": "+45%"},
            {"name": "token_budgeting", "growth": "+32%"},
            {"name": "custom_configs", "growth": "+28%"}
        ]
    }

    print("📊 Live Community Analytics (analytics.zen.dev):")
    print()
    print(f"🌍 Total Executions Today: {community_metrics['total_executions_today']:,}")
    print(f"👥 Active Users: {community_metrics['active_community_users']:,}")
    print(f"⚡ Avg Performance: {community_metrics['average_performance']['execution_ms']}ms")
    print(f"✅ Success Rate: {community_metrics['average_performance']['success_rate']}%")
    print()

    print("🖥️ Platform Distribution:")
    for platform, percentage in community_metrics['platform_distribution'].items():
        print(f"  {platform}: {percentage}%")
    print()

    print("🔥 Trending Features:")
    for feature in community_metrics['trending_features']:
        print(f"  {feature['name']}: {feature['growth']}")

    print("\n🎯 YOUR CONTRIBUTION:")
    print("  📈 Your traces help improve these community insights")
    print("  🤝 Everyone benefits from shared performance data")
    print("  🔍 Transparent analytics vs commercial black boxes")

    print("\n" + "=" * 70 + "\n")


def demo_zen_vs_apex():
    """Demo 5: Zen vs Apex comparison"""
    print("📍 DEMO 5: Zen vs Apex - The Difference")
    print("-" * 50)

    print("🌍 ZEN COMMUNITY ANALYTICS (Open Source):")
    print("  ✅ Zero setup - just import zen")
    print("  🆓 Free forever - Netra covers costs")
    print("  📊 Public insights - community benefits")
    print("  🤝 Collaborative improvement")
    print()

    print("🔒 APEX COMMERCIAL ANALYTICS (Proprietary):")
    print("  🔐 Secure OAuth setup")
    print("  💰 Premium plans with Personalized AI Optimization benefits")
    print("  👤 Data is not shared with community")
    print("  🏢 Individual customer focus")

    print("\n" + "=" * 70 + "\n")


def demo_opt_out():
    """Demo 6: Opt-out mechanism"""
    print("📍 DEMO 6: Easy Opt-Out (User Choice)")
    print("-" * 50)

    print("🔧 Three ways to disable community analytics:")
    print()

    print("Method 1 - Environment Variable:")
    print("  export ZEN_TELEMETRY_DISABLED=true")
    print()

    print("Method 2 - Command Line Flag:")
    print("  zen --no-telemetry \"/analyze-code\"")
    print()

    print("Method 3 - Programmatic:")
    print("  from zen.telemetry import disable_telemetry")
    print("  disable_telemetry()")
    print()

    print("✅ Opt-out respected immediately")
    print("🔒 Zero data collection when disabled")
    print("🤝 Choice always with the user")

    print("\n" + "=" * 70 + "\n")


def main():
    """Run the complete demo"""
    print_banner()

    try:
        demo_basic_import()
        demo_trace_generation()
        demo_privacy_protection()
        demo_community_insights()
        demo_zen_vs_apex()
        demo_opt_out()

        print("🎉 DEMO COMPLETE!")
        print("=" * 70)
        print("Ready to contribute to the community?")
        print("Just run: pip install netra-zen")
        print("Your anonymous usage will help make Zen better for everyone! 🌍")

    except KeyboardInterrupt:
        print("\n\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo error: {e}")


if __name__ == "__main__":
    main()