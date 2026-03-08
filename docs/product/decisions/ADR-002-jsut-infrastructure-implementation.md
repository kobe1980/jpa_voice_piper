# ADR-002: JSUT Corpus Infrastructure Implementation

**Status**: ACCEPTED
**Date**: 2026-03-08
**Deciders**: Architect
**Related**: STORY-002-jsut-corpus-infrastructure.md, ADR-001-japanese-voice-architecture.md

---

## Context

STORY-002 requires automated infrastructure to download, validate, and prepare the JSUT corpus (7,300 utterances, ~10 hours) for Piper training. This infrastructure must:

1. Download 5GB corpus from University of Tokyo source
2. Parse non-standard JSUT transcript format (`AUDIO_ID:transcript_text`)
3. Resample audio from 48kHz to 22050Hz
4. Normalize audio to strict quality standards (SNR ≥ 30dB, no clipping)
5. Generate LJSPEECH-format metadata.csv
6. Respect DDD boundaries and security guardrails
7. Support TDD with testable components

**Key Constraints**:
- Must respect `piper_voice/core/` isolation (no infrastructure dependencies)
- Must enforce filesystem security (only `./dataset`, `./training`, etc.)
- Must handle partial failures gracefully
- Must be testable without downloading full corpus
- Must log all operations for debugging

---

## Decision

### 1. Download Mechanism: `requests` + Streaming

**Decision**: Use Python `requests` library with streaming download.

**Rationale**:
- ✅ Built-in progress tracking via `Content-Length` header
- ✅ Supports resume on connection failure (Range header)
- ✅ Better error handling than `urllib`
- ✅ Clean API for chunk-based processing
- ✅ Standard in Python ecosystem

**Alternatives Considered**:
- ❌ `curl` via subprocess: harder to test, less portable, no Python error handling
- ❌ `urllib`: lower-level API, no built-in progress, more complex

**Implementation**:
```python
import requests
from tqdm import tqdm

def download_jsut_corpus(url: str, output_path: Path) -> None:
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    
    with open(output_path, 'wb') as f:
        with tqdm(total=total_size, unit='B', unit_scale=True) as pbar:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                pbar.update(len(chunk))
```

**Error Handling**:
- Network timeout: 30 seconds per chunk
- Retry logic: 3 attempts with exponential backoff
- Checksum validation: Compare file size with expected value
- Partial download: Delete incomplete file, restart from beginning

---

### 2. Audio Processing Library: `librosa` + `soundfile`

**Decision**: Use `librosa` for resampling/analysis, `soundfile` for I/O.

**Rationale**:
- ✅ `librosa`: Industry-standard for audio ML, excellent resampling quality
- ✅ `soundfile`: Fast WAV I/O, handles 16-bit PCM perfectly
- ✅ Already in project dependencies (see `pyproject.toml`)
- ✅ Well-documented, widely tested
- ✅ Supports all required operations: resample, trim silence, normalize volume

**Alternatives Considered**:
- ❌ `pydub`: Heavier (depends on ffmpeg), less precise for ML use cases
- ❌ `sox` via CLI: Not cross-platform (requires system install), harder to test

**Implementation** (`infrastructure/audio/processor.py`):
```python
import librosa
import soundfile as sf
import numpy as np

class LibrosaAudioProcessor:
    def normalize_audio(
        self, 
        input_path: Path, 
        output_path: Path,
        target_sample_rate: int = 22050
    ) -> None:
        # Load audio
        audio, sr = librosa.load(input_path, sr=None, mono=True)
        
        # Resample
        if sr != target_sample_rate:
            audio = librosa.resample(audio, orig_sr=sr, target_sr=target_sample_rate)
        
        # Trim silence (top_db=30 → 30dB threshold)
        audio, _ = librosa.effects.trim(audio, top_db=30)
        
        # Normalize volume to -3dB peak
        peak = np.abs(audio).max()
        if peak > 0:
            audio = audio / peak * 0.707  # -3dB in linear
        
        # Save as 16-bit PCM WAV
        sf.write(output_path, audio, target_sample_rate, subtype='PCM_16')
```

