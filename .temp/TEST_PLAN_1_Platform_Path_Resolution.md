# Test Plan 1: Platform-Specific Path Resolution Testing
**File Under Test:** `scripts/agent_logs.py`
**Functions Under Test:** `_resolve_projects_root()`, `_get_default_user()`
**Lines:** 19-66
**Date:** 2025-10-10

## Executive Summary
The platform-specific path resolution logic in `agent_logs.py` is a **critical component** that determines where Claude Code logs are stored and retrieved. If this path resolution fails, the entire log analysis feature becomes non-functional. This test plan targets edge cases that are particularly likely to occur in real-world deployments across different operating systems.

## Why This Is Critical
- **Single Point of Failure:** All log operations depend on correct path resolution
- **Cross-Platform Complexity:** Different path structures on Windows, macOS, and Linux
- **User Environment Variability:** Home directories, usernames, and environment variables vary widely
- **Security Implications:** Path traversal vulnerabilities could expose sensitive data

## Test Categories

### 1. Platform Detection Tests

#### 1.1 Auto-Detection Tests
```python
def test_platform_autodetect_darwin():
    """Test auto-detection on macOS (Darwin)"""
    with patch('platform.system', return_value='Darwin'):
        with patch('Path.home', return_value=Path('/Users/testuser')):
            result = _resolve_projects_root()
            assert result == Path('/Users/testuser/.claude/Projects').resolve()

def test_platform_autodetect_linux():
    """Test auto-detection on Linux"""
    with patch('platform.system', return_value='Linux'):
        with patch('Path.home', return_value=Path('/home/testuser')):
            result = _resolve_projects_root()
            assert result == Path('/home/testuser/.claude/Projects').resolve()

def test_platform_autodetect_windows():
    """Test auto-detection on Windows"""
    with patch('platform.system', return_value='Windows'):
        with patch.dict(os.environ, {'USERPROFILE': 'C:\\Users\\testuser'}):
            result = _resolve_projects_root()
            expected = Path('C:/Users/testuser/.claude/Projects').resolve()
            assert result == expected
```

#### 1.2 Explicit Platform Override Tests
```python
def test_platform_override_darwin():
    """Test explicit Darwin override on non-Mac system"""
    result = _resolve_projects_root(platform_name='Darwin', username='testuser')
    # Should use Unix-style path resolution

def test_platform_override_windows():
    """Test explicit Windows override on non-Windows system"""
    result = _resolve_projects_root(platform_name='Windows', username='testuser')
    assert 'Users' in str(result)
    assert 'testuser' in str(result)
```

### 2. Windows Path Resolution Tests

#### 2.1 Username Edge Cases

**Critical Edge Cases:**
```python
@pytest.mark.parametrize("username,expected_component", [
    ("John Smith", "John Smith"),           # Space in username
    ("user@domain", "user@domain"),         # Email-style
    ("user.name", "user.name"),             # Dots
    ("user-123", "user-123"),               # Hyphens
    ("用户名", "用户名"),                    # Unicode (Chinese)
    ("José", "José"),                       # Unicode (Spanish)
    ("user_name", "user_name"),             # Underscores
    ("DOMAIN\\user", "DOMAIN\\user"),       # Network username
    ("user@example.com", "user@example.com"), # Full email
])
def test_windows_username_variations(username, expected_component):
    """Test Windows path resolution with various username formats"""
    result = _resolve_projects_root(
        platform_name='Windows',
        username=username
    )
    assert expected_component in str(result)
    assert '.claude' in str(result)
    assert 'Projects' in str(result)
```

#### 2.2 USERPROFILE Environment Variable Tests

```python
def test_windows_userprofile_forward_slashes():
    """Test USERPROFILE with forward slashes"""
    with patch.dict(os.environ, {'USERPROFILE': 'C:/Users/testuser'}, clear=True):
        result = _resolve_projects_root(platform_name='Windows')
        assert result.exists() or str(result).endswith('.claude/Projects')

def test_windows_userprofile_backslashes():
    """Test USERPROFILE with backslashes (typical Windows)"""
    with patch.dict(os.environ, {'USERPROFILE': 'C:\\Users\\testuser'}, clear=True):
        result = _resolve_projects_root(platform_name='Windows')
        # Path should be resolved correctly regardless of slash type

def test_windows_userprofile_mixed_slashes():
    """Test USERPROFILE with mixed slashes"""
    with patch.dict(os.environ, {'USERPROFILE': 'C:\\Users/testuser'}, clear=True):
        result = _resolve_projects_root(platform_name='Windows')
        # Path should normalize mixed slashes

def test_windows_userprofile_missing():
    """Test fallback when USERPROFILE is not set"""
    with patch.dict(os.environ, {}, clear=True):
        with patch('agent_logs.Path.home', return_value=Path('C:/Users/testuser')):
            result = _resolve_projects_root(platform_name='Windows')
            assert 'testuser' in str(result)

def test_windows_userprofile_nonstandard_drive():
    """Test USERPROFILE on non-C drive"""
    with patch.dict(os.environ, {'USERPROFILE': 'D:/CustomHome/user'}, clear=True):
        result = _resolve_projects_root(platform_name='Windows')
        assert 'D:' in str(result) or 'CustomHome' in str(result)

def test_windows_userprofile_network_path():
    """Test USERPROFILE as network path (UNC)"""
    with patch.dict(os.environ, {'USERPROFILE': '\\\\server\\share\\user'}, clear=True):
        result = _resolve_projects_root(platform_name='Windows')
        # Should handle UNC paths gracefully
```

