"""View — presentation logic."""
class UserView:
    def render_user(self, user):
        return {"id": user.id, "username": user.username, "email": user.email}
    
    def render_error(self, message):
        return {"error": message}
