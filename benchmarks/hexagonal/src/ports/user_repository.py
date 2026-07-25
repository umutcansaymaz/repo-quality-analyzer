"""Port — repository interface."""
from abc import ABC, abstractmethod
from src.domain.user import User

class UserRepositoryPort(ABC):
    @abstractmethod
    def get_by_id(self, user_id: int) -> User: pass
    
    @abstractmethod
    def save(self, user: User) -> User: pass
