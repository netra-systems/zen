#!/bin/bash
# Production build with embedded credentials

echo "🔨 Building Zen with embedded community analytics..."

# Run credential embedding
python scripts/embed_credentials.py

# Build package
python -m build

# Verify embedded credentials
python -c "
try:
    from zen.telemetry.embedded_credentials import get_embedded_credentials
    creds = get_embedded_credentials()
    print('✅ Embedded credentials verified')
except Exception as e:
    print(f'❌ Embedded credentials error: {e}')
"

echo "🚀 Production build complete"
