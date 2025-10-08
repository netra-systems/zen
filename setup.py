"""
Setup script for ZEN - Multi-Instance Claude Orchestrator
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="netra-zen",
    version="1.0.7",
    author=" Systems",
    author_email="pypi@netrasystems.ai",
    description="Multi-instance Claude orchestrator for parallel task execution",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/netra-systems/zen",
    project_urls={
        "Bug Tracker": "https://github.com/netra-systems/zen/issues",
        "Documentation": "https://github.com/netra-systems/zen#readme",
        "Source Code": "https://github.com/netra-systems/zen",
        "Changelog": "https://github.com/netra-systems/zen/blob/main/CHANGELOG.md",
    },
    keywords="claude, ai, orchestration, parallel, automation, llm, anthropic",
    py_modules=["zen_orchestrator"],
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: Commercial :: Commercial",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "PyYAML>=6.0",
        "python-dateutil>=2.8.2",
    ],
    extras_require={
        "dev": ["pytest", "pytest-asyncio", "pytest-cov"],
    },
    entry_points={
        "console_scripts": [
            "zen=zen_orchestrator:run",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.json", "*.md", "docs/*", "tests/*"],
    },
)