# ADR-001: Project Foundation Architecture

**Status:** Accepted  
**Date:** 2026-03-08  
**Deciders:** Architect  
**Related Story:** STORY-001 French Voice Dataset Foundation  

---

## Context and Problem Statement

We need to establish the foundational architecture for creating a high-quality French voice dataset for Piper TTS. This architecture must support:

- Audio recording ingestion and quality validation
- Transcription management and phonetic verification
- Dataset preprocessing for Piper training
- Model training and ONNX export
- Complete pipeline automation with rigorous testing

The architecture must respect Domain-Driven Design principles, maintain strict security boundaries, ensure audio quality non-negotiably, and follow Test-Driven Development practices.

**Core Challenge:** How do we structure the codebase to support complex audio processing workflows while maintaining clean domain boundaries, testability, and security guardrails?

---

## Decision Drivers

### Non-Negotiable Requirements

1. **DDD Compliance**
   - Domain layer (`piper_voice/core`) must never depend on infrastructure
   - Clean separation of concerns across domain/application/infrastructure
   - Dependency inversion: infrastructure adapters injected into domain

2. **Security Guardrails**
   - Filesystem access restricted to: `./dataset`, `./scripts`, `./piper_voice`, `./tests`, `./configs`, `./models`, `./logs`, `./checkpoints`, `./training`, `./docs`
   - FORBIDDEN: `$HOME`, `/`, SSH keys, environment secrets
   - No deletion of `dataset/raw/` (permanent backup)
   - Format restrictions: WAV 16-bit PCM only (16000 Hz or 22050 Hz)
   - File size limits: max 5 MB per WAV
   - Batch limits: max 1000 samples per preprocessing run

3. **Audio Quality Standards** (Non-Negotiable)
   - Sample rate: 22050 Hz (chosen for production quality)
   - Format: WAV 16-bit PCM
   - SNR: ≥ 30 dB
   - Duration: 1-15 seconds per sample
   - No clipping: peak amplitude < 0.95
   - Minimal silence: < 0.3 seconds at start/end

4. **Piper Conformity**
   - LJSPEECH metadata format
   - Official `piper_train.preprocess` workflow
   - Standard training with checkpoint saving
   - ONNX export with config.json

5. **TDD Strict**
   - All code requires tests written FIRST
   - Unit tests for every function
   - Integration tests for complete pipelines
   - Validation tests for quality checks

---

## Architectural Decisions

### 1. Three-Layer DDD Architecture

We adopt a strict three-layer architecture following Domain-Driven Design:

```
┌─────────────────────────────────────────────┐
│           Infrastructure Layer               │
│  (audio processing, filesystem, Piper CLI)  │
│  Depends on: Domain (via ports)             │
└─────────────────┬───────────────────────────┘
                  │ implements ports
                  │ injected into
┌─────────────────▼───────────────────────────┐
│           Application Layer                  │
│  (use cases, orchestration, workflows)      │
│  Depends on: Domain                         │
└─────────────────┬───────────────────────────┘
                  │ uses
                  │
┌─────────────────▼───────────────────────────┐
│              Domain Layer                    │
│  (entities, value objects, ports)           │
│  Depends on: NOTHING                        │
│  Pure business logic, no external deps      │
└─────────────────────────────────────────────┘
```

**Rationale:**
- Domain remains testable without infrastructure dependencies
- Business rules are explicit and centralized
- Infrastructure can be swapped without touching domain
- Enforces single direction of dependency flow

---

### 2. Domain Model (Core Entities)

**Domain Entities** (`piper_voice/core/entities.py`):

- `Voice`: Represents a complete voice model with characteristics (language, sample_rate, speaker_name)
- `AudioSample`: Represents a single audio recording with metadata (file_id, duration, quality_metrics)
- `Phoneme`: Represents a phonetic unit with validation rules
- `Transcript`: Represents text transcription with validation state

**Value Objects** (`piper_voice/core/value_objects.py`):

- `SampleRate`: Valid sample rates (16000, 22050 Hz)
- `Duration`: Time duration with min/max bounds (1-15 seconds)
- `AudioQuality`: Quality metrics (snr, clipping_detected, silence_duration)
- `AudioFormat`: Format specification (WAV 16-bit PCM)

**Domain Ports** (`piper_voice/core/ports.py`):

