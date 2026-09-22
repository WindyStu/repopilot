import json
from dataclasses import asdict

from usercodec.models import Address, User

CURRENT_VERSION = 2


def dumps_user(user: User) -> str:
    payload = asdict(user)
    payload["version"] = CURRENT_VERSION
    return json.dumps(payload, sort_keys=True)


def loads_user(raw: str) -> User:
    payload = json.loads(raw)
    version = payload.pop("version", 1)
    if version == 1:
        full_name = payload.pop("name")
        first_name, last_name = full_name.split(" ", 1)
        address = Address(line1=payload.pop("street"), city=payload.pop("city"))
        return User(first_name=first_name, last_name=last_name, address=address, **payload)
    if version != CURRENT_VERSION:
        raise ValueError(f"unsupported user schema version: {version}")
    return User(**payload)
