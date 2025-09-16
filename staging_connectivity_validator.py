#!/usr/bin/env python3
"""
Comprehensive Staging Connectivity Validator for Issue #1264
Validates that Cloud SQL MySQL→PostgreSQL misconfiguration has been fixed by infrastructure team
"""

import asyncio
import time
import json
import logging
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional
import os
from urllib.parse import urlparse

import httpx
import websockets
import sqlalchemy
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, TimeoutError as SQLTimeoutError

class StagingConnectivityValidator:
    """Comprehensive validator for staging environment connectivity after Issue #1264 infrastructure fix"""

    def __init__(self):
        self.endpoints = {
            'api': 'https://api.staging.netrasystems.ai/health',
            'auth': 'https://auth.staging.netrasystems.ai/health',
            'frontend': 'https://chat.staging.netrasystems.ai',
        }
        self.results = {}
        self.timeout = 15

    async def test_http_connectivity(self) -> Dict[str, Any]:
        """Test HTTP connectivity to all staging services"""
        print("=== Testing HTTP Connectivity ===")
        results = {}

        for name, url in self.endpoints.items():
            start_time = time.time()
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url, follow_redirects=True)
                    duration = time.time() - start_time

                    results[name] = {
                        'url': url,
                        'status': 'UP' if response.status_code == 200 else f'HTTP {response.status_code}',
                        'status_code': response.status_code,
                        'response_time_ms': round(duration * 1000, 2),
                        'success': response.status_code == 200,
                        'content_length': len(response.content) if response.content else 0
                    }

                    if response.status_code == 200 and response.content:
                        try:
                            json_data = response.json()
                            results[name]['service_info'] = {
                                'status': json_data.get('status', 'unknown'),
                                'service': json_data.get('service', 'unknown'),
                                'version': json_data.get('version', 'unknown'),
                                'database_status': json_data.get('database_status', 'unknown')
                            }
                        except:
                            pass  # Not JSON response

                    success_icon = "[OK]" if results[name]['success'] else "[FAIL]"
                    print(f"  {name.upper()}: {success_icon} {results[name]['status']} ({results[name]['response_time_ms']}ms)")

            except Exception as e:
                duration = time.time() - start_time
                results[name] = {
                    'url': url,
                    'status': f'ERROR: {str(e)[:100]}',
                    'success': False,
                    'response_time_ms': round(duration * 1000, 2),
                    'error': str(e)
                }
                print(f"  {name.upper()}: [FAIL] {results[name]['status']} ({results[name]['response_time_ms']}ms)")

        return results

    async def test_websocket_connectivity(self) -> Dict[str, Any]:
        """Test WebSocket connectivity"""
        print("\n=== Testing WebSocket Connectivity ===")
        start_time = time.time()

        try:
            websocket_url = "wss://api.staging.netrasystems.ai/ws"

            # Test WebSocket connection
            websocket = await asyncio.wait_for(
                websockets.connect(websocket_url),
                timeout=self.timeout
            )

            connection_time = time.time() - start_time

            # Test ping
            ping_start = time.time()
            await websocket.ping()
            ping_time = time.time() - ping_start

            # Test message sending
            test_message = {"type": "connectivity_test", "timestamp": datetime.now().isoformat()}
            await websocket.send(json.dumps(test_message))

            await websocket.close()

            result = {
                'websocket_url': websocket_url,
                'success': True,
                'connection_time_ms': round(connection_time * 1000, 2),
                'ping_time_ms': round(ping_time * 1000, 2),
                'total_time_ms': round((time.time() - start_time) * 1000, 2)
            }

            print(f"  WebSocket: [OK] Connected ({result['connection_time_ms']}ms, ping: {result['ping_time_ms']}ms)")
            return result

        except Exception as e:
            duration = time.time() - start_time
            result = {
                'websocket_url': "wss://api.staging.netrasystems.ai/ws",
                'success': False,
                'error': str(e),
                'total_time_ms': round(duration * 1000, 2)
            }
            print(f"  WebSocket: [FAIL] {str(e)[:100]} ({result['total_time_ms']}ms)")
            return result

    async def test_database_connectivity(self) -> Dict[str, Any]:
        """Test database connectivity - the main Issue #1264 validation"""
        print("\n=== Testing Database Connectivity (Issue #1264) ===")

        # Database configuration that should work after infrastructure fix
        db_config = {
            'host': 'postgres.staging.netrasystems.ai',
            'port': '5432',
            'database': 'netra_staging',
            'user': os.environ.get('POSTGRES_USER', 'netra_user'),
            'password': os.environ.get('POSTGRES_PASSWORD', 'test_password'),
        }

        connection_url = f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"

        results = {
            'connection_test': None,
            'health_check_test': None,
            'transaction_test': None,
            'overall_success': False
        }

        # Test 1: Basic Connection
        print("  Testing basic database connection...")
        start_time = time.time()
        try:
            engine = create_engine(
                connection_url,
                pool_timeout=8.0,
                connect_args={"connect_timeout": 8.0}
            )

            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1 as test"))
                assert result.fetchone()[0] == 1

            connection_time = time.time() - start_time
            results['connection_test'] = {
                'success': True,
                'connection_time_ms': round(connection_time * 1000, 2),
                'status': 'Connected successfully'
            }
            print(f"    [OK] Basic connection: {results['connection_test']['connection_time_ms']}ms")

        except Exception as e:
            connection_time = time.time() - start_time
            results['connection_test'] = {
                'success': False,
                'connection_time_ms': round(connection_time * 1000, 2),
                'error': str(e),
                'status': f'Failed: {str(e)[:100]}'
            }
            print(f"    [FAIL] Basic connection failed: {results['connection_test']['connection_time_ms']}ms - {str(e)[:100]}")

            # Issue #1264 detection
            if connection_time >= 7.5:
                print(f"    *** ISSUE #1264 DETECTED: Connection timeout after {connection_time:.2f}s indicates Cloud SQL MySQL→PostgreSQL misconfiguration")

        # Test 2: Health Check Query (simulating /health endpoint)
        if results['connection_test'] and results['connection_test']['success']:
            print("  Testing health check queries...")
            start_time = time.time()
            try:
                engine = create_engine(connection_url, connect_args={"connect_timeout": 3.0})
                with engine.connect() as conn:
                    # Typical health check queries
                    result = conn.execute(text("SELECT 1"))
                    assert result.fetchone()[0] == 1

                    result = conn.execute(text("SELECT current_database()"))
                    db_name = result.fetchone()[0]
                    assert db_name == 'netra_staging'

                health_time = time.time() - start_time
                results['health_check_test'] = {
                    'success': True,
                    'health_time_ms': round(health_time * 1000, 2),
                    'database_name': db_name,
                    'status': 'Health check passed'
                }
                print(f"    [OK] Health check: {results['health_check_test']['health_time_ms']}ms")

            except Exception as e:
                health_time = time.time() - start_time
                results['health_check_test'] = {
                    'success': False,
                    'health_time_ms': round(health_time * 1000, 2),
                    'error': str(e),
                    'status': f'Failed: {str(e)[:100]}'
                }
                print(f"    [FAIL] Health check failed: {results['health_check_test']['health_time_ms']}ms - {str(e)[:100]}")

        # Test 3: Transaction Test
        if results['connection_test'] and results['connection_test']['success']:
            print("  Testing transaction handling...")
            start_time = time.time()
            try:
                engine = create_engine(connection_url, connect_args={"connect_timeout": 5.0})
                with engine.connect() as conn:
                    with conn.begin():
                        conn.execute(text("CREATE TEMP TABLE test_table (id SERIAL PRIMARY KEY, data TEXT)"))
                        conn.execute(text("INSERT INTO test_table (data) VALUES ('test')"))
                        count = conn.execute(text("SELECT COUNT(*) FROM test_table")).fetchone()[0]
                        assert count == 1

                transaction_time = time.time() - start_time
                results['transaction_test'] = {
                    'success': True,
                    'transaction_time_ms': round(transaction_time * 1000, 2),
                    'rows_processed': count,
                    'status': 'Transaction test passed'
                }
                print(f"    [OK] Transaction test: {results['transaction_test']['transaction_time_ms']}ms")

            except Exception as e:
                transaction_time = time.time() - start_time
                results['transaction_test'] = {
                    'success': False,
                    'transaction_time_ms': round(transaction_time * 1000, 2),
                    'error': str(e),
                    'status': f'Failed: {str(e)[:100]}'
                }
                print(f"    [FAIL] Transaction test failed: {results['transaction_test']['transaction_time_ms']}ms - {str(e)[:100]}")

        # Overall database connectivity assessment
        successful_tests = sum(1 for test in [results['connection_test'], results['health_check_test'], results['transaction_test']]
                             if test and test['success'])
        total_tests = sum(1 for test in [results['connection_test'], results['health_check_test'], results['transaction_test']]
                         if test is not None)

        results['overall_success'] = successful_tests == total_tests and total_tests > 0
        results['success_rate'] = successful_tests / total_tests if total_tests > 0 else 0

        return results

    async def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run all validation tests"""
        print("*** STAGING CONNECTIVITY VALIDATION - Issue #1264 ***")
        print("=" * 60)
        print("Validating that Cloud SQL MySQL->PostgreSQL misconfiguration has been fixed")
        print()

        start_time = time.time()

        # Run all tests
        http_results = await self.test_http_connectivity()
        websocket_results = await self.test_websocket_connectivity()
        database_results = await self.test_database_connectivity()

        total_time = time.time() - start_time

        # Compile overall results
        results = {
            'timestamp': datetime.now().isoformat(),
            'total_validation_time_ms': round(total_time * 1000, 2),
            'http_connectivity': http_results,
            'websocket_connectivity': websocket_results,
            'database_connectivity': database_results,
            'overall_assessment': self._assess_overall_status(http_results, websocket_results, database_results)
        }

        self._print_summary(results)
        return results

    def _assess_overall_status(self, http_results: Dict, websocket_results: Dict, database_results: Dict) -> Dict[str, Any]:
        """Assess overall status and determine if Issue #1264 is fixed"""

        # HTTP services status
        http_success_count = sum(1 for result in http_results.values() if result.get('success', False))
        http_total = len(http_results)

        # Database status (most critical for Issue #1264)
        database_success = database_results.get('overall_success', False)

        # WebSocket status
        websocket_success = websocket_results.get('success', False)

        # Overall determination
        if database_success and http_success_count >= 2 and websocket_success:
            status = "FULLY_OPERATIONAL"
            message = "[SUCCESS] All systems operational - Issue #1264 appears to be FIXED"
            infrastructure_fix_applied = True
        elif database_success and http_success_count >= 1:
            status = "PARTIALLY_OPERATIONAL"
            message = "[PARTIAL] Core database fixed, some services still recovering"
            infrastructure_fix_applied = True
        elif http_success_count >= 1:
            status = "INFRASTRUCTURE_IN_PROGRESS"
            message = "[PROGRESS] Some services up, database connectivity still being fixed"
            infrastructure_fix_applied = False
        else:
            status = "INFRASTRUCTURE_ISSUE_PERSISTS"
            message = "[ISSUE] Issue #1264 infrastructure fix not yet applied"
            infrastructure_fix_applied = False

        return {
            'status': status,
            'message': message,
            'infrastructure_fix_applied': infrastructure_fix_applied,
            'http_success_rate': http_success_count / http_total if http_total > 0 else 0,
            'database_connectivity': database_success,
            'websocket_connectivity': websocket_success,
            'ready_for_validation_framework': database_success and http_success_count >= 2
        }

    def _print_summary(self, results: Dict[str, Any]):
        """Print comprehensive summary"""
        print("\n" + "=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)

        assessment = results['overall_assessment']
        print(f"Status: {assessment['message']}")
        print(f"Total Validation Time: {results['total_validation_time_ms']}ms")
        print()

        # HTTP Services Summary
        print("HTTP Services:")
        for name, result in results['http_connectivity'].items():
            status_icon = "[OK]" if result['success'] else "[FAIL]"
            print(f"  {status_icon} {name.upper()}: {result['status']} ({result['response_time_ms']}ms)")

        # WebSocket Summary
        print()
        print("WebSocket:")
        ws_result = results['websocket_connectivity']
        ws_icon = "[OK]" if ws_result['success'] else "[FAIL]"
        ws_status = "Connected" if ws_result['success'] else f"Failed: {ws_result.get('error', 'Unknown')[:50]}"
        print(f"  {ws_icon} WebSocket: {ws_status} ({ws_result.get('total_time_ms', 0)}ms)")

        # Database Summary (Critical for Issue #1264)
        print()
        print("Database Connectivity (Issue #1264 Critical Test):")
        db_results = results['database_connectivity']

        if db_results['connection_test']:
            conn_test = db_results['connection_test']
            conn_icon = "[OK]" if conn_test['success'] else "[FAIL]"
            print(f"  {conn_icon} Connection: {conn_test['status']} ({conn_test['connection_time_ms']}ms)")

        if db_results['health_check_test']:
            health_test = db_results['health_check_test']
            health_icon = "[OK]" if health_test['success'] else "[FAIL]"
            print(f"  {health_icon} Health Check: {health_test['status']} ({health_test['health_time_ms']}ms)")

        if db_results['transaction_test']:
            trans_test = db_results['transaction_test']
            trans_icon = "[OK]" if trans_test['success'] else "[FAIL]"
            print(f"  {trans_icon} Transactions: {trans_test['status']} ({trans_test['transaction_time_ms']}ms)")

        print()
        print("RECOMMENDATIONS:")
        if assessment['infrastructure_fix_applied']:
            print("[SUCCESS] Infrastructure fix appears to be applied!")
            if assessment['ready_for_validation_framework']:
                print("[READY] Ready to run comprehensive Issue #1264 validation framework")
                print("   Next step: Run full test suite to validate all functionality")
            else:
                print("[WAIT] Wait for all services to fully recover, then run validation framework")
        else:
            print("[WAIT] Wait for infrastructure team to apply Cloud SQL configuration fix")
            print("[MONITOR] Continue monitoring with: python staging_monitor.py")

        print()
        print("=" * 60)

async def main():
    """Main entry point"""
    validator = StagingConnectivityValidator()
    results = await validator.run_comprehensive_validation()

    # Save results to file
    report_file = f"staging_connectivity_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"[REPORT] Detailed report saved to: {report_file}")

    # Return appropriate exit code
    if results['overall_assessment']['infrastructure_fix_applied']:
        return 0  # Success
    else:
        return 1  # Infrastructure issue persists

if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)