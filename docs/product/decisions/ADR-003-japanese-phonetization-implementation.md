# ADR-003: Japanese Phonetization Implementation

**Status**: ACCEPTED
**Date**: 2026-03-08
**Deciders**: Architect
**Related**: STORY-003-japanese-phonetization.md, ADR-001-japanese-voice-architecture.md, ADR-002-jsut-infrastructure-implementation.md

---

## Context

STORY-003 requires implementing Japanese phonetization to convert JSUT transcripts (mixed kanji/hiragana/katakana) into phoneme ID sequences for Piper training. This is a critical pipeline step that bridges human-readable Japanese text and machine-readable training data.

**Key Challenges**:

1. **No espeak-ng Support**: espeak-ng has poor Japanese coverage, requiring custom solution
2. **Writing System Complexity**: Japanese mixes kanji (ideographic), hiragana (phonetic), and katakana (foreign words)
3. **Phoneme System Design**: Must define ~100 unique phonemes covering all hiragana characters
4. **DDD Architecture**: Phonetization logic must respect domain/application/infrastructure boundaries
5. **Deterministic Mapping**: Same input must always produce identical phoneme IDs
6. **Error Handling**: Must handle conversion failures gracefully without blocking entire corpus

**Technical Constraints**:
- Input: `metadata.csv` with 7,300 Japanese transcripts (from Phase 2)
- Output: `metadata_phonemes.csv` with format `filename|text|phoneme_ids`
- Output: `phoneme_map.json` with hiragana → ID mappings
- Requirement: 100% success rate (zero phonetization failures)
- Performance: Must complete in <10 minutes for 7,300 transcripts
- Encoding: UTF-8 throughout

**Architectural Requirements** (from CLAUDE.md):
- Domain layer (`piper_voice/core`) must NOT depend on infrastructure
- Infrastructure adapters must be injected via ports (dependency inversion)
- TDD mandatory: tests before implementation
- Security: input validation, character encoding checks, no arbitrary code execution

---

## Decisions

### 1. Layer Ownership: Domain Logic with Infrastructure Adapters

**Decision**: Phonetization is domain logic, implemented in `piper_voice/core`, with pykakasi as infrastructure adapter.

**Architecture**:
```
piper_voice/
├── core/
│   ├── entities.py
│   │   └── PhonemeMap (new entity)
│   │   └── PhonemeSequence (new entity)
│   ├── value_objects.py
│   │   └── Phoneme (new value object)
│   │   └── HiraganaText (new value object)
│   └── ports.py
│       └── KanjiConverterPort (new port)
│       └── PhonetizerPort (new port)
│
├── infrastructure/
│   └── phonetics/
│       ├── pykakasi_adapter.py (implements KanjiConverterPort)
│       └── hiragana_phonetizer.py (implements PhonetizerPort)
│
└── application/
    └── phonemize_japanese.py (orchestration)
```

**Rationale**:
- ✅ Phonetization is core domain concept (not infrastructure concern)
- ✅ Phoneme mapping logic belongs in domain (business rule)
- ✅ pykakasi is infrastructure detail (can be swapped for other converters)
- ✅ Clear separation enables testing without external dependencies
- ✅ Follows ADR-001 DDD architecture

**Alternative Considered**: Put phonetization in infrastructure
- ❌ Violates DDD (domain logic in infrastructure)
- ❌ Makes domain depend on external library
- ❌ Harder to test and maintain

---

### 2. Phoneme Representation: Value Objects with Strong Typing

**Decision**: Create dedicated value objects for phoneme concepts.

**New Domain Value Objects** (`piper_voice/core/value_objects.py`):

```python
from dataclasses import dataclass
from typing import NewType

# Type aliases for clarity
PhonemeID = NewType('PhonemeID', int)
HiraganaChar = NewType('HiraganaChar', str)

@dataclass(frozen=True)
class Phoneme:
    """Single phoneme unit (hiragana character)."""
    character: HiraganaChar
    phoneme_id: PhonemeID
    
    def __post_init__(self):
        if not self.character:
            raise ValueError("Phoneme character cannot be empty")
        if self.phoneme_id < 0:
            raise ValueError(f"Phoneme ID must be non-negative, got {self.phoneme_id}")
        # Validate character is actually hiragana or special character
        if not self._is_valid_phoneme_char(self.character):
            raise ValueError(f"Invalid phoneme character: {self.character}")
    
    @staticmethod
    def _is_valid_phoneme_char(char: str) -> bool:
        """Check if character is valid hiragana or special phoneme character."""
        if not char:
            return False
        # Basic hiragana range (U+3040 to U+309F)
        # Special characters: っ (gemination), ん (nasal), ー (long vowel)
        code = ord(char[0])
        return (0x3040 <= code <= 0x309F) or char in ['ー', ' ']

@dataclass(frozen=True)
class HiraganaText:
    """Pure hiragana representation of Japanese text."""
    text: str
    
    def __post_init__(self):
        if not self.text:
            raise ValueError("Hiragana text cannot be empty")
        # Validate all characters are hiragana or whitespace
        for char in self.text:
            if char.isspace():
                continue
            if not Phoneme._is_valid_phoneme_char(char):
                raise ValueError(f"Non-hiragana character found: {char}")
    
    def __len__(self) -> int:
        return len(self.text)
    
    def chars(self) -> list[HiraganaChar]:
        """Get list of individual hiragana characters."""
        return [HiraganaChar(char) for char in self.text if not char.isspace()]

@dataclass(frozen=True)
class PhonemeSequence:
    """Sequence of phoneme IDs for a single utterance."""
    phoneme_ids: tuple[PhonemeID, ...]
    
    def __post_init__(self):
        if not self.phoneme_ids:
            raise ValueError("Phoneme sequence cannot be empty")
        for pid in self.phoneme_ids:
            if pid < 0:
                raise ValueError(f"Invalid phoneme ID: {pid}")
    
    def __len__(self) -> int:
        return len(self.phoneme_ids)
    
    def to_string(self) -> str:
        """Convert to space-separated string (for metadata.csv)."""
        return ' '.join(str(pid) for pid in self.phoneme_ids)
    
    @classmethod
    def from_string(cls, phoneme_str: str) -> 'PhonemeSequence':
        """Parse from space-separated string."""
        try:
            ids = tuple(PhonemeID(int(x)) for x in phoneme_str.split())
            return cls(ids)
        except ValueError as e:
            raise ValueError(f"Invalid phoneme sequence string: {phoneme_str}") from e
```

