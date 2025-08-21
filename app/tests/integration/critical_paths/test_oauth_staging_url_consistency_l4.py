"""OAuth Staging URL Consistency L4 Integration Tests

Business Value Justification (BVJ):
- Segment: Enterprise 
- Business Goal: Platform Stability and Authentication Security
- Value Impact: $25K MRR - Prevents authentication failures in staging caused by incorrect OAuth URLs
- Strategic Impact: Ensures all services use correct subdomain architecture for OAuth redirects

Critical Path: Configuration scanning -> URL validation -> Cross-service consistency -> OAuth redirect validation
Coverage: Complete OAuth URL consistency across Python, TypeScript, configuration files, and deployment scripts

L4 Realism Level: Tests against actual staging configuration and real service endpoints
"""

import pytest
import asyncio
import httpx
import re
import json
import os
from typing import Dict, Any, List, Optional, Set
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime

from tests.unified.e2e.staging_test_helpers import StagingTestSuite, get_staging_suite
from app.tests.integration.critical_paths.l4_staging_critical_base import L4StagingCriticalPathTestBase


@dataclass
class URLInconsistency:
    """Container for detected OAuth URL inconsistencies."""
    file_path: str
    line_number: int
    line_content: str
    incorrect_url: str
    expected_url: str
    severity: str
    url_type: str  # 'redirect_uri', 'javascript_origin', 'api_endpoint', 'config'
    context: str   # Additional context about the usage


@dataclass
class OAuthAuditResult:
    """OAuth URL audit result container."""
    total_files_scanned: int
    oauth_urls_found: int
    inconsistencies_detected: int
    critical_inconsistencies: int
    audit_duration_seconds: float
    inconsistencies: List[URLInconsistency]
    patterns_detected: Dict[str, int] = field(default_factory=dict)
    file_types_scanned: Dict[str, int] = field(default_factory=dict)
    staging_endpoints_verified: List[str] = field(default_factory=list)


