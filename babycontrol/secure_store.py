"""Encrypted file storage (FEAT-007).

Config and usage data are stored encrypted + authenticated (Fernet) so they
cannot be edited with a text editor. The key lives in `key.bin`; on Windows it
is wrapped with DPAPI (machine scope), so the file is useless if copied away.
This stops casual tampering by a child; it is not protection against a
determined administrator on the same machine.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

RAW_PREFIX = b"RAW1:"
DPAPI_PREFIX = b"DPAPI1:"
_CRYPTPROTECT_UI_FORBIDDEN = 0x1
_CRYPTPROTECT_LOCAL_MACHINE = 0x4


class StoreError(Exception):
    """Stored data is missing its key, unreadable, or has been tampered with."""


def _dpapi(data: bytes, protect: bool) -> bytes:
    import ctypes
    from ctypes import wintypes

    class DataBlob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    buf = ctypes.create_string_buffer(data, len(data))
    blob_in = DataBlob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    blob_out = DataBlob()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    func = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    flags = _CRYPTPROTECT_UI_FORBIDDEN | _CRYPTPROTECT_LOCAL_MACHINE
    if not func(ctypes.byref(blob_in), None, None, None, None, flags,
                ctypes.byref(blob_out)):
        raise StoreError("DPAPI call failed")
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        kernel32.LocalFree(ctypes.cast(blob_out.pbData, ctypes.c_void_p))


def _wrap_key(key: bytes) -> bytes:
    if sys.platform == "win32":
        return DPAPI_PREFIX + _dpapi(key, protect=True)
    return RAW_PREFIX + key


def _unwrap_key(blob: bytes) -> bytes:
    if blob.startswith(RAW_PREFIX):
        return blob[len(RAW_PREFIX):]
    if blob.startswith(DPAPI_PREFIX) and sys.platform == "win32":
        return _dpapi(blob[len(DPAPI_PREFIX):], protect=False)
    raise StoreError("unknown key format")


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


class SecureStore:
    """Encrypted blobs keyed by a per-install key stored under `root`."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.key_path = root / "key.bin"

    def _fernet(self, create: bool) -> Fernet:
        try:
            key = _unwrap_key(self.key_path.read_bytes())
        except FileNotFoundError:
            if not create:
                raise StoreError("encryption key is missing") from None
            key = Fernet.generate_key()
            _atomic_write(self.key_path, _wrap_key(key))
        except OSError as exc:
            raise StoreError(f"cannot read key: {exc}") from exc
        try:
            return Fernet(key)
        except ValueError as exc:
            raise StoreError("encryption key is corrupt") from exc

    def write(self, path: Path, data: bytes) -> None:
        """Encrypt and atomically write `data`. Creates the key if needed."""
        _atomic_write(path, self._fernet(create=True).encrypt(data))

    def read(self, path: Path) -> bytes | None:
        """Decrypt `path`. None if the file does not exist; StoreError if it
        exists but cannot be decrypted (corrupt, tampered, or key lost)."""
        try:
            token = path.read_bytes()
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise StoreError(f"cannot read {path.name}: {exc}") from exc
        try:
            return self._fernet(create=False).decrypt(token)
        except InvalidToken as exc:
            raise StoreError(f"{path.name} is corrupt or was modified") from exc
