# STORY-001: French Voice Dataset Foundation for Piper TTS

## Context / Problem

The Piper TTS ecosystem currently has limited high-quality French voice options available to the open source community. French speakers who want to use Piper for text-to-speech applications face several challenges:

- Limited choice of French voices with natural pronunciation
- Inconsistent audio quality across available French models
- Difficulty finding voices suitable for professional applications (accessibility tools, educational software, audiobook narration)
- Lack of documented, reproducible processes for creating new French voices

This creates a barrier for French-speaking users and developers who want to integrate natural-sounding text-to-speech into their applications, whether for accessibility needs, content creation, or user interface enhancement.

## User Goal

As a French-speaking user or developer, I want access to a high-quality, natural-sounding French voice for Piper TTS so that I can:

- Build accessible applications for visually impaired French speakers
- Create educational content with clear, understandable narration
- Develop voice interfaces for French-language applications
- Generate audiobook or podcast content in French
- Prototype voice-enabled products without expensive commercial TTS licenses

The voice should sound natural, be easily understandable, and work reliably across different types of French text (formal writing, casual speech, technical content, literature).

## Functional Behavior

### Phase 1: Dataset Preparation Infrastructure

1. The system provides a structured workspace where audio recordings can be organized and managed
2. Each audio recording is stored with its corresponding French text transcription
3. The system automatically validates that each audio file meets minimum quality standards before accepting it into the dataset
4. Quality validation checks include:
   - Audio format is correct and compatible with Piper
   - Recording duration is appropriate (not too short or too long)
   - Audio volume is consistent and not distorted
   - Background noise is minimal
   - No clipping or digital artifacts are present
   - Silence at the beginning and end is minimal
5. The system rejects audio files that do not meet quality standards and explains what is wrong
6. Accepted audio files are organized in a structure that Piper can process

### Phase 2: Transcription Quality Assurance

1. Each text transcription is validated to ensure it matches the audio content
2. The system verifies that French text can be correctly converted to phonetic representation
3. Phonetic validation uses standard French pronunciation rules
4. The system detects and flags transcription errors or ambiguous pronunciations
5. All text-audio pairs are organized in a standardized metadata format

### Phase 3: Training Preparation

1. The complete dataset is preprocessed into the format required by Piper training tools
2. A configuration file is generated that specifies the voice characteristics
3. The system verifies that all components are ready for model training
4. A validation report confirms dataset completeness and quality metrics

### Phase 4: Voice Model Creation

1. The Piper training process uses the prepared dataset to create a voice model
2. Training progress can be monitored to understand model quality improvement
3. The system periodically saves training checkpoints in case of interruption
4. When training completes, the voice model is exported in a format ready for use

### Phase 5: Voice Testing and Validation

1. The trained voice model can generate speech from new French text not in the training dataset
2. Sample audio outputs demonstrate the voice quality and naturalness
3. The voice performs correctly on different types of French content:
   - Simple sentences
   - Complex sentences with varied punctuation
   - Numbers and dates
   - Common French names and places
   - Technical or specialized vocabulary
4. The final voice model is packaged with all necessary files for distribution

## Acceptance Criteria

### Dataset Infrastructure
- A directory structure exists for organizing raw recordings, processed audio, and metadata
- Audio validation automatically runs on new files and produces clear pass/fail results
- Quality validation reports specify exactly which criteria failed for rejected files
- At least 100 sample audio files can be successfully validated and organized

### Quality Standards
- All accepted audio files are WAV format, 16-bit PCM
- Sample rate is 22050 Hz
- Signal-to-noise ratio is at least 30 dB
- No clipping is detected (peak amplitude below 0.95)
- Each recording is between 1 and 15 seconds in duration
- Leading and trailing silence is less than 0.3 seconds

### Transcription Format
- Metadata file follows LJSPEECH format specification
- Each audio file has exactly one corresponding text transcription
- All French text passes phonetic validation using standard French pronunciation rules
- Special characters, numbers, and punctuation are handled appropriately

### Training Readiness
- Preprocessing generates all files required by Piper training tools without errors
- Configuration file specifies French language and appropriate voice parameters
- Dataset validation confirms at least 5 hours of usable audio (recommended minimum)
- All validation checks pass with 100% success rate

### Voice Model Output
- Training process completes and produces a model checkpoint
- Model is successfully exported to ONNX format
- Exported model includes required configuration JSON file
- Test synthesis command produces audible French speech from text input
- Generated speech is intelligible and recognizably French

### Documentation
- Clear instructions exist for recording new audio samples
- Quality criteria are documented so a non-technical person can understand them
- Process for adding new transcriptions is documented step-by-step
- Examples of good and bad audio quality are provided for reference

## Out of Scope

This initial foundation does NOT include:

- Multiple voice personas or styles (single voice only)
- Real-time recording interface or mobile app
- Automatic transcription generation from audio (transcripts must be provided manually)
- Advanced voice characteristics (emotional expression, prosody control, speaking rate control)
- Multi-speaker support or voice cloning from small samples
- Commercial distribution or licensing framework
- Web-based interface for dataset management
- Automatic translation from other languages
- Regional French accent variations (standard/neutral French only)
- Voice quality comparison with commercial TTS systems
- Performance optimization for embedded or mobile devices

## Assumptions and Constraints

### Assumptions
- Audio recordings will be provided by a human speaker reading prepared French text
- The speaker has clear pronunciation and a neutral French accent
- Recording environment can achieve at least 30 dB signal-to-noise ratio
- Transcriptions are manually verified for accuracy before being added to dataset
- Target dataset size is between 10-20 hours of audio for production-quality voice
- Computing resources are available for training (GPU access preferred but not required)
- The voice will be contributed to the open source community under an appropriate license

### Constraints
- Must follow official Piper training procedures exactly (no custom modifications)
- Dataset format must be LJSPEECH-compatible for Piper compatibility
- All audio processing must preserve quality and avoid introducing artifacts
- System must work on macOS environment
- Phonetic validation is limited to what espeak-ng supports for French
- Training time may be several hours to days depending on dataset size and hardware
- Model quality depends directly on dataset quality and size (minimum 5 hours recommended, 10+ hours for good quality)

### Quality Constraints
- No degradation of source audio quality is acceptable during processing
- Every audio file must pass all quality checks (no exceptions)
- Failed quality checks must halt processing until issues are corrected
- Original recordings must never be deleted or overwritten (permanent backup)

## Implementation Status

REAL - This feature is the foundation of the entire project and must be fully integrated into the core system. All subsequent work depends on this foundation being solid, tested, and reliable.

## Success Metrics

The foundation is successful when:

1. A non-technical person can follow documentation to record and submit audio samples
2. Quality validation automatically catches all common recording problems
3. At least 100 validated audio samples exist in the dataset with perfect quality scores
4. The complete pipeline from raw recording to trained model executes without manual intervention
5. Test synthesis produces intelligible French speech that correctly pronounces sample sentences
6. The dataset and trained model are ready for open source contribution

## User Value

This foundation enables:

- French-speaking communities to have free, high-quality text-to-speech technology
- Developers to build accessible French-language applications without licensing costs
- Content creators to generate French narration for videos, podcasts, and audiobooks
- Educational institutions to create learning materials with consistent voice quality
- Researchers to experiment with French TTS without commercial restrictions
- The open source community to benefit from a documented, reproducible voice creation process

The end result is a trained French voice model that anyone can download and use with Piper TTS, accompanied by complete documentation and a dataset that demonstrates best practices for future voice contributions.
