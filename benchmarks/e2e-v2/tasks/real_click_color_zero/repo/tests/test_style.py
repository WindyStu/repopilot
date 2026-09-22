from click import style


def test_named_foreground():
    assert style("x", fg="red") == "\033[31mx\033[0m"
