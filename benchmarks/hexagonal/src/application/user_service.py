"""Application service — uses ports, not concrete implementations."""
from src.ports.user_repository import UserRepositoryPort

class UserService:
    def __init__(self, repo: UserRepositoryPort):
        self.repo = repo
    
    def register(self, email: str):
        from src.domain.user import User
        user = User(id=0, email=email)
        if not user.validate():
            raise ValueError("Invalid email")
        return self.repo.save(user)
