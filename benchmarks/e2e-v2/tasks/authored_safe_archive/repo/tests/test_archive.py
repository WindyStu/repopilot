from safearchive import extract_members


def test_extracts_regular_nested_member(tmp_path):
    written = extract_members(tmp_path, {"docs/readme.txt": b"hello"})

    assert written == [(tmp_path / "docs/readme.txt").resolve()]
    assert written[0].read_bytes() == b"hello"
