# Packaging Zen for Global Distribution

## Overview
This guide covers how to package and distribute the Zen orchestrator tool to the global community via PyPI, Homebrew, and other package managers.

## Distribution Channels

### 1. PyPI (Python Package Index)
The primary distribution channel for Python packages.

#### Prerequisites
- PyPI account (https://pypi.org/account/register/)
- Test PyPI account (https://test.pypi.org/account/register/)
- API tokens for both accounts

#### Setup Steps

1. **Install build tools:**
```bash
pip install --upgrade build twine
```

2. **Configure PyPI credentials:**
Create `~/.pypirc`:
```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-YOUR-TOKEN-HERE

[testpypi]
username = __token__
password = pypi-YOUR-TEST-TOKEN-HERE
```

3. **Build the package:**
```bash
cd zen/
python -m build
```

4. **Test upload to TestPyPI:**
```bash
python -m twine upload --repository testpypi dist/*
```

5. **Test installation from TestPyPI:**
```bash
pip install --index-url https://test.pypi.org/simple/ --no-deps zen-orchestrator
```

6. **Upload to PyPI:**
```bash
python -m twine upload dist/*
```

### 2. Homebrew (macOS/Linux)
Popular package manager for macOS and Linux.

#### Create Formula
Create a Homebrew formula in a tap repository:

```ruby
class Zen < Formula
  include Language::Python::Virtualenv

  desc "Multi-instance Claude orchestrator for parallel task execution"
  homepage "https://github.com/netra-systems/zen"
  url "https://files.pythonhosted.org/packages/source/z/zen-orchestrator/zen-orchestrator-1.0.0.tar.gz"
  sha256 "YOUR-SHA256-HERE"
  license "MIT"

  depends_on "python@3.11"

  resource "PyYAML" do
    url "https://files.pythonhosted.org/packages/source/P/PyYAML/PyYAML-6.0.tar.gz"
    sha256 "SHA256-HERE"
  end

  resource "python-dateutil" do
    url "https://files.pythonhosted.org/packages/source/p/python-dateutil/python-dateutil-2.8.2.tar.gz"
    sha256 "SHA256-HERE"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "Claude Code Instance Orchestrator", shell_output("#{bin}/zen --help")
  end
end
```

### 3. Docker Hub
For containerized distribution.

#### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install .

ENTRYPOINT ["zen"]
```

#### Build and Push
```bash
docker build -t netrasystems/zen:latest .
docker push netrasystems/zen:latest
```

### 4. Snap Store (Linux)
For Linux distribution.

Create `snapcraft.yaml`:
```yaml
name: zen-orchestrator
version: '1.0.0'
summary: Multi-instance Claude orchestrator
description: |
  Zen orchestrates multiple Claude Code instances in parallel
  for efficient task execution.

grade: stable
confinement: strict

apps:
  zen:
    command: bin/zen
    plugs:
      - network
      - home

parts:
  zen:
    plugin: python
    source: .
    requirements:
      - requirements.txt
```

## Version Management

### Semantic Versioning
Follow semantic versioning (MAJOR.MINOR.PATCH):
- MAJOR: Breaking API changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes

### Version Locations
Update version in:
1. `setup.py`
2. `__init__.py`
3. `pyproject.toml`
4. Git tag

### Release Process

1. **Update version numbers:**
```bash
# Update version in all files
sed -i '' 's/1.0.0/1.1.0/g' setup.py __init__.py pyproject.toml
```

2. **Update CHANGELOG:**
```bash
# Document changes in CHANGELOG.md
```

3. **Commit and tag:**
```bash
git add .
git commit -m "Release v1.1.0"
git tag -a v1.1.0 -m "Release version 1.1.0"
git push origin main --tags
```

4. **Build distribution:**
```bash
rm -rf dist/ build/ *.egg-info
python -m build
```

5. **Upload to PyPI:**
```bash
python -m twine upload dist/*
```

## GitHub Release Automation

### GitHub Actions Workflow
Create `.github/workflows/release.yml`:

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install build twine
    
    - name: Build package
      run: python -m build
    
    - name: Publish to PyPI
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
      run: twine upload dist/*
    
    - name: Create GitHub Release
      uses: softprops/action-gh-release@v1
      with:
        files: dist/*
        generate_release_notes: true
```

## Testing Distribution

### Local Testing
```bash
# Create virtual environment
python -m venv test-env
source test-env/bin/activate

# Install from local build
pip install dist/zen_orchestrator-*.whl

# Test
zen --help
```

### Integration Testing
```bash
# Test with different Python versions
tox -e py38,py39,py310,py311,py312
```

## Documentation

### PyPI Documentation
- Update README.md with:
  - Clear installation instructions
  - Usage examples
  - API documentation
  - Contributing guidelines

### Documentation Hosting
- ReadTheDocs: https://readthedocs.org/
- GitHub Pages: Via `docs/` directory

## Marketing & Community

### Package Discovery
1. **PyPI Classifiers:** Choose appropriate classifiers in setup.py
2. **Keywords:** Add relevant keywords for search
3. **Badges:** Add badges to README (version, downloads, license)

### Community Channels
1. **GitHub:** Issues, discussions, wiki
2. **Discord/Slack:** Community support
3. **Twitter/X:** Release announcements
4. **Dev.to/Medium:** Tutorial articles

## Security Considerations

### Supply Chain Security
1. **Sign releases:** Use GPG signing for tags
2. **SBOM:** Generate Software Bill of Materials
3. **Vulnerability scanning:** Use GitHub Dependabot
4. **2FA:** Enable on PyPI and GitHub accounts

### License Compliance
1. Ensure all dependencies are compatible with chosen license
2. Include LICENSE file in distribution
3. Add license headers to source files

## Monitoring

### Package Analytics
- PyPI download stats: https://pypistats.org/
- GitHub stars/forks tracking
- User feedback via issues

### Quality Metrics
- Test coverage (aim for >80%)
- Documentation coverage
- Code quality (pylint, black, mypy)

## Troubleshooting

### Common Issues

1. **Module not found after installation:**
   - Check PYTHONPATH
   - Verify installation location
   - Check for naming conflicts

2. **Command not in PATH:**
   - Run `pipx ensurepath`
   - Add to shell configuration

3. **Dependency conflicts:**
   - Use version ranges in requirements
   - Test with different Python versions

## Checklist for Release

- [ ] Version bumped in all files
- [ ] CHANGELOG.md updated
- [ ] Tests passing
- [ ] Documentation updated
- [ ] License file included
- [ ] README has installation instructions
- [ ] Package builds successfully
- [ ] TestPyPI upload successful
- [ ] Installation from TestPyPI works
- [ ] Git tag created
- [ ] PyPI upload successful
- [ ] GitHub release created
- [ ] Announcement posted