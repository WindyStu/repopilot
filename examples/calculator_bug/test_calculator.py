from calculator import divide


def test_divide_preserves_fractional_result():
    assert divide(3, 2) == 1.5


def test_divide_exact_result():
    assert divide(8, 2) == 4
