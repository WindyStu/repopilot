from app.config import build_config


def test_defaults_are_available():
    assert build_config()["port"] == 8000