```python
# Abstract interfaces implemented by infrastructure
class AudioProcessorPort(Protocol):
    def load_audio(self, path: Path) -> AudioData: ...
    def calculate_snr(self, audio: AudioData) -> float: ...
    def detect_clipping(self, audio: AudioData) -> bool: ...
    def measure_silence(self, audio: AudioData) -> tuple[float, float]: ...
    def normalize_volume(self, audio: AudioData) -> AudioData: ...

class PhoneticsCheckerPort(Protocol):
    def validate_text(self, text: str, language: str) -> PhoneticsResult: ...
    def get_phonemes(self, text: str, language: str) -> list[Phoneme]: ...

class FileSystemPort(Protocol):
    def read_audio(self, path: Path) -> bytes: ...
    def write_audio(self, path: Path, data: bytes) -> None: ...
    def list_audio_files(self, directory: Path) -> list[Path]: ...
```

**Rationale:**
- Domain has no knowledge of librosa, soundfile, espeak-ng, or filesystem
- All external interactions go through ports
- Domain logic is 100% testable with mock adapters
- Infrastructure can evolve independently

---

### 3. Application Layer (Use Cases)

**Orchestration Use Cases** (`piper_voice/application/`):

```
application/
├── prepare_dataset.py       # Orchestrates audio normalization + metadata creation
├── validate_quality.py      # Orchestrates quality validation pipeline
├── validate_phonetics.py    # Orchestrates phonetic validation
├── preprocess_for_piper.py  # Orchestrates Piper preprocessing
└── train_voice.py           # Orchestrates training workflow
```

**Key Responsibilities:**
- Coordinate between domain entities and infrastructure adapters
- Implement workflow logic (prepare → validate → preprocess → train)
- Handle error recovery and reporting
- Manage transactions (ensure atomic operations)

**Example Use Case Flow:**

```python
# application/validate_quality.py
class ValidateQualityUseCase:
    def __init__(
        self,
        audio_processor: AudioProcessorPort,
        filesystem: FileSystemPort,
        quality_standards: QualityStandards
    ):
        self.audio_processor = audio_processor
        self.filesystem = filesystem
        self.quality_standards = quality_standards
    
    def execute(self, dataset_path: Path) -> ValidationReport:
        samples = []
        for audio_path in self.filesystem.list_audio_files(dataset_path):
            audio_data = self.audio_processor.load_audio(audio_path)
            quality = AudioQuality(
                snr=self.audio_processor.calculate_snr(audio_data),
                clipping=self.audio_processor.detect_clipping(audio_data),
                silence=self.audio_processor.measure_silence(audio_data)
            )
            sample = AudioSample.create(audio_path, quality)
            samples.append(sample)
        
        return ValidationReport.from_samples(samples, self.quality_standards)
```

**Rationale:**
- Application layer has no domain logic, only workflow coordination
- Testable by injecting mock ports
- Clear separation between "what" (domain) and "how" (infrastructure)

---

### 4. Infrastructure Layer (Adapters)

**Infrastructure Modules** (`piper_voice/infrastructure/`):

```
infrastructure/
├── audio/
│   ├── processor.py           # Implements AudioProcessorPort (librosa/soundfile)
│   ├── quality_analyzer.py    # SNR, clipping, silence detection
│   └── normalizer.py          # Volume normalization
├── phonetics/
│   └── espeak_adapter.py      # Implements PhoneticsCheckerPort (espeak-ng wrapper)
├── piper/
│   ├── preprocessor.py        # Wrapper for piper_train.preprocess
│   ├── trainer.py             # Wrapper for piper_train
│   └── exporter.py            # Wrapper for piper_train.export_onnx
├── filesystem/
│   ├── safe_filesystem.py     # Implements FileSystemPort with guardrails
│   └── path_validator.py     # Enforces security boundaries
└── metadata/
    ├── ljspeech_writer.py     # Writes metadata.csv
    └── dataset_builder.py     # Builds dataset.jsonl
```

**Security Implementation** (`infrastructure/filesystem/safe_filesystem.py`):

```python
ALLOWED_PATHS = [
    Path("./dataset").resolve(),
    Path("./scripts").resolve(),
    Path("./piper_voice").resolve(),
    Path("./tests").resolve(),
    Path("./configs").resolve(),
    Path("./models").resolve(),
    Path("./logs").resolve(),
    Path("./checkpoints").resolve(),
    Path("./training").resolve(),
    Path("./docs").resolve(),
]

FORBIDDEN_OPERATIONS = [
    ("delete", "dataset/raw"),  # Never delete permanent backups
]

class SafeFileSystem(FileSystemPort):
    def _validate_path(self, path: Path) -> None:
        resolved = path.resolve()
        if not any(resolved.is_relative_to(allowed) for allowed in ALLOWED_PATHS):
            raise SecurityError(f"Access denied: {path}")
    
    def write_audio(self, path: Path, data: bytes) -> None:
        self._validate_path(path)
        if len(data) > 5 * 1024 * 1024:  # 5 MB limit
            raise ValidationError("Audio file exceeds 5 MB limit")
        # ... write logic
```