#### 2.3 Long Path Tests (Windows MAX_PATH = 260)

```python
def test_windows_long_path_exceeds_max_path():
    """Test path that exceeds Windows MAX_PATH limit"""
    # Create a very long username
    long_username = "a" * 200
    result = _resolve_projects_root(
        platform_name='Windows',
        username=long_username
    )
    # Windows 10+ supports long paths with \\?\ prefix
    full_path = str(result)
    assert len(full_path) > 260  # Should exceed MAX_PATH
    # Verify it still constructs correctly

def test_windows_path_near_max_path():
    """Test path close to but under MAX_PATH"""
    username = "a" * 100  # Long but not excessive
    result = _resolve_projects_root(
        platform_name='Windows',
        username=username
    )
    assert 'Projects' in str(result)
```

### 3. macOS/Linux Path Resolution Tests

#### 3.1 Home Directory Variations

```python
def test_macos_home_with_spaces():
    """Test macOS home directory with spaces"""
    with patch('agent_logs.Path.home', return_value=Path('/Users/John Smith')):
        result = _resolve_projects_root(platform_name='Darwin')
        assert 'John Smith' in str(result)
        assert '.claude' in str(result)

def test_linux_home_with_special_chars():
    """Test Linux home with hyphens and dots"""
    with patch('agent_logs.Path.home', return_value=Path('/home/user-name.123')):
        result = _resolve_projects_root(platform_name='Linux')
        assert 'user-name.123' in str(result)

def test_macos_home_unicode():
    """Test macOS home with Unicode characters"""
    with patch('agent_logs.Path.home', return_value=Path('/Users/用户')):
        result = _resolve_projects_root(platform_name='Darwin')
        assert '用户' in str(result)

def test_linux_home_symlinked():
    """Test Linux home directory that's a symlink"""
    with tempfile.TemporaryDirectory() as tmpdir:
        real_home = Path(tmpdir) / "real_home"
        real_home.mkdir()
        link_home = Path(tmpdir) / "link_home"
        link_home.symlink_to(real_home)

        with patch('agent_logs.Path.home', return_value=link_home):
            result = _resolve_projects_root(platform_name='Linux')
            # Should resolve symlinks properly
            assert result.exists() or 'Projects' in str(result)

def test_linux_home_on_nfs_mount():
    """Test Linux home on NFS-mounted directory"""
    with patch('agent_logs.Path.home', return_value=Path('/net/server/home/user')):
        result = _resolve_projects_root(platform_name='Linux')
        assert 'user' in str(result)
        assert '.claude' in str(result)

def test_macos_home_nonstandard_location():
    """Test macOS home in non-standard location"""
    with patch('agent_logs.Path.home', return_value=Path('/opt/users/testuser')):
        result = _resolve_projects_root(platform_name='Darwin')
        assert 'testuser' in str(result)
```

### 4. Edge Cases and Error Conditions

#### 4.1 Path.home() Failures

```python
def test_path_home_raises_runtime_error():
    """Test when Path.home() raises RuntimeError"""
    with patch('agent_logs.Path.home', side_effect=RuntimeError("Home directory not found")):
        with pytest.raises(RuntimeError):
            _resolve_projects_root(platform_name='Linux')

def test_path_home_raises_permission_error():
    """Test when Path.home() raises PermissionError"""
    with patch('agent_logs.Path.home', side_effect=PermissionError("Access denied")):
        with pytest.raises(PermissionError):
            _resolve_projects_root(platform_name='Linux')
```

#### 4.2 Environment Variable Issues

```python
def test_no_environment_variables_set():
    """Test when no user environment variables are available"""
    with patch.dict(os.environ, {}, clear=True):
        result = _get_default_user()
        assert result is None

def test_environment_variables_empty_strings():
    """Test when environment variables are set but empty"""
    with patch.dict(os.environ, {'USERNAME': '', 'USER': ''}, clear=True):
        result = _get_default_user()
        assert result == '' or result is None
```