**Rationale**:
- ✅ Strong typing prevents accidental misuse (PhonemeID vs regular int)
- ✅ Validation at construction time (fail-fast)
- ✅ Immutability ensures data integrity
- ✅ Clear semantic meaning (PhonemeSequence vs list[int])
- ✅ Self-documenting code

---

### 3. Phoneme Mapping: Domain Entity with Deterministic Generation

**Decision**: PhonemeMap is a domain entity managing hiragana → ID mappings.

**New Domain Entity** (`piper_voice/core/entities.py`):

```python
from dataclasses import dataclass, field
from typing import Dict
from .value_objects import Phoneme, HiraganaChar, PhonemeID, HiraganaText, PhonemeSequence

@dataclass
class PhonemeMap:
    """Maps hiragana characters to unique phoneme IDs.
    
    This is a domain entity because it encapsulates phoneme system
    business rules and maintains identity across the application.
    """
    _mapping: Dict[HiraganaChar, PhonemeID] = field(default_factory=dict, repr=False)
    _reverse_mapping: Dict[PhonemeID, HiraganaChar] = field(default_factory=dict, repr=False)
    _next_id: int = field(default=0, repr=False)
    
    def add_character(self, char: HiraganaChar) -> PhonemeID:
        """Add hiragana character to map, return its phoneme ID.
        
        If character already exists, return existing ID (idempotent).
        """
        if char in self._mapping:
            return self._mapping[char]
        
        # Validate character
        if not Phoneme._is_valid_phoneme_char(char):
            raise ValueError(f"Invalid hiragana character: {char}")
        
        # Assign new ID
        new_id = PhonemeID(self._next_id)
        self._mapping[char] = new_id
        self._reverse_mapping[new_id] = char
        self._next_id += 1
        
        return new_id
    
    def get_phoneme_id(self, char: HiraganaChar) -> PhonemeID:
        """Get phoneme ID for character. Raises KeyError if not found."""
        if char not in self._mapping:
            raise KeyError(f"Hiragana character not in phoneme map: {char}")
        return self._mapping[char]
    
    def get_character(self, phoneme_id: PhonemeID) -> HiraganaChar:
        """Get hiragana character for phoneme ID. Raises KeyError if not found."""
        if phoneme_id not in self._reverse_mapping:
            raise KeyError(f"Phoneme ID not in map: {phoneme_id}")
        return self._reverse_mapping[phoneme_id]
    
    def has_character(self, char: HiraganaChar) -> bool:
        """Check if character is in map."""
        return char in self._mapping
    
    def phonemize(self, hiragana: HiraganaText) -> PhonemeSequence:
        """Convert hiragana text to phoneme ID sequence.
        
        Raises KeyError if any character is not in map.
        """
        phoneme_ids = []
        for char in hiragana.chars():
            phoneme_ids.append(self.get_phoneme_id(char))
        return PhonemeSequence(tuple(phoneme_ids))
    
    def size(self) -> int:
        """Get number of unique phonemes."""
        return len(self._mapping)
    
    def to_dict(self) -> dict:
        """Export to dictionary (for JSON serialization)."""
        return {
            str(char): int(pid) 
            for char, pid in sorted(self._mapping.items(), key=lambda x: x[1])
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PhonemeMap':
        """Import from dictionary (from JSON)."""
        phoneme_map = cls()
        for char_str, pid_int in data.items():
            char = HiraganaChar(char_str)
            pid = PhonemeID(pid_int)
            phoneme_map._mapping[char] = pid
            phoneme_map._reverse_mapping[pid] = char
            phoneme_map._next_id = max(phoneme_map._next_id, pid_int + 1)
        return phoneme_map
    
    @classmethod
    def build_from_texts(cls, hiragana_texts: list[HiraganaText]) -> 'PhonemeMap':
        """Build phoneme map from collection of hiragana texts.
        
        This ensures deterministic mapping (characters encountered first
        get lower IDs, alphabetical order within same encounter).
        """
        phoneme_map = cls()
        
        # Collect all unique characters
        unique_chars = set()
        for text in hiragana_texts:
            unique_chars.update(text.chars())
        
        # Sort for deterministic ordering
        sorted_chars = sorted(unique_chars)
        
        # Add to map
        for char in sorted_chars:
            phoneme_map.add_character(char)
        
        return phoneme_map
```

