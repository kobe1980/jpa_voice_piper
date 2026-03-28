"""Japanese text normalizer for pre-processing before phonemization.

Handles characters that pykakasi cannot convert to hiragana:
- Fullwidth digits (１２３) → normalized then converted to Japanese readings
- Halfwidth digits (123) → converted to Japanese readings
- Latin characters (A-Z, a-z) → converted to Japanese letter readings
- Fullwidth punctuation (．) → halfwidth equivalents

This module is used as a pre-processing step in the PykakasiAdapter.
"""

import re
import unicodedata

# Japanese readings for single digits
_DIGIT_READINGS: dict[str, str] = {
    "0": "ぜろ",
    "1": "いち",
    "2": "に",
    "3": "さん",
    "4": "よん",
    "5": "ご",
    "6": "ろく",
    "7": "なな",
    "8": "はち",
    "9": "きゅう",
}

# Tens multiplier readings (digit * 10)
# Key is the digit before じゅう; empty string means just じゅう (for 10)
_JYUU_READINGS: dict[int, str] = {
    1: "じゅう",
    2: "にじゅう",
    3: "さんじゅう",
    4: "よんじゅう",
    5: "ごじゅう",
    6: "ろくじゅう",
    7: "ななじゅう",
    8: "はちじゅう",
    9: "きゅうじゅう",
}

# Hundreds multiplier readings (digit * 100)
# Includes rendaku variants: 300 → さんびゃく, 600 → ろっぴゃく, 800 → はっぴゃく
_HYAKU_READINGS: dict[int, str] = {
    1: "ひゃく",
    2: "にひゃく",
    3: "さんびゃく",
    4: "よんひゃく",
    5: "ごひゃく",
    6: "ろっぴゃく",
    7: "ななひゃく",
    8: "はっぴゃく",
    9: "きゅうひゃく",
}

# Thousands multiplier readings (digit * 1000)
# Includes rendaku variants: 3000 → さんぜん, 8000 → はっせん
_SEN_READINGS: dict[int, str] = {
    1: "せん",
    2: "にせん",
    3: "さんぜん",
    4: "よんせん",
    5: "ごせん",
    6: "ろくせん",
    7: "ななせん",
    8: "はっせん",
    9: "きゅうせん",
}

# Latin letter → hiragana readings (Japanese alphabet pronunciation)
_LATIN_READINGS: dict[str, str] = {
    "A": "えー",
    "B": "びー",
    "C": "しー",
    "D": "でぃー",
    "E": "いー",
    "F": "えふ",
    "G": "じー",
    "H": "えいち",
    "I": "あい",
    "J": "じぇー",
    "K": "けー",
    "L": "える",
    "M": "えむ",
    "N": "えぬ",
    "O": "おー",
    "P": "ぴー",
    "Q": "きゅー",
    "R": "あーる",
    "S": "えす",
    "T": "てぃー",
    "U": "ゆー",
    "V": "ぶい",
    "W": "だぶりゅー",
    "X": "えっくす",
    "Y": "わい",
    "Z": "ぜっと",
}

# Pattern to match sequences of digits (including decimal points)
_NUMBER_PATTERN = re.compile(r"\d+(?:\.\d+)?")

# Pattern to match sequences of Latin letters
_LATIN_PATTERN = re.compile(r"[A-Za-z]+")

# ASCII punctuation → Japanese equivalents (after NFKC normalization)
_PUNCTUATION_MAP: dict[str, str] = {
    ".": "。",
    "?": "？",
    "!": "！",
    "-": "ー",
}


def _number_to_hiragana(n: int) -> str:
    """Convert an integer to its Japanese hiragana reading.

    Handles numbers from 0 to 99,999,999 (up to 億).
    Uses standard Japanese number reading rules including
    rendaku (sequential voicing) for 300, 600, 800, 3000, 8000.

    Args:
        n: Non-negative integer to convert.

    Returns:
        Japanese hiragana reading of the number.
    """
    if n == 0:
        return "ぜろ"

    if n < 0:
        return "まいなす" + _number_to_hiragana(-n)

    parts: list[str] = []

    # 万 (man) - ten thousands
    if n >= 10000:
        man_digit = n // 10000
        if man_digit == 1:
            parts.append("いちまん")
        else:
            parts.append(_number_to_hiragana(man_digit) + "まん")
        n %= 10000

    # 千 (sen) - thousands
    if n >= 1000:
        sen_digit = n // 1000
        parts.append(_SEN_READINGS[sen_digit])
        n %= 1000

    # 百 (hyaku) - hundreds
    if n >= 100:
        hyaku_digit = n // 100
        parts.append(_HYAKU_READINGS[hyaku_digit])
        n %= 100

    # 十 (jyuu) - tens
    if n >= 10:
        jyuu_digit = n // 10
        parts.append(_JYUU_READINGS[jyuu_digit])
        n %= 10

    # 一 (ones)
    if n > 0:
        parts.append(_DIGIT_READINGS[str(n)])

    return "".join(parts)


