"""
Comprehensive Frontend Duplicate Export Detection Tests

This test suite validates detection and resolution of TypeScript module export duplications
that cause Next.js webpack compilation failures. Based on the actual error:
"Duplicate export 'isValidWebSocketMessageType'" at line 42:227 in /frontend/types/registry.ts

Test Categories:
1. Module Analysis - Parse TypeScript files for duplicate exports
2. Build Process Tests - Test Next.js webpack module parsing  
3. Edge Cases - Complex re-export chains and circular dependencies
4. Extended Scenarios - Cross-module conflicts and build optimization issues

BVJ: Preventing build failures = stable deployments = better user experience
"""
import pytest
import os
import re
import json
import tempfile
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from shared.isolated_environment import IsolatedEnvironment

class TypeScriptModuleParser:
    """Parse TypeScript modules to detect export patterns"""

    def __init__(self, content: str):
        self.content = content
        self.lines = content.split('\n')

    def extract_exports(self) -> Dict[str, List[Tuple[int, str]]]:
        """Extract all exports with their line numbers and types"""
        exports = {}
        in_export_block = False
        current_export_block = []
        block_start_line = 0
        for line_num, line in enumerate(self.lines, 1):
            stripped_line = line.strip()
            if stripped_line.startswith('export {'):
                in_export_block = True
                current_export_block = [stripped_line]
                block_start_line = line_num
                if '}' in stripped_line and 'from' in stripped_line:
                    self._process_export_block('\n'.join(current_export_block), block_start_line, exports)
                    in_export_block = False
                    current_export_block = []
                elif '}' in stripped_line and 'from' not in stripped_line:
                    self._process_export_block('\n'.join(current_export_block), block_start_line, exports)
                    in_export_block = False
                    current_export_block = []
                continue
            if in_export_block:
                current_export_block.append(stripped_line)
                if '}' in stripped_line:
                    self._process_export_block('\n'.join(current_export_block), block_start_line, exports)
                    in_export_block = False
                    current_export_block = []
                continue
            named_match = re.match('^export\\s+(?:const|let|var|function|class|enum|interface|type)\\s+(\\w+)', stripped_line)
            if named_match:
                name = named_match.group(1)
                exports.setdefault(name, []).append((line_num, 'named_export'))
        return exports

    def _process_export_block(self, block_content: str, start_line: int, exports: Dict[str, List[Tuple[int, str]]]):
        """Process a complete export block"""
        cleaned = re.sub('^export\\s*\\{', '', block_content)
        if ' from ' in cleaned:
            from_match = re.search('from\\s*[\\\'"]([^\\\'"]+)[\\\'"]', cleaned)
            module_path = from_match.group(1) if from_match else 'unknown'
            names_part = cleaned.split(' from ')[0].replace('}', '').strip()
        else:
            module_path = None
            names_part = cleaned.replace('}', '').strip()
        if names_part:
            names = [name.strip() for name in names_part.split(',')]
            for name in names:
                if not name:
                    continue
                if ' as ' in name:
                    name = name.split(' as ')[1].strip()
                export_type = f're_export_from_{module_path}' if module_path else 'export_list'
                exports.setdefault(name, []).append((start_line, export_type))

    def find_duplicates(self) -> Dict[str, List[Tuple[int, str]]]:
        """Find all duplicate exports"""
        exports = self.extract_exports()
        return {name: locations for name, locations in exports.items() if len(locations) > 1}

@pytest.fixture
def frontend_path():
    """Path to frontend directory"""
    return Path(__file__).parent.parent.parent / 'frontend'