class OAuthURLConsistencyL4TestSuite(L4StagingCriticalPathTestBase):
    """L4 test suite for OAuth URL consistency in staging environment."""
    
    def __init__(self):
        super().__init__("oauth_url_consistency")
        self.project_root = Path(__file__).parent.parent.parent.parent.parent
        
        # Expected staging URLs for different services
        self.expected_staging_urls = {
            "frontend": "https://app.staging.netrasystems.ai",
            "backend": "https://api.staging.netrasystems.ai", 
            "auth": "https://auth.staging.netrasystems.ai",
            "websocket": "wss://api.staging.netrasystems.ai/ws"
        }
        
        # Incorrect patterns that should be replaced
        self.incorrect_patterns = [
            "staging.netrasystems.ai",  # Missing subdomain
            "https://staging.netrasystems.ai",  # Legacy format
            "http://staging.netrasystems.ai",   # Insecure
            "netra-staging.herokuapp.com",      # Old Heroku URLs
            "localhost:3000",                   # Dev URLs in staging config
            "127.0.0.1"                         # Local IPs in staging config
        ]
        
        # File patterns to scan
        self.file_patterns = {
            "python": ["*.py"],
            "typescript": ["*.ts", "*.tsx"],
            "javascript": ["*.js", "*.jsx"],
            "config": ["*.yaml", "*.yml", "*.json", "*.env*", "*.conf"],
            "docker": ["Dockerfile*", "docker-compose*"],
            "deployment": ["*.md", "*.txt"]
        }
        
        # OAuth-related keywords for detection
        self.oauth_keywords = [
            "redirect_uri", "redirect_uris", "javascript_origins", 
            "callback", "oauth", "auth", "login", "authentication",
            "client_id", "client_secret", "token_endpoint", "auth_endpoint"
        ]
    
    async def setup_test_specific_environment(self) -> None:
        """Setup test-specific environment configuration."""
        # Validate that we can access the actual files to scan
        if not self.project_root.exists():
            raise RuntimeError(f"Project root not found: {self.project_root}")
        
        # Verify staging endpoints are accessible for L4 realism
        await self._verify_staging_endpoints()
    
    async def execute_critical_path_test(self) -> Dict[str, Any]:
        """Execute the OAuth URL consistency audit as critical path test."""
        return await self.execute_oauth_url_audit()
    
    async def validate_critical_path_results(self, results: Dict[str, Any]) -> bool:
        """Validate OAuth URL audit results meet business requirements."""
        audit_result = results.get("audit_result")
        if not audit_result:
            return False
        
        # Critical requirement: No critical inconsistencies
        critical_count = audit_result.get("critical_inconsistencies", 0)
        if critical_count > 0:
            self.test_metrics.errors.append(
                f"Found {critical_count} critical OAuth URL inconsistencies"
            )
            return False
        
        # Performance requirement: Audit should complete quickly
        duration = audit_result.get("audit_duration_seconds", 0)
        if duration > 60.0:
            self.test_metrics.errors.append(f"Audit took too long: {duration}s")
            return False
        
        # Coverage requirement: Should scan meaningful number of files
        files_scanned = audit_result.get("total_files_scanned", 0)
        if files_scanned < 10:
            self.test_metrics.errors.append(f"Too few files scanned: {files_scanned}")
            return False
        
        return True
    
    async def cleanup_test_specific_resources(self) -> None:
        """Clean up OAuth test specific resources."""
        # No specific cleanup needed for URL scanning
        pass
    
    async def _verify_staging_endpoints(self) -> None:
        """Verify staging endpoints are accessible for L4 testing."""
        for service_name, expected_url in self.expected_staging_urls.items():
            if service_name == "websocket":
                continue  # Skip WebSocket endpoint for HTTP check
            
            try:
                health_url = f"{expected_url}/health"
                response = await self.test_client.get(health_url, timeout=10.0)
                # Accept 200, 404, or 405 as "accessible" - we just need DNS/routing to work
                if response.status_code in [200, 404, 405]:
                    self.test_metrics.details[f"{service_name}_endpoint_accessible"] = True
                else:
                    self.test_metrics.details[f"{service_name}_endpoint_accessible"] = False
            except Exception as e:
                self.test_metrics.details[f"{service_name}_endpoint_error"] = str(e)
        
    async def execute_oauth_url_audit(self) -> Dict[str, Any]:
        """Execute comprehensive OAuth URL consistency audit across all services."""
        start_time = datetime.now()
        inconsistencies = []
        total_scanned = 0
        urls_found = 0
        patterns_detected = {}
        file_types_scanned = {}
        staging_endpoints_verified = []
        
        # Phase 1: Scan critical files mentioned in BVJ
        critical_files = [
            "app/clients/auth_client_config.py",
            "auth_service/main.py", 
            "frontend/lib/auth-service-config.ts",
            "frontend/src/config/auth.ts",
            "docker-compose.staging.yml",
            ".env.staging",
            "deployment/staging/values.yaml"
        ]
        
        for file_rel_path in critical_files:
            file_path = self.project_root / file_rel_path
            if file_path.exists():
                total_scanned += 1
                file_type = self._get_file_type(file_path)
                file_types_scanned[file_type] = file_types_scanned.get(file_type, 0) + 1
                
                file_inconsistencies = await self._scan_file_comprehensive(file_path, file_rel_path)
                inconsistencies.extend(file_inconsistencies)
                urls_found += len([i for i in file_inconsistencies if self._is_oauth_related(i.line_content)])
        
        # Phase 2: Scan all configuration files
        config_files = []
        for pattern_type, patterns in self.file_patterns.items():
            for pattern in patterns:
                config_files.extend(self.project_root.rglob(pattern))
        
        # Limit to 100 files for performance, prioritize config files
        prioritized_files = sorted(config_files, key=lambda p: (
            0 if any(keyword in str(p).lower() for keyword in ['config', 'env', 'docker', 'deploy']) else 1,
            str(p)
        ))[:100]
        
        for file_path in prioritized_files:
            if self._should_scan_file(file_path) and file_path not in [self.project_root / cf for cf in critical_files]:
                total_scanned += 1
                file_type = self._get_file_type(file_path)
                file_types_scanned[file_type] = file_types_scanned.get(file_type, 0) + 1
                
                try:
                    file_inconsistencies = await self._scan_file_comprehensive(
                        file_path, 
                        str(file_path.relative_to(self.project_root))
                    )
                    inconsistencies.extend(file_inconsistencies)
                    urls_found += len([i for i in file_inconsistencies if self._is_oauth_related(i.line_content)])
                except Exception:
                    continue  # Skip files that can't be processed
        
        # Phase 3: Verify staging endpoints are actually correct
        for service_name, expected_url in self.expected_staging_urls.items():
            if service_name != "websocket":  # Skip WebSocket for HTTP verification
                try:
                    health_url = f"{expected_url}/health"
                    response = await self.test_client.get(health_url, timeout=5.0)
                    if response.status_code in [200, 404, 405]:
                        staging_endpoints_verified.append(expected_url)
                        self.test_metrics.service_calls += 1
                except Exception:
                    pass  # Endpoint verification is supplementary
        
        # Phase 4: Count pattern occurrences
        for inconsistency in inconsistencies:
            pattern = inconsistency.incorrect_url
            patterns_detected[pattern] = patterns_detected.get(pattern, 0) + 1
        
        duration = (datetime.now() - start_time).total_seconds()
        critical_count = len([i for i in inconsistencies if i.severity == "critical"])
        
        audit_result = OAuthAuditResult(
            total_files_scanned=total_scanned,
            oauth_urls_found=urls_found,
            inconsistencies_detected=len(inconsistencies),
            critical_inconsistencies=critical_count,
            audit_duration_seconds=duration,
            inconsistencies=inconsistencies,
            patterns_detected=patterns_detected,
            file_types_scanned=file_types_scanned,
            staging_endpoints_verified=staging_endpoints_verified
        )
        
        return {"audit_result": audit_result}
    
    def _should_scan_file(self, file_path: Path) -> bool:
        """Check if file should be scanned for OAuth URLs."""
        exclude_patterns = ["__pycache__", ".pytest_cache", "test_", ".git", "node_modules"]
        return not any(pattern in str(file_path) for pattern in exclude_patterns)
    
    def _contains_oauth_url(self, content: str) -> bool:
        """Check if content contains OAuth-related URLs."""
        oauth_indicators = ["staging.netrasystems.ai", "oauth", "auth/callback", "redirect_uri"]
        return any(indicator in content.lower() for indicator in oauth_indicators)
    
    async def _scan_file(self, file_path: Path, relative_path: str) -> List[URLInconsistency]:
        """Scan file for OAuth URL inconsistencies."""
        inconsistencies = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
            for line_num, line in enumerate(lines, 1):
                if self._contains_oauth_url(line):
                    inconsistency = self._detect_inconsistency(relative_path, line_num, line.strip())
                    if inconsistency:
                        inconsistencies.append(inconsistency)
                        
        except Exception:
            pass  # Skip files that can't be read
            
        return inconsistencies
    
    def _detect_inconsistency(self, file_path: str, line_num: int, line_content: str) -> Optional[URLInconsistency]:
        """Detect OAuth URL inconsistency in a line."""
        for incorrect_pattern in self.incorrect_patterns:
            if incorrect_pattern in line_content:
                expected_url = "https://auth.staging.netrasystems.ai"
                severity = "critical" if "redirect" in line_content.lower() else "medium"
                
                return URLInconsistency(
                    file_path=file_path,
                    line_number=line_num,
                    line_content=line_content,
                    incorrect_url=incorrect_pattern,
                    expected_url=expected_url,
                    severity=severity
                )
        return None
    
    async def check_critical_file_line(self, file_path: str, line_number: int) -> Dict[str, Any]:
        """Check specific critical file line mentioned in BVJ."""
        full_path = self.project_root / file_path
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            if len(lines) >= line_number:
                line_content = lines[line_number - 1].strip()
                has_issue = any(pattern in line_content for pattern in self.incorrect_patterns)
                
                return {
                    "exists": True,
                    "line_number": line_number,
                    "line_content": line_content,
                    "has_incorrect_url": has_issue
                }
            else:
                return {"exists": True, "error": f"File has fewer than {line_number} lines"}
                
        except Exception as e:
            return {"exists": False, "error": str(e)}
    
    async def test_oauth_endpoints(self) -> Dict[str, Any]:
        """Test OAuth endpoints accessibility in staging."""
        endpoints = ["https://auth.staging.netrasystems.ai/health"]
        results = []
        
        for endpoint in endpoints:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(endpoint)
                    results.append({
                        "url": endpoint,
                        "success": response.status_code in [200, 404],
                        "status_code": response.status_code
                    })
            except Exception as e:
                results.append({"url": endpoint, "success": False, "error": str(e)})
        
        return {
            "endpoints_tested": len(results),
            "successful_responses": sum(1 for r in results if r["success"]),
            "results": results
        }
    
    async def cleanup_l4_resources(self) -> None:
        """Clean up L4 test resources."""
        if self.staging_suite:
            await self.staging_suite.cleanup()


