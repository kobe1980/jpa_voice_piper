"""Integration test for phonemizing JSUT-like corpus.

This test validates the phonemization system on a realistic Japanese corpus
similar to JSUT (7,300 transcripts).
"""

from pathlib import Path

from piper_voice.application.phonemize_japanese_corpus import (
    PhonemeCorpusConfig,
    phonemize_japanese_corpus,
)
from piper_voice.infrastructure.phonetics.pykakasi_adapter import PykakasiAdapter


class TestPhonelizeJSUTCorpus:
    """Integration tests for JSUT-like corpus phonemization."""

    def test_phonemize_realistic_japanese_corpus(self, tmp_path: Path) -> None:
        """Test phonemizing realistic Japanese corpus with mixed content."""
        # Arrange - Create sample corpus with realistic Japanese sentences
        input_csv = tmp_path / "metadata.csv"
        output_csv = tmp_path / "metadata_phonemes.csv"
        phoneme_map_json = tmp_path / "phoneme_map.json"

        # Sample sentences covering various Japanese constructs
        sentences = [
            "こんにちは、元気ですか。",  # Pure hiragana with punctuation
            "日本語は面白いです。",  # Kanji + hiragana
            "今日はいい天気ですね。",  # Mixed kanji/hiragana
            "私は学生です。",  # Common sentence
            "ありがとうございます。",  # Polite expression
            "これはテストです。",  # Hiragana + katakana
            "東京に行きました。",  # Place name
            "本を読んでいます。",  # Progressive form
            "美しい花が咲いています。",  # Descriptive sentence
            "彼女は歌手になりたいです。",  # Desire expression
        ]

        # Create metadata
        lines = [
            f"audio_{i:03d}.wav|{sentence}\n"
            for i, sentence in enumerate(sentences)
        ]
        input_csv.write_text("".join(lines), encoding="utf-8")

        config = PhonemeCorpusConfig(
            input_metadata=input_csv,
            output_metadata=output_csv,
            phoneme_map_output=phoneme_map_json,
        )

        # Act - Use real PykakasiAdapter
        kanji_converter = PykakasiAdapter()
        result = phonemize_japanese_corpus(
            config=config,
            kanji_converter=kanji_converter,
        )

        # Assert
        assert result.total_samples == 10
        assert result.successful == 10
        assert result.failed == 0
        assert result.phoneme_count > 0
        assert result.phoneme_count <= 100  # Should be ~50-80 unique chars

    def test_phonemize_validates_output_format(self, tmp_path: Path) -> None:
        """Test that output format is correct (audio_file|phoneme_ids)."""
        # Arrange
        input_csv = tmp_path / "metadata.csv"
        output_csv = tmp_path / "metadata_phonemes.csv"
        phoneme_map_json = tmp_path / "phoneme_map.json"

        input_csv.write_text(
            "audio_001.wav|こんにちは\n" "audio_002.wav|ありがとう\n", encoding="utf-8"
        )

        config = PhonemeCorpusConfig(
            input_metadata=input_csv,
            output_metadata=output_csv,
            phoneme_map_output=phoneme_map_json,
        )

        # Act
        kanji_converter = PykakasiAdapter()
        phonemize_japanese_corpus(
            config=config,
            kanji_converter=kanji_converter,
        )

        # Assert - Validate output format
        output_lines = output_csv.read_text(encoding="utf-8").strip().split("\n")
        assert len(output_lines) == 2

        for line in output_lines:
            parts = line.split("|")
            assert len(parts) == 2
            audio_file, phoneme_ids = parts
            assert audio_file.endswith(".wav")
            assert " " in phoneme_ids  # Space-separated IDs
            # Validate all phoneme IDs are integers
            ids = [int(x) for x in phoneme_ids.split()]
            assert all(id >= 0 for id in ids)

    def test_phonemize_validates_phoneme_map_json(self, tmp_path: Path) -> None:
        """Test that phoneme_map.json is valid and loadable."""
        # Arrange
        input_csv = tmp_path / "metadata.csv"
        output_csv = tmp_path / "metadata_phonemes.csv"
        phoneme_map_json = tmp_path / "phoneme_map.json"

        input_csv.write_text("audio_001.wav|こんにちは\n", encoding="utf-8")

        config = PhonemeCorpusConfig(
            input_metadata=input_csv,
            output_metadata=output_csv,
            phoneme_map_output=phoneme_map_json,
        )

        # Act
        kanji_converter = PykakasiAdapter()
        result = phonemize_japanese_corpus(
            config=config,
            kanji_converter=kanji_converter,
        )

        # Assert - Load and validate JSON
        import json

        with open(phoneme_map_json, encoding="utf-8") as f:
            phoneme_data = json.load(f)

        assert "phonemes" in phoneme_data
        assert len(phoneme_data["phonemes"]) == result.phoneme_count

        # Validate structure (dict mapping character -> ID)
        for character, phoneme_id in phoneme_data["phonemes"].items():
            assert isinstance(character, str)
            assert isinstance(phoneme_id, int)
            assert phoneme_id >= 0

    def test_phonemize_deterministic_across_runs(self, tmp_path: Path) -> None:
        """Test that phonemization is deterministic across multiple runs."""
        # Arrange
        input_csv = tmp_path / "metadata.csv"
        input_csv.write_text("audio_001.wav|こんにちは\n", encoding="utf-8")

        config1 = PhonemeCorpusConfig(
            input_metadata=input_csv,
            output_metadata=tmp_path / "output1.csv",
            phoneme_map_output=tmp_path / "map1.json",
        )

        config2 = PhonemeCorpusConfig(
            input_metadata=input_csv,
            output_metadata=tmp_path / "output2.csv",
            phoneme_map_output=tmp_path / "map2.json",
        )

        kanji_converter = PykakasiAdapter()

        # Act - Run twice
        phonemize_japanese_corpus(config=config1, kanji_converter=kanji_converter)
        phonemize_japanese_corpus(config=config2, kanji_converter=kanji_converter)

        # Assert - Outputs should be identical
        output1 = (tmp_path / "output1.csv").read_text(encoding="utf-8")
        output2 = (tmp_path / "output2.csv").read_text(encoding="utf-8")
        assert output1 == output2

        map1 = (tmp_path / "map1.json").read_text(encoding="utf-8")
        map2 = (tmp_path / "map2.json").read_text(encoding="utf-8")
        assert map1 == map2

    def test_phonemize_handles_all_hiragana_characters(self, tmp_path: Path) -> None:
        """Test phonemizing text with comprehensive hiragana coverage."""
        # Arrange - Include many different hiragana characters
        input_csv = tmp_path / "metadata.csv"
        output_csv = tmp_path / "metadata_phonemes.csv"
        phoneme_map_json = tmp_path / "phoneme_map.json"

        # Comprehensive hiragana text
        comprehensive_text = (
            "あいうえおかきくけこさしすせそたちつてと"
            "なにぬねのはひふへほまみむめもやゆよ"
            "らりるれろわをん"
            "がぎぐげござじずぜぞだぢづでど"
            "ばびぶべぼぱぴぷぺぽ"
            "ぁぃぅぇぉっゃゅょゎ"
        )

        input_csv.write_text(f"audio_001.wav|{comprehensive_text}\n", encoding="utf-8")

        config = PhonemeCorpusConfig(
            input_metadata=input_csv,
            output_metadata=output_csv,
            phoneme_map_output=phoneme_map_json,
        )

        kanji_converter = PykakasiAdapter()

        # Act
        result = phonemize_japanese_corpus(
            config=config,
            kanji_converter=kanji_converter,
        )

        # Assert
        assert result.successful == 1
        # Should capture most/all hiragana characters
        assert result.phoneme_count >= 70  # Most basic hiragana covered

    def test_phonemize_performance_on_medium_corpus(self, tmp_path: Path) -> None:
        """Test performance on medium-sized corpus (1000 samples)."""
        import time

        # Arrange - Generate 1000 samples
        input_csv = tmp_path / "metadata.csv"
        output_csv = tmp_path / "metadata_phonemes.csv"
        phoneme_map_json = tmp_path / "phoneme_map.json"

        sentences = [
            "こんにちは、元気ですか。",
            "日本語は面白いです。",
            "今日はいい天気ですね。",
            "私は学生です。",
            "ありがとうございます。",
        ]

        lines = [
            f"audio_{i:04d}.wav|{sentences[i % len(sentences)]}\n" for i in range(1000)
        ]
        input_csv.write_text("".join(lines), encoding="utf-8")

        config = PhonemeCorpusConfig(
            input_metadata=input_csv,
            output_metadata=output_csv,
            phoneme_map_output=phoneme_map_json,
        )

        kanji_converter = PykakasiAdapter()

        # Act - Measure time
        start_time = time.time()
        result = phonemize_japanese_corpus(
            config=config,
            kanji_converter=kanji_converter,
        )
        elapsed_time = time.time() - start_time

        # Assert
        assert result.total_samples == 1000
        assert result.successful == 1000
        assert result.failed == 0
        # Should complete reasonably fast (< 30 seconds)
        assert elapsed_time < 30.0

    def test_phonemize_handles_edge_case_characters(self, tmp_path: Path) -> None:
        """Test handling edge case Japanese characters."""
        # Arrange
        input_csv = tmp_path / "metadata.csv"
        output_csv = tmp_path / "metadata_phonemes.csv"
        phoneme_map_json = tmp_path / "phoneme_map.json"

        # Edge cases: long vowel mark, small tsu, etc.
        edge_cases = [
            "コーヒー",  # Katakana with long vowel
            "がっこう",  # Small tsu
            "きょう",  # Combined characters
            "ちゃん",  # Combined characters
            "じゃあ",  # Combined characters
        ]

        lines = [f"audio_{i:03d}.wav|{text}\n" for i, text in enumerate(edge_cases)]
        input_csv.write_text("".join(lines), encoding="utf-8")

        config = PhonemeCorpusConfig(
            input_metadata=input_csv,
            output_metadata=output_csv,
            phoneme_map_output=phoneme_map_json,
        )

        kanji_converter = PykakasiAdapter()

        # Act
        result = phonemize_japanese_corpus(
            config=config,
            kanji_converter=kanji_converter,
        )

        # Assert - Should handle all cases
        assert result.successful == len(edge_cases)
        assert result.failed == 0