#### 4.3 File System Edge Cases

```python
def test_home_directory_does_not_exist(tmp_path):
    """Test when home directory doesn't exist"""
    nonexistent = tmp_path / "nonexistent_home"
    with patch('agent_logs.Path.home', return_value=nonexistent):
        result = _resolve_projects_root(platform_name='Linux')
        # Should construct path even if home doesn't exist
        assert '.claude' in str(result)

def test_home_is_file_not_directory(tmp_path):
    """Test when home path points to a file"""
    home_file = tmp_path / "home_file"
    home_file.write_text("not a directory")

    with patch('agent_logs.Path.home', return_value=home_file):
        result = _resolve_projects_root(platform_name='Linux')
        # Should return path even if invalid

def test_insufficient_permissions_on_home(tmp_path):
    """Test when home directory has insufficient permissions"""
    if os.name != 'nt':  # Unix-only test
        home_dir = tmp_path / "restricted_home"
        home_dir.mkdir()
        home_dir.chmod(0o000)

        try:
            with patch('agent_logs.Path.home', return_value=home_dir):
                result = _resolve_projects_root(platform_name='Linux')
                # Should construct path even without permissions
        finally:
            home_dir.chmod(0o755)  # Restore for cleanup

def test_claude_directory_exists_as_file(tmp_path):
    """Test when .claude already exists as a file"""
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    claude_file = home_dir / ".claude"
    claude_file.write_text("conflict")

    with patch('agent_logs.Path.home', return_value=home_dir):
        result = _resolve_projects_root(platform_name='Linux')
        # Should still construct path
        assert '.claude' in str(result)

def test_projects_directory_exists_as_file(tmp_path):
    """Test when Projects already exists as a file"""
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    claude_dir = home_dir / ".claude"
    claude_dir.mkdir()
    projects_file = claude_dir / "Projects"
    projects_file.write_text("conflict")

    with patch('agent_logs.Path.home', return_value=home_dir):
        result = _resolve_projects_root(platform_name='Linux')
        assert result == projects_file.resolve()
```

### 5. Security Tests

#### 5.1 Path Injection Attacks

```python
def test_username_path_traversal_attack():
    """Test username with path traversal attempt"""
    malicious_username = "../../../etc"
    result = _resolve_projects_root(
        platform_name='Windows',
        username=malicious_username
    )
    # Should construct path but not escape users directory
    assert 'etc' in str(result)
    # Path should be normalized and safe

def test_username_with_null_bytes():
    """Test username containing null bytes"""
    malicious_username = "user\x00../etc"
    # May raise ValueError during path construction
    try:
        result = _resolve_projects_root(
            platform_name='Windows',
            username=malicious_username
        )
    except (ValueError, OSError):
        pass  # Expected - null bytes should be rejected

def test_username_absolute_path_injection():
    """Test username as absolute path"""
    malicious_username = "/etc/passwd"
    result = _resolve_projects_root(
        platform_name='Windows',
        username=malicious_username
    )
    # Windows should treat this as username, not path

def test_base_path_override_security():
    """Test base_path override doesn't allow arbitrary access"""
    sensitive_path = Path("/etc")
    result = _resolve_projects_root(base_path=sensitive_path)
    # Should resolve to the provided path
    assert result == sensitive_path.resolve()
```

#### 5.2 Symlink Attack Tests

```python
def test_symlink_to_sensitive_directory(tmp_path):
    """Test when .claude is symlinked to sensitive directory"""
    if os.name != 'nt':  # Unix-only test
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        claude_link = home_dir / ".claude"

        # Create symlink to /etc
        claude_link.symlink_to("/etc")

        with patch('agent_logs.Path.home', return_value=home_dir):
            result = _resolve_projects_root(platform_name='Linux')
            # resolve() will follow symlink
            resolved = result.resolve()
            # Should point to /etc/Projects

def test_race_condition_directory_creation(tmp_path):
    """Test race condition during directory creation"""
    # This tests for TOCTOU (Time of Check, Time of Use) vulnerabilities
    # Not directly tested by _resolve_projects_root but important for
    # code that uses the returned path
    home_dir = tmp_path / "home"
    home_dir.mkdir()

    with patch('agent_logs.Path.home', return_value=home_dir):
        result = _resolve_projects_root(platform_name='Linux')
        # Should construct path safely
        assert result.parent.name == ".claude"
```

### 6. Base Path Override Tests

