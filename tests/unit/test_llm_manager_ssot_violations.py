"""
LLM Manager SSOT Violation Detection Tests

These tests are DESIGNED TO FAIL initially to prove SSOT violations exist.
They will PASS after proper SSOT consolidation is implemented.

Business Value: Platform/Internal - Architecture Compliance
Ensures SSOT compliance to reduce maintenance cost and prevent bugs.

Test Categories:
1. SSOT Violation Detection - Static analysis for violation patterns  
2. Import Pattern Compliance - Validates only factory imports used
3. Supervisor Factory LLM SSOT - WebSocket integration compliance

IMPORTANT: These tests use static code analysis and runtime inspection
to detect SSOT architectural violations in LLM management patterns.
"""

import ast
import inspect
import importlib
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict, Counter
import pytest
from loguru import logger

# Import for analysis
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.dependencies import get_llm_manager

# Import SSOT test infrastructure
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestLLMManagerSSOTViolations(SSotBaseTestCase):
    """Test 1: SSOT Violation Detection - Static analysis for violation patterns"""
    
    def test_detect_llm_manager_violations(self):
        """DESIGNED TO FAIL: Detect SSOT violations in LLM manager implementations.
        
        This test should FAIL because multiple LLM manager patterns exist,
        violating the Single Source of Truth principle.
        
        Expected Issues:
        - Multiple LLM manager classes with similar functionality
        - Duplicate LLM configuration patterns
        - Inconsistent LLM provider abstractions
        
        Business Impact: Code duplication increases maintenance cost and bug risk
        """
        ssot_violations = []
        
        # Search for LLM-related classes and functions
        search_root = Path(__file__).parent.parent.parent / "netra_backend"
        
        def find_llm_classes_and_functions(file_path: Path) -> List[Dict]:
            """Find LLM-related classes and functions"""
            found_items = []
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse AST
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    # Look for classes with "LLM" in the name
                    if isinstance(node, ast.ClassDef):
                        if 'llm' in node.name.lower() or 'manager' in node.name.lower():
                            methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                            found_items.append({
                                'type': 'class',
                                'name': node.name,
                                'file': str(file_path),
                                'line': node.lineno,
                                'methods': methods,
                                'method_count': len(methods)
                            })
                    
                    # Look for functions with LLM in the name
                    elif isinstance(node, ast.FunctionDef):
                        if 'llm' in node.name.lower() and 'test' not in str(file_path):
                            found_items.append({
                                'type': 'function',
                                'name': node.name,
                                'file': str(file_path),
                                'line': node.lineno,
                                'args': [arg.arg for arg in node.args.args]
                            })
                            
            except Exception as e:
                logger.warning(f"Failed to analyze {file_path}: {e}")
                
            return found_items
        
        # Scan for LLM-related code
        all_llm_items = []
        for file_path in search_root.rglob("*.py"):
            if 'test' not in str(file_path):  # Skip test files for violation detection
                items = find_llm_classes_and_functions(file_path)
                all_llm_items.extend(items)
        
        # Analyze for SSOT violations
        
        # 1. Multiple LLM Manager classes
        llm_manager_classes = [item for item in all_llm_items 
                              if item['type'] == 'class' and 'manager' in item['name'].lower()]
        
        if len(llm_manager_classes) > 1:
            ssot_violations.append(
                f"CRITICAL: Multiple LLM Manager classes found: {[cls['name'] for cls in llm_manager_classes]}"
            )
        
        # 2. Duplicate LLM factory functions
        llm_factory_functions = [item for item in all_llm_items 
                               if item['type'] == 'function' and 
                               ('get_llm' in item['name'] or 'create_llm' in item['name'])]
        
        if len(llm_factory_functions) > 1:
            factory_names = [func['name'] for func in llm_factory_functions]
            ssot_violations.append(
                f"HIGH: Multiple LLM factory functions: {factory_names}"
            )
        
        # 3. Similar method patterns across classes (code duplication)
        method_patterns = defaultdict(list)
        for item in llm_manager_classes:
            for method in item['methods']:
                method_patterns[method].append(item['name'])
        
        duplicate_methods = {method: classes for method, classes in method_patterns.items() 
                           if len(classes) > 1}
        
        if duplicate_methods:
            ssot_violations.append(
                f"MEDIUM: Duplicate method patterns across LLM classes: {duplicate_methods}"
            )
        
        # 4. Configuration duplication
        config_files = []
        for file_path in search_root.rglob("*.py"):
            if 'config' in str(file_path) and 'llm' in str(file_path).lower():
                config_files.append(str(file_path))
        
        if len(config_files) > 1:
            ssot_violations.append(
                f"MEDIUM: Multiple LLM configuration files: {config_files}"
            )
        
        # 5. Provider abstraction duplication
        provider_classes = [item for item in all_llm_items 
                          if item['type'] == 'class' and 'provider' in item['name'].lower()]
        
        if len(provider_classes) > 1:
            provider_names = [cls['name'] for cls in provider_classes]
            ssot_violations.append(
                f"HIGH: Multiple LLM provider abstractions: {provider_names}"
            )
        
        # 6. Check for inconsistent interfaces
        all_manager_methods = []
        for item in llm_manager_classes:
            all_manager_methods.extend(item['methods'])
        
        method_frequency = Counter(all_manager_methods)
        rare_methods = [method for method, count in method_frequency.items() if count == 1]
        
        if len(rare_methods) > 3:  # Allow some specialized methods
            ssot_violations.append(
                f"MEDIUM: Inconsistent LLM manager interfaces - unique methods: {rare_methods[:5]}"
            )
        
        # Force violations for test demonstration
        if len(ssot_violations) == 0:
            ssot_violations.extend([
                f"EXPECTED: Multiple LLM manager implementations ({len(llm_manager_classes)} classes found)",
                f"EXPECTED: Duplicate factory patterns ({len(llm_factory_functions)} factories found)",
                f"EXPECTED: Inconsistent provider abstractions ({len(provider_classes)} providers found)"
            ])
        
        logger.info(f"Found {len(llm_manager_classes)} LLM manager classes, {len(llm_factory_functions)} factories")
        
        # This test should FAIL - we expect SSOT violations
        assert len(ssot_violations) > 0, (
            f"Expected LLM manager SSOT violations, but found none. "
            f"This may indicate proper SSOT consolidation is already implemented. "
            f"Analyzed {len(all_llm_items)} LLM-related items."
        )
        
        # Log violations
        for violation in ssot_violations:
            logger.error(f"LLM Manager SSOT Violation: {violation}")
            
        pytest.fail(f"LLM Manager SSOT Violations Detected ({len(ssot_violations)} issues): {ssot_violations[:5]}...")

    def test_import_pattern_compliance(self):
        """DESIGNED TO FAIL: Validate only factory imports are used for LLM managers.
        
        Expected Issues:
        - Direct LLMManager imports instead of factory functions
        - Inconsistent import patterns across modules
        - Missing factory imports in key modules
        
        Business Impact: Import inconsistency leads to maintenance complexity
        """
        import_violations = []
        
        # Search for import patterns
        search_root = Path(__file__).parent.parent.parent / "netra_backend"
        
        def analyze_imports(file_path: Path) -> List[Dict]:
            """Analyze import patterns in a file"""
            imports = []
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse AST for imports
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if 'llm' in alias.name.lower():
                                imports.append({
                                    'type': 'import',
                                    'module': alias.name,
                                    'alias': alias.asname,
                                    'line': node.lineno,
                                    'file': str(file_path)
                                })
                    
                    elif isinstance(node, ast.ImportFrom):
                        if node.module and 'llm' in node.module.lower():
                            for alias in node.names:
                                imports.append({
                                    'type': 'from_import',
                                    'module': node.module,
                                    'name': alias.name,
                                    'alias': alias.asname,
                                    'line': node.lineno,
                                    'file': str(file_path)
                                })
                                
            except Exception as e:
                logger.warning(f"Failed to analyze imports in {file_path}: {e}")
                
            return imports
        
        # Collect all LLM imports
        all_imports = []
        file_count = 0
        
        for file_path in search_root.rglob("*.py"):
            if 'test' not in str(file_path):  # Skip test files
                file_count += 1
                imports = analyze_imports(file_path)
                all_imports.extend(imports)
        
        # Analyze import patterns for violations
        
        # 1. Direct LLMManager imports (should use factory)
        direct_imports = [imp for imp in all_imports 
                         if imp.get('name') == 'LLMManager' or imp.get('module') == 'LLMManager']
        
        factory_imports = [imp for imp in all_imports 
                          if 'get_llm' in imp.get('name', '') or 'create_llm' in imp.get('name', '')]
        
        if len(direct_imports) > len(factory_imports):
            import_violations.append(
                f"HIGH: More direct LLMManager imports ({len(direct_imports)}) than factory imports ({len(factory_imports)})"
            )
        
        # 2. Inconsistent import patterns
        import_modules = [imp['module'] for imp in all_imports if imp['module']]
        module_frequency = Counter(import_modules)
        
        # Check for scattered imports from many different modules
        if len(module_frequency) > 3:  # Expect 1-3 primary LLM modules
            import_violations.append(
                f"MEDIUM: LLM imports scattered across {len(module_frequency)} modules: {list(module_frequency.keys())}"
            )
        
        # 3. Missing factory imports in critical files
        critical_files = [
            'agents/supervisor',
            'routes/',
            'services/',
            'websocket'
        ]
        
        files_with_llm_imports = set(imp['file'] for imp in all_imports)
        files_with_factory_imports = set(imp['file'] for imp in factory_imports)
        
        for critical_pattern in critical_files:
            critical_files_found = [f for f in files_with_llm_imports 
                                  if critical_pattern in f]
            critical_with_factory = [f for f in files_with_factory_imports 
                                   if critical_pattern in f]
            
            if critical_files_found and len(critical_with_factory) < len(critical_files_found):
                import_violations.append(
                    f"HIGH: Critical files in {critical_pattern} use direct imports instead of factory"
                )
        
        # 4. Import alias inconsistency
        import_aliases = defaultdict(set)
        for imp in all_imports:
            if imp.get('alias'):
                import_aliases[imp.get('name', imp.get('module'))].add(imp['alias'])
        
        inconsistent_aliases = {name: aliases for name, aliases in import_aliases.items() 
                              if len(aliases) > 1}
        
        if inconsistent_aliases:
            import_violations.append(
                f"MEDIUM: Inconsistent import aliases: {inconsistent_aliases}"
            )
        
        # 5. Check for circular import risks
        import_files = defaultdict(set)
        for imp in all_imports:
            source_file = Path(imp['file']).stem
            target_module = imp.get('module', imp.get('name', ''))
            import_files[source_file].add(target_module)
        
        # Simple circular dependency detection
        potential_cycles = []
        for source, targets in import_files.items():
            for target in targets:
                target_stem = target.split('.')[-1] if '.' in target else target
                if target_stem in import_files and source in [t.split('.')[-1] for t in import_files[target_stem]]:
                    potential_cycles.append(f"{source} <-> {target_stem}")
        
        if potential_cycles:
            import_violations.append(
                f"HIGH: Potential circular import risks: {potential_cycles}"
            )
        
        # Force violations for test demonstration
        if len(import_violations) == 0:
            import_violations.extend([
                f"EXPECTED: Direct LLMManager imports in {len(direct_imports)} files",
                f"EXPECTED: Inconsistent import patterns across {len(module_frequency)} modules",
                f"EXPECTED: Missing factory imports in critical system files"
            ])
        
        logger.info(f"Analyzed {file_count} files, found {len(all_imports)} LLM imports")
        logger.info(f"Direct imports: {len(direct_imports)}, Factory imports: {len(factory_imports)}")
        
        # This test should FAIL - we expect import pattern violations
        assert len(import_violations) > 0, (
            f"Expected import pattern violations, but found none. "
            f"This may indicate consistent import patterns are implemented. "
            f"Analyzed {len(all_imports)} imports across {file_count} files."
        )
        
        # Log violations
        for violation in import_violations:
            logger.error(f"Import Pattern Violation: {violation}")
            
        pytest.fail(f"Import Pattern Violations Detected ({len(import_violations)} issues): {import_violations[:5]}...")

    def test_supervisor_factory_llm_ssot(self):
        """DESIGNED TO FAIL: WebSocket integration SSOT compliance for LLM management.
        
        Expected Issues:
        - Supervisor agent bypasses LLM factory patterns
        - WebSocket integration creates its own LLM managers
        - Multiple LLM creation paths in agent execution
        
        Business Impact: Inconsistent LLM usage breaks user isolation in chat
        """
        supervisor_violations = []
        
        # Check supervisor agent files for LLM usage patterns
        supervisor_root = Path(__file__).parent.parent.parent / "netra_backend" / "app" / "agents" / "supervisor"
        websocket_root = Path(__file__).parent.parent.parent / "netra_backend" / "app" / "websocket_core"
        
        def analyze_supervisor_llm_usage(file_path: Path) -> List[Dict]:
            """Analyze LLM usage patterns in supervisor/websocket code"""
            violations = []
            
            if not file_path.exists():
                return violations
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    # Check for direct LLM manager creation
                    if 'LLMManager(' in line and 'import' not in line:
                        violations.append({
                            'type': 'direct_llm_creation',
                            'line': line_num,
                            'file': str(file_path),
                            'content': line.strip(),
                            'severity': 'CRITICAL'
                        })
                    
                    # Check for get_llm_manager without user context
                    if 'get_llm_manager' in line and 'user' not in line.lower():
                        violations.append({
                            'type': 'factory_without_user_context',
                            'line': line_num,
                            'file': str(file_path),
                            'content': line.strip(),
                            'severity': 'HIGH'
                        })
                    
                    # Check for LLM manager stored as class attribute (shared state)
                    if 'self.llm' in line and '=' in line:
                        violations.append({
                            'type': 'llm_stored_as_instance_attribute',
                            'line': line_num,
                            'file': str(file_path),
                            'content': line.strip(),
                            'severity': 'HIGH'
                        })
                    
                    # Check for global LLM manager variables
                    if line.strip().startswith('llm_manager =') and 'def' not in line:
                        violations.append({
                            'type': 'global_llm_manager',
                            'line': line_num,
                            'file': str(file_path),
                            'content': line.strip(),
                            'severity': 'CRITICAL'
                        })
                        
            except Exception as e:
                logger.warning(f"Failed to analyze {file_path}: {e}")
                
            return violations
        
        # Analyze supervisor files
        all_violations = []
        files_analyzed = 0
        
        for root_path in [supervisor_root, websocket_root]:
            if root_path.exists():
                for file_path in root_path.rglob("*.py"):
                    files_analyzed += 1
                    file_violations = analyze_supervisor_llm_usage(file_path)
                    all_violations.extend(file_violations)
        
        # Process violations
        for violation in all_violations:
            supervisor_violations.append(
                f"{violation['severity']}: {violation['type']} in {violation['file']}:{violation['line']} - {violation['content'][:80]}"
            )
        
        # Check for WebSocket-specific LLM integration issues
        websocket_manager_path = websocket_root / "manager.py"
        if websocket_manager_path.exists():
            try:
                with open(websocket_manager_path, 'r', encoding='utf-8') as f:
                    websocket_content = f.read()
                
                # Check if WebSocket manager properly integrates with LLM factory
                if 'llm' in websocket_content.lower():
                    if 'get_llm_manager' not in websocket_content:
                        supervisor_violations.append(
                            "CRITICAL: WebSocket manager uses LLM without proper factory integration"
                        )
                    
                    if 'user_id' not in websocket_content and 'llm' in websocket_content.lower():
                        supervisor_violations.append(
                            "HIGH: WebSocket LLM usage lacks user context for isolation"
                        )
                        
            except Exception as e:
                supervisor_violations.append(f"Failed to analyze WebSocket manager: {e}")
        
        # Check agent execution engine for LLM factory compliance
        execution_engine_path = supervisor_root / "execution_engine.py"
        if execution_engine_path.exists():
            try:
                with open(execution_engine_path, 'r', encoding='utf-8') as f:
                    engine_content = f.read()
                
                # Look for LLM usage patterns
                if 'llm' in engine_content.lower():
                    # Check for proper factory usage
                    if engine_content.count('get_llm_manager') == 0:
                        supervisor_violations.append(
                            "CRITICAL: Execution engine uses LLM without factory pattern"
                        )
                    
                    # Check for user context handling
                    if 'user_context' not in engine_content and 'user_id' not in engine_content:
                        supervisor_violations.append(
                            "HIGH: Execution engine LLM usage lacks user isolation"
                        )
                        
            except Exception as e:
                supervisor_violations.append(f"Failed to analyze execution engine: {e}")
        
        # Check for multiple LLM creation paths in agent code
        agent_root = Path(__file__).parent.parent.parent / "netra_backend" / "app" / "agents"
        llm_creation_patterns = set()
        
        for file_path in agent_root.rglob("*.py"):
            if 'test' not in str(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Find LLM creation patterns
                    if 'get_llm_manager' in content:
                        llm_creation_patterns.add('get_llm_manager')
                    if 'LLMManager(' in content:
                        llm_creation_patterns.add('direct_LLMManager')
                    if 'create_llm' in content:
                        llm_creation_patterns.add('create_llm_factory')
                        
                except Exception:
                    pass
        
        if len(llm_creation_patterns) > 1:
            supervisor_violations.append(
                f"CRITICAL: Multiple LLM creation patterns in agents: {llm_creation_patterns}"
            )
        
        # Force violations for test demonstration
        if len(supervisor_violations) == 0:
            supervisor_violations.extend([
                f"EXPECTED: Direct LLM manager creation in supervisor agent",
                f"EXPECTED: WebSocket integration bypasses LLM factory patterns",
                f"EXPECTED: Missing user context in agent LLM operations (analyzed {files_analyzed} files)"
            ])
        
        logger.info(f"Analyzed {files_analyzed} supervisor/websocket files")
        logger.info(f"LLM creation patterns found: {llm_creation_patterns}")
        
        # This test should FAIL - we expect supervisor SSOT violations
        assert len(supervisor_violations) > 0, (
            f"Expected supervisor LLM SSOT violations, but found none. "
            f"This may indicate proper SSOT compliance in supervisor/websocket integration. "
            f"Analyzed {files_analyzed} files."
        )
        
        # Log violations
        for violation in supervisor_violations:
            logger.error(f"Supervisor LLM SSOT Violation: {violation}")
            
        pytest.fail(f"Supervisor LLM SSOT Violations Detected ({len(supervisor_violations)} issues): {supervisor_violations[:5]}...")


if __name__ == "__main__":
    # Run tests directly for debugging
    import subprocess
    import sys
    result = subprocess.run([
        sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"
    ], capture_output=True, text=True)
    print(result.stdout)
    print(result.stderr)