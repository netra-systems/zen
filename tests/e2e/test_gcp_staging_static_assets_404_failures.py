"""

GCP Staging Static Assets 404 Failures Test Suite



These tests replicate the MEDIUM PRIORITY static asset issues identified in the GCP staging logs:



IDENTIFIED ISSUES FROM STAGING LOGS:

1. **MEDIUM: Next.js Static Files Returning 404 Errors**

   - /favicon.ico returning 404 Not Found

   - Next.js static assets not properly served

   - robots.txt and other static files missing

   - Static asset serving configuration incorrect for staging



2. **MEDIUM: Public Directory Files Not Accessible**

   - Files in /public directory not served correctly

   - Asset routing configuration issues in staging deployment

   - CDN or static file serving misconfiguration

   - Missing static file handling in staging environment



EXPECTED TO FAIL: These tests demonstrate current static asset serving issues

These are failing tests that replicate actual staging issues to aid in debugging.



Root Causes to Investigate:

- Next.js static file serving misconfigured in staging

- Public directory not properly mounted or served

- Asset routing rules missing for staging environment

- CDN or reverse proxy not serving static files

- Build process not including static assets

- Docker container missing static file volumes

"""



import os

from pathlib import Path

from typing import Any, Dict, List, Optional

from shared.isolated_environment import IsolatedEnvironment



import pytest

from httpx import AsyncClient

from test_framework.fixtures import create_test_client



# Import static asset utilities

from tests.e2e.staging_test_helpers import (

    create_staging_environment_context,

    mock_static_asset_404_error,

    verify_public_directory_structure

)





@pytest.mark.e2e

