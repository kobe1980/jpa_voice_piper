# User Guide: Piper Voice Dataset Creation Project

**Last Updated:** 2026-03-08
**Version:** 0.1.0

---

## Introduction

This guide documents how to use the Piper Voice Dataset Creation Project **in its current state**.

**IMPORTANT**: The project is in the foundation phase. Only the core domain logic is implemented. Most user-facing functionality (audio processing, dataset preparation, training) is not yet available.

---

## What You Can Do NOW (Available Functionality)

### 1. Set Up the Development Environment

#### Prerequisites
Ensure you have:
- Python 3.11 or higher
- Git
- macOS or Linux

#### Installation Steps

```bash
# Clone the repository
cd /path/to/project

# Run bootstrap script to set up environment
./scripts/bootstrap.sh
```

**What the bootstrap script does:**
- Verifies Python version (3.11+ required)
- Installs UV package manager if not present
- Checks for espeak-ng availability
- Installs all Python dependencies
- Creates necessary directory structure
- Runs initial test suite

**Expected output:**
```
=== Piper Voice Dataset Project Bootstrap ===
Checking Python version...
✓ Python 3.14.3
✓ UV installed
✓ espeak-ng available
Installing dependencies...
✓ Dependencies installed
Creating directory structure...
✓ Directories created
Running test suite...
✓ All tests passed

=== Bootstrap Complete ===
```

### 2. Verify Installation

Run the test suite to verify everything is working:

```bash
./scripts/test.sh
```

**What this tests:**
- Code formatting (ruff)
- Linting (ruff check)
- Type checking (mypy)
- All unit tests (pytest)

**Expected output:**
```
=== Running Quality Pipeline ===
1. Code formatting...
✓ All files formatted correctly
2. Linting...
✓ No linting issues
3. Type checking...
✓ No type errors
4. Unit + Integration tests...
============================= test session starts ==============================
collected 36 items

tests/unit/test_entities.py .................                            [ 47%]
tests/unit/test_value_objects.py ...................                     [100%]

============================== 36 passed in 0.06s ==============================
=== All Checks Passed ===
```

### 3. Use Domain Entities in Python Code

You can import and use the domain entities programmatically:

```python
from pathlib import Path
from piper_voice.core.entities import Voice, AudioSample, Transcript, Phoneme
from piper_voice.core.value_objects import (
    SampleRate, Duration, AudioFormat, AudioQuality
)

# Create a voice entity
voice = Voice(
    id="fr_FR-custom-medium",
    name="French Custom Voice",
    language="fr",
    sample_rate=SampleRate(22050),
    quality_level="medium"
)

# Create an audio sample entity
sample = AudioSample(
    id="sample_001",
    file_path=Path("dataset/raw/sample_001.wav"),
    sample_rate=SampleRate(22050),
    duration=Duration(5.0),
    format=AudioFormat(type="WAV", encoding="PCM_16"),
    quality=AudioQuality(
        snr_db=35.0,
        max_amplitude=0.85,
        has_clipping=False,
        silence_at_start_sec=0.1,
        silence_at_end_sec=0.1,
    )
)

# Add sample to voice (enforces sample rate consistency)
voice.add_sample(sample)

# Check if sample is valid
if sample.is_valid():
    print("Sample meets quality standards")

# Get voice statistics
print(f"Total duration: {voice.total_duration_seconds()}s")
print(f"Valid samples: {voice.valid_sample_count()}")
print(f"Invalid samples: {voice.invalid_sample_count()}")
```

### 4. Validate Quality Metrics

You can programmatically validate audio quality metrics:

```python
from piper_voice.core.value_objects import AudioQuality

# Create quality metrics
quality = AudioQuality(
    snr_db=28.0,  # Below threshold
    max_amplitude=0.97,  # Too high (clipping)
    has_clipping=True,
    silence_at_start_sec=0.5,  # Too much silence
    silence_at_end_sec=0.2,
)

# Validate
is_valid, errors = quality.validate()

if not is_valid:
    print("Quality validation failed:")
    for error in errors:
        print(f"  - {error}")
```

**Expected output:**
```
Quality validation failed:
  - SNR 28.0 dB is below minimum 30 dB
  - Clipping detected (max amplitude: 0.970)
  - Excessive silence at start: 0.50s (max 0.3s)
```

### 5. Work with Transcripts