@pytest.fixture
def sample_registry_ts():
    """Sample registry.ts content with duplicate exports (reproducing actual error)"""
    return "// Re-export all enums and validation functions\nexport {\n  MessageType,\n  AgentStatus,\n  WebSocketMessageType,\n  isValidMessageType,\n  isValidAgentStatus,\n  isValidWebSocketMessageType,\n  getMessageTypeValues,\n  getAgentStatusValues,\n  getWebSocketMessageTypeValues,\n  getEnumKey,\n  ENUM_REGISTRY\n} from './shared/enums';\n\n// WebSocket runtime functions\nexport {\n  createWebSocketError,\n  createWebSocketMessage,\n  isAgentCompletedMessage,\n  isAgentStartedMessage,\n  isAgentUpdateMessage,\n  isErrorMessage,\n  isSubAgentUpdateMessage,\n  isToolCallMessage,\n  isUserMessagePayload,\n  isWebSocketMessage,\n  isValidWebSocketMessageType\n} from './domains/websocket';"

@pytest.fixture
def sample_websocket_ts():
    """Sample websocket.ts content with re-export"""
    return "\n// Re-export enum validation function\nexport { isValidWebSocketMessageType } from '../shared/enums';\n\nexport function createWebSocketMessage() {\n  return {};\n}\n"

@pytest.fixture
def sample_enums_ts():
    """Sample enums.ts content with original export"""
    return "\nexport function isValidWebSocketMessageType(value: string): boolean {\n  return true;\n}\n\nexport enum WebSocketMessageType {\n  USER_MESSAGE = 'user_message',\n  AGENT_UPDATE = 'agent_update'\n}\n"

def test_detect_direct_duplicate_exports_in_registry(sample_registry_ts):
    """
    Test detection of direct duplicate exports within the same module.
    Should FAIL initially to reproduce the actual "Duplicate export" error.
    """
    parser = TypeScriptModuleParser(sample_registry_ts)
    duplicates = parser.find_duplicates()
    assert 'isValidWebSocketMessageType' in duplicates, 'Should detect duplicate export of isValidWebSocketMessageType'
    assert len(duplicates['isValidWebSocketMessageType']) == 2, 'Should find exactly 2 duplicate exports'
    line_numbers = [loc[0] for loc in duplicates['isValidWebSocketMessageType']]
    print(f'Found duplicate at lines: {line_numbers}')
    assert len(line_numbers) == 2, f'Should find exactly 2 duplicates, got {len(line_numbers)}'
    assert line_numbers[0] != line_numbers[1], 'Duplicates should be on different lines'

def test_parse_export_types_and_sources():
    """Test parsing different types of exports and their sources"""
    content = "\nexport const MY_CONST = 'value';\nexport function myFunction() {}\nexport { namedExport } from './other';\nexport { aliased as newName } from './module';\nexport * from './all-exports';\n"
    parser = TypeScriptModuleParser(content)
    exports = parser.extract_exports()
    assert 'MY_CONST' in exports
    assert 'myFunction' in exports
    assert 'namedExport' in exports
    assert 'newName' in exports
    const_export = next((loc for loc in exports['MY_CONST'] if loc[1] == 'named_export'))
    assert const_export is not None

def test_complex_export_list_parsing():
    """Test parsing complex export lists with formatting variations"""
    content = "\nexport {\n  functionA,\n  functionB,\n  functionC as aliasC,\n  CONSTANT_D\n} from './source';\n\nexport {\n  duplicateFunc,\n  anotherFunc\n};\n\nexport function duplicateFunc() {}\n"
    parser = TypeScriptModuleParser(content)
    duplicates = parser.find_duplicates()
    assert 'duplicateFunc' in duplicates
    assert len(duplicates['duplicateFunc']) == 2

def test_detect_re_export_chain_duplicates(sample_registry_ts, sample_websocket_ts, sample_enums_ts):
    """Test detection of duplicates caused by re-export chains"""
    files = {'registry.ts': sample_registry_ts, 'domains/websocket.ts': sample_websocket_ts, 'shared/enums.ts': sample_enums_ts}
    parser = TypeScriptModuleParser(files['registry.ts'])
    duplicates = parser.find_duplicates()
    assert 'isValidWebSocketMessageType' in duplicates
    sources = [loc[1] for loc in duplicates['isValidWebSocketMessageType']]
    assert any(('shared/enums' in source for source in sources))
    assert any(('domains/websocket' in source for source in sources))

