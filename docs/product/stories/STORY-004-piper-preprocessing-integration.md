# STORY-004: Piper Preprocessing Integration

## Title
Prepare Japanese Voice Dataset for Training

## Context / Problem
A voice dataset creator has recorded Japanese audio and generated phoneme representations for each audio file. However, this raw data cannot be directly used for training. The Piper training system requires the audio and phoneme data to be processed into a specific format with normalized audio statistics and structured metadata. Without this preprocessing step, training cannot begin.

The challenge is that the Japanese voice dataset uses a custom phoneme representation system (hiragana characters as phonemes) rather than the standard phoneme system Piper typically expects. The preprocessing must accommodate this custom phoneme mapping while still producing output compatible with Piper's training pipeline.

## User Goal
As a voice dataset creator, I want to preprocess my Japanese audio recordings and phoneme data so that the dataset becomes ready for voice model training in the Piper system.

## Functional Behavior

### Input Requirements
The user provides:
1. A collection of audio files in WAV format (22050 Hz, 16-bit PCM)
2. A phoneme metadata file (metadata_phonemes.csv) containing two columns:
   - Audio filename
   - Phoneme ID sequence (space-separated integers)
3. A phoneme mapping file (phoneme_map.json) that defines:
   - Which hiragana character corresponds to which phoneme ID
   - The complete set of phonemes used in the dataset
   - Special markers (padding, beginning/end of sequence, unknown)

### Preprocessing Steps
The system performs the following actions:

1. **Audio Analysis**
   - Examines all WAV files to calculate audio normalization statistics
   - Computes mean and standard deviation values needed for consistent audio processing
   - Validates that audio files meet format requirements (sample rate, bit depth)

2. **Dataset Structure Creation**
   - Reads the phoneme metadata file
   - Combines audio file references with their corresponding phoneme ID sequences
   - Creates a structured dataset file that links each audio sample to its phoneme representation

3. **Configuration Generation**
   - Creates a configuration file that defines:
     - The custom Japanese phoneme mapping
     - Audio processing parameters
     - Dataset structure information
     - Training-relevant metadata (language, speaker information)

4. **Validation**
   - Verifies all audio files referenced in metadata actually exist
   - Confirms phoneme ID sequences only use IDs defined in the phoneme mapping
   - Checks that generated files are complete and correctly formatted

### Output Generated
The system produces:

1. **dataset.jsonl** - A structured dataset file where each line contains:
   - Path to the audio file
   - Phoneme ID sequence for that audio
   - Audio duration and other metadata

2. **audio_norm_stats.json** - Audio normalization statistics containing:
   - Mean and standard deviation values
   - Statistics needed for consistent audio processing during training

3. **config.json** - A configuration file containing:
   - The custom Japanese phoneme mapping
   - Number of phonemes in the system
   - Audio format specifications
   - Language and speaker metadata

### User Actions Required
1. User places audio files in the dataset directory
2. User ensures metadata_phonemes.csv and phoneme_map.json are present
3. User triggers the preprocessing operation
4. User receives confirmation that preprocessing completed successfully
5. User can verify generated files are present and correctly formatted

## Acceptance Criteria

### Preprocessing Completion
- All three output files (dataset.jsonl, audio_norm_stats.json, config.json) are generated
- File generation completes without errors
- User receives clear success/failure feedback

### Data Integrity
- Every audio file referenced in metadata_phonemes.csv appears in dataset.jsonl
- Every phoneme ID in the dataset exists in the phoneme mapping
- No audio files are missing or inaccessible
- Phoneme ID sequences match exactly between input metadata and output dataset

### Format Compliance
- dataset.jsonl follows the line-delimited JSON format expected by Piper training
- Each line in dataset.jsonl is valid JSON
- audio_norm_stats.json contains valid normalization statistics
- config.json contains all required fields for Piper training

### Custom Phoneme Integration
- config.json includes the complete Japanese phoneme mapping from phoneme_map.json
- The number of phonemes in config.json matches the phoneme map
- Special phoneme markers (padding, begin/end, unknown) are correctly included
- Training system can load and interpret the custom phoneme configuration

### Audio Validation
- All audio files are 22050 Hz sample rate
- All audio files are 16-bit PCM format
- Audio files meet quality standards (duration within acceptable range)
- Audio normalization statistics are mathematically valid

### Reproducibility
- Running preprocessing twice on the same input produces identical output
- Output files are deterministic (no random variations)
- Process can be repeated without manual intervention

## Out of Scope

### Not Included in This Feature
- Creating or recording audio files (assumed to exist already)
- Generating phoneme representations from Japanese text (Phase 3 already completed)
- Running the actual model training (separate feature)
- Audio quality enhancement or noise reduction
- Audio file format conversion (input must already be correct format)
- Generating or modifying metadata_phonemes.csv (assumed complete)
- Phoneme mapping creation (phoneme_map.json assumed ready)
- Multi-speaker dataset handling (single speaker only)
- Incremental preprocessing (always processes complete dataset)
- Preprocessing validation against external standards beyond Piper requirements

### Future Enhancements Not Covered
- Automatic detection of audio format issues with correction suggestions
- Preview mode to inspect preprocessing results before committing
- Partial dataset preprocessing (processing only new/changed files)
- Statistical reporting on dataset characteristics
- Visual inspection tools for preprocessed data

## Assumptions and Constraints

### Assumptions
1. Audio files are already recorded and present in the dataset directory
2. metadata_phonemes.csv is complete and accurate
3. phoneme_map.json correctly represents the Japanese phoneme system being used
4. All audio files are already in the correct format (22050 Hz, 16-bit PCM WAV)
5. The user has sufficient disk space for preprocessed output files
6. The dataset represents a single speaker (not multi-speaker)
7. Phoneme ID sequences in metadata are valid (no references to undefined phonemes)

### Constraints
1. Audio must be exactly 22050 Hz sample rate (no other sample rates accepted)
2. Audio must be 16-bit PCM WAV format (no other formats accepted)
3. Dataset size is limited by available disk space and memory
4. Processing time scales linearly with number of audio files
5. All audio files must be accessible from a single directory structure
6. Phoneme IDs must be non-negative integers
7. The custom phoneme system must use hiragana characters as the base representation
8. Output files must be compatible with Piper's training pipeline expectations

### Technical Dependencies
1. The Piper preprocessing system must support custom phoneme mappings
2. The system must be able to read and parse the custom phoneme_map.json format
3. Audio processing libraries must be available for statistics calculation
4. File system must support the required directory structure

## Implementation Status
**REAL** - This is core functionality required for the Japanese voice training pipeline. Preprocessing is a mandatory step between dataset preparation and model training.

## Related Stories
- **STORY-001**: Audio quality validation (provides validated audio input)
- **STORY-002**: Japanese text to phoneme conversion (provides phoneme metadata input)
- **STORY-003**: Phoneme mapping generation (provides phoneme_map.json input)
- **STORY-005**: Voice model training (consumes preprocessing output) [Future]

## Success Metrics
- Preprocessing completes without errors on a valid dataset
- Generated files are accepted by Piper training system
- Processing time is reasonable (under 1 minute per 100 audio samples as guideline)
- Zero data loss (all input audio samples appear in output dataset)
- Configuration correctly represents the custom Japanese phoneme system
