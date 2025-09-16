#!/bin/bash

echo "🚀 Enabling automatic Claude metrics tracking..."

# Add this directory to PATH (before the real claude)
SCRIPT_DIR="/Users/rindhujajohnson/Netra/GitHub/netra-apex/scripts"

# Check if already in .zshrc
if ! grep -q "Claude auto-tracking" ~/.zshrc; then
    echo "" >> ~/.zshrc
    echo "# Claude auto-tracking" >> ~/.zshrc
    echo "export PATH=\"$SCRIPT_DIR:\$PATH\"" >> ~/.zshrc
    echo "✅ Added to ~/.zshrc"
else
    echo "✅ Already configured"
fi

echo ""
echo "📊 Claude tracking is now enabled!"
echo ""
echo "How it works:"
echo "  • Just use 'claude' normally - no changes needed"
echo "  • Every session automatically tracks to CloudSQL"
echo "  • See cost summary at end of each session"
echo ""
echo "⚠️  Run this to activate: source ~/.zshrc"
echo "  Or just open a new terminal"