def test_webpack_duplicate_module_detection():
    """Test webpack-style duplicate module detection that causes build failures"""
    module_registry = {}

    def register_export(module_path: str, export_name: str, line_info: str):
        """Simulate webpack module registration"""
        key = f'{module_path}#{export_name}'
        if key in module_registry:
            raise Exception(f"Duplicate export '{export_name}' at {line_info}")
        module_registry[key] = line_info
    with pytest.raises(Exception, match="Duplicate export 'isValidWebSocketMessageType'"):
        register_export('registry.ts', 'isValidWebSocketMessageType', 'line 38')
        register_export('registry.ts', 'isValidWebSocketMessageType', 'line 42:227')

def test_next_js_typescript_compilation_simulation():
    """Simulate Next.js TypeScript compilation with duplicate exports"""
    compilation_errors = []

    def compile_typescript_module(content: str, module_path: str):
        """Mock TypeScript compilation"""
        parser = TypeScriptModuleParser(content)
        duplicates = parser.find_duplicates()
        for export_name, locations in duplicates.items():
            if len(locations) > 1:
                line_info = f"line {locations[1][0]}:{len(content.split('\\n')[locations[1][0] - 1])}"
                compilation_errors.append(f"Duplicate export '{export_name}' at {line_info}")
    problematic_content = "\nexport { isValidWebSocketMessageType } from './shared/enums';\nexport { isValidWebSocketMessageType } from './domains/websocket';\n"
    compile_typescript_module(problematic_content, 'registry.ts')
    assert len(compilation_errors) == 1
    assert "Duplicate export 'isValidWebSocketMessageType'" in compilation_errors[0]

def test_build_cache_invalidation_scenarios():
    """Test scenarios where build cache doesn't detect changes in re-exports"""
    cache = {}

    def build_with_cache(module_content: str, module_path: str) -> bool:
        """Simulate cached build process"""
        content_hash = hash(module_content)
        if module_path in cache and cache[module_path]['hash'] == content_hash:
            return True
        parser = TypeScriptModuleParser(module_content)
        duplicates = parser.find_duplicates()
        has_duplicates = len(duplicates) > 0
        cache[module_path] = {'hash': content_hash, 'has_duplicates': has_duplicates}
        return not has_duplicates
    content_with_duplicates = "\nexport { func } from './a';\nexport { func } from './b';\n"
    result1 = build_with_cache(content_with_duplicates, 'test.ts')
    assert result1 is False, 'First build should fail due to duplicates'
    result2 = build_with_cache(content_with_duplicates, 'test.ts')
    assert result2 is False, 'Cached build should also fail'
    fixed_content = "\nexport { func } from './a';\nexport { otherFunc } from './b';\n"
    result3 = build_with_cache(fixed_content, 'test.ts')
    assert result3 is True, 'Fixed content should build successfully'

def test_production_vs_development_build_differences():
    """Test how duplicate exports behave differently in dev vs prod builds"""

    def build_mode_simulation(content: str, is_production: bool=False):
        """Simulate different build behaviors"""
        parser = TypeScriptModuleParser(content)
        duplicates = parser.find_duplicates()
        if is_production:
            if duplicates:
                raise Exception(f'Production build failed: {list(duplicates.keys())}')
            return 'success'
        else:
            if duplicates:
                return f'warning: {list(duplicates.keys())}'
            return 'success'
    problematic_content = "\nexport { isValidWebSocketMessageType } from './shared/enums';  \nexport { isValidWebSocketMessageType } from './domains/websocket';\n"
    dev_result = build_mode_simulation(problematic_content, is_production=False)
    assert 'warning' in dev_result
    with pytest.raises(Exception, match='Production build failed'):
        build_mode_simulation(problematic_content, is_production=True)

def test_circular_dependency_with_re_exports():
    """Test circular dependencies that create complex duplicate scenarios"""
    module_a = "\nexport { sharedFunction } from './module_b';\nexport const LOCAL_CONST = 'a';\n"
    module_b = "\nexport { LOCAL_CONST } from './module_a';\nexport function sharedFunction() {}\n"
    module_c = "\nexport { sharedFunction } from './module_a';\nexport { sharedFunction } from './module_b';\n"
    parser_c = TypeScriptModuleParser(module_c)
    duplicates = parser_c.find_duplicates()
    assert 'sharedFunction' in duplicates
    assert len(duplicates['sharedFunction']) == 2

