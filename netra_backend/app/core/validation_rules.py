"""
Pattern definitions and threat detection rules for input validation.
Contains security threat patterns and detection logic.
"""

import re
from enum import Enum
from typing import Dict, List


class ValidationLevel(str, Enum):
    """Input validation strictness levels.
    
    Following pragmatic rigor principles:
    - PERMISSIVE: Minimal validation, focuses on preventing system failures
    - BASIC: Standard validation with reasonable security measures
    - MODERATE: Enhanced security validation for production environments
    - STRICT: Comprehensive validation for high-security contexts
    
    Removed PARANOID level - overly strict validation that often breaks
    legitimate use cases without providing meaningful security benefits.
    """
    PERMISSIVE = "permissive"  # Minimal validation, prevents system failures
    BASIC = "basic"          # Standard validation with basic security
    MODERATE = "moderate"    # Enhanced security for production
    STRICT = "strict"        # Comprehensive security validation


class SecurityThreat(str, Enum):
    """Types of security threats to detect."""
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    SCRIPT_INJECTION = "script_injection"
    PATH_TRAVERSAL = "path_traversal"
    COMMAND_INJECTION = "command_injection"
    LDAP_INJECTION = "ldap_injection"
    XML_INJECTION = "xml_injection"
    JSON_INJECTION = "json_injection"
    HEADER_INJECTION = "header_injection"


class ThreatPattern:
    """Security threat detection patterns."""
    
    # SQL Injection patterns
    SQL_PATTERNS = [
        r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)',
        r'(-{2}|/\*|\*/)',  # SQL comments
        r'(\b(OR|AND)\s+\d+\s*=\s*\d+)',  # OR 1=1, AND 1=1
        r'(\bxp_cmdshell\b)',  # SQL Server command execution
        r'(\b(sp_|xp_)\w+)',  # SQL Server stored procedures
        r'(;\s*(DROP|DELETE|INSERT|UPDATE))',  # Statement chaining
        r'(\bUNION\s+(ALL\s+)?SELECT)',  # Union-based injections
        r'(\bINTO\s+OUTFILE\b)',  # File operations
    ]
    
    # XSS patterns
    XSS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',  # Event handlers
        r'<iframe[^>]*>',
        r'<object[^>]*>',
        r'<embed[^>]*>',
        r'<link[^>]*>',
        r'<meta[^>]*>',
        r'<style[^>]*>.*?</style>',
        r'expression\s*\(',  # CSS expressions
        r'url\s*\(\s*["\']?\s*javascript:',
        r'data:[^;]*;base64',  # Data URLs
    ]
    
    # Script injection patterns
    SCRIPT_PATTERNS = [
        r'<script[^>]*>',
        r'</script>',
        r'javascript:',
        r'vbscript:',
        r'file:',
        r'data:text/html',
        r'&#x\w+;',  # HTML entities
        r'&\w+;',
    ]
    
    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r'\.\./',
        r'\.\.\\',
        r'%2e%2e%2f',
        r'%2e%2e%5c',
        r'%252e%252e%252f',
        r'%c0%ae%c0%ae%c0%af',
        r'/etc/passwd',
        r'/etc/shadow',
        r'C:\\Windows\\System32',
    ]
    
    # Command injection patterns
    COMMAND_PATTERNS = [
        r'[;&|`$]',  # Command separators
        r'\$\{.*\}',  # Variable expansion
        r'\$\(.*\)',  # Command substitution
        r'`.*`',      # Backticks
        r'>\s*/dev/',  # Output redirection
        r'\|\s*(curl|wget|nc|netcat)',  # Network commands
    ]
    
    # LDAP injection patterns
    LDAP_PATTERNS = [
        r'\*\)\(',
        r'\)\(&',
        r'\|\(&',
        r'[()=*|&]',  # LDAP special characters
    ]
    
    # XML injection patterns
    XML_PATTERNS = [
        r'<!ENTITY',
        r'SYSTEM\s+["\']',
        r'PUBLIC\s+["\']',
        r'<!DOCTYPE',
        r'&\w+;',
        r'<!\[CDATA\[',
    ]


