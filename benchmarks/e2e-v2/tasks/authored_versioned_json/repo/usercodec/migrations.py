def normalize_email(email: str) -> str:
    """Legacy import helper; wire-format decoding does not call it."""

    return email.strip().lower()
