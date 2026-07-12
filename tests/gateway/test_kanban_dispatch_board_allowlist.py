from gateway.kanban_watchers import _resolve_dispatch_board_allowlist


def _normalize(value):
    value = value.strip().lower()
    if "/" in value:
        raise ValueError("bad board")
    return value


def test_dispatch_board_allowlist_distinguishes_all_disabled_and_subset():
    assert _resolve_dispatch_board_allowlist(None, _normalize) is None
    assert _resolve_dispatch_board_allowlist("", _normalize) is None
    assert _resolve_dispatch_board_allowlist([], _normalize) == set()
    assert _resolve_dispatch_board_allowlist("none", _normalize) == set()
    assert _resolve_dispatch_board_allowlist(["Library", "ops", "bad/name"], _normalize) == {"library", "ops"}
