"""API routes — presentation layer."""
from src.services.user_service import UserService

class UserRoutes:
    def __init__(self, user_service: UserService):
        self.user_service = user_service
    
    def register(self, request):
        return self.user_service.register_user(request["username"], request["email"])
    
    def deactivate(self, user_id: int):
        return self.user_service.deactivate_user(user_id)
