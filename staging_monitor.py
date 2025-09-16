#!/usr/bin/env python3
"""
Staging Environment Monitor for Issue #1264
Monitors for infrastructure team fixes to Cloud SQL MySQL→PostgreSQL misconfiguration
"""

import time
import requests
import json
from datetime import datetime
import signal
import sys

class StagingMonitor:
    def __init__(self):
        self.endpoints = {
            'api': 'https://api.staging.netrasystems.ai/health',
            'auth': 'https://auth.staging.netrasystems.ai/health',
            'websocket': 'https://api.staging.netrasystems.ai/ws/health'
        }
        self.timeout = 10
        self.monitoring = True

    def signal_handler(self, sig, frame):
        print('\n\nMonitoring stopped by user.')
        self.monitoring = False
        sys.exit(0)

    def test_endpoint(self, name, url):
        """Test a single endpoint and return status"""
        start_time = time.time()
        try:
            response = requests.get(url, timeout=self.timeout)
            response_time = round((time.time() - start_time) * 1000, 2)

            return {
                'name': name,
                'url': url,
                'status': 'UP' if response.status_code == 200 else f'HTTP {response.status_code}',
                'response_time_ms': response_time,
                'content_length': len(response.content) if response.content else 0,
                'response_preview': response.text[:200] if response.text else ''
            }
        except requests.exceptions.Timeout:
            response_time = round((time.time() - start_time) * 1000, 2)
            return {
                'name': name,
                'url': url,
                'status': 'TIMEOUT',
                'response_time_ms': response_time,
                'content_length': 0,
                'response_preview': ''
            }
        except requests.exceptions.ConnectionError as e:
            response_time = round((time.time() - start_time) * 1000, 2)
            return {
                'name': name,
                'url': url,
                'status': f'CONNECTION_ERROR: {str(e)[:100]}',
                'response_time_ms': response_time,
                'content_length': 0,
                'response_preview': ''
            }
        except Exception as e:
            response_time = round((time.time() - start_time) * 1000, 2)
            return {
                'name': name,
                'url': url,
                'status': f'ERROR: {str(e)[:100]}',
                'response_time_ms': response_time,
                'content_length': 0,
                'response_preview': ''
            }

    def check_all_endpoints(self):
        """Check all endpoints and return results"""
        results = {}
        for name, url in self.endpoints.items():
            results[name] = self.test_endpoint(name, url)
        return results

    def detect_improvements(self, current, previous):
        """Detect if there are any improvements from previous check"""
        improvements = []

        for name, current_result in current.items():
            if name in previous:
                prev_result = previous[name]

                # Check if status improved
                if prev_result['status'] != 'UP' and current_result['status'] == 'UP':
                    improvements.append(f"✅ {name.upper()} is now UP!")

                # Check if response time improved significantly
                if (prev_result['response_time_ms'] > 8000 and
                    current_result['response_time_ms'] < 5000):
                    improvements.append(f"⚡ {name.upper()} response time improved: {prev_result['response_time_ms']}ms → {current_result['response_time_ms']}ms")

                # Check if timeouts stopped
                if 'TIMEOUT' in prev_result['status'] and 'TIMEOUT' not in current_result['status']:
                    improvements.append(f"🔧 {name.upper()} no longer timing out")

        return improvements

    def print_status(self, results, improvements=None):
        """Print current status in a readable format"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n{'='*80}")
        print(f"STAGING ENVIRONMENT STATUS - {timestamp}")
        print(f"{'='*80}")

        if improvements:
            print("*** IMPROVEMENTS DETECTED:")
            for improvement in improvements:
                # Remove emoji characters for Windows compatibility
                clean_improvement = improvement.replace("✅", "[OK]").replace("⚡", "[FAST]").replace("🔧", "[FIXED]")
                print(f"   {clean_improvement}")
            print()

        for name, result in results.items():
            status_icon = "[UP]" if result['status'] == 'UP' else "[DOWN]"
            print(f"{status_icon} {name.upper()}:")
            print(f"   Status: {result['status']}")
            print(f"   Response Time: {result['response_time_ms']}ms")
            print(f"   URL: {result['url']}")

            if result['response_preview'] and result['status'] == 'UP':
                preview = result['response_preview'].replace('\n', ' ')[:100]
                print(f"   Response: {preview}...")
            print()

        # Overall assessment
        up_count = sum(1 for r in results.values() if r['status'] == 'UP')
        total_count = len(results)
        print(f"OVERALL: {up_count}/{total_count} services operational")

        if up_count == total_count:
            print("*** ALL SERVICES ARE UP! Infrastructure fix may be complete!")
        elif up_count > 0:
            print("*** Partial service availability - infrastructure fix may be in progress")
        else:
            print("*** No services available - infrastructure issue persists")

    def monitor_continuously(self, interval_seconds=300):
        """Monitor continuously with specified interval"""
        print("Starting continuous monitoring of staging environment...")
        print(f"Checking every {interval_seconds} seconds. Press Ctrl+C to stop.")

        signal.signal(signal.SIGINT, self.signal_handler)

        previous_results = None

        while self.monitoring:
            try:
                current_results = self.check_all_endpoints()
                improvements = []

                if previous_results:
                    improvements = self.detect_improvements(current_results, previous_results)

                self.print_status(current_results, improvements)

                # Save results for next comparison
                previous_results = current_results

                # If all services are up, we should run our validation
                up_count = sum(1 for r in current_results.values() if r['status'] == 'UP')
                if up_count == len(current_results):
                    print("\n*** ALERT: All services are UP! Consider running Issue #1264 validation framework!")
                    print("   Command: python staging_connectivity_validator.py")

                if self.monitoring:
                    print(f"\nNext check in {interval_seconds} seconds...")
                    time.sleep(interval_seconds)

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error during monitoring: {e}")
                time.sleep(10)

        print("Monitoring stopped.")

def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Monitor staging environment for Issue #1264 infrastructure fixes')
    parser.add_argument('--interval', type=int, default=300, help='Check interval in seconds (default: 300)')
    parser.add_argument('--once', action='store_true', help='Run check once and exit')

    args = parser.parse_args()

    monitor = StagingMonitor()

    if args.once:
        print("Running single check of staging environment...")
        results = monitor.check_all_endpoints()
        monitor.print_status(results)
    else:
        monitor.monitor_continuously(args.interval)

if __name__ == '__main__':
    main()