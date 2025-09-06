#!/usr/bin/env python3
"""
Docker System Health Check Tool
Comprehensive health check for all Docker services
"""
import sys
import os

# Fix Unicode encoding issues on Windows - MUST be done early
if sys.platform == "win32":
    import io
    # Set UTF-8 for subprocess and all Python I/O
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUTF8'] = '1'
    
    # Force Windows console to use UTF-8
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleCP(65001)
        kernel32.SetConsoleOutputCP(65001)
    except Exception:
        pass
    
    # Reconfigure stdout/stderr for UTF-8
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import subprocess
import json
import time
import socket
import urllib.request

def main():
    print('Docker System Health Check')
    print('=' * 80)

    # Define services and their health endpoints
    services = {
        'netra-backend': {'port': 8000, 'endpoint': '/health'},
        'netra-auth': {'port': 8081, 'endpoint': '/health'},
        'netra-frontend': {'port': 3000, 'endpoint': '/'},
        'netra-redis': {'port': 6379, 'type': 'redis'},
        'netra-postgres': {'port': 5432, 'type': 'postgres'},
        'netra-clickhouse': {'port': 8123, 'endpoint': '/ping'}
    }

    results = []
    
    for service_name, config in services.items():
        print(f'\nChecking {service_name}...')
        
        # Check if container is running
        ps_result = subprocess.run(['docker', 'ps', '--filter', f'name={service_name}', '--format', '{{.Status}}'],
                                  capture_output=True, text=True)
        
        if not ps_result.stdout.strip():
            print(f'  [ERROR] Container not running')
            results.append({'service': service_name, 'status': 'not_running', 'error': 'Container not found'})
            continue
        
        status = ps_result.stdout.strip()
        print(f'  Container status: {status}')
        
        # Check for errors in last 50 log lines
        logs_result = subprocess.run(['docker', 'logs', '--tail', '50', service_name],
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
        error_count = 0
        critical_errors = []
        for line in logs_result.stdout.split('\n'):
            if any(keyword in line.lower() for keyword in ['error', 'critical', 'exception', 'failed']):
                # Filter out non-critical errors
                skip_patterns = [
                    'info', 'warning', 'successfully', 'waiting',
                    'non-critical', 'graceful', 'retrying',
                    'will retry', 'creating network'
                ]
                if not any(skip in line.lower() for skip in skip_patterns):
                    error_count += 1
                    if error_count <= 3:
                        critical_errors.append(line[:150])
        
        if critical_errors:
            print(f'  [WARNING] Found {error_count} errors')
            for err in critical_errors:
                print(f'     - {err}')
        else:
            print(f'  [OK] No critical errors in recent logs')
        
        # Test endpoint if applicable
        if 'endpoint' in config:
            try:
                url = f"http://localhost:{config['port']}{config['endpoint']}"
                response = urllib.request.urlopen(url, timeout=3)
                print(f'  [OK] Endpoint responding: {response.status}')
                results.append({'service': service_name, 'status': 'healthy', 'http': response.status})
            except Exception as e:
                error_msg = str(e)[:50]
                print(f'  [ERROR] Endpoint not responding: {error_msg}')
                results.append({'service': service_name, 'status': 'unhealthy', 'error': str(e)[:100]})
        elif config.get('type') == 'redis':
            # Test Redis connection
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2)
                s.connect(('localhost', config['port']))
                s.send(b'PING\r\n')
                response = s.recv(1024)
                s.close()
                if b'PONG' in response:
                    print(f'  [OK] Redis responding: PONG')
                    results.append({'service': service_name, 'status': 'healthy'})
                else:
                    print(f'  [WARNING] Redis response unexpected')
                    results.append({'service': service_name, 'status': 'warning'})
            except Exception as e:
                print(f'  [ERROR] Redis not responding: {str(e)[:50]}')
                results.append({'service': service_name, 'status': 'unhealthy', 'error': str(e)[:100]})
        elif config.get('type') == 'postgres':
            # Test Postgres connection
            try:
                pg_result = subprocess.run(['docker', 'exec', service_name, 'pg_isready'],
                                         capture_output=True, text=True)
                if pg_result.returncode == 0:
                    print(f'  [OK] PostgreSQL is ready')
                    results.append({'service': service_name, 'status': 'healthy'})
                else:
                    print(f'  [ERROR] PostgreSQL not ready')
                    results.append({'service': service_name, 'status': 'unhealthy'})
            except Exception as e:
                print(f'  [ERROR] PostgreSQL check failed: {str(e)[:50]}')
                results.append({'service': service_name, 'status': 'unhealthy', 'error': str(e)[:100]})
        
        if critical_errors and results[-1].get('status') != 'unhealthy':
            results[-1]['warnings'] = critical_errors

    print('\n' + '=' * 80)
    print('Health Check Summary:')
    print('=' * 80)
    
    healthy_count = sum(1 for r in results if r['status'] == 'healthy')
    unhealthy_count = sum(1 for r in results if r['status'] == 'unhealthy')
    warning_count = sum(1 for r in results if r['status'] == 'warning' or 'warnings' in r)
    
    print(f'[OK] Healthy: {healthy_count}')
    print(f'[ERROR] Unhealthy: {unhealthy_count}')
    print(f'[WARNING] Warnings: {warning_count}')
    
    if unhealthy_count > 0:
        print('\nCritical Issues:')
        for r in results:
            if r['status'] == 'unhealthy':
                print(f"  - {r['service']}: {r.get('error', 'Unknown error')}")
    
    # Save results
    with open('docker_health_check.json', 'w') as f:
        json.dump({
            'timestamp': time.time(),
            'results': results,
            'summary': {
                'healthy': healthy_count,
                'unhealthy': unhealthy_count,
                'warnings': warning_count
            }
        }, f, indent=2)
    
    print('\nHealth check results saved to docker_health_check.json')
    
    # Return exit code based on health
    if unhealthy_count > 0:
        return 1
    elif warning_count > 0:
        return 2
    else:
        return 0

if __name__ == '__main__':
    sys.exit(main())