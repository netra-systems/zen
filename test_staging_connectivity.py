#!/usr/bin/env python
"""
Test staging environment connectivity for Golden Path E2E tests.
"""
import sys
import traceback
import requests
from pathlib import Path

# Setup path
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

def test_staging_connectivity():
    """Test connectivity to staging services."""
    results = {}

    print("🌐 Testing Staging Environment Connectivity...")
    print("=" * 60)

    # Staging endpoints to test
    endpoints = {
        "Backend API": "https://staging.netrasystems.ai/health",
        "Auth Service": "https://staging.netrasystems.ai/auth/health",
        "Frontend": "https://staging.netrasystems.ai",
        "WebSocket Endpoint": "wss://api-staging.netrasystems.ai/api/v1/websocket"
    }

    for service_name, url in endpoints.items():
        try:
            if url.startswith("wss://"):
                # Skip WebSocket for now - would need websockets library
                results[service_name] = "⚠️ SKIPPED (WebSocket)"
                print(f"{service_name}: {results[service_name]} - {url}")
                continue

            print(f"\n🔍 Testing {service_name}: {url}")

            # Test with timeout
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                results[service_name] = "✅ HEALTHY"
                print(f"✅ {service_name}: {response.status_code} OK")

                # Try to get some content info
                content_length = len(response.text) if response.text else 0
                print(f"   Content length: {content_length} chars")

            else:
                results[service_name] = f"⚠️ STATUS {response.status_code}"
                print(f"⚠️ {service_name}: HTTP {response.status_code}")

        except requests.exceptions.Timeout:
            results[service_name] = "❌ TIMEOUT"
            print(f"❌ {service_name}: Connection timeout")

        except requests.exceptions.ConnectionError as e:
            results[service_name] = "❌ CONNECTION_ERROR"
            print(f"❌ {service_name}: Connection error - {e}")

        except Exception as e:
            results[service_name] = f"❌ ERROR: {e}"
            print(f"❌ {service_name}: Unexpected error - {e}")

    # Summary
    print("\n" + "=" * 60)
    print("📊 STAGING CONNECTIVITY SUMMARY:")
    print("=" * 60)

    healthy_count = 0
    for service, status in results.items():
        print(f"{service}: {status}")
        if "HEALTHY" in status:
            healthy_count += 1

    total_services = len([s for s in results.values() if "SKIPPED" not in s])
    if total_services > 0:
        health_percentage = (healthy_count / total_services) * 100
        print(f"\n🎯 Health Rate: {healthy_count}/{total_services} ({health_percentage:.1f}%)")

    if healthy_count > 0:
        print("🎉 At least some staging services are accessible!")
        print("✅ Golden Path E2E tests may be able to run")
        return True
    else:
        print("⚠️ No staging services are healthy")
        print("❌ Golden Path E2E tests will likely fail")
        return False

if __name__ == "__main__":
    try:
        success = test_staging_connectivity()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Critical error during connectivity test: {e}")
        traceback.print_exc()
        sys.exit(1)