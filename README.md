# Piper Voice Dataset Creation Project

High-quality French voice dataset creation for Piper TTS, following the official procedure from [rhasspy/piper](https://github.com/rhasspy/piper).

## About

This project aims to create a professional-grade French voice dataset that can be contributed back to the open source community. It follows strict quality standards and the complete Piper training pipeline.

## Quick Start

```bash
# Bootstrap the environment
./scripts/bootstrap.sh

# Run tests
./scripts/test.sh
```

## Pipeline

**audio preparation → quality validation → transcription → phonetic verification → Piper preprocessing → training → ONNX export**

## Requirements

- Python 3.11+
- UV package manager
- espeak-ng (for phonetic validation)
- macOS or Linux

## Documentation

- [CLAUDE.md](CLAUDE.md) - Project rules and workflow
- [docs/product/stories/](docs/product/stories/) - User stories
- [docs/product/decisions/](docs/product/decisions/) - Architecture decisions

## License

MIT
