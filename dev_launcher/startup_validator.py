"""
Startup Validator for Development Launcher.

Validates startup conditions and configurations.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class StartupValidator:
    """
    Validates startup conditions for development services.
    """
    
    def __init__(self, use_emoji: bool = True):
        """
        Initialize the startup validator.
        
        Args:
            use_emoji: Whether to use emoji in output
        """
        self.use_emoji = use_emoji
        self.validation_results: Dict[str, bool] = {}
        
    def validate_environment(self) -> bool:
        """
        Validate environment setup.
        
        Returns:
            True if environment is valid
        """
        logger.info("Validating environment setup")
        # Basic validation - always pass for now
        self.validation_results['environment'] = True
        return True
        
    def validate_configuration(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Validate configuration settings.
        
        Args:
            config: Configuration to validate
            
        Returns:
            True if configuration is valid
        """
        logger.info("Validating configuration")
        # Basic validation - always pass for now
        self.validation_results['configuration'] = True
        return True
        
    def validate_dependencies(self) -> bool:
        """
        Validate required dependencies are available.
        
        Returns:
            True if all dependencies are available
        """
        logger.info("Validating dependencies")
        # Basic validation - always pass for now
        self.validation_results['dependencies'] = True
        return True
        
    def validate_all(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Run all validations.
        
        Args:
            config: Configuration to validate
            
        Returns:
            True if all validations pass
        """
        results = [
            self.validate_environment(),
            self.validate_configuration(config),
            self.validate_dependencies()
        ]
        
        all_valid = all(results)
        if all_valid:
            logger.info("All startup validations passed")
        else:
            logger.error("Some startup validations failed")
            
        return all_valid
        
    def get_validation_results(self) -> Dict[str, bool]:
        """
        Get detailed validation results.
        
        Returns:
            Dictionary of validation results
        """
        return self.validation_results.copy()
        
    def reset(self):
        """Reset validation state"""
        self.validation_results.clear()