**Quality Validation** (`analyze_quality` method):
```python
def analyze_quality(self, file_path: Path) -> AudioQuality:
    audio, sr = librosa.load(file_path, sr=None, mono=True)
    
    # SNR calculation (signal power / noise floor estimate)
    signal_power = np.mean(audio ** 2)
    noise_floor = np.percentile(np.abs(audio), 5) ** 2  # Bottom 5%
    snr_db = 10 * np.log10(signal_power / noise_floor)
    
    # Clipping detection
    max_amplitude = np.abs(audio).max()
    has_clipping = max_amplitude >= 0.95
    
    # Duration
    duration_sec = len(audio) / sr
    
    # Silence detection (start/end)
    silence_threshold = 0.01  # 1% of max amplitude
    start_silence = _count_leading_silence(audio, silence_threshold) / sr
    end_silence = _count_trailing_silence(audio, silence_threshold) / sr
    
    return AudioQuality(
        snr_db=snr_db,
        has_clipping=has_clipping,
        duration_seconds=duration_sec,
        silence_start_sec=start_silence,
        silence_end_sec=end_silence,
        sample_rate=sr,
    )
```

---

### 3. JSUT Structure Parsing: Recursive Directory Walker

**Decision**: Implement JSUT-specific parser that walks directory tree and finds `transcript_utf8.txt` files.

**JSUT Corpus Structure**:
```
jsut_ver1.1/
├── basic5000/
│   ├── wav/
│   │   ├── BASIC5000_0001.wav
│   │   └── ...
│   └── transcript_utf8.txt
├── onomatopoeia300/
│   ├── wav/
│   │   ├── ONOMATOPOEIA300_001.wav
│   │   └── ...
│   └── transcript_utf8.txt
└── ... (10 more subfolders)
```

**Transcript Format** (`transcript_utf8.txt`):
```
BASIC5000_0001:こんにちは、これはテストです。
BASIC5000_0002:今日はいい天気ですね。
```

**Implementation** (`infrastructure/filesystem/jsut_loader.py`):
```python
from pathlib import Path
from typing import Iterator

class JsutCorpusLoader:
    """Loader for JSUT corpus structure."""
    
    def find_transcript_files(self, jsut_root: Path) -> list[Path]:
        """Find all transcript_utf8.txt files recursively."""
        return list(jsut_root.rglob("transcript_utf8.txt"))
    
    def parse_transcript_file(self, transcript_path: Path) -> Iterator[tuple[str, str]]:
        """Parse single transcript file.
        
        Yields:
            (audio_id, transcript_text) tuples
        """
        with open(transcript_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if ':' not in line:
                    continue  # Skip malformed lines
                
                audio_id, text = line.split(':', 1)
                yield (audio_id.strip(), text.strip())
    
    def load_all_transcripts(self, jsut_root: Path) -> list[tuple[Path, str]]:
        """Load all audio-transcript pairs from JSUT corpus.
        
        Returns:
            List of (audio_file_path, transcript) tuples
        """
        results = []
        
        for transcript_file in self.find_transcript_files(jsut_root):
            wav_dir = transcript_file.parent / "wav"
            
            for audio_id, text in self.parse_transcript_file(transcript_file):
                audio_path = wav_dir / f"{audio_id}.wav"
                
                if not audio_path.exists():
                    # Log warning but continue
                    print(f"Warning: Missing audio file {audio_path}")
                    continue
                
                results.append((audio_path, text))
        
        return results
```

**Validation**:
- Check expected folder count (should be ~10 subfolders)
- Verify total utterance count (~7,300 files)
- Report missing audio files
- Validate UTF-8 encoding of transcripts

---

### 4. Metadata Format: LJSPEECH with Japanese Extensions

