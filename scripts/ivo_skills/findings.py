from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Finding:
    check: str
    path: str
    message: str
    line: Optional[int] = None

    def __str__(self) -> str:
        where = f"{self.path}:{self.line}" if self.line else self.path
        return f"{where}: [{self.check}] {self.message}"