**Rationale:**
- All filesystem operations go through validated safe wrapper
- Security guardrails enforced at infrastructure boundary
- Impossible to bypass restrictions from application/domain layers

---

### 5. Directory Structure

```
jpa_voice_piper/
│
├── piper_voice/                    # Main Python package
│   ├── __init__.py
│   ├── core/                       # Domain layer (PURE, no deps)
│   │   ├── __init__.py
│   │   ├── entities.py            # Voice, AudioSample, Transcript, Phoneme
│   │   ├── value_objects.py       # SampleRate, Duration, AudioQuality
│   │   └── ports.py               # Abstract interfaces for infrastructure
│   │
│   ├── application/                # Use cases (orchestration)
│   │   ├── __init__.py
│   │   ├── prepare_dataset.py
│   │   ├── validate_quality.py
│   │   ├── validate_phonetics.py
│   │   ├── preprocess_for_piper.py
│   │   └── train_voice.py
│   │
│   ├── infrastructure/             # Adapters (external systems)
│   │   ├── __init__.py
│   │   ├── audio/
│   │   │   ├── processor.py
│   │   │   ├── quality_analyzer.py
│   │   │   └── normalizer.py
│   │   ├── phonetics/
│   │   │   └── espeak_adapter.py
│   │   ├── piper/
│   │   │   ├── preprocessor.py
│   │   │   ├── trainer.py
│   │   │   └── exporter.py
│   │   ├── filesystem/
│   │   │   ├── safe_filesystem.py
│   │   │   └── path_validator.py
│   │   └── metadata/
│   │       ├── ljspeech_writer.py
│   │       └── dataset_builder.py
│   │
│   └── cli.py                      # CLI entrypoint
│
├── dataset/                        # Dataset workspace
│   ├── raw/                        # PERMANENT BACKUP (read-only in code)
│   ├── wav/                        # Normalized WAV files for Piper
│   ├── metadata.csv                # LJSPEECH format
│   └── validation_report.json      # Quality validation results
│
├── training/                       # Piper preprocessing output
│   ├── config.json
│   ├── dataset.jsonl
│   └── audio_norm_stats.json
│
├── models/                         # Exported ONNX models
│   ├── voice_fr.onnx
│   └── voice_fr.onnx.json
│
├── scripts/                        # Automation scripts
│   ├── bootstrap.sh                # Complete project setup
│   ├── test.sh                     # Run complete test suite
│   ├── generate_metadata.py        # Create initial metadata.csv
│   ├── validate_quality.py         # Quality validation CLI
│   └── prepare_dataset.py          # Dataset normalization CLI
│
├── tests/                          # Test suite
│   ├── unit/                       # Unit tests (domain + isolated components)
│   │   ├── test_entities.py
│   │   ├── test_value_objects.py
│   │   ├── test_audio_quality.py
│   │   └── test_phonetics.py
│   ├── integration/                # Integration tests (complete pipelines)
│   │   ├── test_prepare_pipeline.py
│   │   ├── test_validation_pipeline.py
│   │   └── test_training_pipeline.py
│   └── validation/                 # Conformity tests (Piper compliance)
│       ├── test_metadata_format.py
│       ├── test_preprocessing.py
│       └── test_onnx_export.py
│
├── configs/                        # Configuration files
│   ├── audio_quality.yaml          # Quality thresholds
│   ├── phonetics.yaml              # Phonetic rules
│   └── training.yaml               # Training hyperparameters
│
├── docs/                           # Documentation
│   ├── product/
│   │   ├── stories/                # Product stories
│   │   │   └── STORY-001-french-dataset-foundation.md
│   │   └── decisions/              # Architecture decisions
│   │       └── ADR-001-project-foundation-architecture.md
│   ├── plans/
│   │   └── active/                 # Active development plans
│   ├── PRODUCT.md                  # Product documentation
│   └── USER_GUIDE.md               # User documentation
│
├── logs/                           # Operation logs
│   ├── training_*.log
│   ├── quality_*.json
│   └── phonetics_*.txt
│
├── checkpoints/                    # Training checkpoints
│   └── *.ckpt
│
├── lightning_logs/                 # TensorBoard logs
│   └── version_*/
│
├── pyproject.toml                  # UV project configuration
├── uv.lock                         # Dependency lock file
├── CLAUDE.md                       # Project rules (AUTHORITY)
└── README.md                       # Project overview
```

