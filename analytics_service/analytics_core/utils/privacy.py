"""Privacy Compliance Utilities

Utilities for privacy compliance including PII detection and sanitization.
"""

import re
import hashlib
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PIIPattern:
    """PII detection pattern"""
    name: str
    pattern: str
    replacement: str
    description: str


class PrivacyFilter:
    """Privacy compliance filter for analytics data"""
    
    # PII detection patterns
    PII_PATTERNS = [
        PIIPattern(
            name="email",
            pattern=r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            replacement="[EMAIL]",
            description="Email addresses"
        ),
        PIIPattern(
            name="phone_us",
            pattern=r'\b\d{3}-\d{3}-\d{4}\b',
            replacement="[PHONE]",
            description="US phone numbers (XXX-XXX-XXXX)"
        ),
        PIIPattern(
            name="phone_us_parentheses",
            pattern=r'\b\(\d{3}\)\s*\d{3}-\d{4}\b',
            replacement="[PHONE]",
            description="US phone numbers with parentheses"
        ),
        PIIPattern(
            name="phone_international",
            pattern=r'\+\d{1,3}[\s.-]?\d{3,4}[\s.-]?\d{3,4}[\s.-]?\d{3,4}',
            replacement="[PHONE]",
            description="International phone numbers"
        ),
        PIIPattern(
            name="credit_card",
            pattern=r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
            replacement="[CARD]",
            description="Credit card numbers"
        ),
        PIIPattern(
            name="ssn",
            pattern=r'\b\d{3}-\d{2}-\d{4}\b',
            replacement="[SSN]",
            description="Social Security Numbers"
        ),
        PIIPattern(
            name="ssn_no_dashes",
            pattern=r'\b\d{9}\b',
            replacement="[SSN]",
            description="Social Security Numbers without dashes"
        ),
        PIIPattern(
            name="ip_address",
            pattern=r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
            replacement="[IP]",
            description="IP addresses"
        ),
        PIIPattern(
            name="url",
            pattern=r'https?://[^\s]+',
            replacement="[URL]",
            description="URLs"
        ),
        PIIPattern(
            name="api_key",
            pattern=r'\b[Aa][Pp][Ii][_-]?[Kk][Ee][Yy][_-]?[A-Za-z0-9]{20,}\b',
            replacement="[API_KEY]",
            description="API keys"
        ),
        PIIPattern(
            name="jwt_token",
            pattern=r'\beyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*\b',
            replacement="[JWT_TOKEN]",
            description="JWT tokens"
        ),
    ]
    
    # Sensitive keywords that might indicate PII context
    SENSITIVE_KEYWORDS = [
        'password', 'passwd', 'pwd', 'secret', 'token', 'key',
        'credit card', 'ssn', 'social security', 'driver license',
        'passport', 'bank account', 'routing number', 'pin',
        'username', 'login', 'auth', 'credential'
    ]
    
    def __init__(self, 
                 enable_pii_detection: bool = True,
                 enable_keyword_filtering: bool = True,
                 max_text_length: int = 1000,
                 hash_salt: Optional[str] = None):
        """Initialize privacy filter"""
        self.enable_pii_detection = enable_pii_detection
        self.enable_keyword_filtering = enable_keyword_filtering
        self.max_text_length = max_text_length
        self.hash_salt = hash_salt or "analytics_privacy_salt"
        
        # Compile regex patterns for performance
        self._compiled_patterns = {}
        if enable_pii_detection:
            for pattern in self.PII_PATTERNS:
                try:
                    self._compiled_patterns[pattern.name] = re.compile(
                        pattern.pattern, re.IGNORECASE
                    )
                except re.error as e:
                    logger.error(f"Failed to compile pattern {pattern.name}: {e}")
    
    def sanitize_text(self, text: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Sanitize text and return results with metadata"""
        if not text:
            return {
                'sanitized_text': text,
                'pii_detected': [],
                'was_truncated': False,
                'original_length': 0
            }
        
        original_length = len(text)
        sanitized_text = text
        pii_detected = []
        
        # Apply PII detection and replacement
        if self.enable_pii_detection:
            for pattern in self.PII_PATTERNS:
                if pattern.name in self._compiled_patterns:
                    compiled_pattern = self._compiled_patterns[pattern.name]
                    matches = compiled_pattern.findall(sanitized_text)
                    
                    if matches:
                        pii_detected.append({
                            'type': pattern.name,
                            'count': len(matches),
                            'description': pattern.description
                        })
                        sanitized_text = compiled_pattern.sub(
                            pattern.replacement, sanitized_text
                        )
        
        # Check for sensitive keywords
        if self.enable_keyword_filtering:
            text_lower = sanitized_text.lower()
            for keyword in self.SENSITIVE_KEYWORDS:
                if keyword in text_lower:
                    pii_detected.append({
                        'type': 'sensitive_keyword',
                        'keyword': keyword,
                        'description': f'Contains sensitive keyword: {keyword}'
                    })
        
        # Truncate if too long
        was_truncated = False
        if len(sanitized_text) > self.max_text_length:
            sanitized_text = sanitized_text[:self.max_text_length] + '...[TRUNCATED]'
            was_truncated = True
        
        return {
            'sanitized_text': sanitized_text,
            'pii_detected': pii_detected,
            'was_truncated': was_truncated,
            'original_length': original_length,
            'context': context
        }
    
    def hash_identifier(self, identifier: str, prefix: str = "") -> str:
        """Hash an identifier for privacy protection"""
        if not identifier:
            return identifier
            
        # Use SHA-256 with salt
        hash_input = f"{self.hash_salt}:{prefix}:{identifier}"
        return hashlib.sha256(hash_input.encode()).hexdigest()
    
    def sanitize_user_agent(self, user_agent: str) -> str:
        """Sanitize user agent string to remove detailed version info"""
        if not user_agent:
            return user_agent
        
        # Extract basic browser info only
        browser_patterns = [
            (r'(Chrome)/(\d+)', r'\1/\2'),
            (r'(Firefox)/(\d+)', r'\1/\2'),
            (r'(Safari)/(\d+)', r'\1/\2'),
            (r'(Edge)/(\d+)', r'\1/\2'),
            (r'(Opera)/(\d+)', r'\1/\2'),
        ]
        
        for pattern, replacement in browser_patterns:
            match = re.search(pattern, user_agent)
            if match:
                return f"{match.group(1)}/{match.group(2)}"
        
        # If no match, return generic browser info
        return "Unknown Browser"
    
    def sanitize_ip_address(self, ip_address: str) -> str:
        """Hash IP address for privacy compliance"""
        if not ip_address:
            return ip_address
            
        return self.hash_identifier(ip_address, "ip")
    
    def sanitize_event_properties(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize event properties dictionary"""
        sanitized_properties = {}
        
        for key, value in properties.items():
            if isinstance(value, str):
                # Apply text sanitization
                sanitization_result = self.sanitize_text(value, context=key)
                sanitized_properties[key] = sanitization_result['sanitized_text']
                
                # Add metadata about PII detection if any found
                if sanitization_result['pii_detected']:
                    sanitized_properties[f"{key}_pii_metadata"] = sanitization_result
                    
            elif isinstance(value, (dict, list)):
                # Recursively sanitize nested structures
                sanitized_properties[key] = self._sanitize_nested_data(value)
            else:
                # Keep non-string values as is
                sanitized_properties[key] = value
        
        return sanitized_properties
    
    def _sanitize_nested_data(self, data: Any) -> Any:
        """Recursively sanitize nested data structures"""
        if isinstance(data, dict):
            return {
                key: self._sanitize_nested_data(value)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [self._sanitize_nested_data(item) for item in data]
        elif isinstance(data, str):
            return self.sanitize_text(data)['sanitized_text']
        else:
            return data
    
    def validate_compliance(self, text: str) -> Dict[str, Any]:
        """Validate if text complies with privacy requirements"""
        if not text:
            return {
                'compliant': True,
                'issues': [],
                'risk_level': 'low'
            }
        
        sanitization_result = self.sanitize_text(text)
        pii_detected = sanitization_result['pii_detected']
        
        issues = []
        risk_level = 'low'
        
        if pii_detected:
            risk_level = 'high'
            for pii_info in pii_detected:
                issues.append(f"Detected {pii_info['description']}")
        
        # Check for high-risk patterns
        high_risk_patterns = ['credit_card', 'ssn', 'api_key', 'jwt_token']
        for pii_info in pii_detected:
            if pii_info['type'] in high_risk_patterns:
                risk_level = 'critical'
                break
        
        return {
            'compliant': len(issues) == 0,
            'issues': issues,
            'risk_level': risk_level,
            'pii_detected': pii_detected
        }
    
    def get_privacy_report(self, data_samples: List[str]) -> Dict[str, Any]:
        """Generate privacy compliance report for data samples"""
        total_samples = len(data_samples)
        if total_samples == 0:
            return {
                'total_samples': 0,
                'compliant_samples': 0,
                'compliance_rate': 1.0,
                'risk_breakdown': {},
                'common_pii_types': []
            }
        
        compliant_count = 0
        risk_counts = {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}
        pii_type_counts = {}
        
        for sample in data_samples:
            validation_result = self.validate_compliance(sample)
            
            if validation_result['compliant']:
                compliant_count += 1
            
            risk_level = validation_result['risk_level']
            risk_counts[risk_level] += 1
            
            # Count PII types
            for pii_info in validation_result['pii_detected']:
                pii_type = pii_info['type']
                pii_type_counts[pii_type] = pii_type_counts.get(pii_type, 0) + 1
        
        # Sort PII types by frequency
        common_pii_types = sorted(
            pii_type_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]  # Top 10 most common
        
        return {
            'total_samples': total_samples,
            'compliant_samples': compliant_count,
            'compliance_rate': compliant_count / total_samples,
            'risk_breakdown': risk_counts,
            'common_pii_types': common_pii_types,
            'recommendations': self._generate_privacy_recommendations(risk_counts, pii_type_counts)
        }
    
    def _generate_privacy_recommendations(self, 
                                        risk_counts: Dict[str, int],
                                        pii_type_counts: Dict[str, int]) -> List[str]:
        """Generate privacy compliance recommendations"""
        recommendations = []
        
        if risk_counts.get('critical', 0) > 0:
            recommendations.append(
                "Critical: High-risk PII detected (SSN, credit cards, API keys). "
                "Implement additional filtering."
            )
        
        if risk_counts.get('high', 0) > 0:
            recommendations.append(
                "High: PII patterns detected. Review data collection practices."
            )
        
        if pii_type_counts.get('email', 0) > 10:
            recommendations.append(
                "Consider using hashed email identifiers instead of raw email addresses."
            )
        
        if pii_type_counts.get('ip_address', 0) > 10:
            recommendations.append(
                "IP addresses detected frequently. Ensure they are hashed for privacy."
            )
        
        if not recommendations:
            recommendations.append(
                "Privacy compliance looks good. Continue monitoring for PII leakage."
            )
        
        return recommendations