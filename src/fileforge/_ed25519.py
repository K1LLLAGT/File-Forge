"""Vendored pure-Python Ed25519 (RFC 8032) — sign, verify, public-key derivation.

This is the canonical public-domain reference implementation (Bernstein et al.),
adapted to use Python's built-in modular ``pow`` for speed. It carries **no
third-party dependencies**, which is deliberate: FileForge is distributed to
Termux, Magisk, and Android targets where building a native crypto library
(e.g. ``cryptography``'s Rust backend) is painful or impossible. Licence keys
are signed by the server's private key and verified here with the embedded
public key — no shared secret ships with the client.

Correctness is pinned against the RFC 8032 Section 7.1 Test 1 vector in the
test suite. It is not constant-time; that is irrelevant for verifying our own
short-lived licence signatures.
"""

from __future__ import annotations

import hashlib
import os

b = 256
q = 2 ** 255 - 19
_L = 2 ** 252 + 27742317777372353535851937790883648493  # group order


def _H(m: bytes) -> bytes:
    return hashlib.sha512(m).digest()


def _inv(x: int) -> int:
    return pow(x, q - 2, q)


d = -121665 * _inv(121666) % q
_I = pow(2, (q - 1) // 4, q)


def _xrecover(y: int) -> int:
    xx = (y * y - 1) * _inv(d * y * y + 1)
    x = pow(xx, (q + 3) // 8, q)
    if (x * x - xx) % q != 0:
        x = (x * _I) % q
    if x % 2 != 0:
        x = q - x
    return x


_By = 4 * _inv(5) % q
_Bx = _xrecover(_By)
_B = [_Bx % q, _By % q]


def _edwards(P, Q):
    x1, y1 = P
    x2, y2 = Q
    x3 = (x1 * y2 + x2 * y1) * _inv(1 + d * x1 * x2 * y1 * y2)
    y3 = (y1 * y2 + x1 * x2) * _inv(1 - d * x1 * x2 * y1 * y2)
    return [x3 % q, y3 % q]


def _scalarmult(P, e):
    if e == 0:
        return [0, 1]
    Q = _scalarmult(P, e // 2)
    Q = _edwards(Q, Q)
    if e & 1:
        Q = _edwards(Q, P)
    return Q


def _encodeint(y: int) -> bytes:
    return y.to_bytes(b // 8, "little")


def _encodepoint(P) -> bytes:
    x, y = P
    bits = [(y >> i) & 1 for i in range(b - 1)] + [x & 1]
    return bytes(
        sum(bits[i * 8 + j] << j for j in range(8)) for i in range(b // 8)
    )


def _bit(h: bytes, i: int) -> int:
    return (h[i // 8] >> (i % 8)) & 1


def publickey(sk: bytes) -> bytes:
    """Derive the 32-byte public key from a 32-byte seed."""
    h = _H(sk)
    a = 2 ** (b - 2) + sum(2 ** i * _bit(h, i) for i in range(3, b - 2))
    A = _scalarmult(_B, a)
    return _encodepoint(A)


def _Hint(m: bytes) -> int:
    h = _H(m)
    return sum(2 ** i * _bit(h, i) for i in range(2 * b))


def sign(sk: bytes, msg: bytes) -> bytes:
    """Sign ``msg`` with 32-byte seed ``sk``; returns a 64-byte signature."""
    pk = publickey(sk)
    h = _H(sk)
    a = 2 ** (b - 2) + sum(2 ** i * _bit(h, i) for i in range(3, b - 2))
    r = _Hint(h[b // 8:b // 4] + msg)
    R = _scalarmult(_B, r)
    S = (r + _Hint(_encodepoint(R) + pk + msg) * a) % _L
    return _encodepoint(R) + _encodeint(S)


def _isoncurve(P) -> bool:
    x, y = P
    return (-x * x + y * y - 1 - d * x * x * y * y) % q == 0


def _decodeint(s: bytes) -> int:
    return sum(2 ** i * _bit(s, i) for i in range(0, b))


def _decodepoint(s: bytes):
    y = sum(2 ** i * _bit(s, i) for i in range(0, b - 1))
    x = _xrecover(y)
    if x & 1 != _bit(s, b - 1):
        x = q - x
    P = [x, y]
    if not _isoncurve(P):
        raise ValueError("decoding point that is not on curve")
    return P


def verify(pk: bytes, msg: bytes, sig: bytes) -> bool:
    """Return True iff ``sig`` is a valid signature of ``msg`` under ``pk``."""
    if len(sig) != b // 4 or len(pk) != b // 8:
        return False
    try:
        R = _decodepoint(sig[:b // 8])
        A = _decodepoint(pk)
        S = _decodeint(sig[b // 8:b // 4])
        h = _Hint(_encodepoint(R) + pk + msg)
        return _scalarmult(_B, S) == _edwards(R, _scalarmult(A, h))
    except (ValueError, IndexError):
        return False


def generate_seed() -> bytes:
    """A fresh 32-byte Ed25519 seed (the private key)."""
    return os.urandom(32)
