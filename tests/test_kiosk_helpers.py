from babycontrol import kiosk


def test_format_mmss():
    assert kiosk.format_mmss(0) == "00:00"
    assert kiosk.format_mmss(59.9) == "00:59"
    assert kiosk.format_mmss(1800) == "30:00"
    assert kiosk.format_mmss(-5) == "00:00"


def test_groups_contain_admin_even_when_deny_only():
    elevated = '"BUILTIN\\Administrators","Alias","S-1-5-32-544","Enabled group"'
    filtered = '"BUILTIN\\Administrators","Alias","S-1-5-32-544","Group used for deny only"'
    standard = '"BUILTIN\\Users","Alias","S-1-5-32-545","Mandatory group"'
    assert kiosk.groups_contain_admin(elevated)
    assert kiosk.groups_contain_admin(filtered)
    assert not kiosk.groups_contain_admin(standard)


def test_admin_check_is_false_off_windows():
    import sys
    if sys.platform != "win32":
        assert kiosk.is_admin() is False
