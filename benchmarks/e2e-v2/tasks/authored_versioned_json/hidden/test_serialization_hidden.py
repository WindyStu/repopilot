import json

import pytest

from usercodec import Address, User, dumps_user, loads_user


def test_v2_nested_address_is_typed():
    raw = json.dumps(
        {
            "version": 2,
            "first_name": "Grace",
            "last_name": "Hopper",
            "email": "grace@example.test",
            "address": {"line1": "2 Compiler Way", "city": "Arlington"},
        }
    )

    user = loads_user(raw)

    assert isinstance(user.address, Address)
    assert user.address.city == "Arlington"


def test_v2_round_trip_preserves_nested_dataclass():
    original = User("Ada", "Lovelace", "ada@example.test", Address("1 Byte Rd", "London"))

    assert loads_user(dumps_user(original)) == original


def test_unversioned_v1_payload_remains_supported():
    raw = json.dumps(
        {
            "name": "Katherine Johnson",
            "email": "kj@example.test",
            "street": "3 Orbit Ave",
            "city": "Hampton",
        }
    )

    assert loads_user(raw) == User(
        "Katherine",
        "Johnson",
        "kj@example.test",
        Address("3 Orbit Ave", "Hampton"),
    )


def test_unknown_future_version_is_rejected():
    with pytest.raises(ValueError, match="unsupported user schema version: 99"):
        loads_user('{"version": 99}')