def test_barrel_exports_with_overlapping_members():
    """Test barrel export pattern causing unintended duplicates"""
    barrel_content = "\n// Export everything from domain modules\nexport * from './auth';\nexport * from './websocket';\nexport * from './shared';\n\n// Also explicitly export some items\nexport { isValidWebSocketMessageType } from './shared/enums';\nexport { createUser } from './auth';\n"
    parser = TypeScriptModuleParser(barrel_content)
    exports = parser.extract_exports()
    assert 'isValidWebSocketMessageType' in exports

def test_mixed_named_and_default_export_conflicts():
    """Test conflicts between named and default exports"""
    content = "\nexport default function isValidWebSocketMessageType() {}\nexport { isValidWebSocketMessageType } from './other';\n"
    parser = TypeScriptModuleParser(content)
    exports = parser.extract_exports()
    assert 'isValidWebSocketMessageType' in exports

def test_type_only_vs_runtime_export_conflicts():
    """Test conflicts between type-only and runtime exports"""
    content = "\nexport type { WebSocketMessage } from './types';\nexport { WebSocketMessage } from './runtime';\n\nexport type { isValidWebSocketMessageType } from './type-guards';\nexport { isValidWebSocketMessageType } from './validators';\n"
    parser = TypeScriptModuleParser(content)
    duplicates = parser.find_duplicates()
    assert 'WebSocketMessage' in duplicates
    assert 'isValidWebSocketMessageType' in duplicates

def test_namespace_collision_detection():
    """Test detection of namespace collisions in complex module structures"""
    content = "\nexport namespace WebSocket {\n  export function connect() {}\n}\n\nexport { WebSocket } from './websocket-impl';\n\nexport interface WebSocketMessage {}\nexport type { WebSocketMessage } from './message-types';\n"
    parser = TypeScriptModuleParser(content)
    duplicates = parser.find_duplicates()
    assert 'WebSocket' in duplicates
    assert 'WebSocketMessage' in duplicates

def test_cross_module_duplicate_analysis():
    """Test analysis of duplicates across multiple modules"""
    modules = {'registry.ts': "\nexport { isValidWebSocketMessageType } from './shared/enums';\nexport { isValidWebSocketMessageType } from './domains/websocket';\n", 'shared/enums.ts': '\nexport function isValidWebSocketMessageType(value: string): boolean {\n  return true;\n}\n', 'domains/websocket.ts': "\nexport { isValidWebSocketMessageType } from '../shared/enums';\n"}
    all_duplicates = {}
    for module_path, content in modules.items():
        parser = TypeScriptModuleParser(content)
        duplicates = parser.find_duplicates()
        if duplicates:
            all_duplicates[module_path] = duplicates
    assert 'registry.ts' in all_duplicates
    assert 'isValidWebSocketMessageType' in all_duplicates['registry.ts']

def test_dynamic_import_duplicate_scenarios():
    """Test duplicate detection with dynamic imports"""
    content = "\nexport { dynamicFunction } from './module';\n\n// Later in the same file\nconst dynamicImport = async () => {\n  const { dynamicFunction } = await import('./other-module');\n  return dynamicFunction;\n};\n\nexport { dynamicFunction as dynamicFunctionAlias } from './third-module';\n"
    parser = TypeScriptModuleParser(content)
    exports = parser.extract_exports()
    assert 'dynamicFunction' in exports
    assert 'dynamicFunctionAlias' in exports

