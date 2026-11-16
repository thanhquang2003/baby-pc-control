import random

import pytest

from babycontrol.exercises import (
    ExerciseSession, Question, VOCAB, english_question, math_question, vocab_band,
)


@pytest.mark.parametrize("grade", range(1, 13))
def test_math_answer_is_self_consistent(grade):
    rng = random.Random(grade)
    for _ in range(200):
        q = math_question(grade, rng)
        assert q.subject == "math"
        assert q.check(q.answer)
        assert not q.check("not a number")


def test_math_has_no_negative_subtraction_in_early_grades():
    rng = random.Random(1)
    for grade in (1, 2, 3):
        for _ in range(200):
            assert int(math_question(grade, rng).answer) >= 0


def test_math_division_is_exact():
    rng = random.Random(2)
    for _ in range(300):
        q = math_question(4, rng)
        if "÷" in q.prompt:
            a, _, b = q.prompt.split(" =")[0].split(" ")
            assert int(a) % int(b) == 0


def test_math_accepts_comma_decimal():
    assert Question("math", "x", "2.5").check("2,5")
    assert Question("math", "x", "2.5").check(" 2.50 ")


@pytest.mark.parametrize("grade", [1, 3, 5, 9])
def test_english_questions_valid(grade):
    rng = random.Random(grade)
    for _ in range(200):
        q = english_question(grade, rng)
        assert q.check(q.answer)
        if q.choices:
            assert q.answer in q.choices
            assert len(set(q.choices)) == 4


def test_vocab_bands_cover_all_grades():
    for grade in range(1, 13):
        assert vocab_band(grade) in VOCAB
    for words in VOCAB.values():
        assert len(words) >= 4
        assert len({en for en, _ in words}) == len(words)


def test_session_pass_after_required_correct():
    session = ExerciseSession(3, 4, rng=random.Random(0))
    while not session.passed:
        assert session.submit(session.current.answer)
    assert session.correct == 4 and session.wrong == 0
    assert session.current is None


def test_wrong_answer_does_not_count_and_gets_new_question():
    session = ExerciseSession(3, 2, rng=random.Random(0))
    assert not session.submit("definitely wrong ###")
    assert session.correct == 0 and session.wrong == 1
    assert not session.passed
    assert session.current is not None


def test_session_alternates_subjects():
    session = ExerciseSession(3, 4, rng=random.Random(5))
    subjects = []
    while not session.passed:
        subjects.append(session.current.subject)
        session.submit(session.current.answer)
    assert subjects == ["math", "english", "math", "english"]


def test_submit_after_pass_is_ignored():
    session = ExerciseSession(1, 1, rng=random.Random(0))
    session.submit(session.current.answer)
    assert session.passed
    assert session.submit("anything") is False
    assert session.correct == 1
