"""
Security headers configuration module.
Implements OWASP-compliant security headers for different environments.
"""

from typing import Dict


class SecurityHeadersConfig:
    """Configuration for security headers based on environment."""
    
    @staticmethod
    def get_headers(environment: str = "development") -> Dict[str, str]:
        """Get security headers based on environment."""
        base_headers = SecurityHeadersConfig._get_base_headers()
        return SecurityHeadersConfig._apply_environment_headers(base_headers, environment)
    
    @staticmethod
    def _get_base_headers() -> Dict[str, str]:
        """Get base security headers common to all environments."""
        core_headers = SecurityHeadersConfig._get_core_security_headers()
        additional_headers = SecurityHeadersConfig._get_additional_security_headers()
        return {**core_headers, **additional_headers}
    
    @staticmethod
    def _get_core_security_headers() -> Dict[str, str]:
        """Get core security headers."""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY", 
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": SecurityHeadersConfig._get_permissions_policy()
        }
    
    @staticmethod
    def _get_additional_security_headers() -> Dict[str, str]:
        """Get additional security headers."""
        return {
            "X-Robots-Tag": "noindex, nofollow, noarchive, nosnippet",
            "Cache-Control": "no-store, no-cache, must-revalidate, private",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    
    @staticmethod
    def _apply_environment_headers(headers: Dict[str, str], environment: str) -> Dict[str, str]:
        """Apply environment-specific security headers."""
        if environment == "production":
            headers.update(SecurityHeadersConfig._get_production_headers())
        elif environment == "staging":
            headers.update(SecurityHeadersConfig._get_staging_headers())
        else:
            headers.update(SecurityHeadersConfig._get_development_headers())
        return headers
    
    @staticmethod
    def _get_permissions_policy() -> str:
        """Get permissions policy directive."""
        disabled_features = [
            "geolocation=()", "microphone=()", "camera=()", "payment=()",
            "usb=()", "magnetometer=()", "gyroscope=()", "accelerometer=()",
            "ambient-light-sensor=()", "autoplay=()", "encrypted-media=()",
            "fullscreen=()", "picture-in-picture=()"
        ]
        return ", ".join(disabled_features)
    
    @staticmethod
    def _get_production_headers() -> Dict[str, str]:
        """Get production-specific security headers."""
        return {
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            "Content-Security-Policy": SecurityHeadersConfig._get_production_csp(),
        }
    
    @staticmethod
    def _get_staging_headers() -> Dict[str, str]:
        """Get staging-specific security headers."""
        return {
            "Strict-Transport-Security": "max-age=86400; includeSubDomains",
            "Content-Security-Policy": SecurityHeadersConfig._get_staging_csp(),
        }
    
    @staticmethod
    def _get_development_headers() -> Dict[str, str]:
        """Get development-specific security headers."""
        return {
            "Content-Security-Policy": SecurityHeadersConfig._get_development_csp(),
        }
    
    @staticmethod
    def _get_production_csp() -> str:
        """Get production Content Security Policy."""
        base_directives = SecurityHeadersConfig._get_production_base_directives()
        security_directives = SecurityHeadersConfig._get_production_security_directives()
        return "; ".join(base_directives + security_directives)
    
    @staticmethod
    def _get_production_base_directives() -> list:
        """Get base production CSP directives."""
        return [
            "default-src 'self'",
            "script-src 'self' https://apis.google.com https://www.googletagmanager.com https://tagmanager.google.com https://www.clarity.ms https://scripts.clarity.ms",
            "style-src 'self' https://fonts.googleapis.com",
            "font-src 'self' https://fonts.gstatic.com",
            "img-src 'self' data: https: https://www.googletagmanager.com https://*.clarity.ms https://c.bing.com",
            "connect-src 'self' https://api.netrasystems.ai wss://api.netrasystems.ai https://www.google-analytics.com https://analytics.google.com https://www.googletagmanager.com https://*.clarity.ms"
        ]
    
    @staticmethod
    def _get_production_security_directives() -> list:
        """Get security production CSP directives."""
        return [
            "frame-ancestors 'none'", "base-uri 'self'", "form-action 'self'",
            "upgrade-insecure-requests"
        ]
    
    @staticmethod
    def _get_staging_csp() -> str:
        """Get staging Content Security Policy."""
        base_directives = SecurityHeadersConfig._get_staging_base_directives()
        security_directives = SecurityHeadersConfig._get_staging_security_directives()
        return "; ".join(base_directives + security_directives)
    
    @staticmethod
    def _get_staging_base_directives() -> list:
        """Get base staging CSP directives."""
        return [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https: https://scripts.clarity.ms",
            "style-src 'self' 'unsafe-inline' https:",
            "font-src 'self' https: data:",
            "img-src 'self' data: https: https://c.bing.com",
            "connect-src 'self' https: wss:"
        ]
    
    @staticmethod
    def _get_staging_security_directives() -> list:
        """Get security staging CSP directives."""
        return ["frame-ancestors 'none'", "base-uri 'self'", "form-action 'self'"]
    
    @staticmethod
    def _get_development_csp() -> str:
        """Get development Content Security Policy."""
        base_directives = SecurityHeadersConfig._get_development_base_directives()
        security_directives = SecurityHeadersConfig._get_development_security_directives()
        return "; ".join(base_directives + security_directives)
    
    @staticmethod
    def _get_development_base_directives() -> list:
        """Get base development CSP directives."""
        return [
            "default-src 'self' 'unsafe-inline' 'unsafe-eval'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' http: https: https://scripts.clarity.ms",
            "style-src 'self' 'unsafe-inline' http: https:",
            "font-src 'self' http: https: data:",
            "img-src 'self' data: http: https: https://c.bing.com",
            "connect-src 'self' http: https: ws: wss:"
        ]
    
    @staticmethod
    def _get_development_security_directives() -> list:
        """Get security development CSP directives."""
        return ["frame-ancestors 'self'", "base-uri 'self'", "form-action 'self'"]