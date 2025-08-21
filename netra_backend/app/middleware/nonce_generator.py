"""
Nonce generation module for Content Security Policy.
Provides cryptographically secure nonces for CSP directives.
"""

import secrets


class NonceGenerator:
    """Generate cryptographic nonces for CSP."""
    
    @staticmethod
    def generate_nonce() -> str:
        """Generate a cryptographically secure nonce."""
        return secrets.token_urlsafe(16)
    
    @staticmethod
    def add_nonce_to_csp(csp: str, nonce: str) -> str:
        """Add nonce to CSP script-src directive."""
        return NonceGenerator._add_nonce_to_directives(csp, nonce)
    
    @staticmethod
    def _add_nonce_to_directives(csp: str, nonce: str) -> str:
        """Add nonce to both script-src and style-src directives."""
        nonce_directive = f"'nonce-{nonce}'"
        csp = NonceGenerator._add_to_directive(csp, "script-src", nonce_directive)
        csp = NonceGenerator._add_to_directive(csp, "style-src", nonce_directive)
        return csp
    
    @staticmethod
    def _add_to_directive(csp: str, directive: str, value: str) -> str:
        """Add value to a specific CSP directive."""
        if directive in csp:
            return csp.replace(directive, f"{directive} {value}")
        else:
            return f"{csp}; {directive} 'self' {value}"