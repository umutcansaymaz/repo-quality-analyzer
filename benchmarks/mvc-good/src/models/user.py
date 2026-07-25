"""Model — data and business rules."""
class User:
    def __init__(self, id, username, email):
        self.id = id
        self.username = username
        self.email = email
    
    def is_valid(self):
        return len(self.username) >= 3 and "@" in self.email
