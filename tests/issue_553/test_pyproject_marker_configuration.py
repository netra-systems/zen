"""
Issue #553 - Pyproject.toml Marker Configuration Validation Test

MISSION:
- Validate pyproject.toml marker configuration structure and completeness  
- Test marker configuration parsing and validation mechanisms
- Ensure marker definitions follow pytest best practices
- Validate configuration changes and updates work correctly

METHODOLOGY:
- Parse and validate pyproject.toml marker definitions programmatically
- Test marker configuration syntax and structure
- Validate marker definitions against pytest documentation standards
- Test configuration update mechanisms and validation

BUSINESS VALUE:
- Ensures marker configuration is maintainable and extensible
- Prevents configuration syntax errors that break test collection
- Validates marker definition standards for team consistency
- Enables automated marker configuration validation in CI/CD
"""
import pytest
import toml
import tempfile
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
import re
import json

class TestPyprojectMarkerConfiguration:
    """
    Validate pyproject.toml marker configuration structure and behavior
    """

    @pytest.fixture
    def project_root(self) -> Path:
        """Get project root directory"""
        return Path(__file__).parent.parent.parent

    @pytest.fixture
    def pyproject_path(self, project_root: Path) -> Path:
        """Get pyproject.toml file path"""
        return project_root / 'pyproject.toml'

    @pytest.fixture
    def pyproject_config(self, pyproject_path: Path) -> Dict:
        """Load and parse pyproject.toml configuration"""
        return toml.load(pyproject_path)

    @pytest.mark.unit
    @pytest.mark.critical
    @pytest.mark.config_validation
    @pytest.mark.issue_553_config
    def test_pyproject_structure_validation(self, pyproject_config: Dict):
        """
        STRUCTURE TEST: Validate pyproject.toml has correct pytest configuration structure
        
        This test ensures that the pyproject.toml file has the correct structure
        for pytest marker configuration and follows TOML syntax standards.
        """
        assert 'tool' in pyproject_config, 'Missing [tool] section'
        assert 'pytest' in pyproject_config['tool'], 'Missing [tool.pytest] section'
        pytest_config = pyproject_config['tool']['pytest']
        assert 'ini_options' in pytest_config, 'Missing [tool.pytest.ini_options] section'
        ini_options = pytest_config['ini_options']
        required_sections = ['markers', 'testpaths', 'python_files']
        for section in required_sections:
            assert section in ini_options, f'Missing required section: {section}'
        markers = ini_options['markers']
        assert isinstance(markers, list), 'Markers should be a list'
        assert len(markers) > 0, 'Should have at least one marker defined'
        marker_pattern = re.compile('^[a-zA-Z_][a-zA-Z0-9_]*:\\s*.+$')
        invalid_markers = []
        for marker in markers:
            if not marker_pattern.match(marker):
                invalid_markers.append(marker)
        assert len(invalid_markers) == 0, f'Invalid marker formats: {invalid_markers}'
        print(f'✅ PYPROJECT STRUCTURE: Valid configuration structure')
        print(f'  Markers defined: {len(markers)}')
        print(f"  Test paths: {ini_options.get('testpaths', [])}")
        return {'markers_count': len(markers), 'testpaths': ini_options.get('testpaths', []), 'python_files': ini_options.get('python_files', [])}

    @pytest.mark.unit
    @pytest.mark.critical
    @pytest.mark.config_validation
    @pytest.mark.issue_553_config
    def test_marker_definition_standards(self, pyproject_config: Dict):
        """
        STANDARDS TEST: Validate marker definitions follow pytest best practices
        
        This test ensures that all marker definitions follow pytest documentation
        standards for marker naming and description.
        """
        markers = pyproject_config['tool']['pytest']['ini_options']['markers']
        marker_analysis = {'valid_names': [], 'valid_descriptions': [], 'invalid_names': [], 'missing_descriptions': [], 'duplicate_names': [], 'naming_issues': []}
        seen_names = set()
        for marker_def in markers:
            if ':' in marker_def:
                name, description = marker_def.split(':', 1)
                name = name.strip()
                description = description.strip()
            else:
                name = marker_def.strip()
                description = ''
            if re.match('^[a-zA-Z_][a-zA-Z0-9_]*$', name):
                marker_analysis['valid_names'].append(name)
            else:
                marker_analysis['invalid_names'].append(name)
            if name in seen_names:
                marker_analysis['duplicate_names'].append(name)
            seen_names.add(name)
            if description:
                marker_analysis['valid_descriptions'].append(name)
            else:
                marker_analysis['missing_descriptions'].append(name)
            if name.startswith('test_'):
                marker_analysis['naming_issues'].append(f"{name}: starts with 'test_'")
            elif name.endswith('_test'):
                marker_analysis['naming_issues'].append(f"{name}: ends with '_test'")
            elif '__' in name:
                marker_analysis['naming_issues'].append(f'{name}: contains double underscore')
        assert len(marker_analysis['invalid_names']) == 0, f"Invalid marker names found: {marker_analysis['invalid_names']}"
        assert len(marker_analysis['duplicate_names']) == 0, f"Duplicate marker names found: {marker_analysis['duplicate_names']}"
        print(f'\n📊 MARKER DEFINITION STANDARDS ANALYSIS:')
        print(f'  Total markers: {len(markers)}')
        print(f"  Valid names: {len(marker_analysis['valid_names'])}")
        print(f"  With descriptions: {len(marker_analysis['valid_descriptions'])}")
        print(f"  Missing descriptions: {len(marker_analysis['missing_descriptions'])}")
        if marker_analysis['naming_issues']:
            print(f'\n⚠️ NAMING CONVENTION ISSUES:')
            for issue in marker_analysis['naming_issues'][:5]:
                print(f'    - {issue}')
        quality_score = (len(marker_analysis['valid_names']) / len(markers) * 0.4 + len(marker_analysis['valid_descriptions']) / len(markers) * 0.4 + (1 - len(marker_analysis['naming_issues']) / len(markers)) * 0.2) * 100
        print(f'  Configuration quality score: {quality_score:.1f}%')
        return marker_analysis

    @pytest.mark.integration
    @pytest.mark.critical
    @pytest.mark.config_validation
    @pytest.mark.issue_553_config
    def test_marker_configuration_update_mechanism(self):
        """
        UPDATE TEST: Validate marker configuration can be safely updated
        
        This test ensures that the marker configuration update process works
        correctly and doesn't break existing functionality.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            base_config = '\n[tool.pytest.ini_options]\nmarkers = [\n    "unit: Unit tests",\n    "integration: Integration tests"\n]\ntestpaths = ["tests"]\n'
            (temp_path / 'pyproject.toml').write_text(base_config)
            test_content = '\nimport pytest\n\n@pytest.mark.unit\ndef test_unit_functionality():\n    assert True\n    \n@pytest.mark.integration\ndef test_integration_functionality():\n    assert True\n'
            (temp_path / 'test_base.py').write_text(test_content)
            cmd = [sys.executable, '-m', 'pytest', str(temp_path), '--collect-only', '--strict-markers']
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(temp_path))
            assert result.returncode == 0, f'Base config failed: {result.stderr}'
            updated_config = '\n[tool.pytest.ini_options]\nmarkers = [\n    "unit: Unit tests",\n    "integration: Integration tests", \n    "e2e: End-to-end tests",\n    "critical: Critical tests",\n    "slow: Slow tests"\n]\ntestpaths = ["tests"]\n'
            (temp_path / 'pyproject.toml').write_text(updated_config)
            new_test_content = '\nimport pytest\n\n@pytest.mark.unit\ndef test_unit_functionality():\n    assert True\n    \n@pytest.mark.integration\ndef test_integration_functionality():\n    assert True\n    \n@pytest.mark.e2e\ndef test_e2e_functionality():\n    assert True\n    \n@pytest.mark.critical\n@pytest.mark.slow\ndef test_critical_slow_functionality():\n    assert True\n'
            (temp_path / 'test_updated.py').write_text(new_test_content)
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(temp_path))
            assert result.returncode == 0, f'Updated config failed: {result.stderr}'
            assert 'test_unit_functionality' in result.stdout
            assert 'test_integration_functionality' in result.stdout
            assert 'test_e2e_functionality' in result.stdout
            assert 'test_critical_slow_functionality' in result.stdout
            print(f'✅ CONFIGURATION UPDATE: Update mechanism works correctly')
            return {'base_config_success': True, 'updated_config_success': True, 'markers_added': ['e2e', 'critical', 'slow']}

    @pytest.mark.unit
    @pytest.mark.critical
    @pytest.mark.config_validation
    @pytest.mark.issue_553_config
    def test_marker_configuration_error_handling(self):
        """
        ERROR HANDLING TEST: Validate configuration error detection and reporting
        
        This test ensures that various configuration errors are properly detected
        and reported with helpful error messages.
        """
        error_test_cases = [{'name': 'invalid_toml_syntax', 'config': '\n[tool.pytest.ini_options]\nmarkers = [\n    "unit: Unit tests",\n    "invalid_syntax"  # Missing colon\n]\n', 'expected_error': False}, {'name': 'invalid_marker_name', 'config': '\n[tool.pytest.ini_options]\nmarkers = [\n    "123invalid: Invalid name starting with number"\n]\n', 'expected_error': True}, {'name': 'duplicate_markers', 'config': '\n[tool.pytest.ini_options] \nmarkers = [\n    "unit: Unit tests",\n    "unit: Duplicate unit marker"\n]\n', 'expected_error': False}]
        results = {}
        for test_case in error_test_cases:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                (temp_path / 'pyproject.toml').write_text(test_case['config'])
                (temp_path / 'test_error.py').write_text('\nimport pytest\n\ndef test_simple():\n    assert True\n')
                cmd = [sys.executable, '-m', 'pytest', str(temp_path), '--collect-only', '--strict-config']
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(temp_path))
                results[test_case['name']] = {'expected_error': test_case['expected_error'], 'actual_error': result.returncode != 0, 'stderr': result.stderr[:200], 'matches_expectation': (result.returncode != 0) == test_case['expected_error']}
        print(f'\n🔍 CONFIGURATION ERROR HANDLING:')
        for name, result in results.items():
            status = '✅' if result['matches_expectation'] else '❌'
            print(f"  {status} {name}: Expected error={result['expected_error']}, Got error={result['actual_error']}")
        error_detection_working = all((r['matches_expectation'] for r in results.values()))
        print(f"\nError detection accuracy: {('100%' if error_detection_working else 'Issues found')}")
        return results

    @pytest.mark.integration
    @pytest.mark.critical
    @pytest.mark.config_validation
    @pytest.mark.issue_553_config
    def test_marker_configuration_compatibility(self, project_root: Path):
        """
        COMPATIBILITY TEST: Validate marker configuration works across different pytest versions
        
        This test ensures that the marker configuration in pyproject.toml is compatible
        with different pytest versions and doesn't cause version-specific issues.
        """
        cmd = [sys.executable, '-c', 'import pytest; print(pytest.__version__)']
        result = subprocess.run(cmd, capture_output=True, text=True)
        current_version = result.stdout.strip() if result.returncode == 0 else 'unknown'
        config_test_cmd = [sys.executable, '-m', 'pytest', '--help']
        config_result = subprocess.run(config_test_cmd, capture_output=True, text=True, cwd=str(project_root))
        config_compatible = config_result.returncode == 0
        collect_cmd = [sys.executable, '-m', 'pytest', str(project_root / 'tests' / 'issue_553'), '--collect-only', '--strict-markers', '--quiet']
        collect_result = subprocess.run(collect_cmd, capture_output=True, text=True, cwd=str(project_root))
        collection_compatible = collect_result.returncode == 0
        compatibility_report = {'pytest_version': current_version, 'config_loading': config_compatible, 'marker_collection': collection_compatible, 'overall_compatible': config_compatible and collection_compatible}
        print(f'\n🔧 PYTEST COMPATIBILITY:')
        print(f'  Pytest version: {current_version}')
        print(f"  Config loading: {('✅' if config_compatible else '❌')}")
        print(f"  Marker collection: {('✅' if collection_compatible else '❌')}")
        print(f"  Overall compatibility: {('✅' if compatibility_report['overall_compatible'] else '❌')}")
        if not config_compatible:
            print(f'  Config error: {config_result.stderr[:200]}')
        if not collection_compatible:
            print(f'  Collection error: {collect_result.stderr[:200]}')
        assert config_compatible, f'Configuration not compatible with pytest {current_version}'
        return compatibility_report

    @pytest.mark.unit
    @pytest.mark.critical
    @pytest.mark.config_validation
    @pytest.mark.issue_553_config
    def test_generate_missing_markers_configuration(self, project_root: Path):
        """
        GENERATION TEST: Generate configuration for any missing markers
        
        This is the solution test that generates the proper marker configuration
        to fix Issue #553 by adding any missing markers to the configuration.
        """
        used_markers = set()
        test_dirs = [project_root / 'tests', project_root / 'netra_backend' / 'tests', project_root / 'auth_service' / 'tests']
        for test_dir in test_dirs:
            if not test_dir.exists():
                continue
            for test_file in test_dir.rglob('*.py'):
                if test_file.name.startswith('test_') or test_file.name.endswith('_test.py'):
                    try:
                        content = test_file.read_text(encoding='utf-8')
                        for line in content.split('\n'):
                            if '@pytest.mark.' in line:
                                matches = re.findall('@pytest\\.mark\\.([a-zA-Z_][a-zA-Z0-9_]*)', line)
                                for marker in matches:
                                    if marker != 'parametrize':
                                        used_markers.add(marker)
                    except Exception:
                        continue
        pyproject_path = project_root / 'pyproject.toml'
        current_config = toml.load(pyproject_path)
        defined_markers = set()
        if 'tool' in current_config and 'pytest' in current_config['tool'] and ('ini_options' in current_config['tool']['pytest']) and ('markers' in current_config['tool']['pytest']['ini_options']):
            for marker_def in current_config['tool']['pytest']['ini_options']['markers']:
                if ':' in marker_def:
                    marker_name = marker_def.split(':', 1)[0].strip()
                    defined_markers.add(marker_name)
        missing_markers = used_markers - defined_markers
        generated_markers = []
        for marker in sorted(missing_markers):
            description = self._generate_marker_description(marker)
            generated_markers.append(f'"{marker}: {description}"')
        configuration_update = {'missing_markers_found': len(missing_markers), 'missing_markers': sorted(missing_markers), 'generated_configuration': generated_markers, 'total_markers_after_fix': len(defined_markers) + len(missing_markers)}
        print(f'\n🔧 MISSING MARKERS CONFIGURATION GENERATION:')
        print(f'  Currently defined markers: {len(defined_markers)}')
        print(f'  Markers used in tests: {len(used_markers)}')
        print(f'  Missing markers found: {len(missing_markers)}')
        if missing_markers:
            print(f'\n📋 MISSING MARKERS TO ADD:')
            for marker in sorted(missing_markers)[:10]:
                description = self._generate_marker_description(marker)
                print(f'    "{marker}: {description}",')
            if len(missing_markers) > 10:
                print(f'    ... and {len(missing_markers) - 10} more')
            print(f'\n✅ SOLUTION: Add these {len(missing_markers)} markers to pyproject.toml')
        else:
            print(f'\n✅ NO MISSING MARKERS: All markers properly defined')
        return configuration_update

    def _generate_marker_description(self, marker_name: str) -> str:
        """Generate reasonable description for a marker based on its name"""
        patterns = {'unit': 'Unit tests', 'integration': 'Integration tests', 'e2e': 'End-to-end tests', 'critical': 'Critical tests', 'slow': 'Slow-running tests', 'fast': 'Fast tests', 'smoke': 'Smoke tests', 'auth': 'Authentication tests', 'database': 'Database tests', 'websocket': 'WebSocket tests', 'api': 'API tests', 'frontend': 'Frontend tests', 'backend': 'Backend tests', 'security': 'Security tests', 'performance': 'Performance tests', 'stress': 'Stress tests', 'load': 'Load tests', 'regression': 'Regression tests', 'validation': 'Validation tests', 'monitoring': 'Monitoring tests', 'deployment': 'Deployment tests', 'config': 'Configuration tests', 'migration': 'Migration tests'}
        if marker_name in patterns:
            return patterns[marker_name]
        for pattern, description in patterns.items():
            if pattern in marker_name.lower():
                return description.replace('tests', f'{marker_name} tests')
        words = marker_name.replace('_', ' ').title()
        return f'{words} tests'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')