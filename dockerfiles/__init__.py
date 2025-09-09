# This __init__.py file prevents the docker/ directory from being treated as a namespace package
# that could interfere with the actual docker Python package.
# The docker/ directory contains Dockerfiles and related configuration, not Python modules.