```python
from piper_voice.core.entities import Transcript

# Create a transcript
transcript = Transcript(
    id="trans_001",
    text="  Bonjour,   comment   allez-vous?  ",
    phoneme_ids=[1, 2, 3, 4, 5],
    language="fr"
)

# Get normalized text (cleaned whitespace)
print(transcript.normalized_text())
# Output: "Bonjour, comment allez-vous?"

# Transcripts reject empty text
try:
    invalid = Transcript(id="t", text="", phoneme_ids=[1], language="fr")
except ValueError as e:
    print(f"Error: {e}")
    # Output: "Error: Text cannot be empty"
```

### 6. Run Tests

Run the test suite to understand how the system works:

```bash
# Run all tests
uv run pytest tests/ -v

# Run only entity tests
uv run pytest tests/unit/test_entities.py -v

# Run only value object tests
uv run pytest tests/unit/test_value_objects.py -v

# Run with coverage report
uv run pytest tests/ --cov=piper_voice --cov-report=term-missing
```

---

## What You CANNOT Do Yet (Not Implemented)

### Audio Processing (NOT AVAILABLE)
The following operations are **not yet implemented**:

❌ Load WAV files
❌ Calculate SNR from audio data
❌ Detect clipping in audio files
❌ Measure silence duration
❌ Normalize audio volume
❌ Resample audio to target sample rate

**Workaround**: None. These features must be implemented before audio processing is possible.

### Phonetics Validation (NOT AVAILABLE)
The following operations are **not yet implemented**:

❌ Validate French text with espeak-ng
❌ Convert text to phoneme IDs
❌ Get phoneme mappings for French
❌ Verify pronunciation correctness

**Workaround**: None. espeak-ng integration must be implemented first.

### Dataset Preparation (NOT AVAILABLE)
The following operations are **not yet implemented**:

❌ Generate metadata.csv from recordings
❌ Validate metadata format (LJSPEECH)
❌ Normalize audio files for Piper
❌ Create dataset structure

**Workaround**: None. Dataset preparation pipeline must be implemented first.

### Piper Training (NOT AVAILABLE)
The following operations are **not yet implemented**:

❌ Run Piper preprocessing
❌ Train voice model
❌ Export to ONNX format
❌ Test synthesis

**Workaround**: None. Piper integration must be implemented first.

### CLI Interface (NOT AVAILABLE)
The following CLI commands are **not yet implemented**:

❌ `piper-voice validate-quality --dataset ./dataset`
❌ `piper-voice validate-phonetics --metadata ./dataset/metadata.csv`
❌ `piper-voice prepare-dataset --input ./dataset/raw --output ./dataset/wav`
❌ `piper-voice preprocess --dataset ./dataset --output ./training`

**Workaround**: None. CLI implementation must be completed first.

---

## Directory Structure

After running `bootstrap.sh`, you will have the following structure:

```
jpa_voice_piper/
├── piper_voice/              # Python package
│   ├── core/                 # Domain layer (IMPLEMENTED)
│   │   ├── entities.py      # Voice, AudioSample, Transcript, Phoneme
│   │   ├── value_objects.py # SampleRate, Duration, AudioFormat, AudioQuality
│   │   └── ports.py         # Interface definitions
│   ├── application/          # Use cases (EMPTY - not implemented)
│   └── infrastructure/       # Adapters (EMPTY - not implemented)
│
├── dataset/                  # Dataset workspace (EMPTY)
│   ├── raw/                  # For source audio recordings
│   └── wav/                  # For normalized audio
│
├── training/                 # Piper preprocessing output (EMPTY)
├── models/                   # ONNX models (EMPTY)
├── logs/                     # Operation logs (EMPTY)
├── checkpoints/              # Training checkpoints (EMPTY)
│
├── scripts/                  # Automation scripts
│   ├── bootstrap.sh          # Project setup (WORKING)
│   └── test.sh               # Quality pipeline (WORKING)
│
├── tests/                    # Test suite
│   ├── unit/                 # Unit tests (36 tests PASSING)
│   ├── integration/          # Integration tests (EMPTY)
│   └── validation/           # Validation tests (EMPTY)
│
├── configs/                  # Configuration files (EMPTY)
├── docs/                     # Documentation
│   ├── product/              # Product documentation
│   │   ├── stories/          # User stories
│   │   └── decisions/        # Architecture decisions (ADR)
│   ├── plans/                # Development plans
│   ├── PRODUCT.md            # This document
│   └── USER_GUIDE.md         # User guide
│
├── pyproject.toml            # Project configuration (COMPLETE)
├── CLAUDE.md                 # Project rules (COMPLETE)
└── README.md                 # Project overview (COMPLETE)
```

---

## Development Workflow

### For Developers Contributing to This Project

1. **Set up environment**:
   ```bash
   ./scripts/bootstrap.sh
   ```

