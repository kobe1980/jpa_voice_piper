# Product Documentation: Piper Voice Dataset Creation Project

**Last Updated:** 2026-03-08
**Version:** 0.1.0 (Foundation Phase)
**Status:** Initial Foundation Implemented

---

## Overview

The Piper Voice Dataset Creation Project is a system for creating high-quality French voice datasets compatible with Piper TTS (Text-to-Speech). The project follows the official Piper training procedures and is designed to produce datasets that can be contributed back to the open source community.

## Product Vision

Create a professional-grade French voice dataset through:
- Automated audio quality validation
- Phonetic verification
- Standardized dataset preparation
- Complete training pipeline automation

The end goal is a trained French voice model that anyone can use with Piper TTS, accompanied by complete documentation demonstrating best practices for voice dataset creation.

---

## Current Capabilities (REAL)

### Domain Layer - Business Logic (REAL)

The following core business logic is **fully implemented, tested, and functional**:

#### 1. Audio Sample Management
- **AudioSample Entity**: Represents a single audio recording with metadata
  - File path tracking
  - Sample rate validation
  - Duration tracking
  - Format specification (WAV 16-bit PCM only)
  - Quality metrics integration
  - Validation status checking
- **Status**: REAL - 100% test coverage, all tests passing

#### 2. Voice Management
- **Voice Entity** (Aggregate Root): Represents a complete voice model
  - Voice identification and naming
  - Language specification
  - Sample rate consistency enforcement (all samples must match voice sample rate)
  - Sample collection management
  - Duration calculation (total audio time)
  - Quality metrics (count of valid vs invalid samples)
- **Status**: REAL - 100% test coverage, all tests passing

#### 3. Transcript Management
- **Transcript Entity**: Represents text transcriptions with phoneme data
  - Text storage and validation (rejects empty text)
  - Phoneme ID sequences (required for TTS)
  - Language specification
  - Text normalization (whitespace cleanup)
- **Status**: REAL - 100% test coverage, all tests passing

#### 4. Phoneme Representation
- **Phoneme Entity**: Represents phonetic units
  - Symbol-based identification
  - Language-specific phonemes
  - Phoneme ID mapping
  - Hashable for use in sets/dictionaries
- **Status**: REAL - 100% test coverage, all tests passing

#### 5. Quality Standards (Value Objects)
- **SampleRate**: Enforces valid sample rates (16000 Hz or 22050 Hz only)
- **Duration**: Enforces valid duration bounds (1-15 seconds)
- **AudioFormat**: Enforces WAV 16-bit PCM format requirement
- **AudioQuality**: Audio quality metrics with validation
  - Signal-to-Noise Ratio (SNR) validation (minimum 30 dB)
  - Clipping detection (peak amplitude < 0.95)
  - Silence measurement (max 0.3 seconds at start/end)
  - Complete validation with detailed error reporting
- **Status**: REAL - 100% test coverage, all tests passing

#### 6. Architecture Ports (Interfaces)
The system defines clear contracts for infrastructure adapters:
- **AudioProcessorPort**: Audio loading, quality analysis, normalization
- **PhoneticsCheckerPort**: Text-to-phoneme conversion, validation
- **FileSystemPort**: Safe filesystem operations with security boundaries
- **MetadataRepositoryPort**: LJSPEECH format metadata management
- **PiperTrainingPort**: Piper preprocessing, training, ONNX export
- **Status**: REAL - Interfaces defined, ready for implementation

### Development Infrastructure (REAL)

#### 1. Project Setup Tools
- **bootstrap.sh**: Complete project setup script
  - Python version verification (3.11+ required)
  - UV package manager installation
  - espeak-ng availability check
  - Dependency installation
  - Directory structure creation
  - Initial configuration file generation
- **Status**: REAL - Script exists and is executable

#### 2. Testing Infrastructure
- **test.sh**: Complete quality pipeline
  - Code formatting verification (ruff format)
  - Linting (ruff check)
  - Type checking (mypy)
  - Unit and integration tests (pytest with coverage)
  - Optional audio quality validation
  - Optional phonetics validation
- **Status**: REAL - Script exists and is executable

#### 3. Python Package Configuration
- **pyproject.toml**: Complete project configuration
  - Package metadata and versioning
  - Dependency specifications
  - Optional extras (audio, training, dev)
  - Tool configurations (ruff, mypy, pytest, coverage)
  - CLI entrypoint definition
- **Status**: REAL - Configuration file complete and functional

#### 4. Test Suite
- **36 unit tests** covering domain entities and value objects
  - 17 tests for entities (AudioSample, Voice, Transcript, Phoneme)
  - 19 tests for value objects (SampleRate, Duration, AudioFormat, AudioQuality)
  - All tests passing with 100% coverage on tested modules