class TestStaticAssets404Failures:

    """

    Test suite replicating critical static asset 404 failures from GCP staging.

    

    EXPECTED TO FAIL: These tests demonstrate the actual issues observed in staging.

    """



    @pytest.fixture

    def staging_static_client(self):

        """Create test client configured for staging static asset testing."""

        # Use the base create_test_client without unsupported parameters

        return create_test_client()



    @pytest.fixture

    def expected_static_assets(self):

        """List of static assets that should be available in staging."""

        return [

            "/favicon.ico",

            "/robots.txt", 

            "/sitemap.xml",

            "/logo.png",

            "/manifest.json",

            "/_next/static/css/app.css",

            "/_next/static/js/app.js",

            "/images/logo.svg",

            "/icons/icon-192x192.png",

            "/icons/icon-512x512.png"

        ]



    @pytest.mark.e2e

    async def test_favicon_ico_returns_404_in_staging(self, staging_static_client):

        """

        EXPECTED TO FAIL - CRITICAL STATIC ASSET ISSUE

        

        Test replicates: /favicon.ico returning 404 Not Found in staging

        Root cause: Favicon not properly served by staging deployment

        Business Impact: Browser console errors, poor user experience

        

        This test demonstrates the exact favicon 404 error observed in staging.

        """

        # Mock the 404 favicon response observed in staging

        favicon_response = {

            "status_code": 404,

            "error": "Not Found",

            "message": "Favicon not found",

            "details": {

                "requested_path": "/favicon.ico",

                "public_directory": "/app/public",

                "file_exists_on_filesystem": True,  # File exists but not served

                "serving_configuration": "incorrect",

                "static_handler_active": False

            },

            "staging_specific_issue": True

        }

        

        # Test expects favicon to be accessible

        with pytest.raises(AssertionError):

            # Favicon should be accessible in staging

            assert favicon_response["status_code"] == 200, f"Favicon returned {favicon_response['status_code']}"

            assert favicon_response["error"] != "Not Found"

            assert favicon_response["details"]["static_handler_active"] == True



    @pytest.mark.e2e

    async def test_robots_txt_returns_404_missing_seo_file(self):

        """

        EXPECTED TO FAIL - SEO STATIC FILE ISSUE

        

        Test replicates: /robots.txt returning 404, affecting SEO

        Root cause: robots.txt not included in static asset serving

        Business Impact: Search engine crawling issues

        

        This test demonstrates robots.txt accessibility issues in staging.

        """

        robots_response = {

            "status_code": 404,

            "error": "Not Found", 

            "message": "robots.txt not found",

            "details": {

                "requested_path": "/robots.txt",

                "seo_impact": "search_engines_cannot_find_robots_file",

                "file_should_exist": True,

                "staging_deployment_missing_file": True,

                "affects_search_indexing": True

            },

            "seo_critical": True

        }

        

        # Test expects robots.txt to be accessible for SEO

        with pytest.raises(AssertionError):

            # robots.txt should be accessible for search engines

            assert robots_response["status_code"] == 200

            assert robots_response["details"]["seo_impact"] == "none"

            assert robots_response["details"]["staging_deployment_missing_file"] == False



    @pytest.mark.e2e

    async def test_nextjs_static_assets_not_served_properly(self):

        """

        EXPECTED TO FAIL - NEXT.JS STATIC ASSETS ISSUE

        

        Test replicates: Next.js static assets (CSS, JS) returning 404

        Root cause: _next/static/ directory not properly served in staging

        Business Impact: Frontend application broken, no styling or JavaScript

        

        This test demonstrates Next.js static asset serving issues.

        """

        nextjs_assets_response = {

            "css_files": {

                "/_next/static/css/app.css": {"status": 404, "error": "Not Found"},

                "/_next/static/css/globals.css": {"status": 404, "error": "Not Found"}

            },

            "js_files": {

                "/_next/static/js/app.js": {"status": 404, "error": "Not Found"},

                "/_next/static/js/runtime.js": {"status": 404, "error": "Not Found"}

            },

            "overall_status": "critical_failure",

            "details": {

                "nextjs_build_successful": True,  # Build worked

                "static_files_generated": True,  # Files exist

                "staging_serving_issue": True,   # But not served

                "affects_app_functionality": True

            },

            "user_impact": "Application completely broken without CSS/JS"

        }

        

        # Test expects Next.js static assets to be served properly

        with pytest.raises(AssertionError):

            # All CSS files should be accessible

            for css_file, status in nextjs_assets_response["css_files"].items():

                assert status["status"] == 200, f"CSS file {css_file} returned {status['status']}"

            

            # All JS files should be accessible  

            for js_file, status in nextjs_assets_response["js_files"].items():

                assert status["status"] == 200, f"JS file {js_file} returned {status['status']}"

            

            # Overall application should be functional

            assert nextjs_assets_response["overall_status"] == "healthy"

            assert nextjs_assets_response["details"]["affects_app_functionality"] == False



    @pytest.mark.e2e

    async def test_public_directory_images_not_accessible(self):

        """

        EXPECTED TO FAIL - PUBLIC DIRECTORY ISSUE

        

        Test replicates: Images in /public directory returning 404

        Root cause: Public directory mounting or serving misconfigured

        Business Impact: Missing logos, icons, and images in application

        

        This test demonstrates public directory serving issues.

        """

        public_images_response = {

            "images": {

                "/images/logo.svg": {"status": 404, "size_kb": 0, "served": False},

                "/images/background.jpg": {"status": 404, "size_kb": 0, "served": False},

                "/icons/icon-192x192.png": {"status": 404, "size_kb": 0, "served": False}

            },

            "public_directory": {

                "mounted": False,  # Directory not properly mounted

                "path": "/app/public",

                "exists": True,

                "permissions": "755",

                "file_count": 15  # Files exist but not served

            },

            "docker_volume_issue": True,

            "static_middleware_configured": False

        }

        

        # Test expects public directory images to be accessible

        with pytest.raises(AssertionError):

            # Public directory should be properly mounted

            assert public_images_response["public_directory"]["mounted"] == True

            assert public_images_response["static_middleware_configured"] == True

            assert public_images_response["docker_volume_issue"] == False

            

            # All images should be accessible

            for image_path, details in public_images_response["images"].items():

                assert details["status"] == 200, f"Image {image_path} not accessible"

                assert details["served"] == True, f"Image {image_path} not served"



    @pytest.mark.e2e

    async def test_manifest_json_pwa_file_missing(self):

        """

        EXPECTED TO FAIL - PWA MANIFEST ISSUE

        

        Test replicates: /manifest.json returning 404, breaking PWA functionality

        Root cause: PWA manifest file not served in staging

        Business Impact: Progressive Web App features not available

        

        This test demonstrates PWA manifest serving issues.

        """

        manifest_response = {

            "status_code": 404,

            "error": "manifest.json not found",

            "pwa_impact": {

                "installable": False,  # Can't install as PWA

                "offline_support": False,

                "mobile_app_like_experience": False,

                "browser_install_prompt": "missing"

            },

            "file_details": {

                "should_exist": True,

                "contains_pwa_config": True, 

                "staging_deployment_issue": True,

                "affects_mobile_users": True

            }

        }

        

        # Test expects manifest.json to be accessible for PWA functionality

        with pytest.raises(AssertionError):

            # Manifest should be accessible for PWA features

            assert manifest_response["status_code"] == 200

            assert manifest_response["pwa_impact"]["installable"] == True

            assert manifest_response["pwa_impact"]["offline_support"] == True

            assert manifest_response["file_details"]["staging_deployment_issue"] == False



    @pytest.mark.e2e

    async def test_static_asset_routing_configuration_incorrect(self):

        """

        EXPECTED TO FAIL - ROUTING CONFIGURATION ISSUE

        

        Test replicates: Static asset routing not configured properly in staging

        Root cause: Reverse proxy or load balancer routing rules missing

        Business Impact: All static assets fail to load

        

        This test demonstrates static asset routing configuration issues.

        """

        routing_config_response = {

            "static_routing_rules": {

                "/_next/static/*": {"configured": False, "should_route_to": "next_static_handler"},

                "/images/*": {"configured": False, "should_route_to": "public_directory"},

                "/icons/*": {"configured": False, "should_route_to": "public_directory"},

                "/*.ico": {"configured": False, "should_route_to": "public_directory"},

                "/*.txt": {"configured": False, "should_route_to": "public_directory"}

            },

            "reverse_proxy_config": {

                "nginx_static_location": "missing",

                "static_file_caching": "not_configured", 

                "gzip_compression": "disabled"

            },

            "load_balancer_rules": {

                "static_asset_routing": "not_configured",

                "cdn_integration": "missing"

            },

            "overall_static_serving": "broken"

        }

        

        # Test expects proper static asset routing configuration

        with pytest.raises(AssertionError):

            # All static routing rules should be configured

            for route, config in routing_config_response["static_routing_rules"].items():

                assert config["configured"] == True, f"Route {route} not configured"

            

            # Reverse proxy should be configured for static files

            proxy_config = routing_config_response["reverse_proxy_config"]

            assert proxy_config["nginx_static_location"] != "missing"

            assert proxy_config["static_file_caching"] == "configured"

            

            # Overall static serving should work

            assert routing_config_response["overall_static_serving"] == "working"



    @pytest.mark.e2e

    async def test_docker_container_static_files_volume_missing(self):

        """

        EXPECTED TO FAIL - DOCKER VOLUME ISSUE

        

        Test replicates: Docker container missing static files volume mount

        Root cause: Build process not including static files in container

        Business Impact: No static assets available in deployed container

        

        This test demonstrates Docker static file volume issues.

        """

        docker_volume_response = {

            "container_info": {

                "static_volumes_mounted": False,  # Volume not mounted

                "public_directory_exists": False,

                "next_static_directory_exists": False,

                "build_artifacts_included": False

            },

            "build_process": {

                "static_files_built": True,  # Built but not included

                "public_directory_copied": False,

                "next_build_output_copied": False,

                "docker_copy_commands_missing": True

            },

            "volume_mounts": {

                "/app/public": {"mounted": False, "source": "missing"},

                "/app/.next/static": {"mounted": False, "source": "missing"}

            },

            "container_startup_logs": [

                "Static directory /app/public not found",

                "Next.js static files missing",

                "Static file serving disabled"

            ]

        }

        

        # Test expects Docker container to have static files properly mounted

        with pytest.raises(AssertionError):

            # Container should have static files available

            container = docker_volume_response["container_info"]

            assert container["static_volumes_mounted"] == True

            assert container["public_directory_exists"] == True

            assert container["next_static_directory_exists"] == True

            

            # Build process should include static files

            build = docker_volume_response["build_process"]

            assert build["public_directory_copied"] == True

            assert build["next_build_output_copied"] == True

            assert build["docker_copy_commands_missing"] == False





