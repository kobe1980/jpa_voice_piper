#!/usr/bin/env bash
# Training script for Japanese voice (Piper TTS)
# Compatible with: macOS (MPS), Linux/Windows (CUDA), CPU
#
# Usage:
#   ./scripts/train_japanese_voice.sh [--accelerator gpu|mps|cpu] [--from-scratch]
#
# Requirements:
#   - Dataset prepared in dataset/prepared/
#   - piper-training installed (pip install piper-tts[training])
#   - For transfer learning: French checkpoint downloaded

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Dataset paths
DATASET_CSV="dataset/prepared/metadata_phonemes.csv"
AUDIO_DIR="dataset/prepared/wav"
CACHE_DIR="training"
CONFIG_PATH="training/config.json"

# Training parameters
VOICE_NAME="ja_JP-jsut-medium"
SAMPLE_RATE=22050
PHONEME_TYPE="text"  # Use hiragana-as-phonemes

# Hyperparameters (optimized for convergence)
BATCH_SIZE=32
LEARNING_RATE=0.00005  # Lower for fine-tuning
MAX_EPOCHS=200
VALIDATION_SPLIT=0.1
CHECK_VAL_EVERY_N_EPOCH=5

# Transfer learning checkpoint
CHECKPOINT_URL="https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR-siwis-medium/fr_FR-siwis-medium.ckpt"
CHECKPOINT_FILE="checkpoints/fr_FR-siwis-medium.ckpt"

# ============================================================================
# Parse arguments
# ============================================================================

ACCELERATOR="auto"
FROM_SCRATCH=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --accelerator)
            ACCELERATOR="$2"
            shift 2
            ;;
        --from-scratch)
            FROM_SCRATCH=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --accelerator <gpu|mps|cpu>  Hardware accelerator (default: auto-detect)"
            echo "  --from-scratch               Train from scratch (no transfer learning)"
            echo "  --help                       Show this help message"
            echo ""
            echo "Examples:"
            echo "  # Auto-detect GPU/MPS/CPU"
            echo "  $0"
            echo ""
            echo "  # Force CUDA GPU"
            echo "  $0 --accelerator gpu"
            echo ""
            echo "  # Force Apple Silicon MPS"
            echo "  $0 --accelerator mps"
            echo ""
            echo "  # Train from scratch (no transfer learning)"
            echo "  $0 --from-scratch"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Run '$0 --help' for usage information"
            exit 1
            ;;
    esac
done

# ============================================================================
# Auto-detect accelerator if not specified
# ============================================================================

if [[ "$ACCELERATOR" == "auto" ]]; then
    echo "🔍 Auto-detecting hardware accelerator..."

    if command -v nvidia-smi &> /dev/null && nvidia-smi &> /dev/null; then
        ACCELERATOR="gpu"
        echo "✅ Detected NVIDIA GPU (CUDA)"
    elif [[ "$(uname)" == "Darwin" ]] && [[ "$(uname -m)" == "arm64" ]]; then
        ACCELERATOR="mps"
        echo "✅ Detected Apple Silicon (MPS)"
    else
        ACCELERATOR="cpu"
        echo "⚠️  No GPU detected, using CPU (slow!)"
    fi
fi

# ============================================================================
# Platform-specific configuration
# ============================================================================

NUM_WORKERS=4  # Default for GPU/CPU

if [[ "$ACCELERATOR" == "mps" ]]; then
    # Apple Silicon: disable multiprocessing to prevent semaphore leaks
    NUM_WORKERS=0
    echo "🍎 Apple Silicon detected: disabling dataloader workers"
fi

if [[ "$ACCELERATOR" == "cpu" ]]; then
    echo "⚠️  WARNING: CPU training is VERY SLOW (days to weeks)"
    echo "Consider using a GPU instance (AWS, Google Colab, etc.)"
fi

# ============================================================================
# Validate dataset
# ============================================================================

echo ""
echo "============================================================================"
echo "🔍 Validating dataset"
echo "============================================================================"

