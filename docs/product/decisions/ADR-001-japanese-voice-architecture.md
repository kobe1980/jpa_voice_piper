# ADR-001: Japanese Voice Architecture and Phonetization Strategy

**Status**: ACCEPTED
**Date**: 2026-03-08
**Deciders**: Architect
**Related**: STORY-001-japanese-voice-jsut.md

---

## Context

We need to train the first Japanese voice for Piper TTS using the JSUT corpus. Japanese presents unique challenges:

1. **Phonetization Challenge**: espeak-ng has poor Japanese support
2. **Writing System Complexity**: Mixed kanji, hiragana, katakana
3. **No Existing Japanese Voices**: No precedent in Piper ecosystem
4. **Training Time**: Limited computational resources (macOS MPS)

We must decide:
- How to handle Japanese phonetization
- Which corpus to use
- Training strategy (from scratch vs transfer learning)
- Architecture and security guardrails

---

## Decision

### 1. Phonetization: Hiragana-as-Phonemes

**Decision**: Use hiragana characters directly as phoneme symbols, bypassing espeak-ng entirely.

**Rationale**:
- espeak-ng Japanese support is inadequate
- Hiragana represents Japanese phonology naturally (~100 symbols)
- Proven approach in other Japanese TTS systems
- Simpler than building custom phoneme system
- Deterministic conversion using pykakasi

**Implementation**:
```python
# Convert text → hiragana → phoneme IDs
import pykakasi
kks = pykakasi.kakasi()
result = kks.convert("東京")  # kanji
hiragana = ''.join([item['hira'] for item in result])  # → "とうきょう"
phoneme_ids = [phoneme_map[char] for char in hiragana]
```

**Trade-offs**:
- ✅ Simple, deterministic, no espeak dependency
- ✅ ~100 phonemes (manageable for training)
- ❌ Less fine-grained control than IPA phonemes
- ❌ May miss some pronunciation nuances

### 2. Corpus: JSUT (Japanese Speech Corpus)

**Decision**: Use JSUT corpus from University of Tokyo.

**Specifications**:
- **Size**: ~7,300 utterances, ~10 hours
- **Speaker**: Single female, Tokyo accent
- **Quality**: Studio recording, 48kHz
- **License**: CC BY-SA 4.0 (open source compatible)
- **Source**: https://sites.google.com/site/shinnosuketakamichi/research-topics/jsut-corpus

**Rationale**:
- High quality, professionally recorded
- Open license allows redistribution
- Well-documented and widely used
- Single speaker ensures consistency
- Adequate size for medium-quality voice (10h)

### 3. Transfer Learning: French Checkpoint

**Decision**: Start training from French checkpoint (`fr_FR-siwis-medium.ckpt`).

**Rationale**:
- Transfer learning significantly reduces training time (days → hours)
- French prosody patterns transfer reasonably to Japanese
- Lower computational requirements (feasible on macOS MPS)
- Piper supports checkpoint-based fine-tuning

**Alternative Considered**: Training from scratch
- ❌ Much longer training time (weeks on MPS)
- ❌ Higher computational requirements
- ❌ No advantage for medium-quality target

### 4. Architecture: Maintain DDD Foundation

**Decision**: Keep existing domain layer, add Japanese-specific infrastructure.

**Domain Layer** (unchanged):
- Voice, AudioSample, Transcript, Phoneme entities
- Quality validation (SNR, clipping, duration)
- Ports for infrastructure

**Infrastructure Additions** (new):
- `pykakasi_adapter.py`: Kanji → hiragana conversion
- `hiragana_phonetizer.py`: Hiragana → phoneme IDs
- `jsut_loader.py`: JSUT corpus file parsing
- `japanese_metadata.py`: Japanese-specific metadata handling

**Application Layer**:
- `download_jsut.py`: Corpus download orchestration
- `prepare_jsut_dataset.py`: JSUT-specific preparation
- `phonemize_japanese.py`: Japanese phonetization pipeline

### 5. Audio Quality Standards

**Decision**: Same strict standards as original plan.

