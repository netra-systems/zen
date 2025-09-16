"""Cypress configuration manager for E2E testing.

This module manages Cypress test configuration, including environment setup,
test data, and browser configuration for E2E tests.
"""

import json
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any


logger = logging.getLogger(__name__)


class CypressConfigManager:
    """Manages Cypress test configuration."""
    
    def __init__(self, project_root: Optional[Path] = None):
        """Initialize Cypress config manager.
        
        Args:
            project_root: Optional project root path
        """
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self.cypress_dir = self.project_root / "cypress"
        self.config = self._load_default_config()
        self.environment_config = self._load_environment_config()
    
    def _load_default_config(self) -> Dict:
        """Load default Cypress configuration.
        
        Returns:
            Default configuration dictionary
        """
        return {
            "baseUrl": os.getenv("CYPRESS_BASE_URL", "http://localhost:3000"),
            "viewportWidth": int(os.getenv("CYPRESS_VIEWPORT_WIDTH", "1280")),
            "viewportHeight": int(os.getenv("CYPRESS_VIEWPORT_HEIGHT", "720")),
            "video": os.getenv("CYPRESS_VIDEO", "false").lower() == "true",
            "screenshotOnRunFailure": True,
            "defaultCommandTimeout": int(os.getenv("CYPRESS_COMMAND_TIMEOUT", "10000")),
            "pageLoadTimeout": int(os.getenv("CYPRESS_PAGE_LOAD_TIMEOUT", "30000")),
            "requestTimeout": int(os.getenv("CYPRESS_REQUEST_TIMEOUT", "5000")),
            "responseTimeout": int(os.getenv("CYPRESS_RESPONSE_TIMEOUT", "30000")),
            "retries": {
                "runMode": int(os.getenv("CYPRESS_RUN_RETRIES", "2")),
                "openMode": int(os.getenv("CYPRESS_OPEN_RETRIES", "0"))
            },
            "e2e": {
                "setupNodeEvents": None,
                "specPattern": "cypress/e2e/**/*.cy.{js,jsx,ts,tsx}",
                "supportFile": "cypress/support/e2e.{js,jsx,ts,tsx}"
            },
            "env": {}
        }
    
    def _load_environment_config(self) -> Dict:
        """Load environment-specific configuration.
        
        Returns:
            Environment configuration dictionary
        """
        env_config = {
            "ENVIRONMENT": os.getenv("ENVIRONMENT", "local"),
            "API_BASE_URL": os.getenv("API_BASE_URL", "http://localhost:8000"),
            "AUTH_BASE_URL": os.getenv("AUTH_BASE_URL", "http://localhost:8081"),
            "WEBSOCKET_URL": os.getenv("WEBSOCKET_URL", "ws://localhost:8000/ws"),
        }
        
        # Add test user credentials (for test environment only)
        if env_config["ENVIRONMENT"] in ["local", "test", "development"]:
            env_config.update({
                "TEST_USER_EMAIL": os.getenv("TEST_USER_EMAIL", "test@netrasystems.ai"),
                "TEST_USER_PASSWORD": os.getenv("TEST_USER_PASSWORD", "testpassword"),
                "ADMIN_USER_EMAIL": os.getenv("ADMIN_USER_EMAIL", "admin@netrasystems.ai"),
                "ADMIN_USER_PASSWORD": os.getenv("ADMIN_USER_PASSWORD", "adminpassword"),
            })
        
        return env_config
    
    def get_config(self) -> Dict:
        """Get complete Cypress configuration.
        
        Returns:
            Complete configuration dictionary
        """
        config = self.config.copy()
        config["env"].update(self.environment_config)
        return config
    
    def get_environment_variables(self) -> Dict:
        """Get environment variables for Cypress.
        
        Returns:
            Environment variables dictionary
        """
        return self.environment_config.copy()
    
    def update_config(self, updates: Dict):
        """Update configuration with new values.
        
        Args:
            updates: Dictionary of configuration updates
        """
        self.config.update(updates)
    
    def set_base_url(self, url: str):
        """Set base URL for Cypress tests.
        
        Args:
            url: Base URL to set
        """
        self.config["baseUrl"] = url
        self.environment_config["BASE_URL"] = url
    
    def set_api_base_url(self, url: str):
        """Set API base URL for tests.
        
        Args:
            url: API base URL to set
        """
        self.environment_config["API_BASE_URL"] = url
    
    def enable_video_recording(self, enabled: bool = True):
        """Enable or disable video recording.
        
        Args:
            enabled: Whether to enable video recording
        """
        self.config["video"] = enabled
    
    def set_viewport(self, width: int, height: int):
        """Set viewport dimensions.
        
        Args:
            width: Viewport width
            height: Viewport height
        """
        self.config["viewportWidth"] = width
        self.config["viewportHeight"] = height
    
    def set_timeouts(self, command: Optional[int] = None, page_load: Optional[int] = None, 
                    request: Optional[int] = None, response: Optional[int] = None):
        """Set various timeout values.
        
        Args:
            command: Default command timeout in ms
            page_load: Page load timeout in ms
            request: Request timeout in ms
            response: Response timeout in ms
        """
        if command is not None:
            self.config["defaultCommandTimeout"] = command
        if page_load is not None:
            self.config["pageLoadTimeout"] = page_load
        if request is not None:
            self.config["requestTimeout"] = request
        if response is not None:
            self.config["responseTimeout"] = response
    
    def set_retry_count(self, run_mode: int = 2, open_mode: int = 0):
        """Set retry counts for different modes.
        
        Args:
            run_mode: Retries for run mode
            open_mode: Retries for open mode
        """
        self.config["retries"] = {
            "runMode": run_mode,
            "openMode": open_mode
        }
    
    def add_environment_variable(self, key: str, value: str):
        """Add environment variable.
        
        Args:
            key: Environment variable key
            value: Environment variable value
        """
        self.environment_config[key] = value
    
    def write_cypress_config(self) -> Path:
        """Write Cypress configuration to file.
        
        Returns:
            Path to written configuration file
        """
        config_path = self.project_root / "cypress.config.js"
        
        # Generate JS config file content
        config = self.get_config()
        
        js_content = f"""const {{ defineConfig }} = require('cypress');

module.exports = defineConfig({{
  e2e: {{
    baseUrl: '{config["baseUrl"]}',
    viewportWidth: {config["viewportWidth"]},
    viewportHeight: {config["viewportHeight"]},
    video: {str(config["video"]).lower()},
    screenshotOnRunFailure: {str(config["screenshotOnRunFailure"]).lower()},
    defaultCommandTimeout: {config["defaultCommandTimeout"]},
    pageLoadTimeout: {config["pageLoadTimeout"]},
    requestTimeout: {config["requestTimeout"]},
    responseTimeout: {config["responseTimeout"]},
    retries: {{
      runMode: {config["retries"]["runMode"]},
      openMode: {config["retries"]["openMode"]}
    }},
    specPattern: '{config["e2e"]["specPattern"]}',
    supportFile: '{config["e2e"]["supportFile"]}',
    setupNodeEvents(on, config) {{
      // implement node event listeners here
    }},
  }},
  env: {json.dumps(config["env"], indent=4)}
}});
"""
        
        with open(config_path, 'w') as f:
            f.write(js_content)
        
        logger.info(f"Wrote Cypress configuration to {config_path}")
        return config_path
    
    def write_env_file(self) -> Path:
        """Write environment variables to cypress.env.json.
        
        Returns:
            Path to written environment file
        """
        env_path = self.project_root / "cypress.env.json"
        
        with open(env_path, 'w') as f:
            json.dump(self.environment_config, f, indent=2)
        
        logger.info(f"Wrote Cypress environment to {env_path}")
        return env_path
    
    def get_spec_files(self, pattern: Optional[str] = None) -> List[Path]:
        """Get list of Cypress spec files.
        
        Args:
            pattern: Optional glob pattern to filter specs
            
        Returns:
            List of spec file paths
        """
        cypress_e2e = self.cypress_dir / "e2e"
        if not cypress_e2e.exists():
            return []
        
        if pattern:
            return list(cypress_e2e.glob(pattern))
        else:
            # Default patterns
            patterns = ["**/*.cy.js", "**/*.cy.jsx", "**/*.cy.ts", "**/*.cy.tsx"]
            spec_files = []
            for pattern in patterns:
                spec_files.extend(cypress_e2e.glob(pattern))
            return spec_files
    
    def validate_config(self) -> List[str]:
        """Validate Cypress configuration.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check required directories
        required_dirs = ["cypress", "cypress/e2e", "cypress/support"]
        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            if not dir_path.exists():
                errors.append(f"Required directory missing: {dir_path}")
        
        # Check base URL is accessible
        base_url = self.config.get("baseUrl")
        if not base_url:
            errors.append("baseUrl is not configured")
        
        # Check timeout values are reasonable
        timeouts = ["defaultCommandTimeout", "pageLoadTimeout", "requestTimeout", "responseTimeout"]
        for timeout_name in timeouts:
            timeout_value = self.config.get(timeout_name, 0)
            if timeout_value < 1000:  # Less than 1 second
                errors.append(f"{timeout_name} is too low: {timeout_value}ms")
            elif timeout_value > 300000:  # More than 5 minutes
                errors.append(f"{timeout_name} is too high: {timeout_value}ms")
        
        return errors