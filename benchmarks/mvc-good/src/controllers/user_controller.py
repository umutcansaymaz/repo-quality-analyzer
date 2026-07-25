"""Controller — orchestrates model and view."""
from src.models.user import User
from src.views.user_view import UserView

class UserController:
    def __init__(self):
        self.view = UserView()
    
    def get_user(self, user_id):
        user = User(user_id, "testuser", "test@test.com")
        if user.is_valid():
            return self.view.render_user(user)
        return self.view.render_error("Invalid user")