**Decision**: Generate standard LJSPEECH `metadata.csv` with format:
```
filename|transcript
jsut_basic5000_0001|こんにちは、これはテストです。
jsut_basic5000_0002|今日はいい天気ですね。
```

**LJSPEECH Format Specification**:
- File: `metadata.csv` (pipe-separated, no header)
- Column 1: Filename WITHOUT `.wav` extension
- Column 2: Raw transcript text (UTF-8 encoded)
- Encoding: UTF-8 BOM-free
- Line ending: Unix LF (`\n`)

**Filename Normalization**:
```python
def normalize_filename(jsut_audio_id: str) -> str:
    """Convert JSUT audio ID to normalized filename.
    
    BASIC5000_0001 → jsut_basic5000_0001
    ONOMATOPOEIA300_042 → jsut_onomatopoeia300_042
    """
    return f"jsut_{jsut_audio_id.lower()}"
```

**Implementation** (`infrastructure/filesystem/metadata_writer.py`):
```python
import csv
from pathlib import Path

class MetadataWriter:
    """Write LJSPEECH-format metadata.csv."""
    
    def save_metadata(
        self, 
        samples: list[tuple[str, str]], 
        output_path: Path
    ) -> None:
        """Save metadata in LJSPEECH format.
        
        Args:
            samples: List of (filename_no_ext, transcript) tuples
            output_path: Path to metadata.csv
        """
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f, delimiter='|', quoting=csv.QUOTE_NONE)
            for filename, transcript in samples:
                writer.writerow([filename, transcript])
```

**Validation Requirements**:
- Row count matches WAV file count
- All filenames reference existing WAV files
- No duplicate filenames
- All transcripts are valid UTF-8
- No empty transcripts

---

### 5. Error Handling: Graceful Degradation + Detailed Logging

**Decision**: Implement multi-level error handling with detailed logs.

**Error Categories**:

1. **Fatal Errors** (stop processing):
   - Download failure (after 3 retries)
   - Corrupt archive
   - Missing JSUT structure (no transcript files found)
   - Filesystem permission denied

2. **Warning Errors** (log and continue):
   - Single audio file missing
   - Single audio file fails quality validation
   - Single normalization fails

3. **Info Logs** (progress tracking):
   - Download progress
   - Processing progress (N/7300 files)
   - Quality validation results

**Implementation** (`infrastructure/logging/preparation_logger.py`):
```python
import logging
from pathlib import Path
from datetime import datetime

class PreparationLogger:
    """Logger for dataset preparation pipeline."""
    
    def __init__(self, log_dir: Path):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"jsut_preparation_{timestamp}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def log_download_start(self, url: str, size_mb: float):
        self.logger.info(f"Downloading JSUT corpus: {url} ({size_mb:.1f} MB)")
    
    def log_processing_progress(self, current: int, total: int):
        percentage = (current / total) * 100
        self.logger.info(f"Processing: {current}/{total} ({percentage:.1f}%)")
    
    def log_quality_failure(self, filename: str, reason: str):
        self.logger.warning(f"Quality check failed for {filename}: {reason}")
    
    def log_summary(self, total: int, passed: int, failed: int):
        self.logger.info(f"Summary: {total} files, {passed} passed, {failed} failed")
```

**Retry Logic**:
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
def download_with_retry(url: str, output_path: Path) -> None:
    """Download with exponential backoff retry."""
    response = requests.get(url, stream=True, timeout=30)
    response.raise_for_status()
    # ... download logic
```

---

### 6. Progress Tracking: TQDM + JSON Report

**Decision**: Use `tqdm` for real-time CLI progress, generate JSON report on completion.

**Real-Time Progress** (CLI):
```python
from tqdm import tqdm

def process_all_audio_files(audio_files: list[Path]) -> None:
    with tqdm(total=len(audio_files), desc="Normalizing audio") as pbar:
        for audio_path in audio_files:
            try:
                normalize_audio(audio_path, output_path)
                pbar.update(1)
            except Exception as e:
                pbar.write(f"Failed: {audio_path.name}: {e}")
