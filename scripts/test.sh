#!/usr/bin/env bash
# Test runner script for Piper Voice Dataset Creation Project

set -euo pipefail

echo "🧪 Running Piper Voice test suite..."
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info() {
    echo -e "${GREEN}✓${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
}

# Track overall status
FAILED=0

# 1. Code formatting check
echo "═══════════════════════════════════════════════════════════════"
echo "1️⃣  Checking code formatting with ruff..."
echo "═══════════════════════════════════════════════════════════════"
if uv run ruff format --check .; then
    info "Code formatting check passed"
else
    error "Code formatting check failed"
    echo "   Run: uv run ruff format ."
    FAILED=1
fi
echo ""

# 2. Linting
echo "═══════════════════════════════════════════════════════════════"
echo "2️⃣  Linting code with ruff..."
echo "═══════════════════════════════════════════════════════════════"
if uv run ruff check .; then
    info "Linting passed"
else
    error "Linting failed"
    echo "   Run: uv run ruff check --fix ."
    FAILED=1
fi
echo ""

# 3. Type checking
echo "═══════════════════════════════════════════════════════════════"
echo "3️⃣  Type checking with mypy..."
echo "═══════════════════════════════════════════════════════════════"
if uv run mypy piper_voice; then
    info "Type checking passed"
else
    error "Type checking failed"
    FAILED=1
fi
echo ""

# 4. Unit tests
echo "═══════════════════════════════════════════════════════════════"
echo "4️⃣  Running unit tests..."
echo "═══════════════════════════════════════════════════════════════"
if uv run pytest tests/unit -v; then
    info "Unit tests passed"
else
    error "Unit tests failed"
    FAILED=1
fi
echo ""

# 5. Integration tests
echo "═══════════════════════════════════════════════════════════════"
echo "5️⃣  Running integration tests..."
echo "═══════════════════════════════════════════════════════════════"
if uv run pytest tests/integration -v; then
    info "Integration tests passed"
else
    error "Integration tests failed"
    FAILED=1
fi
echo ""

# 6. Validation tests
echo "═══════════════════════════════════════════════════════════════"
echo "6️⃣  Running validation tests..."
echo "═══════════════════════════════════════════════════════════════"
if uv run pytest tests/validation -v; then
    info "Validation tests passed"
else
    error "Validation tests failed"
    FAILED=1
fi
echo ""

# Final result
echo "═══════════════════════════════════════════════════════════════"
if [ $FAILED -eq 0 ]; then
    info "All tests passed! ✨"
    echo "═══════════════════════════════════════════════════════════════"
    exit 0
else
    error "Some tests failed"
    echo "═══════════════════════════════════════════════════════════════"
    exit 1
fi
