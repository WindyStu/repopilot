from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay: float = 0.1

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        if self.base_delay < 0:
            raise ValueError("base_delay cannot be negative")

    def delay_for(self, failed_attempt: int) -> float:
        return self.base_delay * (2**failed_attempt)
