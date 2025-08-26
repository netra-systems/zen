"""
Cypress Configuration Manager.

Generates dynamic Cypress configuration based on service availability
and environment-specific overrides for E2E test execution.
"""

import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any

from dev_launcher.isolated_environment import get_env

logger = logging.getLogger(__name__)


@dataclass
class CypressConfig:
    """Cypress configuration data structure."""
    
    # Base configuration
    base_url: str = "http://localhost:3000"
    api_url: str = "http://localhost:8000"
    
    # Timeouts (in milliseconds)
    default_command_timeout: int = 10000  # 10 seconds
    page_load_timeout: int = 30000  # 30 seconds
    request_timeout: int = 10000  # 10 seconds
    response_timeout: int = 30000  # 30 seconds
    
    # Viewport
    viewport_width: int = 1280
    viewport_height: int = 720
    
    # Test execution
    watch_for_file_changes: bool = False
    video: bool = False
    screenshot_on_run_failure: bool = True
    retry_runs: int = 2
    retry_opens: int = 0
    
    # Environment variables for tests
    env_vars: Dict[str, Any] = None
    
    # Service URLs
    service_urls: Dict[str, str] = None
    
    def __post_init__(self):
        if self.env_vars is None:
            self.env_vars = {}
        if self.service_urls is None:
            self.service_urls = {}


