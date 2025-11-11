#!/usr/bin/env bash
#
# Setup script for pre-commit hooks
# 
# This script installs and configures pre-commit hooks for the OctoLLM repository.
# It ensures all developers have consistent code quality checks.
#
# Usage: ./scripts/setup/setup-pre-commit.sh

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "🚀 Setting up pre-commit hooks for OctoLLM"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if running in repository root
cd "$REPO_ROOT"

# Step 1: Check Python installation
echo -e "\n${YELLOW}[1/6]${NC} Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error:${NC} Python 3 is not installed. Please install Python 3.11+ first."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION found"

# Step 2: Check Poetry installation
echo -e "\n${YELLOW}[2/6]${NC} Checking Poetry installation..."
if ! command -v poetry &> /dev/null; then
    echo -e "${YELLOW}⚠${NC} Poetry not found. Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
fi

POETRY_VERSION=$(poetry --version | awk '{print $3}')
echo -e "${GREEN}✓${NC} Poetry $POETRY_VERSION found"

# Step 3: Install Python dependencies
echo -e "\n${YELLOW}[3/6]${NC} Installing Python dependencies..."
poetry install --with dev
echo -e "${GREEN}✓${NC} Python dependencies installed"

# Step 4: Install pre-commit
echo -e "\n${YELLOW}[4/6]${NC} Installing pre-commit..."
poetry run pip install pre-commit
echo -e "${GREEN}✓${NC} pre-commit installed"

# Step 5: Install pre-commit hooks
echo -e "\n${YELLOW}[5/6]${NC} Installing pre-commit hooks..."
poetry run pre-commit install
poetry run pre-commit install --hook-type commit-msg
echo -e "${GREEN}✓${NC} Pre-commit hooks installed"

# Step 6: Run pre-commit on all files (optional, for validation)
echo -e "\n${YELLOW}[6/6]${NC} Running pre-commit on all files (this may take a while)..."
if poetry run pre-commit run --all-files; then
    echo -e "${GREEN}✓${NC} All pre-commit checks passed!"
else
    echo -e "${YELLOW}⚠${NC} Some pre-commit checks failed. This is normal for initial setup."
    echo -e "${YELLOW}⚠${NC} Run 'pre-commit run --all-files' to see and fix issues."
fi

# Additional setup for Rust (if available)
if command -v cargo &> /dev/null; then
    echo -e "\n${YELLOW}[Bonus]${NC} Rust detected, installing additional tools..."
    
    # Install rustfmt and clippy if not present
    if ! rustup component list | grep -q 'rustfmt.*installed'; then
        rustup component add rustfmt
        echo -e "${GREEN}✓${NC} rustfmt installed"
    fi
    
    if ! rustup component list | grep -q 'clippy.*installed'; then
        rustup component add clippy
        echo -e "${GREEN}✓${NC} clippy installed"
    fi
    
    # Install cargo-tarpaulin for coverage (Linux only)
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if ! command -v cargo-tarpaulin &> /dev/null; then
            echo "Installing cargo-tarpaulin for code coverage..."
            cargo install cargo-tarpaulin
            echo -e "${GREEN}✓${NC} cargo-tarpaulin installed"
        fi
    fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ Pre-commit setup complete!${NC}"
echo ""
echo "Pre-commit hooks will now run automatically on:"
echo "  • git commit (code quality checks)"
echo "  • git commit (commit message validation)"
echo "  • git push (test coverage checks)"
echo ""
echo "To run pre-commit manually:"
echo "  poetry run pre-commit run --all-files"
echo ""
echo "To skip pre-commit hooks (use sparingly):"
echo "  git commit --no-verify"
echo ""
echo "To update pre-commit hooks:"
echo "  poetry run pre-commit autoupdate"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
