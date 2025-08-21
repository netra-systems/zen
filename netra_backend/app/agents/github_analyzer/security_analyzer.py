"""Security Analyzer Module.

Analyzes security aspects of AI operations maps.
Handles credential exposure detection and security recommendations.
"""

from typing import Dict, List, Any


class SecurityAnalyzer:
    """Analyzes security aspects of AI configurations."""
    
    def analyze_security(self, configurations: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze security aspects."""
        security = self._init_security_structure()
        self._check_exposed_credentials(security, configurations)
        self._add_security_recommendations(security)
        return security
    
    def _init_security_structure(self) -> Dict[str, Any]:
        """Initialize security analysis structure."""
        return {
            "exposed_keys": [],
            "warnings": [],
            "recommendations": []
        }
    
    def _check_exposed_credentials(
        self, 
        security: Dict[str, Any], 
        configurations: Dict[str, Any]
    ) -> None:
        """Check for exposed API credentials."""
        env_vars = configurations.get("env_variables", {})
        self._process_env_vars_for_credentials(security, env_vars)
    
    def _process_env_vars_for_credentials(
        self, security: Dict[str, Any], env_vars: Dict[str, Any]
    ) -> None:
        """Process environment variables for credential exposure."""
        for key, values in env_vars.items():
            if self._is_credential_key(key):
                self._check_credential_values(security, key, values)
    
    def _check_credential_values(
        self,
        security: Dict[str, Any],
        key: str,
        values: List[Dict[str, Any]]
    ) -> None:
        """Check individual credential values for exposure."""
        for value_info in values:
            if self._is_exposed_credential(value_info["value"]):
                warning_message = f"Potential exposed credential: {key}"
                security["warnings"].append(warning_message)
    
    def _is_exposed_credential(self, value: str) -> bool:
        """Check if credential value is exposed."""
        return not value.startswith("****")
    
    def _is_credential_key(self, key: str) -> bool:
        """Check if key represents a credential."""
        return "KEY" in key or "TOKEN" in key
    
    def _add_security_recommendations(
        self, 
        security: Dict[str, Any]
    ) -> None:
        """Add security recommendations if warnings exist."""
        if security["warnings"]:
            recommendation = "Use environment variables or secret management service"
            security["recommendations"].append(recommendation)