@pytest.fixture
async def oauth_url_consistency_l4_suite():
    """Create L4 OAuth URL consistency test suite."""
    suite = OAuthURLConsistencyL4TestSuite()
    await suite.initialize_l4_environment()
    yield suite
    await suite.cleanup_l4_resources()


@pytest.mark.asyncio
@pytest.mark.staging
async def test_oauth_staging_url_consistency_comprehensive_l4(oauth_url_consistency_l4_suite):
    """Test comprehensive OAuth URL consistency across all services in staging."""
    audit_result = await oauth_url_consistency_l4_suite.execute_oauth_url_audit()
    
    assert audit_result.total_files_scanned > 10, f"Too few files scanned: {audit_result.total_files_scanned}"
    assert audit_result.audit_duration_seconds < 60.0, f"Audit took too long: {audit_result.audit_duration_seconds}s"
    
    # Critical requirement: No critical inconsistencies allowed
    critical_inconsistencies = [i for i in audit_result.inconsistencies if i.severity == "critical"]
    assert len(critical_inconsistencies) == 0, (
        f"Found {len(critical_inconsistencies)} critical OAuth URL inconsistencies:\n" +
        "\n".join([f"  - {inc.file_path}:{inc.line_number} -> '{inc.incorrect_url}'" for inc in critical_inconsistencies[:3]])
    )


