# Japanese Voice for Piper TTS (JSUT Corpus)

High-quality Japanese voice training for Piper TTS using the JSUT corpus, following the official procedure from [rhasspy/piper](https://github.com/rhasspy/piper).

## About

This project creates the **first Japanese voice for Piper TTS** using the JSUT (Japanese Speech Corpus of Saruwatari Lab, University of Tokyo). The trained model will be contributed to the open source community.

**Goal**: Train `ja_JP-jsut-medium.onnx` - a medium-quality Japanese voice model.

## Status

**Phase 1 COMPLETE** ✅: Domain foundation and architecture (15% complete)

- Domain entities (Voice, AudioSample, Transcript, Phoneme)
- Quality validation framework (SNR, clipping, duration checks)
- Port definitions for infrastructure
- 36 unit tests, 100% domain coverage

**Remaining**: Infrastructure, phonetization, training (85% not started)

## Quick Start

```bash
# Bootstrap the environment
./scripts/bootstrap.sh

# Run tests
./scripts/test.sh
```

## Pipeline

**JSUT download → audio normalization → kanji→hiragana → phoneme IDs → Piper preprocessing → training (French checkpoint) → ONNX export**

## Key Technical Decisions

- **Corpus**: JSUT (~7,300 utterances, 10h, single female speaker)
- **Phonetization**: Hiragana-as-phonemes (using pykakasi, no espeak-ng)
- **Training**: Transfer learning from French checkpoint (fr_FR-siwis-medium)
- **Sample Rate**: 22050 Hz
- **Quality**: Medium (MOS target ~3.5)

## Requirements

- Python 3.11+
- UV package manager
- pykakasi (for kanji→hiragana conversion)
- Piper training tools
- macOS or Linux
- GPU/MPS recommended for training

## Documentation

- [STORY-001](docs/product/stories/STORY-001-japanese-voice-jsut.md) - What we're building (Japanese voice with JSUT)
- [ADR-001](docs/product/decisions/ADR-001-japanese-voice-architecture.md) - Technical decisions (hiragana phonetization, transfer learning)
- [CLAUDE.md](CLAUDE.md) - Development workflow and rules
- [Original Plan](docs/plans/active/plan_japanese_voice_training.md) - Detailed 7-phase implementation plan

## Project Structure

```
piper_voice/
├── core/                 # Domain layer (100% complete)
│   ├── entities.py      # Voice, AudioSample, Transcript, Phoneme
│   ├── value_objects.py # SampleRate, Duration, AudioQuality, AudioFormat
│   └── ports.py         # Infrastructure interfaces
│
├── infrastructure/       # Adapters (0% - not started)
│   ├── audio/           # Audio processing (librosa, soundfile)
│   ├── phonetics/       # pykakasi wrapper for hiragana
│   ├── filesystem/      # Safe filesystem with guardrails
│   └── piper/           # Piper training coordination
│
└── application/          # Use cases (0% - not started)
    └── (orchestration logic)

dataset/
├── raw/                 # JSUT corpus (to be downloaded)
└── wav/                 # Normalized audio 22050Hz

training/                # Piper preprocessed data
models/                  # Trained ONNX models
checkpoints/             # Training checkpoints
```

## Roadmap

| Phase | Status | Description |
|-------|--------|-------------|
| 1. Foundation | ✅ COMPLETE | Domain entities, quality framework |
| 2. JSUT Infrastructure | 🔴 TODO | Download, normalize JSUT corpus |
| 3. Phonetization | 🔴 TODO | pykakasi integration, hiragana→IDs |
| 4. Training Prep | 🔴 TODO | Piper preprocessing, config |
| 5. Training | 🔴 TODO | Transfer learning from French |
| 6. Export | 🔴 TODO | ONNX export, testing |

**Timeline**: 3-4 weeks total (1 week complete)

## Why This Matters

- **First Japanese voice** in Piper TTS ecosystem
- **Open source** and freely usable
- **Documented process** for future Japanese voices
- **Foundation** for Japanese TTS accessibility and applications

## License

MIT (code) + CC BY-SA 4.0 (trained model - matching JSUT corpus license)

## Contributing

This project follows strict TDD and DDD principles. See [CLAUDE.md](CLAUDE.md) for development workflow.
