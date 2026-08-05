"""Unit tests for ai_tool.core."""
from ai_tool.core import clean_text, sentiment


def test_sentiment_positive():
    assert sentiment("I love this great product") == "positive"


def test_sentiment_negative():
    assert sentiment("this is terrible and bad") == "negative"


def test_sentiment_neutral():
    assert sentiment("hello world") == "neutral"


def test_clean_text():
    assert clean_text("Hello,  World!!") == "hello world"


def test_sentiment_mixed_counts():
    assert sentiment("good but also bad") == "neutral"