"""
GitHub Integration Test Configuration

Centralized configuration management for GitHub integration tests.
Follows SSOT principles and IsolatedEnvironment patterns.

CRITICAL: This is the SINGLE SOURCE OF TRUTH for GitHub test configuration.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from shared.isolated_environment import IsolatedEnvironment

@dataclass
class GitHubTestConfiguration:
    """
    GitHub integration test configuration
    
    CRITICAL: All GitHub test configuration must go through this class
    to ensure consistency and proper environment isolation.
    """
    
    # GitHub API Configuration
    api_base_url: str
    token: str
    repo_owner: str
    repo_name: str
    
    # Test Configuration
    enabled: bool
    test_label: str
    cleanup_enabled: bool
    
    # Rate Limiting Configuration
    rate_limit_buffer: int
    max_issues_per_hour: int
    max_api_calls_per_test: int
    
    # Security Configuration
    webhook_secret: str
    webhook_url: str
    sanitization_enabled: bool
    
    # Performance Configuration
    timeout_seconds: int
    max_concurrent_requests: int
    retry_attempts: int
    retry_delay_seconds: int
    
    # Environment-specific settings
    environment: str  # "test", "integration", "staging"
    debug_mode: bool
    verbose_logging: bool
    
    @classmethod
    def from_isolated_environment(cls, env: IsolatedEnvironment = None) -> "GitHubTestConfiguration":
        """
        Create configuration from IsolatedEnvironment
        
        CRITICAL: This is the CANONICAL way to create GitHub test configuration.
        All tests must use this method to ensure proper environment isolation.
        """
        if env is None:
            env = IsolatedEnvironment()
        
        return cls(
            # GitHub API Configuration
            api_base_url=env.get("GITHUB_API_BASE_URL", "https://api.github.com"),
            token=env.get("GITHUB_TEST_TOKEN", ""),
            repo_owner=env.get("GITHUB_TEST_REPO_OWNER", ""),
            repo_name=env.get("GITHUB_TEST_REPO_NAME", ""),
            
            # Test Configuration
            enabled=env.get("GITHUB_INTEGRATION_TEST_ENABLED", "false").lower() == "true",
            test_label=env.get("GITHUB_TEST_LABEL", "automated-test"),
            cleanup_enabled=env.get("GITHUB_TEST_CLEANUP_ENABLED", "true").lower() == "true",
            
            # Rate Limiting Configuration
            rate_limit_buffer=int(env.get("GITHUB_RATE_LIMIT_BUFFER", "100")),
            max_issues_per_hour=int(env.get("GITHUB_MAX_ISSUES_PER_HOUR", "50")),
            max_api_calls_per_test=int(env.get("GITHUB_MAX_API_CALLS_PER_TEST", "20")),
            
            # Security Configuration
            webhook_secret=env.get("GITHUB_WEBHOOK_SECRET", ""),
            webhook_url=env.get("GITHUB_WEBHOOK_URL", ""),
            sanitization_enabled=env.get("GITHUB_SANITIZATION_ENABLED", "true").lower() == "true",
            
            # Performance Configuration
            timeout_seconds=int(env.get("GITHUB_TIMEOUT_SECONDS", "30")),
            max_concurrent_requests=int(env.get("GITHUB_MAX_CONCURRENT_REQUESTS", "5")),
            retry_attempts=int(env.get("GITHUB_RETRY_ATTEMPTS", "3")),
            retry_delay_seconds=int(env.get("GITHUB_RETRY_DELAY_SECONDS", "1")),
            
            # Environment-specific settings
            environment=env.get("GITHUB_TEST_ENVIRONMENT", "test"),
            debug_mode=env.get("GITHUB_TEST_DEBUG", "false").lower() == "true",
            verbose_logging=env.get("GITHUB_TEST_VERBOSE", "false").lower() == "true"
        )
    
    def validate(self) -> List[str]:
        """
        Validate configuration and return list of validation errors
        
        Returns:
            List of validation error messages. Empty list if valid.
        """
        errors = []
        
        # Required fields validation
        if not self.token:
            errors.append("GITHUB_TEST_TOKEN is required for GitHub integration tests")
        
        if not self.repo_owner:
            errors.append("GITHUB_TEST_REPO_OWNER is required for GitHub integration tests")
        
        if not self.repo_name:
            errors.append("GITHUB_TEST_REPO_NAME is required for GitHub integration tests")
        
        # Security validation
        if self.webhook_url and not self.webhook_secret:
            errors.append("GITHUB_WEBHOOK_SECRET is required when GITHUB_WEBHOOK_URL is configured")
        
        if self.webhook_url and not self.webhook_url.startswith("https://"):
            errors.append("GITHUB_WEBHOOK_URL must use HTTPS for security")
        
        # Rate limiting validation
        if self.max_issues_per_hour <= 0:
            errors.append("GITHUB_MAX_ISSUES_PER_HOUR must be positive")
        
        if self.rate_limit_buffer < 0:
            errors.append("GITHUB_RATE_LIMIT_BUFFER cannot be negative")
        
        # Performance validation
        if self.timeout_seconds <= 0:
            errors.append("GITHUB_TIMEOUT_SECONDS must be positive")
        
        if self.max_concurrent_requests <= 0:
            errors.append("GITHUB_MAX_CONCURRENT_REQUESTS must be positive")
        
        if self.retry_attempts < 0:
            errors.append("GITHUB_RETRY_ATTEMPTS cannot be negative")
        
        # Environment validation
        valid_environments = ["test", "integration", "staging", "production"]
        if self.environment not in valid_environments:
            errors.append(f"GITHUB_TEST_ENVIRONMENT must be one of: {valid_environments}")
        
        return errors
    
    def is_valid(self) -> bool:
        """Check if configuration is valid"""
        return len(self.validate()) == 0
    
    def get_api_headers(self) -> Dict[str, str]:
        """Get standard API headers for GitHub requests"""
        return {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": f"Netra-GitHub-Tests/{self.environment}"
        }
    
    def get_repository_url(self) -> str:
        """Get full repository URL"""
        return f"{self.api_base_url}/repos/{self.repo_owner}/{self.repo_name}"
    
    def should_skip_tests(self) -> tuple[bool, str]:
        """
        Check if tests should be skipped and return reason
        
        Returns:
            Tuple of (should_skip: bool, reason: str)
        """
        if not self.enabled:
            return True, "GitHub integration tests are disabled (GITHUB_INTEGRATION_TEST_ENABLED=false)"
        
        validation_errors = self.validate()
        if validation_errors:
            return True, f"GitHub configuration invalid: {'; '.join(validation_errors)}"
        
        return False, ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary (excluding sensitive data)"""
        return {
            "api_base_url": self.api_base_url,
            "repo_owner": self.repo_owner,
            "repo_name": self.repo_name,
            "enabled": self.enabled,
            "test_label": self.test_label,
            "cleanup_enabled": self.cleanup_enabled,
            "rate_limit_buffer": self.rate_limit_buffer,
            "max_issues_per_hour": self.max_issues_per_hour,
            "max_api_calls_per_test": self.max_api_calls_per_test,
            "sanitization_enabled": self.sanitization_enabled,
            "timeout_seconds": self.timeout_seconds,
            "max_concurrent_requests": self.max_concurrent_requests,
            "retry_attempts": self.retry_attempts,
            "retry_delay_seconds": self.retry_delay_seconds,
            "environment": self.environment,
            "debug_mode": self.debug_mode,
            "verbose_logging": self.verbose_logging,
            # Sensitive fields excluded: token, webhook_secret
            "token_configured": bool(self.token),
            "webhook_configured": bool(self.webhook_url)
        }


