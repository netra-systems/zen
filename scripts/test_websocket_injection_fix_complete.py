#!/usr/bin/env python
"""
COMPREHENSIVE WEBSOCKET INJECTION FIX TEST RUNNER

This script runs the complete test suite for the WebSocket injection fix
and validates that all components are working correctly.

Usage:
    python scripts/test_websocket_injection_fix_complete.py
    
Business Value: $500K+ ARR - Ensures core chat functionality works
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Any

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger


class WebSocketInjectionFixValidator:
    """Comprehensive validator for WebSocket injection fix."""
    
    def __init__(self):
        self.results = {
            'static_analysis': {'passed': 0, 'failed': 0, 'details': []},
            'unit_tests': {'passed': 0, 'failed': 0, 'details': []},
            'integration_tests': {'passed': 0, 'failed': 0, 'details': []},
            'regression_tests': {'passed': 0, 'failed': 0, 'details': []},
            'mission_critical_tests': {'passed': 0, 'failed': 0, 'details': []}
        }
        
    def validate_static_code_analysis(self) -> bool:
        """Validate WebSocket injection code is present."""
        logger.info("🔍 Running static code analysis...")
        
        files_to_check = [
            'netra_backend/app/dependencies.py',
            'netra_backend/app/services/service_factory.py', 
            'netra_backend/app/services/agent_service_core.py'
        ]
        
        required_patterns = [
            'get_websocket_manager',
            'websocket_manager',
            'MessageHandlerService',
            'try:',
            'except Exception'
        ]
        
        all_passed = True
        
        for file_path in files_to_check:
            full_path = project_root / file_path
            if not full_path.exists():
                logger.error(f"❌ File not found: {file_path}")
                all_passed = False
                self.results['static_analysis']['failed'] += 1
                continue
                
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            file_passed = True
            missing_patterns = []
            
            for pattern in required_patterns:
                if pattern not in content:
                    missing_patterns.append(pattern)
                    file_passed = False
                    
            if file_passed:
                logger.info(f"✅ {file_path} - All patterns found")
                self.results['static_analysis']['passed'] += 1
            else:
                logger.error(f"❌ {file_path} - Missing patterns: {missing_patterns}")
                self.results['static_analysis']['failed'] += 1
                self.results['static_analysis']['details'].append(f"{file_path}: Missing {missing_patterns}")
                all_passed = False
                
        return all_passed
        
    def run_test_suite(self, test_path: str, suite_name: str) -> bool:
        """Run a specific test suite."""
        logger.info(f"🧪 Running {suite_name}...")
        
        full_test_path = project_root / test_path
        if not full_test_path.exists():
            logger.error(f"❌ Test file not found: {test_path}")
            self.results[suite_name]['failed'] += 1
            return False
            
        try:
            # Run pytest on the specific test file
            result = subprocess.run([
                sys.executable, '-m', 'pytest', 
                str(full_test_path),
                '-v',
                '--tb=short',
                '--timeout=120',  # 2 minute timeout per test suite
                '--durations=10'
            ], capture_output=True, text=True, cwd=project_root)
            
            if result.returncode == 0:
                logger.info(f"✅ {suite_name} - PASSED")
                self.results[suite_name]['passed'] += 1
                
                # Extract test count from output
                if 'passed' in result.stdout:
                    import re
                    matches = re.findall(r'(\d+) passed', result.stdout)
                    if matches:
                        test_count = int(matches[-1])
                        self.results[suite_name]['details'].append(f"{test_count} tests passed")
                
                return True
            else:
                logger.error(f"❌ {suite_name} - FAILED")
                logger.error(f"STDOUT:\n{result.stdout}")
                logger.error(f"STDERR:\n{result.stderr}")
                self.results[suite_name]['failed'] += 1
                self.results[suite_name]['details'].append(f"Exit code: {result.returncode}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"❌ {suite_name} - TIMEOUT")
            self.results[suite_name]['failed'] += 1
            self.results[suite_name]['details'].append("Test suite timed out")
            return False
        except Exception as e:
            logger.error(f"❌ {suite_name} - ERROR: {e}")
            self.results[suite_name]['failed'] += 1
            self.results[suite_name]['details'].append(f"Exception: {e}")
            return False
            
    def validate_learning_documents(self) -> bool:
        """Validate learning documents are present and cross-linked."""
        logger.info("📚 Validating learning documents...")
        
        required_files = [
            'SPEC/learnings/websocket_injection_fix_comprehensive.xml',
            'tests/mission_critical/test_websocket_injection_fix_comprehensive.py',
            'tests/mission_critical/test_enhanced_tool_execution_websocket_events.py'
        ]
        
        all_exist = True
        
        for file_path in required_files:
            full_path = project_root / file_path
            if not full_path.exists():
                logger.error(f"❌ Missing required file: {file_path}")
                all_exist = False
            else:
                logger.info(f"✅ Found: {file_path}")
                
        # Check learning index contains the new learning
        index_path = project_root / 'SPEC/learnings/index.xml'
        if index_path.exists():
            with open(index_path, 'r', encoding='utf-8') as f:
                index_content = f.read()
                
            if 'websocket_injection_fix_comprehensive.xml' in index_content:
                logger.info("✅ Learning properly indexed")
            else:
                logger.error("❌ Learning not found in index")
                all_exist = False
        else:
            logger.error("❌ Learning index file not found")
            all_exist = False
            
        return all_exist
        
    def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run complete WebSocket injection fix validation."""
        logger.info("\n" + "=" * 80)
        logger.info("COMPREHENSIVE WEBSOCKET INJECTION FIX VALIDATION")
        logger.info("Business Value: $500K+ ARR - Core chat functionality")
        logger.info("=" * 80)
        
        start_time = time.time()
        
        # 1. Static code analysis
        static_passed = self.validate_static_code_analysis()
        
        # 2. Learning documents validation
        docs_passed = self.validate_learning_documents()
        
        # 3. Unit tests
        unit_passed = self.run_test_suite(
            'tests/mission_critical/test_websocket_injection_fix_comprehensive.py',
            'unit_tests'
        )
        
        # 4. Enhanced tool execution tests
        tool_passed = self.run_test_suite(
            'tests/mission_critical/test_enhanced_tool_execution_websocket_events.py', 
            'integration_tests'
        )
        
        # 5. Original mission critical tests (regression check)
        regression_passed = self.run_test_suite(
            'tests/mission_critical/test_websocket_agent_events_suite.py',
            'regression_tests'
        )
        
        duration = time.time() - start_time
        
        # Calculate overall results
        total_passed = sum(cat['passed'] for cat in self.results.values())
        total_failed = sum(cat['failed'] for cat in self.results.values())
        overall_success = (total_failed == 0 and static_passed and docs_passed)
        
        # Generate report
        logger.info("\n" + "=" * 80) 
        logger.info("WEBSOCKET INJECTION FIX VALIDATION REPORT")
        logger.info("=" * 80)
        logger.info(f"Overall Status: {'✅ PASSED' if overall_success else '❌ FAILED'}")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info(f"Total Test Suites: {total_passed + total_failed}")
        logger.info(f"Passed: {total_passed}")
        logger.info(f"Failed: {total_failed}")
        logger.info("")
        
        # Category breakdown
        for category, results in self.results.items():
            status = "✅" if results['failed'] == 0 else "❌"
            logger.info(f"{status} {category.replace('_', ' ').title()}: {results['passed']} passed, {results['failed']} failed")
            for detail in results['details']:
                logger.info(f"    - {detail}")
                
        logger.info("")
        logger.info(f"📋 Static Analysis: {'✅ PASSED' if static_passed else '❌ FAILED'}")
        logger.info(f"📚 Documentation: {'✅ PASSED' if docs_passed else '❌ FAILED'}")
        
        if overall_success:
            logger.info("\n🎉 WEBSOCKET INJECTION FIX VALIDATION SUCCESSFUL!")
            logger.info("✅ All components validated and working correctly")
            logger.info("✅ Real-time chat events should now work via dependency injection")
            logger.info("✅ Regression protection in place")
        else:
            logger.error("\n💥 WEBSOCKET INJECTION FIX VALIDATION FAILED!")
            logger.error("❌ Fix may not be working correctly")
            logger.error("❌ Users may experience 'blank screen' during AI processing")
            
        logger.info("=" * 80)
        
        return {
            'success': overall_success,
            'duration': duration,
            'results': self.results,
            'static_analysis': static_passed,
            'documentation': docs_passed
        }


def main():
    """Main entry point for WebSocket injection fix validation."""
    validator = WebSocketInjectionFixValidator()
    
    try:
        results = validator.run_comprehensive_validation()
        
        # Exit with error code if validation failed
        if not results['success']:
            sys.exit(1)
            
        logger.info("🚀 WebSocket injection fix validation completed successfully!")
        
    except KeyboardInterrupt:
        logger.warning("⚠️  Validation interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"💥 Validation failed with exception: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()