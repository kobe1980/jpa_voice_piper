# STORY-003: Japanese Phonetization for Piper Training

## Context / Problem

Piper TTS training requires converting text transcripts into sequences of phoneme IDs. For most languages, this is handled by espeak-ng, which provides International Phonetic Alphabet (IPA) phonemes. However, espeak-ng has poor support for Japanese, making it unsuitable for Japanese voice training.

Japanese text presents additional complexity due to its mixed writing system (kanji, hiragana, katakana). A sentence like "東京に行きました" combines kanji (東京) with hiragana (に、きました), requiring conversion to a consistent phonetic representation before Piper can process it.

Without a reliable phonetization system, users cannot prepare Japanese transcripts for Piper training. The JSUT corpus contains approximately 7,300 Japanese transcripts in mixed kanji/kana format, and all of them must be converted to phoneme ID sequences before training can begin.

## User Goal

As a user preparing Japanese voice training data, I want to automatically convert all Japanese transcripts (kanji and kana) into phoneme ID sequences so that Piper preprocessing can understand and process them for training.

## Functional Behavior

### Text-to-Hiragana Conversion

1. The user initiates Japanese phonetization on a prepared dataset containing metadata.csv
2. The system reads each Japanese transcript from metadata.csv
3. For each transcript, the system identifies and converts kanji characters to hiragana phonetic representation
4. The system preserves existing hiragana and katakana characters as-is during conversion
5. The system normalizes any special characters or punctuation that may affect phonetization
6. The system produces a pure hiragana representation of the text

### Phoneme Mapping Generation

7. The system analyzes all converted hiragana text to identify unique hiragana characters
8. The system creates a phoneme map assigning a unique integer ID to each hiragana character
9. The system includes all standard hiragana characters (あ, い, う, え, お, か, き, etc.)
10. The system includes hiragana digraphs (きゃ, きゅ, きょ, etc.) if present
11. The system includes special characters (っ for gemination, ん for nasal, ー for long vowels)
12. The system saves this mapping to phoneme_map.json for reference and reproducibility

### Phoneme ID Sequence Generation

13. For each hiragana transcript, the system splits the text into individual hiragana characters
14. The system looks up each hiragana character in the phoneme map
15. The system converts the character to its corresponding phoneme ID
16. The system concatenates all phoneme IDs into a space-separated sequence
17. If any character is not found in the phoneme map, the system reports an error with the problematic text

### Metadata Output

18. The system creates metadata_phonemes.csv with three columns: filename (without extension), original Japanese text, phoneme ID sequence
19. Each row corresponds to one audio file in the dataset
20. The filename column matches the WAV files exactly (without .wav extension)
21. The original Japanese text is preserved for human readability and validation
22. The phoneme ID sequence is the converted numerical representation ready for Piper

### Validation

23. The system verifies that every transcript can be phonetized without errors
24. The system reports the total number of unique phonemes found (expected approximately 100)
25. The system validates that every row in metadata_phonemes.csv has a non-empty phoneme ID sequence
26. The system checks that the number of rows in metadata_phonemes.csv matches the number of audio files
27. The system generates a validation report showing phonetization statistics (total transcripts, unique phonemes, average phoneme length, any errors)

### Error Handling

28. If kanji conversion fails for a specific character, the system reports the filename and problematic text
29. If a hiragana character is not in the phoneme map, the system reports this as an unexpected character error
30. The system provides clear error messages identifying which transcript failed and why
31. The system continues processing remaining transcripts even if some fail, reporting all errors at the end

## Acceptance Criteria

### Successful Conversion
- All 7,300 JSUT transcripts convert from kanji/kana to pure hiragana without errors
- Kanji characters are correctly converted to their hiragana pronunciation
- Existing hiragana and katakana characters are preserved accurately
- No information is lost during conversion (text remains readable and pronounceable)

### Phoneme Map Quality
- The generated phoneme_map.json contains approximately 100 unique hiragana characters
- Every hiragana character used in the transcripts appears in the phoneme map
- Each hiragana character has a unique integer ID
- The phoneme map is saved in a human-readable JSON format
- The phoneme map is deterministic (running twice produces identical results)

### Metadata Output Accuracy
- metadata_phonemes.csv exists with exactly three columns (filename, text, phoneme IDs)
- metadata_phonemes.csv contains exactly 7,300 rows (one per JSUT utterance)
- Every filename in metadata_phonemes.csv corresponds to an existing WAV file
- Every phoneme ID sequence is non-empty and contains only integers separated by spaces
- Original Japanese text is preserved exactly as it appears in the source transcripts

### Validation Success
- The validation report confirms 100% success rate (zero phonetization failures)
- The validation report shows the total count of unique phonemes
- The validation report shows statistics (average sequence length, min/max lengths)
- Any errors are clearly reported with filename and error description

### Format Compatibility
- metadata_phonemes.csv is compatible with Piper preprocessing expectations
- Phoneme IDs are sequential integers starting from a defined base (typically 0 or 1)
- The format matches other Piper phoneme datasets (e.g., format used by espeak-ng output)
- The file encoding is UTF-8 to preserve Japanese characters

### Reproducibility
- Running phonetization twice on the same dataset produces identical phoneme_map.json
- Running phonetization twice produces identical metadata_phonemes.csv
- The phoneme mapping is deterministic and stable

## Out of Scope

