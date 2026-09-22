import pytest

from safearchive import destination_for, extract_members


def test_rejects_sibling_prefix_escape(tmp_path):
    root = tmp_path / "extract"
    root.mkdir()

    with pytest.raises(ValueError, match="escapes destination"):
        destination_for(root, "../extract-escape/payload.txt")


def test_rejects_windows_separator_traversal(tmp_path):
    root = tmp_path / "extract"
    root.mkdir()

    with pytest.raises(ValueError, match="escapes destination"):
        destination_for(root, r"..\outside.txt")


def test_rejects_absolute_member(tmp_path):
    root = tmp_path / "extract"
    root.mkdir()

    with pytest.raises(ValueError, match="escapes destination"):
        destination_for(root, "/tmp/outside.txt")


def test_normal_nested_members_are_written_inside_root(tmp_path):
    root = tmp_path / "extract"

    paths = extract_members(root, {"assets/icons/app.txt": b"safe"})

    assert paths == [(root / "assets/icons/app.txt").resolve()]
    assert paths[0].read_bytes() == b"safe"