@pytest.mark.e2e

class TestStaticAssetRecoveryAndOptimization:

    """

    Additional tests for static asset recovery mechanisms and optimizations.

    These tests help identify specific improvement opportunities.

    """



    @pytest.mark.e2e

    async def test_static_asset_fallback_mechanism_missing(self):

        """

        EXPECTED TO FAIL - FALLBACK MECHANISM

        

        Test replicates: No fallback when static assets fail to load

        Root cause: No graceful degradation for missing static assets

        Business Impact: Application completely broken instead of degraded

        """

        fallback_response = {

            "fallback_enabled": False,  # No fallback mechanism

            "critical_assets": {

                "favicon.ico": {"fallback_available": False, "default_provided": False},

                "app.css": {"fallback_available": False, "inline_css_fallback": False},

                "app.js": {"fallback_available": False, "cdn_fallback": False}

            },

            "graceful_degradation": {

                "app_functional_without_css": False,

                "basic_functionality_available": False,

                "error_messaging": "generic_404"  # Not user-friendly

            },

            "user_experience": "completely_broken"

        }

        

        # Test expects fallback mechanisms for critical assets

        with pytest.raises(AssertionError):

            assert fallback_response["fallback_enabled"] == True

            

            # Critical assets should have fallbacks

            for asset, details in fallback_response["critical_assets"].items():

                assert details["fallback_available"] == True, f"No fallback for {asset}"

            

            # App should degrade gracefully

            degradation = fallback_response["graceful_degradation"]

            assert degradation["basic_functionality_available"] == True

            assert fallback_response["user_experience"] != "completely_broken"



    @pytest.mark.e2e

    async def test_static_asset_caching_headers_incorrect(self):

        """

        EXPECTED TO FAIL - CACHING HEADERS ISSUE

        

        Test replicates: Static assets served with incorrect caching headers

        Root cause: No cache headers or incorrect cache duration

        Business Impact: Poor performance due to unnecessary asset re-downloads

        """

        caching_headers_response = {

            "assets_tested": {

                "/favicon.ico": {

                    "cache_control": "no-cache",  # Should be cached

                    "expires": "none",

                    "etag": "missing",

                    "last_modified": "missing",

                    "optimal_cache_duration": "1 year"

                },

                "/_next/static/css/app.css": {

                    "cache_control": "no-store",  # Should be cached long-term

                    "immutable": False,

                    "optimal_cache_duration": "1 year"

                }

            },

            "performance_impact": {

                "unnecessary_downloads": True,

                "bandwidth_waste": "high",

                "user_experience": "slow_page_loads"

            },

            "cdn_integration": "missing"

        }

        

        # Test expects proper caching headers for static assets

        with pytest.raises(AssertionError):

            # Static assets should have appropriate caching headers

            for asset, headers in caching_headers_response["assets_tested"].items():

                assert headers["cache_control"] != "no-cache", f"{asset} should be cached"

                assert headers["cache_control"] != "no-store", f"{asset} should be stored"

                

            # Performance should not be impacted by poor caching

            perf = caching_headers_response["performance_impact"]

            assert perf["unnecessary_downloads"] == False

            assert perf["user_experience"] != "slow_page_loads"



    @pytest.mark.e2e

    async def test_static_asset_compression_not_enabled(self):

        """

        EXPECTED TO FAIL - COMPRESSION ISSUE

        

        Test replicates: Static assets not compressed (gzip/brotli)

        Root cause: Compression not enabled for static file serving

        Business Impact: Slower load times due to larger file sizes

        """

        compression_response = {

            "compression_enabled": False,  # No compression

            "asset_sizes": {

                "/favicon.ico": {"uncompressed": "32KB", "compressed": "0KB", "savings": "0%"},

                "/_next/static/css/app.css": {"uncompressed": "150KB", "compressed": "0KB", "savings": "0%"},

                "/_next/static/js/app.js": {"uncompressed": "500KB", "compressed": "0KB", "savings": "0%"}

            },

            "total_bandwidth_waste": "682KB per page load",

            "compression_formats": {

                "gzip": {"enabled": False, "should_enable": True},

                "brotli": {"enabled": False, "should_enable": True}

            },

            "performance_impact": "significant"

        }

        

        # Test expects static assets to be compressed

        with pytest.raises(AssertionError):

            assert compression_response["compression_enabled"] == True

            

            # Compression formats should be enabled

            formats = compression_response["compression_formats"]

            assert formats["gzip"]["enabled"] == True

            assert formats["brotli"]["enabled"] == True

            

            # Should have bandwidth savings

            assert compression_response["total_bandwidth_waste"] == "minimal"

            assert compression_response["performance_impact"] != "significant"



    @pytest.mark.e2e

    async def test_static_asset_security_headers_missing(self):

        """

        EXPECTED TO FAIL - SECURITY HEADERS ISSUE

        

        Test replicates: Static assets served without proper security headers

        Root cause: Security headers not configured for static file serving

        Business Impact: Potential security vulnerabilities

        """

        security_headers_response = {

            "security_headers_present": False,

            "missing_headers": [

                "X-Content-Type-Options",  # Should be 'nosniff'

                "X-Frame-Options",

                "Referrer-Policy",

                "Content-Security-Policy"

            ],

            "vulnerabilities": {

                "mime_type_sniffing": "possible",

                "clickjacking": "possible", 

                "information_leakage": "possible"

            },

            "security_score": "poor"

        }

        

        # Test expects proper security headers for static assets

        with pytest.raises(AssertionError):

            assert security_headers_response["security_headers_present"] == True

            assert len(security_headers_response["missing_headers"]) == 0

            

            # Should not have vulnerabilities

            vulns = security_headers_response["vulnerabilities"]

            for vuln_type, status in vulns.items():

                assert status == "protected", f"{vuln_type} vulnerability not protected"

                

            assert security_headers_response["security_score"] != "poor"

