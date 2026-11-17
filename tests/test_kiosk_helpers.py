from babycontrol import kiosk


def test_format_mmss():
    assert kiosk.format_mmss(0) == "00:00"
    assert kiosk.format_mmss(59.9) == "00:59"
    assert kiosk.format_mmss(1800) == "30:00"
    assert kiosk.format_mmss(-5) == "00:00"


def test_kiosk_no_longer_skips_administrators():
    # shared-account mode: the kiosk must run for every user
    assert not hasattr(kiosk, "is_admin")