class CypressConfigManager:
    """
    Manages dynamic Cypress configuration generation.
    
    Generates configuration based on:
    - Service availability and URLs
    - Environment-specific overrides
    - Test execution context
    """
    
    def __init__(self, project_root: Path):
        """
        Initialize config manager.
        
        Args:
            project_root: Root directory of the project
        """
        self.project_root = project_root
        self.frontend_path = project_root / "frontend"
        self.env = get_env()
        
        # Load base configuration from existing cypress.config.ts if available
        self.base_config = self._load_base_config()
        
    def _load_base_config(self) -> Dict[str, Any]:
        """
        Load base configuration from existing Cypress config.
        
        Returns:
            Base configuration dictionary
        """
        config_path = self.frontend_path / "cypress.config.ts"
        
        # For now, return default config
        # In a more sophisticated implementation, we could parse the TS config
        return {
            "e2e": {
                "baseUrl": "http://localhost:3000",
                "supportFile": "cypress/support/e2e.ts",
                "specPattern": "cypress/e2e/**/*.{js,jsx,ts,tsx}",
                "watchForFileChanges": False,
                "video": False,
                "screenshotOnRunFailure": False
            }
        }
        
    def generate_config(self, service_status: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate dynamic Cypress configuration.
        
        Args:
            service_status: Current status of all services
            
        Returns:
            Complete Cypress configuration
        """
        logger.info("Generating dynamic Cypress configuration...")
        
        # Start with base config
        config = CypressConfig()
        
        # Update service URLs based on actual service status
        service_urls = self._extract_service_urls(service_status)
        config.service_urls = service_urls
        
        # Set base URL from frontend service
        if "frontend" in service_urls:
            config.base_url = service_urls["frontend"]
            
        # Set API URL from backend service
        if "backend" in service_urls:
            config.api_url = service_urls["backend"]
            
        # Environment-specific overrides
        self._apply_environment_overrides(config)
        
        # Generate environment variables for Cypress tests
        config.env_vars = self._generate_env_vars(service_status, service_urls)
        
        # Convert to Cypress format
        cypress_config = self._to_cypress_format(config)
        
        logger.info(f"Generated Cypress config with base URL: {config.base_url}")
        
        return cypress_config
        
    def _extract_service_urls(self, service_status: Dict[str, Any]) -> Dict[str, str]:
        """
        Extract service URLs from service status.
        
        Args:
            service_status: Service status dictionary
            
        Returns:
            Dictionary of service URLs
        """
        urls = {}
        
        for service_name, status in service_status.items():
            if status.get("healthy") and status.get("url"):
                urls[service_name] = status["url"]
                
        return urls
        
    def _apply_environment_overrides(self, config: CypressConfig):
        """
        Apply environment-specific configuration overrides.
        
        Args:
            config: Config object to modify
        """
        # Check for environment overrides
        env_base_url = self.env.get("CYPRESS_BASE_URL")
        if env_base_url:
            config.base_url = env_base_url
            logger.info(f"Using environment override for base URL: {env_base_url}")
            
        env_api_url = self.env.get("CYPRESS_API_URL")
        if env_api_url:
            config.api_url = env_api_url
            logger.info(f"Using environment override for API URL: {env_api_url}")
            
        # Timeout overrides
        env_timeout = self.env.get("CYPRESS_DEFAULT_COMMAND_TIMEOUT")
        if env_timeout:
            try:
                config.default_command_timeout = int(env_timeout)
            except ValueError:
                logger.warning(f"Invalid timeout value: {env_timeout}")
                
        # Video recording for CI
        if self.env.get("CI") or self.env.get("CYPRESS_RECORD"):
            config.video = True
            logger.info("Enabling video recording for CI environment")
            
        # Retry configuration for CI
        if self.env.get("CI"):
            config.retry_runs = 3  # More retries in CI
            logger.info("Increasing retry count for CI environment")
            
    def _generate_env_vars(self, service_status: Dict[str, Any], service_urls: Dict[str, str]) -> Dict[str, Any]:
        """
        Generate environment variables for Cypress tests.
        
        Args:
            service_status: Service status dictionary
            service_urls: Service URLs dictionary
            
        Returns:
            Environment variables dictionary
        """
        env_vars = {}
        
        # Service URLs
        env_vars.update(service_urls)
        
        # API configuration
        if "backend" in service_urls:
            env_vars["API_BASE_URL"] = service_urls["backend"]
            env_vars["API_HEALTH_URL"] = f"{service_urls['backend']}/api/health"
            
        # Database connection info (for tests that need it)
        if service_status.get("postgres", {}).get("healthy"):
            postgres_status = service_status["postgres"]
            env_vars["DATABASE_URL"] = postgres_status.get("url", "")
            
        # Redis connection info
        if service_status.get("redis", {}).get("healthy"):
            redis_status = service_status["redis"]
            env_vars["REDIS_URL"] = redis_status.get("url", "")
            
        # Test environment markers
        env_vars["TEST_ENVIRONMENT"] = "e2e"
        env_vars["CYPRESS_RUN"] = "true"
        
        # Authentication test credentials (if needed)
        env_vars["TEST_USER_EMAIL"] = self.env.get("TEST_USER_EMAIL", "test@netra.ai")
        env_vars["TEST_USER_PASSWORD"] = self.env.get("TEST_USER_PASSWORD", "testpassword123")
        
        # Feature flags for testing
        env_vars["ENABLE_TEST_FEATURES"] = "true"
        
        return env_vars
        
    def _to_cypress_format(self, config: CypressConfig) -> Dict[str, Any]:
        """
        Convert config object to Cypress configuration format.
        
        Args:
            config: Config object
            
        Returns:
            Cypress configuration dictionary
        """
        cypress_config = {
            "config": {
                "baseUrl": config.base_url,
                "defaultCommandTimeout": config.default_command_timeout,
                "pageLoadTimeout": config.page_load_timeout,
                "requestTimeout": config.request_timeout,
                "responseTimeout": config.response_timeout,
                "viewportWidth": config.viewport_width,
                "viewportHeight": config.viewport_height,
                "watchForFileChanges": config.watch_for_file_changes,
                "video": config.video,
                "screenshotOnRunFailure": config.screenshot_on_run_failure,
                "retries": {
                    "runMode": config.retry_runs,
                    "openMode": config.retry_opens
                }
            },
            "env": config.env_vars
        }
        
        return cypress_config
        
    def save_config_file(self, config: Dict[str, Any], filename: str = "cypress.generated.json") -> Path:
        """
        Save generated configuration to file.
        
        Args:
            config: Configuration to save
            filename: Output filename
            
        Returns:
            Path to saved configuration file
        """
        config_path = self.frontend_path / filename
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
            
        logger.info(f"Saved Cypress configuration to: {config_path}")
        return config_path
        
    def get_spec_patterns(self, category: Optional[str] = None) -> List[str]:
        """
        Get spec patterns for different test categories.
        
        Args:
            category: Test category (e.g., 'critical', 'smoke', 'auth')
            
        Returns:
            List of spec patterns
        """
        if not category:
            return ["cypress/e2e/**/*.cy.{js,ts}"]
            
        patterns = {
            "critical": [
                "cypress/e2e/critical-*.cy.{js,ts}",
                "cypress/e2e/critical-tests-index.cy.{js,ts}"
            ],
            "smoke": [
                "cypress/e2e/critical-basic-flow.cy.{js,ts}",
                "cypress/e2e/basic-ui-test.cy.{js,ts}"
            ],
            "auth": [
                "cypress/e2e/auth*.cy.{js,ts}",
                "cypress/e2e/complete-auth-flow.cy.{js,ts}",
                "cypress/e2e/critical-auth-flow.cy.{js,ts}"
            ],
            "chat": [
                "cypress/e2e/chat*.cy.{js,ts}",
                "cypress/e2e/demo-chat-*.cy.{js,ts}"
            ],
            "agent": [
                "cypress/e2e/agent-*.cy.{js,ts}",
                "cypress/e2e/critical-agent-*.cy.{js,ts}"
            ],
            "websocket": [
                "cypress/e2e/*websocket*.cy.{js,ts}",
                "cypress/e2e/critical-websocket-*.cy.{js,ts}"
            ]
        }
        
        return patterns.get(category, [f"cypress/e2e/*{category}*.cy.{{js,ts}}"])