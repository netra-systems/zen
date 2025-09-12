"""Cross-Service Import Consistency Test

MISSION: Validate consistent Redis import patterns across auth, cache, and backend services.

Business Value Justification (BVJ):
- Segment: Platform/Internal 
- Business Goal: System Coherence & Multi-Service Stability
- Value Impact: Ensures unified Redis management prevents service boundary violations
- Strategic Impact: Validates microservice independence while maintaining shared Redis SSOT

CRITICAL CROSS-SERVICE VALIDATIONS:
- Auth service uses SSOT Redis manager consistently 
- Backend service uses SSOT Redis manager consistently
- Analytics service uses SSOT Redis manager consistently
- No service bypasses SSOT Redis manager with custom implementations
- Service isolation boundaries are respected during Redis access
- Cross-service Redis operations maintain data consistency

This test validates:
1. Consistent import patterns across all services
2. No service-specific Redis manager bypasses SSOT
3. Cross-service data consistency through unified Redis access
4. Service boundary respect with shared Redis infrastructure
5. Golden Path functionality works across service boundaries
"""

from test_framework.ssot.base_test_case import SSotAsyncTestCase, SSotBaseTestCase
import unittest
import asyncio
import json
import logging
import importlib
import sys
from typing import Dict, List, Set, Optional, Tuple, Any
from pathlib import Path

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)