- **Status**: REAL - Tests exist and pass

---

## Current Limitations (INCOMPLETE/PLANNED)

### Infrastructure Adapters (INCOMPLETE)

The following infrastructure adapters are **defined as interfaces but NOT YET IMPLEMENTED**:

#### 1. Audio Processing Infrastructure
- Audio file loading (librosa/soundfile integration)
- SNR calculation
- Clipping detection
- Silence measurement
- Audio normalization
- **Status**: INCOMPLETE - Port defined, no implementation yet

#### 2. Phonetics Infrastructure
- espeak-ng wrapper
- Text-to-phoneme conversion
- Phoneme map generation
- French phonetic validation
- **Status**: INCOMPLETE - Port defined, no implementation yet

#### 3. Filesystem Infrastructure
- Safe filesystem operations with security guardrails
- Path validation (allowed/forbidden directories)
- Audio file listing
- Directory creation
- **Status**: INCOMPLETE - Port defined, no implementation yet

#### 4. Metadata Infrastructure
- LJSPEECH format metadata.csv reading/writing
- Metadata validation
- **Status**: INCOMPLETE - Port defined, no implementation yet

#### 5. Piper Training Infrastructure
- Piper preprocessing wrapper
- Training coordination
- ONNX export
- **Status**: INCOMPLETE - Port defined, no implementation yet

### Application Layer (PLANNED)

The following use cases are **planned but NOT YET IMPLEMENTED**:

#### 1. Dataset Preparation Use Cases
- Prepare dataset (audio normalization + metadata creation)
- Validate quality (quality validation pipeline)
- Validate phonetics (phonetic validation pipeline)
- Preprocess for Piper (Piper preprocessing orchestration)
- Train voice (training workflow coordination)
- **Status**: PLANNED - No implementation yet

#### 2. CLI Interface
- Command-line interface for dataset operations
- **Status**: PLANNED - Entrypoint defined in pyproject.toml, no implementation

### Scripts and Automation (PLANNED)

The following scripts are **planned but NOT YET IMPLEMENTED**:

- generate_metadata.py (create metadata.csv from recordings)
- validate_quality.py (CLI for quality validation)
- validate_phonetics.py (CLI for phonetics validation)
- prepare_dataset.py (CLI for dataset preparation)
- **Status**: PLANNED - No implementation yet

### Configuration Files (PLANNED)

The following configuration files are **planned but NOT YET CREATED**:

- configs/audio_quality.yaml (quality thresholds)
- configs/phonetics.yaml (phonetic rules)
- configs/training.yaml (training hyperparameters)
- **Status**: PLANNED - No files yet

### Dataset Infrastructure (EMPTY)

The following dataset directories exist but are **empty**:

- dataset/raw/ (for audio recordings)
- dataset/wav/ (for normalized audio)
- training/ (for Piper preprocessing output)
- models/ (for exported ONNX models)
- logs/ (for operation logs)
- checkpoints/ (for training checkpoints)
- **Status**: INCOMPLETE - Directories exist, no content

---

## System Requirements

### Required
- Python 3.11 or higher
- UV package manager (for dependency management)
- espeak-ng 1.51+ (for phonetic validation)
- macOS or Linux operating system

### Recommended for Training
- GPU with CUDA support (for faster training)
- 16GB+ RAM
- 50GB+ free disk space

### Python Dependencies
- numpy >= 1.24.0
- scipy >= 1.10.0
- librosa >= 0.10.0
- soundfile >= 0.12.0
- pydantic >= 2.0.0

---

## Audio Quality Standards

### Format Requirements (Enforced by Domain Layer)
- **Format**: WAV 16-bit PCM only
- **Sample Rate**: 16000 Hz or 22050 Hz
- **Duration**: 1-15 seconds per sample
- **File Size**: Maximum 5 MB per file

### Quality Requirements (Enforced by AudioQuality Value Object)
- **Signal-to-Noise Ratio (SNR)**: Minimum 30 dB
- **Clipping**: Peak amplitude must be below 0.95 (no clipping)
- **Silence**: Maximum 0.3 seconds at start and end
- **Validation**: All samples must pass quality validation

---

## Supported Use Cases

### Currently Supported (REAL)
1. **Domain Modeling**: Create and validate voice, audio sample, transcript, and phoneme entities
2. **Quality Standards Enforcement**: Validate audio quality metrics programmatically
3. **Business Rule Validation**: Enforce sample rate consistency, duration limits, format requirements
4. **Development Setup**: Bootstrap development environment with all dependencies
5. **Quality Assurance**: Run complete test suite with coverage reporting