```

**Final Report** (`logs/jsut_preparation_report.json`):
```json
{
  "timestamp": "2026-03-08T14:30:00Z",
  "corpus": "JSUT v1.1",
  "total_utterances": 7300,
  "processed_utterances": 7285,
  "failed_utterances": 15,
  "total_duration_hours": 9.8,
  "quality_metrics": {
    "avg_snr_db": 42.3,
    "clipping_count": 0,
    "avg_duration_sec": 4.8
  },
  "failed_files": [
    {"file": "BASIC5000_0042.wav", "reason": "SNR too low (28.5 dB)"},
    {"file": "ONOMATOPOEIA300_013.wav", "reason": "Duration too short (0.8s)"}
  ]
}
```

---

### 7. Testing Strategy: Mock Corpus + Integration Tests

**Decision**: Create minimal mock JSUT corpus for unit tests, use real samples for integration tests.

**Mock Corpus Structure** (`tests/fixtures/mock_jsut/`):
```
mock_jsut/
├── basic5000/
│   ├── wav/
│   │   ├── BASIC5000_0001.wav  # 3-second test audio
│   │   └── BASIC5000_0002.wav
│   └── transcript_utf8.txt
└── onomatopoeia300/
    ├── wav/
    │   └── ONOMATOPOEIA300_001.wav
    └── transcript_utf8.txt
```

**Unit Tests** (Fast, No Network):
```python
# tests/unit/test_jsut_loader.py
def test_parse_transcript_file():
    """Test transcript parsing with mock file."""
    mock_transcript = Path("tests/fixtures/mock_jsut/basic5000/transcript_utf8.txt")
    loader = JsutCorpusLoader()
    
    pairs = list(loader.parse_transcript_file(mock_transcript))
    
    assert len(pairs) == 2
    assert pairs[0] == ("BASIC5000_0001", "こんにちは")

# tests/unit/test_audio_processor.py
def test_normalize_audio_resamples_correctly():
    """Test audio normalization with synthetic audio."""
    # Generate synthetic 48kHz audio
    audio_48k = generate_sine_wave(duration=2.0, sample_rate=48000)
    
    processor = LibrosaAudioProcessor()
    processor.normalize_audio(input_path, output_path, target_sample_rate=22050)
    
    # Verify output
    output_audio, output_sr = librosa.load(output_path, sr=None)
    assert output_sr == 22050
    assert len(output_audio) == int(2.0 * 22050)
```

**Integration Tests** (Slower, Uses Real Samples):
```python
# tests/integration/test_jsut_preparation_pipeline.py
@pytest.mark.integration
def test_full_preparation_pipeline():
    """Test complete JSUT preparation with real samples."""
    # Use 3 real JSUT samples (included in repo as test fixtures)
    jsut_samples = Path("tests/fixtures/jsut_samples/")
    output_dir = tmp_path / "prepared"
    
    # Run full pipeline
    prepare_jsut_dataset(jsut_samples, output_dir)
    
    # Verify outputs
    assert (output_dir / "metadata.csv").exists()
    assert (output_dir / "wav").exists()
    
    metadata = load_metadata(output_dir / "metadata.csv")
    assert len(metadata) == 3
    
    for filename, _ in metadata:
        wav_path = output_dir / "wav" / f"{filename}.wav"
        assert wav_path.exists()
        
        # Validate audio quality
        quality = analyze_quality(wav_path)
        assert quality.snr_db >= 30
        assert not quality.has_clipping
