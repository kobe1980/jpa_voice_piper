# STORY-001: Japanese Voice Training with JSUT Corpus for Piper TTS

## Context / Problem

The Piper TTS ecosystem currently has **no Japanese voice models** available. Japanese speakers who want to use Piper for text-to-speech face a complete absence of options:

- Zero Japanese voices exist in the official Piper repository
- No documented process for creating Japanese voices with Piper
- Japanese phonetization is challenging (espeak-ng has poor Japanese support)
- Complex writing system (kanji, hiragana, katakana) requires special handling

This creates a significant barrier for Japanese-speaking users and developers who want natural-sounding text-to-speech for accessibility, education, content creation, or voice interfaces.

## User Goal

As a Japanese-speaking user or developer, I want access to a natural-sounding Japanese voice for Piper TTS so that I can:

- Build accessible applications for visually impaired Japanese speakers
- Create educational content with clear Japanese narration
- Develop voice interfaces for Japanese-language applications
- Generate audiobook or podcast content in Japanese
- Prototype voice-enabled products for the Japanese market

The voice should sound natural, pronounce Japanese correctly, and handle mixed kanji/kana text appropriately.

## Functional Behavior

### Phase 1: JSUT Corpus Acquisition and Preparation

1. Download the JSUT (Japanese speech corpus of Saruwatari Lab, University of Tokyo) dataset
   - ~7,300 utterances
   - ~10 hours of speech
   - Single female speaker
   - Studio quality, 48kHz recordings
   - CC BY-SA 4.0 license (open source compatible)

2. Organize corpus into standardized structure
   - Extract audio files
   - Parse transcript files (transcript_utf8.txt format)
   - Verify file integrity and completeness

3. Normalize audio to Piper requirements
   - Convert from 48kHz to 22050Hz
   - Ensure mono channel
   - Trim excessive silence
   - WAV 16-bit PCM format

### Phase 2: Japanese Phonetization Strategy

**Challenge**: espeak-ng does not support Japanese well.

**Solution**: Use hiragana directly as phonemes (proven effective approach).

1. Convert kanji to hiragana using pykakasi library
2. Use hiragana characters as phoneme symbols
3. Create phoneme mapping: hiragana → phoneme IDs
4. Generate metadata_phonemes.csv with phoneme ID sequences

### Phase 3: Training Preparation

1. Create LJSPEECH-format metadata: `audio.wav|Japanese text`
2. Prepare phonemized metadata: `audio.wav|Japanese text|phoneme IDs`
3. Generate phoneme_map.json (~100 unique hiragana phonemes)
4. Configure Piper training parameters for Japanese

### Phase 4: Model Training

1. Download French checkpoint for fine-tuning (fr_FR-siwis-medium)
   - Transfer learning significantly reduces training time
   - French prosody patterns transfer reasonably to Japanese

2. Train voice model using Piper training tools
   - Batch size: 16-32
   - Max epochs: 1000+
   - Checkpoint every 10 epochs
   - Monitor with TensorBoard

3. Export trained model to ONNX format
   - ja_JP-jsut-medium.onnx
   - ja_JP-jsut-medium.onnx.json

### Phase 5: Voice Testing and Validation

1. Test synthesis with common Japanese phrases:
   - "こんにちは" (Hello)
   - "ありがとうございます" (Thank you)
   - "さようなら" (Goodbye)

2. Validate intelligibility and naturalness
3. Package model for distribution

## Acceptance Criteria

### Corpus Setup
- JSUT corpus downloaded successfully (~7,300 files)
- All audio files verified and accessible
- Transcripts extracted and parsed correctly

### Audio Quality
- All audio normalized to 22050Hz mono WAV 16-bit PCM
- Signal-to-noise ratio ≥ 30 dB
- No clipping (peak amplitude < 0.95)
- Duration 1-15 seconds per sample
- Minimal silence (<0.3s at start/end)