if [[ ! -f "$DATASET_CSV" ]]; then
    echo "❌ ERROR: Dataset CSV not found: $DATASET_CSV"
    echo ""
    echo "Please prepare the dataset first:"
    echo "  python scripts/prepare_jsut_dataset.py \\"
    echo "    --jsut-dir dataset/jsut/basic5000 \\"
    echo "    --output-dir dataset/prepared \\"
    echo "    --sample-rate 22050"
    echo ""
    echo "Then phonemize:"
    echo "  python scripts/phonemize_japanese.py \\"
    echo "    --input dataset/prepared/metadata.csv \\"
    echo "    --output dataset/prepared/metadata_phonemes.csv \\"
    echo "    --phoneme-map dataset/prepared/phoneme_map.json"
    exit 1
fi

if [[ ! -d "$AUDIO_DIR" ]]; then
    echo "❌ ERROR: Audio directory not found: $AUDIO_DIR"
    exit 1
fi

SAMPLE_COUNT=$(wc -l < "$DATASET_CSV" | tr -d ' ')
echo "✅ Dataset validated: $SAMPLE_COUNT samples"

if [[ $SAMPLE_COUNT -lt 100 ]]; then
    echo "⚠️  WARNING: Dataset has only $SAMPLE_COUNT samples (recommend > 1000)"
fi

# ============================================================================
# Download transfer learning checkpoint (if needed)
# ============================================================================

if [[ "$FROM_SCRATCH" == false ]]; then
    echo ""
    echo "============================================================================"
    echo "📥 Transfer Learning Setup"
    echo "============================================================================"

    mkdir -p checkpoints

    if [[ -f "$CHECKPOINT_FILE" ]]; then
        echo "✅ Checkpoint already downloaded: $CHECKPOINT_FILE"
    else
        echo "📥 Downloading French checkpoint for transfer learning..."
        echo "URL: $CHECKPOINT_URL"

        if command -v wget &> /dev/null; then
            wget -O "$CHECKPOINT_FILE" "$CHECKPOINT_URL"
        elif command -v curl &> /dev/null; then
            curl -L -o "$CHECKPOINT_FILE" "$CHECKPOINT_URL"
        else
            echo "❌ ERROR: Neither wget nor curl found"
            echo "Please download manually:"
            echo "  $CHECKPOINT_URL"
            echo "Save to: $CHECKPOINT_FILE"
            exit 1
        fi

        echo "✅ Checkpoint downloaded"
    fi

    CHECKPOINT_SIZE=$(du -h "$CHECKPOINT_FILE" | cut -f1)
    echo "Checkpoint size: $CHECKPOINT_SIZE"
else
    echo ""
    echo "============================================================================"
    echo "🏗️  Training from Scratch"
    echo "============================================================================"
    echo "⚠️  WARNING: Training from scratch will take MUCH longer"
    echo "Estimated time:"
    echo "  - GPU (CUDA):   24-48 hours"
    echo "  - Apple Silicon: 48-96 hours"
    echo "  - CPU:          7-14 days (!)"

    # Adjust hyperparameters for from-scratch training
    MAX_EPOCHS=500
    LEARNING_RATE=0.0001
fi

# ============================================================================
# Print training configuration
# ============================================================================

echo ""
echo "============================================================================"
echo "🚀 Training Configuration"
echo "============================================================================"
echo "Hardware:"
echo "  Accelerator:       $ACCELERATOR"
echo "  Dataloader workers: $NUM_WORKERS"
echo ""
echo "Dataset:"
echo "  CSV file:          $DATASET_CSV"
echo "  Audio directory:   $AUDIO_DIR"
echo "  Sample count:      $SAMPLE_COUNT"
echo "  Sample rate:       $SAMPLE_RATE Hz"
echo "  Phoneme type:      $PHONEME_TYPE (hiragana-as-phonemes)"
echo ""
echo "Hyperparameters:"
echo "  Batch size:        $BATCH_SIZE"
echo "  Learning rate:     $LEARNING_RATE"
echo "  Max epochs:        $MAX_EPOCHS"
echo "  Validation split:  $VALIDATION_SPLIT"
echo ""
echo "Transfer learning:"
if [[ "$FROM_SCRATCH" == false ]]; then
    echo "  Enabled:           YES"
    echo "  Checkpoint:        $CHECKPOINT_FILE"
