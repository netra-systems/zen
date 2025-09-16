#!/usr/bin/env python3
"""
VPC Dependencies Validation Script

Prevents VPC egress regressions like the Sept 15, 2025 incident where
changing to "all-traffic" broke Cloud SQL Unix socket connections.

This script validates that BOTH Cloud SQL and external service access work
with the current VPC egress configuration before deployment.

Related Learning Documents:
- SPEC/learnings/vpc_egress_cloud_sql_regression_critical.xml
- SPEC/learnings/vpc_clickhouse_proxy_solutions.xml
- docs/infrastructure/vpc-egress-regression-timeline.md
"""

import asyncio
import subprocess
import sys
import time
import logging
from typing import Dict, List, Tuple, Optional
import asyncpg
import aiohttp
import json
from urllib.parse import urlparse

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class VPCDependencyValidator:
    """
    Validates that VPC egress configuration allows access to all required services.
    
    CRITICAL: This validator prevents regressions like commit 2acf46c8a where
    VPC egress changes broke Cloud SQL connectivity.
    """
    
    def __init__(self, project_id: str = "netra-staging"):
        self.project_id = project_id
        self.validation_results: Dict[str, Dict] = {}
        
    async def validate_all_dependencies(self) -> bool:
        """
        Validate all critical VPC dependencies.
        
        Returns:
            bool: True if all dependencies accessible, False if any fail
        """
        logger.info("🔍 Starting comprehensive VPC dependency validation...")
        
        # Get current VPC egress setting
        vpc_egress = await self._get_current_vpc_egress()
        logger.info(f"📋 Current VPC egress setting: {vpc_egress}")
        
        # Validation tests
        tests = [
            ("cloud_sql", self._validate_cloud_sql_connection),
            ("clickhouse", self._validate_clickhouse_connection),
            ("redis", self._validate_redis_connection),
            ("external_apis", self._validate_external_apis),
        ]
        
        all_passed = True
        for test_name, test_func in tests:
            logger.info(f"🧪 Running {test_name} validation...")
            try:
                result = await test_func()
                self.validation_results[test_name] = result
                if result['status'] == 'success':
                    logger.info(f"✅ {test_name}: {result['message']}")
                else:
                    logger.error(f"❌ {test_name}: {result['message']}")
                    all_passed = False
            except Exception as e:
                logger.error(f"💥 {test_name} validation failed with exception: {e}")
                self.validation_results[test_name] = {
                    'status': 'error',
                    'message': f"Exception: {e}",
                    'duration_ms': 0
                }
                all_passed = False
        
        # Generate summary report
        self._generate_validation_report(vpc_egress, all_passed)
        
        return all_passed
    
    async def _get_current_vpc_egress(self) -> str:
        """Get current VPC egress setting from deployed service."""
        try:
            cmd = [
                "gcloud", "run", "services", "describe", "netra-auth-service",
                "--region=us-central1", f"--project={self.project_id}",
                "--format=value(spec.template.metadata.annotations['run.googleapis.com/vpc-access-egress'])"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.stdout.strip() or "not-set"
        except subprocess.CalledProcessError:
            return "unknown"
    
    async def _validate_cloud_sql_connection(self) -> Dict:
        """
        Validate Cloud SQL connection works (critical for Unix socket access).
        
        REGRESSION CONTEXT: VPC egress "all-traffic" blocks Cloud SQL Unix socket proxy.
        This test ensures Cloud SQL proxy is accessible.
        """
        start_time = time.time()
        
        try:
            # Get Cloud SQL connection details from secrets
            secrets = await self._get_postgres_secrets()
            
            if not secrets or not secrets.get('host'):
                return {
                    'status': 'error',
                    'message': 'Could not retrieve Cloud SQL secrets',
                    'duration_ms': int((time.time() - start_time) * 1000)
                }
            
            # Test Unix socket connection (the critical path that breaks with all-traffic)
            if '/cloudsql/' in secrets['host']:
                connection_url = f"postgresql://{secrets['user']}:{secrets['password']}@/{secrets['database']}?host={secrets['host']}"
                
                # Test connection with timeout (should be <1 second for healthy system)
                conn = await asyncio.wait_for(
                    asyncpg.connect(connection_url),
                    timeout=5.0  # If this times out, VPC egress is likely blocking
                )
                
                # Simple query to verify functionality
                result = await conn.fetchval("SELECT 1")
                await conn.close()
                
                duration_ms = int((time.time() - start_time) * 1000)
                
                if duration_ms > 3000:  # Slow connection indicates VPC routing issues
                    return {
                        'status': 'warning',
                        'message': f'Cloud SQL connection slow ({duration_ms}ms) - may indicate VPC routing issues',
                        'duration_ms': duration_ms
                    }
                
                return {
                    'status': 'success',
                    'message': f'Cloud SQL Unix socket connection healthy ({duration_ms}ms)',
                    'duration_ms': duration_ms
                }
            else:
                return {
                    'status': 'info',
                    'message': 'Cloud SQL using TCP connection (not Unix socket)',
                    'duration_ms': int((time.time() - start_time) * 1000)
                }
                
        except asyncio.TimeoutError:
            duration_ms = int((time.time() - start_time) * 1000)
            return {
                'status': 'error',
                'message': f'Cloud SQL connection timeout ({duration_ms}ms) - VPC egress likely blocking Unix socket access',
                'duration_ms': duration_ms
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Cloud SQL connection failed: {e}',
                'duration_ms': int((time.time() - start_time) * 1000)
            }
    
    async def _validate_clickhouse_connection(self) -> Dict:
        """
        Validate ClickHouse Cloud connection works.
        
        CONTEXT: This external service requires internet access and was the original
        reason for changing VPC egress to "all-traffic".
        """
        start_time = time.time()
        
        try:
            # Get ClickHouse connection details
            clickhouse_url = await self._get_secret("clickhouse-password-staging")
            if not clickhouse_url:
                return {
                    'status': 'error',
                    'message': 'Could not retrieve ClickHouse password',
                    'duration_ms': int((time.time() - start_time) * 1000)
                }
            
            # Test HTTP connection to ClickHouse Cloud
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                test_url = "https://xedvrr4c3r.us-central1.gcp.clickhouse.cloud:8443/ping"
                async with session.get(test_url) as response:
                    duration_ms = int((time.time() - start_time) * 1000)
                    
                    if response.status == 200:
                        return {
                            'status': 'success',
                            'message': f'ClickHouse Cloud accessible ({duration_ms}ms)',
                            'duration_ms': duration_ms
                        }
                    else:
                        return {
                            'status': 'error',
                            'message': f'ClickHouse returned status {response.status}',
                            'duration_ms': duration_ms
                        }
                        
        except asyncio.TimeoutError:
            return {
                'status': 'error',
                'message': 'ClickHouse connection timeout - external access blocked',
                'duration_ms': int((time.time() - start_time) * 1000)
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'ClickHouse connection failed: {e}',
                'duration_ms': int((time.time() - start_time) * 1000)
            }
    
    async def _validate_redis_connection(self) -> Dict:
        """Validate Redis connection works through VPC."""
        start_time = time.time()
        
        try:
            # Redis should work with both private-ranges-only and all-traffic
            # since it's within GCP private network
            return {
                'status': 'info',
                'message': 'Redis validation not implemented (internal service)',
                'duration_ms': int((time.time() - start_time) * 1000)
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Redis validation error: {e}',
                'duration_ms': int((time.time() - start_time) * 1000)
            }
    
    async def _validate_external_apis(self) -> Dict:
        """
        Validate external API access (OpenAI, Anthropic, Gemini, etc.).
        
        CRITICAL PATTERN: All external internet services require Cloud NAT with
        private-ranges-only VPC egress. This test validates the universal pattern
        discovered in the Sept 15, 2025 VPC egress regression.
        """
        start_time = time.time()
        
        try:
            # Test external service connectivity (all require Cloud NAT)
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                test_urls = [
                    "https://api.openai.com/v1/models",  # OpenAI LLM API
                    "https://api.anthropic.com/v1/messages",  # Anthropic LLM API
                    "https://generativelanguage.googleapis.com/v1/models",  # Google Gemini API
                    "https://xedvrr4c3r.us-central1.gcp.clickhouse.cloud:8443/ping",  # ClickHouse Analytics
                    "https://httpbin.org/get",  # Generic external connectivity test
                ]
                
                accessible_count = 0
                for url in test_urls:
                    try:
                        async with session.get(url) as response:
                            # We expect 401/403 (auth errors) which means connectivity works
                            if response.status in [200, 401, 403]:
                                accessible_count += 1
                    except:
                        pass  # Connection failed
                
                duration_ms = int((time.time() - start_time) * 1000)
                
                if accessible_count == len(test_urls):
                    return {
                        'status': 'success',
                        'message': f'External APIs accessible ({accessible_count}/{len(test_urls)})',
                        'duration_ms': duration_ms
                    }
                elif accessible_count > 0:
                    return {
                        'status': 'warning',
                        'message': f'Some external APIs accessible ({accessible_count}/{len(test_urls)})',
                        'duration_ms': duration_ms
                    }
                else:
                    return {
                        'status': 'error',
                        'message': 'No external APIs accessible - internet access blocked',
                        'duration_ms': duration_ms
                    }
                    
        except Exception as e:
            return {
                'status': 'error',
                'message': f'External API validation failed: {e}',
                'duration_ms': int((time.time() - start_time) * 1000)
            }
    
    async def _get_postgres_secrets(self) -> Optional[Dict[str, str]]:
        """Get PostgreSQL connection secrets from GCP Secret Manager."""
        try:
            secrets = {}
            secret_names = {
                'host': 'postgres-host-staging',
                'user': 'postgres-user-staging', 
                'password': 'postgres-password-staging',
                'database': 'postgres-db-staging',
                'port': 'postgres-port-staging'
            }
            
            for key, secret_name in secret_names.items():
                secret_value = await self._get_secret(secret_name)
                if secret_value:
                    secrets[key] = secret_value
            
            return secrets if len(secrets) == len(secret_names) else None
            
        except Exception as e:
            logger.error(f"Failed to get PostgreSQL secrets: {e}")
            return None
    
    async def _get_secret(self, secret_name: str) -> Optional[str]:
        """Get secret value from GCP Secret Manager."""
        try:
            cmd = [
                "gcloud", "secrets", "versions", "access", "latest",
                "--secret", secret_name, f"--project={self.project_id}"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None
    
    def _generate_validation_report(self, vpc_egress: str, all_passed: bool):
        """Generate comprehensive validation report."""
        print("\n" + "="*80)
        print("🔍 VPC DEPENDENCY VALIDATION REPORT")
        print("="*80)
        
        print(f"📋 VPC Egress Setting: {vpc_egress}")
        print(f"🎯 Overall Status: {'✅ PASS' if all_passed else '❌ FAIL'}")
        print(f"📅 Validation Time: {time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        print("\n📊 Individual Test Results:")
        print("-" * 50)
        
        for test_name, result in self.validation_results.items():
            status_icon = {
                'success': '✅',
                'warning': '⚠️',
                'error': '❌',
                'info': '🔵'
            }.get(result['status'], '❓')
            
            print(f"{status_icon} {test_name.upper()}: {result['message']}")
            print(f"   Duration: {result['duration_ms']}ms")
        
        print("\n🎯 CRITICAL ANALYSIS:")
        print("-" * 50)
        
        # Analyze potential VPC egress issues
        cloud_sql_result = self.validation_results.get('cloud_sql', {})
        clickhouse_result = self.validation_results.get('clickhouse', {})
        
        if cloud_sql_result.get('status') == 'error' and 'timeout' in cloud_sql_result.get('message', '').lower():
            print("🚨 CRITICAL: Cloud SQL timeout detected!")
            print("   This indicates VPC egress 'all-traffic' is blocking Unix socket access.")
            print("   SOLUTION: Change to 'private-ranges-only' + implement Cloud NAT for external access.")
            print("   See: SPEC/learnings/vpc_egress_cloud_sql_regression_critical.xml")
        
        external_apis_result = self.validation_results.get('external_apis', {})
        if external_apis_result.get('status') == 'error' and vpc_egress == 'private-ranges-only':
            print("⚠️  WARNING: External API access blocked with private-ranges-only")
            print("   AFFECTED SERVICES: OpenAI, Anthropic, Gemini, ClickHouse, external webhooks")
            print("   SOLUTION: Implement Cloud NAT for external service access.")
            print("   See: docs/infrastructure/vpc-egress-decision-matrix.md")
        
        if vpc_egress == 'all-traffic':
            print("⚠️  RISK: VPC egress 'all-traffic' may break Cloud SQL Unix sockets")
            print("   Monitor Cloud SQL connection times carefully.")
        
        print("\n📚 Related Documentation:")
        print("-" * 50)
        print("• SPEC/learnings/vpc_egress_cloud_sql_regression_critical.xml")
        print("• docs/infrastructure/vpc-egress-decision-matrix.md")
        print("• docs/infrastructure/clickhouse-network-path-analysis.md") 
        print("• SPEC/learnings/vpc_clickhouse_proxy_solutions.xml") 
        print("• docs/infrastructure/vpc-egress-regression-timeline.md")
        print("• scripts/deploy_to_gcp_actual.py:1088 (VPC egress configuration)")
        
        print("\n🔧 Recommended Actions:")
        print("-" * 50)
        if not all_passed:
            print("❌ VALIDATION FAILED - Do NOT deploy until issues resolved")
            if cloud_sql_result.get('status') == 'error':
                print("1. Fix Cloud SQL connectivity (likely VPC egress issue)")
            if clickhouse_result.get('status') == 'error':
                print("2. Implement Cloud NAT for external service access")
            print("3. Re-run validation after fixes")
        else:
            print("✅ ALL TESTS PASSED - Safe to deploy")
            print("1. Continue with deployment")
            print("2. Monitor connection times post-deployment")
        
        print("="*80)


async def main():
    """Main validation entry point."""
    if len(sys.argv) > 1:
        project_id = sys.argv[1]
    else:
        project_id = "netra-staging"
    
    print(f"🚀 Starting VPC dependency validation for project: {project_id}")
    print("📋 This prevents regressions like the Sept 15, 2025 Cloud SQL incident")
    
    validator = VPCDependencyValidator(project_id)
    success = await validator.validate_all_dependencies()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())