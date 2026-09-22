from pathlib import Path


def destination_for(root: Path, member_name: str) -> Path:
    root = root.resolve()
    candidate = (root / member_name).resolve()
    if not str(candidate).startswith(str(root)):
        raise ValueError(f"archive member escapes destination: {member_name}")
    return candidate