else
    echo "  Enabled:           NO (training from scratch)"
fi
echo "============================================================================"
echo ""

# ============================================================================
# Confirm before starting
# ============================================================================

echo "⏰ Estimated training time:"
if [[ "$FROM_SCRATCH" == false ]]; then
    case $ACCELERATOR in
        gpu)
            echo "   GPU (CUDA):   6-12 hours"
            ;;
        mps)
            echo "   Apple Silicon: 12-24 hours"
            ;;
        cpu)
            echo "   CPU:          3-7 days (!)"
            ;;
    esac
else
    case $ACCELERATOR in
        gpu)
            echo "   GPU (CUDA):   24-48 hours"
            ;;
        mps)
            echo "   Apple Silicon: 48-96 hours"
            ;;
        cpu)
            echo "   CPU:          7-14 days (!)"
            ;;
    esac
fi

echo ""
read -p "Press ENTER to start training, or Ctrl+C to cancel..."

# ============================================================================
# Build training command
# ============================================================================

TRAIN_CMD=(
    python -m piper.train
    fit
    --data.voice_name "$VOICE_NAME"
    --data.csv_path "$DATASET_CSV"
    --data.audio_dir "$AUDIO_DIR"
    --data.cache_dir "$CACHE_DIR"
    --data.config_path "$CONFIG_PATH"
    --data.batch_size "$BATCH_SIZE"
    --data.validation_split "$VALIDATION_SPLIT"
    --data.num_workers "$NUM_WORKERS"
    --data.phoneme_type "$PHONEME_TYPE"
    --data.espeak_voice "ja"
    --model.sample_rate "$SAMPLE_RATE"
    --model.learning_rate "$LEARNING_RATE"
    --trainer.max_epochs "$MAX_EPOCHS"
    --trainer.check_val_every_n_epoch "$CHECK_VAL_EVERY_N_EPOCH"
    --trainer.accelerator "$ACCELERATOR"
    --trainer.precision 32
)

# Add checkpoint for transfer learning
if [[ "$FROM_SCRATCH" == false ]]; then
    TRAIN_CMD+=(--ckpt_path "$CHECKPOINT_FILE")
fi

# ============================================================================
# Launch training
# ============================================================================

echo ""
echo "============================================================================"
echo "🚀 Starting Training"
echo "============================================================================"
echo ""
echo "Command:"
echo "${TRAIN_CMD[@]}"
echo ""
echo "📊 Monitor progress:"
echo "  tensorboard --logdir ./lightning_logs --port 6006"
echo ""
echo "🔍 Watch logs:"
echo "  tail -f lightning_logs/version_*/config.yaml"
echo ""
echo "============================================================================"
echo ""

# Execute training
"${TRAIN_CMD[@]}"

EXIT_CODE=$?

# ============================================================================
# Post-training report
# ============================================================================

echo ""
echo "============================================================================"

if [[ $EXIT_CODE -eq 0 ]]; then
    echo "✅ Training completed successfully!"
    echo "============================================================================"
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. Find best checkpoint:"
    echo "   ls -lh lightning_logs/version_*/checkpoints/*.ckpt"
    echo ""
    echo "2. Export to ONNX:"
    echo "   python -m piper.train.export_onnx \\"
    echo "     lightning_logs/version_X/checkpoints/epoch=Y-step=Z.ckpt \\"
    echo "     models/ja_JP-jsut-medium.onnx"
    echo ""
    echo "3. Test synthesis:"
    echo "   echo 'こんにちは' | piper -m models/ja_JP-jsut-medium.onnx"
    echo ""
else
    echo "❌ Training failed with exit code: $EXIT_CODE"
    echo "============================================================================"
    echo ""
    echo "Check logs:"
    echo "  cat lightning_logs/version_*/config.yaml"
    echo "  tensorboard --logdir ./lightning_logs"
    echo ""
fi

exit $EXIT_CODE
