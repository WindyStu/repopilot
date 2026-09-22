import pytest

from click import style


def test_zero_foreground_palette_index_is_not_dropped():
    assert style("x", fg=0) == "\033[38;5;0mx\033[0m"


def test_zero_background_palette_index_is_not_dropped():
    assert style("x", bg=0) == "\033[48;5;0mx\033[0m"


def test_boolean_is_not_accepted_as_palette_index():
    with pytest.raises(ValueError, match="Unknown color"):
        style("x", fg=False)


def test_out_of_range_palette_index_is_rejected():
    with pytest.raises(ValueError, match="Unknown color"):
        style("x", fg=256)


def test_invalid_rgb_component_is_rejected():
    with pytest.raises(ValueError, match="Unknown color"):
        style("x", bg=(0, -1, 2))
