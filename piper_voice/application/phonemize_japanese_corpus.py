"""Application use case for phonemizing Japanese corpus.

This use case orchestrates the two-pass phonemization process:
1. Pass 1: Convert kanji → hiragana for all texts
2. Build PhonemeMap from unique hiragana characters
3. Pass 2: Convert hiragana → phoneme IDs

Follows DDD: Application layer orchestrates domain entities and infrastructure adapters.
"""

from dataclasses import dataclass, field
from pathlib import Path

from piper_voice.core.entities import PhonemeMap
from piper_voice.core.ports import KanjiConverterPort
from piper_voice.core.value_objects import HiraganaText
from piper_voice.infrastructure.phonetics.hiragana_phonetizer import HiraganaPhonetizer


@dataclass(frozen=True)
class PhonemeCorpusConfig:
    """Configuration for corpus phonemization.

    Attributes:
        input_metadata: Path to input metadata.csv (audio_file|japanese_text)
        output_metadata: Path to output metadata_phonemes.csv (audio_file|phoneme_ids)
        phoneme_map_output: Path to output phoneme_map.json
    """

    input_metadata: Path
    output_metadata: Path
    phoneme_map_output: Path


@dataclass
class PhonemeResult:
    """Result of corpus phonemization.

    Attributes:
        total_samples: Total number of samples processed
        successful: Number of successfully phonemized samples
        failed: Number of failed samples
        phoneme_count: Total number of unique phonemes in map
        errors: List of error messages for failed samples
    """

    total_samples: int
    successful: int
    failed: int
    phoneme_count: int
    errors: list[str] = field(default_factory=list)


def phonemize_japanese_corpus(
    config: PhonemeCorpusConfig,
    kanji_converter: KanjiConverterPort,
) -> PhonemeResult:
    """Phonemize Japanese corpus in two passes.

    Pass 1: Convert all Japanese text to hiragana
    Pass 2: Build phoneme map and convert hiragana to phoneme IDs

    Args:
        config: Configuration for input/output paths
        kanji_converter: Adapter for kanji→hiragana conversion

    Returns:
        PhonemeResult with statistics and errors

    Raises:
        ValueError: If no samples found in input
        FileNotFoundError: If input metadata doesn't exist
    """
    # Validate input exists
    if not config.input_metadata.exists():
        raise FileNotFoundError(f"Input metadata not found: {config.input_metadata}")

    # Load input metadata
    lines = config.input_metadata.read_text(encoding="utf-8").strip().split("\n")
    if not lines or (len(lines) == 1 and not lines[0]):
        raise ValueError("No samples found in input metadata")

    samples: list[tuple[str, str]] = []
    for line in lines:
        if not line.strip():
            continue
        parts = line.split("|")
        if len(parts) != 2:
            continue
        audio_file, japanese_text = parts
        samples.append((audio_file, japanese_text))

    if not samples:
        raise ValueError("No samples found in input metadata")

    # Pass 1: Convert all texts to hiragana
    hiragana_texts: list[tuple[str, HiraganaText]] = []
    errors: list[str] = []

    for audio_file, japanese_text in samples:
        try:
            hiragana = kanji_converter.convert_to_hiragana(japanese_text)
            hiragana_texts.append((audio_file, hiragana))
        except Exception as e:
            errors.append(f"{audio_file}: {e}")

    # Build phoneme map from all unique hiragana characters
    all_hiragana = [hiragana for _, hiragana in hiragana_texts]
    phoneme_map = PhonemeMap.build_from_texts(all_hiragana)

    # Create phonetizer with the built map
    phonetizer = HiraganaPhonetizer(phoneme_map)

    # Pass 2: Convert hiragana to phoneme IDs
    output_lines: list[str] = []

    for audio_file, hiragana in hiragana_texts:
        try:
            sequence = phonetizer.phonemize(hiragana)
            phoneme_ids_str = sequence.to_string()
            output_lines.append(f"{audio_file}|{phoneme_ids_str}")
        except Exception as e:
            errors.append(f"{audio_file}: {e}")

    # Save output metadata
    config.output_metadata.write_text("\n".join(output_lines) + "\n", encoding="utf-8")

    # Save phoneme map
    phoneme_map.save_to_json(config.phoneme_map_output)

    # Return results
    return PhonemeResult(
        total_samples=len(samples),
        successful=len(output_lines),
        failed=len(errors),
        phoneme_count=len(phoneme_map.phonemes),
        errors=errors,
    )
