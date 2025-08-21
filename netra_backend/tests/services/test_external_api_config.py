"""Tests for ExternalAPIConfig configurations."""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest

# Add project root to path
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Add project root to path

from netra_backend.app.services.external_api_client import ExternalAPIConfig

# Add project root to path


class TestExternalAPIConfig:
    """Test ExternalAPIConfig configurations."""
    
    def test_google_api_config(self):
        """Test Google API configuration."""
        config = ExternalAPIConfig.GOOGLE_API_CONFIG
        self._verify_google_config(config)
    
    def _verify_google_config(self, config):
        """Verify Google API config values."""
        assert config.name == "google_api"
        assert config.failure_threshold == 3
        assert config.recovery_timeout == 30.0
        assert config.timeout_seconds == 10.0
    
    def test_openai_api_config(self):
        """Test OpenAI API configuration."""
        config = ExternalAPIConfig.OPENAI_API_CONFIG
        self._verify_openai_config(config)
    
    def _verify_openai_config(self, config):
        """Verify OpenAI API config values."""
        assert config.name == "openai_api"
        assert config.failure_threshold == 5
        assert config.recovery_timeout == 20.0
        assert config.timeout_seconds == 15.0
    
    def test_anthropic_api_config(self):
        """Test Anthropic API configuration."""
        config = ExternalAPIConfig.ANTHROPIC_API_CONFIG
        self._verify_anthropic_config(config)
    
    def _verify_anthropic_config(self, config):
        """Verify Anthropic API config values."""
        assert config.name == "anthropic_api"
        assert config.failure_threshold == 5
        assert config.recovery_timeout == 20.0
        assert config.timeout_seconds == 15.0
    
    def test_generic_api_config(self):
        """Test generic API configuration."""
        config = ExternalAPIConfig.GENERIC_API_CONFIG
        self._verify_generic_config(config)
    
    def _verify_generic_config(self, config):
        """Verify generic API config values."""
        assert config.name == "external_api"
        assert config.failure_threshold == 3
        assert config.recovery_timeout == 30.0
        assert config.timeout_seconds == 10.0
    
    def test_fast_api_config(self):
        """Test fast API configuration."""
        config = ExternalAPIConfig.FAST_API_CONFIG
        self._verify_fast_config(config)
    
    def _verify_fast_config(self, config):
        """Verify fast API config values."""
        assert config.name == "fast_api"
        assert config.failure_threshold == 2
        assert config.recovery_timeout == 10.0
        assert config.timeout_seconds == 3.0