---

### 6. Technology Stack

**Core Technologies:**

| Component | Technology | Version | Justification |
|-----------|-----------|---------|---------------|
| Python | CPython | 3.11+ | Piper requirement, modern type hints |
| Package Manager | UV | latest | Fast, modern, deterministic |
| Audio Processing | librosa | 0.10+ | Industry standard for audio analysis |
| Audio I/O | soundfile | 0.12+ | High-quality WAV read/write |
| Phonetics | espeak-ng | 1.51+ | Official Piper phonetic backend |
| TTS Training | piper_train | latest | Official Piper training tools |
| Deep Learning | PyTorch | 2.0+ | Piper dependency |
| Testing | pytest | 7.4+ | Industry standard, rich plugin ecosystem |
| Linting | ruff | 0.1+ | Fast, comprehensive Python linter |
| Type Checking | mypy | 1.7+ | Static type safety |
| Monitoring | TensorBoard | latest | Training visualization |

**Dependency Management Strategy:**

```toml
# pyproject.toml structure
[project]
name = "piper-voice-dataset"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    # Core (minimal for CLI)
    "pydantic>=2.0",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
audio = [
    "librosa>=0.10.0",
    "soundfile>=0.12.0",
    "numpy>=1.24.0",
    "scipy>=1.11.0",
]
training = [
    "piper-train>=1.0.0",
    "torch>=2.0.0",
    "tensorboard>=2.14.0",
]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.1.0",
    "mypy>=1.7.0",
]
```

**Rationale:**
- Minimal core dependencies (domain remains lightweight)
- Optional extras for audio processing (not needed for all use cases)
- Training tools isolated (heavy dependencies only when training)
- Clean separation enables faster testing and deployment

---

### 7. Testing Strategy (TDD Enforcement)

**Test Structure:**

```
tests/
├── conftest.py                     # Shared fixtures
├── unit/                           # Fast, isolated tests
│   ├── core/
│   │   ├── test_audio_sample.py   # Domain entity tests
│   │   ├── test_voice.py
│   │   ├── test_transcript.py
│   │   └── test_phoneme.py
│   ├── application/
│   │   ├── test_validate_quality_usecase.py
│   │   └── test_prepare_dataset_usecase.py
│   └── infrastructure/
│       ├── test_audio_processor.py
│       ├── test_espeak_adapter.py
│       └── test_safe_filesystem.py
│
├── integration/                    # Multi-component tests
│   ├── test_quality_validation_pipeline.py
│   ├── test_dataset_preparation_pipeline.py
│   ├── test_phonetics_validation_pipeline.py
│   └── test_piper_preprocessing_pipeline.py
│
└── validation/                     # Conformity tests
    ├── test_ljspeech_format.py
    ├── test_piper_preprocessing_output.py
    └── test_onnx_export_validity.py
```

**Test Requirements (Non-Negotiable):**

1. **Every function requires unit test BEFORE implementation**
   - Domain entities: test business rules, validation, state transitions
   - Value objects: test invariants, comparison, serialization
   - Use cases: test orchestration logic with mock adapters
   - Infrastructure: test external integration with real components

2. **Integration tests required for complete pipelines**
   - Audio validation: raw audio → quality report
   - Dataset preparation: raw audio → normalized WAV + metadata.csv
   - Phonetics validation: metadata.csv → phonetic validation report
   - Piper preprocessing: dataset → training/dataset.jsonl

3. **Validation tests for Piper conformity**
   - LJSPEECH format compliance
   - Piper preprocessing success
   - ONNX export validity
   - Synthesis test (echo "test" | piper -m model.onnx)

**Test Data Strategy:**

```
tests/fixtures/
├── audio/
│   ├── valid_sample.wav           # Meets all quality criteria
│   ├── clipped_sample.wav         # Has clipping (should fail)
│   ├── noisy_sample.wav           # Low SNR (should fail)
│   ├── short_sample.wav           # Too short (should fail)
│   └── long_sample.wav            # Too long (should fail)
├── metadata/
│   ├── valid_metadata.csv         # LJSPEECH format
│   └── invalid_metadata.csv       # Malformed
└── config/
    └── test_config.yaml
```

