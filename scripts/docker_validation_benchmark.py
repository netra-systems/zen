#!/usr/bin/env python3
"""
Docker Infrastructure Validation and Benchmark Script

Validates the unified Docker configuration and runs performance benchmarks
to ensure all requirements are met:
- Services start in < 30 seconds
- No port conflicts in parallel runs  
- Memory usage < 2GB per test suite
- Cleanup completes in < 5 seconds

Usage:
    python scripts/docker_validation_benchmark.py [options]
    
Options:
    --env ENV           Environment to test (dev, test, alpine-test, ci)
    --parallel N        Run N parallel instances
    --quick             Quick validation only
    --full              Full benchmark suite
"""

import argparse
import subprocess
import sys
import time
import json
import os
import threading
import statistics
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import concurrent.futures

# Validation criteria
MAX_STARTUP_TIME = 30  # seconds
MAX_MEMORY_PER_SUITE = 2048  # MB
MAX_CLEANUP_TIME = 5  # seconds
PARALLEL_TEST_COUNT = 3


class DockerValidator:
    """Validates Docker infrastructure configuration"""
    
    def __init__(self, env: str = 'test'):
        self.env = env
        self.compose_file = 'docker-compose.unified.yml'
        self.env_file = self._get_env_file(env)
        self.results = {
            'startup_times': [],
            'memory_usage': [],
            'port_conflicts': [],
            'cleanup_times': [],
            'parallel_tests': [],
            'benchmarks': {},
            'validations': {}
        }
    
    def _get_env_file(self, env: str) -> str:
        """Get environment file for the specified environment"""
        env_map = {
            'dev': '.env.local',
            'test': '.env.test',
            'alpine-test': '.env.alpine-test',
            'ci': '.env.ci'
        }
        return env_map.get(env, '.env.test')
    
    def run_command(self, cmd: List[str], timeout: int = 60) -> Tuple[int, str, str]:
        """Run a command with timeout"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", f"Command timed out after {timeout} seconds"
    
    def docker_compose_cmd(self, *args) -> List[str]:
        """Build docker-compose command"""
        cmd = ['docker-compose', '-f', self.compose_file]
        
        if self.env_file and Path(self.env_file).exists():
            cmd.extend(['--env-file', self.env_file])
        
        if self.env in ['test', 'alpine-test', 'ci']:
            cmd.extend(['--profile', self.env])
        
        cmd.extend(args)
        return cmd
    
    def validate_startup_time(self) -> Dict[str, float]:
        """Validate that all services start within time limit"""
        print(f"\n[Validation] Testing startup time for {self.env}...")
        
        # Clean start
        self.run_command(self.docker_compose_cmd('down', '-v'), timeout=30)
        
        # Start timer
        start_time = time.time()
        
        # Start services
        returncode, stdout, stderr = self.run_command(
            self.docker_compose_cmd('up', '-d'),
            timeout=60
        )
        
        if returncode != 0:
            print(f"  [U+2717] Failed to start services: {stderr}")
            return {}
        
        # Wait for all services to be healthy
        services = self._get_service_names()
        startup_times = {}
        
        for service in services:
            service_start = time.time()
            healthy = False
            
            while time.time() - service_start < MAX_STARTUP_TIME:
                container = f"netra-{self.env}-{service}"
                returncode, stdout, _ = self.run_command(
                    ['docker', 'inspect', container, '--format', '{{.State.Health.Status}}'],
                    timeout=5
                )
                
                if returncode == 0 and 'healthy' in stdout:
                    healthy = True
                    break
                
                time.sleep(1)
            
            service_time = time.time() - service_start
            startup_times[service] = service_time
            
            if healthy:
                status = "[U+2713]" if service_time < MAX_STARTUP_TIME else " WARNING: "
                print(f"  {status} {service}: {service_time:.1f}s")
            else:
                print(f"  [U+2717] {service}: Failed to become healthy")
        
        total_time = time.time() - start_time
        self.results['startup_times'].append(total_time)
        
        status = "[U+2713]" if total_time < MAX_STARTUP_TIME else "[U+2717]"
        print(f"  {status} Total startup time: {total_time:.1f}s (limit: {MAX_STARTUP_TIME}s)")
        
        return startup_times
    
    def validate_memory_usage(self) -> Dict[str, float]:
        """Validate memory usage is within limits"""
        print(f"\n[Validation] Testing memory usage...")
        
        memory_usage = {}
        total_memory = 0
        
        services = self._get_service_names()
        
        for service in services:
            container = f"netra-{self.env}-{service}"
            returncode, stdout, _ = self.run_command(
                ['docker', 'stats', container, '--no-stream', '--format', '{{.MemUsage}}'],
                timeout=5
            )
            
            if returncode == 0:
                # Parse memory (e.g., "123.4MiB / 512MiB")
                mem_str = stdout.strip().split('/')[0].strip()
                
                if 'MiB' in mem_str:
                    mem_mb = float(mem_str.replace('MiB', ''))
                elif 'GiB' in mem_str:
                    mem_mb = float(mem_str.replace('GiB', '')) * 1024
                else:
                    mem_mb = 0
                
                memory_usage[service] = mem_mb
                total_memory += mem_mb
                
                print(f"  {service}: {mem_mb:.1f}MB")
        
        self.results['memory_usage'].append(total_memory)
        
        status = "[U+2713]" if total_memory < MAX_MEMORY_PER_SUITE else "[U+2717]"
        print(f"  {status} Total memory: {total_memory:.1f}MB (limit: {MAX_MEMORY_PER_SUITE}MB)")
        
        return memory_usage
    
    def validate_cleanup_time(self) -> float:
        """Validate cleanup completes quickly"""
        print(f"\n[Validation] Testing cleanup time...")
        
        start_time = time.time()
        
        returncode, stdout, stderr = self.run_command(
            self.docker_compose_cmd('down', '-v'),
            timeout=30
        )
        
        cleanup_time = time.time() - start_time
        self.results['cleanup_times'].append(cleanup_time)
        
        if returncode == 0:
            status = "[U+2713]" if cleanup_time < MAX_CLEANUP_TIME else " WARNING: "
            print(f"  {status} Cleanup time: {cleanup_time:.1f}s (limit: {MAX_CLEANUP_TIME}s)")
        else:
            print(f"  [U+2717] Cleanup failed: {stderr}")
        
        return cleanup_time
    
    def validate_parallel_execution(self, count: int = PARALLEL_TEST_COUNT) -> List[bool]:
        """Validate parallel execution without conflicts"""
        print(f"\n[Validation] Testing {count} parallel instances...")
        
        results = []
        threads = []
        
        def run_parallel_instance(instance_id: int):
            """Run a single parallel instance"""
            # Generate dynamic ports
            returncode, stdout, _ = self.run_command(
                ['python', 'scripts/allocate_test_ports.py', 
                 '--parallel-id', str(instance_id),
                 '--output', f'.env.parallel-{instance_id}'],
                timeout=10
            )
            
            if returncode != 0:
                results.append(False)
                print(f"  [U+2717] Instance {instance_id}: Port allocation failed")
                return
            
            # Start with dynamic ports
            env_file = f'.env.parallel-{instance_id}'
            cmd = ['docker-compose', '-f', self.compose_file,
                   '--env-file', env_file,
                   '-p', f'test-{instance_id}',
                   'up', '-d']
            
            returncode, _, stderr = self.run_command(cmd, timeout=60)
            
            if returncode == 0:
                results.append(True)
                print(f"  [U+2713] Instance {instance_id}: Started successfully")
                
                # Cleanup
                self.run_command(
                    ['docker-compose', '-f', self.compose_file,
                     '--env-file', env_file,
                     '-p', f'test-{instance_id}',
                     'down', '-v'],
                    timeout=30
                )
            else:
                results.append(False)
                print(f"  [U+2717] Instance {instance_id}: Failed - {stderr[:100]}")
            
            # Cleanup env file
            try:
                os.remove(env_file)
            except:
                pass
        
        # Start parallel instances
        with concurrent.futures.ThreadPoolExecutor(max_workers=count) as executor:
            futures = [executor.submit(run_parallel_instance, i) for i in range(count)]
            concurrent.futures.wait(futures)
        
        success_rate = sum(results) / len(results) * 100 if results else 0
        print(f"  Parallel success rate: {success_rate:.0f}%")
        
        return results
    
    def run_performance_benchmarks(self) -> Dict[str, float]:
        """Run performance benchmarks"""
        print(f"\n[Benchmark] Running performance tests...")
        
        benchmarks = {}
        
        # Database write benchmark
        print("  Testing database writes...")
        start = time.time()
        
        for i in range(100):
            self.run_command(
                ['docker', 'exec', f'netra-{self.env}-postgres',
                 'psql', '-U', 'test', '-d', 'netra_test', '-c',
                 f"INSERT INTO test_bench_{i} VALUES (1, 'data');"],
                timeout=1
            )
        
        benchmarks['db_writes_per_sec'] = 100 / (time.time() - start)
        
        # Redis operations benchmark
        print("  Testing Redis operations...")
        start = time.time()
        
        self.run_command(
            ['docker', 'exec', f'netra-{self.env}-redis',
             'redis-benchmark', '-t', 'set,get', '-n', '1000', '-q'],
            timeout=10
        )
        
        benchmarks['redis_ops_time'] = time.time() - start
        
        # API response time
        print("  Testing API response...")
        response_times = []
        
        for _ in range(10):
            start = time.time()
            self.run_command(
                ['curl', '-s', f'http://localhost:{self._get_port("backend")}/health'],
                timeout=5
            )
            response_times.append((time.time() - start) * 1000)
        
        benchmarks['api_response_ms'] = statistics.mean(response_times) if response_times else 0
        
        print(f"  Database writes: {benchmarks.get('db_writes_per_sec', 0):.1f}/sec")
        print(f"  Redis benchmark: {benchmarks.get('redis_ops_time', 0):.2f}s")
        print(f"  API response: {benchmarks.get('api_response_ms', 0):.1f}ms")
        
        return benchmarks
    
    def _get_service_names(self) -> List[str]:
        """Get list of service names for the environment"""
        base_services = ['postgres', 'redis', 'clickhouse', 'backend', 'auth']
        
        if self.env == 'dev':
            return base_services + ['frontend']
        else:
            return base_services
    
    def _get_port(self, service: str) -> int:
        """Get port for a service based on environment"""
        port_map = {
            'dev': {
                'postgres': 5433,
                'redis': 6380,
                'backend': 8000,
                'auth': 8081,
                'frontend': 3000
            },
            'test': {
                'postgres': 5434,
                'redis': 6381,
                'backend': 8001,
                'auth': 8082,
                'frontend': 3001
            },
            'alpine-test': {
                'postgres': 5435,
                'redis': 6382,
                'backend': 8002,
                'auth': 8083,
                'frontend': 3002
            },
            'ci': {
                'postgres': 5436,
                'redis': 6383,
                'backend': 8003,
                'auth': 8084,
                'frontend': 3003
            }
        }
        
        return port_map.get(self.env, {}).get(service, 8000)
    
    def generate_report(self) -> str:
        """Generate validation report"""
        report = []
        report.append("=" * 60)
        report.append("Docker Infrastructure Validation Report")
        report.append(f"Environment: {self.env}")
        report.append(f"Timestamp: {datetime.now().isoformat()}")
        report.append("=" * 60)
        
        # Validation results
        report.append("\nValidation Results:")
        report.append("-" * 40)
        
        # Startup time
        if self.results['startup_times']:
            avg_startup = statistics.mean(self.results['startup_times'])
            status = "PASS" if avg_startup < MAX_STARTUP_TIME else "FAIL"
            report.append(f"Startup Time: {status} ({avg_startup:.1f}s / {MAX_STARTUP_TIME}s)")
        
        # Memory usage
        if self.results['memory_usage']:
            avg_memory = statistics.mean(self.results['memory_usage'])
            status = "PASS" if avg_memory < MAX_MEMORY_PER_SUITE else "FAIL"
            report.append(f"Memory Usage: {status} ({avg_memory:.0f}MB / {MAX_MEMORY_PER_SUITE}MB)")
        
        # Cleanup time
        if self.results['cleanup_times']:
            avg_cleanup = statistics.mean(self.results['cleanup_times'])
            status = "PASS" if avg_cleanup < MAX_CLEANUP_TIME else "FAIL"
            report.append(f"Cleanup Time: {status} ({avg_cleanup:.1f}s / {MAX_CLEANUP_TIME}s)")
        
        # Parallel execution
        if self.results['parallel_tests']:
            success_rate = sum(self.results['parallel_tests']) / len(self.results['parallel_tests']) * 100
            status = "PASS" if success_rate == 100 else "WARN" if success_rate >= 50 else "FAIL"
            report.append(f"Parallel Execution: {status} ({success_rate:.0f}% success)")
        
        # Benchmark results
        if self.results['benchmarks']:
            report.append("\nPerformance Benchmarks:")
            report.append("-" * 40)
            
            for metric, value in self.results['benchmarks'].items():
                report.append(f"{metric}: {value:.2f}")
        
        # Overall status
        report.append("\n" + "=" * 60)
        
        all_passed = all([
            statistics.mean(self.results['startup_times']) < MAX_STARTUP_TIME 
                if self.results['startup_times'] else True,
            statistics.mean(self.results['memory_usage']) < MAX_MEMORY_PER_SUITE 
                if self.results['memory_usage'] else True,
            statistics.mean(self.results['cleanup_times']) < MAX_CLEANUP_TIME 
                if self.results['cleanup_times'] else True
        ])
        
        if all_passed:
            report.append("[U+2713] All validations PASSED")
        else:
            report.append("[U+2717] Some validations FAILED")
        
        report.append("=" * 60)
        
        return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(
        description='Validate and benchmark Docker infrastructure'
    )
    parser.add_argument(
        '--env',
        choices=['dev', 'test', 'alpine-test', 'ci'],
        default='test',
        help='Environment to validate'
    )
    parser.add_argument(
        '--parallel',
        type=int,
        default=0,
        help='Number of parallel instances to test'
    )
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Quick validation only'
    )
    parser.add_argument(
        '--full',
        action='store_true',
        help='Full benchmark suite'
    )
    parser.add_argument(
        '--output',
        help='Output report file',
        default='docker_validation_report.txt'
    )
    
    args = parser.parse_args()
    
    validator = DockerValidator(env=args.env)
    
    print(f"Docker Infrastructure Validation")
    print(f"Environment: {args.env}")
    print("=" * 60)
    
    try:
        # Run validations
        if not args.quick or args.full:
            validator.validate_startup_time()
            validator.validate_memory_usage()
        
        if args.full:
            validator.run_performance_benchmarks()
        
        if args.parallel > 0:
            validator.validate_parallel_execution(args.parallel)
        
        validator.validate_cleanup_time()
        
        # Generate and save report
        report = validator.generate_report()
        print("\n" + report)
        
        with open(args.output, 'w') as f:
            f.write(report)
        print(f"\nReport saved to: {args.output}")
        
        # Return exit code based on results
        all_passed = all([
            statistics.mean(validator.results['startup_times']) < MAX_STARTUP_TIME 
                if validator.results['startup_times'] else True,
            statistics.mean(validator.results['memory_usage']) < MAX_MEMORY_PER_SUITE 
                if validator.results['memory_usage'] else True,
            statistics.mean(validator.results['cleanup_times']) < MAX_CLEANUP_TIME 
                if validator.results['cleanup_times'] else True
        ])
        
        return 0 if all_passed else 1
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        validator.validate_cleanup_time()
        return 1
    except Exception as e:
        print(f"\nError: {e}")
        validator.validate_cleanup_time()
        return 1


if __name__ == '__main__':
    sys.exit(main())