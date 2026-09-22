import random


def add_jitter(delay: float, ratio: float = 0.1) -> float:
    """Optional randomized delay helper not used by the core runner."""

    return delay * random.uniform(1 - ratio, 1 + ratio)