```

**No Full Download in Tests**:
- Unit tests use mock corpus (3 files, included in repo)
- Integration tests use 3 real JSUT samples (120 KB total)
- Full corpus download only in user-initiated commands
- CI/CD tests run in <10 seconds

---

## Infrastructure Adapters to Implement

### Primary Adapters (Week 1 Priority)

1. **`infrastructure/audio/processor.py`**
   - Implements `AudioProcessorPort`
   - Class: `LibrosaAudioProcessor`
   - Methods: `load_audio`, `analyze_quality`, `normalize_audio`
   - Dependencies: librosa, soundfile, numpy

2. **`infrastructure/filesystem/jsut_loader.py`**
   - JSUT-specific corpus loader
   - Class: `JsutCorpusLoader`
   - Methods: `find_transcript_files`, `parse_transcript_file`, `load_all_transcripts`
   - No external dependencies (stdlib only)

3. **`infrastructure/filesystem/safe_fs.py`**
   - Implements `FileSystemPort` with security guardrails
   - Class: `SafeFileSystem`
   - Methods: `is_path_allowed`, `list_audio_files`, `ensure_directory`
   - Enforces allowed paths: `./dataset`, `./training`, `./models`, etc.

4. **`infrastructure/filesystem/metadata_writer.py`**
   - Implements `MetadataRepositoryPort`
   - Class: `LjspeechMetadataWriter`
   - Methods: `save_metadata`, `load_metadata`
   - Handles LJSPEECH CSV format

### Secondary Adapters (Week 1-2)

5. **`infrastructure/download/corpus_downloader.py`**
   - Download and extract JSUT corpus
   - Class: `JsutCorpusDownloader`
   - Methods: `download`, `extract`, `verify_checksum`
   - Dependencies: requests, tqdm, tarfile

6. **`infrastructure/logging/preparation_logger.py`**
   - Structured logging for preparation pipeline
   - Class: `PreparationLogger`
   - Methods: `log_download_start`, `log_processing_progress`, `log_summary`
   - Outputs: CLI logs + JSON report

### Application Layer Orchestration

7. **`application/download_jsut.py`**
   - Use case: Download and verify JSUT corpus
   - Function: `download_jsut_corpus(output_dir: Path) -> None`
   - Coordinates: Downloader + SafeFileSystem + Logger

8. **`application/prepare_jsut_dataset.py`**
   - Use case: Prepare JSUT for Piper training
   - Function: `prepare_jsut_dataset(jsut_dir: Path, output_dir: Path) -> None`
   - Coordinates: JsutLoader + AudioProcessor + MetadataWriter + Logger

---

## Security Guardrails Implementation

### Allowed Paths Enforcement

**`infrastructure/filesystem/safe_fs.py`**:
```python
from pathlib import Path

class SafeFileSystem:
    """Filesystem operations with security guardrails."""
    
    ALLOWED_ROOTS = [
        Path("./dataset"),
        Path("./training"),
        Path("./models"),
        Path("./logs"),
        Path("./checkpoints"),
        Path("./scripts"),
        Path("./piper_voice"),
        Path("./tests"),
        Path("./configs"),
        Path("./docs"),
    ]
    
    def is_path_allowed(self, path: Path) -> bool:
        """Check if path is within allowed directories."""
        path_abs = path.resolve()
        
        for allowed_root in self.ALLOWED_ROOTS:
            allowed_abs = allowed_root.resolve()
            try:
                path_abs.relative_to(allowed_abs)
                return True
            except ValueError:
                continue
        
        return False
    
    def ensure_directory(self, path: Path) -> None:
        """Create directory if allowed."""
        if not self.is_path_allowed(path):
            raise PermissionError(f"Path not allowed: {path}")
        
        path.mkdir(parents=True, exist_ok=True)
```

### File Size Limits

**Audio Processor**:
```python
MAX_FILE_SIZE_MB = 5

def normalize_audio(self, input_path: Path, ...) -> None:
    file_size_mb = input_path.stat().st_size / (1024 * 1024)
    
    if file_size_mb > MAX_FILE_SIZE_MB:
        raise ValueError(f"File too large: {file_size_mb:.1f} MB > {MAX_FILE_SIZE_MB} MB")
    
    # ... proceed with normalization
