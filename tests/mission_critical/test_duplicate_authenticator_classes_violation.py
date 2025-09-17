"""
Test for WebSocket Authentication SSOT Violation: Duplicate UnifiedWebSocketAuthenticator Classes

BUSINESS IMPACT: $500K+ ARR - WebSocket authentication chaos blocking Golden Path
"""
ISSUE: #1076 - Two complete UnifiedWebSocketAuthenticator classes exist in unified_websocket_auth.py

This test SHOULD FAIL INITIALLY (reproducing the SSOT violation) and PASS AFTER REMEDIATION.

SSOT Gardener Step 2.1: Detect that two complete UnifiedWebSocketAuthenticator classes exist.
Lines 288-1492 (Primary SSOT) and Lines 1494-1656 (Duplicate Legacy)

Expected Test Behavior:
- FAILS NOW: Two class definitions detected
- PASSES AFTER: Only one class definition remains after SSOT consolidation
"

import ast
import os
import unittest
from typing import List, Dict, Any
from test_framework.ssot.base_test_case import SSotAsyncTestCase


class DuplicateAuthenticatorClassesViolationTests(SSotAsyncTestCase):
    "
    Mission Critical Test: WebSocket Authentication SSOT Violation Detection
    
    Tests that only one UnifiedWebSocketAuthenticator class exists in the codebase.
    This is a business-critical test protecting $500K+ ARR chat functionality.
