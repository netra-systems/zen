#!/usr/bin/env python3
"""
MCP Dependency Diagnostic Script

Validates MCP dependency availability and provides detailed diagnostics
for troubleshooting integration test collection issues.

This script helps identify:
1. Missing MCP packages
2. Version incompatibilities
3. Import errors
4. Environment-specific issues

Usage:
    python scripts/diagnose_mcp_dependencies.py
"""

import sys
import traceback
from typing import Dict, Any, List

def check_basic_imports() -> Dict[str, Any]:
    """Check if basic Python packages can be imported."""
    results = {}
    
    basic_packages = ['asyncio', 'typing', 'logging', 'json']
    for package in basic_packages:
        try:
            __import__(package)
            results[package] = {'status': 'success', 'error': None}
        except ImportError as e:
            results[package] = {'status': 'failed', 'error': str(e)}
    
    return results

def check_mcp_dependencies() -> Dict[str, Any]:
    """Check MCP-specific dependencies."""
    results = {}
    
    # Test fastmcp package
    try:
        import fastmcp
        results['fastmcp'] = {
            'status': 'success', 
            'version': getattr(fastmcp, '__version__', 'unknown'),
            'error': None
        }
    except ImportError as e:
        results['fastmcp'] = {'status': 'failed', 'error': str(e), 'version': None}
    except Exception as e:
        results['fastmcp'] = {'status': 'error', 'error': str(e), 'version': None}
    
    # Test mcp package
    try:
        import mcp
        results['mcp'] = {
            'status': 'success',
            'version': getattr(mcp, '__version__', 'unknown'),
            'error': None
        }
    except ImportError as e:
        results['mcp'] = {'status': 'failed', 'error': str(e), 'version': None}
    except Exception as e:
        results['mcp'] = {'status': 'error', 'error': str(e), 'version': None}
    
    # Test mcp.types specifically
    try:
        from mcp.types import Tool, TextContent, ImageContent
        results['mcp.types'] = {
            'status': 'success',
            'classes': ['Tool', 'TextContent', 'ImageContent'],
            'error': None
        }
    except ImportError as e:
        results['mcp.types'] = {'status': 'failed', 'error': str(e), 'classes': None}
    except Exception as e:
        results['mcp.types'] = {'status': 'error', 'error': str(e), 'classes': None}
    
    return results

def check_netra_mcp_integration() -> Dict[str, Any]:
    """Check Netra's MCP integration components."""
    results = {}
    
    # Add current directory to path
    import os
    sys.path.insert(0, os.getcwd())
    
    # Test MCP routes module
    try:
        from netra_backend.app.routes.mcp import is_mcp_available, get_mcp_status
        results['mcp_routes'] = {
            'status': 'success',
            'mcp_available': is_mcp_available(),
            'mcp_status': get_mcp_status(),
            'error': None
        }
    except ImportError as e:
        results['mcp_routes'] = {'status': 'import_failed', 'error': str(e)}
    except Exception as e:
        results['mcp_routes'] = {'status': 'error', 'error': str(e)}
    
    # Test MCP handlers
    try:
        from netra_backend.app.routes.mcp.handlers import MCPHandlers
        results['mcp_handlers'] = {'status': 'success', 'error': None}
    except ImportError as e:
        results['mcp_handlers'] = {'status': 'import_failed', 'error': str(e)}
    except Exception as e:
        results['mcp_handlers'] = {'status': 'error', 'error': str(e)}
    
    # Test MCP service
    try:
        from netra_backend.app.services.mcp_service import MCPService
        results['mcp_service'] = {'status': 'success', 'error': None}
    except ImportError as e:
        results['mcp_service'] = {'status': 'import_failed', 'error': str(e)}
    except Exception as e:
        results['mcp_service'] = {'status': 'error', 'error': str(e)}
    
    return results

def check_app_integration() -> Dict[str, Any]:
    """Check if the main app can load with MCP integration."""
    results = {}
    
    try:
        from netra_backend.app.main import app
        results['main_app'] = {'status': 'success', 'error': None}
    except ImportError as e:
        results['main_app'] = {'status': 'import_failed', 'error': str(e)}
    except Exception as e:
        results['main_app'] = {'status': 'error', 'error': str(e)}
    
    # Test route imports
    try:
        from netra_backend.app.core.app_factory_route_imports import _import_core_routers
        routers = _import_core_routers()
        results['core_routers'] = {
            'status': 'success',
            'router_count': len(routers),
            'has_mcp_router': 'mcp_router' in routers,
            'available_routers': list(routers.keys()),
            'error': None
        }
    except ImportError as e:
        results['core_routers'] = {'status': 'import_failed', 'error': str(e)}
    except Exception as e:
        results['core_routers'] = {'status': 'error', 'error': str(e)}
    
    return results

def check_test_collection() -> Dict[str, Any]:
    """Check if integration tests can be collected."""
    results = {}
    
    try:
        import subprocess
        import os
        
        # Change to the project directory
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Try to collect a specific integration test
        cmd = [
            sys.executable, '-m', 'pytest', 
            'tests/integration/agent_execution_flows/test_agent_execution_context_management.py',
            '--collect-only', '-q'
        ]
        
        result = subprocess.run(
            cmd, 
            cwd=project_dir,
            capture_output=True, 
            text=True, 
            timeout=30
        )
        
        results['test_collection'] = {
            'status': 'success' if result.returncode == 0 else 'failed',
            'return_code': result.returncode,
            'stdout_lines': len(result.stdout.split('\n')) if result.stdout else 0,
            'stderr_lines': len(result.stderr.split('\n')) if result.stderr else 0,
            'has_mcp_errors': 'mcp' in result.stderr.lower() if result.stderr else False,
            'error': result.stderr if result.returncode != 0 else None
        }
        
    except subprocess.TimeoutExpired:
        results['test_collection'] = {'status': 'timeout', 'error': 'Test collection timed out'}
    except Exception as e:
        results['test_collection'] = {'status': 'error', 'error': str(e)}
    
    return results

