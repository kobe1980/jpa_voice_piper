#!/bin/bash
# Complete workflow to create a Japanese voice model with JSUT corpus
#
# This script automates the entire pipeline:
# 1. Download JSUT corpus
# 2. Prepare dataset
# 3. Phonemize corpus
# 4. Preprocess for Piper
# 5. Train voice model
# 6. Export to ONNX
# 7. Test the voice
#
# Usage:
#   ./scripts/create_japanese_voice.sh [--skip-download] [--fast] [--high-quality]

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default options
SKIP_DOWNLOAD=false
TRAINING_MODE="fast"
JSUT_SUBSET="basic5000"
SAMPLE_RATE=22050

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --skip-download)
      SKIP_DOWNLOAD=true
      shift
      ;;
    --fast)
      TRAINING_MODE="fast"
      shift
      ;;
    --high-quality)
      TRAINING_MODE="high-quality"
      shift
      ;;
    --full-jsut)
      JSUT_SUBSET="all"
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--skip-download] [--fast|--high-quality] [--full-jsut]"
      exit 1
      ;;
  esac
done

# Helper functions
print_header() {
    echo ""
    echo -e "${BLUE}========================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

check_command() {
    if ! command -v $1 &> /dev/null; then
        print_error "Required command not found: $1"
        echo "Please install $1 and try again"
        exit 1
    fi
}

estimate_time() {
    local step=$1
    local mode=$2

    case $step in
        download)
            echo "~10 minutes (depends on connection speed)"
            ;;
        prepare)
            echo "~30-60 minutes (5,000 audio files)"
            ;;
        phonemize)
            echo "~3-5 minutes"
            ;;
        preprocess)
            echo "~5-10 minutes"
            ;;
        train)
            if [[ $mode == "fast" ]]; then
                echo "~30 min (GPU) / ~1-2 hours (Apple Silicon) / ~5-10 hours (CPU)"
            else
                echo "~1-2 days (GPU) / ~2-3 days (Apple Silicon) / Not recommended (CPU)"
            fi
            ;;
        export)
            echo "~1 minute"
            ;;
    esac
}

# Main script
print_header "🎌 Japanese Voice Creation Pipeline"

echo "Configuration:"
echo "  JSUT Subset: $JSUT_SUBSET"
echo "  Sample Rate: $SAMPLE_RATE Hz"
echo "  Training Mode: $TRAINING_MODE"
echo "  Skip Download: $SKIP_DOWNLOAD"
echo ""

# Check prerequisites
print_header "Step 0: Checking Prerequisites"

print_info "Checking required commands..."
check_command uv
check_command wget
check_command unzip

print_info "Checking Python packages..."
if ! uv run python -c "import pykakasi" 2>/dev/null; then
    print_error "Python package 'pykakasi' not found"
    echo "Run: uv sync --extra audio"
    exit 1
fi

print_success "All prerequisites satisfied"

# Estimate total time
print_info "Estimated total time:"
if [[ $TRAINING_MODE == "fast" ]]; then
    echo "  - With GPU: ~2-3 hours"
    echo "  - With Apple Silicon: ~3-5 hours"
    echo "  - With CPU: ~15-20 hours"
else
    echo "  - With GPU: ~1-2 days"
    echo "  - With Apple Silicon: ~2-3 days"
fi
echo ""

read -p "Continue? [Y/n] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]] && [[ ! -z $REPLY ]]; then
    echo "Aborted by user"
    exit 0
fi

# Step 1: Download JSUT corpus
if [[ $SKIP_DOWNLOAD == false ]]; then
    print_header "Step 1/7: Download JSUT Corpus ($(estimate_time download))"

    if [ -d "dataset/jsut/$JSUT_SUBSET" ]; then
        print_warning "JSUT directory already exists: dataset/jsut/$JSUT_SUBSET"
        read -p "Skip download? [Y/n] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
            print_info "Skipping download"
        else
            print_info "Downloading JSUT $JSUT_SUBSET..."
            ./scripts/download_jsut.sh
        fi
    else
        print_info "Downloading JSUT $JSUT_SUBSET..."
        ./scripts/download_jsut.sh
    fi

    print_success "JSUT corpus ready"
else
    print_header "Step 1/7: Download JSUT Corpus (SKIPPED)"
    print_info "Using existing JSUT corpus"
fi

# Step 2: Prepare dataset
print_header "Step 2/7: Prepare Dataset ($(estimate_time prepare))"

if [ -d "dataset/prepared" ]; then
    print_warning "Prepared dataset directory already exists"
    read -p "Overwrite? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Removing existing prepared dataset..."
        rm -rf dataset/prepared
    else
        print_info "Skipping dataset preparation"
        if [ ! -f "dataset/prepared/metadata.csv" ]; then
            print_error "metadata.csv not found in dataset/prepared"
            exit 1
        fi
        print_success "Using existing prepared dataset"
        # Skip to next step
        SKIP_PREPARE=true
    fi
