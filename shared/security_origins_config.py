"""
Shared Security Origins Configuration - SSOT for CORS and CSP
Centralizes all allowed origins and security domains for the application.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Enable secure cross-origin requests and content loading
- Value Impact: Prevents security errors that block legitimate user interactions
- Strategic Impact: Unified security configuration for all services
"""

from typing import Dict, List, Set
from enum import Enum


class SecurityEnvironment(Enum):
    """Environment types for security configuration."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class SecurityOriginsConfig:
    """
    Single Source of Truth for security origins configuration.
    Used by both CORS and CSP configurations.
    """
    
    # ========== SHARED DOMAINS ==========
    # These are domains used across all environments
    
    # Google services (OAuth, Analytics, Fonts)
    GOOGLE_DOMAINS = [
        "https://apis.google.com",
        "https://accounts.google.com",
        "https://oauth2.googleapis.com",
        "https://www.googleapis.com",
        "https://fonts.googleapis.com",
        "https://fonts.gstatic.com",
        "https://www.googletagmanager.com",
        "https://tagmanager.google.com",
        "https://www.google-analytics.com",
        "https://analytics.google.com",
        "https://stats.g.doubleclick.net"
    ]
    
    # Microsoft Clarity Analytics
    CLARITY_DOMAINS = [
        "https://www.clarity.ms",
        "https://scripts.clarity.ms",
        "https://*.clarity.ms",
        "https://c.bing.com"
    ]
    
    # Third-party services mentioned in CSP requirements
    THIRD_PARTY_SERVICES = [
        "https://cloudflare-dns.com",
        "https://featureassets.org",
        "https://prodregistryv2.org",
        "https://statsigapi.net"
    ]
    
    # Sentry error tracking
    SENTRY_DOMAINS = [
        "https://o4509974514106368.ingest.us.sentry.io",
        "https://*.sentry.io"  # Wildcard for flexibility
    ]
    
    # ========== ENVIRONMENT-SPECIFIC DOMAINS ==========
    
    @classmethod
    def get_production_domains(cls) -> Dict[str, List[str]]:
        """Get production-specific domains."""
        return {
            "app": [
                "https://netrasystems.ai",
                "https://www.netrasystems.ai",
                "https://app.netrasystems.ai",
                "https://api.netrasystems.ai",
                "https://auth.netrasystems.ai"
            ],
            "websocket": [
                "wss://api.netrasystems.ai",
                "wss://app.netrasystems.ai"
            ]
        }
    
    @classmethod
    def get_staging_domains(cls) -> Dict[str, List[str]]:
        """Get staging-specific domains."""
        return {
            "app": [
                "https://staging.netrasystems.ai",
                "https://app.staging.netrasystems.ai",
                "https://auth.staging.netrasystems.ai",  # CRITICAL: Auth subdomain
                "https://api.staging.netrasystems.ai",
                "https://backend.staging.netrasystems.ai"
            ],
            "cloud_run": [
                # Cloud Run service URLs for staging
                "https://netra-frontend-701982941522.us-central1.run.app",
                "https://netra-backend-701982941522.us-central1.run.app",
                "https://netra-auth-701982941522.us-central1.run.app"
            ],
            "websocket": [
                "wss://app.staging.netrasystems.ai",
                "wss://api.staging.netrasystems.ai",
                "wss://backend.staging.netrasystems.ai"
            ]
        }
    
    @classmethod
    def get_development_domains(cls) -> Dict[str, List[str]]:
        """Get development-specific domains."""
        return {
            "localhost": [
                # HTTP localhost variants
                "http://localhost:3000",
                "http://localhost:3001",
                "http://localhost:3002",
                "http://localhost:8000",
                "http://localhost:8080",
                "http://localhost:8081",
                "http://localhost:5173",  # Vite
                "http://localhost:4200",  # Angular
                
                # 127.0.0.1 variants
                "http://127.0.0.1:3000",
                "http://127.0.0.1:3001",
                "http://127.0.0.1:3002",
                "http://127.0.0.1:8000",
                "http://127.0.0.1:8080",
                "http://127.0.0.1:8081",
                "http://127.0.0.1:5173",
                "http://127.0.0.1:4200",
                
                # HTTPS variants for local cert testing
                "https://localhost:3000",
                "https://localhost:3001",
                "https://localhost:8000",
                "https://localhost:8080",
                "https://127.0.0.1:3000",
                "https://127.0.0.1:3001",
                "https://127.0.0.1:8000",
                "https://127.0.0.1:8080",
                
                # 0.0.0.0 for Docker/container scenarios
                "http://0.0.0.0:3000",
                "http://0.0.0.0:8000",
                "http://0.0.0.0:8080"
            ],
            "docker": [
                # Docker service names
                "http://frontend:3000",
                "http://backend:8000",
                "http://auth:8081",
                "http://netra-frontend:3000",
                "http://netra-backend:8000",
                "http://netra-auth:8081"
            ],
            "websocket": [
                "ws://localhost:3000",
                "ws://localhost:8000",
                "ws://127.0.0.1:3000",
                "ws://127.0.0.1:8000",
                "wss://localhost:3000",
                "wss://localhost:8000"
            ]
        }
    
    # ========== CORS CONFIGURATION ==========
    
    @classmethod
    def get_cors_origins(cls, environment: str) -> List[str]:
        """
        Get CORS allowed origins for the specified environment.
        
        Args:
            environment: The environment (development, staging, production)
            
        Returns:
            List of allowed CORS origins
        """
        env = SecurityEnvironment(environment.lower())
        
        if env == SecurityEnvironment.PRODUCTION:
            domains = cls.get_production_domains()
            return domains["app"]
            
        elif env == SecurityEnvironment.STAGING:
            domains = cls.get_staging_domains()
            # Include all staging domains plus development for testing
            staging_origins = (
                domains["app"] + 
                domains["cloud_run"] +
                cls.get_development_domains()["localhost"][:8]  # Include main localhost ports
            )
            return staging_origins
            
        else:  # Development
            domains = cls.get_development_domains()
            return domains["localhost"] + domains["docker"]
    
    # ========== CSP CONFIGURATION ==========
    
    @classmethod
    def get_csp_connect_sources(cls, environment: str) -> List[str]:
        """
        Get CSP connect-src values for the specified environment.
        
        Args:
            environment: The environment (development, staging, production)
            
        Returns:
            List of allowed connect-src values for CSP
        """
        env = SecurityEnvironment(environment.lower())
        sources = ["'self'"]
        
        # Add common third-party services
        sources.extend(cls.GOOGLE_DOMAINS)
        sources.extend(cls.CLARITY_DOMAINS)
        sources.extend(cls.THIRD_PARTY_SERVICES)
        sources.extend(cls.SENTRY_DOMAINS)
        
        if env == SecurityEnvironment.PRODUCTION:
            domains = cls.get_production_domains()
            sources.extend(domains["app"])
            sources.extend(domains["websocket"])
            
        elif env == SecurityEnvironment.STAGING:
            domains = cls.get_staging_domains()
            sources.extend(domains["app"])
            sources.extend(domains["cloud_run"])
            sources.extend(domains["websocket"])
            # Allow broader connections in staging
            sources.extend(["https:", "wss:"])
            
        else:  # Development
            # Very permissive in development
            sources.extend(["http:", "https:", "ws:", "wss:"])
        
        return sources
    
    @classmethod
    def get_csp_worker_sources(cls, environment: str) -> List[str]:
        """
        Get CSP worker-src values for the specified environment.
        
        Args:
            environment: The environment (development, staging, production)
            
        Returns:
            List of allowed worker-src values for CSP
        """
        env = SecurityEnvironment(environment.lower())
        sources = ["'self'", "blob:"]  # blob: is required for web workers
        
        if env == SecurityEnvironment.DEVELOPMENT:
            # More permissive in development
            sources.extend(["http:", "https:"])
        
        return sources
    
    @classmethod
    def get_csp_script_sources(cls, environment: str) -> List[str]:
        """
        Get CSP script-src values for the specified environment.
        
        Args:
            environment: The environment (development, staging, production)
            
        Returns:
            List of allowed script-src values for CSP
        """
        env = SecurityEnvironment(environment.lower())
        sources = ["'self'"]
        
        # Add Google and Clarity scripts
        script_domains = [
            "https://apis.google.com",
            "https://www.googletagmanager.com",
            "https://tagmanager.google.com",
            "https://www.clarity.ms",
            "https://scripts.clarity.ms"
        ]
        sources.extend(script_domains)
        
        if env == SecurityEnvironment.DEVELOPMENT:
            # Allow inline scripts and eval in development
            sources.extend(["'unsafe-inline'", "'unsafe-eval'", "http:", "https:"])
        elif env == SecurityEnvironment.STAGING:
            # Limited inline/eval in staging for debugging
            sources.extend(["'unsafe-inline'", "'unsafe-eval'", "https:"])
        # Production remains strict (no unsafe-inline or unsafe-eval)
        
        return sources
    
    @classmethod
    def get_all_external_origins(cls) -> Set[str]:
        """
        Get all external origins that need to be allowed across environments.
        
        Returns:
            Set of all external origin domains
        """
        all_origins = set()
        all_origins.update(cls.GOOGLE_DOMAINS)
        all_origins.update(cls.CLARITY_DOMAINS)
        all_origins.update(cls.THIRD_PARTY_SERVICES)
        all_origins.update(cls.SENTRY_DOMAINS)
        return all_origins
    
    @classmethod
    def validate_origin(cls, origin: str, environment: str) -> bool:
        """
        Validate if an origin is allowed for the specified environment.
        
        Args:
            origin: The origin to validate
            environment: The environment to check against
            
        Returns:
            True if the origin is allowed, False otherwise
        """
        allowed_origins = cls.get_cors_origins(environment)
        
        # Direct match
        if origin in allowed_origins:
            return True
        
        # Check if it's an external service we allow
        external_origins = cls.get_all_external_origins()
        if origin in external_origins:
            return True
        
        # In development, be more permissive with localhost
        if environment == "development":
            import re
            localhost_pattern = r'^https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\])(:\d+)?/?$'
            if re.match(localhost_pattern, origin):
                return True
        
        return False


# ========== HELPER FUNCTIONS ==========

def get_environment_origins(environment: str = "development") -> Dict[str, List[str]]:
    """
    Get all origins configuration for an environment.
    
    Args:
        environment: The environment (development, staging, production)
        
    Returns:
        Dictionary with cors_origins, csp_connect, csp_worker, csp_script lists
    """
    return {
        "cors_origins": SecurityOriginsConfig.get_cors_origins(environment),
        "csp_connect": SecurityOriginsConfig.get_csp_connect_sources(environment),
        "csp_worker": SecurityOriginsConfig.get_csp_worker_sources(environment),
        "csp_script": SecurityOriginsConfig.get_csp_script_sources(environment)
    }