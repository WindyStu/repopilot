from collections.abc import Mapping
from pathlib import Path

from safearchive.validation import destination_for


def extract_members(root: Path, members: Mapping[str, bytes]) -> list[Path]:
    written = []
    for member_name, content in members.items():
        destination = destination_for(root, member_name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        written.append(destination)
    return written
