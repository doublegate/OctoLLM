#!/bin/bash
# Setup script for pre-commit hooks

set -euo pipefail

echo "🔧 Installing pre-commit hooks for OctoLLM"

# Check if pre-commit is installed
if ! command -v pre-commit &> /dev/null; then
    echo "📦 Installing pre-commit..."
    pip install pre-commit
fi

# Install pre-commit hooks
echo "🎣 Installing git hooks..."
pre-commit install

# Run pre-commit on all files to verify setup
echo "✅ Running pre-commit on all files..."
pre-commit run --all-files || {
    echo "⚠️  Some hooks failed. This is normal on first run."
    echo "   Files have been auto-fixed where possible."
}

echo "✅ Pre-commit hooks installed successfully!"
echo ""
echo "Usage:"
echo "  - Hooks run automatically on 'git commit'"
echo "  - Manual run: 'pre-commit run --all-files'"
echo "  - Update hooks: 'pre-commit autoupdate'"
