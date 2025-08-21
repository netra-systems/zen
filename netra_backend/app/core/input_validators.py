"""
Core input validation classes and functionality.
Provides comprehensive input validation with threat detection.
"""

import urllib.parse
from typing import Dict, List, Any, Optional

from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.exceptions_auth import NetraSecurityException
from netra_backend.app.schemas.shared_types import ValidationResult as BaseValidationResult

from netra_backend.app.core.validation_rules import (
    ValidationLevel, SecurityThreat, PatternCompiler, ValidationConstraints, ThreatDetector
)
from netra_backend.app.core.input_sanitizers import (
    InputNormalizer, InputSanitizer, EncodingAnalyzer, SecurityValidator, ContentTypeValidator
)

logger = central_logger.get_logger(__name__)


class SecurityValidationResult(BaseValidationResult):
    """Extended validation result for security-specific validation."""
    threats_detected: List[str] = []
    from_cache: bool = False


class EnhancedInputValidator:
    """Comprehensive input validator with threat detection."""
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.MODERATE):
        self.validation_level = validation_level
        self.constraints = ValidationConstraints(validation_level)
        self.enable_caching = False
        self.custom_rules = {}
        self._cache = {}
        self._initialize_components()
    
    def _initialize_components(self) -> None:
        """Initialize validator components."""
        pattern_compiler = PatternCompiler()
        compiled_patterns = pattern_compiler.compile_all_patterns()
        
        self.threat_detector = ThreatDetector(compiled_patterns)
        self.normalizer = InputNormalizer()
        self.sanitizer = InputSanitizer(self.constraints.suspicious_chars)
        self.encoding_analyzer = EncodingAnalyzer(self.constraints.suspicious_chars)
        self.security_validator = SecurityValidator()
        self.content_validator = ContentTypeValidator(self.security_validator)
    
    def validate_input(self, input_value: str, field_name: str = "input",
                      context: Optional[Dict[str, Any]] = None) -> SecurityValidationResult:
        """Comprehensive input validation."""
        try:
            if not input_value:
                return self._create_empty_input_result()
            return self._validate_with_caching(input_value, field_name, context)
        except Exception as e:
            return self._create_error_result(field_name, e)

    def _validate_with_caching(self, input_value: str, field_name: str,
                              context: Optional[Dict[str, Any]]) -> SecurityValidationResult:
        """Validate input with caching support."""
        cached_result = self._check_validation_cache(input_value, field_name, context)
        if cached_result:
            return cached_result
        result = self._perform_comprehensive_validation(input_value, field_name, context)
        result.from_cache = False
        self._store_validation_cache(input_value, field_name, context, result)
        return result

    def _check_validation_cache(self, input_value: str, field_name: str,
                               context: Optional[Dict[str, Any]]) -> Optional[SecurityValidationResult]:
        """Check cache for existing validation result."""
        if not self.enable_caching:
            return None
        cache_key = f"{input_value}:{field_name}:{context}"
        if cache_key not in self._cache:
            return None
        return self._create_cached_result_copy(self._cache[cache_key])

    def _create_cached_result_copy(self, cached_result: SecurityValidationResult) -> SecurityValidationResult:
        """Create a copy of cached result to avoid modification."""
        return SecurityValidationResult(
            is_valid=cached_result.is_valid,
            errors=cached_result.errors.copy(),
            warnings=cached_result.warnings.copy(),
            sanitized_value=cached_result.sanitized_value,
            confidence_score=cached_result.confidence_score,
            threats_detected=cached_result.threats_detected.copy(),
            from_cache=True
        )

    def _store_validation_cache(self, input_value: str, field_name: str,
                               context: Optional[Dict[str, Any]], result: SecurityValidationResult) -> None:
        """Store validation result in cache if enabled."""
        if self.enable_caching:
            cache_key = f"{input_value}:{field_name}:{context}"
            self._cache[cache_key] = result
    
    def _create_empty_input_result(self) -> SecurityValidationResult:
        """Create result for empty input."""
        return SecurityValidationResult(
            is_valid=True,
            sanitized_value="",
            confidence_score=1.0
        )
    
    def _perform_comprehensive_validation(self, input_value: str, field_name: str,
                                        context: Optional[Dict[str, Any]]) -> BaseValidationResult:
        """Perform comprehensive validation on input value."""
        result = self._create_base_validation_result(input_value)
        self._perform_basic_validation_checks(input_value, result)
        threats = self._detect_and_process_threats(input_value, result, field_name)
        result.sanitized_value = self.sanitizer.sanitize_input(input_value, threats)
        self._apply_context_validation(input_value, context, result)
        self._apply_custom_rules(input_value, result)
        return result
    
    def _create_base_validation_result(self, input_value: str) -> SecurityValidationResult:
        """Create base validation result object."""
        return SecurityValidationResult(is_valid=True, sanitized_value=input_value)
    
    def _perform_basic_validation_checks(self, input_value: str, result: BaseValidationResult) -> None:
        """Perform basic validation checks."""
        self._check_length(input_value, result)
        self._check_encoding(input_value, result)
        self._check_validation_level_constraints(input_value, result)
    
    def _detect_and_process_threats(self, input_value: str, result: BaseValidationResult, 
                                   field_name: str) -> List[SecurityThreat]:
        """Detect threats and update result validity."""
        normalized_input = self.normalizer.normalize_for_detection(input_value)
        threats = self.threat_detector.detect_threats(normalized_input, input_value)
        
        if threats:
            self._mark_result_as_invalid(result, field_name, threats)
        return threats
    
    def _mark_result_as_invalid(self, result: SecurityValidationResult, field_name: str, 
                               threats: List[SecurityThreat]) -> None:
        """Mark validation result as invalid due to threats."""
        result.is_valid = False
        result.errors.append(f"Security threats detected in {field_name}: {[t.value for t in threats]}")
        result.threats_detected = [t.value for t in threats]
        result.confidence_score = 0.0
    
    def _apply_context_validation(self, input_value: str, context: Optional[Dict[str, Any]], 
                                 result: BaseValidationResult) -> None:
        """Apply context-specific validation if provided."""
        if context:
            self._validate_context(input_value, context, result)
    
    def _create_error_result(self, field_name: str, error: Exception) -> BaseValidationResult:
        """Create validation result for error cases."""
        logger.error(f"Input validation error for {field_name}: {error}")
        return BaseValidationResult(
            is_valid=False,
            errors=[f"Validation error: {str(error)}"],
            confidence_score=0.0
        )
    
    def _check_length(self, input_value: str, result: BaseValidationResult) -> None:
        """Check input length."""
        if len(input_value) > self.constraints.max_input_length:
            result.warnings.append(f"Input length ({len(input_value)}) exceeds maximum ({self.constraints.max_input_length})")
            result.confidence_score *= 0.8
    
    def _check_encoding(self, input_value: str, result: BaseValidationResult) -> None:
        """Check for encoding issues."""
        try:
            self._check_double_url_encoding(input_value, result)
            self._check_base64_encoding(input_value, result)
        except Exception as e:
            result.warnings.append(f"Encoding check failed: {e}")
    
    def _check_double_url_encoding(self, input_value: str, result: BaseValidationResult) -> None:
        """Check for double URL encoding."""
        decoded = urllib.parse.unquote(input_value)
        if self.encoding_analyzer.is_double_encoded(input_value, decoded):
            result.warnings.append("Potential double URL encoding detected")
            result.confidence_score *= 0.9
    
    def _check_base64_encoding(self, input_value: str, result: BaseValidationResult) -> None:
        """Check for suspicious base64 encoded content."""
        if not self.encoding_analyzer.is_valid_base64_format(input_value):
            return
        
        if self.encoding_analyzer.has_suspicious_base64_content(input_value):
            result.warnings.append("Suspicious base64 encoded content")
            result.confidence_score *= 0.7
    
    def _validate_context(self, input_value: str, context: Dict[str, Any], 
                         result: BaseValidationResult) -> None:
        """Perform context-specific validation."""
        input_type = context.get('type', 'general')
        validation_map = {
            'email': self._validate_email_context,
            'url': self._validate_url_context,
            'filename': self._validate_filename_context,
            'json': self._validate_json_context
        }
        
        if input_type in validation_map:
            validation_map[input_type](input_value, result)
    
    def _validate_email_context(self, email: str, result: BaseValidationResult) -> None:
        """Validate email format context."""
        is_valid, error_msg = self.content_validator.validate_email_content(email)
        if not is_valid:
            result.warnings.append(error_msg)
            result.confidence_score *= 0.8
    
    def _validate_url_context(self, url: str, result: BaseValidationResult) -> None:
        """Validate URL format and security context."""
        is_valid, error_msg = self.content_validator.validate_url_content(url)
        if not is_valid:
            if "dangerous" in error_msg.lower():
                result.is_valid = False
                result.errors.append(error_msg)
            else:
                result.warnings.append(error_msg)
                result.confidence_score *= 0.8
    
    def _validate_filename_context(self, filename: str, result: BaseValidationResult) -> None:
        """Validate filename security context."""
        is_valid, error_msg = self.content_validator.validate_filename_content(filename)
        if not is_valid:
            if "path traversal" in error_msg.lower():
                result.is_valid = False
                result.errors.append(error_msg)
            else:
                result.warnings.append(error_msg)
                result.confidence_score *= 0.5
    
    def _validate_json_context(self, json_str: str, result: BaseValidationResult) -> None:
        """Validate JSON input context."""
        is_valid, error_msg = self.content_validator.validate_json_content(json_str)
        if not is_valid:
            result.warnings.append(error_msg)
            result.confidence_score *= 0.7
    
    def bulk_validate(self, inputs: Dict[str, str], 
                     contexts: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, BaseValidationResult]:
        """Validate multiple inputs efficiently."""
        results = {}
        for field_name, input_value in inputs.items():
            context = contexts.get(field_name) if contexts else None
            results[field_name] = self.validate_input(input_value, field_name, context)
        return results
    
    def add_custom_rule(self, name: str, rule_func):
        """Add custom validation rule."""
        self.custom_rules[name] = rule_func
    
    def _apply_custom_rules(self, input_value: str, result: BaseValidationResult) -> None:
        """Apply custom validation rules."""
        for rule_name, rule_func in self.custom_rules.items():
            try:
                if not rule_func(input_value):
                    result.is_valid = False
                    result.errors.append(f"Custom rule '{rule_name}' failed")
                    result.confidence_score *= 0.5
            except Exception as e:
                logger.warning(f"Custom rule '{rule_name}' failed with error: {e}")
                result.warnings.append(f"Custom rule '{rule_name}' evaluation failed")
    
    def _check_validation_level_constraints(self, input_value: str, result: BaseValidationResult) -> None:
        """Check validation level specific constraints."""
        from .validation_rules import ValidationLevel
        
        if self.validation_level == ValidationLevel.STRICT:
            self._check_strict_html_content(input_value, result)
        elif self.validation_level == ValidationLevel.PARANOID:
            self._check_paranoid_constraints(input_value, result)
    
    def _check_strict_html_content(self, input_value: str, result: BaseValidationResult) -> None:
        """Check for HTML content in strict mode."""
        import re
        html_pattern = re.compile(r'<[^>]+>', re.IGNORECASE)
        if html_pattern.search(input_value):
            result.is_valid = False
            result.errors.append("HTML content not allowed in strict validation mode")
            result.confidence_score = 0.0
    
    def _check_paranoid_constraints(self, input_value: str, result: BaseValidationResult) -> None:
        """Apply paranoid level constraints."""
        suspicious_chars = self.constraints.suspicious_chars
        found_chars = set(input_value) & suspicious_chars
        if found_chars:
            result.is_valid = False
            result.errors.append(f"Suspicious characters not allowed: {found_chars}")
            result.confidence_score = 0.0


