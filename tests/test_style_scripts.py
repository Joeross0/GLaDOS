from pathlib import Path

from glados.core.style_scripts import (
    STYLE_SCRIPTS_PREFIX,
    load_style_scripts,
    save_style_scripts,
    wrap_style_scripts,
)


def test_wrap_empty() -> None:
    assert wrap_style_scripts("   ") is None


def test_wrap_includes_prefix(tmp_path: Path) -> None:
    wrapped = wrap_style_scripts("Hello, test subject.")
    assert wrapped is not None
    assert wrapped.startswith(STYLE_SCRIPTS_PREFIX)
    assert "Hello, test subject." in wrapped


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "style_scripts.txt"
    save_style_scripts("line one\nline two", path)
    assert load_style_scripts(path) == "line one\nline two\n"
    save_style_scripts("", path)
    assert load_style_scripts(path) == ""
    assert not path.exists()