# STORY-002: JSUT Corpus Infrastructure

## Context / Problem

The JSUT (Japanese Speech corpus from the University of Tokyo) is a high-quality Japanese speech dataset containing approximately 10 hours of studio-recorded speech from a single female speaker with a Tokyo accent. This corpus is publicly available under CC BY-SA 4.0 license and represents an ideal foundation for training a Japanese Piper TTS voice.

However, using this corpus requires several preparation steps: downloading from the official source, verifying file integrity, parsing non-standard transcript formats, converting audio files from their original 48kHz format to Piper's requirements (22050Hz), and organizing everything into the standardized LJSPEECH structure that Piper expects.

Currently, there is no automated way to perform these preparation steps. Users must manually download, extract, parse, convert, and organize approximately 7,300 audio files and their transcripts, which is error-prone and time-consuming.

## User Goal

As a user preparing to train a Japanese voice for Piper TTS, I want to automatically download and prepare the JSUT corpus so that I have a properly formatted, validated dataset ready for training without manual intervention.

## Functional Behavior

### Download and Verification

1. The system provides a command to initiate JSUT corpus preparation
2. The system downloads the JSUT corpus archive from the official University of Tokyo source
3. The system verifies the download integrity by checking file size and optional checksum
4. The system extracts the archive to a temporary working location
5. The system verifies the expected corpus structure is present (multiple folders, transcript files, WAV files)
6. The system counts the total number of utterances and confirms it matches expected values (approximately 7,300 files)

### Transcript Parsing

7. The system locates all transcript files named `transcript_utf8.txt` across all subfolders
8. For each transcript file, the system parses each line in the format `AUDIO_ID:transcript_text`
9. The system validates that each audio ID corresponds to an existing WAV file
10. The system reports any missing audio files or orphaned transcripts
11. The system aggregates all transcript entries into a single unified list

### Audio Normalization

12. For each audio file, the system reads the original 48kHz WAV file
13. The system resamples the audio to 22050Hz (Piper standard)
14. The system converts to mono if the audio is stereo
15. The system trims silence from the beginning and end of the audio
16. The system normalizes the volume to a consistent level
17. The system validates audio quality (SNR, clipping, duration constraints)
18. The system saves the normalized audio to the standardized location

### Dataset Organization

19. The system creates a standardized directory structure (dataset/raw/, dataset/wav/)
20. The system copies original audio files to dataset/raw/ as permanent backups
21. The system saves normalized audio files to dataset/wav/ with standardized naming
22. The system generates metadata.csv in LJSPEECH format with columns: filename (without extension), transcript
23. The system generates a validation report showing total utterances, total duration, quality metrics
24. The system preserves the original JSUT folder structure in dataset/raw/jsut/ for reference

### Progress and Reporting

25. The system displays progress during download (percentage, transfer rate)
26. The system displays progress during processing (files processed, estimated time remaining)
27. The system logs all operations to a preparation log file
28. The system provides a final summary report with statistics (total files, total duration, quality pass rate, any errors)

## Acceptance Criteria

### Download Success
- The JSUT corpus archive downloads completely from the official source
- The downloaded file size matches the expected size (within tolerance)
- The archive extracts without errors

### Corpus Validation
- The system identifies all expected JSUT subfolders (BASIC5000, ONOMATOPOEPIA300, etc.)
- The system finds approximately 7,300 audio files
- The system finds corresponding transcript files for all subfolders
- The system reports zero missing audio-transcript pairs

### Audio Quality
- All normalized audio files are 22050Hz, 16-bit PCM, mono WAV format
- All normalized audio files pass quality validation (SNR greater than 30dB, no clipping, appropriate duration)
- Silence is trimmed from beginning and end (less than 0.3 seconds of silence)
- Volume is normalized consistently across all files