# Validation decorators for easy use
def validate_input_data(validation_level: ValidationLevel = ValidationLevel.MODERATE):
    """Decorator to validate function input data."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            validator = EnhancedInputValidator(validation_level)
            _validate_positional_arguments(validator, args)
            _validate_keyword_arguments(validator, kwargs)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def _validate_positional_arguments(validator: EnhancedInputValidator, args: tuple) -> None:
    """Validate positional string arguments."""
    for i, arg in enumerate(args):
        if isinstance(arg, str):
            result = validator.validate_input(arg, f"arg_{i}")
            if not result.is_valid:
                _raise_validation_exception(f"argument {i}", result.errors)


def _validate_keyword_arguments(validator: EnhancedInputValidator, kwargs: dict) -> None:
    """Validate keyword string arguments."""
    for key, value in kwargs.items():
        if isinstance(value, str):
            result = validator.validate_input(value, key)
            if not result.is_valid:
                _raise_validation_exception(f"parameter {key}", result.errors)


def _raise_validation_exception(location: str, errors: list) -> None:
    """Raise NetraSecurityException for validation failures."""
    raise NetraSecurityException(
        message=f"Invalid input in {location}: {errors}"
    )


# Global validator instances
strict_validator = EnhancedInputValidator(ValidationLevel.STRICT)
moderate_validator = EnhancedInputValidator(ValidationLevel.MODERATE)
basic_validator = EnhancedInputValidator(ValidationLevel.BASIC)