**Coverage Requirements:**

- Minimum 90% code coverage
- 100% coverage for domain layer (critical business logic)
- All error paths must be tested
- Security guardrails must have dedicated tests

**Example TDD Workflow:**

```python
# Step 1: Write failing test FIRST
def test_audio_sample_rejects_clipped_audio():
    quality = AudioQuality(snr=35.0, clipping=True, silence=(0.1, 0.1))
    
    with pytest.raises(ValidationError, match="clipping detected"):
        AudioSample.create(
            file_id="test",
            duration=Duration(5.0),
            quality=quality
        )

# Step 2: Run test → FAILS (AudioSample doesn't exist yet)
# Step 3: Implement minimal code to pass
# Step 4: Run test → PASSES
# Step 5: Refactor
# Step 6: Commit
```

---

### 8. Security Guardrails Implementation

**Path Validation** (`infrastructure/filesystem/path_validator.py`):

```python
from pathlib import Path
from typing import Final

# Immutable whitelist
ALLOWED_ROOTS: Final[frozenset[Path]] = frozenset([
    Path("./dataset").resolve(),
    Path("./scripts").resolve(),
    Path("./piper_voice").resolve(),
    Path("./tests").resolve(),
    Path("./configs").resolve(),
    Path("./models").resolve(),
    Path("./logs").resolve(),
    Path("./checkpoints").resolve(),
    Path("./training").resolve(),
    Path("./docs").resolve(),
])

# Read-only paths
READ_ONLY_PATHS: Final[frozenset[Path]] = frozenset([
    Path("./dataset/raw").resolve(),
])

class PathValidator:
    @staticmethod
    def validate_read(path: Path) -> None:
        resolved = path.resolve()
        if not any(resolved.is_relative_to(root) for root in ALLOWED_ROOTS):
            raise SecurityError(f"Read access denied: {path}")
    
    @staticmethod
    def validate_write(path: Path) -> None:
        resolved = path.resolve()
        
        # Check whitelist
        if not any(resolved.is_relative_to(root) for root in ALLOWED_ROOTS):
            raise SecurityError(f"Write access denied: {path}")
        
        # Check read-only paths
        if any(resolved.is_relative_to(ro) for ro in READ_ONLY_PATHS):
            raise SecurityError(f"Write denied (read-only): {path}")
    
    @staticmethod
    def validate_delete(path: Path) -> None:
        resolved = path.resolve()
        
        # Never allow deletion in dataset/raw/
        if resolved.is_relative_to(Path("./dataset/raw").resolve()):
            raise SecurityError("Deletion forbidden in dataset/raw (permanent backup)")
        
        PathValidator.validate_write(path)  # Must pass write checks
```

**Format Validation** (`infrastructure/audio/format_validator.py`):

```python
ALLOWED_FORMATS: Final[set[str]] = {"WAV"}
ALLOWED_SAMPLE_RATES: Final[set[int]] = {16000, 22050}
MAX_FILE_SIZE_BYTES: Final[int] = 5 * 1024 * 1024  # 5 MB

class AudioFormatValidator:
    @staticmethod
    def validate_file(path: Path) -> None:
        # Check file size
        if path.stat().st_size > MAX_FILE_SIZE_BYTES:
            raise ValidationError(f"File exceeds 5 MB: {path}")
        
        # Check format (using soundfile)
        info = sf.info(path)
        
        if info.format != "WAV":
            raise ValidationError(f"Only WAV format allowed, got: {info.format}")
        
        if info.subtype != "PCM_16":
            raise ValidationError(f"Only 16-bit PCM allowed, got: {info.subtype}")
        
        if info.samplerate not in ALLOWED_SAMPLE_RATES:
            raise ValidationError(
                f"Sample rate must be 16000 or 22050 Hz, got: {info.samplerate}"
            )
```

**Batch Limits** (`application/preprocess_for_piper.py`):

```python
MAX_BATCH_SIZE: Final[int] = 1000

class PreprocessForPiperUseCase:
    def execute(self, dataset_path: Path) -> None:
        audio_files = self.filesystem.list_audio_files(dataset_path)
        
        if len(audio_files) > MAX_BATCH_SIZE:
            raise ValidationError(
                f"Batch size {len(audio_files)} exceeds limit of {MAX_BATCH_SIZE}"
            )
        
        # ... proceed with preprocessing
```

**Rationale:**
- Security enforced at infrastructure boundary (impossible to bypass)
- All violations raise exceptions (fail-fast)
- Immutable configuration (frozenset prevents tampering)
- Explicit, testable security rules

