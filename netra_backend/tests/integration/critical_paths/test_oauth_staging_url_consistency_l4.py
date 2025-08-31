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

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from netra_backend.tests.integration.e2e.staging_test_helpers import StagingTestSuite, get_staging_suite
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

StagingTestSuite = AsyncMock
get_staging_suite = AsyncMock
from netra_backend.tests.integration.critical_paths.l4_staging_critical_base import (
    L4StagingCriticalPathTestBase,
)

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
            "https://app.staging.netrasystems.ai",  # Legacy format
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
            "docker-compose.yml",  # Local Docker Compose (no staging reference)
            ".env.staging",        # Actual staging environment variables
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
        exclude_patterns = [
            "__pycache__", ".pytest_cache", "test_", ".git", "node_modules",
            ".mypy_cache", ".tox", "venv", ".venv", "dist", "build",
            ".DS_Store", "*.pyc", "*.pyo", "*.log"
        ]
        file_str = str(file_path).lower()
        
        # Exclude certain patterns but include important config files
        if any(pattern in file_str for pattern in exclude_patterns):
            return False
        
        # Include if file size is reasonable (< 1MB)
        try:
            if file_path.stat().st_size > 1024 * 1024:
                return False
        except OSError:
            return False
        
        return True
    
    def _get_file_type(self, file_path: Path) -> str:
        """Get categorized file type for scanning."""
        extension = file_path.suffix.lower()
        name = file_path.name.lower()
        
        if extension in ['.py']:
            return 'python'
        elif extension in ['.ts', '.tsx']:
            return 'typescript'
        elif extension in ['.js', '.jsx']:
            return 'javascript'
        elif extension in ['.yaml', '.yml', '.json'] or name.startswith('.env'):
            return 'config'
        elif 'dockerfile' in name or 'docker-compose' in name:
            return 'docker'
        else:
            return 'other'
    
    def _is_oauth_related(self, content: str) -> bool:
        """Check if content contains OAuth-related URLs."""
        content_lower = content.lower()
        return any(keyword in content_lower for keyword in self.oauth_keywords)
    
    async def _scan_file_comprehensive(self, file_path: Path, relative_path: str) -> List[URLInconsistency]:
        """Comprehensively scan file for OAuth URL inconsistencies."""
        inconsistencies = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
            for line_num, line in enumerate(lines, 1):
                line_content = line.strip()
                if not line_content or line_content.startswith('#'):
                    continue
                
                # Check for any staging URLs or OAuth patterns
                if self._contains_staging_pattern(line_content):
                    inconsistency = self._detect_comprehensive_inconsistency(
                        relative_path, line_num, line_content
                    )
                    if inconsistency:
                        inconsistencies.append(inconsistency)
                        
        except Exception:
            pass  # Skip files that can't be read
            
        return inconsistencies
    
    def _contains_staging_pattern(self, content: str) -> bool:
        """Check if content contains any staging-related patterns."""
        # Check for incorrect patterns
        for pattern in self.incorrect_patterns:
            if pattern in content:
                return True
        
        # Check for OAuth-related content with staging URLs
        if 'staging' in content.lower() and any(keyword in content.lower() for keyword in self.oauth_keywords):
            return True
        
        return False
    
    def _detect_comprehensive_inconsistency(self, file_path: str, line_num: int, line_content: str) -> Optional[URLInconsistency]:
        """Detect OAuth URL inconsistency with enhanced context detection."""
        for incorrect_pattern in self.incorrect_patterns:
            if incorrect_pattern in line_content:
                # Determine the correct replacement based on context
                expected_url, url_type = self._determine_correct_url(line_content, incorrect_pattern)
                
                # Determine severity based on context
                severity = self._determine_severity(line_content, url_type)
                
                # Get context about the usage
                context = self._get_usage_context(line_content)
                
                return URLInconsistency(
                    file_path=file_path,
                    line_number=line_num,
                    line_content=line_content,
                    incorrect_url=incorrect_pattern,
                    expected_url=expected_url,
                    severity=severity,
                    url_type=url_type,
                    context=context
                )
        return None
    
    def _determine_correct_url(self, line_content: str, incorrect_pattern: str) -> tuple:
        """Determine the correct URL and type based on line content context."""
        line_lower = line_content.lower()
        
        # Check for redirect URIs (should point to auth service)
        if any(keyword in line_lower for keyword in ['redirect_uri', 'callback', 'oauth_callback']):
            return "https://auth.staging.netrasystems.ai/auth/callback", "redirect_uri"
        
        # Check for JavaScript origins (should point to frontend)
        if any(keyword in line_lower for keyword in ['javascript_origin', 'origin', 'cors']):
            return "https://app.staging.netrasystems.ai", "javascript_origin"
        
        # Check for API endpoints (should point to backend)
        if any(keyword in line_lower for keyword in ['api', 'endpoint', 'backend']):
            return "https://api.staging.netrasystems.ai", "api_endpoint"
        
        # Check for frontend/UI references
        if any(keyword in line_lower for keyword in ['frontend', 'ui', 'app', 'client']):
            return "https://app.staging.netrasystems.ai", "frontend"
        
        # Default to auth service for OAuth-related content
        if any(keyword in line_lower for keyword in self.oauth_keywords):
            return "https://auth.staging.netrasystems.ai", "auth_service"
        
        # Generic staging reference - suggest backend API
        return "https://api.staging.netrasystems.ai", "config"
    
    def _determine_severity(self, line_content: str, url_type: str) -> str:
        """Determine severity of the inconsistency."""
        line_lower = line_content.lower()
        
        # Critical: OAuth redirect URIs and authentication endpoints
        if url_type in ['redirect_uri', 'auth_service'] or any(
            keyword in line_lower for keyword in ['redirect_uri', 'oauth', 'callback', 'authentication']
        ):
            return "critical"
        
        # High: JavaScript origins and CORS settings
        if url_type == 'javascript_origin' or 'cors' in line_lower:
            return "high"
        
        # Medium: API endpoints and configuration
        if url_type in ['api_endpoint', 'config']:
            return "medium"
        
        # Low: Frontend references and documentation
        return "low"
    
    def _get_usage_context(self, line_content: str) -> str:
        """Get context about how the URL is being used."""
        line_lower = line_content.lower()
        
        if 'redirect_uri' in line_lower:
            return "OAuth redirect URI configuration"
        elif 'javascript_origin' in line_lower:
            return "CORS JavaScript origins configuration"
        elif 'callback' in line_lower:
            return "OAuth callback URL"
        elif any(keyword in line_lower for keyword in ['client_id', 'client_secret']):
            return "OAuth client configuration"
        elif 'endpoint' in line_lower or 'url' in line_lower:
            return "Service endpoint configuration"
        elif any(keyword in line_lower for keyword in ['env', 'config']):
            return "Environment configuration"
        else:
            return "General staging URL reference"
    
    async def check_critical_file_line(self, file_path: str, line_number: int) -> Dict[str, Any]:
        """Check specific critical file line mentioned in BVJ."""
        full_path = self.project_root / file_path
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            if len(lines) >= line_number:
                line_content = lines[line_number - 1].strip()
                has_issue = any(pattern in line_content for pattern in self.incorrect_patterns)
                
                # Provide detailed analysis if issue found
                issue_details = None
                if has_issue:
                    inconsistency = self._detect_comprehensive_inconsistency(
                        file_path, line_number, line_content
                    )
                    if inconsistency:
                        issue_details = {
                            "incorrect_url": inconsistency.incorrect_url,
                            "expected_url": inconsistency.expected_url,
                            "severity": inconsistency.severity,
                            "url_type": inconsistency.url_type,
                            "context": inconsistency.context
                        }
                
                return {
                    "exists": True,
                    "line_number": line_number,
                    "line_content": line_content,
                    "has_incorrect_url": has_issue,
                    "issue_details": issue_details
                }
            else:
                return {"exists": True, "error": f"File has fewer than {line_number} lines"}
                
        except Exception as e:
            return {"exists": False, "error": str(e)}
    
    @pytest.mark.asyncio
    async def test_oauth_endpoints_accessibility(self) -> Dict[str, Any]:
        """Test OAuth endpoints accessibility in staging environment."""
        endpoints_to_test = [
            ("auth_health", "https://auth.staging.netrasystems.ai/health"),
            ("auth_oauth", "https://auth.staging.netrasystems.ai/oauth"),
            ("api_health", "https://api.staging.netrasystems.ai/health"),
            ("frontend_health", "https://app.staging.netrasystems.ai/health")
        ]
        
        results = []
        
        for endpoint_name, endpoint_url in endpoints_to_test:
            try:
                response = await self.test_client.get(endpoint_url, timeout=10.0)
                success = response.status_code in [200, 404, 405]  # Accept these as "accessible"
                
                results.append({
                    "name": endpoint_name,
                    "url": endpoint_url,
                    "success": success,
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds() if hasattr(response, 'elapsed') else 0
                })
                
                self.test_metrics.service_calls += 1
                
            except Exception as e:
                results.append({
                    "name": endpoint_name,
                    "url": endpoint_url,
                    "success": False,
                    "error": str(e)
                })
        
        return {
            "endpoints_tested": len(results),
            "successful_responses": sum(1 for r in results if r["success"]),
            "failed_responses": sum(1 for r in results if not r["success"]),
            "results": results
        }
    
    async def validate_oauth_redirect_urls(self) -> Dict[str, Any]:
        """Validate that OAuth redirect URLs follow correct subdomain pattern."""
        redirect_validations = []
        
        # Check auth_client_config.py specifically for the known issue
        auth_config_path = self.project_root / "app/clients/auth_client_config.py"
        
        if auth_config_path.exists():
            try:
                with open(auth_config_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Look for redirect_uris patterns
                redirect_uri_pattern = r'redirect_uris?\s*=\s*\[([^\]]+)\]'
                javascript_origins_pattern = r'javascript_origins?\s*=\s*\[([^\]]+)\]'
                
                import re
                
                redirect_matches = re.findall(redirect_uri_pattern, content, re.IGNORECASE)
                origin_matches = re.findall(javascript_origins_pattern, content, re.IGNORECASE)
                
                for match in redirect_matches:
                    if "staging.netrasystems.ai" in match and "auth.staging.netrasystems.ai" not in match:
                        redirect_validations.append({
                            "type": "redirect_uri",
                            "content": match.strip(),
                            "valid": False,
                            "issue": "Should use auth.staging.netrasystems.ai subdomain"
                        })
                    else:
                        redirect_validations.append({
                            "type": "redirect_uri",
                            "content": match.strip(),
                            "valid": True
                        })
                
                for match in origin_matches:
                    if "staging.netrasystems.ai" in match and "app.staging.netrasystems.ai" not in match:
                        redirect_validations.append({
                            "type": "javascript_origin",
                            "content": match.strip(),
                            "valid": False,
                            "issue": "Should use app.staging.netrasystems.ai subdomain"
                        })
                    else:
                        redirect_validations.append({
                            "type": "javascript_origin",
                            "content": match.strip(),
                            "valid": True
                        })
                        
            except Exception as e:
                redirect_validations.append({
                    "type": "error",
                    "error": f"Failed to validate auth config: {str(e)}"
                })
        
        valid_count = sum(1 for v in redirect_validations if v.get("valid", False))
        
        return {
            "total_validations": len(redirect_validations),
            "valid_redirects": valid_count,
            "invalid_redirects": len(redirect_validations) - valid_count,
            "validations": redirect_validations
        }

@pytest.fixture
async def oauth_url_consistency_l4_suite():
    """Create L4 OAuth URL consistency test suite with proper L4 base."""
    suite = OAuthURLConsistencyL4TestSuite()
    await suite.initialize_l4_environment()
    yield suite
    await suite.cleanup_l4_resources()

@pytest.mark.asyncio
@pytest.mark.staging
@pytest.mark.l4
@pytest.mark.asyncio
async def test_oauth_staging_url_consistency_comprehensive_l4(oauth_url_consistency_l4_suite):
    """L4 Test: Comprehensive OAuth URL consistency across all services in staging.
    
    This test validates that all staging OAuth URLs follow the correct subdomain architecture.
    BVJ: $25K MRR - Prevents authentication failures caused by incorrect OAuth URLs.
    """
    # Execute the complete critical path test with L4 metrics
    test_metrics = await oauth_url_consistency_l4_suite.run_complete_critical_path_test()
    
    # Validate that test succeeded
    assert test_metrics.success, f"OAuth URL consistency test failed: {test_metrics.errors}"
    
    # Validate performance requirements
    assert test_metrics.duration < 60.0, f"Test took too long: {test_metrics.duration:.2f}s"
    assert test_metrics.service_calls > 0, "No staging service calls were made"
    
    # Get detailed audit results
    audit_data = test_metrics.details.get("audit_result")
    assert audit_data is not None, "Audit results not found in test metrics"
    
    # Critical requirement: No critical inconsistencies allowed
    critical_count = audit_data.get("critical_inconsistencies", 0)
    assert critical_count == 0, (
        f"Found {critical_count} critical OAuth URL inconsistencies. "
        f"See inconsistencies in test metrics for details."
    )
    
    # Coverage requirement: Should scan meaningful number of files
    files_scanned = audit_data.get("total_files_scanned", 0)
    assert files_scanned >= 10, f"Too few files scanned: {files_scanned}"

@pytest.mark.asyncio
@pytest.mark.staging
@pytest.mark.l4
@pytest.mark.asyncio
async def test_auth_client_config_fallback_url_l4(oauth_url_consistency_l4_suite):
    """L4 Test: Specific validation of auth_client_config.py fallback configuration.
    
    Tests the specific line mentioned in BVJ that contains incorrect fallback URL.
    """
    await oauth_url_consistency_l4_suite.initialize_l4_environment()
    
    result = await oauth_url_consistency_l4_suite.check_critical_file_line(
        "app/clients/auth_client_config.py", 369
    )
    
    assert result["exists"] is True, "Critical file app/clients/auth_client_config.py does not exist"
    assert "line_content" in result, "Could not read line content"
    
    # Specific test for the known issue: line 369 should not contain "https://app.staging.netrasystems.ai"
    line_content = result.get("line_content", "")
    has_incorrect_url = result.get("has_incorrect_url", False)
    
    if has_incorrect_url:
        issue_details = result.get("issue_details", {})
        pytest.fail(
            f"Line 369 contains incorrect URL pattern:\n"
            f"  Current: {line_content}\n"
            f"  Issue: {issue_details.get('incorrect_url', 'Unknown')}\n"
            f"  Expected: {issue_details.get('expected_url', 'Unknown')}\n"
            f"  Context: {issue_details.get('context', 'Unknown')}\n"
            f"  Severity: {issue_details.get('severity', 'Unknown')}"
        )

@pytest.mark.asyncio
@pytest.mark.staging
@pytest.mark.l4
@pytest.mark.asyncio
async def test_oauth_redirect_uri_validation_l4(oauth_url_consistency_l4_suite):
    """L4 Test: Validate OAuth redirect URIs follow correct staging subdomain pattern."""
    await oauth_url_consistency_l4_suite.initialize_l4_environment()
    
    validation_result = await oauth_url_consistency_l4_suite.validate_oauth_redirect_urls()
    
    assert validation_result["total_validations"] > 0, "No OAuth redirect validations performed"
    
    invalid_count = validation_result["invalid_redirects"]
    if invalid_count > 0:
        invalid_details = [
            v for v in validation_result["validations"] 
            if not v.get("valid", True)
        ]
        
        failure_message = f"Found {invalid_count} invalid OAuth redirect configurations:\n"
        for detail in invalid_details[:3]:  # Show first 3 issues
            failure_message += f"  - {detail.get('type', 'unknown')}: {detail.get('issue', 'Unknown issue')}\n"
        
        pytest.fail(failure_message)

@pytest.mark.asyncio
@pytest.mark.staging
@pytest.mark.l4
@pytest.mark.asyncio
async def test_staging_oauth_endpoints_accessibility_l4(oauth_url_consistency_l4_suite):
    """L4 Test: Validate that staging OAuth endpoints are accessible.
    
    This test verifies that the expected staging subdomains are actually reachable,
    providing L4 realism by testing against the actual staging environment.
    """
    await oauth_url_consistency_l4_suite.initialize_l4_environment()
    
    endpoint_results = await oauth_url_consistency_l4_suite.test_oauth_endpoints_accessibility()
    
    assert endpoint_results["endpoints_tested"] > 0, "No OAuth endpoints tested"
    
    failed_count = endpoint_results["failed_responses"]
    total_count = endpoint_results["endpoints_tested"]
    success_rate = endpoint_results["successful_responses"] / total_count
    
    # Allow some endpoints to be unreachable (staging environment may be partial)
    # but require at least 50% accessibility
    assert success_rate >= 0.5, (
        f"OAuth endpoint accessibility too low: {success_rate:.1%} "
        f"({endpoint_results['successful_responses']}/{total_count})"
    )

@pytest.mark.asyncio
@pytest.mark.staging
@pytest.mark.l4
@pytest.mark.asyncio
async def test_oauth_audit_performance_and_coverage_l4(oauth_url_consistency_l4_suite):
    """L4 Test: Validate OAuth URL audit performance and coverage requirements."""
    await oauth_url_consistency_l4_suite.initialize_l4_environment()
    
    # Execute audit and measure performance
    audit_results = await oauth_url_consistency_l4_suite.execute_oauth_url_audit()
    audit_data = audit_results["audit_result"]
    
    # Performance requirements
    duration = audit_data.audit_duration_seconds
    assert duration < 60.0, f"Audit took too long: {duration:.2f}s (max: 60s)"
    
    # Coverage requirements
    files_scanned = audit_data.total_files_scanned
    assert files_scanned >= 10, f"Too few files scanned: {files_scanned} (min: 10)"
    
    # File type diversity
    file_types = audit_data.file_types_scanned
    assert len(file_types) >= 2, f"Should scan multiple file types, only found: {list(file_types.keys())}"

@pytest.mark.asyncio
@pytest.mark.staging
@pytest.mark.l4
@pytest.mark.asyncio
async def test_oauth_url_pattern_analysis_l4(oauth_url_consistency_l4_suite):
    """L4 Test: Analyze OAuth URL patterns to identify systematic issues."""
    await oauth_url_consistency_l4_suite.initialize_l4_environment()
    
    audit_results = await oauth_url_consistency_l4_suite.execute_oauth_url_audit()
    audit_data = audit_results["audit_result"]
    
    patterns_detected = audit_data.patterns_detected
    inconsistencies = audit_data.inconsistencies
    
    # Validate that we're not seeing widespread systematic issues
    total_inconsistencies = audit_data.inconsistencies_detected
    if total_inconsistencies > 0:
        # Group by severity
        severity_counts = {}
        for inconsistency in inconsistencies:
            severity = inconsistency.severity
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # Critical and high severity issues should be minimal
        critical_and_high = severity_counts.get("critical", 0) + severity_counts.get("high", 0)
        assert critical_and_high == 0, (
            f"Found {critical_and_high} critical/high severity OAuth URL issues. "
            f"These must be fixed before deployment."
        )