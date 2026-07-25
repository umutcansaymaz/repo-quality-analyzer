"""Domain entity."""
from dataclasses import dataclass

@dataclass
class User:
    id: int
    email: str
    def validate(self):
        return "@" in self.email
