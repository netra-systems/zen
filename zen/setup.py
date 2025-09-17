"""
Setup script for ZEN - Multi-Instance Claude Orchestrator
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="zen-orchestrator",
    version="1.0.0",
    author="Netra Systems",
    description="Multi-instance Claude orchestrator for parallel task execution",
    long_description=long_description,
    long_description_content_type="text/markdown",
    py_modules=["zen_orchestrator"],
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
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
        "asyncio-subprocess",
        "PyYAML",
        "python-dateutil",
    ],
    extras_require={
        "netra": ["netraoptimizer"],
        "dev": ["pytest", "pytest-asyncio", "pytest-cov"],
    },
    entry_points={
        "console_scripts": [
            "zen=zen_orchestrator:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.json", "*.md", "docs/*", "tests/*"],
    },
)