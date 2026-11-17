from datetime import datetime

import pytest

from babycontrol.config import (
    Config, ConfigCorrupt, ConfigError, StudyWindow, load_config, save_config,
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


def test_config_is_encrypted_on_disk(tmp_path):
    config = Config(daily_limit_minutes=77)
    config.set_password("secret")
    save_config(config, tmp_path)
    raw = (tmp_path / "config.dat").read_bytes()
    # words only: short digit strings can occur by chance in base64 ciphertext
    assert b"secret" not in raw and b"daily_limit" not in raw
    assert not (tmp_path / "config.json").exists()


def test_edited_config_falls_back_to_backup(tmp_path):
    save_config(Config(daily_limit_minutes=20), tmp_path)
    save_config(Config(daily_limit_minutes=40), tmp_path)    # .bak holds the 20
    (tmp_path / "config.dat").write_bytes(b"gAAAA-tampered")
    assert load_config(tmp_path).daily_limit_minutes == 20


def test_deleted_config_falls_back_to_backup(tmp_path):
    save_config(Config(daily_limit_minutes=20), tmp_path)
    save_config(Config(daily_limit_minutes=40), tmp_path)
    (tmp_path / "config.dat").unlink()
    assert load_config(tmp_path).daily_limit_minutes == 20


def test_all_copies_tampered_raises_corrupt(tmp_path):
    save_config(Config(), tmp_path)
    save_config(Config(), tmp_path)
    (tmp_path / "config.dat").write_bytes(b"junk")
    (tmp_path / "config.bak").write_bytes(b"junk")
    with pytest.raises(ConfigCorrupt):
        load_config(tmp_path)


def test_deleted_config_after_setup_raises_corrupt(tmp_path):
    save_config(Config(), tmp_path)
    (tmp_path / "config.dat").unlink()
    with pytest.raises(ConfigCorrupt):
        load_config(tmp_path)          # configured marker still present


def test_lost_key_raises_corrupt(tmp_path):
    save_config(Config(), tmp_path)
    (tmp_path / "key.bin").unlink()
    with pytest.raises(ConfigCorrupt):
        load_config(tmp_path)


def test_legacy_plain_json_is_migrated(tmp_path):
    (tmp_path / "config.json").write_text(
        '{"daily_limit_minutes": 25, "grade": 4, "math_questions": 2, '
        '"english_questions": 2, "study_windows": [], "password_salt": "", '
        '"password_hash": ""}')
    config = load_config(tmp_path)
    assert config.daily_limit_minutes == 25
    save_config(config, tmp_path)
    assert not (tmp_path / "config.json").exists()
    assert load_config(tmp_path).daily_limit_minutes == 25


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