**Rationale**:
- ✅ Entity maintains identity (single source of truth for phoneme system)
- ✅ Encapsulates business rules (validation, ID assignment)
- ✅ Deterministic construction (sorted order → reproducible)
- ✅ Bidirectional mapping (char → ID and ID → char)
- ✅ Serialization support (JSON import/export)
- ✅ Clear domain language (phonemize, not "convert")

---

### 4. Kanji Conversion: Infrastructure Port + pykakasi Adapter

**Decision**: Define port for kanji conversion, implement with pykakasi adapter.

**Port Definition** (`piper_voice/core/ports.py`):

```python
from abc import ABC, abstractmethod
from typing import Protocol
from .value_objects import HiraganaText

class KanjiConverterPort(Protocol):
    """Port for converting Japanese text (kanji/kana) to pure hiragana."""
    
    def convert_to_hiragana(self, japanese_text: str) -> HiraganaText:
        """Convert mixed Japanese text to pure hiragana.
        
        Args:
            japanese_text: Text containing kanji, hiragana, katakana
            
        Returns:
            HiraganaText value object with pure hiragana
            
        Raises:
            ValueError: If conversion fails or result contains non-hiragana
        """
        ...
```

**Adapter Implementation** (`piper_voice/infrastructure/phonetics/pykakasi_adapter.py`):

```python
import pykakasi
from typing import Optional
from piper_voice.core.ports import KanjiConverterPort
from piper_voice.core.value_objects import HiraganaText

class PykakasiAdapter:
    """Adapter for pykakasi library (kanji → hiragana conversion)."""
    
    def __init__(self):
        self._kks = pykakasi.kakasi()
    
    def convert_to_hiragana(self, japanese_text: str) -> HiraganaText:
        """Convert Japanese text to pure hiragana using pykakasi."""
        if not japanese_text or not japanese_text.strip():
            raise ValueError("Input text cannot be empty")
        
        try:
            # pykakasi returns list of dicts with different reading formats
            result = self._kks.convert(japanese_text)
            
            # Extract hiragana reading (key: 'hira')
            hiragana_chars = []
            for item in result:
                if 'hira' in item:
                    hiragana_chars.append(item['hira'])
                else:
                    # Fallback to original if no hiragana key
                    hiragana_chars.append(item.get('orig', ''))
            
            hiragana_str = ''.join(hiragana_chars)
            
            # Validate result
            if not hiragana_str:
                raise ValueError(f"pykakasi produced empty result for: {japanese_text}")
            
            # Create value object (validation happens here)
            return HiraganaText(hiragana_str)
            
        except Exception as e:
            raise ValueError(f"Failed to convert to hiragana: {japanese_text}") from e
```

**Rationale**:
- ✅ Port in domain, adapter in infrastructure (dependency inversion)
- ✅ Domain doesn't know about pykakasi (can swap implementations)
- ✅ Adapter handles external library quirks
- ✅ Strong error handling with context
- ✅ Returns domain value object (not raw string)

**Alternative Considered**: Call pykakasi directly from application
- ❌ Violates clean architecture
- ❌ Harder to test (requires real pykakasi)
- ❌ Cannot mock or swap implementations

---

### 5. Phonetizer Port: Domain Contract for Phonemization

**Decision**: Define port for complete phonemization pipeline.

**Port Definition** (`piper_voice/core/ports.py`):

```python
from typing import Protocol
from .entities import PhonemeMap
from .value_objects import HiraganaText, PhonemeSequence

class PhonetizerPort(Protocol):
    """Port for phonemizing hiragana text to phoneme sequences."""
    
    def phonemize(
        self, 
        hiragana: HiraganaText, 
        phoneme_map: PhonemeMap
    ) -> PhonemeSequence:
        """Convert hiragana text to phoneme ID sequence.
        
        Args:
            hiragana: Pure hiragana text
            phoneme_map: Mapping of hiragana characters to phoneme IDs
            
        Returns:
            PhonemeSequence with phoneme IDs
            
        Raises:
            KeyError: If hiragana contains character not in phoneme_map
        """
        ...
```

**Adapter Implementation** (`piper_voice/infrastructure/phonetics/hiragana_phonetizer.py`):