```

### Read-Only Protection

**Dataset Raw Backup**:
```python
def save_normalized_audio(self, audio_path: Path, output_dir: Path) -> None:
    """Save normalized audio, never modify source."""
    if "dataset/raw" in str(audio_path):
        raise PermissionError("Cannot modify files in dataset/raw/ (permanent backup)")
    
    # ... save to output_dir
```

---

## DDD Boundary Compliance

### Domain Layer (UNCHANGED)
- `piper_voice/core/entities.py`: No changes
- `piper_voice/core/value_objects.py`: No changes
- `piper_voice/core/ports.py`: No changes

**Verification**:
```python
# domain must NOT import from infrastructure
assert "infrastructure" not in open("piper_voice/core/entities.py").read()
assert "librosa" not in open("piper_voice/core/entities.py").read()
assert "requests" not in open("piper_voice/core/entities.py").read()
```

### Infrastructure Layer (NEW IMPLEMENTATIONS)
- All new adapters implement ports defined in `core/ports.py`
- Infrastructure can import from `core` (dependency inversion)
- Infrastructure never imported by `core`

**Dependency Flow**:
```
Application Layer
    ↓ (uses)
Domain Layer (Ports)
    ↑ (implements)
Infrastructure Layer (Adapters)
```

---

## Consequences

### Positive

✅ **Testability**: Mock corpus enables fast unit tests without network
✅ **Robustness**: Retry logic + error handling ensures reliability
✅ **Security**: SafeFileSystem enforces path restrictions
✅ **Progress Visibility**: Real-time progress + detailed logs
✅ **DDD Compliance**: Domain layer remains pure, no infrastructure leakage
✅ **Scalability**: Same infrastructure can support other Japanese corpora (JVS, JSSS)

### Negative

❌ **Complexity**: More code than simple script approach
❌ **Testing Overhead**: Must maintain mock corpus fixtures
❌ **Learning Curve**: Developers must understand DDD ports/adapters

### Risks

1. **JSUT URL Change**: University may move/remove corpus
   - **Mitigation**: Mirror corpus locally, document alternative URLs

2. **Librosa Performance**: Resampling 7,300 files may be slow
   - **Mitigation**: Batch processing, progress tracking, expected time ~30 min

3. **Memory Usage**: Loading large audio files may exhaust memory
   - **Mitigation**: Process one file at a time, never load entire corpus into RAM

---

## Implementation Checklist

### Week 1: Core Infrastructure

- [ ] Implement `LibrosaAudioProcessor` with tests
- [ ] Implement `JsutCorpusLoader` with tests
- [ ] Implement `SafeFileSystem` with tests
- [ ] Implement `LjspeechMetadataWriter` with tests
- [ ] Create mock JSUT corpus for tests
- [ ] Implement `JsutCorpusDownloader` with tests

### Week 1-2: Application Layer

- [ ] Implement `download_jsut_corpus` use case
- [ ] Implement `prepare_jsut_dataset` use case
- [ ] Implement `PreparationLogger`
- [ ] Add CLI commands for download + prepare
- [ ] Integration tests with real JSUT samples

### Week 2: Validation

- [ ] Test on full JSUT corpus (7,300 files)
- [ ] Verify all quality checks pass
- [ ] Verify metadata.csv LJSPEECH compliance
- [ ] Verify Piper preprocessing accepts output
- [ ] Generate preparation report

---

## References

- [JSUT Corpus](https://sites.google.com/site/shinnosuketakamichi/research-topics/jsut-corpus)
- [Librosa Documentation](https://librosa.org/doc/latest/)
- [LJSPEECH Dataset Format](https://keithito.com/LJ-Speech-Dataset/)
- [Piper Training Guide](https://github.com/rhasspy/piper/blob/master/TRAINING.md)
- STORY-002: `docs/product/stories/STORY-002-jsut-corpus-infrastructure.md`
- ADR-001: `docs/product/decisions/ADR-001-japanese-voice-architecture.md`

---

**This ADR defines the architectural decisions for JSUT infrastructure implementation.**
All code must follow these decisions. TDD is mandatory. Security guardrails are non-negotiable.