---

### 9. Audio Quality Validation Pipeline

**Quality Standards** (`configs/audio_quality.yaml`):

```yaml
sample_rate: 22050  # Hz (chosen for production quality)
bit_depth: 16       # bits
format: WAV
encoding: PCM

quality_thresholds:
  snr_min: 30.0           # dB (signal-to-noise ratio)
  peak_amplitude_max: 0.95  # (clipping detection)
  duration_min: 1.0       # seconds
  duration_max: 15.0      # seconds
  silence_max: 0.3        # seconds (start/end)

validation_rules:
  reject_on_clipping: true
  reject_on_low_snr: true
  reject_on_invalid_duration: true
  reject_on_excessive_silence: true
```

**Quality Analyzer** (`infrastructure/audio/quality_analyzer.py`):

```python
class AudioQualityAnalyzer:
    def analyze(self, audio: np.ndarray, sample_rate: int) -> AudioQuality:
        snr = self._calculate_snr(audio)
        clipping = self._detect_clipping(audio)
        silence_start, silence_end = self._measure_silence(audio, sample_rate)
        
        return AudioQuality(
            snr=snr,
            clipping_detected=clipping,
            silence_start=silence_start,
            silence_end=silence_end
        )
    
    def _calculate_snr(self, audio: np.ndarray) -> float:
        # Signal power
        signal_power = np.mean(audio ** 2)
        
        # Estimate noise floor (bottom 10th percentile of absolute values)
        noise_floor = np.percentile(np.abs(audio), 10)
        noise_power = noise_floor ** 2
        
        if noise_power == 0:
            return float('inf')
        
        snr_linear = signal_power / noise_power
        snr_db = 10 * np.log10(snr_linear)
        
        return snr_db
    
    def _detect_clipping(self, audio: np.ndarray) -> bool:
        peak = np.max(np.abs(audio))
        return peak >= 0.95
    
    def _measure_silence(
        self, 
        audio: np.ndarray, 
        sample_rate: int,
        threshold_db: float = -40.0
    ) -> tuple[float, float]:
        # Convert to dB
        audio_db = librosa.amplitude_to_db(np.abs(audio), ref=np.max)
        
        # Find first/last non-silent frames
        non_silent = audio_db > threshold_db
        first_sound = np.argmax(non_silent)
        last_sound = len(audio) - np.argmax(non_silent[::-1]) - 1
        
        silence_start = first_sound / sample_rate
        silence_end = (len(audio) - last_sound - 1) / sample_rate
        
        return silence_start, silence_end
```

**Validation Use Case** (`application/validate_quality.py`):

```python
class ValidateQualityUseCase:
    def execute(self, dataset_path: Path) -> ValidationReport:
        results = []
        
        for audio_path in self.filesystem.list_audio_files(dataset_path / "raw"):
            try:
                # Load audio
                audio_data = self.audio_processor.load_audio(audio_path)
                
                # Analyze quality
                quality = self.quality_analyzer.analyze(
                    audio_data.samples,
                    audio_data.sample_rate
                )
                
                # Validate against standards
                validation = self._validate_quality(quality, audio_data.duration)
                
                results.append(ValidationResult(
                    file_path=audio_path,
                    quality=quality,
                    passed=validation.passed,
                    errors=validation.errors
                ))
            
            except Exception as e:
                results.append(ValidationResult(
                    file_path=audio_path,
                    quality=None,
                    passed=False,
                    errors=[str(e)]
                ))
        
        return ValidationReport(results)
```

**Rationale:**
- Automated quality validation (no manual checks)
- Clear, measurable quality criteria
- Detailed error reporting (actionable feedback)
- Fail-fast approach (catch problems early)

---

### 10. Bootstrap Strategy

**Bootstrap Script** (`scripts/bootstrap.sh`):

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "=== Piper Voice Dataset Project Bootstrap ==="

# 1. Check Python version
echo "Checking Python version..."
python_version=$(python3 --version | cut -d' ' -f2)
required_version="3.11"
if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"; then
    echo "ERROR: Python 3.11+ required, found $python_version"
    exit 1
fi
echo "✓ Python $python_version"

# 2. Install UV if not present
if ! command -v uv &> /dev/null; then
    echo "Installing UV package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi
echo "✓ UV installed"

# 3. Check espeak-ng
if ! command -v espeak-ng &> /dev/null; then
    echo "ERROR: espeak-ng not found"
    echo "Install with: brew install espeak-ng"
    exit 1