fi

if [[ $SKIP_PREPARE != true ]]; then
    print_info "Preparing JSUT dataset..."
    print_info "This will take approximately $(estimate_time prepare)"

    uv run python scripts/prepare_jsut_dataset.py \
        --jsut-dir "dataset/jsut/$JSUT_SUBSET" \
        --output-dir dataset/prepared \
        --sample-rate $SAMPLE_RATE

    if [ $? -eq 0 ]; then
        print_success "Dataset prepared successfully"
    else
        print_error "Dataset preparation failed"
        exit 1
    fi
fi

# Step 3: Phonemize corpus
print_header "Step 3/7: Phonemize Corpus ($(estimate_time phonemize))"

if [ -f "dataset/prepared/metadata_phonemes.csv" ]; then
    print_warning "Phonemized metadata already exists"
    read -p "Skip phonemization? [Y/n] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
        print_info "Skipping phonemization"
        SKIP_PHONEMIZE=true
    else
        print_info "Re-phonemizing corpus..."
        rm -f dataset/prepared/metadata_phonemes.csv
        rm -f dataset/prepared/phoneme_map.json
    fi
fi

if [[ $SKIP_PHONEMIZE != true ]]; then
    print_info "Converting Japanese text to phoneme IDs..."
    print_info "This will take approximately $(estimate_time phonemize)"

    uv run python scripts/phonemize_japanese.py \
        --input dataset/prepared/metadata.csv \
        --output dataset/prepared/metadata_phonemes.csv \
        --phoneme-map dataset/prepared/phoneme_map.json

    if [ $? -eq 0 ]; then
        print_success "Corpus phonemized successfully"
    else
        print_error "Phonemization failed"
        exit 1
    fi
fi

# Step 4: Preprocess for Piper
print_header "Step 4/7: Preprocess for Piper Training ($(estimate_time preprocess))"

if [ -d "training" ]; then
    print_warning "Training directory already exists"
    read -p "Overwrite? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Removing existing training data..."
        rm -rf training
    else
        print_info "Skipping preprocessing"
        if [ ! -f "training/dataset.jsonl" ] || [ ! -f "training/config.json" ]; then
            print_error "Required files not found in training directory"
            exit 1
        fi
        print_success "Using existing preprocessed data"
        SKIP_PREPROCESS=true
    fi
fi

if [[ $SKIP_PREPROCESS != true ]]; then
    print_info "Creating Piper training files..."
    print_info "This will take approximately $(estimate_time preprocess)"

    uv run python scripts/preprocess_piper.py \
        --input-metadata dataset/prepared/metadata_phonemes.csv \
        --phoneme-map dataset/prepared/phoneme_map.json \
        --audio-dir dataset/prepared/wav \
        --output-dir training \
        --sample-rate $SAMPLE_RATE

    if [ $? -eq 0 ]; then
        print_success "Dataset preprocessed successfully"
    else
        print_error "Preprocessing failed"
        exit 1
    fi
fi

# Step 5: Download base checkpoint (optional)
print_header "Step 5/7: Base Checkpoint (Optional)"

mkdir -p checkpoints

if [ -f "checkpoints/base_model.ckpt" ]; then
    print_success "Base checkpoint already exists"
    print_info "Training will use transfer learning (10-50x faster)"
else
    print_warning "No base checkpoint found"
    print_info "Transfer learning uses a pre-trained checkpoint to accelerate training"
    print_info "Without it, training will be 10-50x slower (from scratch)"
    echo ""
    read -p "Download base checkpoint? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Please manually download a base checkpoint from:"
        print_info "  https://github.com/rhasspy/piper/releases"
        print_info ""
        print_info "Or provide a URL to download:"
        read -p "Checkpoint URL (or press Enter to skip): " CHECKPOINT_URL

        if [[ ! -z $CHECKPOINT_URL ]]; then
            print_info "Downloading checkpoint..."
            wget "$CHECKPOINT_URL" -O checkpoints/base_model.ckpt

            if [ $? -eq 0 ]; then
                print_success "Checkpoint downloaded"
            else
                print_warning "Download failed, training will start from scratch"
                rm -f checkpoints/base_model.ckpt
            fi
        else
            print_info "Skipping checkpoint download"
            print_warning "Training will start from scratch (much slower)"
        fi
    else
        print_info "Training will start from scratch"
    fi
fi

# Step 6: Train voice model
print_header "Step 6/7: Train Voice Model ($(estimate_time train $TRAINING_MODE))"

