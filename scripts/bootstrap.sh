#!/usr/bin/env bash
# Bootstrap script for Piper Voice Dataset Creation Project
# This script sets up the complete development environment

set -euo pipefail

echo "🚀 Bootstrapping Piper Voice Dataset Creation Project..."
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status messages
info() {
    echo -e "${GREEN}✓${NC} $1"
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
}

# Check Python version
echo "📋 Checking Python version..."
if ! command -v python3 &> /dev/null; then
    error "Python 3 is not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
PYTHON_MAJOR=$(python3 -c 'import sys; print(sys.version_info[0])')
PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info[1])')

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
    error "Python 3.11+ required, found $PYTHON_VERSION"
    exit 1
fi

info "Python $PYTHON_VERSION found"

# Check if UV is installed
echo ""
echo "📦 Checking UV package manager..."
if ! command -v uv &> /dev/null; then
    warn "UV not found, installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"

    if ! command -v uv &> /dev/null; then
        error "UV installation failed"
        exit 1
    fi
fi

UV_VERSION=$(uv --version)
info "UV found: $UV_VERSION"

# Check espeak-ng
echo ""
echo "🗣  Checking espeak-ng (phonetics engine)..."
if ! command -v espeak-ng &> /dev/null; then
    warn "espeak-ng not found"
    echo "   Please install espeak-ng:"
    echo "   macOS:   brew install espeak-ng"
    echo "   Linux:   sudo apt-get install espeak-ng"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    ESPEAK_VERSION=$(espeak-ng --version | head -n 1)
    info "$ESPEAK_VERSION found"

    # Check French voice
    if espeak-ng --voices | grep -q "fr"; then
        info "French voice available in espeak-ng"
    else
        warn "French voice not found in espeak-ng"
    fi
fi

# Sync dependencies
echo ""
echo "📚 Installing Python dependencies..."
uv sync

if [ $? -eq 0 ]; then
    info "Dependencies installed successfully"
else
    error "Dependency installation failed"
    exit 1
fi

# Install dev dependencies
echo ""
echo "🛠  Installing development dependencies..."
uv sync --extra dev

# Verify directory structure
echo ""
echo "📁 Verifying directory structure..."

REQUIRED_DIRS=(
    "piper_voice/core"
    "piper_voice/application"
    "piper_voice/infrastructure"
    "tests/unit"
    "tests/integration"
    "tests/validation"
    "scripts"
    "dataset/raw"
    "dataset/wav"
    "training"
    "models"
    "logs"
    "checkpoints"
    "configs"
    "docs/product/stories"
    "docs/product/decisions"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        info "$dir"
    else
        warn "$dir missing (creating...)"
        mkdir -p "$dir"
    fi
done

# Create config templates if they don't exist
echo ""
echo "⚙️  Creating configuration templates..."

# Audio quality config
if [ ! -f "configs/audio_quality.yaml" ]; then
    cat > configs/audio_quality.yaml <<EOF
# Audio Quality Validation Configuration

sample_rates:
  - 16000
  - 22050

format:
  type: "WAV"
  encoding: "PCM_16"

quality:
  min_snr_db: 30.0
  max_clipping_amplitude: 0.95
  max_silence_duration_sec: 0.3

duration:
  min_sec: 1.0
  max_sec: 15.0

file_size:
  max_mb: 5.0
EOF
    info "Created configs/audio_quality.yaml"
fi

# Phonetics config
if [ ! -f "configs/phonetics.yaml" ]; then
    cat > configs/phonetics.yaml <<EOF
# Phonetics Validation Configuration

language: "fr"
espeak_voice: "fr-fr"

validation:
  check_phonemization: true
  reject_on_error: true
  max_unknown_phonemes: 0
EOF
    info "Created configs/phonetics.yaml"
fi

# Training config
if [ ! -f "configs/training.yaml" ]; then
    cat > configs/training.yaml <<EOF
# Training Configuration

model:
  name: "fr_FR-custom-medium"
  sample_rate: 22050
  quality: "medium"

training:
  batch_size: 32
  max_epochs: 10000
  validation_split: 0.1
  num_test_examples: 5
  checkpoint_every_n_epochs: 1
  precision: 32

paths:
  dataset_dir: "./training"
  checkpoint_dir: "./checkpoints"
  model_output_dir: "./models"
EOF
    info "Created configs/training.yaml"
fi

# Run tests
echo ""
echo "🧪 Running initial test suite..."
if [ -f "scripts/test.sh" ]; then
    ./scripts/test.sh
else
    warn "Test script not found, skipping tests"
fi

# Final status
echo ""
echo "═══════════════════════════════════════════════════════════════"
info "Bootstrap complete!"
echo ""
echo "Next steps:"
echo "  1. Record audio files and place them in dataset/raw/"
echo "  2. Run: uv run python scripts/generate_metadata.py"
echo "  3. Run: uv run python scripts/validate_quality.py"
echo "  4. Run: uv run python scripts/prepare_dataset.py"
echo ""
echo "Development commands:"
echo "  Run tests:        ./scripts/test.sh"
echo "  Format code:      uv run ruff format ."
echo "  Lint code:        uv run ruff check ."
echo "  Type check:       uv run mypy piper_voice"
echo ""
echo "Documentation:"
echo "  Product stories:  docs/product/stories/"
echo "  ADRs:            docs/product/decisions/"
echo "  User guide:      docs/USER_GUIDE.md"
echo "═══════════════════════════════════════════════════════════════"