### Not Included in This Story
- Training the Piper model (covered by separate training story)
- Validating pronunciation accuracy against human speech (assumes conversion is correct)
- Custom phoneme adjustments or manual overrides (automated only)
- Handling multiple phonetic readings of kanji (uses most common reading)
- Accent or pitch annotation (hiragana only, no prosodic markers)
- Integration with espeak-ng (bypasses espeak-ng entirely)
- Support for languages other than Japanese (Japanese-specific implementation)
- User interface for phoneme editing (automated pipeline only)
- Audio alignment verification (assumes text matches audio correctly)

### Future Considerations
- These capabilities may be added later but are explicitly excluded now:
  - Manual phoneme correction workflow
  - Alternative kanji readings for ambiguous cases
  - Prosodic marker integration (accent, pitch, intonation)
  - Multi-language phonetization support
  - Pronunciation dictionary for exceptional cases
  - Phoneme visualization tools

## Assumptions and Constraints

### Assumptions
- The pykakasi library provides accurate kanji-to-hiragana conversion for JSUT corpus text
- Standard hiragana pronunciation is sufficient for medium-quality TTS (no need for IPA precision)
- JSUT transcripts use standard modern Japanese orthography
- Approximately 100 unique hiragana phonemes will cover all JSUT transcripts
- The default kanji reading selected by pykakasi is appropriate for the context
- metadata.csv already exists (created by Phase 2 infrastructure)
- All transcripts in metadata.csv are valid Japanese text

### Constraints
- Phonetization must complete in reasonable time (under 10 minutes for 7,300 transcripts)
- Phoneme map must not exceed 200 unique phonemes (typical hiragana coverage is ~100)
- Every transcript must successfully phonetize (zero tolerance for failures)
- The output must be compatible with Piper's preprocessing expectations
- Phoneme IDs must be non-negative integers

### Technical Constraints
- Must use pykakasi for kanji conversion (as specified in ADR-001)
- Must produce LJSPEECH-compatible metadata format
- Must preserve original Japanese text for human validation
- Phoneme IDs must be space-separated integers in the metadata file
- File encoding must be UTF-8 throughout

### Quality Constraints
- Zero phonetization failures allowed (100% success rate required)
- Phoneme map must be complete (no missing hiragana characters)
- Conversion must be deterministic (same input always produces same output)
- Metadata must match audio files exactly (no missing or extra rows)

## Implementation Status

**REAL**: This feature must be fully integrated into the main system as it is a critical step in the training pipeline. Piper cannot train without phonemized metadata.

## Success Metrics

This feature is successful when:
- A user can run a single command to phonetize all JSUT transcripts
- All 7,300 transcripts are successfully converted to phoneme ID sequences
- metadata_phonemes.csv is generated and ready for Piper preprocessing
- The phoneme map contains approximately 100 unique hiragana phonemes
- The validation report confirms zero errors
- The output is immediately usable by the next phase (Piper preprocessing)

## Dependencies

### Required Before This Story
- STORY-002: JSUT Corpus Infrastructure (must have metadata.csv and audio files)
- pykakasi library installed and functional
- Dataset structure established (dataset/wav/, metadata.csv exists)

### Required For This Story
- metadata.csv with Japanese transcripts
- Approximately 7,300 audio files in dataset/wav/
- pykakasi Python library
- Python file I/O capabilities

### Blocks These Future Stories
- STORY-004: Piper Preprocessing (requires metadata_phonemes.csv)
- STORY-005: Model Training (requires preprocessed phoneme data)
- STORY-006: Voice Quality Validation (requires trained model)

## User Workflow

### Expected User Experience

1. User has completed Phase 2 (JSUT corpus is downloaded, normalized, metadata.csv exists)
2. User runs the phonetization command: `python scripts/phonemize_japanese.py`
3. System displays progress: "Phonetizing 7,300 transcripts..."
4. System reports conversion statistics in real-time
5. System completes and displays: "Phonetization complete. Generated phoneme_map.json and metadata_phonemes.csv"
6. User verifies output by inspecting:
   - phoneme_map.json (sees approximately 100 hiragana → ID mappings)
   - metadata_phonemes.csv (sees filename, original Japanese, phoneme IDs)
   - Validation report (sees 100% success rate)
7. User proceeds to next phase (Piper preprocessing) with confidence that all transcripts are ready

### Error Scenario

1. If phonetization fails for any transcript:
2. System displays: "Error: Failed to phonetize transcript in file jsut_basic5000_0042.wav"
3. System shows the problematic text and error reason
4. System continues processing remaining files
5. System generates error report: logs/phonetization_errors.txt
6. User reviews errors and decides whether to fix source transcripts or proceed with successful subset

## User Value

This phonetization capability enables:

- Automated preparation of Japanese training data without manual phonetic transcription
- Confidence that all transcripts are correctly converted to machine-readable phoneme sequences
- Transparency into the phoneme system (phoneme_map.json is human-readable)
- Foundation for Piper training with Japanese text
- Validation that the entire corpus is phonetically processable before training begins
- Clear error reporting if any transcripts cannot be handled
- Reproducible phoneme mappings for consistent training across runs

The end result is metadata_phonemes.csv, a critical file that bridges human-readable Japanese text and machine-readable phoneme IDs, enabling Piper to learn Japanese pronunciation patterns during training.