def _replace_number(match: re.Match[str]) -> str:
    """Replace a matched number string with its Japanese hiragana reading.

    Handles both integers and decimals (e.g. 3.5 → さんてんご).

    Args:
        match: Regex match object containing the number string.

    Returns:
        Japanese hiragana reading of the number.
    """
    text = match.group()

    if "." in text:
        # Decimal number: read integer part, then てん, then each digit
        integer_part, decimal_part = text.split(".", 1)
        result = _number_to_hiragana(int(integer_part)) if integer_part else "ぜろ"
        result += "てん"
        for digit in decimal_part:
            result += _DIGIT_READINGS[digit]
        return result

    return _number_to_hiragana(int(text))


def _replace_latin(match: re.Match[str]) -> str:
    """Replace a matched Latin letter sequence with Japanese hiragana readings.

    Each letter is converted to its Japanese alphabet pronunciation.

    Args:
        match: Regex match object containing the Latin letter sequence.

    Returns:
        Japanese hiragana reading of the letters.
    """
    return "".join(_LATIN_READINGS.get(c.upper(), "") for c in match.group())


def _expand_noma(text: str) -> str:
    """Expand 々 (noma) kanji repetition mark by repeating the previous character.

    For example: 人々 → 人人, 日々 → 日日
    This allows pykakasi to convert each kanji individually.

    Args:
        text: Text that may contain 々.

    Returns:
        Text with 々 replaced by the preceding character.
    """
    result: list[str] = []
    for i, char in enumerate(text):
        if char == "々" and i > 0:
            result.append(result[-1])
        else:
            result.append(char)
    return "".join(result)


def _normalize_punctuation(text: str) -> str:
    """Convert remaining ASCII punctuation to Japanese equivalents.

    After NFKC normalization, fullwidth punctuation becomes halfwidth.
    This step converts them back to the Japanese forms expected by
    the HiraganaText validator.

    Args:
        text: Text that may contain ASCII punctuation.

    Returns:
        Text with ASCII punctuation replaced by Japanese equivalents.
    """
    for ascii_char, japanese_char in _PUNCTUATION_MAP.items():
        text = text.replace(ascii_char, japanese_char)
    return text


def normalize_japanese_text(text: str) -> str:
    """Normalize Japanese text for phonemization.

    Applies the following transformations in order:
    1. NFKC Unicode normalization (fullwidth → halfwidth for digits/Latin)
    2. Convert digit sequences to Japanese hiragana readings
    3. Convert Latin letter sequences to Japanese hiragana readings
    4. Expand 々 (noma) kanji repetition mark
    5. Convert remaining ASCII punctuation to Japanese equivalents

    Args:
        text: Raw Japanese text that may contain fullwidth digits,
              Latin characters, or other non-convertible characters.

    Returns:
        Normalized text with digits and Latin characters replaced
        by their Japanese hiragana readings. Kanji and katakana
        are left intact for pykakasi to handle.
    """
    # Step 1: NFKC normalization (fullwidth digits/letters → halfwidth)
    text = unicodedata.normalize("NFKC", text)

    # Step 2: Replace number sequences with Japanese readings
    text = _NUMBER_PATTERN.sub(_replace_number, text)

    # Step 3: Replace Latin letter sequences with hiragana readings
    text = _LATIN_PATTERN.sub(_replace_latin, text)
    # Step 4: Expand 々 (noma) repetition mark
    text = _expand_noma(text)

    # Step 5: Normalize remaining ASCII punctuation to Japanese forms
    text = _normalize_punctuation(text)

    return text