### Phonetization System
- pykakasi successfully converts all kanji to hiragana
- Phoneme map contains ~100 unique hiragana characters
- metadata_phonemes.csv generated with phoneme ID sequences
- All texts phonetizable without errors

### Training Readiness
- Preprocessing completes without errors
- config.json generated with Japanese parameters
- dataset.jsonl created with phoneme sequences
- French checkpoint downloaded and ready

### Voice Model Output
- Training completes successfully (minimum 100 epochs)
- Model exported to ONNX format
- Test synthesis produces intelligible Japanese speech
- Voice sounds natural and recognizably Japanese

### Documentation
- Step-by-step guide for reproducing the process
- Phonemization approach documented (hiragana strategy)
- Training parameters and decisions explained
- Examples of successful synthesis provided

## Out of Scope

This initial voice does NOT include:

- Multiple speakers or voice personas
- Regional Japanese dialects (Tokyo accent only)
- Emotional expression or prosody control
- Real-time synthesis optimization
- Automatic transcription or speech recognition
- Katakana loanword special handling (uses standard hiragana conversion)
- Custom phoneme system beyond hiragana
- Commercial distribution framework
- Mobile/embedded optimization

## Assumptions and Constraints

### Assumptions
- JSUT corpus is publicly available and downloadable
- French checkpoint (fr_FR-siwis-medium) provides good starting point
- Hiragana-as-phonemes approach is sufficient for medium quality
- 10 hours of data is adequate for medium-quality voice
- Training hardware has GPU/MPS acceleration (training on CPU too slow)
- Model will be contributed to open source community

### Constraints
- Must use official Piper training procedures
- Must follow LJSPEECH dataset format
- Phonetization limited to pykakasi capabilities
- Training time: 2-5 days depending on hardware
- Model quality depends on JSUT corpus quality (single speaker, studio recording)
- macOS M1/M2/M3 MPS acceleration works but slower than CUDA

### Quality Constraints
- No degradation of JSUT source audio quality
- Every audio file must pass quality validation
- Phoneme mapping must be deterministic and consistent
- Training must converge (loss decreases consistently)

## Implementation Status

REAL - Foundation layer complete (domain entities, quality validation framework).
INCOMPLETE - Infrastructure adapters, phonetization, training coordination not yet implemented.

## Success Metrics

The Japanese voice is successful when:

1. JSUT corpus fully preprocessed and validated (7,300 samples)
2. Phonetization converts 100% of texts to hiragana phoneme IDs
3. Training converges with decreasing loss over 500+ epochs
4. Synthesized Japanese speech is intelligible to native speakers
5. Voice model passes quality assessment (MOS > 3.0 for medium quality)
6. Model and documentation ready for open source contribution to Piper

## User Value

This Japanese voice enables:

- First Japanese TTS option in open source Piper ecosystem
- Japanese-speaking community access to free, quality TTS
- Developers to build Japanese voice interfaces without licensing costs
- Content creators to generate Japanese narration for media
- Educational institutions to create Japanese learning materials
- Researchers to experiment with Japanese TTS
- Foundation for future Japanese voice improvements and variations

The end result is a trained Japanese voice model (ja_JP-jsut-medium) that anyone can download and use with Piper TTS, filling a critical gap in the Piper language portfolio.

## Technical Approach Highlights

**Phonetization Strategy**: Hiragana-as-phonemes
- Advantage: Simple, deterministic, no espeak-ng dependency
- Trade-off: Less control over pronunciation nuances
- Precedent: Successfully used in other Japanese TTS projects

**Transfer Learning**: Start from French checkpoint
- Advantage: Faster convergence, reduced training time
- Rationale: French prosody patterns transfer reasonably to Japanese
- Alternative considered: Training from scratch (much slower)

**Corpus Choice**: JSUT
- Advantage: High quality, open license, well-documented
- Size: ~10 hours (adequate for medium quality voice)
- Speaker: Single female (consistency)
