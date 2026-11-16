from datetime import datetime

import pytest

from babycontrol.config import (
    Config, ConfigError, StudyWindow, load_config, save_config,
)

MON_1930 = datetime(2026, 11, 16, 19, 30)  # 2026-11-16 is a Monday
SAT_1930 = datetime(2026, 11, 21, 19, 30)


def test_defaults_when_missing(tmp_path):
    config = load_config(tmp_path)
    assert config.daily_limit_minutes == 30
    assert config.study_windows == []


def test_roundtrip(tmp_path):
    config = Config(grade=5, math_questions=4, english_questions=1,
                    study_windows=[StudyWindow([0, 1], "19:00", "20:30")])
    config.set_password("secret")
    save_config(config, tmp_path)
    loaded = load_config(tmp_path)
    assert loaded.grade == 5
    assert (loaded.math_questions, loaded.english_questions) == (4, 1)
    assert loaded.study_windows[0].days == [0, 1]
    assert loaded.verify_password("secret")
    assert not loaded.verify_password("wrong")


def test_password_not_stored_plain(tmp_path):
    config = Config()
    config.set_password("secret")
    save_config(config, tmp_path)
    assert "secret" not in (tmp_path / "config.json").read_text()


def test_verify_without_password_is_false():
    assert not Config().verify_password("")


def test_study_window_matching():
    config = Config(study_windows=[StudyWindow([0], "19:00", "20:30")])
    assert config.is_study_time(MON_1930)
    assert not config.is_study_time(SAT_1930)
    assert not config.is_study_time(datetime(2026, 11, 16, 20, 30))  # end exclusive
    assert not config.is_study_time(datetime(2026, 11, 16, 18, 59))


@pytest.mark.parametrize("kwargs", [
    {"daily_limit_minutes": 0}, {"grade": 13}, {"math_questions": -1},
    {"english_questions": 51}, {"math_questions": 0, "english_questions": 0},
])
def test_invalid_values_rejected(kwargs, tmp_path):
    with pytest.raises(ConfigError):
        save_config(Config(**kwargs), tmp_path)


@pytest.mark.parametrize("window", [
    StudyWindow([], "19:00", "20:00"),
    StudyWindow([7], "19:00", "20:00"),
    StudyWindow([0], "20:00", "19:00"),
    StudyWindow([0], "bad", "19:00"),
])
def test_invalid_window_rejected(window):
    with pytest.raises(ConfigError):
        Config(study_windows=[window]).validate()


def test_short_password_rejected():
    with pytest.raises(ConfigError):
        Config().set_password("abc")