class PatternCompiler:
    """Compiles threat detection patterns for efficient matching."""
    
    def __init__(self):
        self.compiled_patterns = {}
    
    def compile_all_patterns(self) -> Dict[SecurityThreat, List[re.Pattern]]:
        """Compile all threat detection patterns."""
        self._compile_injection_patterns()
        self._compile_web_attack_patterns()
        self._compile_system_attack_patterns()
        self._compile_data_attack_patterns()
        return self.compiled_patterns
    
    def _compile_injection_patterns(self) -> None:
        """Compile SQL and command injection patterns."""
        self.compiled_patterns[SecurityThreat.SQL_INJECTION] = [
            re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            for pattern in ThreatPattern.SQL_PATTERNS
        ]
        self.compiled_patterns[SecurityThreat.COMMAND_INJECTION] = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in ThreatPattern.COMMAND_PATTERNS
        ]
    
    def _compile_web_attack_patterns(self) -> None:
        """Compile XSS and script injection patterns."""
        self.compiled_patterns[SecurityThreat.XSS] = [
            re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            for pattern in ThreatPattern.XSS_PATTERNS
        ]
        self.compiled_patterns[SecurityThreat.SCRIPT_INJECTION] = [
            re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            for pattern in ThreatPattern.SCRIPT_PATTERNS
        ]
    
    def _compile_system_attack_patterns(self) -> None:
        """Compile path traversal and LDAP injection patterns."""
        self.compiled_patterns[SecurityThreat.PATH_TRAVERSAL] = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in ThreatPattern.PATH_TRAVERSAL_PATTERNS
        ]
        self.compiled_patterns[SecurityThreat.LDAP_INJECTION] = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in ThreatPattern.LDAP_PATTERNS
        ]
    
    def _compile_data_attack_patterns(self) -> None:
        """Compile XML injection patterns."""
        self.compiled_patterns[SecurityThreat.XML_INJECTION] = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in ThreatPattern.XML_PATTERNS
        ]


class ValidationConstraints:
    """Input validation constraints based on validation level.
    
    Implements pragmatic rigor principles:
    - Be liberal in what you accept, conservative in what you send
    - Default to resilience with progressive enforcement
    - Focus on preventing real security threats, not theoretical purity
    """
    
    def __init__(self, validation_level: ValidationLevel):
        self.validation_level = validation_level
        self.max_input_length = self._get_max_length()
        self.suspicious_chars = self._get_suspicious_chars()
        self.allow_fallbacks = self._should_allow_fallbacks()
    
    def _get_max_length(self) -> int:
        """Get maximum input length based on validation level.
        
        Adjusted for pragmatic rigor - limits should prevent abuse
        while accommodating legitimate use cases.
        """
        length_limits = {
            ValidationLevel.PERMISSIVE: 1000000,  # 1MB - very permissive for development
            ValidationLevel.BASIC: 500000,       # 500KB - reasonable for most content
            ValidationLevel.MODERATE: 100000,    # 100KB - production standard
            ValidationLevel.STRICT: 50000,       # 50KB - high-security contexts
        }
        return length_limits[self.validation_level]
    
    def _get_suspicious_chars(self) -> set:
        """Get suspicious character set based on validation level.
        
        More permissive approach - only flag truly dangerous patterns.
        Following Postel's Law: be liberal in what you accept.
        """
        if self.validation_level == ValidationLevel.PERMISSIVE:
            # Only block the most dangerous injection patterns
            return set('<script>')  # Just prevent obvious script tags
        elif self.validation_level == ValidationLevel.BASIC:
            # Block common injection vectors but allow normal punctuation
            return set('<>&;"\'')  # Basic XSS prevention
        elif self.validation_level == ValidationLevel.MODERATE:
            # Enhanced blocking for production environments
            return set('<>&;"\';|`$')  # Standard production security
        else:  # STRICT
            # Comprehensive blocking for high-security contexts
            return set('<>"\'&;|`$(){}[]\\*')  # Original strict behavior
    
    def _should_allow_fallbacks(self) -> bool:
        """Determine if fallback behaviors should be allowed.
        
        Permissive levels allow graceful degradation instead of hard failures.
        """
        return self.validation_level in [ValidationLevel.PERMISSIVE, ValidationLevel.BASIC]


class ThreatDetector:
    """Detects security threats in input using compiled patterns."""
    
    def __init__(self, patterns: Dict[SecurityThreat, List[re.Pattern]]):
        self.patterns = patterns
    
    def detect_threats(self, normalized_input: str, original_input: str) -> List[SecurityThreat]:
        """Detect security threats in normalized input."""
        threats = []
        for threat_type, pattern_list in self.patterns.items():
            if self._check_threat_patterns(pattern_list, normalized_input, threat_type, original_input):
                threats.append(threat_type)
        return threats
    
    def _check_threat_patterns(self, patterns: List[re.Pattern], normalized_input: str,
                              threat_type: SecurityThreat, input_value: str) -> bool:
        """Check if any pattern matches the normalized input."""
        from netra_backend.app.logging_config import central_logger
        logger = central_logger.get_logger(__name__)
        
        for pattern in patterns:
            if pattern.search(normalized_input):
                logger.warning(f"Detected {threat_type.value} in input: {input_value[:100]}...")
                return True
        return False