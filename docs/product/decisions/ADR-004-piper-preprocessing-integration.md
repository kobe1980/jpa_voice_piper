# ADR-004: Piper Preprocessing Integration

**Status**: ACCEPTED
**Date**: 2026-03-08
**Deciders**: Architect
**Related**: STORY-004-piper-preprocessing-integration.md, ADR-001-japanese-voice-architecture.md, ADR-003-japanese-phonetization-implementation.md

---

## Context

STORY-004 requires integrating with Piper's preprocessing pipeline to prepare Japanese voice dataset for training. This is the critical bridge between phoneme preparation (Phase 3) and actual model training.

**Key Challenges**:

1. **Custom Phoneme System**: Piper preprocessing typically uses espeak-ng, but we have custom hiragana phonemes
2. **Dataset Format Conversion**: Transform metadata_phonemes.csv → dataset.jsonl (Piper's training format)
3. **Configuration Generation**: Create config.json with custom phoneme mapping
4. **Audio Statistics**: Calculate normalization statistics for consistent training
5. **DDD Architecture**: Maintain domain/application/infrastructure boundaries
6. **Piper API Integration**: Decide between subprocess calls vs Python API imports

**Technical Constraints**:
- Input: `dataset/wav/*.wav` (22050 Hz, 16-bit PCM), `dataset/metadata_phonemes.csv`, `dataset/phoneme_map.json`
- Output: `training/dataset.jsonl`, `training/audio_norm_stats.json`, `training/config.json`
- Requirement: Compatible with Piper training pipeline
- Performance: Must preprocess 7,300 samples in <30 minutes
- Validation: Output must be deterministic and reproducible

**Architectural Requirements** (from CLAUDE.md):
- Domain layer (`piper_voice/core`) must NOT depend on infrastructure
- Infrastructure adapters must be injected via ports
- TDD mandatory: tests before implementation
- Security: path validation, no modification of dataset/raw/, timeout for subprocesses

---

## Decisions

### 1. Piper Integration Strategy: Hybrid Python API + Subprocess

**Decision**: Use Python API for audio processing, subprocess wrapper for training compatibility.

**Architecture**:
```
piper_voice/
├── core/
│   ├── entities.py
│   │   └── PiperDataset (new entity)
│   │   └── TrainingConfig (new entity)
│   └── ports.py
│       └── PiperPreprocessorPort (already exists as PiperTrainingPort)
│
├── infrastructure/
│   └── piper/
│       ├── preprocessor_adapter.py (new: implements preprocessing logic)
│       ├── audio_stats.py (new: audio normalization statistics)
│       └── config_generator.py (new: generates Piper config.json)
│
└── application/
    └── preprocess_japanese_dataset.py (new: orchestration use case)
```

**Integration Approach**:

**Option A - Python API Import** (CHOSEN):
```python
# Direct import of Piper preprocessing utilities
from piper_train.preprocess import (
    preprocess_dataset,
    AudioNormalizer,
    calculate_audio_stats
)
```

**Rationale**:
- ✅ Direct control over preprocessing logic
- ✅ Better error handling and debugging
- ✅ Access to intermediate results
- ✅ No subprocess overhead
- ✅ Easier to test with mocks
- ❌ Requires piper_train as dependency

**Option B - Subprocess Wrapper** (Fallback):
```python
# Call piper_train.preprocess as subprocess
subprocess.run([
    "python", "-m", "piper_train.preprocess",
    "--input-dir", dataset_dir,
    "--output-dir", output_dir,
    "--config", config_path
], check=True, timeout=1800)
```

**Rationale**:
- ✅ Isolation from Piper internal changes
- ✅ Standard Piper interface
- ❌ Limited error visibility
- ❌ Harder to customize
- ❌ Subprocess overhead
- ❌ Timeout management complexity

**Final Decision**: Use **Option A (Python API)** with Option B as fallback if Piper API is unstable.

**Dependency Management**:
```toml
# pyproject.toml
[project.optional-dependencies]
training = [
    "torch>=2.0.0",
    "onnxruntime>=1.15.0",
    "piper-tts @ git+https://github.com/rhasspy/piper.git@master#subdirectory=src/python",  # Piper preprocessing
]
```

---

### 2. Custom Phoneme Integration: Configuration Override

**Decision**: Override Piper's default phoneme system via custom config.json.

**Phoneme Integration Strategy**:

Piper preprocessing typically expects:
```json
{
  "audio": {
    "sample_rate": 22050
  },
  "phoneme_id_map": {
    "a": 0,
    "b": 1,
    ...
  },
  "num_symbols": 200
}
```

**Our Custom Config** (generated from phoneme_map.json):
```json
{
  "audio": {
    "sample_rate": 22050,
    "filter_length": 1024,
    "hop_length": 256,
    "win_length": 1024,
    "mel_channels": 80,
    "mel_fmin": 0.0,
    "mel_fmax": 8000.0
  },
  "inference": {
    "noise_scale": 0.667,
    "length_scale": 1.0,
    "noise_w": 0.8
  },
  "phoneme_id_map": {
    "あ": 0,
    "い": 1,
    "う": 2,
    ...
    "ん": 98,
    "っ": 99
  },
  "num_symbols": 100,
  "espeak": {
    "voice": "ja"
  },
  "language": {
    "code": "ja",
    "family": "japanese",
    "region": "JP",
    "name_native": "日本語",
    "name_english": "Japanese",
    "key": "ja_jp"
  },
  "dataset": "jsut_hiragana",
  "custom_phonemes": true
}
```

**Key Configuration Points**:

1. **phoneme_id_map**: Maps hiragana characters to phoneme IDs (from Phase 3 phoneme_map.json)
2. **num_symbols**: Total unique phonemes (~100 for hiragana)
3. **custom_phonemes: true**: Flag indicating non-standard phoneme system
4. **audio parameters**: Preserve Piper defaults for VITS model
5. **language metadata**: Document Japanese voice characteristics

**Config Generation Logic** (`infrastructure/piper/config_generator.py`):
```python
from pathlib import Path
import json
from typing import Dict, Any
from piper_voice.core.entities import PhonemeMap

class PiperConfigGenerator:
    """Generates Piper config.json from custom phoneme map."""
    
    DEFAULT_AUDIO_CONFIG = {
        "sample_rate": 22050,
        "filter_length": 1024,
        "hop_length": 256,
        "win_length": 1024,
        "mel_channels": 80,
        "mel_fmin": 0.0,
        "mel_fmax": 8000.0
    }
    
    DEFAULT_INFERENCE_CONFIG = {
        "noise_scale": 0.667,
        "length_scale": 1.0,
        "noise_w": 0.8
    }
    
    def generate_config(
        self,
        phoneme_map: PhonemeMap,
        output_path: Path,
        dataset_name: str = "jsut_hiragana"
    ) -> None:
        """Generate Piper config.json from phoneme map.
        
        Args:
            phoneme_map: PhonemeMap entity with hiragana → ID mappings
            output_path: Path to save config.json
            dataset_name: Name of dataset for documentation
            
        Raises:
            ValueError: If phoneme map is empty or invalid
        """
        if len(phoneme_map) == 0:
            raise ValueError("Cannot generate config from empty phoneme map")
        
        # Convert phoneme map to dictionary
        phoneme_id_dict = phoneme_map.to_dict()["phonemes"]
        
        config = {
            "audio": self.DEFAULT_AUDIO_CONFIG.copy(),
            "inference": self.DEFAULT_INFERENCE_CONFIG.copy(),
            "phoneme_id_map": phoneme_id_dict,
            "num_symbols": len(phoneme_map),
            "espeak": {
                "voice": "ja"
            },
            "language": {
                "code": "ja",
                "family": "japanese",
                "region": "JP",
                "name_native": "日本語",
                "name_english": "Japanese",
                "key": "ja_jp"
            },
            "dataset": dataset_name,
            "custom_phonemes": True
        }
        
        # Write to file
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
```

**Rationale**:
- ✅ Explicit phoneme mapping (no espeak-ng guessing)
- ✅ Preserves Piper audio parameters (compatibility)
- ✅ Documents custom phoneme system
- ✅ Reproducible configuration
- ✅ Self-contained (no external dependencies)

---

### 3. Dataset Format Transformation: metadata_phonemes.csv → dataset.jsonl

**Decision**: Transform CSV to JSONL with audio metadata enrichment.

**Input Format** (metadata_phonemes.csv from Phase 3):
```csv
jsut_basic5000_0001|こんにちは、今日はいい天気ですね。|0 12 23 45 67 89 12 34 56 78 90
jsut_basic5000_0002|音声認識の実験を行いました。|12 34 56 78 90 12 34 56 78 90 12
```

**Output Format** (dataset.jsonl for Piper training):
```jsonl
{"audio_file":"jsut_basic5000_0001.wav","phoneme_ids":[0,12,23,45,67,89,12,34,56,78,90],"speaker_id":0,"text":"こんにちは、今日はいい天気ですね。","audio_norm_path":"jsut_basic5000_0001_norm.wav"}
{"audio_file":"jsut_basic5000_0002.wav","phoneme_ids":[12,34,56,78,90,12,34,56,78,90,12],"speaker_id":0,"text":"音声認識の実験を行いました。","audio_norm_path":"jsut_basic5000_0002_norm.wav"}
```

**Transformation Logic** (`infrastructure/piper/preprocessor_adapter.py`):
```python
import json
from pathlib import Path
from typing import List, Dict, Any
from piper_voice.core.ports import PiperTrainingPort
from piper_voice.core.entities import PhonemeMap

class PiperPreprocessorAdapter:
    """Adapter for Piper preprocessing operations."""
    
    def transform_metadata_to_jsonl(
        self,
        metadata_phonemes_path: Path,
        output_jsonl_path: Path,
        audio_dir: Path,
        speaker_id: int = 0
    ) -> int:
        """Transform metadata_phonemes.csv to dataset.jsonl.
        
        Args:
            metadata_phonemes_path: Input CSV file
            output_jsonl_path: Output JSONL file
            audio_dir: Directory containing WAV files
            speaker_id: Speaker ID (single-speaker = 0)
            
        Returns:
            Number of entries processed
            
        Raises:
            FileNotFoundError: If metadata file or audio files missing
            ValueError: If metadata format invalid
        """
        if not metadata_phonemes_path.exists():
            raise FileNotFoundError(f"Metadata file not found: {metadata_phonemes_path}")
        
        if not audio_dir.exists():
            raise FileNotFoundError(f"Audio directory not found: {audio_dir}")
        
        entries_processed = 0
        
        with open(metadata_phonemes_path, "r", encoding="utf-8") as infile, \
             open(output_jsonl_path, "w", encoding="utf-8") as outfile:
            
            for line_num, line in enumerate(infile, 1):
                line = line.strip()
                if not line:
                    continue
                
                # Parse CSV line (filename|text|phoneme_ids)
                parts = line.split("|")
                if len(parts) != 3:
                    raise ValueError(
                        f"Invalid metadata format at line {line_num}: "
                        f"expected 3 fields, got {len(parts)}"
                    )
                
                filename_base, text, phoneme_ids_str = parts
                
                # Validate audio file exists
                audio_file = f"{filename_base}.wav"
                audio_path = audio_dir / audio_file
                if not audio_path.exists():
                    raise FileNotFoundError(
                        f"Audio file not found: {audio_path} (line {line_num})"
                    )
                
                # Parse phoneme IDs
                try:
                    phoneme_ids = [int(x) for x in phoneme_ids_str.split()]
                except ValueError as e:
                    raise ValueError(
                        f"Invalid phoneme IDs at line {line_num}: {phoneme_ids_str}"
                    ) from e
                
                # Create JSONL entry
                entry = {
                    "audio_file": audio_file,
                    "phoneme_ids": phoneme_ids,
                    "speaker_id": speaker_id,
                    "text": text,
                    "audio_norm_path": f"{filename_base}_norm.wav"
                }
                
                outfile.write(json.dumps(entry, ensure_ascii=False) + "\n")
                entries_processed += 1
        
        return entries_processed
```

**Rationale**:
- ✅ Preserves all phoneme information
- ✅ Adds audio metadata (file paths, speaker ID)
- ✅ Line-by-line processing (memory efficient)
- ✅ Validation during transformation (fail-fast)
- ✅ JSONL format (standard for Piper training)

---

### 4. Audio Normalization Statistics: Calculate Before Training

**Decision**: Calculate audio statistics during preprocessing, save for training.

**Audio Statistics Required**:
- Mean amplitude across all audio files
- Standard deviation of amplitudes
- Min/max values for normalization
- Duration statistics

**Statistics Calculation** (`infrastructure/piper/audio_stats.py`):
```python
import json
import numpy as np
import librosa
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass

@dataclass
class AudioStatistics:
    """Audio normalization statistics for training."""
    mean: float
    std: float
    min_val: float
    max_val: float
    total_duration: float
    num_samples: int
    sample_rate: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "mean": float(self.mean),
            "std": float(self.std),
            "min": float(self.min_val),
            "max": float(self.max_val),
            "total_duration_seconds": float(self.total_duration),
            "num_audio_files": self.num_samples,
            "sample_rate": self.sample_rate
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AudioStatistics":
        """Create from dictionary."""
        return cls(
            mean=data["mean"],
            std=data["std"],
            min_val=data["min"],
            max_val=data["max"],
            total_duration=data["total_duration_seconds"],
            num_samples=data["num_audio_files"],
            sample_rate=data["sample_rate"]
        )

class AudioStatsCalculator:
    """Calculate audio normalization statistics."""
    
    def calculate_stats(
        self,
        audio_files: List[Path],
        sample_rate: int = 22050
    ) -> AudioStatistics:
        """Calculate statistics from audio files.
        
        Args:
            audio_files: List of WAV file paths
            sample_rate: Expected sample rate
            
        Returns:
            AudioStatistics with normalization parameters
            
        Raises:
            ValueError: If audio files have wrong sample rate
        """
        if not audio_files:
            raise ValueError("No audio files provided")
        
        all_amplitudes: List[float] = []
        total_duration = 0.0
        
        for audio_path in audio_files:
            # Load audio
            audio, sr = librosa.load(audio_path, sr=None)
            
            # Validate sample rate
            if sr != sample_rate:
                raise ValueError(
                    f"Audio file {audio_path.name} has sample rate {sr}, "
                    f"expected {sample_rate}"
                )
            
            # Collect statistics
            all_amplitudes.extend(audio.tolist())
            total_duration += len(audio) / sr
        
        # Calculate statistics
        amplitudes_array = np.array(all_amplitudes, dtype=np.float32)
        
        return AudioStatistics(
            mean=float(np.mean(amplitudes_array)),
            std=float(np.std(amplitudes_array)),
            min_val=float(np.min(amplitudes_array)),
            max_val=float(np.max(amplitudes_array)),
            total_duration=total_duration,
            num_samples=len(audio_files),
            sample_rate=sample_rate
        )
    
    def save_stats(
        self,
        stats: AudioStatistics,
        output_path: Path
    ) -> None:
        """Save statistics to JSON file.
        
        Args:
            stats: AudioStatistics to save
            output_path: Path to output JSON file
        """
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(stats.to_dict(), f, indent=2)
```

**Rationale**:
- ✅ Precomputed statistics (faster training startup)
- ✅ Consistent normalization across training runs
- ✅ Validates audio format during preprocessing
- ✅ Provides dataset quality metrics
- ✅ Reproducible (deterministic calculation)

---

### 5. Application Orchestration: Complete Preprocessing Pipeline

**Decision**: Application layer orchestrates all preprocessing steps with validation.

**Use Case Implementation** (`piper_voice/application/preprocess_japanese_dataset.py`):
```python
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import logging

from piper_voice.core.entities import PhonemeMap
from piper_voice.core.ports import FileSystemPort
from piper_voice.infrastructure.piper.preprocessor_adapter import PiperPreprocessorAdapter
from piper_voice.infrastructure.piper.config_generator import PiperConfigGenerator
from piper_voice.infrastructure.piper.audio_stats import AudioStatsCalculator, AudioStatistics

@dataclass
class PreprocessingResult:
    """Result of Piper preprocessing."""
    dataset_jsonl_path: Path
    config_path: Path
    audio_stats_path: Path
    num_samples: int
    audio_stats: AudioStatistics
    success: bool
    error: Optional[str] = None

def preprocess_japanese_dataset(
    dataset_dir: Path,
    output_dir: Path,
    phoneme_map_path: Path,
    metadata_phonemes_path: Path,
    sample_rate: int = 22050,
    filesystem: Optional[FileSystemPort] = None,
    logger: Optional[logging.Logger] = None
) -> PreprocessingResult:
    """Preprocess Japanese dataset for Piper training.
    
    Pipeline:
    1. Validate inputs (paths exist, sample rate correct)
    2. Load phoneme map
    3. Transform metadata_phonemes.csv → dataset.jsonl
    4. Calculate audio normalization statistics
    5. Generate Piper config.json
    6. Validate outputs
    
    Args:
        dataset_dir: Directory with wav/ and metadata files
        output_dir: Output directory for training/ artifacts
        phoneme_map_path: Path to phoneme_map.json (from Phase 3)
        metadata_phonemes_path: Path to metadata_phonemes.csv (from Phase 3)
        sample_rate: Expected audio sample rate (22050 Hz)
        filesystem: Optional filesystem adapter for path validation
        logger: Optional logger
        
    Returns:
        PreprocessingResult with paths and statistics
        
    Raises:
        FileNotFoundError: If required input files missing
        ValueError: If preprocessing fails
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    # Phase 1: Validate inputs
    logger.info("Validating input paths...")
    
    if not dataset_dir.exists():
        raise FileNotFoundError(f"Dataset directory not found: {dataset_dir}")
    
    if not phoneme_map_path.exists():
        raise FileNotFoundError(f"Phoneme map not found: {phoneme_map_path}")
    
    if not metadata_phonemes_path.exists():
        raise FileNotFoundError(f"Metadata not found: {metadata_phonemes_path}")
    
    audio_dir = dataset_dir / "wav"
    if not audio_dir.exists():
        raise FileNotFoundError(f"Audio directory not found: {audio_dir}")
    
    # Validate output directory is allowed
    if filesystem and not filesystem.is_path_allowed(output_dir):
        raise PermissionError(f"Output directory not allowed: {output_dir}")
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Phase 2: Load phoneme map
    logger.info(f"Loading phoneme map from {phoneme_map_path}")
    phoneme_map = PhonemeMap.load_from_json(phoneme_map_path)
    logger.info(f"Loaded phoneme map with {len(phoneme_map)} phonemes")
    
    # Phase 3: Transform metadata to JSONL
    logger.info("Transforming metadata to dataset.jsonl...")
    preprocessor = PiperPreprocessorAdapter()
    
    dataset_jsonl_path = output_dir / "dataset.jsonl"
    num_samples = preprocessor.transform_metadata_to_jsonl(
        metadata_phonemes_path=metadata_phonemes_path,
        output_jsonl_path=dataset_jsonl_path,
        audio_dir=audio_dir,
        speaker_id=0
    )
    logger.info(f"Created dataset.jsonl with {num_samples} samples")
    
    # Phase 4: Calculate audio statistics
    logger.info("Calculating audio normalization statistics...")
    audio_files = list(audio_dir.glob("*.wav"))
    
    if len(audio_files) != num_samples:
        logger.warning(
            f"Audio file count mismatch: {len(audio_files)} files, "
            f"{num_samples} metadata entries"
        )
    
    stats_calculator = AudioStatsCalculator()
    audio_stats = stats_calculator.calculate_stats(audio_files, sample_rate)
    
    audio_stats_path = output_dir / "audio_norm_stats.json"
    stats_calculator.save_stats(audio_stats, audio_stats_path)
    logger.info(f"Saved audio statistics to {audio_stats_path}")
    logger.info(
        f"Audio stats: mean={audio_stats.mean:.4f}, std={audio_stats.std:.4f}, "
        f"duration={audio_stats.total_duration:.1f}s"
    )
    
    # Phase 5: Generate Piper config
    logger.info("Generating Piper config.json...")
    config_generator = PiperConfigGenerator()
    config_path = output_dir / "config.json"
    config_generator.generate_config(
        phoneme_map=phoneme_map,
        output_path=config_path,
        dataset_name="jsut_hiragana"
    )
    logger.info(f"Saved config.json to {config_path}")
    
    # Phase 6: Validate outputs
    logger.info("Validating preprocessing outputs...")
    
    required_outputs = [dataset_jsonl_path, config_path, audio_stats_path]
    for output_path in required_outputs:
        if not output_path.exists():
            raise ValueError(f"Expected output not found: {output_path}")
    
    logger.info("Preprocessing complete!")
    
    return PreprocessingResult(
        dataset_jsonl_path=dataset_jsonl_path,
        config_path=config_path,
        audio_stats_path=audio_stats_path,
        num_samples=num_samples,
        audio_stats=audio_stats,
        success=True,
        error=None
    )
```

**Rationale**:
- ✅ Clear pipeline steps with logging
- ✅ Comprehensive validation (inputs and outputs)
- ✅ Error handling with context
- ✅ Testable by mocking adapters
- ✅ Respects DDD boundaries (orchestration in application)
- ✅ Detailed result reporting

---

### 6. Error Handling Strategy: Fail-Fast with Clear Context

**Decision**: Fail immediately on preprocessing errors with detailed error messages.

**Error Categories**:

1. **Input Validation Errors** (Fail-Fast):
   - Missing files (phoneme_map.json, metadata_phonemes.csv, audio files)
   - Invalid paths (outside allowed directories)
   - Wrong audio format (sample rate != 22050 Hz)
   → Raise FileNotFoundError or ValueError immediately

2. **Format Errors** (Fail-Fast):
   - Invalid metadata_phonemes.csv format
   - Malformed phoneme IDs
   - Invalid JSON in phoneme_map
   → Raise ValueError with line number and context

3. **Audio Processing Errors** (Fail-Fast):
   - Cannot load audio file
   - Statistics calculation failure
   - Sample rate mismatch
   → Raise ValueError with file name and reason

4. **Output Errors** (Fail-Fast):
   - Cannot write output files
   - Disk full
   - Permission denied
   → Raise IOError with path and reason

**Error Enhancement Pattern**:
```python
try:
    audio, sr = librosa.load(audio_path, sr=None)
except Exception as e:
    raise ValueError(
        f"Failed to load audio file: {audio_path}\n"
        f"Reason: {type(e).__name__}: {e}\n"
        f"Check: file exists, correct format (WAV 16-bit PCM)"
    ) from e
```

**Rationale**:
- ✅ Clear error messages for debugging
- ✅ No partial preprocessing (all-or-nothing)
- ✅ Fail fast (don't waste time on bad data)
- ✅ Actionable error guidance (what to check)
- ❌ No graceful degradation (unlike Phase 3, where we continued on errors)

**Why Fail-Fast Here?**
- Preprocessing is deterministic (no ambiguity like kanji conversion)
- Bad preprocessing → bad training → wasted hours
- Better to fail now than during training

---

### 7. Security Guardrails: Path Validation and Limits

**Decision**: Strict security validation using existing SafeFileSystem.

**Security Measures**:

1. **Path Validation** (via FileSystemPort):
```python
ALLOWED_DIRECTORIES = [
    Path("./dataset"),
    Path("./training"),
    Path("./models"),
    Path("./logs"),
    Path("./checkpoints")
]

def is_path_allowed(path: Path) -> bool:
    """Check if path is within allowed directories."""
    abs_path = path.resolve()
    for allowed_dir in ALLOWED_DIRECTORIES:
        allowed_abs = allowed_dir.resolve()
        if abs_path == allowed_abs or allowed_abs in abs_path.parents:
            return True
    return False
```

2. **Read-Only Source Protection**:
```python
# NEVER modify dataset/raw/ (permanent backups)
# ONLY read from dataset/wav/ and dataset/metadata_phonemes.csv
# ONLY write to training/

def validate_output_path(output_path: Path) -> None:
    """Ensure output path is not in read-only directories."""
    read_only_dirs = [Path("./dataset/raw")]
    
    for readonly in read_only_dirs:
        if readonly.resolve() in output_path.resolve().parents:
            raise PermissionError(
                f"Cannot write to read-only directory: {output_path}"
            )
```

3. **File Size Limits**:
```python
MAX_AUDIO_FILE_SIZE = 5 * 1024 * 1024  # 5 MB per audio file
MAX_TOTAL_DATASET_SIZE = 10 * 1024 * 1024 * 1024  # 10 GB total

def validate_audio_file(audio_path: Path) -> None:
    """Validate audio file size."""
    file_size = audio_path.stat().st_size
    if file_size > MAX_AUDIO_FILE_SIZE:
        raise ValueError(
            f"Audio file too large: {audio_path.name} "
            f"({file_size / 1024 / 1024:.1f} MB > 5 MB limit)"
        )
```

4. **Subprocess Timeout** (if using subprocess):
```python
PREPROCESSING_TIMEOUT = 1800  # 30 minutes max

subprocess.run(
    preprocess_command,
    check=True,
    timeout=PREPROCESSING_TIMEOUT
)
```

**Rationale**:
- ✅ Prevents path traversal attacks
- ✅ Protects source audio files
- ✅ Prevents disk exhaustion
- ✅ Prevents runaway processes
- ✅ Consistent with project security policy (CLAUDE.md)

---

### 8. Testing Strategy: Multi-Layer TDD with Piper Mocking

**Decision**: Test each layer independently, mock Piper dependencies.

**Unit Tests** (Infrastructure Adapters):

```python
# tests/unit/test_piper_config_generator.py
def test_config_generator_creates_valid_config():
    """Test config generator produces valid Piper config."""
    phoneme_map = PhonemeMap()
    phoneme_map.add_phoneme("あ")
    phoneme_map.add_phoneme("い")
    
    generator = PiperConfigGenerator()
    output_path = tmp_path / "config.json"
    
    generator.generate_config(phoneme_map, output_path)
    
    # Verify file exists
    assert output_path.exists()
    
    # Verify valid JSON
    with open(output_path) as f:
        config = json.load(f)
    
    # Verify required fields
    assert config["num_symbols"] == 2
    assert config["phoneme_id_map"]["あ"] == 0
    assert config["phoneme_id_map"]["い"] == 1
    assert config["audio"]["sample_rate"] == 22050
    assert config["custom_phonemes"] is True

def test_config_generator_rejects_empty_phoneme_map():
    """Test config generator fails on empty phoneme map."""
    empty_map = PhonemeMap()
    generator = PiperConfigGenerator()
    
    with pytest.raises(ValueError, match="empty phoneme map"):
        generator.generate_config(empty_map, Path("config.json"))

# tests/unit/test_audio_stats_calculator.py
def test_audio_stats_calculator_computes_statistics(tmp_path):
    """Test audio statistics calculation."""
    # Create test audio files
    audio1 = np.random.randn(22050) * 0.5  # 1 second, range ~[-1.5, 1.5]
    audio2 = np.random.randn(22050) * 0.5
    
    audio1_path = tmp_path / "audio1.wav"
    audio2_path = tmp_path / "audio2.wav"
    
    sf.write(audio1_path, audio1, 22050)
    sf.write(audio2_path, audio2, 22050)
    
    # Calculate stats
    calculator = AudioStatsCalculator()
    stats = calculator.calculate_stats([audio1_path, audio2_path])
    
    # Verify statistics
    assert stats.num_samples == 2
    assert stats.sample_rate == 22050
    assert stats.total_duration == pytest.approx(2.0, abs=0.1)
    assert -0.1 < stats.mean < 0.1  # Near zero for random noise
    assert 0.4 < stats.std < 0.6  # Expected std ~0.5

def test_audio_stats_rejects_wrong_sample_rate(tmp_path):
    """Test audio stats fails on wrong sample rate."""
    audio = np.random.randn(16000)
    audio_path = tmp_path / "audio_16k.wav"
    sf.write(audio_path, audio, 16000)  # Wrong sample rate
    
    calculator = AudioStatsCalculator()
    
    with pytest.raises(ValueError, match="sample rate 16000, expected 22050"):
        calculator.calculate_stats([audio_path], sample_rate=22050)

# tests/unit/test_preprocessor_adapter.py
def test_preprocessor_transforms_metadata_to_jsonl(tmp_path):
    """Test metadata transformation to JSONL."""
    # Create test metadata
    metadata_path = tmp_path / "metadata_phonemes.csv"
    with open(metadata_path, "w", encoding="utf-8") as f:
        f.write("file1|こんにちは|0 1 2 3 4\n")
        f.write("file2|ありがとう|5 6 7 8 9\n")
    
    # Create test audio files
    audio_dir = tmp_path / "wav"
    audio_dir.mkdir()
    
    for filename in ["file1.wav", "file2.wav"]:
        audio_path = audio_dir / filename
        audio = np.zeros(22050)
        sf.write(audio_path, audio, 22050)
    
    # Transform
    adapter = PiperPreprocessorAdapter()
    output_path = tmp_path / "dataset.jsonl"
    
    num_samples = adapter.transform_metadata_to_jsonl(
        metadata_phonemes_path=metadata_path,
        output_jsonl_path=output_path,
        audio_dir=audio_dir
    )
    
    assert num_samples == 2
    assert output_path.exists()
    
    # Verify JSONL content
    with open(output_path) as f:
        lines = f.readlines()
    
    assert len(lines) == 2
    
    entry1 = json.loads(lines[0])
    assert entry1["audio_file"] == "file1.wav"
    assert entry1["phoneme_ids"] == [0, 1, 2, 3, 4]
    assert entry1["text"] == "こんにちは"
    assert entry1["speaker_id"] == 0

def test_preprocessor_fails_on_missing_audio_file(tmp_path):
    """Test preprocessor fails when audio file missing."""
    metadata_path = tmp_path / "metadata_phonemes.csv"
    with open(metadata_path, "w", encoding="utf-8") as f:
        f.write("file1|こんにちは|0 1 2 3 4\n")
    
    audio_dir = tmp_path / "wav"
    audio_dir.mkdir()
    # Don't create file1.wav (intentional)
    
    adapter = PiperPreprocessorAdapter()
    output_path = tmp_path / "dataset.jsonl"
    
    with pytest.raises(FileNotFoundError, match="Audio file not found.*file1.wav"):
        adapter.transform_metadata_to_jsonl(
            metadata_phonemes_path=metadata_path,
            output_jsonl_path=output_path,
            audio_dir=audio_dir
        )
```

**Integration Tests** (Full Pipeline):

```python
# tests/integration/test_preprocess_japanese_pipeline.py
@pytest.fixture
def mock_dataset(tmp_path):
    """Create mock Japanese dataset for testing."""
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir()
    
    # Create wav directory with audio files
    wav_dir = dataset_dir / "wav"
    wav_dir.mkdir()
    
    for i in range(3):
        audio_path = wav_dir / f"file{i}.wav"
        audio = np.random.randn(22050) * 0.5
        sf.write(audio_path, audio, 22050)
    
    # Create metadata_phonemes.csv
    metadata_path = dataset_dir / "metadata_phonemes.csv"
    with open(metadata_path, "w", encoding="utf-8") as f:
        f.write("file0|こんにちは|0 1 2 3 4\n")
        f.write("file1|ありがとう|5 6 7 8 9\n")
        f.write("file2|さようなら|10 11 12 13 14\n")
    
    # Create phoneme_map.json
    phoneme_map = PhonemeMap()
    for char in "こんにちはありがとうさようなら":
        phoneme_map.add_phoneme(char)
    
    phoneme_map_path = dataset_dir / "phoneme_map.json"
    phoneme_map.save_to_json(phoneme_map_path)
    
    return dataset_dir

def test_full_preprocessing_pipeline(mock_dataset, tmp_path):
    """Test complete preprocessing pipeline end-to-end."""
    output_dir = tmp_path / "training"
    
    result = preprocess_japanese_dataset(
        dataset_dir=mock_dataset,
        output_dir=output_dir,
        phoneme_map_path=mock_dataset / "phoneme_map.json",
        metadata_phonemes_path=mock_dataset / "metadata_phonemes.csv",
        sample_rate=22050
    )
    
    # Verify success
    assert result.success is True
    assert result.error is None
    assert result.num_samples == 3
    
    # Verify outputs exist
    assert result.dataset_jsonl_path.exists()
    assert result.config_path.exists()
    assert result.audio_stats_path.exists()
    
    # Verify dataset.jsonl content
    with open(result.dataset_jsonl_path) as f:
        lines = f.readlines()
    assert len(lines) == 3
    
    for line in lines:
        entry = json.loads(line)
        assert "audio_file" in entry
        assert "phoneme_ids" in entry
        assert "text" in entry
        assert entry["speaker_id"] == 0
    
    # Verify config.json content
    with open(result.config_path) as f:
        config = json.load(f)
    
    assert config["num_symbols"] == 14  # Unique hiragana in dataset
    assert config["custom_phonemes"] is True
    assert config["audio"]["sample_rate"] == 22050
    assert "phoneme_id_map" in config
    
    # Verify audio_norm_stats.json
    with open(result.audio_stats_path) as f:
        stats = json.load(f)
    
    assert stats["num_audio_files"] == 3
    assert stats["sample_rate"] == 22050
    assert "mean" in stats
    assert "std" in stats

def test_preprocessing_fails_on_missing_phoneme_map(mock_dataset, tmp_path):
    """Test preprocessing fails gracefully when phoneme_map missing."""
    output_dir = tmp_path / "training"
    
    # Delete phoneme map
    (mock_dataset / "phoneme_map.json").unlink()
    
    with pytest.raises(FileNotFoundError, match="Phoneme map not found"):
        preprocess_japanese_dataset(
            dataset_dir=mock_dataset,
            output_dir=output_dir,
            phoneme_map_path=mock_dataset / "phoneme_map.json",
            metadata_phonemes_path=mock_dataset / "metadata_phonemes.csv"
        )

def test_preprocessing_validates_audio_sample_rate(mock_dataset, tmp_path):
    """Test preprocessing detects wrong audio sample rate."""
    # Create audio file with wrong sample rate
    wav_dir = mock_dataset / "wav"
    bad_audio_path = wav_dir / "file_bad.wav"
    audio = np.zeros(16000)
    sf.write(bad_audio_path, audio, 16000)  # Wrong: 16kHz instead of 22.05kHz
    
    # Add to metadata
    metadata_path = mock_dataset / "metadata_phonemes.csv"
    with open(metadata_path, "a", encoding="utf-8") as f:
        f.write("file_bad|テスト|0 1 2\n")
    
    output_dir = tmp_path / "training"
    
    with pytest.raises(ValueError, match="sample rate 16000, expected 22050"):
        preprocess_japanese_dataset(
            dataset_dir=mock_dataset,
            output_dir=output_dir,
            phoneme_map_path=mock_dataset / "phoneme_map.json",
            metadata_phonemes_path=mock_dataset / "metadata_phonemes.csv"
        )
```

**Validation Tests** (Output Format Compliance):

```python
# tests/validation/test_piper_format_compliance.py
def test_dataset_jsonl_is_valid_jsonl(preprocessing_output):
    """Test dataset.jsonl is valid line-delimited JSON."""
    with open(preprocessing_output.dataset_jsonl_path) as f:
        for line_num, line in enumerate(f, 1):
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON at line {line_num}: {e}")
            
            # Verify required fields
            required_fields = ["audio_file", "phoneme_ids", "speaker_id", "text"]
            for field in required_fields:
                assert field in entry, f"Missing field '{field}' at line {line_num}"

def test_config_json_matches_piper_schema(preprocessing_output):
    """Test config.json matches Piper expected schema."""
    with open(preprocessing_output.config_path) as f:
        config = json.load(f)
    
    # Required top-level fields
    assert "audio" in config
    assert "phoneme_id_map" in config
    assert "num_symbols" in config
    
    # Audio config
    assert config["audio"]["sample_rate"] == 22050
    assert "filter_length" in config["audio"]
    assert "hop_length" in config["audio"]
    
    # Phoneme map
    assert isinstance(config["phoneme_id_map"], dict)
    assert len(config["phoneme_id_map"]) == config["num_symbols"]
    
    # All phoneme IDs should be sequential integers starting from 0
    phoneme_ids = sorted(config["phoneme_id_map"].values())
    assert phoneme_ids == list(range(len(phoneme_ids)))

def test_preprocessing_is_deterministic(mock_dataset, tmp_path):
    """Test preprocessing produces identical results on repeated runs."""
    output_dir1 = tmp_path / "training1"
    output_dir2 = tmp_path / "training2"
    
    result1 = preprocess_japanese_dataset(
        dataset_dir=mock_dataset,
        output_dir=output_dir1,
        phoneme_map_path=mock_dataset / "phoneme_map.json",
        metadata_phonemes_path=mock_dataset / "metadata_phonemes.csv"
    )
    
    result2 = preprocess_japanese_dataset(
        dataset_dir=mock_dataset,
        output_dir=output_dir2,
        phoneme_map_path=mock_dataset / "phoneme_map.json",
        metadata_phonemes_path=mock_dataset / "metadata_phonemes.csv"
    )
    
    # Compare dataset.jsonl (should be identical)
    with open(result1.dataset_jsonl_path) as f1, \
         open(result2.dataset_jsonl_path) as f2:
        assert f1.read() == f2.read()
    
    # Compare config.json (should be identical)
    with open(result1.config_path) as f1, \
         open(result2.config_path) as f2:
        config1 = json.load(f1)
        config2 = json.load(f2)
        assert config1 == config2
```

**Test Coverage Requirements**:
- Config generator: 100% coverage (critical for training)
- Audio stats calculator: 95% coverage (handles external audio files)
- Preprocessor adapter: 95% coverage (transformation logic)
- Application use case: 90% coverage (orchestration)

---

### 9. DDD Architecture Compliance: Clear Layer Boundaries

**Decision**: Strict adherence to DDD layers with no cross-contamination.

**Layer Responsibilities**:

**Domain Layer** (`piper_voice/core/`):
- Contains: PhonemeMap entity (already exists from Phase 3)
- New entities: None needed (preprocessing is infrastructure concern)
- Ports: PiperTrainingPort already defined
- **NO imports from**: infrastructure, application, external libraries

**Infrastructure Layer** (`piper_voice/infrastructure/piper/`):
- Contains: PiperPreprocessorAdapter, PiperConfigGenerator, AudioStatsCalculator
- Implements: PiperTrainingPort (preprocess_dataset method)
- **CAN import**: librosa, numpy, piper_train (if using Python API)
- **CANNOT import**: application layer

**Application Layer** (`piper_voice/application/`):
- Contains: preprocess_japanese_dataset use case
- Orchestrates: infrastructure adapters
- **CAN import**: core (entities, ports), infrastructure (adapters)
- **CANNOT**: contain business logic or I/O operations

**Dependency Flow**:
```
Application → Infrastructure → Domain
     ↓              ↓
   Ports ←--------─┘
```

**Example - CORRECT Architecture**:
```python
# piper_voice/application/preprocess_japanese_dataset.py
from piper_voice.core.entities import PhonemeMap  # ✅ Domain import
from piper_voice.core.ports import PiperTrainingPort  # ✅ Port import
from piper_voice.infrastructure.piper.preprocessor_adapter import PiperPreprocessorAdapter  # ✅ Adapter import

def preprocess_japanese_dataset(...):
    phoneme_map = PhonemeMap.load_from_json(...)  # ✅ Domain entity
    adapter = PiperPreprocessorAdapter()  # ✅ Infrastructure adapter
    adapter.transform_metadata_to_jsonl(...)  # ✅ Adapter method
```

**Example - INCORRECT Architecture**:
```python
# piper_voice/core/entities.py
import librosa  # ❌ FORBIDDEN: domain depends on infrastructure
import subprocess  # ❌ FORBIDDEN: domain depends on OS

class PhonemeMap:
    def preprocess_audio(self, audio_path):  # ❌ FORBIDDEN: audio processing in domain
        audio, sr = librosa.load(audio_path)  # ❌ FORBIDDEN
```

**Rationale**:
- ✅ Domain remains pure (testable without external dependencies)
- ✅ Infrastructure is swappable (can replace piper_train)
- ✅ Clear separation of concerns
- ✅ Follows ADR-001 DDD architecture
- ✅ Maintainable and extensible

---

## Implementation Plan

### Phase 4a: Infrastructure Layer (TDD FIRST)

**Day 1: Config Generation**
1. Write tests for PiperConfigGenerator
   - `tests/unit/test_piper_config_generator.py`
   - Run tests → FAIL (not implemented)
2. Implement PiperConfigGenerator
   - `piper_voice/infrastructure/piper/config_generator.py`
   - Run tests → PASS

**Day 2: Audio Statistics**
1. Write tests for AudioStatsCalculator
   - `tests/unit/test_audio_stats_calculator.py`
   - Run tests → FAIL (not implemented)
2. Implement AudioStatsCalculator
   - `piper_voice/infrastructure/piper/audio_stats.py`
   - Run tests → PASS

**Day 3: Preprocessor Adapter**
1. Write tests for PiperPreprocessorAdapter
   - `tests/unit/test_preprocessor_adapter.py`
   - Run tests → FAIL (not implemented)
2. Implement PiperPreprocessorAdapter
   - `piper_voice/infrastructure/piper/preprocessor_adapter.py`
   - Run tests → PASS

### Phase 4b: Application Layer (TDD FIRST)

**Day 4: Preprocessing Use Case**
1. Write integration tests
   - `tests/integration/test_preprocess_japanese_pipeline.py`
   - Run tests → FAIL (not implemented)
2. Implement use case
   - `piper_voice/application/preprocess_japanese_dataset.py`
   - Run tests → PASS

### Phase 4c: Validation and CLI (TDD FIRST)

**Day 5: Format Validation**
1. Write validation tests
   - `tests/validation/test_piper_format_compliance.py`
   - Run tests → FAIL
2. Fix any format issues
   - Run tests → PASS
3. Add CLI script
   - `scripts/preprocess_dataset.py`

### Phase 4d: Real Dataset Testing

**Day 6: JSUT Integration**
1. Run on real JSUT dataset (7,300 samples)
2. Verify all outputs generated correctly
3. Validate preprocessing completes in <30 minutes
4. Generate preprocessing report
5. Fix any edge cases discovered

**Deliverables**:
- [ ] PiperConfigGenerator with tests (100% coverage)
- [ ] AudioStatsCalculator with tests (95% coverage)
- [ ] PiperPreprocessorAdapter with tests (95% coverage)
- [ ] preprocess_japanese_dataset use case with tests (90% coverage)
- [ ] Validation tests for Piper format compliance
- [ ] CLI script (`scripts/preprocess_dataset.py`)
- [ ] training/dataset.jsonl (7,300 entries)
- [ ] training/config.json (custom Japanese phoneme map)
- [ ] training/audio_norm_stats.json
- [ ] Preprocessing validation report

---

## Consequences

### Positive

✅ **Piper Compatibility**: Custom phonemes integrated with Piper training pipeline
✅ **Deterministic Output**: Reproducible preprocessing results
✅ **DDD Compliance**: Clean architecture with clear boundaries
✅ **Testability**: Each component testable in isolation
✅ **Validation**: Comprehensive format compliance checks
✅ **Security**: Path validation and read-only source protection
✅ **Error Transparency**: Clear error messages with context
✅ **Performance**: Efficient line-by-line processing

### Negative

❌ **Piper Dependency**: Requires piper_train as dependency (or complex subprocess wrapper)
❌ **Piper API Stability**: May break if Piper internal API changes
❌ **Complexity**: More code than simple preprocessing script
❌ **Configuration Coupling**: Must match Piper's expected config schema

### Risks

1. **Piper API Changes**: Piper preprocessing API may change in future versions
   - **Mitigation**: Pin piper_train version, fallback to subprocess if API breaks

2. **Config Schema Mismatch**: Our config.json may not match Piper training expectations
   - **Mitigation**: Validation tests against real Piper training, refer to Piper TRAINING.md

3. **Performance Bottleneck**: Audio statistics calculation may be slow for large datasets
   - **Mitigation**: Progress tracking, parallel processing if needed (future optimization)

4. **Memory Usage**: Loading all audio for statistics may exhaust memory
   - **Mitigation**: Streaming calculation, process in batches if needed

---

## Validation Criteria (From STORY-004)

This architecture must satisfy all STORY-004 acceptance criteria:

- [ ] All three output files (dataset.jsonl, audio_norm_stats.json, config.json) generated
- [ ] Every audio file in metadata_phonemes.csv appears in dataset.jsonl
- [ ] Every phoneme ID in dataset exists in phoneme mapping (config.json)
- [ ] dataset.jsonl follows line-delimited JSON format
- [ ] config.json contains complete Japanese phoneme mapping from phoneme_map.json
- [ ] All audio files are 22050 Hz sample rate
- [ ] Audio normalization statistics are mathematically valid
- [ ] Running preprocessing twice produces identical output (determinism)
- [ ] Processing completes in reasonable time (<30 minutes for 7,300 samples)

---

## References

- [STORY-004: Piper Preprocessing Integration](../stories/STORY-004-piper-preprocessing-integration.md)
- [ADR-001: Japanese Voice Architecture](ADR-001-japanese-voice-architecture.md)
- [ADR-003: Japanese Phonetization Implementation](ADR-003-japanese-phonetization-implementation.md)
- [Piper TRAINING.md](https://github.com/rhasspy/piper/blob/master/TRAINING.md)
- [Piper Training Documentation](https://github.com/rhasspy/piper/tree/master/src/python)
- CLAUDE.md: Project rules and principles (TDD, DDD, security)

---

**This ADR is the architectural authority for Piper preprocessing integration.**
All code must follow these decisions. TDD is mandatory. DDD boundaries are non-negotiable. Security validation is required. Configuration must be compatible with Piper training pipeline.
