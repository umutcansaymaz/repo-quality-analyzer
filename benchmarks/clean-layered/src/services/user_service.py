"""User service — business logic layer."""
from src.repository.user_repo import UserRepository
from src.models.user import User

class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo
    
    def register_user(self, username: str, email: str) -> User:
        user = User(id=0, username=username, email=email)
        return self.repo.save(user)
    
    def deactivate_user(self, user_id: int) -> User:
        user = self.repo.get_by_id(user_id)
        user.is_active = False
        return self.repo.save(user)