def get_environment_info() -> Dict[str, Any]:
    """Get environment information."""
    import platform
    import os
    
    return {
        'python_version': sys.version,
        'platform': platform.platform(),
        'working_directory': os.getcwd(),
        'python_path': sys.path[:3],  # First 3 entries
        'environment_vars': {
            'ENVIRONMENT': os.environ.get('ENVIRONMENT', 'not_set'),
            'PYTHONPATH': os.environ.get('PYTHONPATH', 'not_set'),
            'PATH': len(os.environ.get('PATH', '').split(os.pathsep))
        }
    }

def print_diagnostics():
    """Print comprehensive MCP diagnostics."""
    print("=" * 80)
    print("MCP DEPENDENCY DIAGNOSTIC REPORT")
    print("=" * 80)
    
    # Environment info
    print("\n[ENV] ENVIRONMENT INFORMATION")
    print("-" * 40)
    env_info = get_environment_info()
    print(f"Python Version: {env_info['python_version']}")
    print(f"Platform: {env_info['platform']}")
    print(f"Working Directory: {env_info['working_directory']}")
    print(f"Environment: {env_info['environment_vars']['ENVIRONMENT']}")
    
    # Basic imports
    print("\n[PKG] BASIC PACKAGE IMPORTS")
    print("-" * 40)
    basic_results = check_basic_imports()
    for package, result in basic_results.items():
        status = "[OK]" if result['status'] == 'success' else "[FAIL]"
        print(f"{status} {package}: {result['status']}")
        if result['error']:
            print(f"   Error: {result['error']}")
    
    # MCP dependencies
    print("\n[MCP] MCP DEPENDENCY CHECK")
    print("-" * 40)
    mcp_results = check_mcp_dependencies()
    all_mcp_success = True
    
    for package, result in mcp_results.items():
        if result['status'] == 'success':
            print(f"[OK] {package}: {result['status']}")
            if 'version' in result and result['version']:
                print(f"   Version: {result['version']}")
            if 'classes' in result and result['classes']:
                print(f"   Classes: {', '.join(result['classes'])}")
        else:
            all_mcp_success = False
            print(f"[FAIL] {package}: {result['status']}")
            print(f"   Error: {result['error']}")
    
    # Netra MCP integration
    print("\n[NETRA] NETRA MCP INTEGRATION")
    print("-" * 40)
    netra_results = check_netra_mcp_integration()
    all_netra_success = True
    
    for component, result in netra_results.items():
        if result['status'] == 'success':
            print(f"[OK] {component}: {result['status']}")
            if 'mcp_available' in result:
                print(f"   MCP Available: {result['mcp_available']}")
            if 'mcp_status' in result:
                print(f"   MCP Mode: {result['mcp_status'].get('mode', 'unknown')}")
        else:
            all_netra_success = False
            print(f"[FAIL] {component}: {result['status']}")
            print(f"   Error: {result['error']}")
    
    # App integration
    print("\n[APP] APP INTEGRATION")
    print("-" * 40)
    app_results = check_app_integration()
    all_app_success = True
    
    for component, result in app_results.items():
        if result['status'] == 'success':
            print(f"[OK] {component}: {result['status']}")
            if 'has_mcp_router' in result:
                print(f"   MCP Router Included: {result['has_mcp_router']}")
            if 'router_count' in result:
                print(f"   Total Routers: {result['router_count']}")
        else:
            all_app_success = False
            print(f"[FAIL] {component}: {result['status']}")
            print(f"   Error: {result['error']}")
    
    # Test collection
    print("\n[TEST] TEST COLLECTION")
    print("-" * 40)
    test_results = check_test_collection()
    
    if test_results['test_collection']['status'] == 'success':
        print(f"[OK] test_collection: success")
        print(f"   Tests discovered: {test_results['test_collection']['stdout_lines']} lines")
        print(f"   MCP-related errors: {test_results['test_collection']['has_mcp_errors']}")
    else:
        print(f"[FAIL] test_collection: {test_results['test_collection']['status']}")
        if test_results['test_collection']['error']:
            print(f"   Error: {test_results['test_collection']['error']}")
    
    # Summary
    print("\n[SUMMARY] RESULTS")
    print("-" * 40)
    if all_mcp_success and all_netra_success and all_app_success:
        print("[SUCCESS] ALL CHECKS PASSED - MCP integration is working correctly")
        print("   Integration tests should collect without MCP-related errors")
    else:
        print("[WARNING] ISSUES DETECTED:")
        if not all_mcp_success:
            print("   - MCP dependency issues found")
        if not all_netra_success:
            print("   - Netra MCP integration issues found") 
        if not all_app_success:
            print("   - App integration issues found")
        
        print("\n[REMEDIATION] RECOMMENDATIONS:")
        if not all_mcp_success:
            print("   1. Install missing MCP dependencies: pip install fastmcp mcp")
        print("   2. Restart development environment")
        print("   3. Run integration tests with --verbose flag for detailed errors")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    try:
        print_diagnostics()
    except Exception as e:
        print(f"[ERROR] DIAGNOSTIC SCRIPT FAILED: {e}")
        traceback.print_exc()
        sys.exit(1)