### Not Yet Supported (INCOMPLETE/PLANNED)
1. Audio file processing and analysis
2. Phonetic validation with espeak-ng
3. Dataset preparation and metadata generation
4. Piper preprocessing and training
5. ONNX model export
6. CLI-based dataset operations
7. Automated quality validation pipelines

---

## Known Limitations

### Architecture Limitations
- **Infrastructure not implemented**: Domain layer is complete, but no infrastructure adapters exist yet
- **No application layer**: Use cases defined but not implemented
- **No CLI functionality**: CLI entrypoint defined but not implemented
- **No scripts**: Utility scripts planned but not created

### Functional Limitations
- **Cannot process audio files**: No audio processing infrastructure
- **Cannot validate phonetics**: No espeak-ng integration
- **Cannot prepare datasets**: No dataset preparation pipeline
- **Cannot train models**: No Piper integration
- **No real dataset**: Empty dataset directories

### Testing Limitations
- **Domain layer only**: Only domain entities and value objects are tested
- **No integration tests**: Integration tests directory exists but empty
- **No validation tests**: Validation tests directory exists but empty
- **No infrastructure tests**: Infrastructure adapters not implemented

---

## Future Capabilities (Roadmap)

### Phase 1: Infrastructure Implementation
- Implement audio processing adapters (librosa/soundfile)
- Implement phonetics adapters (espeak-ng)
- Implement filesystem adapters with security guardrails
- Implement metadata adapters (LJSPEECH format)

### Phase 2: Application Layer
- Implement quality validation use case
- Implement phonetics validation use case
- Implement dataset preparation use case
- Implement Piper preprocessing use case

### Phase 3: User Interface
- Implement CLI interface
- Implement utility scripts
- Create configuration files

### Phase 4: Training Pipeline
- Implement Piper training coordination
- Implement checkpoint management
- Implement ONNX export
- Implement model testing

### Phase 5: Dataset Creation
- Record audio samples
- Generate metadata
- Validate quality and phonetics
- Train initial voice model

---

## Security Model

### Filesystem Security (Designed, Not Yet Implemented)
The system is designed with security guardrails:

**Allowed Paths**:
- ./dataset
- ./scripts
- ./piper_voice
- ./tests
- ./configs
- ./models
- ./logs
- ./checkpoints
- ./training
- ./docs

**Forbidden Paths**:
- $HOME directory
- System root (/)
- SSH keys
- Environment secrets

**Protected Paths**:
- dataset/raw/ is designed to be read-only (permanent backup)

**Note**: These security guardrails are architecturally defined but not yet implemented in code.

---

## Target Users

### Primary Users
1. **Voice Dataset Creators**: People recording audio for TTS training
2. **Developers**: Integrating French TTS into applications
3. **Researchers**: Experimenting with French TTS

### User Needs (Design Goals)
1. High-quality, natural-sounding French voice
2. Free and open source (no licensing costs)
3. Accessible for visually impaired French speakers
4. Suitable for professional applications
5. Documented and reproducible process

---

## Open Source Contribution

### Contribution Goals
- Create a French voice model for the Piper TTS community
- Demonstrate best practices for voice dataset creation
- Provide complete documentation for reproducibility
- Enable others to create similar datasets

### License
MIT License

---

## Development Status Summary

| Component | Status | Coverage | Notes |
|-----------|--------|----------|-------|
| Domain Entities | REAL | 100% | Fully implemented and tested |
| Value Objects | REAL | 100% | Fully implemented and tested |
| Domain Ports | REAL | N/A | Interfaces defined |
| Audio Infrastructure | INCOMPLETE | 0% | Not implemented |
| Phonetics Infrastructure | INCOMPLETE | 0% | Not implemented |
| Filesystem Infrastructure | INCOMPLETE | 0% | Not implemented |
| Metadata Infrastructure | INCOMPLETE | 0% | Not implemented |
| Piper Infrastructure | INCOMPLETE | 0% | Not implemented |
| Application Use Cases | PLANNED | 0% | Not implemented |
| CLI Interface | PLANNED | 0% | Not implemented |
| Utility Scripts | PLANNED | 0% | Not implemented (bootstrap and test scripts exist) |
| Configuration Files | PLANNED | 0% | Not created |
| Dataset Content | EMPTY | N/A | Directories exist, no content |

**Overall Status**: Foundation phase complete. Domain layer is solid and tested. Infrastructure and application layers are next.

---

## Contact and Support

This is a personal project for contributing to the Piper TTS open source community.

For issues or questions, refer to the project documentation in CLAUDE.md and ADR documents in docs/product/decisions/.