```python
from piper_voice.core.ports import PhonetizerPort
from piper_voice.core.entities import PhonemeMap
from piper_voice.core.value_objects import HiraganaText, PhonemeSequence

class HiraganaPhonetizer:
    """Infrastructure adapter for hiragana → phoneme ID conversion."""
    
    def phonemize(
        self, 
        hiragana: HiraganaText, 
        phoneme_map: PhonemeMap
    ) -> PhonemeSequence:
        """Convert hiragana to phoneme IDs using provided map.
        
        This is a simple delegation to PhonemeMap.phonemize(),
        but exists as a separate adapter for:
        - Explicit infrastructure layer presence
        - Future enhancement (e.g., prosody, accent handling)
        - Testing and mocking
        """
        try:
            return phoneme_map.phonemize(hiragana)
        except KeyError as e:
            # Enhance error message with context
            raise KeyError(
                f"Cannot phonemize hiragana text: {hiragana.text}. "
                f"Missing character in phoneme map: {e}"
            ) from e
```

**Rationale**:
- ✅ Port defines domain contract
- ✅ Adapter can be enhanced without changing domain
- ✅ Clear separation: PhonemeMap (entity) vs HiraganaPhonetizer (adapter)
- ✅ Testable in isolation

**Note**: This adapter is thin now but provides extension point for future enhancements (accent marks, prosody, alternative phoneme strategies).

---

### 6. Application Orchestration: Use Case with Error Handling

**Decision**: Application layer orchestrates full pipeline with comprehensive error handling.

**Use Case Implementation** (`piper_voice/application/phonemize_japanese.py`):

```python
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import json
import logging

from piper_voice.core.entities import PhonemeMap
from piper_voice.core.value_objects import HiraganaText, PhonemeSequence
from piper_voice.core.ports import KanjiConverterPort, PhonetizerPort, MetadataRepositoryPort

@dataclass
class PhonemizationResult:
    """Result of phonemizing a single transcript."""
    filename: str
    original_text: str
    hiragana_text: Optional[HiraganaText]
    phoneme_sequence: Optional[PhonemeSequence]
    error: Optional[str]
    
    @property
    def success(self) -> bool:
        return self.error is None

@dataclass
class PhonemizationReport:
    """Summary report of entire phonemization process."""
    total_transcripts: int
    successful: int
    failed: int
    unique_phonemes: int
    results: list[PhonemizationResult]
    
    @property
    def success_rate(self) -> float:
        return (self.successful / self.total_transcripts) * 100 if self.total_transcripts > 0 else 0.0

def phonemize_japanese_corpus(
    metadata_csv_path: Path,
    output_dir: Path,
    kanji_converter: KanjiConverterPort,
    phonetizer: PhonetizerPort,
    metadata_repo: MetadataRepositoryPort,
    logger: Optional[logging.Logger] = None
) -> PhonemizationReport:
    """Phonemize entire Japanese corpus (application use case).
    
    Pipeline:
    1. Read metadata.csv (filename|japanese_text)
    2. For each transcript:
       a. Convert kanji → hiragana
       b. Collect unique hiragana characters
    3. Build phoneme map from all unique characters
    4. For each transcript:
       a. Convert hiragana → phoneme IDs
    5. Save metadata_phonemes.csv (filename|text|phoneme_ids)
    6. Save phoneme_map.json
    7. Generate report
    
    Args:
        metadata_csv_path: Path to input metadata.csv
        output_dir: Directory for outputs (metadata_phonemes.csv, phoneme_map.json)
        kanji_converter: Adapter for kanji → hiragana conversion
        phonetizer: Adapter for hiragana → phoneme IDs
        metadata_repo: Adapter for reading/writing metadata files
        logger: Optional logger for progress tracking
        
    Returns:
        PhonemizationReport with success/failure statistics
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Phase 1: Load metadata
    logger.info(f"Loading metadata from {metadata_csv_path}")
    metadata = metadata_repo.load_metadata(metadata_csv_path)
    logger.info(f"Loaded {len(metadata)} transcripts")
    
    # Phase 2: Convert all to hiragana
    logger.info("Converting kanji to hiragana...")
    hiragana_results = []
    hiragana_texts = []
    
    for filename, original_text in metadata:
        try:
            hiragana = kanji_converter.convert_to_hiragana(original_text)
            hiragana_results.append(PhonemizationResult(
                filename=filename,
                original_text=original_text,
                hiragana_text=hiragana,
                phoneme_sequence=None,
                error=None
            ))
            hiragana_texts.append(hiragana)
        except Exception as e:
            logger.warning(f"Failed to convert {filename}: {e}")
            hiragana_results.append(PhonemizationResult(
                filename=filename,
                original_text=original_text,
                hiragana_text=None,
                phoneme_sequence=None,
                error=str(e)
            ))
    
    conversion_success = sum(1 for r in hiragana_results if r.success)
    logger.info(f"Hiragana conversion: {conversion_success}/{len(metadata)} successful")
    
    # Phase 3: Build phoneme map from all hiragana texts
    logger.info("Building phoneme map...")
    phoneme_map = PhonemeMap.build_from_texts([h for h in hiragana_texts if h is not None])
    logger.info(f"Phoneme map contains {phoneme_map.size()} unique phonemes")
    
    # Phase 4: Phonemize all hiragana texts
    logger.info("Converting hiragana to phoneme IDs...")
    final_results = []
    
    for result in hiragana_results:
        if not result.success:
            # Already failed in hiragana conversion
            final_results.append(result)
            continue
        
        try:
            phoneme_seq = phonetizer.phonemize(result.hiragana_text, phoneme_map)
            final_results.append(PhonemizationResult(
                filename=result.filename,
                original_text=result.original_text,
                hiragana_text=result.hiragana_text,
                phoneme_sequence=phoneme_seq,
                error=None
            ))
        except Exception as e:
            logger.warning(f"Failed to phonemize {result.filename}: {e}")
            final_results.append(PhonemizationResult(
                filename=result.filename,
                original_text=result.original_text,
                hiragana_text=result.hiragana_text,
                phoneme_sequence=None,
                error=str(e)
            ))
    
    successful_results = [r for r in final_results if r.success]
    failed_results = [r for r in final_results if not r.success]
    
    logger.info(f"Phonemization complete: {len(successful_results)}/{len(metadata)} successful")
    
    # Phase 5: Save outputs
    logger.info("Saving outputs...")
    
    # Save metadata_phonemes.csv
    metadata_phonemes_path = output_dir / "metadata_phonemes.csv"
    phoneme_metadata = [
        (r.filename, r.original_text, r.phoneme_sequence.to_string())
        for r in successful_results
    ]
    
    # Write with custom format (3 columns)
    with open(metadata_phonemes_path, 'w', encoding='utf-8') as f:
        for filename, text, phoneme_ids in phoneme_metadata:
            f.write(f"{filename}|{text}|{phoneme_ids}\n")
    
    logger.info(f"Saved {len(phoneme_metadata)} entries to {metadata_phonemes_path}")
    
    # Save phoneme_map.json
    phoneme_map_path = output_dir / "phoneme_map.json"
    with open(phoneme_map_path, 'w', encoding='utf-8') as f:
        json.dump(phoneme_map.to_dict(), f, ensure_ascii=False, indent=2)
    
    logger.info(f"Saved phoneme map ({phoneme_map.size()} phonemes) to {phoneme_map_path}")
    
    # Phase 6: Generate report
    report = PhonemizationReport(
        total_transcripts=len(metadata),
        successful=len(successful_results),
        failed=len(failed_results),
        unique_phonemes=phoneme_map.size(),
        results=final_results
    )
    
    logger.info(f"Phonemization report: {report.success_rate:.1f}% success rate")
    
    if failed_results:
        logger.warning(f"Failed transcripts: {len(failed_results)}")
        for result in failed_results[:10]:  # Show first 10 errors
            logger.warning(f"  {result.filename}: {result.error}")
    
    return report
```

