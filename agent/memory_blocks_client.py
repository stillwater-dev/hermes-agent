"""Thin HTTP client for the Hermes Memory Service (HMS) memory *blocks*.

HMS runs locally (default ``http://127.0.0.1:7821``) and exposes per-profile
"memory blocks" -- a structured, budget-respecting replacement for the flat
``MEMORY.md`` / per-profile ``MEMORY.yaml`` curated-memory store.

This module is intentionally dependency-free (stdlib ``urllib`` only) and
*fail-soft*: every call returns ``None``/``False`` on any error so callers can
fall back to the legacy on-disk render.  Nothing here may raise into the
agent's hot path.

Toggles (env):
  * ``HERMES_MEMORY_BLOCKS_READ``  -- read curated memory from HMS blocks
    (default: ON; "0"/"false"/"no"/"off" disables -> legacy MEMORY.md render).
  * ``HERMES_MEMORY_BLOCKS_WRITE`` -- ALSO persist memory-tool writes into HMS
    blocks (default: OFF; opt-in with "1"/"true"/"yes"/"on").
  * ``HERMES_HMS_URL`` -- override base URL (default http://127.0.0.1:7821).
  * ``HERMES_HMS_TIMEOUT`` -- per-request timeout seconds (default 2.0).
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

_TRUTHY = {"1", "true", "yes", "on"}
_FALSY = {"0", "false", "no", "off"}


def _flag(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    v = raw.strip().lower()
    if v in _TRUTHY:
        return True
    if v in _FALSY:
        return False
    return default


def blocks_read_enabled() -> bool:
    """Read curated memory from HMS blocks? Defaults ON (with YAML fallback)."""
    return _flag("HERMES_MEMORY_BLOCKS_READ", True)


def blocks_write_enabled() -> bool:
    """Mirror memory-tool writes into HMS blocks? Defaults OFF (staged)."""
    return _flag("HERMES_MEMORY_BLOCKS_WRITE", False)


def _base_url() -> str:
    return os.environ.get("HERMES_HMS_URL", "http://127.0.0.1:7821").rstrip("/")


def _timeout() -> float:
    try:
        return float(os.environ.get("HERMES_HMS_TIMEOUT", "2.0"))
    except (TypeError, ValueError):
        return 2.0


def fetch_context(profile: str) -> Optional[str]:
    """Return the composed, budget-respecting curated-memory text for ``profile``.

    Returns the block text on success, or ``None`` on ANY failure (HMS down,
    HTTP error, malformed JSON, empty text).  Callers fall back to the legacy
    MEMORY.md render on ``None``.
    """
    if not profile:
        return None
    try:
        qs = urllib.parse.urlencode({"profile": profile})
        url = f"{_base_url()}/memories/blocks/context?{qs}"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=_timeout()) as resp:
            if resp.status != 200:
                return None
            data = json.loads(resp.read().decode("utf-8"))
        text = data.get("text") if isinstance(data, dict) else None
        if isinstance(text, str) and text.strip():
            return text
        return None
    except (urllib.error.URLError, urllib.error.HTTPError, OSError,
            ValueError, json.JSONDecodeError):
        return None
    except Exception:
        # Defensive: never raise into the system-prompt build path.
        return None


def _post(path: str, payload: dict) -> bool:
    try:
        url = f"{_base_url()}{path}"
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=body, method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=_timeout()) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


def append_block(profile: str, label: str, text: str) -> bool:
    """Append ``text`` to ``profile``/``label`` block. Fail-soft -> bool."""
    if not (profile and label and text and text.strip()):
        return False
    return _post("/memories/blocks/append",
                 {"profile": profile, "label": label, "text": text})


def replace_block(profile: str, label: str, text: str) -> bool:
    """Replace ``profile``/``label`` block contents with ``text``. Fail-soft."""
    if not (profile and label):
        return False
    return _post("/memories/blocks/replace",
                 {"profile": profile, "label": label, "text": text})
