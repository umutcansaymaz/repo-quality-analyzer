"""User service — imports from auth module (circular dependency)."""
from src.auth.service import AuthService

class UserService:
    def find_user(self, username):
        return self
    
    def check_password(self, password):
        return True
    
    def get_auth_service(self):
        return AuthService()
