"""Password hashing — bcrypt round-trips, rejects wrong values, handles edge cases."""
from __future__ import annotations

import pytest

from provectus_analytics.auth.passwords import hash_password, verify_password


def test_hash_then_verify_roundtrip():
    h = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", h)


def test_verify_rejects_wrong_password():
    h = hash_password("right")
    assert not verify_password("wrong", h)


def test_hash_is_salted_unique_per_call():
    """bcrypt embeds a fresh salt each call → same plaintext never produces
    the same hash twice."""
    assert hash_password("same") != hash_password("same")


def test_verify_handles_empty_inputs_without_raising():
    assert not verify_password("", "")
    assert not verify_password("anything", "")
    assert not verify_password("", "$2b$12$" + "x" * 53)


def test_verify_handles_malformed_hash_without_raising():
    assert not verify_password("anything", "not-a-bcrypt-hash")


def test_hash_rejects_empty_password():
    with pytest.raises(ValueError):
        hash_password("")