"
    
    def setup_method(self, method):
        "Set up test environment for SSOT violation detection.
        super().setup_method(method)
        self.target_file = /Users/anthony/Desktop/netra-apex/netra_backend/app/websocket_core/unified_websocket_auth.py""
        self.expected_class_name = UnifiedWebSocketAuthenticator
    
    @property
    def test_metadata(self) -> Dict[str, Any]:
        "Access test metadata through context."
        if hasattr(self, '_test_context') and self._test_context:
            return self._test_context.metadata
        return {}
    
    def test_only_one_unified_websocket_authenticator_class_exists(self):
    "
        CRITICAL TEST: Should FAIL currently - detects duplicate UnifiedWebSocketAuthenticator classes.
        
        This test inspects the unified_websocket_auth.py file and counts occurrences of
        'class UnifiedWebSocketAuthenticator'. It should FAIL now because there are 2 classes
        and PASS after SSOT consolidation when only 1 class remains.
        
        Business Impact: Authentication chaos prevention for Golden Path user flow
        "
        self.assertTrue(os.path.exists(self.target_file), 
                       fTarget file does not exist: {self.target_file})
        
        # Read and parse the file
        with open(self.target_file, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        # Count class definitions using AST parsing for accuracy
        class_definitions = self._count_class_definitions(file_content, self.expected_class_name)
        
        # Log detailed findings for debugging
        self._log_class_analysis(file_content, class_definitions)
        
        # CRITICAL ASSERTION: Should FAIL now (2 classes), PASS after remediation (1 class)
        self.assertEqual(len(class_definitions), 1,
                        f"SSOT VIOLATION DETECTED: Found {len(class_definitions)} 
                        f'{self.expected_class_name}' class definitions, expected exactly 1. "
                        fLocations: {[f'Line {d['line_number']}' for d in class_definitions]} 
                        fThis indicates authentication SSOT violation blocking Golden Path.)"
    
    def test_class_definitions_line_ranges_non_overlapping(self):
    "
        SUPPORTING TEST: Verify that if multiple classes exist, they don't overlap.
        
        This test ensures that duplicate classes are actually separate definitions
        rather than parsing errors or nested classes.
        "
        if not os.path.exists(self.target_file):
            self.skipTest(fTarget file does not exist: {self.target_file}")
        
        with open(self.target_file, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        class_definitions = self._count_class_definitions(file_content, self.expected_class_name)
        
        if len(class_definitions) <= 1:
            self.skipTest(Only one or zero class definitions found - no overlap to check)
        
        # Check that class definitions don't overlap (indicating real duplicates)
        for i, class_def in enumerate(class_definitions):
            for j, other_def in enumerate(class_definitions):
                if i != j:
                    # Verify line ranges don't overlap
                    self.assertFalse(
                        self._ranges_overlap(
                            (class_def['line_number'], class_def['end_line'],
                            (other_def['line_number'], other_def['end_line']
                        ),
                        fClass definitions at lines {class_def['line_number']} and ""
                        f{other_def['line_number']} appear to overlap - possible parsing error
                    )
    
    def test_ssot_consolidation_metadata_validation(self):
        
        METADATA TEST: Validate SSOT consolidation progress indicators.
        
        This test checks for indicators that SSOT consolidation is in progress
        or completed, such as deprecation warnings or migration comments.
""
        if not os.path.exists(self.target_file):
            self.skipTest(fTarget file does not exist: {self.target_file})
        
        with open(self.target_file, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        # Check for SSOT consolidation indicators
        ssot_indicators = self._find_ssot_indicators(file_content)
        
        # Log findings
        self.logger.info(fSSOT CONSOLIDATION: Found {len(ssot_indicators['deprecation_warnings']} deprecation warnings)"
        self.logger.info(f"SSOT CONSOLIDATION: Found {len(ssot_indicators['ssot_comments']} SSOT comments)
        
        # Record metadata for analysis
        self.test_metadata.update({
            ssot_deprecation_warnings: len(ssot_indicators['deprecation_warnings'],
            ssot_comments: len(ssot_indicators['ssot_comments'],"
            migration_indicators": ssot_indicators['migration_indicators']
        }
        
        # This test is informational - always passes but logs progress
        self.assertTrue(True, SSOT metadata validation completed)
    
    def _count_class_definitions(self, file_content: str, class_name: str) -> List[Dict[str, Any]]:
        ""
        Count class definitions using AST parsing for accuracy.
        
        Args:
            file_content: Content of the Python file
            class_name: Name of the class to count
            
        Returns:
            List of dictionaries with class definition details

        class_definitions = []
        
        try:
            # Parse with AST for accurate class detection
            tree = ast.parse(file_content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    # Calculate approximate end line
                    end_line = getattr(node, 'end_lineno', node.lineno + 100)
                    
                    class_definitions.append({
                        'name': node.name,
                        'line_number': node.lineno,
                        'end_line': end_line,
                        'methods_count': len([n for n in node.body if isinstance(n, ast.FunctionDef)],
                        'docstring': ast.get_docstring(node)
                    }
        
        except SyntaxError as e:
            # Fallback to simple text parsing if AST fails
            self.logger.warning(f"AST parsing failed ({e}, using text-based parsing)")
            return self._count_class_definitions_text_based(file_content, class_name)
        
        return class_definitions
    
    def _count_class_definitions_text_based(self, file_content: str, class_name: str) -> List[Dict[str, Any]]:
        "
        Fallback method to count class definitions using text parsing.
        
        Args:
            file_content: Content of the Python file
            class_name: Name of the class to count
            
        Returns:
            List of dictionaries with class definition details
"
        class_definitions = []
        lines = file_content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith(f'class {class_name}'):
                # Extract any inheritance or annotations
                class_signature = stripped
                
                class_definitions.append({
                    'name': class_name,
                    'line_number': line_num,
                    'end_line': line_num + 100,  # Approximate
                    'methods_count': 'unknown',
                    'signature': class_signature,
                    'docstring': None
                }
        
        return class_definitions
    
    def _log_class_analysis(self, file_content: str, class_definitions: List[Dict[str, Any]]:
        "Log detailed analysis of class definitions found.
        self.logger.info(fCLASS ANALYSIS: Found {len(class_definitions)} '{self.expected_class_name}' definitions")"
        
        for i, class_def in enumerate(class_definitions, 1):
            self.logger.info(fCLASS {i}: Line {class_def['line_number']}-{class_def['end_line']}, 
                           fMethods: {class_def['methods_count']})
            
            if class_def.get('docstring'):
                # Log first line of docstring for identification
                first_doc_line = class_def['docstring'].split('\n')[0].strip()
                self.logger.info(f"CLASS {i} DOC: {first_doc_line[:100]}...)
        
        # Additional file statistics
        total_lines = len(file_content.split('\n'))
        self.logger.info(fFILE STATS: {total_lines} total lines in {self.target_file}")
        
        # Record in test metadata for later analysis
        self.test_metadata.update({
            file_total_lines: total_lines,
            classes_found": len(class_definitions),"
            class_locations: [fLine {cd['line_number']} for cd in class_definitions]
        }
    
    def _ranges_overlap(self, range1: tuple, range2: tuple) -> bool:
        Check if two line number ranges overlap.""
        start1, end1 = range1
        start2, end2 = range2
        
        return not (end1 < start2 or end2 < start1)
    
    def _find_ssot_indicators(self, file_content: str) -> Dict[str, List[str]]:
        
        Find indicators of SSOT consolidation progress in the file.
        
        Args:
            file_content: Content of the file to analyze
            
        Returns:
            Dictionary with different types of SSOT indicators
""
        lines = file_content.split('\n')
        
        indicators = {
            'deprecation_warnings': [],
            'ssot_comments': [],
            'migration_indicators': []
        }
        
        for line_num, line in enumerate(lines, 1):
            line_lower = line.lower()
            
            # Look for deprecation warnings
            if 'deprecated' in line_lower or 'deprecationwarning' in line_lower:
                indicators['deprecation_warnings'].append(fLine {line_num}: {line.strip()})
            
            # Look for SSOT comments
            if 'ssot' in line_lower and ('#' in line or '"' in line or ''' in line):
                indicators['ssot_comments'].append(f"Line {line_num}: {line.strip()})
            
            # Look for migration indicators
            if any(keyword in line_lower for keyword in ['migration', 'backward compatibility', 'legacy']:
                indicators['migration_indicators'].append(f"Line {line_num}: {line.strip()}")
        
        return indicators


if __name__ == '__main__':
    unittest.main()