2. **Create a feature branch**:
   ```bash
   git checkout -b feature/my-feature
   ```

3. **Write tests first (TDD)**:
   ```bash
   # Create test file in tests/unit/ or tests/integration/
   # Write failing tests
   uv run pytest tests/ -v
   ```

4. **Implement feature**:
   ```bash
   # Write minimal code to pass tests
   # Run tests again
   uv run pytest tests/ -v
   ```

5. **Run quality checks**:
   ```bash
   ./scripts/test.sh
   ```

6. **Commit changes**:
   ```bash
   git add .
   git commit -m "feat: Add my feature"
   ```

7. **Merge to main** (if all checks pass):
   ```bash
   git checkout main
   git merge feature/my-feature
   ```

---

## Testing

### Run All Tests
```bash
uv run pytest tests/ -v
```

### Run Specific Test File
```bash
uv run pytest tests/unit/test_entities.py -v
```

### Run Tests with Coverage
```bash
uv run pytest tests/ --cov=piper_voice --cov-report=html
# Open htmlcov/index.html in browser to see coverage report
```

### Run Quality Pipeline
```bash
./scripts/test.sh
```

---

## Common Questions

### Q: Can I record audio and create a dataset now?
**A: No.** The audio processing infrastructure is not yet implemented. You can set up the environment and work with domain entities programmatically, but you cannot process actual audio files.

### Q: Can I train a voice model?
**A: No.** The Piper integration is not yet implemented. The training pipeline is planned but not available.

### Q: What can I actually do with this project right now?
**A: You can:**
- Set up the development environment
- Run tests to understand the domain model
- Use domain entities programmatically in Python code
- Validate quality metrics programmatically
- Contribute to implementing infrastructure adapters

### Q: When will audio processing be available?
**A: It is planned for Phase 2** (Infrastructure Implementation). See the roadmap in PRODUCT.md.

### Q: How do I report issues or contribute?
**A:** This is a personal project following strict TDD and architecture guidelines. See CLAUDE.md for contribution rules and ADR documents for architecture decisions.

### Q: Is the project usable for end users?
**A: Not yet.** The project is in the foundation phase. Only the core domain logic is implemented. End-user functionality (CLI, scripts, audio processing) is planned but not available.

---

## Troubleshooting

### Bootstrap Script Fails

**Problem**: `bootstrap.sh` exits with error

**Solutions**:
1. Check Python version: `python3 --version` (must be 3.11+)
2. Check if espeak-ng is installed: `espeak-ng --version`
   - macOS: `brew install espeak-ng`
   - Linux: `sudo apt-get install espeak-ng`
3. Ensure you have internet connection (for UV installation)

### Tests Fail

**Problem**: `pytest` shows test failures

**Solutions**:
1. Ensure dependencies are installed: `uv sync`
2. Check Python version: `python3 --version`
3. Run tests with verbose output: `uv run pytest tests/ -v`
4. Check if virtual environment is activated

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'piper_voice'`

**Solutions**:
1. Install package in development mode: `uv sync`
2. Ensure you're in the project root directory
3. Check if virtual environment is active

### Type Checking Fails

**Problem**: `mypy` reports type errors

**Solutions**:
1. Check if mypy is installed: `uv run mypy --version`
2. Run mypy with verbose output: `uv run mypy piper_voice/ --show-error-codes`
3. Some third-party libraries (librosa, soundfile) have type stubs that may be incomplete

---

## Next Steps

To make this project fully functional, the following must be implemented (in order):

1. **Infrastructure Adapters** (Phase 2)
   - Audio processing (librosa/soundfile)
   - Phonetics validation (espeak-ng)
   - Filesystem operations (with security guardrails)
   - Metadata management (LJSPEECH format)

2. **Application Use Cases** (Phase 3)
   - Quality validation pipeline
   - Phonetics validation pipeline
   - Dataset preparation pipeline
   - Piper preprocessing coordination

3. **User Interface** (Phase 4)
   - CLI implementation
   - Utility scripts
   - Configuration files

4. **Training Pipeline** (Phase 5)
   - Piper training coordination
   - ONNX export
   - Model testing

See docs/product/decisions/ADR-001-project-foundation-architecture.md for the complete architecture plan.

---

## Additional Resources

- **Project Rules**: CLAUDE.md
- **Architecture Decisions**: docs/product/decisions/ADR-001-project-foundation-architecture.md
- **User Story**: docs/product/stories/STORY-001-french-dataset-foundation.md
- **Product Documentation**: docs/PRODUCT.md
- **Piper TTS Official Docs**: https://github.com/rhasspy/piper