print_info "Training configuration:"
if [[ $TRAINING_MODE == "fast" ]]; then
    echo "  - Mode: Fast Experiment (100 epochs)"
    echo "  - Purpose: Quick testing"
    TRAIN_ARGS="--fast-experiment"
else
    echo "  - Mode: High Quality (5000 epochs)"
    echo "  - Purpose: Production model"
    TRAIN_ARGS="--high-quality"
fi
echo ""

print_warning "Training can take a long time!"
print_info "Estimated duration: $(estimate_time train $TRAINING_MODE)"
echo ""
print_info "You can:"
print_info "  - Monitor progress in real-time (logs will be displayed)"
print_info "  - Interrupt with Ctrl+C (can be resumed later)"
print_info "  - Monitor with TensorBoard: tensorboard --logdir lightning_logs"
echo ""

read -p "Start training now? [Y/n] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]] && [[ ! -z $REPLY ]]; then
    print_info "Training skipped"
    print_info "You can start training manually with:"
    echo "  uv run python scripts/train_voice.py \\"
    echo "    --dataset-dir training \\"
    echo "    --output-dir output \\"
    echo "    --checkpoint-dir checkpoints \\"
    echo "    $TRAIN_ARGS"
    exit 0
fi

print_info "Starting training..."
print_info "This may take $(estimate_time train $TRAINING_MODE)"
print_info "Press Ctrl+C to interrupt (training can be resumed)"
echo ""

uv run python scripts/train_voice.py \
    --dataset-dir training \
    --output-dir output \
    --checkpoint-dir checkpoints \
    $TRAIN_ARGS

if [ $? -eq 0 ]; then
    print_success "Training completed successfully!"
else
    print_error "Training failed or was interrupted"
    print_info "You can resume training by running the same command again"
    exit 1
fi

# Step 7: Export to ONNX
print_header "Step 7/7: Export Model to ONNX ($(estimate_time export))"

print_info "Finding best checkpoint..."
LATEST_CHECKPOINT=$(ls -t checkpoints/epoch-*.ckpt 2>/dev/null | head -1)

if [ -z "$LATEST_CHECKPOINT" ]; then
    print_error "No checkpoint found in checkpoints/"
    print_info "Please check that training completed successfully"
    exit 1
fi

print_info "Using checkpoint: $LATEST_CHECKPOINT"

mkdir -p models

print_info "Exporting to ONNX format..."
uv run python -m piper_train.export_onnx \
    "$LATEST_CHECKPOINT" \
    models/voice_ja_jsut.onnx

if [ $? -ne 0 ]; then
    print_error "ONNX export failed"
    exit 1
fi

print_info "Copying configuration..."
cp training/config.json models/voice_ja_jsut.onnx.json

print_success "Model exported successfully!"

# Step 8: Test the voice
print_header "🎉 Voice Model Ready!"

print_success "Model created: models/voice_ja_jsut.onnx"
echo ""

print_info "Testing the voice model..."

echo "こんにちは、これは私のカスタム音声です。" | \
    piper --model models/voice_ja_jsut.onnx \
         --output_file test_voice_output.wav

if [ $? -eq 0 ]; then
    print_success "Test synthesis successful!"
    print_info "Output saved to: test_voice_output.wav"
    echo ""

    print_info "Playing audio..."
    if command -v afplay &> /dev/null; then
        afplay test_voice_output.wav
    elif command -v aplay &> /dev/null; then
        aplay test_voice_output.wav
    else
        print_warning "Audio player not found (afplay/aplay)"
        print_info "Please play test_voice_output.wav manually"
    fi
else
    print_warning "Test synthesis failed"
    print_info "Please check that piper is installed correctly"
fi

# Summary
print_header "📊 Summary"

echo "Voice model created successfully!"
echo ""
echo "Model location:"
echo "  - ONNX model: models/voice_ja_jsut.onnx"
echo "  - Config file: models/voice_ja_jsut.onnx.json"
echo ""
echo "Usage:"
echo "  echo 'あなたのテキストをここに入力' | \\"
echo "    piper --model models/voice_ja_jsut.onnx \\"
echo "         --output_file output.wav"
echo ""
echo "Training artifacts:"
echo "  - Dataset: dataset/prepared/"
echo "  - Training data: training/"
echo "  - Checkpoints: checkpoints/"
echo "  - Logs: lightning_logs/"
echo ""

if [[ $TRAINING_MODE == "fast" ]]; then
    print_warning "Fast experiment mode was used (100 epochs)"
    print_info "For better quality, retrain with:"
    echo "  uv run python scripts/train_voice.py \\"
    echo "    --dataset-dir training \\"
    echo "    --output-dir output \\"
    echo "    --checkpoint-dir checkpoints \\"
    echo "    --high-quality"
    echo ""
fi

print_success "🎌 Japanese voice creation complete!"
