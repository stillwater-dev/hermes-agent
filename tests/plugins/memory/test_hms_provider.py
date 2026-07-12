import json
from unittest.mock import patch

from plugins.memory import load_memory_provider
from plugins.memory.hms import HMSMemoryProvider


class Response:
    status = 200

    def __init__(self, data):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.data).encode()


def test_provider_discovery_and_profile_scoped_read(monkeypatch):
    monkeypatch.setenv("HMS_BASE_URL", "http://hms.local/")
    monkeypatch.setenv("HMS_TIMEOUT_S", "1.25")
    provider = load_memory_provider("hms")
    assert isinstance(provider, HMSMemoryProvider)
    provider.initialize("session", agent_identity="profile one")

    with patch("urllib.request.urlopen", return_value=Response({"text": " curated memory "})) as urlopen:
        assert provider.system_prompt_block() == "curated memory"

    assert urlopen.call_args.args[0] == "http://hms.local/memories/blocks/context?profile=profile+one"
    assert urlopen.call_args.kwargs["timeout"] == 1.25


def test_legacy_hermes_service_name_loads_hms():
    assert isinstance(load_memory_provider("hermes_service"), HMSMemoryProvider)


def test_production_env_aliases_and_read_toggle(monkeypatch):
    monkeypatch.setenv("HERMES_HMS_URL", "http://legacy-hms:9000/")
    monkeypatch.setenv("HERMES_HMS_TIMEOUT", "3.5")
    provider = HMSMemoryProvider()
    provider.initialize("session", agent_identity="library")

    with patch("urllib.request.urlopen", return_value=Response({"text": "memory"})) as urlopen:
        assert provider.system_prompt_block() == "memory"
    assert urlopen.call_args.args[0].startswith("http://legacy-hms:9000/")
    assert urlopen.call_args.kwargs["timeout"] == 3.5

    monkeypatch.setenv("HERMES_MEMORY_BLOCKS_READ", "off")
    with patch("urllib.request.urlopen") as urlopen:
        assert provider.system_prompt_block() == ""
    urlopen.assert_not_called()


def test_read_fails_soft_without_profile_or_valid_response():
    provider = HMSMemoryProvider()
    assert provider.system_prompt_block() == ""

    provider.initialize("session", agent_identity="coder")
    with patch("urllib.request.urlopen", side_effect=OSError("down")):
        assert provider.system_prompt_block() == ""
    with patch("urllib.request.urlopen", return_value=Response({"text": None})):
        assert provider.system_prompt_block() == ""


def test_provider_is_read_only():
    assert HMSMemoryProvider().get_tool_schemas() == []
