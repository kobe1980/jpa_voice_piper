"""Unit tests for LJSpeech metadata writer.

Following TDD: These tests are written BEFORE implementation.
Tests the LJSPEECH format metadata.csv generation for Piper.
"""

from pathlib import Path

import pytest

from piper_voice.infrastructure.filesystem.metadata_writer import (
    LJSpeechMetadataWriter,
)


@pytest.fixture
def metadata_writer(tmp_path: Path) -> LJSpeechMetadataWriter:
    """Create metadata writer instance."""
    return LJSpeechMetadataWriter(tmp_path)


class TestLJSpeechMetadataWriter:
    """Tests for LJSpeechMetadataWriter."""

    def test_write_metadata_creates_file(
        self, metadata_writer: LJSpeechMetadataWriter, tmp_path: Path
    ) -> None:
        """Test that write_metadata creates metadata.csv file."""
        pairs = [
            (Path("audio1.wav"), "これはテストです"),
            (Path("audio2.wav"), "二番目のテスト"),
        ]

        metadata_writer.write_metadata(pairs)

        metadata_file = tmp_path / "metadata.csv"
        assert metadata_file.exists()

    def test_write_metadata_uses_ljspeech_format(
        self, metadata_writer: LJSpeechMetadataWriter, tmp_path: Path
    ) -> None:
        """Test that metadata uses LJSPEECH format: filename|transcript."""
        pairs = [
            (Path("audio1.wav"), "これはテストです"),
            (Path("audio2.wav"), "二番目のテスト"),
        ]

        metadata_writer.write_metadata(pairs)

        metadata_file = tmp_path / "metadata.csv"
        content = metadata_file.read_text(encoding="utf-8")

        # Check format: filename|transcript (no .wav extension)
        lines = content.strip().split("\n")
        assert len(lines) == 2
        assert lines[0] == "audio1|これはテストです"
        assert lines[1] == "audio2|二番目のテスト"

    def test_write_metadata_strips_wav_extension(
        self, metadata_writer: LJSpeechMetadataWriter, tmp_path: Path
    ) -> None:
        """Test that .wav extension is stripped from filenames."""
        pairs = [(Path("test.wav"), "テスト")]

        metadata_writer.write_metadata(pairs)

        metadata_file = tmp_path / "metadata.csv"
        content = metadata_file.read_text(encoding="utf-8")

        assert content.strip() == "test|テスト"

    def test_write_metadata_preserves_utf8_characters(
        self, metadata_writer: LJSpeechMetadataWriter, tmp_path: Path
    ) -> None:
        """Test that Japanese UTF-8 characters are preserved."""
        pairs = [
            (Path("audio1.wav"), "日本語のテキスト"),
            (Path("audio2.wav"), "ひらがな、カタカナ、漢字"),
        ]

        metadata_writer.write_metadata(pairs)

        metadata_file = tmp_path / "metadata.csv"
        content = metadata_file.read_text(encoding="utf-8")

        assert "日本語のテキスト" in content
        assert "ひらがな、カタカナ、漢字" in content

    def test_write_metadata_handles_empty_list(
        self, metadata_writer: LJSpeechMetadataWriter, tmp_path: Path
    ) -> None:
        """Test that writing empty list creates empty metadata file."""
        pairs: list[tuple[Path, str]] = []

        metadata_writer.write_metadata(pairs)

        metadata_file = tmp_path / "metadata.csv"
        assert metadata_file.exists()
        assert metadata_file.read_text(encoding="utf-8") == ""

    def test_write_metadata_overwrites_existing_file(
        self, metadata_writer: LJSpeechMetadataWriter, tmp_path: Path
    ) -> None:
        """Test that writing metadata overwrites existing file."""
        metadata_file = tmp_path / "metadata.csv"
        metadata_file.write_text("old content", encoding="utf-8")

        pairs = [(Path("new.wav"), "新しいテスト")]
        metadata_writer.write_metadata(pairs)

        content = metadata_file.read_text(encoding="utf-8")
        assert content == "new|新しいテスト\n"
        assert "old content" not in content

    def test_write_metadata_handles_special_characters(
        self, metadata_writer: LJSpeechMetadataWriter, tmp_path: Path
    ) -> None:
        """Test that special characters in transcript are preserved."""
        pairs = [
            (Path("audio1.wav"), "これは「テスト」です。"),
            (Path("audio2.wav"), "質問？答え！"),
        ]

        metadata_writer.write_metadata(pairs)

        metadata_file = tmp_path / "metadata.csv"
        content = metadata_file.read_text(encoding="utf-8")

        assert "これは「テスト」です。" in content
        assert "質問？答え！" in content

    def test_write_metadata_rejects_empty_transcript(
        self, metadata_writer: LJSpeechMetadataWriter
    ) -> None:
        """Test that empty transcripts raise ValueError."""
        pairs = [(Path("audio.wav"), "")]

        with pytest.raises(ValueError, match="Empty transcript"):
            metadata_writer.write_metadata(pairs)

    def test_write_metadata_rejects_whitespace_only_transcript(
        self, metadata_writer: LJSpeechMetadataWriter
    ) -> None:
        """Test that whitespace-only transcripts raise ValueError."""
        pairs = [(Path("audio.wav"), "   \t\n  ")]

        with pytest.raises(ValueError, match="Empty transcript"):
            metadata_writer.write_metadata(pairs)

    def test_write_metadata_validates_all_pairs_before_writing(
        self, metadata_writer: LJSpeechMetadataWriter, tmp_path: Path
    ) -> None:
        """Test that validation happens before writing (atomic operation)."""
        metadata_file = tmp_path / "metadata.csv"

        # Mix valid and invalid pairs
        pairs = [
            (Path("valid.wav"), "有効なテスト"),
            (Path("invalid.wav"), ""),  # Empty transcript - should fail
        ]

        with pytest.raises(ValueError, match="Empty transcript"):
            metadata_writer.write_metadata(pairs)

        # File should not be created/modified if validation fails
        if metadata_file.exists():
            content = metadata_file.read_text(encoding="utf-8")
            # Should not contain partial data
            assert "valid" not in content

    def test_write_metadata_handles_path_objects(
        self, metadata_writer: LJSpeechMetadataWriter, tmp_path: Path
    ) -> None:
        """Test that Path objects (not just strings) work correctly."""
        audio_path = tmp_path / "subdir" / "audio.wav"

        pairs = [(audio_path, "パステスト")]
        metadata_writer.write_metadata(pairs)

        metadata_file = tmp_path / "metadata.csv"
        content = metadata_file.read_text(encoding="utf-8")

        # Should use stem (filename without extension)
        assert content.strip() == "audio|パステスト"

    def test_write_metadata_preserves_line_order(
        self, metadata_writer: LJSpeechMetadataWriter, tmp_path: Path
    ) -> None:
        """Test that metadata lines preserve input order."""
        pairs = [
            (Path("audio_003.wav"), "三"),
            (Path("audio_001.wav"), "一"),
            (Path("audio_002.wav"), "二"),
        ]

        metadata_writer.write_metadata(pairs)

        metadata_file = tmp_path / "metadata.csv"
        lines = metadata_file.read_text(encoding="utf-8").strip().split("\n")

        # Order should match input order (not sorted)
        assert lines[0] == "audio_003|三"
        assert lines[1] == "audio_001|一"
        assert lines[2] == "audio_002|二"

    def test_write_metadata_handles_pipe_character_in_transcript(
        self, metadata_writer: LJSpeechMetadataWriter
    ) -> None:
        """Test that pipe character in transcript raises error."""
        pairs = [(Path("audio.wav"), "テスト|無効")]

        with pytest.raises(ValueError, match="Transcript contains pipe character"):
            metadata_writer.write_metadata(pairs)

    def test_write_metadata_adds_newline_at_end(
        self, metadata_writer: LJSpeechMetadataWriter, tmp_path: Path
    ) -> None:
        """Test that metadata file ends with newline."""
        pairs = [(Path("audio.wav"), "テスト")]

        metadata_writer.write_metadata(pairs)

        metadata_file = tmp_path / "metadata.csv"
        content = metadata_file.read_text(encoding="utf-8")

        assert content.endswith("\n")
