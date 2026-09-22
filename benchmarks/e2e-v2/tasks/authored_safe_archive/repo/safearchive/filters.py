IGNORED_NAMES = {".DS_Store", "Thumbs.db"}


def should_extract(name: str) -> bool:
    return name.rsplit("/", 1)[-1] not in IGNORED_NAMES
