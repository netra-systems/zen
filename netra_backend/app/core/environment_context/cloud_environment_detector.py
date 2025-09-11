"""
CloudEnvironmentDetector - Robust environment detection for Cloud Run and other platforms.

This module provides comprehensive environment detection specifically designed to work
in Cloud Run staging environments and prevent Golden Path validation failures.

ROOT CAUSE RESOLUTION: 
- Eliminates DEVELOPMENT defaults that cause localhost:8081 connection attempts in staging
- Provides definitive environment detection using Cloud Run metadata
- Implements fail-fast validation when environment cannot be determined

Business Impact: Protects $500K+ ARR by ensuring Golden Path validation works in staging
"""

import os
import json
import asyncio
import aiohttp
from datetime import UTC, datetime
from typing import Dict, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass

from netra_backend.app.logging_config import central_logger


class CloudPlatform(Enum):
    """Supported cloud platforms for deployment."""
    CLOUD_RUN = "cloud_run"
    APP_ENGINE = "app_engine" 
    GKE = "gke"
    UNKNOWN = "unknown"


class EnvironmentType(Enum):
    """Environment types with precise detection logic."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"  
    PRODUCTION = "production"
    UNKNOWN = "unknown"


@dataclass
class EnvironmentContext:
    """Complete environment context with cloud platform details."""
    environment_type: EnvironmentType
    cloud_platform: CloudPlatform
    service_name: Optional[str] = None
    project_id: Optional[str] = None
    region: Optional[str] = None
    revision: Optional[str] = None
    confidence_score: float = 0.0
    detection_metadata: Dict[str, Any] = None
    detection_timestamp: datetime = None
    
    def __post_init__(self):
        if self.detection_metadata is None:
            self.detection_metadata = {}
        if self.detection_timestamp is None:
            self.detection_timestamp = datetime.now(UTC)


class CloudEnvironmentDetector:
    """
    Comprehensive cloud environment detection with fail-fast validation.
    
    CRITICAL FEATURES:
    - Cloud Run metadata API for definitive staging detection
    - Multiple detection strategies with confidence scoring
    - Fail-fast when environment cannot be determined
    - Cache results to avoid repeated expensive calls
    """
    
    def __init__(self):
        self.logger = central_logger.get_logger(__name__)
        self._cache: Optional[EnvironmentContext] = None
        self._metadata_endpoint = "http://metadata.google.internal/computeMetadata/v1/"
        self._detection_strategies = [
            self._detect_via_cloud_run_metadata,
            self._detect_via_environment_variables,
            self._detect_via_gcp_service_variables,
            self._detect_via_app_engine_metadata,
        ]
    
    async def detect_environment_context(self, force_refresh: bool = False) -> EnvironmentContext:
        """
        Detect complete environment context with high confidence.
        
        Args:
            force_refresh: Skip cache and perform fresh detection
            
        Returns:
            EnvironmentContext with environment type and platform details
            
        Raises:
            RuntimeError: When environment cannot be determined with confidence
        """
        if self._cache and not force_refresh:
            self.logger.debug("Returning cached environment context")
            return self._cache
        
        self.logger.info("Starting comprehensive environment detection")
        
        best_context = None
        best_confidence = 0.0
        detection_results = []
        
        # Try all detection strategies
        for strategy in self._detection_strategies:
            try:
                context = await strategy()
                if context and context.confidence_score > best_confidence:
                    best_context = context
                    best_confidence = context.confidence_score
                detection_results.append({
                    "strategy": strategy.__name__,
                    "result": context.environment_type.value if context else None,
                    "confidence": context.confidence_score if context else 0.0
                })
            except Exception as e:
                self.logger.warning(f"Detection strategy {strategy.__name__} failed: {e}")
                detection_results.append({
                    "strategy": strategy.__name__,
                    "result": None,
                    "confidence": 0.0,
                    "error": str(e)
                })
        
        # Validate detection confidence
        if not best_context or best_confidence < 0.7:
            self._log_detection_failure(detection_results, best_confidence)
            raise RuntimeError(
                f"Cannot determine environment with sufficient confidence. "
                f"Best confidence: {best_confidence:.2f}, required: 0.7. "
                f"This is a critical failure for Golden Path validation."
            )
        
        # Cache and log successful detection
        self._cache = best_context
        self._log_successful_detection(best_context, detection_results)
        
        return best_context
    
    async def _detect_via_cloud_run_metadata(self) -> Optional[EnvironmentContext]:
        """
        Detect environment using Cloud Run metadata API.
        
        This is the most reliable method for Cloud Run environments.
        Uses the GCP metadata service to get definitive service information.
        """
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5.0)) as session:
                # Get service name
                service_response = await self._fetch_metadata(
                    session, "instance/attributes/goog-cloudrun-service-name"
                )
                if not service_response:
                    return None
                
                service_name = service_response.strip()
                
                # Get additional Cloud Run metadata
                project_id = await self._fetch_metadata(session, "project/project-id")
                region = await self._fetch_metadata(session, "instance/region")
                revision = await self._fetch_metadata(session, "instance/attributes/goog-revision")
                
                # Extract region name from full path if needed
                if region and "/" in region:
                    region = region.split("/")[-1]
                
                # Determine environment from service name
                environment_type = self._classify_service_environment(service_name)
                
                confidence = 0.9  # High confidence for Cloud Run metadata
                
                return EnvironmentContext(
                    environment_type=environment_type,
                    cloud_platform=CloudPlatform.CLOUD_RUN,
                    service_name=service_name,
                    project_id=project_id,
                    region=region,
                    revision=revision,
                    confidence_score=confidence,
                    detection_metadata={
                        "method": "cloud_run_metadata",
                        "service_name": service_name,
                        "project_id": project_id,
                        "region": region,
                        "revision": revision
                    }
                )
                
        except asyncio.TimeoutError:
            self.logger.debug("Cloud Run metadata API timeout - likely not running in Cloud Run")
            return None
        except Exception as e:
            self.logger.debug(f"Cloud Run metadata detection failed: {e}")
            return None
    
    async def _detect_via_environment_variables(self) -> Optional[EnvironmentContext]:
        """
        Detect environment using standard environment variables.
        
        Checks ENVIRONMENT variable and other standard indicators.
        """
        environment_var = os.environ.get("ENVIRONMENT", "").lower()
        k_service = os.environ.get("K_SERVICE", "")
        
        if not environment_var and not k_service:
            return None
        
        # Direct ENVIRONMENT variable
        if environment_var:
            env_type = self._parse_environment_type(environment_var)
            confidence = 0.8 if env_type != EnvironmentType.UNKNOWN else 0.3
            
            return EnvironmentContext(
                environment_type=env_type,
                cloud_platform=CloudPlatform.CLOUD_RUN if k_service else CloudPlatform.UNKNOWN,
                service_name=k_service if k_service else None,
                confidence_score=confidence,
                detection_metadata={
                    "method": "environment_variables",
                    "environment_var": environment_var,
                    "k_service": k_service
                }
            )
        
        # Fallback to K_SERVICE analysis
        if k_service:
            env_type = self._classify_service_environment(k_service)
            confidence = 0.75 if env_type != EnvironmentType.UNKNOWN else 0.4
            
            return EnvironmentContext(
                environment_type=env_type,
                cloud_platform=CloudPlatform.CLOUD_RUN,
                service_name=k_service,
                confidence_score=confidence,
                detection_metadata={
                    "method": "k_service_analysis",
                    "k_service": k_service
                }
            )
        
        return None
    
    async def _detect_via_gcp_service_variables(self) -> Optional[EnvironmentContext]:
        """
        Detect environment using GCP-specific service variables.
        
        Analyzes various GCP environment variables for patterns.
        """
        gcp_vars = {
            "GOOGLE_CLOUD_PROJECT": os.environ.get("GOOGLE_CLOUD_PROJECT"),
            "GCP_PROJECT": os.environ.get("GCP_PROJECT"),
            "GCLOUD_PROJECT": os.environ.get("GCLOUD_PROJECT"),
            "K_REVISION": os.environ.get("K_REVISION"),
            "K_CONFIGURATION": os.environ.get("K_CONFIGURATION"),
        }
        
        # Filter out None values
        gcp_vars = {k: v for k, v in gcp_vars.items() if v}
        
        if not gcp_vars:
            return None
        
        # Analyze project ID for environment indicators
        project_id = gcp_vars.get("GOOGLE_CLOUD_PROJECT") or gcp_vars.get("GCP_PROJECT") or gcp_vars.get("GCLOUD_PROJECT")
        
        if project_id:
            if "staging" in project_id.lower():
                env_type = EnvironmentType.STAGING
                confidence = 0.7
            elif "prod" in project_id.lower() or "production" in project_id.lower():
                env_type = EnvironmentType.PRODUCTION 
                confidence = 0.7
            elif "dev" in project_id.lower() or "test" in project_id.lower():
                env_type = EnvironmentType.DEVELOPMENT
                confidence = 0.6
            else:
                env_type = EnvironmentType.UNKNOWN
                confidence = 0.3
            
            return EnvironmentContext(
                environment_type=env_type,
                cloud_platform=CloudPlatform.CLOUD_RUN,  # Assume Cloud Run if GCP vars present
                project_id=project_id,
                revision=gcp_vars.get("K_REVISION"),
                confidence_score=confidence,
                detection_metadata={
                    "method": "gcp_service_variables",
                    "project_id": project_id,
                    "gcp_vars": gcp_vars
                }
            )
        
        return None
    
    async def _detect_via_app_engine_metadata(self) -> Optional[EnvironmentContext]:
        """
        Detect environment using App Engine metadata.
        
        Checks for App Engine specific environment variables.
        """
        gae_application = os.environ.get("GAE_APPLICATION")
        gae_version = os.environ.get("GAE_VERSION")
        gae_service = os.environ.get("GAE_SERVICE")
        
        if not any([gae_application, gae_version, gae_service]):
            return None
        
        # Analyze App Engine variables for environment
        env_indicators = [gae_application, gae_version, gae_service]
        env_indicators = [x for x in env_indicators if x]  # Remove None values
        
        combined_text = " ".join(env_indicators).lower()
        
        if "staging" in combined_text:
            env_type = EnvironmentType.STAGING
            confidence = 0.8
        elif any(x in combined_text for x in ["prod", "production"]):
            env_type = EnvironmentType.PRODUCTION
            confidence = 0.8
        elif any(x in combined_text for x in ["dev", "development", "test"]):
            env_type = EnvironmentType.DEVELOPMENT
            confidence = 0.7
        else:
            env_type = EnvironmentType.PRODUCTION  # Default for App Engine
            confidence = 0.5
        
        return EnvironmentContext(
            environment_type=env_type,
            cloud_platform=CloudPlatform.APP_ENGINE,
            service_name=gae_service,
            project_id=gae_application,
            confidence_score=confidence,
            detection_metadata={
                "method": "app_engine_metadata",
                "gae_application": gae_application,
                "gae_version": gae_version,
                "gae_service": gae_service
            }
        )
    
    async def _fetch_metadata(self, session: aiohttp.ClientSession, endpoint: str) -> Optional[str]:
        """
        Fetch data from GCP metadata service.
        
        Args:
            session: HTTP client session
            endpoint: Metadata endpoint path
            
        Returns:
            Metadata value or None if not available
        """
        try:
            url = f"{self._metadata_endpoint}{endpoint}"
            headers = {"Metadata-Flavor": "Google"}
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    return None
                    
        except Exception as e:
            self.logger.debug(f"Failed to fetch metadata from {endpoint}: {e}")
            return None
    
    def _classify_service_environment(self, service_name: str) -> EnvironmentType:
        """
        Classify environment based on service name patterns.
        
        Args:
            service_name: Service name from Cloud Run or other platform
            
        Returns:
            Classified environment type
        """
        service_lower = service_name.lower()
        
        # Explicit staging patterns
        staging_patterns = ["staging", "stage", "-stg-", "_staging_"]
        if any(pattern in service_lower for pattern in staging_patterns):
            return EnvironmentType.STAGING
        
        # Explicit production patterns  
        production_patterns = ["production", "prod", "-prod-", "_prod_"]
        if any(pattern in service_lower for pattern in production_patterns):
            return EnvironmentType.PRODUCTION
        
        # Development patterns
        dev_patterns = ["development", "develop", "dev", "test", "-dev-", "_dev_", "_test_"]
        if any(pattern in service_lower for pattern in dev_patterns):
            return EnvironmentType.DEVELOPMENT
        
        # Special case: netra-backend-staging
        if "netra-backend-staging" == service_lower:
            return EnvironmentType.STAGING
        
        # Special case: netra-backend (production)
        if "netra-backend" == service_lower:
            return EnvironmentType.PRODUCTION
        
        return EnvironmentType.UNKNOWN
    
    def _parse_environment_type(self, environment_str: str) -> EnvironmentType:
        """Parse environment string into EnvironmentType enum."""
        env_lower = environment_str.lower().strip()
        
        if env_lower in ["staging", "stage"]:
            return EnvironmentType.STAGING
        elif env_lower in ["production", "prod"]:
            return EnvironmentType.PRODUCTION
        elif env_lower in ["development", "develop", "dev"]:
            return EnvironmentType.DEVELOPMENT
        elif env_lower in ["testing", "test"]:
            return EnvironmentType.TESTING
        else:
            return EnvironmentType.UNKNOWN
    
    def _log_successful_detection(self, context: EnvironmentContext, detection_results: list) -> None:
        """Log successful environment detection with details."""
        self.logger.info("=" * 60)
        self.logger.info("ENVIRONMENT DETECTION SUCCESS")
        self.logger.info("=" * 60)
        self.logger.info(f"Environment Type: {context.environment_type.value}")
        self.logger.info(f"Cloud Platform: {context.cloud_platform.value}")
        self.logger.info(f"Confidence Score: {context.confidence_score:.2f}")
        
        if context.service_name:
            self.logger.info(f"Service Name: {context.service_name}")
        if context.project_id:
            self.logger.info(f"Project ID: {context.project_id}")
        if context.region:
            self.logger.info(f"Region: {context.region}")
        
        self.logger.info(f"Detection Method: {context.detection_metadata.get('method', 'unknown')}")
        
        # Log all detection attempts for debugging
        self.logger.debug("All detection results:")
        for result in detection_results:
            self.logger.debug(f"  {result['strategy']}: {result['result']} (confidence: {result['confidence']:.2f})")
        
        self.logger.info("=" * 60)
    
    def _log_detection_failure(self, detection_results: list, best_confidence: float) -> None:
        """Log environment detection failure with detailed diagnostics."""
        self.logger.error("=" * 60)
        self.logger.error("ENVIRONMENT DETECTION FAILURE - CRITICAL")
        self.logger.error("=" * 60)
        self.logger.error(f"Best confidence achieved: {best_confidence:.2f} (required: 0.7)")
        self.logger.error("This will cause Golden Path validation to fail!")
        
        self.logger.error("\nDetection attempt results:")
        for result in detection_results:
            status = "SUCCESS" if result['confidence'] > 0.0 else "FAILED"
            error_info = f" - {result.get('error', 'No error')}" if 'error' in result else ""
            self.logger.error(f"  {result['strategy']}: {status} (confidence: {result['confidence']:.2f}){error_info}")
        
        # Environment variables diagnostic
        self.logger.error("\nEnvironment variables diagnostic:")
        env_vars_to_check = [
            "ENVIRONMENT", "K_SERVICE", "GOOGLE_CLOUD_PROJECT", 
            "GAE_APPLICATION", "GAE_VERSION", "K_REVISION"
        ]
        for var in env_vars_to_check:
            value = os.environ.get(var, "<NOT SET>")
            # Mask sensitive values
            if "project" in var.lower() and value != "<NOT SET>":
                value = f"{value[:6]}...{value[-3:]}" if len(value) > 9 else "***"
            self.logger.error(f"  {var}: {value}")
        
        self.logger.error("\nSuggested fixes:")
        self.logger.error("  1. Set ENVIRONMENT variable explicitly in deployment")
        self.logger.error("  2. Verify Cloud Run service name includes environment indicator")
        self.logger.error("  3. Check GCP project ID contains environment information")
        self.logger.error("=" * 60)
    
    def get_cached_context(self) -> Optional[EnvironmentContext]:
        """Get cached environment context without triggering detection."""
        return self._cache
    
    def clear_cache(self) -> None:
        """Clear cached detection results."""
        self._cache = None
        self.logger.debug("Environment detection cache cleared")


# Singleton instance for global usage
_detector_instance: Optional[CloudEnvironmentDetector] = None


def get_cloud_environment_detector() -> CloudEnvironmentDetector:
    """Get singleton CloudEnvironmentDetector instance."""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = CloudEnvironmentDetector()
    return _detector_instance


async def detect_current_environment() -> EnvironmentContext:
    """
    Convenience function to detect current environment.
    
    Returns:
        EnvironmentContext with current environment details
        
    Raises:
        RuntimeError: When environment cannot be determined
    """
    detector = get_cloud_environment_detector()
    return await detector.detect_environment_context()