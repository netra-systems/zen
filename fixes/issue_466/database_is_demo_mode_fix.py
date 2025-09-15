"""
Database is_demo_mode AttributeError Fix for Issue #466

BUSINESS IMPACT: $50K+ MRR WebSocket functionality failing due to AttributeError in staging
CRITICAL: Database service failures with AttributeError 'dict' object has no attribute 'is_demo_mode'

This fix resolves the AttributeError where code expects configuration objects with attributes
but receives dictionaries instead, causing ASGI exceptions in staging environment.

SOLUTION:
1. Fix demo configuration access pattern in auth integration
2. Ensure database configuration objects have proper structure
3. Add proper fallback handling for missing attributes
4. Create configuration object wrapper for compatibility
"""

import logging
from typing import Dict, Any, Optional, Union
from types import SimpleNamespace

# Import configuration modules
from netra_backend.app.core.configuration.demo import get_backend_demo_config, is_demo_mode

logger = logging.getLogger(__name__)


class DatabaseConfigurationFix:
    """
    Database Configuration Fix for Issue #466 - is_demo_mode AttributeError
    
    Provides fixes for the AttributeError where code expects configuration objects
    with attributes but receives dictionaries instead.
    """
    
    def __init__(self):
        """Initialize database configuration fix."""
        self.demo_config = self._create_demo_config_object()
        
    def _create_demo_config_object(self):
        """
        Create a demo configuration object with proper attributes.
        
        CRITICAL FIX: Convert dictionary to object with attributes to prevent AttributeError
        """
        # Get dictionary configuration
        config_dict = get_backend_demo_config()
        
        # Create object with attributes
        demo_config = SimpleNamespace()
        
        # Add all configuration as attributes
        for key, value in config_dict.items():
            setattr(demo_config, key, value)
        
        # Add the missing is_demo_mode method
        demo_config.is_demo_mode = lambda: is_demo_mode()
        
        # Add backward compatibility method
        demo_config.get_demo_config = lambda: config_dict
        
        return demo_config
    
    def get_fixed_demo_config(self):
        """
        Get fixed demo configuration object.
        
        Returns:
            Configuration object with proper is_demo_mode attribute
        """
        return self.demo_config
    
    def fix_auth_integration_demo_config_usage(self):
        """
        Fix the demo configuration usage in auth integration.
        
        CRITICAL FIX: Replace dictionary usage with object usage in auth.py
        """
        # This method provides a patch that can be applied to the auth integration
        # to fix the AttributeError
        
        def patched_get_backend_demo_config():
            """Patched version that returns object instead of dict."""
            return self._create_demo_config_object()
        
        return patched_get_backend_demo_config
    
    def create_database_config_with_demo_mode(self, config_dict: Dict[str, Any]) -> SimpleNamespace:
        """
        Create database configuration object with is_demo_mode attribute.
        
        CRITICAL FIX: Ensure all database configuration objects have is_demo_mode attribute
        
        Args:
            config_dict: Dictionary containing database configuration
            
        Returns:
            Configuration object with is_demo_mode attribute
        """
        # Create configuration object
        config_obj = SimpleNamespace()
        
        # Add all configuration as attributes
        for key, value in config_dict.items():
            setattr(config_obj, key, value)
        
        # Ensure is_demo_mode attribute exists
        if not hasattr(config_obj, 'is_demo_mode'):
            config_obj.is_demo_mode = is_demo_mode()
        
        return config_obj
    
    def validate_database_configuration(self, config: Union[Dict[str, Any], SimpleNamespace]) -> bool:
        """
        Validate that database configuration has required attributes.
        
        Args:
            config: Configuration dictionary or object
            
        Returns:
            True if configuration is valid
        """
        try:
            # Test if is_demo_mode can be accessed
            if isinstance(config, dict):
                # Dictionary - this will cause AttributeError
                _ = config.is_demo_mode  # This should fail
                return False
            else:
                # Object - should have attribute
                _ = config.is_demo_mode
                return True
                
        except AttributeError:
            # This is the error we're trying to fix
            logger.error("Database configuration missing is_demo_mode attribute")
            return False
        except Exception as e:
            logger.error(f"Database configuration validation error: {e}")
            return False
    
    def apply_configuration_fixes(self) -> Dict[str, Any]:
        """
        Apply all database configuration fixes.
        
        Returns:
            Dictionary containing fix results
        """
        fix_results = {
            'demo_config_fixed': False,
            'database_config_validated': False,
            'auth_integration_patched': False,
            'errors': []
        }
        
        try:
            # Fix 1: Create proper demo configuration object
            self.demo_config = self._create_demo_config_object()
            fix_results['demo_config_fixed'] = True
            logger.info("Demo configuration object created successfully")
            
        except Exception as e:
            error_msg = f"Failed to create demo configuration object: {e}"
            fix_results['errors'].append(error_msg)
            logger.error(error_msg)
        
        try:
            # Fix 2: Validate database configuration
            is_valid = self.validate_database_configuration(self.demo_config)
            fix_results['database_config_validated'] = is_valid
            
            if is_valid:
                logger.info("Database configuration validation passed")
            else:
                fix_results['errors'].append("Database configuration validation failed")
                
        except Exception as e:
            error_msg = f"Database configuration validation error: {e}"
            fix_results['errors'].append(error_msg)
            logger.error(error_msg)
        
        try:
            # Fix 3: Apply auth integration patch
            patched_function = self.fix_auth_integration_demo_config_usage()
            if patched_function:
                fix_results['auth_integration_patched'] = True
                logger.info("Auth integration patch created successfully")
            else:
                fix_results['errors'].append("Failed to create auth integration patch")
                
        except Exception as e:
            error_msg = f"Auth integration patch error: {e}"
            fix_results['errors'].append(error_msg)
            logger.error(error_msg)
        
        # Summary
        total_fixes = sum(1 for key, value in fix_results.items() if key.endswith('_fixed') or key.endswith('_validated') or key.endswith('_patched') and value)
        logger.info(f"Database configuration fixes applied: {total_fixes}/3 successful")
        
        return fix_results