def test_build_optimization_duplicate_detection():
    """Test duplicate detection in optimized builds (tree shaking scenarios)"""

    def tree_shake_analysis(content: str) -> Dict[str, bool]:
        """Simulate tree-shaking analysis"""
        parser = TypeScriptModuleParser(content)
        exports = parser.extract_exports()
        used_exports = {}
        for export_name in exports:
            used_exports[export_name] = True
        return used_exports
    content = "\nexport { unusedFunction } from './module-a';\nexport { unusedFunction } from './module-b';\nexport { usedFunction } from './module-c';\n"
    analysis = tree_shake_analysis(content)
    parser = TypeScriptModuleParser(content)
    duplicates = parser.find_duplicates()
    assert 'unusedFunction' in duplicates
    assert 'usedFunction' in analysis

def test_monorepo_cross_package_duplicates():
    """Test duplicate detection across monorepo packages"""
    packages = {'@netra/frontend-types': "\nexport { WebSocketMessage } from './websocket';\nexport { isValidWebSocketMessageType } from './validators';\n", '@netra/shared-types': "\nexport { WebSocketMessage } from './base';\nexport { isValidWebSocketMessageType } from './enums';\n", 'main-app': "\nexport { WebSocketMessage } from '@netra/frontend-types';\nexport { WebSocketMessage } from '@netra/shared-types';\n"}
    parser = TypeScriptModuleParser(packages['main-app'])
    duplicates = parser.find_duplicates()
    assert 'WebSocketMessage' in duplicates
    assert len(duplicates['WebSocketMessage']) == 2

def test_webpack_module_federation_duplicates():
    """Test duplicate detection in webpack module federation scenarios"""
    federation_config = {'host_app': "\nexport { isValidWebSocketMessageType } from 'remote1/validators';\nexport { isValidWebSocketMessageType } from 'remote2/utils';\n", 'remote1': '\nexport function isValidWebSocketMessageType() {}\n', 'remote2': '  \nexport function isValidWebSocketMessageType() {}\n'}
    parser = TypeScriptModuleParser(federation_config['host_app'])
    duplicates = parser.find_duplicates()
    assert 'isValidWebSocketMessageType' in duplicates

def test_incremental_build_duplicate_detection():
    """Test duplicate detection in incremental builds"""
    build_state = {'previous_exports': {'registry.ts': {'isValidWebSocketMessageType': [(38, 're_export_from_shared/enums')]}}, 'current_exports': {'registry.ts': {'isValidWebSocketMessageType': [(38, 're_export_from_shared/enums'), (142, 're_export_from_domains/websocket')]}}}

    def detect_new_duplicates(previous, current):
        new_duplicates = {}
        for module, exports in current.items():
            for export_name, locations in exports.items():
                if len(locations) > 1:
                    prev_locations = previous.get(module, {}).get(export_name, [])
                    if len(prev_locations) <= 1:
                        new_duplicates[export_name] = locations
        return new_duplicates
    new_duplicates = detect_new_duplicates(build_state['previous_exports'], build_state['current_exports'])
    assert 'isValidWebSocketMessageType' in new_duplicates

def test_analyze_actual_frontend_registry_file(frontend_path):
    """Test analysis of the actual frontend registry.ts file"""
    registry_path = frontend_path / 'types' / 'registry.ts'
    if not registry_path.exists():
        pytest.skip('Frontend registry.ts not found')
    with open(registry_path, 'r', encoding='utf-8') as f:
        content = f.read()
    parser = TypeScriptModuleParser(content)
    duplicates = parser.find_duplicates()
    if duplicates:
        print(f'Found duplicates in registry.ts: {duplicates}')
        assert False, f'ACTUAL BUILD ERROR DETECTED: Duplicate exports found that will cause webpack compilation failure: {duplicates}'
    assert len(duplicates) == 0, 'Registry should not have duplicate exports'

def test_analyze_websocket_domain_file(frontend_path):
    """Test analysis of the actual websocket domain file"""
    websocket_path = frontend_path / 'types' / 'domains' / 'websocket.ts'
    if not websocket_path.exists():
        pytest.skip('Frontend websocket.ts not found')
    with open(websocket_path, 'r', encoding='utf-8') as f:
        content = f.read()
    parser = TypeScriptModuleParser(content)
    exports = parser.extract_exports()
    assert 'isValidWebSocketMessageType' in exports

