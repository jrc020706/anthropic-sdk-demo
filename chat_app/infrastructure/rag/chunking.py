from __future__ import annotations

import math
from typing import List

DEFAULT_CHUNK_TOKENS = 600      # PDF baseline: 500-800 tokens per chunk
DEFAULT_OVERLAP_RATIO = 0.15    # PDF baseline: 10-20% overlap
CHARS_PER_TOKEN = 4.0           # average chars per token for Latin scripts

# Structure markers, from the strongest (paragraph) to the weakest (word).
BOUNDARIES = ("\n\n", "\n", ". ", "; ", " ")

# Safety net so a chunk never leaves the 500-800 token baseline.
MIN_SIZE_RATIO = 0.90
MAX_SIZE_RATIO = 1.30


def estimate_tokens(text: str) -> int:
    """Approximates the token count of ``text`` without a tokenizer."""
    if not text:
        return 0
    return max(1, math.ceil(len(text) / CHARS_PER_TOKEN))


def _closest_boundary(text: str, start: int, end: int, window: int, *, forward: bool) -> int:
    """Nearest occurrence of a structure marker on one side of ``end``."""
    lower = max(start + 1, end - window)
    upper = min(len(text), end + window)
    for separator in BOUNDARIES:
        if forward:
            index = text.find(separator, end, upper)
        else:
            index = text.rfind(separator, lower, end)
        if index != -1:
            position = index + len(separator)
            if start < position <= len(text):
                return position
    return -1


def _snap_boundary(text: str, start: int, end: int, window: int) -> int:
    """Moves ``end`` to a paragraph, line or sentence boundary.

    Forward boundaries are preferred so a chunk is never shorter than the
    requested size; if none exists, the closest previous boundary is used.
    """
    if end >= len(text):
        return end
    forward = _closest_boundary(text, start, end, window, forward=True)
    if forward != -1:
        return forward
    backward = _closest_boundary(text, start, end, window, forward=False)
    if backward != -1:
        return backward
    return end


def _nearest_word_cut(text: str, start: int, end: int) -> int:
    """Last resort cut on a space close to the requested size."""
    index = text.rfind(" ", start + 1, end + 1)
    if index != -1:
        return index + 1
    index = text.find(" ", end, min(len(text), end + 200))
    if index != -1:
        return index + 1
    return min(len(text), end)


def chunk_text(
    text: str,
    target_tokens: int = DEFAULT_CHUNK_TOKENS,
    overlap_ratio: float = DEFAULT_OVERLAP_RATIO,
) -> List[str]:
    """Splits ``text`` into overlapping chunks sized in tokens.

    The window slides over the document, its right edge is snapped forward to
    the nearest paragraph/line/sentence boundary, and the next window starts
    ``overlap_ratio`` before that edge. The resulting chunks stay inside the
    500-800 token baseline with a 10-20% overlap.
    """
    cleaned = text.strip()
    if not cleaned:
        return []
    if target_tokens < 50:
        raise ValueError("target_tokens must be at least 50.")
    if not 0 <= overlap_ratio < 0.9:
        raise ValueError("overlap_ratio must be between 0 and 0.89.")

    target_chars = max(1, int(target_tokens * CHARS_PER_TOKEN))
    overlap_chars = int(target_chars * overlap_ratio)
    window = max(1, target_chars // 4)
    min_chars = int(target_chars * MIN_SIZE_RATIO)
    max_chars = int(target_chars * MAX_SIZE_RATIO)

    if len(cleaned) <= target_chars:
        return [cleaned]

    chunks: list[str] = []
    start = 0
    total = len(cleaned)
    while start < total:
        raw_end = min(total, start + target_chars)
        if raw_end >= total:
            end = total
        else:
            snapped = _snap_boundary(cleaned, start, raw_end, window)
            if min_chars <= snapped - start <= max_chars:
                end = snapped
            else:
                # Keep the requested size but cut on a word boundary.
                end = _nearest_word_cut(cleaned, start, raw_end)
        if end <= start:
            break
        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= total:
            break
        # The next window starts exactly ``overlap_chars`` before this edge,
        # so the requested overlap ratio is really applied.
        start = max(start + 1, end - overlap_chars)

    return chunks
