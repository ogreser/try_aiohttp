import pytest

from .utils import MentionCounter, normalize_text


@pytest.mark.parametrize('mention, text, count', [
    ('A', 'ab a abc a', 2),
    ('Ab', 'ab a abc a', 1),
    ('b a', 'ab a abc a', 0),
    ('Abc', 'ab a abc a', 1),
    ('Abc a', 'ab a abc a abc b', 1),
])
def test_MentionCounter_process_text(mention, text, count):
    m = MentionCounter(mention)
    m.process_text(text)
    assert m.count == count



@pytest.mark.parametrize('text, normalized_text', [
    ("es, ban them; I'm tired of seeing Valleywag stories on News.YC.", 
     'es ban them i m tired of seeing valleywag stories on news yc'),
    ('<i>or</i> HN: the Next Iteration<p>I get the impression', 'or hn the next iteration i get the impression'),
])
def test_normalize_text(text, normalized_text):
    assert normalize_text(text) == normalized_text