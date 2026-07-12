"""Read profile-scoped curated memory from Hermes Memory Service (HMS)."""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from typing import Any, Dict, List

from agent.memory_provider import MemoryProvider


class HMSMemoryProvider(MemoryProvider):
    def __init__(self) -> None:
        self._profile = ""

    @property
    def name(self) -> str:
        return "hms"

    def is_available(self) -> bool:
        return True

    def initialize(self, session_id: str, **kwargs) -> None:
        self._profile = str(kwargs.get("agent_identity") or "").strip()

    def system_prompt_block(self) -> str:
        if not self._profile:
            return ""
        if os.environ.get("HERMES_MEMORY_BLOCKS_READ", "1").strip().lower() in {
            "0", "false", "no", "off",
        }:
            return ""
        try:
            base_url = os.environ.get(
                "HMS_BASE_URL",
                os.environ.get("HERMES_HMS_URL", "http://127.0.0.1:7821"),
            ).rstrip("/")
            query = urllib.parse.urlencode({"profile": self._profile})
            timeout = float(os.environ.get(
                "HMS_TIMEOUT_S", os.environ.get("HERMES_HMS_TIMEOUT", "2.0")
            ))
            with urllib.request.urlopen(
                f"{base_url}/memories/blocks/context?{query}", timeout=timeout
            ) as response:
                if response.status != 200:
                    return ""
                data = json.loads(response.read().decode("utf-8"))
            text = data.get("text") if isinstance(data, dict) else ""
            return text.strip() if isinstance(text, str) else ""
        except Exception:
            return ""

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return []
