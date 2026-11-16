from babycontrol import kiosk


def test_format_mmss():
    assert kiosk.format_mmss(0) == "00:00"
    assert kiosk.format_mmss(59.9) == "00:59"
    assert kiosk.format_mmss(1800) == "30:00"
    assert kiosk.format_mmss(-5) == "00:00"


def test_admin_check_is_false_off_windows():
    import sys
    if sys.platform != "win32":
        assert kiosk.is_admin() is False
