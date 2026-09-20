from glados.utils.workers import recommended_worker_count, resolve_worker_count


def test_resolve_worker_count_honors_explicit_value() -> None:
    assert resolve_worker_count(6) == 6
    assert resolve_worker_count(99, ceiling=16) == 16


def test_resolve_worker_count_auto_uses_machine() -> None:
    auto = resolve_worker_count(0)
    assert 4 <= auto <= 16


def test_recommended_worker_count_leaves_headroom() -> None:
    count = recommended_worker_count(reserve=2, floor=4, ceiling=16)
    assert 4 <= count <= 16