class GitHubTestConfigurationFactory:
    """
    Factory for creating GitHub test configurations for different scenarios
    
    CRITICAL: Use these factory methods for consistent configuration creation.
    """
    
    @staticmethod
    def for_unit_tests(env: IsolatedEnvironment = None) -> GitHubTestConfiguration:
        """Create configuration optimized for unit tests"""
        config = GitHubTestConfiguration.from_isolated_environment(env)
        
        # Unit tests typically don't need real API calls
        config.enabled = False
        config.timeout_seconds = 5
        config.max_api_calls_per_test = 0
        config.cleanup_enabled = False
        
        return config
    
    @staticmethod
    def for_integration_tests(env: IsolatedEnvironment = None) -> GitHubTestConfiguration:
        """Create configuration optimized for integration tests"""
        config = GitHubTestConfiguration.from_isolated_environment(env)
        
        # Integration tests need real API access but with limits
        config.timeout_seconds = 30
        config.max_api_calls_per_test = 10
        config.max_concurrent_requests = 3
        config.cleanup_enabled = True
        
        return config
    
    @staticmethod
    def for_e2e_tests(env: IsolatedEnvironment = None) -> GitHubTestConfiguration:
        """Create configuration optimized for e2e tests"""
        config = GitHubTestConfiguration.from_isolated_environment(env)
        
        # E2E tests need full functionality
        config.timeout_seconds = 60
        config.max_api_calls_per_test = 50
        config.max_concurrent_requests = 5
        config.cleanup_enabled = True
        config.verbose_logging = True
        
        return config
    
    @staticmethod
    def for_mission_critical_tests(env: IsolatedEnvironment = None) -> GitHubTestConfiguration:
        """Create configuration optimized for mission critical tests"""
        config = GitHubTestConfiguration.from_isolated_environment(env)
        
        # Mission critical tests need maximum reliability
        config.timeout_seconds = 120
        config.max_api_calls_per_test = 100
        config.max_concurrent_requests = 10
        config.retry_attempts = 5
        config.retry_delay_seconds = 2
        config.cleanup_enabled = True
        config.debug_mode = True
        config.verbose_logging = True
        
        return config


# SSOT Configuration Instance
def get_github_test_config(test_type: str = "default") -> GitHubTestConfiguration:
    """
    Get GitHub test configuration for specified test type
    
    CRITICAL: This is the CANONICAL way to get GitHub test configuration.
    All tests should use this function.
    
    Args:
        test_type: Type of test ("unit", "integration", "e2e", "mission_critical", "default")
    
    Returns:
        GitHubTestConfiguration instance
    """
    factory = GitHubTestConfigurationFactory()
    
    if test_type == "unit":
        return factory.for_unit_tests()
    elif test_type == "integration":
        return factory.for_integration_tests()
    elif test_type == "e2e":
        return factory.for_e2e_tests()
    elif test_type == "mission_critical":
        return factory.for_mission_critical_tests()
    else:
        return GitHubTestConfiguration.from_isolated_environment()


# Configuration validation helper
def validate_github_test_environment() -> tuple[bool, List[str]]:
    """
    Validate GitHub test environment configuration
    
    Returns:
        Tuple of (is_valid: bool, error_messages: List[str])
    """
    config = get_github_test_config()
    errors = config.validate()
    return len(errors) == 0, errors