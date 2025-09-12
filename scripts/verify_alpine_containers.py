#!/usr/bin/env python3
"""
Alpine Container Verification and Optimization Script

Verifies that Alpine containers are properly configured and optimized for:
- Minimal memory usage
- Fast startup times
- Proper health checks
- Resource limits

Usage:
    python scripts/verify_alpine_containers.py [options]
    
Options:
    --env ENV           Environment to verify (dev, test, alpine-test, ci)
    --build             Build images before verification
    --benchmark         Run performance benchmarks
    --fix               Attempt to fix found issues
"""

import argparse
import subprocess
import sys
import time
import json
import psutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime

# Configuration
ALPINE_ENVIRONMENTS = ['alpine-test', 'ci']
MAX_STARTUP_TIME = 30  # seconds
MAX_MEMORY_MB = {
    'postgres': 1024,
    'redis': 512,
    'clickhouse': 1024,
    'backend': 2048,
    'auth': 2048,
    'frontend': 512
}

# Health check endpoints
HEALTH_ENDPOINTS = {
    'backend': 'http://localhost:{port}/health',
    'auth': 'http://localhost:{port}/health',
    'frontend': 'http://localhost:{port}/api/health'
}


class AlpineVerifier:
    """Verifies and optimizes Alpine containers"""
    
    def __init__(self, env: str = 'alpine-test'):
        self.env = env
        self.compose_file = 'docker-compose.unified.yml'
        self.env_file = self._get_env_file(env)
        self.results = {
            'startup_times': {},
            'memory_usage': {},
            'health_checks': {},
            'image_sizes': {},
            'issues': []
        }
    
    def _get_env_file(self, env: str) -> str:
        """Get the appropriate env file for the environment"""
        env_map = {
            'dev': '.env.local',
            'test': '.env.test',
            'alpine-test': '.env.alpine-test',
            'ci': '.env.ci'
        }
        return env_map.get(env, '.env.local')
    
    def run_docker_command(self, *args, capture_output: bool = True) -> subprocess.CompletedProcess:
        """Run a docker-compose command"""
        cmd = [
            'docker-compose',
            '-f', self.compose_file,
            '--env-file', self.env_file
        ]
        
        if self.env in ALPINE_ENVIRONMENTS:
            cmd.extend(['--profile', self.env])
        
        cmd.extend(args)
        
        return subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            timeout=120
        )
    
    def check_alpine_dockerfiles(self) -> List[str]:
        """Verify Alpine Dockerfiles exist and are optimized"""
        issues = []
        dockerfiles = [
            'docker/backend.alpine.Dockerfile',
            'docker/auth.alpine.Dockerfile',
            'docker/frontend.alpine.Dockerfile'
        ]
        
        for dockerfile in dockerfiles:
            path = Path(dockerfile)
            if not path.exists():
                issues.append(f"Missing Alpine Dockerfile: {dockerfile}")
                continue
            
            with open(path, 'r') as f:
                content = f.read()
                
                # Check for optimization patterns
                if 'alpine3.19' not in content and 'alpine' not in content.lower():
                    issues.append(f"{dockerfile} not using Alpine base image")
                
                if '--no-cache' not in content:
                    issues.append(f"{dockerfile} not using --no-cache for apk")
                
                if 'rm -rf /var/cache/apk' not in content:
                    issues.append(f"{dockerfile} not cleaning apk cache")
                
                if 'USER' not in content and 'adduser' not in content:
                    issues.append(f"{dockerfile} not using non-root user")
                
                if 'tini' not in content and 'dumb-init' not in content:
                    issues.append(f"{dockerfile} not using init system")
        
        return issues
    
    def build_images(self) -> bool:
        """Build Alpine images"""
        print("Building Alpine images...")
        
        result = self.run_docker_command('build', '--no-cache')
        
        if result.returncode != 0:
            print(f"Build failed: {result.stderr}")
            return False
        
        print("Images built successfully")
        return True
    
    def measure_image_sizes(self) -> Dict[str, float]:
        """Measure Docker image sizes"""
        sizes = {}
        
        # Image names based on environment
        image_prefix = {
            'alpine-test': 'netra-alpine-test',
            'ci': 'netra-ci',
            'test': 'netra-test',
            'dev': 'netra-dev'
        }.get(self.env, 'netra')
        
        services = ['backend', 'auth', 'frontend']
        
        for service in services:
            image_name = f"{image_prefix}-{service}:latest"
            
            result = subprocess.run(
                ['docker', 'images', image_name, '--format', '{{.Size}}'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and result.stdout.strip():
                size_str = result.stdout.strip()
                # Convert size to MB
                if 'GB' in size_str:
                    size_mb = float(size_str.replace('GB', '')) * 1024
                elif 'MB' in size_str:
                    size_mb = float(size_str.replace('MB', ''))
                else:
                    size_mb = 0
                
                sizes[service] = size_mb
                
                # Check if size is optimized (Alpine should be < 200MB for Python)
                if service in ['backend', 'auth'] and size_mb > 200:
                    self.results['issues'].append(
                        f"{service} image size ({size_mb:.1f}MB) exceeds Alpine target (200MB)"
                    )
        
        return sizes
    
    def start_services(self) -> bool:
        """Start Docker services"""
        print(f"Starting services for {self.env}...")
        
        result = self.run_docker_command('up', '-d')
        
        if result.returncode != 0:
            print(f"Failed to start services: {result.stderr}")
            return False
        
        return True
    
    def measure_startup_time(self, service: str) -> float:
        """Measure time for a service to become healthy"""
        start_time = time.time()
        container_name = f"netra-{self.env}-{service}"
        
        for _ in range(MAX_STARTUP_TIME):
            result = subprocess.run(
                ['docker', 'inspect', container_name, '--format', '{{.State.Health.Status}}'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                status = result.stdout.strip()
                if status == 'healthy':
                    return time.time() - start_time
            
            time.sleep(1)
        
        return -1  # Service didn't become healthy
    
    def measure_memory_usage(self, service: str) -> float:
        """Measure memory usage of a service"""
        container_name = f"netra-{self.env}-{service}"
        
        result = subprocess.run(
            ['docker', 'stats', container_name, '--no-stream', '--format', '{{.MemUsage}}'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            mem_str = result.stdout.strip()
            # Parse memory usage (e.g., "123.4MiB / 512MiB")
            if '/' in mem_str:
                used = mem_str.split('/')[0].strip()
                if 'MiB' in used:
                    return float(used.replace('MiB', ''))
                elif 'GiB' in used:
                    return float(used.replace('GiB', '')) * 1024
        
        return 0
    
    def verify_health_checks(self) -> Dict[str, bool]:
        """Verify health check configurations"""
        health_status = {}
        
        services = ['postgres', 'redis', 'clickhouse', 'backend', 'auth', 'frontend']
        
        for service in services:
            container_name = f"netra-{self.env}-{service}"
            
            # Check if health check is configured
            result = subprocess.run(
                ['docker', 'inspect', container_name, '--format', '{{json .Config.Healthcheck}}'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                try:
                    healthcheck = json.loads(result.stdout.strip())
                    if healthcheck and healthcheck.get('Test'):
                        health_status[service] = True
                        
                        # Verify health check parameters
                        interval = healthcheck.get('Interval', 0) / 1e9  # Convert nanoseconds
                        if interval > 30:
                            self.results['issues'].append(
                                f"{service} health check interval ({interval}s) too long"
                            )
                    else:
                        health_status[service] = False
                        self.results['issues'].append(f"{service} missing health check")
                except json.JSONDecodeError:
                    health_status[service] = False
        
        return health_status
    
    def verify_resource_limits(self) -> Dict[str, Dict[str, float]]:
        """Verify resource limits are configured"""
        limits = {}
        
        services = ['postgres', 'redis', 'clickhouse', 'backend', 'auth', 'frontend']
        
        for service in services:
            container_name = f"netra-{self.env}-{service}"
            
            result = subprocess.run(
                ['docker', 'inspect', container_name, '--format', 
                 '{{json .HostConfig.Memory}},{{json .HostConfig.CpuQuota}}'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                try:
                    parts = result.stdout.strip().split(',')
                    memory_bytes = int(parts[0]) if parts[0] != '0' else 0
                    cpu_quota = int(parts[1]) if len(parts) > 1 and parts[1] != '0' else 0
                    
                    limits[service] = {
                        'memory_mb': memory_bytes / (1024 * 1024) if memory_bytes else 0,
                        'cpu_cores': cpu_quota / 100000 if cpu_quota else 0
                    }
                    
                    # Check if limits are set
                    if memory_bytes == 0:
                        self.results['issues'].append(f"{service} missing memory limit")
                    elif service in MAX_MEMORY_MB:
                        if limits[service]['memory_mb'] > MAX_MEMORY_MB[service]:
                            self.results['issues'].append(
                                f"{service} memory limit ({limits[service]['memory_mb']:.0f}MB) "
                                f"exceeds target ({MAX_MEMORY_MB[service]}MB)"
                            )
                    
                    if cpu_quota == 0:
                        self.results['issues'].append(f"{service} missing CPU limit")
                    
                except (ValueError, IndexError):
                    limits[service] = {'memory_mb': 0, 'cpu_cores': 0}
        
        return limits
    
    def run_performance_benchmark(self) -> Dict[str, float]:
        """Run performance benchmarks"""
        benchmarks = {}
        
        # Benchmark database operations
        print("Running database benchmark...")
        start = time.time()
        
        # Simple PostgreSQL benchmark
        subprocess.run([
            'docker', 'exec', f'netra-{self.env}-postgres',
            'psql', '-U', 'test', '-d', 'netra_test', '-c',
            'CREATE TABLE IF NOT EXISTS bench_test (id SERIAL, data TEXT); '
            'INSERT INTO bench_test (data) SELECT md5(random()::text) FROM generate_series(1, 1000); '
            'SELECT COUNT(*) FROM bench_test; '
            'DROP TABLE bench_test;'
        ], capture_output=True)
        
        benchmarks['postgres_ops'] = time.time() - start
        
        # Benchmark Redis operations
        print("Running Redis benchmark...")
        start = time.time()
        
        subprocess.run([
            'docker', 'exec', f'netra-{self.env}-redis',
            'redis-cli', 'eval',
            'for i=1,1000 do redis.call("SET", "bench:"..i, "data") end; '
            'for i=1,1000 do redis.call("GET", "bench:"..i) end; '
            'for i=1,1000 do redis.call("DEL", "bench:"..i) end',
            '0'
        ], capture_output=True)
        
        benchmarks['redis_ops'] = time.time() - start
        
        return benchmarks
    
    def stop_services(self) -> None:
        """Stop Docker services"""
        print("Stopping services...")
        self.run_docker_command('down', '-v')
    
    def generate_report(self) -> str:
        """Generate verification report"""
        report = []
        report.append(f"Alpine Container Verification Report")
        report.append(f"Environment: {self.env}")
        report.append(f"Timestamp: {datetime.now().isoformat()}")
        report.append("=" * 60)
        
        # Image sizes
        if self.results['image_sizes']:
            report.append("\nImage Sizes:")
            for service, size in self.results['image_sizes'].items():
                status = "[U+2713]" if size < 200 else " WARNING: "
                report.append(f"  {status} {service}: {size:.1f}MB")
        
        # Startup times
        if self.results['startup_times']:
            report.append("\nStartup Times:")
            for service, time_sec in self.results['startup_times'].items():
                if time_sec > 0:
                    status = "[U+2713]" if time_sec < 30 else " WARNING: "
                    report.append(f"  {status} {service}: {time_sec:.1f}s")
                else:
                    report.append(f"  [U+2717] {service}: Failed to start")
        
        # Memory usage
        if self.results['memory_usage']:
            report.append("\nMemory Usage:")
            for service, mem_mb in self.results['memory_usage'].items():
                max_mb = MAX_MEMORY_MB.get(service, 1024)
                status = "[U+2713]" if mem_mb < max_mb else " WARNING: "
                report.append(f"  {status} {service}: {mem_mb:.1f}MB / {max_mb}MB")
        
        # Health checks
        if self.results['health_checks']:
            report.append("\nHealth Checks:")
            for service, configured in self.results['health_checks'].items():
                status = "[U+2713]" if configured else "[U+2717]"
                report.append(f"  {status} {service}: {'Configured' if configured else 'Missing'}")
        
        # Issues
        if self.results['issues']:
            report.append("\nIssues Found:")
            for issue in self.results['issues']:
                report.append(f"   WARNING:  {issue}")
        else:
            report.append("\n[U+2713] No issues found")
        
        report.append("\n" + "=" * 60)
        
        # Overall status
        total_issues = len(self.results['issues'])
        if total_issues == 0:
            report.append("[U+2713] Alpine containers are properly optimized")
        else:
            report.append(f" WARNING:  Found {total_issues} optimization opportunities")
        
        return "\n".join(report)
    
    def fix_issues(self) -> List[str]:
        """Attempt to fix common issues"""
        fixes = []
        
        for issue in self.results['issues']:
            if "missing health check" in issue:
                # Health checks should be in docker-compose.unified.yml
                fixes.append(f"Health check configuration needed for: {issue}")
            
            elif "memory limit" in issue:
                # Memory limits should be in env files
                fixes.append(f"Memory limit adjustment needed for: {issue}")
            
            elif "image size" in issue:
                # Image optimization needed
                fixes.append(f"Dockerfile optimization needed for: {issue}")
        
        return fixes


def main():
    parser = argparse.ArgumentParser(
        description='Verify and optimize Alpine containers'
    )
    parser.add_argument(
        '--env',
        choices=['dev', 'test', 'alpine-test', 'ci'],
        default='alpine-test',
        help='Environment to verify'
    )
    parser.add_argument(
        '--build',
        action='store_true',
        help='Build images before verification'
    )
    parser.add_argument(
        '--benchmark',
        action='store_true',
        help='Run performance benchmarks'
    )
    parser.add_argument(
        '--fix',
        action='store_true',
        help='Attempt to fix found issues'
    )
    parser.add_argument(
        '--output',
        help='Output report file',
        default='alpine_verification_report.txt'
    )
    
    args = parser.parse_args()
    
    verifier = AlpineVerifier(env=args.env)
    
    print(f"Verifying Alpine containers for {args.env} environment...")
    print("-" * 60)
    
    # Check Dockerfiles
    print("\nChecking Alpine Dockerfiles...")
    dockerfile_issues = verifier.check_alpine_dockerfiles()
    verifier.results['issues'].extend(dockerfile_issues)
    
    # Build if requested
    if args.build:
        if not verifier.build_images():
            print("Build failed, exiting")
            return 1
    
    # Measure image sizes
    print("\nMeasuring image sizes...")
    verifier.results['image_sizes'] = verifier.measure_image_sizes()
    
    # Start services
    print("\nStarting services...")
    if not verifier.start_services():
        print("Failed to start services")
        return 1
    
    # Wait for services to stabilize
    print("Waiting for services to stabilize...")
    time.sleep(10)
    
    # Measure startup times
    print("\nMeasuring startup times...")
    services = ['postgres', 'redis', 'backend', 'auth']
    for service in services:
        startup_time = verifier.measure_startup_time(service)
        verifier.results['startup_times'][service] = startup_time
        if startup_time < 0:
            verifier.results['issues'].append(f"{service} failed to become healthy")
    
    # Measure memory usage
    print("\nMeasuring memory usage...")
    for service in services:
        mem_usage = verifier.measure_memory_usage(service)
        verifier.results['memory_usage'][service] = mem_usage
    
    # Verify health checks
    print("\nVerifying health checks...")
    verifier.results['health_checks'] = verifier.verify_health_checks()
    
    # Verify resource limits
    print("\nVerifying resource limits...")
    verifier.verify_resource_limits()
    
    # Run benchmarks if requested
    if args.benchmark:
        print("\nRunning performance benchmarks...")
        benchmarks = verifier.run_performance_benchmark()
        print(f"  PostgreSQL operations: {benchmarks.get('postgres_ops', 0):.2f}s")
        print(f"  Redis operations: {benchmarks.get('redis_ops', 0):.2f}s")
    
    # Stop services
    verifier.stop_services()
    
    # Generate report
    report = verifier.generate_report()
    print("\n" + report)
    
    # Save report
    with open(args.output, 'w') as f:
        f.write(report)
    print(f"\nReport saved to: {args.output}")
    
    # Fix issues if requested
    if args.fix and verifier.results['issues']:
        print("\nAttempting to fix issues...")
        fixes = verifier.fix_issues()
        for fix in fixes:
            print(f"  - {fix}")
    
    # Return exit code based on issues
    return 0 if len(verifier.results['issues']) == 0 else 1


if __name__ == '__main__':
    sys.exit(main())