### Dataset Structure
- The file `dataset/raw/jsut/` contains original JSUT structure as backup
- The file `dataset/wav/` contains exactly one normalized WAV file per utterance
- The file `metadata.csv` exists in LJSPEECH format
- The file `metadata.csv` contains exactly the same number of rows as there are WAV files
- Each row in metadata.csv references an existing WAV file
- All transcript text in metadata.csv is valid UTF-8 encoded Japanese

### Metadata Accuracy
- Each metadata.csv entry correctly maps to its corresponding audio file
- Transcript text matches the original JSUT transcript exactly (no corruption)
- Filename format is consistent (e.g., jsut_basic5000_0001.wav)

### Reporting
- A preparation log file documents all operations performed
- A validation report summarizes total files, duration, quality metrics
- Any errors or warnings are clearly reported with file names and error types

### Reproducibility
- Running the preparation command multiple times produces identical results
- The preparation can be interrupted and resumed without data corruption
- Previously prepared data can be detected and skipped or overwritten based on user preference

## Out of Scope

### Not Included in This Story
- Training the actual Piper model (covered by separate training story)
- Multi-speaker handling (JSUT is single-speaker only)
- Support for other Japanese corpora (this story is JSUT-specific)
- Manual recording tools (this story uses existing corpus only)
- Phonetic validation with espeak-ng (Japanese phonetics may require different tooling)
- Custom audio quality thresholds (uses project-wide defaults from configs/audio_quality.yaml)
- User interface beyond command-line (CLI only)
- Automatic retry of failed downloads (user must retry manually)
- Differential updates (always processes entire corpus)
- Subset selection (processes all JSUT utterances)

### Future Considerations
- These capabilities may be added in later stories but are explicitly excluded now:
  - Support for additional Japanese corpora (JVS, JSSS, etc.)
  - Advanced Japanese phonetic validation
  - Custom quality threshold configuration per corpus
  - Web interface for preparation monitoring
  - Incremental processing of new corpus additions

## Assumptions and Constraints

### Assumptions
- The official JSUT corpus URL remains accessible and stable
- The corpus structure (folder names, transcript format) remains consistent with current version
- The user has sufficient disk space (approximately 15GB: 5GB download, 5GB extracted, 5GB normalized)
- The user has a working internet connection for download
- The system has necessary audio processing libraries installed (librosa, soundfile)
- Japanese text encoding is UTF-8 throughout the corpus

### Constraints
- Processing time depends on system performance (estimated 30-60 minutes for full corpus)
- Audio normalization is CPU-intensive and may not be interruptible
- Temporary disk space must be available during processing
- The original JSUT license (CC BY-SA 4.0) must be preserved and documented
- Network bandwidth affects download time
- Sample rate conversion from 48kHz to 22050Hz is lossy by nature

### Technical Constraints
- Must respect Piper audio requirements (22050Hz, 16-bit PCM, mono)
- Must conform to LJSPEECH metadata format for Piper compatibility
- Must maintain audio quality standards defined in project guardrails
- Must preserve original files as permanent backups per project rules

## Implementation Status

**REAL**: This feature must be fully integrated into the main system as it provides the foundational dataset for the Japanese voice training pipeline. Without this infrastructure, no training can proceed.

## Success Metrics

This feature is successful when:
- A user can run a single command and obtain a fully prepared JSUT dataset
- The entire preparation process completes without manual intervention
- The resulting dataset passes all quality validations
- The metadata.csv format is immediately usable by Piper preprocessing
- The preparation log provides clear troubleshooting information if any issues occur

## Dependencies

### Required Before This Story
- Phase 1 foundation (project structure, base configuration)
- Audio quality validation infrastructure
- Audio normalization utilities

### Required For This Story
- Internet connectivity for corpus download
- Sufficient disk space (15GB minimum)
- Python audio processing libraries (librosa, soundfile)
- Standard file I/O capabilities

### Blocks These Future Stories
- STORY-003: Training pipeline (requires prepared dataset)
- STORY-004: Quality evaluation (requires trained model from prepared dataset)