**Rationale**:
- ✅ Clear separation: orchestration (app) vs logic (domain) vs I/O (infra)
- ✅ Comprehensive error handling (don't stop on first failure)
- ✅ Progress tracking with logging
- ✅ Detailed report for debugging
- ✅ Testable by mocking adapters

---

### 7. Error Handling Strategy: Fail-Fast vs Graceful Degradation

**Decision**: Two-phase approach with different error strategies.

**Phase 1: Hiragana Conversion** (Graceful Degradation):
- Continue processing even if some transcripts fail
- Collect all errors for final report
- Log warnings but don't stop pipeline

**Phase 2: Phoneme Mapping** (Fail-Fast):
- If phoneme map is incomplete (missing characters), fail immediately
- Report missing character with context
- Don't generate partial output

**Error Categories**:

1. **Input Validation Errors** (Fail-Fast):
   - Empty text
   - Invalid encoding
   - Metadata file not found
   → Raise ValueError, stop processing

2. **Conversion Errors** (Graceful):
   - pykakasi conversion failure
   - Unexpected characters
   → Log warning, mark as failed, continue

3. **Phoneme Mapping Errors** (Graceful):
   - Character not in phoneme map
   → Log warning, mark as failed, continue

4. **I/O Errors** (Fail-Fast):
   - Cannot write output files
   - Disk full
   → Raise IOError, stop processing

**Rationale**:
- ✅ Maximize corpus utilization (don't lose 7,299 transcripts due to 1 failure)
- ✅ Clear error reporting (know exactly which transcripts failed)
- ✅ Critical errors still stop pipeline (fail-fast for I/O)
- ✅ Meets STORY-003 requirement (generate error report, continue processing)

---

### 8. Testing Strategy: Multi-Layer TDD Approach

**Decision**: Test each layer independently with clear boundaries.

**Unit Tests** (Domain Layer):

```python
# tests/unit/test_phoneme_value_objects.py
def test_phoneme_validates_hiragana_character():
    """Test Phoneme validates character is actually hiragana."""
    # Valid hiragana
    phoneme = Phoneme(character='あ', phoneme_id=0)
    assert phoneme.character == 'あ'
    
    # Invalid: kanji
    with pytest.raises(ValueError, match="Invalid phoneme character"):
        Phoneme(character='東', phoneme_id=0)
    
    # Invalid: latin
    with pytest.raises(ValueError, match="Invalid phoneme character"):
        Phoneme(character='a', phoneme_id=0)

def test_hiragana_text_validates_all_characters():
    """Test HiraganaText rejects non-hiragana."""
    # Valid
    text = HiraganaText("こんにちは")
    assert len(text) == 5
    
    # Invalid: contains kanji
    with pytest.raises(ValueError, match="Non-hiragana character"):
        HiraganaText("今日は")

def test_phoneme_sequence_serialization():
    """Test PhonemeSequence to/from string conversion."""
    seq = PhonemeSequence((1, 2, 3, 4, 5))
    string = seq.to_string()
    assert string == "1 2 3 4 5"
    
    parsed = PhonemeSequence.from_string(string)
    assert parsed == seq

# tests/unit/test_phoneme_map.py
def test_phoneme_map_deterministic_generation():
    """Test PhonemeMap generates same IDs for same input."""
    texts = [
        HiraganaText("こんにちは"),
        HiraganaText("ありがとう")
    ]
    
    map1 = PhonemeMap.build_from_texts(texts)
    map2 = PhonemeMap.build_from_texts(texts)
    
    assert map1.to_dict() == map2.to_dict()

def test_phoneme_map_sorted_order():
    """Test PhonemeMap assigns IDs in sorted order."""
    texts = [HiraganaText("くあい")]  # Not alphabetical
    phoneme_map = PhonemeMap.build_from_texts(texts)
    
    # Should be sorted: あ, い, く
    assert phoneme_map.get_phoneme_id('あ') < phoneme_map.get_phoneme_id('い')
    assert phoneme_map.get_phoneme_id('い') < phoneme_map.get_phoneme_id('く')

def test_phoneme_map_phonemize():
    """Test PhonemeMap.phonemize converts text to IDs."""
    phoneme_map = PhonemeMap()
    phoneme_map.add_character('あ')  # ID: 0
    phoneme_map.add_character('い')  # ID: 1
    
    hiragana = HiraganaText("あいあ")
    sequence = phoneme_map.phonemize(hiragana)
    
    assert sequence.phoneme_ids == (0, 1, 0)

def test_phoneme_map_missing_character_error():
    """Test PhonemeMap raises KeyError for unknown character."""
    phoneme_map = PhonemeMap()
    phoneme_map.add_character('あ')
    
    hiragana = HiraganaText("い")  # Not in map
    
    with pytest.raises(KeyError, match="not in phoneme map"):
        phoneme_map.phonemize(hiragana)
```

**Integration Tests** (Infrastructure Adapters):

```python
# tests/integration/test_pykakasi_adapter.py
def test_pykakasi_converts_kanji_to_hiragana():
    """Test pykakasi adapter converts kanji correctly."""
    adapter = PykakasiAdapter()
    
    # Simple kanji
    result = adapter.convert_to_hiragana("東京")
    assert result.text == "とうきょう"
    
    # Mixed kanji and hiragana
    result = adapter.convert_to_hiragana("今日は晴れです")
    assert "きょう" in result.text
    assert "はれ" in result.text

def test_pykakasi_handles_katakana():
    """Test pykakasi converts katakana to hiragana."""
    adapter = PykakasiAdapter()
    
    result = adapter.convert_to_hiragana("コンピュータ")
    # Should be hiragana equivalent
    assert result.text == "こんぴゅーた"

def test_pykakasi_error_handling():
    """Test pykakasi adapter error handling."""
    adapter = PykakasiAdapter()
    
    # Empty input
    with pytest.raises(ValueError, match="cannot be empty"):
        adapter.convert_to_hiragana("")
```

**End-to-End Tests** (Application Use Case):

```python
# tests/integration/test_phonemize_japanese_pipeline.py
@pytest.fixture
def mock_jsut_metadata(tmp_path):
    """Create mock JSUT metadata.csv."""
    metadata_path = tmp_path / "metadata.csv"
    with open(metadata_path, 'w', encoding='utf-8') as f:
        f.write("jsut_basic5000_0001|こんにちは\n")
        f.write("jsut_basic5000_0002|東京に行きました\n")
        f.write("jsut_basic5000_0003|今日はいい天気です\n")
    return metadata_path

def test_full_phonemization_pipeline(mock_jsut_metadata, tmp_path):
    """Test complete phonemization pipeline end-to-end."""
    # Setup adapters
    kanji_converter = PykakasiAdapter()
    phonetizer = HiraganaPhonetizer()
    metadata_repo = LjspeechMetadataWriter()
    
    output_dir = tmp_path / "output"
    
    # Run pipeline
    report = phonemize_japanese_corpus(
        metadata_csv_path=mock_jsut_metadata,
        output_dir=output_dir,
        kanji_converter=kanji_converter,
        phonetizer=phonetizer,
        metadata_repo=metadata_repo
    )
    
    # Verify report
    assert report.total_transcripts == 3
    assert report.successful == 3
    assert report.failed == 0
    assert report.unique_phonemes > 0
    
    # Verify outputs exist
    assert (output_dir / "metadata_phonemes.csv").exists()
    assert (output_dir / "phoneme_map.json").exists()
    
    # Verify metadata_phonemes.csv content
    with open(output_dir / "metadata_phonemes.csv", 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    assert len(lines) == 3
    
    # Each line should have 3 pipe-separated fields
    for line in lines:
        parts = line.strip().split('|')
        assert len(parts) == 3
        filename, text, phoneme_ids = parts
        assert filename.startswith("jsut_")
        assert text  # Original Japanese text preserved
        assert phoneme_ids  # Phoneme IDs present
        assert all(c.isdigit() or c.isspace() for c in phoneme_ids)
    
    # Verify phoneme_map.json content
    with open(output_dir / "phoneme_map.json", 'r', encoding='utf-8') as f:
        phoneme_map_data = json.load(f)
    
    assert len(phoneme_map_data) == report.unique_phonemes
    
    # All keys should be hiragana, all values should be integers
    for char, phoneme_id in phoneme_map_data.items():
        assert len(char) == 1
        assert isinstance(phoneme_id, int)
        assert phoneme_id >= 0

def test_phonemization_error_handling(tmp_path):
    """Test phonemization handles errors gracefully."""
    # Create metadata with problematic entry
    metadata_path = tmp_path / "metadata.csv"
    with open(metadata_path, 'w', encoding='utf-8') as f:
        f.write("file1|こんにちは\n")
        f.write("file2|\n")  # Empty text (should fail)
        f.write("file3|ありがとう\n")
    
    kanji_converter = PykakasiAdapter()
    phonetizer = HiraganaPhonetizer()
    metadata_repo = LjspeechMetadataWriter()
    
    output_dir = tmp_path / "output"
    
    report = phonemize_japanese_corpus(
        metadata_csv_path=metadata_path,
        output_dir=output_dir,
        kanji_converter=kanji_converter,
        phonetizer=phonetizer,
        metadata_repo=metadata_repo
    )
    
    # Should have 2 successful, 1 failed
    assert report.total_transcripts == 3
    assert report.successful == 2
    assert report.failed == 1
    
    # Failed entry should be in results
    failed = [r for r in report.results if not r.success]
    assert len(failed) == 1
    assert failed[0].filename == "file2"
    assert failed[0].error is not None
```

**Test Coverage Requirements**:
- Domain value objects: 100% coverage (critical validation logic)
- Domain entities: 100% coverage (PhonemeMap is central)
- Infrastructure adapters: 90% coverage (external library behavior may vary)
- Application use case: 90% coverage (focus on error paths)

---

### 9. Security and Validation Rules

**Decision**: Implement strict input validation and encoding checks.

**Security Measures**:

1. **Input Validation**:
```python
def validate_japanese_text(text: str) -> None:
    """Validate Japanese text input."""
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")
    
    # Check for suspicious characters
    suspicious_chars = ['<', '>', '&', ';', '`', '$', '|', '\x00']
    for char in suspicious_chars:
        if char in text:
            raise ValueError(f"Suspicious character detected: {char}")
    
    # Validate UTF-8 encoding
    try:
        text.encode('utf-8')
    except UnicodeEncodeError as e:
        raise ValueError("Text contains invalid UTF-8 characters") from e
    
    # Validate length (prevent DoS)
    MAX_TEXT_LENGTH = 500  # Max characters per transcript
    if len(text) > MAX_TEXT_LENGTH:
        raise ValueError(f"Text too long: {len(text)} > {MAX_TEXT_LENGTH}")
```

2. **Phoneme Map Size Limit**:
```python
MAX_PHONEMES = 200  # Hiragana should be ~100, allow buffer

def build_from_texts(cls, hiragana_texts: list[HiraganaText]) -> 'PhonemeMap':
    phoneme_map = cls()
    # ... build map ...
    
    if phoneme_map.size() > MAX_PHONEMES:
        raise ValueError(
            f"Phoneme map too large: {phoneme_map.size()} > {MAX_PHONEMES}. "
            f"Expected ~100 hiragana phonemes."
        )
    
    return phoneme_map
```

3. **File Path Validation** (Already in SafeFileSystem from ADR-002):
- Only allow writes to `./dataset`, `./training`, `./models`, `./logs`
- Prevent path traversal attacks
- Validate output paths before writing

4. **Encoding Enforcement**:
- All file I/O uses `encoding='utf-8'` explicitly
- No reliance on system default encoding
- Validate UTF-8 before processing

**Rationale**:
- ✅ Prevents injection attacks (no shell execution with user input)
- ✅ Prevents DoS (length limits, phoneme count limits)
- ✅ Ensures data integrity (UTF-8 validation)
- ✅ Fails fast on malformed input

---

## Implementation Plan

### Phase 3a: Domain Layer (Week 1, Day 1-2) — TDD FIRST

**Test First, Then Implement**:

1. **Day 1 Morning**: Write domain value object tests
   - `tests/unit/test_phoneme_value_objects.py`
   - Run tests → ALL FAIL (expected)

2. **Day 1 Afternoon**: Implement domain value objects
   - `piper_voice/core/value_objects.py`: Phoneme, HiraganaText, PhonemeSequence
   - Run tests → ALL PASS

3. **Day 1 Evening**: Write PhonemeMap entity tests
   - `tests/unit/test_phoneme_map.py`
   - Run tests → ALL FAIL (expected)

4. **Day 2 Morning**: Implement PhonemeMap entity
   - `piper_voice/core/entities.py`: PhonemeMap
   - Run tests → ALL PASS

5. **Day 2 Afternoon**: Write port tests (using mocks)
   - `tests/unit/test_ports.py`
   - Run tests → ALL PASS (ports are interfaces)

### Phase 3b: Infrastructure Layer (Week 1, Day 3-4) — TDD FIRST

**Test First, Then Implement**:

1. **Day 3 Morning**: Write pykakasi adapter tests
   - `tests/integration/test_pykakasi_adapter.py`
   - Run tests → ALL FAIL (adapter not implemented)

2. **Day 3 Afternoon**: Implement pykakasi adapter
   - `piper_voice/infrastructure/phonetics/pykakasi_adapter.py`
   - Run tests → ALL PASS

3. **Day 4 Morning**: Write phonetizer adapter tests
   - `tests/integration/test_hiragana_phonetizer.py`
   - Run tests → ALL FAIL (adapter not implemented)

4. **Day 4 Afternoon**: Implement phonetizer adapter
   - `piper_voice/infrastructure/phonetics/hiragana_phonetizer.py`
   - Run tests → ALL PASS

### Phase 3c: Application Layer (Week 1, Day 5) — TDD FIRST

**Test First, Then Implement**:

1. **Day 5 Morning**: Write application use case tests
   - `tests/integration/test_phonemize_japanese_pipeline.py`
   - Run tests → ALL FAIL (use case not implemented)

2. **Day 5 Afternoon**: Implement application use case
   - `piper_voice/application/phonemize_japanese.py`
   - Run tests → ALL PASS

3. **Day 5 Evening**: Add CLI script
   - `scripts/phonemize_japanese.py`
   - Manual testing with real JSUT data

### Phase 3d: Full Corpus Validation (Week 2, Day 1)

1. Run on full JSUT corpus (7,300 transcripts)
2. Verify 100% success rate
3. Validate phoneme map size (~100 phonemes)
4. Generate validation report
5. Fix any edge cases discovered

**Deliverables**:
- [ ] Domain value objects with tests (100% coverage)
- [ ] PhonemeMap entity with tests (100% coverage)
- [ ] Ports defined in `core/ports.py`
- [ ] PykakasiAdapter with tests (90% coverage)
- [ ] HiraganaPhonetizer with tests (90% coverage)
- [ ] Application use case with tests (90% coverage)
- [ ] CLI script (`scripts/phonemize_japanese.py`)
- [ ] metadata_phonemes.csv for JSUT (7,300 rows)
- [ ] phoneme_map.json (~100 phonemes)
- [ ] Validation report confirming 100% success

---

## Consequences

### Positive

✅ **DDD Compliance**: Domain layer remains pure, no infrastructure dependencies
✅ **Testability**: Each layer testable in isolation with mocks
✅ **Maintainability**: Clear separation of concerns, easy to understand
✅ **Extensibility**: Can add new phoneme strategies without changing domain
✅ **Type Safety**: Strong typing with value objects prevents errors
✅ **Determinism**: Reproducible phoneme mappings
✅ **Error Transparency**: Comprehensive error reporting
✅ **Security**: Input validation prevents injection and DoS

### Negative

❌ **Complexity**: More code than simple script approach
❌ **Learning Curve**: Developers must understand DDD, ports/adapters
❌ **Initial Development Time**: TDD + architecture setup takes longer
❌ **Boilerplate**: Value objects require more code than raw types

### Risks

1. **pykakasi Accuracy**: Kanji conversion may have errors for ambiguous readings
   - **Mitigation**: Generate validation report, manual review of sample, accept medium quality
   
2. **Phoneme Count Exceeds 200**: Unexpected characters in corpus
   - **Mitigation**: Validation error will catch this, investigate and fix

3. **Performance**: Phonemizing 7,300 transcripts may be slow
   - **Mitigation**: Expected <10 minutes based on pykakasi benchmarks, progress tracking

4. **Memory Usage**: Loading all transcripts into memory
   - **Mitigation**: Process in streaming fashion if needed (future optimization)

---

## Validation Criteria (From STORY-003)

This architecture must satisfy all STORY-003 acceptance criteria:

- [ ] All 7,300 JSUT transcripts convert from kanji/kana to pure hiragana without errors
- [ ] Phoneme map contains approximately 100 unique hiragana characters
- [ ] metadata_phonemes.csv exists with exactly three columns (filename, text, phoneme IDs)
- [ ] metadata_phonemes.csv contains exactly 7,300 rows
- [ ] Every phoneme ID sequence is non-empty and contains only integers separated by spaces
- [ ] Validation report confirms 100% success rate
- [ ] phoneme_map.json is human-readable and deterministic
- [ ] Running phonemization twice produces identical results

---

## References

- [STORY-003: Japanese Phonetization](../stories/STORY-003-japanese-phonetization.md)
- [ADR-001: Japanese Voice Architecture](ADR-001-japanese-voice-architecture.md)
- [ADR-002: JSUT Infrastructure Implementation](ADR-002-jsut-infrastructure-implementation.md)
- [pykakasi Documentation](https://github.com/miurahr/pykakasi)
- [Domain-Driven Design](https://martinfowler.com/bliki/DomainDrivenDesign.html)
- [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)
- CLAUDE.md: Project rules and principles

---

**This ADR is the architectural authority for Japanese phonetization implementation.**
All code must follow these decisions. TDD is mandatory. DDD boundaries are non-negotiable. Security validation is required.
