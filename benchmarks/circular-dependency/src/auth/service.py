"""Auth service — imports from user module (circular dependency)."""
from src.user.service import UserService

class AuthService:
    def login(self, username, password):
        user = UserService().find_user(username)
        if user and user.check_password(password):
            return self._create_token(user)
        return None
    
    def _create_token(self, user):
        return f"token_{user.id}"