fi
echo "✓ espeak-ng available"

# 4. Sync dependencies
echo "Installing dependencies..."
uv sync --all-extras
echo "✓ Dependencies installed"

# 5. Create directory structure
echo "Creating directory structure..."
mkdir -p dataset/raw dataset/wav
mkdir -p training models logs checkpoints
mkdir -p docs/product/stories docs/product/decisions docs/plans/active
mkdir -p tests/unit tests/integration tests/validation
mkdir -p configs
echo "✓ Directories created"

# 6. Create config templates if not exist
if [ ! -f configs/audio_quality.yaml ]; then
    cat > configs/audio_quality.yaml << 'EOCONFIG'
sample_rate: 22050
bit_depth: 16
format: WAV
encoding: PCM

quality_thresholds:
  snr_min: 30.0
  peak_amplitude_max: 0.95
  duration_min: 1.0
  duration_max: 15.0
  silence_max: 0.3

validation_rules:
  reject_on_clipping: true
  reject_on_low_snr: true
  reject_on_invalid_duration: true
  reject_on_excessive_silence: true
EOCONFIG
    echo "✓ Created configs/audio_quality.yaml"
fi

# 7. Run tests to verify installation
echo "Running test suite..."
if uv run pytest tests/ -v; then
    echo "✓ All tests passed"
else
    echo "WARNING: Some tests failed (expected if first run)"
fi

echo ""
echo "=== Bootstrap Complete ==="
echo "Next steps:"
echo "  1. Record audio samples in dataset/raw/"
echo "  2. Run: python scripts/generate_metadata.py"
echo "  3. Run: python scripts/validate_quality.py"
echo "  4. Run: python scripts/prepare_dataset.py"
echo ""
```

**Rationale:**
- Single command setup (`./scripts/bootstrap.sh`)
- Validates all prerequisites before proceeding
- Idempotent (safe to run multiple times)
- Clear error messages with resolution steps
- Creates complete directory structure
- Runs tests to verify installation

---

### 11. Merge Requirements (Quality Gate)

A change can ONLY be merged to `main` if ALL criteria pass:

**Automated Checks:**
1. `uv run ruff check .` → EXIT 0
2. `uv run ruff format --check .` → EXIT 0
3. `uv run mypy piper_voice/` → EXIT 0
4. `uv run pytest tests/` → EXIT 0 (all tests pass)
5. `python scripts/validate_quality.py --dataset ./dataset` → EXIT 0 (if audio exists)
6. `python scripts/validate_phonetics.py --metadata ./dataset/metadata.csv` → EXIT 0 (if metadata exists)

**Manual Checks (Architect Review):**
7. DDD boundaries respected (core has no infrastructure deps)
8. Security guardrails intact (no new risky paths/operations)
9. TDD followed (tests written BEFORE code)
10. Patch size ≤ 10 files, ≤ 600 lines changed

**Pipeline Script** (`scripts/test.sh`):

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "=== Running Quality Pipeline ==="

echo "1. Code formatting..."
uv run ruff format --check . || { echo "FAIL: ruff format"; exit 1; }

echo "2. Linting..."
uv run ruff check . || { echo "FAIL: ruff check"; exit 1; }

echo "3. Type checking..."
uv run mypy piper_voice/ || { echo "FAIL: mypy"; exit 1; }

echo "4. Unit + Integration tests..."
uv run pytest tests/ -v --cov=piper_voice --cov-report=term-missing || { echo "FAIL: pytest"; exit 1; }

if [ -f dataset/metadata.csv ]; then
    echo "5. Audio quality validation..."
    python scripts/validate_quality.py --dataset ./dataset || { echo "FAIL: quality validation"; exit 1; }
    
    echo "6. Phonetics validation..."
    python scripts/validate_phonetics.py --metadata ./dataset/metadata.csv || { echo "FAIL: phonetics validation"; exit 1; }
fi

echo "=== All Checks Passed ==="
```

**Rationale:**
- Automated quality gate (no human judgment required)
- Consistent standards across all changes
- Fast feedback (catches issues before review)
- Prevents technical debt accumulation

---

## Consequences

### Positive

1. **Clean Architecture**
   - Domain logic is isolated and testable
   - Infrastructure can evolve independently
   - Clear separation of concerns

2. **Security by Design**
   - Guardrails enforced at compile time (type system + runtime checks)
   - Impossible to bypass security boundaries
   - Explicit, auditable security rules