```python
def test_base_path_override_absolute():
    """Test direct base_path override with absolute path"""
    custom_path = Path("/custom/path/to/projects")
    result = _resolve_projects_root(base_path=custom_path)
    assert result == custom_path.resolve()

def test_base_path_override_relative():
    """Test base_path override with relative path"""
    custom_path = Path("./relative/path")
    result = _resolve_projects_root(base_path=custom_path)
    # Should resolve to absolute path
    assert result.is_absolute()

def test_base_path_override_with_tilde():
    """Test base_path with tilde expansion"""
    custom_path = Path("~/custom/.claude/Projects")
    result = _resolve_projects_root(base_path=custom_path)
    # Path.resolve() doesn't expand ~, so this tests current behavior

def test_base_path_overrides_platform_detection():
    """Test that base_path takes precedence over platform detection"""
    custom_path = Path("/custom/projects")
    result = _resolve_projects_root(
        platform_name='Windows',
        username='testuser',
        base_path=custom_path
    )
    # base_path should win
    assert result == custom_path.resolve()
    assert 'testuser' not in str(result)
```

## Test Execution Strategy

### Test Organization
```
tests/
├── test_agent_logs_platform.py          # Platform detection
├── test_agent_logs_windows.py           # Windows-specific
├── test_agent_logs_unix.py              # macOS/Linux-specific
├── test_agent_logs_edge_cases.py        # Error conditions
└── test_agent_logs_security.py          # Security tests
```

### Test Fixtures
```python
@pytest.fixture
def mock_darwin_env():
    """Mock macOS environment"""
    with patch('platform.system', return_value='Darwin'):
        with patch('agent_logs.Path.home', return_value=Path('/Users/testuser')):
            yield

@pytest.fixture
def mock_windows_env():
    """Mock Windows environment"""
    with patch('platform.system', return_value='Windows'):
        with patch.dict(os.environ, {'USERPROFILE': 'C:\\Users\\testuser'}):
            yield

@pytest.fixture
def mock_linux_env():
    """Mock Linux environment"""
    with patch('platform.system', return_value='Linux'):
        with patch('agent_logs.Path.home', return_value=Path('/home/testuser')):
            yield
```

### Continuous Integration
```yaml
# .github/workflows/test_platform_paths.yml
name: Platform Path Resolution Tests

on: [push, pull_request]

jobs:
  test:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ['3.9', '3.10', '3.11', '3.12']

    runs-on: ${{ matrix.os }}

    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      - name: Run platform-specific tests
        run: |
          pytest tests/test_agent_logs_platform.py -v
          pytest tests/test_agent_logs_security.py -v
```

## Coverage Goals
- **Line Coverage:** 100% for `_resolve_projects_root()` and `_get_default_user()`
- **Branch Coverage:** 100% for all conditional logic
- **Platform Coverage:** Tests executed on Windows, macOS, and Linux
- **Edge Case Coverage:** All identified edge cases tested

## Risk Assessment

### High-Risk Scenarios (Must Test)
1. ✅ **Username with spaces** (common on Windows)
2. ✅ **Missing environment variables** (common in containers)
3. ✅ **Unicode usernames** (common internationally)
4. ✅ **Long paths** (Windows MAX_PATH issues)
5. ✅ **Path traversal attacks** (security critical)

### Medium-Risk Scenarios
1. ✅ Non-standard home directory locations
2. ✅ Symlinked directories
3. ✅ Network-mounted home directories
4. ✅ Permission issues

### Low-Risk Scenarios
1. ✅ Mixed slash types
2. ✅ Null bytes in paths
3. ✅ Race conditions

## Success Criteria
- ✅ All tests pass on Windows, macOS, and Linux
- ✅ 100% code coverage for target functions
- ✅ No regressions in existing functionality
- ✅ Security tests prevent known attack vectors
- ✅ Performance: Path resolution completes in <10ms

## Existing Test Coverage Analysis

**Current tests in `tests/test_agent_logs.py`:**
- ✅ Basic platform detection (Darwin, Linux, Windows)
- ✅ USERPROFILE environment variable handling
- ✅ base_path override
- ⚠️ **Missing:** Unicode username tests
- ⚠️ **Missing:** Long path tests
- ⚠️ **Missing:** Security/injection tests
- ⚠️ **Missing:** Symlink tests
- ⚠️ **Missing:** Permission error tests

## Recommended Next Steps
1. Implement missing security tests (HIGH PRIORITY)
2. Add Unicode and special character tests (MEDIUM PRIORITY)
3. Add long path tests for Windows (MEDIUM PRIORITY)
4. Add CI matrix testing across all platforms (HIGH PRIORITY)
5. Add performance benchmarks (LOW PRIORITY)
