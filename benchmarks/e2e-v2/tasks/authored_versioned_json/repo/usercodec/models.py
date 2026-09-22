from dataclasses import dataclass


@dataclass(frozen=True)
class Address:
    line1: str
    city: str


@dataclass(frozen=True)
class User:
    first_name: str
    last_name: str
    email: str
    address: Address