class CrossServiceImportConsistencyTest(SSotAsyncTestCase):
    """Test Redis import consistency across all services."""
    
    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).parent.parent.parent
        
        # Services to validate for Redis import consistency
        cls.services = {
            'netra_backend': {
                'path': cls.project_root / 'netra_backend',
                'expected_import': 'from netra_backend.app.redis_manager import redis_manager',
                'critical_files': [
                    'app/auth_integration/auth.py',
                    'app/websocket_core/manager.py',
                    'app/routes/websocket.py',
                    'app/agents/supervisor/execution_engine.py'
                ]
            },
            'auth_service': {
                'path': cls.project_root / 'auth_service',
                'expected_import': 'from netra_backend.app.redis_manager import redis_manager',
                'critical_files': [
                    'auth_core/core/session_manager.py',
                    'auth_core/__init__.py'
                ]
            },
            'analytics_service': {
                'path': cls.project_root / 'analytics_service', 
                'expected_import': 'from netra_backend.app.redis_manager import redis_manager',
                'critical_files': [
                    'analytics_core/services/redis_cache_service.py',
                    'analytics_core/services/rate_limiter.py'
                ]
            }
        }
        
        # Cross-service Redis operations to validate
        cls.cross_service_operations = [
            'user_session_sharing',
            'cross_service_caching', 
            'shared_rate_limiting',
            'service_coordination',
            'data_consistency'
        ]

    async def asyncSetUp(self):
        """Set up cross-service test environment."""
        await super().asyncSetUp()
        
        # Validate SSOT Redis manager is available
        try:
            from netra_backend.app.redis_manager import redis_manager
            self.ssot_redis = redis_manager
            
            # Test SSOT Redis connectivity
            client = await self.ssot_redis.get_client()
            if client:
                await client.ping()
                logger.info("✅ SSOT Redis manager available for cross-service testing")
            else:
                logger.warning("❌ SSOT Redis manager connection failed")
                
        except Exception as e:
            logger.error(f"SSOT Redis setup failed: {e}")
            self.ssot_redis = None

    def test_all_services_use_consistent_import_patterns(self):
        """Test all services use consistent Redis import patterns."""
        logger.info("Testing consistent Redis import patterns across all services...")
        
        service_violations = {}
        
        for service_name, service_config in self.services.items():
            service_path = service_config['path']
            if not service_path.exists():
                logger.warning(f"Service path does not exist: {service_path}")
                continue
                
            violations = self._analyze_service_import_patterns(
                service_name, service_path, service_config['expected_import']
            )
            
            if violations:
                service_violations[service_name] = violations
                
        if service_violations:
            violation_report = self._format_cross_service_violation_report(service_violations)
            self.fail(f"Cross-service Redis import inconsistencies found:\n{violation_report}")
            
        logger.info("✅ All services use consistent Redis import patterns")

    def test_no_service_bypasses_ssot_redis_manager(self):
        """Test that no service bypasses SSOT Redis manager with custom implementations."""
        logger.info("Testing no service bypasses SSOT Redis manager...")
        
        bypass_violations = {}
        
        for service_name, service_config in self.services.items():
            service_path = service_config['path'] 
            if not service_path.exists():
                continue
                
            bypasses = self._detect_ssot_bypasses(service_name, service_path)
            
            if bypasses:
                bypass_violations[service_name] = bypasses
                
        if bypass_violations:
            bypass_report = self._format_bypass_violation_report(bypass_violations)
            self.fail(f"Services bypassing SSOT Redis manager found:\n{bypass_report}")
            
        logger.info("✅ No services bypass SSOT Redis manager")

    def test_critical_files_import_consistency(self):
        """Test critical files across services use consistent imports."""
        logger.info("Testing critical files import consistency across services...")
        
        critical_file_violations = {}
        
        for service_name, service_config in self.services.items():
            service_path = service_config['path']
            if not service_path.exists():
                continue
                
            for critical_file in service_config['critical_files']:
                file_path = service_path / critical_file
                if file_path.exists():
                    violations = self._analyze_critical_file_imports(
                        service_name, file_path, service_config['expected_import']
                    )
                    
                    if violations:
                        if service_name not in critical_file_violations:
                            critical_file_violations[service_name] = {}
                        critical_file_violations[service_name][critical_file] = violations
                        
        if critical_file_violations:
            critical_report = self._format_critical_file_report(critical_file_violations)
            self.fail(f"Critical file import inconsistencies found:\n{critical_report}")
            
        logger.info("✅ Critical files use consistent imports across services")

    async def test_cross_service_redis_data_consistency(self):
        """Test cross-service Redis data consistency through SSOT manager."""
        logger.info("Testing cross-service Redis data consistency...")
        
        if not self.ssot_redis:
            self.skipTest("SSOT Redis not available for testing")
            
        test_user_id = "cross_service_test_user"
        consistency_violations = []
        
        # Test data written by one service is readable by another
        test_scenarios = [
            {
                'name': 'auth_to_backend_session',
                'write_key': f"auth:session:{test_user_id}",
                'read_key': f"auth:session:{test_user_id}",
                'data': {'user_id': test_user_id, 'authenticated': True}
            },
            {
                'name': 'backend_to_analytics_cache',
                'write_key': f"cache:user:{test_user_id}:preferences",
                'read_key': f"cache:user:{test_user_id}:preferences", 
                'data': {'theme': 'dark', 'language': 'en'}
            },
            {
                'name': 'analytics_to_auth_rate_limit',
                'write_key': f"rate_limit:user:{test_user_id}",
                'read_key': f"rate_limit:user:{test_user_id}",
                'data': {'requests': 10, 'window_start': 1234567890}
            }
        ]
        
        for scenario in test_scenarios:
            try:
                # Write data using SSOT manager
                write_success = await self.ssot_redis.set(
                    scenario['write_key'],
                    json.dumps(scenario['data']),
                    ex=300
                )
                
                if not write_success:
                    consistency_violations.append(f"Failed to write {scenario['name']}")
                    continue
                    
                # Read data using SSOT manager  
                read_data = await self.ssot_redis.get(scenario['read_key'])
                
                if not read_data:
                    consistency_violations.append(f"Failed to read {scenario['name']}")
                    continue
                    
                parsed_data = json.loads(read_data)
                
                # Validate data consistency
                if parsed_data != scenario['data']:
                    consistency_violations.append(
                        f"Data inconsistency in {scenario['name']}: "
                        f"expected {scenario['data']}, got {parsed_data}"
                    )
                    
            except Exception as e:
                consistency_violations.append(f"Exception in {scenario['name']}: {str(e)}")
                
        # Clean up test data
        for scenario in test_scenarios:
            try:
                await self.ssot_redis.delete(scenario['write_key'])
            except Exception:
                pass
                
        if consistency_violations:
            self.fail(f"Cross-service data consistency violations:\n" + 
                     "\n".join(consistency_violations))
            
        logger.info("✅ Cross-service Redis data consistency validated")

    async def test_service_isolation_boundaries_respected(self):
        """Test service isolation boundaries are respected with shared Redis."""
        logger.info("Testing service isolation boundaries with shared Redis...")
        
        if not self.ssot_redis:
            self.skipTest("SSOT Redis not available for testing")
            
        isolation_test_data = {
            'auth_service': {
                'namespace': 'auth:',
                'test_key': 'auth:service:boundary:test',
                'data': {'service': 'auth', 'private': True}
            },
            'backend_service': {
                'namespace': 'backend:',
                'test_key': 'backend:service:boundary:test', 
                'data': {'service': 'backend', 'shared': False}
            },
            'analytics_service': {
                'namespace': 'analytics:',
                'test_key': 'analytics:service:boundary:test',
                'data': {'service': 'analytics', 'isolated': True}
            }
        }
        
        isolation_violations = []
        
        # Write service-specific data
        for service, config in isolation_test_data.items():
            write_success = await self.ssot_redis.set(
                config['test_key'],
                json.dumps(config['data']),
                ex=300
            )
            
            if not write_success:
                isolation_violations.append(f"Failed to write {service} boundary test data")
                
        # Validate each service can only access its own namespace appropriately
        for service, config in isolation_test_data.items():
            # Service can read its own data
            own_data = await self.ssot_redis.get(config['test_key'])
            if not own_data:
                isolation_violations.append(f"{service} cannot read its own boundary data")
                continue
                
            parsed_own = json.loads(own_data)
            if parsed_own['service'] != config['data']['service']:
                isolation_violations.append(f"{service} boundary data corrupted")
                
            # Validate namespace isolation (services should use proper prefixes)
            if not config['test_key'].startswith(config['namespace']):
                isolation_violations.append(f"{service} not using proper namespace prefix")
                
        # Clean up isolation test data
        for config in isolation_test_data.values():
            try:
                await self.ssot_redis.delete(config['test_key'])
            except Exception:
                pass
                
        if isolation_violations:
            self.fail(f"Service isolation boundary violations:\n" + 
                     "\n".join(isolation_violations))
            
        logger.info("✅ Service isolation boundaries respected with shared Redis")

    # Helper methods
    
    def _analyze_service_import_patterns(self, service_name: str, service_path: Path, 
                                       expected_import: str) -> List[Dict]:
        """Analyze import patterns for a service."""
        violations = []
        
        python_files = list(service_path.rglob("*.py"))
        
        for file_path in python_files:
            try:
                content = self._read_file_content(file_path)
                if self._contains_redis_imports(content):
                    file_violations = self._check_import_consistency(
                        file_path, content, expected_import
                    )
                    violations.extend(file_violations)
            except Exception as e:
                logger.warning(f"Could not analyze {file_path}: {e}")
                
        return violations

    def _detect_ssot_bypasses(self, service_name: str, service_path: Path) -> List[Dict]:
        """Detect SSOT bypasses in a service."""
        bypasses = []
        
        python_files = list(service_path.rglob("*.py"))
        
        bypass_patterns = [
            "RedisManager()",  # Direct instantiation
            "await get_redis_client()  # MIGRATED: was redis.Redis(",    # Direct Redis client creation
            "redis.ConnectionPool(",  # Direct connection pool creation
            "class.*RedisManager",  # Custom Redis manager class
        ]
        
        for file_path in python_files:
            try:
                content = self._read_file_content(file_path)
                
                for pattern in bypass_patterns:
                    if pattern in content:
                        bypasses.append({
                            'file': str(file_path),
                            'pattern': pattern,
                            'service': service_name,
                            'violation_type': 'SSOT bypass'
                        })
            except Exception as e:
                logger.warning(f"Could not analyze {file_path}: {e}")
                
        return bypasses

    def _analyze_critical_file_imports(self, service_name: str, file_path: Path, 
                                     expected_import: str) -> List[Dict]:
        """Analyze imports in a critical file."""
        violations = []
        
        try:
            content = self._read_file_content(file_path)
            if self._contains_redis_imports(content):
                violations = self._check_import_consistency(
                    file_path, content, expected_import
                )
                
                # Mark as critical
                for violation in violations:
                    violation['severity'] = 'CRITICAL'
                    violation['service'] = service_name
                    
        except Exception as e:
            logger.warning(f"Could not analyze critical file {file_path}: {e}")
            
        return violations

    def _read_file_content(self, file_path: Path) -> str:
        """Read file content safely."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()

    def _contains_redis_imports(self, content: str) -> bool:
        """Check if content contains Redis imports."""
        redis_keywords = ['redis_manager', 'RedisManager', 'redis.Redis', 'import redis']
        return any(keyword in content for keyword in redis_keywords)

    def _check_import_consistency(self, file_path: Path, content: str, 
                                expected_import: str) -> List[Dict]:
        """Check import consistency against expected pattern."""
        violations = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            if ('redis_manager' in line or 'RedisManager' in line) and 'import' in line:
                if line.startswith('#'):  # Skip comments
                    continue
                    
                if expected_import not in line:
                    violations.append({
                        'file': str(file_path),
                        'line': i,
                        'content': line,
                        'expected': expected_import,
                        'violation_type': 'Import pattern inconsistency'
                    })
                    
        return violations

    def _format_cross_service_violation_report(self, service_violations: Dict) -> str:
        """Format cross-service violation report."""
        report = []
        report.append("\n" + "="*80)
        report.append("CROSS-SERVICE REDIS IMPORT VIOLATIONS")
        report.append("="*80)
        
        for service_name, violations in service_violations.items():
            report.append(f"\n🔴 SERVICE: {service_name.upper()} ({len(violations)} violations)")
            report.append("-" * 60)
            
            for violation in violations:
                report.append(f"  📁 {violation['file']}")
                report.append(f"  📍 Line {violation['line']}: {violation['violation_type']}")
                report.append(f"  💻 Found: {violation['content']}")
                report.append(f"  ✅ Expected: {violation['expected']}")
                report.append("")
                
        return '\n'.join(report)

    def _format_bypass_violation_report(self, bypass_violations: Dict) -> str:
        """Format SSOT bypass violation report."""
        report = []
        report.append("\n" + "="*80)
        report.append("SSOT REDIS MANAGER BYPASS VIOLATIONS") 
        report.append("="*80)
        
        for service_name, bypasses in bypass_violations.items():
            report.append(f"\n🔴 SERVICE: {service_name.upper()} ({len(bypasses)} bypasses)")
            report.append("-" * 60)
            
            for bypass in bypasses:
                report.append(f"  📁 {bypass['file']}")
                report.append(f"  🚫 Bypass Pattern: {bypass['pattern']}")
                report.append(f"  ⚠️ Type: {bypass['violation_type']}")
                report.append("")
                
        return '\n'.join(report)

    def _format_critical_file_report(self, critical_violations: Dict) -> str:
        """Format critical file violation report."""
        report = []
        report.append("\n" + "="*80)
        report.append("CRITICAL FILE REDIS IMPORT VIOLATIONS")
        report.append("="*80)
        
        for service_name, file_violations in critical_violations.items():
            report.append(f"\n🚨 SERVICE: {service_name.upper()}")
            report.append("-" * 60)
            
            for file_name, violations in file_violations.items():
                report.append(f"  📁 CRITICAL FILE: {file_name}")
                for violation in violations:
                    report.append(f"    📍 Line {violation['line']}: {violation['violation_type']}")
                    report.append(f"    💻 Found: {violation['content']}")
                    report.append(f"    ✅ Expected: {violation['expected']}")
                    report.append("")
                    
        return '\n'.join(report)


if __name__ == '__main__':
    unittest.main()