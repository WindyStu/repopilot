import json

from usercodec import Address, User, dumps_user


def test_dump_uses_current_version():
    user = User("Ada", "Lovelace", "ada@example.test", Address("1 Byte Rd", "London"))

    payload = json.loads(dumps_user(user))

    assert payload["version"] == 2
    assert payload["address"]["city"] == "London"
