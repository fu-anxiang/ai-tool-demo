"""Core logic: lexicon-based sentiment analysis + text cleaning."""
import re

POSITIVE = {"good", "great", "love", "nice", "awesome", "excellent", "best", "like"}
NEGATIVE = {"bad", "terrible", "hate", "awful", "worst", "poor", "sucks"}


def clean_text(text: str) -> str:
    """Remove punctuation, collapse whitespace, lowercase."""
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.lower().split())


def sentiment(text: str) -> str:
    """Classify text as positive / negative / neutral (lexicon-based)."""
    words = set(clean_text(text).split())
    pos = len(words & POSITIVE)
    neg = len(words & NEGATIVE)
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"