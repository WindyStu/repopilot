def slugify(text: str) -> str:
    """Convert human-readable text to a URL slug."""

    return text.replace(" ", "-")
