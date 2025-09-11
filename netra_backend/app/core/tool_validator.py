"""Tool Validator - Enhanced diagnostics and validation for tool operations.

This module provides comprehensive validation capabilities for tool registration,
execution, and management operations with detailed diagnostics and error context.

Business Value:
- Provides detailed validation diagnostics for faster issue resolution
- Enables proactive identification of tool configuration problems
- Supports comprehensive error context for debugging and monitoring
- Enhances developer experience with clear validation messages
- Reduces time to resolution for tool-related issues

Related to Issue #390: Tool Registration Exception Handling Improvements
"""

from typing import Any, Dict, List, Optional, Tuple, Type, Union, Callable
from datetime import datetime, timezone
import inspect
import sys
from pathlib import Path

from netra_backend.app.core.exceptions_tools import (
    ToolTypeValidationException,
    ToolNameValidationException,
    ToolHandlerValidationException,
    ToolDependencyException,
    ToolCategoryException
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ToolValidator:
    """Comprehensive validator for tool operations with enhanced diagnostics.
    
    This class provides detailed validation for all tool-related operations,
    offering rich error context and structured diagnostic information.
    """
    
    def __init__(self):
        """Initialize tool validator with default configuration."""
        self.valid_categories = {
            "analysis", "optimization", "monitoring", "reporting", 
            "data_management", "system", "testing", "default"
        }
        
        # Version requirements for common dependencies
        self.dependency_versions = {
            "numpy": {"min": "1.20.0", "max": "2.0.0"},
            "pandas": {"min": "1.3.0", "max": "3.0.0"},
            "sklearn": {"min": "1.0.0", "max": "2.0.0"},
            "requests": {"min": "2.25.0", "max": "3.0.0"}
        }
        
        logger.debug("ToolValidator initialized")
    
    def validate_tool_type(self, 
                          tool: Any, 
                          expected_types: Optional[List[Type]] = None,
                          tool_id: Optional[str] = None,
                          user_id: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validate tool type with detailed diagnostics.
        
        Args:
            tool: Tool instance to validate
            expected_types: List of expected types (defaults to common tool types)
            tool_id: Tool ID for context
            user_id: User ID for context
            
        Returns:
            Tuple of (is_valid, diagnostic_info)
            
        Raises:
            ToolTypeValidationException: If validation fails and exceptions enabled
        """
        diagnostic_info = {
            'validation_type': 'tool_type',
            'tool_id': tool_id,
            'user_id': user_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'actual_type': type(tool).__name__,
            'actual_module': getattr(type(tool), '__module__', 'unknown'),
            'has_required_methods': {},
            'inheritance_chain': [cls.__name__ for cls in type(tool).__mro__]
        }
        
        # Set default expected types if not provided
        if expected_types is None:
            try:
                from netra_backend.app.services.unified_tool_registry.models import UnifiedTool
                from langchain_core.tools import BaseTool
                expected_types = [UnifiedTool, BaseTool]
            except ImportError:
                expected_types = []
        
        # Check if tool matches expected types
        is_valid_type = False
        expected_type_names = []
        
        for expected_type in expected_types:
            expected_type_names.append(expected_type.__name__)
            if isinstance(tool, expected_type):
                is_valid_type = True
                break
        
        diagnostic_info['expected_types'] = expected_type_names
        diagnostic_info['matches_expected_type'] = is_valid_type
        
        # Check for required methods/attributes
        required_methods = ['name', '__call__', 'run', '_run', 'execute']
        for method in required_methods:
            has_method = hasattr(tool, method)
            is_callable = callable(getattr(tool, method, None)) if has_method else False
            diagnostic_info['has_required_methods'][method] = {
                'exists': has_method,
                'callable': is_callable
            }
        
        # Check for common tool patterns
        diagnostic_info['has_name_attribute'] = hasattr(tool, 'name')
        diagnostic_info['has_description'] = hasattr(tool, 'description')
        diagnostic_info['name_value'] = getattr(tool, 'name', None)
        diagnostic_info['description_value'] = getattr(tool, 'description', None)
        
        if not is_valid_type:
            logger.warning(f"Tool type validation failed for {tool_id}: {diagnostic_info}")
            return False, diagnostic_info
        
        logger.debug(f"Tool type validation passed for {tool_id}")
        return True, diagnostic_info
    
    def validate_tool_name(self, 
                          name: Any, 
                          tool_id: Optional[str] = None,
                          user_id: Optional[str] = None,
                          existing_names: Optional[List[str]] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validate tool name with comprehensive diagnostics.
        
        Args:
            name: Tool name to validate
            tool_id: Tool ID for context
            user_id: User ID for context
            existing_names: List of existing names to check for conflicts
            
        Returns:
            Tuple of (is_valid, diagnostic_info)
        """
        diagnostic_info = {
            'validation_type': 'tool_name',
            'tool_id': tool_id,
            'user_id': user_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'name_value': name,
            'name_type': type(name).__name__,
            'validation_rules': {},
            'suggestions': []
        }
        
        is_valid = True
        validation_issues = []
        
        # Rule 1: Name must be a string
        if not isinstance(name, str):
            is_valid = False
            validation_issues.append("name_not_string")
            diagnostic_info['validation_rules']['is_string'] = False
        else:
            diagnostic_info['validation_rules']['is_string'] = True
            
            # Rule 2: Name must not be empty
            if not name or not name.strip():
                is_valid = False
                validation_issues.append("name_empty")
                diagnostic_info['validation_rules']['not_empty'] = False
            else:
                diagnostic_info['validation_rules']['not_empty'] = True
                
                # Rule 3: Name length restrictions
                if len(name) > 100:
                    is_valid = False
                    validation_issues.append("name_too_long")
                    diagnostic_info['validation_rules']['length_valid'] = False
                else:
                    diagnostic_info['validation_rules']['length_valid'] = True
                
                # Rule 4: Name character restrictions
                invalid_chars = set(name) - set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.')
                if invalid_chars:
                    is_valid = False
                    validation_issues.append("invalid_characters")
                    diagnostic_info['validation_rules']['valid_characters'] = False
                    diagnostic_info['invalid_characters'] = list(invalid_chars)
                else:
                    diagnostic_info['validation_rules']['valid_characters'] = True
                
                # Rule 5: Check for conflicts with existing names
                if existing_names and name in existing_names:
                    is_valid = False
                    validation_issues.append("name_conflict")
                    diagnostic_info['validation_rules']['no_conflict'] = False
                    diagnostic_info['existing_names'] = existing_names
                    
                    # Generate suggestions for alternative names
                    base_name = name.rstrip('0123456789')
                    for i in range(1, 10):
                        suggestion = f"{base_name}_{i}"
                        if suggestion not in existing_names:
                            diagnostic_info['suggestions'].append(suggestion)
                            break
                else:
                    diagnostic_info['validation_rules']['no_conflict'] = True
        
        diagnostic_info['validation_issues'] = validation_issues
        diagnostic_info['is_valid'] = is_valid
        
        if not is_valid:
            logger.warning(f"Tool name validation failed for {tool_id}: {validation_issues}")
            return False, diagnostic_info
        
        logger.debug(f"Tool name validation passed for {tool_id}")
        return True, diagnostic_info
    
    def validate_tool_handler(self, 
                             handler: Any, 
                             tool_id: Optional[str] = None,
                             user_id: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validate tool handler with detailed signature analysis.
        
        Args:
            handler: Handler function/method to validate
            tool_id: Tool ID for context
            user_id: User ID for context
            
        Returns:
            Tuple of (is_valid, diagnostic_info)
        """
        diagnostic_info = {
            'validation_type': 'tool_handler',
            'tool_id': tool_id,
            'user_id': user_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'handler_type': type(handler).__name__,
            'is_callable': callable(handler),
            'signature_info': {},
            'validation_issues': []
        }
        
        is_valid = True
        
        # Rule 1: Handler must be callable
        if not callable(handler):
            is_valid = False
            diagnostic_info['validation_issues'].append("not_callable")
        else:
            # Analyze handler signature
            try:
                sig = inspect.signature(handler)
                diagnostic_info['signature_info'] = {
                    'parameter_count': len(sig.parameters),
                    'parameters': {},
                    'has_return_annotation': sig.return_annotation != inspect.Signature.empty,
                    'return_annotation': str(sig.return_annotation) if sig.return_annotation != inspect.Signature.empty else None
                }
                
                # Analyze parameters
                for param_name, param in sig.parameters.items():
                    param_info = {
                        'kind': str(param.kind),
                        'has_default': param.default != inspect.Parameter.empty,
                        'default_value': str(param.default) if param.default != inspect.Parameter.empty else None,
                        'has_annotation': param.annotation != inspect.Parameter.empty,
                        'annotation': str(param.annotation) if param.annotation != inspect.Parameter.empty else None
                    }
                    diagnostic_info['signature_info']['parameters'][param_name] = param_info
                
                # Check for async handler
                diagnostic_info['is_async'] = inspect.iscoroutinefunction(handler)
                
            except Exception as e:
                diagnostic_info['signature_analysis_error'] = str(e)
                logger.warning(f"Failed to analyze handler signature for {tool_id}: {e}")
        
        diagnostic_info['is_valid'] = is_valid
        
        if not is_valid:
            logger.warning(f"Tool handler validation failed for {tool_id}: {diagnostic_info['validation_issues']}")
            return False, diagnostic_info
        
        logger.debug(f"Tool handler validation passed for {tool_id}")
        return True, diagnostic_info
    
    def validate_tool_dependencies(self, 
                                  dependencies: List[str],
                                  tool_id: Optional[str] = None,
                                  user_id: Optional[str] = None,
                                  check_versions: bool = True) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validate tool dependencies with version checking.
        
        Args:
            dependencies: List of dependency names
            tool_id: Tool ID for context
            user_id: User ID for context
            check_versions: Whether to check version compatibility
            
        Returns:
            Tuple of (is_valid, diagnostic_info)
        """
        diagnostic_info = {
            'validation_type': 'tool_dependencies',
            'tool_id': tool_id,
            'user_id': user_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'dependency_status': {},
            'missing_dependencies': [],
            'version_conflicts': [],
            'satisfied_dependencies': []
        }
        
        all_satisfied = True
        
        for dep in dependencies:
            dep_info = {
                'name': dep,
                'available': False,
                'version': None,
                'version_compatible': None,
                'import_error': None
            }
            
            # Try to import dependency
            try:
                imported_module = __import__(dep)
                dep_info['available'] = True
                
                # Try to get version
                version = getattr(imported_module, '__version__', None)
                if version:
                    dep_info['version'] = version
                    
                    # Check version compatibility if enabled
                    if check_versions and dep in self.dependency_versions:
                        version_req = self.dependency_versions[dep]
                        dep_info['version_requirements'] = version_req
                        
                        # Simple version comparison (would need proper version parsing in production)
                        try:
                            from packaging import version as pkg_version
                            current_version = pkg_version.parse(version)
                            min_version = pkg_version.parse(version_req['min'])
                            max_version = pkg_version.parse(version_req['max'])
                            
                            if min_version <= current_version < max_version:
                                dep_info['version_compatible'] = True
                                diagnostic_info['satisfied_dependencies'].append(dep)
                            else:
                                dep_info['version_compatible'] = False
                                diagnostic_info['version_conflicts'].append({
                                    'dependency': dep,
                                    'current_version': version,
                                    'required_range': f"{version_req['min']} - {version_req['max']}"
                                })
                                all_satisfied = False
                        except ImportError:
                            # packaging not available, assume compatible
                            dep_info['version_compatible'] = True
                            diagnostic_info['satisfied_dependencies'].append(dep)
                else:
                    # No version info, assume compatible
                    dep_info['version_compatible'] = True
                    diagnostic_info['satisfied_dependencies'].append(dep)
                    
            except ImportError as e:
                dep_info['available'] = False
                dep_info['import_error'] = str(e)
                diagnostic_info['missing_dependencies'].append(dep)
                all_satisfied = False
            
            diagnostic_info['dependency_status'][dep] = dep_info
        
        diagnostic_info['all_satisfied'] = all_satisfied
        diagnostic_info['missing_count'] = len(diagnostic_info['missing_dependencies'])
        diagnostic_info['conflict_count'] = len(diagnostic_info['version_conflicts'])
        
        if not all_satisfied:
            logger.warning(f"Tool dependency validation failed for {tool_id}: "
                         f"{diagnostic_info['missing_count']} missing, "
                         f"{diagnostic_info['conflict_count']} conflicts")
            return False, diagnostic_info
        
        logger.debug(f"Tool dependency validation passed for {tool_id}")
        return True, diagnostic_info
    
    def validate_tool_category(self, 
                              category: str,
                              tool_id: Optional[str] = None,
                              user_id: Optional[str] = None,
                              custom_categories: Optional[List[str]] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validate tool category with suggestions.
        
        Args:
            category: Category to validate
            tool_id: Tool ID for context
            user_id: User ID for context
            custom_categories: Additional valid categories
            
        Returns:
            Tuple of (is_valid, diagnostic_info)
        """
        diagnostic_info = {
            'validation_type': 'tool_category',
            'tool_id': tool_id,
            'user_id': user_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'category': category,
            'valid_categories': list(self.valid_categories),
            'suggestions': []
        }
        
        # Include custom categories if provided
        valid_categories = self.valid_categories.copy()
        if custom_categories:
            valid_categories.update(custom_categories)
            diagnostic_info['custom_categories'] = custom_categories
        
        is_valid = category in valid_categories
        diagnostic_info['is_valid'] = is_valid
        
        if not is_valid:
            # Generate suggestions based on similarity
            suggestions = []
            category_lower = category.lower()
            
            for valid_cat in valid_categories:
                # Simple similarity check
                if category_lower in valid_cat.lower() or valid_cat.lower() in category_lower:
                    suggestions.append(valid_cat)
            
            # If no similar categories found, suggest most common ones
            if not suggestions:
                suggestions = ['analysis', 'optimization', 'system', 'default']
            
            diagnostic_info['suggestions'] = suggestions[:3]  # Top 3 suggestions
            
            logger.warning(f"Tool category validation failed for {tool_id}: '{category}' not in valid categories")
            return False, diagnostic_info
        
        logger.debug(f"Tool category validation passed for {tool_id}")
        return True, diagnostic_info
    
    def generate_validation_report(self, 
                                  tool: Any,
                                  handler: Optional[Callable] = None,
                                  dependencies: Optional[List[str]] = None,
                                  tool_id: Optional[str] = None,
                                  user_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate comprehensive validation report for a tool.
        
        Args:
            tool: Tool to validate
            handler: Optional handler to validate
            dependencies: Optional dependencies to validate
            tool_id: Tool ID for context
            user_id: User ID for context
            
        Returns:
            Comprehensive validation report
        """
        report = {
            'tool_id': tool_id,
            'user_id': user_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'overall_valid': True,
            'validation_summary': {},
            'detailed_results': {}
        }
        
        # Validate tool type
        type_valid, type_info = self.validate_tool_type(tool, tool_id=tool_id, user_id=user_id)
        report['validation_summary']['type'] = type_valid
        report['detailed_results']['type'] = type_info
        if not type_valid:
            report['overall_valid'] = False
        
        # Validate tool name
        tool_name = getattr(tool, 'name', None)
        name_valid, name_info = self.validate_tool_name(tool_name, tool_id=tool_id, user_id=user_id)
        report['validation_summary']['name'] = name_valid
        report['detailed_results']['name'] = name_info
        if not name_valid:
            report['overall_valid'] = False
        
        # Validate handler if provided
        if handler is not None:
            handler_valid, handler_info = self.validate_tool_handler(handler, tool_id=tool_id, user_id=user_id)
            report['validation_summary']['handler'] = handler_valid
            report['detailed_results']['handler'] = handler_info
            if not handler_valid:
                report['overall_valid'] = False
        
        # Validate dependencies if provided
        if dependencies:
            deps_valid, deps_info = self.validate_tool_dependencies(dependencies, tool_id=tool_id, user_id=user_id)
            report['validation_summary']['dependencies'] = deps_valid
            report['detailed_results']['dependencies'] = deps_info
            if not deps_valid:
                report['overall_valid'] = False
        
        # Validate category
        category = getattr(tool, 'category', 'default')
        cat_valid, cat_info = self.validate_tool_category(category, tool_id=tool_id, user_id=user_id)
        report['validation_summary']['category'] = cat_valid
        report['detailed_results']['category'] = cat_info
        if not cat_valid:
            report['overall_valid'] = False
        
        logger.info(f"Generated validation report for {tool_id}: overall_valid={report['overall_valid']}")
        return report


# Export main validator class
__all__ = ['ToolValidator']