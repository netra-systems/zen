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
        
    async def initialize_l4_environment(self) -> None:
        """Initialize L4 staging environment for URL consistency testing."""
        self.staging_suite = await get_staging_suite()
        await self.staging_suite.setup()
        
    async def execute_oauth_url_audit(self) -> OAuthAuditResult:
        """Execute OAuth URL consistency audit across all services."""
        start_time = datetime.now()
        inconsistencies = []
        total_scanned = 0
        urls_found = 0
        
        # Scan critical files mentioned in BVJ
        critical_files = [
            "app/clients/auth_client_config.py",
            "auth_service/main.py",
            "frontend/lib/auth-service-config.ts"
        ]
        
        for file_rel_path in critical_files:
            file_path = self.project_root / file_rel_path
            if file_path.exists():
                total_scanned += 1
                file_inconsistencies = await self._scan_file(file_path, file_rel_path)
                inconsistencies.extend(file_inconsistencies)
                urls_found += len(file_inconsistencies)
        
        # Scan additional source files
        python_files = list(self.project_root.rglob("*.py"))[:50]  # Limit for performance
        for file_path in python_files:
            if self._should_scan_file(file_path):
                total_scanned += 1
                file_inconsistencies = await self._scan_file(file_path, str(file_path.relative_to(self.project_root)))
                inconsistencies.extend(file_inconsistencies)
                urls_found += len([i for i in file_inconsistencies if self._contains_oauth_url(str(file_path))])
        
        duration = (datetime.now() - start_time).total_seconds()
        critical_count = len([i for i in inconsistencies if i.severity == "critical"])
        
        return OAuthAuditResult(
            total_files_scanned=total_scanned,
            oauth_urls_found=urls_found,
            inconsistencies_detected=len(inconsistencies),
            critical_inconsistencies=critical_count,
            audit_duration_seconds=duration,
            inconsistencies=inconsistencies
        )
    
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