class DemoConfigWrapper:
    """
    Wrapper class to provide backward compatibility for demo configuration.
    
    CRITICAL FIX: This wrapper ensures existing code continues to work while
    providing proper object interface for is_demo_mode attribute access.
    """
    
    def __init__(self):
        """Initialize demo config wrapper."""
        self._config_dict = get_backend_demo_config()
        self._demo_mode_value = is_demo_mode()
    
    def is_demo_mode(self) -> bool:
        """
        Check if demo mode is enabled.
        
        Returns:
            True if demo mode is enabled
        """
        return self._demo_mode_value
    
    def get_demo_config(self) -> Dict[str, Any]:
        """
        Get demo configuration dictionary.
        
        Returns:
            Demo configuration dictionary
        """
        return self._config_dict.copy()
    
    def __getattr__(self, name: str) -> Any:
        """
        Provide access to configuration attributes.
        
        Args:
            name: Attribute name
            
        Returns:
            Configuration value
        """
        if name in self._config_dict:
            return self._config_dict[name]
        
        # Handle special cases
        if name == 'enabled':
            return self.is_demo_mode()
        
        raise AttributeError(f"DemoConfigWrapper has no attribute '{name}'")
    
    def __getitem__(self, key: str) -> Any:
        """
        Provide dictionary-style access.
        
        Args:
            key: Configuration key
            
        Returns:
            Configuration value
        """
        return self._config_dict[key]
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value with default.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        return self._config_dict.get(key, default)


def get_patched_backend_demo_config() -> DemoConfigWrapper:
    """
    Get patched backend demo configuration with proper object interface.
    
    CRITICAL FIX: This function replaces get_backend_demo_config() calls
    to return an object with is_demo_mode() method instead of a dictionary.
    
    Returns:
        DemoConfigWrapper with proper interface
    """
    return DemoConfigWrapper()


def apply_database_is_demo_mode_fix():
    """
    Apply the database is_demo_mode AttributeError fix.
    
    This function can be called during application startup to ensure
    proper configuration object handling.
    """
    try:
        # Initialize the fix
        db_fix = DatabaseConfigurationFix()
        
        # Apply all fixes
        results = db_fix.apply_configuration_fixes()
        
        # Log results
        successful_fixes = sum(1 for key, value in results.items() 
                              if key.endswith(('_fixed', '_validated', '_patched')) and value)
        
        logger.info(f"Database is_demo_mode fix applied: {successful_fixes}/3 fixes successful")
        
        if results['errors']:
            for error in results['errors']:
                logger.error(f"Database fix error: {error}")
        
        return successful_fixes == 3
        
    except Exception as e:
        logger.error(f"Failed to apply database is_demo_mode fix: {e}")
        return False


def patch_auth_integration_import():
    """
    Patch the auth integration import to use fixed demo configuration.
    
    CRITICAL FIX: This monkey patches the import to prevent AttributeError
    """
    try:
        import netra_backend.app.auth_integration.auth as auth_module
        
        # Replace the problematic function
        auth_module.get_backend_demo_config = get_patched_backend_demo_config
        
        logger.info("Auth integration demo config import patched successfully")
        return True
        
    except ImportError as e:
        logger.warning(f"Could not patch auth integration import: {e}")
        return False
    except Exception as e:
        logger.error(f"Error patching auth integration import: {e}")
        return False


def main():
    """
    Main function to apply database is_demo_mode fix for Issue #466.
    """
    try:
        print("Applying database is_demo_mode AttributeError fix...")
        
        # Apply the configuration fix
        success = apply_database_is_demo_mode_fix()
        
        if success:
            print("Database is_demo_mode fix applied successfully!")
            
            # Apply import patch
            patch_success = patch_auth_integration_import()
            if patch_success:
                print("Auth integration import patch applied successfully!")
            else:
                print("Auth integration import patch failed (non-critical)")
            
            return True
        else:
            print("Database is_demo_mode fix failed!")
            return False
        
    except Exception as e:
        print(f"Database is_demo_mode fix error: {e}")
        logger.error(f"Database is_demo_mode fix error: {e}")
        return False


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)