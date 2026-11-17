import pytest

from babycontrol.secure_store import SecureStore, StoreError


def test_roundtrip_and_ciphertext(tmp_path):
    store = SecureStore(tmp_path)
    path = tmp_path / "a.dat"
    store.write(path, b"hello world")
    assert b"hello" not in path.read_bytes()
    assert store.read(path) == b"hello world"


def test_missing_file_is_none(tmp_path):
    assert SecureStore(tmp_path).read(tmp_path / "nope.dat") is None


def test_tampered_file_raises(tmp_path):
    store = SecureStore(tmp_path)
    path = tmp_path / "a.dat"
    store.write(path, b"data")
    blob = bytearray(path.read_bytes())
    blob[-3] ^= 0x01
    path.write_bytes(bytes(blob))
    with pytest.raises(StoreError):
        store.read(path)


def test_lost_key_raises_instead_of_regenerating(tmp_path):
    store = SecureStore(tmp_path)
    path = tmp_path / "a.dat"
    store.write(path, b"data")
    (tmp_path / "key.bin").unlink()
    with pytest.raises(StoreError):
        store.read(path)


def test_key_is_reused_across_instances(tmp_path):
    path = tmp_path / "a.dat"
    SecureStore(tmp_path).write(path, b"data")
    assert SecureStore(tmp_path).read(path) == b"data"


def test_garbage_key_file_raises(tmp_path):
    path = tmp_path / "a.dat"
    SecureStore(tmp_path).write(path, b"data")
    (tmp_path / "key.bin").write_bytes(b"RAW1:not-a-valid-key")
    with pytest.raises(StoreError):
        SecureStore(tmp_path).read(path)