3. **Quality Assurance**
   - Automated validation catches issues early
   - TDD ensures comprehensive test coverage
   - Merge gate prevents quality regression

4. **Maintainability**
   - Clear structure aids navigation
   - Dependencies flow in one direction
   - Refactoring is safe (tests catch breakage)

5. **Piper Conformity**
   - Official workflows guaranteed
   - LJSPEECH format enforced
   - Training pipeline standardized

### Negative

1. **Initial Complexity**
   - More upfront design required
   - Steeper learning curve for contributors
   - Additional abstractions to understand

2. **Boilerplate**
   - Ports require interface definitions
   - Dependency injection setup needed
   - More files to navigate

3. **Testing Overhead**
   - TDD requires discipline
   - More test code than production code
   - Longer initial development time

### Mitigation

- **Complexity**: Comprehensive documentation and examples
- **Boilerplate**: Use code generation where appropriate
- **Testing**: Provide test templates and fixtures

---

## Implementation Plan

### Phase 1: Foundation (Week 1)
1. Create directory structure (`bootstrap.sh`)
2. Setup `pyproject.toml` with UV
3. Implement domain entities (Voice, AudioSample, Transcript, Phoneme)
4. Implement value objects (SampleRate, Duration, AudioQuality)
5. Define ports (AudioProcessorPort, PhoneticsCheckerPort, FileSystemPort)
6. Write unit tests for domain layer (TDD)

### Phase 2: Infrastructure (Week 2)
1. Implement SafeFileSystem adapter with path validation
2. Implement AudioProcessor adapter (librosa/soundfile)
3. Implement AudioQualityAnalyzer (SNR, clipping, silence)
4. Implement EspeakAdapter (espeak-ng wrapper)
5. Write unit tests for infrastructure adapters (TDD)

### Phase 3: Application Layer (Week 3)
1. Implement ValidateQualityUseCase
2. Implement ValidatePhoneticsUseCase
3. Implement PrepareDatasetUseCase
4. Implement PreprocessForPiperUseCase
5. Write integration tests for use cases (TDD)

### Phase 4: CLI and Scripts (Week 4)
1. Implement CLI entrypoint (`piper_voice/cli.py`)
2. Implement `scripts/validate_quality.py`
3. Implement `scripts/validate_phonetics.py`
4. Implement `scripts/prepare_dataset.py`
5. Implement `scripts/generate_metadata.py`
6. Write end-to-end tests

### Phase 5: Training Coordination (Week 5)
1. Implement PiperPreprocessor wrapper
2. Implement PiperTrainer wrapper
3. Implement PiperExporter wrapper
4. Implement TrainVoiceUseCase
5. Write validation tests for Piper conformity

### Phase 6: Documentation (Week 6)
1. Write USER_GUIDE.md (recording audio, preparing dataset)
2. Write PRODUCT.md (dataset status, model characteristics)
3. Write DATASET_STATUS.md (quality metrics)
4. Create example workflows
5. Document contribution process

---

## Acceptance Criteria

This architecture is accepted when:

1. ✅ All domain entities exist with zero infrastructure dependencies
2. ✅ All ports are defined with clear contracts
3. ✅ Security guardrails are implemented and tested
4. ✅ Audio quality validation pipeline works end-to-end
5. ✅ Phonetics validation pipeline works end-to-end
6. ✅ Dataset preparation pipeline produces LJSPEECH-compliant output
7. ✅ Piper preprocessing succeeds with prepared dataset
8. ✅ Test coverage ≥ 90% (100% for domain layer)
9. ✅ All quality gates pass (ruff, mypy, pytest)
10. ✅ Bootstrap script creates working environment
11. ✅ Documentation is complete and accurate

---

## References

- [Piper TTS Training Guide](https://github.com/rhasspy/piper/blob/master/TRAINING.md)
- [LJSPEECH Dataset Format](https://keithito.com/LJ-Speech-Dataset/)
- [Domain-Driven Design (Eric Evans)](https://www.domainlanguage.com/ddd/)
- [Clean Architecture (Robert C. Martin)](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Test-Driven Development (Kent Beck)](https://www.amazon.com/Test-Driven-Development-Kent-Beck/dp/0321146530)

---

## Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-03-08 | 1.0 | Architect | Initial architecture decision |

---

**Decision:** ACCEPTED

This architecture provides the foundation for building a high-quality French voice dataset for Piper TTS while respecting DDD principles, security guardrails, audio quality standards, and TDD practices.

Implementation must follow this architecture strictly. Any deviation requires explicit approval and documentation in a new ADR.
