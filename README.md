# 🎌 Piper Voice - Japanese TTS Dataset Creation

> **Create high-quality Japanese TTS voice models for Piper using the JSUT corpus**

This project provides a complete pipeline to create Japanese Text-to-Speech voice models compatible with [Piper TTS](https://github.com/rhasspy/piper), using Domain-Driven Design (DDD) architecture and Test-Driven Development (TDD).

## ✨ Features

- 🎯 **One-Command Pipeline**: Automated A-Z workflow from dataset to voice model
- 📦 **JSUT Corpus Support**: Use free, professional-quality Japanese speech corpus (~7,300 utterances)
- 🧠 **Custom Phonemization**: Hiragana-as-phonemes strategy bypassing espeak-ng (~100 phonemes)
- 🚀 **Transfer Learning**: 10-50x faster training with base checkpoints
- 🔧 **Hardware Auto-Detection**: GPU/MPS/CPU with optimized configurations
- 📊 **Quality Validation**: Automatic audio quality checks (SNR, clipping, silence)
- 🏗️ **Clean Architecture**: DDD + TDD + Hexagonal Architecture
- 🧪 **266 Tests**: 76% coverage, all quality gates passing

## 🚀 Quick Start

### Windows (Recommended for GPU Training)

```powershell
# Clone repo (includes 4061 audio samples via Git LFS)
git clone https://github.com/kobe1980/jpa_voice_piper.git
cd jpa_voice_piper

# Complete setup (Python, PyTorch GPU, Piper, validation)
setup_windows.bat

# Launch training
train_windows.bat
```

**That's it!** Dataset (5.4 GB) is included via Git LFS.

**Duration:** 6-12 hours on GPU (RTX 3060+) with transfer learning

📖 **See [WINDOWS_QUICKSTART.md](WINDOWS_QUICKSTART.md) for detailed guide**

### macOS / Linux

```bash
# Clone and setup
git clone https://github.com/kobe1980/jpa_voice_piper.git
cd jpa_voice_piper

# Install dependencies
./scripts/bootstrap.sh  # or: uv sync --all-extras

# Launch training
python scripts/train_japanese_voice.py
```

**Duration:** 12-24 hours on Apple Silicon MPS with transfer learning

## 📖 Documentation

### Quick Start Guides
- **[WINDOWS_QUICKSTART.md](WINDOWS_QUICKSTART.md)** - Windows GPU training (recommended)
- **[JSUT Quickstart Guide](docs/JSUT_QUICKSTART.md)** - Manual dataset preparation

### Training & Architecture
- **[TRAINING_ON_WINDOWS_GPU.md](TRAINING_ON_WINDOWS_GPU.md)** - Complete Windows setup guide
- **[TRAINING_FAILURE_REPORT.md](TRAINING_FAILURE_REPORT.md)** - Training diagnostics & solutions
- **[SUMMARY_AND_NEXT_STEPS.md](SUMMARY_AND_NEXT_STEPS.md)** - Action plan & recommendations
- **[CLAUDE.md](CLAUDE.md)** - Architecture, TDD rules, DDD principles

## 🎯 Usage

```bash
# Fast experiment (100 epochs, ~2-3 hours with GPU)
./scripts/create_japanese_voice.sh --fast

# High quality (5000 epochs, ~1-2 days with GPU)
./scripts/create_japanese_voice.sh --high-quality

# Skip download if JSUT already exists
./scripts/create_japanese_voice.sh --skip-download --fast
```

See [JSUT_QUICKSTART.md](docs/JSUT_QUICKSTART.md) for manual step-by-step workflow.

---

**Made with ❤️ for the Japanese TTS community**

🤖 Generated with [Claude Code](https://claude.com/claude-code)