def test_full_frontend_build_simulation(frontend_path):
    """Simulate a full frontend build to detect all duplicate export issues"""
    types_path = frontend_path / 'types'
    if not types_path.exists():
        pytest.skip('Frontend types directory not found')
    all_duplicates = {}
    for ts_file in types_path.rglob('*.ts'):
        if ts_file.is_file():
            try:
                with open(ts_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                parser = TypeScriptModuleParser(content)
                duplicates = parser.find_duplicates()
                if duplicates:
                    relative_path = ts_file.relative_to(frontend_path)
                    all_duplicates[str(relative_path)] = duplicates
            except Exception as e:
                print(f'Error analyzing {ts_file}: {e}')
    if all_duplicates:
        print(f'\\nDuplicate exports found across {len(all_duplicates)} files:')
        for file_path, duplicates in all_duplicates.items():
            print(f'  {file_path}: {list(duplicates.keys())}')
        assert False, f'Found duplicate exports that will cause build failures: {all_duplicates}'

def test_large_file_duplicate_detection_performance():
    """Test performance of duplicate detection on large TypeScript files"""
    import time
    large_content_lines = []
    for i in range(1000):
        large_content_lines.append(f"export const CONST_{i} = 'value_{i}';")
    large_content_lines.append("export { duplicateExport } from './module1';")
    large_content_lines.append("export { duplicateExport } from './module2';")
    large_content = '\\n'.join(large_content_lines)
    start_time = time.time()
    parser = TypeScriptModuleParser(large_content)
    duplicates = parser.find_duplicates()
    end_time = time.time()
    assert end_time - start_time < 1.0, 'Large file analysis should complete quickly'
    assert 'duplicateExport' in duplicates

def test_duplicate_export_fix_validation():
    """
    Test validation that duplicate exports are properly fixed.
    This test demonstrates the correct pattern after fix is applied.
    """
    fixed_registry = "// Re-export all enums and validation functions\nexport {\n  MessageType,\n  AgentStatus,\n  WebSocketMessageType,\n  isValidMessageType,\n  isValidAgentStatus,\n  isValidWebSocketMessageType,\n  getMessageTypeValues,\n  getAgentStatusValues,\n  getWebSocketMessageTypeValues,\n  getEnumKey,\n  ENUM_REGISTRY\n} from './shared/enums';\n\n// WebSocket runtime functions (without isValidWebSocketMessageType duplicate)\nexport {\n  createWebSocketError,\n  createWebSocketMessage,\n  isAgentCompletedMessage,\n  isAgentStartedMessage,\n  isAgentUpdateMessage,\n  isErrorMessage,\n  isSubAgentUpdateMessage,\n  isToolCallMessage,\n  isUserMessagePayload,\n  isWebSocketMessage\n} from './domains/websocket';"
    parser = TypeScriptModuleParser(fixed_registry)
    duplicates = parser.find_duplicates()
    assert len(duplicates) == 0, f'Fixed registry should have no duplicates, found: {duplicates}'
    exports = parser.extract_exports()
    assert 'isValidWebSocketMessageType' in exports, 'Function should still be exported'
    assert len(exports['isValidWebSocketMessageType']) == 1, 'Function should be exported exactly once'

def test_comprehensive_error_reporting():
    """Test comprehensive error reporting for multiple duplicate issues"""
    complex_problematic_content = "\nexport { duplicateA } from './module1';\nexport { duplicateA } from './module2';\nexport { duplicateB } from './module3';\nexport { duplicateB } from './module4';\nexport function duplicateC() {}\nexport const duplicateC = 'value';\n"
    parser = TypeScriptModuleParser(complex_problematic_content)
    duplicates = parser.find_duplicates()
    assert len(duplicates) == 3, f'Should detect 3 duplicates, found {len(duplicates)}'
    assert 'duplicateA' in duplicates
    assert 'duplicateB' in duplicates
    assert 'duplicateC' in duplicates
    for duplicate_name, locations in duplicates.items():
        assert len(locations) == 2, f'{duplicate_name} should have 2 occurrences, found {len(locations)}'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')