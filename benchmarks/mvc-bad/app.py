"""MVC violation — everything in one class (fat controller + anemic model + no view)."""

class App:
    """Controller + Model + View all in one class."""
    def __init__(self):
        self.users = []
    
    def create_user(self, username, email):
        # Validation (model logic in controller)
        if len(username) < 3:
            return "<html><body><h1>Error: Username too short</h1></body></html>"
        
        # Data storage (model logic)
        user = {"id": len(self.users) + 1, "username": username, "email": email}
        self.users.append(user)
        
        # HTML rendering (view logic in controller)
        return f"<html><body><h1>User created: {username}</h1><p>Email: {email}</p></body></html>"
    
    def list_users(self):
        html = "<html><body><ul>"
        for user in self.users:
            html += f"<li>{user['username']} ({user['email']})</li>"
        html += "</ul></body></html>"
        return html
    
    def delete_user(self, user_id):
        self.users = [u for u in self.users if u["id"] != user_id]
        return "<html><body><h1>User deleted</h1></body></html>"
