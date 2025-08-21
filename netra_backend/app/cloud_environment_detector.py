"""Cloud environment detection utilities - part of modular config_loader split."""

from typing import Optional

from netra_backend.app.config import get_config
from netra_backend.app.logging_config import central_logger as logger


def _check_k_service_for_staging() -> str:
    """Check K_SERVICE environment variable for staging."""
    config = get_config()
    k_service = config.k_service
    if k_service and "staging" in k_service.lower():
        logger.debug(f"Staging from K_SERVICE: {k_service}")
        return "staging"
    return ""


def _check_pr_number_for_staging() -> str:
    """Check PR_NUMBER environment variable for staging."""
    config = get_config()
    if config.pr_number:
        logger.debug(f"Staging from PR_NUMBER")
        return "staging"
    return ""


def detect_cloud_run_environment() -> Optional[str]:
    """Detect if running in Cloud Run and determine environment."""
    config = get_config()
    if not config.k_service:
        return None
    env = _check_k_service_for_staging()
    if env:
        return env
    env = _check_pr_number_for_staging()
    if env:
        return env
    return "production"


def detect_app_engine_environment() -> Optional[str]:
    """Detect if running in App Engine and determine environment."""
    config = get_config()
    if not config.gae_application:
        return None
    
    gae_app = config.gae_application or ""
    gae_version = config.gae_version or ""
    
    if "staging" in gae_app.lower() or "staging" in gae_version.lower():
        logger.debug(f"Staging from GAE: {gae_app}/{gae_version}")
        return "staging"
    
    return "production"


class CloudEnvironmentDetector:
    """Detects cloud environment and platform."""
    
    def __init__(self):
        self.cloud_platform: Optional[str] = None
        self._cached_result: Optional[str] = None
    
    def detect_environment(self) -> Optional[str]:
        """Detect cloud environment with caching."""
        if self._cached_result is not None:
            return self._cached_result
        
        # Cloud Run takes precedence
        cloud_run_env = detect_cloud_run_environment()
        if cloud_run_env:
            self.cloud_platform = "cloud_run"
            self._cached_result = cloud_run_env
            return cloud_run_env
        
        # Then App Engine
        app_engine_env = detect_app_engine_environment()
        if app_engine_env:
            self.cloud_platform = "app_engine"
            self._cached_result = app_engine_env
            return app_engine_env
        
        # Then GKE
        gke_env = self.detect_gke_environment()
        if gke_env:
            self.cloud_platform = "gke"
            self._cached_result = gke_env
            return gke_env
        
        return None
    
    def detect_gke_environment(self) -> Optional[str]:
        """Detect Google Kubernetes Engine environment."""
        config = get_config()
        if not (config.kubernetes_service_host and config.google_cloud.project_id):
            return None
        return "production"