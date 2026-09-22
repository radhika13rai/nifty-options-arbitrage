"""
Market Intelligence News Deduplication Engine.
Implements exact-match SHA-256 fingerprinting and token-level Jaccard similarity
with a sliding TTL cache to eliminate syndicated, rehashed, or repeated wire stories.
"""

import hashlib
import re
import time
from typing import Optional, Set


def normalize_headline(headline: str) -> str:
    """Normalizes headline string for linguistic fingerprinting."""
    text = headline.lower().strip()
    text = re.sub(r"\s*[-–—|]\s*(reuters|bloomberg|the economic times|economic times|et|livemint|mint|pti|ndtv|cnbc|moneycontrol|times of india|business standard).*$", "", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def stem_word(w: str) -> str:
    """Lightweight suffix stemmer to unify word variants."""
    for sfx in ("ing", "ed", "es", "s"):
        if w.endswith(sfx) and len(w) - len(sfx) >= 3:
            res = w[:-len(sfx)]
            if sfx in ("es", "ed") and not res.endswith("e"):
                res += "e"
            return res
    return w


def tokenize(text: str) -> Set[str]:
    """Tokenizes text into significant words (>2 chars, excluding common stopwords)."""
    stopwords = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "with",
        "by", "about", "as", "into", "like", "through", "after", "over", "between",
        "out", "against", "during", "without", "before", "under", "around", "among",
        "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
        "do", "does", "did", "will", "would", "shall", "should", "may", "might",
        "must", "can", "could", "of", "it", "its", "from", "up", "down"
    }
    words = re.findall(r"\b[a-z0-9]{3,}\b", text.lower())
    return {stem_word(w) for w in words if w not in stopwords}


def jaccard_similarity(set_a: Set[str], set_b: Set[str]) -> float:
    """Calculates Jaccard similarity coefficient between two token sets."""
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a.intersection(set_b))
    union = len(set_a.union(set_b))
    return round(intersection / union, 4) if union > 0 else 0.0


class NewsDeduplicator:
    """
    Sliding window deduplicator preventing redundant signal ingestion and ML bias.
    Retains processed headlines up to ttl_sec (default: 6 hours).
    """

    def __init__(self, ttl_sec: float = 21600.0, jaccard_threshold: float = 0.45):
        self.ttl_sec = ttl_sec
        self.jaccard_threshold = jaccard_threshold
        self._history: dict[str, tuple[str, Set[str], float]] = {}

    def _purge_expired(self, current_time_ms: float) -> None:
        """Removes records older than the sliding TTL window."""
        cutoff_ms = current_time_ms - (self.ttl_sec * 1000.0)
        expired_keys = [k for k, v in self._history.items() if v[2] < cutoff_ms]
        for k in expired_keys:
            self._history.pop(k, None)

    def is_duplicate(self, raw_headline: str, timestamp_ms: Optional[float] = None) -> bool:
        now_ms = timestamp_ms or (time.time() * 1000.0)
        self._purge_expired(now_ms)

        norm = normalize_headline(raw_headline)
        if not norm:
            return True

        h = hashlib.sha256(norm.encode("utf-8")).hexdigest()
        if h in self._history:
            return True

        tokens = tokenize(norm)
        if not tokens:
            return False

        for _, (existing_norm, existing_tokens, _) in self._history.items():
            if jaccard_similarity(tokens, existing_tokens) >= self.jaccard_threshold:
                return True

        return False

    def register(self, raw_headline: str, timestamp_ms: Optional[float] = None) -> Optional[str]:
        now_ms = timestamp_ms or (time.time() * 1000.0)
        if self.is_duplicate(raw_headline, now_ms):
            return None

        norm = normalize_headline(raw_headline)
        h = hashlib.sha256(norm.encode("utf-8")).hexdigest()
        tokens = tokenize(norm)
        self._history[h] = (norm, tokens, now_ms)
        return h

    def clear(self) -> None:
        self._history.clear()

    @property
    def cached_count(self) -> int:
        return len(self._history)


news_deduplicator = NewsDeduplicator()
