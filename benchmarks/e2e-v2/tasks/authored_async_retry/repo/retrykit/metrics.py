from dataclasses import dataclass


@dataclass
class RetryMetrics:
    attempts: int = 0
    failures: int = 0
