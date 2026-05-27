"""Shared slowapi Limiter instance for the auth router.

slowapi binds rate limits to a Limiter at decoration time, so the instance has
to live at module level rather than inside a factory. main.py wires this
limiter onto app.state and adds the SlowAPIMiddleware.
"""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