- **Format**: WAV 16-bit PCM
- **Sample Rate**: 22050 Hz (downsample from JSUT's 48kHz)
- **SNR**: ≥ 30 dB
- **Duration**: 1-15 seconds per sample
- **No Clipping**: Peak amplitude < 0.95
- **Minimal Silence**: < 0.3s at start/end

**Rationale**: JSUT is high quality, should meet all standards after normalization.

### 6. Security Guardrails

**Allowed Paths**:
- `dataset/`, `training/`, `models/`, `checkpoints/`, `logs/`
- `scripts/`, `piper_voice/`, `tests/`, `configs/`, `docs/`

**Forbidden**:
- `$HOME`, `/`, SSH keys, secrets

**Read-Only**:
- `dataset/raw/` (JSUT source, never modify)

**File Limits**:
- Max 5 MB per WAV file
- Max 1000 samples per batch processing

### 7. Testing Strategy

**Unit Tests** (TDD):
- pykakasi conversion (kanji → hiragana)
- Hiragana phonetization (hiragana → IDs)
- Phoneme map generation
- JSUT metadata parsing

**Integration Tests**:
- Full pipeline: JSUT → normalized audio → metadata_phonemes.csv
- Piper preprocessing on prepared dataset
- ONNX export and synthesis test

**Validation Tests**:
- All 7,300 JSUT samples phonetize successfully
- Phoneme map covers all unique hiragana
- Generated metadata.csv is LJSPEECH-compliant

---

## Consequences

### Positive

✅ **Feasibility**: Hiragana approach is simple and proven
✅ **Speed**: Transfer learning makes training feasible on MPS
✅ **Quality**: JSUT corpus is high quality, open license
✅ **Foundation**: Domain layer is reusable for other languages
✅ **Community**: First Japanese voice for Piper ecosystem

### Negative

❌ **Pronunciation Limitations**: Hiragana less precise than IPA
❌ **Single Speaker**: No voice diversity (one female voice)
❌ **Training Time**: Still 2-5 days on macOS MPS
❌ **Model Quality**: Medium quality (not commercial-grade)
❌ **Katakana Handling**: Standard hiragana conversion may miss loanword nuances

### Risks

1. **pykakasi Accuracy**: Kanji → hiragana conversion may have errors
   - Mitigation: Validate all conversions, manual review of problematic cases

2. **Transfer Learning Mismatch**: French → Japanese may not transfer well
   - Mitigation: Monitor training loss, ready to train from scratch if needed

3. **JSUT Download**: Corpus may become unavailable
   - Mitigation: Mirror corpus locally, document alternative sources

---

## Implementation Plan (6 Phases)

### Phase 1: Foundation ✅ COMPLETE
- Domain entities, value objects, ports
- Test suite, quality gates
- **Status**: 100% complete

### Phase 2: JSUT Infrastructure (Week 1)
- Download and extract JSUT corpus
- Audio normalization (48kHz → 22050Hz)
- JSUT metadata parsing

### Phase 3: Japanese Phonetization (Week 1-2)
- pykakasi integration
- Hiragana phonetizer
- Phoneme map generation
- metadata_phonemes.csv creation

### Phase 4: Training Preparation (Week 2)
- Piper preprocessing pipeline
- French checkpoint download
- Training configuration

### Phase 5: Model Training (Week 2-3)
- Launch training with checkpoint
- Monitor TensorBoard
- Checkpoint management

### Phase 6: Export and Validation (Week 3)
- ONNX export
- Synthesis testing
- Quality validation
- Documentation

**Total Timeline**: 3-4 weeks

---

## Technical Decisions Summary

| Decision | Choice | Alternative Considered |
|----------|--------|----------------------|
| Phonetization | Hiragana-as-phonemes | espeak-ng, custom IPA |
| Corpus | JSUT (10h, female) | Record custom, use JVS |
| Training Strategy | Transfer from French | Train from scratch |
| Sample Rate | 22050 Hz | 16000 Hz, 48000 Hz |
| Architecture | DDD (domain/app/infra) | Monolithic scripts |
| Testing | TDD strict (90% coverage) | Ad-hoc testing |
| Security | Filesystem guardrails | No restrictions |

---

## References

- [JSUT Corpus](https://sites.google.com/site/shinnosuketakamichi/research-topics/jsut-corpus)
- [pykakasi Library](https://github.com/miurahr/pykakasi)
- [Piper Training](https://github.com/OHF-voice/piper1-gpl)
- [VITS Architecture](https://arxiv.org/abs/2106.06103)
- Original plan: `docs/plans/active/plan_japanese_voice_training.md`

---

**This ADR is the architectural authority for the Japanese voice project.**
All implementation must follow these decisions. Deviations require new ADR.