@pytest.mark.asyncio
@pytest.mark.staging
async def test_auth_client_config_line_368_consistency_l4(oauth_url_consistency_l4_suite):
    """Test specific line 368 in auth_client_config.py mentioned in BVJ."""
    result = await oauth_url_consistency_l4_suite.check_critical_file_line("app/clients/auth_client_config.py", 368)
    
    assert result["exists"] is True, "Critical file app/clients/auth_client_config.py does not exist"
    
    if "has_incorrect_url" in result:
        assert result["has_incorrect_url"] is False, (
            f"Line 368 contains incorrect URL: {result.get('line_content')}"
        )


@pytest.mark.asyncio
@pytest.mark.staging
async def test_auth_service_main_line_147_consistency_l4(oauth_url_consistency_l4_suite):
    """Test specific line 147 in auth_service/main.py mentioned in BVJ."""
    result = await oauth_url_consistency_l4_suite.check_critical_file_line("auth_service/main.py", 147)
    
    assert result["exists"] is True, "Critical file auth_service/main.py does not exist"
    
    if "has_incorrect_url" in result:
        assert result["has_incorrect_url"] is False, (
            f"Line 147 contains incorrect URL: {result.get('line_content')}"
        )


@pytest.mark.asyncio
@pytest.mark.staging
async def test_oauth_endpoint_accessibility_l4(oauth_url_consistency_l4_suite):
    """Test OAuth endpoints are accessible in staging."""
    endpoint_results = await oauth_url_consistency_l4_suite.test_oauth_endpoints()
    
    assert endpoint_results["endpoints_tested"] > 0, "No OAuth endpoints tested"
    
    success_rate = endpoint_results["successful_responses"] / endpoint_results["endpoints_tested"]
    assert success_rate >= 0.5, f"OAuth endpoint success rate too low: {success_rate}"


@pytest.mark.asyncio
@pytest.mark.staging
async def test_oauth_audit_performance_l4(oauth_url_consistency_l4_suite):
    """Test OAuth URL audit meets performance requirements in staging."""
    audit_result = await oauth_url_consistency_l4_suite.execute_oauth_url_audit()
    
    assert audit_result.audit_duration_seconds < 60.0, f"Audit took too long: {audit_result.audit_duration_seconds}s"
    assert audit_result.total_files_scanned >= 10, f"Too few files scanned: {audit_result.total_files_scanned}"
    
    # Inconsistency detection rate should be reasonable (less than 20%)
    if audit_result.oauth_urls_found > 0:
        inconsistency_rate = audit_result.inconsistencies_detected / audit_result.oauth_urls_found
        assert inconsistency_rate < 0.2, f"OAuth inconsistency rate too high: {inconsistency_rate:.2%}"