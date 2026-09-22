from click import Argument, Choice, DateTime


def test_optional_choice_does_not_get_double_brackets():
    argument = Argument("method", type=Choice(["foo", "bar"]), required=False)
    assert argument.make_metavar() == "[foo|bar]"


def test_variadic_choice_reuses_choice_brackets():
    argument = Argument("method", type=Choice(["foo", "bar"]), required=False, nargs=-1)
    assert argument.make_metavar() == "[foo|bar]..."


def test_optional_datetime_does_not_get_double_brackets():
    argument = Argument("when", type=DateTime(["%Y-%m-%d"]), required=False)
    assert argument.make_metavar() == "[%Y-%m-%d]"
