"""JWT encode/decode + the access-vs-refresh discrimination."""
from __future__ import annotations

import time
from datetime import timedelta
from unittest.mock import patch

import jwt
import pytest

from provectus_analytics.auth import tokens
from provectus_analytics.auth.config import settings


def test_access_token_decodes_to_same_user_id():
    tok = tokens.make_access_token(42)
    assert tokens.decode_token(tok, expected_type="access") == 42


def test_refresh_token_decodes_to_same_user_id():
    tok = tokens.make_refresh_token(99)
    assert tokens.decode_token(tok, expected_type="refresh") == 99


def test_access_token_rejected_as_refresh():
    tok = tokens.make_access_token(1)
    with pytest.raises(tokens.TokenError):
        tokens.decode_token(tok, expected_type="refresh")


def test_refresh_token_rejected_as_access():
    tok = tokens.make_refresh_token(1)
    with pytest.raises(tokens.TokenError):
        tokens.decode_token(tok, expected_type="access")


def test_malformed_token_rejected():
    with pytest.raises(tokens.TokenError):
        tokens.decode_token("not.a.token", expected_type="access")


def test_token_signed_with_different_secret_rejected():
    bad = jwt.encode({"sub": "1", "typ": "access", "exp": 9999999999, "iat": 0},
                     "wrong-secret", algorithm=settings.jwt_algorithm)
    with pytest.raises(tokens.TokenError):
        tokens.decode_token(bad, expected_type="access")


def test_expired_token_rejected():
    # Encode a token that's already expired.
    expired = jwt.encode(
        {"sub": "1", "typ": "access",
         "iat": int(time.time()) - 100, "exp": int(time.time()) - 10},
        settings.secret_key, algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(tokens.TokenError, match="expired"):
        tokens.decode_token(expired, expected_type="access")
