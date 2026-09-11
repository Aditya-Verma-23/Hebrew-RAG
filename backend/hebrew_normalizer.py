"""
hebrew_normalizer.py
--------------------
Normalizes Hebrew text:
- Unicode NFC normalization
- Strips nikud (diacritical marks) - optional
- Removes RTL/LTR control characters
- Cleans whitespace
- Fixes punctuation
"""

import re
import unicodedata
from typing import Optional


# Hebrew Unicode ranges
HEBREW_LETTERS = range(0x05D0, 0x05EA + 1)       # א-ת
HEBREW_NIKUD = range(0x05B0, 0x05C7 + 1)          # Diacritics / vowel marks
HEBREW_CANTILLATION = range(0x0591, 0x05AF + 1)   # Cantillation marks
HEBREW_PRESENTATION = range(0xFB1D, 0xFB4E + 1)   # Presentation forms

# RTL/LTR control characters
BIDI_CONTROLS = {
    '\u200F',  # RIGHT-TO-LEFT MARK
    '\u200E',  # LEFT-TO-RIGHT MARK
    '\u202A',  # LEFT-TO-RIGHT EMBEDDING
    '\u202B',  # RIGHT-TO-LEFT EMBEDDING
    '\u202C',  # POP DIRECTIONAL FORMATTING
    '\u202D',  # LEFT-TO-RIGHT OVERRIDE
    '\u202E',  # RIGHT-TO-LEFT OVERRIDE
    '\u2066',  # LEFT-TO-RIGHT ISOLATE
    '\u2067',  # RIGHT-TO-LEFT ISOLATE
    '\u2068',  # FIRST STRONG ISOLATE
    '\u2069',  # POP DIRECTIONAL ISOLATE
    '\u061C',  # ARABIC LETTER MARK
    '\uFEFF',  # ZERO WIDTH NO-BREAK SPACE (BOM)
    '\u200B',  # ZERO WIDTH SPACE
    '\u200C',  # ZERO WIDTH NON-JOINER
    '\u200D',  # ZERO WIDTH JOINER
}


def strip_nikud(text: str) -> str:
    """Remove Hebrew diacritical marks (nikud/vowel points)."""
    # Remove nikud (U+05B0–U+05C7)
    result = []
    for char in text:
        cp = ord(char)
        if 0x05B0 <= cp <= 0x05C7:
            continue  # Skip nikud
        if 0x0591 <= cp <= 0x05AF:
            continue  # Skip cantillation
        result.append(char)
    return "".join(result)


def normalize_hebrew(text: str, remove_nikud: bool = True) -> str:
    """
    Normalize Hebrew text:
    1. Unicode NFC normalization
    2. Strip bidi control characters
    3. Optionally strip nikud
    4. Normalize whitespace
    5. Fix common encoding issues
    """
    if not text:
        return ""
    
    # 1. Unicode NFC normalization
    text = unicodedata.normalize("NFC", text)
    
    # 2. Remove bidi control characters
    for ctrl in BIDI_CONTROLS:
        text = text.replace(ctrl, "")
    
    # 3. Strip nikud if requested
    if remove_nikud:
        text = strip_nikud(text)
    
    # 4. Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    
    # 5. Remove excessive whitespace within lines (but preserve newlines)
    lines = text.split("\n")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in lines]
    
    # 6. Collapse multiple consecutive blank lines into a single one
    result_lines = []
    prev_blank = False
    for line in lines:
        is_blank = len(line.strip()) == 0
        if is_blank and prev_blank:
            continue
        result_lines.append(line)
        prev_blank = is_blank
    
    text = "\n".join(result_lines).strip()
    
    # 7. Replace non-standard apostrophes / quote chars with standard ones
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201C", '"').replace("\u201D", '"')
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    
    # 8. Replace Hebrew presentation forms with their basic equivalents
    # (some EPUBs use FB1D-FB4E range)
    normalized_chars = []
    for char in text:
        cp = ord(char)
        if 0xFB1D <= cp <= 0xFB4E:
            # Try to get the NFKD decomposition
            decomposed = unicodedata.normalize("NFKD", char)
            normalized_chars.append(decomposed)
        else:
            normalized_chars.append(char)
    text = "".join(normalized_chars)
    
    return text


def is_hebrew_text(text: str, threshold: float = 0.3) -> bool:
    """Check if text contains significant Hebrew content."""
    if not text:
        return False
    
    hebrew_count = sum(
        1 for ch in text
        if 0x05D0 <= ord(ch) <= 0x05EA
    )
    total_alpha = sum(1 for ch in text if ch.isalpha())
    
    if total_alpha == 0:
        return False
    
    return (hebrew_count / total_alpha) >= threshold


if __name__ == "__main__":
    sample = "שָׁלוֹם עוֹלָם! Hello World. \u200F\u200E"
    print("Original:", repr(sample))
    print("Normalized:", normalize_hebrew(sample))
    print("Is Hebrew:", is_hebrew_text(sample))
