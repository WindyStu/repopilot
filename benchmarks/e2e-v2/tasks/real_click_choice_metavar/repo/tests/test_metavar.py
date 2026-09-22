from click import Argument


def test_plain_optional_argument_gets_brackets():
    assert Argument("name", required=False).make_metavar() == "[NAME]"
