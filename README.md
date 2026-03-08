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

## 🚀 Quick Start (One Command)

```bash
# Clone and setup
git clone https://github.com/kobe1980/jpa_voice_piper.git
cd jpa_voice_piper

# Install dependencies
./scripts/bootstrap.sh

# Create Japanese voice model (one command!)
./scripts/create_japanese_voice.sh
```

This will:
1. ✅ Download JSUT corpus (~10 min)
2. ✅ Prepare dataset (~30-60 min)
3. ✅ Phonemize corpus (~3-5 min)
4. ✅ Preprocess for Piper (~5-10 min)
5. ✅ Train voice model (~30 min to 2 days depending on hardware)
6. ✅ Export to ONNX (~1 min)
7. ✅ Test your voice!

**Total time:** ~2-3 hours (fast experiment with GPU)

## 📖 Documentation

- **[JSUT Quickstart Guide](docs/JSUT_QUICKSTART.md)** - Step-by-step manual workflow
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
