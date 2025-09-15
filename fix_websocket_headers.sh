#!/bin/bash

# Fix WebSocket extra_headers parameter to additional_headers for Python 3.13 compatibility
echo "Starting WebSocket headers parameter fix..."

count=0
for file in $(find . -name "*.py" -not -path "./.test_venv/*" -not -path "./node_modules/*" -not -path "./.pytest_cache/*" -exec grep -l "websockets\.connect.*extra_headers" {} \;); do
    echo "Fixing $file"
    sed -i '' 's/extra_headers=/additional_headers=/g' "$file"
    ((count++))
done

echo "Fixed $count files"
echo "WebSocket headers parameter fix complete!"