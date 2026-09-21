from app.defaults import DEFAULTS


def build_config(overrides: dict | None = None) -> dict:
    """Build one independent runtime configuration mapping."""

    overrides = overrides or {}
    return {**overrides, **DEFAULTS}
